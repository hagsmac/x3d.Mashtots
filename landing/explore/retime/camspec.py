"""explore/retime: the world camera and the spectral moments, as patches on the approved generator (patch.py applies them after its own).

CAMERA. Every vertex shader of the Landing ends in  x3d_ProjectionMatrix * x3d_ModelViewMatrix * (position).  The patch inserts one matrix, CAM,
computed in tl() from the one clock:  x3d_ModelViewMatrix * CAM * (position).  CAM turns the whole set (the mural, the helix, the letters, the
cards) about a pivot and pushes it towards the viewer, so a sweep is a camera move that follows seeks, the director's speed and any re-timing,
with no Script and no Viewpoint animation. The choreography is data in presets.json: "camera" is a list of moves, each a weight k (any GLSL
expression of the clock, e.g. plateau(t_, TL, TT + 5.0, 1.8)), a yaw and a pitch in radians, a push in world units, a pivot.

COLOUR. "spectral" is a list of moments, each a weight k and a metric; while one is active the letters take the colour of their metric:
  pitch     the letter's own note in the score (the stone's ladder, make_music.lf_row), doubled 40 or 41 times into 400-800 THz: visible light
            spans almost exactly one octave. The hue is the CIE 1931 2-degree colour of that frequency (the analytic fit of Wyman, Sloan and
            Shirley 2013, accurate between 420 and 650 nm; beyond, the spectrum's chromaticity hardly moves, so the hue is taken at the nearer end),
            brightness normalised so that every letter stays legible. Sound-to-light by octaves is an authored mapping; each step of it is physics.
  value     log10 of the letter's numeric value (1 ... 9000), on Turbo (a perceptually ordered rainbow; Mikhailov 2019).
  fastmode  the measured fastest mode of the Grabar graph (data-graph/), consonants -> vowels, on Turbo.
  pagerank  the deck's PageRank at the current iteration (the authored graph): every letter starts at 1/36 and the colours separate as
            rank flows; scaled from the final minimum to the final maximum, on Turbo. The node glows take the same colour.
A legend (the spectrum in use and what it means) shows with each moment.
"""

import json as _json, os as _os
_L = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..", "scratch", "landing.json"), encoding="utf-8"))
PRV0 = f"{min(_L['PR'][14]) / _L['PRmax']:.4f}"     # the final minimum of PageRank over its maximum: the bottom of the PageRank moment's colour scale

SPECLIB = r"""
float g_(float x, float mu, float s1, float s2){ float t = (x - mu) / (x < mu ? s1 : s2); return exp(-0.5 * t * t); }
vec3 lightHue(float nm){                          // the hue of monochromatic light (CIE 1931 2-degree -> sRGB), brightness normalised
  nm = clamp(nm, 420.0, 650.0);
  float X = 1.056 * g_(nm, 599.8, 37.9, 31.0) + 0.362 * g_(nm, 442.0, 16.0, 26.7) - 0.065 * g_(nm, 501.1, 20.4, 26.2);
  float Y = 0.821 * g_(nm, 568.8, 46.9, 40.5) + 0.286 * g_(nm, 530.9, 16.3, 31.1);
  float Z = 1.217 * g_(nm, 437.0, 11.8, 36.0) + 0.681 * g_(nm, 459.0, 26.0, 13.8);
  vec3 c = mat3(3.2406, -0.9689, 0.0557, -1.5372, 1.8758, -0.2040, -0.4986, 0.0415, 1.0570) * vec3(X, Y, Z);
  c -= min(0.0, min(c.r, min(c.g, c.b)));         // outside the sRGB gamut: add white until no channel is negative
  return pow(c / max(c.r, max(c.g, max(c.b, 1e-6))), vec3(1.0 / 2.2));
}
vec3 turbo(float x){                              // Turbo, the polynomial fit (Mikhailov 2019, Apache-2.0)
  const vec4 kR = vec4(0.13572138, 4.61539260, -42.66032258, 132.13108234), kG = vec4(0.09140261, 2.19418839, 4.84296658, -14.18503333), kB = vec4(0.10667330, 12.64194608, -60.58204836, 110.36276771);
  const vec2 kR2 = vec2(-152.94239396, 59.28637943), kG2 = vec2(4.27729857, 2.82956604), kB2 = vec2(-89.90310912, 27.34824973);
  x = clamp(x, 0.0, 1.0); vec4 v4 = vec4(1.0, x, x * x, x * x * x); vec2 v2 = v4.zw * v4.z;
  return clamp(vec3(dot(v4, kR) + dot(v2, kR2), dot(v4, kG) + dot(v2, kG2), dot(v4, kB) + dot(v2, kB2)), 0.0, 1.0);
}
"""

