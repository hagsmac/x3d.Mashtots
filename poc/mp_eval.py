#!/usr/bin/env python3
"""Held-out scoring: bits per byte on every held-out set, and MultiBLiMP minimal-pair accuracy.

bpb = (sum of the negative log-likelihood, in nats, of every text token) / (ln 2 x the UTF-8 bytes of the text).
The <eos> that separates documents is fed as context but never scored, so bpb compares tokenizers on exactly the same bytes.
Documents are concatenated and cut into non-overlapping windows of the model's context; the first token of a window sees no earlier window
(the same rule for every arm).
"""
from __future__ import annotations

import math
import pathlib

import numpy as np
import torch

import mp_common as C
import mp_data as D


@torch.no_grad()
def bpb_on_docs(model, enc, docs, device, seq, batch=16, dtype=torch.bfloat16):
    """bpb of the whole set, plus bits and bytes per document (for the paired bootstrap in mp_analyze)."""
    stream, scored, doc_of = [], [], []
    doc_bytes = []
    for d, (ids, t) in enumerate(zip(enc.encode_batch(docs), docs)):
        stream.append(enc.eos)
        scored.append(False)
        doc_of.append(d)
        stream.extend(ids)
        scored.extend([True] * len(ids))
        doc_of.extend([d] * len(ids))
        doc_bytes.append(len(t.encode("utf-8")))
    stream, scored, doc_of = np.asarray(stream, dtype=np.int64), np.asarray(scored, dtype=bool), np.asarray(doc_of)
    nll_tok = np.zeros(len(stream), dtype=np.float64)              # nll of predicting stream[i] (0 where not scored)
    xs, ys, starts = [], [], []

    def flush():
        if not xs:
            return
        T = max(len(x) for x in xs)
        X = torch.full((len(xs), T), enc.eos, dtype=torch.long)
        Y = torch.full((len(xs), T), -1, dtype=torch.long)
        for i, (x, y) in enumerate(zip(xs, ys)):
            X[i, :len(x)] = torch.from_numpy(x)
            Y[i, :len(y)] = torch.from_numpy(y)
        X, Y = X.to(device), Y.to(device)
        with torch.autocast(device_type=device.split(":")[0], dtype=dtype, enabled=device.startswith("cuda")):
            out = model(X, Y, reduction="none")
        per = out["loss"].view(len(xs), T).float().cpu().numpy()
        for i, (a, y) in enumerate(zip(starts, ys)):
            nll_tok[a + 1:a + 1 + len(y)] += per[i, :len(y)]
        xs.clear()
        ys.clear()
        starts.clear()

    n = len(stream)
    for a in range(0, n - 1, seq):
        b = min(n, a + seq + 1)
        if b - a < 2:
            break
        w, sc = stream[a:b], scored[a + 1:b]
        xs.append(w[:-1])
        ys.append(np.where(sc, w[1:], -1))
        starts.append(a)
        if len(xs) >= batch:
            flush()
    flush()
    nll_tok[~scored] = 0.0
    bits_doc = np.bincount(doc_of, weights=nll_tok, minlength=len(docs)) / math.log(2)
    nbytes, ntok = int(sum(doc_bytes)), int(scored.sum())
    nll = float(nll_tok.sum())
    return dict(bpb=nll / (math.log(2) * max(1, nbytes)), nats_per_token=nll / max(1, ntok), tokens=ntok, bytes=nbytes,
                bytes_per_token=nbytes / max(1, ntok), doc_bits=[round(float(x), 2) for x in bits_doc], doc_bytes=doc_bytes)


@torch.no_grad()
def sentence_logprob(model, enc, sents, device, batch=64, dtype=torch.bfloat16):
    out = []
    for i in range(0, len(sents), batch):
        ids = [[enc.eos] + x for x in enc.encode_batch(sents[i:i + batch])]
        T = max(len(x) for x in ids)
        X = torch.full((len(ids), T), enc.eos, dtype=torch.long)
        Y = torch.full((len(ids), T), -1, dtype=torch.long)
        for j, x in enumerate(ids):
            X[j, :len(x)] = torch.tensor(x)
            Y[j, :len(x) - 1] = torch.tensor(x[1:])
        X, Y = X.to(device), Y.to(device)
        with torch.autocast(device_type=device.split(":")[0], dtype=dtype, enabled=device.startswith("cuda")):
            logits = model(X)["logits"].float()
        lp = torch.log_softmax(logits, -1)
        tok = lp.gather(-1, Y.clamp(min=0).unsqueeze(-1)).squeeze(-1) * (Y >= 0)
        out += tok.sum(-1).tolist()
    return out


def score_all(model, enc, root, device, seq, max_pairs=2000):
    root = pathlib.Path(root)
    model.train(False)
    res = {"bpb": {}, "multiblimp": {}}
    for p in sorted((root / "eval").glob("*.jsonl")):
        if p.stem.startswith("multiblimp_"):
            rows = list(D.read_jsonl(p))[:max_pairs]
            if not rows:
                continue
            g = sentence_logprob(model, enc, [r["good"] for r in rows], device)
            b = sentence_logprob(model, enc, [r["bad"] for r in rows], device)
            res["multiblimp"][p.stem.split("_", 1)[1]] = dict(pairs=len(rows), accuracy=float(np.mean([x > y for x, y in zip(g, b)])))
            continue
        docs = [r["t"] for r in D.read_jsonl(p)]
        if docs:
            res["bpb"][p.stem] = bpb_on_docs(model, enc, docs, device, seq)
    for v in "EWG":
        vals = [r["bpb"] for k, r in res["bpb"].items() if k.startswith(v + "_")]
        res[f"bpb_{v}"] = float(np.mean(vals)) if vals else None
    if res.get("bpb_E") is not None and res.get("bpb_W") is not None:
        res["bpb_EW_equal"] = (res["bpb_E"] + res["bpb_W"]) / 2           # the headline: Eastern and Western weighted equally
    res["grade"] = "DRY RUN (tiny model, local)" if C.LOCAL else "Measured"
    return res
