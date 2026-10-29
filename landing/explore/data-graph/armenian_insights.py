#!/usr/bin/env python3
"""What the Armenian language itself shows when measured: three questions answered from corpora already on this disk (no download).

  1. Did the alphabet's structure survive fifteen centuries?  Grabar (UD CAVaL, 5th century on) against modern Eastern (UD ArmTDP) and
     Western Armenian (UD ArmTDP-hyw): letter frequencies, the bigram graph, and the fastest mode's vowel split, era by era.
  2. Does Mashtots's ORDER of the letters carry linguistic structure?  The deck's third attention head ("order") assumes that neighbours in
     the alphabet attend to each other. Measured: is co-occurrence in Grabar related to distance in the alphabet? (Permutation test.)
  3. What do machines charge for the language of 405?  Tokens per word for Grabar, Eastern and Western Armenian, and English
     (the UDHR's English as the reference text), with two tokenizers on disk (Mistral Nemo Tekken, and Llama-family if present).
Every number printed is Measured on the named corpus; nothing here measures inspiration, which stays a tradition (Koryun's account).
Run: python3 explore/data-graph/armenian_insights.py   -> out/insights.json and out/insights.md
"""
import glob, json, os, re, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.expanduser("~/Projects/x3d/work/armenian-tokenizer-census/data")
L = json.load(open(os.path.join(ROOT, "scratch/landing.json"), encoding="utf-8"))
LET = "".join(d[0] for d in L["DATA"]); N = 36; IDX = {c: i for i, c in enumerate(LET)}
VOWEL = np.array([d[5] for d in L["DATA"]], bool)
CORPORA = {"Grabar (CAVaL)": "UD_Classical_Armenian-CAVaL", "Eastern (ArmTDP)": "UD_Armenian-ArmTDP", "Western (ArmTDP-hyw)": "UD_Western_Armenian-ArmTDP"}

def sentences(folder):
    out = []
    for fn in sorted(glob.glob(os.path.join(DATA, folder, "*.conllu"))):
        for line in open(fn, encoding="utf-8"):
            if line.startswith("# text = "): out.append(line[9:].strip())
    return out
def words(sents):
    ws, extra = [], collections.Counter()
    for s in sents:
        for w in re.findall(r"[Ա-Ֆա-և]+", s):
            w = w.upper().replace("և".upper(), "ԵՒ").replace("և", "ԵՒ")
            for ch in w:
                if ch not in IDX: extra[ch] += 1
            k = "".join(ch for ch in w if ch in IDX)
            if k: ws.append(k)
    return ws, extra
def stats(ws):
    f = np.zeros(N); B = np.zeros((N, N))
    for w in ws:
        for ch in w: f[IDX[ch]] += 1
        for a, b in zip(w, w[1:]): B[IDX[a], IDX[b]] += 1
    return f, B
def fast_mode(B):
    C = B + B.T; np.fill_diagonal(C, 0); d = np.maximum(C.sum(1), 1e-9)
    ev, U = np.linalg.eigh(C / np.sqrt(np.outer(d, d))); v = U[:, 0] / np.sqrt(d)
    if np.mean((v > 0) == VOWEL) < 0.5: v = -v
    return float(ev[0]), v / np.abs(v).max()
def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b)); return float(np.corrcoef(ra, rb)[0, 1])
def rownorm(B): return B / np.maximum(B.sum(1, keepdims=True), 1)

res = {"grade": "Measured", "eras": {}}
F, BB = {}, {}
for name, folder in CORPORA.items():
    ws, extra = words(sentences(folder)); f, B = stats(ws); lam, v = fast_mode(B)
    F[name], BB[name] = f, B
    res["eras"][name] = dict(words=len(ws), letters=int(f.sum()), outside_36={k: v_ for k, v_ in extra.most_common(4)},
                             fast_mode_eigenvalue=round(lam, 3), vowel_side="".join(LET[i] for i in range(N) if v[i] > 0),
                             agree_with_vowel_flags=round(float(np.mean((v > 0) == VOWEL)), 3), top5="".join(LET[i] for i in np.argsort(-f)[:5]))
names = list(CORPORA)
res["across_eras"] = {}
for a in range(3):
    for b in range(a + 1, 3):
        A, Bm = names[a], names[b]
        iu = np.triu_indices(N, 1)
        res["across_eras"][f"{A} vs {Bm}"] = dict(
            letter_frequency_spearman=round(spearman(F[A], F[Bm]), 3),
            bigram_rows_correlation=round(float(np.corrcoef(rownorm(BB[A]).ravel(), rownorm(BB[Bm]).ravel())[0, 1]), 3))

