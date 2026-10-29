#!/usr/bin/env python3
"""Stage 1: flatten the outlines of the 36 capitals in Mshtakan (macOS system font) to polylines, in em units. -> contours.json"""
import json
from fontTools.ttLib import TTCollection
from fontTools.pens.basePen import BasePen
from letters import CODE

class Flat(BasePen):
    def __init__(self, gs, steps=8):
        super().__init__(gs); self.steps = steps; self.cs = []; self.cur = None
    def _moveTo(self, p): self.cur = [p]; self.cs.append(self.cur)
    def _lineTo(self, p): self.cur.append(p)
    def _qCurveToOne(self, c, p):
        a = self.cur[-1]
        for k in range(1, self.steps + 1):
            t = k / self.steps; u = 1 - t
            self.cur.append((u*u*a[0] + 2*u*t*c[0] + t*t*p[0], u*u*a[1] + 2*u*t*c[1] + t*t*p[1]))
    def _curveToOne(self, c1, c2, p):
        a = self.cur[-1]
        for k in range(1, self.steps + 1):
            t = k / self.steps; u = 1 - t
            self.cur.append(tuple(u**3*a[j] + 3*u*u*t*c1[j] + 3*u*t*t*c2[j] + t**3*p[j] for j in (0, 1)))
    def _closePath(self):
        c = self.cur
        if len(c) > 1 and abs(c[0][0]-c[-1][0]) < 1e-9 and abs(c[0][1]-c[-1][1]) < 1e-9: c.pop()
    _endPath = _closePath

font = TTCollection("/System/Library/Fonts/Supplemental/Mshtakan.ttc").fonts[0]
assert font["name"].getDebugName(4) == "Mshtakan"
upm = font["head"].unitsPerEm; cmap = font.getBestCmap(); gs = font.getGlyphSet()
out = []
for cp in CODE:
    pen = Flat(gs); gs[cmap[cp]].draw(pen)
    cs = [[(x/upm, y/upm) for x, y in c] for c in pen.cs if len(c) >= 3]
    out.append(dict(codepoint=cp, advance=gs[cmap[cp]].width/upm, contours=cs))
json.dump(out, open("contours.json", "w"))
print("upm", upm, "contours per letter", [len(g["contours"]) for g in out])
