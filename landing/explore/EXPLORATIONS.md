# Mashtots Landing: explorations

28 October 2026 · the Landing as approved (204.25 s, v5 score) · prototypes in this folder, the approved files untouched.

**How each claim was checked.** *Measured*: a script or a run in the browser produced the number (the command is given). *By eye*: a screenshot in the Claude built-in browser (Chrome 152 on an Apple M3; the pane is 800 px wide, so the stage was 800 x 450 unless stated). *Not checked*: nothing was listened to, no headset, no second browser, no other GPU.

---

## 1. Three things to do first

1. **Fix the astronomer's helix (half of it was invisible).** *Done, at your request (28 Oct):* two bugs in `make_landing.py`, found and checked here (section 2). The fix restores the double strand through the letters, the polar axis, the ecliptic pole, the dashed precession circle, three orbits and the degree ticks, all of which were in the code and the README but not on screen. See them side by side: `helixfix/compare.html`.
2. **Give the graph acts their time, with speed ramps, and let the music follow.** Today each graph act gets 4.0 to 6.3 s (rates 1.5 to 2.0). The `retime/` timeline puts each act on whole bars of the groove (4 to 6 bars, 7.5 to 11.25 s) and *ramps* the speed inside it: slow motion where the eye should land, time-lapse through iterations. The `director/` page lets you audition any timing on the approved scene before anything is baked. The `live-score/` engine computes the score from whichever timeline is chosen (0 notes outside the harmony table on all three timelines).
3. **Let the alphabet speak for itself: measured data in the graph acts.** The graph acts run on three hand-made attention heads. A real corpus already on this disk (342,533 letters of Grabar) gives a measured graph whose *fastest* mode separates the vowels from the consonants on 35 of 36 letters. The one letter it disagrees on is Ւ, which in Grabar is the consonant *w* outside the digraph ու. It is built as a new act (`vowels`) inside the spectral cut, graded **Measured**, with a bootstrap.

---

## 2. Two bugs in the approved helix (Measured and by eye) — fixed 28 Oct

**Applied to `make_landing.py`** (backup and checksums in `helixfix/before/`): `if (v.x > 8.5)`, `LINE_PROPS` (1-px lines) and alpha × 1.6 for the armillary and the strand. *Measured:*

- **Clean rebuild first:** the unchanged generator, run in an isolated folder, reproduces the v5 scene byte for byte, and all 10 textures, `sections.json`, `timeline_real.json` and `prayer.json` with it.
- **After the fix:** the rebuilt scene differs from v5 in exactly five lines (two line widths, the threshold, two alphas). XSD valid, 0 errors, 0 warnings.
- **Installed:** `mashtots-landing.x3d` md5 `f5387a7856ab6d362dd2d191c93ae2fa` (v5: `07c67f5b9d69e428f06f52e17e313789`).

`helixfix/compare.html` shows v5 and the fixed scene side by side, locked to the same frozen moment, with shared camera keys. From camera 2 the v5 strand turns out to be a large translucent gold sheet; fixed, it spirals through the letters.


**Bug A: three elements of the armillary go through the wrong branch.** In `ArmillaryShader`, the first test is `if (v.x > 5.0)` (meant for the constellations, whose vertices are encoded as `x = 10 + star.x`, 9 to 11). The ecliptic pole (kind 6), the precession circle (kind 7) and the three orbits (kind 8) also have `v.x > 5`, so they never reach their own branches: they are drawn as "constellations" at 2 to 4 globe radii, vertical PAPER lines that swing round with the rotation and are magnified by perspective.
*Measured:* reproducing the shader's maths for those vertices predicts vertical lines at x = 599, 727 and 797 px (800-px pane) at T = 137.5 s; the streaks seen there were at 597, 727 and 795. *Fix:* `if (v.x > 8.5)`.

**Bug B: two-pixel lines draw almost nothing.** The v5 tuning gave the armillary and the strand `LineProperties linewidthScaleFactor='2'`. In X_ITE 16.5.1 these two ComposedShader line sets then render only partly: of the armillary only the constellations, of the double strand a small fan.
*Checked live, by eye:* the same frozen frame with the factor switched to 1 shows the full armillary, recoloured red with a debug shader to be sure. Width 1 also shows the four turns of the strand. The mechanism inside X_ITE was not investigated.
*Quick fix* (in the copy here): 1-px lines with alpha × 1.6. *Proper fix* (proposed): expand the lines to 2-px quads in the vertex shader, as `ArcShader` already does for the attention arcs.

