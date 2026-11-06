# Feature checklist: every feature and the control that exposes it

Each row names a feature of the slide show, the on-screen control that runs it, its key and URL option (if any), and how it was checked.
**Test** = `tools/feature-test.js` clicked that control in Chromium (Playwright, Apple M3, 1600 x 900, 2026-11-03) and the stage's state changed as it should:
**148 of 148 passed, 0 console errors or warnings** (output in `tools/feature-test-result.txt`). **Load** = the URL variant was loaded and checked separately. **Eye** = looked at in a screenshot (`docs/shots/`).

Deck = the control deck (right panel, button **deck** in the pill, key `K`). Info = the info panel (left, **info**, key `I`). Pill = the control bar at the bottom of the picture.

## Transport and time

| feature | control | key | URL | checked |
|---|---|---|---|---|
| play / pause | Pill ▶, Deck **▶ play / ❚❚ pause** | space | `paused=1` | Test |
| previous / next section | Deck **⏮ ⏭**, section tabs at the top | ← → | `#stone` ... `#return` | Test |
| one frame back / forward (pauses) | Deck **◂ frame**, **frame ▸** | , . | | Test |
| back to the start of the loop | Deck **⟲ 0:00** | | `t=0` | Test |
| seek anywhere | Deck scrubber; click an act on the act bar or the minimap | | `t=SEC` | Test |
| speed 0.25x, 0.5x, 0.75x, 1x, 1.5x, 2x | Deck **speed** buttons | [ ] | `speed=X` | Test (6) |
| jump to any of the 10 sections | Deck **Sections** grid, top tabs, Info **sections** table rows | ← → | `#id` | Test (10) |
| jump to any of the 30 acts | Deck **Acts** grid, act bar, minimap, Info **acts** table rows | | | Test (30) |
| link to this exact moment, plan and level | Deck **link here** (copies the URL) | | `t`, `seed`, `dazzle` | Test |

## Cameras

| feature | control | key | checked |
|---|---|---|---|
| scene camera (Cam) / helix / ring / stone | Deck **scene, helix, ring, stone** | 1 2 3 4 | Test (4) |
| free orbit (drag to turn) | Deck **orbit** | O | Test |

## Dazzle (the time-effects conductor)

| feature | control | key | URL | checked |
|---|---|---|---|---|
| level off / subtle / dazzle / wild | Deck **Dazzle** buttons, Pill **dazzle** (cycles) | D | `dazzle=` | Test (4) |
| draw a new plan | Deck **new plan** | R | | Test |
| fix a plan by seed / keep it every loop | Deck seed box + **use seed**, **fixed** | | `seed=N` | Test |
| show where this loop's effects fall | Deck **show plan**, Pill **plan** (ticks on the act bar) | P | | Test |
| see the plan as a list and jump to an effect | Deck plan list (click a row), minimap diamonds | | | Test |
| replay any of the 15 moments now | Deck **Moment replays** (15 buttons) | | | Test (15), Eye (`s5`) |
| calm (half speed, no dazzle, no motes) | Deck **calm** | M | `calm=1` | Test |

## Display

| feature | control | key | URL | checked |
|---|---|---|---|---|
| captions over the picture | Deck **captions**, Pill captions icon | C | | Test |
| graded panels (authored beside measured) | Deck **graded panels** | G | `panels=0` | Test |
| title card at each section change (new) | Deck **title cards** | | `titles=0` | Test, Eye (`s3`) |
| hide every control | Deck **hide controls** | H | `ui=0` | Test, Load |
| full screen | Deck **full screen**, Pill full-screen icon | F | | present; browsers refuse it to a script, not clicked by the test |
| key help | Deck **key help**, Pill ? | ? / Esc | | Test |
| the start card (begin with sound / silently) | Deck **start card** | | `gate=0` skips it | Test, Eye (`s2`) |
| info panel: this act, sections, acts, grades, keys & URL, credits, limits | Pill **info**, Info tabs (7) | I | `info=1` | Test (7) |
| control deck | Pill **deck** | K | `deck=1` | Test |
| skin: pill / the old director's bar / none | Deck **skin** buttons | | `ui=bar`, `ui=0` | Load |
| scene: measured build / expanded without the mint layers | Deck **scene** buttons | | `scene=expanded` | Load (loop 255.0 s) |

## Sound (synthesised live; unlistened)

| feature | control | key | URL | checked |
|---|---|---|---|---|
| the live score on / off | Deck **sound**, Pill **sound**, start card **Begin with sound** | S | | Test (AudioContext running) |
| tape effects of time dilation on / off | Deck **tape effects** | X | `fx=0` | Test |
| effects level | Deck slider | | | Test |
| fire each effect voice by hand: tape-stop, rewind, riser, sink, tick | Deck **try** buttons (5) | | | Test (5, no error; not heard) |
| score seed 0 / 1 / 2 | Deck **score seed** | | `scoreseed=` | Test (5,278 / 5,242 / 5,257 events) |
| score layers: tour styles, composed duduk, saws, risers, graph sonification, measured acts | Deck **layers** (6 toggles; rebuild the score) | | `layers=-saws,...` | Test (each removes events), Load |
| score version: v2 mixed / v2 unmixed / v1 | Deck **version** buttons | | `mix=0`, `score=v1` | Load |

## Other pieces in this project

| piece | where | controls on screen | checked |
|---|---|---|---|
| the approved cut (204 s, mp3 score in 3 variants, harp mix, v4) | Deck link, `./run.sh approved` | strip: cut switcher, cameras 1-4, orbit, ⏮ ⏭, cinema, full screen, info card; Listen and score mode (now keyboard-focusable) | Eye (`s6`, `s7`), Listen played `landing_score_c.mp3` |
| slide 1 (16.65 s) | Deck link, `./run.sh slide1` | strip: cameras slide, stone, gilt line (keys 2 and 3 now bind the right ones), orbit, info | Eye (`s8`) |
| slide 1, classic (no shaders) | Deck link | strip, info | Eye (`s9`) |
| score lab (the live score alone: sections, layers, offline measure, calibration) | Deck link, `./run.sh score` | the lab's own controls | Eye (`s10`) |
| effects lab (offline measurement of each tape effect) | Deck link | runs on load | Eye (`s11`): tape-stop falling 2.5 -> 0.15 kHz, as in the build notes |
| the director's page (the earlier page the stage grew from) | Deck link | its own bar | Load, console clean |
| the v1 score lab | Deck link | its own controls | Load |

## Readouts (deck, "Now")

time and loop length, the deck's own act time, the act (and whether the deck's clock holds), the section, the current rate (speed x calm x dazzle), X3D frames per second, the bound camera, dazzle level / plan seed / number of effects, loop count, sound state (AudioContext state, sample rate, tape effects), score (version, seed, events, harmony audit).
