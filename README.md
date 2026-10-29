# x3d.Mashtots

Mashtots System 2: the Armenian alphabet read as a transformer, ported from the deck animation into X3D. It runs on X_ITE 16.5.1 with GLSL shaders, one clock and no Script node. The score is synthesised in Python. Everything is graded: Measured, Established, Estimate, Conjecture, authored.

Snapshot of 29 Oct 2026, taken from `~/Projects/x3d/work/` on the working Mac.

## What is where

| folder | what | start here |
|---|---|---|
| `landing/` | **The Landing** (204 s loop, the demo cut): the generator, the scene, the score (mp3s and their generator), the page. Plus `explore/`, all the exploration and prototypes. | `landing/README.md`, then `landing/explore/EXPLORATIONS.md`, `landing/explore/REVIEW.md`, `landing/explore/STATE.md` |
| `slide1-FROZEN/` (+ `.tar.gz`) | The approved slide-1 port, frozen (with checksums). Never edited. | its README |
| `numerals/` | A static 36-letter X3D lattice and the numeral maths. | `numerals/README.md` |
| `poc/` | The Mashtots proof of concept (notebook, plan, pre-registration, data card, funding one-pager). | `poc/README.md` |
| `armenian-tokenizer-census/` | Tokenizer fertility on Armenian (Eastern, Western, Classical, UDHR). **`data/` (127 MB of downloaded third-party treebanks and tokenizer files) is not included:** re-fetch it with `fetch_tokenizers.py` and the UD treebanks (UD_Armenian-ArmTDP, UD_Armenian-BSUT, UD_Classical_Armenian-CAVaL, UD_Western_Armenian-ArmTDP) and the UDHR texts. | its README, `out/results.md` |
| `notes/` | Hand-over notes from the working sessions (Landing exploration, Nemotron and Armenian research, the POC, the census). | |

## Run the Landing

```bash
cd landing && python3 serve.py 8794
```

- **The demo:** http://127.0.0.1:8794/index.html. Add `?cinema` (or press `c`) for cinema mode. The page is ready in about 2.4 s on an M3.
- **Prototypes** (see `landing/explore/README.md`):
  - `explore/director/`: pause, slow motion, presets, captions.
  - `explore/retime/`: re-timing, camera shots, spectral colours, the measured vowels act. Build with `PRESET=graph-expanded ./build.sh`.
  - `explore/stereo/`: anaglyph, side by side, wiggle.
  - `explore/live-score/`: the score in WebAudio.
  - `explore/data-graph/`: the measured Grabar graph and the Armenian insights. These need the census `data/`.

## Status and open items

- **Applied to the demo cut (28 Oct):**
  - the helix fix (two bugs that hid most of the armillary and the strand);
  - the load fix (11.2 s → 2.4 s);
  - dimming of the strand and the armillary;
  - cinema mode;
  - the honest order head;
  - four Armenian caption beats.
- **Bug finds bound for hagopjay/x3d_mcp and this repo:** `landing/explore/UPSTREAM-LEDGER.md`.
- **Not done:**
  - nobody has listened to the live score;
  - stereo has not been tried with glasses or a headset;
  - an Armenian reader should check all the Armenian text;
  - the poster frame is paused.

## Licences of included third-party material

- X_ITE: vendored in `landing/vendor/`, under its own licence.
- Noto Serif Armenian and Lora fonts: SIL Open Font License.
- The mural: Van Khachatur, the staircase fresco of the Matenadaran, 1959–60, a photograph via Wikimedia Commons. It is credited in the page and the colophon.
