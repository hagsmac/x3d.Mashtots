# Mashtots Landing: a thorough review (28 Oct, for demos to friends and investors)

> **Applied the same day, after your answers** (laptop demos, approved cut + fixes): the load fix (page ready 2.4 s, was 11.2 s), the dimming of the strand and the armillary, cinema mode (key `c`), the honest order head, and the four Armenian beats as graded captions. See the README, "Demo fixes". Still open: items 3, 4, 7 to 9 below.

**How each claim was checked:**
- *Measured*: a script or a browser run, named in the text.
- *By eye*: screenshots in the Claude built-in browser (Chrome 152, Apple M3).
- *Not checked*: other browsers, phones, weaker GPUs, listening.

## 1. Verdict

The piece is strong and unusual: one clock, no Script, about 50 shaders, real mathematics baked from the deck's own code, an honest grading of every number, and a score that follows the same harmony table. The graph half is the heart of it. For demos, three things matter more than anything new:

1. **The first 9 seconds are a black screen.** *Measured:* the approved scene's first frame comes at 9.0 s on an M3, with all files local. **Fixed in the copy (2.1 s), not yet in the approved scene** (§3).
2. **Restoring the helix exposed a balance problem.** The strand and the armillary are now visible, as designed but never seen. The armillary's large orbit ellipses cross the graph acts, and the strand glows brightly through the writing, the prayer and Shirakatsi's table. Both need dimming in those stretches (by eye, §4).
3. **Pick one demo cut and make it bulletproof.** The approved timing (204 s, with the mp3 score) is the reliable one today. The graph-expanded cut (255 s: camera, spectral colours, rank as height, the measured vowels act) is the more striking one, but it needs the live score, which nobody has listened to yet (§5).

## 2. What works (keep)