# 2. the alphabet's order: co-occurrence against distance in the alphabet (Grabar), permutation test
B = BB[names[0]]; C = B + B.T; np.fill_diagonal(C, 0); P = C / C.sum()
iu = np.triu_indices(N, 1); dist = np.abs(iu[0] - iu[1]).astype(float); w = P[iu]
obs = spearman(-dist, w)                              # > 0: neighbours in the alphabet co-occur more
rng = np.random.default_rng(405); perm = []
for _ in range(2000):
    p = rng.permutation(N); d = np.abs(p[iu[0]] - p[iu[1]]).astype(float); perm.append(spearman(-d, w))
perm = np.array(perm)
res["alphabet_order"] = dict(spearman_neighbourliness=round(obs, 3), permutation_p=round(float(np.mean(perm >= obs)), 4), null_mean=round(float(perm.mean()), 3), null_sd=round(float(perm.std()), 3),
                             within_row_vs_across=None)
row = lambda i: i // 9; same = np.array([row(i) == row(j) for i, j in zip(*iu)])
res["alphabet_order"]["within_row_vs_across"] = dict(mean_cooccurrence_same_row=float(w[same].mean()), mean_cooccurrence_other_rows=float(w[~same].mean()))

# 3. what tokenizers charge: tokens per word
from tokenizers import Tokenizer
toks = {}
for label, path in (("Mistral Nemo (Tekken)", "tok-mistral-nemo/tokenizer.json"), ("DeepSeek V3", "tok-deepseek-v3/tokenizer.json"), ("gpt-oss (o200k-based)", "tok-gpt-oss-20b/tokenizer.json")):
    fp = os.path.join(DATA, path)
    if os.path.exists(fp): toks[label] = Tokenizer.from_file(fp)
def eng_words():
    import xml.etree.ElementTree as ET
    fp = os.path.join(DATA, "udhr", "udhr_eng.xml"); t = ET.parse(fp)
    txt = " ".join(e.text or "" for e in t.iter() if (e.text or "").strip()); return [txt]
texts = {n: sentences(f) for n, f in CORPORA.items()}; texts["English (UDHR)"] = eng_words()
res["tokens_per_word"] = {}
for tn, tk in toks.items():
    row_ = {}
    for n, sents in texts.items():
        sample = sents[:3000]; nw = sum(len(re.findall(r"\w+", s)) for s in sample); nt = sum(len(tk.encode(s).ids) for s in sample)
        row_[n] = round(nt / max(nw, 1), 2)
    res["tokens_per_word"][tn] = row_

os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(res, open(os.path.join(HERE, "out", "insights.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
md = ["# Armenian, measured: three questions (corpora on disk; every number Measured)\n"]
md.append("## 1. Fifteen centuries\n\n| era | words | letters | top 5 | fastest mode, vowel side | agrees with the vowel flags |\n|---|---:|---:|---|---|---:|")
for n, e in res["eras"].items(): md.append(f"| {n} | {e['words']:,} | {e['letters']:,} | {e['top5']} | {e['vowel_side']} | {e['agree_with_vowel_flags']:.0%} |")
md.append("\n| pair | letter frequencies (Spearman) | bigram rows (Pearson) |\n|---|---:|---:|")
for k, v in res["across_eras"].items(): md.append(f"| {k} | {v['letter_frequency_spearman']:+.3f} | {v['bigram_rows_correlation']:+.3f} |")
ao = res["alphabet_order"]
md.append(f"\n## 2. Does the alphabet's order carry structure? (Grabar)\n\nCo-occurrence against closeness in the alphabet: Spearman {ao['spearman_neighbourliness']:+.3f}; under 2,000 random orders {ao['null_mean']:+.3f} ± {ao['null_sd']:.3f}; p = {ao['permutation_p']}.")
md.append(f"Same row of the stone (the decades) against different rows: mean co-occurrence share {ao['within_row_vs_across']['mean_cooccurrence_same_row']:.5f} against {ao['within_row_vs_across']['mean_cooccurrence_other_rows']:.5f}.")
md.append("\n## 3. What machines charge (tokens per word)\n\n| tokenizer | " + " | ".join(texts) + " |\n|---|" + "---:|" * len(texts))
for tn, r in res["tokens_per_word"].items(): md.append(f"| {tn} | " + " | ".join(f"{r[n]:.2f}" for n in texts) + " |")
open(os.path.join(HERE, "out", "insights.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
