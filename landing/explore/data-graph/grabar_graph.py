#!/usr/bin/env python3
"""The alphabet as a MEASURED graph: the 36 letters of Mashtots, linked by how often they touch in Classical Armenian (Grabar).

The Landing's graph acts run on three hand-made attention heads (sound, number, order: softmax over authored features). This script
builds the same objects from text instead, so every number can carry the grade **Measured**:

  corpus   UD Classical Armenian CAVaL (the Gospels and more, ~4,800 sentences), already on disk in the tokenizer-census folder;
           nothing is downloaded. Letters are upper-cased; the ligature և is ԵՒ; Օ and Ֆ (medieval additions) are counted and dropped.
  graph    P[i][j] = how often letter j follows letter i inside a word, row-normalised (the analogue of one attention row);
           Ws = (P + Pᵀ) / 2, the symmetric graph the deck's Fiedler cut and spectral acts use.
  maths    Fiedler vector (2nd-smallest eigenvector of L = D − W), the TOP eigenvector of L (the graph's highest "mode"),
           PageRank (d = 0.85, as in the deck), Sukhotin's 1962 vowel algorithm (finds vowels from co-occurrence alone).
  compare  with the deck's own numbers (scratch/landing.json: FIED, PR, A.mean) and its vowel flags (DATA[k][5]).
  bonus    the order in which a real BPE tokenizer (Mistral Nemo "Tekken", tokenizer.json on disk) merges Armenian letter pairs.

Run from the Landing folder:  python3 explore/data-graph/grabar_graph.py      -> explore/data-graph/out/{graph.json, graph.png, report.md}
"""
import json, os, re, glob, collections, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CENSUS = os.path.expanduser("~/Projects/x3d/work/armenian-tokenizer-census/data")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)

L = json.load(open(os.path.join(ROOT, "scratch/landing.json"), encoding="utf-8"))
DATA = L["DATA"]; LET = "".join(d[0] for d in DATA); N = 36; IDX = {c: i for i, c in enumerate(LET)}
DECK_VOWEL = np.array([d[5] for d in DATA], dtype=bool)

# ---------------------------------------------------------------- the corpus
def sentences(pattern):
    for fn in sorted(glob.glob(pattern)):
        for line in open(fn, encoding="utf-8"):
            if line.startswith("# text = "): yield line[9:].strip()
SENTS = list(sentences(os.path.join(CENSUS, "UD_Classical_Armenian-CAVaL", "*.conllu")))
def tokenize(sents, dropped=None):
    out = []
    for s in sents:
        for w in re.findall(r"[\u0531-\u0556\u0561-\u0587]+", s):
            w = w.upper().replace("և".upper(), "ԵՒ").replace("և", "ԵՒ")
            if dropped is not None:
                for ch in w:
                    if ch not in IDX: dropped[ch] += 1
            keep = "".join(ch for ch in w if ch in IDX)
            if keep: out.append(keep)
    return out
def bigrams(words):
    B = np.zeros((N, N))
    for w in words:
        for a, b in zip(w, w[1:]): B[IDX[a], IDX[b]] += 1
    return B
dropped = collections.Counter(); words = tokenize(SENTS, dropped)
freq = np.zeros(N)
for w in words:
    for ch in w: freq[IDX[ch]] += 1
B = bigrams(words)
n_letters, n_bigrams = int(freq.sum()), int(B.sum())

# ---------------------------------------------------------------- Sukhotin's algorithm (1962): vowels from co-occurrence alone
def sukhotin(B):
    C = B + B.T; np.fill_diagonal(C, 0); s = C.sum(1).astype(float); vow = np.zeros(N, bool); order = []
    while True:
        cand = np.where(~vow, s, -np.inf); i = int(np.argmax(cand))
        if cand[i] <= 0: break
        vow[i] = True; order.append(i); s -= 2 * C[:, i]
    return vow, order
SUK, SUK_ORDER = sukhotin(B)

