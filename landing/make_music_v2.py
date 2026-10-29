#!/usr/bin/env python3
"""The score of the Landing, synthesised offline and locked to its real-time loop (204.25 s; see timeline.py).

Two halves, one language.
  The slow half (stone, helix, tour, the sentence of 405, the Lord's Prayer, the numerals, Shirakatsi's table):
    * Pythagorean tuning (3-limit): every pitch is a product of 3:2 fifths folded into the octave, rooted on D (the dam, the duduk's drone).
    * A letter's pitch is its place on the 4 x 9 stone: its column (the numeral digit 1..9) is a step of the natural-minor ladder
      1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2, 9/4; its row (units, tens, hundreds, thousands) is a key a fifth higher each time.
    * The stone is a plate: a letter is the Chladni mode (n, m) = (column + 1, row + 1); its quiet glassy overtones are the neighbouring modes,
      f ~ sqrt(n^2 + m^2), snapped to the nearest Pythagorean ratio. (An authored mapping, not a property of Armenian.)
    * Numbers sound as chords: the letters of 405 = NE, 1512, 2026 and 1475 are struck together. The multiplication table is played as ladder runs.
  The modern half (the alphabet as a graph, then pre-training in Armenian): a groove at 128 BPM that builds act by act on a beat grid pinned to the finale.
    * Kick, hats, clap, bass, a Markov arpeggio (the letters walk the attention graph; each hop is a note, snapped to the chord) played on the kanun,
      supersaw pads and stabs, risers, a drop. The six letters of Mashtots (M A SH T O TS) are the hook: F# D B E C G, which is D Mixolydian.
    * The key brightens from minor (the ancient half, the build) to Mixolydian at the drop.
  Armenian-inflected modal writing; not a transcription of any sharakan.
Run: python3 make_music.py  ->  landing_score.mp3 (and .wav); the X3D page keeps it in step with the clock."""
import json, math, subprocess, sys, wave
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt

SR = 44100
D = json.load(open("scratch/landing.json", encoding="utf-8"))
TL = json.load(open("scratch/timeline_real.json", encoding="utf-8"))
SEGS, CYC, BPM = TL["segs"], TL["cycle"], TL["bpm"]
BEAT = 60.0 / BPM; BAR = 4 * BEAT; S16 = BEAT / 4
N = 36
TAIL = 7.0
NS = int((CYC + TAIL) * SR)
F32 = np.float32
Z = lambda: np.zeros(NS, dtype=F32)
LN, RN, WLN, WRN = Z(), Z(), Z(), Z()                          # normal bus: dry L/R and the reverb send
LD_, RD_, WLD, WRD = Z(), Z(), Z(), Z()                        # ducked bus (side-chained to the kick)
KICKS = []                                                     # kick times for the side-chain
rng = np.random.default_rng(405)

def seg(name): return next(s for s in SEGS if s["name"] == name)
def ra(name, a):
    """real time of act time `a` inside the segment `name`"""
    s = seg(name); return s["r0"] + (a - s["a0"]) / s["rate"]
def rstart(name): return seg(name)["r0"]
def rdur(name): return seg(name)["dur"]
T_ = {k: D[k] for k in ("T1", "TL", "TT", "TC", "TW2", "TS2", "TB2", "TSP", "TP", "TA", "TD", "TD2", "TF", "TPC", "TSV", "TSV2", "TH", "T2", "T3")}
begin, stagger, flight, S_, P = D["begin"], D["stagger"], D["flight"], D["S"], D["P"]
FIN0, FIN1, PRA0, PRA1, NUM0, NUM1, SHI0, SHI1, COL0, COL1 = (TL[k] for k in ("FIN0", "FIN1", "PRA0", "PRA1", "NUM0", "NUM1", "SHI0", "SHI1", "COL0", "COL1"))
LET = "".join(d[0] for d in D["DATA"])

# ------------------------------------------------------------------ tuning
D4 = 293.665
LADDER = [1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2, 9/4]
def fold(x):
    while x >= 2: x /= 2
    while x < 1: x *= 2
    return x
