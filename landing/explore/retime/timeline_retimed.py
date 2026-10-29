"""A re-timable version of timeline.py: the same segments, sized by a PRESET (presets.json), with smooth speed ramps.

timeline.py maps real time onto the deck's act time with one constant rate per segment. Here a segment may also
  * be sized in bars of the 128 BPM grid ("bars": 4 -> 7.5 s), in seconds ("sec"), or by a constant rate ("rate", as before),
  * carry a speed PROFILE: relative rates at fractions of its real duration, [[u, p], ...], linear in between, scaled so that the
    segment still covers exactly its act range. Act time is then piecewise QUADRATIC in real time (the rate itself is continuous),
    so a slow-motion moment eases in and out instead of jumping,
  * be SPLIT at an act time with a new hold in between (the "vowels" act inside the spectral cut),
  * FILL whatever is left of a target loop length ("fill": true on one segment, "total" on the preset).
Each profile piece becomes one GLSL segment: real start RB, act start SA, rate at start SRT, rate at end SRE.
    act(tr) = SA + tau * (SRT + 0.5 * (SRE - SRT) * tau / d),   tau = tr - RB,  d = segment length.
A hold is a segment whose two rates are 0. The preset "approved" reproduces timeline.py exactly (checked by check_timeline.py).
Select a preset with PRESET=name (default graph-expanded).
"""
import json, math, os

BPM = 128.0
BAR = 4 * 60.0 / BPM                       # 1.875 s
HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = json.load(open(os.path.join(HERE, "presets.json"), encoding="utf-8"))
PRESET = os.environ.get("PRESET", "graph-expanded")

# the approved timeline (timeline.py), as data: name, act start, act end (None for a hold), rate or hold length, section tag
def base(D, prayer_dur, numerals_dur, shira_dur, finale_bars):
    A = D
    return [("flight", 0, A["T1"], 1.0, "stone"), ("line", A["T1"], A["TL"], 1.0, None), ("lift", A["TL"], A["TT"], 1.0, "helix"),
            ("tour", A["TT"], A["TC"], 1.5, "tour"), ("write", A["TC"], A["TW2"], 1.15, "writing"),
            ("prayer", A["TW2"], None, prayer_dur, None), ("numerals", A["TW2"], None, numerals_dur, "numbers"), ("shirakatsi", A["TW2"], None, shira_dur, None),
            ("space", A["TW2"], A["TS2"], 1.3, "embedding"), ("web", A["TS2"], A["TB2"], 1.5, "graph"), ("msg", A["TB2"], A["TSP"], 1.7, None),
            ("spectral", A["TSP"], A["TP"], 1.8, None), ("pagerank", A["TP"], A["TA"], 1.9, None), ("anneal", A["TA"], A["TD"], 2.0, None),
            ("descent", A["TD"], A["TD2"], 2.0, None), ("walk", A["TD2"], A["TF"], 2.0, None), ("fourier", A["TF"], A["TPC"], 2.0, None),
            ("poincare", A["TPC"], A["TSV"], 2.0, None), ("svd", A["TSV"], A["TSV2"], 2.0, None), ("collapse", A["TSV2"], A["TH"], 1.5, None),
            ("finale", A["TH"], None, finale_bars * BAR, "pretraining"), ("line2", A["TH"], A["T2"], 1.0, None), ("return", A["T2"], A["T3"], 1.0, "return"),
            ("rest", A["T3"], A["CYCLE"], 1.0, None)]

def _pieces(name, a0, a1, dur, profile, section):
    """split a run of act range [a0, a1] over `dur` real seconds into linear-rate pieces following `profile`"""
    prof = profile or [[0.0, 1.0], [1.0, 1.0]]
    assert prof[0][0] == 0.0 and prof[-1][0] == 1.0, (name, prof)
    area = sum((u1 - u0) * (p0 + p1) / 2 for (u0, p0), (u1, p1) in zip(prof, prof[1:]))
    c = (a1 - a0) / (dur * area)                                          # scale: the pieces cover exactly the act range
    out, a = [], a0
    for k, ((u0, p0), (u1, p1)) in enumerate(zip(prof, prof[1:])):
        d = (u1 - u0) * dur
        if d <= 1e-9: continue
        r0, r1 = c * p0, c * p1; da = d * (r0 + r1) / 2
        out.append(dict(name=name, part=k, a0=a, a1=a + da, rate=r0, rate_end=r1, dur=d, section=section if k == 0 else None))
        a += da
    out[-1]["a1"] = a1
    return out