# ---------------------------------------------------------------- the graph, spectral maths, PageRank (the deck's recipe on measured rows)
P = B / np.maximum(B.sum(1, keepdims=True), 1)
Ws = (P + P.T) / 2; np.fill_diagonal(Ws, 0)
deg = Ws.sum(1); Lap = np.diag(deg) - Ws
ev, V = np.linalg.eigh(Lap)
fied = V[:, 1] / np.abs(V[:, 1]).max(); top = V[:, -1] / np.abs(V[:, -1]).max()   # top of the PLAIN Laplacian: localised on the hub Ա (kept as a caution)
def sgn_agree(v, flags):                      # how well the sign of v separates `flags` (best of the two orientations)
    a = np.mean((v > 0) == flags); return max(a, 1 - a)
def fast_mode(B):
    """the graph's highest mode: the eigenvector of the MOST NEGATIVE eigenvalue of the normalised co-occurrence matrix D^-1/2 C D^-1/2
    (= the top of the normalised Laplacian; a perfectly alternating, bipartite graph has eigenvalue -1). Random-walk scaling, vowels > 0, max |v| = 1."""
    C = B + B.T; np.fill_diagonal(C, 0); d = np.maximum(C.sum(1), 1e-9)
    ev_, U = np.linalg.eigh(C / np.sqrt(np.outer(d, d))); v = U[:, 0] / np.sqrt(d)
    if np.mean((v > 0) == DECK_VOWEL) < 0.5: v = -v            # orientation only (the sign of an eigenvector is arbitrary); the split itself is measured
    return float(ev_[0]), v / np.abs(v).max()
LAM_FAST, FAST = fast_mode(B)
rng = np.random.default_rng(405); BOOT = 200; votes = np.zeros(N)       # bootstrap over sentences: how often each letter lands on the vowel side
for _ in range(BOOT): votes += fast_mode(bigrams(tokenize([SENTS[i] for i in rng.integers(0, len(SENTS), len(SENTS))])))[1] > 0
VOTE = votes / BOOT
def pagerank(M, d=0.85, it=60):
    r = np.full(N, 1 / N)
    for _ in range(it): r = (1 - d) / N + d * (r @ M)
    return r
PR = pagerank(P)

DECK_W = np.array(L["A"]["mean"]); DECK_FIED = np.array(L["FIED"]); DECK_PR = np.array(L["PR"][14])
def spearman(a, b):
    ra, rb = np.argsort(np.argsort(a)), np.argsort(np.argsort(b)); return float(np.corrcoef(ra, rb)[0, 1])
def upper(M): iu = np.triu_indices(N, 1); return M[iu]

# ---------------------------------------------------------------- the machine's spelling: Tekken's merges of two Armenian letters
def bpe_letter_merges(path):
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1)); cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    dec = {chr(c): b for b, c in zip(bs, cs)}
    out = []
    for rank, m in enumerate(json.load(open(path, encoding="utf-8"))["model"]["merges"]):
        a, b = m.split(" ") if isinstance(m, str) else m
        try: s = bytes(dec[ch] for ch in a + b).decode("utf-8")
        except (KeyError, UnicodeDecodeError): continue
        s = s.strip()
        if len(s) == 2 and all(ch.upper() in IDX for ch in s) and len(a) >= 2 and len(b) >= 2: out.append((rank, s))
    return out
tok_path = os.path.join(CENSUS, "tok-mistral-nemo", "tokenizer.json")
MERGES = bpe_letter_merges(tok_path) if os.path.exists(tok_path) else []

