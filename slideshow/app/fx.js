// fx.js: the sound of time dilation. The live score is synthesised from the timeline, so when the dazzle layer slows or jumps the clock the NOTES stretch (their
// pitch stays); this module adds what a tape machine or a scrubbed reel would add:
//   * a master low-pass that follows the playback rate (slow = duller, as a slowed reel is), with a small gain dip at a near-stop
//   * tapeStop  (freeze)   a falling saw + noise sweep and a soft thump: the reel losing speed
//   * rewind    (echo / replay) a rising filtered-noise scrub with a high zip, panned left to right: the reel wound back to the start of the replay
//   * riser     (surge)    a swelling band-pass noise and a rising sine
//   * sink      (dip)      a low falling sine and a dark swoosh
//   * tick      (cut)      a short high click
// Everything is oscillators and one noise buffer (no samples). Works on a live AudioContext and on an OfflineAudioContext (see fx_measure.html).
// Nothing here has been listened to by its author; the levels were chosen from measurements (peak, spectral movement), see README.

let NZ = null;
function noiseBuffer(ctx) {
  if (NZ && NZ.sampleRate === ctx.sampleRate) return NZ;
  NZ = ctx.createBuffer(1, Math.round(ctx.sampleRate * 2), ctx.sampleRate);
  const y = NZ.getChannelData(0); let a = 12345;
  for (let i = 0; i < y.length; i++) { a = (a * 1664525 + 1013904223) >>> 0; y[i] = (a / 4294967296) * 2 - 1; }    // a fixed LCG: the same noise everywhere
  return NZ;
}
const expTo = (p, v0, v1, t0, d) => { p.setValueAtTime(v0, t0); p.exponentialRampToValueAtTime(Math.max(v1, 1e-4), t0 + d); };

