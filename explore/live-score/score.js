// score.js: the Landing's score (v4/v5), LIVE in WebAudio, re-anchored to any timeline (the approved one or a re-timed preset).
// Nothing here is new music: the harmony table, the stone's ladder, the voices' recipes, the improviser and the groove's gates are make_music.py's,
// exported by export_score_data.py. What is new is that the events are COMPUTED FROM THE TIMELINE at run time:
//   * a letter, an act entry or a key change before the groove sits at an ACT time (it follows the picture whatever the speed ramps do);
//   * a chord inside a hold sits at a FRACTION of the hold;
//   * the groove sits on the 128 BPM bar grid counted from the finale's first beat; the build (two bars a chord, F C Dm Bb ...) is regenerated
//     for however many bars the graph acts now take, and its gates (hats, kick, dhol, bass, arpeggio) are stretched to fit.
// Voices: plucked ones (kanun, glass, struck plate, sand) are additive buffers computed with the Python formulas and cached; sustained ones
// (duduk, dam, pads, bass, drums) are native oscillators and filters, so a whole loop renders far faster than real time (measured in index.html).
// Simplified against the mp3 (say so when comparing): no tour styles (duet, taksim, dhol dance, pulse), no saw stabs or saw pad, no risers,
// one reverb, no BS.1770 stem balancing (one global calibration instead), the composed duduk anchors (entrance, prayer, Amen, hook) left out.

// ------------------------------------------------------------------ timelines (the same maths as timeline_retimed.py)
export class Timeline {
  constructor(segs, cycle) { this.segs = segs; this.cycle = cycle; }
  seg(tr) { for (const s of this.segs) if (tr < s.r0 + s.dur || s === this.segs[this.segs.length - 1]) return s; }
  act(tr) { const s = this.seg(tr), tau = tr - s.r0; return s.a0 + tau * (s.rate + 0.5 * (s.rate_end - s.rate) * tau / Math.max(s.dur, 1e-9)); }
  span(name) { const p = this.segs.filter(s => s.name === name); return p.length ? [p[0].r0, p[p.length - 1].r0 + p[p.length - 1].dur] : null; }
  realOfAct(a, name) {                                        // first real time at which act time reaches a (runs only; inside segment `name` if given)
    for (const s of this.segs) {
      if (!(s.rate > 0 || s.rate_end > 0)) continue;
      if (name && s.name.replace(/2$/, "") !== name) continue;
      if (a < s.a0 - 1e-9 || a > s.a1 + 1e-9) continue;
      const k = (s.rate_end - s.rate) / s.dur, da = a - s.a0;
      return s.r0 + (Math.abs(k) < 1e-12 ? da / s.rate : (-s.rate + Math.sqrt(Math.max(0, s.rate * s.rate + 2 * k * da))) / k);
    }
    return name ? this.realOfAct(a) : null;
  }
}

// ------------------------------------------------------------------ pitch: Pythagorean tuning on D (A4 = 440.5 Hz, D4 = 293.665)
export const D4 = 293.665, D3 = D4 / 2;
const PCN = { D: 0, Eb: 1, E: 2, F: 3, "F#": 4, G: 5, "G#": 6, A: 7, Bb: 8, B: 9, C: 10, "C#": 11 };
export function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