def _size(spec, a0, a1, default_rate):
    if "bars" in spec: return spec["bars"] * BAR
    if "sec" in spec: return spec["sec"]
    return (a1 - a0) / spec.get("rate", default_rate)

def build(D, prayer_dur, numerals_dur, shira_dur, finale_bars=20, preset=None):
    P = PRESETS[preset or PRESET]; ov = P.get("segments", {})
    segs, fill_at = [], None
    for name, a0, a1, x, section in base(D, prayer_dur, numerals_dur, shira_dur, finale_bars):
        o = ov.get(name, {})
        if a1 is None:                                                    # a hold
            dur = o["bars"] * BAR if "bars" in o else o.get("sec", x)
            segs.append(dict(name=name, part=0, a0=a0, a1=a0, rate=0.0, rate_end=0.0, dur=dur, section=section))
            continue
        if "split_at" in o:                                               # run, new hold, run (the hold sits at act time a0 + split_at)
            am = a0 + o["split_at"]; h = o["hold"]
            segs += _pieces(name, a0, am, _size(o["first"], a0, am, x), o["first"].get("profile"), section)
            segs.append(dict(name=h["name"], part=0, a0=am, a1=am, rate=0.0, rate_end=0.0, dur=h["bars"] * BAR if "bars" in h else h["sec"], section=h.get("section")))
            segs += _pieces(name + "2", am, a1, _size(o["second"], am, a1, x), o["second"].get("profile"), None)
            continue
        if o.get("fill"): fill_at = (len(segs), name, a0, a1, o.get("profile"), section)
        segs += _pieces(name, a0, a1, _size(o, a0, a1, x), o.get("profile"), section)
    if fill_at:                                                           # resize the fill segment so the loop is exactly `total` long
        i, name, a0, a1, prof, section = fill_at
        n_old = len(_pieces(name, a0, a1, 1.0, prof, section))
        rest = sum(s["dur"] for s in segs) - sum(s["dur"] for s in segs[i:i + n_old])
        segs[i:i + n_old] = _pieces(name, a0, a1, P["total"] - rest, prof, section)
    t = 0.0
    for s in segs: s["r0"] = t; t += s["dur"]
    return segs, t

def act_at(segs, tr):
    for s in segs:
        if tr < s["r0"] + s["dur"] or s is segs[-1]:
            tau = tr - s["r0"]; return s["a0"] + tau * (s["rate"] + 0.5 * (s["rate_end"] - s["rate"]) * tau / max(s["dur"], 1e-9))
    return 0.0

def real_of_act(segs, a, after_hold=False):
    """first real time at which act time reaches a (runs only)"""
    for s in segs:
        if (s["rate"] > 0 or s["rate_end"] > 0) and s["a0"] - 1e-9 <= a <= s["a1"] + 1e-9:
            r0, k, da = s["rate"], (s["rate_end"] - s["rate"]) / s["dur"], a - s["a0"]
            tau = da / r0 if abs(k) < 1e-12 else (-r0 + math.sqrt(max(0.0, r0 * r0 + 2 * k * da))) / k
            return s["r0"] + tau
    raise ValueError(a)

def hold_start(segs, name):
    """real start and total length of the (possibly multi-piece) segment `name`"""
    for i, s in enumerate(segs):
        if s["name"] == name:
            dur = 0.0
            for s2 in segs[i:]:
                if s2["name"] != name: break
                dur += s2["dur"]
            return s["r0"], dur
    raise KeyError(name)

def glsl_arrays(segs):
    n = len(segs)
    f = lambda xs: ", ".join(f"{x:.5f}" for x in xs)
    rb = [s["r0"] for s in segs] + [segs[-1]["r0"] + segs[-1]["dur"]]
    return n, f(rb), f([s["a0"] for s in segs]), f([s["rate"] for s in segs]), f([s["rate_end"] for s in segs])
