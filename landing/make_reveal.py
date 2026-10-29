#!/usr/bin/env python3
"""Mashtots slide 1 as X3D 4.0 in the Gobbler-3 style: one number (phase) drives everything on the GPU.

reveal.js animates 36 letters with a per-frame loop. The portable port (make_reveal_classic.py) needs 216 PositionInterpolators.
Here the same flights, same seed-405 control points, same stagger / flight / cubic ease run in ONE vertex shader: the file carries
each letter's six numbers (stone cell, gilt-line slot, two Bezier handles, start time) as vertex attributes, and `phase` (the
TimeSensor fraction, ROUTEd straight into the shader) says when. No Script node. The stone, glow and gilt hairline are a second
shader driven by the same phase; embers are a ParticleSystem gated by a BooleanSequencer (Gobbler's EmberWindow pattern).
Enhancements over reveal.js (all in the CONSTANTS block, set to 0 to get the flat original): LIFT (letters swell toward the camera
mid-flight, real depth), DOLLY (slow push-in while they gather)."""
import math, os, sys, argparse
from PIL import Image
from reveal_data import *

ap = argparse.ArgumentParser(description="--freeze SEC writes a still frame (phase fixed, clock unrouted) to --out, for inspection; default is the looping animation")
ap.add_argument("--freeze", type=float); ap.add_argument("--out", default="mashtots-reveal.x3d"); ap.add_argument("--cam", nargs=3, type=float)
ARGS = ap.parse_args()
# ---------------- constants (the 2D original = LIFT 0, DOLLY 0) ----------------
LIFT = 1.1            # world units a letter rises toward the camera at mid-flight
DOLLY = 0.55          # camera push-in while the line forms
HALF = 0.30           # letter quad half-size (world units; 1 unit = 100 slide px)
GHOSTS = 5            # comet-trail copies per letter
LAG = 0.055           # seconds each trail copy runs behind
CAM_Z = 12.55         # at rest; 16:9 canvas, vertical fov 0.9 rad sees 12.2 x 21.7 world units here, so the whole 16.3-wide line fits

