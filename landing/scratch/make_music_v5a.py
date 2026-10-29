#!/usr/bin/env python3
"""The score of the Landing (v4), synthesised offline and locked to its real-time loop (204.25 s; see timeline.py).

History. v1 (the one whose harp you loved): a dam drone, an improvised duduk, a kanun note per letter. v2 added a groove and many sonification layers; measured, it had real faults (every plucked note ended in a click,
four keys at once plus random draws so layers could clash, 60-90 % of the energy below 250 Hz). v3 fixed those with ONE harmony table and measured stem levels, but it lost some of what you loved: the duduk became sparse and composed,
the harp was flattened to a safe pentatonic, the dam was inaudible and the groove was too synthetic. v4 keeps v3's discipline and brings the Armenian instruments back:
  1. The harp is the stone's own again: a letter's pitch = a step of the natural-minor ladder (column), its row a key a fifth higher (D, A, E, B minor). The four rows of the tour are four rising runs, each in its own key,
     and the HARMONY NOW FOLLOWS THE ROWS (Dm Bb F | Am F | Em C | Bm G, then D major and its dominant A falling to Dm for the prayer), so the modal journey is back and nothing clashes. The D drone (the dam) is a chord tone or colour tone in every one of those chords.
     The letters fall home in the same keys, in reverse. Harp glissandi and rolled chords mark the joints. Sections where letters sound in no order (the writing, the prayer, the graph acts) use the chord's pentatonic as in v3.
  2. The duduk improvises again (the deck's phrasing: a random walk on the scale, 3-6 notes, a long last note on a chord tone, grace notes, mordents, scoops, slides between neighbours) but it listens to the harmony: a long note is always a tone of the chord,
     a passing note may be any note of the key, a note that would sound across a chord change it does not fit is cut short. In the modern half it improvises on the beat grid over the groove. The composed phrases stay at the entrance, the prayer, the Amen and the hook.
  3. The dam is a second duduk: a reed spectrum on D3 and A3 (audible on a laptop), periodic over the loop.
  4. The groove keeps its entrances but is less synthetic: the dhol (3 + 3 + 2) and tek are louder, the kanun arpeggio accents the same tresillo, the saws are quieter.
Rules kept from v3: every voice ends with a release (no hard cuts); the stems are balanced by measured loudness (BS.1770); -17 LUFS, -1 dBFS ceiling; a click-free loop seam; every pitched note is audited against the harmony (audit()).
Two files: landing_score.mp3 (full) and landing_score_harp.mp3 (the same music without drums, bass, saws and risers).
Run: python3 make_music.py  (about 2 minutes);  then python3 analyze_score.py landing_score.mp3 to measure it."""
import bisect, json, math, os, random, re, subprocess, sys, time, wave
from functools import lru_cache
import numpy as np
from scipy.signal import fftconvolve, butter, sosfilt
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import lfilter
import score_tools as st

T_START = time.time()
SR = 44100
D = json.load(open("scratch/landing.json", encoding="utf-8"))
TL = json.load(open("scratch/timeline_real.json", encoding="utf-8"))
SEGS, CYC, BPM = TL["segs"], TL["cycle"], TL["bpm"]
BEAT = 60.0 / BPM; BAR = 4 * BEAT; S16 = BEAT / 4
N = 36
CYC_N = int(round(CYC * SR)); TAIL = 6.0; NS = CYC_N + int(TAIL * SR)
F32 = np.float32
SEED = int(os.environ.get("SEED", "0")); TAG = os.environ.get("TAG", "")      # SEED 0 is the approved v4 behaviour; other seeds change the improvisation, the arpeggio patterns, the fills and the ornaments
rng = np.random.default_rng(405 + SEED)

def seg(name): return next(s for s in SEGS if s["name"] == name)
def ra(name, a): s = seg(name); return s["r0"] + (a - s["a0"]) / s["rate"]            # real time of act time a inside the segment
def rstart(name): return seg(name)["r0"]
def rdur(name): return seg(name)["dur"]
T_ = {k: D[k] for k in ("T1", "TL", "TT", "TC", "TW2", "TS2", "TB2", "TSP", "TP", "TA", "TD", "TD2", "TF", "TPC", "TSV", "TSV2", "TH", "T2", "T3")}
begin, stagger, flight, S_, P = D["begin"], D["stagger"], D["flight"], D["S"], D["P"]
FIN0, FIN1, PRA0, PRA1, NUM0, NUM1, SHI0, SHI1, COL0, COL1 = (TL[k] for k in ("FIN0", "FIN1", "PRA0", "PRA1", "NUM0", "NUM1", "SHI0", "SHI1", "COL0", "COL1"))
LET = "".join(d[0] for d in D["DATA"])
def bar_t(b): return FIN0 + b * BAR                                                   # time of bar b (b = 0 is the finale's first bar; negative before)
def bar_of(t): return (t - FIN0) / BAR
def q16(t): return FIN0 + round((t - FIN0) / S16) * S16
T_GROOVE = bar_t(-29)                                                                 # from here events are locked to the 16th grid

# ------------------------------------------------------------------ tuning: Pythagorean (3-limit) on D
D4 = 293.665; D3 = D4 / 2
PCR = {"D": 1.0, "Eb": 256/243, "E": 9/8, "F": 32/27, "F#": 81/64, "G": 4/3, "G#": 729/512, "A": 3/2, "Bb": 128/81, "B": 27/16, "C": 16/9, "C#": 243/128}
PCN = {pc: i for i, pc in enumerate(["D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B", "C", "C#"])}      # semitones above D
def hz(name):
    """'A4' -> Hz (scientific octave numbers; A4 = 440.5 Hz in this tuning, D4 = 293.665)"""
    pc, o = name[:-1], int(name[-1]); od = o - (1 if pc in ("C", "C#") else 0)
    return D3 * PCR[pc] * 2.0 ** (od - 3)
def ladder(pcs, lo, hi):
    out = []
    for o in range(0, 9):
        for pc in pcs:
            f = D3 * PCR[pc] * 2.0 ** (o - 3)
            if lo <= f <= hi: out.append(f)
    return sorted(out)

# ------------------------------------------------------------------ harmony: one table for the whole piece
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
        "Bm": ("B", "C#", "D", "E", "F#", "G", "A"), "DM": ("D", "E", "F#", "G", "A", "B", "C#"), "Dx": ("D", "E", "F#", "G", "A", "B", "C")}   # the keys the piece visits (Dx = D Mixolydian, the drop)
SCALE_LAD = {k: ladder(KEYS[k], 270.0, 900.0) for k in KEYS}                          # the duduk's range, D4 to A5, in each key
PENT = {c: ladder(CH[c]["pent"], 140.0, 2100.0) for c in CH}                          # D3 up, five notes to the octave
def tone_ladder(ch, lo=190.0, n=8):
    cand = sorted((D3 * PCR[pc] * 2.0 ** (o - 3), pc) for o in range(0, 9) for pc in CH[ch]["tones"])
    i0 = next(i for i, (f, pc) in enumerate(cand) if f >= lo and pc == CH[ch]["root"])
    return [f for f, _ in cand[i0:i0 + n]]
TONES = {c: tone_ladder(c) for c in CH}
LOOP = ["Dm", "Bb", "F", "C"]
HARM = []                                                                              # (t0, t1, chord, key)
def hb(k0, nb, ch, key): HARM.append((FIN0 + k0 * BEAT, FIN0 + (k0 + nb) * BEAT, ch, key))      # k0 beats from the finale's first beat (negative before it), nb beats long; 4 beats = 1 bar
hb(-336, 16, "Dm", "Dm"); hb(-320, 16, "Bb", "Dm"); hb(-304, 11, "F", "Dm")           # the stone wakes (Dm); the helix lifts (Bb); row 0 of the tour: D minor
hb(-293, 11, "Am", "Am"); hb(-282, 11, "F", "Am")                                      # row 1: A minor
hb(-271, 11, "Em", "Em"); hb(-260, 11, "C", "Em")                                      # row 2: E minor
hb(-249, 11, "Bm", "Bm"); hb(-238, 11, "G", "Bm")                                      # row 3: B minor
hb(-227, 11, "D", "DM"); hb(-216, 8, "A", "DM")                                        # the sentence: D major, then its dominant A (the leading tone C# falls to D)
hb(-208, 32, "Dm", "Dm")                                                               # the prayer: Dm held for eight bars
hb(-176, 12, "D", "DM")                                                                # the Amen: D major
hb(-164, 16, "Bb", "Dm"); hb(-148, 16, "F", "Dm"); hb(-132, 20, "C", "Dm")             # the numerals, Shirakatsi, the first of the embedding space
for k, b in enumerate(range(-28, 0, 2)): hb(4 * b, 8, LOOP[(k + 2) % 4], "Dm")         # the build: two bars a chord, F C Dm Bb ... landing on Dm at bar 0
for k, b in enumerate(range(0, 10, 2)): hb(4 * b, 8, LOOP[k % 4] if k < 4 else "Dm", "Dm")   # the finale's first ten bars: Dm Bb F C Dm
for b, c in zip(range(10, 18), ("D", "C", "G", "C", "D", "C", "G", "C")): hb(4 * b, 4, c, "Dx")   # the drop: D C G C, D Mixolydian
hb(72, 8, "D", "DM"); hb(80, 48, "D", "DM")                                             # the outro and the return rest on D
for a_, b_ in zip(HARM, HARM[1:]): assert abs(a_[1] - b_[0]) < 1e-6, (a_, b_)          # the table has no gaps
HT = [h[0] for h in HARM]
def chord_at(t):
    i = bisect.bisect_right(HT, t) - 1
    return HARM[max(i, 0)][2]
def key_at(t):
    i = bisect.bisect_right(HT, t) - 1
    return HARM[max(i, 0)][3]