def letter_ratio(i): return LADDER[i % 9] * fold(1.5 ** (i // 9))
def letter_freq(i, octave=0): return D4 * letter_ratio(i) * 2.0 ** (octave + (-1 if i // 9 == 0 else 0))
PYTH = sorted({fold(1.5 ** k) * 2.0 ** j for k in range(-6, 8) for j in range(0, 2)})
def snap(r): return min(PYTH, key=lambda p: abs(math.log(p / r)))
def plate_overtones(i):
    n, m = i % 9 + 1, i // 9 + 1; base = math.sqrt(n * n + m * m)
    return [snap(math.sqrt((n + a) ** 2 + (m + b) ** 2) / base) for a, b in ((1, 0), (0, 1), (1, 1))]
def cents(f): return 1200 * math.log2(f / D4)

# ------------------------------------------------------------------ DSP helpers
def add(buf, x, t0):
    i0 = int(round(t0 * SR))
    if i0 >= len(buf) or i0 + len(x) <= 0: return
    a, b = max(0, -i0), min(len(x), len(buf) - i0)
    buf[i0 + a:i0 + b] += x[a:b].astype(F32)
def put(x, t0, pan=0.0, wet=0.25, gain=1.0, duck=False):
    th = (pan + 1) * math.pi / 4; gl, gr = math.cos(th) * gain, math.sin(th) * gain
    L, R, WL, WR = (LD_, RD_, WLD, WRD) if duck else (LN, RN, WLN, WRN)
    add(L, x * gl * (1 - wet * 0.5), t0); add(R, x * gr * (1 - wet * 0.5), t0)
    add(WL, x * gl * wet, t0); add(WR, x * gr * wet, t0)
def lp(x, fc, order=2):
    sos = butter(order, min(fc, SR * 0.45) / (SR / 2), btype="low", output="sos"); return sosfilt(sos, x)
def hp(x, fc, order=2):
    sos = butter(order, fc / (SR / 2), btype="high", output="sos"); return sosfilt(sos, x)
def bp(x, lo, hi):
    sos = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos"); return sosfilt(sos, x)
def smooth_noise(n, hz):
    k = int(n / SR * hz) + 3; pts = rng.normal(size=k); xs = np.linspace(0, k - 1, n); return np.interp(xs, np.arange(k), pts)

def duduk(f0, dur, f_from=None, vib=1.0, grace=False, amp=1.0, legato=False, rel=0.35):
    n = int((dur + rel) * SR); t = np.arange(n) / SR
    cents_ = np.zeros(n)
    if f_from: cents_ += np.where(t < 0.10, 1200 * math.log2(f_from / f0) * (1 - t / 0.10) ** 2, 0.0)
    if grace: cents_ += np.where(t < 0.15, -200 * (1 - t / 0.15), 0.0)
    depth = 7.0 * vib * (1 - np.exp(-t / 0.7)); cents_ += depth * np.sin(2 * math.pi * 5.3 * t + rng.uniform(0, 6.28)) + 2.5 * smooth_noise(n, 1.7)
    f = f0 * 2.0 ** (cents_ / 1200.0); ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.zeros(n)
    for h in range(1, 19):
        fh = f0 * h
        if fh > 7500: break
        a = (1.0 / h ** 0.85) * (1.0 + 0.55 * (h % 2 == 1)) * (0.30 + math.exp(-(math.log(fh / 1100.0)) ** 2 / (2 * 0.75 ** 2))) / (1 + (fh / 4300.0) ** 4)
        y += a * np.sin(h * ph)
    y /= 4.0
    att = 0.10 if legato else 0.20
    env = np.minimum(1.0, t / att) ** 1.5 * np.where(t < dur, 1.0, np.exp(-(t - dur) / (rel / 4.5)))
    env *= 0.92 + 0.08 * np.sin(2 * math.pi * 0.35 * t)
    breath = bp(rng.normal(size=n), 900, 2400) * 0.05 * np.minimum(1, t / 0.12) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.1))
    return amp * (y + breath) * env
def drone(f, dur, amp=1.0, fade=3.0, det=0.6):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for dtn in (-det, det):
        ph = 2 * math.pi * f * 2.0 ** (dtn / 1200) * t
        for h in range(1, 11): y += np.sin(h * ph + h) / h ** 1.25
    y = lp(y, 900) * 0.22
    env = np.minimum(1.0, t / fade) * np.minimum(1.0, (dur - t) / fade) * (0.85 + 0.15 * np.sin(2 * math.pi * 0.11 * t + 1))
    return amp * y * env
def kanun(f, amp=1.0, dur=2.6, bright=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n); B = 0.0003
    for h in range(1, 13):
        fh = f * h * math.sqrt(1 + B * h * h)
        if fh > 9000: break
        y += (1.0 / h ** (1.15 / bright)) * np.exp(-t / (1.7 / h ** 0.72)) * np.sin(2 * math.pi * fh * t + 0.4 * h)
    click = bp(rng.normal(size=n), 2500, 7000) * np.exp(-t / 0.012) * 0.25
    y = (y + click) * np.minimum(1.0, t / 0.004)
    return amp * y * 0.5
def glass(f, i, amp=1.0, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.sin(2 * math.pi * f * t) * np.exp(-t / 0.9)
    for k, r in enumerate(plate_overtones(i)): y += (0.35 / (k + 1)) * np.sin(2 * math.pi * f * r * t + k) * np.exp(-t / (0.6 + 0.2 * k))
    return amp * y * np.minimum(1.0, t / 0.01) * 0.4
def pad(freqs, dur, amp=1.0, fade=2.5, wave="tri"):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for f in freqs:
        for dtn in (-3, 3):
            ph = 2 * math.pi * f * 2.0 ** (dtn / 1200) * t
            y += (np.arcsin(np.sin(ph)) * 2 / math.pi) if wave == "tri" else np.sin(ph)
    y = lp(y, 1800) / max(1, len(freqs)) * 0.5
    return amp * y * np.minimum(1.0, t / fade) * np.minimum(1.0, (dur - t) / fade)
def wavetable_tone(f, dur, amps, phases, amp=1.0, fade=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for h, (a, p) in enumerate(zip(amps, phases), start=1):
        if f * h > 9000: break
        y += a * np.sin(2 * math.pi * f * h * t + p)
    return amp * y * np.minimum(1.0, t / fade) * np.minimum(1.0, (dur - t) / fade)
def supersaw(f, dur, amp=1.0, cutoff=2600.0, att=0.02, rel=0.25):
    n = int((dur + rel) * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for dt_ in (-24, -14, -6, 0, 6, 14, 24):
        ph = (f * 2.0 ** (dt_ / 1200.0) * t + rng.random()) % 1.0
        y += 2 * ph - 1
    y = lp(y / 7.0, cutoff)
    env = np.minimum(1.0, t / att) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (rel / 4)))
    return amp * y * env

pluck_letter_calls = 0
def pluck_letter(i, t0, amp=0.08, soft=False, octave=0, glass_amp=0.35, duck=False):
    f = letter_freq(i, octave); pan = (i % 9 - 4) / 5.5
    put(kanun(f, amp * (0.35 if soft else 1.0), dur=0.9 if soft else 2.6), t0, pan=pan, wet=0.3, duck=duck)
    if not soft and glass_amp > 0: put(glass(f * 2, i, amp * glass_amp), t0, pan=-pan, wet=0.5, duck=duck)

# ---- drums
def _kick():
    n = int(0.42 * SR); t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.028); ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.16) + 0.35 * np.sin(2 * ph) * np.exp(-t / 0.05)
    y += bp(rng.normal(size=n), 1500, 6000) * np.exp(-t / 0.006) * 0.25
    return y * np.minimum(1.0, t / 0.0015)
def _clap():
    n = int(0.28 * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for k, d_ in enumerate((0.0, 0.011, 0.022)): y += np.where(t >= d_, np.exp(-(t - d_) / 0.012), 0.0) * rng.normal(size=n)
    y = bp(y, 900, 6500) + 0.7 * np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.07), 0.0) * bp(rng.normal(size=n), 1200, 5500)
    return y * 0.5
