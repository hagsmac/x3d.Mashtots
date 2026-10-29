# Mashtots Landing: deep exploration + prototypes (hand-over, 2026-10-28)

Where: ~/Projects/x3d/work/mashtots-landing/explore/ (read EXPLORATIONS.md first; README.md has one line per prototype). Approved files untouched (mashtots-landing.x3d md5 07c67f5b9d69e428f06f52e17e313789, timestamps of Oct 27).

Findings worth knowing outside this project
- X_ITE 16.5.1: LineProperties linewidthScaleFactor='2' on an IndexedLineSet driven by a ComposedShader renders almost nothing (Landing: of the armillary only the constellations; of the helix strand a small fan). Checked live by switching the factor on a frozen frame and recolouring with a debug shader. Use 1-px lines or expand quads in the vertex shader (ArcShader pattern).
- Landing bug: ArmillaryShader tests `v.x > 5.0` before the kind branches, so kinds 6-8 (ecliptic pole, precession circle, orbits) are drawn as stray vertical lines. Fix `v.x > 8.5`. Predicted streak positions matched the observed ones within 2 px.
- x3d_mcp validation passes both scenes (XSD + 0/0 semantic): it cannot see shader-logic bugs.
- Owning time in an X_ITE scene without Script: write the Seek TimeSensor's cycleInterval (ROUTEd to every shader's toff) from a field callback on the clock's elapsedTime, every frame: pause, slow motion, frame step, preview of a different timeline (director/index.html).
- WebAudio: disconnect each voice's gain/panner on `ended`, and schedule OfflineAudioContext renders in slices with suspend()/resume(); otherwise a 2,000-event loop never finishes rendering.

Built (all runnable): retime/ (presets with bars + speed ramps + new holds; patched generator COPY with a measured "vowels" act, flow particles, the two helix fixes), director/, live-score/ (0 notes outside the harmony table on 3 timelines x 3 seeds; r = 0.61 loudness vs the mp3), data-graph/ (Grabar UD CAVaL: the normalised graph's fastest mode separates vowels on 35/36, Ւ the exception; Tekken's first Armenian merge is ու).
Not done: listening; headset; Blender bake; attention from an open model (needs a download, ask the user).

Update (same day, second round)
- The two helix fixes are APPLIED to the approved make_landing.py at the user's request (rebuild differs from v5 in exactly 5 lines; installed md5 f5387a7856ab6d362dd2d191c93ae2fa; v5 backup + checksums in explore/helixfix/before/; side by side: explore/helixfix/compare.html).
- Camera without Script, in sync with seeking: insert one mat4 CAM, computed in the shared GLSL tl() from the clock, into every `x3d_ModelViewMatrix *` (string replace in the generator's shader()). Choreography as data (weight expression, yaw, pitch, push, pivot). Avoids TimeSensor.fraction (wall clock) entirely. explore/retime/camspec.py.
- Spectral colour done right: a note doubled 40-41 octaves lands in 400-800 THz (visible light ~ one octave). The Wyman-Sloan-Shirley CIE fit drifts below 420 / above 650 nm (gives cyan at 392, orange at 696): clamp the wavelength to 420-650 for hue. Turbo (polynomial) for plain scalars.
