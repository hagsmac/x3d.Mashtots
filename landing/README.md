# Mashtots System 2, the Landing, as X3D (fork of the approved slide-1 port)

`~/Projects/x3d/work/mashtots-slide1-FROZEN/` (read-only, with checksums and a tarball) is the slide-1 port you approved. This folder is the fork that grows
it into the whole Landing (`MashtotsLanding.dc.html`, v7), plus a medieval middle and a modern finale. One loop, 204 s.

## Run it

```bash
cd ~/Projects/x3d/work/mashtots-landing && python3 serve.py 8794
```

Open http://127.0.0.1:8794/index.html (WebGL2 browser; X_ITE 16.5.1 is vendored). The scene is 2.5 MB with about 60 shaders: allow ~15 to 25 s to load.
`serve.py` is a static server with caching off (the generator rewrites textures) and byte ranges on (a browser can only seek a score it has fully downloaded unless the server answers Range requests; `python3 -m http.server` does not, so use `serve.py`).

- **Section tabs** across the top (ten major sections): click to skip, or use the left and right arrow keys. A thin gold bar shows where you are. `index.html#tour` opens at a section.
- **Listen** (bottom left) starts the score; browsers keep audio muted until a click. The page keeps the audio element in step with the clock (it nudges the playback rate by 5 % when it drifts, and jumps only if it is lost), also after you skip. The second button cycles the full score, the harp-and-duduk version and the previous (v3) mix.
- Keys `1` slide camera, `2` the helix from the side, `3` the ring up close, `4` the painted stone, `f` free navigation (drag to orbit; the helix and the globe are real 3D).
- `?slide1` plays the approved slide-1 port, `?classic` its shader-free fallback.

## What plays (real time, 204.25 s)

