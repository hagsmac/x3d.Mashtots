// deck.js: the standalone's control deck and info panel. Every feature of the expanded cut gets a button here, including the ones that were
// keyboard-only (frame steps, speeds, cameras, orbit, effects, panels) or URL-only (scene, score version, score seed and layers, UI skin, seed).
// It drives the stage only through window.__stage (stage.html), so the engine stays the Landing's own.
//   right: the DECK (transport, sections, acts, cameras, dazzle + plan + moment replays, display, sound + score, scene, other pieces, readouts)
//   left:  the INFO panel (this act and its grades, all sections, all acts, the grades, keys and URL options, credits, limits)
//   over the picture: a title card at each section change, a glowing playhead on the act bar, drifting letters behind the start card
import { SECTIONS, ACTS, GRADES, KEYS, URLS, CREDITS } from './info.js';
import { MOMENTS, VIEWS } from './conductor.js';

const LETTERS = 'ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ';
const BAR = 1.875;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// Markup comes only from this file's templates and info.js, with every data value passed through esc(); put() is the one place it is parsed.
const put = (el, markup) => { el.replaceChildren(document.createRange().createContextualFragment(markup)); return el; };
const E = (tag, cls, markup) => { const e = document.createElement(tag); if (cls) e.className = cls; if (markup != null) put(e, markup); return e; };
const mmss = (t, d = 0) => { const s = d ? (Math.floor(t % 60 * 10 ** d) / 10 ** d).toFixed(d) : String(Math.floor(t % 60)); return `${Math.floor(t / 60)}:${s.padStart(d ? 3 + d : 2, '0')}`; };   // truncates, like the pill
const chip = g => `<span class="g g-${g}" title="${esc(GRADES[g].tip)}">${GRADES[g].label}</span>`;
const ICON = {
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/></svg>',
  deck: '<svg viewBox="0 0 24 24"><path d="M4 7h10M18 7h2M4 12h4M12 12h8M4 17h12"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="17" r="2"/></svg>',
};