def chord_end(t):
    i = bisect.bisect_right(HT, t) - 1
    return HARM[i][1] if i >= 0 else HARM[0][0]
def pc_of(f):
    c = (1200 * math.log2(f / D3)) % 1200
    return min(PCN, key=lambda pc: abs(((c - 100 * PCN[pc]) + 600) % 1200 - 600))
def safe_pcs(t):
    c = CH[chord_at(t + 0.001)]; return set(c["pent"]) | set(c["tones"]) | set(c["ext"])

NOTELOG = []                                                                          # (t, f, kind, dur): checked against HARM at the end
def LOG(t, f, kind, dur=0.0): NOTELOG.append((float(t), float(f), kind, float(dur)))

def kdeg(i): return i % 9 + 2 * (i // 9)                                              # a letter's step on the ladder: column + 2 row  (0..14)
def lf(i, t, shift=0):
    lad = PENT[chord_at(t)]; return lad[max(0, min(len(lad) - 1, kdeg(i) + shift))]
def pen_deg(k, t):
    lad = PENT[chord_at(t)]; return lad[max(0, min(len(lad) - 1, k))]
def hdur(t0, base, ring=0.6): return max(0.5, min(base, chord_end(t0 + 0.001) + ring - t0))   # a harp note rings into the next chord for at most `ring` s (the pedal is lifted)

# ------------------------------------------------------------------ stems
def Z(): return np.zeros(NS, dtype=F32)
STEM_CFG = {  # duck depth in the full mix (the kick pumps it), mono?
    "drone": (0.00, False), "pad": (0.45, False), "harp": (0.20, False), "arp": (0.40, False), "duduk": (0.10, False),
    "kick": (0.0, True), "bass": (0.50, True), "perc": (0.0, False), "saw": (0.55, False), "fx": (0.0, False), "plate": (0.0, False)}
class Stem:
    def __init__(s, mono): s.mono = mono; s.L = s.R = s.W = s.M = None                 # arrays are made when first written (a stem that is never used costs nothing)
    def get(s, k):
        if getattr(s, k) is None: setattr(s, k, Z())
        return getattr(s, k)
STEMS = {k: Stem(v[1]) for k, v in STEM_CFG.items()}
KICKS = []
def add(buf, x, t0):
    i0 = int(round(t0 * SR))
    if i0 >= len(buf) or i0 + len(x) <= 0: return
    a, b = max(0, -i0), min(len(x), len(buf) - i0)
    buf[i0 + a:i0 + b] += x[a:b].astype(F32)
def put(x, t0, stem, pan=0.0, send=0.0, room=0.0, gain=1.0):
    s = STEMS[stem]
    if s.mono: add(s.get("L"), x * gain, t0)
    else:
        th = (pan + 1) * math.pi / 4; add(s.get("L"), x * (math.cos(th) * math.sqrt(2) * gain), t0); add(s.get("R"), x * (math.sin(th) * math.sqrt(2) * gain), t0)
    if send: add(s.get("W"), x * (send * gain), t0)
    if room: add(s.get("M"), x * (room * gain), t0)

# ------------------------------------------------------------------ DSP helpers
def noise(n): return rng.normal(size=n)
def lp(x, fc, order=2): return sosfilt(butter(order, min(fc, SR * 0.45) / (SR / 2), btype="low", output="sos"), x)
def hp(x, fc, order=2): return sosfilt(butter(order, fc / (SR / 2), btype="high", output="sos"), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo / (SR / 2), min(hi, SR * 0.45) / (SR / 2)], btype="band", output="sos"), x)
def smooth_noise(n, hz_, r=None):
    r = r or rng; k = int(n / SR * hz_) + 3; pts = r.normal(size=k); return np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
def norm(y, peak=1.0):
    m = float(np.abs(y).max()); return (y * (peak / m)).astype(F32) if m > 0 else y.astype(F32)
def fade_out(y, ms=25):
    k = min(len(y), int(SR * ms / 1000)); y[-k:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(k) / k); return y
CLICKS = [norm(bp(rng.normal(size=int(0.1 * SR)), 2500, 7000) * np.exp(-np.arange(int(0.1 * SR)) / SR / 0.012)) for _ in range(6)]

@lru_cache(maxsize=700)
def _kanun(f, dur, tau, bright, click, k):
    n = int((dur + 0.4) * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for h in range(1, 15):
        fh = f * h * math.sqrt(1 + 0.0003 * h * h)
        if fh > 9000: break
        y += (1.0 / h ** (1.15 / bright)) * np.exp(-t / (tau / h ** 0.72)) * np.sin(2 * math.pi * fh * t + 0.4 * h)
    y = norm(y); c = CLICKS[k % len(CLICKS)]; y[:len(c)] += c[:n] * click
    y *= np.minimum(1.0, t / 0.004) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.06))                 # fingers damp the string: no hard cut
    return norm(fade_out(y, 30))
def kanun(f, dur=2.0, tau=1.5, bright=1.0, click=0.22):
    """a plucked string: harmonic partials with their own decays (the harp you liked), then damped"""
    return _kanun(round(f, 2), round(dur, 1), tau, bright, click, int(f) % 6)

@lru_cache(maxsize=500)
def _glass(f, dur, tau):
    n = int((dur + 0.4) * SR); t = np.arange(n) / SR
    y = np.sin(2 * math.pi * f * t) * np.exp(-t / tau) + 0.5 * np.sin(2 * math.pi * f * 1.0022 * t + 1.1) * np.exp(-t / tau)           # a beating pair: the shimmer of struck glass
    y += 0.26 * np.sin(2 * math.pi * 2 * f * t + 0.5) * np.exp(-t / (tau * 0.7)) + 0.09 * np.sin(2 * math.pi * 3 * f * t + 2) * np.exp(-t / (tau * 0.5))   # only harmonic partials: octave, then the fifth above it
    y *= np.minimum(1.0, t / 0.012) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.08))
    return norm(fade_out(y, 30))
def glass(f, dur=1.4, tau=0.8): return _glass(round(f, 2), round(dur, 1), tau)

def duduk(f0, dur, f_from=None, vib=1.0, scoop=False, grace=None, mord=None, rel=0.45, seed=0):
    """a double-reed: odd-weighted harmonics under a nasal formant near 1 kHz, a soft breath attack, vibrato that blooms after half a second, slow pitch drift; the note may scoop up, slide from the last note, or open with a grace note"""
    r = np.random.default_rng(seed); n = int((dur + rel) * SR); t = np.arange(n) / SR
    cents = np.zeros(n); near = f_from is not None and abs(1200 * math.log2(f_from / f0)) <= 320
    if near: cents += np.where(t < 0.07, 1200 * math.log2(f_from / f0) * (1 - t / 0.07) ** 2, 0.0)        # a slide only between neighbouring notes; a leap is a clean new note
    elif scoop: cents += np.where(t < 0.16, -90 * (1 - t / 0.16) ** 2, 0.0)
    if grace: cents += np.where(t < 0.085, 1200 * math.log2(grace / f0), np.where(t < 0.12, 1200 * math.log2(grace / f0) * (1 - (t - 0.085) / 0.035), 0.0))
    if mord: cents += np.where((t >= 0.05) & (t < 0.10), 1200 * math.log2(mord / f0), 0.0)                    # a mordent: the note, its upper neighbour, the note
    cents += 11.0 * vib * (1 - np.exp(-np.maximum(t - 0.45, 0) / 0.5)) * np.sin(2 * math.pi * (5.3 + 0.25 * np.sin(0.7 * t)) * t + r.uniform(0, 6.28)) + 2.5 * smooth_noise(n, 1.4, r)
    ph = 2 * math.pi * np.cumsum(f0 * 2.0 ** (cents / 1200.0)) / SR
    env = (1 - np.exp(-t / 0.07)) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (rel / 4.5))) * (1 + 0.05 * np.sin(2 * math.pi * 0.31 * t + r.uniform(0, 6.28)))
    lo, hi = np.zeros(n), np.zeros(n)
    for h in range(1, 19):
        fh = f0 * h
        if fh > 6000: break
        a = h ** -0.95 * (1.0 + 0.6 * (h % 2 == 1)) * (0.3 + math.exp(-math.log(fh / 1250.0) ** 2 / (2 * 0.8 ** 2))) / (1 + (fh / 4600.0) ** 4)
        if h <= 3: lo += a * np.sin(h * ph)
        else: hi += a * np.sin(h * ph)
    y = lo + hi * (0.55 + 0.45 * np.minimum(env, 1.0))                                  # a louder reed is brighter
    y = y * env + bp(r.normal(size=n), 800, 2600) * 0.03 * (1 + 2.2 * np.exp(-t / 0.12)) * env                            # the breath
    return norm(hp(y, 130))

