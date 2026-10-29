"""Measuring tools for the score: loudness (ITU-R BS.1770 K-weighting, gated), sensory roughness (Sethares), and a pitch-class fit against the harmony table.
Used by make_music.py (to set the master level) and analyze_score.py (to compare scores). Nothing here makes a sound; it only measures one."""
import math, subprocess
import numpy as np
from scipy.signal import lfilter


def read_audio(path, sr=44100):
    """decode any audio file to float32 (n, 2) with ffmpeg"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(np.float32)


def _kweight_coeffs(fs):
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533          # stage 1: the head-related high shelf
    A = 10 ** (G / 40); w0 = 2 * math.pi * fc / fs; al = math.sin(w0) / (2 * Q); cw = math.cos(w0); sA = math.sqrt(A)
    b = np.array([A * ((A + 1) + (A - 1) * cw + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - 2 * sA * al)])
    a = np.array([(A + 1) - (A - 1) * cw + 2 * sA * al, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - 2 * sA * al])
    f2, Q2 = 38.13547087613982, 0.5003270373253953                                  # stage 2: the RLB high-pass
    w2 = 2 * math.pi * f2 / fs; a2 = math.sin(w2) / (2 * Q2); c2 = math.cos(w2)
    b2 = np.array([(1 + c2) / 2, -(1 + c2), (1 + c2) / 2]); aa2 = np.array([1 + a2, -2 * c2, 1 - a2])
    return (b / a[0], a / a[0]), (b2 / aa2[0], aa2 / aa2[0])


def kweighted(x, fs=44100):
    (b1, a1), (b2, a2) = _kweight_coeffs(fs)
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)


def block_loudness(x, fs=44100, win=0.4, hop=0.1):
    """mean-square loudness (LUFS) of overlapping blocks of a (n, ch) signal"""
    y = kweighted(x.astype(np.float64), fs); n = int(win * fs); h = int(hop * fs)
    cs = np.concatenate([np.zeros((1, y.shape[1])), np.cumsum(y * y, axis=0)])
    starts = np.arange(0, len(y) - n, h)
    ms = (cs[starts + n] - cs[starts]) / n
    return -0.691 + 10 * np.log10(np.maximum(ms.sum(axis=1), 1e-12)), starts / fs


def integrated_lufs(x, fs=44100):
    l, _ = block_loudness(x, fs)
    g = l[l > -70]
    if len(g) == 0: return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(10 ** ((g + 0.691) / 10))) - 10
    g2 = l[l > rel]
    return float(-0.691 + 10 * np.log10(np.mean(10 ** ((g2 + 0.691) / 10))))


def short_term(x, fs=44100, win=3.0, hop=1.0):
    l, t = block_loudness(x, fs, win=win, hop=hop)
    return l, t + win / 2


def true_peak_db(x):
    """sample peak in dBFS (4x oversampled estimate, enough to see inter-sample overs)"""
    from scipy.signal import resample_poly
    m = 0.0
    for c in range(x.shape[1]): m = max(m, float(np.abs(resample_poly(x[:, c], 4, 1)).max()))
    return 20 * math.log10(max(m, 1e-9))


def roughness_series(x, fs=44100, win=8192, hop=None, fmin=90.0, fmax=5000.0, npk=28):
    """Sethares sensory dissonance of the strongest spectral peaks per frame, normalised by the peaks' own power (0 = smooth, higher = rougher)"""
    hop = hop or fs // 2; w = np.hanning(win); fr = np.fft.rfftfreq(win, 1 / fs); sel = (fr >= fmin) & (fr <= fmax); frs = fr[sel]
    mono = x.mean(axis=1) if x.ndim == 2 else x; out = []; ts = []
    for s in range(0, len(mono) - win, hop):
        sp = np.abs(np.fft.rfft(mono[s:s + win] * w))[sel]
        pk = np.where((sp[1:-1] > sp[:-2]) & (sp[1:-1] >= sp[2:]))[0] + 1
        if len(pk) < 2: out.append(0.0); ts.append((s + win / 2) / fs); continue
        top = pk[np.argsort(sp[pk])[::-1][:npk]]; f = frs[top]; a = sp[top] / sp[top].max()
        F1, F2 = np.meshgrid(f, f, indexing="ij"); A1, A2 = np.meshgrid(a, a, indexing="ij")
        fmn = np.minimum(F1, F2); d = np.abs(F1 - F2); s_ = 0.24 / (0.0207 * fmn + 18.96)
        dis = A1 * A2 * (np.exp(-3.5 * s_ * d) - np.exp(-5.75 * s_ * d))
        out.append(float(np.triu(dis, 1).sum() / max((a ** 2).sum(), 1e-9))); ts.append((s + win / 2) / fs)
    return np.array(out), np.array(ts)


def pitch_class_energy(x, fs, t0, t1, d_hz, win=16384):
    """energy per pitch class (12 bins, 0 = D, step = semitone) in x[t0:t1], from a Hann-windowed FFT; pitches are measured against d_hz = the D of the tuning"""
    seg = x[int(t0 * fs):int(t1 * fs)]
    seg = seg.mean(axis=1) if seg.ndim == 2 else seg
    if len(seg) < 2048: return np.zeros(12)
    acc = np.zeros(12); nfr = max(1, (len(seg) - win) // (win // 2) + 1) if len(seg) > win else 1
    for k in range(nfr):
        s = seg[k * (win // 2):k * (win // 2) + win]
        if len(s) < win: s = np.pad(s, (0, win - len(s)))
        sp = np.abs(np.fft.rfft(s * np.hanning(win))) ** 2; fr = np.fft.rfftfreq(win, 1 / fs)
        ok = (fr >= 110) & (fr <= 2000)
        cents = 1200 * np.log2(fr[ok] / d_hz); pcf = (cents % 1200) / 100.0
        nearest = np.round(pcf).astype(int) % 12; dev = np.abs(pcf - np.round(pcf))
        w = np.where(dev < 0.35, 1.0, 0.0)                                           # keep only bins within 35 cents of a semitone
        np.add.at(acc, nearest, sp[ok] * w)
    return acc / max(acc.sum(), 1e-12)


def high_shelf(fs, f0, gain_db, Q=0.7071):
    """RBJ high-shelf biquad: +gain_db above about f0"""
    A = 10 ** (gain_db / 40); w0 = 2 * math.pi * f0 / fs; al = math.sin(w0) / (2 * Q); cw = math.cos(w0); sA = math.sqrt(A)
    b = np.array([A * ((A + 1) + (A - 1) * cw + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - 2 * sA * al)])
    a = np.array([(A + 1) - (A - 1) * cw + 2 * sA * al, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - 2 * sA * al])
    return b / a[0], a / a[0]


def peaking(fs, f0, gain_db, Q=1.0):
    """RBJ peaking-EQ biquad"""
    A = 10 ** (gain_db / 40); w0 = 2 * math.pi * f0 / fs; al = math.sin(w0) / (2 * Q); cw = math.cos(w0)
    b = np.array([1 + al * A, -2 * cw, 1 - al * A]); a = np.array([1 + al / A, -2 * cw, 1 - al / A])
    return b / a[0], a / a[0]
