// measured.js: "authored beside measured". Overlay panels laid over the Landing's graph acts and finale, each with its grade.
// The scene's graph acts run on the deck's AUTHORED heads; the Grabar corpus (UD CAVaL, 342,533 letters) and the tokenizer census give MEASURED
// counterparts. These panels put the two side by side at the moment the scene shows the authored one. They are HTML over the canvas, driven by
// the page's clock V (so they follow pause, speed, dilation, replays and seeks) and read their numbers from measured.json
// (built from the source files by integrated/build_measured.py, which asserts the values quoted in the explore write-ups).
//
// Panels (segment names are the timeline's; f0..f1 the fraction of the segment):
//   pagerank  left   PageRank, top five: the deck's graph is nearly flat, the measured one is led by Ա (and tracks letter frequency)
//   cut       left   the Fiedler cut: how well the sign of the vector separates the vowel flags: authored, measured, and the measured fastest mode
//   chords    left   the 630 chords: authored weights vs measured bigram weights; does the alphabet's order carry structure?
//   tokens    left   tokenizer space: the first merges, vowel+consonant share, median first-merge rank (during the 'tokens' hold)
//   svd       left   SVD + k-means on the measured graph: the four clusters, the vowel cluster, settling iteration (during the 'svdm' hold)
//   census    right  tokens per word on Eastern Armenian per tokenizer; Nemotron's is Tekken; Tekken's first Armenian merge is ու

const E = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const pct = (x, d = 1) => (100 * x).toFixed(d) + '%';
const chip = (kind, text) => E('span', 'chip ' + kind, text);

function barRows(rows, scaleMax, fmt, kind = '') {
  const box = E('div', 'rows ' + kind);
  for (const [label, v] of rows) {
    const r = E('div', 'row'), t = E('i'); t.style.width = Math.max(1.2, 100 * v / scaleMax) + '%';
    r.append(E('b', 'l', label), E('span', 'trk').appendChild(t).parentNode, E('span', 'v', fmt(v)));
    box.append(r);
  }
  return box;
}

function strip(values, vowel, order) {
  // the 36 letters sorted by the vector's value; a gold cell is a vowel (the deck's flag), grey a consonant; the tick marks where the vector crosses zero
  const idx = [...values.keys()].sort((a, b) => values[a] - values[b]);
  const s = E('div', 'strip'); let tick = -1;
  idx.forEach((i, k) => { const c = E('i', vowel[i] ? 'v' : 'c'); c.title = `${order[i]} ${values[i].toFixed(2)}`; s.append(c); if (tick < 0 && values[i] > 0) tick = k; });
  if (tick > 0) { const m = E('u'); m.style.left = (100 * tick / idx.length) + '%'; s.append(m); }
  return s;
}

