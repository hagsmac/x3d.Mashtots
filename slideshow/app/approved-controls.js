// approved-controls.js: on-screen buttons for the approved cut and slide 1 (index.html), whose features were keyboard- or URL-only:
// the cut (approved Landing / slide 1 / slide 1 classic), cameras, orbit, cinema, previous / next section, and an info card.
// A classic script loaded after index.html's own: it uses that page's globals (canvas, q, isLanding, setCinema, cinema, step).
(function () {
  const MODE = isLanding ? 'landing' : q.has('slide1') ? 'slide1' : q.has('classic') ? 'classic' : 'file';
  const CAMS = { landing: [['Cam', 'slide', '1'], ['CamHelix', 'helix', '2'], ['CamRing', 'ring', '3'], ['CamStone', 'stone', '4']],
                 slide1: [['Cam', 'slide', '1'], ['CamStone', 'stone', '2'], ['CamLine', 'gilt line', '3']], classic: [], file: [] }[MODE];
  const css = document.createElement('style');
  css.textContent = `
  #ac{position:fixed;right:12px;bottom:calc(3% + 30px);justify-content:flex-end;z-index:30;display:flex;flex-wrap:wrap;gap:4px;align-items:center;max-width:min(560px,94vw);padding:6px 8px;border-radius:12px;
    background:rgba(16,14,13,.82);border:1px solid rgba(205,150,70,.4);backdrop-filter:blur(6px);font:600 12px Georgia,serif;transition:opacity .5s}
  #ac a,#ac button{all:unset;cursor:pointer;padding:4px 9px;border-radius:7px;border:1px solid rgba(205,150,70,.3);color:#e6c58e;background:rgba(36,30,26,.7)}
  #ac a:hover,#ac button:hover{background:rgba(205,150,70,.2)} #ac [aria-pressed=true],#ac a.on{background:rgba(224,176,98,.35);color:#fff2d4;border-color:#e8b86a}
  #ac a:focus-visible,#ac button:focus-visible{outline:2px solid #f0cd96} #ac .sep{width:1px;height:20px;background:rgba(205,150,70,.35);margin:0 2px} #ac kbd{font:10px Georgia;color:#b9965e}
  .cinema~#ac,body.ac-dim #ac{opacity:.15} #ac:hover{opacity:1!important}
  #acinfo{position:fixed;inset:0;z-index:40;display:none;align-items:center;justify-content:center;background:rgba(11,10,10,.84);backdrop-filter:blur(4px)}
  #acinfo.show{display:flex} #acinfo .c{max-width:min(92vw,760px);max-height:88vh;overflow:auto;color:#d8d2cc;font:15px/1.6 Georgia,serif;padding:8px}
  #acinfo h3{color:#e8b86a;margin:0 0 .4em;font-size:22px} #acinfo td{padding:2px 10px 2px 0;vertical-align:top} #acinfo kbd{color:#e8b86a}
  #listen,#mode{outline-offset:2px}`;
  document.head.append(css);
  const bar = document.createElement('div'); bar.id = 'ac'; bar.setAttribute('role', 'toolbar'); bar.setAttribute('aria-label', 'controls');
  const add = (el) => { bar.append(el); return el; };
  const a = (href, text, on, title) => { const e = document.createElement('a'); e.href = href; e.textContent = text; if (on) e.className = 'on'; if (title) e.title = title; return add(e); };
  const b = (text, fn, title) => { const e = document.createElement('button'); e.type = 'button'; e.textContent = text; e.onclick = fn; if (title) e.title = title; return add(e); };
  const sep = () => { const s = document.createElement('span'); s.className = 'sep'; add(s); };
  a('stage.html?deck=1', '← the expanded cut', false, 'the main show: the expanded measured cut with the control deck');
  sep();
  a('index.html?standalone=1', 'approved cut', MODE === 'landing'); a('index.html?slide1&standalone=1', 'slide 1', MODE === 'slide1'); a('index.html?classic&standalone=1', 'slide 1 classic', MODE === 'classic');
  sep();
  const camBtns = CAMS.map(([vp, label, key]) => { const e = b(label, () => bind(vp), `camera ${vp} (key ${key})`); e.dataset.vp = vp; return e; });
  function bind(vp) { try { canvas.browser.currentScene.getNamedNode(vp).set_bind = true; for (const c of camBtns) c.setAttribute('aria-pressed', String(c.dataset.vp === vp)); } catch (_) {} }
  if (MODE === 'slide1') addEventListener('keydown', e => { const vp = { 2: 'CamStone', 3: 'CamLine' }[e.key]; if (vp) bind(vp); });      // the page maps 2 and 3 to the Landing's names
  let orbitBtn = null;
  if (MODE === 'landing' || MODE === 'slide1') orbitBtn = b('orbit', () => { try { const n = canvas.browser.currentScene.getNamedNode('Nav'); n.type = n.type[0] === 'NONE' ? ['EXAMINE', 'ANY'] : ['NONE']; orbitBtn.setAttribute('aria-pressed', String(n.type[0] !== 'NONE')); } catch (_) {} }, 'free navigation, drag to orbit (key f)');
  if (MODE === 'landing') {
    sep();
    b('⏮', () => step(-1), 'previous section (←)'); b('⏭', () => step(1), 'next section (→)');
    const cin = b('cinema', () => { setCinema(!cinema); cin.setAttribute('aria-pressed', String(cinema)); }, 'cinema mode: the chrome fades, the scene shows its title block (key c)');
    addEventListener('keydown', e => { if (e.key === 'c') cin.setAttribute('aria-pressed', String(cinema)); });
    for (const id of ['listen', 'mode']) { const el = document.getElementById(id); el.setAttribute('role', 'button'); el.tabIndex = 0; el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); el.click(); } }); }
  }
  sep();
  b('full screen', () => { const d = document; if (d.fullscreenElement) d.exitFullscreen(); else d.documentElement.requestFullscreen?.().catch(() => {}); });
  b('ⓘ info', () => card.classList.toggle('show'), 'what this is, keys, credits');
  document.body.append(bar);
  const card = document.createElement('div'); card.id = 'acinfo'; card.setAttribute('role', 'dialog');
  const c = document.createElement('div'); c.className = 'c'; card.append(c);
  const P = (tag, text) => { const e = document.createElement(tag); e.textContent = text; c.append(e); return e; };
  if (MODE === 'landing') {
    P('h3', 'The approved cut (204.25 s)');
    P('p', 'The Landing as approved on 27 October 2026: the deck "Mashtots System 2" ported to X3D, one clock, ten sections, ~60 shaders. Its score is a rendered mp3 kept in step with the clock (the rate is nudged by 5 % when it drifts; a jump if it is lost).');
    P('p', 'Listen: the full score; the button beside it cycles full score / harp + duduk (no drums, bass or saws) / v4, the previous approved mix. Three seeded variants (A, B, C) of the score: one is drawn on each Listen and again at each loop.');
    P('p', 'Grades as in the expanded cut: the deck\'s attention heads are authored; the finale\'s token bill is Measured; the scaling law\'s three points are placeholders; the floor is Established inside 70 M to 1 B parameters and an Estimate beyond; the closing line is a Conjecture. The expanded cut adds the measured (mint) layers, the dazzle conductor and the live score.');
  } else if (MODE === 'slide1') {
    P('h3', 'Slide 1 (16.65 s loop)');
    P('p', 'Slide 1 of the deck, the first piece ported: the 36 letters leave the alphabet stone in the mural, cross the dark on cubic Bezier paths (seed 405, begin 0.9 s, stagger 0.075 s, flight 2.8 s, hold 4 s, cubic ease: all from the deck\'s reveal.js) with comet trails, settle into one gilt line, rest and go home. One clock, two shaders, one mesh.');
  } else {
    P('h3', 'Slide 1, classic');
    P('p', 'The same flights as slide 1 with 216 PositionInterpolators and no shaders (441 KB): portable, lower fidelity (flat glow, trails always on). No named cameras or navigation node.');
  }
  P('p', 'Keys: ← → sections · 1-4 cameras · f orbit · c cinema (approved cut). Every key has a button in the strip at the top right.');
  P('p', 'Credits: mural by Van Khachatur, the staircase fresco of the Matenadaran, 1959-60 (photograph via Wikimedia Commons). X_ITE 16.5.1, vendored. Glyphs: the 36 letters of Mashtots, checked against the alphabet order. Not listened to by its builder.');
  P('p', 'Press Esc or click outside to close.');
  card.onclick = e => { if (e.target === card) card.classList.remove('show'); };
  addEventListener('keydown', e => { if (e.key === 'Escape') card.classList.remove('show'); });
  document.body.append(card);
  // dim the strip after 4 s without a pointer
  let t = 0; const wake = () => { document.body.classList.remove('ac-dim'); clearTimeout(t); t = setTimeout(() => document.body.classList.add('ac-dim'), 4000); };
  for (const ev of ['pointermove', 'keydown', 'pointerdown']) addEventListener(ev, wake, { passive: true }); wake();
})();