export function buildScore(data, tl, seed = 0) {
  const PCR = data.PCR, CH = data.CH, KEYS = data.KEYS, A = data.act, BAR = data.BAR, BEAT = BAR / 4, S16 = BEAT / 4;
  const hz = nm => { const pc = nm.slice(0, -1), o = +nm.slice(-1), od = o - (pc === "C" || pc === "C#" ? 1 : 0); return D3 * PCR[pc] * 2 ** (od - 3); };
  const ladder = (pcs, lo, hi) => { const out = []; for (let o = 0; o < 9; o++) for (const pc of pcs) { const f = D3 * PCR[pc] * 2 ** (o - 3); if (f >= lo && f <= hi) out.push(f); } return out.sort((a, b) => a - b); };
  const pcOf = f => { const c = ((1200 * Math.log2(f / D3)) % 1200 + 1200) % 1200; let best = null, bd = 1e9; for (const [pc, n] of Object.entries(PCN)) { const d = Math.abs(((c - 100 * n) + 600 + 1200) % 1200 - 600); if (d < bd) { bd = d; best = pc; } } return best; };
  const fin0 = tl.span("finale")[0], fin1 = tl.span("finale")[1];
  const barT = b => fin0 + b * BAR;
  // ---- the groove: where it starts, how many bars the build has now ----
  const sp = tl.span("space");
  const g0 = Math.ceil((sp[0] + 1.0 - fin0) / BAR);                                     // approved: -29
  const stretch = -g0 / data.GROOVE_BARS;                                                // build gates scale with the build
  const gateBar = b => b < 0 ? Math.round(b * stretch) : b;
  const gate = (spec, bf) => { for (const e of spec) { const a = gateBar(e[0]), b = gateBar(e[1]); if (bf >= a && bf < b) return e.length === 3 ? e[2] : e[2] + (e[3] - e[2]) * (bf - a) / (b - a); } return 0; };
  // ---- the harmony table, re-anchored ----
  const HARM = [];
  for (const h of data.harm) {
    const at = h.at; let t;
    if (at.kind === "bar") { if (at.bar < 0) continue; t = barT(at.bar); }                  // the build is regenerated below; the finale keeps its bars
    else if (at.kind === "act") t = tl.realOfAct(at.act, at.seg);
    else { const s = tl.span(at.seg); t = s[0] + at.frac * (s[1] - s[0]); }
    HARM.push({ t0: t, chord: h.chord, key: h.key });
  }
  const firstEven = Math.ceil((g0 + 1) / 2) * 2;
  for (let b = firstEven; b < 0; b += 2) HARM.push({ t0: barT(b), chord: data.LOOP[(((b / 2) % 4) + 4) % 4], key: "Dm" });
  HARM.sort((a, b) => a.t0 - b.t0);
  for (let i = 0; i < HARM.length; i++) HARM[i].t1 = i + 1 < HARM.length ? HARM[i + 1].t0 : tl.cycle + 30;
  const hidx = t => { let lo = 0, hi = HARM.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (HARM[m].t0 <= t) lo = m; else hi = m - 1; } return lo; };
  const chordAt = t => HARM[hidx(t)].chord, keyAt = t => HARM[hidx(t)].key, chordEnd = t => HARM[hidx(t)].t1;
  const safe = t => { const c = CH[chordAt(t + 0.001)]; return new Set([...c.pent, ...c.tones, ...c.ext]); };
  const TONES = {}; for (const c in CH) { const cand = []; for (let o = 0; o < 9; o++) for (const pc of CH[c].tones) cand.push([D3 * PCR[pc] * 2 ** (o - 3), pc]); cand.sort((a, b) => a[0] - b[0]); const i0 = cand.findIndex(([f, pc]) => f >= 190 && pc === CH[c].root); TONES[c] = cand.slice(i0, i0 + 8).map(x => x[0]); }
  const SCALE = {}; for (const k in KEYS) SCALE[k] = ladder(KEYS[k], 270, 900);
  const PENT = {}; for (const c in CH) PENT[c] = ladder(CH[c].pent, 140, 2100);
  const fold = x => { while (x >= 2) x /= 2; while (x < 1) x *= 2; return x; };
  const lfRow = i => { const r = Math.floor(i / 9); return D4 * data.LADDER[i % 9] * fold(1.5 ** r) * (r === 0 ? 0.5 : 1); };
  const kdeg = i => i % 9 + 2 * Math.floor(i / 9);
  const lf = (i, t, shift = 0) => { const lad = PENT[chordAt(t)]; return lad[Math.max(0, Math.min(lad.length - 1, kdeg(i) + shift))]; };
  const hdur = (t0, base, ring = 0.6) => Math.max(0.5, Math.min(base, chordEnd(t0 + 0.001) + ring - t0));
  const lowAmp = f => Math.min(1, (f / 330) ** 0.6);
  const ev = [], LOG = (t, f, kind, dur = 0) => log.push({ t, f, kind, dur }), log = [];
  const q16 = t => fin0 + Math.round((t - fin0) / S16) * S16;
  const rnd = mulberry32(405 + 7919 * seed);
  const pluckRow = (i, t, amp, dur, glassAmp, kind, limit = true) => { const f = lfRow(i), d = limit ? hdur(t, dur, 0.9) : dur, pan = (i % 9 - 4) / 5.5; amp *= lowAmp(f);
    ev.push({ t, v: "kanun", f, dur: d, amp, pan, send: 0.32 }); LOG(t, f, kind, d); if (glassAmp) ev.push({ t, v: "glass", f: f * 2, dur: d * 0.7, amp: amp * glassAmp, pan: -pan, send: 0.5 }); };
  const pluck = (i, t, amp = 0.16, dur = 2.2, shift = 0, glassAmp = 0.3) => { const f = lf(i, t, shift), d = hdur(t, dur), pan = (kdeg(i) - 7) / 9; amp *= lowAmp(f);
    ev.push({ t, v: "kanun", f, dur: d, amp, pan, send: 0.32 }); LOG(t, f, "harp"); if (glassAmp) ev.push({ t, v: "glass", f: f * 2, dur: d * 0.7, amp: amp * glassAmp, pan: -pan, send: 0.5 }); };
  const flourish = (t, ch, amp = 0.06) => TONES[ch].slice(0, 7).forEach((f, j) => { ev.push({ t: t + j * 0.055, v: "kanun", f, dur: 1.5, amp: amp * lowAmp(f), pan: -0.5 + j / 6, send: 0.35, tau: 1.0 }); LOG(t + j * 0.055, f, "arp", 1.5); });
  const gliss = (t, key, lo, hi, n, dt, amp) => { const lad = ladder(data.KEYS[key], lo, hi); for (let j = 0; j < n; j++) { const f = lad[Math.round(j * (lad.length - 1) / (n - 1))], u = j / (n - 1);
    ev.push({ t: t + j * dt, v: "kanun", f, dur: 1.3, amp: amp * (0.55 + 0.45 * u) * lowAmp(f), pan: -0.7 + 1.4 * u, send: 0.35, tau: 0.8 }); LOG(t + j * dt, f, "gliss"); } };

  // ---- the stone wakes: four rising runs as the 36 letters leave, softly again as they land (exempt from the audit: they sweep four keys on purpose)
  data.letters.forEach((p, i) => { pluckRow(i, tl.realOfAct(p.t0, "flight"), 0.10, 2.2, 0.25, "cascade", false); pluckRow(i, tl.realOfAct(Math.min(p.t0 + data.flight, A.T1), "flight") ?? tl.realOfAct(p.t0 + data.flight), 0.05, 1.4, 0, "cascade", false); });
  gliss(tl.span("lift")[0] + 0.05, "Dm", 146, 1250, 22, 0.06, 0.05);
  // ---- the tour: one note per spotlit letter on the stone's own pitch; a rolled chord marks each key; the struck plate and its sand
  for (let k = 0; k < 36; k++) {
    const tk = tl.realOfAct(A.TT + k * data.pace, "tour"); pluckRow(k, tk, 0.15, 2.4, 0.3, "row");
    const n = k % 9 + 1, m = Math.floor(k / 9) + 1, fk = lfRow(k);
    ev.push({ t: tk, v: "plate", f: fk, nm: n + m, amp: 0.17 * Math.min(1, (fk / 330) ** 0.5), pan: -(k % 9 - 4) / 5.5, send: 0.5 });
    for (const pn of [-0.7, 0.7]) ev.push({ t: tk + 0.03, v: "sand", n: 5 * (n + m), seed: 1000 * seed + 2 * k + (pn > 0), amp: 0.11, pan: pn, send: 0.2 });
    if (k % 9 === 0 && k > 0) flourish(tk + 0.05, ["Am", "Em", "Bm"][k / 9 - 1]);
  }
  // ---- the writing: a glissando in D major into the sentence; the prayer and the numerals sound in
  gliss(tl.span("write")[0], "DM", 146, 1300, 24, 0.05, 0.05);
  for (const [nm, i] of [["prayer", 15], ["numerals", 14]]) { const s = tl.span(nm); if (s) pluck(i, s[0] + 0.02, 0.12); }
  // ---- act entries: the letter that sounds each act in (on the 16th grid once the groove has started)
  for (const [segn, [key, i]] of Object.entries(data.ENTRY)) { let t = tl.realOfAct(A[key], segn); if (t == null) continue; t += 0.02; if (t >= barT(g0)) t = q16(t); pluck(i, t, 0.12, 1.6); }
  // ---- the letters fall home: the runs in reverse (exempt)
  data.letters.forEach((p, i) => pluckRow(i, tl.realOfAct(p.r0, "return") ?? tl.realOfAct(p.r0), 0.08, 1.8, 0.2, "cascade", false));
  // ---- pads: one chord at a time (the chord's own voicing), long attacks
  for (const h of HARM) { if (h.t0 > tl.cycle) break; const b = (h.t0 - fin0) / BAR, g = b < -52 * stretch ? 1 : b < g0 ? 0.8 : 0.55;
    CH[h.chord].pad.forEach((nm, k) => { const f = hz(nm); ev.push({ t: h.t0 - 0.2, v: "pad", f, dur: h.t1 - h.t0 + 0.2, amp: 0.06 * g, pan: (k - 1) * 0.35, send: 0.5 }); LOG(h.t0, f, "pad"); }); }
  // ---- the duduk: the deck's phrasing, made to listen (make_music.improv)
  const improv = (t0, t1, groove, start, amp = 0.2) => {
    let t = t0, fcur = hz(start);
    const q8 = x => { const h = BEAT / 2; return fin0 + Math.round((x - fin0) / h) * h; };
    const choice = a => a[Math.floor(rnd() * a.length)];
    while (t < t1 - 1.5) {
      if (groove) t = q8(t);
      const n = 3 + Math.floor(rnd() * 4); let prev = null, prevEnd = -9;
      for (let k = 0; k < n; k++) {
        if (t >= t1 - 1.0) break;
        const lad = SCALE[keyAt(t)]; let i0 = 0; lad.forEach((g, j) => { if (Math.abs(Math.log(g / fcur)) < Math.abs(Math.log(lad[i0] / fcur))) i0 = j; });
        const u = rnd(); let step = u < .3 ? -1 : u < .6 ? 1 : u < .72 ? -2 : u < .84 ? 2 : u < .92 ? 0 : (rnd() < .5 ? -3 : 3);
        if (lad[i0] >= hz("D5") && step > 0) step = -step; if (lad[i0] <= hz("E4") && step < 0) step = -step;
        const i1 = Math.max(0, Math.min(lad.length - 1, i0 + step)), last = k === n - 1;
        let dur = groove ? (last ? choice([4, 6]) : choice([1.5, 2, 3, 4])) * BEAT : last ? 2.4 + 1.8 * rnd() : choice([0.7, 0.9, 1.2, 1.6, 2.2]);
        let f = lad[i1]; const sp = safe(t);
        if ((dur >= 1 || last) && !sp.has(pcOf(f))) f = lad.filter(g => sp.has(pcOf(g))).reduce((a, g) => Math.abs(Math.log(g / f)) < Math.abs(Math.log(a / f)) ? g : a);
        if (last && rnd() < 0.7) { const tp = new Set(CH[chordAt(t + 0.001)].tones), near = lad.filter(g => tp.has(pcOf(g)) && Math.abs(Math.log(g / f)) < 0.22); if (near.length) f = near.reduce((a, g) => Math.abs(Math.log(g / f)) < Math.abs(Math.log(a / f)) ? g : a); }
        const tb = chordEnd(t + 0.001); if (t + dur > tb - 0.05 && !safe(tb + 0.01).has(pcOf(f))) dur = Math.max(0.45, tb - 0.12 - t);
        const j = lad.indexOf(f), up = j >= 0 && j + 1 < lad.length ? lad[j + 1] : null;
        const grace = up && dur >= 0.9 && rnd() < 0.35 ? up : null, mord = up && !grace && dur >= 1.2 && rnd() < 0.12 ? up : null;
        ev.push({ t, v: "duduk", f, dur, from: prev && t - prevEnd < 0.06 ? prev : null, scoop: k === 0 && rnd() < 0.3, grace, mord, vib: (0.9 + 0.5 * rnd()) * (dur >= 1.6 ? 1.3 : 1), amp: amp * (0.85 + 0.15 * rnd()), pan: 0.12, send: 0.38 });
        LOG(t, f, "duduk", dur); prev = f; prevEnd = t + dur; fcur = f; t += dur;
      }
      t += groove ? choice([2, 3, 4]) * BEAT : (1.2 + 2.3 * rnd());
    }
  };
  improv(tl.span("tour")[0] + 6, barT(g0), false, ["A4", "D5", "F4"][seed % 3]);
  improv(fin0 + 2 * BAR, fin1 - BAR, true, "A4", 0.18);
  // ---- the groove: every 16th from the build's first bar to the end of the finale
  const bassRoot = ch => { let f = D3 * PCR[CH[ch].root] / 2; while (f < 57) f *= 2; while (f > 118) f /= 2; return f; };
  const ACC = [1.0, 0.45, 0.5, 0.6, 0.45, 0.5, 1.0, 0.45, 0.5, 0.6, 0.45, 0.5, 1.0, 0.45, 0.8, 0.5];
  const PAT = [[0, 2, 4, 2, 1, 3, 5, 3, 0, 2, 4, 2, 1, 3, 5, 3], [0, 3, 2, 3, 1, 4, 2, 4, 0, 3, 2, 3, 1, 5, 3, 5]];
  const G = data.GATES;
  for (let si = g0 * 16; si < Math.round((fin1 - fin0) / S16); si++) {
    const t = fin0 + si * S16, bf = si / 16, sb = ((si % 16) + 16) % 16, b = Math.floor(si / 16), ch = chordAt(t), tn = TONES[ch];
    let gk = sb % 4 === 0 ? gate(G.floor, bf) : 0; if (gk === 0 && sb % 8 === 0) gk = gate(G.half, bf);
    if (gk > 0) ev.push({ t, v: "kick", amp: 0.9 * gk });
    if (sb === 0 && gate(G.heart, bf) > 0) ev.push({ t, v: "kick", amp: 0.35 });
    const gc = gate(G.clap, bf); if (gc > 0 && (sb === 4 || sb === 12)) ev.push({ t, v: "clap", amp: 0.4 * gc, pan: 0.05 });
    const gh = gate(G.hat8, bf); if (gh > 0 && sb % 2 === 0 && sb % 4 !== 2) ev.push({ t, v: "hat", amp: 0.16 * gh * (sb % 8 === 0 ? 1 : 0.75), pan: -0.2 });
    const go = gate(G.ohat, bf); if (go > 0 && sb % 4 === 2) ev.push({ t, v: "ohat", amp: 0.2 * go, pan: 0.25 });
    const g16 = gate(G.hat16, bf); if (g16 > 0 && sb % 2 === 1) ev.push({ t, v: "hat", amp: 0.1 * g16, pan: sb % 4 === 1 ? 0.3 : -0.3 });
    const gd = gate(G.dhol, bf); if (gd > 0 && sb % 2 === 0) { const e8 = sb / 2; if ([0, 3, 6].includes(e8)) ev.push({ t, v: "dum", amp: 0.38 * gd, pan: -0.15 }); else if ([2, 5, 7].includes(e8)) ev.push({ t, v: "tek", amp: 0.27 * gd, pan: 0.2 }); }
    const gb = gate(G.bass, bf); if (gb > 0 && sb % 4 === 2) { const f = bassRoot(ch) * (sb === 14 && bf >= 10 && b % 2 === 1 ? 2 : 1); ev.push({ t, v: "bass", f, dur: S16 * 3, amp: 0.5 * gb }); LOG(t, f, "bass"); }
    const g8 = gate(G.arp8, bf), g16a = gate(G.arp16, bf), ga = g16a > 0 ? g16a : (sb % 2 === 0 ? g8 : 0);
    if (ga > 0) { const f = tn[PAT[b % 4 === 3 ? 1 : 0][sb]]; ev.push({ t, v: "kanun", f, dur: 0.42, tau: 0.32, bright: 1.35, click: 0.1, amp: 0.2 * ga * ACC[sb], pan: 0.32 * Math.sin(si * 0.9), send: 0.12 }); LOG(t, f, "arp"); }
  }
  ev.sort((a, b) => a.t - b.t);
  // ---- the audit: every pitched note against the chord sounding at its start (the stone's own runs and glissandi are exempt, as in make_music)
  // the same rules as make_music.audit(): harp: the chord's pentatonic and colour tone; tour rows and glissandi: also the key's scale; duduk: a long
  // note (1 s or more) the chord's set, a passing note any note of the key (or C#); bass: its root; pads and arpeggios: only the triad
  let outside = 0, checked = 0; const bad = [];
  for (const n of log) {
    if (n.kind === "cascade" || n.t > tl.cycle + 1) continue; checked++;
    const ch = chordAt(n.t + 0.001), c = CH[ch], scale = new Set(KEYS[keyAt(n.t + 0.001)]), set = new Set([...c.pent, ...c.tones, ...c.ext]), pc = pcOf(n.f);
    const allowed = n.kind === "harp" ? set : (n.kind === "row" || n.kind === "gliss") ? new Set([...scale, ...set]) : n.kind === "duduk" ? (n.dur >= 1.0 ? set : new Set([...scale, ...set, "C#"])) : n.kind === "bass" ? new Set([c.root]) : new Set(c.tones);
    if (!allowed.has(pc)) { outside++; if (bad.length < 8) bad.push(`${n.kind} ${n.f.toFixed(1)} Hz (${pc}) at ${n.t.toFixed(2)} s over ${ch}`); }
  }
  return { events: ev, harm: HARM, log, audit: { checked, outside, bad }, groove: { startBar: g0, buildBars: -g0, stretch }, fin0, fin1, cycle: tl.cycle };
}

