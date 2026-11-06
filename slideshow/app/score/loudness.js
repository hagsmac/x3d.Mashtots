// loudness.js: ITU-R BS.1770 loudness (K-weighting, 400 ms blocks, absolute -70 and relative -10 LU gates) and a few spectral measures, ported from make_music's score_tools.py.
// Used only by the calibration and measurement page (index.html); nothing here makes a sound.
function kCoefs(fs) {
  const G = 3.999843853973347, Q = 0.7071752369554196, fc = 1681.974450955533, A = 10 ** (G / 40), w0 = 2 * Math.PI * fc / fs, al = Math.sin(w0) / (2 * Q), cw = Math.cos(w0), sA = Math.sqrt(A);
  const b = [A * ((A + 1) + (A - 1) * cw + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - 2 * sA * al)], a = [(A + 1) - (A - 1) * cw + 2 * sA * al, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - 2 * sA * al];
  const f2 = 38.13547087613982, Q2 = 0.5003270373253953, w2 = 2 * Math.PI * f2 / fs, a2 = Math.sin(w2) / (2 * Q2), c2 = Math.cos(w2);
  const b2 = [(1 + c2) / 2, -(1 + c2), (1 + c2) / 2], aa2 = [1 + a2, -2 * c2, 1 - a2];
  return [[b.map(x => x / a[0]), a.map(x => x / a[0])], [b2.map(x => x / aa2[0]), aa2.map(x => x / aa2[0])]];
}
function biquad(x, b, a) { const y = new Float64Array(x.length); let x1 = 0, x2 = 0, y1 = 0, y2 = 0; for (let i = 0; i < x.length; i++) { const v = x[i], o = b[0] * v + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2; x2 = x1; x1 = v; y2 = y1; y1 = o; y[i] = o; } return y; }
export function kweight(x, fs) { const [[b1, a1], [b2, a2]] = kCoefs(fs); return biquad(biquad(x, b1, a1), b2, a2); }
export function blockLoudness(chs, fs, win = 0.4, hop = 0.1) {                 // chs: array of Float32Array (one per channel); returns { l: LUFS per block, t: block start seconds }
  const n = Math.round(win * fs), h = Math.round(hop * fs), cs = chs.map(c => { const y = kweight(c, fs), s = new Float64Array(y.length + 1); for (let i = 0; i < y.length; i++) s[i + 1] = s[i] + y[i] * y[i]; return s; });
  const len = chs[0].length, l = [], t = []; for (let s = 0; s < len - n; s += h) { let ms = 0; for (const c of cs) ms += (c[s + n] - c[s]) / n; l.push(-0.691 + 10 * Math.log10(Math.max(ms, 1e-12))); t.push(s / fs); }
  return { l, t };
}
export function integratedLufs(chs, fs) {
  const { l } = blockLoudness(chs, fs), g = l.filter(v => v > -70); if (!g.length) return -70;
  const rel = -0.691 + 10 * Math.log10(g.reduce((s, v) => s + 10 ** ((v + 0.691) / 10), 0) / g.length) - 10, g2 = l.filter(v => v > rel);
  return g2.length ? -0.691 + 10 * Math.log10(g2.reduce((s, v) => s + 10 ** ((v + 0.691) / 10), 0) / g2.length) : -70;
}
export function shortTerm(chs, fs, win = 3.0, hop = 0.5) { const { l, t } = blockLoudness(chs, fs, win, hop); return { l, t: t.map(x => x + win / 2) }; }
export const chans = b => Array.from({ length: b.numberOfChannels }, (_, c) => b.getChannelData(c));
export function peakDb(chs) { let m = 0; for (const c of chs) for (let i = 0; i < c.length; i++) { const v = Math.abs(c[i]); if (v > m) m = v; } return 20 * Math.log10(Math.max(m, 1e-9)); }
export function peakLin(chs) { let m = 0; for (const c of chs) for (let i = 0; i < c.length; i++) { const v = Math.abs(c[i]); if (v > m) m = v; } return m; }
export const interp1 = (x, xs, ys) => { if (x <= xs[0]) return ys[0]; for (let i = 1; i < xs.length; i++) if (x <= xs[i]) return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / Math.max(1e-9, xs[i] - xs[i - 1]); return ys[ys.length - 1]; };
export function uniform(a, size) { const n = a.length, out = new Array(n), h = size >> 1; for (let i = 0; i < n; i++) { let s = 0, c = 0; for (let j = i - h; j <= i + (size - 1 - h); j++) { const k = Math.min(n - 1, Math.max(0, j)); s += a[k]; c++; } out[i] = s / c; } return out; }
export function pearson(a, b) { const n = Math.min(a.length, b.length); let ma = 0, mb = 0; for (let i = 0; i < n; i++) { ma += a[i]; mb += b[i]; } ma /= n; mb /= n; let sab = 0, saa = 0, sbb = 0; for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; } return sab / Math.sqrt(saa * sbb); }
// spectral centroid and band energies of a stretch of a mono mix (Hann windows of 4096, hop 2048, radix-2 FFT)
function fft(re, im) { const n = re.length; for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
  for (let len = 2; len <= n; len <<= 1) { const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang); for (let i = 0; i < n; i += len) { let cr = 1, ci = 0; for (let k = 0; k < len / 2; k++) { const a = i + k, b = i + k + len / 2, tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr; re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti; const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr; } } } }
export function spectrum(chs, fs, t0, t1) {
  const N = 4096, w = new Float64Array(N).map((_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N)), bands = [0, 0, 0, 0], edges = [0, 250, 1000, 4000, 1e9]; let num = 0, den = 0;
  const m = chs.length, a = Math.max(0, Math.floor(t0 * fs)), b = Math.min(chs[0].length - N, Math.floor(t1 * fs));
  for (let s = a; s < b; s += 2048) { const re = new Float64Array(N), im = new Float64Array(N); for (let i = 0; i < N; i++) { let v = 0; for (const c of chs) v += c[s + i]; re[i] = v / m * w[i]; } fft(re, im);
    for (let k = 1; k < N / 2; k++) { const f = k * fs / N, p = re[k] * re[k] + im[k] * im[k]; num += f * p; den += p; for (let q = 0; q < 4; q++) if (f >= edges[q] && f < edges[q + 1]) bands[q] += p; } }
  const tot = bands.reduce((x, y) => x + y, 1e-30); return { centroid: den > 0 ? num / den : 0, bands: bands.map(x => 10 * Math.log10(x / tot + 1e-12)) };
}