*Before and after* (by eye, t = 20 s, the tour): the approved scene shows a sparse globe with a few grey bars; the fixed build shows the ticked ecliptic and equator, the polar axis, the precession circle, three orbits and the double strand. See them side by side:
`director/index.html?scene=approved&t=20&paused=1` and `director/index.html?scene=retime&preset=approved&t=20&paused=1` (the `approved` preset is the approved timing plus the fixes).

Neither bug is visible to the validator. `validate_one.py` (x3d_mcp) passes both the approved scene and the re-timed build: XSD valid, 0 errors, 0 warnings, 5 infos. A static check reads structure, not what a shader draws (the same blind spot the jepa-bridge notes measured: 23 of 40 seeded defect classes missed). See 5.5 for a cheap behavioural check that would have caught both.

The brightness, the polar axis's length (it now crosses the whole frame, as coded) and the strand's prominence beside the tour's arcs are yours to tune once they are visible.

---

## 3. Time: the eye-catching sections, expanded, contracted, ramped

What the approved timeline gives each part (Measured, `retime/check_timeline.py`):

| part | real time | act rate | note |
|---|---:|---:|---|
| the stone, the flight | 6.15 s | 1.0 | the deck's pace |
| the helix lifts | **2.0 s** | 1.0 | one of the most striking moves, over in two seconds |
| the tour of 36 | 40.8 s | 1.5 | 1.13 s a letter |
| writing 405 | 11.75 s | 1.15 | |
| prayer, numerals, Shirakatsi (holds) | 17 + 12 + 10 s | 0 | |
| embedding space | 8.1 s | 1.3 | |
| **ten graph acts** | **46.2 s in all, 4.0 to 6.3 s each** | **1.5 to 2.0** | about 2 bars of the groove each, starting off the bar line |
| pre-training finale | 37.5 s | hold, 20 bars | |

**What `retime/` adds.**

- **Whole bars.** A segment can be sized in bars of the 128 BPM grid, so every graph act starts on a downbeat.
- **Smooth speed ramps.** A segment can carry a speed profile: relative rates at fractions of its length, linear in between, scaled so the act still covers exactly its act range. Act time becomes quadratic inside a piece, so slow motion eases in and out instead of jumping. The GLSL warp gains one array (the rate at the end of each piece).
- **New holds.** An act can be split with a new hold, as the measured vowels act is.
- **Fill.** One segment can fill whatever is left of a target loop length.

*Measured:* the `approved` preset reproduces `timeline.py` exactly (difference 0 at every 10 ms). Every preset is checked for continuity, monotonic act time, exact act ranges and bar alignment.

**Two presets** (`retime/presets.json`):

| | approved | **graph-expanded** | same-length |
|---|---:|---:|---:|
| loop | 204.25 s | 255.05 s | 204.25 s |
| graph half (embedding to collapse) | 55.6 s | **105.0 s** | 75.0 s |
| each graph act | 4.0-6.3 s | 4-6 bars (7.5-11.25 s) | 3-4 bars |
| new measured act (vowels) | - | 4 bars | 3 bars |
| tour | 40.8 s | 40.8 s | 28.4 s (fills) |
| prayer / numerals / Shirakatsi | 17 / 12 / 10 s | same | 14 / 10 / 8 s |
| helix lift | 2.0 s | 3.4 s, slowed to 0.45 in the middle | 2.0 s |

**The ramps, and why** (graph-expanded). The idea is a film editor's speed ramp: slow where something is revealed, time-lapse where the process repeats.

- **Lift:** slowed in the middle (0.45×). The letters rise into 3D; the eye needs that moment.
- **Web:** 0.8× while the 630 chords draw in, then 1.2×.
- **Message passing:** 0.6× for the first hop from Ճ (the only hop you can follow), then faster.
- **Fiedler cut:** 0.45× through the drop; then the 4-bar vowels hold; then the rest.
- **PageRank:** 0.55× for the first iterations (rank visibly flowing), 1.7× time-lapse to convergence.
- **Annealing:** fast through the hot middle (1.5×), slow at both cold ends (0.6×), where structure freezes in. Time itself cools.
- **Descent:** slow first steps, then quicker through the momentum spiral.
- **Markov walk:** time-lapse at the end (1.6×), as the occupancy converges.
- **Fourier, Poincaré, SVD:** near the deck's own pace, on 5 or 6 bars.

**Auditioning without baking.** `director/index.html?preview=graph-expanded` plays the approved scene through that preset. Holds map proportionally; a new act (the vowels) shows as a frozen frame until baked. *Measured:* the mapping lands on the same act time at every probe point, for example 137 s of the preset → 123.48 s of the approved scene (act TSP + 3).