// ------------------------------------------------------------------ voices
const cache = new Map();
function buf(ctx, key, n, fill) { if (cache.has(key) && cache.get(key).sampleRate === ctx.sampleRate) return cache.get(key); const b = ctx.createBuffer(1, n, ctx.sampleRate); fill(b.getChannelData(0), ctx.sampleRate); norm(b.getChannelData(0)); cache.set(key, b); return b; }
function norm(y) { let m = 0; for (const v of y) m = Math.max(m, Math.abs(v)); if (m > 0) for (let i = 0; i < y.length; i++) y[i] /= m; }
function addPartial(y, sr, f, amp, dec, ph, t0 = 0) {          // y += amp * exp(-t/dec) * sin(2 pi f t + ph), by complex rotation (fast, exact enough)
  const w = 2 * Math.PI * f / sr, r = Math.exp(-1 / (dec * sr)), cw = Math.cos(w) * r, sw = Math.sin(w) * r; let re = Math.cos(ph) * amp, im = Math.sin(ph) * amp;
  for (let i = Math.round(t0 * sr); i < y.length; i++) { y[i] += im; const nre = re * cw - im * sw; im = re * sw + im * cw; re = nre; }
}
function kanunBuf(ctx, f, dur, tau = 1.5, bright = 1, click = 0.22) {
  const k = `k${f.toFixed(2)}_${dur.toFixed(1)}_${tau}_${bright}_${click}`;
  return buf(ctx, k, Math.round((dur + 0.4) * ctx.sampleRate), (y, sr) => {
    for (let h = 1; h <= 14; h++) { const fh = f * h * Math.sqrt(1 + 0.0003 * h * h); if (fh > 9000 || fh > sr * 0.45) break; addPartial(y, sr, fh, 1 / h ** (1.15 / bright), tau / h ** 0.72, 0.4 * h); }
    norm(y); const r = mulberry32(Math.round(f * 100)); let lp = 0;
    for (let i = 0; i < Math.min(y.length, sr * 0.06); i++) { const x = r() * 2 - 1; lp += 0.5 * (x - lp); y[i] += (x - lp) * Math.exp(-i / sr / 0.012) * click; }   // the pick: a bright click
    for (let i = 0; i < y.length; i++) { const t = i / sr; y[i] *= Math.min(1, t / 0.004) * (t < dur ? 1 : Math.exp(-(t - dur) / 0.06)); }
    const fo = Math.round(0.03 * sr); for (let i = 0; i < fo; i++) y[y.length - fo + i] *= 0.5 + 0.5 * Math.cos(Math.PI * i / fo);
  });
}
function glassBuf(ctx, f, dur, tau = 0.8) {
  return buf(ctx, `g${f.toFixed(2)}_${dur.toFixed(1)}`, Math.round((dur + 0.4) * ctx.sampleRate), (y, sr) => {
    addPartial(y, sr, f, 1, tau, 0); addPartial(y, sr, f * 1.0022, 0.5, tau, 1.1); addPartial(y, sr, 2 * f, 0.26, tau * 0.7, 0.5); addPartial(y, sr, 3 * f, 0.09, tau * 0.5, 2);
    for (let i = 0; i < y.length; i++) { const t = i / sr; y[i] *= Math.min(1, t / 0.012) * (t < dur ? 1 : Math.exp(-(t - dur) / 0.08)); }
  });
}
function plateBuf(ctx, f, nm, dur = 1.6) {
  return buf(ctx, `p${f.toFixed(2)}_${nm}`, Math.round((dur + 0.4) * ctx.sampleRate), (y, sr) => {
    const det = 1 + 0.0009 * nm; addPartial(y, sr, f, 1, 1.2, 0); addPartial(y, sr, f * det, 0.6, 1.2, 1.0); addPartial(y, sr, 2 * f, 0.3, 0.9, 0.4); addPartial(y, sr, 4 * f * det, 0.14 * nm / 10, 0.6, 0);
    for (let i = 0; i < y.length; i++) { const t = i / sr; y[i] *= Math.min(1, t / 0.01) * (t < dur ? 1 : Math.exp(-(t - dur) / 0.08)); }
  });
}
function sandBuf(ctx, ngr, seed, dur = 1.3) {                   // grains of bright filtered noise falling over a second and thinning out
  return buf(ctx, `s${ngr}_${seed}`, Math.round(dur * ctx.sampleRate), (y, sr) => {
    const r = mulberry32(seed + 1);
    for (let g = 0; g < ngr; g++) { const u = r() ** 1.8 * (dur - 0.05), lo = 2200 * (6000 / 2200) ** r(), a = (0.35 + 0.65 * r()) * (1 - 0.6 * u / dur); addPartial(y, sr, lo * 1.25, a, 96 / 14 / sr * 1.0 + 0.0015, r() * 6.28, u); }
  });
}
let NOISE = null;
function noiseBuf(ctx) { if (!NOISE || NOISE.sampleRate !== ctx.sampleRate) { NOISE = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate); const y = NOISE.getChannelData(0), r = mulberry32(7); for (let i = 0; i < y.length; i++) y[i] = r() * 2 - 1; } return NOISE; }
const waves = new Map();
function reedWave(ctx, f, nmax = 18, top = 6000, roll = 4600) {   // the duduk's spectrum: odd-weighted harmonics under a nasal formant near 1.25 kHz
  const key = `${f.toFixed(1)}_${nmax}_${top}`; if (waves.has(key) && waves.get(key).ctx === ctx) return waves.get(key).w;
  const re = new Float32Array(nmax + 1), im = new Float32Array(nmax + 1);
  for (let h = 1; h <= nmax; h++) { const fh = f * h; if (fh > top) break; im[h] = h ** -0.95 * (1 + 0.6 * (h % 2)) * (0.3 + Math.exp(-(Math.log(fh / 1250) ** 2) / (2 * 0.8 ** 2))) / (1 + (fh / roll) ** 4); }
  const w = ctx.createPeriodicWave(re, im, { disableNormalization: false }); waves.set(key, { ctx, w }); return w;
}
function triWave(ctx) { const key = "tri"; if (waves.has(key) && waves.get(key).ctx === ctx) return waves.get(key).w; const re = new Float32Array(12), im = new Float32Array(12); for (const h of [1, 3, 5, 7, 9, 11]) im[h] = ((-1) ** ((h - 1) / 2)) / h ** 2; im[1] += 0.25; const w = ctx.createPeriodicWave(re, im); waves.set(key, { ctx, w }); return w; }