@lru_cache(maxsize=200)
def _padnote(f, dur, att, rel):
    n = int((dur + rel) * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for dt, vg in ((-3, 0.22), (0, 1.0), (3, 0.22)):                                      # a shallow shimmer (the beat is 40 % deep, not 100 %)
        ph = 2 * math.pi * f * 2.0 ** (dt / 1200) * t
        for h in (1, 3, 5, 7, 9, 11):                                                    # a triangle wave, band-limited
            if f * h > 5000: break
            y += vg * ((-1) ** ((h - 1) // 2)) / h ** 2 * np.sin(h * ph)
    y = lp(y + 0.25 * np.sin(2 * math.pi * f * t), 1500)
    env = np.minimum(1.0, t / att) ** 1.5 * np.where(t < dur, 1.0, 0.5 + 0.5 * np.cos(np.pi * np.clip((t - dur) / rel, 0, 1)))
    return norm(y * env)
def padnote(f, dur, att=1.2, rel=1.4): return _padnote(round(f, 2), round(dur, 1), att, rel)

@lru_cache(maxsize=300)
def _supersaw(f, dur, cutoff, att, rel, seed):
    r = np.random.default_rng(seed); n = int((dur + rel) * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for dt in (-20, -11, -4, 0, 4, 11, 20):                                              # seven band-limited saws (additive: no aliasing)
        fv = f * 2.0 ** (dt / 1200.0); phi = r.uniform(0, 6.28)
        for h in range(1, int(min(cutoff * 1.7, 9000) / fv) + 1): y += np.sin(2 * math.pi * h * fv * t + phi * h) / h
    y = lp(y, cutoff)
    env = np.minimum(1.0, t / att) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (rel / 4)))
    return norm(fade_out(y * env, 20))
def supersaw(f, dur, cutoff=2600.0, att=0.012, rel=0.12): return _supersaw(round(f, 2), round(dur, 2), cutoff, att, rel, int(f) % 7)

# ---- drums, bass, effects (each normalised to a peak of 1; the gains are set where they are used)
def _kick():
    n = int(0.4 * SR); t = np.arange(n) / SR; f = 50 + 125 * np.exp(-t / 0.024); ph = 2 * math.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t / 0.15) + 0.28 * np.sin(2 * ph) * np.exp(-t / 0.05)
    y[:len(CLICKS[1])] += CLICKS[1][:n] * 0.16
    return norm(fade_out(hp(y * np.minimum(1.0, t / 0.0012), 32), 12))
def _clap():
    n = int(0.3 * SR); t = np.arange(n) / SR; y = np.zeros(n)
    for d_ in (0.0, 0.010, 0.021): y += np.where(t >= d_, np.exp(-(t - d_) / 0.011), 0.0) * rng.normal(size=n)
    y = bp(y, 1000, 4200) + 0.8 * np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.06), 0.0) * bp(rng.normal(size=n), 1100, 3800)
    return norm(fade_out(y * np.minimum(1.0, t / 0.0006), 20))
def _hat(open_=False):
    n = int((0.22 if open_ else 0.06) * SR); t = np.arange(n) / SR
    return norm(fade_out(lp(hp(rng.normal(size=n), 6500), 15000) * np.exp(-t / (0.08 if open_ else 0.016)) * np.minimum(1.0, t / 0.0006), 6))
def _dum():
    n = int(0.3 * SR); t = np.arange(n) / SR; f = 78 + 34 * np.exp(-t / 0.05); ph = 2 * math.pi * np.cumsum(f) / SR
    return norm(fade_out(np.sin(ph) * np.exp(-t / 0.12) * np.minimum(1.0, t / 0.002) + 0.2 * bp(rng.normal(size=n), 200, 900) * np.exp(-t / 0.03), 15))
def _tek():
    n = int(0.14 * SR); t = np.arange(n) / SR
    return norm(fade_out((bp(rng.normal(size=n), 1800, 5200) * np.exp(-t / 0.02) + 0.5 * np.sin(2 * math.pi * 410 * t) * np.exp(-t / 0.035)) * np.minimum(1.0, t / 0.0006), 10))
KICK, CLAP, HAT, OHAT, DUM, TEK = _kick(), _clap(), _hat(), _hat(True), _dum(), _tek()
@lru_cache(maxsize=80)
def _bass(f, dur):
    n = int((dur + 0.06) * SR); t = np.arange(n) / SR
    y = np.sin(2 * math.pi * f * t) + 0.4 * np.sin(4 * math.pi * f * t) + 0.12 * np.sin(6 * math.pi * f * t)
    y += 0.25 * lp(sum(np.sin(2 * math.pi * h * f * t) / h for h in range(1, 10)), 480)
    return norm(fade_out(y * np.minimum(1.0, t / 0.006) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.02)), 20))
def bassnote(f, dur): return _bass(round(f, 2), round(dur, 3))
def riser(dur, f0=300.0, f1=9000.0):
    n = int(dur * SR); x = noise(n); out = np.zeros(n); u = np.linspace(0, 1, n); nb = 20
    for k in range(nb):
        c = f0 * (f1 / f0) ** (k / (nb - 1)); out += bp(x, c * 0.75, min(c * 1.33, 16000)) * np.exp(-((u * (nb - 1) - k) ** 2) / 0.9)
    return norm(fade_out(out * u ** 2.2, 40))
def snare_roll(dur):
    n = int(dur * SR); y = np.zeros(n); t = 0.0
    hit = norm(bp(noise(int(0.1 * SR)), 1500, 8000) * np.exp(-np.arange(int(0.1 * SR)) / SR / 0.025))
    while t < dur:
        a = int(t * SR); m = min(len(hit), n - a); y[a:a + m] += hit[:m] * (0.25 + 0.75 * t / dur)
        t += S16 * (1.0 if t < dur * 0.5 else 0.5 if t < dur * 0.8 else 0.25)
    return norm(fade_out(y, 20))
def impact(dur=2.4):
    n = int(dur * SR); t = np.arange(n) / SR; f = 52 * np.exp(-t / 0.9) + 30; ph = 2 * math.pi * np.cumsum(f) / SR
    return norm(fade_out(np.sin(ph) * np.exp(-t / 0.8) + lp(noise(n), 900) * np.exp(-t / 0.5) * 0.5, 60))

# ------------------------------------------------------------------ the dam: a second duduk holding the tonic (a reed spectrum under a nasal formant), periodic over the loop so that the seam makes no click
def build_drone():
    Pn = CYC_N / SR; t = np.arange(CYC_N) / SR
    def autom(pts): return np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    d2_gain = autom([(0, 1.0), (bar_t(-27), 1.0), (bar_t(-17), 0.12), (FIN1, 0.12), (FIN1 + 3, 1.0), (CYC_N / SR, 1.0)])   # the sub-D leaves the room while the bass plays
    def reed(f, nmax, phi):
        y = np.zeros(CYC_N)
        for h in range(1, nmax + 1):
            fh = f * h
            if fh > 4200: break
            a = h ** -0.95 * (1.0 + 0.6 * (h % 2 == 1)) * (0.3 + math.exp(-math.log(fh / 1250.0) ** 2 / (2 * 0.8 ** 2))) / (1 + (fh / 3400.0) ** 4)
            y += a * np.sin(2 * math.pi * (round(fh * Pn) / Pn) * t + phi * h)             # f * period = a whole number of cycles
        return y
    out = reed(D3, 22, 0.7) * (1 + 0.08 * np.sin(2 * math.pi * 19 * t / Pn)) + 0.45 * reed(D3 * 1.5, 10, 2.1) * (1 + 0.08 * np.sin(2 * math.pi * 23 * t / Pn + 1.0))
    sub = sum(a * np.sin(2 * math.pi * (round(D3 / 2 * h * Pn) / Pn) * t + 0.3 * h) for h, a in ((1, 1.0), (2, 0.5), (3, 0.3)))
    out = out + 0.7 * sub * d2_gain * (1 + 0.1 * np.sin(2 * math.pi * 17 * t / Pn))
    dist = np.minimum(t, Pn - t); out *= 1 - 0.6 * np.exp(-(dist / 2.0) ** 2)                  # a soft dip at the seam: the loop breathes
    s = STEMS["drone"]; s.get("L")[:CYC_N] += out.astype(F32); s.get("R")[:CYC_N] += out.astype(F32); s.get("W")[:CYC_N] += (out * 0.25).astype(F32)
build_drone()

# ------------------------------------------------------------------ pads: one chord at a time, voice-led (each chord moves by step), long attacks
def pad_gain(t0):
    b = bar_of(t0)
    if b < -52: return 1.0
    if b < -28: return 0.8
    return 0.55
for (t0, t1, ch, key_) in HARM:
    if t0 > CYC: break
    for k, nm in enumerate(CH[ch]["pad"]):
        f = hz(nm); put(padnote(f, t1 - t0 + 0.2, 1.2, 1.4), t0 - 0.2, "pad", pan=(k - 1) * 0.35, send=0.5, gain=0.06 * pad_gain(t0)); LOG(t0, f, "pad")

# ------------------------------------------------------------------ the harp (kanun): the letters, each on its step of the chord's pentatonic
def pluck(i, t0, amp=0.16, dur=2.2, shift=0, glass_amp=0.3, tau=1.5, stem="harp", send=0.32):
    f = lf(i, t0, shift); d = hdur(t0, dur); pan = (kdeg(i) - 7) / 9.0; amp *= min(1.0, (f / 330.0) ** 0.6)                    # the low strings are quieter: no mud
    put(kanun(f, d, tau=tau), t0, stem, pan=pan, send=send, gain=amp); LOG(t0, f, "harp")
    if glass_amp: put(glass(f * 2, d * 0.7), t0, stem, pan=-pan, send=0.5, gain=amp * glass_amp)
def pluck_k(k, t0, amp=0.1, dur=1.2, pan=0.0, glass_amp=0.0, tau=1.2, stem="harp"):
    f = pen_deg(k, t0); d = hdur(t0, dur); amp *= min(1.0, (f / 330.0) ** 0.6)
    put(kanun(f, d, tau=tau), t0, stem, pan=pan, send=0.3, gain=amp); LOG(t0, f, "harp")
    if glass_amp: put(glass(f * 2, d * 0.7), t0, stem, pan=-pan, send=0.5, gain=amp * glass_amp)

# ---- the stone's own pitches (the original harp): column = a step of the natural-minor ladder, row = a key a fifth higher (D, A, E, B minor)
LADDER = [1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2, 9/4]
def fold(x):
    while x >= 2: x /= 2
    while x < 1: x *= 2
    return x
def lf_row(i):
    r = i // 9; return D4 * LADDER[i % 9] * fold(1.5 ** r) * (0.5 if r == 0 else 1.0)
