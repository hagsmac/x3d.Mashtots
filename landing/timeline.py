"""The real-time timeline of the Landing: how the deck's act time is stretched, compressed and paused.

The original JavaScript runs 193.31 s of act time (T1 ... CYCLE). Here real time is a piecewise map onto it:
  * the slow, astronomical opening plays at the deck's pace (rate 1),
  * the tour and the writing are a little quicker,
  * from the embedding space on, the graph mathematics accelerates act by act (rate 1.3 -> 2.0): the modern, machine half,
  * HOLDs freeze act time while new acts play (the Lord's Prayer, the numerals, Shirakatsi, the pre-training finale), with real-time windows of their own.
Every shader gets  T_ = real time  (rotations, shimmer; continuous)  and  t_ = warp(T_)  (act time; all the deck's windows and flights).
"""
import math

BPM = 128.0
BAR = 4 * 60.0 / BPM                       # 1.875 s

def build(D, prayer_dur, numerals_dur, shira_dur, finale_bars=20):
    A = {k: D[k] for k in ("T1", "TL", "TT", "TC", "TW2", "TS2", "TB2", "TSP", "TP", "TA", "TD", "TD2", "TF", "TPC", "TSV", "TSV2", "TH", "T2", "T3", "CYCLE")}
    segs = []
    def run(name, a0, a1, rate, section=None): segs.append(dict(name=name, a0=a0, a1=a1, rate=rate, dur=(a1 - a0) / rate, section=section))
    def hold(name, at, dur, section=None): segs.append(dict(name=name, a0=at, a1=at, rate=0.0, dur=dur, section=section))
    run("flight", 0, A["T1"], 1.0, "stone")
    run("line", A["T1"], A["TL"], 1.0)
    run("lift", A["TL"], A["TT"], 1.0, "helix")
    run("tour", A["TT"], A["TC"], 1.5, "tour")
    run("write", A["TC"], A["TW2"], 1.15, "writing")
    hold("prayer", A["TW2"], prayer_dur)
    hold("numerals", A["TW2"], numerals_dur, "numbers")
    hold("shirakatsi", A["TW2"], shira_dur)
    run("space", A["TW2"], A["TS2"], 1.3, "embedding")
    for name, a0, a1, r, sec in (("web", "TS2", "TB2", 1.5, "graph"), ("msg", "TB2", "TSP", 1.7, None), ("spectral", "TSP", "TP", 1.8, None), ("pagerank", "TP", "TA", 1.9, None),
                                 ("anneal", "TA", "TD", 2.0, None), ("descent", "TD", "TD2", 2.0, None), ("walk", "TD2", "TF", 2.0, None), ("fourier", "TF", "TPC", 2.0, None),
                                 ("poincare", "TPC", "TSV", 2.0, None), ("svd", "TSV", "TSV2", 2.0, None)):
        run(name, A[a0], A[a1], r, sec)
    run("collapse", A["TSV2"], A["TH"], 1.5)
    hold("finale", A["TH"], finale_bars * BAR, "pretraining")
    run("line2", A["TH"], A["T2"], 1.0)
    run("return", A["T2"], A["T3"], 1.0, "return")
    run("rest", A["T3"], A["CYCLE"], 1.0)
    t = 0.0
    for s in segs: s["r0"] = t; t += s["dur"]
    return segs, t

def real_of_act(segs, a, after_hold=False):
    """first real time at which act time reaches a (runs only); used to place the score's act-time events"""
    for s in segs:
        if s["rate"] > 0 and s["a0"] - 1e-9 <= a <= s["a1"] + 1e-9:
            return s["r0"] + (a - s["a0"]) / s["rate"]
    raise ValueError(a)

def hold_start(segs, name):
    for s in segs:
        if s["name"] == name: return s["r0"], s["dur"]
    raise KeyError(name)

def glsl_arrays(segs):
    n = len(segs)
    f = lambda xs: ", ".join(f"{x:.5f}" for x in xs)
    rb = [s["r0"] for s in segs] + [segs[-1]["r0"] + segs[-1]["dur"]]
    return n, f(rb), f([s["a0"] for s in segs]), f([s["rate"] for s in segs])
