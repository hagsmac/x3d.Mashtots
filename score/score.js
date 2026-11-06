// score.js (v2): the Landing's score (make_music.py v4/v5), LIVE in WebAudio, re-anchored to any timeline (the approved one or a re-timed preset).
// Derived from explore/live-score/score.js (a copy of the Landing's own), which stays untouched beside it. What is new here is the part of make_music.py that
// the first live score left out (each layer can be switched off from buildScore's `opts`, for measuring it):
//   styles    the tour's four styles, one a row, dealt out by the seed: a duet (a second duduk), kanun taksim (random runs), a dhol dance, a pulse
//   composed  the duduk the way make_music has it: the composed phrases (the helix lift, the chant, the Amen, Shirakatsi's last chord), the improviser in its
//             three free windows and over the dhol in the build, the finale's six-letter hook, the long notes before the drop, the last phrases and the colophon
//   saws      chord stabs on the dhol's 3 + 3 + 2, a held saw pad, a soft saw under the hook
//   fx        risers, snare rolls and impacts at the joints of the arrangement, the harp sweep into the drop
//   sonif     the sonification of the writing, prayer, numerals, Shirakatsi's table and the graph acts (messages, Fiedler cut, PageRank, anneal, descent,
//             walk, Fourier, Poincare, SVD + k-means): a layer the first live score did not have at all
//   measured  the mint layer's own sound (only on a timeline that has the measured holds): the Grabar graph's fastest mode lifts the vowels (a rising run, a duduk choir of the
//             six vowels, consonants plucked), the tokenizer-space cascade ordered by merge rank and the first eight merges as chords, PageRank as a chord that converges, the
//             Fourier pedal of the measured ranks, the heaviest bigrams as dyads, the measured k-means (vowel cluster on the duduk), the anneal's detune following the measured
//             row entropy, the descent following the measured loss, the walkers on the measured chain
//   mix       stem balancing: every voice goes to a stem bus (drone, pad, harp, arp, duduk, kick, bass, perc, saw, fx, plate) with the weight that makes its
//             integrated BS.1770 loudness the target make_music.py sets (calibrated offline, baked in score_mix.json), the kick pumps the pads, bass, saws,
//             arpeggio and harp (sidechain), the stems' high shelves, a short room and the hall (make_music's impulse responses), the master's EQ and its
//             level plan (a gain ride over the loop, calibrated offline), then a limiter.
// Still simplified against the mp3 (say so when comparing): the improvisation is generated live from a seeded generator, not the mp3's notes; the tape-fx
// pitch drop of the time-dilation layer lives in fx.js; the drone is not periodic over the loop; the limiter is a compressor without look-ahead.

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
export const STEMS = ["drone", "pad", "harp", "arp", "duduk", "kick", "bass", "perc", "saw", "fx", "plate"];
export const STEM_OF = { kanun: "harp", glass: "harp", plate: "plate", sand: "plate", duduk: "duduk", pad: "pad", cluster: "pad", fourier: "pad", bass: "bass", kick: "kick", hat: "perc", ohat: "perc", clap: "perc", dum: "perc", tek: "perc", saw: "saw", riser: "fx", roll: "fx", impact: "fx" };
export const stemOf = e => e.stem || STEM_OF[e.v];

