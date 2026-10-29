# explore/: prototypes for the Mashtots Landing (2026-10-28)

Nothing here changes the approved files (`../mashtots-landing.x3d`, `../index.html`, `../make_landing.py`, `../make_music.py`, the mp3s); copies are made and patched here.
Serve the Landing folder as usual (`cd .. && python3 serve.py 8794`); the scene takes 15 to 25 s to load. The full write-up is **EXPLORATIONS.md**.

| prototype | one line | run |
|---|---|---|
| `director/` | A transport for any build: pause, 0.1 to 4x, frame steps, loop one act, captions (graded), calm mode, plates (one still per act); it previews a re-timing preset on the approved scene without baking, and plays the live score for re-timed builds. | http://127.0.0.1:8794/explore/director/index.html (add `?preview=graph-expanded`, or `?scene=retime&preset=graph-expanded`, `&t=SEC&paused=1`) |
| `retime/` | Re-timable timeline (bars of the 128 BPM grid, smooth speed ramps, new holds) and a patched COPY of the generator that bakes a re-timed Landing: a new measured act (the vowels), rank flowing along the chords, camera sweeps and corner shots (`camspec.py`), letters coloured on the spectrum by their own metrics, rank as height. | `PRESET=graph-expanded ./retime/build.sh` (7 s), check: `python3 retime/check_timeline.py`, view: http://127.0.0.1:8794/explore/retime/index.html?preset=graph-expanded |
| `live-score/` | The v4/v5 score synthesised live in WebAudio from the same tables, re-anchored to any timeline; audit, offline render, loudness compared with the mp3. | `python3 live-score/export_score_data.py`, then http://127.0.0.1:8794/explore/live-score/index.html |
| `data-graph/` | The alphabet as a MEASURED graph: 342,533 letters of Grabar (UD CAVaL, already on disk), the graph's fastest mode finds the vowels, Sukhotin's algorithm, Tekken's merges; compared with the deck's authored graph. | `python3 data-graph/grabar_graph.py` (2 s) -> `data-graph/out/{report.md, graph.png, graph.json}` |
| `stereo/` | The re-timed Landing in stereo: two copies of the scene render the left and right eye (an Eye TimeSensor ROUTEd to every shader moves each camera by half the separation, converging on the shot's target), held on the same moment. Anaglyph (red-cyan glasses), side by side (phone viewer, headset), cross-eyed, wiggle (no equipment). | http://127.0.0.1:8794/explore/stereo/index.html?mode=anaglyph (keys: space, ← →, m mode, [ ] separation) |
| `helixfix/` | The helix fix applied to the approved scene (28 Oct): `compare.html` shows v5 and the fixed scene side by side at the same frozen moment; `before/` keeps the v5 files and checksums. | http://127.0.0.1:8794/explore/helixfix/compare.html?t=20&cam=2 |
| `poster/` | Paused: a capture page that renders the scene's first frame to `poster.jpg` (with `receive.py` on port 8795), for a poster in place of the loading screen. | `python3 poster/receive.py 8795`, then http://127.0.0.1:8794/explore/poster/capture.html |
| `review/` | The load-time probe and benchmarks behind REVIEW.md §3. | http://127.0.0.1:8794/explore/review/loadprobe.html |
| `probe.html` | What this browser offers (WebGPU, WebXR, WebGL2 limits, WebAudio). | http://127.0.0.1:8794/explore/probe.html |