export class Voices {
  constructor(ctx, dest) {
    this.ctx = ctx; this.master = ctx.createGain(); this.master.gain.value = 0.78;      // measured: 0.9 peaked at -0.1 dBFS over a loop
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 3; comp.attack.value = 0.01; comp.release.value = 0.25;
    this.master.connect(comp); comp.connect(dest || ctx.destination);
    this.rev = ctx.createConvolver(); const n = Math.round(2.6 * ctx.sampleRate), ir = ctx.createBuffer(2, n, ctx.sampleRate);    // one hall: decaying noise, darker as it fades
    for (let c = 0; c < 2; c++) { const y = ir.getChannelData(c), r = mulberry32(11 + c); let lp = 0; for (let i = 0; i < n; i++) { const t = i / ctx.sampleRate, k = 0.15 + 0.85 * Math.exp(-t / 0.6); lp += k * ((r() * 2 - 1) - lp); y[i] = lp * Math.exp(-t / 0.75); } }
    this.rev.buffer = ir; this.revIn = ctx.createGain(); this.revIn.gain.value = 0.55; this.revIn.connect(this.rev); this.rev.connect(this.master);
    this.live = new Set();
  }
  out(pan = 0, send = 0) { const p = this.ctx.createStereoPanner(); p.pan.value = Math.max(-1, Math.min(1, pan)); p.connect(this.master); if (send) { const s = this.ctx.createGain(); s.gain.value = send; p.connect(s); s.connect(this.revIn); p._send = s; } return p; }
  // a finished voice is DISCONNECTED: otherwise every note's gain and panner stay in the graph and are processed on every block for the rest of the loop
  track(node, ...chain) { this.live.add(node); node.onended = () => { this.live.delete(node); for (const n of chain) { try { n.disconnect(); if (n._send) n._send.disconnect(); } catch (_) {} } }; return node; }
  stopAll(at) { for (const n of this.live) { try { n.stop(at); } catch (_) {} } this.live.clear(); }
  sample(b, at, amp, pan, send, rate = 1) { const s = this.ctx.createBufferSource(); s.buffer = b; s.playbackRate.value = rate; const g = this.ctx.createGain(); g.gain.value = amp; const p = this.out(pan, send); s.connect(g); g.connect(p); s.start(at); this.track(s, s, g, p); }
  play(e, at, k = 1) {                                          // k: real seconds per piece second (1 / speed)
    const c = this.ctx, d = (e.dur || 0) * k;
    switch (e.v) {
      case "kanun": return this.sample(kanunBuf(c, e.f, Math.max(0.3, Math.round(d * 10) / 10), e.tau || 1.5, e.bright || 1, e.click ?? 0.22), at, e.amp, e.pan, e.send);
      case "glass": return this.sample(glassBuf(c, e.f, Math.max(0.3, Math.round(d * 10) / 10)), at, e.amp, e.pan, e.send);
      case "plate": return this.sample(plateBuf(c, e.f, e.nm), at, e.amp, e.pan, e.send);
      case "sand": return this.sample(sandBuf(c, e.n, e.seed), at, e.amp, e.pan, e.send);
      case "duduk": return this.duduk(e, at, d);
      case "pad": return this.pad(e, at, d);
      case "bass": { const o = c.createOscillator(); o.type = "sawtooth"; o.frequency.value = e.f; const lp = c.createBiquadFilter(); lp.frequency.value = 380; const g = c.createGain(); g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(e.amp * 0.5, at + 0.006); g.gain.setTargetAtTime(0, at + d, 0.03); const p = this.out(0, 0); o.connect(lp); lp.connect(g); g.connect(p); o.start(at); o.stop(at + d + 0.3); return this.track(o, o, lp, g, p); }
      case "kick": { const o = c.createOscillator(); o.frequency.setValueAtTime(120, at); o.frequency.exponentialRampToValueAtTime(45, at + 0.12); const g = c.createGain(); g.gain.setValueAtTime(e.amp * 0.9, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.38); const p = this.out(0, 0); o.connect(g); g.connect(p); o.start(at); o.stop(at + 0.4); return this.track(o, o, g, p); }
      case "hat": case "ohat": case "clap": case "tek": { const s = c.createBufferSource(); s.buffer = noiseBuf(c); const f = c.createBiquadFilter(); f.type = e.v === "clap" ? "bandpass" : e.v === "tek" ? "bandpass" : "highpass"; f.frequency.value = e.v === "clap" ? 1300 : e.v === "tek" ? 3400 : 7000; f.Q.value = e.v === "tek" ? 2.5 : 0.8;
        const len = e.v === "ohat" ? 0.26 : e.v === "clap" ? 0.18 : e.v === "tek" ? 0.07 : 0.05, g = c.createGain(); g.gain.setValueAtTime(e.amp, at); g.gain.exponentialRampToValueAtTime(0.001, at + len); const p = this.out(e.pan || 0, e.v === "clap" ? 0.2 : 0.05); s.connect(f); f.connect(g); g.connect(p); s.start(at, Math.random() * 1.5); s.stop(at + len + 0.02); return this.track(s, s, f, g, p); }
      case "dum": { const o = c.createOscillator(); o.frequency.setValueAtTime(95, at); o.frequency.exponentialRampToValueAtTime(62, at + 0.2); const g = c.createGain(); g.gain.setValueAtTime(e.amp, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.32); const p = this.out(e.pan || 0, 0.12); o.connect(g); g.connect(p); o.start(at); o.stop(at + 0.35); return this.track(o, o, g, p); }
    }
  }
  duduk(e, at, d) {
    const c = this.ctx, o = c.createOscillator(); o.setPeriodicWave(reedWave(c, e.f)); o.frequency.value = e.f;
    const cents = r => 1200 * Math.log2(r);
    if (e.from && Math.abs(cents(e.from / e.f)) <= 320) { o.detune.setValueAtTime(cents(e.from / e.f), at); o.detune.linearRampToValueAtTime(0, at + 0.07); }
    else if (e.scoop) { o.detune.setValueAtTime(-90, at); o.detune.linearRampToValueAtTime(0, at + 0.16); }
    if (e.grace) { o.detune.setValueAtTime(cents(e.grace / e.f), at); o.detune.setValueAtTime(cents(e.grace / e.f), at + 0.085); o.detune.linearRampToValueAtTime(0, at + 0.12); }
    if (e.mord) { o.detune.setValueAtTime(0, at + 0.05); o.detune.setValueAtTime(cents(e.mord / e.f), at + 0.05); o.detune.setValueAtTime(0, at + 0.10); }
    const lfo = c.createOscillator(); lfo.frequency.value = 5.3; const depth = c.createGain(); depth.gain.setValueAtTime(0, at); depth.gain.setValueAtTime(0, at + 0.45); depth.gain.linearRampToValueAtTime(11 * e.vib, at + 0.95); lfo.connect(depth); depth.connect(o.detune);
    const env = c.createGain(); env.gain.setValueAtTime(0, at); env.gain.setTargetAtTime(e.amp, at, 0.07); env.gain.setTargetAtTime(0, at + d, 0.45 / 4.5);
    const hp = c.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 130;
    const br = c.createBufferSource(); br.buffer = noiseBuf(c); const bp = c.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 1450; bp.Q.value = 0.8;
    const bg = c.createGain(); bg.gain.setValueAtTime(0, at); bg.gain.linearRampToValueAtTime(0.03 * 3.2 * e.amp, at + 0.03); bg.gain.setTargetAtTime(0.03 * e.amp, at + 0.03, 0.12); bg.gain.setTargetAtTime(0, at + d, 0.1);
    const p = this.out(e.pan, e.send); o.connect(env); env.connect(hp); br.connect(bp); bp.connect(bg); bg.connect(hp); hp.connect(p);
    const end = at + d + 0.6; o.start(at); lfo.start(at); br.start(at, Math.random()); o.stop(end); lfo.stop(end); br.stop(end);
    this.track(o, o, env, hp, p); this.track(lfo, lfo, depth); this.track(br, br, bp, bg);
  }
  pad(e, at, d) {
    const c = this.ctx, lp = c.createBiquadFilter(); lp.frequency.value = 1500; const env = c.createGain();
    env.gain.setValueAtTime(0, at); env.gain.linearRampToValueAtTime(e.amp, at + 1.2); env.gain.setValueAtTime(e.amp, at + Math.max(1.2, d)); env.gain.linearRampToValueAtTime(0, at + Math.max(1.2, d) + 1.4);
    const p = this.out(e.pan, e.send); lp.connect(env); env.connect(p);
    [[-3, 0.22], [0, 1], [3, 0.22]].forEach(([dt, vg], j) => { const o = c.createOscillator(); o.setPeriodicWave(triWave(c)); o.frequency.value = e.f; o.detune.value = dt; const g = c.createGain(); g.gain.value = vg / 1.44; o.connect(g); g.connect(lp); o.start(at); o.stop(at + Math.max(1.2, d) + 1.5); if (j === 2) this.track(o, o, g, lp, env, p); else this.track(o, o, g); });
  }
  drone(at, level = 0.07) {                                     // the dam: a second duduk holding D3 and A3, with a sub-D; it breathes slowly
    const c = this.ctx, g = c.createGain(); g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(level, at + 2.5); g.connect(this.out(0, 0.25));
    const parts = [[D3, 1, 22], [D3 * 1.5, 0.45, 10]];
    for (const [f, a, nmax] of parts) { const o = c.createOscillator(); o.setPeriodicWave(reedWave(c, f, nmax, 4200, 3400)); o.frequency.value = f; const og = c.createGain(); og.gain.value = a; const lfo = c.createOscillator(); lfo.frequency.value = 0.09 + a * 0.02; const lg = c.createGain(); lg.gain.value = 0.08 * a; lfo.connect(lg); lg.connect(og.gain); o.connect(og); og.connect(g); o.start(at); lfo.start(at); this.track(o); this.track(lfo); }
    const sub = c.createOscillator(); sub.frequency.value = D3 / 2; const sg = c.createGain(); sg.gain.value = 0.35; sub.connect(sg); sg.connect(g); sub.start(at); this.track(sub);
    this.droneGain = g; this.subGain = sg; return g;
  }
}