def pluck_row(i, t0, amp=0.16, dur=2.4, glass_amp=0.3, tau=1.5, kind="row", ring=0.9, limit=True):
    f = lf_row(i); d = hdur(t0, dur, ring) if limit else dur; pan = (i % 9 - 4) / 5.5; amp *= min(1.0, (f / 330.0) ** 0.6)
    put(kanun(f, d, tau=tau), t0, "harp", pan=pan, send=0.32, gain=amp); LOG(t0, f, kind, d)
    if glass_amp: put(glass(f * 2, d * 0.7), t0, "harp", pan=-pan, send=0.5, gain=amp * glass_amp)
def gliss(t0, key, lo, hi, n, dt, amp, up=True, stem="harp"):
    """a harp glissando through the notes of a key (the pedals set to the scale): n notes dt apart, ascending or falling, panned across"""
    lad = ladder(KEYS[key] if isinstance(key, str) else key, lo, hi); seq = [lad[int(round(x))] for x in np.linspace(0, len(lad) - 1, n)]; seq = seq if up else seq[::-1]
    for j, f in enumerate(seq):
        u = j / max(1, n - 1); put(kanun(f, 1.3, tau=0.8), t0 + j * dt, stem, pan=(-0.7 + 1.4 * u) if up else (0.7 - 1.4 * u), send=0.35, gain=amp * (0.55 + 0.45 * (u if up else 1 - u)) * min(1.0, (f / 330.0) ** 0.6)); LOG(t0 + j * dt, f, "gliss", 1.3)
def flourish(t0, ch, n=7, dt=0.055, amp=0.07):
    """a rolled chord, the kanun's way of marking a new harmony: the chord's tones, ascending"""
    for j, f in enumerate(TONES[ch][:n]): put(kanun(f, 1.5, tau=1.0), t0 + j * dt, "harp", pan=-0.5 + j / (n - 1), send=0.35, gain=amp * min(1.0, (f / 330.0) ** 0.6)); LOG(t0 + j * dt, f, "arp", 1.5)

# ---- the stone wakes: four rising harp runs as the 36 letters leave (the four rows: D, A, E, B minor), the same runs very softly as they land
for i in range(N): pluck_row(i, P[i]["t0"], amp=0.10, dur=2.2, glass_amp=0.25, kind="cascade", limit=False)
for i in range(N): pluck_row(i, P[i]["t0"] + flight, amp=0.05, dur=1.4, glass_amp=0.0, kind="cascade", limit=False)
gliss(bar_t(-80) + 0.85, "Dm", 146.0, 1250.0, 22, 0.06, 0.05)                           # the helix lifts: a glissando up the scale

# ---- the tour: one note per spotlit letter on the stone's own pitch, the glass an octave above; the harmony follows the rows (Dm | Am | Em | Bm), a rolled chord marks each key
for k in range(N): pluck_row(k, ra("tour", T_["TT"] + k * S_), amp=0.15, dur=2.4, glass_amp=0.3, kind="row")
for k0, ch in ((-293, "Am"), (-271, "Em"), (-249, "Bm")): flourish(FIN0 + k0 * BEAT + 0.05, ch, amp=0.06)

# ---- the tour's cymatics: each spotlit letter is a plate struck at its own pitch. Its mode (n, m) = (column + 1, row + 1) is the Chladni figure the scene draws; a richer mode shimmers faster
# (the beating pair is (n + m) x 0.09 % apart) and settles more sand: n + m x 7 grains of filtered noise fall over a second and thin out (the sand finding the nodal lines).
@lru_cache(maxsize=64)
def _plate(f, nm_, dur):
    n_ = int((dur + 0.4) * SR); t = np.arange(n_) / SR; det = 1.0 + 0.0009 * nm_
    y = np.sin(2 * math.pi * f * t) * np.exp(-t / 1.2) + 0.6 * np.sin(2 * math.pi * f * det * t + 1.0) * np.exp(-t / 1.2)
    y += 0.30 * np.sin(2 * math.pi * 2 * f * t + 0.4) * np.exp(-t / 0.9) + 0.14 * (nm_ / 10.0) * np.sin(2 * math.pi * 4 * f * det * t) * np.exp(-t / 0.6)      # octave partials only: no clash in any key
    y *= np.minimum(1.0, t / 0.01) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.08))
    return norm(fade_out(y, 30))
GRAINS = [norm(bp(rng.normal(size=96), lo, lo * 1.6) * np.exp(-np.arange(96) / 14.0)) for lo in np.geomspace(2200, 6000, 14)]
def sand(ngr, dur, seed):
    r = np.random.default_rng(seed); n = int(dur * SR); y = np.zeros(n)
    for u in r.random(ngr) ** 1.8 * (dur - 0.05):
        g = GRAINS[int(r.integers(len(GRAINS)))]; i0 = int(u * SR); y[i0:i0 + len(g)] += g * r.uniform(0.35, 1.0) * (1 - 0.6 * u / dur)
    return y