| time | section | what |
|---|---|---|
| 0 | **Քար** The stone | the 36 letters leave the painted stone (it rings: a Chladni sand figure per leaving letter), fly on the deck's seed-405 Bezier paths with comet trails, settle on the gilt line |
| 9 | **The astronomer's helix** | they lift into a turning 3D helix inside the astronomer's globe: now a double strand threaded through the letters, light running up and down it (the spotlit letter's stretch glows), and an armillary around it: degree ticks on the ecliptic and the equator, the polar axis, the ecliptic pole, a dashed precession circle, three orbits with comet-trail planets, constellation lines between the stars |
| 11 | **Տառ առ տառ** The tour of 36 | card, three attention heads, 36 x 36 map, stone grid, the letter's Chladni figure |
| 52 | **Writing 405** | the first sentence (Proverbs 1:2) written glyph by glyph, inked in flight, causal attention arcs |
| 64 | **Հայր մեր** The Lord's Prayer | the Grabar text written the same way (one line left out, see below) |
| 81 | **Letters are numbers** | the 4 x 9 numeral matrix; 405 = ՆԵ, 1512 = ՌՇԺԲ, 2026 = ՍԻԶ, 1475 = ՌՆՀԵ light their letters; then Shirakatsi's table, recomputed in his numerals |
| 103 | **Embedding space** | the letters on two articulatory axes, the 3 x 36 x 36 attention tensor turning beside them |
| 111 | **The alphabet as a graph** | 630 chords on the ring; GNN message passing from Ճ; the Fiedler cut; PageRank; annealing; gradient descent; the Markov walk; Fourier epicycles; the Poincare disk; SVD + k-means (each act at 1.5 to 2x the deck's pace) |
| 158 | **Նախաուսուցում** Pre-training in Armenian | 20 bars at 128 BPM: the token bill, one word in many shapes, the law (the drop), the Armenian-only floor |
| 196 | **Տուն** Return | the letters fall home; the colophon (written in the Armenian year 1475 = 2026) and the mural credit |

The slow, astronomical half runs at the deck's pace; the tour and the writing are a little quicker; from the embedding space on the graph acts accelerate; the finale is on a beat grid.
The deck's act time (193.31 s) is warped onto real time by `timeline.py`; holds freeze act time while the new acts play.

## Numbers and honesty

- Every number of the graph acts comes from the ORIGINAL JavaScript, run in Node (`extract_landing_data.js`) and baked.
- The finale's figures are the deck's own, with its grades: the token bill (UDHR, Armenian / English: o200k 1.51, Mistral Tekken 1.74, Gemma 3/4 2.67, DeepSeek 2.87, Qwen 5.41, Llama 3.1 8.73, cl100k 10.15) and the word shapes are **Measured**;
  the data-scaling law L(D) = 1.69 + 410.7 D^-0.28 is the published fit and **its three points are placeholders** (the deck says so, so does the scene); the Armenian-only floor bpb(N) = 4.9e5 N^-0.795 + 0.439 is **Established** inside 70 M to 1 B parameters and an **Estimate** beyond.
  The closing line (a sacred language can become a domain programming language) is the deck's **Conjecture**.
- The Lord's Prayer is the Classical Armenian text as printed on dominicweb.eu (the same wording appears on several church sites; spelling varies a little between editions). The glyph atlas has the 36 letters of Mashtots, so the line
  *Զհաց մեր հանապազորդ տուր մեզ այսօր* is left out: its Օ is one of two letters added in the Middle Ages. The scene says so. Please have an Armenian reader check the text.
- The Chladni mapping (a letter is the plate mode (n, m) = (column + 1, row + 1)) is authored, not a property of Armenian.

## How it is built

| file | what |
|---|---|
| `extract_landing_data.js` | runs the ORIGINAL Landing math in Node and dumps `scratch/landing.json` |
| `make_landing.py` | bakes it into `mashtots-landing.x3d` (2.5 MB): ~60 ComposedShaders, one clock, no Script |
| `timeline.py` | the real-time timeline: act time warped onto real time, holds for the new acts, bar grid for the finale |
| `landing_glsl.py` | the shared GLSL: warp, helix in true 3D, ring, every letter layout (`lstate`), interlude and finale factors |
| `landing_text.py` | text atlas (Noto Serif Armenian and Lora from `fonts/`, SIL OFL; Georgia, Arial Unicode, Mshtakan as fallbacks; sub/superscripts faked where no font has them) |
| `make_music.py` | the score (v4): `landing_score.mp3` (full) and `landing_score_harp.mp3` (no drums, bass, saws), 204.25 s, the length of the loop (`landing_score_v3.mp3` is the previous mix); `score_tools.py` measures loudness / roughness, `analyze_score.py` and `view_spec.py` report and draw |
| `sections.json` | the ten sections and the shader names, read by the page |
| `mkstill.sh SEC [x y z]` | a frozen frame at REAL time SEC (`ACT=1 ./mkstill.sh SEC` takes the deck's act time); open `index.html?src=still_SEC.x3d` |
| `validate_one.py` | XSD + semantic check through the x3d_mcp server |

Time is `Clock.elapsedTime` plus a seek offset; X_ITE 16.5.1 computes `TimeSensor.fraction_changed` from wall-clock time and ignores `startTime`, so a fresh load would start at a random point.
Both clocks start at load through a `ProximitySensor`. Seeking writes a disabled `TimeSensor`'s `cycleInterval`, which is ROUTEd to every shader's `toff` (writing custom shader fields from SAI was not picked up).
The label mesh is chunked, and `Shape`s that the shader moves carry a `bboxSize` (otherwise they are culled when the camera looks away from the origin).

## v5 (the score and the helix, a further pass)

- **The helix**: `ArmillaryShader` and `HelixStrandShader` in `make_landing.py` (`effects()`), planets as extra quads of `StarShader`. Fades with the globe's veil; the strand fades while the letters leave the helix for the embedding space.
- **Helix fix (28 Oct)**: until now most of the helix was not on screen. With `linewidthScaleFactor='2'` X_ITE 16.5.1 drew almost nothing of these two line sets (of the armillary only the constellations, of the strand a small fan, a gold sheet from camera 2); and the armillary's first test, `v.x > 5.0`, sent the ecliptic pole, the precession circle and the orbits through the constellations' branch (stray grey bars). Now: `v.x > 8.5`, 1-px lines (`LINE_PROPS`), alpha x 1.6. The rebuild differs from the v5 scene in exactly those five lines. Before and after side by side, at the same frozen moment: `explore/helixfix/compare.html`; the v5 files and checksums are in `explore/helixfix/before/`.
- **Demo fixes (28 Oct, at the user's request; v5-helix files and checksums in `explore/demofix/before/`):**
  - **Load time.** Placeholder coordinates are now distinct (`dummy()` in `make_landing.py`). X_ITE 16.5.1 builds an IndexedFaceSet with shared vertices and coincident coordinates very slowly. *Measured:* the page is ready in 2.4 s instead of 11.2 s (first frame 3.0 s instead of 9.0 s); the cause was isolated in `explore/review/`.
  - **Dimming.** The strand drops to 40 % behind the writing and the interludes. The armillary drops to 30 % behind the interludes' text and under the graph acts.
  - **Cinema mode.** Key `c` or `?cinema`: the tabs, hints and progress bar fade, Listen shows on hover, and the title block shows only in the opening and the return. A disabled `Cinema` TimeSensor is ROUTEd to the label shader.
  - **Honesty.** The attention map's subtitle now says the heads are authored (`softmax(−‖q−k‖² / τ) · 3 authored heads`), with a note: measured in Grabar, letters next to each other in the alphabet co-occur less than chance.
  - **Armenian beats** (captions, every number graded):
    - Mashtots kept the Greek order (graph, opening act);
    - fifteen centuries of the same letter graph (embedding space);
    - Grabar's per-word token cost (the bill);
    - Koryun's vision as tradition, beside what is measured (colophon).
    - Numbers: `explore/data-graph/armenian_insights.py`. **The new English captions need no translation; an Armenian reader should still check the whole text.**
- **Tour cymatics (audio)**: each spotlit letter is also a struck plate (`_plate`): the mode (n, m) = (column + 1, row + 1) of the Chladni figure the scene draws sets how fast the plate shimmers and how much sand falls (7 (n + m) / 2 grains of filtered noise per channel, thinning out). Octave partials only, so it fits every key.
- **Tour styles**, one a row: D minor the duduk and the dam; A minor kanun taksim (random runs through the key); E minor a soft dhol dance enters; B minor a pulse (heartbeat, hats) foreshadows the groove.
- **Randomness**: `SEED=n TAG=_x python3 make_music.py` renders a variant: another improvisation, a pattern chosen per bar for the arpeggio with a few dropped notes, a fill into every eighth bar, bass octave jumps, grace notes on the hook, other taksim runs and sand. Seed 0 is the approved v4 behaviour (plus the tour layers).
  The page draws one of three variants (`landing_score.mp3`, `_b`, `_c`; the harp version likewise) at random on each Listen and again at each loop; the note under the buttons says which.

## The score

`make_music.py` (v4, about 80 s to render; `OUT=scratch/stage` renders beside the files the page is playing) writes `landing_score.mp3` (the full score) and `landing_score_harp.mp3` (the same music without drums, bass, saws or risers: the kanun, the duduk, the dam and the pads).
The button next to **Listen** cycles three mixes: the full score, the harp-and-duduk version, and `landing_score_v4.mp3` (the approved v4 mix, before the tour layers and variants, kept for comparison; `make_music_v4.py`, `_v3.py`, `_v2.py` are the earlier scripts).

History: v1 (a dam, an improvised duduk, a kanun note per letter) had the harp you loved. v2 added a groove and many sonification layers and, measured, had real faults (every plucked note ended in a click; four keys at once plus random draws; 60 to 90 % of the energy below 250 Hz).
v3 fixed those with one harmony table and measured stem levels and "sounded good", but lost some of the Armenian instruments: a sparse composed duduk, a flattened pentatonic harp, an inaudible dam, a synthetic groove. v4 keeps v3's discipline and brings them back:

1. **The harp is the stone's own again.** A letter's pitch is a step of the natural-minor ladder (its column: 1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2, 9/4 on D, Pythagorean tuning) and its row is a key a fifth higher: D, A, E, B minor.
   The opening cascade and the landing are four rising runs through those keys; the tour of the 36 is the same four runs slowly; the letters fall home through them in reverse. **The harmony now follows the rows** (Dm Bb F | Am F | Em C | Bm G; then D major and its dominant A, whose leading tone C# falls to the Dm of the prayer),
   so the modal journey is back and nothing clashes (the dam on D is a chord tone or colour tone in every one of those chords). A rolled chord marks each new key; harp glissandi mark the helix lifting, the sentence beginning and the sweep into the drop. Where letters sound in no order (the writing, the prayer, the graph acts) the harp uses the chord's pentatonic, as in v3.
2. **The duduk improvises again** (the deck's phrasing: a random walk on the scale, 3 to 6 notes, a long last note, 70 % on a chord tone; scoops, grace notes, mordents, slides between neighbouring notes) **but it listens**: a long note is always a tone of the chord (or its pentatonic), a passing note may be any note of the key,
   a note that would sound across a chord change it does not fit is cut short. It sounds about 80 % of the time through the tour, the prayer and the build (v3: about half, and never in the build). In the modern half it plays on the beat grid over the dhol. Composed phrases remain at its entrance, the prayer chant, the Amen, the hook.
3. **The dam is a second duduk**: a reed spectrum (a nasal formant near 1.2 kHz) on D3 and A3, audible on a laptop, periodic over the loop (the seam makes no click).
4. **The groove is less synthetic**: its entrances are as before (hats, half-time then four-on-the-floor kick, claps, off-beat bass, dhol in 3 + 3 + 2) but the dhol and tek are louder, the kanun arpeggio accents the same tresillo (steps 0, 6, 12), the saw stabs, pads and the lead under the hook are 4 to 7 dB quieter.
   The six letters of Mashtots are still the hook (F# D B | E C G over D | C, then G | C, in D Mixolydian: duduk, a kanun octave above, a soft saw).

Kept from v3: every voice ends with a release (no hard cuts); ten stems balanced by BS.1770 loudness (drone, pad, harp, arp, duduk, kick, bass, perc, saw, fx), kick side-chain, a gentle master EQ, a section-level loudness plan, -17 LUFS and a -1 dBFS ceiling, a click-free seam;
`audit()` checks every pitched note against the harmony table (the stone's own opening and return runs are exempt: they sweep four keys on purpose): about 2,000 notes, 0 outside.

Armenian-inflected modal writing; not a transcription of any sharakan. **Nobody has heard v4 yet but you: it was checked by measurement (loudness by section, spectral balance, the note audit, spectrogram readings of the sections, the seam, how much of each stretch the duduk and the harp are sounding), not by ear.**
Measure a score: `python3 analyze_score.py landing_score.mp3` (LUFS, band shares, roughness by section; writes `scratch/analysis_*.png`); read a stretch of it as a pitch-grid picture: `python3 view_spec.py landing_score.mp3 26 50` (`scratch/view_26_50.png`); `DIAG=1 python3 make_music.py` prints each stem's loudness by section.

## Honest limits

- Checked only in the Claude desktop built-in browser (X_ITE, WebGL2): X_ITE's own counter reads 40 to 75 fps across the scenes (the page's requestAnimationFrame count 50 to 80); the busiest scene is the finale's last chart. No second browser, no headset. Invisible quads are pushed out of the clip volume and unused letter arrays are pruned to keep it there.
- The X3D file carries no Sound node by default (the page owns the audio so that seeking works); `X3D_SOUND=1 python3 make_landing.py` adds one for other viewers (it then starts muted at intensity 0).
- Not ported: the deck page's footer links, the live-improvised music (the score is fixed and seeded).
- The text atlas is the scene's largest texture (about 21 M texels); the first load decodes it.

*Tuned ("more of it")*: the armillary and strands are about twice as bright (and were drawn two pixels wide, which hid most of them: see the helix fix above; now 1 px, alpha x 1.6); the plate and sand are louder (sand 5 (n + m) grains a channel); the four tour styles are dealt out differently in each variant (a second duduk duet in another register, kanun taksim every 2 to 4 s, a dhol dance with claps, a pulse with hats and shaker) and each variant's improviser starts in its own register (A4, D5, F4).