# ---------------- atlas: the 36 glyph PNGs in one 6x6 sheet (one texture, one draw call) ----------------
G = 192
atlas = Image.new("RGBA", (6 * G, 6 * G), (0, 0, 0, 0))
for i in range(N):
    atlas.paste(Image.open(f"glyphs/g{i:02d}.png").convert("RGBA"), ((i % 6) * G, (i // 6) * G))
atlas.save("glyphs/atlas.png", optimize=True)
def uv(i):            # inset half a texel so bilinear filtering never bleeds a neighbour's glyph in
    # the shader gets the atlas through an SFNode field and X_ITE hands it over top-row-first (v = 0 at the TOP of the PNG), so the
    # bottom corner of a quad samples v = (row + 1) / 6. Found by drawing one cell on every quad (DEBUG_UV): the standard bottom-origin
    # mapping showed the stone's glyphs scrambled (atlas rows reversed).
    e = 0.5 / (6 * G); c, r = i % 6, i // 6
    return (c / 6 + e, (r + 1) / 6 - e, (c + 1) / 6 - e, r / 6 + e)

# ---------------- mesh: back layers first (so trails draw under the letter), main layer last ----------------
f = lambda v: f"{v:.4f}".rstrip("0").rstrip(".") if "." in f"{v:.4f}" else f"{v:.4f}"
coord, A, B, C, U, idx = [], [], [], [], [], []
for g in range(GHOSTS, -1, -1):                       # g = 0 is the letter itself
    alpha = 1.0 if g == 0 else 1 - (1 - 0.5 * (1 - g / (GHOSTS + 1)) ** 1.6)   # same fade as the classic ghosts
    for i, p in enumerate(P):
        u0, v0, u1, v1 = uv(int(os.environ.get("DEBUG_UV", i))); base = len(coord)
        for cx_, cy_ in ((-HALF, -HALF), (HALF, -HALF), (HALF, HALF), (-HALF, HALF)):
            coord.append(f"{f(cx_)} {f(cy_)} {f(-0.02 * g)}"); U.append(f"{u0:.5f} {v0:.5f} {u1:.5f} {v1:.5f}")
            A.append(f"{f(wx(p['sx']))} {f(wy(p['sy']))} {f(wx(p['tx']))} {f(wy(p['ty']))}")
            B.append(f"{f(wx(p['c1x']))} {f(wy(p['c1y']))} {f(wx(p['c2x']))} {f(wy(p['c2y']))}")
            C.append(f"{p['t0']:.3f} {g * LAG:.3f} {alpha:.3f} {1 if g else 0}")
        idx.append(f"{base} {base+1} {base+2} {base+3} -1")

VS = f"""data:x-shader/x-vertex,#version 300 es
precision highp float;
precision highp int;
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
uniform float phase;                      // TimeSensor fraction, 0..1 over one cycle
in vec4 x3d_Vertex;                       // quad corner (+-HALF, +-HALF, layer z)
in vec4 aU;                               // this letter's atlas rectangle u0 v0 u1 v1 (own attribute: the Appearance has no texture, so TexCoord is not relied on)
in vec4 aA;                               // stone cell xy, line slot xy (world)
in vec4 aB;                               // Bezier handle 1 xy, handle 2 xy (world)
in vec4 aC;                               // start time, trail lag, trail alpha, is-trail
out vec2 vUV; out float vA; out float vMove; out float vSettle; out float vX;
const float CYC = {CYC:.4f}, TOTAL = {total:.4f}, HOLD = {hold:.4f}, FLIGHT = {flight:.4f}, LIFT = {LIFT:.3f};
float ease(float p) {{ return p < 0.5 ? 4.0 * p * p * p : 1.0 - pow(-2.0 * p + 2.0, 3.0) / 2.0; }}
void main() {{
  float t = phase * CYC;
  float tOut = t - (aC.x + aC.y);                                   // seconds since this copy left the stone
  float tBack = t - (TOTAL + HOLD + aC.x + aC.y);                   // seconds since it started home
  float pr = tBack > 0.0 ? 1.0 - clamp(tBack / FLIGHT, 0.0, 1.0) : clamp(tOut / FLIGHT, 0.0, 1.0);
  float e = ease(pr), u = 1.0 - e;
  vec2 p = u*u*u*aA.xy + 3.0*u*u*e*aB.xy + 3.0*u*e*e*aB.zw + e*e*e*aA.zw;   // cubic Bezier, the exact reveal.js curve
  float s = 0.7 + 0.3 * min(1.0, e * 3.0);
  float edge = min(e, 1.0 - e);
  vUV = vec2(x3d_Vertex.x > 0.0 ? aU.z : aU.x, x3d_Vertex.y > 0.0 ? aU.w : aU.y);
  vA = aC.z * (aC.w > 0.5 ? smoothstep(0.0, 0.06, edge) : 1.0);      // trails exist only while moving
  vMove = 4.0 * e * (1.0 - e);
  vSettle = smoothstep(0.97, 1.0, e);
  vX = p.x;
  float z = x3d_Vertex.z + LIFT * sin(3.14159265 * e);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(p + x3d_Vertex.xy * s, z, 1.0);
}}
"""
FS = """data:x-shader/x-fragment,#version 300 es
precision highp float;
precision highp int;
uniform sampler2D atlas;
uniform float phase;
in vec2 vUV; in float vA; in float vMove; in float vSettle; in float vX;
out vec4 x3d_FragColor;
void main() {
  vec4 g = texture(atlas, vUV);
  float a = g.a * vA;
  if (a < 0.01) discard;
  vec3 hot = vec3(1.0, 0.93, 0.72);
  vec3 col = mix(g.rgb, hot, 0.6 * vMove) * (1.05 + 0.45 * vMove);   // gold at rest, white-hot in flight
  float wave = 0.5 + 0.5 * sin(vX * 3.2 - phase * 62.8);               // slow shimmer travelling along the settled line
  col *= 1.0 + vSettle * 0.28 * wave;
  x3d_FragColor = vec4(col, a);
}
"""

# ---------------- backdrop: dark stone wall, the alphabet stone with its 4x9 carved cells, teal glow, gilt hairline ----------------
sx0, sy0 = wx(src["x"] + src["w"] / 2), wy(src["y"] + src["h"] / 2)
HX, HY = src["w"] * S / 2 + 0.12, src["h"] * S / 2 + 0.12
LINE_Y = wy(row["y"]) - 0.34; LINE_HALF = (row["w"] / 2) * S + 0.1
BVS = """data:x-shader/x-vertex,#version 300 es
precision highp float;
uniform mat4 x3d_ProjectionMatrix;
uniform mat4 x3d_ModelViewMatrix;
in vec4 x3d_Vertex;
out vec2 vP;
void main() { vP = x3d_Vertex.xy; gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex; }
"""
BFS = f"""data:x-shader/x-fragment,#version 300 es
precision highp float;
precision highp int;
uniform float phase;
in vec2 vP;
out vec4 x3d_FragColor;
const float CYC = {CYC:.4f}, TOTAL = {total:.4f}, HOLD = {hold:.4f}, BEGIN = {begin:.3f}, STAGGER = {stagger:.3f};
const vec2 SC = vec2({sx0:.4f}, {sy0:.4f}), SH = vec2({HX:.4f}, {HY:.4f});
const float LINE_Y = {LINE_Y:.4f}, LINE_HALF = {LINE_HALF:.4f};
float h2(vec2 p) {{ vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }}
float vn(vec2 x) {{ vec2 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }}
void main() {{
  float t = phase * CYC;
  float n = vn(vP * 3.0) * 0.6 + vn(vP * 11.0) * 0.4;
  vec3 col = vec3(0.030, 0.027, 0.036) * (0.8 + 0.5 * n);                         // dark mural wall
  col *= 1.0 - 0.07 * dot(vP * vec2(0.045, 0.08), vP * vec2(0.045, 0.08)) * 30.0; // vignette
  // the stone: a plate, carved cells that stay lit while their letter is still in them
  vec2 d = abs(vP - SC) - SH;
  float plate = 1.0 - smoothstep(-0.02, 0.02, max(d.x, d.y));
  vec2 cell = (vP - SC + SH - 0.12) / (SH * 2.0 - 0.24);                          // 0..1 over the carved area
  float inside = step(0.0, cell.x) * step(cell.x, 1.0) * step(0.0, cell.y) * step(cell.y, 1.0);
  vec2 cg = vec2(floor(cell.x * 4.0), floor((1.0 - cell.y) * 9.0));
  float idx = cg.y * 4.0 + cg.x;
  float t0 = BEGIN + idx * STAGGER;
  float away = step(t0 + 0.1, t) * (1.0 - step(TOTAL + HOLD + t0 + {flight:.3f}, t));   // gone from its cell until it is home again
  float present = 1.0 - away;
  vec2 gf = fract(vec2(cell.x * 4.0, (1.0 - cell.y) * 9.0));
  float groove = inside * (smoothstep(0.0, 0.06, min(gf.x, 1.0 - gf.x)) * smoothstep(0.0, 0.05, min(gf.y, 1.0 - gf.y)));
  vec3 stone = vec3(0.17, 0.145, 0.12) * (0.75 + 0.5 * n);
  stone *= 1.0 - 0.45 * inside * (1.0 - groove);                                 // joints between cells
  stone += inside * groove * present * vec3(0.03, 0.07, 0.07);
  col = mix(col, stone, plate);
  // teal glow that swells as letters leave and again as they come home
  float out_ = smoothstep(BEGIN - 0.6, BEGIN + 0.8, t) * (1.0 - smoothstep(BEGIN + 3.8, BEGIN + 5.2, t));
  float back_ = smoothstep(TOTAL + HOLD + BEGIN - 0.6, TOTAL + HOLD + BEGIN + 0.8, t) * (1.0 - smoothstep(TOTAL + HOLD + BEGIN + 3.8, TOTAL + HOLD + BEGIN + 5.2, t));
  float swell = 0.55 + 0.9 * max(out_, back_) + 0.07 * sin(t * 2.1);
  vec2 q = (vP - SC) * vec2(1.0, 0.62);
  col += vec3(0.28, 0.62, 0.58) * (exp(-dot(q, q) / 1.6) * 0.16 + exp(-dot(q, q) / 0.35) * 0.20) * swell;
  // gilt hairline under the settled line: grows from the middle, retreats before the letters go home
  float amt = smoothstep(TOTAL - 1.6, TOTAL - 0.1, t) * (1.0 - smoothstep(TOTAL + HOLD + BEGIN - 0.3, TOTAL + HOLD + BEGIN + 1.1, t));
  float L = LINE_HALF * amt;
  float along = 1.0 - smoothstep(L - 0.5, L, abs(vP.x));
  float w = abs(vP.y - LINE_Y);
  col += vec3(0.88, 0.68, 0.40) * along * (exp(-w * w / 0.00005) * 0.9 + exp(-w * w / 0.004) * 0.12);
  col += (h2(gl_FragCoord.xy) - 0.5) * 0.012;                                    // dither, no banding in the dark
  x3d_FragColor = vec4(col, 1.0);
}}
"""

# ---------------- embers: sprite texture as 16x16 luminance+alpha PixelTexture ----------------
def ember_image(n=16):
    rows = []
    for y in range(n):
        for x in range(n):
            r2 = ((x + .5 - n / 2) ** 2 + (y + .5 - n / 2) ** 2) / (n / 2) ** 2
            rows.append(f"0xFF{int(255 * max(0.0, 1 - r2) ** 2):02X}")
    return f"{n} {n} 2 " + " ".join(rows)

gk = lambda *ts: " ".join(f"{t / CYC:.5f}" for t in ts)
span = (N - 1) * stagger + 0.6
out = []; w = out.append
w("<?xml version='1.0' encoding='UTF-8'?>")
w("<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>")
w("  <head>")
w("    <component name='ParticleSystems' level='3'/>")
w("    <component name='Shaders' level='1'/>")
w("    <component name='Shape' level='4'/>")
w("    <meta name='title' content='mashtots-reveal.x3d'/>")
w("    <meta name='description' content='Slide 1 of the Mashtots deck as X3D: the 36 letters of the Mesrop Mashtots alphabet leave the alphabet stone, cross the dark on the same cubic Bezier paths as reveal.js (seed 405, stagger 0.075 s, flight 2.8 s, cubic ease), settle into one gilt line, rest, and return. One TimeSensor fraction drives a vertex shader (the Gobbler 3 pattern); embers gated by a BooleanSequencer; no Script node.'/>")
w("    <meta name='creator' content='port of the Mashtots deck JavaScript; X3D by Claude for the x3d.io project, in the style of hagopjay Gobbler 3'/>")
w("    <meta name='generator' content='make_reveal.py + reveal_data.py'/>")
w("    <meta name='fallback' content='mashtots-reveal-classic.x3d: same animation with 216 PositionInterpolators, no shaders'/>")
w("  </head>\n  <Scene>")
w("    <WorldInfo title='Mashtots reveal' info='&quot;36 letters, stone to gilt line&quot;'>")
w("      <MetadataSet containerField='metadata' name='reveal' reference='reveal.js of the Mashtots deck'>")
w(f"        <MetadataInteger name='seed' value='405'/><MetadataInteger name='letters' value='{N}'/>")
w(f"        <MetadataFloat name='beginSeconds' value='{begin}'/><MetadataFloat name='staggerSeconds' value='{stagger}'/><MetadataFloat name='flightSeconds' value='{flight}'/><MetadataFloat name='holdSeconds' value='{hold}'/><MetadataFloat name='cycleSeconds' value='{CYC:.3f}'/>")
w(f"        <MetadataString name='alphabet' value='{' '.join(chr(34) + c + chr(34) for c in LET)}'/>")
w("      </MetadataSet>")
w("    </WorldInfo>")
w("    <NavigationInfo DEF='Nav' type='&quot;NONE&quot;' headlight='false'/>")
w(f"    <Viewpoint DEF='Cam' position='{' '.join(map(str, ARGS.cam)) if ARGS.cam else f'0 0 {CAM_Z}'}' fieldOfView='0.9' description='slide'/>")
w("    <Viewpoint DEF='CamStone' position='-2.2 1.0 4.6' fieldOfView='0.9' description='alphabet stone'/>")
w("    <Viewpoint DEF='CamLine' position='-4.2 -1.5 6.2' fieldOfView='0.9' description='gilt line, left half'/>")
w("    <Background skyColor='0.027 0.024 0.035'/>")
w(f"    <TimeSensor DEF='Clock' cycleInterval='{CYC:.3f}' loop='true'/>")
w("    <!-- Backdrop: one quad, one fragment shader. Wall, alphabet stone with its 4 x 9 carved cells, teal glow, gilt hairline. -->")
w("    <Shape><Appearance>")
w("      <Material diffuseColor='0.03 0.03 0.04'/>")
w("      <ComposedShader DEF='StoneShader' language='GLSL'>")
w(f"        <field name='phase' type='SFFloat' accessType='inputOutput' value='{(ARGS.freeze or 0) / CYC:.5f}'/>")
w(f"        <ShaderPart type='VERTEX'><![CDATA[{BVS}]]></ShaderPart>")
w(f"        <ShaderPart type='FRAGMENT'><![CDATA[{BFS}]]></ShaderPart>")
w("      </ComposedShader>")
w("    </Appearance><IndexedFaceSet coordIndex='0 1 2 3 -1'><Coordinate point='-17 -9.5 -0.3 17 -9.5 -0.3 17 9.5 -0.3 -17 9.5 -0.3'/></IndexedFaceSet></Shape>")
w("    <!-- The letters: 36 x 6 quads in ONE mesh. Per-vertex attributes aA, aB, aC carry each letter's stone cell, gilt-line slot, Bezier handles and start time;")
w("         the vertex shader turns `phase` into position. Back trail layers come first so they draw under the letter. If shaders are unavailable the plain")
w("         textured Material shows the alphabet at rest (use mashtots-reveal-classic.x3d there). -->")
w("    <!-- bboxSize matters: the quads' own coordinates all sit near the origin and the shader moves them, so without it a browser culls the whole mesh whenever the camera looks away from the origin. -->")
w("    <Shape bboxCenter='0 0.5 0.6' bboxSize='21 13 3.4'><Appearance alphaMode='BLEND'>")
w("      <Material diffuseColor='0.88 0.68 0.40' emissiveColor='0.5 0.38 0.2'/>")
w("      <ComposedShader DEF='LetterShader' language='GLSL'>")
w(f"        <field name='phase' type='SFFloat' accessType='inputOutput' value='{(ARGS.freeze or 0) / CYC:.5f}'/>")
w("        <field name='atlas' type='SFNode' accessType='inputOutput'><ImageTexture url='&quot;glyphs/atlas.png&quot;'/></field>")
w(f"        <ShaderPart type='VERTEX'><![CDATA[{VS}]]></ShaderPart>")
w(f"        <ShaderPart type='FRAGMENT'><![CDATA[{FS}]]></ShaderPart>")
w("      </ComposedShader>")
w("    </Appearance>")
w(f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'>")
w(f"      <Coordinate point='{', '.join(coord)}'/>")
w(f"      <FloatVertexAttribute name='aU' numComponents='4' value='{' '.join(U)}'/>")
w(f"      <FloatVertexAttribute name='aA' numComponents='4' value='{' '.join(A)}'/>")
w(f"      <FloatVertexAttribute name='aB' numComponents='4' value='{' '.join(B)}'/>")
w(f"      <FloatVertexAttribute name='aC' numComponents='4' value='{' '.join(C)}'/>")
w("    </IndexedFaceSet></Shape>")
w("    <!-- Embers: sparks lift off the stone while the letters leave and again while they come home (Gobbler's EmberWindow pattern). -->")
w(f"    <Transform translation='{sx0:.3f} {sy0:.3f} 0.1'>")
w("      <ParticleSystem DEF='Embers' geometryType='SPRITE' maxParticles='400' particleLifetime='2.2' lifetimeVariation='0.4' particleSize='0.16 0.16' colorKey='0 0.15 0.6 1' createParticles='false'>")
w(f"        <Appearance alphaMode='BLEND'><UnlitMaterial emissiveColor='1 1 1'/><PixelTexture repeatS='false' repeatT='false' image='{ember_image()}'/></Appearance>")
w("        <ColorRGBA color='1 0.93 0.7 0.7, 0.9 0.7 0.4 0.9, 0.6 0.35 0.18 0.5, 0.25 0.15 0.1 0'/>")
w("        <ConeEmitter position='0 0 0' direction='0.5 1 0.3' angle='0.9' speed='1.3' variation='0.6' mass='0.001' surfaceArea='0.05' on='true'/>")
w("      </ParticleSystem>")
w("    </Transform>")
w(f"    <BooleanSequencer DEF='EmberWindow' key='{gk(0, begin - .3, begin + span, total + hold + begin - .3, total + hold + begin + span, CYC)}' keyValue='false true false true false false'/>")
w("    <!-- Camera: a slow push-in while the line forms, back out as it returns. -->")
w(f"    <PositionInterpolator DEF='Dolly' key='{gk(0, begin, total, total + hold, total + hold + begin + flight, CYC)}' keyValue='0 0 {CAM_Z}, 0 0 {CAM_Z}, 0 0 {CAM_Z - DOLLY}, 0 0 {CAM_Z - DOLLY * 0.8}, 0 0 {CAM_Z}, 0 0 {CAM_Z}'/>")
w("    <!-- One clock. The shaders take phase; the sequencer gates the embers; the interpolator moves the camera. -->")
if ARGS.freeze is None:
    for to in ("LetterShader", "StoneShader"):
        w(f"    <ROUTE fromNode='Clock' fromField='fraction_changed' toNode='{to}' toField='phase'/>")
    w("    <ROUTE fromNode='Clock' fromField='fraction_changed' toNode='EmberWindow' toField='set_fraction'/>")
    w("    <ROUTE fromNode='EmberWindow' fromField='value_changed' toNode='Embers' toField='set_createParticles'/>")
    w("    <ROUTE fromNode='Clock' fromField='fraction_changed' toNode='Dolly' toField='set_fraction'/>")
    w("    <ROUTE fromNode='Dolly' fromField='value_changed' toNode='Cam' toField='set_position'/>")
w("  </Scene>\n</X3D>")
open(ARGS.out, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("cycle", round(CYC, 2), "s;", N, "letters x", GHOSTS + 1, "layers;", len(coord), "vertices; bytes", sum(len(s) + 1 for s in out), "(classic:", os.path.getsize("mashtots-reveal-classic.x3d"), ")")
