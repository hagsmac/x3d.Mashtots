// info.js: what every section and act of the expanded cut shows, the data behind it and its grade.
// Grades as the deck and the Landing use them:
//   Measured     counted or computed from real data (a corpus, a tokenizer file), reproducible from the files named
//   Established  standard scholarship or a standard table (letter values, the colophon's calendar, a published fit inside its range)
//   Estimate     an extrapolation beyond what was measured or established
//   Conjecture   an argument the piece makes, not a result
//   Authored     made by hand for the picture (the deck's three attention heads, layouts, mappings): not data, and said so
// Sources: mashtots-landing/README.md, the integrated build's README.md (measured layers), explore/director/captions.json, measured.json.
// Text written for this standalone in English; the Armenian section names are the Landing's own (sections.json). Nothing here adds new Armenian.

export const GRADES = {
  measured:    { label: 'Measured',    hy: 'չափված',  tip: 'counted or computed from real data; reproducible from the named files' },
  established: { label: 'Established', hy: '',        tip: 'standard scholarship or a standard table; a published fit inside its range' },
  estimate:    { label: 'Estimate',    hy: '',        tip: 'an extrapolation beyond what was measured or established' },
  conjecture:  { label: 'Conjecture',  hy: '',        tip: 'an argument the piece makes, not a result' },
  authored:    { label: 'Authored',    hy: '',        tip: 'hand-made for the picture (the deck\'s heads, layouts, mappings): not data' },
};