def _hat(open_=False):
    n = int((0.16 if open_ else 0.05) * SR); t = np.arange(n) / SR
    return hp(rng.normal(size=n), 7000) * np.exp(-t / (0.07 if open_ else 0.018)) * 0.35
def _dum():
    n = int(0.34 * SR); t = np.arange(n) / SR
    f = 74 + 40 * np.exp(-t / 0.05); ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.13) + 0.25 * bp(rng.normal(size=n), 200, 900) * np.exp(-t / 0.03)
    return y * np.minimum(1.0, t / 0.002)
def _tek():
    n = int(0.14 * SR); t = np.arange(n) / SR
    y = bp(rng.normal(size=n), 1800, 5200) * np.exp(-t / 0.02) + 0.5 * np.sin(2 * math.pi * 410 * t) * np.exp(-t / 0.035)
    return y * 0.55
KICK, CLAP, HAT, OHAT = _kick(), _clap(), _hat(), _hat(True)
DUM, TEK = _dum(), _tek()
def bassnote(f, dur, amp=1.0):
    n = int((dur + 0.08) * SR); t = np.arange(n) / SR
    y = np.sin(2 * math.pi * f * t) + 0.45 * np.sin(4 * math.pi * f * t) + 0.18 * np.sin(6 * math.pi * f * t)
    saw = lp(2 * ((f * t) % 1.0) - 1, 420) * 0.35
    env = np.minimum(1.0, t / 0.006) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.02))
    return amp * (y + saw) * env * 0.5
def riser(dur, amp=1.0, f0=300.0, f1=9000.0):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    noise = rng.normal(size=n); out = np.zeros(n)
    nb = 24
    for k in range(nb):                                         # a moving band: sample-wise crossfade between fixed bands
        c = f0 * (f1 / f0) ** (k / (nb - 1)); w = np.exp(-((u * (nb - 1) - k) ** 2) / 0.8)
        out += bp(noise, c * 0.8, min(c * 1.25, 20000)) * w
    return amp * out * (u ** 2) * 0.35
def snare_roll(dur, amp=1.0):
    n = int(dur * SR); y = np.zeros(n); t = 0.0; k = 0
    while t < dur:
        hit = bp(rng.normal(size=int(0.1 * SR)), 1500, 8000) * np.exp(-np.arange(int(0.1 * SR)) / SR / 0.025)
        a = int(t * SR); y[a:a + len(hit)] += hit[:max(0, n - a)] * (0.3 + 0.7 * (t / dur)) ; k += 1
        t += S16 * (1.0 if t < dur * 0.5 else 0.5 if t < dur * 0.8 else 0.25)
    return amp * y
def impact(dur=2.4, amp=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 55 * np.exp(-t / 0.9) + 28; ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.8) + lp(rng.normal(size=n), 900) * np.exp(-t / 0.5) * 0.5
    return amp * y * 0.8

# ------------------------------------------------------------------ the slow half
# ---- the dam: a drone on D, and the chord pads over it
for f_, a_ in ((D4 / 4, 0.40), (D4 / 2, 0.30), (D4 / 2 * 1.5, 0.16)): put(drone(f_, CYC + 2.0, a_), 0.0, pan=0.0, wet=0.2)
CHORDS = {"i": (1, 32/27, 3/2), "VII": (16/9 / 2, 81/64 * 16/9 / 2, 3/2 * 16/9 / 2), "v": (3/2 / 2, 3/2 / 2 * 32/27, 3/2 / 2 * 3/2), "iv": (4/3 / 2, 4/3 / 2 * 32/27, 4/3 / 2 * 3/2), "VI": (128/81 / 2, 128/81 / 2 * 81/64, 128/81 / 2 * 3/2)}
NEXT = {"i": ["VII", "iv", "v", "VI"], "VII": ["i", "VI"], "v": ["i", "iv"], "iv": ["i", "VII"], "VI": ["VII", "i"]}
t = 5.5; ch = "i"; crng = np.random.default_rng(11)
while t < CYC - 8:
    dur = 11 + crng.random() * 5
    if not (FIN0 - 6 <= t <= FIN1):                                 # the groove brings its own harmony in the finale
        fr = [D4 * r * 2 for r in CHORDS[ch]]
        put(pad(fr + [fr[0] / 2], dur + 5, 0.075, fade=3.5), t, pan=0.0, wet=0.35)
    ch = NEXT[ch][int(crng.integers(len(NEXT[ch])))]; t += dur