- **The stone and the flight:** seed-405 paths, comet trails, the stone ringing per letter.
- **The helix in true 3D,** now with the strand and the armillary visible (fixed 28 Oct).
- **The tour:** one card per letter at about 1.1 s each, its Chladni figure, its struck plate. The rhythm is right.
- **The writing:** the ink order (`pen_time`, geodesic distance inside the glyph) is a genuinely original idea.
- **The graph acts:** each is a real computation, and the deck's numbers are baked exactly.
- **The finale:** the grades on screen; placeholders said to be placeholders.
- **Engineering:**
  - one GLSL library and one timeline;
  - a deterministic generator: a clean rebuild reproduces the scene byte for byte (*measured*);
  - a validated scene (0 errors, 0 warnings);
  - 60 fps at 1080p on an M3 (*measured*; the display's cap).

## 3. Load time: the first impression (Measured)

| scene | first frame | main-thread work |
|---|---:|---:|
| approved, today | 9.0 s | 8.6 s |
| re-timed copy, before the fix | 15.4 s | 15.1 s |
| **copy with the fix (approved timing)** | **2.1 s** | 1.8 s |
| **graph-expanded with the fix** | **2.1 s** (director page ready at 2.3 s) | 1.7 s |

- **Where the time went** (`review/loadprobe.html` wraps every WebGL call that could block and records long tasks):
  - the GPU spends under 0.7 s in all (50 programs, none over 4 ms);
  - the rest was X_ITE's own JavaScript, building three strip meshes whose vertices are shared between quads and whose coordinates all coincide (placeholder `0 0 0`; the shaders read only attributes).
- **Isolated:**
  - the writing act's arcs with a trivial shader take 2,486 ms; with distinct dummy coordinates, 121 ms;
  - shared vertices alone are fast, and coincident points alone are fast (`review/geobench.py`).
- **The fix:** distinct dummy coordinates in the three meshes (tour arcs, writing arcs, the pen strip), whose shaders never read `x3d_Vertex`. In `retime/patch.py`; checked by eye that the arcs still draw. **Applying it to the approved scene needs your yes.** Logged for x3d_mcp as M4 in `UPSTREAM-LEDGER.md`.
- **Still to do for a link people open themselves:** about 5.5 MB to download (scene 2.4, X_ITE 1.3, text atlas 1.4, mural 0.4), plus 4.9 MB of mp3 when listening. Gzip on the server would shrink the scene to a fraction (it is text). A poster frame in place of "loading…" would make even 2 s feel instant.

## 4. Visual review, act by act (by eye)

| act | works | issue found today | proposal |
|---|---|---|---|
| stone, flight | the mural, the trails | none seen | keep |
| lift, helix | true 3D; the restored strand and armillary | the strand is prominent beside the tour's arcs | dim the strand to about 70 % during the tour |
| tour | rhythm, cards, plate | none; the glances keep the card readable | keep |
| writing, prayer, Shirakatsi | ink order, the honesty note on Օ | the strand glows through the text (it dims only partly, and only for the numerals and Shirakatsi) | dim the strand by the interlude (× 0.4) and by the writing's shrink |
| embedding | the tensor as a volume (with the orbit) | none | keep |
| graph acts | the maths, the flow, rank as height | the armillary's orbit ellipses and polar axis cross the ring (visible since the fix) | fade the armillary with the web (× (1 − 0.7 webK)) |
| finale | grades, the push across the drop | the title block takes the lower third throughout | offer a cinema mode that hides the title after the opening |
| return, colophon | the letters falling home, the colophon | none | keep |

## 5. Demo robustness (technical)

- **One cut, one URL, one tab.** Background tabs are throttled, so keep the demo tab in front and the laptop on power.
- **Audio:** browsers keep it muted until a click; the Listen button is the right affordance. The mp3 fits only the approved timing. The live score fits any timing (audit: 0 notes outside the table) but has not been heard.
- **Browsers:** tested only in Chrome (built-in pane). Safari, Firefox and phones are untested. X_ITE needs WebGL2.
- **Size and shaders:** each of about 50 shaders carries the whole GLSL library (about 0.5 MB of GLSL in all); my camera and colour layers add more (3.1 MB build). Not a frame-rate problem (60 fps), but stripping unused functions per shader would trim it.
- **Validation is blind to shader logic:** x3d_mcp passed both helix bugs. Shader unit tests and frame probes are proposed (ledger M2).

## 6. Armenian, measured (`data-graph/armenian_insights.py`, `out/insights.md`)

| question | measured answer | how to show it |
|---|---|---|
| Does the data find the vowels? | Yes: the graph's fastest mode separates the vowels on 35 of 36 letters in Grabar; Ւ alone differs (the consonant w). | built: the vowels act |
| Did the structure survive fifteen centuries? | The vowel split holds: Grabar 97 %, Eastern 94 %, Western 97 %. Letter-to-letter statistics correlate at r = 0.86 to 0.89 between Grabar and today's Eastern and Western. | a new beat: the same graph in 405 and in 2026, overlaid |
| Does Mashtots's ORDER carry linguistic structure? | No. Neighbours in the alphabet co-occur slightly less than chance (Spearman −0.11, against 0 ± 0.06 for random orders). Letters in the same row co-occur less (0.00057 against 0.00086). The order is historical (the Greek order with Armenian sounds inserted), not statistical. | correct the deck's "order" head honestly, or show the contrast |
| What do machines charge? | Tokens per word, Grabar / Eastern / Western / English: Tekken 3.10 / 3.15 / 3.39 / 1.15; DeepSeek 3.89 / 4.50 / 4.34 / 1.12; gpt-oss 2.68 / 2.73 / 2.77 / 1.13. The language of 405 costs no more than today's. | add Grabar to the finale's bill |

- **On divine inspiration.** The tradition (Koryun, Mashtots's student, writes of a vision) belongs in the piece as tradition. What can be **measured** is the alphabet's design: a letter for each sound, a value for each letter, structure strong enough that a machine finds the vowels unaided and that persists for fifteen centuries.
- **Caveat:** the UD corpora differ in genre (Gospels against news and fiction).

## 7. Ranked improvements

| # | improvement | effort | impact | status |
|---|---|---|---|---|
| 1 | Load fix in the approved scene (9 s → about 2 s) | S | **very high** for demos | in the copy; needs your yes |
| 2 | Dim the strand in the interludes and the armillary in the graph acts | S | high | proposed |
| 3 | A poster frame while loading, and gzip on the server | S | high for shared links | proposed |
| 4 | Choose the demo cut; for graph-expanded, finish the live score (tour styles, the composed duduk phrases) and listen | M | high | prototype works |
| 5 | Cinema mode (the title fades after the opening; captions optional) | S | medium-high | proposed |
| 6 | Armenian beats: fifteen centuries; the order is Greek; Grabar on the bill | M | high (truth, surprise) | measured, not built |
| 7 | Cross-browser check (Safari, Firefox, iPad) before showing outside Chrome | S | high risk reduction | not done |
| 8 | Shader unit tests and frame probes (would have caught both helix bugs) | M | medium | proposed (ledger M2) |
| 9 | Strip unused GLSL per shader | M | low-medium | proposed |