export function buildScore(data, tl, seed = 0, opts = {}) {
  const O = { styles: true, composed: true, saws: true, fx: true, sonif: true, measured: true, ...opts };
  const PCR = data.PCR, CH = data.CH, KEYS = data.KEYS, A = data.act, BAR = data.BAR, BEAT = BAR / 4, S16 = BEAT / 4, SO = data.sonif;
  const hz = nm => { const pc = nm.slice(0, -1), o = +nm.slice(-1), od = o - (pc === "C" || pc === "C#" ? 1 : 0); return D3 * PCR[pc] * 2 ** (od - 3); };
  const ladder = (pcs, lo, hi) => { const out = []; for (let o = 0; o < 9; o++) for (const pc of pcs) { const f = D3 * PCR[pc] * 2 ** (o - 3); if (f >= lo && f <= hi) out.push(f); } return out.sort((a, b) => a - b); };
  const pcOf = f => { const c = ((1200 * Math.log2(f / D3)) % 1200 + 1200) % 1200; let best = null, bd = 1e9; for (const [pc, n] of Object.entries(PCN)) { const d = Math.abs(((c - 100 * n) + 600 + 1200) % 1200 - 600); if (d < bd) { bd = d; best = pc; } } return best; };
  const fin0 = tl.span("finale")[0], fin1 = tl.span("finale")[1];
  const barT = b => fin0 + b * BAR, ra = (a, seg) => tl.realOfAct(a, seg);
  // ---- the groove: where it starts, how many bars the build has now ----
  const sp = tl.span("space");
  const g0 = Math.ceil((sp[0] + 1.0 - fin0) / BAR);                                     // approved: -29
  const stretch = -g0 / data.GROOVE_BARS;                                                // build gates scale with the build
  const gateBar = b => b < 0 ? Math.round(b * stretch) : b, barS = b => b < 0 ? b * stretch : b;
  const gate = (spec, bf) => { for (const e of spec) { const a = gateBar(e[0]), b = gateBar(e[1]); if (bf >= a && bf < b) return e.length === 3 ? e[2] : e[2] + (e[3] - e[2]) * (bf - a) / (b - a); } return 0; };
  // a position that survives re-timing (the exporter's anchors): a bar from the groove on, an act time in a run, a fraction of a hold, an offset from the loop's end
  const anchorT = a => a.kind === "bar" ? barT(barS(a.bar)) : a.kind === "act" ? ra(a.act, a.seg) : a.kind === "end" ? tl.cycle + a.off : (s => s ? s[0] + a.frac * (s[1] - s[0]) : null)(tl.span(a.seg));
  // ---- the harmony table, re-anchored ----
  const HARM = [];
  for (const h of data.harm) {
    const at = h.at; let t;
    if (at.kind === "bar") { if (at.bar < 0) continue; t = barT(at.bar); }                  // the build is regenerated below; the finale keeps its bars
    else if (at.kind === "act") t = ra(at.act, at.seg);
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
  const penDeg = (k, t) => { const lad = PENT[chordAt(t)]; return lad[Math.max(0, Math.min(lad.length - 1, k))]; };
  const hdur = (t0, base, ring = 0.6) => Math.max(0.5, Math.min(base, chordEnd(t0 + 0.001) + ring - t0));
  const lowAmp = f => Math.min(1, (f / 330) ** 0.6);
  const ev = [], LOG = (t, f, kind, dur = 0) => log.push({ t, f, kind, dur }), log = [];
  const q16 = t => fin0 + Math.round((t - fin0) / S16) * S16;
  const rnd = mulberry32(405 + 7919 * seed), R = s => mulberry32(s + 7919 * seed);
  const pluckRow = (i, t, amp, dur, glassAmp, kind, limit = true) => { const f = lfRow(i), d = limit ? hdur(t, dur, 0.9) : dur, pan = (i % 9 - 4) / 5.5; amp *= lowAmp(f);
    ev.push({ t, v: "kanun", f, dur: d, amp, pan, send: 0.32 }); LOG(t, f, kind, d); if (glassAmp) ev.push({ t, v: "glass", f: f * 2, dur: d * 0.7, amp: amp * glassAmp, pan: -pan, send: 0.5 }); };
  const pluck = (i, t, amp = 0.16, dur = 2.2, shift = 0, glassAmp = 0.3, tau = 1.5, panAbs = null) => { const f = lf(i, t, shift), d = hdur(t, dur), pan = panAbs ?? (kdeg(i) - 7) / 9; amp *= lowAmp(f);
    ev.push({ t, v: "kanun", f, dur: d, amp, pan, send: 0.32, tau }); LOG(t, f, "harp"); if (glassAmp) ev.push({ t, v: "glass", f: f * 2, dur: d * 0.7, amp: amp * glassAmp, pan: -pan, send: 0.5 }); };
  const pluckK = (k, t, amp = 0.1, dur = 1.2, pan = 0, glassAmp = 0, tau = 1.2) => { const f = penDeg(k, t), d = hdur(t, dur); amp *= lowAmp(f);
    ev.push({ t, v: "kanun", f, dur: d, amp, pan, send: 0.3, tau }); LOG(t, f, "harp"); if (glassAmp) ev.push({ t, v: "glass", f: f * 2, dur: d * 0.7, amp: amp * glassAmp, pan: -pan, send: 0.5 }); };
  const flourish = (t, ch, amp = 0.06) => TONES[ch].slice(0, 7).forEach((f, j) => { ev.push({ t: t + j * 0.055, v: "kanun", f, dur: 1.5, amp: amp * lowAmp(f), pan: -0.5 + j / 6, send: 0.35, tau: 1.0 }); LOG(t + j * 0.055, f, "arp", 1.5); });
  const gliss = (t, key, lo, hi, n, dt, amp, up = true) => { const lad = ladder(typeof key === "string" ? data.KEYS[key] : key, lo, hi), seq = []; for (let j = 0; j < n; j++) seq.push(lad[Math.round(j * (lad.length - 1) / (n - 1))]); if (!up) seq.reverse();
    seq.forEach((f, j) => { const u = j / (n - 1); ev.push({ t: t + j * dt, v: "kanun", f, dur: 1.3, amp: amp * (0.55 + 0.45 * (up ? u : 1 - u)) * lowAmp(f), pan: up ? -0.7 + 1.4 * u : 0.7 - 1.4 * u, send: 0.35, tau: 0.8 }); LOG(t + j * dt, f, "gliss"); }); };
  const dnote = (t, f, dur, o = {}) => { ev.push({ t, v: "duduk", f, dur: dur * 0.985, from: o.from ?? null, scoop: !!o.scoop, grace: o.grace ?? null, mord: o.mord ?? null, vib: o.vib ?? 1, amp: o.amp ?? 0.2, pan: o.pan ?? 0.12, send: o.send ?? 0.38 }); LOG(t, f, "duduk", dur); };
  const fxe = (t, v, dur, amp, send, extra = {}) => ev.push({ t, v, dur, amp, send, ...extra });
  const toTone = (f, ch) => ladder(CH[ch].tones, 140, 2100).reduce((a, g) => Math.abs(Math.log(g / f)) < Math.abs(Math.log(a / f)) ? g : a);
  const segsOf = (t0, t1) => { const out = []; for (const h of HARM) { const a = Math.max(t0, h.t0), b = Math.min(t1, h.t1); if (b - a > 0.3) out.push({ a, b, chord: h.chord }); } return out; };     // the chords sounding in [t0, t1]
  const dk = (t, f, dur, amp = 0.1, o = {}) => { const tb = chordEnd(t + 0.001); if (t + dur > tb - 0.05 && !safe(tb + 0.01).has(pcOf(f))) dur = Math.max(0.45, tb - 0.12 - t);       // a duduk note, cut short before a chord that does not hold it
    ev.push({ t, v: "duduk", f, dur, vib: o.vib ?? 1, scoop: !!o.scoop, amp, pan: o.pan ?? 0.12, send: 0.38 }); LOG(t, f, "duduk", dur); };
  const vtone = (i, t) => { let f = lf(i, t); while (f < 270) f *= 2; while (f > 900) f /= 2; return f; };                          // a letter's pitch (a step of the chord's pentatonic) in the duduk's range
  const sustain = (i, t0, t1, amp) => { for (const g of segsOf(t0, t1)) dk(g.a, vtone(i, g.a), g.b - g.a, amp); };                // a held duduk note that follows the harmony

  // ---- the stone wakes: four rising runs as the 36 letters leave, softly again as they land (exempt from the audit: they sweep four keys on purpose)
  data.letters.forEach((p, i) => { pluckRow(i, ra(p.t0, "flight"), 0.10, 2.2, 0.25, "cascade", false); pluckRow(i, ra(Math.min(p.t0 + data.flight, A.T1), "flight") ?? ra(p.t0 + data.flight), 0.05, 1.4, 0, "cascade", false); });
  gliss(tl.span("lift")[0] + 0.05, "Dm", 146, 1250, 22, 0.06, 0.05);
  // ---- the tour: one note per spotlit letter on the stone's own pitch; a rolled chord marks each key; the struck plate and its sand
  for (let k = 0; k < 36; k++) {
    const tk = ra(A.TT + k * data.pace, "tour"); pluckRow(k, tk, 0.15, 2.4, 0.3, "row");
    const n = k % 9 + 1, m = Math.floor(k / 9) + 1, fk = lfRow(k);
    ev.push({ t: tk, v: "plate", f: fk, nm: n + m, amp: 0.17 * Math.min(1, (fk / 330) ** 0.5), pan: -(k % 9 - 4) / 5.5, send: 0.5 });
    for (const pn of [-0.7, 0.7]) ev.push({ t: tk + 0.03, v: "sand", n: 5 * (n + m), seed: 1000 * seed + 2 * k + (pn > 0), amp: 0.11, pan: pn, send: 0.2 });
    if (k % 9 === 0 && k > 0) flourish(tk + 0.05, ["Am", "Em", "Bm"][k / 9 - 1]);
  }
  // ---- the writing: a glissando in D major into the sentence; the prayer and the numerals sound in
  gliss(tl.span("write")[0], "DM", 146, 1300, 24, 0.05, 0.05);
  for (const [nm, i] of [["prayer", 15], ["numerals", 14]]) { const s = tl.span(nm); if (s) pluck(i, s[0] + 0.02, 0.12); }
  // ---- act entries: the letter that sounds each act in (on the 16th grid once the groove has started)
  for (const [segn, [key, i]] of Object.entries(data.ENTRY)) { let t = ra(A[key], segn); if (t == null) continue; t += 0.02; if (t >= barT(g0)) t = q16(t); pluck(i, t, 0.12, 1.6); }
  // ---- the letters fall home: the runs in reverse (exempt)
  data.letters.forEach((p, i) => pluckRow(i, ra(p.r0, "return") ?? ra(p.r0), 0.08, 1.8, 0.2, "cascade", false));
  // ---- pads: one chord at a time (the chord's own voicing), long attacks
  for (const h of HARM) { if (h.t0 > tl.cycle) break; const b = (h.t0 - fin0) / BAR, g = b < -52 * stretch ? 1 : b < g0 ? 0.8 : 0.55;
    CH[h.chord].pad.forEach((nm, k) => { const f = hz(nm); ev.push({ t: h.t0 - 0.2, v: "pad", f, dur: h.t1 - h.t0 + 0.2, amp: 0.06 * g, pan: (k - 1) * 0.35, send: 0.5 }); LOG(h.t0, f, "pad"); }); }

  // ---- the duduk: the deck's phrasing, made to listen (make_music.improv); free time (rubato) or, over the dhol, on the eighth-note grid
  const improv = (t0, t1, groove, start, amp = 0.2, o = {}) => {
    const r = o.r || rnd, activity = o.activity || 1, pan = o.pan ?? 0.12, choice = a => a[Math.floor(r() * a.length)];
    let t = t0, fcur = hz(start);
    const q8 = x => { const h = BEAT / 2; return fin0 + Math.round((x - fin0) / h) * h; };
    while (t < t1 - 1.5) {
      if (groove) t = q8(t);
      const n = 3 + Math.floor(r() * 4); let prev = null, prevEnd = -9;
      for (let k = 0; k < n; k++) {
        if (t >= t1 - 1.0) break;
        const lad = SCALE[keyAt(t)]; let i0 = 0; lad.forEach((g, j) => { if (Math.abs(Math.log(g / fcur)) < Math.abs(Math.log(lad[i0] / fcur))) i0 = j; });
        const u = r(); let step = u < .3 ? -1 : u < .6 ? 1 : u < .72 ? -2 : u < .84 ? 2 : u < .92 ? 0 : (r() < .5 ? -3 : 3);
        if (lad[i0] >= hz("D5") && step > 0) step = -step; if (lad[i0] <= hz("E4") && step < 0) step = -step;
        const i1 = Math.max(0, Math.min(lad.length - 1, i0 + step)), last = k === n - 1;
        let dur = groove ? (last ? choice([4, 6]) : choice([1.5, 2, 3, 4])) * BEAT : last ? 2.4 + 1.8 * r() : choice([0.7, 0.9, 1.2, 1.6, 2.2]);
        let f = lad[i1]; const sp = safe(t);
        if ((dur >= 1 || last) && !sp.has(pcOf(f))) f = lad.filter(g => sp.has(pcOf(g))).reduce((a, g) => Math.abs(Math.log(g / f)) < Math.abs(Math.log(a / f)) ? g : a);
        if (last && r() < 0.7) { const tp = new Set(CH[chordAt(t + 0.001)].tones), near = lad.filter(g => tp.has(pcOf(g)) && Math.abs(Math.log(g / f)) < 0.22); if (near.length) f = near.reduce((a, g) => Math.abs(Math.log(g / f)) < Math.abs(Math.log(a / f)) ? g : a); }
        const tb = chordEnd(t + 0.001); if (t + dur > tb - 0.05 && !safe(tb + 0.01).has(pcOf(f))) dur = Math.max(0.45, tb - 0.12 - t);
        const j = lad.indexOf(f), up = j >= 0 && j + 1 < lad.length ? lad[j + 1] : null;
        const grace = up && dur >= 0.9 && r() < 0.35 ? up : null, mord = up && !grace && dur >= 1.2 && r() < 0.12 ? up : null;
        ev.push({ t, v: "duduk", f, dur, from: prev && t - prevEnd < 0.06 ? prev : null, scoop: k === 0 && r() < 0.3, grace, mord, vib: (0.9 + 0.5 * r()) * (dur >= 1.6 ? 1.3 : 1), amp: amp * (0.85 + 0.15 * r()), pan, send: 0.38 });
        LOG(t, f, "duduk", dur); prev = f; prevEnd = t + dur; fcur = f; t += dur;
      }
      t += groove ? choice([2, 3, 4]) * BEAT : (1.2 + 2.3 * r()) / activity;
    }
  };
  const melody = (t0, notes, amp = 0.2, vib = 1) => {                                         // the composed phrases: (note, beats, flags) with s = scoop, v = more vibrato, gX = grace note from X
    let t = t0, prev = null;
    for (const [nm, beats, fl] of notes) {
      const dur = beats * BEAT; if (nm == null) { t += dur; prev = null; continue; }
      const f = hz(nm), mg = fl.match(/g([A-G][#b]?[0-9])/), scoop = fl.includes("s");
      dnote(t, f, dur, { from: prev && !scoop ? prev : null, scoop, grace: mg ? hz(mg[1]) : null, vib: vib * (fl.includes("v") ? 1.45 : 1), amp });
      prev = f; t += dur;
    }
  };
  if (O.composed) {
    for (const m of data.MELODIES) { const t = anchorT(m.at); if (t != null) melody(t, data.PH[m.name], m.amp, m.vib); }
    for (const w of data.IMPROV) { const a = anchorT(w.t0), b = anchorT(w.t1); if (a == null || b == null || b - a < 3) continue; improv(a, b, w.groove, ["A4", "D5", "F4"][seed % 3], w.amp, { activity: w.activity, r: R(w.seed) }); }
  }
  // ---- the tour's four styles, one a row; each seed deals them out differently: a duet (a second duduk, another register), kanun taksim (random runs through the key),
  // a dhol dance (dum and tek in 3 + 3 + 2 with a clap), a pulse (heartbeat, hats, a shaker) that foreshadows the groove
  if (O.styles) {
    const TROW = [0, 1, 2, 3].map(r => ra(A.TT + 9 * r * data.pace, "tour")).concat([ra(A.TC, "tour")]);
    const STY = [["duet", "taksim", "dhol", "pulse"], ["taksim", "pulse", "duet", "dhol"], ["dhol", "duet", "pulse", "taksim"]][seed % 3], tkr = R(77 + 5000);
    for (let r = 0; r < 4; r++) {
      const a = TROW[r] + (r ? 1.2 : 0.5), b = TROW[r + 1] - 0.4, sty = STY[r];
      if (sty === "taksim") { let tk = a; while (tk < b - 2.0) { gliss(tk, keyAt(tk + 0.1), 220, 1100, 8 + Math.floor(tkr() * 7), 0.055 + 0.02 * tkr(), 0.085, tkr() < 0.6); tk += 1.8 + 1.8 * tkr(); } }
      else if (sty === "duet") improv(a, b, false, "D4", 0.15, { activity: 1.4, pan: -0.3, r: R(5000 + 97 * r) });
      else for (let si = Math.trunc((a - fin0) / S16); si < Math.trunc((b - fin0) / S16); si++) {
        const t = fin0 + si * S16, sb = ((si % 16) + 16) % 16, e8 = sb >> 1, ramp = Math.min(1, (t - a) / 4);
        if (sty === "dhol") {
          if (sb % 2 === 0 && [0, 3, 6].includes(e8)) ev.push({ t, v: "dum", amp: 0.2 * ramp, pan: -0.15, room: 0.2 }); else if (sb % 2 === 0 && [2, 5, 7].includes(e8)) ev.push({ t, v: "tek", amp: 0.15 * ramp, pan: 0.2, room: 0.2 });
          if (sb === 4 || sb === 12) ev.push({ t, v: "clap", amp: 0.1 * ramp, pan: 0.05, room: 0.3 });
        } else {
          if (sb % 4 === 0) ev.push({ t, v: "kick", amp: 0.16 * ramp });
          if (sb % 4 === 2) ev.push({ t, v: "hat", amp: 0.12 * ramp, pan: -0.2, room: 0.06 });
          if (sb % 2 === 1) ev.push({ t, v: "hat", amp: 0.05 * ramp, pan: 0.3, room: 0.06 });
          if (sb % 8 === 4) ev.push({ t, v: "tek", amp: 0.1 * ramp, pan: 0.2, room: 0.2 });
        }
      }
    }
  }
  // ---- the writing, the prayer, the numerals and Shirakatsi's table, then the graph acts (make_music.py: each sounds what its picture shows)
  if (O.sonif) {
    for (const w of SO.write) { const t = ra(A.TC + 1 + w.q * SO.GDT, "write"); if (t != null) pluck(w.src, t, 0.11, 1.0, 0, 0.25, 0.9); }
    const pr0 = tl.span("prayer")[0], nu0 = tl.span("numerals")[0], sh0 = tl.span("shirakatsi")[0];
    for (const w of SO.prayer) pluck(w.src, pr0 + 1 + w.k * SO.prayerGDT, 0.055, 1.2, 0, 0, 1.0);
    for (const fl of data.FLOURISH) { const t = anchorT(fl.at); if (t != null) flourish(t, fl.chord, fl.amp); }
    for (let i = 0; i < 36; i++) pluck(i, nu0 + 0.7 + i * 0.035, 0.065, 0.9, 0, 0, 0.9);
    for (const q of SO.eqs) q.idx.forEach((i, j) => pluck(i, nu0 + q.dt + 0.11 * j, 0.13, 2.2, 0, 0.45));
    for (let r = 1; r < 10; r++) for (let c = 1; c < 10; c++) pluckK((r * c - 1) % 9 + (r < 5 ? 0 : 5), sh0 + 0.9 + (r * 10 + c) * 0.045, 0.045, 0.6, (c - 5) / 6, 0, 0.5);
    for (let r = 1; r < 10; r++) { const t = sh0 + 0.9 + (r * 10 + r) * 0.045, f = penDeg((r * r - 1) % 9 + 5, t); ev.push({ t, v: "glass", f, dur: 1.2, amp: 0.05, pan: 0, send: 0.5 }); LOG(t, f, "harp"); }
    { const w0 = tl.span("web")[0], s0 = tl.span("space")[0];                                                    // the embedding scan, then the web's sparkle over the 630 chords
      for (let q = Math.floor(A.TW2 * 1.5); q < Math.floor(A.TS2 * 1.5); q++) { const t = ra(q / 1.5, "space"); if (t != null && t >= s0 && t < w0) pluck(q % 36, t, 0.05, 0.9, 5, 0, 0.8); }
      for (let q = 0; q < 26; q++) pluckK(7 + (q * 5) % 8, q16(w0 + 0.2 + q * 0.2345), 0.05, 0.7, ((q * 7) % 11 - 5) / 6, 0, 0.7); }
    SO.msg.forEach((m, l) => { const t = ra(A.TB2 + 1.5 * l, "msg"); if (t == null) return; const t0 = q16(t); m.top.forEach((i, j) => pluck(i, t0 + 0.03 * j, 0.1 * (0.5 + m.w[j]), 1.0, 0, 0.4)); });
    { const t0 = tl.span("spectral")[0], dur = tl.span("spectral")[1] - t0;   // Fiedler cut: a held note for each side, left and right
      for (const [lst, pan] of [[SO.fied.pos, 0.5], [SO.fied.neg, -0.5]]) for (const i of lst) { const f = toTone(lf(i, t0, 5), chordAt(t0)); ev.push({ t: t0 - 0.2, v: "pad", f, dur: dur + 0.2, att: 0.6, rel: 0.8, amp: 0.05, pan, send: 0.45 }); LOG(t0, f, "pad"); } }
    for (let k = 0; k < 15; k++) { const t = ra(A.TP + 6.0 / 14 * k, "pagerank"); if (t != null) SO.prtop.forEach((i, j) => pluck(i, q16(t) + 0.02 * j, 0.03 + 0.07 * k / 14, 0.8, 0, 0, 0.9)); }
    { const t0 = tl.span("anneal")[0], dur = tl.span("anneal")[1] - t0;                                              // anneal: a cluster that starts wide and settles to a unison
      [[0, -0.2], [2, 0.2], [3, 0.0]].forEach(([ix, pan]) => { const f = TONES[chordAt(t0 + 0.1)][ix]; ev.push({ t: t0, v: "cluster", f, dur, amp: 0.06, pan, send: 0.4 }); LOG(t0, f, "pad"); }); }
    { const t0 = tl.span("descent")[0]; SO.descent_k.forEach((k, q) => pluckK(k, q16(t0 + 0.1 + q * 0.2345), 0.075, 0.8, -0.2, 0, 0.9)); }
    SO.walk.forEach((sq, vi) => sq.forEach((i, k) => { const t = ra(A.TD2 + k / 1.7, "walk"); if (t != null) pluck(i, q16(t) + 0.012 * vi, 0.08, 0.9, [-5, 0, 5][vi], 0, 0.9); }));
    { const t0 = tl.span("fourier")[0], dfo = tl.span("fourier")[1] - t0; ev.push({ t: t0, v: "fourier", f: D3, dur: dfo + 0.8, hs: SO.four.hs, mags: SO.four.mags, phs: SO.four.phs, amp: 0.07, send: 0.4 }); LOG(t0, D3, "pedal"); }
    { const t0 = tl.span("poincare")[0]; for (let q = 0; q < 18; q++) pluckK(4 + (q * 3) % 11, q16(t0 + 0.2 + q * 0.117), 0.05, 1.2, (q - 9) / 11, 0.3, 1.2); }
    { const cl = tl.span("collapse")[0]; SO.svd_k.forEach((row, it) => { const t = ra(A.TSV + 3 + it, "svd"); if (t == null) return; const ts = q16(t); if (ts < cl) row.forEach((kk, k) => pluckK(kk, ts + 0.04 * k, 0.07, 1.0, (k - 1.5) / 2.5, 0.35, 1.2)); }); }
  }
  // ---- the MEASURED acts: the mint layer sounds from the measured data (Grabar, 342,533 letters; the tokenizer's merge list). It uses the same voices as the authored acts,
  // with a shimmer of glass on top and a little more to the right, so that gold (authored, kanun) and mint (measured, glass) can be told apart. Only on a timeline that has the holds.
  if (O.measured && data.sonifM && tl.span("svdm")) {
    const SM = data.sonifM, R_ = 0.25;
    { const [v0, v1] = tl.span("vowels"), V = SM.vowels, h0 = v0 + BAR, h1 = v1 - BAR;                                    // the fastest mode lifts the vowels: a rising run, the vowel choir, the strongest consonants plucked, the run falling back
      V.order.forEach((i, r) => pluckK(Math.round(14 * r / 35), v0 + 0.05 + (BAR - 0.1) * r / 35, 0.04 + 0.05 * r / 35, 0.9, R_ + 0.5 * (r / 17.5 - 1), 0.5, 0.9));
      V.vowels.forEach((i, j) => sustain(i, h0 + j * BEAT * 0.5, h1, 0.07));
      V.order.slice(0, 8).forEach((i, j) => pluck(i, h0 + j * BEAT, 0.03 + 0.05 * Math.abs(V.mode[i]), 0.9, 0, 0.3, 0.9));
      V.order.forEach((i, r) => pluckK(Math.round(14 * (35 - r) / 35), h1 + (BAR - 0.1) * r / 35, 0.03 + 0.03 * (35 - r) / 35, 0.9, R_ + 0.5 * (1 - r / 17.5), 0.5, 0.9)); }
    { const k0 = tl.span("tokens")[0], TK = SM.tok;                                                                       // tokenizer space: the letters sound in the order of their first merge (time = the picture's radius, pan = its x), then the first eight merges as chords
      TK.order_rank.forEach(i => pluck(i, k0 + 1.0 + 2.6 * TK.u[i], 0.06, 1.0, 0, 0.5, 0.9, TK.pan[i]));
      TK.merges.forEach((m, q) => { const t = q16(k0 + 4.0 + q * BEAT); pluck(m.a, t, 0.08, 1.0, 0, 0.5, 0.9, R_ - 0.15); pluck(m.b, t + 0.02, 0.08, 1.0, 0, 0.5, 0.9, R_ + 0.15); }); }
    for (let k = 0; k < 15; k++) { const t = ra(A.TP + 6.0 / 14 * k, "pagerank"); if (t != null) SM.pr.top.forEach((i, j) => pluck(i, q16(t) + 0.015 + 0.012 * j, 0.02 + 0.10 * SM.pr.rel[k][j], 0.8, 0, 0.5, 0.9, R_ + 0.1 * (j - 2))); }   // PageRank: the five top letters as one chord, each as loud as its rank now is
    { const t = ra(A.TP + 6.3, "pagerank"); if (t != null) dk(t, vtone(SM.pr.top[0], t), 2.5, 0.09, { vib: 1.2, scoop: true }); }                                           // the winner (Ա, 14.5 %) held
    { const t0 = tl.span("fourier")[0], dfo = tl.span("fourier")[1] - t0; ev.push({ t: t0, v: "fourier", f: D4, dur: dfo + 0.8, hs: SM.four.hs, mags: SM.four.mags, phs: SM.four.phs, amp: 0.05, pan: 0.3, send: 0.4 }); LOG(t0, D4, "pedal"); }   // the measured ranks' own spectrum, an octave above the authored pedal
    { const t0 = tl.span("poincare")[0]; SM.poinc.forEach((c, q) => { const t = q16(t0 + 0.3 + q * BEAT), a = 0.03 + 0.09 * c.w; pluck(c.a, t, a, 1.2, 0, 0.5, 1.0, R_ - 0.15); pluck(c.b, t + 0.02, a, 1.2, 0, 0.5, 1.0, R_ + 0.15); }); }   // the heaviest measured chords as dyads, as loud as they are heavy
    { const [s0, s1] = tl.span("svdm"), K = SM.svd;                                                                       // k-means on the measured plane: a rolled chord per iteration until it settles (iteration 2), the vowel cluster on the duduk; then the settled chord is held
      for (let it = 0; it <= K.settle; it++) { const ts = q16(s0 + 1.5 + 0.75 * it); K.k[it].forEach((kk, k) => { if (k === K.vowel_cluster) { let f = penDeg(kk, ts + 0.04 * k); while (f < 270) f *= 2; while (f > 900) f /= 2; dk(ts + 0.04 * k, f, 0.9, 0.08, { pan: 0.3 }); } else pluckK(kk, ts + 0.04 * k, 0.07, 1.0, (k - 1.5) / 2.5 + 0.15, 0.5, 1.2); }); }
      const ts = s0 + 1.5 + 0.75 * (K.settle + 1);
      for (const g of segsOf(ts, s1 - 0.3)) K.k[K.settle].forEach((kk, k) => { if (k === K.vowel_cluster) { let f = penDeg(kk, g.a); while (f < 270) f *= 2; while (f > 900) f /= 2; dk(g.a, f, g.b - g.a, 0.08, { pan: 0.3, vib: 1.2 }); } else { const f = toTone(penDeg(kk, g.a), g.chord); ev.push({ t: g.a - 0.2, v: "pad", f, dur: g.b - g.a + 0.2, att: 0.6, rel: 0.8, amp: 0.05, pan: (k - 1.5) / 2.5 + 0.15, send: 0.45 }); LOG(g.a, f, "pad"); } }); }
    { const [t0, t1] = tl.span("anneal"), AN = SM.anneal;                                                                  // anneal: the cluster's detune follows the measured mean row entropy at the temperature the picture shows (cold, hot, cold)
      for (const g of segsOf(t0, t1)) { const n = 24, curve = Array.from({ length: n }, (_, i) => { const a = tl.act(g.a + (g.b - g.a) * i / (n - 1)), sv = 0.5 - 0.5 * Math.cos(2 * Math.PI * (a - A.TA) / AN.period), x = Math.max(0, Math.min(12, sv * 12)), j = Math.min(11, Math.floor(x)); return (AN.H[j] + (AN.H[j + 1] - AN.H[j]) * (x - j)) / AN.H[12]; });
        [[1, 0.1], [3, 0.4], [4, 0.25]].forEach(([ix, pan]) => { const f = TONES[g.chord][ix]; ev.push({ t: g.a, v: "cluster", f, dur: g.b - g.a, amp: 0.05, pan, send: 0.4, curve }); LOG(g.a, f, "pad"); }); } }
    { const DS = SM.desc, rg = DS.start - DS.floor;                                                                       // descent: a falling line down the ladder that follows the measured loss, then a held low note at the floor
      for (let q = 0; q < 16; q++) { const t = ra(A.TD + 6.5 * q / 15, "descent"); if (t == null) continue; const L = DS.loss[Math.min(47, Math.round(47 * q / 15))]; pluckK(Math.round(13 * Math.sqrt(Math.max(0, L - DS.floor) / rg)), q16(t) + 0.02, 0.075, 0.8, 0.2, 0.5, 0.9); }
      const te = ra(A.TD + 6.5, "descent"); if (te != null) dk(te + 0.1, toTone(hz("D4"), chordAt(te + 0.1)), 2.2, 0.09, { vib: 0.9 }); }
    SM.walk.forEach((sq, vi) => sq.forEach((i, k) => { const t = ra(A.TD2 + k / 1.7, "walk"); if (t != null) pluck(i, q16(t) + 0.012 * vi + 0.03, 0.08, 0.9, [-3, 2, 7][vi], 0.5, 0.9, (kdeg(i) - 7) / 9 + R_); }));   // the three walkers on the measured chain, a hair behind the authored ones
  }
  // ---- the finale's melody: the six letters of Mashtots are the hook, F# D B | E C G (D | C, then G | C); long notes before the drop; the last phrases; the harp wash
  if (O.composed) {
    const HOOK = [["F#5", 1], ["D5", 1], ["B4", 2], ["E5", 1], ["C5", 1], ["G4", 2]], UP = [1, 2, 1, 2, 2, 2];
    [10, 12, 14].forEach((b0, rep) => { let t = barT(b0); HOOK.forEach(([nm, beats], k) => {
      const f = hz(nm) * (rep === 2 && k === 5 ? 2 : 1), dur = beats * BEAT;
      ev.push({ t, v: "duduk", f, dur: dur * 0.97, from: k === 1 || k === 4 ? hz(HOOK[k - 1][0]) : null, grace: seed && rep > 0 && (k === 0 || k === 3) ? f * 2 ** (UP[k] / 12) : null, vib: 1.0, amp: 0.36, pan: 0.08, send: 0.3 }); LOG(t, f, "hook", dur);
      ev.push({ t, v: "kanun", f: f * 2, dur: dur * 1.2, amp: 0.2, pan: -0.25, send: 0.3, tau: 0.9, bright: 1.3 }); LOG(t, f * 2, "hook", dur);
      if (O.saws) ev.push({ t, v: "saw", f, dur: dur * 0.95, cutoff: 1700, att: 0.02, rel: 0.15, amp: 0.07, pan: 0, room: 0.12, send: 0.1 });
      t += dur; }); });
    for (const [b0, nm, beats] of [[2, "D5", 7], [4, "C5", 7], [6, "E5", 7], [8, "A4", 7.5]]) { ev.push({ t: barT(b0) + 0.05, v: "duduk", f: hz(nm), dur: beats * BEAT, scoop: true, vib: 1.15, amp: 0.2, pan: 0.1, send: 0.4 }); LOG(barT(b0), hz(nm), "duduk", beats * BEAT); }
    for (const [b0, nm, beats, fl] of [[16, "D5", 3, ""], [16.75, "B4", 1, ""], [17, "G4", 4, "v"], [18, "D5", 8, "v"]]) { ev.push({ t: barT(b0), v: "duduk", f: hz(nm), dur: beats * BEAT, scoop: b0 === 18, vib: fl ? 1.3 : 1.0, amp: 0.2, pan: 0.1, send: 0.4 }); LOG(barT(b0), hz(nm), "duduk", beats * BEAT); }
    for (let i = 0; i < 36; i++) pluck(i, barT(16) + 0.2 + i * 0.05, 0.05, 1.2, 0, 0);
    const col0 = fin1 + data.COL0_OFF, col1 = fin1 + data.COL1_OFF;                                   // the colophon: open fifths, then a last duduk D
    for (const nm of ["D3", "A3", "D4"]) { ev.push({ t: col0 + 0.3, v: "pad", f: hz(nm), dur: col1 - col0 + 1.0, att: 1.8, rel: 2.5, amp: 0.07, pan: 0, send: 0.5 }); LOG(col0 + 0.3, hz(nm), "pad"); }
    ev.push({ t: col0 + 1.3, v: "duduk", f: hz("D4"), dur: 4.5, vib: 0.8, rel: 1.4, amp: 0.17, pan: 0.1, send: 0.45 }); LOG(col0 + 1.3, hz("D4"), "duduk", 4.5);
    ev.push({ t: tl.cycle - 8.0, v: "duduk", f: hz("D3"), dur: 5.0, vib: 0.6, rel: 2.2, amp: 0.15, pan: 0.1, send: 0.45 }); LOG(tl.cycle - 8.0, hz("D3"), "duduk", 5.0);
  }
  // ---- the groove: every 16th from the build's first bar to the end of the finale
  const bassRoot = ch => { let f = D3 * PCR[CH[ch].root] / 2; while (f < 57) f *= 2; while (f > 118) f /= 2; return f; };
  const ACC = [1.0, 0.45, 0.5, 0.6, 0.45, 0.5, 1.0, 0.45, 0.5, 0.6, 0.45, 0.5, 1.0, 0.45, 0.8, 0.5];
  const PAT = [[0, 2, 4, 2, 1, 3, 5, 3, 0, 2, 4, 2, 1, 3, 5, 3], [0, 3, 2, 3, 1, 4, 2, 4, 0, 3, 2, 3, 1, 5, 3, 5], data.ARP_PAT3];
  const G = data.GATES, vr = R(9038), BARPAT = {}, hstep = new Set(HARM.map(h => Math.round((h.t0 - fin0) / S16)));
  for (let si = g0 * 16; si < Math.round((fin1 - fin0) / S16); si++) {
    const t = fin0 + si * S16, bf = si / 16, sb = ((si % 16) + 16) % 16, b = Math.floor(si / 16), ch = chordAt(t), tn = TONES[ch];
    let gk = sb % 4 === 0 ? gate(G.floor, bf) : 0; if (gk === 0 && sb % 8 === 0) gk = gate(G.half, bf);
    if (gk > 0) ev.push({ t, v: "kick", amp: 0.9 * gk, duck: true });
    if (sb === 0 && gate(G.heart, bf) > 0) ev.push({ t, v: "kick", amp: 0.35, duck: true });
    const gc = gate(G.clap, bf); if (gc > 0 && (sb === 4 || sb === 12)) ev.push({ t, v: "clap", amp: 0.4 * gc, pan: 0.05, room: 0.2 });
    const gh = gate(G.hat8, bf); if (gh > 0 && sb % 2 === 0 && sb % 4 !== 2) ev.push({ t, v: "hat", amp: 0.16 * gh * (sb % 8 === 0 ? 1 : 0.75), pan: -0.2, room: 0.04 });
    const go = gate(G.ohat, bf); if (go > 0 && sb % 4 === 2) ev.push({ t, v: "ohat", amp: 0.2 * go, pan: 0.25, room: 0.1 });
    const g16 = gate(G.hat16, bf); if (g16 > 0 && sb % 2 === 1) ev.push({ t, v: "hat", amp: 0.1 * g16, pan: sb % 4 === 1 ? 0.3 : -0.3, room: 0.04 });
    const gd = gate(G.dhol, bf); if (gd > 0 && sb % 2 === 0) { const e8 = sb / 2; if ([0, 3, 6].includes(e8)) ev.push({ t, v: "dum", amp: 0.38 * gd, pan: -0.15, room: 0.12 }); else if ([2, 5, 7].includes(e8)) ev.push({ t, v: "tek", amp: 0.27 * gd, pan: 0.2, room: 0.14 }); }
    const gb = gate(G.bass, bf); if (gb > 0 && sb % 4 === 2) { const f = bassRoot(ch) * ((sb === 14 && bf >= 10 && b % 2 === 1) || (seed && sb === 10 && vr() < 0.22) ? 2 : 1); ev.push({ t, v: "bass", f, dur: S16 * 3, amp: 0.5 * gb }); LOG(t, f, "bass"); }
    const g8 = gate(G.arp8, bf), g16a = gate(G.arp16, bf), ga = g16a > 0 ? g16a : (sb % 2 === 0 ? g8 : 0);
    if (ga > 0) { const pat = seed ? PAT[BARPAT[b] ??= [0, 0, 1, 2][Math.floor(vr() * 4)]] : PAT[b % 4 === 3 ? 1 : 0], f = tn[pat[sb]];
      if (!(seed && sb % 4 && vr() < 0.06)) { ev.push({ t, v: "kanun", stem: "arp", f, dur: 0.42, tau: 0.32, bright: 1.35, click: 0.1, amp: 0.2 * ga * ACC[sb], pan: 0.32 * Math.sin(si * 0.9), send: 0.12, room: 0.1 }); LOG(t, f, "arp"); } }
    if (seed && gd > 0 && b % 8 === 7 && sb >= 12) ev.push({ t, v: "tek", amp: 0.2 * (0.6 + 0.12 * (sb - 12)), pan: 0.2, room: 0.14 });          // a fill into every eighth bar
    if (O.saws) {
      const gs = gate(data.G_STAB, bf); if (gs > 0 && (sb === 0 || sb === 6 || sb === 12)) for (let k = 0; k < 4; k++) { ev.push({ t, v: "saw", f: tn[k], dur: S16 * 2.2, cutoff: 2300, amp: 0.13 * gs, pan: (k - 1.5) * 0.3, room: 0.14, send: 0.1 }); LOG(t, tn[k], "stab"); }
      const gp = gate(data.G_SAWPAD, bf); if (gp > 0 && hstep.has(si)) CH[ch].pad.forEach((nm, k) => { const f = hz(nm) * 2; ev.push({ t, v: "saw", f, dur: chordEnd(t) - t, cutoff: 1500, att: 0.3, rel: 0.6, amp: 0.05 * gp, pan: (k - 1) * 0.45, send: 0.4 }); LOG(t, f, "sawpad"); });
    }
  }
  // ---- risers, rolls, impacts at the joints of the arrangement, and the harp sweeping up into the drop
  if (O.fx) {
    gliss(barT(9.3), ["D", "G", "A", "C"], 220, 1800, 30, 0.04, 0.08);
    fxe(barT(-5), "riser", 5 * BAR, 0.22, 0.3); fxe(barT(-2), "roll", 2 * BAR, 0.3, 0.15, { s16: S16 });
    fxe(fin0, "impact", 2.6, 1.2, 0.4); fxe(fin0, "riser", 2 * BAR, 0.15, 0.3, { f0: 400, f1: 7000 });
    fxe(barT(2), "impact", 1.8, 0.6, 0.35);
    fxe(barT(6.8), "riser", 3.2 * BAR, 0.22, 0.3); fxe(barT(9), "roll", 1.0 * BAR, 0.34, 0.15, { s16: S16 });
    fxe(barT(10), "impact", 3.2, 1.4, 0.45); ev.push({ t: barT(10), v: "clap", amp: 0.4, room: 0.3 });
    fxe(barT(16), "impact", 2.0, 0.4, 0.4); fxe(fin1 - 0.3, "impact", 4.2, 1.0, 0.5);
  }
  ev.sort((a, b) => a.t - b.t);
  // ---- the audit: every pitched note against the chord sounding at its start (the stone's own runs and glissandi are exempt, as in make_music)
  // the same rules as make_music.audit(): harp / hook: the chord's pentatonic and colour tone; tour rows and glissandi: also the key's scale; duduk: a long
  // note (1 s or more) the chord's set, a passing note any note of the key (or C#); bass: its root; the pedal: D or A; pads, stabs, saw pads and arpeggios: only the triad
  let outside = 0, checked = 0; const bad = [];
  for (const n of log) {
    if (n.kind === "cascade" || n.t > tl.cycle + 1) continue; checked++;
    const ch = chordAt(n.t + 0.001), c = CH[ch], scale = new Set(KEYS[keyAt(n.t + 0.001)]), set = new Set([...c.pent, ...c.tones, ...c.ext]), pc = pcOf(n.f);
    const allowed = n.kind === "harp" || n.kind === "hook" ? set : (n.kind === "row" || n.kind === "gliss") ? new Set([...scale, ...set]) : n.kind === "duduk" ? (n.dur >= 1.0 ? set : new Set([...scale, ...set, "C#"])) : n.kind === "bass" ? new Set([c.root]) : n.kind === "pedal" ? new Set(["D", "A"]) : new Set(c.tones);
    if (!allowed.has(pc)) { outside++; if (bad.length < 8) bad.push(`${n.kind} ${n.f.toFixed(1)} Hz (${pc}) at ${n.t.toFixed(2)} s over ${ch}`); }
  }
  // the dam's sub-D leaves the room while the bass plays (make_music.build_drone: d2_gain), and the level plan as piece-time points
  const sub = [[0, 1], [barT(barS(-27)), 1], [barT(barS(-17)), 0.12], [fin1, 0.12], [fin1 + 3, 1], [tl.cycle, 1]];
  const droneSub = p => { if (p <= sub[0][0]) return sub[0][1]; for (let i = 1; i < sub.length; i++) if (p <= sub[i][0]) return sub[i - 1][1] + (sub[i][1] - sub[i - 1][1]) * (p - sub[i - 1][0]) / Math.max(1e-9, sub[i][0] - sub[i - 1][0]); return sub[sub.length - 1][1]; };
  const plan = data.PLAN.map(q => ({ t: anchorT(q.at), lufs: q.lufs })).filter(q => q.t != null).sort((a, b) => a.t - b.t);
  return { events: ev, harm: HARM, log, audit: { checked, outside, bad }, groove: { startBar: g0, buildBars: -g0, stretch }, fin0, fin1, cycle: tl.cycle, droneSub, plan, layers: O };
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
// make_music's two impulse responses: decaying noise under a 2nd-order low-pass, a pre-delay, unit energy (the convolver's own normalisation is switched off)
const irs = new Map();
function irPair(ctx, rt60, hf, pre, seed) {
  const key = `${rt60}_${hf}_${ctx.sampleRate}`; if (irs.has(key)) return irs.get(key);
  const sr = ctx.sampleRate, n = Math.round(rt60 * 1.15 * sr), ir = ctx.createBuffer(2, n, sr);
  const w0 = 2 * Math.PI * hf / sr, al = Math.sin(w0) / (2 * 0.7071), cw = Math.cos(w0), b0 = (1 - cw) / 2, b1 = 1 - cw, a0 = 1 + al, a1 = -2 * cw, a2 = 1 - al;
  for (let c = 0; c < 2; c++) {
    const y = ir.getChannelData(c), r = mulberry32(seed + c), skip = Math.round(pre * (c ? 1.35 : 1) * sr); let x1 = 0, x2 = 0, y1 = 0, y2 = 0, e = 0;
    for (let i = 0; i < n; i++) { const t = i / sr, x = Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(2 * Math.PI * r()) * Math.exp(-6.9 * t / rt60), o = (b0 * x + b1 * x1 + b0 * x2 - a1 * y1 - a2 * y2) / a0; x2 = x1; x1 = x; y2 = y1; y1 = o; y[i] = i < skip ? 0 : o * Math.min(1, t / 0.015); e += y[i] * y[i]; }
    const k = 1 / Math.sqrt(e); for (let i = 0; i < n; i++) y[i] *= k;
  }
  irs.set(key, ir); return ir;
}

export class Voices {
  // cfg.cal: calibration (every stem at weight 1, no EQ, no sidechain, no reverb, no master chain: the dry stems exactly as a loudness meter should see them)
  // cfg.mix: one timeline's baked mix { w: weight per stem, master, ride: dB per 0.5 s of the piece, norm: peak per voice }; cfg.data: score_data.json (stem EQ, duck depths)
  constructor(ctx, dest, cfg = {}) {
    this.ctx = ctx; this.cal = !!cfg.cal; this.mix = cfg.mix || null; this.data = cfg.data || null; this.norm = cfg.norm || (cfg.mix && cfg.mix.norm) || {};
    const out = dest || ctx.destination; this.master = ctx.createGain(); this.master.gain.value = this.cal ? 1 : this.mix ? this.mix.master : 0.78;
    if (this.cal) this.master.connect(out);
    else {
      const pk = ctx.createBiquadFilter(); pk.type = "peaking"; pk.frequency.value = 380; pk.Q.value = 0.9; pk.gain.value = -2.5;             // a little out of the boxy 380 Hz, a little up above 3 kHz
      const hs = ctx.createBiquadFilter(); hs.type = "highshelf"; hs.frequency.value = 3200; hs.gain.value = 3;
      this.ride = ctx.createGain(); this.ride.gain.value = 1;
      const comp = ctx.createDynamicsCompressor(); comp.threshold.value = this.mix ? -2 : -14; comp.knee.value = this.mix ? 0 : 30; comp.ratio.value = this.mix ? 20 : 3; comp.attack.value = this.mix ? 0.003 : 0.01; comp.release.value = this.mix ? 0.15 : 0.25;
      this.master.connect(pk); pk.connect(hs); hs.connect(this.ride); this.ride.connect(comp); this.comp = comp;
      if (this.mix) { const sh = ctx.createWaveShaper(), cv = new Float32Array(4097); for (let i = 0; i < cv.length; i++) { const x = i / 2048 - 1, ab = Math.abs(x); cv[i] = Math.sign(x) * (ab < 0.8 ? ab : 0.8 + 0.2 * Math.tanh((ab - 0.8) / 0.2)); } sh.curve = cv; comp.connect(sh); sh.connect(out); }   // a ceiling after the limiter (the same curve as fx.js): linear to 0.8, then a tanh knee that never passes 1.0
      else comp.connect(out);
      this.revIn = ctx.createGain(); this.roomIn = ctx.createGain();
      for (const [inn, rt, hf, pre, seed] of [[this.revIn, 3.1, 4800, 0.016, 1], [this.roomIn, 0.5, 6500, 0.004, 3]]) { const cv = ctx.createConvolver(); cv.normalize = false; cv.buffer = irPair(ctx, rt, hf, pre, seed); const g = ctx.createGain(); g.gain.value = 0.9; inn.connect(cv); cv.connect(g); g.connect(this.master); }
    }
    this.stem = {};
    for (const nm of STEMS) {
      const w = this.cal ? 1 : this.mix && this.mix.w ? this.mix.w[nm] ?? 1 : 1, eq = !this.cal && this.data && this.data.STEM_EQ[nm], depth = !this.cal && this.data ? this.data.STEM_CFG[nm] : 0;
      const chain = to => { const head = ctx.createGain(); let node = head; if (eq) { const sh = ctx.createBiquadFilter(); sh.type = "highshelf"; sh.frequency.value = eq[0]; sh.gain.value = eq[1]; node.connect(sh); node = sh; } const duck = ctx.createGain(), wg = ctx.createGain(); wg.gain.value = w; node.connect(duck); duck.connect(wg); wg.connect(to); return { head, duck }; };
      this.stem[nm] = { dry: chain(this.master), depth, wet: this.cal ? null : chain(this.revIn), room: this.cal ? null : chain(this.roomIn) };
    }
    this.live = new Set();
  }
  // a voice's output: its own level, a mono send to the hall and the room (before the pan, as make_music does), then the pan into the stem bus
  out(pan = 0, send = 0, room = 0, stem = "harp") {
    const c = this.ctx, st = this.stem[stem], inp = c.createGain(), p = c.createStereoPanner(); p.pan.value = Math.max(-1, Math.min(1, pan)); inp.connect(p); p.connect(st.dry.head); inp._p = p;
    if (send && st.wet) { const s = c.createGain(); s.gain.value = send; inp.connect(s); s.connect(st.wet.head); inp._s = s; }
    if (room && st.room) { const s = c.createGain(); s.gain.value = room; inp.connect(s); s.connect(st.room.head); inp._r = s; }
    return inp;
  }
  // a finished voice is DISCONNECTED: otherwise every note's gain and panner stay in the graph and are processed on every block for the rest of the loop
  track(node, ...chain) { this.live.add(node); node.onended = () => { this.live.delete(node); for (const n of chain) { try { n.disconnect(); if (n._p) n._p.disconnect(); if (n._s) n._s.disconnect(); if (n._r) n._r.disconnect(); } catch (_) {} } }; return node; }
  stopAll(at) { for (const n of this.live) { try { n.stop(at); } catch (_) {} } this.live.clear(); for (const nm of STEMS) for (const k of ["dry", "wet", "room"]) { const s = this.stem[nm][k]; if (s) { s.duck.gain.cancelScheduledValues(at); s.duck.gain.setValueAtTime(1, at); } } }
  duck(at) { for (const nm of STEMS) { const st = this.stem[nm]; if (!st.depth) continue; for (const k of ["dry", "wet", "room"]) { const g = st[k] && st[k].duck.gain; if (g) { g.setValueAtTime(1 - st.depth, at); g.setTargetAtTime(1, at, 0.12); } } } }   // the kick pumps: 1 - depth at the hit, back with a 0.12 s time constant
  rideAt(p) { if (this.cal || !this.mix || !this.mix.ride) return; const r = this.mix.ride, x = Math.max(0, p / 0.5), i = Math.min(r.length - 1, Math.floor(x)), j = Math.min(r.length - 1, i + 1), db = r[i] + (r[j] - r[i]) * (x - i); this.ride.gain.setTargetAtTime(10 ** (db / 20), this.ctx.currentTime, 0.2); }
  rideCurve(t0, t1) { if (this.cal || !this.mix || !this.mix.ride) return; const r = this.mix.ride, n = Math.max(2, Math.ceil((t1 - t0) / 0.5)), a = new Float32Array(n); for (let i = 0; i < n; i++) a[i] = 10 ** (r[Math.min(r.length - 1, Math.round((t0 + i * 0.5) / 0.5))] / 20); this.ride.gain.setValueCurveAtTime(a, 0, t1 - t0); }
  subTo(level, at) { if (this.subGain) this.subGain.gain.setTargetAtTime(0.35 * level, at, 0.3); }
  sample(b, at, amp, pan, send, room, stem, rate = 1) { const s = this.ctx.createBufferSource(); s.buffer = b; s.playbackRate.value = rate; const g = this.ctx.createGain(); g.gain.value = amp; const p = this.out(pan, send, room, stem); s.connect(g); g.connect(p); s.start(at); this.track(s, s, g, p); }
  play(e, at, k = 1) {                                          // k: real seconds per piece second (1 / speed)
    const c = this.ctx, d = (e.dur || 0) * k, stem = stemOf(e), a = e.amp * (this.norm[e.v] ?? 1), P = e.pan || 0, S = e.send || 0, M = e.room || 0;
    switch (e.v) {
      case "kanun": return this.sample(kanunBuf(c, e.f, Math.max(0.3, Math.round(d * 10) / 10), e.tau || 1.5, e.bright || 1, e.click ?? 0.22), at, a, P, S, M, stem);
      case "glass": return this.sample(glassBuf(c, e.f, Math.max(0.3, Math.round(d * 10) / 10)), at, a, P, S, M, stem);
      case "plate": return this.sample(plateBuf(c, e.f, e.nm), at, a, P, S, M, stem);
      case "sand": return this.sample(sandBuf(c, e.n, e.seed), at, a, P, S, M, stem);
      case "duduk": return this.duduk(e, at, d, a);
      case "pad": return this.pad(e, at, d, a);
      case "saw": return this.saw(e, at, d, a);
      case "cluster": return this.cluster(e, at, d, a);
      case "fourier": return this.fourier(e, at, d, a);
      case "riser": return this.riser(e, at, d, a);
      case "roll": return this.roll(e, at, d, a);
      case "impact": return this.impact(e, at, d, a);
      case "bass": { const o = c.createOscillator(); o.type = "sawtooth"; o.frequency.value = e.f; const lp = c.createBiquadFilter(); lp.frequency.value = 380; const g = c.createGain(); g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(a * 0.5, at + 0.006); g.gain.setTargetAtTime(0, at + d, 0.03); const p = this.out(0, 0, 0, "bass"); o.connect(lp); lp.connect(g); g.connect(p); o.start(at); o.stop(at + d + 0.3); return this.track(o, o, lp, g, p); }
      case "kick": { if (e.duck) this.duck(at); const o = c.createOscillator(); o.frequency.setValueAtTime(120, at); o.frequency.exponentialRampToValueAtTime(45, at + 0.12); const g = c.createGain(); g.gain.setValueAtTime(a * 0.9, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.38); const p = this.out(0, 0, 0, "kick"); o.connect(g); g.connect(p); o.start(at); o.stop(at + 0.4); return this.track(o, o, g, p); }
      case "hat": case "ohat": case "clap": case "tek": { const s = c.createBufferSource(); s.buffer = noiseBuf(c); const f = c.createBiquadFilter(); f.type = e.v === "clap" ? "bandpass" : e.v === "tek" ? "bandpass" : "highpass"; f.frequency.value = e.v === "clap" ? 1300 : e.v === "tek" ? 3400 : 7000; f.Q.value = e.v === "tek" ? 2.5 : 0.8;
        const len = e.v === "ohat" ? 0.26 : e.v === "clap" ? 0.18 : e.v === "tek" ? 0.07 : 0.05, g = c.createGain(); g.gain.setValueAtTime(a, at); g.gain.exponentialRampToValueAtTime(0.001, at + len); const p = this.out(P, e.v === "clap" ? 0.2 : 0.05, M, "perc"); s.connect(f); f.connect(g); g.connect(p); s.start(at, (e.t * 7.31) % 1.5); s.stop(at + len + 0.02); return this.track(s, s, f, g, p); }
      case "dum": { const o = c.createOscillator(); o.frequency.setValueAtTime(95, at); o.frequency.exponentialRampToValueAtTime(62, at + 0.2); const g = c.createGain(); g.gain.setValueAtTime(a, at); g.gain.exponentialRampToValueAtTime(0.001, at + 0.32); const p = this.out(P, 0.12, M, "perc"); o.connect(g); g.connect(p); o.start(at); o.stop(at + 0.35); return this.track(o, o, g, p); }
    }
  }
  duduk(e, at, d, a) {
    const c = this.ctx, o = c.createOscillator(), rel = e.rel ?? 0.45; o.setPeriodicWave(reedWave(c, e.f)); o.frequency.value = e.f;
    const cents = r => 1200 * Math.log2(r);
    if (e.from && Math.abs(cents(e.from / e.f)) <= 320) { o.detune.setValueAtTime(cents(e.from / e.f), at); o.detune.linearRampToValueAtTime(0, at + 0.07); }
    else if (e.scoop) { o.detune.setValueAtTime(-90, at); o.detune.linearRampToValueAtTime(0, at + 0.16); }
    if (e.grace) { o.detune.setValueAtTime(cents(e.grace / e.f), at); o.detune.setValueAtTime(cents(e.grace / e.f), at + 0.085); o.detune.linearRampToValueAtTime(0, at + 0.12); }
    if (e.mord) { o.detune.setValueAtTime(0, at + 0.05); o.detune.setValueAtTime(cents(e.mord / e.f), at + 0.05); o.detune.setValueAtTime(0, at + 0.10); }
    const lfo = c.createOscillator(); lfo.frequency.value = 5.3; const depth = c.createGain(); depth.gain.setValueAtTime(0, at); depth.gain.setValueAtTime(0, at + 0.45); depth.gain.linearRampToValueAtTime(11 * e.vib, at + 0.95); lfo.connect(depth); depth.connect(o.detune);
    const env = c.createGain(); env.gain.setValueAtTime(0, at); env.gain.setTargetAtTime(a, at, 0.07); env.gain.setTargetAtTime(0, at + d, rel / 4.5);
    const hp = c.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 130;
    const br = c.createBufferSource(); br.buffer = noiseBuf(c); const bp = c.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 1450; bp.Q.value = 0.8;
    const bg = c.createGain(); bg.gain.setValueAtTime(0, at); bg.gain.linearRampToValueAtTime(0.03 * 3.2 * a, at + 0.03); bg.gain.setTargetAtTime(0.03 * a, at + 0.03, 0.12); bg.gain.setTargetAtTime(0, at + d, 0.1);
    const p = this.out(e.pan, e.send, e.room || 0, "duduk"); o.connect(env); env.connect(hp); br.connect(bp); bp.connect(bg); bg.connect(hp); hp.connect(p);
    const end = at + d + rel * 1.3; o.start(at); lfo.start(at); br.start(at, (e.t * 3.17) % 1.5); o.stop(end); lfo.stop(end); br.stop(end);
    this.track(o, o, env, hp, p); this.track(lfo, lfo, depth); this.track(br, br, bp, bg);
  }
  pad(e, at, d, a) {
    const c = this.ctx, lp = c.createBiquadFilter(); lp.frequency.value = 1500; const env = c.createGain(), att = e.att ?? 1.2, rel = e.rel ?? 1.4, hold = Math.max(att, d);
    env.gain.setValueAtTime(0, at); env.gain.linearRampToValueAtTime(a, at + att); env.gain.setValueAtTime(a, at + hold); env.gain.linearRampToValueAtTime(0, at + hold + rel);
    const p = this.out(e.pan, e.send, e.room || 0, "pad"); lp.connect(env); env.connect(p);
    [[-3, 0.22], [0, 1], [3, 0.22]].forEach(([dt, vg], j) => { const o = c.createOscillator(); o.setPeriodicWave(triWave(c)); o.frequency.value = e.f; o.detune.value = dt; const g = c.createGain(); g.gain.value = vg / 1.44; o.connect(g); g.connect(lp); o.start(at); o.stop(at + hold + rel + 0.1); if (j === 2) this.track(o, o, g, lp, env, p); else this.track(o, o, g); });
  }
  saw(e, at, d, a) {                                            // make_music.supersaw: seven detuned saws (-20 .. +20 cents) under a 2nd-order low-pass, a short attack, a release of rel / 4
    const c = this.ctx, lp = c.createBiquadFilter(), env = c.createGain(), att = e.att ?? 0.012, rel = e.rel ?? 0.12; lp.type = "lowpass"; lp.frequency.value = e.cutoff || 2600; lp.Q.value = -3;
    env.gain.setValueAtTime(0, at); env.gain.linearRampToValueAtTime(a, at + att); env.gain.setValueAtTime(a, at + Math.max(att, d)); env.gain.setTargetAtTime(0, at + Math.max(att, d), rel / 4);
    const p = this.out(e.pan, e.send, e.room || 0, "saw"); lp.connect(env); env.connect(p); const end = at + Math.max(att, d) + rel * 1.6 + 0.05;
    [-20, -11, -4, 0, 4, 11, 20].forEach((dt, j) => { const o = c.createOscillator(); o.type = "sawtooth"; o.frequency.value = e.f; o.detune.value = dt; const g = c.createGain(); g.gain.value = 1 / 7; o.connect(g); g.connect(lp); o.start(at); o.stop(end); if (j === 6) this.track(o, o, g, lp, env, p); else this.track(o, o, g); });
  }
  cluster(e, at, d, a) {                                        // anneal: five triangle waves start spread over 26 cents and settle to a unison as the temperature falls
    const c = this.ctx, lp = c.createBiquadFilter(), env = c.createGain(); lp.frequency.value = 2200; env.gain.setValueAtTime(0, at); env.gain.linearRampToValueAtTime(a, at + 0.6); env.gain.setValueAtTime(a, at + Math.max(0.6, d - 0.6)); env.gain.linearRampToValueAtTime(0, at + d);
    const p = this.out(e.pan, e.send, 0, "pad"); lp.connect(env); env.connect(p);
    for (let kk = 0; kk < 5; kk++) { const o = c.createOscillator(); o.type = "triangle"; o.frequency.value = e.f; const cur = new Float32Array(24).map((_, i) => 26 * (e.curve ? e.curve[Math.round(i / 23 * (e.curve.length - 1))] : (1 - i / 23) ** 2) * (kk - 2) / 2); o.detune.setValueCurveAtTime(cur, at, Math.max(0.1, d)); const g = c.createGain(); g.gain.value = 0.2; o.connect(g); g.connect(lp); o.start(at); o.stop(at + d + 0.1); if (kk === 4) this.track(o, o, g, lp, env, p); else this.track(o, o, g); }
  }
  fourier(e, at, d, a) {                                        // the Fourier act: a tone of D whose partials (D and A only) arrive one by one, each with its own phase
    const c = this.ctx, env = c.createGain(); env.gain.setValueAtTime(0, at); env.gain.linearRampToValueAtTime(a, at + 0.4); env.gain.setValueAtTime(a, at + Math.max(0.4, d - 0.5)); env.gain.linearRampToValueAtTime(0, at + d);
    const p = this.out(e.pan || 0, e.send, 0, "pad"); env.connect(p); const dfo = d - 0.8;
    e.hs.forEach((h, j) => { const re = new Float32Array(2), im = new Float32Array(2); re[1] = Math.sin(e.phs[j]); im[1] = Math.cos(e.phs[j]); const o = c.createOscillator(); o.setPeriodicWave(c.createPeriodicWave(re, im, { disableNormalization: true })); o.frequency.value = (e.f || D3) * h;
      const on = 0.1 + dfo * 0.75 * j / 7, g = c.createGain(), curve = new Float32Array(48).map((_, i) => e.mags[j] * h ** -0.4 * (0.5 + 0.5 * Math.tanh((i / 47 * d - on) / 0.25))); g.gain.setValueCurveAtTime(curve, at, d); o.connect(g); g.connect(env); o.start(at); o.stop(at + d + 0.1); if (j === 7) this.track(o, o, g, env, p); else this.track(o, o, g); });
  }
  riser(e, at, d, a) {                                          // swelling band-passed noise: one band sweeping f0 to f1 (make_music mixes twenty), level rising as u^2.2
    const c = this.ctx, s = c.createBufferSource(); s.buffer = noiseBuf(c); s.loop = true; const bp = c.createBiquadFilter(); bp.type = "bandpass"; bp.Q.value = 1.7; bp.frequency.setValueAtTime(e.f0 || 300, at); bp.frequency.exponentialRampToValueAtTime(e.f1 || 9000, at + d);
    const g = c.createGain(); g.gain.setValueCurveAtTime(new Float32Array(64).map((_, i) => a * (i / 63) ** 2.2), at, d); const p = this.out(0, e.send, 0, "fx"); s.connect(bp); bp.connect(g); g.connect(p); s.start(at, 0); s.stop(at + d + 0.04); this.track(s, s, bp, g, p);
  }
  roll(e, at, d, a) {                                           // a snare roll: noise hits that speed up (every 16th, then 32nds, then 64ths), louder towards the end
    const c = this.ctx, s = c.createBufferSource(); s.buffer = noiseBuf(c); s.loop = true; const bp = c.createBiquadFilter(); bp.type = "bandpass"; bp.frequency.value = 3500; bp.Q.value = 0.6; const g = c.createGain(); g.gain.value = 0;
    const kk = d / e.dur; let t = 0;
    while (t < e.dur) { const T = at + t * kk; g.gain.setValueAtTime((0.25 + 0.75 * t / e.dur) * a, T); g.gain.setTargetAtTime(0, T + 0.002, 0.025 * kk); t += e.s16 * (t < e.dur * 0.5 ? 1.0 : t < e.dur * 0.8 ? 0.5 : 0.25); }
    const p = this.out(0, e.send, 0, "fx"); s.connect(bp); bp.connect(g); g.connect(p); s.start(at, 0); s.stop(at + d + 0.1); this.track(s, s, bp, g, p);
  }
  impact(e, at, d, a) {                                         // a low boom: a sine falling from 82 to 30 Hz with a dark noise burst
    const c = this.ctx, o = c.createOscillator(), g = c.createGain(), n = c.createBufferSource(), lp = c.createBiquadFilter(), ng = c.createGain(); n.buffer = noiseBuf(c); lp.frequency.value = 900;
    o.frequency.setValueCurveAtTime(new Float32Array(48).map((_, i) => 30 + 52 * Math.exp(-(i / 47 * Math.min(d, 4)) / 0.9)), at, Math.min(d, 4));
    g.gain.setValueAtTime(a, at); g.gain.setTargetAtTime(0, at, 0.8); ng.gain.setValueAtTime(a * 0.5, at); ng.gain.setTargetAtTime(0, at, 0.5);
    const p = this.out(0, e.send, 0, "fx"); o.connect(g); g.connect(p); n.connect(lp); lp.connect(ng); ng.connect(p); o.start(at); o.stop(at + d); n.start(at, 0); n.stop(at + Math.min(d, 2.5)); this.track(o, o, g, p); this.track(n, n, lp, ng);
  }
  drone(at, level = 0.07) {                                     // the dam: a second duduk holding D3 and A3, with a sub-D; it breathes slowly
    const c = this.ctx, g = c.createGain(); g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(level, at + 2.5); g.connect(this.out(0, 0.25, 0, "drone"));
    const parts = [[D3, 1, 22], [D3 * 1.5, 0.45, 10]];
    for (const [f, a, nmax] of parts) { const o = c.createOscillator(); o.setPeriodicWave(reedWave(c, f, nmax, 4200, 3400)); o.frequency.value = f; const og = c.createGain(); og.gain.value = a; const lfo = c.createOscillator(); lfo.frequency.value = 0.09 + a * 0.02; const lg = c.createGain(); lg.gain.value = 0.08 * a; lfo.connect(lg); lg.connect(og.gain); o.connect(og); og.connect(g); o.start(at); lfo.start(at); this.track(o); this.track(lfo); }
    const sub = c.createOscillator(); sub.frequency.value = D3 / 2; const sg = c.createGain(); sg.gain.value = 0.35; sub.connect(sg); sg.connect(g); sub.start(at); this.track(sub);
    this.droneGain = g; this.subGain = sg; return g;
  }
}

// ------------------------------------------------------------------ the player: schedules the score against a piece clock (its own, or the director's)
export class Player {
  constructor(ctx, score, voices) { this.ctx = ctx; this.s = score; this.v = voices; this.idx = 0; this.on = false; this.speed = 1; this.p0 = 0; this.a0 = 0; this.timer = null; this.lastRide = -1; }
  pieceNow() { return this.p0 + (this.ctx.currentTime - this.a0) * this.speed; }
  seekIdx(p) { const E = this.s.events; let lo = 0, hi = E.length; while (lo < hi) { const m = (lo + hi) >> 1; if (E[m].t < p) lo = m + 1; else hi = m; } this.idx = lo; }
  start(p, speed = 1) {
    this.stop(); this.on = true; this.speed = speed; this.p0 = p; this.a0 = this.ctx.currentTime + 0.05; this.seekIdx(p);
    this.v.drone(this.a0); this.v.subTo(this.s.droneSub(p), this.a0); this.timer = setInterval(() => this.tick(), 25); this.tick();
  }
  follow(p, speed) {                                             // the director's clock (called ~10 times a second)
    this.external = true;
    if (!this.on) return this.start(p, speed);
    const now = this.ctx.currentTime;
    if (speed !== this.speed) { this.p0 = this.pieceNow(); this.a0 = now; this.speed = speed; }         // a new speed: new mapping, the sounding notes go on
    const drift = this.pieceNow() - p;
    if (Math.abs(drift) > 0.5) { this.v.stopAll(now + 0.02); this.p0 = p; this.a0 = now + 0.03; this.seekIdx(p); this.v.drone(this.a0); this.v.subTo(this.s.droneSub(p), this.a0); }   // a seek or the loop
    else if (Math.abs(drift) > 0.02) this.p0 -= drift * 0.5;                                           // a little drift: ease the mapping, no cut
  }
  stop() { this.on = false; clearInterval(this.timer); this.v.stopAll(this.ctx.currentTime + 0.01); }
  tick() {
    if (!this.on) return;
    const E = this.s.events, p = this.pieceNow(), horizon = p + 0.25 * this.speed, k = 1 / this.speed, now = this.ctx.currentTime;
    while (this.idx < E.length && E[this.idx].t < horizon) { const e = E[this.idx++]; const at = this.a0 + (e.t - this.p0) * k; if (at >= now - 0.01) this.v.play(e, Math.max(at, now), k); }
    if (now - this.lastRide > 0.1) { this.lastRide = now; this.v.rideAt(p); this.v.subTo(this.s.droneSub(p), now); }              // the level plan and the dam's sub follow the piece clock
    if (!this.external && this.idx >= E.length && p >= this.s.cycle) { const over = p - this.s.cycle; this.start(over, this.speed); }    // the loop
  }
}

// ------------------------------------------------------------------ offline render (for measurement: speed, loudness by second; o.cal and o.stems for the calibration)
export async function renderOffline(score, t0, t1, sr = 32000, o = {}) {
  const n = Math.ceil((t1 - t0 + 1) * sr), ctx = new OfflineAudioContext(2, n, sr), v = new Voices(ctx, ctx.destination, { cal: o.cal, mix: o.mix, data: o.data, norm: o.norm });
  const want = e => !o.stems || o.stems.has(stemOf(e));
  if (!o.stems || o.stems.has("drone")) {
    v.drone(0); const m = Math.max(2, Math.ceil((t1 - t0) / 0.5)), cur = new Float32Array(m).map((_, i) => 0.35 * score.droneSub(t0 + i * 0.5)); v.subGain.gain.setValueCurveAtTime(cur, 0, t1 - t0);
  }
  v.rideCurve(t0, t1);
  let prep = 0, i = 0; const E = score.events.filter(e => e.t >= t0 && e.t < t1 && want(e)), SL = 2.0;
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