# ---- the stone wakes: a glassy ascending cascade as the letters leave, a quiet kanun arpeggio as they land
for i in range(N):
    t0 = P[i]["t0"]
    put(glass(letter_freq(i, 1), i, 0.07, 1.2), t0, pan=(i % 9 - 4) / 6, wet=0.5)
    pluck_letter(i, t0 + flight, amp=0.05, glass_amp=0.2)

# ---- the duduk improvises in D (seeded; the deck's phrasing rules, Pythagorean pitches), until the finale; softly again after it
POOL = [0, 2, 3, 5, 7, 8, 10, 12]; PR_ = [1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2]
drng = np.random.default_rng(405); deg = 2; prevf = None
def phrase():
    global deg
    ln = 3 + int(drng.integers(0, 4)); notes = []
    for k in range(ln):
        r = drng.random(); step = -1 if r < .3 else 1 if r < .6 else -2 if r < .72 else 2 if r < .84 else 0 if r < .92 else (-3 if drng.random() < .5 else 3)
        deg = max(0, min(7, deg + step)); last = k == ln - 1
        if last and drng.random() < .7: deg = [0, 4, 2, 7][int(drng.integers(0, 4))]
        notes.append((PR_[deg], 2.4 + drng.random() * 1.8 if last else [.7, .9, 1.2, 1.6, 2.2][int(drng.integers(0, 5))], drng.random() < .35, last))
    return notes
def quiet(tt):
    if rstart("tour") <= tt < rstart("write"): return 0.55
    if PRA0 <= tt < SHI1: return 0.5
    if rstart("fourier") <= tt < rstart("poincare"): return 0.55
    if rstart("web") <= tt < FIN0: return 0.7
    return 1.0
t = 6.6
while t < CYC - 9:
    if FIN0 - 1.0 <= t < FIN1: t = FIN1 + 0.2; prevf = None; continue
    for ratio, dur, grace, last in phrase():
        if t > CYC - 9 or FIN0 - 1.0 <= t < FIN1: break
        f = D4 * ratio
        put(duduk(f, dur, f_from=prevf, grace=grace, amp=0.34 * quiet(t) * (0.8 if t > FIN1 else 1.0), legato=prevf is not None, vib=1.0), t, pan=0.12, wet=0.32)
        prevf = f; t += dur
    t += 1.4 + drng.random() * 2.6; prevf = None

# ---- the tour: a plucked note per spotlit letter, the stone's glass partials beside it
for k in range(N): pluck_letter(k, ra("tour", T_["TT"] + k * S_), amp=0.10)
# ---- the writing of the sentence: each glyph sounds softly as it leaves its source letter
for q, sl in enumerate(D["slots"]):
    if sl["src"] >= 0: pluck_letter(sl["src"], ra("write", T_["TC"] + 1 + q * D["GDT"]), amp=0.12, soft=True)
# ---- the Lord's Prayer (Grabar): a Dm pad under it, a soft pluck on a third of the glyphs, an Amen of D major at the end
pr = json.load(open("scratch/prayer.json", encoding="utf-8")); prng = np.random.default_rng(6)
put(pad([D4 / 2, D4 * 1.5 / 2, D4 * 32 / 27], PRA1 - PRA0 + 2, 0.10, fade=3.0), PRA0, wet=0.45)
for k, sl in enumerate(pr["slots"]):
    if sl["src"] >= 0 and prng.random() < 0.33: pluck_letter(sl["src"], PRA0 + 1 + k * pr["GDT"], amp=0.12, soft=True)