// the ten sections (ids of sections-measured.json)
export const SECTIONS = {
  stone: {
    what: 'The 36 letters of Mesrop Mashtots leave the alphabet stone painted in Van Khachatur\'s Matenadaran fresco. Each one rings the stone as it leaves (a Chladni sand figure per letter), flies on the deck\'s seed-405 Bezier path with a comet trail, and settles on a gilt line.',
    data: [['established', 'The 36 original letters and their order (Mashtots, c. 405 AD); Օ and Ֆ, added in the Middle Ages, are not in the atlas.'],
           ['authored', 'Flight paths: cubic Beziers from the deck\'s seed 405 (begin 0.9 s, stagger 0.075 s, flight 2.8 s).'],
           ['authored', 'The Chladni mapping: a letter is plate mode (n, m) = (column + 1, row + 1) of the 4 x 9 table. Not a property of Armenian.']],
    look: 'Comet trails, the stone ringing, the gilt line forming left to right.',
  },
  helix: {
    what: 'The letters lift into a turning double-strand helix inside an astronomer\'s armillary globe: ecliptic and equator with degree ticks, the polar axis, the ecliptic pole, a dashed precession circle, three orbits with comet-trail planets.',
    data: [['authored', 'The armillary is a picture of the astronomer\'s instruments (Anania Shirakatsi, 7th century, is the astronomer the piece has in mind); no astronomical data is plotted.'],
           ['established', 'The two helix fixes (kinds 6 to 8 of the armillary; the strand drawn as quads) are documented in the Landing\'s exploration notes.']],
    look: 'Light running up and down the strand; the spotlit letter\'s stretch glows.',
  },
  tour: {
    what: 'The tour of the 36: each letter gets its card (name, sound, number, order), three attention heads drawn as arcs, the 36 x 36 attention map, its place in the stone grid and its Chladni figure. A fourth head, mint and dashed, is measured.',
    data: [['authored', 'The three heads (sound, number, order) are the deck\'s hand-made features: softmax(-||k - k\'||^2 / tau). Not a trained model.'],
           ['measured', 'The mint dashed head: the five most likely next letters in Grabar, P(next | letter), from UD CAVaL (342,533 letters). Ա -> Ն .17, Յ .12, Ր .12; Ո -> Ւ .36 (the digraph ու).'],
           ['authored', 'Chladni figure: plate mode (column + 1, row + 1).']],
    look: 'The mint dashed arcs beside the gold, white and pale-teal authored ones.',
  },
  writing: {
    what: 'Writing 405: the first sentence translated into Armenian, Proverbs 1:2 ("To know wisdom and instruction, to perceive the words of understanding"), written glyph by glyph, inked in flight, each glyph throwing causal attention arcs back to the three before it.',
    data: [['established', 'The text: Ճանաչել զիմաստութիւն եւ զխրատ, իմանալ զբանս հանճարոյ (Proverbs 1:2 in Grabar), traditionally the first sentence written in the letters.'],
           ['measured', 'Arc weights: the measured chance, in Grabar, of that letter exactly d = 1, 2, 3 letters after the earlier one (in-word skip-grams; 269,088 / 199,996 / 146,307 pairs). 97 in-word arcs span 0.0007 to 0.60.'],
           ['authored', 'Arcs across a word boundary have no in-word statistic and stay faint.']],
    look: 'The strongest arcs about twice as opaque and 1.8 times as wide as the median one.',
  },
  prayer: {
    what: 'The Lord\'s Prayer in Classical Armenian, written the same way, glyph by glyph with weighted arcs.',
    data: [['established', 'Text as printed on dominicweb.eu (the same wording on several church sites; spelling varies a little between editions). One line (Զհաց մեր հանապազորդ տուր մեզ այսօր) is left out: its Օ entered the alphabet in the Middle Ages and is not in the atlas. The scene says so.'],
           ['measured', 'Arc weights from the same Grabar skip-gram statistics as the writing.']],
    look: 'NEEDS A NATIVE READER: the prayer text should be checked by an Armenian reader.',
    flag: true,
  },
  numbers: {
    what: 'Letters are numbers: the 4 x 9 matrix (units, tens, hundreds, thousands). 405 = ՆԵ, 1512 = ՌՇԺԲ, 2026 = ՍԻԶ and 1475 = ՌՆՀԵ light their letters; then Shirakatsi\'s table, recomputed in his own numerals.',
    data: [['established', 'Letter values 1 to 9000 (the standard Armenian numeral table).'],
           ['established', 'Anania Shirakatsi\'s arithmetic tables (7th century), recomputed, not transcribed from a manuscript.']],
    look: 'The four years lighting their letters in the matrix.',
  },
  embedding: {
    what: 'The embedding space: the letters on two articulatory axes beside the turning 3 x 36 x 36 attention tensor. Then a new hold, tokenizer space: the letters glide to where a real tokenizer puts them.',
    data: [['authored', 'The two axes and the class rings are a hand-made articulatory layout; the tensor is the three authored heads.'],
           ['measured', 'Tokenizer space: Mistral Nemo\'s Tekken tokenizer (also Nemotron Nano 9B v2\'s) has 198 merges of two whole Armenian letters. Radius = rank of a letter\'s first merge (log scale), angle = spectral embedding of the merge graph. First merge ու (rank 1,986), then ան 2,247, ակ 4,608, եր 5,194, ին 5,941. 141 of 198 merges (71 %) pair a vowel with a consonant; 31 % would by chance.'],
           ['authored', 'The positions are a picture of the merge list (radius from one number, angle from a layout), not a metric.']],
    look: 'The 198 mint merge lines, brighter the earlier the merge; Ո and Ւ side by side at the centre.',
  },
  graph: {
    what: 'The alphabet as a graph: 630 chords on the ring, then GNN message passing from Ճ, the Fiedler cut, the measured vowels act, PageRank, annealing, gradient descent, a Markov walk, Fourier epicycles, the Poincare disk, SVD + k-means, and the collapse. Gold = the deck\'s authored graph, mint = the same procedure on the measured Grabar graph.',
    data: [['authored', 'The deck\'s graph is built from its three authored heads; every gold number comes from the original JavaScript, run in Node and baked.'],
           ['measured', 'Mint layers: the deck\'s own procedures, ported line by line and checked against the deck\'s numbers first, then run on the measured row-normalised bigram matrix of Grabar (UD CAVaL, 342,533 letters).'],
           ['measured', 'Headline results: the fastest mode lifts the vowels (35 of 36 agree; Ւ is the consonant w); PageRank led by Ա 14.5 %; measured k-means puts all 7 vowels in one cluster and settles at iteration 2.']],
    look: 'Press G for the graded panels: authored and measured numbers side by side.',
  },
  pretraining: {
    what: 'Pre-training in Armenian, 20 bars at 128 BPM: the token bill, one word in many shapes, the data-scaling law (the drop), the Armenian-only floor, and the closing line.',
    data: [['measured', 'Token bill (UDHR, Armenian / English): o200k 1.51, Mistral Tekken 1.74, Gemma 3/4 2.67, DeepSeek 2.87, Qwen 5.41, Llama 3.1 8.73, cl100k 10.15. Word shapes: measured.'],
           ['measured', 'Census panel (G): tokens per word on Eastern Armenian (UD ArmTDP, 82,056 words): o200k 2.64 ... cl100k 13.93. Fertility is not competence: no model was run.'],
           ['established', 'L(D) = 1.69 + 410.7 D^-0.28 is the published fit; its three plotted points are PLACEHOLDERS (the deck and the scene say so).'],
           ['established', 'Armenian-only floor bpb(N) = 4.9e5 N^-0.795 + 0.439: Established inside 70 M to 1 B parameters.'],
           ['estimate', 'The same floor beyond 1 B parameters.'],
           ['conjecture', 'The closing line: a sacred language can become a domain programming language.']],
    look: 'The drop at bar 10; the floor curve; the law\'s placeholder points.',
  },
  return: {
    what: 'The letters return to the line and fall home into the stone. The colophon: written in the Armenian year 1475, which is 2026.',
    data: [['established', 'Armenian calendar: year 1 began in 552 AD, so 1475 + 551 = 2026.'],
           ['established', 'Mural: Van Khachatur, the three-part staircase fresco of the Matenadaran, 1959-60 (photograph via Wikimedia Commons).']],
    look: 'The colophon stays whole through the return\'s camera sweep (fixed in the QA pass).',
  },
};