What I would contract (offered as the `same-length` preset): the three medieval holds by 2 to 3 s each, and possibly the tour. A shorter tour costs the per-letter plate sounds their room, so it is your call. I would not contract the finale: its 20 bars carry the bill, the shapes and the drop on the beat grid.

---

## 4. Stage by stage

Each stage: what it does → what is strongest → ways to take it deeper (grounded in the code).

**The stone and the flight (0-9 s).** 36 letters leave the painted mural on seed-405 Bezier paths with comet-trail copies, ringing the stone; ripples where they land on the gilt line. *Strongest:* the trails and the cascade of four rising harp runs (the stone's own ladder, row = key). *Deeper:*
- give each flight a speed curve from its letter's frequency in Grabar (common letters leave first, or fastest);
- make the comet trail out of the letter's own ink-order texture (`pen_time` already computes it), so the trail is the letter being un-written;
- land each letter with a Chladni ripple of its own mode instead of a plain ring.

**The astronomer's helix (9-11 s and behind the tour).** The letters in a true-3D helix (four turns of nine, the numeral rows) inside an armillary sphere with stars, planets and constellations. *Strongest:* the true 3D (cameras 2 and 3 show it). *Deeper:*
- **fix it first** (section 2): the strand and most of the armillary are invisible today;
- let the armillary keep astronomical time: precession at the real rate (one degree per 71.6 years), scaled so a full turn takes a loop, with a caption on the scale;
- place the three planets from Shirakatsi's own cosmology (he wrote on the planets and eclipses), graded as historical, not modern;
- give the strand's running light the tour's spotlight timing (it already glows at the spotlit stretch).

**The tour of the 36 (11-52 s).** Per letter: card, three attention heads (arcs), the 36 x 36 map, the stone grid, a Chladni figure (mode = column + 1, row + 1), a struck-plate sound. *Strongest:* the rhythm of one letter per 1.1 s with its own plate and sand. *Deeper:*
- the sand is static (`exp(-f²)`). Grains could *find* the nodal lines: integrate dx/dt = −∇(f²) in the vertex shader from a seeded start, with steps proportional to the letter's age. That is stateless (no Script) and deterministic;
- for the four letters on the diagonal (n = m: Ա, Ի, Յ, Տ) the antisymmetric figure vanishes and the shader falls back to a plain product, a square grid unlike the curved figures of the other 32; the symmetric combination (cos·cos + cos·cos) keeps them in the family;
- **honesty:** the map's subtitle reads `softmax(QKᵀ / √d)`, which suggests a model. The heads are hand-made features (vowel and voicing, grid position, order; `buildAttention()` in the deck). Label them "authored heads", or replace them with measured ones (5.3).

**Writing 405 (52-64 s).** Proverbs 1:2 written glyph by glyph, each glyph inked in calligraphic order (a geodesic-distance "pen time" inside the glyph, `pen_time()`), flying from its source letter, with causal attention arcs. *Strongest:* the ink order, a real computational idea. *Deeper:*
- slow the first word to a calligrapher's pace (a ramp), then let the rest stream;
- one arc per glyph shows the attention to its previous glyphs: weight them by measured Grabar bigram probabilities (the data are in `data-graph/out/graph.json`);
- the "ink" could bleed: a 2-tap diffusion in the fragment shader keyed to pen time.

**The Lord's Prayer (64-81 s).** Grabar text, written the same way; one line left out because of Օ, which the scene says. *Strongest:* the honesty note. *Deeper:*
- set it to the Armenian Church's eight-voice system (ութձայն): the duduk in one *dzayn* for the prayer instead of the Dm pad (needs a musician's source; do not invent a mode and call it liturgical);
- show the omitted line as a ghost (the outline of Օ only), so the absence is visible.

**Letters are numbers, Shirakatsi's table (81-103 s).** The 4 x 9 numeral matrix; 405, 1512, 2026, 1475 light their letters; Shirakatsi's table recomputed in his numerals. *Deeper:*
- let the visitor type a number or a word (5.8);
- write the products of the table at the speed of a hand (ink order again), one row per bar.

**Embedding space (103-111 s).** The letters on two hand-chosen articulatory axes, coloured by class; the 3 x 36 x 36 tensor turning. *Deeper:*
- a measured embedding: the top two eigenvectors of the Grabar co-occurrence graph (a spectral embedding, computed in `data-graph/`), shown beside or morphing from the authored one;
- tokenizer space: the letters placed by the merge rank of their bigrams (Tekken merges ու first, at rank 1,986).