t_amen = PRA0 + 1 + len(pr["slots"]) * pr["GDT"] + 0.6
put(pad([D4 / 2, D4 * 81 / 64 / 2, D4 * 1.5 / 2, D4], 5.5, 0.12, fade=1.5), t_amen, wet=0.5)
put(duduk(D4, 4.2, amp=0.30, vib=0.8, rel=1.0), t_amen, pan=0.1, wet=0.4)
# ---- letters are numbers: the ladder run as the matrix forms; each equation is struck as a chord of its own letters
for i in range(N): pluck_letter(i, NUM0 + 0.7 + i * 0.035, amp=0.10, soft=True)
def to_arm(n):
    out = ""
    for pw in (3, 2, 1, 0):
        dgt = (n // 10 ** pw) % 10
        if dgt: out += LET[pw * 9 + dgt - 1]
    return out
for k, n in enumerate(TL["EQS"]):
    idx = [LET.index(c) for c in to_arm(n)]
    for j, i in enumerate(idx): pluck_letter(i, TL["EQ_T"][k] + 0.12 * j, amp=0.12, glass_amp=0.5)
    put(pad([letter_freq(i, 0) for i in idx], 1.9, 0.11, fade=0.4), TL["EQ_T"][k], wet=0.45)
# ---- Shirakatsi's table: row by row, the products as steps of the ladder (digital roots)
for r in range(1, 10):
    for c in range(1, 10):
        tt = SHI0 + 0.9 + (r * 10 + c) * 0.045
        step = (r * c - 1) % 9
        put(kanun(D4 * LADDER[step] * (0.5 if r < 5 else 1.0), 0.04, dur=0.8), tt, pan=(c - 5) / 6, wet=0.35)
for r in range(1, 10): put(glass(D4 * LADDER[(r * r - 1) % 9], r, 0.06, 0.9), SHI0 + 0.9 + (r * 10 + r) * 0.045, pan=0.0, wet=0.5)   # the squares ring a little

# ---- act entries (the letter that sounds each act in, as in the deck) and the embedding space
ENTRY = {"space": ("TW2", 0), "write": ("TC", 18), "web": ("TS2", 28), "msg": ("TB2", 19), "spectral": ("TSP", 11), "pagerank": ("TP", 25), "anneal": ("TA", 26),
         "descent": ("TD", 2), "walk": ("TD2", 35), "fourier": ("TF", 34), "poincare": ("TPC", 15), "svd": ("TSV", 29)}
for segn, (key, i) in ENTRY.items(): pluck_letter(i, ra(segn, T_[key]) + 0.02, amp=0.12, octave=-1 if segn == "space" else 0)
pluck_letter(15, PRA0 + 0.02, amp=0.12); pluck_letter(14, NUM0 + 0.02, amp=0.12)
for q in range(int(T_["TW2"] * 1.5), int(T_["TS2"] * 1.5)):
    tt = ra("space", q / 1.5)
    if rstart("space") <= tt < rstart("web"): put(glass(letter_freq(q % 36, 1), q % 36, 0.035, 0.7), tt, pan=0.5, wet=0.5)

# ---- the graph acts, on the compressed clock
prng2 = np.random.default_rng(4050)
for q in range(0, 120):
    tt = rstart("web") + 0.5 + q * (rstart("spectral") - rstart("web") - 0.8) / 120
    i = int(prng2.integers(0, N)); put(glass(letter_freq(i, 1), i, 0.03, 0.5), tt, pan=float(prng2.uniform(-.8, .8)), wet=0.55)
MSG = D["MSG"]
for l in range(6):
    top = sorted(range(N), key=lambda i: -MSG[l][i])[:3]
    for i in top: pluck_letter(i, ra("msg", T_["TB2"] + 1.5 * l) + 0.05, amp=0.07 * (0.5 + MSG[l][i]), glass_amp=0.5)
FI = D["FIED"]; pos = sorted(range(N), key=lambda i: -FI[i])[:3]; neg = sorted(range(N), key=lambda i: FI[i])[:3]
dsp = rdur("spectral")
put(pad([letter_freq(i, 1) for i in pos], dsp + 1.0, 0.10, fade=1.0), rstart("spectral") - 0.3, pan=0.45, wet=0.4)
put(pad([letter_freq(i, 0) for i in neg], dsp + 1.0, 0.10, fade=1.0), rstart("spectral") - 0.3, pan=-0.45, wet=0.4)
PRL = D["PR"]; top3 = [i for _, i in D["PRtop"]]
for k in range(15):
    for i in top3: pluck_letter(i, ra("pagerank", T_["TP"] + 6.0 / 14 * k), amp=0.025 + 0.07 * k / 14, glass_amp=0.3)
put(pad([letter_freq(i, 0) for i in top3], rdur("pagerank") + 0.5, 0.10, fade=2.0), rstart("pagerank") - 0.2, wet=0.4)
def cluster(f, t0, dur, spread_fn, amp):
    n = int(dur * SR); tt = np.arange(n) / SR; y = np.zeros(n); sp = spread_fn(tt)
    for k in range(7):
        c = (k - 3) / 3.0; ph = 2 * math.pi * np.cumsum(f * 2.0 ** (c * sp / 1200)) / SR
        y += np.arcsin(np.sin(ph)) * 2 / math.pi
    y = lp(y, 2200) / 7 * amp * np.minimum(1.0, tt / 1.0) * np.minimum(1.0, (dur - tt) / 1.0)
    put(y, t0, pan=0.0, wet=0.4)
dan = rdur("anneal")
for f_ in (D4, D4 * 1.5, D4 * 2): cluster(f_, rstart("anneal"), dan, lambda tt: 3 + 55 * (0.5 - 0.5 * np.cos(6.2831853 * tt / dan)), 0.13)
GD = D["GD"]; lossv = [w[0] ** 2 + 3 * w[1] ** 2 + .6 * w[0] * w[1] for w in GD]
dd = rdur("descent"); tt = np.arange(int(dd * SR)) / SR; u = np.clip(tt / (6.5 / 2.0), 0, 1) * 47
lo = np.interp(u, np.arange(48), lossv); fd = D4 * 2.0 ** (0.45 * np.sqrt(np.maximum(lo, 0)))
ph = 2 * np.cumsum(np.pi * fd) / SR
tone = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.18 * np.sin(3 * ph)) * np.minimum(1, tt / 0.2) * np.minimum(1, (dd - tt) / 0.5)
put(lp(tone, 2500) * 0.075, rstart("descent"), pan=-0.2, wet=0.35)
Wm = D["A"]["mean"]
import random
wrng = random.Random(35); seqs = []
for i in range(N):
    sq = [i]
    for h in range(16):
        r = wrng.random(); n_ = sq[-1]; acc = 0.0; m = 0
        for m in range(N):
            acc += Wm[n_][m]
            if r <= acc: break
        sq.append(min(N - 1, m))
    seqs.append(sq)
for vi, w_ in enumerate((3, 14, 29)):
    for k in range(16): pluck_letter(seqs[w_][k], ra("walk", T_["TD2"] + k / 1.7) + 0.04 * vi, amp=0.085, glass_amp=0.15, octave=vi - 1 if vi != 1 else 0)
val = np.array([PRL[14][i] / D["PRmax"] for i in range(N)]); val = np.interp(np.linspace(0, N, 720, endpoint=False), np.arange(N + 1), np.append(val, val[0]))
sp_ = np.fft.rfft(val - val.mean()) / len(val); mags = np.abs(sp_[1:20]); phs = np.angle(sp_[1:20]); mags = mags / mags.max()
for q in range(17):
    K = 3 + q; ts = ra("fourier", T_["TF"] + q * 7.2 / 17)
    amps = np.where(np.arange(19) < K, mags * (np.arange(1, 20) ** -0.3), 0.0)
    put(wavetable_tone(D4 / 2, 7.2 / 17 / 2.0 + 0.5, amps / 3.0, phs, amp=0.17, fade=0.2), ts, pan=0.0, wet=0.4)
