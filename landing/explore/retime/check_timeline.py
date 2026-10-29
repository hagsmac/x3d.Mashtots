#!/usr/bin/env python3
"""Checks the re-timing code against the approved timeline.py and prints what each preset does.
   1. preset "approved" must give the same segment starts and the same act time at every real time (sampled every 10 ms) as timeline.py;
   2. every preset: act time is continuous and never runs backwards, each run segment ends exactly on its act range, bar-sized acts start on the bar grid;
   3. a table of real durations per section, approved vs each preset.
Also writes timelines.json (every preset's pieces), which the director page reads.   Run from anywhere: python3 explore/retime/check_timeline.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE); sys.path.insert(1, ROOT)
import timeline as T0                      # the approved module (read only)
import timeline_retimed as TR
D = json.load(open(os.path.join(ROOT, "scratch/landing.json"), encoding="utf-8"))
ARGS = (17.0, 12.0, 10.0, 20)

segs0, tot0 = T0.build(D, *ARGS)
def act0(tr):
    for s in segs0:
        if tr < s["r0"] + s["dur"] or s is segs0[-1]: return s["a0"] + (tr - s["r0"]) * s["rate"]
segsA, totA = TR.build(D, *ARGS, preset="approved")
assert abs(tot0 - totA) < 1e-9, (tot0, totA)
assert [round(s["r0"], 9) for s in segs0] == [round(s["r0"], 9) for s in segsA]
err = max(abs(act0(k * 0.01) - TR.act_at(segsA, k * 0.01)) for k in range(int(tot0 * 100)))
print(f"approved preset: {len(segsA)} pieces, loop {totA:.3f} s, max act-time difference vs timeline.py {err:.2e} s")
assert err < 1e-9

out = {}
for name in TR.PRESETS:
    segs, tot = TR.build(D, *ARGS, preset=name)
    prev = None
    for k in range(int(tot * 200)):                                   # every 5 ms: continuous, monotone
        a = TR.act_at(segs, k / 200)
        if prev is not None: assert a >= prev - 1e-9 and a - prev < 0.05, (name, k / 200, prev, a)
        prev = a
    for s in segs:
        if s["rate"] or s["rate_end"]:
            end = s["a0"] + s["dur"] * (s["rate"] + s["rate_end"]) / 2
            assert abs(end - s["a1"]) < 1e-6, (name, s["name"], end, s["a1"])
    fin0 = TR.hold_start(segs, "finale")[0]
    ov = TR.PRESETS[name]["segments"]
    for nm, o in ov.items():                                           # bar-sized acts start on the grid (counted back from the finale's first beat)
        if "bars" in o and TR.hold_start(segs, nm)[0] >= TR.hold_start(segs, "space")[0]:
            b = (TR.hold_start(segs, nm)[0] - fin0) / TR.BAR
            assert abs(b - round(b)) < 1e-6, (name, nm, b)
    out[name] = dict(about=TR.PRESETS[name].get("about", ""), cycle=tot, segs=segs)
json.dump(out, open(os.path.join(HERE, "timelines.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)

names = ["flight", "line", "lift", "tour", "write", "prayer", "numerals", "shirakatsi", "space", "web", "msg", "spectral", "vowels", "spectral2", "pagerank",
         "anneal", "descent", "walk", "fourier", "poincare", "svd", "collapse", "finale", "line2", "return", "rest"]
print(f"\n{'segment':<11}" + "".join(f"{p:>16}" for p in out))
for nm in names:
    row = []
    for p in out:
        try: row.append(TR.hold_start(out[p]["segs"], nm)[1])
        except KeyError: row.append(None)
    print(f"{nm:<11}" + "".join(f"{(f'{x:7.2f} s' if x is not None else '-'):>16}" for x in row))
print(f"{'LOOP':<11}" + "".join(f"{out[p]['cycle']:>14.2f} s" for p in out))
g = lambda p: sum(TR.hold_start(out[p]["segs"], nm)[1] for nm in names[8:22] if any(s["name"] == nm for s in out[p]["segs"]))
print(f"{'graph half':<11}" + "".join(f"{g(p):>14.2f} s" for p in out) + "   (embedding space to collapse)")
print("\nall checks passed; wrote timelines.json")