CAMLIB = r"""
// ---- explore/retime: the world camera and the spectral moments, both functions of the one clock (the preset writes their choreography) ----
mat4 CAM = mat4(1.0);                             // every vertex shader multiplies by it: x3d_ModelViewMatrix * CAM * position
float camAmt = 0.0;                               // how strongly a move is on (0..1): the title block dims by it
float specAmt = 0.0, specMode = -1.0;             // the active spectral moment: how much, and which metric (0 pitch, 1 value, 2 fastest mode, 3 PageRank)
uniform vec4 LM[36];                              // the letters' metrics (x its note as light, nm; y log10 value; z fastest mode; w final PageRank)
float rankZ = 0.0;                                // the PageRank moment lifts each letter out of the ring's plane by its rank
float bump(float x, float a, float b){ float u = (x - a) / (b - a); return (u <= 0.0 || u >= 1.0) ? 0.0 : pow(sin(PI * u), 2.0); }
float plateau(float x, float a, float b, float d){ return (x <= a || x >= b) ? 0.0 : ease(cl((x - a) / d)) * (1.0 - ease(cl((x - (b - d)) / d))); }
mat4 mTrans(vec3 v){ return mat4(1.0, 0.0, 0.0, 0.0,  0.0, 1.0, 0.0, 0.0,  0.0, 0.0, 1.0, 0.0,  v.x, v.y, v.z, 1.0); }
mat4 mRotY(float a){ float c = cos(a), s = sin(a); return mat4(c, 0.0, -s, 0.0,  0.0, 1.0, 0.0, 0.0,  s, 0.0, c, 0.0,  0.0, 0.0, 0.0, 1.0); }
mat4 mRotX(float a){ float c = cos(a), s = sin(a); return mat4(1.0, 0.0, 0.0, 0.0,  0.0, c, s, 0.0,  0.0, -s, c, 0.0,  0.0, 0.0, 0.0, 1.0); }
mat4 lookAtM(vec3 e, vec3 c){                      // a view matrix: eye e looking at c, y up
  vec3 f = normalize(c - e), sd = normalize(cross(f, vec3(0.0, 1.0, 0.0))), up = cross(sd, f);
  return mat4(sd.x, up.x, -f.x, 0.0,  sd.y, up.y, -f.y, 0.0,  sd.z, up.z, -f.z, 0.0,  -dot(sd, e), -dot(up, e), dot(f, e), 1.0);
}
float prog(float x, float a, float b){ return clamp((x - a) / (b - a), 0.0, 1.0); }
void camera(){
  float yaw = 0.0, pitch = 0.0, push = 0.0, w = 0.0, k, u = 0.0; vec3 piv = vec3(0.0);
  // look-at shots blend by weight: eye and target are offsets from the slide camera (eye 0 0 15, looking at the origin)
  vec3 E0 = vec3(0.0, 0.0, 15.0), eyeOff = vec3(0.0), tgtOff = vec3(0.0);
  vec3 HCW = vec3((HC.x - 960.0) * 0.01, (540.0 - HC.y) * 0.01, -HR * 0.01), RINGW = vec3(0.0, 1.95, 0.0), TENSORW = vec3(3.7, 1.68, 0.0), STONEW = vec3(-2.055, 1.26, 0.0);
@CAMERA_GLSL@
  camAmt = clamp(w, 0.0, 1.0);
  piv = w > 1e-4 ? piv / w : vec3(0.0);
  mat4 legacy = mTrans(vec3(0.0, 0.0, push)) * mTrans(piv) * mRotX(pitch) * mRotY(yaw) * mTrans(-piv);
  vec3 eye = E0 + eyeOff + vec3(eyeX - 1.0, 0.0, 0.0);          // eyeX: the stereo eye (1 = centre); the target stays, so the two eyes converge on it
  CAM = mTrans(vec3(0.0, 0.0, 15.0)) * lookAtM(eye, tgtOff) * legacy;
}
void spectral(){
  float k; specAmt = 0.0; specMode = -1.0;
@SPECTRAL_GLSL@
  rankZ = specMode > 2.5 ? specAmt : 0.0;
}
""" + SPECLIB

