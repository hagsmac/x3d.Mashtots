// conductor.js: the "dazzle" layer. A seeded plan of time effects laid over the Landing's timeline, different on every loop.
//
// The scene's time is the page's V (see stage.html). Each frame the conductor says by how much to scale the speed (`mult`), whether to jump V
// (an instant replay) and whether to cut to another viewpoint. Nothing here touches the scene or the maths of an act: act time stays monotonic
// except in a replay, which simply shows the same computed frames again. The live score follows V and the rate, so a dilation is also heard.
//
// Effects (all in the page's own seconds, never baked):
//   dip     a smooth slow-motion bell: the rate falls to `depth` and comes back
//   surge   a smooth time-lapse bell: the rate rises to `gain`
//   freeze  a hit-stop: the rate falls to ~0.05 for a fraction of a second, then eases back
//   echo    an instant replay: V jumps back `back` s and replays at `rate`, then carries on from where it was
//   cut     a flash-cut to another named viewpoint (Cam, CamHelix, CamRing, CamStone) for `dur` s
//   replay  a MOMENT replay (see MOMENTS): the moment plays once as the piece has it, then comes back at 0.3 to 0.7x, usually from another camera
//   wobble  the rate breathes around 1 for the length of an act (annealing's heat, the walk)
//
// Plans are generated from (seed, level) and the timeline's segment names, so they follow any preset. Same seed, same plan.

export function mulberry32(a) {
  return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}

export const LEVELS = {
  off:    { n: [0, 0],   kinds: {} },
  subtle: { n: [3, 4],   moments: [0, 0], kinds: { dip: 3, surge: 1 },                              depth: [0.40, 0.70], dur: [1.6, 2.6] },
  dazzle: { n: [6, 8],   moments: [1, 2], kinds: { dip: 4, surge: 2, freeze: 2, echo: 2, cut: 2, wobble: 2 }, depth: [0.15, 0.60], dur: [1.2, 2.6] },
  wild:   { n: [10, 13], moments: [3, 4], kinds: { dip: 4, surge: 3, freeze: 3, echo: 3, cut: 4, wobble: 3 }, depth: [0.08, 0.50], dur: [0.9, 2.4] },
};

// Where something worth catching happens, by segment name: fraction of the segment, which effects suit it, a weight.
// (Fractions, not seconds, so a re-timed preset keeps the intent. Segments the preset lacks are skipped.)
export const POOL = [
  { seg: 'flight',   f: [0.30, 0.95], kinds: ['dip', 'freeze', 'cut', 'echo'], w: 3, label: 'the letters leave the stone' },
  { seg: 'line',     f: [0.20, 0.90], kinds: ['dip', 'surge'],                 w: 1, label: 'the line' },
  { seg: 'lift',     f: [0.40, 0.90], kinds: ['echo', 'freeze', 'cut'],        w: 4, label: 'the helix lifts' },
  { seg: 'tour',     f: [0.04, 0.96], kinds: ['dip', 'echo', 'freeze', 'surge', 'cut'], w: 6, label: 'one letter of the 36' },
  { seg: 'write',    f: [0.10, 0.90], kinds: ['dip', 'freeze'],                w: 2, label: 'the ink order' },
  { seg: 'prayer',   f: [0.20, 0.80], kinds: ['dip'],                          w: 1, label: 'the prayer' },
  { seg: 'numerals', f: [0.30, 0.80], kinds: ['dip'],                          w: 1, label: 'numerals' },
  { seg: 'space',    f: [0.10, 0.85], kinds: ['dip', 'cut', 'echo'],           w: 2, label: 'the embedding turns' },
  { seg: 'svdm',     f: [0.20, 0.95], kinds: ['dip', 'freeze', 'cut', 'echo'], w: 3, label: 'the measured SVD plane' },
  { seg: 'tokens',   f: [0.25, 0.95], kinds: ['dip', 'freeze', 'cut', 'echo'], w: 3, label: 'the letters in tokenizer space' },
  { seg: 'web',      f: [0.30, 0.95], kinds: ['dip', 'surge'],                 w: 2, label: 'the 630 chords' },
  { seg: 'msg',      f: [0.05, 0.50], kinds: ['dip', 'echo', 'freeze'],        w: 3, label: 'the first hop from Ճ' },
  { seg: 'spectral', f: [0.30, 0.95], kinds: ['dip', 'freeze', 'echo'],        w: 3, label: 'the Fiedler cut' },
  { seg: 'vowels',   f: [0.15, 0.90], kinds: ['dip', 'freeze', 'cut', 'echo'], w: 4, label: 'the measured vowels lift' },
  { seg: 'pagerank', f: [0.10, 0.90], kinds: ['dip', 'surge', 'echo'],         w: 2, label: 'rank flows' },
  { seg: 'anneal',   f: [0.00, 1.00], kinds: ['wobble'],                       w: 2, label: 'the heat' },
  { seg: 'descent',  f: [0.30, 0.90], kinds: ['surge', 'dip'],                 w: 1, label: 'gradient descent' },
  { seg: 'walk',     f: [0.40, 1.00], kinds: ['surge', 'wobble'],              w: 1, label: 'the Markov walk' },
  { seg: 'fourier',  f: [0.20, 0.90], kinds: ['dip', 'echo', 'freeze', 'cut'], w: 4, label: 'epicycles redraw the curve' },
  { seg: 'poincare', f: [0.15, 0.90], kinds: ['dip', 'echo', 'cut'],           w: 3, label: 'the Poincaré disk' },
  { seg: 'svd',      f: [0.15, 0.90], kinds: ['dip', 'echo', 'freeze', 'cut'], w: 3, label: 'SVD and k-means' },
  { seg: 'collapse', f: [0.30, 0.90], kinds: ['freeze'],                      w: 3, label: 'the collapse' },
  { seg: 'finale',   f: [0.10, 0.90], kinds: ['dip'],                          w: 1, label: 'the finale' },
  { seg: 'return',   f: [0.15, 0.85], kinds: ['dip', 'cut'],                   w: 2, label: 'the return' },
];

