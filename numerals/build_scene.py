#!/usr/bin/env python3
"""Stage 3: tris.json + letters.json -> mashtots-numeral-lattice.x3d
36 letters as extruded Mshtakan outlines on a 9 x 4 lattice: column = digit 1..9, row = place (units at the bottom, thousands on top).
Under each letter, `digit` small cubes (a unary abacus). Each letter Transform carries a MetadataSet (letter, Unicode, name, value, place, digit)."""
import json
from xml.sax.saxutils import quoteattr
from letters import table

T = table(); G = json.load(open("tris.json"))
PITCH_X, PITCH_Y, DEPTH, SCALE = 1.25, 1.55, 0.16, 1.0
ROW_COL = ["0.78 0.58 0.22", "0.28 0.62 0.60", "0.60 0.34 0.58", "0.70 0.30 0.26"]     # units, tens, hundreds, thousands

def area2(p, q, r): return (q[0]-p[0])*(r[1]-p[1]) - (r[0]-p[0])*(q[1]-p[1])
def sarea(c): return sum(c[i][0]*c[(i+1) % len(c)][1] - c[(i+1) % len(c)][0]*c[i][1] for i in range(len(c))) / 2
def inside(pt, c):
    x, y = pt; w = False
    for i in range(len(c)):
        (x1, y1), (x2, y2) = c[i], c[(i+1) % len(c)]
        if (y1 > y) != (y2 > y) and x < (x2-x1) * (y-y1) / (y2-y1) + x1: w = not w
    return w

def mesh(g):
    V = g["verts"]; xs = [p[0] for p in V]; ys = [p[1] for p in V]
    cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2          # centre the bbox on the cell
    P = [(round((x-cx)*SCALE, 4), round((y-cy)*SCALE, 4)) for x, y in V]
    pts, idx = [], []
    def add(p, z): pts.append("%g %g %g" % (p[0], p[1], z)); return len(pts) - 1
    n = len(P); front = [add(p, DEPTH/2) for p in P]; back = [add(p, -DEPTH/2) for p in P]
    for a, b, c in g["tris"]:                                  # caps: front CCW seen from +z, back reversed
        if area2(P[a], P[b], P[c]) < 0: b, c = c, b
        idx.append((front[a], front[b], front[c])); idx.append((back[a], back[c], back[b]))
    off = 0; C = g["contours"]
    for k, c in enumerate(C):
        m = len(c); pc = P[off:off+m]; off += m
        depth = sum(inside(c[0], o) for j, o in enumerate(C) if j != k)
        if (sarea(c) > 0) != (depth % 2 == 0): pc = pc[::-1]; ids = list(range(off-m, off))[::-1]
        else: ids = list(range(off-m, off))
        for i in range(m):                                     # side wall, outward normal (verified by test below)
            a, b = ids[i], ids[(i+1) % m]
            idx.append((back[a], back[b], front[b], front[a]))
    return pts, idx

def meta(r):
    s = lambda n, v: '<MetadataString containerField="value" name=%s value=%s/>' % (quoteattr(n), quoteattr('"%s"' % v))
    i = lambda n, v: '<MetadataInteger containerField="value" name=%s value="%d"/>' % (quoteattr(n), v)
    return ('<MetadataSet containerField="metadata" name="letter" reference="https://www.unicode.org/charts/PDF/U0530.pdf">'
            + s("char", r["char"]) + s("codepoint", r["codepoint"]) + s("unicodeName", r["unicode_name"])
            + i("index", r["index"]) + i("value", r["value"]) + i("place", r["place"]) + i("digit", r["digit"]) + '</MetadataSet>')

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<X3D profile="Interchange" version="4.0" xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance" xsd:noNamespaceSchemaLocation="https://www.web3d.org/specifications/x3d-4.0.xsd">',
       '<head><meta name="title" content="Mashtots numeral lattice"/>',
       '<meta name="description" content="The 36 letters of the Armenian alphabet as extruded outlines on a 9 x 4 lattice: column = digit, row = decimal place. Under each letter, one cube per unit of its digit."/>',
       '<meta name="generator" content="work/mashtots-numerals/build_scene.py"/></head><Scene>',
       '<WorldInfo title="Mashtots numeral lattice" info="Letters: Mshtakan outlines. Values: standard Armenian alphabetic numerals, sum of all 36 = 49995."/>',
       '<NavigationInfo type=\'"EXAMINE" "ANY"\' headlight="false"/>',
       '<DirectionalLight direction="-0.4 -0.5 -0.8" intensity="0.95" ambientIntensity="0.35"/>',
       '<DirectionalLight direction="0.6 0.3 0.5" intensity="0.35" color="0.8 0.85 1"/>',
       '<Viewpoint DEF="Cam" description="Lattice" position="5 2.3 13.5" centerOfRotation="5 2.3 0"/>',
       '<Viewpoint DEF="CamLow" description="Low angle" position="5 -3 8" orientation="1 0 0 0.35" centerOfRotation="5 2.3 0"/>',
       '<Background skyColor="0.04 0.035 0.05"/>',
       '<Shape DEF="CubeShape" visible="false"><Appearance><Material/></Appearance><Box size="0.13 0.13 0.13"/></Shape>']
ncubes = 0
for r, g in zip(T, G):
    assert g["codepoint"] == int(r["codepoint"][2:], 16)
    pts, idx = mesh(g)
    x, y = r["col"] * PITCH_X, r["row"] * PITCH_Y
    col = ROW_COL[r["row"]]
    ci = " ".join(" ".join(map(str, f)) + " -1" for f in idx)
    out.append('<Transform DEF="L%02d_%s" translation="%g %g 0">' % (r["index"], r["codepoint"][2:], x, y) + meta(r))
    out.append('<Shape><Appearance><Material diffuseColor="%s" specularColor="0.25 0.25 0.25" shininess="0.35"/></Appearance>' % col)
    out.append('<IndexedFaceSet solid="true" creaseAngle="0.7" coordIndex="%s"><Coordinate point="%s"/></IndexedFaceSet></Shape>' % (ci, ", ".join(pts)))
    for d in range(r["digit"]):                                # unary digit under the letter, 3 per line
        cx, cy = (d % 5 - 2) * 0.17, -0.62 - (d // 5) * 0.17
        out.append('<Transform translation="%g %g 0"><Shape><Appearance><Material diffuseColor="%s" emissiveColor="%s"/></Appearance><Box size="0.13 0.13 0.13"/></Shape></Transform>'
                   % (cx, cy, col, " ".join("%.2f" % (float(v)*0.35) for v in col.split())))
        ncubes += 1
    out.append('</Transform>')
out.append('</Scene></X3D>')
out = [l for l in out if "CubeShape" not in l]                 # the unused DEF template is dropped; boxes are inline (no USE needed)
open("mashtots-numeral-lattice.x3d", "w", encoding="utf-8").write("\n".join(out))
print("letters", len(T), "cubes", ncubes, "expected", sum(r["digit"] for r in T))
