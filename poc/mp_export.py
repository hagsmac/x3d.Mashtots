#!/usr/bin/env python3
"""Export the real model's letter attention, letter embeddings and the landing's two texts as one JSON for an X3D scene (schema: EXPORT-SCHEMA.md).

usage: python3 -I mp_export.py --root DATA --runs RUNS --out results/mashtots_model_export.json
Selection rules are PREREG.md section 6 (fixed before training): the largest finished `bytes` model for letter-level attention and contextual
embeddings, the largest finished `mashtots` model for input embeddings and token pieces; the three most structured heads, at most one per layer.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp_common as C  # noqa: E402
import mp_data as D  # noqa: E402
import mp_model as M  # noqa: E402
import mp_tok as TK  # noqa: E402

WIN, NWIN, MAXD = 512, 200, 64
NL = len(C.LETTERS_38)
LETTER_ID = {}
for i, c in enumerate(C.LETTERS_38):
    LETTER_ID[c] = i
    LETTER_ID[C.LOWER[c]] = i


def largest(runs, arm):
    best = None
    for p in pathlib.Path(runs).glob(f"{arm}-*/done.json"):
        d = p.parent
        if d.name.endswith("-G"):
            continue
        meta = json.loads((d / "meta.json").read_text())
        n = meta["params"]["non_embedding"]
        if best is None or n > best[0]:
            best = (n, d, meta)
    return best


def load_model(run_dir, device):
    cfg = M.Config(**json.loads((run_dir / "config.json").read_text()))
    m = M.GPT(cfg)
    sd = torch.load(run_dir / "model.pt", map_location="cpu", weights_only=False)
    m.load_state_dict({k: v.float() if v.is_floating_point() else v for k, v in sd.items()})
    m.train(False)
    return m.to(device), cfg


def byte_letters(text):
    """For every UTF-8 byte of `text`: (letter id or -1, index of its character, is the last byte of that character)."""
    lid, cidx, last = [], [], []
    for ci, ch in enumerate(text):
        n = len(ch.encode("utf-8"))
        L = LETTER_ID.get(ch, -1)
        for k in range(n):
            lid.append(L)
            cidx.append(ci)
            last.append(k == n - 1)
    return np.array(lid), np.array(cidx), np.array(last)


def sample_texts(root):
    out = []
    for name in ("E_armweb_test", "W_wiki_heldout", "E_ud_armtdp_test", "W_ud_hyw_test"):
        p = pathlib.Path(root) / "eval" / f"{name}.jsonl"
        if p.exists():
            out.append((name, [r["t"] for r in D.read_jsonl(p)]))
    pick = [x for x in out if x[0] in ("E_armweb_test", "W_wiki_heldout")]
    return pick if len(pick) == 2 else [x for x in out if x[0].endswith("_test") and "ud" in x[0]][:2] or out[:2]


@torch.no_grad()
def letter_attention(model, cfg, root, device):
    L, H = cfg.L, cfg.H
    S = torch.zeros(L, H, NL, NL, dtype=torch.float64, device=device)
    Cn = torch.zeros(NL, NL, dtype=torch.float64, device=device)
    hid_sum = torch.zeros(NL, cfg.d, dtype=torch.float64, device=device)
    hid_n = torch.zeros(NL, dtype=torch.float64, device=device)
    band = torch.ones(WIN, WIN, device=device).tril()
    band = band - torch.ones(WIN, WIN, device=device).tril(-MAXD - 1)
    used = {}
    for name, docs in sample_texts(root):
        text = "\n".join(docs)
        raw = text.encode("utf-8")
        lid, cix, last = byte_letters(text)
        k = 0
        for a in range(0, len(raw) - WIN, WIN):
            if k >= NWIN:
                break
            ids = torch.tensor(list(raw[a:a + WIN]), device=device)[None]
            out = model(ids, need_attn=True, need_hidden=True)
            att = torch.stack([x[0] for x in out["attn"]]).double()                      # L, H, T, T
            ll = torch.tensor(lid[a:a + WIN], device=device)
            cc = torch.tensor(cix[a:a + WIN], device=device)
            bw = band * (cc[:, None] != cc[None, :])                                     # not within one letter occurrence (its own two bytes)
            oh = torch.zeros(WIN, NL, dtype=torch.float64, device=device)
            ok = ll >= 0
            oh[ok.nonzero().squeeze(-1), ll[ok]] = 1.0
            S += torch.einsum("lhpq,pi,qj->lhij", att * bw, oh, oh)
            Cn += oh.T @ bw.double() @ oh
            hl = out["hidden"][-1][0].double()
            lm = torch.tensor(last[a:a + WIN], device=device) & ok
            idx = lm.nonzero().squeeze(-1)
            hid_sum.index_add_(0, ll[idx], hl[idx])
            hid_n.index_add_(0, ll[idx], torch.ones(len(idx), dtype=torch.float64, device=device))
            k += 1
        used[name] = k
    A = (S / Cn.clamp(min=1)).cpu().numpy()
    emb = (hid_sum / hid_n.clamp(min=1)[:, None]).cpu().numpy()
    return A, Cn.cpu().numpy(), emb, hid_n.cpu().numpy(), used


def row_norm(m):
    r = m.sum(-1, keepdims=True)
    return np.where(r > 0, m / np.where(r > 0, r, 1), 0)


def structure(A36):
    P = row_norm(A36)
    rows = P[P.sum(-1) > 0]
    if not len(rows):
        return 0.0
    ent = -(rows * np.log(np.clip(rows, 1e-12, 1))).sum(-1)
    return float(1 - ent.mean() / math.log(36))


def select_heads(A):
    L, H = A.shape[:2]
    sc = [(structure(A[l, h, :36, :36]), l, h) for l in range(L) for h in range(H)]
    sc.sort(key=lambda x: (-x[0], x[1], x[2]))
    chosen, layers = [], set()
    for s, l, h in sc:
        if l in layers:
            continue
        chosen.append(dict(layer=l, head=h, structure=round(s, 4)))
        layers.add(l)
        if len(chosen) == 3:
            break
    if len(chosen) < 3:                                      # fewer layers than 3: allow repeats in layer order
        for s, l, h in sc:
            if all((c["layer"], c["head"]) != (l, h) for c in chosen):
                chosen.append(dict(layer=l, head=h, structure=round(s, 4)))
            if len(chosen) == 3:
                break
    return chosen, [[round(structure(A[l, h, :36, :36]), 4) for h in range(H)] for l in range(L)]


def pca3(X, mask=None):
    X = np.asarray(X, dtype=np.float64)
    keep = np.ones(len(X), bool) if mask is None else np.asarray(mask, bool)
    Y = X[keep] - X[keep].mean(0)
    U, s, Vt = np.linalg.svd(Y, full_matrices=False)
    P = np.zeros((len(X), 3))
    P[keep] = Y @ Vt[:3].T
    scale = np.abs(P[keep]).max() or 1
    return (P / scale).round(4).tolist(), (s[:3] ** 2 / (s ** 2).sum()).round(4).tolist()


def cosine(X):
    X = np.asarray(X, dtype=np.float64)
    n = np.linalg.norm(X, axis=1, keepdims=True)
    Z = X / np.where(n > 0, n, 1)
    return (Z @ Z.T).round(4).tolist()


@torch.no_grad()
def probe_bytes(model, text, heads, device):
    raw = text.encode("utf-8")
    ids = torch.tensor([256] + list(raw), device=device)[None]          # <eos> as the start
    out = model(ids, need_attn=True)
    lp = torch.log_softmax(out["logits"][0, :-1].float(), -1)
    nll = -lp.gather(-1, ids[0, 1:, None]).squeeze(-1).cpu().numpy() / math.log(2)
    _, cidx, _ = byte_letters(text)
    n = len(text)
    surpr = np.bincount(cidx, weights=nll, minlength=n)
    mats = []
    for hsel in heads:
        a = out["attn"][hsel["layer"]][0, hsel["head"], 1:, 1:].double().cpu().numpy()  # byte x byte, without the start token
        G = np.zeros((n, n))
        cnt = np.bincount(cidx, minlength=n).astype(float)
        np.add.at(G, (cidx[:, None].repeat(len(cidx), 1), cidx[None, :].repeat(len(cidx), 0)), a)
        G = G / np.maximum(cnt[:, None], 1)                                   # mean over the query glyph's bytes, summed over the key glyph's
        mats.append(G.round(4).tolist())
    return surpr.round(3).tolist(), mats


@torch.no_grad()
def probe_tokens(model, enc, text, device):
    ids = enc.encode(text)
    x = torch.tensor([enc.eos] + ids, device=device)[None]
    lp = torch.log_softmax(model(x)["logits"][0, :-1].float(), -1)
    nll = (-lp.gather(-1, x[0, 1:, None]).squeeze(-1) / math.log(2)).cpu().numpy()
    pieces = TK.probe_pieces(enc, text)["pieces"]
    return dict(pieces=pieces, surprisal_bits=nll.round(3).tolist())


def export(root, runs, out, device="cpu"):
    root, runs = pathlib.Path(root), pathlib.Path(runs)
    grade = "DRY RUN (tiny model, local)" if C.LOCAL else "Measured"
    res = dict(schema="mashtots-export/1", version=C.VERSION, built=C.stamp(), grade=grade,
               prereg_sha256=C.sha256_file(root / "PREREG.md") if (root / "PREREG.md").exists() else None,
               letters=[dict(index=i, ch=c, lower=C.LOWER[c], numeral=C.NUMERAL.get(c), mashtots=i < 36) for i, c in enumerate(C.LETTERS_38)],
               notes=["attention values are means over pairs of byte positions at most 64 apart, never within one letter occurrence (PREREG 6)",
                      "row-normalised maps follow the landing's convention (each row sums to 1 over the 36 letters)"])
    b = largest(runs, "bytes")
    if b:
        n, d, meta = b
        model, cfg = load_model(d, device)
        A, counts, emb, occ, used = letter_attention(model, cfg, root, device)
        heads, struct = select_heads(A)
        res["letters_model"] = dict(run=d.name, params=meta["params"], tokens=meta["tokens"], bpb=C.load_json(d / "eval.json", {}).get("bpb_EW_equal"),
                                    layers=cfg.L, heads=cfg.H, windows_used=used)
        res["attention"] = dict(window=WIN, max_distance=MAXD, layers=cfg.L, heads=cfg.H, pair_counts=counts.astype(int).tolist(),
                                letter_attention=np.round(A, 6).tolist(), structure=struct, selected_heads=heads,
                                selected_row_normalised=[row_norm(A[h["layer"], h["head"], :36, :36]).round(4).tolist() for h in heads],
                                mean_row_normalised=row_norm(A[:, :, :36, :36].mean((0, 1))).round(4).tolist())
        p3, ev = pca3(emb, occ > 0)
        res["embeddings"] = dict(contextual=dict(source=d.name, occurrences=occ.astype(int).tolist(), pca3=p3, explained=ev, cosine36=cosine(emb[:36])))
        res["probes"] = {}
        for k, txt in C.PROBES.items():
            s, mats = probe_bytes(model, txt, heads, device)
            slots, n_ = [], 0
            for ch in C.LANDING_TEXTS[k]:                    # the landing writes every character but the spaces as a glyph slot
                slots.append(None if ch == " " else n_)
                n_ += ch != " "
            res["probes"][k] = dict(upper=C.LANDING_TEXTS[k], text=txt, glyphs=list(C.LANDING_TEXTS[k]), landing_slot=slots, surprisal_bits=s,
                                    attention_selected=mats)
    m = largest(runs, "mashtots")
    if m:
        n, d, meta = m
        model, cfg = load_model(d, device)
        enc = TK.load_encoder(root, "mashtots")
        W = model.emb.weight.detach().double().cpu().numpy()
        ids = [enc.tok.token_to_id(C.LOWER[c]) for c in C.LETTERS_38]
        X = np.stack([W[i] if i is not None else np.zeros(W.shape[1]) for i in ids])
        p3, ev = pca3(X, [i is not None for i in ids])
        res.setdefault("embeddings", {})["input"] = dict(source=d.name, token_ids=ids, pca3=p3, explained=ev, cosine36=cosine(X[:36]))
        res["token_model"] = dict(run=d.name, params=meta["params"], bpb=C.load_json(d / "eval.json", {}).get("bpb_EW_equal"))
        for k, txt in C.PROBES.items():
            res.setdefault("probes", {}).setdefault(k, dict(upper=C.LANDING_TEXTS[k], text=txt))["token_model"] = probe_tokens(model, enc, txt, device)
    out = pathlib.Path(out)
    C.dump_json(res, out)
    print(f"export: {out} ({out.stat().st_size / 1e6:.2f} MB); letters model {res.get('letters_model', {}).get('run')}, "
          f"token model {res.get('token_model', {}).get('run')}; heads {res.get('attention', {}).get('selected_heads')}")
    preview(res, out.parent / "figs")
    return res


def preview(res, d):
    if "attention" not in res:
        return
    import mp_analyze as AN
    plt = AN._plt()
    d.mkdir(parents=True, exist_ok=True)
    letters = [l["ch"] for l in res["letters"][:36]]
    fig, axs = plt.subplots(1, 4, figsize=(17, 4.6))
    for ax, m, h in zip(axs[:3], res["attention"]["selected_row_normalised"], res["attention"]["selected_heads"]):
        ax.imshow(np.array(m), cmap="magma")
        ax.set_title(f"layer {h['layer']} head {h['head']} (structure {h['structure']:.2f})", fontsize=9)
        ax.set_xticks(range(36), letters, fontsize=5)
        ax.set_yticks(range(36), letters, fontsize=5)
    p = np.array(res["embeddings"]["contextual"]["pca3"])[:36]
    axs[3].scatter(p[:, 0], p[:, 1], s=8, color="#b8862b")
    for i, c in enumerate(letters):
        axs[3].annotate(c, (p[i, 0], p[i, 1]), fontsize=9)
    axs[3].set_title("letters, contextual embedding (PCA 1-2)", fontsize=9)
    fig.suptitle(f"The real model, read as the landing reads its authored heads [{res['grade']}]", x=0.01, ha="left")
    fig.savefig(d / "export_preview.png")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--runs", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    export(a.root, a.runs or os.path.join(a.root, "runs"), a.out or os.path.join(a.root, "results", "mashtots_model_export.json"), a.device)


if __name__ == "__main__":
    main()