for k in range(N):
    tk = ra("tour", T_["TT"] + k * S_); n_, m_ = k % 9 + 1, k // 9 + 1; fk = lf_row(k)
    put(_plate(round(fk, 2), n_ + m_, 1.6), tk, "plate", pan=-(k % 9 - 4) / 5.5, send=0.5, gain=0.10 * min(1.0, (fk / 330.0) ** 0.5))
    for ch_, pn in ((0, -0.7), (1, 0.7)): put(sand(7 * (n_ + m_) // 2, 1.1, 1000 * SEED + 2 * k + ch_), tk + 0.03, "plate", pan=pn, send=0.15, gain=0.05)

# ---- the tour's four styles, one a row: D minor, the duduk and the dam (the ancient); A minor, kanun taksim (random runs through the key); E minor, a soft dhol dance enters; B minor, a pulse (heartbeat and hats) foreshadows the groove
TROW = [ra("tour", T_["TT"] + 9 * r * S_) for r in range(4)] + [ra("tour", T_["TC"])]
tr_ = random.Random(77 + 31 * SEED); tk_ = TROW[1] + 1.2
while tk_ < TROW[2] - 2.2:
    gliss(tk_, "Am", 220.0, 1000.0, tr_.randint(7, 12), 0.07 + 0.02 * tr_.random(), 0.05, up=tr_.random() < 0.65); tk_ += 2.6 + 2.4 * tr_.random()
for si_ in range(int((TROW[2] - FIN0) / S16), int((TROW[4] - FIN0) / S16)):
    tq_ = FIN0 + si_ * S16; sb_ = si_ % 16; w_ = 1.0 if tq_ >= TROW[3] else 0.55; e8 = sb_ // 2
    if sb_ % 2 == 0 and e8 in (0, 3, 6): put(DUM, tq_, "perc", pan=-0.15, room=0.2, gain=0.11 * w_)
    elif sb_ % 2 == 0 and e8 in (2, 5, 7): put(TEK, tq_, "perc", pan=0.2, room=0.2, gain=0.08 * w_)
    if tq_ >= TROW[3]:
        if sb_ % 4 == 0: put(KICK, tq_, "kick", gain=0.09)
        if sb_ % 4 == 2: put(HAT, tq_, "perc", pan=-0.2, room=0.06, gain=0.07)
# ---- the writing: a glissando in D major into the sentence, then each glyph sounds softly as it leaves its source letter
gliss(rstart("write"), "DM", 146.0, 1300.0, 24, 0.05, 0.05)
for q, sl in enumerate(D["slots"]):
    if sl["src"] >= 0: pluck(sl["src"], ra("write", T_["TC"] + 1 + q * D["GDT"]), amp=0.11, dur=1.0, glass_amp=0.25, tau=0.9)
# ---- the Lord's Prayer: the dominant A falls to Dm (a rolled chord); every fifth glyph, very softly; the pad is Dm; the Amen is D major
flourish(FIN0 - 208 * BEAT + 0.05, "Dm", amp=0.07); flourish(FIN0 - 176 * BEAT + 0.3, "D", amp=0.06)
pr = json.load(open("scratch/prayer.json", encoding="utf-8"))
for k, sl in enumerate(pr["slots"]):
    if sl["src"] >= 0 and k % 5 == 0: pluck(sl["src"], PRA0 + 1 + k * pr["GDT"], amp=0.055, dur=1.2, glass_amp=0.0, tau=1.0)
# ---- letters are numbers: the ladder runs as the matrix forms, then each number is struck as a chord of its own letters
flourish(FIN0 - 148 * BEAT + 0.05, "F", amp=0.06)
for i in range(N): pluck(i, NUM0 + 0.7 + i * 0.035, amp=0.065, dur=0.9, glass_amp=0.0, tau=0.9)
def to_arm(n):
    out = ""
    for pw in (3, 2, 1, 0):
        dgt = (n // 10 ** pw) % 10
        if dgt: out += LET[pw * 9 + dgt - 1]
    return out
for k, n in enumerate(TL["EQS"]):
    idx = [LET.index(c) for c in to_arm(n)]
    for j, i in enumerate(idx): pluck(i, TL["EQ_T"][k] + 0.11 * j, amp=0.13, dur=2.2, glass_amp=0.45)
# ---- Shirakatsi's table: row by row, each product a step of the ladder by its digital root; the squares ring in glass
for r in range(1, 10):
    for c in range(1, 10):
        tt = SHI0 + 0.9 + (r * 10 + c) * 0.045; k = (r * c - 1) % 9 + (0 if r < 5 else 5)
        pluck_k(k, tt, amp=0.045, dur=0.6, pan=(c - 5) / 6, tau=0.5)
for r in range(1, 10):
    tt = SHI0 + 0.9 + (r * 10 + r) * 0.045; f = pen_deg((r * r - 1) % 9 + 5, tt); put(glass(f, 1.2), tt, "harp", pan=0.0, send=0.5, gain=0.05); LOG(tt, f, "harp")
# ---- act entries: the letter that sounds each act in (as in the deck), and the embedding scan
ENTRY = {"space": ("TW2", 0), "web": ("TS2", 28), "msg": ("TB2", 19), "spectral": ("TSP", 11), "pagerank": ("TP", 25), "anneal": ("TA", 26),
         "descent": ("TD", 2), "walk": ("TD2", 35), "fourier": ("TF", 34), "poincare": ("TPC", 15), "svd": ("TSV", 29)}
for segn, (key, i) in ENTRY.items():
    tt = ra(segn, T_[key]) + 0.02; tt = q16(tt) if tt >= T_GROOVE else tt
    pluck(i, tt, amp=0.12, dur=1.6, glass_amp=0.3)
pluck(15, PRA0 + 0.02, amp=0.12, glass_amp=0.3); pluck(14, NUM0 + 0.02, amp=0.12, glass_amp=0.3)
for q in range(int(T_["TW2"] * 1.5), int(T_["TS2"] * 1.5)):
    tt = ra("space", q / 1.5)
    if rstart("space") <= tt < rstart("web"): pluck(q % 36, tt, amp=0.05, dur=0.9, shift=5, glass_amp=0.0, tau=0.8)

# ------------------------------------------------------------------ the duduk: composed anchors (the entrance, the prayer, the Amen, the hook) and an improviser that listens to the harmony
# (s = scoop up to the note, v = more vibrato, gX = grace note from X)
def dnote(t, f, dur, prev=None, scoop=False, grace=None, mord=None, vib=1.0, amp=0.2, pan=0.12, send=0.38, seed=0, kind="duduk", stem="duduk"):
    put(duduk(f, dur * 0.985, f_from=prev if prev and not scoop else None, scoop=scoop, grace=grace, mord=mord, vib=vib, seed=seed), t, stem, pan=pan, send=send, gain=amp); LOG(t, f, kind, dur)
def melody(t0, notes, amp=0.2, vib=1.0, pan=0.12, send=0.38):
    t = t0; prev = None
    for nm, beats, fl in notes:
        dur = beats * BEAT
        if nm is None: t += dur; prev = None; continue
        f = hz(nm); mg = re.search(r"g([A-G][#b]?[0-9])", fl); gr = hz(mg.group(1)) if mg else None
        dnote(t, f, dur, prev=prev, scoop=("s" in fl), grace=gr, vib=vib * (1.45 if "v" in fl else 1.0), amp=amp, pan=pan, send=send, seed=int(t * 100) % 9973)
        prev = f; t += dur
def improv(t0, t1, seed, amp=0.2, groove=False, activity=1.0, pan=0.12):
    """the deck's phrasing (a random walk on the scale, 3-6 notes, a long last note, 70 % of the time on a chord tone), made to listen: a long note is always a tone of the chord (or its pentatonic / colour tone),
    a passing note (under a second) may be any note of the key, a note that would sound across a chord change it does not fit is cut short; ornaments: scoop, grace note from the upper neighbour, mordent; slides between neighbouring notes.
    groove=True: the notes are multiples of half a beat and start on the eighth-note grid (the duduk over the dhol); otherwise free time (rubato)"""
    r = random.Random(seed); t = t0; f_cur = hz("A4")
    def q8(x): h = BEAT / 2; return FIN0 + round((x - FIN0) / h) * h
    while t < t1 - 1.5:
        if groove: t = q8(t)
        n = 3 + r.randrange(4); prev = None; prev_end = -9.0
        for k in range(n):
            if t >= t1 - 1.0: break
            lad = SCALE_LAD[key_at(t)]; i0 = min(range(len(lad)), key=lambda j: abs(math.log(lad[j] / f_cur))); u = r.random()
            step = -1 if u < .3 else 1 if u < .6 else -2 if u < .72 else 2 if u < .84 else 0 if u < .92 else (-3 if r.random() < .5 else 3)
            if lad[i0] >= hz("D5") and step > 0: step = -step                               # a pull towards the middle of the range
            if lad[i0] <= hz("E4") and step < 0: step = -step
            i1 = max(0, min(len(lad) - 1, i0 + step)); last = k == n - 1
            if groove: dur = (r.choice((4, 6)) if last else r.choice((1.5, 2, 3, 4))) * BEAT
            else: dur = (2.4 + 1.8 * r.random()) if last else r.choice((0.7, 0.9, 1.2, 1.6, 2.2))
            f = lad[i1]; sp = safe_pcs(t)
            if (dur >= 1.0 or last) and pc_of(f) not in sp: f = min((g for g in lad if pc_of(g) in sp), key=lambda g: abs(math.log(g / f)))
            if last and r.random() < 0.7:
                tp = set(CH[chord_at(t + 0.001)]["tones"]); near = [g for g in lad if pc_of(g) in tp and abs(math.log(g / f)) < 0.22]
                if near: f = min(near, key=lambda g: abs(math.log(g / f)))
            tb = chord_end(t + 0.001)
            if t + dur > tb - 0.05 and pc_of(f) not in safe_pcs(tb + 0.01): dur = max(0.45, tb - 0.12 - t)
            j = min(range(len(lad)), key=lambda jj: abs(math.log(lad[jj] / f))); up = lad[j + 1] if j + 1 < len(lad) else None
            gr = up if (up and dur >= 0.9 and r.random() < 0.35) else None
            md = up if (up and gr is None and dur >= 1.2 and r.random() < 0.12) else None
            dnote(t, f, dur, prev=prev if (prev and t - prev_end < 0.06) else None, scoop=(k == 0 and r.random() < 0.3), grace=gr, mord=md, vib=(0.9 + 0.5 * r.random()) * (1.3 if dur >= 1.6 else 1.0),
                  amp=amp * (0.85 + 0.15 * r.random()), pan=pan, seed=int(t * 100) % 9973)
            prev = f; prev_end = t + dur; f_cur = f; t += dur
        t += (r.choice((2, 3, 4)) * BEAT) if groove else (1.2 + 2.3 * r.random()) / activity
PH = {"Bb_enter": [("D5", 5, "s"), ("C5", 3, ""), ("Bb4", 3, ""), ("G4", 3, ""), (None, 2, "")],
      "chant":    [("D4", 7, "sgE4"), ("A4", 4, ""), ("G4", 2, ""), ("F4", 3, ""), ("D4", 11, "v")],
      "Amen":     [("D4", 8, "s"), ("F#4", 3, "v")],
      "C_lead":   [("E4", 4, "s"), ("G4", 3, ""), ("E4", 2, ""), ("D4", 5, "v"), (None, 2, "")]}
melody(bar_t(-80) + 0.9, PH["Bb_enter"], amp=0.17)               # the duduk enters as the helix lifts (Bb)
improv(17.0, 60.3, 405 + 997 * SEED, amp=0.2)                                 # the tour and the writing: it travels with the harp through Dm, Am, Em, Bm, D
melody(bar_t(-52) + 1.2, PH["chant"], amp=0.17, vib=1.1)         # the prayer: a chant on Dm
melody(bar_t(-44) + 0.1, PH["Amen"], amp=0.18)                   # the Amen: D major
improv(82.6, 96.0, 1475 + 997 * SEED, amp=0.15, activity=0.6)                 # the numerals: sparse, under the equations
melody(bar_t(-32) + 0.2, PH["C_lead"], amp=0.16)                 # Shirakatsi's last chord: C, leading into the build
improv(106.6, 110.4, 2026 + 997 * SEED, amp=0.14, activity=0.7)               # the embedding space
improv(bar_t(-24.5), bar_t(-1.3), 128 + 997 * SEED, amp=0.17, groove=True)    # the modern half: the duduk over the dhol, on the beat grid

# ------------------------------------------------------------------ the graph acts and the groove (the modern half), on the 128 BPM grid pinned to the finale
def gate(spec, bf):
    """spec = [(from bar, to bar, gain) or (from, to, gain at start, gain at end)]: a layer's level at bar position bf (0 when it is not playing)"""
    for e in spec:
        if e[0] <= bf < e[1]: return e[2] if len(e) == 3 else e[2] + (e[3] - e[2]) * (bf - e[0]) / (e[1] - e[0])
    return 0.0
G_HEART = [(-29, -25, 1.0)]
G_HAT8 = [(-25, -1, 0.35, 0.6), (0, 2, 0.3), (2, 10, 0.6), (10, 18, 0.7)]
G_HAT16 = [(-13, -1, 0.35, 0.5), (4, 9, 0.5), (10, 16, 0.7)]
G_OHAT = [(-15, -1, 0.5, 0.75), (2, 9, 0.8), (10, 18, 0.9)]
G_HALF = [(-22, -17, 0.55, 0.8), (0, 2, 0.5)]
G_FLOOR = [(-17, -1, 0.6, 0.9), (2, 9, 0.95), (10, 16, 1.0), (16, 18, 0.7)]
G_CLAP = [(-19, -1, 0.4, 0.65), (2, 9, 0.8), (10, 16, 0.9), (16, 18, 0.55)]
G_BASS = [(-17, -1, 0.5, 0.85), (2, 9, 1.0), (10, 18, 1.0)]
G_DHOL = [(-15, -1, 0.45, 0.7), (2, 9, 0.8), (10, 16, 0.95), (16, 18, 0.5)]
G_ARP8 = [(-25, -19, 0.45, 0.6), (0, 2, 0.6), (16, 20, 0.55)]            # eighth-note arpeggio
G_ARP16 = [(-19, -1, 0.5, 0.85), (2, 10, 0.9), (10, 16, 1.0)]            # sixteenth-note arpeggio
G_STAB = [(-8, -1, 0.4, 0.6), (2, 9, 0.8), (10, 16, 1.0)]
G_SAWPAD = [(-10, -1, 0.4, 0.65), (2, 9, 0.8), (10, 18, 1.0)]
ARP_PAT = [[0, 2, 4, 2, 1, 3, 5, 3, 0, 2, 4, 2, 1, 3, 5, 3], [0, 3, 2, 3, 1, 4, 2, 4, 0, 3, 2, 3, 1, 5, 3, 5], [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 5, 4, 3, 2]]
vr = random.Random(31 * SEED + 7); BARPAT = {}                       # SEED > 0: a pattern chosen per bar, a few dropped notes, fills before every eighth bar, bass octave jumps
ARP_ACC = [1.0, 0.45, 0.5, 0.6, 0.45, 0.5, 1.0, 0.45, 0.5, 0.6, 0.45, 0.5, 1.0, 0.45, 0.8, 0.5]      # the accents fall on the tresillo, steps 0, 6, 12: the kanun dances in the dhol's 3 + 3 + 2
HSTEP = {round((h[0] - FIN0) / S16) for h in HARM}                                 # the steps at which a chord begins
def bass_root(ch):
    f = D3 * PCR[CH[ch]["root"]] / 2
    while f < 57: f *= 2
    while f > 118: f /= 2
    return f
si0 = int(math.ceil((T_GROOVE - FIN0) / S16)); si1 = int((FIN1 + 0.3 - FIN0) / S16)
for si in range(si0, si1):
    t = FIN0 + si * S16; bf = si / 16.0; sb = si % 16; b = si // 16; ch = chord_at(t); tn = TONES[ch]
    # -- drums
    gk = gate(G_FLOOR, bf) if sb % 4 == 0 else 0.0
    if gk == 0.0 and sb % 8 == 0: gk = gate(G_HALF, bf)
    if gk > 0: put(KICK, t, "kick", gain=0.9 * gk); KICKS.append(t)
    if sb == 0 and gate(G_HEART, bf) > 0: put(KICK, t, "kick", gain=0.35); KICKS.append(t)
    gc = gate(G_CLAP, bf)
    if gc > 0 and sb in (4, 12): put(CLAP, t, "perc", pan=0.05, room=0.2, gain=0.4 * gc)
    gh = gate(G_HAT8, bf)
    if gh > 0 and sb % 2 == 0 and sb % 4 != 2: put(HAT, t, "perc", pan=-0.2, room=0.04, gain=0.16 * gh * (1.0 if sb % 8 == 0 else 0.75))
    go = gate(G_OHAT, bf)
    if go > 0 and sb % 4 == 2: put(OHAT, t, "perc", pan=0.25, room=0.1, gain=0.2 * go)
    g16 = gate(G_HAT16, bf)
    if g16 > 0 and sb % 2 == 1: put(HAT, t, "perc", pan=0.3 if sb % 4 == 1 else -0.3, room=0.04, gain=0.1 * g16)
    gd = gate(G_DHOL, bf)
    if gd > 0 and sb % 2 == 0:                                                           # the dhol in 3 + 3 + 2: dum on the eighths 0, 3, 6; tek on 2, 5, 7
        e8 = sb // 2
        if e8 in (0, 3, 6): put(DUM, t, "perc", pan=-0.15, room=0.12, gain=0.38 * gd)
        elif e8 in (2, 5, 7): put(TEK, t, "perc", pan=0.2, room=0.14, gain=0.27 * gd)
    # -- bass: the root of the chord on the off-beat eighths
    gb = gate(G_BASS, bf)
    if gb > 0 and sb % 4 == 2:
        root = bass_root(ch) * (2.0 if ((sb == 14 and bf >= 10 and b % 2 == 1) or (SEED and sb == 10 and vr.random() < 0.22)) else 1.0)
        put(bassnote(root, S16 * 3.0), t, "bass", gain=0.5 * gb); LOG(t, root, "bass")
    # -- the arpeggio: a short kanun pluck through the chord's tones
    g8, g16a = gate(G_ARP8, bf), gate(G_ARP16, bf); ga = g16a if g16a > 0 else (g8 if sb % 2 == 0 else 0.0)
    if ga > 0:
        if SEED: pat = ARP_PAT[BARPAT.setdefault(b, vr.choice((0, 0, 1, 2)))]
        else: pat = ARP_PAT[1 if b % 4 == 3 else 0]
        f = tn[pat[sb]]
        if not (SEED and sb % 4 and vr.random() < 0.06): put(kanun(f, 0.42, tau=0.32, bright=1.35, click=0.10), t, "arp", pan=0.32 * math.sin(si * 0.9), send=0.12, room=0.1, gain=0.2 * ga * ARP_ACC[sb]); LOG(t, f, "arp")
    if SEED and gd > 0 and b % 8 == 7 and sb >= 12: put(TEK, t, "perc", pan=0.2, room=0.14, gain=0.2 * (0.6 + 0.12 * (sb - 12)))      # a fill into every eighth bar
    # -- chord stabs on the tresillo (the 3 + 3 + 2 of the dhol): steps 0, 6, 12
    gs = gate(G_STAB, bf)
    if gs > 0 and sb in (0, 6, 12):
        for k, ix in enumerate((0, 1, 2, 3)):
            f = tn[ix]; put(supersaw(f, S16 * 2.2, cutoff=2300.0), t, "saw", pan=(k - 1.5) * 0.3, room=0.14, send=0.1, gain=0.13 * gs); LOG(t, f, "stab")
    # -- held saw pad, once per chord
    gp = gate(G_SAWPAD, bf)
    if gp > 0 and si in HSTEP:
        t1 = chord_end(t)
        for k, nm in enumerate(CH[ch]["pad"]):
            f = hz(nm) * 2; put(supersaw(f, t1 - t, cutoff=1500.0, att=0.3, rel=0.6), t, "saw", pan=(k - 1) * 0.45, send=0.4, gain=0.05 * gp); LOG(t, f, "sawpad")

# ---- the sonification of the graph acts, locked to the grid and in key
for q in range(0, 26):                                                                  # web: a sparkle in glass over the 630 chords
    tt = q16(rstart("web") + 0.2 + q * 0.2345); pluck_k(7 + (q * 5) % 8, tt, amp=0.05, dur=0.7, pan=((q * 7) % 11 - 5) / 6, tau=0.7)
MSG = D["MSG"]
for l in range(6):                                                                      # msg: each message-passing round strikes its three strongest letters, rolled
    tt0 = q16(ra("msg", T_["TB2"] + 1.5 * l)); top = sorted(range(N), key=lambda i: -MSG[l][i])[:3]
    for j, i in enumerate(top): pluck(i, tt0 + 0.03 * j, amp=0.1 * (0.5 + MSG[l][i]), dur=1.0, glass_amp=0.4)
FI = D["FIED"]; pos = sorted(range(N), key=lambda i: -FI[i])[:3]; neg = sorted(range(N), key=lambda i: FI[i])[:3]
t_sp = rstart("spectral")                                                               # spectral: the two sides of the Fiedler cut, a held note each, left and right
def to_tone(f, ch): return min(ladder(CH[ch]["tones"], 140.0, 2100.0), key=lambda g: abs(math.log(g / f)))
for lst, pan in ((pos, 0.5), (neg, -0.5)):
    for i in lst: put(padnote(to_tone(lf(i, t_sp, 5), chord_at(t_sp)), rdur("spectral") + 0.2, 0.6, 0.8), t_sp - 0.2, "pad", pan=pan, send=0.45, gain=0.05); LOG(t_sp, to_tone(lf(i, t_sp, 5), chord_at(t_sp)), "pad")
top3 = [i for _, i in D["PRtop"]]
for k in range(15):                                                                     # pagerank: the three highest-ranked letters, ever louder
    tt = q16(ra("pagerank", T_["TP"] + 6.0 / 14 * k))
    for j, i in enumerate(top3): pluck(i, tt + 0.02 * j, amp=0.03 + 0.07 * k / 14, dur=0.8, glass_amp=0.0, tau=0.9)
dan = rdur("anneal"); t_an = rstart("anneal")                                           # anneal: a cluster that starts wide and settles to a unison (the temperature falling)
for ix, pn in ((0, -0.2), (2, 0.2), (3, 0.0)):
    f = TONES[chord_at(t_an + 0.1)][ix]; n = int(dan * SR); tt = np.arange(n) / SR; y = np.zeros(n); u = tt / dan
    for kk in range(5):
        spread = 26 * (1 - u) ** 2 * (kk - 2) / 2; ph = 2 * math.pi * np.cumsum(f * 2.0 ** (spread / 1200)) / SR
        y += np.arcsin(np.sin(ph)) * 2 / math.pi
    y = lp(y / 5, 2200) * np.minimum(1.0, tt / 0.6) * np.minimum(1.0, (dan - tt) / 0.6)
    put(norm(y), t_an, "pad", pan=pn, send=0.4, gain=0.06); LOG(t_an, f, "pad")
GD = D["GD"]; lossv = np.array([w[0] ** 2 + 3 * w[1] ** 2 + .6 * w[0] * w[1] for w in GD]); t_de = rstart("descent")   # descent: the loss, as a falling line down the ladder
for q in range(0, 16):
    u = q / 15.0; lo = float(np.interp(u * 47, np.arange(48), lossv)); k = int(round(13 * math.sqrt(max(lo, 0) / lossv.max())))
    pluck_k(k, q16(t_de + 0.1 + q * 0.2345), amp=0.075, dur=0.8, pan=-0.2, tau=0.9)
Wm = D["A"]["mean"]
import random
wrng = random.Random(35); seqs = []
for i in range(N):
    sq = [i]
    for h in range(16):
        r_ = wrng.random(); n_ = sq[-1]; acc = 0.0; m = 0
        for m in range(N):
            acc += Wm[n_][m]
            if r_ <= acc: break
        sq.append(min(N - 1, m))
    seqs.append(sq)
for vi, w_ in enumerate((3, 14, 29)):                                                   # walk: three walkers on the attention graph, a note per hop
    for k in range(16): pluck(seqs[w_][k], q16(ra("walk", T_["TD2"] + k / 1.7)) + 0.012 * vi, amp=0.08, dur=0.9, shift=(-5, 0, 5)[vi], glass_amp=0.0, tau=0.9)
val = np.array([D["PR"][14][i] / D["PRmax"] for i in range(N)]); val = np.interp(np.linspace(0, N, 720, endpoint=False), np.arange(N + 1), np.append(val, val[0]))
sp_ = np.fft.rfft(val - val.mean()) / len(val); mags = np.abs(sp_[1:20]); phs = np.angle(sp_[1:20]); mags = mags / mags.max()
t_fo = rstart("fourier"); dfo = rdur("fourier"); n = int((dfo + 0.8) * SR); tt = np.arange(n) / SR; y = np.zeros(n)
for j, h in enumerate((1, 2, 3, 4, 6, 8, 12, 16)):                                      # fourier: a tone of D whose partials (only 3-limit ones: D and A) arrive one by one, each with its own phase
    on = 0.1 + dfo * 0.75 * j / 7; y += mags[min(j, 18)] * (h ** -0.4) * np.sin(2 * math.pi * D3 * h * tt + phs[j]) * (0.5 + 0.5 * np.tanh((tt - on) / 0.25))
put(norm(y * np.minimum(1.0, tt / 0.4) * np.minimum(1.0, (n / SR - tt) / 0.5)), t_fo, "pad", send=0.4, gain=0.07); LOG(t_fo, D3, "pedal")
for q in range(18):                                                                     # poincare: a strum across the disk
    pluck_k(4 + (q * 3) % 11, q16(rstart("poincare") + 0.2 + q * 0.117), amp=0.05, dur=1.2, pan=(q - 9) / 11, glass_amp=0.3)
KM = D["KM"]; t_sv = rstart("svd")
for it in range(7):                                                                     # svd + k-means: at each iteration the four centroids sound, as a rolled chord on the ladder
    ts = q16(ra("svd", T_["TSV"] + 3 + it))
    if ts < rstart("collapse"):
        for k in range(4):
            mem = [i for i in range(N) if KM[it]["assign"][i] == k]; kk = int(round(np.mean([kdeg(i) for i in mem]))) if mem else 4
            pluck_k(kk, ts + 0.04 * k, amp=0.07, dur=1.0, pan=(k - 1.5) / 2.5, glass_amp=0.35)

# ---- risers, rolls, impacts at the joints of the arrangement
gliss(bar_t(9.3), ("D", "G", "A", "C"), 220.0, 1800.0, 30, 0.04, 0.08)                   # into the drop: the harp sweeps up D, G, A, C (no third: it fits the minor chord it crosses and the major chord it lands on)
put(riser(5 * BAR), bar_t(-5), "fx", send=0.3, gain=0.22)
put(snare_roll(2 * BAR), bar_t(-2), "fx", send=0.15, gain=0.3)
put(impact(2.6), FIN0, "fx", send=0.4, gain=1.2); put(riser(2 * BAR, 400, 7000), FIN0, "fx", send=0.3, gain=0.15)
put(impact(1.8), bar_t(2), "fx", send=0.35, gain=0.6)
put(riser(3.2 * BAR, 300, 9000), bar_t(6.8), "fx", send=0.3, gain=0.22); put(snare_roll(1.0 * BAR), bar_t(9), "fx", send=0.15, gain=0.34)
put(impact(3.2), bar_t(10), "fx", send=0.45, gain=1.4); put(CLAP, bar_t(10), "perc", room=0.3, gain=0.4)
put(impact(2.0), bar_t(16), "fx", send=0.4, gain=0.4)
put(impact(4.2), FIN1 - 0.3, "fx", send=0.5, gain=1.0)

# ------------------------------------------------------------------ the finale's melody: the six letters of Mashtots are the hook, F# D B | E C G  (D | C, then G | C)
HOOK = [("F#5", 1), ("D5", 1), ("B4", 2), ("E5", 1), ("C5", 1), ("G4", 2)]
SEMI_UP = [1, 2, 1, 2, 2, 2]                                                   # the upper neighbour in the key: F#-G, E-F#
for rep, b0 in enumerate((10, 12, 14)):
    t = bar_t(b0)
    for k, (nm, beats) in enumerate(HOOK):
        f = hz(nm) * (2.0 if (rep == 2 and k == 5) else 1.0)
        put(duduk(f, beats * BEAT * 0.97, vib=1.0, seed=rep * 10 + k + 100 * SEED, f_from=(hz(HOOK[k - 1][0]) if k in (1, 4) else None), grace=(f * 2 ** (SEMI_UP[k] / 12) if (SEED and rep > 0 and k in (0, 3)) else None)), t, "duduk", pan=0.08, send=0.3, gain=0.36); LOG(t, f, "hook", beats * BEAT)
        put(kanun(f * 2, beats * BEAT * 1.2, tau=0.9, bright=1.3), t, "harp", pan=-0.25, send=0.3, gain=0.2); LOG(t, f * 2, "hook", beats * BEAT)
        put(supersaw(f, beats * BEAT * 0.95, cutoff=1700.0, att=0.02, rel=0.15), t, "saw", pan=0.0, room=0.12, send=0.1, gain=0.07)      # a soft saw under the reed
        t += beats * BEAT
for (b0, nm, beats) in ((2, "D5", 7), (4, "C5", 7), (6, "E5", 7), (8, "A4", 7.5)):   # long notes before the drop, each on a tone of its chord
    put(duduk(hz(nm), beats * BEAT, vib=1.15, scoop=True, seed=b0), bar_t(b0) + 0.05, "duduk", pan=0.1, send=0.4, gain=0.2); LOG(bar_t(b0), hz(nm), "duduk", beats * BEAT)
for (b0, nm, beats, fl) in ((16, "D5", 3, ""), (16.75, "B4", 1, ""), (17, "G4", 4, "v"), (18, "D5", 8, "v")):
    put(duduk(hz(nm), beats * BEAT, vib=1.3 if fl else 1.0, seed=int(b0 * 7), scoop=(b0 == 18)), bar_t(b0), "duduk", pan=0.1, send=0.4, gain=0.2); LOG(bar_t(b0), hz(nm), "duduk", beats * BEAT)
for i in range(N): pluck(i, bar_t(16) + 0.2 + i * 0.05, amp=0.05, dur=1.2, glass_amp=0.0)   # the harp wash as the organisation completes

# ------------------------------------------------------------------ return and colophon: the letters fall home (a falling cascade in D), then open fifths and a last duduk D
for i in range(N):
    tt = ra("return", T_["T2"] + (N - 1 - i) * stagger); pluck_row(i, tt, amp=0.08, dur=1.6, glass_amp=0.3, kind="cascade", limit=False)      # the letters fall home through the keys, B minor to D minor
for nm in ("D3", "A3", "D4"):
    f = hz(nm); put(padnote(f, COL1 - COL0 + 1.0, 1.8, 2.5), COL0 + 0.3, "pad", send=0.5, gain=0.07); LOG(COL0 + 0.3, f, "pad")
put(duduk(hz("D4"), 4.5, vib=0.8, seed=1475, rel=1.4), COL0 + 1.3, "duduk", pan=0.1, send=0.45, gain=0.17); LOG(COL0 + 1.3, hz("D4"), "duduk", 4.5)
put(duduk(hz("D3"), 5.0, vib=0.6, seed=2026, rel=2.2), CYC - 8.0, "duduk", pan=0.1, send=0.45, gain=0.15); LOG(CYC - 8.0, hz("D3"), "duduk", 5.0)

print("scored in %.0f s: %d kicks, %d logged notes" % (time.time() - T_START, len(KICKS), len(NOTELOG)))

# ------------------------------------------------------------------ audit: every pitched event against the harmony table
def audit():
    """every pitched event against the harmony table. The stone's own runs (the opening cascade, the landing, the return) are exempt: they sweep through four keys on purpose.
    harp / hook: the chord's pentatonic and colour tone; tour letters and glissandi: the key's scale; duduk: a long note (a second or more) a tone of the chord or its pentatonic, a passing note any note of the key (or the leading tone);
    pads, stabs, saw pads, arpeggios and rolled chords: only the triad; the bass: its root; the pedal tone (D3 with D and A partials): D or A"""
    bad = []
    for t, f, kind, dur in NOTELOG:
        if kind == "cascade" or t > CYC + 1: continue
        ch = chord_at(t + 0.001); c = CH[ch]; scale = set(KEYS[key_at(t + 0.001)]); chordset = set(c["pent"]) | set(c["tones"]) | set(c["ext"]); pc = pc_of(f)
        if kind in ("harp", "hook"): allowed = chordset
        elif kind in ("row", "gliss"): allowed = scale | chordset
        elif kind == "duduk": allowed = chordset if dur >= 1.0 else (scale | chordset | {"C#"})
        elif kind == "bass": allowed = {c["root"]}
        elif kind == "pedal": allowed = {"D", "A"}
        else: allowed = set(c["tones"])
        if pc not in allowed: bad.append((round(t, 2), ch, key_at(t + 0.001), kind, pc, round(f, 1), round(dur, 2)))
    print("audit: %d pitched events, %d outside the harmony table" % (len(NOTELOG), len(bad)))
    for x in bad[:40]: print("   ", x)
    json.dump([[h[0], h[1], h[2], sorted(set(CH[h[2]]["pent"]) | set(CH[h[2]]["tones"]), key=lambda p: PCN[p])] for h in HARM], open("scratch/harmony.json", "w"))
audit()
def presence(kind_prefix, windows):
    """how much of each stretch has the duduk / the harp sounding (a number you can compare with v3)"""
    rows = []
    for nm, a, b in windows:
        cov = np.zeros(int((b - a) * 20) + 1, dtype=bool)
        for t, f, k, d in NOTELOG:
            if k in kind_prefix and t < b and t + max(d, 0.3) > a: cov[max(0, int((t - a) * 20)):int((min(t + max(d, 0.3), b) - a) * 20) + 1] = True
        rows.append("%s %2.0f%%" % (nm, 100 * cov.mean()))
    return ", ".join(rows)
_W = [("tour+writing", 11.15, 63.7), ("prayer", 63.7, 80.7), ("numbers+shira", 80.7, 102.7), ("build", FIN0 - 47.5, FIN0), ("finale", FIN0, FIN1)]
print("duduk sounding:", presence(("duduk", "hook"), _W)); print("harp sounding:", presence(("harp", "row", "cascade", "gliss", "arp", "hook"), _W))

# ------------------------------------------------------------------ mix, reverb, master
duck_env = np.zeros(NS, dtype=F32); kk = int(0.4 * SR); ker = np.exp(-np.arange(kk) / SR / 0.12).astype(F32)
for tk in KICKS:
    i0 = int(tk * SR)
    if i0 + kk < NS: duck_env[i0:i0 + kk] = np.maximum(duck_env[i0:i0 + kk], ker)
def make_ir(rt60, hf, pre, seed):
    r = np.random.default_rng(seed); n = int(rt60 * 1.15 * SR); t = np.arange(n) / SR; ir = r.normal(size=n) * np.exp(-6.9 * t / rt60)
    ir = lp(ir, hf) * np.minimum(1, t / 0.015); ir[:int(pre * SR)] *= 0.0; return ir / math.sqrt(float(np.sum(ir ** 2)))
IRS = {"W": (make_ir(3.1, 4800, 0.016, 1), make_ir(3.1, 4800, 0.022, 2)), "M": (make_ir(0.5, 6500, 0.004, 3), make_ir(0.5, 6500, 0.007, 4))}
def reverb(x, which): return fftconvolve(x, IRS[which][0])[:NS].astype(F32), fftconvolve(x, IRS[which][1])[:NS].astype(F32)

DIAG = bool(os.environ.get("DIAG"))
def diag(nm, dry, d):
    """DIAG=1: the loudness of each stem (as weighted into the mix) in each section, and its spectral centroid, so the balance can be judged by number"""
    from analyze_score import SECTIONS
    if d is not None: dry = dry * d[:CYC_N, None]
    row = []
    for _, a, b in SECTIONS:
        seg_ = dry[int(a * SR):int(b * SR)]
        row.append("%5.0f" % st.integrated_lufs(seg_) if len(seg_) > SR and np.abs(seg_).max() > 1e-5 else "    -")
    from scipy.signal import welch
    fr, sp = welch(dry.mean(axis=1), SR, nperseg=16384)
    print("  %-6s %s | centroid %5.0f Hz" % (nm, " ".join(row), float((sp * fr).sum() / max(sp.sum(), 1e-12))))
TARGET = {"drone": -37, "pad": -38, "harp": -25.5, "arp": -32, "duduk": -25, "kick": -30, "bass": -31.5, "perc": -31, "saw": -38, "fx": -32, "plate": -31}   # stem loudness (LUFS, gated) before the master
RET_W, RET_M = 0.9, 0.9
STEM_EQ = {"harp": (2500.0, 4.0), "arp": (3000.0, 4.0), "duduk": (2200.0, 3.0), "pad": (3000.0, 2.0), "perc": (5000.0, -1.0), "plate": (3000.0, 3.0)}      # (high-shelf corner Hz, dB): the plucks and the reed need their top
def eq(nm, a):
    if nm not in STEM_EQ or a is None: return a
    f0, g = STEM_EQ[nm]; b, aa = st.high_shelf(SR, f0, g); return lfilter(b, aa, a).astype(F32)
def cfilt(x, b=None, a=None, sos=None, pre=2 * SR):
    """filter a loop without a start-up click: prime the filter with the end of the loop (the music is circular)"""
    xe = np.concatenate([x[-pre:], x], axis=0)
    return (sosfilt(sos, xe, axis=0) if sos is not None else lfilter(b, a, xe, axis=0))[pre:].astype(F32)
def master_eq(x):
    """a gentle clean-up: a little out of the boxy 380 Hz, a little up above 3 kHz"""
    for b, a in (st.peaking(SR, 380.0, -2.5, 0.9), st.high_shelf(SR, 3200.0, 3.0)): x = cfilt(x, b, a)
    return x
def level(x, pts, max_db=4.0, smooth=3.0):
    """ride the master gently (3 s windows, at most +-max_db, smoothed) so that the short-term loudness follows a section-level plan: quiet ancient half, a building groove, the drop, a quiet return"""
    l, t = st.short_term(x, SR, win=3.0, hop=0.5); want = np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    g = uniform_filter1d(np.clip(want - l, -max_db, max_db), size=max(1, int(smooth / 0.5)), mode="nearest")
    return x * np.interp(np.arange(len(x)) / SR, t, 10 ** (g / 20.0)).astype(F32)[:, None]
PLAN = [(0, -25), (3, -23.5), (10, -21), (52, -20.5), (63, -21.5), (66, -22.5), (80, -22.5), (82, -21), (103, -21), (111, -20.5), (117, -19.5), (126, -18), (150, -17), (157, -17), (158.3, -19), (162, -16.5), (177, -16), (177.8, -14.5), (188, -14.5), (190, -17), (196, -19), (204.25, -22)]
def mix(names, use_duck, tag):
    outL, outR, W, M = Z(), Z(), Z(), Z(); report = []
    for nm in names:
        s = STEMS[nm]
        if s.L is None: continue
        sL = s.L; sR = s.L if s.mono else s.R; dry = np.stack([sL[:CYC_N], sR[:CYC_N]], 1)
        lu = st.integrated_lufs(dry) if np.abs(dry).max() > 1e-6 else -70.0
        w = 10 ** ((TARGET[nm] - lu) / 20.0) if lu > -69 else 0.0; report.append("%s %.1f->%.1f" % (nm, lu, TARGET[nm]))
        d = (1.0 - STEM_CFG[nm][0] * duck_env) if use_duck else 1.0
        eL = eq(nm, sL); eR = eL if s.mono else eq(nm, sR); outL += eL * d * w; outR += eR * d * w
        if s.W is not None: W += eq(nm, s.W) * d * w
        if s.M is not None: M += s.M * d * w
        if DIAG: diag(nm, dry * np.float32(w), d if use_duck else None)
    print(tag, "stem loudness:", ", ".join(report))
    wl, wr = reverb(W, "W"); ml, mr = reverb(M, "M")
    L = outL + RET_W * wl + RET_M * ml; R = outR + RET_W * wr + RET_M * mr
    nT = int(TAIL * SR)                                                                  # the reverb tail of the end of the loop sounds again at its start
    fl = L[:CYC_N].copy(); fr = R[:CYC_N].copy(); fl[:nT] += L[CYC_N:CYC_N + nT]; fr[:nT] += R[CYC_N:CYC_N + nT]
    x = np.stack([fl, fr], 1)
    x = cfilt(x, sos=butter(2, 30 / (SR / 2), "high", output="sos"))                                              # nothing below 30 Hz
    return x
def limiter(x, ceil, look=0.005, rel=0.15):
    blk = int(SR * 0.001); nb = len(x) // blk
    env = np.abs(x[:nb * blk]).max(axis=1).reshape(nb, blk).max(axis=1); g = np.minimum(1.0, ceil / np.maximum(env, 1e-9)); w = max(1, int(look / 0.001))
    g = minimum_filter1d(g, size=2 * w + 1, mode="nearest"); a = 1 - math.exp(-0.001 / rel); gs = np.empty_like(g); cur = 1.0
    for i in range(nb): cur = min(g[i], cur + (1 - cur) * a); gs[i] = cur
    gs = uniform_filter1d(gs, size=w, mode="nearest"); gain = np.interp(np.arange(len(x)) / blk - 0.5, np.arange(nb), gs).astype(F32)
    return x * gain[:, None]
def master(x, target_lufs, tag):
    x = level(level(master_eq(x), PLAN), PLAN, max_db=2.0)
    il = st.integrated_lufs(x); x = x * F32(10 ** ((target_lufs - il) / 20.0)); x = limiter(x, 0.89)                    # 0.89 = -1 dBFS
    il2 = st.integrated_lufs(x); x = x * F32(10 ** ((target_lufs - il2) / 20.0)); x = limiter(x, 0.89)
    n_ = int(0.012 * SR); ramp = (0.5 - 0.5 * np.cos(np.pi * np.arange(n_) / n_)).astype(F32)[:, None]; x[:n_] *= ramp; x[-n_:] *= ramp[::-1]      # the loop seam is quiet; a 12 ms fade makes it click-proof (the mp3 pads its last frame)
    pk = float(np.abs(x).max()); print("%s: %.1f LUFS integrated (was %.1f), peak %.3f (%.2f dBFS), true peak %.2f dBFS" % (tag, st.integrated_lufs(x), il, pk, 20 * math.log10(pk), st.true_peak_db(x)))
    return x
OUT = os.environ.get("OUT", ".")                                                  # OUT=scratch/stage renders beside, not over, the files the page is playing
def export(x, name):
    name = os.path.join(OUT, name)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(name + ".wav", "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", name + ".wav", "-codec:a", "libmp3lame", "-b:a", "192k", name + ".mp3"], check=True)
    os.remove(name + ".wav"); print("wrote %s.mp3 (%.2f s)" % (name, len(x) / SR))

full = master(mix(["drone", "pad", "harp", "arp", "duduk", "kick", "bass", "perc", "saw", "fx", "plate"], True, "full"), -17.0, "full")
export(full, "landing_score" + TAG); del full
harp = master(mix(["drone", "pad", "harp", "arp", "duduk", "plate"], False, "harp"), -18.0, "harp")
export(harp, "landing_score_harp" + TAG)
print("total %.0f s" % (time.time() - T_START))