GLSL_CAMSPEC = [
 ("uniform float toff;", "uniform float toff;\nuniform float eyeX;       // explore: the stereo eye, routed from the Eye TimeSensor (1 = centre; left and right are 1 -+ half the separation)"),
 ("bool inHelix;\nvoid tl(){", "bool inHelix;\n" + CAMLIB + "void tl(){"),
 ("// the attention map hides while an interlude holds act time\n}", "// the attention map hides while an interlude holds act time\n  camera(); spectral();\n}"),
]

GEN_CAMSPEC = [
 # the preset's choreography -> GLSL; the letters' metrics
 ('assert MEAS["order"] == "".join(d[0] for d in D["DATA"]), "letter order"',
  'assert MEAS["order"] == "".join(d[0] for d in D["DATA"]), "letter order"\n'
  '_PRE = timeline.PRESETS[timeline.PRESET]\n'
  '_PIVOT = {"helix": ((D["HC"]["x"] - 960) * 0.01, (540 - D["HC"]["y"]) * 0.01, -D["R"] * 0.01), "tensor": ((D["TV"]["x"] - 960) * 0.01, (540 - D["TV"]["y"]) * 0.01, 0.0),\n'
  '          "ring": (0.0, (540 - 345) * 0.01, 0.0), "stone": ((754.5 - 960) * 0.01, (540 - 414) * 0.01, 0.0), "slide": (0.0, 0.0, 0.0)}\n'
  'import camspec as _cs\n'
  'CAMERA_GLSL = _cs.camera_glsl(_PRE.get("camera", []), _PIVOT)\n'
  '_METRIC = {"pitch": 0, "value": 1, "fastmode": 2, "pagerank": 3}\n'
  'SPECTRAL_GLSL = "\\n".join(f"  k = {s[\'k\']}; if (k > specAmt) {{ specAmt = k; specMode = {_METRIC[s[\'metric\']]}.0; }}   // {s[\'name\']}" for s in _PRE.get("spectral", []))\n'
  'CONSTS.update(CAMERA_GLSL=CAMERA_GLSL or "  // (no camera moves in this preset)", SPECTRAL_GLSL=SPECTRAL_GLSL or "  // (no spectral moments in this preset)")\n'
  'def _light_nm(f):                                  # a note doubled until it is light (400 to 800 THz); its wavelength in nm\n'
  '    while f < 400e12: f *= 2\n'
  '    return 299792458.0 / f * 1e9\n'
  '_LAD = [1, 9/8, 32/27, 4/3, 3/2, 128/81, 16/9, 2, 9/4]\n'
  'def _fold(x):\n'
  '    while x >= 2: x /= 2\n'
  '    while x < 1: x *= 2\n'
  '    return x\n'
  '_PITCH = [293.665 * _LAD[i % 9] * _fold(1.5 ** (i // 9)) * (0.5 if i // 9 == 0 else 1.0) for i in range(N)]      # the stone\'s own pitches (make_music.lf_row)\n'
  '_PR14 = D["PR"][14]; _pr0, _pr1 = min(_PR14), max(_PR14)\n'
  'LM = [(_light_nm(_PITCH[i]), math.log10((i % 9 + 1) * 10 ** (i // 9)) / math.log10(9000), 0.5 + 0.5 * MEAS["fast_mode"][i], (_PR14[i] - _pr0) / (_pr1 - _pr0)) for i in range(N)]'),
 # the camera, in every vertex shader that has the clock
 ("def shader(name, fields, vs, fs):\n    vs = collapse_invisible(vs)",
  "def shader(name, fields, vs, fs):\n    vs = collapse_invisible(vs)\n"
  "    if \"void tl()\" in vs: vs = vs.replace(\"x3d_ModelViewMatrix *\", \"x3d_ModelViewMatrix * CAM *\")      # explore: the world camera"),
 # the letters: their metrics, and the colour of the active moment
 ("in vec4 aK;                       // letter index, ghost index, kind (0 glyph, 1 bloom, 2 trail copy)",
  "in vec4 aK;                       // letter index, ghost index, kind (0 glyph, 1 bloom, 2 trail copy)\n"
  "uniform sampler2D NODES;          // explore: PageRank by iteration (rows 6..20 of nodes.png), for the PageRank moment\n"
  "float rankNow(int i, float t){    // the letter's PageRank at the current iteration: 0 = the final minimum, 1 = the final maximum\n"
  "  float pk = clamp((t - TP) / 6.0 * 14.0, 0.0, 14.0); int k0 = int(floor(pk)), k1 = min(14, k0 + 1);\n"
  "  return (mix(texelFetch(NODES, ivec2(i, 6 + k0), 0).r, texelFetch(NODES, ivec2(i, 6 + k1), 0).r, pk - floor(pk)) - " + PRV0 + ") / (1.0 - " + PRV0 + ");\n}"),
 ("  if (kind < 0.5) { vCol = vec4(col, alpha); }",
  "  if (specAmt > 0.0 && st > 0.5) { vec4 lm = LM[i]; vec3 sc = specMode < 0.5 ? lightHue(lm.x) : turbo(specMode < 1.5 ? lm.y : specMode < 2.5 ? lm.z : rankNow(i, t));\n"
  "    col = mix(col, sc, specAmt); alpha = mix(alpha, max(alpha, 0.85), specAmt); bloom = mix(bloom, max(bloom, 0.3), specAmt); }\n"
  "  if (kind < 0.5) { vCol = vec4(col, alpha); }"),
 ('sh = shader("LetterShader", lfields() + "\\n" + sfnode_tex("atlas", "glyphs/atlas_white.png")',
  'sh = shader("LetterShader", lfields() + "\\n" + sfnode_tex("NODES", "glyphs/nodes.png", nearest=True) + "\\n" + sfnode_tex("atlas", "glyphs/atlas_white.png")'),
 # the node glows of PageRank take the same colour
 ("    r = 6.0 + 40.0 * mix(a0, a1, prK - floor(prK));",
  "    r = 6.0 + 40.0 * mix(a0, a1, prK - floor(prK));\n"
  "    if (specAmt > 0.0 && specMode > 2.5) col = mix(col, turbo((mix(a0, a1, prK - floor(prK)) - " + PRV0 + ") / (1.0 - " + PRV0 + ")), specAmt);      // explore: rank as colour, as it converges"),
 # the labels: one mode per spectral moment
 ("MODES = dict(none=0, veil=1, space=2, web=3, spec=4, poin=5, svd=6, vow=7)", "MODES = dict(none=0, veil=1, space=2, web=3, spec=4, poin=5, svd=6, vow=7, spec0=8, spec1=9, spec2=10, spec3=11)"),
 ("m < 6.5 ? svdK : vowK;", "m < 6.5 ? svdK : m < 7.5 ? vowK : (abs(specMode - (m - 8.0)) < 0.5 ? specAmt : 0.0);"),
 # the legend
 ("def pulses():", "def spectral_legend():\n"
  "    \"\"\"the legend of the spectral moments: the spectrum in use (a bar; for notes, ticks at the seven naturals) and what the colour means\"\"\"\n"
  "    if not _PRE.get(\"spectral\"): return\n"
  "    x0, y0, w_, h_ = 1552, 703, 224, 8\n"
  "    ticks = sorted((299792.458 / _light_nm(293.665 * r) - 400.0) / 400.0 for r in (1, 9/8, 32/27, 4/3, 3/2, 27/16, 16/9))      # D E F G A B C as light (0 = 400 THz, 1 = 800 THz)\n"
  "    vs = rect_vs(x0, y0, w_, h_, 0.03, \"out float vK; out float vM;\", \"vK = specAmt; vM = specMode;\", kill=\"vK <= 0.0\")\n"
  "    fs = SPECLIB_FS + \"\\nin vec2 vP; in float vA; in float vK; in float vM; out vec4 x3d_FragColor;\\nconst float TK[7] = float[7](\" + \", \".join(f\"{t:.4f}\" for t in ticks) + \");\\n\" + r\"\"\"\n"
  "void main(){\n"
  "  if (vK <= 0.0) discard;\n"
  "  float u = clamp((vP.x - @X0@) / @W@, 0.0, 1.0);\n"
  "  vec3 c = vM < 0.5 ? lightHue(299792.458 / mix(400.0, 800.0, u)) : turbo(u);\n"
  "  if (vM < 0.5) for (int k = 0; k < 7; k++) if (abs(u - TK[k]) * @W@ < 0.7) c *= 0.25;     // the seven naturals of D, where they fall in light\n"
  "  x3d_FragColor = vec4(c, 0.95 * vK);\n"
  "}\n"
  "\"\"\".replace(\"@X0@\", f\"{x0:.1f}\").replace(\"@W@\", f\"{w_:.1f}\")\n"
  "    rect_shape(\"SpecBarShader\", \"the legend of the spectral moments: the spectrum in use\", vs, fs)\n"
  "    TXT = [(\"գույն · colour = the letter's note as light: its frequency doubled 40 or 41 times (CIE 1931 hue)\", \"400 THz · red\", \"violet · 800 THz\"),\n"
  "           (\"գույն · colour = log10 of the letter's value (Turbo)\", \"1\", \"9 000\"),\n"
  "           (\"գույն · colour = the fastest mode, Measured in 342 533 letters of Grabar\", \"consonants\", \"vowels\"),\n"
  "           (\"գույն · colour = PageRank of the authored graph, as it converges (all start at 1/36)\", \"low\", \"high\")]\n"
  "    for j, (title, lo, hi) in enumerate(TXT):\n"
  "        ATL.add(f\"spl_t{j}\", title, 16); ATL.add(f\"spl_l{j}\", lo, 14); ATL.add(f\"spl_h{j}\", hi, 14)\n"
  "        label(f\"spl_t{j}\", x0 + w_, 694, col=C_PAPER, a=0.8, baseline=True, align=\"r\", mode=f\"spec{j}\")\n"
  "        label(f\"spl_l{j}\", x0, 729, col=NEUTRAL(190), a=0.8, baseline=True, mode=f\"spec{j}\")\n"
  "        label(f\"spl_h{j}\", x0 + w_, 729, col=NEUTRAL(190), a=0.8, baseline=True, align=\"r\", mode=f\"spec{j}\")\n"
  "\n"
  "def pulses():"),
 ("\npulses()\nflow()\ndescent()\n", "\npulses()\nflow()\nspectral_legend()\ndescent()\n"),
 # the fragment shaders do not include the library: give the legend its own copy of the colour functions
 ("HEAD = \"#version 300 es\\nprecision highp float;\\nprecision highp int;\\n\"",
  "HEAD = \"#version 300 es\\nprecision highp float;\\nprecision highp int;\\n\"\nSPECLIB_FS = \"const float PI = 3.14159265;\\n\" + " + repr(SPECLIB)),
 ('("LD", LD), ("LE", LE)))', '("LD", LD), ("LE", LE), ("LM", LM)))'),
 # the title block (the labels on the one-shot intro clock) stays put while the camera moves, and dims: it is an overlay, not part of the set
 ("  vCol = vec4(aC.rgb, aC.a * ((aM.w > 0.5 && aM.w < 1.5) ? 1.0 : a) * k * cineK);\n  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);",
  "  bool hud = aX.x > 0.5 && aX.x < 1.5;           // explore: the title block\n"
  "  vCol = vec4(aC.rgb, aC.a * ((aM.w > 0.5 && aM.w < 1.5) ? 1.0 : a) * k * cineK * (hud ? 1.0 - 0.55 * camAmt : 1.0));\n"
  "  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * (hud ? inverse(CAM) : mat4(1.0)) * vec4(pos, 1.0);"),
]