**The graph acts (111-157 s).** 630 chords on the ring weighted by attention; message passing from Ճ; the Fiedler cut; PageRank; annealing; gradient descent; the Markov walk; Fourier epicycles redrawing the PageRank curve; the Poincaré disk with geodesics; SVD ranks and k-means. *Strongest:* each act is a real computation, run by the deck's own JavaScript and baked. *Deeper:*
- **time** (section 3);
- **flow** (built): particles carry the actual flow along the heaviest chords, d·r_j·W_ji per PageRank iteration and W_ij·h_j per message layer. In the authored graph rank flows mostly between alphabet neighbours (the "order" head), so the streams hug the ring; on the measured graph they would cross it;
- **the measured vowels** (built): a hold inside the cut where the measured graph takes over;
- annealing: let the chords' alpha shimmer with the temperature (thermal noise amplitude ∝ τ);
- the Markov walk: walkers as comets whose tails fade with the mixing time;
- Poincaré: a faint {7,3} tiling behind the geodesics, so the hyperbolic metric is felt;
- SVD: the residual energy as a fading veil over the ring.

**Pre-training in Armenian (158-196 s).** 20 bars at 128 BPM: the token bill (Measured), one word in many shapes (Measured), the scaling law L(D) with placeholder points (said so), the Armenian-only floor (Established inside 70 M to 1 B, Estimate beyond), the closing Conjecture. *Strongest:* the grades on screen. *Deeper:*
- add the census result as a beat: Nemotron Nano 9B v2's tokenizer is Tekken (same merges, verified in the sibling census; 2.99 tokens a word on Eastern Armenian);
- "the machine's first Armenian bigram is ու" (Tekken merge rank 1,986, Measured): Mashtots's digraph for /u/, rediscovered by a compression algorithm;
- replace the law's placeholder points with a measured point when there is one (the deck already marks them).

**Return and colophon (196-204 s).** The letters fall home; the colophon dated in the Armenian era (1475 = 2026). *Deeper:*
- mirror the opening exactly (the flight paths reversed with the same seed);
- let the colophon be written in ink order like the sentence.

---

## 5. Technical directions, with evidence

**5.1 Live generative audio in WebAudio (built: `live-score/`).**
- *Re-anchoring:* the score is computed from the timeline at run time. Before the groove, events sit at act times; inside holds, at fractions; the groove sits on the bar grid from the finale, with the build regenerated for however many bars it now has.
- *Voices:* plucked voices are additive buffers using the Python formulas, cached; sustained voices are native oscillators.
- *Measured:*

