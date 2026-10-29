#!/usr/bin/env python3
"""Measure a score file (or several, to compare): loudness by section, roughness, spectral balance, clicks; writes scratch/analysis_<name>.png.
usage: python3 analyze_score.py landing_score.mp3 [other.mp3 ...]"""
import json, math, os, sys
import numpy as np
import score_tools as st

TL = json.load(open("scratch/timeline_real.json", encoding="utf-8"))
FIN0, BAR = TL["FIN0"], TL["bar"]
SECTIONS = [("stone+helix", 0, 11.15), ("tour", 11.15, 51.95), ("writing", 51.95, 63.7), ("prayer", 63.7, 80.7), ("numbers", 80.7, 92.7), ("shirakatsi", 92.7, 102.7), ("space", 102.7, 110.77),
            ("graph build", 110.77, FIN0 - 0.001), ("finale 0-10", FIN0, FIN0 + 10 * BAR), ("drop 10-16", FIN0 + 10 * BAR, FIN0 + 16 * BAR), ("outro 16-20", FIN0 + 16 * BAR, FIN0 + 20 * BAR), ("return", FIN0 + 20 * BAR, TL["cycle"])]
BANDS = [("sub<90", 20, 90), ("bass 90-250", 90, 250), ("low-mid 250-800", 250, 800), ("mid 0.8-2.5k", 800, 2500), ("presence 2.5-6k", 2500, 6000), ("air>6k", 6000, 16000)]


def band_shares(seg, fs):
    mono = seg.mean(axis=1); n = 1 << int(math.floor(math.log2(min(len(mono), 1 << 17))))
    sp = np.zeros(n // 2 + 1)
    for s in range(0, len(mono) - n + 1, n): sp += np.abs(np.fft.rfft(mono[s:s + n] * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1 / fs); tot = sp[(fr >= 20) & (fr <= 16000)].sum()
    return [sp[(fr >= a) & (fr < b)].sum() / max(tot, 1e-12) for _, a, b in BANDS]


def click_count(x, fs):
    """transients that are not note onsets are hard to tell apart; this counts frames where the high band (> 6 kHz) jumps by > 12 dB over the previous 5 ms and the low band does not (a click, not a hat or a pluck onset)"""
    from scipy.signal import butter, sosfilt
    mono = x.mean(axis=1); hi = sosfilt(butter(4, 6000 / (fs / 2), "high", output="sos"), mono)
    blk = int(0.005 * fs); nb = len(hi) // blk
    e = np.sqrt((hi[:nb * blk].reshape(nb, blk) ** 2).mean(axis=1) + 1e-12)
    jump = 20 * np.log10(e[1:] / np.maximum(e[:-1], 1e-9))
    return int(np.sum((jump > 12) & (e[1:] > 10 ** (-60 / 20))))


def report(path):
    x = st.read_audio(path); fs = 44100; name = os.path.splitext(os.path.basename(path))[0]
    il = st.integrated_lufs(x, fs); tp = st.true_peak_db(x)
    print("\n=== %s: %.2f s, integrated %.1f LUFS, true peak %.2f dBFS, %d clicks (5 ms jumps in the high band)" % (name, len(x) / fs, il, tp, click_count(x, fs)))
    rough, rt = st.roughness_series(x, fs)
    print("%-14s %7s %7s %7s | %s | rough" % ("section", "LUFS", "max3s", "crest", " ".join("%-9s" % b[0][:9] for b in BANDS)))
    stl, stt = st.short_term(x, fs)
    for nm, a, b in SECTIONS:
        seg = x[int(a * fs):int(b * fs)]
        if len(seg) < fs: continue
        l, _ = st.block_loudness(seg, fs, win=min(3.0, len(seg) / fs * 0.9), hop=0.5)
        mono = seg.mean(axis=1); crest = 20 * math.log10(np.abs(seg).max() / max(math.sqrt(np.mean(seg ** 2)), 1e-9))
        sh = band_shares(seg, fs); r = rough[(rt >= a) & (rt < b)]
        print("%-14s %7.1f %7.1f %6.1fdB | %s | %.3f" % (nm, st.integrated_lufs(seg, fs) if len(seg) > 2 * fs else l.mean(), l.max(), crest, " ".join("%8.0f%%" % (100 * s) for s in sh), r.mean() if len(r) else 0))
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        from scipy.signal import spectrogram
        fig, ax = plt.subplots(3, 1, figsize=(16, 9), sharex=True, gridspec_kw=dict(height_ratios=[3, 1, 1]))
        f, t, S = spectrogram(x.mean(axis=1), fs, nperseg=4096, noverlap=3072); S = 10 * np.log10(S + 1e-12); sel = (f > 40) & (f < 8000)
        ax[0].pcolormesh(t, f[sel], S[sel], vmin=S[sel].max() - 70, vmax=S[sel].max(), shading="auto", cmap="magma"); ax[0].set_yscale("log"); ax[0].set_ylabel("Hz")
        ax[1].plot(stt, stl, "k"); ax[1].set_ylabel("short-term LUFS"); ax[2].plot(rt, rough, "r"); ax[2].set_ylabel("roughness")
        for _, a, _b in SECTIONS:
            for k in range(3): ax[k].axvline(a, color="w" if k == 0 else "gray", lw=0.6, alpha=0.6)
        ax[2].set_xlabel("s"); fig.tight_layout(); out = "scratch/analysis_%s.png" % name; fig.savefig(out, dpi=80); print("plot ->", out)
    except Exception as e: print("plot skipped:", e)


if __name__ == "__main__":
    for p in sys.argv[1:] or ["landing_score.mp3"]: report(p)