// the 30 acts (timeline segment names) -> one line + grades
export const ACTS = {
  flight:     ['The 36 letters leave the painted stone; each rings it as it leaves (its Chladni sand figure).', ['authored', 'established']],
  line:       ['They settle on the gilt line.', ['authored']],
  lift:       ['They lift into a turning helix inside the astronomer\'s armillary globe.', ['authored']],
  tour:       ['The tour of the 36: card, three authored heads, a fourth measured head (mint, dashed), the 36 x 36 map, the Chladni figure.', ['authored', 'measured']],
  write:      ['Writing 405: Proverbs 1:2 written glyph by glyph; arcs weighted by measured Grabar skip-grams.', ['established', 'measured']],
  prayer:     ['The Lord\'s Prayer in Grabar, one line left out (its Օ is medieval). Needs a native reader.', ['established', 'measured']],
  numerals:   ['Letters are numbers: the 4 x 9 matrix; 405, 1512, 2026 and 1475 light their letters.', ['established']],
  shirakatsi: ['Shirakatsi\'s table, recomputed in his own numerals.', ['established']],
  space:      ['The embedding space: two articulatory axes (authored) beside the turning 3 x 36 x 36 tensor.', ['authored']],
  tokens:     ['Tokenizer space (hold, 7.5 s): radius = Tekken\'s first-merge rank, angle = merge-graph spectral layout; 198 merges in mint.', ['measured', 'authored']],
  space2:     ['The embedding act finishes in tokenizer space.', ['measured']],
  web:        ['630 chords weighted by the authored heads; measured vs authored weight r = -0.11.', ['authored', 'measured']],
  msg:        ['Message passing from Ճ: h(l+1) = A h(l), six layers, on the authored graph.', ['authored']],
  spectral:   ['The Fiedler cut: the second eigenvector of L = D - W splits the ring (lambda2 = 0.488, authored graph).', ['authored']],
  vowels:     ['Measured: in 342,533 letters of Grabar the graph\'s fastest mode lifts the vowels; 35 of 36 agree, Ւ is the consonant w.', ['measured']],
  spectral2:  ['The Fiedler cut, continued.', ['authored']],
  pagerank:   ['PageRank, d = 0.85, 15 iterations: gold circles (authored, nearly flat) and mint rings (measured: Ա 14.5 %, Ն 9.2 %, Ե 7.1 %).', ['authored', 'measured']],
  anneal:     ['Annealing: tau sweeps 0.12 to 3 and back. Mint: measured rows raised to 1/tau (entropy 0.28 to 4.10 bits).', ['authored', 'measured']],
  descent:    ['Gradient descent with momentum. Mint: a bigram softmax model\'s real loss, 5.170 -> 3.387 bits in 48 steps (floor 3.354).', ['authored', 'measured']],
  walk:       ['A Markov walk: 36 walkers. Mint: walkers on the measured chain, TV 0.086 from stationary after 16 hops (one seeded run).', ['authored', 'measured']],
  fourier:    ['Fourier epicycles redraw the PageRank curve (19 harmonics). Mint: the measured curve, one tall spike (Ա).', ['authored', 'measured']],
  poincare:   ['The Poincare disk: chords as hyperbolic geodesics. Mint: 84 % of measured weight on vowel + consonant chords (32 % of chords).', ['authored', 'measured']],
  svd:        ['SVD of the attention matrix; k-means finds four families (authored).', ['authored']],
  svdm:       ['Measured SVD plane (hold, rank-spread): one cluster takes all 7 vowels; assignments settle at iteration 2.', ['measured', 'authored']],
  svd2:       ['Back from the measured plane.', ['authored']],
  collapse:   ['The graph folds back into the line.', ['authored']],
  finale:     ['Pre-training in Armenian: token bill (Measured), law (published fit, placeholder points), floor (Established, then Estimate), closing line (Conjecture).', ['measured', 'established', 'estimate', 'conjecture']],
  line2:      ['The letters return to the line.', ['authored']],
  return:     ['They fall home into the stone.', ['authored']],
  rest:       ['The colophon: written in the Armenian year 1475, which is 2026.', ['established']],
};