export function buildPanels(root, M, tl) {
  const panels = [];
  const add = (id, side, seg, f0, f1, build, more = []) => { const sp = tl.span(seg); if (!sp) return; const el = E('section', `panel ${side}`); el.id = 'pn-' + id; build(el); root.append(el);
    const wins = [[sp[0] + (sp[1] - sp[0]) * f0, sp[0] + (sp[1] - sp[0]) * f1]];
    for (const [s2, g0, g1] of more) { const q = tl.span(s2); if (q) wins.push([q[0] + (q[1] - q[0]) * g0, q[0] + (q[1] - q[0]) * g1]); }
    panels.push({ id, el, wins, t0: wins[0][0], t1: wins[0][1] }); };

  // ---- PageRank -------------------------------------------------------------------------------------------------------------------
  const P = M.pagerank;
  add('pagerank', 'left', 'pagerank', 0.06, 1.0, el => {
    el.append(E('h4', null, 'PageRank · the top five letters'));
    const mx = 0.15;                                                                   // one scale for both, so the flat one looks flat
    const a = E('div', 'blk'); a.append(chip('auth', 'authored · the deck\'s three heads'), barRows(P.authored_top, mx, v => pct(v), 'auth'));
    const m = E('div', 'blk'); m.append(chip('meas', 'Measured · Grabar, ' + M.pagerank.grade_measured.match(/[\d,]+ letters/)[0]), barRows(P.measured_top, mx, v => pct(v), 'meas'));
    el.append(a, m, E('p', 'fine', `The deck's graph is almost flat (1 / 36 = 2.8 % each). The measured one is led by Ա alone, and it follows letter frequency (Spearman ${P.spearman_measured_vs_frequency > 0 ? '+' : ''}${P.spearman_measured_vs_frequency.toFixed(2)}). The two agree on nothing (Spearman ${P.spearman_authored_vs_measured > 0 ? '+' : ''}${P.spearman_authored_vs_measured.toFixed(2)}). In the scene the gold streams are the deck's, the mint streams the measured graph's.`));
  });

  // ---- the Fiedler cut ------------------------------------------------------------------------------------------------------------
  const C = M.cut;
  add('cut', 'left', 'spectral', 0.05, 1.0, el => {
    el.append(E('h4', null, 'The Fiedler cut · do the vowels fall out?'));
    const row = (kind, label, vals, sepv, extra) => { const b = E('div', 'blk'); b.append(chip(kind, label), strip(vals, C.vowel, C.order), E('p', 'sub', extra)); return b; };
    el.append(
      row('auth', 'authored', C.authored.v, C.authored.separates, `sign splits the vowel flags ${pct(C.authored.separates, 0)}`),
      row('meas', 'Measured · plain Fiedler vector', C.measured.v, C.measured.separates, `sign splits the vowel flags ${pct(C.measured.separates, 0)}`),
      row('meas', 'Measured · the fastest mode', C.fast_mode.v, C.fast_mode.separates, `${pct(C.fast_mode.separates, 0)}: ${C.order.length - C.fast_mode.disagrees_on.length} of ${C.order.length}; the one miss is ${C.fast_mode.disagrees_on}`),
      E('p', 'fine', 'gold = vowel (the deck\'s flag), grey = consonant, tick = where the vector crosses zero. The next act is the fastest mode, run on the corpus.'));
  });

  // ---- the chords -----------------------------------------------------------------------------------------------------------------
  const K = M.chords;
  add('chords', 'left', 'web', 0.40, 1.0, el => {
    el.append(E('h4', null, `${K.pairs} chords · authored weight against measured`));
    el.append(E('div', 'big', `r = ${K.edge_weight_correlation.toFixed(2)}`),
      chip('meas', 'Measured · bigram counts, Grabar'),
      E('p', 'fine', `The weight the deck gives a chord and the weight the text gives it are uncorrelated across all ${K.pairs} letter pairs.`),
      E('p', 'fine', `Does the alphabet's order carry structure? Letters next to each other co-occur slightly less than chance would give: Spearman ${K.order_vs_cooccurrence_spearman.toFixed(3)} against ${K.order_null_mean.toFixed(3)} ± ${K.order_null_sd.toFixed(3)} for 2,000 random orders (${K.order_z.toFixed(1)} sd).`));
  });

  // ---- tokenizer space -----------------------------------------------------------------------------------------------------------
  const TK = M.tokens;
  if (TK) add('tokens', 'left', 'tokens', 0.30, 1.0, el => {
    el.append(E('h4', null, 'Tokenizer space · who the machine glues first'), chip('meas', 'Measured · Tekken (Nemotron Nano 9B v2)'));
    const rows = TK.top.map(([pair, rank, w]) => [pair, w]);
    const box = barRows(rows, 1.0, w => '', 'meas wide'); box.querySelectorAll('.l').forEach((l, i) => { l.textContent = `${TK.top[i][0]}`; l.style.fontFamily = '"Noto Serif Armenian","Mshtakan",serif'; l.style.width = '2.2cqw'; l.style.color = '#e8b86a'; });
    box.querySelectorAll('.v').forEach((v, i) => { v.textContent = TK.top[i][1].toLocaleString('en-US'); v.style.width = '3.4cqw'; });
    el.append(box);
    el.append(E('p', 'fine', `Earliest two-letter Armenian merges (longer bar = earlier). ${TK.vc} of ${TK.n_merges} pair a vowel with a consonant: ${(100 * TK.vc_share).toFixed(0)} % (${(100 * TK.vc_chance).toFixed(0)} % for random pairs). Median first-merge rank: vowels ${Math.round(TK.vowel_median_rank).toLocaleString('en-US')}, consonants ${Math.round(TK.consonant_median_rank).toLocaleString('en-US')}. The layout is a picture of the list, not a metric.`));
  }, [['space2', 0.0, 0.7]]);

  // ---- the measured SVD + k-means ------------------------------------------------------------------------------------------------
  const SV = M.svd;
  if (SV) add('svd', 'left', 'svdm', 0.45, 1.0, el => {
    el.append(E('h4', null, 'SVD + k-means, run on the measured graph'), chip('meas', 'Measured · Grabar, the deck\'s procedure'));
    const box = E('div', 'rows meas');
    for (const [letters, vowels] of SV.clusters) {
      const r = E('div', 'row'), trk = E('span', 'trk'), bar = E('i'); bar.style.width = (100 * letters.length / 11) + '%'; trk.append(bar);
      const l = E('b', 'l', vowels ? `${vowels} V` : ''); l.style.width = '2.2cqw'; l.style.fontSize = '.78cqw';
      const t = E('span', 'cl', letters); t.style.cssText = 'font:600 .9cqw/1.2 "Noto Serif Armenian","Mshtakan",serif;color:#e8b86a;letter-spacing:.05cqw;margin-left:.3cqw;white-space:nowrap';
      r.append(l, trk, E('span', 'v', String(letters.length)), t); box.append(r);
    }
    el.append(box);
    el.append(E('p', 'fine', `One cluster takes all 7 vowels (and Յ, Ռ, Ք); the other three hold only consonants. It comes out the same on the raw plane, the rank-spread plane and the relaxed one. Assignments stop changing at iteration ${SV.settle_measured} (the deck's graph: ${SV.settle_authored}). Each axis is spread by rank because one letter dominates the raw plane.`));
  }, [['svd2', 0.0, 1.0]]);

  // ---- the census -----------------------------------------------------------------------------------------------------------------
  const N = M.census;
  add('census', 'right', 'finale', 0.04, 0.62, el => {
    el.append(E('h4', null, N.title), E('p', 'sub', N.corpus), chip('meas', 'Measured'));
    el.append(barRows(N.bars, 14.5, v => v.toFixed(2), 'meas wide'));
    el.append(E('p', 'fine', N.nemotron_is_tekken + '. ' + N.caveat));
    const merge = E('div', 'merge'); const p0 = N.tekken_pairs[0];
    merge.append(E('b', 'hy', p0.pair), E('span', null, `Tekken's first two-letter Armenian merge, rank ${p0.rank.toLocaleString('en-US')}: Mashtots's own digraph for /u/. Then ${N.tekken_pairs.slice(1, 5).map(p => p.pair).join(', ')}.`));
    el.append(merge);
  });
  return panels;
}