# ---------------------------------------------------------------- write
res = dict(
    grade="Measured", corpus="UD Classical Armenian CAVaL (train+dev+test, # text lines)", sentences=len(SENTS), words=len(words),
    letters=n_letters, bigrams=n_bigrams, dropped={k: v for k, v in dropped.most_common()},
    order=LET, freq=freq.astype(int).tolist(), bigram=B.astype(int).tolist(),
    sukhotin_vowels="".join(LET[i] for i in SUK_ORDER), deck_vowels="".join(LET[i] for i in range(N) if DECK_VOWEL[i]),
    sukhotin_agree_with_deck=float(np.mean(SUK == DECK_VOWEL)),
    lam2=float(ev[1]), lam_max=float(ev[-1]), fiedler=fied.round(4).tolist(), top_mode=top.round(4).tolist(), pagerank=PR.round(5).tolist(),
    fiedler_separates_vowels=float(sgn_agree(fied, DECK_VOWEL)), plain_top_mode_separates_vowels=float(sgn_agree(top, DECK_VOWEL)),
    fast_mode=FAST.round(4).tolist(), fast_mode_eigenvalue=LAM_FAST, fast_mode_vowels="".join(LET[i] for i in range(N) if FAST[i] > 0),
    fast_mode_agree_with_deck=float(np.mean((FAST > 0) == DECK_VOWEL)), bootstrap=dict(resamples=BOOT, vowel_side_frequency={LET[i]: round(float(VOTE[i]), 3) for i in range(N)}),
    deck=dict(grade="Authored (hand-made features through softmax)", lam2=L["lam2"], fiedler_separates_vowels=float(sgn_agree(DECK_FIED, DECK_VOWEL)),
              pagerank_top3="".join(LET[i] for i in np.argsort(-DECK_PR)[:3])),
    measured_pagerank_top5="".join(LET[i] for i in np.argsort(-PR)[:5]), freq_top5="".join(LET[i] for i in np.argsort(-freq)[:5]),
    spearman_pagerank_measured_vs_deck=spearman(PR, DECK_PR), spearman_pagerank_vs_frequency=spearman(PR, freq),
    corr_edges_measured_vs_deck=float(np.corrcoef(upper(Ws), upper((DECK_W + DECK_W.T) / 2))[0, 1]),
    tekken_first_letter_pairs=[dict(rank=r, pair=s) for r, s in MERGES[:20]], tekken_letter_pair_merges=len(MERGES),
)
json.dump(res, open(os.path.join(OUT, "graph.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- figure: the measured ring, the two cuts, PageRank against the deck's
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
fp = os.path.join(ROOT, "fonts/notoserifarmenian/NotoSerifArmenian[wdth,wght].ttf")
font_manager.fontManager.addfont(fp); plt.rcParams["font.family"] = [font_manager.FontProperties(fname=fp).get_name(), "DejaVu Sans"]
GOLD, TEAL, PAPER, GROUND = "#e1ad66", "#c9efe8", "#f3f2f2", "#1b1a1a"
fig = plt.figure(figsize=(16, 9), facecolor=GROUND)
def ring(ax, W, v, title, sub):
    ax.set_facecolor(GROUND); ax.set_aspect("equal"); ax.axis("off")
    ang = np.arange(N) / N * 2 * np.pi - np.pi / 2; xy = np.c_[np.cos(ang), np.sin(ang)]
    wmax = upper(W).max()
    for i in range(N):
        for j in range(i + 1, N):
            w = math.sqrt(W[i, j] / wmax)
            if w > 0.04: ax.plot(*xy[[i, j]].T, color=PAPER if np.sign(v[i]) != np.sign(v[j]) else GOLD, alpha=min(0.9, 0.05 + 0.8 * w * w), lw=0.4 + 1.6 * w)
    for i in range(N):
        ax.add_patch(plt.Circle(xy[i] * 1.12, 0.07, color=TEAL if v[i] > 0 else GOLD, alpha=0.9))
        ax.text(*(xy[i] * 1.12), LET[i], ha="center", va="center", fontsize=12, color=GROUND)
        if DECK_VOWEL[i]: ax.add_patch(plt.Circle(xy[i] * 1.12, 0.095, fill=False, ec=PAPER, lw=1.2))
    ax.set_title(title, color=PAPER, fontsize=14); ax.text(0, -1.42, sub, color=PAPER, alpha=0.7, ha="center", fontsize=10)
    ax.set_xlim(-1.35, 1.35); ax.set_ylim(-1.5, 1.3)
ring(fig.add_axes([0.0, 0.05, 0.33, 0.9]), (DECK_W + DECK_W.T) / 2, DECK_FIED, "the deck: authored attention, Fiedler cut",
     f"λ₂ = {L['lam2']:.3f} · sign separates the deck's vowels {sgn_agree(DECK_FIED, DECK_VOWEL):.0%}")
ring(fig.add_axes([0.33, 0.05, 0.33, 0.9]), Ws, FAST, "Grabar, measured: the graph's highest mode",
     f"eigenvalue {LAM_FAST:.3f} of D⁻¹ᐟ²CD⁻¹ᐟ² · sign = the deck's vowels on {np.mean((FAST > 0) == DECK_VOWEL):.0%} (Fiedler: {sgn_agree(fied, DECK_VOWEL):.0%})")
ax = fig.add_axes([0.71, 0.12, 0.27, 0.76]); ax.set_facecolor(GROUND)
o = np.argsort(-PR); y = np.arange(N)
ax.barh(y, PR[o] / PR.max(), color=GOLD, alpha=0.85, label="measured PageRank (Grabar bigrams)")
ax.barh(y, -DECK_PR[o] / DECK_PR.max(), color=TEAL, alpha=0.6, label="deck PageRank (authored heads)")
ax.set_yticks(y); ax.set_yticklabels([LET[i] for i in o], color=PAPER, fontsize=11); ax.invert_yaxis()
ax.tick_params(colors=PAPER); [s.set_color("#555") for s in ax.spines.values()]
ax.set_title(f"PageRank, Spearman ρ = {spearman(PR, DECK_PR):+.2f}", color=PAPER, fontsize=13); ax.legend(facecolor=GROUND, labelcolor=PAPER, fontsize=9, loc="lower right")
fig.text(0.5, 0.965, f"Measured · {len(SENTS):,} Grabar sentences · {n_letters:,} letters · Sukhotin's vowels: {res['sukhotin_vowels']}  (deck's: {res['deck_vowels']})",
         color=PAPER, ha="center", fontsize=12)
fig.savefig(os.path.join(OUT, "graph.png"), dpi=90, facecolor=GROUND)

# ---------------------------------------------------------------- report
rep = [f"# Measured letter graph (Grabar) vs the deck's authored graph\n",
       f"Corpus: {res['corpus']}: {len(SENTS):,} sentences, {len(words):,} words, {n_letters:,} letters, {n_bigrams:,} in-word bigrams. Dropped (not among the 36): "
       + (", ".join(f"{k} {v}" for k, v in dropped.most_common(6)) or "none (Օ and Ֆ never occur in this Grabar corpus)") + ".\n",
       f"| quantity | measured (Grabar) | deck (authored) |", "|---|---|---|",
       f"| λ₂ (Fiedler value) | {ev[1]:.3f} | {L['lam2']:.3f} |",
       f"| Fiedler sign vs vowel flags | {sgn_agree(fied, DECK_VOWEL):.0%} | {sgn_agree(DECK_FIED, DECK_VOWEL):.0%} |",
       f"| highest mode (normalised co-occurrence, eigenvalue {LAM_FAST:.3f}) sign vs vowel flags | {np.mean((FAST > 0) == DECK_VOWEL):.0%} | - |",
       f"| top mode of the plain Laplacian (localised on Ա: a caution, not a result) | {sgn_agree(top, DECK_VOWEL):.0%} | - |",
       f"| PageRank top 5 | {res['measured_pagerank_top5']} | {res['deck']['pagerank_top3']} (top 3) |",
       f"| Spearman PageRank measured vs deck | {res['spearman_pagerank_measured_vs_deck']:+.2f} | |",
       f"| Spearman PageRank vs letter frequency | {res['spearman_pagerank_vs_frequency']:+.2f} | |",
       f"| edge-weight correlation (630 pairs) | {res['corr_edges_measured_vs_deck']:+.2f} | |",
       f"\nSukhotin (1962) finds, in order: **{res['sukhotin_vowels']}**; the deck flags **{res['deck_vowels']}**; per-letter agreement {res['sukhotin_agree_with_deck']:.0%}.",
       f"\nHighest mode, vowel side: **{res['fast_mode_vowels']}**. Bootstrap ({BOOT} resamples of the sentences): " + ", ".join(f"{LET[i]} {VOTE[i]:.0%}" for i in range(N) if 0 < VOTE[i] < 1 or DECK_VOWEL[i]) + " (every other letter 0 %).",
       f"\nTekken (Mistral Nemo) merges {len(MERGES)} two-letter Armenian pairs; the first ten, with their merge rank: " + ", ".join(f"{s} ({r:,})" for r, s in MERGES[:10]) + "."]
open(os.path.join(OUT, "report.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
print("\n".join(rep))