export const KEYS = [
  ['space', 'play or pause'], ['← →', 'previous or next section'], [', .', 'one frame back or forward (pauses)'], ['[ ]', 'slower or faster (0.25x to 2x)'],
  ['D', 'dazzle level: off, subtle, dazzle, wild'], ['R', 'draw a new plan now'], ['P', 'show where this loop\'s effects fall'],
  ['S', 'sound on or off (the live score)'], ['X', 'time-dilation effects on or off'], ['C', 'captions'], ['M', 'calm: half speed, no dazzle, no drifting particles'],
  ['G', 'graded panels (authored beside measured)'], ['H', 'hide all controls'], ['F', 'full screen'], ['1 2 3 4', 'cameras: scene, helix, ring, stone'],
  ['O', 'orbit (drag to turn the scene)'], ['I', 'info panel'], ['K', 'control deck'], ['?', 'key help'], ['Esc', 'close help / panels'],
];

export const URLS = [
  ['?dazzle=off|subtle|dazzle|wild', 'start at a dazzle level'], ['&seed=N', 'fix the plan (same seed, same plan)'], ['&t=SEC', 'start at a time'],
  ['&paused=1', 'start paused'], ['&calm=1', 'start calm'], ['&gate=0', 'skip the start card'], ['&ui=0|bar', 'no controls / the old director\'s bar'],
  ['&panels=0', 'hide the graded panels'], ['&scene=expanded', 'the expanded cut without the measured mint layers'], ['&fx=0', 'no time-dilation effects'],
  ['&score=v1', 'the first, simplified live score'], ['&mix=0', 'score v2 without the calibrated stem mix'], ['&scoreseed=0|1|2', 'fix the score\'s improvisation seed'],
  ['&layers=-styles,-saws...', 'switch score layers off (styles, composed, saws, fx, sonif, measured)'], ['&speed=X', 'start at a speed'], ['&deck=1 / &info=1', 'open the deck or the info panel'],
  ['#stone ... #return', 'start at a section'],
];

export const CREDITS = [
  ['Concept and deck', '"Mashtots System 2" (the alphabet read as a transformer), the HTML deck MashtotsLanding.dc.html; its graph acts\' numbers are the deck\'s own JavaScript, run in Node and baked.'],
  ['X3D port', 'The Landing (make_landing.py, X3D 4.0, ~60 GLSL shaders), slide 1 (make_reveal.py), the expanded measured cut, the dazzle conductor, the live score v2, the tape effects: built with Claude across the Mashtots sessions (Oct 2026).'],
  ['Mural', 'Van Khachatur, the three-part staircase fresco of the Matenadaran, Yerevan, 1959-60; photograph via Wikimedia Commons.'],
  ['Data', 'UD Classical Armenian CAVaL (Grabar Gospels, CC BY-NC-SA; 342,533 letters); UD Armenian ArmTDP (Eastern, 82,056 words); Mistral Nemo / Nemotron Nano 9B v2 Tekken tokenizer.json (read locally, nothing run); UDHR text for the token bill.'],
  ['Texts', 'Proverbs 1:2 in Grabar; the Lord\'s Prayer in Classical Armenian (dominicweb.eu wording). Both need a native reader\'s check.'],
  ['Software', 'X_ITE 16.5.1 (create3000; vendored, runs offline); WebAudio (the score and the effects are synthesised live, no samples).'],
  ['Fonts', 'Lora and Noto Serif Armenian, SIL Open Font License (fonts/*/OFL.txt).'],
  ['Honesty', 'Nobody has listened to the live score or the effects (the builder cannot hear): every audio figure is a measurement, not a judgement. Armenian text was checked only at script level.'],
];