GLSL_CAMSPEC += [
 ("      if (svdK > 0.0) { p.xy = mix(p.xy, W(LE[i].xy, 0.0).xy, svdK); }",
  "      if (svdK > 0.0) { p.xy = mix(p.xy, W(LE[i].xy, 0.0).xy, svdK); }\n"
  "      if (rankZ > 0.0) p.z += rankZ * 1.4 * LM[i].w * cl((t_ - TP) / 6.0);       // explore: rank as height, rising as PageRank converges"),
]

GEN_CAMSPEC += [
 ("        <field name='toff' type='SFTime' accessType='inputOutput' value='0'/>\"",
  "        <field name='toff' type='SFTime' accessType='inputOutput' value='0'/>\\n        <field name='eyeX' type='SFTime' accessType='inputOutput' value='1'/>\""),
 ('w("    <TimeSensor DEF=\'Cinema\' enabled=\'false\' cycleInterval=\'1\' loop=\'false\'/>")',
  'w("    <TimeSensor DEF=\'Cinema\' enabled=\'false\' cycleInterval=\'1\' loop=\'false\'/>")\n'
  'w("    <!-- explore: the stereo eye for stereo pages (1 = centre), ROUTEd to every shader\'s eyeX -->")\n'
  'w("    <TimeSensor DEF=\'Eye\' enabled=\'false\' cycleInterval=\'1\' loop=\'false\'/>")'),
 ("    for n in sorted(set(shader_names)): w(f\"    <ROUTE fromNode='Seek' fromField='cycleInterval' toNode='{n}' toField='toff'/>\")",
  "    for n in sorted(set(shader_names)): w(f\"    <ROUTE fromNode='Seek' fromField='cycleInterval' toNode='{n}' toField='toff'/>\")\n"
  "    for n in sorted(set(shader_names)): w(f\"    <ROUTE fromNode='Eye' fromField='cycleInterval' toNode='{n}' toField='eyeX'/>\")"),
]

def camera_glsl(moves, pivots):
    """GLSL lines for camera(): a legacy move turns the set (yaw, pitch, push about a pivot); a SHOT is a look-at (eye, target: GLSL vec3
    expressions that may use u, the shot's progress, and HCW, RINGW, TENSORW, STONEW); every move has a weight k, and the weights blend"""
    out = []
    for c in moves:
        if "eye" in c:
            out.append(f"  k = {c['k']}; u = {c.get('u', '0.0')}; eyeOff += k * (({c['eye']}) - E0); tgtOff += k * ({c['target']}); w += k;   // {c['name']}")
        else:
            P = pivots[c["pivot"]]
            out.append(f"  k = {c['k']}; yaw += {c['yaw']:.4f} * k; pitch += {c['pitch']:.4f} * k; push += {c.get('push', 0.0):.4f} * k; "
                       f"piv += k * vec3({P[0]:.4f}, {P[1]:.4f}, {P[2]:.4f}); w += k;   // {c['name']}")
    return "\n".join(out)
