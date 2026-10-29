# Mashtots slide 1 as X3D

Slide 1 of the Mashtots deck (`reveal.js`): the 36 letters of Mesrop Mashtots's alphabet leave the alphabet stone in the mural,
cross the dark on cubic Bezier paths with comet trails, settle into one gilt line, rest, and go home. A 16.65 s loop.

## Run it

```bash
cd ~/Projects/x3d/work/mashtots && python3 -m http.server 8793
```

Open http://127.0.0.1:8793/index.html. Keys: `1` slide camera, `2` alphabet stone, `3` gilt line, `f` free navigation (drag to orbit).
`?classic` loads the shader-free fallback. Needs a WebGL2 browser (X_ITE 16.5.1 is vendored in `vendor/x_ite/`).

## Files

| file | what |
|---|---|
| `mashtots-reveal.x3d` | the main file (125 KB): one clock, two shaders, one mesh, embers, camera. XSD valid, semantic 0 errors / 0 warnings |
| `mashtots-reveal-classic.x3d` | same flights with 216 PositionInterpolators, no shaders (441 KB). Portable, lower fidelity (flat glow, trails always on) |
| `reveal_data.py` | the shared data: seed 405 control points, begin 0.9 s, stagger 0.075 s, flight 2.8 s, hold 4 s, cubic ease (all from `reveal.js`) |
| `make_reveal.py` | generator of the main file. `--freeze SEC --out F --cam X Y Z` writes a still frame for inspection |
| `make_reveal_classic.py` | generator of the fallback |
| `glyphs/` | 36 glyph PNGs (Mshtakan, verified 36/36 against the alphabet order) and `atlas.png` (6 x 6 sheet) |
| `validate_one.py` | XSD + semantic check through the x3d_mcp server: `x3d_mcp/.venv/bin/python validate_one.py FILE.x3d` |
| `still_*.x3d` | inspection frames (rest, flight, line, close-ups) |

## How it maps to the JavaScript

| reveal.js | X3D |
|---|---|
| per-frame loop, `t` | `TimeSensor Clock` fraction, ROUTEd into the shaders' `phase` uniform |
| `mulberry32(405)` control points, cubic Bezier, ease | the same six numbers per letter as vertex attributes `aA aB aC`; the vertex shader evaluates the curve |
| 6 trail copies | 6 quad layers in the same mesh, drawn back to front, visible only while moving |
| stone, glow, gilt line (canvas) | one backdrop quad with a fragment shader: carved 4 x 9 cells that empty as letters leave, teal swell, hairline that grows from the middle |
| (nothing) | `ParticleSystem` embers gated by a `BooleanSequencer`, camera dolly by a `PositionInterpolator`, `LIFT` (letters rise toward the camera mid-flight), 3 viewpoints |

Set `LIFT = 0` and `DOLLY = 0` in `make_reveal.py` for the flat original.

## Patterns taken from hagopjay's Gobbler 3

One `phase` number drives the GPU; per-vertex data carried as attributes; `alphaMode='BLEND'`; Embers `ParticleSystem` with a
`PixelTexture` sprite, `ColorRGBA` colour ramp and a `BooleanSequencer` window; no `Script`; comments that say why.

## Two things that cost time (so they are written down)

1. **Texture rows.** X_ITE hands a texture given through a `ComposedShader` `SFNode` field to GLSL top row first, so v = 0 is the TOP of
   the PNG. With the standard bottom-origin mapping the stone showed the wrong glyphs (atlas rows reversed). Found by drawing one atlas cell on
   every quad (`DEBUG_UV=0 python3 make_reveal.py ...`). Another viewer may differ; the classic file avoids the question.
2. **Culling.** The quads' own coordinates sit near the origin and the shader moves them, so a browser culls the whole mesh when the camera
   looks away from the origin. The letters `Shape` therefore carries `bboxCenter` / `bboxSize`.

## Not done

Slides after 1 (helix, attention, Markov, Fourier, Poincare), the mural / stone photographs as textures (the deck's `assets/` has them), sound.
The preview was checked in the Claude desktop built-in browser only (X_ITE, WebGL2); no second browser, no headset.