export const VIEWS = ['CamHelix', 'CamRing', 'CamStone'];
const BAR = 1.875;                                              // s, one bar of the 128 BPM groove (live-score/score_data.json)
const LETTERS = 'ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ';

// The brilliant moments: the ones that last two seconds and, without this layer, are seen once per loop at one pace from one angle.
// `at` is where the moment ENDS (fraction f of segment `seg`, or a bar of the finale); `len` is how much of it is replayed (s);
// `p` is the chance that a loop replays it at all (so some only appear on some loops); `rate` the replay speed range.
// `letter: true` picks a different letter of the tour on every loop: the plate you may never see slowed again.
export const MOMENTS = [
  { id: 'lift',     seg: 'lift',     f: 0.72, len: 2.2, p: 0.85, rate: [0.30, 0.45], label: 'the helix lifts' },
  { id: 'stone',    seg: 'flight',   f: 0.85, len: 2.4, p: 0.50, rate: [0.35, 0.55], label: 'the letters settle on the line' },
  { id: 'plate',    seg: 'tour',     letter: true, len: 1.9, p: 0.90, rate: [0.30, 0.50], label: 'the plate of' },
  { id: 'svdm',     seg: 'svdm',     f: 0.50, len: 2.4, p: 0.50, rate: [0.30, 0.50], label: 'k-means finds the vowels' },
  { id: 'tokens',   seg: 'tokens',   f: 0.62, len: 2.6, p: 0.55, rate: [0.30, 0.50], label: 'the letters settle into tokenizer space' },
  { id: 'hop',      seg: 'msg',      f: 0.20, len: 2.0, p: 0.60, rate: [0.30, 0.50], label: 'the first hop from Ճ' },
  { id: 'cut',      seg: 'spectral', f: 0.90, len: 2.2, p: 0.60, rate: [0.30, 0.50], label: 'the Fiedler cut' },
  { id: 'vowels',   seg: 'vowels',   f: 0.55, len: 2.5, p: 0.70, rate: [0.30, 0.50], label: 'the vowels lift out of the ring' },
  { id: 'rank',     seg: 'pagerank', f: 0.55, len: 2.0, p: 0.40, rate: [0.35, 0.55], label: 'rank flows' },
  { id: 'fourier',  seg: 'fourier',  f: 0.45, len: 2.0, p: 0.45, rate: [0.35, 0.55], label: 'the epicycles redraw the curve' },
  { id: 'poincare', seg: 'poincare', f: 0.50, len: 2.2, p: 0.35, rate: [0.35, 0.55], label: 'chords become geodesics' },
  { id: 'svd',      seg: 'svd',      f: 0.55, len: 2.2, p: 0.40, rate: [0.35, 0.55], label: 'k-means settles' },
  { id: 'collapse', seg: 'collapse', f: 0.85, len: 1.2, p: 0.50, rate: [0.30, 0.50], label: 'the collapse' },
  { id: 'drop',     seg: 'finale',   bar: 10,   len: 1.5, p: 0.30, rate: [0.50, 0.70], label: 'into the drop' },   // the groove slows too: kept mild and rare
  { id: 'return',   seg: 'return',   f: 0.40, len: 2.0, p: 0.30, rate: [0.35, 0.55], label: 'the letters fall home' },
];

