#!/usr/bin/env python3
"""Mashtots slide 1 as pure X3D 4.0, no shaders, no Script: 216 PositionInterpolators (36 letters x 6 trail copies) on one TimeSensor.
The portable fallback of mashtots-reveal.x3d (which does the same flights on the GPU). Same data: reveal_data.py."""
from reveal_data import *
def track(p, lag):
    """keys/positions/scale for one letter (lag = seconds behind, for trail ghosts)."""
    keys, pos, sc = [], [], []
    def add(t, x, y, s):
        k = min(1.0, max(0.0, t / CYC))
        if keys and k <= keys[-1]: k = keys[-1] + 1e-6
        keys.append(round(k, 6)); pos.append(f"{wx(x)} {wy(y)} 0"); sc.append(round(s, 3))
    add(0, p["sx"], p["sy"], .7)
    steps = 24
    for leg, (t_start, rev) in enumerate(((p["t0"] + lag, False), (total + hold + p["t0"] + lag, True))):
        for k in range(steps + 1):
            pr = k / steps; e = ease(pr if not rev else 1 - pr)
            x, y = bez(p, e); s = .7 + .3 * min(1, e * 3)
            add(t_start + pr * flight, x, y, s)
        if leg == 0: add(total + hold + p["t0"] + lag - .01, p["tx"], p["ty"], 1.0)
    add(CYC, p["sx"], p["sy"], .7)
    return keys, pos, sc
GHOSTS = 5
out = []
w = out.append
w("<?xml version='1.0' encoding='UTF-8'?>")
w("<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>")
w("  <head>")
w("    <meta name='title' content='mashtots-reveal-classic.x3d'/>")
w("    <meta name='description' content='Slide 1 of the Mashtots deck as X3D: the 36 letters of Mesrop Mashtots alphabet leave the alphabet stone in the mural, cross the dark on cubic Bezier paths with comet trails, settle into one gilt line, rest, and return. Port of reveal.js (seed 405, stagger 0.075 s, flight 2.8 s, cubic ease). TimeSensor, PositionInterpolator, ScalarInterpolator and ROUTEs only; no Script.'/>")
w("    <meta name='creator' content='port of the Mashtots deck JavaScript; X3D by Claude for the x3d.io project'/>")
w("  </head>\n  <Scene>")
w("    <WorldInfo title='Mashtots reveal' info='36 letters, stone to gilt line'/>")
w("    <NavigationInfo type='\"NONE\"' headlight='false'/>")
w("    <Viewpoint position='0 0 12.2' fieldOfView='0.9' description='slide'/>")
w("    <Background skyColor='0.027 0.024 0.035'/>")
w("    <DirectionalLight direction='0 0 -1' intensity='0.4'/>")
w(f"    <TimeSensor DEF='Clock' cycleInterval='{CYC:.3f}' loop='true'/>")
# the stone: plate + teal glow that swells while letters leave and again as they return
cx, cy = wx(src['x'] + src['w']/2), wy(src['y'] + src['h']/2)
w(f"    <Transform translation='{cx} {cy} -0.3'><Shape><Appearance><Material diffuseColor='0.16 0.14 0.12' emissiveColor='0.03 0.04 0.04'/></Appearance><Box size='{src['w']*S+0.3:.3f} {src['h']*S+0.3:.3f} 0.2'/></Shape></Transform>")
w(f"    <Transform DEF='Glow' translation='{cx} {cy} -0.1'><Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='0.79 0.94 0.91' transparency='0.92' DEF='GlowMat'/></Appearance><Sphere radius='1.4'/></Shape><Shape><Appearance><Material diffuseColor='0 0 0' emissiveColor='0.79 0.94 0.91' transparency='0.8' DEF='GlowMat2'/></Appearance><Sphere radius='0.9'/></Shape></Transform>")
gk = [0, (begin-.8)/CYC, begin/CYC, (total-1.2)/CYC, (total+hold-1.0)/CYC, (total+hold+begin)/CYC, (CYC-.8)/CYC, 1]
gv = [1, 1, .85, 1, 1, .85, 1, 1]
w(f"    <ScalarInterpolator DEF='GlowI' key='{' '.join(f'{k:.5f}' for k in gk)}' keyValue='{' '.join(map(str, gv))}'/>")
w("    <ROUTE fromNode='Clock' fromField='fraction_changed' toNode='GlowI' toField='set_fraction'/>")
w("    <ROUTE fromNode='GlowI' fromField='value_changed' toNode='GlowMat' toField='set_transparency'/>")
# letters: one Text geometry per glyph (DEF/USE), gold material, ghosts fade behind
for i, p in enumerate(P):
    for g in range(GHOSTS + 1):
        lag = g * 0.055
        keys, pos, sc = track(p, lag)
        nm = f"L{i}_{g}"
        tr = 0 if g == 0 else round(1 - 0.5 * (1 - g / (GHOSTS + 1)) ** 1.6, 3)
        w(f"    <Transform DEF='{nm}' translation='{pos[0]}' scale='{sc[0]} {sc[0]} 1'><Shape><Appearance><Material diffuseColor='1 1 1' emissiveColor='0.7 0.7 0.7' transparency='{tr}'/><ImageTexture url='&quot;glyphs/g{i:02d}.png&quot;'/></Appearance><IndexedFaceSet coordIndex='0 1 2 3 -1' solid='false'><Coordinate point='-0.3 -0.3 0 0.3 -0.3 0 0.3 0.3 0 -0.3 0.3 0'/><TextureCoordinate point='0 0 1 0 1 1 0 1'/></IndexedFaceSet></Shape></Transform>")
        w(f"    <PositionInterpolator DEF='{nm}P' key='{' '.join(map(str, keys))}' keyValue='{' '.join(pos)}'/>")
        w(f"    <ROUTE fromNode='Clock' fromField='fraction_changed' toNode='{nm}P' toField='set_fraction'/><ROUTE fromNode='{nm}P' fromField='value_changed' toNode='{nm}' toField='set_translation'/>")
w("  </Scene>\n</X3D>")
open("mashtots-reveal-classic.x3d", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("cycle", round(CYC, 2), "s;", N, "letters x", GHOSTS + 1, "copies; bytes", sum(len(s) for s in out))