export function initDeck(S) {
  const q = S.q, body = document.body, stage = document.getElementById('stage');
  const state = { titles: q.get('titles') !== '0', lastSec: -1 };

  // ------------------------------------------------------------------ the two buttons in the pill
  const hud = document.getElementById('hud');
  const bInfo = E('button', null, ICON.info + '<span class="lab">info</span>'); bInfo.type = 'button'; bInfo.setAttribute('aria-label', 'Info panel (I)'); bInfo.id = 'h-info';
  const bDeck = E('button', null, ICON.deck + '<span class="lab">deck</span>'); bDeck.type = 'button'; bDeck.setAttribute('aria-label', 'Control deck (K)'); bDeck.id = 'h-deck';
  hud.prepend(bInfo); hud.append(bDeck);

  // ------------------------------------------------------------------ panels
  const deck = E('aside', 'dk-panel dk-right'); deck.id = 'deck'; deck.setAttribute('aria-label', 'Control deck');
  const info = E('aside', 'dk-panel dk-left'); info.id = 'info'; info.setAttribute('aria-label', 'Info');
  document.body.append(deck, info);
  function open(which, on) {
    const el = which === 'deck' ? deck : info, b = which === 'deck' ? bDeck : bInfo;
    on = on ?? !body.classList.contains(which + '-open');
    body.classList.toggle(which + '-open', on); b.setAttribute('aria-pressed', String(on)); el.toggleAttribute('inert', !on);
    window.dispatchEvent(new Event('resize'));
  }
  bInfo.onclick = () => open('info'); bDeck.onclick = () => open('deck');

  // ------------------------------------------------------------------ DECK
  const sec = (title, sub) => { const s = E('section', 'dk-sec'); s.append(E('h3', null, esc(title) + (sub ? ` <small>${esc(sub)}</small>` : ''))); deck.append(s); return s; };
  const btn = (parent, label, fn, { title = '', cls = '', key = '' } = {}) => {
    const b = E('button', 'dk-b ' + cls, label + (key ? ` <kbd>${esc(key)}</kbd>` : '')); b.type = 'button'; if (title) b.title = title; b.onclick = fn; parent.append(b); return b;
  };
  const row = (parent, cls = '') => { const r = E('div', 'dk-row ' + cls); parent.append(r); return r; };
  const toggles = [];
  const toggle = (parent, label, get, set, opts = {}) => { const b = btn(parent, label, () => { set(!get()); sync(); }, opts); b._get = get; toggles.push(b); return b; };
  const lab = (parent, text) => parent.append(E('span', 'dk-l', esc(text)));

  deck.append(E('header', 'dk-head', '<b lang="hy">Կառավարում</b> · control deck <button type="button" class="dk-x" aria-label="close the deck (K)">×</button>'));
  deck.querySelector('.dk-x').onclick = () => open('deck', false);

  // readouts
  const now = sec('Now', 'live readouts');
  const ro = E('dl', 'dk-ro'); now.append(ro);
  const RO = {};
  for (const [k, label] of [['time', 'time'], ['act', 'act time'], ['seg', 'act'], ['sec', 'section'], ['rate', 'rate'], ['fps', 'frames/s'], ['view', 'camera'], ['dz', 'dazzle'], ['loop', 'loop'], ['snd', 'sound'], ['score', 'score']]) {
    ro.append(E('dt', null, esc(label))); RO[k] = E('dd'); ro.append(RO[k]);
  }

  // transport
  const tr = sec('Transport', 'space · ← → · , . · [ ]');
  const r1 = row(tr);
  const bPlay = btn(r1, '▶ play', () => S.setPaused(!S.paused), { key: 'space', cls: 'wide' });
  btn(r1, '⏮', () => S.actStep(-1), { title: 'previous section (←)' });
  btn(r1, '⏭', () => S.actStep(1), { title: 'next section (→)' });
  btn(r1, '◂ frame', () => S.step(-1 / 30), { title: 'one frame back (,)' });
  btn(r1, 'frame ▸', () => S.step(1 / 30), { title: 'one frame forward (.)' });
  btn(r1, '⟲ 0:00', () => S.goto(0), { title: 'back to the start of the loop' });
  const scrubWrap = row(tr, 'dk-scrub');
  const scrub = E('input'); scrub.type = 'range'; scrub.min = 0; scrub.max = S.cyc; scrub.step = 0.05; scrub.value = 0; scrub.setAttribute('aria-label', 'seek');
  const scrubT = E('span', 'dk-mono', '0:00'); scrubWrap.append(scrub, scrubT);
  let scrubbing = false;
  scrub.addEventListener('input', () => { scrubbing = true; S.goto(+scrub.value); scrubT.textContent = mmss(+scrub.value, 1); });
  scrub.addEventListener('change', () => { scrubbing = false; });
  const mini = E('div', 'dk-mini'); tr.append(mini);                    // a minimap of the acts with this loop's effects
  const sp = row(tr); lab(sp, 'speed');
  const speedBtns = [0.25, 0.5, 0.75, 1, 1.5, 2].map(x => { const b = btn(sp, x + '×', () => S.setSpeed(x)); b.dataset.speed = x; return b; });

  // sections and acts
  const ss = sec('Sections', '10 · click to go');
  const secGrid = E('div', 'dk-grid2'); ss.append(secGrid);
  const secBtns = S.SEC.sections.map((s, i) => btn(secGrid, `<span lang="hy">${esc(s.hy)}</span><small>${esc(s.en)} · ${mmss(s.t)}</small>`, () => S.goto(s.t), { cls: 'dk-sect' }));
  const as = sec('Acts', `${uniqueSegs().length} · mint: has a measured layer · ◆ the deck's clock holds (an act the deck did not have)`);
  const actGrid = E('div', 'dk-acts'); as.append(actGrid);
  const actBtns = uniqueSegs().map(nm => {
    const spn = S.span(nm), hold = S.segs.find(s => s.name === nm).rate === 0, gr = (ACTS[nm] || ['', []])[1];
    const b = btn(actGrid, `${hold ? '◆ ' : ''}${esc(nm)}<small>${mmss(spn[0])}</small>`, () => S.goto(spn[0] + 0.01), { title: (ACTS[nm] || [''])[0], cls: gr.includes('measured') ? 'm' : '' });
    b.dataset.seg = nm; return b;
  });

  // cameras
  const cs = sec('Cameras', '1 2 3 4 · O orbit');
  const camRow = row(cs);
  const camBtns = [['Cam', 'scene', '1'], ['CamHelix', 'helix', '2'], ['CamRing', 'ring', '3'], ['CamStone', 'stone', '4']].map(([vp, label, k]) => {
    const b = btn(camRow, label, () => S.setView(vp === 'Cam' ? '' : vp), { key: k, title: `bind the ${vp} viewpoint` }); b.dataset.vp = vp === 'Cam' ? '' : vp; return b; });
  toggle(camRow, 'orbit', () => { try { return S.scene.getNamedNode('Nav').type[0] !== 'NONE'; } catch { return false; } }, v => S.setOrbit(v), { key: 'O', title: 'free navigation: drag to orbit the scene' });
  cs.append(E('p', 'dk-note', 'The dazzle layer also cuts to the helix, ring and stone viewpoints on its own; a seek or a loop returns to the scene camera.'));

  // dazzle
  const dz = sec('Dazzle', 'D · R · P');
  const lvRow = row(dz);
  const lvBtns = ['off', 'subtle', 'dazzle', 'wild'].map(l => { const b = btn(lvRow, l, () => S.setLevel(l)); b.dataset.lv = l; return b; });
  const seedRow = row(dz); lab(seedRow, 'seed');
  const seedIn = E('input', 'dk-num'); seedIn.type = 'number'; seedIn.min = 0; seedIn.max = 999999; seedIn.setAttribute('aria-label', 'plan seed'); seedRow.append(seedIn);
  btn(seedRow, 'use seed', () => { const v = Math.max(0, +seedIn.value | 0); S.fixedSeed = v; S.cond.reseed(v); S.cond.rearm(S.V); S.drawTicks(); S.chip(`plan #${v} (fixed)`); });
  toggle(seedRow, 'fixed', () => S.fixedSeed != null, v => { S.fixedSeed = v ? S.cond.seed : null; }, { title: 'keep this plan on every loop (otherwise a new seed each loop)' });
  const plRow = row(dz);
  btn(plRow, 'new plan', () => S.reroll(), { key: 'R' });
  toggle(plRow, 'show plan', () => body.classList.contains('ticks'), v => S.setPlan(v), { key: 'P', title: 'ticks on the act bar where this loop\'s effects fall' });
  const planList = E('ol', 'dk-plan'); dz.append(planList);
  dz.append(E('p', 'dk-note', '<b>dip</b> slow-motion bell · <b>surge</b> time-lapse · <b>freeze</b> hit-stop · <b>echo</b> instant replay · <b>cut</b> to another camera · <b>replay</b> a moment, slowed, usually from another camera · <b>wobble</b> the rate breathes. Click an effect to land 2 s before it.'));
  const mm = sec('Moment replays', `${MOMENTS.length} · the two seconds that never come back`);
  const momGrid = E('div', 'dk-grid2'); mm.append(momGrid);
  for (const m of MOMENTS) btn(momGrid, `${esc(m.label)}${m.letter ? ' …' : ''}<small>${esc(m.seg)} · chance ${m.p} per loop</small>`, () => replayNow(m), { cls: 'dk-mom', title: 'play this moment now and replay it slowed (switches dazzle on if it is off)' });

  // display
  const cf = sec('Display', 'C · M · G · H · F');
  const cfRow = row(cf, 'dk-wrap');
  toggle(cfRow, 'calm', () => S.calm, v => S.setCalm(v), { key: 'M', title: 'half speed, no dazzle, no drifting motes and sparks' });
  toggle(cfRow, 'captions', () => body.classList.contains('subs'), v => S.setSubs(v), { key: 'C' });
  toggle(cfRow, 'graded panels', () => !body.classList.contains('nopanels'), v => S.setPanels(v), { key: 'G', title: 'authored beside measured, over the graph acts and the finale' });
  toggle(cfRow, 'title cards', () => state.titles, v => { state.titles = v; }, { title: 'a card at each section change' });
  const cfRow2 = row(cf, 'dk-wrap');
  btn(cfRow2, 'hide controls', () => S.setHidden(true), { key: 'H', title: 'H brings them back' });
  btn(cfRow2, 'full screen', () => S.fullscreen(), { key: 'F' });
  btn(cfRow2, 'key help', () => S.setHelp(!S.helpOpen), { key: '?' });
  btn(cfRow2, 'start card', () => S.showGate(), { title: 'show the start card again' });

  // sound
  const sd = sec('Sound', 'S · X · nobody has listened to it');
  const sdRow = row(sd);
  toggle(sdRow, 'sound', () => S.listening, v => S.setSound(v), { key: 'S', title: 'the live score: synthesised in WebAudio from the timeline' });
  toggle(sdRow, 'tape effects', () => S.fxOn, v => S.setFx(v), { key: 'X', title: 'the sound of time dilation (fx.js)' });
  const fxRow = row(sd); lab(fxRow, 'effects level');
  const fxLv = E('input'); fxLv.type = 'range'; fxLv.min = 0; fxLv.max = 1; fxLv.step = 0.05; fxLv.value = 0.5; fxLv.setAttribute('aria-label', 'effects level'); fxRow.append(fxLv);
  fxLv.oninput = () => { if (S.live && S.live.fx) S.live.fx.setLevel(+fxLv.value); };
  const tryRow = row(sd, 'dk-wrap'); lab(tryRow, 'try');
  for (const [kind, label] of [['freeze', 'tape-stop'], ['echo', 'rewind'], ['surge', 'riser'], ['dip', 'sink'], ['cut', 'tick']]) btn(tryRow, label, () => tryFx(kind), { title: `fire the ${label} voice now (the conductor's "${kind}")` });
  const scRow = row(sd); lab(scRow, 'score seed');
  const seedBtns = [0, 1, 2].map(n => { const b = btn(scRow, String(n), () => { S.SCORE.seed = n; S.restartScore(); sync(); }, { title: 'the improvisation and arrangement seed of the live score' }); b.dataset.ss = n; return b; });
  const lyRow = row(sd, 'dk-wrap'); lab(lyRow, 'layers');
  for (const [k, label] of [['styles', 'tour styles'], ['composed', 'composed duduk'], ['saws', 'saws'], ['fx', 'risers'], ['sonif', 'graph sonification'], ['measured', 'measured acts']])
    toggle(lyRow, label, () => S.SCORE.layers[k] !== false, v => { S.SCORE.layers[k] = v; S.restartScore(); }, { title: `score v2 layer "${k}" (rebuilds the score)` });
  const verRow = row(sd); lab(verRow, 'version');
  const vNow = q.get('score') === 'v1' ? 'v1' : q.get('mix') === '0' ? 'v2raw' : 'v2';
  for (const [v, label, params] of [['v2', 'v2 mixed', { score: null, mix: null }], ['v2raw', 'v2 unmixed', { score: null, mix: '0' }], ['v1', 'v1 (first)', { score: 'v1', mix: null }]]) {
    const b = btn(verRow, label, () => reload(params), { title: 'reloads at this moment' }); b.setAttribute('aria-pressed', String(v === vNow)); }
  sd.append(E('p', 'dk-note', 'Score v2: everything make_music.py has, in 11 stems, mixed to -17 LUFS (measured offline in Chromium). Unlistened by its builder: judge it by ear.'));

  // scene and skin
  const sc = sec('Scene and skin', 'these reload at this moment');
  const scRow2 = row(sc); lab(scRow2, 'scene');
  for (const [v, label] of [['measured', 'measured build'], ['expanded', 'expanded, no mint']]) { const b = btn(scRow2, label, () => reload({ scene: v === 'measured' ? null : 'expanded' })); b.setAttribute('aria-pressed', String(S.SCENE === v)); }
  const skRow = row(sc); lab(skRow, 'skin');
  for (const [v, label] of [[null, 'pill'], ['bar', 'director\'s bar'], ['0', 'none']]) { const b = btn(skRow, label, () => reload({ ui: v })); b.setAttribute('aria-pressed', String((q.get('ui') || null) === v)); }
  const lk = row(sc, 'dk-link');
  const linkIn = E('input', 'dk-url'); linkIn.readOnly = true; linkIn.setAttribute('aria-label', 'link to this moment');
  lk.append(linkIn);
  btn(lk, 'link here', () => { linkIn.value = urlWith({ t: S.V.toFixed(2), seed: S.cond.seed, dazzle: S.cond.level, gate: '0', deck: null }); linkIn.select(); navigator.clipboard?.writeText(linkIn.value).then(() => S.chip('link copied'), () => {}); }, { title: 'a URL that reopens this moment, plan and level' });

  // other pieces
  const ot = sec('Other pieces in this project');
  const otRow = row(ot, 'dk-wrap');
  for (const [href, label, title] of [['index.html?standalone=1', 'the approved cut', 'the approved Landing (204 s): mp3 score in three variants, harp mix, cinema mode'], ['index.html?slide1&nav&standalone=1', 'slide 1', 'the approved slide-1 port: a 16.65 s loop'],
    ['index.html?classic&standalone=1', 'slide 1, classic', 'slide 1 without shaders (216 interpolators)'], ['score/index.html', 'score lab', 'the live score alone: play any section, switch layers, measure a whole loop offline'],
    ['fx_measure.html', 'effects lab', 'renders each tape effect offline and measures it'], ['explore/director/index.html?scene=retime&preset=graph-expanded', 'director\'s page', 'the earlier director page this stage grew from: speed, frame steps, presets'],
    ['explore/live-score/index.html', 'score v1 lab', 'the first, simplified live score against the approved mp3']]) { const a = E('a', 'dk-b', esc(label)); a.href = href; a.title = title; otRow.append(a); }

  // ------------------------------------------------------------------ INFO
  info.append(E('header', 'dk-head', '<b lang="hy">Տեղեկություն</b> · info <button type="button" class="dk-x" aria-label="close the info panel (I)">×</button>'));
  info.querySelector('.dk-x').onclick = () => open('info', false);
  const tabs = E('nav', 'in-tabs'), pane = E('div', 'in-pane'); info.append(tabs, pane);
  const TABS = [['now', 'this act'], ['sections', 'sections'], ['acts', 'acts'], ['grades', 'grades'], ['keys', 'keys & URL'], ['credits', 'credits'], ['limits', 'limits']];
  let tab = 'now';
  for (const [id, label] of TABS) { const b = btn(tabs, esc(label), () => { tab = id; renderInfo(true); }); b.dataset.tab = id; }
  function renderInfo(force) {
    for (const b of tabs.children) b.setAttribute('aria-pressed', String(b.dataset.tab === tab));
    if (tab === 'now') {
      const seg = S.seg.name, i = secIdx(), s = S.SEC.sections[i], I = SECTIONS[s.id] || {}, A = ACTS[seg] || ACTS[seg.replace(/2$/, '')] || ['', []];
      const key = seg + '|' + i; if (!force && pane.dataset.key === key) return; pane.dataset.key = key;
      put(pane, `<p class="in-kick">section ${i + 1} of ${S.SEC.sections.length} · starts ${mmss(s.t)}</p><h2><span lang="hy">${esc(s.hy)}</span> ${esc(s.en)}</h2>
        <p>${esc(I.what || '')}</p>${I.flag ? '<p class="in-flag">⚑ Needs a native Armenian reader.</p>' : ''}
        <h4>The data and its grade</h4><ul class="in-data">${(I.data || []).map(([g, t]) => `<li>${chip(g)} ${esc(t)}</li>`).join('')}</ul>
        <h4>Now playing: the act <code>${esc(seg)}</code> ${A[1].map(chip).join(' ')}</h4><p>${esc(A[0])}</p>
        ${I.look ? `<h4>Look for</h4><p class="in-look">${esc(I.look)}</p>` : ''}`);
      return;
    }
    if (!force) return; pane.dataset.key = '';
    if (tab === 'sections') put(pane, `<table class="in-t"><tr><th>time</th><th>section</th><th>what</th></tr>${S.SEC.sections.map(s => `<tr data-t="${s.t}"><td>${mmss(s.t)}</td><td><span lang="hy">${esc(s.hy)}</span><br><small>${esc(s.en)}</small></td><td>${esc((SECTIONS[s.id] || {}).what || '')}</td></tr>`).join('')}</table>`);
    if (tab === 'acts') put(pane, `<table class="in-t"><tr><th>time</th><th>act</th><th>grades</th><th>what</th></tr>${uniqueSegs().map(n => { const spn = S.span(n), A = ACTS[n] || ['', []]; return `<tr data-t="${spn[0] + 0.01}"><td>${mmss(spn[0])}<br><small>${(spn[1] - spn[0]).toFixed(1)} s</small></td><td><code>${esc(n)}</code></td><td>${A[1].map(chip).join(' ')}</td><td>${esc(A[0])}</td></tr>`; }).join('')}</table>`);
    if (tab === 'grades') put(pane, `<p>The Landing grades every figure, as the deck did. The colours are a code, not a theme: in the scene gold and paper are the deck's authored numbers, <b class="mint">mint</b> is measured.</p><ul class="in-data">${Object.keys(GRADES).map(g => `<li>${chip(g)} ${esc(GRADES[g].tip)}</li>`).join('')}</ul><p>The graded panels (<kbd>G</kbd>) put authored and measured side by side: PageRank top five, the Fiedler cut, the 630 chords, tokenizer space, the measured SVD clusters and the tokenizer census.</p>`);
    if (tab === 'keys') put(pane, `<h4>Keys</h4><table class="in-t">${KEYS.map(([k, v]) => `<tr><td><kbd>${esc(k)}</kbd></td><td>${esc(v)}</td></tr>`).join('')}</table><p>Phones: tap the picture to show or hide the controls, double-tap to pause.</p><h4>URL options</h4><table class="in-t">${URLS.map(([k, v]) => `<tr><td><code>${esc(k)}</code></td><td>${esc(v)}</td></tr>`).join('')}</table>`);
    if (tab === 'credits') put(pane, `<table class="in-t">${CREDITS.map(([k, v]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(v)}</td></tr>`).join('')}</table>`);
    if (tab === 'limits') put(pane, `<ul class="in-data">
        <li>${chip('authored')} The deck's three attention heads are hand-made features, not a trained model; the scene says so in its legend.</li>
        <li>Audio: <b>nobody has listened</b> to the live score, the tape effects or the mint layer's sonification. Loudness (-17 LUFS), spectra and the harmony audit are measured; taste is not.</li>
        <li>Armenian: the section names and scene text are the Landing's; the start card's "և սկսել" and the Lord's Prayer text need a native reader.</li>
        <li>The measured SVD plane is shown rank-spread (the raw plane piles letters up); k-means inertia there is not comparable with the deck's.</li>
        <li>The walk's TV figures are one seeded run each, not a significance test. The descent uses η = 20 (a choice among 5, 10, 20, 40).</li>
        <li>Tokenizer space is a picture of the merge list, not a metric; fertility is not competence: no model was run.</li>
        <li>Tested in Chromium on an Apple M3. Safari, Firefox, other GPUs, real touch hardware and screen readers: not tested.</li></ul>`);
    for (const r of pane.querySelectorAll('tr[data-t]')) { r.classList.add('go'); r.onclick = () => S.goto(+r.dataset.t); }
  }

  // ------------------------------------------------------------------ over the picture: title card, playhead, start-card letters
  const card = E('div', 'tc'); card.setAttribute('aria-hidden', 'true'); stage.append(card);
  let cardT = 0;
  addEventListener('stage:seg', e => {
    const { sec: s, index } = e.detail;
    if (tab === 'now') renderInfo();
    if (index === state.lastSec) return; const first = state.lastSec < 0; state.lastSec = index;
    if (first || !state.titles || S.paused) return;
    const I = SECTIONS[s.id] || {}, gs = [...new Set((I.data || []).map(d => d[0]))];
    put(card, `<div class="tc-n">${String(index + 1).padStart(2, '0')} / ${S.SEC.sections.length}</div><div class="tc-hy" lang="hy">${esc(s.hy)}</div><div class="tc-en">${esc(s.en)}</div><div class="tc-g">${gs.map(chip).join('')}</div>`);
    card.classList.remove('on'); void card.offsetWidth; card.classList.add('on'); clearTimeout(cardT); cardT = setTimeout(() => card.classList.remove('on'), 3200);
  });
  const head = E('i', 'ph'); document.getElementById('acts').append(head);
  drift(document.getElementById('gate'));

  // ------------------------------------------------------------------ actions
  function replayNow(m) {
    const spn = S.span(m.seg); if (!spn) { S.chip('this build has no ' + m.seg); return; }
    if (S.calm) S.setCalm(false);
    if (S.cond.level === 'off') S.setLevel('dazzle');
    let at, label = m.label;
    if (m.letter) { const i = 2 + Math.floor(Math.random() * 32); at = spn[0] + (i + 1) * (spn[1] - spn[0]) / 36; label = `${m.label} ${LETTERS[i]}`; }
    else if (m.bar != null) at = spn[0] + m.bar * BAR; else at = spn[0] + (spn[1] - spn[0]) * m.f;
    const ev = { at, kind: 'replay', seg: m.seg, label, fired: false, back: m.len, rate: (m.rate[0] + m.rate[1]) / 2, view: VIEWS[Math.floor(Math.random() * VIEWS.length)], moment: m.id, manual: true };
    S.cond.events = S.cond.events.filter(e => !e.manual && Math.abs(e.at - at) > 3); S.cond.events.push(ev); S.cond.events.sort((a, b) => a.at - b.at);
    S.goto(Math.max(0, at - m.len - 1.2)); S.drawTicks(); if (S.paused) S.setPaused(false); S.chip('moment · ' + label);
  }
  async function tryFx(kind) {
    if (!S.listening) await S.setSound(true);
    if (S.live && S.live.fx) { S.live.fx.trigger(kind, { dur: 1.2 }); S.chip(kind + ' · sound only'); }
  }
  function urlWith(params) { const u = new URL(location.href); for (const [k, v] of Object.entries(params)) { if (v == null) u.searchParams.delete(k); else u.searchParams.set(k, v); } u.hash = ''; return u.toString(); }
  function reload(params) { location.href = urlWith({ t: S.V.toFixed(2), gate: '0', deck: body.classList.contains('deck-open') ? '1' : null, info: body.classList.contains('info-open') ? '1' : null, ...params }); }
  function secIdx() { let k = 0; S.SEC.sections.forEach((s, i) => { if (S.V >= s.t - 0.05) k = i; }); return k; }
  function uniqueSegs() { const n = []; for (const s of S.segs) if (!n.includes(s.name)) n.push(s.name); return n; }

  // minimap: one cell per act, a tick per effect, the playhead
  const miniHead = E('u');
  function drawMini() {
    mini.replaceChildren();
    for (const nm of uniqueSegs()) { const spn = S.span(nm), d = E('i', S.segs.find(s => s.name === nm).rate === 0 ? 'h' : ['vowels', 'tokens', 'svdm'].includes(nm) ? 'm' : ''); d.style.left = (100 * spn[0] / S.cyc) + '%'; d.style.width = (100 * (spn[1] - spn[0]) / S.cyc) + '%'; d.title = nm; d.onclick = () => S.goto(spn[0] + 0.01); mini.append(d); }
    for (const ev of S.cond.events) { const b = E('b', 'k-' + ev.kind); b.style.left = (100 * ev.at / S.cyc) + '%'; b.title = `${ev.kind} · ${ev.label} · ${ev.at.toFixed(1)} s`; mini.append(b); }
    mini.append(miniHead);
  }
  let planKey = '';
  function drawPlan() {
    const key = `${S.cond.level}|${S.cond.seed}|${S.cond.events.map(e => e.at.toFixed(1)).join(',')}`; if (key === planKey) return; planKey = key; drawMini();
    planList.replaceChildren();
    if (!S.cond.events.length) planList.append(E('li', 'none', 'no effects at this level'));
    for (const ev of S.cond.events) {
      const extra = ev.kind === 'dip' ? `to ${ev.depth.toFixed(2)}×` : ev.kind === 'surge' ? `to ${ev.gain.toFixed(1)}×` : ev.rate ? `at ${ev.rate.toFixed(2)}×` : ev.kind === 'wobble' ? `±${Math.round(ev.amp * 100)} %` : '';
      const li = E('li', 'k-' + ev.kind, `<span class="dk-mono">${mmss(ev.at, 1)}</span> <b>${esc(ev.kind)}</b> ${esc(ev.label)}${ev.view ? ` <small>→ ${esc(ev.view)}</small>` : ''} <small>${extra}</small>`);
      li.onclick = () => S.goto(Math.max(0, ev.at - 2)); planList.append(li);
    }
  }

  // ------------------------------------------------------------------ the loop
  function sync() {
    for (const b of toggles) b.setAttribute('aria-pressed', String(!!b._get()));
    put(bPlay, (S.paused ? '▶ play' : '❚❚ pause') + ' <kbd>space</kbd>');
    for (const b of speedBtns) b.setAttribute('aria-pressed', String(+b.dataset.speed === S.speed));
    for (const b of lvBtns) b.setAttribute('aria-pressed', String(b.dataset.lv === S.cond.level));
    for (const b of seedBtns) b.setAttribute('aria-pressed', String(+b.dataset.ss === S.SCORE.seed));
    for (const b of camBtns) b.setAttribute('aria-pressed', String(b.dataset.vp === (S.view || '')));
    if (document.activeElement !== seedIn) seedIn.value = S.cond.seed;
  }
  function tick() {
    const V = S.V, sg = S.seg, i = secIdx(), s = S.SEC.sections[i];
    RO.time.textContent = `${mmss(V, 1)} / ${mmss(S.cyc)}`; RO.act.textContent = `${S.act.toFixed(2)} s (the deck's clock)`;
    RO.seg.textContent = sg.name + (sg.rate === 0 && sg.rate_end === 0 ? ' (hold)' : ''); RO.sec.textContent = `${i + 1} · ${s.en}`;
    RO.rate.textContent = S.paused ? 'paused' : `${(S.speed * (S.calm ? 0.5 : 1) * S.mult).toFixed(2)}×`; RO.fps.textContent = String(S.fps);
    RO.view.textContent = S.view || 'scene (Cam)'; RO.dz.textContent = `${S.cond.level} · plan #${S.cond.seed}${S.fixedSeed != null ? ' (fixed)' : ''} · ${S.cond.events.length} effects`;
    RO.loop.textContent = String(S.loops + 1);
    RO.snd.textContent = S.listening && S.live ? `on · ${S.live.ctx.state} · ${S.live.ctx.sampleRate} Hz · tape effects ${S.fxOn ? 'on' : 'off'}` : 'off';
    RO.score.textContent = S.live ? `${q.get('score') === 'v1' ? 'v1' : 'v2'} · seed ${S.SCORE.seed} · ${S.live.score.events.length} events · harmony audit ${S.live.score.audit.outside} of ${S.live.score.audit.checked} outside` : `seed ${S.SCORE.seed} · built on first sound`;
    if (!scrubbing) { scrub.value = V; scrubT.textContent = mmss(V, 1); }
    miniHead.style.left = (100 * V / S.cyc) + '%'; head.style.left = (100 * V / S.cyc) + '%';
    secBtns.forEach((b, j) => b.classList.toggle('on', j === i)); for (const b of actBtns) b.classList.toggle('on', b.dataset.seg === sg.name);
    drawPlan(); sync();
  }
  setInterval(tick, 150); tick();
  renderInfo(true);
  deck.setAttribute('inert', ''); info.setAttribute('inert', '');
  if (q.get('deck') === '1') open('deck', true);
  if (q.get('info') === '1') open('info', true);
  return {
    toggle: which => open(which),
    closeAll: () => { let any = false; for (const w of ['deck', 'info']) if (body.classList.contains(w + '-open')) { open(w, false); any = true; } return any; },
  };
}

