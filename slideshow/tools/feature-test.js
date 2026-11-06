// feature-test.js: clicks every control of the deck and the info panel on stage.html and checks that the stage's state changed as it should.
// Run it in the page (it is an async function expression): Playwright `page.evaluate(src)`, or paste into the console after the scene has loaded
// (open stage.html?gate=0&deck=1&info=1), or load it as a <script> and call window.__featureTest(). Returns [{feature, control, ok, detail}]. It turns the sound on (needs a click-started page in a
// normal browser; Playwright allows it). It does not test full screen (browsers refuse it without a real gesture) or the reloading buttons
// (scene, skin, score version): tools/run-feature-test.mjs loads those URLs separately.
window.__featureTest = async () => {
  const S = window.__stage, R = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const deck = document.getElementById('deck'), info = document.getElementById('info');
  const B = (scope, re) => [...scope.querySelectorAll('button, a')].find(b => re.test(b.textContent.trim()));
  const ok = (feature, control, cond, detail = '') => R.push({ feature, control, ok: !!cond, detail: String(detail) });
  const click = async (scope, re, ms = 250) => { const b = B(scope, re); if (!b) throw new Error('no control ' + re); b.click(); await wait(ms); return b; };
  const secOf = () => { let k = 0; S.SEC.sections.forEach((s, i) => { if (S.V >= s.t - 0.05) k = i; }); return k; };
  S.setLevel('dazzle'); S.goto(30); S.setPaused(false); await wait(300);

  await click(deck, /^❚❚ pause|^▶ play/); ok('pause / play', 'deck ▶/❚❚', S.paused === true, 'paused=' + S.paused);
  await click(deck, /^▶ play/); ok('pause / play', 'deck ▶/❚❚', S.paused === false);
  let i0 = secOf(); await click(deck, /^⏭$/); ok('next section', 'deck ⏭', secOf() === i0 + 1, `${i0} -> ${secOf()}`);
  i0 = secOf(); await click(deck, /^⏮$/); ok('previous section', 'deck ⏮', secOf() === i0 - 1, `${i0} -> ${secOf()}`);
  S.goto(40); await wait(150); let v0 = S.V; await click(deck, /^frame ▸/, 400); ok('frame forward (pauses)', 'deck frame ▸', S.paused && Math.abs(S.V - v0 - 1 / 30) < 0.2, (S.V - v0).toFixed(3));
  v0 = S.V; await click(deck, /^◂ frame/, 400); ok('frame back', 'deck ◂ frame', Math.abs(v0 - S.V - 1 / 30) < 0.05, (v0 - S.V).toFixed(3));
  await click(deck, /^⟲ 0:00/); ok('back to the start', 'deck ⟲ 0:00', S.V < 0.5, S.V.toFixed(2));
  const scrub = deck.querySelector('.dk-scrub input'); scrub.value = 120; scrub.dispatchEvent(new Event('input')); scrub.dispatchEvent(new Event('change')); await wait(200);
  ok('seek anywhere', 'deck scrubber', Math.abs(S.V - 120) < 0.3, S.V.toFixed(2));
  for (const x of [0.25, 0.5, 0.75, 1, 1.5, 2]) { await click(deck, new RegExp('^' + x.toString().replace('.', '\\.') + '×$'), 80); ok('speed ' + x + '×', 'deck speed', S.speed === x, S.speed); }
  S.setSpeed(1);
  for (const s of S.SEC.sections) { const b = [...deck.querySelectorAll('.dk-sect')].find(e => e.textContent.includes(s.en)); b.click(); await wait(60); ok('section: ' + s.en, 'deck Sections', Math.abs(S.V - s.t) < 0.3, S.V.toFixed(2)); }
  for (const b of deck.querySelectorAll('.dk-acts .dk-b')) { b.click(); await wait(60); ok('act: ' + b.dataset.seg, 'deck Acts', S.seg.name === b.dataset.seg, S.seg.name); }
  for (const [label, vp] of [['helix', 'CamHelix'], ['ring', 'CamRing'], ['stone', 'CamStone'], ['scene', '']]) { await click(deck, new RegExp('^' + label + ' '), 150); ok('camera ' + (vp || 'Cam'), 'deck Cameras', S.view === vp, S.view); }
  await click(deck, /^orbit/); ok('orbit on', 'deck orbit', S.scene.getNamedNode('Nav').type[0] !== 'NONE', S.scene.getNamedNode('Nav').type[0]);
  await click(deck, /^orbit/); ok('orbit off', 'deck orbit', S.scene.getNamedNode('Nav').type[0] === 'NONE');
  for (const l of ['off', 'subtle', 'wild', 'dazzle']) { await click(deck, new RegExp('^' + l + '$'), 80); ok('dazzle ' + l, 'deck Dazzle', S.cond.level === l, S.cond.level); }
  const seedIn = deck.querySelector('.dk-num'); seedIn.value = 21; await click(deck, /^use seed/); ok('fix a plan seed', 'deck seed + use seed', S.cond.seed === 21 && S.fixedSeed === 21, S.cond.seed);
  await click(deck, /^fixed/); ok('unfix the seed', 'deck fixed', S.fixedSeed == null);
  let sd = S.cond.seed; await click(deck, /^new plan/); ok('draw a new plan', 'deck new plan', S.cond.seed !== sd, `${sd} -> ${S.cond.seed}`);
  await click(deck, /^show plan/); ok('show the plan on the act bar', 'deck show plan', document.body.classList.contains('ticks') && document.querySelectorAll('#acts i:not(.ph)').length === S.cond.events.length, document.querySelectorAll('#acts i:not(.ph)').length);
  await click(deck, /^show plan/);
  const li = deck.querySelector('.dk-plan li:not(.none)'); if (li) { li.click(); await wait(100); const ev = S.cond.events[0]; ok('jump to a planned effect', 'deck plan list', Math.abs(S.V - Math.max(0, ev.at - 2)) < 0.3, S.V.toFixed(2)); }
  for (const b of deck.querySelectorAll('.dk-mom')) { b.click(); await wait(60); const ev = S.cond.events.find(e => e.manual); ok('moment replay: ' + b.firstChild.textContent.trim(), 'deck Moment replays', ev && S.V < ev.at && S.cond.level !== 'off', ev ? `${ev.label} @${ev.at.toFixed(1)}` : 'none'); }
  await click(deck, /^calm/); ok('calm on', 'deck calm', S.calm); await click(deck, /^calm/); ok('calm off', 'deck calm', !S.calm);
  await click(deck, /^captions/); ok('captions', 'deck captions', document.body.classList.contains('subs')); await click(deck, /^captions/);
  await click(deck, /^graded panels/); ok('graded panels off', 'deck graded panels', document.body.classList.contains('nopanels')); await click(deck, /^graded panels/); ok('graded panels on', 'deck graded panels', !document.body.classList.contains('nopanels'));
  await click(deck, /^title cards/); const tcb = B(deck, /^title cards/); ok('title cards toggle', 'deck title cards', tcb.getAttribute('aria-pressed') === 'false'); await click(deck, /^title cards/);
  await click(deck, /^hide controls/); ok('hide controls', 'deck hide controls', document.body.classList.contains('nobar')); S.setHidden(false);
  await click(deck, /^key help/); ok('key help', 'deck key help', document.getElementById('help').classList.contains('show')); S.setHelp(false);
  await click(deck, /^start card/); ok('show the start card', 'deck start card', document.getElementById('gate').classList.contains('show')); document.getElementById('g-silent').click(); await wait(200);
  ok('full screen', 'deck full screen + pill', !!B(deck, /^full screen/) && typeof S.fullscreen === 'function', 'present (not clickable without a real gesture)');
  await click(deck, /^sound/, 2500); ok('sound (live score)', 'deck sound', S.listening && S.live && S.live.ctx.state === 'running', S.live && S.live.ctx.state);
  await click(deck, /^tape effects/); ok('tape effects off', 'deck tape effects', !S.fxOn); await click(deck, /^tape effects/); ok('tape effects on', 'deck tape effects', S.fxOn);
  const lv = deck.querySelector('input[aria-label="effects level"]'); lv.value = 0.8; lv.dispatchEvent(new Event('input')); await wait(50); ok('effects level', 'deck slider', Math.abs(S.live.fx.bus.gain.value - 0.8) < 1e-6, S.live.fx.bus.gain.value);
  for (const n of ['tape-stop', 'rewind', 'riser', 'sink', 'tick']) { let err = null; try { await click(deck, new RegExp('^' + n + '$'), 120); } catch (e) { err = e; } ok('try effect: ' + n, 'deck try', !err, err || 'fired'); }
  for (const n of [0, 1, 2]) { await click(deck, new RegExp('^' + n + '$'), 2500); ok('score seed ' + n, 'deck score seed', S.SCORE.seed === n && S.live && S.live.score, S.live && S.live.score.events.length + ' events'); }
  for (const [label, k] of [['tour styles', 'styles'], ['composed duduk', 'composed'], ['saws', 'saws'], ['risers', 'fx'], ['graph sonification', 'sonif'], ['measured acts', 'measured']]) {
    const before = S.live.score.events.length; await click(deck, new RegExp('^' + label + '$'), 2500);
    ok('score layer off: ' + k, 'deck layers', S.SCORE.layers[k] === false && S.live.score.events.length < before, `${before} -> ${S.live.score.events.length} events`);
    await click(deck, new RegExp('^' + label + '$'), 1500);
  }
  await click(deck, /^sound/, 300); ok('sound off', 'deck sound', !S.listening);
  await click(deck, /^link here/); const url = deck.querySelector('.dk-url').value; ok('link to this moment', 'deck link here', /[?&]t=/.test(url) && /seed=/.test(url), url.replace(location.origin, ''));
  for (const a of deck.querySelectorAll('.dk-sec a.dk-b')) { const r = await fetch(a.href); ok('other piece: ' + a.textContent, 'deck link', r.ok, r.status + ' ' + a.getAttribute('href')); }
  for (const b of info.querySelectorAll('.in-tabs .dk-b')) { b.click(); await wait(60); const pane = info.querySelector('.in-pane'); ok('info tab: ' + b.textContent, 'info panel', pane.textContent.trim().length > 80, pane.textContent.trim().length + ' chars'); }
  // keys
  const key = async (k, ms = 150) => { dispatchEvent(new KeyboardEvent('keydown', { key: k })); await wait(ms); };
  S.goto(30); await wait(150);
  let s0 = S.paused; await key(' '); ok('key space', 'keyboard', S.paused !== s0); await key(' ');
  i0 = secOf(); await key('ArrowRight'); ok('key →', 'keyboard', secOf() === i0 + 1); await key('ArrowLeft'); ok('key ←', 'keyboard', secOf() === i0);
  let L0 = S.cond.level; await key('d'); ok('key D', 'keyboard', S.cond.level !== L0, `${L0} -> ${S.cond.level}`);
  sd = S.cond.seed; await key('r'); ok('key R', 'keyboard', S.cond.seed !== sd);
  await key('p'); ok('key P', 'keyboard', document.body.classList.contains('ticks')); await key('p');
  await key('c'); ok('key C', 'keyboard', document.body.classList.contains('subs')); await key('c');
  await key('m'); ok('key M', 'keyboard', S.calm); await key('m');
  await key('g'); ok('key G', 'keyboard', document.body.classList.contains('nopanels')); await key('g');
  await key('h'); ok('key H', 'keyboard', document.body.classList.contains('nobar')); await key('h');
  await key('x'); ok('key X', 'keyboard', !S.fxOn); await key('x');
  await key('2'); ok('key 2', 'keyboard', S.view === 'CamHelix'); await key('1'); ok('key 1', 'keyboard', S.view === '');
  await key('o'); ok('key O', 'keyboard', S.scene.getNamedNode('Nav').type[0] !== 'NONE'); await key('o');
  await key(']'); ok('key ]', 'keyboard', S.speed === 1.5); await key('['); ok('key [', 'keyboard', S.speed === 1);
  v0 = S.V; await key('.', 300); ok('key .', 'keyboard', S.paused && S.V > v0); await key(' ');
  await key('?'); ok('key ?', 'keyboard', document.getElementById('help').classList.contains('show')); await key('Escape'); ok('key Esc', 'keyboard', !document.getElementById('help').classList.contains('show'));
  const di = document.body.classList.contains('info-open'); await key('i'); ok('key I', 'keyboard', document.body.classList.contains('info-open') !== di); await key('i');
  const dk = document.body.classList.contains('deck-open'); await key('k'); ok('key K', 'keyboard', document.body.classList.contains('deck-open') !== dk); await key('k');
  await key('s', 2500); ok('key S', 'keyboard', S.listening); await key('s');
  return R;
}
