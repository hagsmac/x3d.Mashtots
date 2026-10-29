# Where the Mashtots exploration stands (resume note, 28 Oct, before a compaction)

## Done and verified
- **The helix fix is in the approved scene** (the user said yes). In `make_landing.py`: `if (v.x > 8.5)`, `LINE_PROPS` (1-px lines), alpha × 1.6 for the armillary and the strand.
  - The rebuild differs from v5 in exactly 5 lines.
  - `mashtots-landing.x3d` md5 `f5387a7856ab6d362dd2d191c93ae2fa`.
  - v5 backup and checksums: `helixfix/before/`; side by side: `helixfix/compare.html`. The README records the fix.
- **Prototypes** (one line each in `README.md`; everything measured is in `EXPLORATIONS.md`):
  - `retime/`: presets, speed ramps, the measured vowels act, flow particles, the camera layer and spectral colours (`camspec.py`), rank as height;
  - `director/`: transport, captions, preview of presets;
  - `live-score/`: WebAudio score from any timeline;
  - `data-graph/`: the measured Grabar graph.
- **Camera, tuned:**
  - the title block stays put and dims during moves;
  - gentler tour glances;
  - a slow push across the finale's drop (0.9), with a 0.12 pump on each kick;
  - 59-60 fps while playing; XSD valid, 0/0 semantic.

## Demo fixes applied (28 Oct, the user's yes)
- **Approved scene:** md5 `fa72b284ea4986432fb8319c7d6fdd87`, text atlas `1898fb119fb4238e454636c41fb2f6b0`. Backups with their own textures: `demofix/before/` (helix-fixed) and `helixfix/before/` (v5); both proven by byte-identical regeneration.
- **What changed:** the load fix (ready 2.4 s), the dimming, cinema mode (`c`), the honest order head, and four Armenian caption beats. `retime/` re-synced (its patches no longer carry what the original now has).
- **The demo cut is the approved one plus these fixes,** shown on the user's laptop in Chrome.

## Third round (28 Oct)
- Look-at shots and viewpoint blending in `retime/camspec.py` (`camera_glsl()`); stereo page `stereo/` (anaglyph, side by side, cross-eyed, wiggle).
- **Paused by the user:** the poster frame (`poster/`, ready to capture).

## Rules in force
- **Approved files** (`mashtots-landing.x3d`, `index.html`, `make_landing.py`, `make_music.py`, the mp3s): change only on the user's explicit yes, with a backup and a byte-level diff first. Never touch `../mashtots-slide1-FROZEN/`.
- **Pushes are on HOLD.** Log every bug find in `UPSTREAM-LEDGER.md`. Destinations, chosen by the user: hagopjay/x3d_mcp (as validator checks) and a future hagopjay/mashtots repo the owner creates. When the user says go: a hagsmac fork branch plus a cross-fork PR; never `main`, no force-push.
- **No downloads** (fonts, models, data) without asking.
- **Grades on everything:** Measured, Established, Estimate, Conjecture, authored. Audio is never listened to.

## Done since: the review (`REVIEW.md`), the questions, and the demo fixes. Still open from the review: a poster frame while loading; gzip if the piece is ever shared as a link; the live score for the expanded cut; a cross-browser check; shader unit tests; trimming the GLSL.

## Earlier plan (kept for the record)
1. A **thorough review and assessment** of the whole Landing and the prototypes, visual and technical.
2. **Clarifying questions** (AskUserQuestion) to spec further improvements, visual and technical.
3. **Armenian as a source of real insight.** Pursue what can be measured or shown about the language and the alphabet's design: near one-letter-one-sound spelling, the numeral values, Grabar morphology, what tokenizers do to it, Sukhotin's vowels, the fastest mode.
   - Present "divinely inspired" as tradition (Koryun's account of Mashtots's vision), graded as such, never as a measured claim.
4. The user plans demos for friends and possibly investors, so polish and robustness matter (load time, a first impression without waiting, the reliability of the build). **The voice interface was dropped by the user. Do not build it.**

## Open items carried over
- the 2-px lines as shader quads (if the user wants the v5 line width back);
- the brightness of the strand and the polar axis's length, now visible;
- the tour's subtitle honesty label (`softmax(QKᵀ/√d)` → the heads are authored);
- the live score's missing layers (tour styles, composed duduk anchors, stem balancing);
- the ideas in `EXPLORATIONS.md` §12.4 (emission spectrum, 3D spectral embedding, card swatches, the Chladni figure in its note's colour, a carved stone).