// call every ~100 ms with the page's clock; a panel is shown while V is inside its window
export function updatePanels(panels, V, on = true) {
  for (const p of panels) p.el.classList.toggle('show', on && p.wins.some(([a, b]) => V >= a && V < b));
}

export const PANEL_CSS = `
#panels{position:absolute;inset:0;pointer-events:none;z-index:2;container-type:size}
.panel{position:absolute;box-sizing:border-box;padding:.9cqw 1cqw;width:19cqw;background:rgba(11,10,10,.66);border:1px solid rgba(205,150,70,.32);border-radius:.5cqw;
  font:.86cqw/1.35 "Lora",Georgia,serif;color:#d8d2cc;opacity:0;transform:translateY(.6cqw);transition:opacity .6s,transform .6s;backdrop-filter:blur(3px)}
.panel.left{left:1.2cqw;top:12cqh}
.panel.right{right:1.2cqw;top:12cqh;width:21cqw}
.panel.show{opacity:1;transform:none}
.panel h4{margin:0 0 .5cqw;font:600 .98cqw/1.25 "Lora",Georgia,serif;color:#e8b86a;letter-spacing:.01em}
.panel .blk{margin:.5cqw 0 .6cqw}
.panel .chip{display:inline-block;font:.7cqw/1 "Lora",Georgia,serif;padding:.25cqw .5cqw;border-radius:.3cqw;margin-bottom:.35cqw;letter-spacing:.03em}
.chip.auth{background:rgba(139,135,132,.22);color:#b9b3ad;border:1px solid rgba(185,179,173,.35)}
.chip.meas{background:rgba(127,227,208,.14);color:#7fe3d0;border:1px solid rgba(127,227,208,.45)}
.rows .row{display:flex;align-items:center;gap:.4cqw;margin:.14cqw 0}
.rows .l{width:1.3cqw;font:600 1.05cqw/1 "Noto Serif Armenian","Mshtakan",serif;color:#e8b86a}
.rows .trk{flex:1;height:.55cqw;background:rgba(255,255,255,.07);border-radius:.3cqw;overflow:hidden}
.rows .trk i{display:block;height:100%;background:#cd9646;border-radius:.3cqw}
.rows.meas .trk i{background:#7fe3d0}
.rows.wide .l{width:9.4cqw;font:.76cqw/1.2 "Lora",Georgia,serif;color:#d8d2cc}
.rows.wide .v{width:2.4cqw}
.rows .v{width:2.6cqw;text-align:right;font-variant-numeric:tabular-nums;color:#b9b3ad}
.panel .fine{margin:.5cqw 0 0;color:#9d9792;font-size:.74cqw}
.panel .sub{margin:.2cqw 0 0;color:#9d9792;font-size:.74cqw}
.strip{position:relative;display:flex;gap:1px;height:1.1cqw}
.strip i{flex:1;border-radius:1px;background:#3a3a46}
.strip i.v{background:#e8b86a}
.strip u{position:absolute;top:-.25cqw;bottom:-.25cqw;width:2px;margin-left:-1px;background:#fff;opacity:.8}
.big{font:600 2.6cqw/1.1 "Lora",Georgia,serif;color:#7fe3d0;margin:.2cqw 0 .3cqw}
.merge{display:flex;gap:.7cqw;align-items:center;margin-top:.6cqw;padding-top:.5cqw;border-top:1px solid rgba(205,150,70,.25);color:#b9b3ad;font-size:.76cqw}
.merge .hy{font:600 2.8cqw/1 "Noto Serif Armenian","Mshtakan",serif;color:#e8b86a}
body.nopanels #panels{display:none}
@media (prefers-reduced-motion:reduce){.panel{transition:none}}
`;