export class Conductor {
  constructor(segs, cycle, { level = 'dazzle', seed = null } = {}) {
    this.segs = segs; this.cycle = cycle; this.level = LEVELS[level] ? level : 'dazzle';
    this.span = n => { const p = segs.filter(s => s.name === n); return p.length ? [p[0].r0, p[p.length - 1].r0 + p[p.length - 1].dur] : null; };
    this.reseed(seed);
  }

  setLevel(level) { if (LEVELS[level]) { this.level = level; this.plan(this.seed); } }
  reseed(seed) { this.seed = (seed == null ? Math.floor(Math.random() * 1e6) : seed) >>> 0; this.plan(this.seed); }

  // ---- the plan ----------------------------------------------------------------------------------------------------------------------
  plan(seed) {
    const L = LEVELS[this.level], rnd = mulberry32(seed), pick = (a, b) => a + (b - a) * rnd();
    this.events = []; this.active = []; this.echo = null; this.cutUntil = 0; this.lastV = null; this.log = [];
    if (!L.n[1]) return;
    const n = L.n[0] + Math.floor(rnd() * (L.n[1] - L.n[0] + 1));
    const pool = POOL.filter(p => this.span(p.seg));
    const kindsOK = new Set(Object.keys(L.kinds));
    const used = [];
    // the moment replays first: a weighted draw (chance p per loop), no more than the level allows, never two close together
    if (L.moments && L.moments[1]) {
      const want = L.moments[0] + Math.floor(rnd() * (L.moments[1] - L.moments[0] + 1));
      const cand = MOMENTS.filter(m => this.span(m.seg) && rnd() < Math.min(1, m.p * 1.15));
      for (let i = cand.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [cand[i], cand[j]] = [cand[j], cand[i]]; }     // Fisher-Yates: the same plan in every engine
      for (const m of cand) {
        if (this.events.length >= want) break;
        const [s0, s1] = this.span(m.seg);
        let at, label = m.label;
        if (m.letter) { const i = 2 + Math.floor(rnd() * 32); at = s0 + (i + 1) * (s1 - s0) / 36; label = `${m.label} ${LETTERS[i]}`; }
        else if (m.bar != null) at = s0 + m.bar * BAR;
        else at = s0 + (s1 - s0) * m.f;
        if (at < 2.0 + m.len || at > this.cycle - 2.0 || used.some(u => Math.abs(u - at) < 6.5)) continue;
        used.push(at);
        const view = rnd() < 0.75 ? VIEWS[Math.floor(rnd() * VIEWS.length)] : '';       // usually from another camera
        this.events.push({ at, kind: 'replay', seg: m.seg, label, fired: false, back: m.len, rate: pick(...m.rate), view, moment: m.id });
      }
    }
    let guard = 0;
    const nMoments = this.events.length;
    while (this.events.length - nMoments < n && guard++ < 400) {
      // a weighted draw of a place, then an effect that suits it and this level
      const tot = pool.reduce((a, p) => a + p.w, 0); let r = rnd() * tot, p = pool[0];
      for (const q of pool) { r -= q.w; if (r <= 0) { p = q; break; } }
      const ks = p.kinds.filter(k => kindsOK.has(k)); if (!ks.length) continue;
      const kt = ks.reduce((a, k) => a + L.kinds[k], 0); let kr = rnd() * kt, kind = ks[0];
      for (const k of ks) { kr -= L.kinds[k]; if (kr <= 0) { kind = k; break; } }
      const [s0, s1] = this.span(p.seg), at = s0 + (s1 - s0) * pick(p.f[0], p.f[1]);
      if (at < 2.0 || at > this.cycle - 2.0) continue;                                   // leave the first and last seconds alone
      if (used.some(u => Math.abs(u - at) < 6.5)) continue;                              // room between effects
      used.push(at);
      const ev = { at, kind, seg: p.seg, label: p.label, fired: false };
      if (kind === 'dip')    { ev.depth = pick(...L.depth); ev.dur = pick(...L.dur); }
      if (kind === 'surge')  { ev.gain = pick(1.8, this.level === 'wild' ? 3.2 : 2.4); ev.dur = pick(1.4, 3.0); }
      if (kind === 'freeze') { ev.dur = pick(0.35, 0.8); }
      if (kind === 'echo')   { ev.back = pick(1.3, 2.6); ev.rate = pick(0.3, 0.55); }
      if (kind === 'cut')    { ev.view = VIEWS[Math.floor(rnd() * VIEWS.length)]; ev.dur = pick(0.9, 1.8); }
      if (kind === 'wobble') { ev.span = [s0, s1]; ev.amp = pick(0.25, 0.45); ev.freq = pick(0.5, 1.1); ev.phase = rnd() * 6.283; ev.at = s0; }
      this.events.push(ev);
    }
    this.events.sort((a, b) => a.at - b.at);
  }

