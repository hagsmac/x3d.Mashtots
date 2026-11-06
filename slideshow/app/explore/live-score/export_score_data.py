#!/usr/bin/env python3
"""Exports what the live score needs into score_data.json (read by score.js). Nothing here is new music: the tables are the v4/v5 score's.

  harmony   scratch/harmony.json (written by make_music.py: the one harmony table, real time of the approved timeline), re-expressed so that
            it can follow ANY timeline: an entry before the groove is anchored to (segment, act time) in a run or (segment, fraction) in a hold;
            the groove and the finale are anchored to the bar grid counted from the finale's first beat (bar 0).
  tables    the chord table CH, the keys, Pythagorean ratios on D, the stone's ladder, the act entries, the groove's gates: copied from make_music.py
            (keep in step if the score changes; check_tables() compares the chords against harmony.json).
  letters   the 36 flights (act start t0 and return r0), the act constants, the pace.
Run from anywhere:  python3 explore/live-score/export_score_data.py
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
L = json.load(open(os.path.join(ROOT, "scratch/landing.json"), encoding="utf-8"))
H = json.load(open(os.path.join(ROOT, "scratch/harmony.json"), encoding="utf-8"))
TLR = json.load(open(os.path.join(ROOT, "scratch/timeline_real.json"), encoding="utf-8"))
SEGS = TLR["segs"]; FIN0 = TLR["FIN0"]; BAR = TLR["bar"]; BEAT = BAR / 4

# ---- copied from make_music.py (v4 + v5) ----
PCR = {"D": 1.0, "Eb": 256/243, "E": 9/8, "F": 32/27, "F#": 81/64, "G": 4/3, "G#": 729/512, "A": 3/2, "Bb": 128/81, "B": 27/16, "C": 16/9, "C#": 243/128}
CH = {"Dm": dict(root="D", tones=("D", "F", "A"), pent=("D", "F", "G", "A", "C"), pad=("A3", "D4", "F4"), ext=("E",)),
      "Bb": dict(root="Bb", tones=("Bb", "D", "F"), pent=("Bb", "C", "D", "F", "G"), pad=("Bb3", "D4", "F4"), ext=("A",)),
      "F":  dict(root="F", tones=("F", "A", "C"), pent=("F", "G", "A", "C", "D"), pad=("A3", "C4", "F4"), ext=("E",)),
      "C":  dict(root="C", tones=("C", "E", "G"), pent=("C", "D", "E", "G", "A"), pad=("G3", "C4", "E4"), ext=("B",)),
      "D":  dict(root="D", tones=("D", "F#", "A"), pent=("D", "E", "F#", "A", "B"), pad=("A3", "D4", "F#4"), ext=("C#",)),
      "G":  dict(root="G", tones=("G", "B", "D"), pent=("G", "A", "B", "D", "E"), pad=("G3", "B3", "D4"), ext=("F#",)),
      "Am": dict(root="A", tones=("A", "C", "E"), pent=("A", "C", "D", "E", "G"), pad=("A3", "C4", "E4"), ext=("B",)),
      "Em": dict(root="E", tones=("E", "G", "B"), pent=("E", "G", "A", "B", "D"), pad=("G3", "B3", "E4"), ext=("F#",)),
      "Bm": dict(root="B", tones=("B", "D", "F#"), pent=("B", "D", "E", "F#", "A"), pad=("F#3", "B3", "D4"), ext=("C#",)),
      "A":  dict(root="A", tones=("A", "C#", "E"), pent=("A", "B", "C#", "E", "F#"), pad=("A3", "C#4", "E4"), ext=("G#",))}
KEYS = {"Dm": ("D", "E", "F", "G", "A", "Bb", "C"), "Am": ("A", "B", "C", "D", "E", "F", "G"), "Em": ("E", "F#", "G", "A", "B", "C", "D"),
        "Bm": ("B", "C#", "D", "E", "F#", "G", "A"), "DM": ("D", "E", "F#", "G", "A", "B", "C#"), "Dx": ("D", "E", "F#", "G", "A", "B", "C")}
LADDER = [1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2, 9/4]
LOOP = ["Dm", "Bb", "F", "C"]
ENTRY = {"space": ("TW2", 0), "web": ("TS2", 28), "msg": ("TB2", 19), "spectral": ("TSP", 11), "pagerank": ("TP", 25), "anneal": ("TA", 26),
         "descent": ("TD", 2), "walk": ("TD2", 35), "fourier": ("TF", 34), "poincare": ("TPC", 15), "svd": ("TSV", 29)}
GATES = dict(heart=[(-29, -25, 1.0)], hat8=[(-25, -1, 0.35, 0.6), (0, 2, 0.3), (2, 10, 0.6), (10, 18, 0.7)], hat16=[(-13, -1, 0.35, 0.5), (4, 9, 0.5), (10, 16, 0.7)],
             ohat=[(-15, -1, 0.5, 0.75), (2, 9, 0.8), (10, 18, 0.9)], half=[(-22, -17, 0.55, 0.8), (0, 2, 0.5)], floor=[(-17, -1, 0.6, 0.9), (2, 9, 0.95), (10, 16, 1.0), (16, 18, 0.7)],
             clap=[(-19, -1, 0.4, 0.65), (2, 9, 0.8), (10, 16, 0.9), (16, 18, 0.55)], bass=[(-17, -1, 0.5, 0.85), (2, 9, 1.0), (10, 18, 1.0)],
             dhol=[(-15, -1, 0.45, 0.7), (2, 9, 0.8), (10, 16, 0.95), (16, 18, 0.5)], arp8=[(-25, -19, 0.45, 0.6), (0, 2, 0.6), (16, 20, 0.55)],
             arp16=[(-19, -1, 0.5, 0.85), (2, 10, 0.9), (10, 16, 1.0)])
GROOVE_BARS = 29                                   # make_music: T_GROOVE = bar_t(-29); the build's gates live in bars -29 .. 0

def check_tables():
    for t0, t1, ch, pent in H: assert set(CH[ch]["pent"]) == set(pent), (ch, pent)

def anchor(t):
    """approved real time -> a position that survives re-timing: ('bar', b) from the groove on, else (segment, 'act', a) in a run, (segment, 'frac', u) in a hold"""
    if t >= FIN0 - GROOVE_BARS * BAR - 1e-6: return dict(kind="bar", bar=(t - FIN0) / BAR)
    for s in SEGS:
        if s["r0"] - 1e-9 <= t < s["r0"] + s["dur"] - 1e-9:
            if s["rate"] > 0: return dict(kind="act", seg=s["name"], act=s["a0"] + (t - s["r0"]) * s["rate"])
            return dict(kind="frac", seg=s["name"], frac=(t - s["r0"]) / s["dur"])
    return dict(kind="act", seg=SEGS[-1]["name"], act=SEGS[-1]["a1"])

check_tables()
FIRST_KEYS = ["Dm", "Dm", "Dm", "Am", "Am", "Em", "Em", "Bm", "Bm", "DM", "DM"]          # make_music's hb(): the stone, the helix, the tour's four rows, the sentence
def key_of(i, t0, ch):
    if i < len(FIRST_KEYS): return FIRST_KEYS[i]
    b = (t0 - FIN0) / BAR
    if 10 - 1e-6 <= b < 18 - 1e-6 and ch in ("D", "C", "G"): return "Dx"                     # the drop: D C G C in D Mixolydian
    return "DM" if ch in ("D", "A") else "Dm"
harm = [dict(at=anchor(t0), chord=ch, key=key_of(i, t0, ch)) for i, (t0, t1, ch, _) in enumerate(H)]
out = dict(
    about="score_data.json for explore/live-score: exported from scratch/harmony.json, scratch/landing.json and tables copied from make_music.py",
    act={k: L[k] for k in ("T1", "TL", "TT", "TC", "TW2", "TS2", "TB2", "TSP", "TP", "TA", "TD", "TD2", "TF", "TPC", "TSV", "TSV2", "TH", "T2", "T3", "CYCLE")},
    pace=L["S"], flight=L["flight"], flightR=L["flightR"], letters=[dict(t0=p["t0"], r0=p["r0"]) for p in L["P"]], chars="".join(d[0] for d in L["DATA"]),
    PCR=PCR, CH=CH, KEYS=KEYS, LADDER=LADDER, LOOP=LOOP, ENTRY=ENTRY, GATES=GATES, GROOVE_BARS=GROOVE_BARS, BPM=TLR["bpm"], BAR=BAR,
    harm=harm, n_harm=len(harm),
)
json.dump(out, open(os.path.join(HERE, "score_data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
kinds = {}
for h in harm: kinds[h["at"]["kind"]] = kinds.get(h["at"]["kind"], 0) + 1
print("wrote score_data.json:", len(harm), "harmony entries", kinds)