for i in range(0, N, 2): put(glass(letter_freq(i, 1), i, 0.05, 3.2), rstart("poincare") + 0.3 + 0.03 * i, pan=(i % 9 - 4) / 5, wet=0.6)
KM = D["KM"]
def cluster_pitch(it, k):
    mem = [i for i in range(N) if KM[it]["assign"][i] == k]
    return D4 * math.exp(np.mean([math.log(letter_ratio(i)) for i in mem])) if mem else D4
dsv = rdur("svd")
for r in range(6): put(pad([D4 * LADDER[(r * 2) % 9] / 2], dsv - r * dsv / 6 + 0.5, 0.055, fade=1.0), rstart("svd") + r * dsv / 6, pan=(r - 2.5) / 3.5, wet=0.45)
for it in range(7):
    ts = ra("svd", T_["TSV"] + 3 + it)
    if ts < rstart("collapse"):
        for k in range(4): put(pad([cluster_pitch(it, k)], 1.0, 0.045, fade=0.3, wave="sine"), ts, pan=(k - 1.5) / 2.5, wet=0.45)

# ------------------------------------------------------------------ the modern half: the groove, on a beat grid pinned to the finale
grid0 = FIN0 - math.floor(FIN0 / BEAT) * BEAT
steps = np.arange(0, int((CYC - grid0) / S16))
st_t = grid0 + steps * S16
bar_idx = np.floor((st_t - FIN0) / BAR).astype(int)             # bars relative to the finale (negative before it)
step_in_bar = np.round(((st_t - FIN0) / S16)).astype(int) % 16
def G(spec, t):
    for a, b, g in spec:
        if a <= t < b: return g
    return 0.0
B = BAR
t_web, t_msg, t_spec, t_pr, t_an, t_de, t_wk, t_fo, t_po, t_sv, t_col = (rstart(n) for n in ("web", "msg", "spectral", "pagerank", "anneal", "descent", "walk", "fourier", "poincare", "svd", "collapse"))
F3a, F3b = FIN0 + 10 * B, FIN0 + 16 * B
KICK_SPEC = [(t_msg, t_pr, 0.0), (t_pr, FIN0, 0.78), (FIN0 + 2 * B, FIN0 + 16 * B, 0.95), (FIN0 + 16 * B, FIN0 + 18 * B, 0.6)]
HALF_SPEC = [(t_msg, t_pr, 0.5)]
HAT8 = [(t_web, t_msg, 0.35), (t_msg, FIN0, 0.5), (FIN0 + 2 * B, FIN0 + 18 * B, 0.7)]
HAT16 = [(t_de, FIN0, 0.4), (FIN0 + 4 * B, FIN0 + 16 * B, 0.5)]
OHAT_S = [(t_an, FIN0, 0.6), (FIN0 + 2 * B, FIN0 + 17 * B, 0.8)]
DHOL_S = [(FIN0 + 2 * B, FIN0 + 16 * B, 0.8), (FIN0 + 16 * B, FIN0 + 18 * B, 0.45)]
CLAP_S = [(t_an, FIN0, 0.55), (FIN0 + 2 * B, FIN0 + 16 * B, 0.8), (FIN0 + 16 * B, FIN0 + 18 * B, 0.4)]
BASS = [(t_spec, t_pr, 0.35), (t_pr, FIN0, 0.65), (FIN0 + 2 * B, FIN0 + 17 * B, 1.0)]
ARP = [(t_spec, t_pr, 0.25), (t_pr, t_wk, 0.4), (t_wk, FIN0, 0.65), (FIN0 + B, FIN0 + 10 * B, 0.8), (FIN0 + 10 * B, FIN0 + 16 * B, 1.0), (FIN0 + 16 * B, FIN0 + 19 * B, 0.55)]
STAB = [(FIN0 + 2 * B, FIN0 + 10 * B, 0.6), (FIN0 + 10 * B, FIN0 + 16 * B, 0.9)]
SPADV = [(t_fo, FIN0 - 0.5 * B, 0.5), (FIN0 + 10 * B, FIN0 + 17 * B, 0.9)]
# chord loops (ratios to D; pcs in cents) -- the ancient half and the build in a minor mode, the drop in Mixolydian
CH_MIN = [("Dm", 1.0, (0, 294, 702)), ("C", 16/9, (996, 204, 498)), ("G", 4/3, (498, 906, 0)), ("Am", 3/2, (702, 996, 204))]
CH_MIX = [("D", 1.0, (0, 408, 702)), ("C", 16/9, (996, 204, 498)), ("G", 4/3, (498, 906, 0)), ("C", 16/9, (996, 204, 498))]
SC_MIN = (0, 204, 294, 498, 702, 906, 996); SC_MIX = (0, 204, 408, 498, 702, 906, 996)
def chord_at(t):
    b = int(math.floor((t - FIN0) / B))
    drop = FIN0 + 10 * B <= t < FIN0 + 20 * B
    return (CH_MIX if drop else CH_MIN)[b % 4], (SC_MIX if drop else SC_MIN)
def snap_pc(f, allowed):
    c = cents(f); base = 1200 * math.floor(c / 1200); pc = c - base
    best = min(allowed + (1200,), key=lambda a: abs(pc - a)); return D4 * 2.0 ** ((base + best) / 1200.0)