export class TapeFx {
  constructor(ctx, { level = 0.5, dest = null } = {}) {
    this.ctx = ctx; this.on = true; this.rate = 1;
    const final = dest || ctx.destination;
    // a ceiling, not a compressor (a compressor swallowed the 30 ms click, measured): linear up to 0.8, then a tanh knee that never passes 1.0, so the music's own -1.6 dBFS peaks
    // are untouched and music plus effects together cannot clip
    const out = ctx.createWaveShaper(), curve = new Float32Array(4097);
    for (let i = 0; i < curve.length; i++) { const x = (i / 2048) - 1, a = Math.abs(x); curve[i] = Math.sign(x) * (a < 0.8 ? a : 0.8 + 0.2 * Math.tanh((a - 0.8) / 0.2)); }
    out.curve = curve; out.oversample = '2x'; out.connect(final);
    this.lp = ctx.createBiquadFilter(); this.lp.type = 'lowpass'; this.lp.frequency.value = 18000; this.lp.Q.value = 0.4;     // the music goes through this
    this.mg = ctx.createGain(); this.lp.connect(this.mg); this.mg.connect(out);
    this.bus = ctx.createGain(); this.bus.gain.value = level; this.bus.connect(out);                                            // the effects go here
  }
  get musicDest() { return this.lp; }
  setLevel(x) { this.bus.gain.value = x; }
  // follow the playback rate: dull when slow, a small dip near a stop; smoothed so the page's 10 Hz updates never click
  setRate(rate, at = this.ctx.currentTime) {
    const r = Math.max(0.04, Math.min(1.6, rate)); this.rate = r;
    const cut = r >= 1 ? 18000 : Math.max(240, 18000 * Math.pow(r, 1.7));
    this.lp.frequency.setTargetAtTime(cut, at, 0.07);
    this.mg.gain.setTargetAtTime(0.55 + 0.45 * Math.min(1, r / 0.35), at, 0.07);
  }
  _voice(at, dur, build) {                        // build(ctx, bus, at, dur) -> nodes[]; every node is disconnected when the voice ends
    const nodes = build(this.ctx, this.bus, at, dur), end = at + dur + 0.2;
    const last = nodes[nodes.length - 1]; if (last && last.stop) last.onended = () => { for (const n of nodes) { try { n.disconnect(); } catch (_) {} } };
    return end;
  }
  trigger(kind, o = {}, at = this.ctx.currentTime + 0.01) {
    if (!this.on) return 0;
    switch (kind) {
      case 'freeze': return this.tapeStop(at, 0.62);
      case 'echo': case 'replay': return this.rewind(at, 0.42);
      case 'surge': return this.riser(at, Math.min(1.6, Math.max(0.7, (o.dur || 1.6) * 0.7)));
      case 'dip': return this.sink(at, Math.min(1.4, Math.max(0.6, (o.dur || 1.6) * 0.55)));
      case 'cut': return this.tick(at);
      default: return 0;
    }
  }
  tapeStop(at, dur = 0.62) {
    return this._voice(at, dur + 0.25, (c, bus) => {
      const g = c.createGain(), lp = c.createBiquadFilter(), saw = c.createOscillator();
      saw.type = 'sawtooth'; expTo(saw.frequency, 260, 24, at, dur); lp.type = 'lowpass'; expTo(lp.frequency, 2600, 110, at, dur); lp.Q.value = 1.2;
      g.gain.setValueAtTime(1e-4, at); g.gain.linearRampToValueAtTime(0.34, at + 0.015); g.gain.exponentialRampToValueAtTime(1e-4, at + dur + 0.1);
      saw.connect(lp); lp.connect(g); g.connect(bus); saw.start(at); saw.stop(at + dur + 0.12);
      const n = c.createBufferSource(), bp = c.createBiquadFilter(), ng = c.createGain(); n.buffer = noiseBuffer(c); bp.type = 'bandpass'; bp.Q.value = 1.1; expTo(bp.frequency, 1500, 90, at, dur);
      ng.gain.setValueAtTime(0.28, at); ng.gain.exponentialRampToValueAtTime(1e-4, at + dur); n.connect(bp); bp.connect(ng); ng.connect(bus); n.start(at, 0); n.stop(at + dur + 0.05);
      const th = c.createOscillator(), tg = c.createGain(); th.frequency.setValueAtTime(70, at + dur * 0.78); th.frequency.exponentialRampToValueAtTime(34, at + dur * 0.78 + 0.18);
      tg.gain.setValueAtTime(1e-4, at + dur * 0.78); tg.gain.linearRampToValueAtTime(0.42, at + dur * 0.78 + 0.012); tg.gain.exponentialRampToValueAtTime(1e-4, at + dur * 0.78 + 0.22);
      th.connect(tg); tg.connect(bus); th.start(at + dur * 0.78); th.stop(at + dur * 0.78 + 0.25);
      return [g, lp, saw, ng, bp, n, tg, th];
    });
  }
  rewind(at, dur = 0.42) {
    return this._voice(at, dur + 0.2, (c, bus) => {
      const n = c.createBufferSource(), bp = c.createBiquadFilter(), g = c.createGain(), pan = c.createStereoPanner();
      n.buffer = noiseBuffer(c); bp.type = 'bandpass'; bp.Q.value = 3.5; expTo(bp.frequency, 250, 7000, at, dur);
      g.gain.setValueAtTime(1e-4, at); g.gain.exponentialRampToValueAtTime(0.5, at + dur * 0.72); g.gain.exponentialRampToValueAtTime(1e-4, at + dur + 0.08);
      pan.pan.setValueAtTime(-0.7, at); pan.pan.linearRampToValueAtTime(0.7, at + dur);
      n.connect(bp); bp.connect(g); g.connect(pan); pan.connect(bus); n.start(at, 0.3); n.stop(at + dur + 0.1);
      const z = c.createOscillator(), zg = c.createGain(); z.type = 'sine'; expTo(z.frequency, 700, 4600, at, dur);
      zg.gain.setValueAtTime(1e-4, at); zg.gain.linearRampToValueAtTime(0.16, at + dur * 0.8); zg.gain.exponentialRampToValueAtTime(1e-4, at + dur + 0.05);
      z.connect(zg); zg.connect(pan); z.start(at); z.stop(at + dur + 0.08);
      return [bp, g, n, zg, pan, z];
    });
  }
  riser(at, dur = 1.2) {
    return this._voice(at, dur + 0.2, (c, bus) => {
      const n = c.createBufferSource(), bp = c.createBiquadFilter(), g = c.createGain(); n.buffer = noiseBuffer(c); bp.type = 'bandpass'; bp.Q.value = 2; expTo(bp.frequency, 300, 6000, at, dur);
      g.gain.setValueAtTime(1e-4, at); g.gain.linearRampToValueAtTime(0.3, at + dur * 0.92); g.gain.exponentialRampToValueAtTime(1e-4, at + dur + 0.1);
      n.connect(bp); bp.connect(g); g.connect(bus); n.start(at, 0.2); n.stop(at + dur + 0.12);
      const s = c.createOscillator(), sg = c.createGain(); s.type = 'sine'; expTo(s.frequency, 160, 640, at, dur);
      sg.gain.setValueAtTime(1e-4, at); sg.gain.linearRampToValueAtTime(0.1, at + dur * 0.9); sg.gain.exponentialRampToValueAtTime(1e-4, at + dur + 0.1);
      s.connect(sg); sg.connect(bus); s.start(at); s.stop(at + dur + 0.12);
      return [bp, g, n, sg, s];
    });
  }
  sink(at, dur = 0.9) {
    return this._voice(at, dur + 0.2, (c, bus) => {
      const o = c.createOscillator(), g = c.createGain(); o.type = 'sine'; expTo(o.frequency, 190, 46, at, dur);
      g.gain.setValueAtTime(1e-4, at); g.gain.linearRampToValueAtTime(0.22, at + 0.06); g.gain.exponentialRampToValueAtTime(1e-4, at + dur + 0.1);
      o.connect(g); g.connect(bus); o.start(at); o.stop(at + dur + 0.12);
      const n = c.createBufferSource(), lp = c.createBiquadFilter(), ng = c.createGain(); n.buffer = noiseBuffer(c); lp.type = 'lowpass'; expTo(lp.frequency, 900, 160, at, dur);
      ng.gain.setValueAtTime(0.12, at); ng.gain.exponentialRampToValueAtTime(1e-4, at + dur); n.connect(lp); lp.connect(ng); ng.connect(bus); n.start(at, 0.5); n.stop(at + dur + 0.05);
      return [g, o, lp, ng, n];
    });
  }
  tick(at) {
    return this._voice(at, 0.12, (c, bus) => {
      const n = c.createBufferSource(), hp = c.createBiquadFilter(), g = c.createGain(); n.buffer = noiseBuffer(c); hp.type = 'highpass'; hp.frequency.value = 2500;
      g.gain.setValueAtTime(0.25, at); g.gain.exponentialRampToValueAtTime(1e-4, at + 0.07); n.connect(hp); hp.connect(g); g.connect(bus); n.start(at, 0.9); n.stop(at + 0.1);
      const o = c.createOscillator(), og = c.createGain(); o.frequency.value = 1320; og.gain.setValueAtTime(0.1, at); og.gain.exponentialRampToValueAtTime(1e-4, at + 0.05); o.connect(og); og.connect(bus); o.start(at); o.stop(at + 0.06);
      return [hp, g, n, og, o];
    });
  }
}
