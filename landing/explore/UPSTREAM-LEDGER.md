# Upstream ledger: bug finds and fixes waiting to be pushed

**Status: HOLD.** Nothing here has been pushed. On 28 Oct the user chose two destinations: **x3d_mcp** (as validator checks) and a **new Mashtots repo** under hagopjay, which the owner creates. Then they said to hold: keep track, push later.
**Route when the user says go:** a branch on the `hagsmac/*` fork plus a cross-fork PR to `hagopjay/*`. Never `main`, no force-push, nothing to `Web3DConsortium/*` or to X_ITE upstream without an explicit "send" (handoff/README.md, push policy).
`hagopjay/x3d_mcp` has issues disabled and no open PRs (checked 28 Oct), so findings go in as PRs with tests, not issues.

## For hagopjay/x3d_mcp (validator checks)

| # | find | evidence | proposed fix in x3d_mcp | status |
|---|---|---|---|---|
| M1 | A `ComposedShader` on an `IndexedLineSet` with `LineProperties linewidthScaleFactor > 1` renders almost nothing in X_ITE 16.5.1. Landing: of the armillary only the constellations; of the helix strand a small fan (a gold sheet from camera 2). | Checked live on a frozen frame: switching the factor 2 → 1 brings everything back. A debug shader painting every vertex red showed only the constellations at width 2. Side by side: `explore/helixfix/compare.html?t=20&cam=2`. | A semantic **warning** (renderer-specific): "linewidthScaleFactor > 1 with a ComposedShader line set: X_ITE 16.5.1 draws almost nothing; use 1-px lines or expand quads in the vertex shader." Plus a test fixture (two-line scene). x3d_mcp's `src/validation` has no rule on it today (only the schema entry). | ready to write |
| M2 | x3d_mcp passes scenes whose shaders draw the wrong thing. The approved Landing passed (XSD valid, 0 errors, 0 warnings, 5 infos) with the armillary's ecliptic pole, precession circle and orbits sent through the wrong branch (`if (v.x > 5.0)` before the kind tests). | `explore/EXPLORATIONS.md` section 2: the stray lines' positions, predicted from the shader's maths, matched the screen within 2 px. | Not statically checkable in general. Proposal: an optional **behavioural** tool, either frame probes (render named frames headless and compare with stored images) or a "shader unit test" hook (re-run a shader's vertex maths on the CPU for its encoded vertices and assert they land in the frame). Document the blind spot in the validator's README. | idea; needs design |
| M4 | **Load-time slow path in X_ITE 16.5.1:** an `IndexedFaceSet` whose vertices are shared between faces and whose coordinates all coincide (placeholders such as `0 0 0`, common when a shader reads only attributes) costs seconds of main-thread work. The Landing's writing-act arcs (1,848 quads in strips): 2,486 ms. The same arcs with distinct dummy coordinates: 121 ms. Shared vertices alone (with distinct points) and coincident points alone (with unshared vertices) are both fast. | `explore/review/geobench.py`, `bench/realarcs_trivialshader.x3d` against `bench/realarcs_distinct.x3d`, timed with `review/loadprobe.html` (long tasks). Whole scene: first frame 9.0 s (approved) → 2.1 s with distinct dummies. | A semantic **warning**: "IndexedFaceSet with shared vertex indices and N coincident coordinates: X_ITE builds it very slowly; give unused placeholder coordinates distinct values." Test: the two bench scenes. | ready to write |
| M3 | (Related, same family as the jepa-bridge finding: x3d_mcp missed 23 of 40 seeded physics-defect classes.) Static validation passes what a renderer shows wrongly. | `../jepa-bridge/BRAINSTORM.md` | Cross-reference M1/M2 in any PR description. | note |

## For a new Mashtots repo (hagopjay/mashtots, to be created by the owner)

| # | find / fix | where it is now | status |
|---|---|---|---|
| L1 | Armillary branch bug: `v.x > 5.0` → `v.x > 8.5` (the constellations only). | **Applied** to `make_landing.py` 28 Oct; the rebuild differs from v5 in exactly 5 lines; v5 backup and checksums in `explore/helixfix/before/`. | fixed locally |
| L2 | Wide lines hide the armillary and the strand: `LINE_PROPS` (1 px) and alpha × 1.6. Proper fix still open: 2-px quads expanded in the vertex shader (the `ArcShader` pattern). | **Applied** (same rebuild). | fixed locally; proper fix open |
| L3 | WebAudio voices never disconnected: every note's gain and panner stayed in the graph, so a whole-loop offline render did not finish in 100 s (7.7 s after the fix), and live playback would slowly fill up. | `explore/live-score/score.js` (fixed: disconnect on `ended`; offline renders scheduled in slices). | fixed in the prototype |
| L4 | Honesty: the tour's map subtitle `softmax(QKᵀ / √d)` suggested a model; the heads are hand-made features. | `make_landing.py`, `m_sub` and the `m_note` lines | **applied 28 Oct** |
| L7 | **Load time 9 s → about 2 s:** distinct dummy coordinates in the three strip meshes whose shaders ignore `x3d_Vertex` (tour arcs, writing arcs, the pen strip). In `explore/retime/patch.py`, not yet in the approved generator (needs the user's yes). | `explore/review/` | **applied to the approved scene 28 Oct** (`dummy()`) |
| L5 | The vendored X_ITE lacks `assets/fonts/PT_Sans/PTSans-Regular.woff2` (404 on every load; it only affects X_ITE's own interface). | `vendor/x_ite/` | note |
| L6 | Earlier wrong observation, corrected: the "load-time streaks" were L1 (they come and go as the globe turns). | EXPLORATIONS.md section 11 | documentation |

## X_ITE upstream (create3000/x_ite): not hagopjay, only with an explicit "send"

| # | find | note |
|---|---|---|
| X1 | The wide-line path (M1), as an X_ITE bug report with a minimal scene. | Write the repro first; ask before filing anywhere. |
| X2 | Known gotchas already in the README: `TimeSensor.fraction` is wall-clock based and ignores the seek offset; SAI writes to custom shader fields are not applied, though ROUTEd events are. | Check upstream's issues before reporting. |
