#!/usr/bin/env python3
"""Apply PREREG.md section 5 to the finished runs; write results/RESULTS.md, results/analysis.json and the figures.

usage: python3 -I mp_analyze.py --root DATA [--runs RUNS_DIR] [--out RESULTS_DIR]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp_common as C  # noqa: E402

R = 2000
DECK_SET = "E_armweb_test"


def load_runs(runs):
    out = {}
    for p in sorted(pathlib.Path(runs).glob("*/eval.json")):
        out[p.parent.name] = json.loads(p.read_text())
    return out


def nparams(r):
    return r["params"]["non_embedding"]


def _set_bpb(bits, byts, idx):
    return bits[idx].sum(-1) / byts[idx].sum(-1)


def paired(ra, rb, varieties=("E", "W"), seed=405):
    """Delta = metric(a) - metric(b) with a paired bootstrap over evaluation documents (PREREG 5, H2 / H4)."""
    rng = np.random.default_rng(seed)
    per_var = {v: [] for v in varieties}
    point = {v: [] for v in varieties}
    for k, sa in ra["bpb"].items():
        if k[0] not in varieties or k not in rb["bpb"]:
            continue
        sb = rb["bpb"][k]
        ba, bb = np.array(sa["doc_bits"]), np.array(sb["doc_bits"])
        by = np.array(sa["doc_bytes"], dtype=float)
        if len(ba) != len(bb) or len(ba) == 0:
            continue
        idx = rng.integers(0, len(ba), (R, len(ba)))
        per_var[k[0]].append(_set_bpb(ba, by, idx) - _set_bpb(bb, by, idx))
        point[k[0]].append(ba.sum() / by.sum() - bb.sum() / by.sum())
    vs = [v for v in varieties if per_var[v]]
    if not vs:
        return None
    boot = np.mean([np.mean(per_var[v], axis=0) for v in vs], axis=0)
    est = float(np.mean([np.mean(point[v]) for v in vs]))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return dict(delta=round(est, 4), ci95=[round(float(lo), 4), round(float(hi), 4)], varieties=vs)


def verdict_of(d):
    if d is None:
        return "n/a"
    return "better" if d["ci95"][0] > 0 else "worse" if d["ci95"][1] < 0 else "no difference"


def fit_floor(ns, ys):
    from scipy.optimize import curve_fit
    ns, ys = np.asarray(ns, float), np.asarray(ys, float)

    def f(n, a, alpha, e):
        return np.log(a * n ** -alpha + e)
    try:
        p, _ = curve_fit(f, ns, np.log(ys), p0=[1e3, 0.4, 0.3], bounds=([1e-9, 0.0, 0.0], [1e12, 2.0, 2.0]), maxfev=20000)
        return dict(A=float(p[0]), alpha=float(p[1]), E=float(p[2]), points=len(ns))
    except Exception as exc:
        return dict(error=str(exc)[:200])


def analyze(root, runs_dir, out):
    root, out = pathlib.Path(root), pathlib.Path(out)
    (out / "figs").mkdir(parents=True, exist_ok=True)
    runs = load_runs(runs_dir)
    dry = C.LOCAL or any("DRY RUN" in str(r.get("grade", "")) for r in runs.values())
    G = "DRY RUN" if dry else "Measured"
    A = dict(grade=G, built=C.stamp(), runs={}, H={})
    for name, r in runs.items():
        A["runs"][name] = dict(arm=r["arm"], size=r["size"], grabar=r["grabar"], N=nparams(r), tokens=r["tokens"], bpb_E=r.get("bpb_E"), bpb_W=r.get("bpb_W"),
                               bpb_G=r.get("bpb_G"), bpb_EW=r.get("bpb_EW_equal"), bpb_deck_set=r["bpb"].get(DECK_SET, {}).get("bpb"),
                               western_gap=(r["bpb_W"] - r["bpb_E"]) if r.get("bpb_W") and r.get("bpb_E") else None,
                               multiblimp={k: v["accuracy"] for k, v in r.get("multiblimp", {}).items()}, mixture=r.get("mixture"),
                               epochs=r.get("epochs_per_pool"), train_minutes=round(r.get("train_seconds", 0) / 60, 1), final_loss=r.get("final_loss"))

    main = {n: r for n, r in runs.items() if not r["grabar"]}
    sizes = sorted({r["size"] for r in main.values()}, key=lambda s: C.non_embedding_params(s))

    def get(arm, size, g=False):
        return runs.get(C.run_id(arm, size, g))

    # H2: mashtots vs bpe, bytes vs bpe
    h2 = {}
    for s in sizes:
        a, b, c = get("bpe", s), get("mashtots", s), get("bytes", s)
        h2[s] = dict(mashtots_vs_bpe=paired(a, b) if a and b else None, bytes_vs_bpe=paired(a, c) if a and c else None)
        for k in list(h2[s]):
            if h2[s][k]:
                h2[s][k]["verdict"] = verdict_of(h2[s][k])   # positive delta = the second arm has lower bpb than bpe
    both = [s for s in sizes if h2[s]["mashtots_vs_bpe"]]
    if both:
        top = both[-1]
        verd = [h2[s]["mashtots_vs_bpe"]["verdict"] for s in both]
        if h2[top]["mashtots_vs_bpe"]["verdict"] == "better" and "worse" not in verd:
            h2v = "PASS"
        elif h2[top]["mashtots_vs_bpe"]["verdict"] == "worse":
            h2v = "FAIL"
        else:
            h2v = "inconclusive"
    else:
        h2v = "not run"
    A["H"]["H2"] = dict(per_size=h2, verdict=h2v, rule="mashtots better at the largest size with both arms and worse at none")

    # H3: fits and the deck
    h3 = {"fits": {}, "deck_points": []}
    for arm in C.ARMS:
        pts = [(nparams(get(arm, s)), get(arm, s)) for s in sizes if get(arm, s)]
        for n, r in pts:
            y = r["bpb"].get(DECK_SET, {}).get("bpb")
            if y is None:
                continue
            dk = C.deck_floor(n)
            rel = y / dk - 1
            inside = C.DECK["armenian_floor"]["range"][0] <= n <= C.DECK["armenian_floor"]["range"][1]
            h3["deck_points"].append(dict(arm=arm, N=n, bpb=round(y, 4), deck=round(dk, 4), rel=round(rel, 4), deck_grade=C.floor_grade(n),
                                          verdict=("consistent" if abs(rel) <= 0.10 else "better" if rel < 0 else "worse") if inside else "outside the deck's range"))
        if len(pts) >= 4:
            for key, metric in ((DECK_SET, lambda r: r["bpb"].get(DECK_SET, {}).get("bpb")), ("bpb_EW", lambda r: r.get("bpb_EW_equal"))):
                xs = [(n, metric(r)) for n, r in pts if metric(r)]
                if len(xs) >= 4:
                    h3["fits"][f"{arm}:{key}"] = fit_floor(*zip(*xs))
    A["H"]["H3"] = h3

    # H4: Grabar
    h4 = {}
    for s in sizes:
        a, b = get("bpe", s), get("bpe", s, True)
        if a and b:
            d = paired(a, b, varieties=("G",))
            ew = (b.get("bpb_EW_equal") or 0) - (a.get("bpb_EW_equal") or 0)
            h4[s] = dict(grabar=d, verdict=verdict_of(d), EW_cost=round(ew, 4))
    if h4:
        ok = all(v["verdict"] == "better" and v["EW_cost"] <= 0.01 for v in h4.values())
        A["H"]["H4"] = dict(per_size=h4, verdict="PASS" if ok and len(h4) >= 2 else "FAIL" if any(v["verdict"] != "better" for v in h4.values()) else "inconclusive")
    else:
        A["H"]["H4"] = dict(verdict="not run")

    # H6: grammar, binomial test for the largest run of each arm
    h6 = {}
    from scipy.stats import binomtest
    for arm in C.ARMS:
        big = [get(arm, s) for s in sizes if get(arm, s)]
        if big:
            r = big[-1]
            h6[arm] = {}
            for lang, m in r.get("multiblimp", {}).items():
                k = int(round(m["accuracy"] * m["pairs"]))
                h6[arm][lang] = dict(size=r["size"], accuracy=round(m["accuracy"], 4), pairs=m["pairs"],
                                     p_one_sided=float(binomtest(k, m["pairs"], 0.5, alternative="greater").pvalue))
    A["H"]["H6"] = h6

    # H1 and the tokenizer study come from the tokenizer cells
    A["token_bill"] = C.load_json(out / "token_bill.json")
    A["our_tokenizers"] = C.load_json(out / "our_tokenizers.json")
    A["data_stats"] = C.load_json(root / "data_stats.json")
    if A["token_bill"]:
        h1 = {}
        for name, row in A["token_bill"]["rows"].items():
            if row.get("udhr_ratio") and row.get("deck"):
                rel = row["udhr_ratio"] / row["deck"] - 1
                h1[name] = dict(ours=row["udhr_ratio"], deck=row["deck"], rel=round(rel, 4), reproduces=abs(rel) <= 0.05)
        A["H"]["H1"] = h1
    C.dump_json(A, out / "analysis.json")
    figures(A, out / "figs")
    (out / "RESULTS.md").write_text(report(A))
    print((out / "RESULTS.md").read_text()[:6000])
    return A


# ---------------------------------------------------------------------------------------------------------- figures
COL = {"bytes": "#8a8f98", "bpe": "#3b6ea8", "mashtots": "#b8862b", "bpe_morph": "#7aa0cc", "mashtots_nomorph": "#d9b56b"}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    fams = []
    for fam in ("DejaVu Sans", "Noto Sans Armenian", "Noto Serif Armenian", "Arial Unicode MS"):     # Latin first, Armenian as fallback
        try:
            font_manager.findfont(fam, fallback_to_default=False)
            fams.append(fam)
        except Exception:
            continue
    if fams:
        plt.rcParams["font.family"] = fams
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 130, "savefig.bbox": "tight"})
    return plt


def figures(A, d):
    plt = _plt()
    tag = A["grade"]
    tb = A.get("token_bill")
    if tb:
        rows = [(n, r) for n, r in tb["rows"].items() if r.get("udhr_ratio")]
        rows.sort(key=lambda x: x[1]["udhr_ratio"])
        ours = (A.get("our_tokenizers") or {}).get("arms", {})
        fig, ax = plt.subplots(figsize=(8, 0.42 * (len(rows) + len(ours)) + 1.2))
        labels, vals, cols = [], [], []
        for n, r in rows:
            labels.append(n.split(" (")[0])
            vals.append(r["udhr_ratio"])
            cols.append("#5b6470")
        for arm, r in ours.items():
            labels.append(f"ours: {arm}")
            vals.append(r["udhr_ratio"])
            cols.append(COL.get(arm, "#999"))
        y = np.arange(len(labels))
        ax.barh(y, vals, color=cols)
        for i, (n, r) in enumerate(rows):
            if r.get("deck"):
                ax.plot([r["deck"]], [i], "k|", ms=14)
        ax.axvline(1.0, color="#999", lw=0.8, ls=":")
        ax.set_yticks(y, labels)
        ax.set_xscale("log")
        ax.set_xlabel("UDHR tokens, Armenian / English (log scale; | = the deck's figure)")
        ax.set_title(f"The token bill [{tag}]", loc="left")
        fig.savefig(d / "token_bill.png")
        plt.close(fig)
    ot = A.get("our_tokenizers")
    if tb and ot:
        fig, ax = plt.subplots(figsize=(9, 4))
        names = [n for n, r in tb["rows"].items() if r.get("fertility")] + [f"ours: {a}" for a in ot["arms"]]
        keys = ["E:ud_armtdp", "W:ud_hyw", "G:ud_caval"]
        vals = [[tb["rows"][n]["fertility"][k]["tok_per_word"] for k in keys] for n in names if n in tb["rows"]]
        vals += [[ot["arms"][a]["fertility"][k]["tok_per_word"] for k in keys] for a in ot["arms"]]
        x = np.arange(len(names))
        for j, (k, c) in enumerate(zip(keys, ["#3b6ea8", "#b8862b", "#7a4e8a"])):
            ax.bar(x + (j - 1) * 0.27, [v[j] for v in vals], 0.27, label={"E": "Eastern", "W": "Western", "G": "Grabar"}[k[0]], color=c)
        ax.set_xticks(x, [n.split(" (")[0] for n in names], rotation=40, ha="right", fontsize=8)
        ax.set_ylabel("tokens per word (UD test)")
        ax.legend(frameon=False)
        ax.set_title(f"Word cost by variety [{tag}]", loc="left")
        fig.savefig(d / "fertility.png")
        plt.close(fig)
    pts = A["H"].get("H3", {}).get("deck_points", [])
    if pts:
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
        ns = np.logspace(math.log10(3e6), math.log10(1.2e9), 200)
        ax.plot(ns, [C.deck_floor(n) for n in ns], "k--", lw=1, label="deck: 4.9e5 N^-0.795 + 0.439")
        ax.axvspan(70e6, 1e9, color="#e8e2d0", alpha=0.6, lw=0, label="deck Established (70M-1B)")
        ax.plot([C.COPA_REFERENCE["params"]], [C.COPA_REFERENCE["bpb_panel_mean_union"]], "s", color="#444", label="COPA 410M (published, other panel)")
        for arm in C.ARMS:
            p = sorted([(q["N"], q["bpb"]) for q in pts if q["arm"] == arm])
            if p:
                ax.plot(*zip(*p), "o-", color=COL[arm], label=f"ours: {arm}")
            fit = A["H"]["H3"]["fits"].get(f"{arm}:{DECK_SET}")
            if fit and "A" in fit:
                ax.plot(ns, fit["A"] * ns ** -fit["alpha"] + fit["E"], ":", color=COL[arm], lw=1)
        ax.set_xscale("log")
        ax.set_xlabel("non-embedding parameters N")
        ax.set_ylabel("bits per byte, ArmWeb test (Eastern news)")
        ax.set_title(f"The Armenian floor [{tag}]", loc="left")
        ax.legend(frameon=False, fontsize=7)
        fig.savefig(d / "scaling.png")
        plt.close(fig)


# ---------------------------------------------------------------------------------------------------------- the report
def _f(x, n=3):
    return "-" if x is None else f"{x:.{n}f}"


def report(A):
    g = A["grade"]
    L = [f"# Mashtots PoC results ({g})", "", f"Built {A['built']}. Every number below is **{g}** unless its row says otherwise. Rules: `PREREG.md`.", ""]
    if g == "DRY RUN":
        L += ["> **DRY RUN.** A tiny model on a few MB of UD text on a Mac: these numbers test the plumbing and mean nothing about Armenian.", ""]
    h1 = A["H"].get("H1")
    if h1:
        L += ["## H1 The token bill (UDHR, Armenian tokens / English tokens)", "", "| tokenizer | ours | deck (its grade: Measured) | gap | within 5 % |", "|---|---|---|---|---|"]
        for n, r in h1.items():
            L.append(f"| {n} | {r['ours']:.2f} | {r['deck']:.2f} | {100 * r['rel']:+.1f} % | {'yes' if r['reproduces'] else 'no'} |")
        L.append("")
    ot = A.get("our_tokenizers")
    if ot:
        L += ["## Our tokenizers (tokens per word on UD test sentences; stem-boundary recall / precision against UD lemmas)", "",
              "| arm | vocab | Eastern | Western | Grabar | UDHR hy/en | boundary E (R/P) | boundary W (R/P) | round-trip failures |", "|---|---|---|---|---|---|---|---|---|"]
        for arm, r in ot["arms"].items():
            f, b = r["fertility"], r["boundary"]
            L.append(f"| {arm} | {r['vocab']} | {f['E:ud_armtdp']['tok_per_word']:.2f} | {f['W:ud_hyw']['tok_per_word']:.2f} | {f['G:ud_caval']['tok_per_word']:.2f} | "
                     f"{r['udhr_ratio']:.2f} | {b['E']['recall']:.2f} / {b['E']['precision']:.2f} | {b['W']['recall']:.2f} / {b['W']['precision']:.2f} | {r['roundtrip_failures']} |")
        L += ["", "Our tokenizers are trained on Armenian only, so their UDHR ratio says what an Armenian-first vocabulary costs English, not a like-for-like bill.", ""]
    L += ["## The runs", "", "| run | N (non-emb.) | tokens | bpb E | bpb W | bpb G | **bpb E+W** | ArmWeb test | W - E | MultiBLiMP hye / hyw | minutes |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in sorted(A["runs"].items(), key=lambda kv: (kv[1]["N"], kv[0])):
        mb = r["multiblimp"]
        L.append(f"| {n} | {r['N'] / 1e6:.1f}M | {r['tokens'] / 1e6:.0f}M | {_f(r['bpb_E'])} | {_f(r['bpb_W'])} | {_f(r['bpb_G'])} | **{_f(r['bpb_EW'])}** | "
                 f"{_f(r['bpb_deck_set'])} | {_f(r['western_gap'])} | {_f(mb.get('hye'), 2)} / {_f(mb.get('hyw'), 2)} | {r['train_minutes']} |")
    L.append("")
    h2 = A["H"]["H2"]
    L += [f"## H2 Does the script-aware tokenizer help? **{h2['verdict']}**", "", f"Rule: {h2['rule']}. Delta = bpb(bpe) - bpb(other), E+W equal; positive = the other arm is better.", "",
          "| size | mashtots vs bpe | 95 % CI | verdict | bytes vs bpe | 95 % CI |", "|---|---|---|---|---|---|"]
    for s, v in h2["per_size"].items():
        m, b = v["mashtots_vs_bpe"], v["bytes_vs_bpe"]
        L.append(f"| {s} | {_f(m and m['delta'], 4)} | {m and m['ci95']} | {m and m['verdict']} | {_f(b and b['delta'], 4)} | {b and b['ci95']} |")
    L.append("")
    h3 = A["H"]["H3"]
    if h3["deck_points"]:
        L += ["## H3 The floor, against the deck's bpb(N) = 4.9e5 N^-0.795 + 0.439", "", "| arm | N | ours (ArmWeb test) | deck | gap | deck's grade at N | verdict |", "|---|---|---|---|---|---|---|"]
        for q in h3["deck_points"]:
            L.append(f"| {q['arm']} | {q['N'] / 1e6:.1f}M | {q['bpb']:.3f} | {q['deck']:.3f} | {100 * q['rel']:+.1f} % | {q['deck_grade']} | {q['verdict']} |")
        for k, f in h3["fits"].items():
            if "A" in f:
                L.append(f"\nFit {k}: bpb(N) = {f['A']:.3g} N^-{f['alpha']:.3f} + {f['E']:.3f} ({f['points']} points, 3 parameters: indicative only; "
                         f"E beyond 150M is an Estimate).")
        L.append("")
    h4 = A["H"].get("H4", {})
    L += [f"## H4 Does Grabar text help Grabar? **{h4.get('verdict')}**", ""]
    for s, v in h4.get("per_size", {}).items():
        L.append(f"* {s}: Delta bpb_G = {v['grabar'] and v['grabar']['delta']} (95 % CI {v['grabar'] and v['grabar']['ci95']}), {v['verdict']}; cost on E+W {v['EW_cost']:+.4f} bpb")
    L += ["", "The `-G` models were trained on CC BY-NC-SA text (UD CAVaL): they carry a non-commercial condition.", ""]
    h6 = A["H"].get("H6", {})
    if h6:
        L += ["## H6 Grammar (MultiBLiMP)", ""]
        for arm, langs in h6.items():
            for lang, r in langs.items():
                L.append(f"* {arm} {r['size']}, {lang}: {r['accuracy']:.3f} of {r['pairs']} pairs (one-sided p = {r['p_one_sided']:.2g} against chance)")
        L.append("")
    ds = A.get("data_stats")
    if ds:
        what = "counts of the dry-run data" if g == "DRY RUN" else "Measured on this run's download"
        L += [f"## Data ({what})", "", "| pool | MB | documents |", "|---|---|---|"]
        for v, p in ds["pools"].items():
            L.append(f"| {v} | {p['bytes'] / 1e6:.1f} | {p['docs']} |")
        L += ["", f"Variety classifier on single UD test sentences: {ds['classifier']['accuracy']}.",
              "Dialect x spelling, bytes kept: " + ", ".join(f"{k} {v / 1e6:.1f} MB" for k, v in ds.get("crosstab_bytes", {}).items()), ""]
    L += ["## Grades of the deck's figures used here", ""]
    for k, v in C.DECK.items():
        L.append(f"* {k}: {v['grade']}")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--runs", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    analyze(a.root, a.runs or os.path.join(a.root, "runs"), a.out or os.path.join(a.root, "results"))


if __name__ == "__main__":
    main()