// ------------------------------------------------------------------ the player: schedules the score against a piece clock (its own, or the director's)
export class Player {
  constructor(ctx, score, voices) { this.ctx = ctx; this.s = score; this.v = voices; this.idx = 0; this.on = false; this.speed = 1; this.p0 = 0; this.a0 = 0; this.timer = null; }
  pieceNow() { return this.p0 + (this.ctx.currentTime - this.a0) * this.speed; }
  seekIdx(p) { const E = this.s.events; let lo = 0, hi = E.length; while (lo < hi) { const m = (lo + hi) >> 1; if (E[m].t < p) lo = m + 1; else hi = m; } this.idx = lo; }
  start(p, speed = 1) {
    this.stop(); this.on = true; this.speed = speed; this.p0 = p; this.a0 = this.ctx.currentTime + 0.05; this.seekIdx(p);
    this.v.drone(this.a0); this.timer = setInterval(() => this.tick(), 25); this.tick();
  }
  follow(p, speed) {                                             // the director's clock (called ~10 times a second)
    this.external = true;
    if (!this.on) return this.start(p, speed);
    const now = this.ctx.currentTime;
    if (speed !== this.speed) { this.p0 = this.pieceNow(); this.a0 = now; this.speed = speed; }         // a new speed: new mapping, the sounding notes go on
    const drift = this.pieceNow() - p;
    if (Math.abs(drift) > 0.5) { this.v.stopAll(now + 0.02); this.p0 = p; this.a0 = now + 0.03; this.seekIdx(p); this.v.drone(this.a0); }   // a seek or the loop
    else if (Math.abs(drift) > 0.02) this.p0 -= drift * 0.5;                                           // a little drift: ease the mapping, no cut
  }
  stop() { this.on = false; clearInterval(this.timer); this.v.stopAll(this.ctx.currentTime + 0.01); }
  tick() {
    if (!this.on) return;
    const E = this.s.events, horizon = this.pieceNow() + 0.25 * this.speed, k = 1 / this.speed;
    while (this.idx < E.length && E[this.idx].t < horizon) { const e = E[this.idx++]; const at = this.a0 + (e.t - this.p0) * k; if (at >= this.ctx.currentTime - 0.01) this.v.play(e, Math.max(at, this.ctx.currentTime), k); }
    if (!this.external && this.idx >= E.length && this.pieceNow() >= this.s.cycle) { const over = this.pieceNow() - this.s.cycle; this.start(over, this.speed); }    // the loop
  }
}