mrng = np.random.default_rng(128); state = int(mrng.integers(0, N)); arp_pat = [1.0, 0.55, 0.8, 0.5, 1.0, 0.55, 0.8, 0.6, 1.0, 0.5, 0.8, 0.55, 1.0, 0.6, 0.85, 0.5]
for n_, (tt, sb, bi) in enumerate(zip(st_t, step_in_bar, bar_idx)):
    if tt < t_web - 1.0 or tt > FIN1 + 0.1: continue
    chn, scale = chord_at(tt)
    kg = G(KICK_SPEC, tt)
    if (sb % 4 == 0 and kg > 0) or (sb % 8 == 0 and G(HALF_SPEC, tt) > 0):
        g = kg if kg > 0 else G(HALF_SPEC, tt)
        add(LN, KICK * 0.55 * g, tt); add(RN, KICK * 0.55 * g, tt); KICKS.append(tt)
    dg = G(DHOL_S, tt)
    if dg > 0 and sb % 2 == 0:
        e8 = sb // 2                                              # the eighth note in the bar: dum on 0, 3, 6 and tek on 2, 5, 7 (3 + 3 + 2)
        if e8 in (0, 3, 6): put(DUM * 0.5 * dg, tt, pan=-0.15, wet=0.15)
        elif e8 in (2, 5, 7): put(TEK * 0.45 * dg, tt, pan=0.2, wet=0.2)
    if sb % 8 == 4 and G(CLAP_S, tt) > 0: put(CLAP * 0.35 * G(CLAP_S, tt), tt, pan=0.05, wet=0.25)
    if sb % 2 == 0 and G(HAT8, tt) > 0 and sb % 4 != 2: put(HAT * 0.55 * G(HAT8, tt), tt, pan=-0.2, wet=0.1)
    if sb % 4 == 2 and G(OHAT_S, tt) > 0: put(OHAT * 0.5 * G(OHAT_S, tt), tt, pan=0.25, wet=0.15)
    if sb % 2 == 1 and G(HAT16, tt) > 0: put(HAT * 0.35 * G(HAT16, tt), tt, pan=0.3 if sb % 4 == 1 else -0.3, wet=0.1)
    if sb % 4 == 2 and G(BASS, tt) > 0:
        root = D4 * chn[1] / 4.0
        while root > 125: root /= 2
        while root < 60: root *= 2
        if sb == 14: root *= 2.0
        put(bassnote(root, S16 * 3.2, 0.55 * G(BASS, tt)), tt, pan=0.0, wet=0.05, duck=True)
    ag = G(ARP, tt)
    if ag > 0:
        # the letters walk the attention graph: each hop is a note, folded into the chord
        row = Wm[state]; r_ = mrng.random(); acc = 0.0; nxt = 0
        for nxt in range(N):
            acc += row[nxt]
            if r_ <= acc: break
        state = min(N - 1, nxt)
        f = letter_freq(state);
        while f < D4: f *= 2
        while f > D4 * 4: f /= 2
        chord_pcs = tuple(chn[2]); use = chord_pcs if mrng.random() < 0.65 else scale
        f = snap_pc(f, tuple(use))
        pan = math.sin(n_ * 0.7) * 0.5
        put(kanun(f, 0.05 * ag * arp_pat[sb], dur=0.6, bright=1.4), tt, pan=pan, wet=0.28, duck=True)
    sg = G(STAB, tt)
    minor = chn[0] in ("Dm", "Am")
    base = D4 * chn[1]
    while base >= D4: base /= 2
    while base < D4 / 2: base *= 2
    if sg > 0 and sb % 8 == 2:
        for ratio in (1.0, 32/27 if minor else 81/64, 3/2, 2.0):
            put(supersaw(base * 2 * ratio, S16 * 2.6, 0.035 * sg, cutoff=3200), tt, pan=(ratio - 1.5) * 0.3, wet=0.3, duck=True)
    pg = G(SPADV, tt)
    if pg > 0 and sb == 0 and bi % 2 == 0:
        for k_ in (1.0, 3/2, 2.0 * (32/27 if minor else 81/64)):
            put(supersaw(base * k_, 2 * B, 0.03 * pg, cutoff=1800, att=0.25, rel=0.6), tt, pan=float(mrng.uniform(-.4, .4)), wet=0.4, duck=True)
# risers, rolls, impacts at the joints of the arrangement
put(riser(t_col + (FIN0 - t_col) - (t_sv), 0.5), t_sv, wet=0.4)
put(impact(2.6, 0.9), FIN0, wet=0.45); put(riser(2 * B, 0.45, 400, 7000), FIN0, wet=0.4); put(snare_roll(0.9 * B, 0.5), FIN0 + 1.1 * B, wet=0.3)
put(impact(1.8, 0.7), FIN0 + 2 * B, wet=0.4)
put(riser(3 * B, 0.5, 300, 9000), FIN0 + 6.8 * B, wet=0.4); put(snare_roll(1.0 * B, 0.7), FIN0 + 9 * B, wet=0.3)
put(impact(3.0, 1.0), F3a, wet=0.5); put(CLAP * 0.5, F3a, wet=0.4)
put(impact(2.0, 0.6), F3b, wet=0.5); put(riser(0.5 * B, 0.3, 500, 6000), F3b - 0.5 * B, wet=0.4)
put(impact(4.0, 0.7), FIN1 - 0.3, wet=0.6)
# ---- the finale's melody: the six letters of Mashtots are the hook, F# D B E C G
HOOK = [("Մ", 1), ("Ա", 1), ("Շ", 2), ("Տ", 1), ("Ո", 1), ("Ց", 2)]
def hook_f(ch):
    f = letter_freq(LET.index(ch));
    while f < D4: f *= 2
    while f >= D4 * 2: f /= 2
    return f