// the start card: the 36 letters drift up like embers behind the title (2D canvas; idles while the card is closed)
function drift(gate) {
  if (!gate || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const c = document.createElement('canvas'); c.className = 'drift'; gate.prepend(c); const g = c.getContext('2d');
  const P = Array.from({ length: 54 }, (_, i) => ({ ch: LETTERS[i % 36], x: Math.random(), y: Math.random(), v: 0.012 + Math.random() * 0.03, s: 14 + Math.random() * 30, a: Math.random() * 6.28, w: 0.3 + Math.random() }));
  let last = performance.now();
  function frame(t) {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (t - last) / 1000); last = t;
    if (!gate.classList.contains('show')) return;
    const W = gate.clientWidth * devicePixelRatio, H = gate.clientHeight * devicePixelRatio;
    if (c.width !== W || c.height !== H) { c.width = W; c.height = H; }
    g.clearRect(0, 0, W, H); g.textAlign = 'center'; g.shadowColor = 'rgba(232,184,106,.8)'; g.shadowBlur = 12 * devicePixelRatio;
    for (const p of P) {
      p.y -= p.v * dt; p.a += dt * p.w; if (p.y < -0.05) { p.y = 1.05; p.x = Math.random(); }
      const al = Math.max(0, Math.min(1, (1.05 - p.y) * 2) * Math.min(1, (p.y + 0.05) * 3) * (0.25 + 0.2 * Math.sin(p.a)));
      g.font = `${(p.s * devicePixelRatio).toFixed(0)}px "Noto Serif Armenian", serif`; g.fillStyle = `rgba(232,184,106,${al.toFixed(3)})`;
      g.fillText(p.ch, (p.x + 0.02 * Math.sin(p.a)) * W, p.y * H);
    }
  }
  requestAnimationFrame(frame);
}