  // Seeks and loop wraps re-arm the plan: whatever lies behind the new position counts as done.
  rearm(V) { for (const e of this.events) e.fired = e.at < V - 0.05 && e.kind !== 'wobble'; this.active = []; this.echo = null; this.cutUntil = 0; this.resetView = true; }

  // ---- every frame: V is the page's current time, dt the frame time in seconds -----------------------------------------------------------
  // returns { mult, jump, view, note } ; jump is a new V (an echo), view a viewpoint name or '' (back to the scene's own), note a label for a chip.
  step(V, dt) {
    const out = { mult: 1, jump: null, view: null, note: null, fx: null };
    if (this.resetView) { this.resetView = false; out.view = ''; }
    if (!this.events.length) return out;
    if (this.lastV !== null && V < this.lastV - this.cycle / 2) { this.loopEnded = true; }     // wrapped
    this.lastV = V;
    // fire what V has reached
    for (const e of this.events) {
      if (e.fired || e.kind === 'wobble') continue;
      if (V >= e.at && V < e.at + 1.2) {
        e.fired = true; out.note = `${e.kind} · ${e.label}`; this.log.push(`${e.kind}@${e.at.toFixed(1)}`);
        out.fx = { kind: e.kind, dur: e.dur, back: e.back, rate: e.rate, depth: e.depth, gain: e.gain };      // what to sound (fx.js)
        if (e.kind === 'echo' || e.kind === 'replay') {
          this.echo = { ...e, target: e.at, left: e.back / e.rate * 2 + 3 }; out.jump = Math.max(0, e.at - e.back);
          out.note = `${e.kind} · ${e.label}`; if (e.view) out.view = e.view;
        }
        else if (e.kind === 'cut') { this.cutUntil = e.dur; out.view = e.view; }
        else this.active.push({ ...e, u: 0 });
      } else if (V >= e.at + 1.2) e.fired = true;
    }
    // the effects in progress
    let m = 1;
    for (const a of this.active) {
      a.u += dt; const x = Math.min(1, a.u / a.dur), bell = Math.sin(Math.PI * x) ** 2;       // 0 .. 1 .. 0
      if (a.kind === 'dip') m = Math.min(m, 1 - (1 - a.depth) * bell);
      else if (a.kind === 'surge') m = Math.max(m, 1 + (a.gain - 1) * bell);
      else if (a.kind === 'freeze') m = Math.min(m, 1 - 0.95 * Math.sin(Math.PI * Math.min(1, a.u / (a.dur * 1.6))) ** 0.5);
    }
    this.active = this.active.filter(a => a.u < (a.kind === 'freeze' ? a.dur * 1.6 : a.dur));
    for (const e of this.events) if (e.kind === 'wobble' && V >= e.span[0] && V < e.span[1]) {
      const x = (V - e.span[0]) / (e.span[1] - e.span[0]), env = Math.sin(Math.PI * x);
      m *= 1 + e.amp * env * Math.sin(e.phase + 6.283 * e.freq * (V - e.span[0]));
    }
    // the replay: slow, until V is back where the jump started, then forward at full rate (V never passes the echo again)
    if (this.echo) {
      const Vc = out.jump != null ? out.jump : V;
      if (Vc >= this.echo.target) { if (this.echo.view) out.view = ''; this.echo = null; }
      else { m = this.echo.rate; this.echo.left -= dt; if (this.echo.left < 0) { if (this.echo.view) out.view = ''; this.echo = null; } }
    }
    if (this.cutUntil > 0) { this.cutUntil -= dt; if (this.cutUntil <= 0) out.view = ''; }
    out.mult = Math.max(0.04, m);
    return out;
  }

  describe() { return this.events.map(e => `${e.at.toFixed(1)}s ${e.kind} ${e.seg}${e.kind === 'replay' ? ' [' + e.label + (e.view ? ', ' + e.view : '') + ']' : ''}`).join(', '); }
}