| check | result |
|---|---|
| events | 2,232 (approved) · 3,017 (graph-expanded) · 2,553 (same-length) |
| harmony audit (make_music's own rules) | **0 notes outside the table on 3 timelines × 3 seeds** (1,045 to 1,436 pitched notes) |
| offline render, whole loop at 32 kHz | 15 to 26× real time (two runs: 13.4 s and 7.7 s) |
| peak | −1.1 dBFS |
| loudness by second against the approved mp3, same timeline | Pearson r = 0.61; sections within ±4.5 dB (helix −4.5, return −4.0, tour +2.5) |
| following the director | drift −2 to −12 ms (the sound a hair behind); pause leaves 0 nodes; at half speed the score advances 1.00 s per 2 s with the picture |

- *A bug found and fixed on the way:* finished notes kept their gain and panner in the graph. Before the fix a whole-loop render did not finish in 100 s; after it, 7.7 s.
- *Not done:* the tour styles (duet, taksim, dhol, pulse), the composed duduk anchors (entrance, prayer, Amen, hook), saw stabs and risers, BS.1770 stem balancing. That is why the tour, helix and return differ most from the mp3. *Not listened to.*
- *Verdict:* worth it. It is what makes re-timing, seeds per loop, slow motion and interaction possible. Path to replace the mp3: port the missing layers, then calibrate stem gains to the mp3's measured section loudness.

**5.2 WebGPU or compute for the graph stages (evaluated, not built).**
- *Measured:* this browser has WebGPU (Metal 3, 4 GB storage buffers, 1,024 invocations per workgroup).
- *Measured (plain JS, one core; `node data-graph/bench_graph.mjs`):* a Fiedler vector (300 power steps) plus PageRank (15 iterations) takes 1.3 ms at N = 36, 105 ms at N = 500 and 1.8 s at N = 2,000.
- *Verdict:* for the 36-letter acts WebGPU buys nothing; they are baked and would cost a millisecond live. It becomes relevant for a vocabulary-scale graph (a tokenizer's 130k merges, a 2,000-token attention graph) or for particle systems in the 10^5 range (the Chladni sand, the flow). X_ITE renders through WebGL2, so WebGPU would mean a second renderer.

**5.3 Real data for the tour and the graph (built in part: `data-graph/`).**
- *Measured, no download:* UD Classical Armenian CAVaL, already on disk in `../armenian-tokenizer-census/data`:

| quantity | measured (Grabar) | deck (authored) |
|---|---|---|
| corpus | 4,781 sentences, 73,445 words, 342,533 letters (Օ and Ֆ never occur) | - |
| fastest mode (most negative eigenvalue −0.644 of D⁻¹ᐟ²CD⁻¹ᐟ²) separates the deck's vowels | **35 of 36** (only Ւ differs) | - |
| bootstrap, 200 resamples of the sentences | every vowel on the vowel side 100 %, Դ 7 %, Ւ 0 % | - |
| Sukhotin's 1962 algorithm finds | ԱԵՈԻԷԴԸ (34 of 36 agree: Դ in, Ւ out) | ԱԵԷԸԻՈՒ |
| Fiedler cut separates vowels | 56 % | 64 % |
| PageRank, measured vs authored | Spearman +0.02 (top: ԱՆԵՈՐ, which is ρ = +0.95 with letter frequency) | top: ԼՆՅ |
| edge weights, measured vs authored (630 pairs) | r = −0.11 | |
| Tekken's two-letter Armenian merges | 198; first ու (rank 1,986), then ան, ակ, եր, ին, այ, ար, ել, ամ, ատ | |

- *A caution I hit and kept in the report:* the top eigenvector of the *plain* Laplacian also gives "97 %", but it is localised on the hub Ա, with every other value within ±0.06. The normalised operator is the robust one, hence the bootstrap.
- *Next, needs your permission:* attention maps and embeddings from an open model on Armenian text. Candidates are in the sibling note `mashtots-nemotron-research.md` (Gemma-4-E4B, arm-gemma-e4b). That means downloading a model (several GB); I did not.

**5.4 WebXR (evaluated, not built).**
- *Measured:* `navigator.xr` exists, but `immersive-vr` and `immersive-ar` are unsupported here (no headset).
- *Not checked:* X_ITE's WebXR path in this version.
- *Verdict:* the helix, globe and strands are true 3D and would read well in a headset (once fixed, section 2). Most acts are drawn on the slide plane (z = 0) and would be flat cards. A worthwhile "helix room" sibling: the globe at the viewer's scale, letters orbiting. Effort M, impact medium; the shader-displaced shapes need correct bboxSize (already set).

**5.5 Validation with x3d_mcp and behavioural checks.**
- *Measured:* both scenes pass x3d_mcp (XSD + semantics). It did not see the two helix bugs.
- *Proposal: behavioural checks that run here and are cheap:*
  - **shader unit tests:** re-implement a shader's vertex maths in Python (as I did for the armillary) and assert that every element lands inside the frame and its own radius;
  - **frame probes:** the director's freeze makes any frame reproducible (`?t=SEC&paused=1`). A Playwright script can capture the 10 plate frames and compare them with stored images (a "visual regression" of the piece).

**5.6 Round trips with x3d-blender-io (reasoned, not run).** Nearly every shape's coordinates are *parameters* (for example `3 0.0139 0` means "a tick on the ecliptic"), turned into positions by the shader. An X3D importer would place garbage. A Blender round trip needs a bake: evaluate `lstate()` and the act shaders on the CPU (the Python generator already has the data) and write keyframed geometry. Effort L; value: print-quality renders, film. I did not touch the user's live Blender.

**5.7 Performance headroom (Measured).**
- The re-timed build: 2.67 MB, a 7.4 s build, 900 extra flow quads, 36 warp pieces instead of 24.
- It holds **60 fps, the display's cap, at a 1920 × 1080 stage** at the four busiest moments: PageRank with flow, the vowels act, the finale's last chart, and the tour.
- Headroom above vsync cannot be read this way; a weaker GPU is the real test (not available).

**5.8 Accessibility (built in `director/`).**
- **Pause, slow motion and frame steps**, from writing the seek offset every frame. *Measured:* the scene holds at T = 137.000 s for 2 s.
- **Plates:** one still per act, stepped with the arrows.
- **Calm mode:** half speed, the drifting particles hidden.
- **Reduced motion:** honours `prefers-reduced-motion` by starting paused and calm.
- **Captions:** one per segment, with grades, in an `aria-live` region.
- **Keyboard:** every control (space, arrows, `,` `.`, `[` `]`, L, C, M, P).
- *Not checked:* with a screen reader. Proposal: move these into `index.html`.

---

## 6. Creative directions

**Music.**
- Sonify the measured split in the vowels act: vowels sung by the duduk, consonants plucked on the kanun.
- PageRank as a voicing: each letter's pitch on its ladder, loudness ∝ rank, so the chord converges as the ranks do.
- The Fiedler cut as stereo: f > 0 left, f < 0 right.
- The prayer in one of the eight voices of Armenian chant, from a real source.
- The build's ramps on the bar grid (built into the timing); a drum fill into each act's downbeat.

**Narrative and pacing.**
- Three movements: Script (stone, helix, tour, writing), Number (prayer, numerals, Shirakatsi), Machine (space, graph, pre-training), then Return.
- One breath of silence before the drop.
- The measured act placed where the authored maths ends: first the deck's model of the alphabet, then the alphabet's own data.

**Typography and calligraphy.**
- Erkatagir (the uncial of the 5th century) for the stone. It needs an OFL font with erkatagir forms (ask before any download).
- Bolorgir for the prayer.
- The ink-order texture could drive a real calligraphic stroke animation if stroke data exist.

**Sibling pieces.** The same pipeline for alphabets made by one person for one book, each with a measured graph from a corpus (Sukhotin's vowels per language):

- Gothic (Wulfila, 4th c.);
- Glagolitic (Constantine-Cyril, 9th c.);
- Georgian and Caucasian Albanian, which Armenian tradition (Koryun) also credits to Mashtots: grade it as tradition, contested;
- the Cherokee syllabary (Sequoyah, 1821).

**Interaction: play the stone.**
- 36 `TouchSensor`s on the stone grid; their `touchTime` ROUTEd to a shader field, so the plate shows the touched letter's mode with no Script.
- The page hears the touch (SAI callback) and plays its kanun note, plate and sand through the live engine.
- Spelling a word shows its number in Armenian numerals (the scene's `to_arm()`) and lights its letters on the graph.

**Honesty.** Keep the four grades on screen and add a fifth word where needed: **authored** for the hand-made heads and embedding. The vowels act shows the pattern: the corpus, the size, the operator, the one disagreement, the bootstrap.

---

## 7. What I built and measured

| prototype | what it shows | key measurements |
|---|---|---|
| `retime/` | presets, ramps, new holds; a patched COPY of the generator (`patch.py` rebuilds it from the originals: 17 patches to the generator and 6 to the GLSL, each must match exactly once) | `approved` preset = `timeline.py` exactly; build 7.4 s; XSD valid, 0/0 semantic; 60 fps at 1080p |
| `retime/` new act **vowels** | the measured fastest mode lifts the vowels out of the ring; chords crossfade to measured bigram weights; graded captions | by eye; the data as in 5.3 |
| `retime/` **flow** | rank as light along the 90 heaviest chords per act (PageRank, message passing) | by eye |
| `retime/` **helix fixes** | Bug A and Bug B (section 2) | streak positions predicted within 2 px; before/after by eye |
| `director/` | transport, captions, calm, plates, preview of presets on the approved scene, live score for builds | freeze exact; preview maps to the right act time; drift −2 to −12 ms |
| `live-score/` | the score from any timeline | 0 notes outside the table (9 runs); 15-26× real time; r = 0.61 against the mp3; peak −1.1 dBFS |
| `data-graph/` | the measured Grabar graph against the authored one | as in 5.3 |

## 8. Ranked directions (effort S/M/L, impact)

| # | direction | effort | impact | status |
|---|---|---|---|---|
| 1 | Fix the helix (Bug A one line; Bug B 1-px now, shader quads later) | S | **high** | **applied to the approved scene, 28 Oct** |
| 2 | Re-timing with ramps + director auditioning | M (adoption) | **high** | prototype works end to end |
| 3 | Measured graph: vowels act, then measured PageRank and Fiedler beside the authored | S-M | **high** (truth, surprise) | act built |
| 4 | Live score replacing the mp3s | M-L | high | engine works; missing layers listed |
| 5 | Flow particles in more acts (walk comets, annealing shimmer, residual veil) | S each | medium-high | PageRank and message passing built |
| 6 | Accessibility into index.html (pause, plates, captions, reduced motion) | S | medium | built in the director |
| 7 | Behavioural validation (shader unit tests, frame probes) | S-M | medium (prevents another invisible helix) | one test done by hand |
| 8 | Chladni sand that finds its nodal lines | S | medium | designed, not built |
| 9 | Play the stone | M | medium-high (for a public page) | designed |
| 10 | Real attention from an open model | M (+ a download) | high | needs your yes |
| 11 | WebXR helix room | M | medium | needs a headset to test |
| 12 | Sibling alphabets | L | high (as a series) | idea |
| 13 | WebGPU | L | low at 36 letters | not needed now |
| 14 | Blender bake | L | low-medium | reasoned |

## 9. Recommended next step

One short session on the approved generator, in this order:

1. *(done 28 Oct)* the helix fixes; look at the helix with fresh eyes (`helixfix/compare.html`), and decide the strand's brightness and the polar axis's length;
2. replace `timeline.py` with `timeline_retimed.py`. It is backward compatible: the `approved` preset reproduces today's timing exactly. Then pick a preset with the director;
3. if you like the expanded graph half, adopt the live score for the modern half first (the groove is the part it already does best), and keep the mp3 for the approved timing until the tour layers are ported.

## 10. Proposed changes to the approved files (not applied)

- *Applied 28 Oct:* `make_landing.py`, `ArmillaryShader`: `if (v.x > 5.0)` → `if (v.x > 8.5)`.
- *Applied 28 Oct:* the armillary and the strand: `linewidthScaleFactor='2'` → `'1'` with alpha × 1.6. Still open: 2-px quads expanded in the vertex shader, if you want the v5 width back.
- The camera and the spectral moments (`explore/retime/camspec.py`): 10 small patches, all optional per preset.
- `timeline.py` → `explore/retime/timeline_retimed.py` (+ `presets.json`); `landing_glsl.py` gains `SRE` (rate at the end of a piece) and the quadratic warp (6 small patches, in `explore/retime/patch.py`).
- `index.html`: the director's transport and captions; the live score as an option.
- The tour's map subtitle: say that the heads are authored.

## 11. Limits and open questions

- Nothing was listened to. The live score is checked only by audit, loudness and timing.
- The Armenian of the new captions needs a reader: «չափված», «ձայնավոր · vowels», «բաղաձայն · consonants», «Գրաբար, 342 533 տառ».
- All visual checks were in an 800-px pane, apart from the 1080p fps runs; one browser, one GPU.
- The `same-length` preset shortens the tour to 28.4 s (0.79 s a letter); that may be too fast.
- An early observation was wrong, corrected in this note: I first took the streaks for a load-time glitch. They are Bug A; they come and go because their positions turn with the globe.

---

## 12. Second round (28 Oct): real 3D, the spectrum, more

You asked for camera sweeps and corner shots that show the piece is real 3D, and for letters coloured on the spectrum by the piece's own metrics. Both are built into the re-timed copy (`retime/camspec.py`, driven by `presets.json`) and checked in the browser.

### 12.1 The camera is a function of the one clock (built)

Every vertex shader ends in `x3d_ProjectionMatrix * x3d_ModelViewMatrix * position`. The copy inserts one matrix, `CAM`, computed in `tl()`: `x3d_ModelViewMatrix * CAM * position` (51 insertions, all of them; the 48 uniform declarations are untouched).

- `CAM` turns the whole set (mural, helix, letters, cards, labels) about a pivot and pushes it towards the viewer.
- A sweep is therefore a camera move that follows seeks, the director's pause and speed, and any re-timing. It needs no Script and no Viewpoint animation (X_ITE's `TimeSensor.fraction` is wall-clock based and ignores the seek offset, so interpolators would not stay in sync).
- The choreography is data: each move is a weight `k` (any GLSL expression of the clock), a yaw, a pitch, a push and a pivot.

| move (graph-expanded) | when | yaw / pitch / push | what it shows (by eye) |
|---|---|---|---|
| corner shot of the helix | the lift, released by the tour's second letter | −0.45 / −0.16 / 1.0 | the slide plane recedes; the helix stands as a column inside the armillary |
| a glance from the other corner, back, then from below | each new row of the tour (keys A, E, B minor) | ±0.18 / ±0.06 / 0.35 | the helix's depth; the card stays readable |
| orbit of the attention tensor | the embedding space | −0.32 / 0.12 / 0.7 | the 3 × 36 × 36 tensor reads as a block of cells |
| corner shot of the ring | PageRank | 0.55 / 0.22 / 0.7 | rank as height (12.3) |
| a slow push across the drop | finale bars 10 to 18, swelling over 3.5 bars | 0.06 / 0.03 / 0.9 | the law and the letters' cloud come closer; at 1.6 the chart's heading slid under the tabs, so 0.9 |
| the set breathes with each kick | the same bars | 0 / 0 / 0.12 × kick | a small pump on the beat |
| crane down | the return | 0.22 / −0.24 / 0.6 | the letters falling home onto the gilt line |

**The title block stays put.** The title block's labels (on the one-shot intro clock) undo the camera (`inverse(CAM)` in the label shader) and dim by up to 55 % while a move is on. They read as an overlay in front of a turning set, instead of swinging into large slanted text.

*Measured:* 59–60 fps while playing the lift, the tensor orbit and the drop (visible pane; 60 is the display's cap). Build 7 s, 3.05 MB; XSD valid, 0/0 semantic.

### 12.2 Colour on the spectrum, by the piece's own metrics (built)

While a *spectral moment* is active, the letters take the colour of a metric, and a legend says which.

- **The letters' notes, as light.** Each letter's note in the score (the stone's ladder, `make_music.lf_row`) is doubled 40 or 41 times into 400–800 THz; visible light spans almost exactly one octave. The colour is the CIE 1931 2° colour of that frequency.
  - *Measured:* D → 464 nm blue, E → 413 violet, F → 392 violet, G → 696 red, A → 619 orange, B♭ → 588 yellow-orange, B → 550 yellow-green, C → 522 green, C♯ → 489 cyan. Each row of the stone, a minor scale, sweeps the rainbow.
  - *Checked numerically:* the analytic CIE fit (Wyman, Sloan and Shirley 2013) is good between 420 and 650 nm but drifts in the tails (cyan at 392 nm, orange at 696 nm). The true spectrum's chromaticity is nearly constant beyond those points, so the hue is taken at the nearer end; brightness is normalised for legibility.
  - *Grade:* every step is physics; mapping sound to light by octaves is an **authored** choice, and the legend says so.
- **Plain numbers on Turbo,** a rainbow made perceptually even (*checked:* dark blue → cyan → yellow-green → orange → dark red):
  - the numerals by log₁₀ of their value: each decade column becomes a band;
  - the vowels act by the **Measured** fastest mode: vowels warm, consonants cool;
  - PageRank **as it converges**: every letter starts at 1/36 (one colour) and the colours separate iteration by iteration. The node glows take the same colour.
- **The legend:** a spectrum bar (for notes, with dark ticks where D, E, F, G, A, B, C fall in light), what the colour means, and the ends.

### 12.3 Rank as height (built)

During PageRank each letter rises out of the ring's plane by its rank, rising as the iteration converges. The chords, the flow beads, the node glows and the labels follow, because they all place letters with `lstate()`. With the corner shot (12.1) the ring becomes a relief; on the slide camera you would see almost nothing. *By eye:* the most convincingly three-dimensional frame of the graph half.

### 12.4 More suggestions (not built)

- **The alphabet's emission spectrum.** The 36 notes as light fall on only 10 wavelengths (the ten pitch classes the stone uses). Draw them as spectral lines, brightness = how many letters share a line: an image that joins letters, music and light.
- **A 3D spectral embedding of the measured graph.** The fastest mode and the next two eigenvectors of the Grabar graph as x, y, z: a point cloud of the alphabet to orbit in a corner shot, with the vowels apart.
- **Each tour card shows its letter's light:** "Ա · D3 146.8 Hz → 464 nm", with a swatch.
- **The Chladni figure in its note's colour,** so the plate, the sound and the colour are one quantity.
- **Camera on the beat in the finale:** a slow push across the drop (bars 10–18), a one-degree nudge on each kick.
- **The stone carved in true 3D:** extruded glyphs, lit, for the first seconds, before the letters fly as light.
- **Depth for every graph act,** like rank as height: Fiedler value or message-passing activation as z, each with its own corner shot.

### 12.5 Look-at shots, viewpoint blending, stereo (built, third round)

- **Look-at shots.** A camera move can now be a real shot: an eye and a target, both GLSL expressions of the clock (with `u`, the shot's progress, and named points: the helix centre, the ring, the tensor, the stone). Every move has a weight; weights blend the eye and the target as offsets from the slide camera, so the camera glides into a shot and out again with no cut. In graph-expanded:
  - the lift orbits a third of the way round the helix, rising;
  - the last letters of the tour: a dive inside the helix, the letters circling the viewer;
  - PageRank: a high corner of the ring, rank as relief;
  - the return: looking down onto the stone.
  The older yaw/pitch moves (tour glances, tensor orbit, the drop's push) still compose with the shots.
- **Stereo** (`stereo/`): an `eyeX` uniform in every shader, ROUTEd from an `Eye` TimeSensor, moves the eye sideways while the target stays put, so the two eyes converge on what the shot looks at. *By eye:* the anaglyph separates by depth as it should (the helix near the screen in the lift shot, the cards further off); side by side gives two full 16:9 views. *Not checked:* with glasses, in a headset, frame rate with two scenes (the pane was in the background).
- **Not done here, and why:** WebXR. This browser reports no immersive-vr or immersive-ar session (no headset), so a WebXR mode could not be tested; side by side plays in a headset's flat-video or browser view as a stand-in.