for rep in range(3):
    t0 = F3a + rep * 8 * BEAT; tt = t0
    for k, (ch_, beats) in enumerate(HOOK):
        f = hook_f(ch_) * (2.0 if (rep == 2 and k == len(HOOK) - 1) else 1.0)
        put(duduk(f, beats * BEAT * 0.97, amp=0.30, legato=k > 0, vib=1.0), tt, pan=0.1, wet=0.3)
        put(kanun(f * 2, 0.10, dur=1.2, bright=1.3), tt, pan=-0.2, wet=0.35)
        tt += beats * BEAT
# earlier in the finale and at the end: long duduk notes
for (b0, f_, beats) in ((FIN0 + 2 * B, D4, 7.5), (FIN0 + 6 * B, D4 * 4 / 3, 7.5), (FIN0 + 16 * B, D4, 7.5), (FIN0 + 18 * B, D4 / 2, 7.0)):
    put(duduk(f_, beats * BEAT, amp=0.26, vib=1.0, rel=1.2), b0, pan=0.12, wet=0.4)
# ---- the finale's letters: a harp wash as the organisation completes
for i in range(N): pluck_letter(i, F3a + 1.0 * B + i * 0.05, amp=0.05, soft=True, duck=True)

# ---- return and colophon: the letters fall home (a descending cascade); a D major chord and a last duduk note close the loop on the tonic
for i in range(N):
    tt = ra("return", T_["T2"] + (N - 1 - i) * stagger)
    put(glass(letter_freq(i, 1), i, 0.055, 1.2), tt, pan=(i % 9 - 4) / 6, wet=0.5)
    pluck_letter(i, tt + 2.2, amp=0.035, soft=True)
put(pad([D4 / 2, D4 * 81 / 64 / 2, D4 * 1.5 / 2, D4], COL1 - COL0 + 4.0, 0.12, fade=1.8), COL0 + 0.3, wet=0.5)
put(duduk(D4, 4.5, amp=0.26, vib=0.7, rel=1.4), COL0 + 1.3, pan=0.1, wet=0.45)
put(duduk(D4 / 2, 5.0, amp=0.24, vib=0.6, rel=2.0), CYC - 8.0, pan=0.1, wet=0.45)

# ------------------------------------------------------------------ side-chain, the stone room, loop seam, master
duck = np.zeros(NS, dtype=F32); kk = int(0.38 * SR); ker = np.exp(-np.arange(kk) / SR / 0.11).astype(F32)
for tk in KICKS:
    i0 = int(tk * SR)
    if i0 + kk < NS: duck[i0:i0 + kk] = np.maximum(duck[i0:i0 + kk], ker)
dk = (1.0 - 0.72 * duck)
LN += LD_ * dk; RN += RD_ * dk; WLN += WLD * dk; WRN += WRD * dk
def reverb(wl, wr, rt60=3.4):
    n = int(rt60 * 1.1 * SR); t = np.arange(n) / SR; outs = []
    for _ in range(2):
        ir = rng.normal(size=n) * np.exp(-6.9 * t / rt60); ir = lp(ir, 5200) * np.minimum(1, t / 0.02); outs.append((ir / np.sqrt(np.sum(ir ** 2))).astype(F32))
    return fftconvolve(wl, outs[0])[:NS].astype(F32), fftconvolve(wr, outs[1])[:NS].astype(F32)
rl, rr = reverb(WLN, WRN)
outL = LN + rl * 0.9; outR = RN + rr * 0.9
nT = int(TAIL * SR); cyc = int(CYC * SR)
fl = outL[:cyc].copy(); fr_ = outR[:cyc].copy(); fl[:nT] += outL[cyc:cyc + nT]; fr_[:nT] += outR[cyc:cyc + nT]
def limit(x, thr=0.42, rel=0.35, look=0.004):
    """a block-wise look-ahead limiter: 1 ms blocks, instant attack (with look-ahead), exponential release; keeps the kick and the impacts from setting the loudness"""
    blk = int(SR * 0.001); nb = len(x) // blk
    env = np.abs(x[:nb * blk]).max(axis=1).reshape(nb, blk).max(axis=1)
    g = np.minimum(1.0, thr / np.maximum(env, 1e-9))
    w = max(1, int(look / 0.001))
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    g = minimum_filter1d(g, size=2 * w + 1, mode="nearest")
    a = 1 - math.exp(-0.001 / rel); gs = np.empty_like(g); cur = 1.0
    for i in range(nb):
        cur = min(g[i], cur + (1 - cur) * a); gs[i] = cur
    gs = uniform_filter1d(gs, size=w, mode="nearest")
    xs = np.arange(len(x)) / blk - 0.5
    gain = np.interp(xs, np.arange(nb), gs).astype(F32)
    return x * gain[:, None]
pre = np.stack([fl, fr_], 1); pk = float(np.abs(pre).max())
pre = limit(pre / pk, 0.80, 0.30); pre *= 0.93 / float(np.abs(pre).max())
mix = np.tanh(pre * 1.15) / np.tanh(1.15)
print("peak before limiter %.3f, rms %.3f, kicks %d" % (pk, float(np.sqrt(np.mean(mix ** 2))), len(KICKS)))
pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
with wave.open("landing_score.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "landing_score.wav", "-codec:a", "libmp3lame", "-b:a", "192k", "landing_score.mp3"], check=True)
print("wrote landing_score.mp3,", round(cyc / SR, 2), "s")