// ------------------------------------------------------------------ offline render (for measurement: speed, loudness by second)
export async function renderOffline(score, t0, t1, sr = 32000) {
  const n = Math.ceil((t1 - t0 + 1) * sr), ctx = new OfflineAudioContext(2, n, sr), v = new Voices(ctx, ctx.destination);
  v.drone(0); let prep = 0, i = 0; const E = score.events.filter(e => e.t >= t0 && e.t < t1), SL = 2.0;
  const sched = until => { const w0 = performance.now(); while (i < E.length && E[i].t - t0 < until) { v.play(E[i], E[i].t - t0, 1); i++; } prep += performance.now() - w0; };
  sched(SL + 0.5);
  for (let s = SL; s < t1 - t0; s += SL) ctx.suspend(s).then(() => { sched(s + SL + 0.5); ctx.resume(); });   // the next slice's notes are made just before they are needed
  const r0 = performance.now(), out = await ctx.startRendering();
  return { buffer: out, prepMs: prep, renderMs: performance.now() - r0 - prep, seconds: t1 - t0 };
}
export function rmsDb(buffer, hop = 1.0) {                       // loudness proxy: RMS in dB per hop (both channels)
  const sr = buffer.sampleRate, L = buffer.getChannelData(0), R = buffer.numberOfChannels > 1 ? buffer.getChannelData(1) : L, out = [];
  for (let i = 0; i + hop * sr <= L.length; i += Math.round(hop * sr)) { let s = 0; for (let j = i; j < i + hop * sr; j++) s += L[j] * L[j] + R[j] * R[j]; out.push(10 * Math.log10(s / (2 * hop * sr) + 1e-12)); }
  return out;
}
