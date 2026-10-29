#!/usr/bin/env python3
"""A zoomed spectrogram of part of a score, with the Pythagorean pitch grid drawn in (so a note can be read off the picture): python3 view_spec.py FILE T0 T1 [FMAX] -> scratch/view_<T0>_<T1>.png"""
import sys, json, math
import numpy as np
import score_tools as st
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.signal import spectrogram
path, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]); fmax = float(sys.argv[4]) if len(sys.argv) > 4 else 2500.0
x = st.read_audio(path); fs = 44100; seg = x[int(t0 * fs):int(t1 * fs)].mean(axis=1)
f, t, S = spectrogram(seg, fs, nperseg=8192, noverlap=8192 - 1024); S = 10 * np.log10(S + 1e-14); sel = (f >= 100) & (f <= fmax)
fig, ax = plt.subplots(figsize=(18, 7)); ax.pcolormesh(t + t0, f[sel], S[sel], vmin=S[sel].max() - 60, vmax=S[sel].max(), cmap="magma", shading="auto"); ax.set_yscale("log")
PCR = {"D": 1.0, "E": 9/8, "F": 32/27, "F#": 81/64, "G": 4/3, "A": 3/2, "Bb": 128/81, "B": 27/16, "C": 16/9}
D3 = 293.665 / 2
for o in range(0, 7):
    for pc, r in PCR.items():
        fr = D3 * r * 2 ** (o - 0) * 1.0 / (2 ** 0)
        fr = D3 * r * 2 ** o
        if 100 <= fr <= fmax:
            ax.axhline(fr, color="w" if pc in ("D", "A") else "c", lw=0.4, alpha=0.5 if pc in ("D", "A") else 0.3); ax.text(t0 + 0.02 * (t1 - t0), fr, pc, color="w", fontsize=7, va="center")
try:
    for a, b, c, pcs in json.load(open("scratch/harmony.json")):
        if t0 <= a < t1: ax.axvline(a, color="lime", lw=1.0); ax.text(a, fmax * 0.93, c, color="lime", fontsize=10)
except Exception: pass
ax.set_ylim(100, fmax); fig.tight_layout(); out = "scratch/view_%d_%d.png" % (t0, t1); fig.savefig(out, dpi=70); print(out)
