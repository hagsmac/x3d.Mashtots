#!/usr/bin/env python3
"""Mashtots Landing (v7) as X3D 4.0 in the Gobbler-3 style: one TimeSensor elapsedTime `phase` drives every shader; no Script node.

Fork of the approved slide-1 port (work/mashtots-slide1-FROZEN). The numbers are the ORIGINAL JavaScript's: extract_landing_data.js runs
the Landing's own math (attention heads, Fiedler vector, PageRank, message passing, SVD, k-means, DFT, seed-405 flights, stars) in Node and
this script bakes the result. Run:  node extract_landing_data.js && python3 make_landing.py [--freeze SEC --out F --cam X Y Z]
"""
import json, math, os, sys, argparse
from PIL import Image, ImageDraw, ImageFont
from landing_glsl import lib
from landing_text import Atlas, SC
import timeline

ap = argparse.ArgumentParser()
ap.add_argument("--freeze", type=float, help="write a still frame at this REAL time (clock unrouted)")
ap.add_argument("--act", type=float, help="like --freeze, but give the deck's act time (first moment the warp reaches it)")
ap.add_argument("--out", default="mashtots-landing.x3d")
ap.add_argument("--cam", nargs=3, type=float)
ARGS = ap.parse_args()

D = json.load(open("scratch/landing.json", encoding="utf-8"))
N = 36
CYCLE = D["CYCLE"]
P, EMB, FIED, SVDXY, KM, STARS, MOTES = D["P"], D["EMB"], D["FIED"], D["SVDXY"], D["KM"], D["STARS"], D["motes"]
DATA = D["DATA"]
PRAYER_DUR, NUMERALS_DUR, SHIRA_DUR, FINALE_BARS = 17.0, 12.0, 10.0, 20
SEGS, CYCLE_REAL = timeline.build(D, PRAYER_DUR, NUMERALS_DUR, SHIRA_DUR, FINALE_BARS)
_n, _rb, _sa, _srt = timeline.glsl_arrays(SEGS)
if ARGS.act is not None: ARGS.freeze = timeline.real_of_act(SEGS, ARGS.act)
LET = "".join(d[0] for d in DATA)
NSA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts/notoserifarmenian/NotoSerifArmenian[wdth,wght].ttf")     # the deck uses Noto Serif Armenian (Google Fonts, OFL)

# ---------------- constants shared with the GLSL ----------------
CONSTS = {k: D[k] for k in ("CYCLE", "T1", "TL", "TT", "TC", "TW2", "TS2", "TB2", "TSP", "TP", "TA", "TD", "TD2", "TF", "TPC", "TSV", "TSV2", "TH", "T2", "T3")}
CONSTS.update(BEGIN=D["begin"], FLIGHT=D["flight"], FLIGHTR=D["flightR"], PACE=D["S"], HCX=D["HC"]["x"], HCY=D["HC"]["y"], HR=D["R"], HHH=D["HH"], HF=D["F"], RG=D["RG"])
def _hold(name): return timeline.hold_start(SEGS, name)
NUM0, _nd = _hold("numerals"); NUM1 = NUM0 + _nd
SHI0, _sd = _hold("shirakatsi"); SHI1 = SHI0 + _sd
PRA0, _pd = _hold("prayer"); PRA1 = PRA0 + _pd
FIN0, _fd = _hold("finale"); FIN1 = FIN0 + _fd
BEAT, BAR = 60.0 / timeline.BPM, timeline.BAR
CONSTS.update(NUM0=NUM0, NUM1=NUM1, SHI0=SHI0, SHI1=SHI1, FIN0=FIN0, FIN1=FIN1, ORG0=FIN0 + 10 * BAR, ORG1=FIN0 + 16 * BAR, BEAT=BEAT, BAR=BAR)
_l2, _l2d = _hold("line2"); COL0 = _l2 + 0.2; COL1 = CYCLE_REAL - 0.2
CONSTS.update(COL0=COL0, COL1=COL1)
CONSTS.update(NSEG=str(_n), NSEG1=str(_n + 1), RB=_rb, SA=_sa, SRT=_srt, CYCLER=CYCLE_REAL)
LIB = lib(CONSTS)
BZ, KZ = -6.6, (15 + 6.6) / 15                 # backdrop plane behind the helix, scaled so that it reads 1:1 from the slide camera
FOV = 2 * math.atan(5.4 / 15)

# ---------------- glyph atlas: white glyphs, alpha only, tinted per letter in the shader ----------------
G = 192
os.makedirs("glyphs", exist_ok=True)

def pen_time(alpha_img):
    """calligraphic ink order: geodesic distance inside the glyph from where a pen would touch down (upper left), 0..1 in the red channel"""
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    a = np.asarray(alpha_img) > 60; ys, xs = np.nonzero(a)
    if len(ys) == 0: return np.zeros(a.shape, dtype=np.uint8)
    idx = -np.ones(a.shape, dtype=np.int64); idx[ys, xs] = np.arange(len(ys))
    rows, cols, wts = [], [], []
    for dy, dx, w in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.414), (1, -1, 1.414)):
        y2, x2 = ys + dy, xs + dx; ok = (y2 >= 0) & (y2 < a.shape[0]) & (x2 >= 0) & (x2 < a.shape[1])
        ok[ok] &= a[y2[ok], x2[ok]]
        i0, i1 = idx[ys[ok], xs[ok]], idx[y2[ok], x2[ok]]
        rows += [i0, i1]; cols += [i1, i0]; wts += [np.full(len(i0), w)] * 2
    g = coo_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(len(ys), len(ys))).tocsr()
    start = int(np.argmin(ys * 1.0 + xs * 0.35))
    dist = dijkstra(g, directed=False, indices=start)
    dist[~np.isfinite(dist)] = np.nanmax(dist[np.isfinite(dist)])        # a stray island is inked last
    out = np.zeros(a.shape, dtype=np.uint8); out[ys, xs] = np.round(255 * dist / max(dist.max(), 1e-6)).astype(np.uint8)
    return out


# ---- the four numeral equations of the deck and the letters each one lights (real-time windows inside the numerals hold) ----
def to_arm(n):
    out = ""
    for pw in (3, 2, 1, 0):
        d = (n // 10 ** pw) % 10
        if d: out += LET[pw * 9 + d - 1]
    return out
EQS = [(405, "այբուբենի տարեթիվը · the year of the alphabet"), (1512, "առաջին տպագիր գիրքը · the first printed book"), (2026, "այս երեկո · tonight"), (1475, "թուին Հայոց · tonight, in the Armenian era")]
EQ_T = [NUM0 + 3.0 + 1.9 * k for k in range(4)]
_conds = []
for k, (n, _) in enumerate(EQS):
    idxs = [LET.index(ch) for ch in to_arm(n)]
    t0, t1 = EQ_T[k], EQ_T[k] + 1.9
    _conds.append("  if (T_ >= %.3f && T_ < %.3f && (%s)) h = max(h, cl((T_ - %.3f) / 0.3) * (1.0 - cl((T_ - (%.3f - 0.3)) / 0.3)));" % (t0, t1, " || ".join(f"i == {j}" for j in idxs), t0, t1))
NUMHI_GLSL = "float numHi(int i){ float h = 0.0;\n" + "\n".join(_conds) + "\n  return h; }"

def build_atlas(path, wght):
    from fontTools.ttLib import TTFont
    ft = ImageFont.truetype(NSA, 96); ft.set_variation_by_axes([wght, 100])
    hh = TTFont(NSA)["hhea"]; asc_em = hh.ascent / (hh.ascent - hh.descent)                 # canvas 'middle' = the middle of the em square
    atlas = Image.new("RGBA", (6 * G, 7 * G), (255, 255, 255, 0))
    for i, ch in enumerate(LET + ","):
        tile = Image.new("L", (G, G), 0)
        ImageDraw.Draw(tile).text((G / 2, G / 2 + (asc_em - 0.5) * 96), ch, font=ft, fill=255, anchor="ms")
        tm = Image.fromarray(pen_time(tile))
        rgba = Image.merge("RGBA", (tm, Image.new("L", (G, G), 255), Image.new("L", (G, G), 255), tile))      # R = ink time, A = glyph
        atlas.paste(rgba, ((i % 6) * G, (i // 6) * G))
    atlas.save(path, optimize=True)
build_atlas("glyphs/atlas_white.png", 300)            # the letters (deck: weight 300)
build_atlas("glyphs/atlas_white_w.png", 400)          # the written sentence (deck: weight 400)

# ---------------- baked data as uniform arrays ----------------
def f(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s
def mf4(rows): return ", ".join(" ".join(f(x) for x in r) for r in rows)
LA = [(p["sx"], p["sy"], p["tx"], p["ty"]) for p in P]
LB = [(p["c1"]["x"], p["c1"]["y"], p["c2"]["x"], p["c2"]["y"]) for p in P]
LC = [(p["t0"], p["r0"], p["ph"], EMB[i]["c"]) for i, p in enumerate(P)]
def kmcode(i): return sum(KM[j]["assign"][i] * 4 ** j for j in range(7))
LD = [(EMB[i]["x"], EMB[i]["y"], FIED[i], kmcode(i)) for i in range(N)]
LE = [(SVDXY[i]["x"], SVDXY[i]["y"], 0, 0) for i in range(N)]
def lfields():
    return "\n".join(f"        <field name='{n}' type='MFVec4f' accessType='inputOutput' value='{mf4(r)}'/>" for n, r in (("LA", LA), ("LB", LB), ("LC", LC), ("LD", LD), ("LE", LE)))
PH = f"{ARGS.freeze or 0:.4f}"
INTRO_DEFAULT = "60" if ARGS.freeze is not None else "0"      # stills: 60 s into the one-shot clock, so the titles are up
def phase_field(): return f"        <field name='etime' type='SFTime' accessType='inputOutput' value='{PH}'/>\n        <field name='toff' type='SFTime' accessType='inputOutput' value='0'/>"

HEAD = "#version 300 es\nprecision highp float;\nprecision highp int;\n"
HEAD_NONE = ""
VERT_IN = "uniform mat4 x3d_ProjectionMatrix;\nuniform mat4 x3d_ModelViewMatrix;\nin vec4 x3d_Vertex;\n"
COLLAPSE = " if (vCol.a < 0.003) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);"          # an invisible element is pushed outside the clip volume: no rasterising, no fragments
def collapse_invisible(vs):
    if "out vec4 vCol" not in vs or "gl_Position" not in vs: return vs
    i = vs.rindex("gl_Position"); j = vs.index(";", i) + 1
    return vs[:j] + COLLAPSE + vs[j:]
import re as _re
def prune_letter_fields(fields, vs):
    """drop the five 36-vec4 letter arrays from shaders that never read them (X_ITE uploads user fields on every draw)"""
    used = vs.count("lstate(") > LIB.count("lstate(") or any(vs.count(n + "[") > LIB.count(n + "[") for n in ("LA", "LB", "LC", "LD", "LE"))
    if used: return fields
    return "\n".join(l for l in fields.split("\n") if not _re.search(r"<field name='L[A-E]' ", l))
def shader(name, fields, vs, fs):
    vs = collapse_invisible(vs)
    fields = prune_letter_fields(fields, vs)
    return (f"      <ComposedShader DEF='{name}' language='GLSL'>\n{phase_field()}\n{fields}\n"
            f"        <ShaderPart type='VERTEX'><![CDATA[data:x-shader/x-vertex,{HEAD}{vs}]]></ShaderPart>\n"
            f"        <ShaderPart type='FRAGMENT'><![CDATA[data:x-shader/x-fragment,{HEAD}{fs}]]></ShaderPart>\n      </ComposedShader>\n")
def sfnode_tex(name, url, nearest=False):
    tp = "<TextureProperties magnificationFilter='NEAREST_PIXEL' minificationFilter='NEAREST_PIXEL' generateMipMaps='false' boundaryModeS='CLAMP_TO_EDGE' boundaryModeT='CLAMP_TO_EDGE'/>" if nearest else ""
    return f"        <field name='{name}' type='SFNode' accessType='inputOutput'><ImageTexture url='&quot;{url}&quot;'>{tp}</ImageTexture></field>"

shapes = []          # (comment, xml)
SHADERS = ["BackdropShader", "LetterShader", "LabelShader"]
def add(comment, xml): shapes.append((comment, xml))
def quad_mesh(corners_per_item, n_items, extra_attrs, coord_fn):
    pass

# =====================================================================================================================
# 1. backdrop: ground, the framed mural, the veil that falls over it, the light inside the stone
# =====================================================================================================================
BD_VS = LIB + VERT_IN + r"""
out vec2 vP; out float vVeil; out float vGlow; out float vDrift; out vec3 vRing;
void main(){
  tl();
  float t = t_;
  vP = vec2(x3d_Vertex.x / (0.01 * @KZ@) + 960.0, 540.0 - x3d_Vertex.y / (0.01 * @KZ@));
  float outK = cl((t - BEGIN + 0.8) / 1.2) * (1.0 - cl((t - T1 + 1.2) / 1.6)), backK = cl((t - T2 + 0.4) / 1.2) * (1.0 - cl((t - T3 - 0.2) / 1.2));
  vVeil = max(max(veil, finK), colK * 0.86); vGlow = (0.12 + 0.06 * sin(T_ * 0.7) + max(outK, backK) * 0.3) * (1.0 - veil * 0.7) + 0.07 * kick * finK;
  // the stone as a Chladni plate: while letters leave (or come home) it rings through their modes (n, m) = (column + 1, row + 1); idle, it breathes
  float idxF = outK > 0.0 ? (t - BEGIN) / 0.07 : backK > 0.0 ? 35.0 - (t - T2) / 0.07 : T_ * 0.4;
  vRing = vec3(clamp(max(outK, backK), 0.0, 1.0), idxF, 1.0 - veil);
  vDrift = 0.5 - 0.5 * cos(6.2831853 * T_ / (CYCLER / 4.0));
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * x3d_Vertex;
}
""".replace("@KZ@", repr(KZ))
BD_FS = r"""
uniform sampler2D mural;
in vec2 vP; in float vVeil; in float vGlow; in float vDrift; in vec3 vRing;
out vec4 x3d_FragColor;
const vec3 GROUND = vec3(0.10196, 0.09804, 0.09804), PAPER = vec3(0.9529, 0.9490, 0.9490), TEAL = vec3(0.78824, 0.93725, 0.91373);
float h2(vec2 p){ vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
float chladni(vec2 p, float idx){
  float i = mod(floor(idx), 36.0), n = mod(i, 9.0) + 1.0, m = floor(i / 9.0) + 1.0;
  float f = (n == m) ? cos(n * 3.14159265 * p.x) * cos(m * 3.14159265 * p.y) : cos(n * 3.14159265 * p.x) * cos(m * 3.14159265 * p.y) - cos(m * 3.14159265 * p.x) * cos(n * 3.14159265 * p.y);
  return exp(-pow(f / 0.16, 2.0));                                     // sand gathers where the plate does not move
}
void main(){
  vec3 col = GROUND;
  vec2 p = vP;
  // the plate: a cream frame (14 px) around the mural, left 260 top 88, 1400 wide
  vec2 lo = vec2(260.0, 88.0), hi = vec2(1660.0, 88.0 + 483.6);
  if (p.x >= lo.x && p.x <= hi.x && p.y >= lo.y && p.y <= hi.y) {
    col = PAPER * 0.96;
    vec2 q = p - (lo + 14.0), sz = vec2(1372.0, 455.6);
    if (q.x >= 0.0 && q.y >= 0.0 && q.x <= sz.x && q.y <= sz.y) {
      vec2 uv = q / sz;                                                // top-origin texture rows (see README)
      float s = 1.0 + 0.025 * vDrift;                                  // the slow drift of the fresco
      uv = (uv - 0.5) / s + 0.5 + vec2(6.0, -4.0) * vDrift / sz;
      col = texture(mural, clamp(uv, 0.0, 1.0)).rgb;
    }
    // the veil falls over the plate while the helix is up
    col = mix(col, GROUND, 0.82 * vVeil);
  }
  // sand figure on the stone
  { vec2 q = (p - vec2(686.0, 284.0)) / vec2(137.0, 260.0);
    if (q.x >= 0.0 && q.x <= 1.0 && q.y >= 0.0 && q.y <= 1.0) {
      float fr = fract(vRing.y), sd = mix(chladni(q, vRing.y), chladni(q, vRing.y + 1.0), fr);
      float amp = (0.55 * vRing.x + 0.10 * (1.0 - vRing.x)) * vRing.z;
      col = mix(col, TEAL, sd * amp * 0.8);
    } }
  // the light inside the stone
  vec2 sc = vec2(686.0 + 137.0 / 2.0, 284.0 + 260.0 / 2.0); float gr = 260.0 * 1.1;
  float r = length(p - sc); float ga = vGlow * clamp((gr - r) / (gr - 10.0), 0.0, 1.0);
  col = mix(col, TEAL, ga);
  col += (h2(gl_FragCoord.xy) - 0.5) * 0.008;
  x3d_FragColor = vec4(col, 1.0);
}
"""
def backdrop():
    x0, x1, y0, y1 = -400, 2320, -300, 1380
    pts = " ".join(f"{f((x - 960) * 0.01 * KZ)} {f((540 - y) * 0.01 * KZ)} {BZ}" for x, y in ((x0, y1), (x1, y1), (x1, y0), (x0, y0)))
    sh = shader("BackdropShader", sfnode_tex("mural", "assets_src/mural.jpg"), BD_VS, BD_FS)
    add("backdrop: ground, framed mural with veil, stone light",
        f"    <Shape><Appearance>\n      <Material diffuseColor='0.1 0.1 0.1'/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet coordIndex='0 1 2 3 -1'><Coordinate point='{pts}'/></IndexedFaceSet></Shape>")

# =====================================================================================================================
# 2. letters: glyph + bloom + comet-trail copies, all in one mesh
# =====================================================================================================================
GHOSTS, LAG = 5, 0.055
LET_VS = LIB + VERT_IN + r"""
in vec4 aK;                       // letter index, ghost index, kind (0 glyph, 1 bloom, 2 trail copy)
uniform sampler2D ATT;            // 36 x 36 attention rows, tile 0 = the three heads averaged, normalised by the row maximum
out vec2 vUV; out vec4 vCol; out vec2 vQ; out float vKind;
const vec3 CLS0 = vec3(0.78824, 0.93725, 0.91373), CLS1 = vec3(0.88235, 0.67843, 0.4), CLS2 = vec3(0.95294, 0.94902, 0.94902), CLS3 = vec3(0.76078, 0.55294, 0.25490);
vec3 clsCol(int c){ return c == 0 ? CLS0 : c == 1 ? CLS1 : c == 2 ? CLS2 : CLS3; }
@NUMHI@
void main(){
  tl();
  int i = int(aK.x); float g = aK.y, kind = aK.z;
  float t = t_;
  Ls L = lstate(i, t - g * @LAG@);
  float pr = L.pr; float st = L.st;
  bool moving = st == 1.0 || st == 3.0;
  float ph = LC[i].z;
  float T = T_;
  // size in em px
  float size;
  if (st == 0.0) size = 20.0; else size = (pr < 0.5 ? mix(20.0, 46.0, ease(pr * 2.0)) : mix(46.0, 27.0, ease((pr - 0.5) * 2.0))) * (inHelix ? mix(1.0, 1.45 * L.s, veil) : 1.0);
  vec3 col = mix(TEAL, pr < 0.6 ? GOLD : mix(GOLD, DEEP, (pr - 0.6) / 0.4), cl(pr / 0.6));
  float breathe = moving ? 1.0 : 0.82 + 0.18 * (0.5 + 0.5 * sin(T * 1.1 + ph));
  float alpha = min(1.0, pr * 6.0 + 0.2) * breathe;
  bool isSpot = float(i) == spot;
  if (isSpot) { size *= 1.9; col = TEAL; alpha = 1.0; }
  else if (spot >= 0.0) alpha *= 0.55 + 0.45 * texelFetch(ATT, ivec2(i, int(spot)), 0).r;
  if (inHelix) alpha *= mix(1.0, 0.55 + 0.45 * cl((L.zpx + HR) / (2.0 * HR)), veil) * (1.0 - 0.3 * shrink);
  if (spaceK > 0.0) { col = mix(col, clsCol(int(LC[i].w)), spaceK * 0.85); alpha = min(1.0, alpha * mix(1.0, 1.3, spaceK)); }
  if (svdK > 0.0 && svdJ >= 0.0) { int code = int(LD[i].w); int a = (code >> (2 * int(svdJ))) & 3; col = mix(col, clsCol(a), svdK * 0.85); }
  float bloom = moving ? 0.45 * sin(PI * pr) : (isSpot ? 0.35 : 0.10 * breathe);
  if (numK > 0.0) { float hi = numHi(i); size *= 1.0 + 0.55 * hi * numK; col = mix(col, PAPER, hi * numK * 0.8); alpha = mix(alpha, 1.0, hi * numK); bloom += 0.3 * hi * numK; }
  if (shiK > 0.0) alpha *= 1.0 - 0.8 * shiK;
  if (finK > 0.0) { size *= 1.0 + 0.45 * finK + 0.10 * kick * finK; col = mix(col, clsCol(int(LC[i].w)), orgK * finK * 0.9); alpha = mix(alpha, 1.0, 0.6 * finK) * (1.0 - 0.8 * finDim * finK); bloom += 0.35 * kick * finK; }
  vec2 cn = x3d_Vertex.xy;          // corner, -1 or 1
  vKind = kind; vQ = cn;
  float half_ = size;               // quad half-size in px = em (tile = 2 em)
  if (st == 0.0) { // at the stone: the light sweeping across it
    float sweep = mod(T * 150.0, 137.0 + 260.0 + 600.0) - 300.0, dist = (LA[i].x - 686.0) + (LA[i].y - 284.0), boost = cl(1.0 - abs(dist - sweep) / 60.0);
    col = mix(TEAL, PAPER, boost); alpha = 0.18 + 0.1 * sin(T * 1.3 + ph) + 0.5 * boost; bloom = 0.0;
  }
  if (kind < 0.5) { vCol = vec4(col, alpha); }
  else if (kind < 1.5) { vCol = vec4(col, bloom); half_ = size * 1.6; }
  else {   // trail copies exist only while the letter is moving
    float edge = min(pr, 1.0 - pr); float m = moving ? smoothstep(0.0, 0.06, edge) : 0.0;
    float fade = 0.5 * pow(1.0 - g / 6.0, 1.6);
    vCol = vec4(col, alpha * fade * m);
  }
  vec2 cell = vec2(mod(float(i), 6.0), floor(float(i) / 6.0));
  vUV = (cell + vec2(0.5 + 0.49 * cn.x, 0.5 - 0.49 * cn.y)) / vec2(6.0, 7.0);
  vec3 pos = L.pos + vec3(cn * half_ * 0.01, -g * 0.002);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
""".replace("@LAG@", repr(LAG)).replace("@NUMHI@", NUMHI_GLSL)
LET_FS = r"""
uniform sampler2D atlas;
in vec2 vUV; in vec4 vCol; in vec2 vQ; in float vKind;
out vec4 x3d_FragColor;
void main(){
  if (vKind > 0.5 && vKind < 1.5) { float a = vCol.a * max(0.0, 1.0 - length(vQ)); if (a < 0.003) discard; x3d_FragColor = vec4(vCol.rgb, a); return; }
  float a = texture(atlas, vUV).a * vCol.a;
  if (a < 0.01) discard;
  x3d_FragColor = vec4(vCol.rgb, a);
}
"""
def letters():
    coords, attrs, idx = [], [], []
    order = []      # bloom first, then trail copies (far to near), then glyphs on top
    for i in range(N): order.append((i, 0, 1))
    for g in range(GHOSTS, 0, -1):
        for i in range(N): order.append((i, g, 2))
    for i in range(N): order.append((i, 0, 0))
    for (i, g, kind) in order:
        base = len(coords)
        for cx, cy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            coords.append(f"{cx} {cy} 0"); attrs.append(f"{i} {g} {kind} 0")
        idx.append(f"{base} {base+1} {base+2} {base+3} -1")
    sh = shader("LetterShader", lfields() + "\n" + sfnode_tex("atlas", "glyphs/atlas_white.png") + "\n" + sfnode_tex("ATT", "glyphs/att.png", nearest=True), LET_VS, LET_FS)
    add("the 36 letters: bloom, comet-trail copies and glyphs in one mesh; every position comes from lstate()",
        f"    <Shape bboxCenter='0 0 -2' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n"
        f"      <FloatVertexAttribute name='aK' numComponents='4' value='{' '.join(attrs)}'/></IndexedFaceSet></Shape>")

# ---------------- attention data texture (36 x 36 per tile, 8 bit) ----------------
def write_att():
    A = D["A"]; M, RM = A["mean"], A["rowMax"]
    tiles = [[[M[i][j] / RM[i] for j in range(N)] for i in range(N)]]
    w = 36 * len(tiles); im = Image.new("L", (w, 36))
    for tI, tile in enumerate(tiles):
        for i in range(N):
            for j in range(N): im.putpixel((tI * 36 + j, i), int(round(255 * max(0.0, min(1.0, tile[i][j])))))
    im.save("glyphs/att.png")

# =====================================================================================================================
# 3. labels: every piece of text is a strip of the text atlas on a quad; one mesh, one shader
# =====================================================================================================================
ATL = Atlas(4096)
LABELS = []
def NEUTRAL(v): return (v / 255, v / 255, v / 255)
C_GOLD, C_DEEP, C_TEAL, C_PAPER = (225/255, 173/255, 102/255), (194/255, 141/255, 65/255), (201/255, 239/255, 232/255), (243/255, 242/255, 242/255)
C_ACC, C_ACC3, C_ACC4 = (205/255, 150/255, 70/255), (240/255, 205/255, 150/255), (225/255, 173/255, 102/255)
INTRO = 100000.0                                   # seconds per cycle of the one-shot clock (the titles rise once, then stay)
MODES = dict(none=0, veil=1, space=2, web=3, spec=4, poin=5, svd=6)
def label(key, x, y, col=C_PAPER, a=1.0, ts=0.0, te=None, fi=0.01, fo=0.01, mode="none", anchor=-1, rise=0.0, align="l", baseline=False, clock=0, glow=0.0, scale=1.0, ease_in=False, grow=0, wpx=None, hpx=None):
    """place strip `key` (already in ATL). x,y = left/top of the strip in deck px (or its baseline if baseline=True; align c/r shifts by the width).
    anchor >= 0: x,y become an offset in px from that letter's position. clock 1 = the one-shot intro clock (seconds since load)."""
    if te is None: te = CYCLE if clock == 0 else 1e9
    w, h, asc = ATL.rects[key][4], ATL.rects[key][5], ATL.rects[key][6]
    if baseline: y -= asc
    if align == "c": x -= w * scale / 2
    elif align == "r": x -= w * scale
    if wpx is not None: w = wpx / scale
    if hpx is not None: h = hpx / scale
    LABELS.append(dict(grow=grow, key=key, x=x, y=y, w=w * scale, h=h * scale, col=col, a=a, ts=ts, te=te, fi=fi, fo=fo, mode=MODES[mode], anchor=anchor, rise=rise, clock=clock, ease=1 if ease_in else 0))

LAB_VS = LIB + VERT_IN + r"""
uniform float itime;                               // seconds since load, one shot: the titles rise once and stay
in vec4 aR; in vec4 aP; in vec4 aC; in vec4 aW; in vec4 aM; in vec4 aX;
out vec2 vUV; out vec4 vCol;
void main(){
  tl();
  float clk = aX.x < 0.5 ? t_ : aX.x < 1.5 ? itime : T_;
  float ts = aW.x, te = aW.y, fi = aW.z, fo = aW.w;
  float a = (clk >= ts && clk <= te) ? cl((clk - ts) / fi) * (1.0 - cl((clk - (te - fo)) / fo)) : 0.0;
  if (aX.y > 0.5) a = 1.0 - pow(1.0 - a, 3.0);                          // eased rise (the deck's cubic-bezier(.2,.8,.2,1))
  float m = aM.x;
  float k = m < 0.5 ? 1.0 : m < 1.5 ? mapK : m < 2.5 ? spaceK : m < 3.5 ? webK : m < 4.5 ? specK : m < 5.5 ? poinK : svdK;
  vec2 c = x3d_Vertex.xy;                           // 0..1, (0,0) = top-left
  vec2 px = aP.xy + c * ((aM.w > 0.5 && aM.w < 1.5) ? vec2(aP.z * a, aP.w) : aP.zw);
  if (aM.w > 1.5) px.x += aM.z * (clk - aW.x);                              // scroll mode: aM.z is a speed in px per second
  vec3 pos;
  if (aM.y >= 0.0) {
    Ls L = lstate(int(aM.y), t_);
    vec2 lp = vec2(L.pos.x * 100.0 + 960.0, 540.0 - L.pos.y * 100.0), dv = lp - vec2(960.0, 345.0);
    vec2 rad = dv / max(length(dv), 1.0) * aX.z;                                  // radial labels (PageRank leaders): outward from the ring centre
    vec2 off = px + rad + vec2((aX.z > 0.0 && dv.x < 0.0) ? -aX.w : 0.0, 0.0);
    pos = L.pos + vec3(off.x * 0.01, -off.y * 0.01, 0.02);
  }
  else pos = W(px + vec2(0.0, aM.w > 1.5 ? 0.0 : aM.z * (1.0 - a)), 0.03);
  vUV = vec2(mix(aR.x, aR.z, c.x), mix(aR.y, aR.w, c.y));
  vCol = vec4(aC.rgb, aC.a * ((aM.w > 0.5 && aM.w < 1.5) ? 1.0 : a) * k);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
LAB_FS = r"""
uniform sampler2D tex;
in vec2 vUV; in vec4 vCol;
out vec4 x3d_FragColor;
void main(){
  float a = texture(tex, vUV).a * vCol.a;
  if (a < 0.004) discard;
  x3d_FragColor = vec4(vCol.rgb, a);
}
"""
def labels_mesh():
    if not LABELS: return
    atlas_w, atlas_h = ATL.build("glyphs/text_atlas.png")
    fields = lfields() + "\n" + sfnode_tex("tex", "glyphs/text_atlas.png") + f"\n        <field name='itime' type='SFTime' accessType='inputOutput' value='{INTRO_DEFAULT}'/>"
    CH = 280
    for ci in range(0, len(LABELS), CH):
        part = LABELS[ci:ci + CH]
        coords, A_R, A_P, A_C, A_W, A_M, A_X, idx = [], [], [], [], [], [], [], []
        for L in part:
            base = len(coords); u0, v0, u1, v1 = ATL.uv(L["key"])
            for cx, cy in ((0, 0), (1, 0), (1, 1), (0, 1)):
                coords.append(f"{cx} {cy} 0")
                A_R.append(f"{u0:.6f} {v0:.6f} {u1:.6f} {v1:.6f}"); A_P.append(f"{f(L['x'])} {f(L['y'])} {f(L['w'])} {f(L['h'])}")
                A_C.append(f"{f(L['col'][0])} {f(L['col'][1])} {f(L['col'][2])} {f(L['a'])}"); A_W.append(f"{f(L['ts'])} {f(min(L['te'], 1e8))} {f(L['fi'])} {f(L['fo'])}")
                A_M.append(f"{L['mode']} {L['anchor']} {f(L['rise'])} {L['grow']}"); A_X.append(f"{L['clock']} {L['ease']} {L.get('radial', 0)} {f(L['w'])}")
            idx.append(f"{base} {base+1} {base+2} {base+3} -1")
        if ci == 0: sh = shader("LabelShader", fields, LAB_VS, LAB_FS)
        else: sh = "      <ComposedShader USE='LabelShader'/>\n"
        attrs = "".join(f"      <FloatVertexAttribute name='{n}' numComponents='4' value='{' '.join(v)}'/>\n" for n, v in (("aR", A_R), ("aP", A_P), ("aC", A_C), ("aW", A_W), ("aM", A_M), ("aX", A_X)))
        add(f"labels {ci}..{ci + len(part)} of {len(LABELS)}: strips of the text atlas ({atlas_w} x {atlas_h})",
            f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
            f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n{attrs}    </IndexedFaceSet></Shape>")

def build_labels_A():
    ATL.add_image("solid", Image.new("L", (8, 8), 255))
    # the title block: rises once at 6.5 s / 7.4 s after load and stays (one-shot clock)
    ATL.add("h1", "Մաշտոց Համակարգ 2", 118, track=-0.01, wght=300)
    ATL.add("h1en", "Mashtots System 2", 52)
    ATL.add("p_hy", "Այբուբենը առաջին համակարգն էր։ Սա երկրորդն է։", 36, wght=300)
    ATL.add("p_en", "The alphabet was the first system. This is the second.", 34)
    ATL.add("p_loc", "Մատենադարան · Երևան · 2026", 24, track=0.08, upper=True)
    label("solid", 144, 675, col=C_PAPER, a=0.16, ts=6.1, fi=1.2, fo=1e9, clock=1, grow=1, wpx=1632, hpx=2, ease_in=True)
    label("h1", 144, 817, baseline=True, ts=6.5, fi=1.0, rise=14, clock=1, ease_in=True)
    w1 = ATL.size("h1")[0]
    label("h1en", 144 + w1 + 40, 817, col=NEUTRAL(165), baseline=True, ts=6.5, fi=1.0, rise=14, clock=1, ease_in=True)
    label("p_hy", 144, 896, baseline=True, ts=7.4, fi=1.0, rise=14, clock=1, ease_in=True)
    label("p_en", 144, 942, col=NEUTRAL(165), baseline=True, ts=7.4, fi=1.0, rise=14, clock=1, ease_in=True)
    label("p_loc", 1776, 896, col=C_ACC, baseline=True, align="r", ts=7.4, fi=1.0, rise=14, clock=1, ease_in=True)


# =====================================================================================================================
# 4. dust motes, landing ripples, spark bursts, the astronomer's globe
# =====================================================================================================================
def quads(n, attrs_fn, corners=((-1, -1), (1, -1), (1, 1), (-1, 1))):
    """n quads; attrs_fn(i, corner_index) -> dict name -> 4 numbers. Returns coord, index and attribute strings."""
    coords, idx, attrs = [], [], {}
    for i in range(n):
        base = len(coords)
        for ci, (cx, cy) in enumerate(corners):
            coords.append(f"{cx} {cy} 0")
            for k, v in attrs_fn(i, ci).items(): attrs.setdefault(k, []).append(" ".join(f(x) for x in v))
        idx.append(f"{base} {base+1} {base+2} {base+3} -1")
    return coords, idx, attrs
def attr_xml(attrs): return "".join(f"      <FloatVertexAttribute name='{k}' numComponents='4' value='{' '.join(v)}'/>\n" for k, v in attrs.items())
def fx_shape(name, comment, vs, fs, coords, idx, attrs, fields="", z_far=False, lines=False):
    sh = shader(name, lfields() + "\n" + fields, vs, fs)
    geo = (f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n{attr_xml(attrs)}    </IndexedFaceSet>")
    add(comment, f"    <Shape bboxCenter='0 0 -2' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n{geo}</Shape>")
    SHADERS.append(name)
POINT_FS = r"""
in vec4 vCol; in vec2 vQ; in float vMode;
out vec4 x3d_FragColor;
void main(){
  float r = length(vQ);
  float a = vCol.a;
  if (vMode < 0.5) a *= smoothstep(1.0, 0.55, r);                  // soft disc
  else if (vMode < 1.5) a *= max(0.0, 1.0 - r);                    // linear glow, like the deck's two-stop radial gradients
  else if (vMode < 2.5) { float age = vCol.a; a = 0.0; }
  if (a < 0.003) discard;
  x3d_FragColor = vec4(vCol.rgb, a);
}
"""

ORBIT_GLSL = """
vec3 orbitQ(float j, float ps, float rg){                                 // three tilted ellipses around the globe
  float a = rg * (1.10 + 0.13 * j), b = a * (0.93 - 0.11 * j), tilt = j < 0.5 ? 0.55 : (j < 1.5 ? -0.38 : 0.95), sp = j < 0.5 ? 0.0 : (j < 1.5 ? 1.2 : 2.4);
  vec3 q = vec3(a * cos(ps), 0.0, b * sin(ps));
  q = vec3(q.x, q.y * cos(tilt) - q.z * sin(tilt), q.y * sin(tilt) + q.z * cos(tilt));
  float c = cos(sp), s = sin(sp);
  return vec3(c * q.x + s * q.z, q.y, -s * q.x + c * q.z);
}
"""
def effects():
    # ---- dust motes (the deck's 70 drifting specks), behind the veil ----
    M = MOTES
    def at(i, ci):
        m = M[i]; cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]
        return {"aA": (m["x"], m["y"], m["s"], m["a"]), "aB": (m["r"], m["ph"], cx, cy)}
    coords, idx, attrs = quads(len(M), at)
    vs = LIB + VERT_IN + r"""
in vec4 aA; in vec4 aB;
out vec4 vCol; out vec2 vQ; out float vMode;
void main(){
  tl(); float t = t_;
  float y = -4.0 + mod(aA.y + 4.0 - 60.0 * aA.z * T_, 1080.0 + 8.0);
  float x = aA.x + 20.0 * (cos(aB.y) - cos(0.4 * T_ + aB.y));
  float a = aA.w * (0.6 + 0.4 * sin(0.9 * T_ + aB.y));
  if (x > 260.0 && x < 1660.0 && y > 88.0 && y < 572.0) a *= 1.0 - 0.82 * veil;
  vec2 cn = aB.zw; vQ = cn; vMode = 0.0; vCol = vec4(GOLD, a);
  vec3 pos = W(vec2(x, y) + cn * aB.x * 1.4, 0.0) * @KZ@; pos.z = @BZ@ + 0.05;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
""".replace("@KZ@", repr(KZ)).replace("@BZ@", repr(BZ))
    fx_shape("MoteShader", "dust motes", vs, HEAD_NONE + POINT_FS, coords, idx, attrs)

    # ---- ripples where each letter settles on the line ----
    def at(i, ci):
        cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]
        return {"aA": (i, cx, cy, 0)}
    coords, idx, attrs = quads(N, at)
    vs = LIB + VERT_IN + r"""
in vec4 aA;
out vec4 vCol; out vec2 vQ; out float vMode;
void main(){
  tl(); float t = t_;
  int i = int(aA.x); float age = (t - (LC[i].x + FLIGHT)) / 0.8;
  vec2 cn = aA.yz; vQ = cn * 60.0; vMode = 3.0;
  vCol = vec4(GOLD, (age >= 0.0 && age < 1.0 && t < T1 + 1.0) ? age : -1.0);     // age rides in alpha, the fragment shader draws the ring
  vec3 pos = W(LA[i].zw + cn * 60.0, 0.012);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    fs = r"""
in vec4 vCol; in vec2 vQ; in float vMode;
out vec4 x3d_FragColor;
void main(){
  float age = vCol.a; if (age < 0.0) discard;
  float d = abs(length(vQ) - (4.0 + 44.0 * age));
  float a = 0.55 * (1.0 - age) * smoothstep(1.6, 0.3, d);
  if (a < 0.003) discard;
  x3d_FragColor = vec4(vCol.rgb, a);
}
"""
    fx_shape("RippleShader", "ripples where the letters land", vs, fs, coords, idx, attrs)

    # ---- sparks: 22 per spotlit letter, thrown from its place in the helix ----
    import random
    rng = random.Random(405)
    SP = [[(rng.random() * 6.283, 40 + rng.random() * 110, .8 + rng.random() * 1.6) for _ in range(22)] for _ in range(N)]
    def at(i, ci):
        k, s = divmod(i, 22); a, v, r = SP[k][s]; cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]
        return {"aA": (k, cx, cy, r), "aB": (math.cos(a) * v, math.sin(a) * v - 20, 0, 0)}
    coords, idx, attrs = quads(N * 22, at)
    vs = LIB + VERT_IN + r"""
in vec4 aA; in vec4 aB;
out vec4 vCol; out vec2 vQ; out float vMode;
void main(){
  tl(); float t = t_;
  int k = int(aA.x); float ts = TT + float(k) * PACE, tau = t - ts, life = 1.0 - tau / 1.3;
  vec2 cn = aA.yz; vQ = cn; vMode = 0.0;
  bool on = tau >= 0.0 && life > 0.0;
  vCol = vec4(TEAL, on ? 0.8 * life : 0.0);
  float zpx; vec3 h = helix3(k, 0.0, ts, zpx);
  vec2 off = vec2(aB.x * (1.0 - exp(-0.9 * tau)) / 0.9, aB.y * tau + 15.0 * tau * tau);
  vec3 pos = h + vec3(off.x, -off.y, 0.0) * 0.01 + vec3(cn * aA.w * max(life, 0.0) * 1.6 * 0.01, 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    fx_shape("SparkShader", "sparks from the spotlit letter", vs, HEAD_NONE + POINT_FS, coords, idx, attrs)

    # ---- the astronomer's globe: meridians, parallels, ecliptic as lines; stars and the sun as soft points ----
    coords, idx = [], []
    def line(kind, a, b, n):
        base = len(coords)
        for k in range(n + 1):
            coords.append(f"{kind} {k / n:.5f} {f(a)}")        # line sets take no vertex attributes in the schema: the coordinate carries (kind, u, parameter)
        idx.append(" ".join(str(base + k) for k in range(n + 1)) + " -1")
    for m in range(8): line(0, m, 0, 40)
    for lat in (-60, -30, 0, 30, 60): line(1, lat, 0, 64)
    line(2, 0, 0, 72)
    vs = LIB + VERT_IN + r"""
out vec4 vCol;
const float EC = 23.4 / 180.0 * 3.14159265;
void main(){
  tl(); float t = t_;
  float rg = RG * (1.0 - 0.45 * shrink), rot = -T_ * 0.12;
  float kind = x3d_Vertex.x, u = x3d_Vertex.y, p = x3d_Vertex.z;
  vec3 q;
  if (kind < 0.5) { float ph = p / 8.0 * PI + rot, th = -PI / 2.0 + u * PI; q = vec3(rg * cos(th) * cos(ph), rg * sin(th), rg * cos(th) * sin(ph)); }
  else if (kind < 1.5) { float la = p / 180.0 * PI, r = rg * cos(la), ps = u * 6.2831853 + rot; q = vec3(r * cos(ps), rg * sin(la), r * sin(ps)); }
  else { float ps = u * 6.2831853 + rot; q = vec3(rg * cos(ps), rg * sin(ps) * sin(EC), rg * sin(ps) * cos(EC)); }
  float front = cl((-q.z + rg) / (2.0 * rg));
  vec3 col = kind < 1.5 ? GOLD : TEAL;
  float a = kind < 1.5 ? (0.045 + 0.07 * front) : (0.06 + 0.10 * front);
  vCol = vec4(col, a * veil);
  vec3 c = vec3((HC.x - 960.0) * 0.01, (540.0 - (HC.y + 108.0 * shrink)) * 0.01, -HR * 0.01);
  vec3 pos = c + vec3(q.x, -q.y, -q.z) * 0.01;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    fs = r"""
in vec4 vCol;
out vec4 x3d_FragColor;
void main(){ x3d_FragColor = vCol; }
"""
    sh = shader("GlobeLineShader", lfields(), vs, fs)
    add("the astronomer's globe: meridians, parallels, ecliptic",
        f"    <Shape bboxCenter='{(D['HC']['x']-960)*0.01:.2f} 1 -3' bboxSize='10 10 10'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("GlobeLineShader")

    # ---- the armillary: degree ticks on the ecliptic and the equator, the polar axis, the ecliptic pole and the precession circle (marching dashes), three orbits, constellations joined between the stars ----
    ac, ai = [], []
    def aline(pts):
        base = len(ac)
        for p in pts: ac.append(f"{f(p[0])} {f(p[1])} {f(p[2])}")
        ai.append(" ".join(str(base + k) for k in range(len(pts))) + " -1")
    for k in range(72):
        aline([(3, k / 72, 0), (3, k / 72, 1)]); aline([(4, k / 72, 0), (4, k / 72, 1)])
    aline([(5, 0, 0), (5, 0, 1)]); aline([(6, 0, 0), (6, 0, 1)])
    aline([(7, k / 96, 0) for k in range(97)])
    for j in range(3): aline([(8, k / 96, j) for k in range(97)])
    # constellations: six chains of four stars, each star joined to its nearest unused neighbour
    crng = random.Random(1475); used = set()
    for _ in range(6):
        cur = crng.choice([i for i in range(len(STARS)) if i not in used]); chain = [cur]; used.add(cur)
        for _k in range(3):
            c0 = STARS[chain[-1]]
            nxt = min((i for i in range(len(STARS)) if i not in used), key=lambda i: (STARS[i]["x"] - c0["x"]) ** 2 + (STARS[i]["y"] - c0["y"]) ** 2 + (STARS[i]["z"] - c0["z"]) ** 2)
            chain.append(nxt); used.add(nxt)
        aline([(10 + STARS[i]["x"], STARS[i]["y"], STARS[i]["z"]) for i in chain])
    avs = LIB + VERT_IN + ORBIT_GLSL + r"""
out vec4 vCol; out vec2 vD;
const float EC = 23.4 / 180.0 * 3.14159265;
void main(){
  tl(); float t = t_;
  float rg = RG * (1.0 - 0.45 * shrink), rot = -T_ * 0.12;
  vec3 v = x3d_Vertex.xyz; float kind = floor(v.x + 0.5), u = v.y, p = v.z;
  vec3 q = vec3(0.0), col = TEAL; float a = 0.0; vD = vec2(0.0);
  if (v.x > 5.0) {
    vec3 s = vec3(v.x - 10.0, v.y, v.z); float ph = atan(s.z, s.x) + rot, rr = length(s.xz);
    q = vec3(rg * rr * cos(ph), rg * s.y, rg * rr * sin(ph)); col = PAPER;
    float front = cl((-q.z + rg) / (2.0 * rg)); a = (0.2 + 0.4 * front) * (0.7 + 0.3 * sin(T_ * 0.9 + s.x * 7.0));
  } else if (kind == 3.0 || kind == 4.0) {
    float idx = floor(u * 72.0 + 0.5), major = mod(idx, 6.0) < 0.5 ? 1.0 : 0.0, rad = rg * (1.0 + p * (major > 0.5 ? 0.07 : 0.028)), ps = idx / 72.0 * 6.2831853 + rot;
    q = kind == 3.0 ? vec3(rad * cos(ps), rad * sin(ps) * sin(EC), rad * sin(ps) * cos(EC)) : vec3(rad * cos(ps), 0.0, rad * sin(ps));
    col = kind == 3.0 ? TEAL : GOLD; float front = cl((-q.z + rg) / (2.0 * rg)); a = (major > 0.5 ? 0.65 : 0.32) * (0.35 + 0.65 * front);
  } else if (kind == 5.0) { q = vec3(0.0, mix(-1.34, 1.34, p) * rg, 0.0); col = GOLD; a = 0.42; }
  else if (kind == 6.0) { q = vec3(0.0, cos(EC), -sin(EC)) * mix(-1.26, 1.26, p) * rg; a = 0.32; }
  else if (kind == 7.0) { float ps = u * 6.2831853; q = 1.26 * rg * vec3(sin(EC) * cos(ps), cos(EC), sin(EC) * sin(ps)); col = GOLD; a = 0.5; vD = vec2(40.0, u * 40.0 - T_ * 1.4); }
  else { q = orbitQ(p, u * 6.2831853, rg); float front = cl((-q.z + rg) / (2.0 * rg)); col = p < 0.5 ? GOLD : (p < 1.5 ? TEAL : PAPER); a = 0.22 + 0.3 * front; if (p > 1.5) vD = vec2(30.0, u * 30.0 + T_ * 0.5); }
  vCol = vec4(col, a * veil * (1.0 - 0.4 * hold_));
  vec3 c = vec3((HC.x - 960.0) * 0.01, (540.0 - (HC.y + 108.0 * shrink)) * 0.01, -HR * 0.01);
  vec3 pos = c + vec3(q.x, -q.y, -q.z) * 0.01;
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    afs = r"""
in vec4 vCol; in vec2 vD;
out vec4 x3d_FragColor;
void main(){ float m = vD.x > 0.0 ? step(0.45, fract(vD.y)) : 1.0; x3d_FragColor = vec4(vCol.rgb, vCol.a * m); }
"""
    sh = shader("ArmillaryShader", lfields(), avs, afs)
    add("the armillary: ticks, axes, precession circle, orbits, constellations",
        f"    <Shape bboxCenter='{(D['HC']['x']-960)*0.01:.2f} 1 -3' bboxSize='16 16 16'><Appearance alphaMode='BLEND'>\n      <LineProperties applied='true' linewidthScaleFactor='2'/><Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(ai)}'><Coordinate point='{', '.join(ac)}'/></IndexedLineSet></Shape>")
    SHADERS.append("ArmillaryShader")

    # ---- the helix as a double strand: the letters are threaded on the backbone; a second strand, rungs between them, light running up and down, the spotlit letter's stretch glowing ----
    hc, hi = [], []
    def hline(pts):
        base = len(hc)
        for p in pts: hc.append(f"{f(p[0])} {f(p[1])} {f(p[2])}")
        hi.append(" ".join(str(base + k) for k in range(len(pts))) + " -1")
    for st_ in (0, 1): hline([(0, -0.6 + k * 0.2, st_) for k in range(int(36.2 / 0.2) + 1)])
    for k in range(0, 72): hline([(1, k * 0.5, 0), (1, k * 0.5, 1)])
    hvs = LIB + VERT_IN + r"""
out vec4 vCol; out vec2 vD;
void main(){
  tl(); float t = t_;
  vec3 v = x3d_Vertex.xyz; float kind = v.x, s = v.y, st = v.z;
  float r = HR * (1.0 - 0.5 * shrink) * (st < 0.5 ? 1.0 : 0.93), hh = HHH * (1.0 - 0.5 * shrink), cy = HC.y + 108.0 * shrink;
  float a = s / 36.0 * PI * 8.0 + T_ * 0.22 + st * PI, X = r * cos(a), Z = r * sin(a), Y = (s / 35.0 - 0.5) * hh;
  vec3 pos = vec3((HC.x + X - 960.0) * 0.01, (540.0 - (cy + Y)) * 0.01, -(HR + Z) * 0.01);
  float front = cl((-Z + HR) / (2.0 * HR));
  float p1 = mod(T_ * 3.2, 52.0) - 8.0, p2 = 44.0 - mod(T_ * 2.1 + 17.0, 52.0);
  float glow = exp(-(s - p1) * (s - p1) / 2.5) + 0.7 * exp(-(s - p2) * (s - p2) / 2.5);
  float spotG = spot >= 0.0 ? exp(-(s - spot) * (s - spot) / 1.4) * (1.0 - 0.6 * spotK) : 0.0;
  float edge = smoothstep(-0.6, 0.6, s) * smoothstep(36.2, 34.8, s);
  float base = kind < 0.5 ? (st < 0.5 ? 0.9 : 0.5) : 0.24 + 0.1 * sin(T_ * 1.3 + s * 2.0);
  float al = (base * (0.3 + 0.7 * front) + (0.85 * glow + 1.0 * spotG) * (kind < 0.5 ? 1.0 : 0.8)) * edge;
  vec3 col = mix(GOLD, TEAL, clamp(glow + 0.4 * st, 0.0, 1.0)); if (spotG > 0.3) col = PAPER;
  vD = vec2(0.0);
  vCol = vec4(col, al * veil * (1.0 - spaceK) * (1.0 - webK) * (1.0 - 0.5 * max(numK, shiK)));
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    sh = shader("HelixStrandShader", lfields(), hvs, afs)
    add("the astronomer's helix as a double strand with running light",
        f"    <Shape bboxCenter='{(D['HC']['x']-960)*0.01:.2f} 1 -3' bboxSize='16 16 16'><Appearance alphaMode='BLEND'>\n      <LineProperties applied='true' linewidthScaleFactor='2'/><Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(hi)}'><Coordinate point='{', '.join(hc)}'/></IndexedLineSet></Shape>")
    SHADERS.append("HelixStrandShader")
    # stars + sun
    def at(i, ci):
        cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]
        if i < len(STARS): st = STARS[i]; return {"aA": (st["x"], st["y"], st["z"], st["tw"]), "aB": (st["s"], cx, cy, 0)}
        return {"aA": (0, 0, 0, 0), "aB": (-1 - (i - len(STARS)), cx, cy, 0)}            # two sun quads: glow, core; then 21 planet quads (aB.x <= -3)
    NPL = 21
    coords, idx, attrs = quads(len(STARS) + 2 + NPL, at)
    vs = LIB + VERT_IN + ORBIT_GLSL + r"""
in vec4 aA; in vec4 aB;
out vec4 vCol; out vec2 vQ; out float vMode;
const float EC = 23.4 / 180.0 * 3.14159265;
void main(){
  tl(); float t = t_;
  float rg = RG * (1.0 - 0.45 * shrink), rot = -T_ * 0.12;
  vec2 cn = aB.yz; vQ = cn;
  vec3 q; float rad, a; vec3 col = PAPER; vMode = 0.0;
  if (aB.x > 0.0) {
    float ph = atan(aA.z, aA.x) + rot, rr = length(aA.xz);
    q = vec3(rg * rr * cos(ph), rg * aA.y, rg * rr * sin(ph));
    float front = cl((-q.z + rg) / (2.0 * rg));
    a = (0.1 + 0.45 * (0.5 + 0.5 * sin(T_ * 1.7 + aA.w))) * veil * (0.35 + 0.65 * front);
    rad = aB.x * (0.6 + 0.6 * front) * 1.6;
  } else {
    float sp = T_ * 0.3 + rot;
    q = vec3(rg * cos(sp), rg * sin(sp) * sin(EC), rg * sin(sp) * cos(EC));
    if (aB.x < -2.5) {
      float id = -3.0 - aB.x, j = floor(id / 7.0 + 0.001), k = id - 7.0 * j;
      float w = 0.5 / pow(1.0 + 0.7 * j, 1.5), ps = T_ * w + 1.7 * j - 0.07 * k * (1.0 + 0.3 * j);
      q = orbitQ(j, ps, rg); float front = cl((-q.z + rg) / (2.0 * rg));
      a = (k < 0.5 ? 0.95 : 0.8 * (1.0 - k / 7.0)) * veil * (0.5 + 0.5 * front); rad = (k < 0.5 ? 9.5 : 6.5 - 0.7 * k) * (3.4 - j) / 2.4; col = j < 0.5 ? GOLD : (j < 1.5 ? TEAL : PAPER); vMode = k < 0.5 ? 1.0 : 0.0;
    } else if (aB.x > -1.5) { a = 0.7 * veil; rad = 26.0; col = GOLD; vMode = 1.0; } else { a = 0.95 * veil; rad = 3.0; }
  }
  vCol = vec4(col, a);
  vec3 c = vec3((HC.x - 960.0) * 0.01, (540.0 - (HC.y + 108.0 * shrink)) * 0.01, -HR * 0.01);
  vec3 pos = c + vec3(q.x, -q.y, -q.z) * 0.01 + vec3(cn * rad * 0.01, 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    fx_shape("StarShader", "stars and the sun on the globe", vs, HEAD_NONE + POINT_FS, coords, idx, attrs)


# =====================================================================================================================
# 5. the tour: card, attention arcs, ring, dashed line, stone grid, attention map
# =====================================================================================================================
def rect_vs(x0, y0, w, h, z, extra_out="", extra_body="", kill="false"):
    return LIB + VERT_IN + f"""
out vec2 vP; out float vA; {extra_out}
void main(){{
  tl(); vec2 c = x3d_Vertex.xy;
  vP = vec2({x0}, {y0}) + c * vec2({w}, {h});
  vA = 1.0;
  {extra_body}
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(vP, {z}), 1.0);
  if ({kill}) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
}}
"""
def rect_shape(name, comment, vs, fs, fields=""):
    coords, idx = "0 0 0 1 0 0 1 1 0 0 1 0", "0 1 2 3 -1"
    sh = shader(name, lfields() + "\n" + fields, vs, fs)
    add(comment, f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n    <IndexedFaceSet solid='false' coordIndex='{idx}'><Coordinate point='{coords}'/></IndexedFaceSet></Shape>")
    SHADERS.append(name)

def anneal_tile(sv):
    """Wcur / row max at softmax temperature tau(sv), sv in 0..1 along the cosine sweep, exactly the deck's formula."""
    A = D["A"]; tau = math.exp(math.log(0.12) + (math.log(3) - math.log(0.12)) * sv)
    out = []
    for i in range(N):
        acc = [0.0] * N
        for h in range(3):
            sc = [(-math.inf if i == j else -A["d2"][h][i][j] / (tau * A["taus"][h] / 0.25)) for j in range(N)]
            m = max(sc); e = [math.exp(v - m) for v in sc]; Z = sum(e)
            for j in range(N): acc[j] += e[j] / Z / 3
        mx = max(acc); out.append([v / mx for v in acc])
    return out
def write_tables():
    A = D["A"]; M, RM = A["mean"], A["rowMax"]
    tiles = [[[M[i][j] / RM[i] for j in range(N)] for i in range(N)]]
    tiles += [anneal_tile(k / 12) for k in range(13)]
    for k in range(1, 7): tiles.append([[D["WK"][k][i][j] / D["WKmax"][k][i] for j in range(N)] for i in range(N)])
    att = Image.new("L", (36 * len(tiles), 36))
    for t_i, tile in enumerate(tiles):
        for i in range(N):
            for j in range(N): att.putpixel((t_i * 36 + j, i), int(round(255 * max(0.0, min(1.0, tile[i][j])))))
    att.save("glyphs/att.png")
    top = Image.new("RGBA", (15, 36))              # x = head * 5 + rank, y = spot; R = kin letter, G = weight / the head's best
    for k in range(N):
        for h in range(3):
            for r in range(5):
                w, j = A["top"][h][k][r]; wn = w / A["top"][h][k][0][0]
                top.putpixel((h * 5 + r, k), (j, int(round(255 * wn)), 0, 255))
    top.save("glyphs/top.png")

ATTLIB = r"""
uniform sampler2D ATT;     // 20 tiles of 36 x 36: 0 the three heads averaged, 1..13 annealing steps, 14..19 SVD ranks 1..6; value = W / row maximum
float annealS(){ if (T_ >= FIN0 && T_ < FIN1) return 1.0 - orgK; return (t_ >= TA && t_ < TD) ? 0.5 - 0.5 * cos(6.2831853 * (t_ - TA) / 8.0) : -1.0; }
float attn(int i, int j){
  float tile = 0.0, fr = 0.0;
  if (svdR > 0.0) tile = 13.0 + svdR;
  else { float s = annealS(); if (s >= 0.0) { float g = s * 12.0; tile = 1.0 + floor(min(g, 11.999)); fr = g - floor(min(g, 11.999)); } }
  int t0 = int(tile);
  float a = texelFetch(ATT, ivec2(t0 * 36 + j, i), 0).r;
  if (fr > 0.0) a = mix(a, texelFetch(ATT, ivec2((t0 + 1) * 36 + j, i), 0).r, fr);
  return a;
}
"""

BIGOFF = {}
FADE = "float fadeK(){ return min(1.0, spotK * 4.0) * (1.0 - cl((spotK - 0.85) / 0.15)); }\n"
def tour():
    write_tables()
    ATL.add_image("solid", Image.new("L", (8, 8), 255))
    A = D["A"]; S_ = D["S"]; TT_ = D["TT"]
    # ---- the card of the spotlit letter ----
    ARM_COL = C_ACC4
    for k in range(N):
        d = DATA[k]; idx_n = k + 1
        num = str((k % 9 + 1) * 10 ** (k // 9)); num = f"{int(num):,}".replace(",", " ")
        row = D["ROWS"][k // 9]; kind = "ձայնավոր" if d[5] else "բաղաձայն"
        kind_full = "ձայնավոր · vowel" if d[5] else ("շնչեղ բաղաձայն · aspirated" if d[8] else ("ձայնեղ բաղաձայն · voiced" if d[7] else "խուլ բաղաձայն · voiceless"))
        ATL.add(f"c_hdr{k}", f"Տառ {idx_n} · 36-ից · {row}", 24, track=0.08, upper=True)
        ATL.add(f"c_name{k}", d[1], 56, wght=300)
        ATL.add(f"c_trk{k}", f"{d[2]} · {kind}", 36)
        ATL.add(f"c_num{k}", f"= {num}", 24, tag=(None, 16, 8))
        ATL.add(f"c_kf{k}", kind_full, 24, tag=(None, 16, 8))
        ATL.add(f"c_word{k}", d[3], 44, wght=300)
        ATL.add(f"c_gloss{k}", d[4], 32)
        ATL.add(f"c_pos{k}", f"դիրք · position {k // 9 + 1} × {k % 9 + 1} · 4 × 9", 20)
        # the big glyph (230 px) and its soft glow, from Noto Serif Armenian, weight 200, drawn at 1 texel per deck px
        bigf = ImageFont.truetype(NSA, 230); bigf.set_variation_by_axes([200, 100])
        im = Image.new("L", (300, 300), 0)
        ImageDraw.Draw(im).text((150, 234), d[0], font=bigf, fill=255, anchor="ms")
        from PIL import ImageFilter
        gl = im.resize((75, 75)).filter(ImageFilter.GaussianBlur(60 / 4 / 1.5))
        bb = im.getbbox() or (0, 0, 8, 8); pad = 3
        bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad))
        BIGOFF[k] = (bb[0], bb[1])
        ATL.add_image(f"c_big{k}", im.crop(bb)); ATL.rects[f"c_big{k}"][4:6] = [bb[2] - bb[0], bb[3] - bb[1]]       # only the glyph's own box goes into the atlas
        ATL.add_image(f"c_glow{k}", gl); ATL.rects[f"c_glow{k}"][4:6] = [300, 300]
        ts = TT_ + k * S_; kw = dict(ts=ts, te=ts + S_, fi=0.9, fo=0.01, rise=22, ease_in=True)
        label(f"c_hdr{k}", 144, 156, col=C_ACC, baseline=True, **kw)
        label(f"c_glow{k}", 144 + 0, 175 - 28, col=C_ACC4, a=0.35, **kw)
        label(f"c_big{k}", 144 + BIGOFF[k][0], 175 - 28 + BIGOFF[k][1], col=C_ACC4, **kw)
        bigw = 250
        label(f"c_name{k}", 144 + bigw + 34 - 20, 378, baseline=True, **kw)
        label(f"c_trk{k}", 144 + bigw + 34 - 20, 424, col=NEUTRAL(165), baseline=True, **kw)
        label(f"c_num{k}", 144, 452, col=C_ACC3, **kw)
        label(f"c_kf{k}", 144 + ATL.size(f"c_num{k}")[0] + 14, 452, col=NEUTRAL(190), **kw)
        label(f"c_word{k}", 144, 556, baseline=True, **kw)
        label(f"c_gloss{k}", 144 + ATL.size(f"c_word{k}")[0] + 18, 556, col=NEUTRAL(165), baseline=True, **kw)
        fk = dict(ts=ts, te=ts + S_, fi=S_ * 0.25, fo=S_ * 0.15)
        label(f"c_pos{k}", 144 + 9 * 21 + 16, 630, col=C_PAPER, a=0.6, baseline=True, **fk)
        # attention values beside the kin letter of each head's best match: "0,12" in the head's colour
        for h in range(3):
            w, j = A["top"][h][k][0]
            key = f"v_{w:.2f}"
            ATL.add(key, f"{w:.2f}".replace(".", ","), 20)
            label(key, 28, (h - 1) * 18, col=[C_GOLD, C_TEAL, C_PAPER][h], a=0.9, anchor=j, baseline=False, **fk)
    # ---- the map's text ----
    ATL.add("m_title", "Ուշադրություն · attention", 22); ATL.add("m_sub", "softmax(QKᵀ / √d) · 36 × 36 · 3 heads", 20)
    label("m_title", 1540, 114, col=C_GOLD, a=0.9, baseline=True, mode="veil", fi=0.01)
    label("m_sub", 1540, 138, col=C_PAPER, a=0.55, baseline=True, mode="veil")
    for h, nm in enumerate(("ձայն · sound", "թիվ · number", "կարգ · order")):
        ATL.add(f"m_head{h}", nm, 20)
        y = 150 + 36 * 6 + 30 + h * 28
        label(f"m_head{h}", 1540 + 34, y, col=C_PAPER, a=0.7, baseline=True, mode="veil")
    # the lit row's letter, beside the map
    for k in range(N):
        ATL.add(f"m_row{k}", DATA[k][0], 22, wght=300)
        ts = TT_ + k * S_
        label(f"m_row{k}", 1540 + 36 * 6 + 10, 150 + k * 6 + 7, col=C_TEAL, baseline=True, ts=ts, te=ts + S_, fi=0.01, fo=0.01, mode="veil")

    # ---- attention arcs: 3 heads x 5 kin, drawn for the spotlit letter only; kin and weights come from the TOP table ----
    ns = 17; coords, idx, attrs = [], [], {"aA": []}
    for m in range(15):
        base = len(coords)
        for k in range(ns + 1):
            for side in (-1, 1):
                coords.append("0 0 0"); attrs["aA"].append(f"{m} {k / ns:.5f} {side} 0")
        for k in range(ns):
            a0 = base + 2 * k
            idx.append(f"{a0} {a0+1} {a0+3} {a0+2} -1")
    vs = LIB + VERT_IN + r"""
uniform sampler2D TOP; uniform ivec4 x3d_Viewport;
in vec4 aA;
out vec4 vCol;
vec3 headCol(int h){ return h == 0 ? GOLD : h == 1 ? TEAL : PAPER; }
void main(){
  tl();
  float fade = min(1.0, spotK * 4.0) * (1.0 - cl((spotK - 0.85) / 0.15));
  int m = int(aA.x); int h = m / 5; float u = aA.y, side = aA.z;
  vec4 e = texelFetch(TOP, ivec2(m, int(max(spot, 0.0))), 0);
  int j = int(e.r * 255.0 + 0.5); float wn = e.g;
  vCol = vec4(headCol(h), spot >= 0.0 ? (0.12 + 0.7 * wn) * fade : 0.0);
  Ls Q = lstate(int(max(spot, 0.0)), t_), K = lstate(j, t_);
  vec3 c = (Q.pos + K.pos) * 0.5 + vec3(float(h - 1) * 40.0, 30.0 + float(h) * 18.0, 0.0) * 0.01;
  float u1 = 1.0 - u;
  vec3 p = u1 * u1 * Q.pos + 2.0 * u1 * u * c + u * u * K.pos;
  vec3 d = 2.0 * u1 * (c - Q.pos) + 2.0 * u * (K.pos - c);
  vec4 c0 = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(p, 1.0), c1 = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(p + normalize(d) * 0.05, 1.0);
  vec2 vp = vec2(x3d_Viewport.zw);
  vec2 s0 = c0.xy / c0.w * vp * 0.5, s1 = c1.xy / c1.w * vp * 0.5, dir = normalize(s1 - s0 + vec2(1e-6));
  float wpx = (0.8 + 2.4 * wn) * vp.x / 1920.0 * 0.5;
  vec2 off = vec2(-dir.y, dir.x) * side * wpx;
  gl_Position = c0; gl_Position.xy += off / (vp * 0.5) * c0.w;
}
"""
    fs = r"""
in vec4 vCol; out vec4 x3d_FragColor;
void main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }
"""
    sh = shader("ArcShader", lfields() + "\n" + sfnode_tex("TOP", "glyphs/top.png", nearest=True), vs, fs)
    add("attention arcs from the spotlit letter to its kin, one colour per head",
        f"    <Shape bboxCenter='0 0 -2' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n{attr_xml(attrs)}    </IndexedFaceSet></Shape>")
    SHADERS.append("ArcShader")

    # ---- the dashed line from the spotlit letter to its card, and the ring around it ----
    vs = LIB + VERT_IN + r"""
out vec4 vCol; out float vS;
void main(){
  tl();
  float fade = min(1.0, spotK * 4.0) * (1.0 - cl((spotK - 0.85) / 0.15));
  vec3 q = lstate(int(max(spot, 0.0)), t_).pos, e = W(vec2(560.0, 300.0), 0.02);
  vS = x3d_Vertex.x * length(e - q) * 100.0;
  vCol = vec4(GOLD, spot >= 0.0 ? 0.5 * fade : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(x3d_Vertex.x < 0.5 ? q : e, 1.0);
}
"""
    fs = r"""
in vec4 vCol; in float vS; out vec4 x3d_FragColor;
void main(){ if (vCol.a < 0.003 || mod(vS, 12.0) > 4.0) discard; x3d_FragColor = vCol; }
"""
    sh = shader("DashShader", lfields(), vs, fs)
    add("dashed line from the spotlit letter to its card",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='0 1 -1'><Coordinate point='0 0 0 1 0 0'/></IndexedLineSet></Shape>")
    SHADERS.append("DashShader")

    vs = LIB + VERT_IN + r"""
out vec2 vQ; out float vA; out float vR;
void main(){
  tl(); float t = t_;
  float fade = min(1.0, spotK * 4.0) * (1.0 - cl((spotK - 0.85) / 0.15));
  vec3 q = lstate(int(max(spot, 0.0)), t).pos;
  vec2 c = x3d_Vertex.xy; vQ = c * 60.0; vA = spot >= 0.0 ? 0.8 * fade : 0.0; vR = 34.0 + 6.0 * sin(T_ * 3.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(q + vec3(c * 0.6, 0.015), 1.0);
}
"""
    fs = r"""
in vec2 vQ; in float vA; in float vR; out vec4 x3d_FragColor;
const vec3 GOLD = vec3(0.88235, 0.67843, 0.4);
void main(){ float a = vA * smoothstep(1.6, 0.4, abs(length(vQ) - vR)); if (a < 0.003) discard; x3d_FragColor = vec4(GOLD, a); }
"""
    sh = shader("RingShader", lfields(), vs, fs)
    add("ring around the spotlit letter",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='0 1 2 3 -1'><Coordinate point='-1 -1 0 1 -1 0 1 1 0 -1 1 0'/></IndexedFaceSet></Shape>")
    SHADERS.append("RingShader")

    # ---- the alphabet stone as a 4 x 9 positional grid (one quad, cells drawn in the fragment shader) ----
    vs = rect_vs(144, 586, 9 * 21 - 3, 4 * 21 - 3, 0.02, "out float vFade;", "vFade = (spot >= 0.0) ? min(1.0, spotK * 4.0) * (1.0 - cl((spotK - 0.85) / 0.15)) : 0.0; vSpot = spot;", kill="vFade <= 0.0").replace("out vec2 vP;", "out vec2 vP; out float vSpot;")
    fs = r"""
in vec2 vP; in float vA; in float vFade; in float vSpot; out vec4 x3d_FragColor;
const vec3 GOLD = vec3(0.88235, 0.67843, 0.4), TEAL = vec3(0.78824, 0.93725, 0.91373);
void main(){
  vec2 q = vP - vec2(144.0, 586.0); vec2 cell = floor(q / 21.0); vec2 inn = q - cell * 21.0;
  if (inn.x > 18.0 || inn.y > 18.0 || vFade <= 0.0) discard;
  float i = cell.y * 9.0 + cell.x;
  bool lit = abs(i - vSpot) < 0.5;
  float a = (lit ? 0.95 : (i < vSpot ? 0.34 : 0.14)) * vFade;
  x3d_FragColor = vec4(lit ? TEAL : GOLD, a);
}
"""
    rect_shape("GridShader", "the alphabet stone as a 4 x 9 positional grid", vs, fs)

    # ---- the attention map, 36 x 36, the spotlit row lit ----
    vs = rect_vs(1536, 146, 228, 228, 0.02, "out float vV; out float vSpot; flat out float vTile; flat out float vFr;", "vV = mapK; vSpot = spot; { float tile = 0.0, fr = 0.0; if (svdR > 0.0) tile = 13.0 + svdR; else { float s_ = annealS(); if (s_ >= 0.0) { float g = s_ * 12.0; tile = 1.0 + floor(min(g, 11.999)); fr = g - floor(min(g, 11.999)); } } vTile = tile; vFr = fr; }", kill="vV <= 0.0").replace("out vec2 vP;", "out vec2 vP;").replace(LIB + VERT_IN, LIB + ATTLIB + VERT_IN)
    fs = r"""
uniform sampler2D ATT;
in vec2 vP; in float vV; in float vSpot; flat in float vTile; flat in float vFr; out vec4 x3d_FragColor;
const vec3 GOLD = vec3(0.88235, 0.67843, 0.4), TEAL = vec3(0.78824, 0.93725, 0.91373);
void main(){
  if (vV <= 0.0) discard;
  vec2 q = vP - vec2(1540.0, 150.0); vec2 cell = floor(q / 6.0); vec2 inn = q - cell * 6.0;
  float a = 0.0; vec3 col = GOLD;
  if (cell.x >= 0.0 && cell.x < 36.0 && cell.y >= 0.0 && cell.y < 36.0 && inn.x < 5.0 && inn.y < 5.0) {
    int t0 = int(vTile); float v = texelFetch(ATT, ivec2(t0 * 36 + int(cell.x), int(cell.y)), 0).r;
    if (vFr > 0.0) v = mix(v, texelFetch(ATT, ivec2((t0 + 1) * 36 + int(cell.x), int(cell.y)), 0).r, vFr);
    bool row = abs(cell.y - vSpot) < 0.5;
    col = row ? TEAL : GOLD; a = (0.06 + 0.8 * v) * vV * (row ? 1.0 : 0.75);
  }
  if (vSpot >= 0.0) {                                    // outline round the lit row
    vec2 o = vP - vec2(1538.0, 148.0 + vSpot * 6.0), sz = vec2(219.0, 9.0);
    if (o.x >= 0.0 && o.y >= 0.0 && o.x <= sz.x && o.y <= sz.y && (o.x < 1.0 || o.y < 1.0 || o.x > sz.x - 1.0 || o.y > sz.y - 1.0)) { col = TEAL; a = 0.9 * vV; }
  }
  if (a < 0.003) discard;
  x3d_FragColor = vec4(col, a);
}
"""
    rect_shape("MapShader", "the 36 x 36 attention map", vs, fs, sfnode_tex("ATT", "glyphs/att.png", nearest=True))
    # legend bars (three small lines)
    for h, col in enumerate((C_GOLD, C_TEAL, C_PAPER)):
        y = 150 + 36 * 6 + 30 + h * 28 - 8
        label("solid", 1540, y, col=col, a=0.9, mode="veil", wpx=22, hpx=2)


# =====================================================================================================================
# 6. the writing of the first sentence of 405, and the embedding space with the attention tensor
# =====================================================================================================================
def writing_act(tag, SL, GDT, DW, CLK, W0, W1, S0, S1, ns=14, nprev=3):
    NG = len(SL)
    PX = lambda src: src.replace("@CLK@", CLK).replace("@W0@", f"{W0:.4f}").replace("@W1@", f"{W1:.4f}").replace("@S0@", f"{S0:.1f}").replace("@S1@", f"{S1:.1f}")
    GS = [(sl["x"], sl["y"], sl["src"] if sl["src"] >= 0 else 36, sl["word"]) for sl in SL]
    gs_field = f"        <field name='GS' type='MFVec4f' accessType='inputOutput' value='{mf4(GS)}'/>"
    pre = f"const float NG = {NG}.0, GDT = {GDT}, DW = {DW};\nuniform vec4 GS[{NG}];\n" + r"""
// state of glyph k of the sentence: where it is, how far along its flight from its source letter in the helix
void wglyph(int k, out vec3 pos, out float u, out float e, out float fadeOut){
  float tw = @CLK@ - @W0@; fadeOut = cl((tw - (DW - 1.3)) / 1.1);
  u = (tw - (1.0 + float(k) * GDT)) / 0.55;
  vec4 g = GS[k]; int src = int(g.z);
  vec3 slotW = W(g.xy, 0.03);
  vec3 s0 = src < 36 ? lstate(src, t_).pos : W(g.xy + vec2(0.0, -40.0), 0.0);
  e = ease(min(1.0, max(u, 0.0)));
  pos = mix(s0, slotW, e);
}
bool wOn(){ return @CLK@ >= @W0@ && @CLK@ < @W1@; }
"""
    # glyphs + glow
    def at(i, ci):
        k, kind = divmod(i, 2); cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]
        return {"aA": (k, cx, cy, kind)}
    coords, idx, attrs = quads(NG * 2, at)
    vs = LIB + VERT_IN + pre + r"""
in vec4 aA; out vec2 vUV; out vec4 vCol; out vec2 vQ; out float vKind; out float vInk;
void main(){
  tl(); int k = int(aA.x); vec3 pos; float u, e, fo; wglyph(k, pos, u, e, fo);
  vInk = ease(clamp(u, 0.0, 1.0)) * 1.12 - 0.04;                       // the glyph is written in flight: ink time runs from the pen's first touch
  float size = mix(@S0@, @S1@, e); vec3 col = mix(GOLD, DEEP, e);
  bool on = wOn() && u > 0.0; float kind = aA.w; vKind = kind; vQ = aA.yz;
  float a = on ? (kind < 0.5 ? (0.35 + 0.6 * e) * (1.0 - fo) : (u < 1.0 ? 0.4 : 0.12) * (1.0 - fo)) : 0.0;
  vCol = vec4(col, a);
  float half_ = kind < 0.5 ? size : size * 1.4;
  int gi = int(GS[k].z); vec2 cell = vec2(mod(float(gi), 6.0), floor(float(gi) / 6.0));
  vUV = (cell + vec2(0.5 + 0.49 * aA.y, 0.5 - 0.49 * aA.z)) / vec2(6.0, 7.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos + vec3(aA.yz * half_ * 0.01, kind < 0.5 ? 0.0 : -0.002), 1.0);
}
"""
    fs = r"""
uniform sampler2D atlas;
in vec2 vUV; in vec4 vCol; in vec2 vQ; in float vKind; in float vInk; out vec4 x3d_FragColor;
void main(){
  vec3 rgb = vCol.rgb; float a;
  if (vKind < 0.5) {
    vec4 g = texture(atlas, vUV); float tm = g.r;
    float inked = smoothstep(vInk, vInk - 0.07, tm);                    // 1 where the pen has already been
    float tip = exp(-pow((tm - vInk) / 0.035, 2.0)) * (vInk < 1.0 ? 1.0 : 0.0);
    a = g.a * vCol.a * max(inked, 0.0); rgb = mix(rgb, vec3(1.0, 0.96, 0.82), clamp(tip * 0.9, 0.0, 1.0)); a = max(a, g.a * tip * 0.9 * vCol.a);
  } else a = vCol.a * max(0.0, 1.0 - length(vQ));
  if (a < 0.004) discard;
  x3d_FragColor = vec4(rgb, a);
}
"""
    fx_shape("Write" + tag + "Shader", "the writing: glyphs fly out of their source letters", PX(vs), fs, coords, idx, attrs, fields=gs_field + "\n" + sfnode_tex("atlas", "glyphs/atlas_white_w.png"))
    # causal attention arcs back to the three glyphs before
    arcs = []
    for k in range(1, NG):
        for b in range(max(0, k - nprev), k): arcs.append((k, b))
    coords, idx, av = [], [], []
    for (k, b) in arcs:
        base = len(coords)
        for q in range(ns + 1):
            for side in (-1, 1): coords.append("0 0 0"); av.append(f"{k} {b} {q / ns:.4f} {side}")
        for q in range(ns):
            a0 = base + 2 * q; idx.append(f"{a0} {a0+1} {a0+3} {a0+2} -1")
    vs = LIB + VERT_IN + pre + r"""
uniform ivec4 x3d_Viewport;
in vec4 aA; out vec4 vCol;
void main(){
  tl(); int k = int(aA.x), b = int(aA.y); float uu = aA.z, side = aA.w;
  vec3 pos; float u, e, fo; wglyph(k, pos, u, e, fo);
  vec3 pv = W(GS[b].xy, 0.03);
  bool same = GS[b].w == GS[k].w;
  float a = (wOn() && u > 0.0 && u < 2.4) ? (same ? 0.4 : 0.18) * (1.0 - u / 2.4) * (1.0 - fo) : 0.0;
  vCol = vec4(same ? TEAL : GOLD, a);
  vec3 c = vec3((pos.x + pv.x) * 0.5, max(pos.y, pv.y) + (26.0 + float(k - b) * 10.0) * 0.01, 0.03);
  float u1 = 1.0 - uu;
  vec3 p = u1 * u1 * pos + 2.0 * u1 * uu * c + uu * uu * pv;
  vec3 d = 2.0 * u1 * (c - pos) + 2.0 * uu * (pv - c);
  vec4 c0 = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(p, 1.0), c1 = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(p + normalize(d) * 0.05, 1.0);
  vec2 vp = vec2(x3d_Viewport.zw);
  vec2 s0 = c0.xy / c0.w * vp * 0.5, s1 = c1.xy / c1.w * vp * 0.5, dir = normalize(s1 - s0 + vec2(1e-6));
  float wpx = (same ? 1.4 : 0.8) * vp.x / 1920.0 * 0.5;
  gl_Position = c0; gl_Position.xy += vec2(-dir.y, dir.x) * side * wpx / (vp * 0.5) * c0.w;
}
"""
    fs = r"""
in vec4 vCol; out vec4 x3d_FragColor;
void main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }
"""
    sh = shader("Write" + tag + "ArcShader", lfields() + "\n" + gs_field, PX(vs), fs)
    add("causal attention arcs: each glyph attends to the three before it",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n      <FloatVertexAttribute name='aA' numComponents='4' value='{' '.join(av)}'/>\n    </IndexedFaceSet></Shape>")
    SHADERS.append("Write" + tag + "ArcShader")
    # thread from the source letter to the flying glyph
    coords, idx = [], []
    for k in range(NG):
        base = len(coords); coords.append(f"{k} 0 0"); coords.append(f"{k} 1 0"); idx.append(f"{base} {base+1} -1")
    vs = LIB + VERT_IN + pre + r"""
out vec4 vCol;
void main(){
  tl(); int k = int(x3d_Vertex.x); vec3 pos; float u, e, fo; wglyph(k, pos, u, e, fo);
  int src = int(GS[k].z); vec3 s0 = src < 36 ? lstate(src, t_).pos : W(GS[k].xy + vec2(0.0, -40.0), 0.0);
  vCol = vec4(GOLD, (wOn() && u > 0.0 && u < 1.0) ? 0.35 * (1.0 - e) : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(x3d_Vertex.y < 0.5 ? s0 : pos, 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("Write" + tag + "LineShader", lfields() + "\n" + gs_field, PX(vs), fs)
    add("threads from the source letters to the flying glyphs",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("Write" + tag + "LineShader")

def writing():
    SL = D["slots"]; NG = len(SL); GDT = D["GDT"]; DW = D["DW"]
    writing_act("", SL, GDT, DW, "t_", D["TC"], D["TW2"], 26.0, 40.0)
    ATL.add("w_tr", "To know wisdom and instruction; to perceive the words of understanding.", 26)
    ATL.add("w_ref", f"Առակաց Ա․2 · Proverbs 1:2 · 405 · {NG} glyphs · causal attention", 22)
    ts = D["TC"] + 1 + NG * GDT + 0.9
    for key, y, col, a in (("w_tr", 352, C_PAPER, 0.75), ("w_ref", 392, C_GOLD, 0.8)):
        label(key, 960, y, col=col, a=a, baseline=True, align="c", ts=ts, te=D["TC"] + DW - 0.2, fi=1.2, fo=1.1)

def space():
    # the four classes as dashed rings with their names
    HU = D["HULLS"]; CL = D["CLASSES"]
    rows = []
    for c, hl in enumerate(HU):
        cx, cy = (hl["x0"] + hl["x1"]) / 2, (hl["y0"] + hl["y1"]) / 2
        rows.append((cx, cy, (hl["x1"] - hl["x0"]) / 2 + 48, (hl["y1"] - hl["y0"]) / 2 + 34, *[v / 255 for v in CL[c][1]]))
        ATL.add(f"s_cls{c}", CL[c][0], 20)
        label(f"s_cls{c}", hl["x0"] - 20, cy - rows[-1][3] - 10, col=tuple(v / 255 for v in CL[c][1]), a=0.85, baseline=True, mode="space")
    hf = f"        <field name='HU' type='MFVec4f' accessType='inputOutput' value='{mf4([r[:4] for r in rows])}'/>\n        <field name='HC4' type='MFVec3f' accessType='inputOutput' value='{', '.join(' '.join(f(v) for v in r[4:]) for r in rows)}'/>"
    vs = rect_vs(0, 0, 1920, 1080, 0.02, "out float vS;", "vS = spaceK;", kill="vS <= 0.0")
    fs = r"""
uniform vec4 HU[4]; uniform vec3 HC4[4];
in vec2 vP; in float vA; in float vS; out vec4 x3d_FragColor;
void main(){
  if (vS <= 0.0) discard;
  float best = 0.0; vec3 col = vec3(0.0);
  for (int c = 0; c < 4; c++) {
    vec2 q = vP - HU[c].xy; vec2 r = HU[c].zw;
    float f = dot(q / r, q / r) - 1.0;
    vec2 gdir = 2.0 * q / (r * r); float d = abs(f) / max(length(gdir), 1e-4);            // distance to the ellipse in px
    float arc = atan(q.y / r.y, q.x / r.x) * (r.x + r.y) * 0.5;
    float a = 0.22 * vS * smoothstep(1.3, 0.3, d) * (mod(arc, 10.0) < 3.0 ? 1.0 : 0.0);
    if (a > best) { best = a; col = HC4[c]; }
  }
  if (best < 0.003) discard;
  x3d_FragColor = vec4(col, best);
}
"""
    rect_shape("HullShader", "dashed rings round the four classes", vs, fs, hf)
    # nearest-kin edges from the sound head
    pairs = []
    for i in range(N):
        for w_, j in D["A"]["top"][0][i][:2]: pairs.append((i, j))
    coords, idx = [], []
    for (i, j) in pairs:
        base = len(coords); coords.append(f"{i} {j} 0"); coords.append(f"{i} {j} 1"); idx.append(f"{base} {base+1} -1")
    vs = LIB + VERT_IN + r"""
out vec4 vCol;
void main(){
  tl(); int i = int(x3d_Vertex.x), j = int(x3d_Vertex.y);
  vCol = vec4(GOLD, 0.16 * spaceK);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(lstate(x3d_Vertex.z < 0.5 ? i : j, t_).pos + vec3(0.0, 0.0, -0.01), 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("KinShader", lfields(), vs, fs)
    add("nearest-kin edges in the embedding space",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("KinShader")
    # axes and their names
    for (x, y, w_, h_) in ((300, 586, 880, 1), (300, 120, 1, 466)): label("solid", x, y, col=C_PAPER, a=0.18, mode="space", wpx=w_, hpx=max(h_, 1) if h_ > 1 else 1)
    ATL.add("s_axes", "ներդրման տարածություն · embedding space · 2 principal axes: place →, voicing ↓", 20)
    ATL.add("s_lab", "շրթնային · labial", 20); ATL.add("s_glot", "կոկորդային · glottal", 20)
    label("s_axes", 300, 612, col=C_PAPER, a=0.6, baseline=True, mode="space")
    label("s_lab", 330, 112, col=C_PAPER, a=0.45, baseline=True, mode="space")
    label("s_glot", 1150, 112, col=C_PAPER, a=0.45, baseline=True, align="r", mode="space")
    # the tensor, 3 x 36 x 36, as 3888 points turning in depth
    write_heads()
    coords = [f"{h} {i} {j}" for h in range(3) for i in range(N) for j in range(N)]
    vs = LIB + VERT_IN + r"""
uniform sampler2D HEADS; uniform ivec4 x3d_Viewport;
out vec4 vCol;
const float TVX = 1330.0, TVY = 372.0, TVF = 900.0, TILT = 0.45, TCELL = 5.0;
void main(){
  tl(); float t = t_;
  int h = int(x3d_Vertex.x), i = int(x3d_Vertex.y), j = int(x3d_Vertex.z);
  float th = T_ * 0.25; int scan = int(mod(floor(t * 1.5), 36.0));
  float x3 = (float(j) - 17.5) * TCELL, y3 = (float(i) - 17.5) * TCELL, z3 = float(h - 1) * 70.0;
  float xr = x3 * cos(th) + z3 * sin(th), zr = -x3 * sin(th) + z3 * cos(th);
  float yr = y3 * cos(TILT) - zr * sin(TILT), zz = y3 * sin(TILT) + zr * cos(TILT), k = TVF / (TVF + zz);
  float v = texelFetch(HEADS, ivec2(h * 36 + j, i), 0).r * 0.6;
  bool hot = i == scan;
  vec3 col = h == 0 ? GOLD : h == 1 ? TEAL : PAPER;
  vCol = vec4(col, min(1.0, (0.05 + 0.6 * v) * (hot ? 1.9 : 1.0)) * spaceK * k);
  gl_PointSize = max(1.0, (hot ? 4.4 : 3.0) * k * float(x3d_Viewport.z) / 1920.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(vec2(TVX + xr * k, TVY + yr * k), 0.02), 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("TensorShader", lfields() + "\n" + sfnode_tex("HEADS", "glyphs/heads.png", nearest=True), vs, fs)
    add("the attention tensor, 3 x 36 x 36",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <PointSet><Coordinate point='{', '.join(coords)}'/></PointSet></Shape>")
    SHADERS.append("TensorShader")
    ATL.add("s_tens", "3 × 36 × 36 · ուշադրության թենզորը · the attention tensor", 20)
    label("s_tens", 1330, 568, col=C_GOLD, a=0.8, baseline=True, align="c", mode="space")
    for k in range(N):                      # the scan row: one letter and its row number, changing every 2/3 s
        ATL.add(f"s_scan{k}", f"{DATA[k][0]} · տող {k + 1}", 22)
    ts0, ts1 = D["TW2"], D["TS2"]
    for q in range(int(ts0 * 1.5), int(ts1 * 1.5) + 1):
        k = q % 36; a_, b_ = q / 1.5, (q + 1) / 1.5
        label(f"s_scan{k}", 1330, 540, col=C_TEAL, a=0.8, baseline=True, align="c", mode="space", ts=a_, te=b_, fi=0.01, fo=0.01)

def write_heads():
    A = D["A"]; im = Image.new("L", (108, 36))
    for h in range(3):
        for i in range(N):
            for j in range(N): im.putpixel((h * 36 + j, i), int(round(255 * max(0.0, min(1.0, A["heads"][h][i][j] / A["rowMax"][i])))))
    im.save("glyphs/heads.png")


# =====================================================================================================================
# 7. the web: 630 chords on the ring, node circles, pulses, the captions of each act
# =====================================================================================================================
def caption(prefix, states, y=612, col=C_PAPER, a=0.6, size=20, key="cap"):
    """centred caption = a static prefix strip + a small number strip per state (ts, te, text). All states are laid out so the whole line is centred."""
    ATL.add(f"{key}_p", prefix, size)
    wp = ATL.size(f"{key}_p")[0]
    for n, (ts, te, txt) in enumerate(states):
        ATL.add(f"{key}_n_{txt}", txt, size)
        wn = ATL.size(f"{key}_n_{txt}")[0]; x0 = 960 - (wp + wn) / 2
        label(f"{key}_p", x0, y, col=col, a=a, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")
        label(f"{key}_n_{txt}", x0 + wp, y, col=col, a=a, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")

def web():
    TS2, TB2, TSP, TP, TA, TD = D["TS2"], D["TB2"], D["TSP"], D["TP"], D["TA"], D["TD"]
    TM = TB2
    def c(x): return str(x).replace(".", ",")
    # ---- captions ----
    ATL.add("web_cap", "ամբողջապես կապակցված · fully connected · 36 × 35 ⁄ 2 = 630 chords, weighted by attention · signal on the heaviest edges", 20)
    label("web_cap", 960, 612, col=C_PAPER, a=0.6, baseline=True, align="c", mode="web", ts=TS2, te=TB2, fi=0.01, fo=0.01)
    caption("GNN · հաղորդագրությունների փոխանցում Ճ-ից · message passing from Ճ · h⁽ˡ⁺¹⁾ = Â h⁽ˡ⁾ · շերտ l = ", [(TM + 1.5 * l, TM + 1.5 * (l + 1) if l < 5 else TSP, str(l)) for l in range(6)], key="cmsg")
    ATL.add("spec_cap", f"Լապլասիան L = D − W · Fiedler vector · spectral cut · λ₂ = {c(round(D['lam2'], 3))}", 20)
    label("spec_cap", 960, 612, col=C_PAPER, a=0.6, baseline=True, align="c", mode="web", ts=TSP, te=TP, fi=0.01, fo=0.01)
    ATL.add("spec_pos", "f > 0", 20); ATL.add("spec_neg", "f < 0", 20)
    label("spec_pos", 960, 90, col=C_GOLD, a=0.85, baseline=True, align="c", mode="spec"); label("spec_neg", 960, 640, col=C_TEAL, a=0.85, baseline=True, align="c", mode="spec")
    ktot = 6.0 / 14.0
    caption("PageRank · d = 0,85 · r ← (1−d)/N + d·Mᵀr · կրկնություն · iteration ", [(TP + ktot * k, TP + ktot * (k + 1) if k < 14 else TA, str(k)) for k in range(15)], key="cpr")
    # anneal: tau sampled every 0.2 s
    st = []
    for n in range(40):
        ts = TA + n * 0.2; u = (ts + 0.1 - TA) / 8; tau = math.exp(math.log(.12) + (math.log(3) - math.log(.12)) * (.5 - .5 * math.cos(6.283 * u)))
        st.append((ts, ts + 0.2, f"{tau:.2f}".replace(".", ",")))
    caption("softmax(−‖q−k‖² / τ) · ջերմաստիճան · temperature τ = ", st, key="can")
    # the three PageRank leaders, labelled next to their circles (radially outward from the ring centre)
    for rank, (val, i) in enumerate(D["PRtop"]):
        for k0 in range(15):
            key = f"prl_{D['DATA'][i][0]}{D['PR'][k0][i]:.3f}"
            ATL.add(key, f"{D['DATA'][i][0]} {D['PR'][k0][i]:.3f}".replace(".", ","), 20)
            LABELS.append(dict(grow=0, key=key, x=0, y=7 - ATL.rects[key][6], w=ATL.size(key)[0], h=ATL.size(key)[1], col=C_TEAL, a=0.9, ts=TP + ktot * k0, te=TP + ktot * (k0 + 1) if k0 < 14 else TA, fi=0.01, fo=0.01, mode=MODES["web"], anchor=i, rise=0.0, clock=0, ease=0, radial=58))

    # ---- chords: every pair, a straight line whose alpha is the attention weight ----
    pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    coords, idx = [], []
    for (i, j) in pairs:
        base = len(coords); coords.append(f"{i} {j} 0"); coords.append(f"{i} {j} 1"); idx.append(f"{base} {base+1} -1")
    CH = LIB + ATTLIB + VERT_IN + r"""
uniform float FIED[36];
out vec4 vCol;
void main(){
  tl(); float t = t_;
  int i = int(x3d_Vertex.x), j = int(x3d_Vertex.y);
  float w = (attn(i, j) + attn(j, i)) * 0.5;
  float al = (0.025 + 0.42 * w * w) * max(webK, finK * orgK * (1.0 - finDim) * 0.9); vec3 col = GOLD;
  if (t >= TB2 && t < TSP) { float mf = mod(t - TB2, 1.5) / 1.5; al *= 1.0 + 0.9 * sin(PI * mf) * w; }
  float fi_ = LD[i].z, fj_ = LD[j].z;
  if (specK > 0.0 && sign(fi_) != sign(fj_)) { col = PAPER; al = max(al, 0.14 * specK); }
  vCol = vec4(col, al * (1.0 - poinK));
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(lstate(x3d_Vertex.z < 0.5 ? i : j, t).pos + vec3(0.0, 0.0, -0.004), 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("ChordShader", lfields() + "\n" + sfnode_tex("ATT", "glyphs/att.png", nearest=True), CH.replace("uniform float FIED[36];\n", ""), fs)
    add("the 630 chords of the alphabet graph, alpha = attention weight (SVD, annealing and the spectral cut re-colour them)",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("ChordShader")

    # ---- the eight-point star inscribed in the ring (two squares) ----
    coords, idx = [], []
    for off in (0, 1):
        base = len(coords)
        for k in range(5): coords.append(f"{off} {k} 0")
        idx.append(" ".join(str(base + k) for k in range(5)) + " -1")
    vs = LIB + VERT_IN + r"""
out vec4 vCol;
void main(){
  tl(); float t = t_;
  float an = x3d_Vertex.x * PI / 4.0 + x3d_Vertex.y * PI / 2.0 + T_ * 0.08;
  vCol = vec4(GOLD, 0.4 * webK * (1.0 - specK) * (1.0 - poinK) * (1.0 - svdK));
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(vec2(960.0 + 250.0 * cos(an), 345.0 + 228.0 * sin(an)), 0.0), 1.0);
}
"""
    sh = shader("StarRingShader", lfields(), vs, fs)
    add("the khachkar's eight-point star inscribed in the ring",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("StarRingShader")

    # ---- node circles: message passing, the spectral cut, PageRank ----
    write_nodes()
    def at(i, ci):
        cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]; return {"aA": (i, cx, cy, 0)}
    coords, idx, attrs = quads(N, at)
    vs = LIB + VERT_IN + r"""
uniform sampler2D NODES;
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vR;
void main(){
  tl(); float t = t_; int i = int(aA.x); vec2 cn = aA.yz;
  float r = 0.0; vec3 col = GOLD; float al = 0.35;
  if (t >= TB2 && t < TSP) {
    int ml = int(min(5.0, floor((t - TB2) / 1.5))); float mf = mod(t - TB2, 1.5) / 1.5;
    float a0 = texelFetch(NODES, ivec2(i, ml), 0).r, a1 = texelFetch(NODES, ivec2(i, min(5, ml + 1)), 0).r;
    r = 6.0 + 26.0 * mix(a0, a1, ease(mf));
  } else if (specK > 0.0) { r = 15.0 * specK; col = LD[i].z > 0.0 ? GOLD : TEAL; al = 0.3; }
  else if (t >= TP && t < TA) {
    float prK = min(14.0, (t - TP) / 6.0 * 14.0); int k0 = int(floor(prK)), k1 = min(14, k0 + 1);
    float a0 = texelFetch(NODES, ivec2(i, 6 + k0), 0).r, a1 = texelFetch(NODES, ivec2(i, 6 + k1), 0).r;
    r = 6.0 + 40.0 * mix(a0, a1, prK - floor(prK));
  }
  vCol = vec4(col, al * webK); vR = r; vQ = cn * (r * 1.5 + 3.0);
  vec3 pos = lstate(i, t).pos + vec3(vQ * 0.01, 0.006);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    fs = r"""
in vec4 vCol; in vec2 vQ; in float vR; out vec4 x3d_FragColor;
void main(){
  if (vR <= 0.0) discard;
  float d = length(vQ);
  float glow = vCol.a * max(0.0, 1.0 - d / (vR * 1.5));
  float ring = 0.6 * (vCol.a / 0.35) * 0.35 * smoothstep(1.4, 0.3, abs(d - vR)) * 1.7;
  float a = max(glow, ring * (vCol.a > 0.0 ? 1.0 : 0.0));
  if (a < 0.003) discard;
  x3d_FragColor = vec4(vCol.rgb, a);
}
"""
    sh = shader("NodeShader", lfields() + "\n" + sfnode_tex("NODES", "glyphs/nodes.png", nearest=True), vs, fs)
    add("node circles: message passing from Ճ, the Fiedler cut, PageRank",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n{attr_xml(attrs)}    </IndexedFaceSet></Shape>")
    SHADERS.append("NodeShader")

def write_nodes():
    """36 x 21 texture: rows 0..5 message passing (Ճ one-hot, then Â h), rows 6..20 PageRank iterations 0..14 over the final maximum"""
    im = Image.new("L", (36, 21))
    for l in range(6):
        for i in range(N): im.putpixel((i, l), int(round(255 * max(0.0, min(1.0, D["MSG"][l][i])))))
    for k in range(15):
        for i in range(N): im.putpixel((i, 6 + k), int(round(255 * max(0.0, min(1.0, D["PR"][k][i] / D["PRmax"])))))
    im.save("glyphs/nodes.png")


def pulses():
    import random
    rng = random.Random(4050)
    A = D["A"]; R = 24
    tex = Image.new("RGBA", (R, 86))
    for slot in range(86):
        for n in range(R):
            i = int(rng.random() * N); h = int(rng.random() * 3); r3 = int(rng.random() * 3); v = 0.6 + rng.random() * 0.7
            j = A["top"][h][i][r3][1]
            tex.putpixel((n, slot), (i, j, h, int(round((v - 0.6) / 0.7 * 255))))
    tex.save("glyphs/pulses.png")
    def at(slot, ci):
        m, kind = divmod(slot, 2); cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]; return {"aA": (m, kind, cx, cy)}
    coords, idx, attrs = quads(86 * 2, at)
    vs = LIB + VERT_IN + r"""
uniform sampler2D PULSE;
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); float t = t_; int slot = int(aA.x); float kind = aA.y; vec2 cn = aA.zw;
  bool bwd = slot >= 60;
  float tb = bwd ? TD : (slot < 26 ? TS2 : TB2), te = bwd ? TD2 : TSP;
  float a = 0.0; vec3 pa = vec3(0.0), pb = vec3(0.0); float u = 0.0, hh = 0.0;
  if (t >= tb && t < te) {
    float tt = t - tb;
    for (int n = 0; n < 24; n++) {
      vec4 e = texelFetch(PULSE, ivec2(n, slot), 0) * 255.0;
      float v = 0.6 + e.a / 255.0 * 0.7, dur = 1.0 / v;
      if (tt < dur) {
        int i = int(e.r + 0.5), j = int(e.g + 0.5); hh = e.b;
        vec3 p0 = lstate(bwd ? j : i, t).pos, p1 = lstate(bwd ? i : j, t).pos;
        u = tt * v; pa = mix(p0, p1, max(0.0, u - 0.12)); pb = mix(p0, p1, u); a = webK; break;
      }
      tt -= dur;
    }
  }
  vKind = kind; vQ = cn;
  vec3 hc = hh < 0.5 ? GOLD : hh < 1.5 ? TEAL : PAPER;
  vec3 pos;
  if (kind < 0.5) {            // the comet: a short segment ending at the head
    vec3 d = pb - pa; vec2 dn = normalize(d.xy + vec2(1e-5, 0.0)); vec2 nm = vec2(-dn.y, dn.x);
    vec3 base = cn.x < 0.0 ? pa : pb;
    pos = base + vec3(nm * cn.y * 0.008, 0.008);
    vCol = vec4(bwd ? DEEP : hc, 0.7 * a);
  } else {                     // the bright head
    pos = pb + vec3(cn * 0.04, 0.009);
    vCol = vec4(bwd ? GOLD : TEAL, 0.95 * a);
  }
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}
"""
    fs = r"""
in vec4 vCol; in vec2 vQ; in float vKind; out vec4 x3d_FragColor;
void main(){
  float a = vCol.a; if (vKind > 0.5) a *= smoothstep(1.0, 0.6, length(vQ));
  if (a < 0.004) discard; x3d_FragColor = vec4(vCol.rgb, a);
}
"""
    sh = shader("PulseShader", lfields() + "\n" + sfnode_tex("PULSE", "glyphs/pulses.png", nearest=True), vs, fs)
    add("signal pulses running along the heaviest edges (backwards during gradient descent)",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n{attr_xml(attrs)}    </IndexedFaceSet></Shape>")
    SHADERS.append("PulseShader")


# =====================================================================================================================
# 8. gradient descent, the Markov walk, Fourier epicycles, the Poincare disk, SVD + k-means
# =====================================================================================================================
def static_lines(name, comment, polys, alpha_expr, color="PAPER", z=0.02, extra_fields="", extra_decl="", vs_extra=""):
    coords, idx = [], []
    for poly in polys:
        base = len(coords)
        for (x, y, k) in poly: coords.append(f"{f(x)} {f(y)} {f(k)}")
        idx.append(" ".join(str(base + q) for q in range(len(poly))) + " -1")
    vs = LIB + VERT_IN + extra_decl + f"""
out vec4 vCol;
void main(){{
  tl(); float t = t_;
  float a = {alpha_expr};
  vec3 pos = vec3(x3d_Vertex.xy, {z}); {vs_extra}
  vCol = vec4({color}, a);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);
}}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader(name, lfields() + "\n" + extra_fields, vs, fs)
    add(comment, f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
                 f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append(name)
def wxy(x, y): return ((x - 960) * 0.01, (540 - y) * 0.01)
def caption_full(states, y=612, col=C_PAPER, a=0.6, size=20, key="cf"):
    for n, (ts, te, txt) in enumerate(states):
        ATL.add(f"{key}{n}", txt, size)
        label(f"{key}{n}", 960, y, col=col, a=a, baseline=True, align="c", mode="web", ts=ts, te=te, fi=0.01, fo=0.01)
def caption3(prefix, states, suffix, y=612, col=C_PAPER, a=0.6, size=20, key="c3"):
    ATL.add(f"{key}_p", prefix, size); ATL.add(f"{key}_s", suffix, size)
    wp, ws = ATL.size(f"{key}_p")[0], ATL.size(f"{key}_s")[0]
    for n, (ts, te, txt) in enumerate(states):
        ATL.add(f"{key}_n_{txt}", txt, size); wn = ATL.size(f"{key}_n_{txt}")[0]; x0 = 960 - (wp + wn + ws) / 2
        label(f"{key}_p", x0, y, col=col, a=a, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")
        label(f"{key}_n_{txt}", x0 + wp, y, col=col, a=a, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")
        label(f"{key}_s", x0 + wp + wn, y, col=col, a=a, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")
def cm(x, nd=3): return f"{x:.{nd}f}".replace(".", ",")
def quad_shader(name, comment, vs, fs, n, at, fields="", tex=None):
    coords, idx, attrs = quads(n, at)
    sh = shader(name, lfields() + "\n" + fields, vs, fs)
    add(comment, f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
                 f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n{attr_xml(attrs)}    </IndexedFaceSet></Shape>")
    SHADERS.append(name)
CORN = ((-1, -1), (1, -1), (1, 1), (-1, 1))
SOLID_FS = "in vec4 vCol; in vec2 vQ; in float vKind; out vec4 x3d_FragColor;\nvoid main(){ float a = vCol.a; if (vKind > 0.5) a *= smoothstep(1.0, 0.55, length(vQ)); if (a < 0.004) discard; x3d_FragColor = vec4(vCol.rgb, a); }\n"

def descent():
    TD, TD2 = D["TD"], D["TD2"]; GD = D["GD"]; DWIN = f"(t >= TD && t < TD2)"
    # contours of the bowl L(w) = w1^2 + 3 w2^2 + 0.6 w1 w2
    polys = []
    for c in (.08, .25, .6, 1.2, 2.1, 3.3, 4.8):
        poly = []
        for k in range(73):
            th = k / 72 * 6.283; rr = math.sqrt(c / (math.cos(th) ** 2 + 3 * math.sin(th) ** 2 + .6 * math.cos(th) * math.sin(th)))
            gx, gy = 490 + rr * math.cos(th) * 110, 355 - rr * math.sin(th) * 110
            poly.append((*wxy(gx, gy), 0))
        polys.append(poly)
    static_lines("BowlShader", "contours of the loss bowl", polys, f"{DWIN} ? 0.14 * webK : 0.0")
    # trajectory, revealed step by step
    gdw = [wxy(490 + w[0] * 110, 355 - w[1] * 110) for w in GD]
    gf = f"        <field name='GDW' type='MFVec2f' accessType='inputOutput' value='{', '.join(f'{f(x)} {f(y)}' for x, y in gdw)}'/>"
    poly = [(0, 0, k) for k in range(48)]
    static_lines("TrajShader", "the momentum trajectory", [poly], f"({DWIN} && x3d_Vertex.z <= floor(min(47.0, cl((t - TD) / 6.5) * 47.0)) + 1.0) ? 0.7 * webK : 0.0",
                 color="GOLD", extra_fields=gf, extra_decl="uniform vec2 GDW[48];\n",
                 vs_extra="{ float gk = min(47.0, cl((t - TD) / 6.5) * 47.0); int k0 = int(floor(gk)), kk = int(x3d_Vertex.z); vec2 q = GDW[kk]; if (kk == k0 + 1) q = mix(GDW[k0], GDW[kk], gk - floor(gk)); pos.xy = q; }")
    # the ball
    def at(i, ci): cx, cy = CORN[ci]; return {"aA": (cx, cy, 0, 0)}
    vs = LIB + VERT_IN + r"""
uniform vec2 GDW[48];
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); float t = t_; vec2 cn = aA.xy; vQ = cn;
  float gk = min(47.0, cl((t - TD) / 6.5) * 47.0); int k0 = int(floor(gk)), k1 = min(47, k0 + 1);
  vec2 b = mix(GDW[k0], GDW[k1], gk - floor(gk));
  bool on = t >= TD && t < TD2;
  vKind = aA.w;
  vCol = vec4(TEAL, on ? 0.8 * webK : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(b.x + cn.x * 0.22, b.y + cn.y * 0.22, 0.03, 1.0);
}
""".replace("vKind = aA.w;", "vKind = 1.0;")
    quad_shader("BallShader", "the ball rolling down the bowl", vs, SOLID_FS, 1, at, fields=gf)
    # texts: the loss at each step, the update rule, the caption
    pre = "L(w) = w₁² + 3w₂² + 0,6·w₁w₂ · "
    ATL.add("d_pre", pre, 20); wp = ATL.size("d_pre")[0]
    for k0 in range(48):
        w0 = GD[k0]; loss = w0[0] ** 2 + 3 * w0[1] ** 2 + .6 * w0[0] * w0[1]
        txt = f"քայլ {k0} · L = {cm(loss)}"; ATL.add(f"d_t{k0}", txt, 20)
        ts = TD + k0 * 6.5 / 47; te = TD + (k0 + 1) * 6.5 / 47 if k0 < 47 else TD2
        label("d_pre", 300, 135, col=C_PAPER, a=0.7, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")
        label(f"d_t{k0}", 300 + wp, 135, col=C_PAPER, a=0.7, baseline=True, ts=ts, te=te, fi=0.01, fo=0.01, mode="web")
    ATL.add("d_upd", "w ← w + v · v ← βv − η∇L", 20)
    label("d_upd", 300, 585, col=C_GOLD, a=0.7, baseline=True, ts=TD, te=TD2, fi=0.01, fo=0.01, mode="web")
    ATL.add("d_cap", "գրադիենտային վայրէջք · gradient descent with momentum · η = 0,08 · β = 0,9 · հետադարձ անցում · backward pass on the graph", 20)
    label("d_cap", 960, 612, col=C_PAPER, a=0.6, baseline=True, align="c", ts=TD, te=TD2, fi=0.01, fo=0.01, mode="web")

def walk():
    import random
    TD2, TF = D["TD2"], D["TF"]; Wm = D["A"]["mean"]
    rng = random.Random(35)
    L = 17; seqs = []
    for i in range(N):
        sq = [i]
        for h in range(L - 1):
            r = rng.random(); n = sq[-1]; acc = 0.0; m = 0
            for m in range(N):
                acc += Wm[n][m]
                if r <= acc: break
            sq.append(min(N - 1, m))
        seqs.append(sq)
    wt = Image.new("L", (L, N)); occ_t = Image.new("L", (L, N))
    occ = [0] * N; hist = []
    for h in range(L):
        for w in range(N): occ[seqs[w][h]] += 1
        hist.append(list(occ))
    for w in range(N):
        for h in range(L): wt.putpixel((h, w), seqs[w][h])
    for h in range(L):
        mx = max(1, max(hist[h]))
        for i in range(N): occ_t.putpixel((h, i), int(round(255 * hist[h][i] / mx)))
    wt.save("glyphs/walk.png"); occ_t.save("glyphs/occ.png")
    # walkers
    def at(i, ci): cx, cy = CORN[ci]; return {"aA": (i, cx, cy, 0)}
    vs = LIB + VERT_IN + r"""
uniform sampler2D WALK;
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); float t = t_; int w = int(aA.x); vec2 cn = aA.yz; vQ = cn; vKind = 1.0;
  bool on = t >= TD2 && t < TF;
  float hp = (t - TD2) * 1.7; int h = int(min(15.0, floor(hp))); float e = ease(hp >= 16.0 ? 1.0 : fract(hp));
  int n = int(texelFetch(WALK, ivec2(h, w), 0).r * 255.0 + 0.5), m = int(texelFetch(WALK, ivec2(h + 1, w), 0).r * 255.0 + 0.5);
  vec3 p = mix(lstate(n, t).pos, lstate(m, t).pos, e);
  vCol = vec4(TEAL, on ? 0.9 * webK : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(p + vec3(cn * 0.03, 0.012), 1.0);
}
"""
    quad_shader("WalkerShader", "36 random walkers hopping along the chords", vs, SOLID_FS, N, at, fields=sfnode_tex("WALK", "glyphs/walk.png", nearest=True))
    # occupancy bars (gold) and the stationary distribution (a tick)
    prn = [D["PR"][14][i] / D["PRmax"] for i in range(N)]
    def at(i, ci):
        n, kind = divmod(i, 2); cx, cy = CORN[ci]; return {"aA": (n, kind, cx, cy), "aB": (prn[n], 0, 0, 0)}
    vs = LIB + VERT_IN + r"""
uniform sampler2D OCC;
in vec4 aA; in vec4 aB; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); float t = t_; int i = int(aA.x); float kind = aA.y; vec2 cn = aA.zw; vQ = cn; vKind = 0.0;
  bool on = t >= TD2 && t < TF;
  int h = int(min(16.0, floor((t - TD2) * 1.7)));
  float bar = 70.0 * texelFetch(OCC, ivec2(h, i), 0).r;
  vec3 pw = lstate(i, t).pos; vec2 pp = vec2(pw.x * 100.0 + 960.0, 540.0 - pw.y * 100.0), dv = pp - vec2(960.0, 345.0);
  vec2 u = dv / max(length(dv), 1.0), nm = vec2(-u.y, u.x);          // px, y down
  vec2 q;
  if (kind < 0.5) { float s = cn.x < 0.0 ? 30.0 : 30.0 + bar; q = pp + u * s + nm * cn.y * 3.0; vCol = vec4(GOLD, on ? 0.75 * webK : 0.0); }
  else { float s = 30.0 + 70.0 * aB.x; q = pp + u * (s + cn.x * 0.6) + nm * cn.y * 5.0; vCol = vec4(PAPER, on ? 0.5 * webK : 0.0); }
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(q, 0.011), 1.0);
}
"""
    quad_shader("OccShader", "occupancy bars against the stationary distribution", vs, SOLID_FS, N * 2, at, fields=sfnode_tex("OCC", "glyphs/occ.png", nearest=True))
    st = [(TD2 + k / 1.7, TD2 + (k + 1) / 1.7 if k < 15 else TF, str(36 * (k + 1))) for k in range(16)]
    caption3("Մարկով · random walk · 36 walkers on the transition matrix · occupancy ", st, " hops → stationary π (outlined)", key="cwalk")

def fourier():
    TF, TPC = D["TF"], D["TPC"]; ZK = D["ZK"]
    zk = ", ".join(f"{z['k']} {f(z['re'])} {f(z['im'])} {f(z['mag'])}" for z in ZK)
    zf = f"        <field name='ZKU' type='MFVec4f' accessType='inputOutput' value='{zk}'/>"
    FPRE = r"""
uniform vec4 ZKU[19];
float fU(){ return cl((t_ - TF) / 7.2); }
float fK(float u){ return min(19.0, 3.0 + floor(u * 17.0)); }
vec2 rotc(vec2 p){ float th = T_ * 0.08; return vec2(960.0 + p.x * cos(th) - p.y * sin(th), 345.0 + p.x * sin(th) + p.y * cos(th)); }
vec2 chain(float u, int upto, out vec2 vel){            // centre of epicycle `upto` and its vector
  float thp = u * 6.2831853; vec2 p = vec2(0.0); vel = vec2(0.0);
  for (int l = 0; l < 19; l++) {
    vec4 z = ZKU[l]; float c = cos(z.x * thp), s = sin(z.x * thp);
    vec2 v = vec2(z.y * c - z.z * s, z.y * s + z.z * c);
    if (l == upto) { vel = v; return p; }
    p += v;
  }
  return p;
}
"""
    # circles, vectors, pen dot
    def at(i, ci):
        l, kind = divmod(i, 3); cx, cy = CORN[ci]; return {"aA": (l, kind, cx, cy)}
    vs = LIB + VERT_IN + FPRE + r"""
uniform ivec4 x3d_Viewport;
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind; out float vR;
void main(){
  tl(); float t = t_; int l = int(aA.x); float kind = aA.y; vec2 cn = aA.zw; vQ = cn; vKind = kind; vR = 0.0;
  bool on = t >= TF && t < TPC; float u = fU(), K = fK(u);
  vec2 vel; vec2 c0 = chain(u, l, vel);
  float mag = ZKU[l].w; bool act = on && float(l) < K;
  vec2 q;
  if (kind < 0.5) { vR = mag; q = rotc(c0 + cn * (mag + 3.0)); vQ = cn * (mag + 3.0); vCol = vec4(PAPER, act ? 0.22 * webK : 0.0); }
  else if (kind < 1.5) {
    vec2 a0 = rotc(c0), a1 = rotc(c0 + vel); vec2 d = a1 - a0; vec2 dn = normalize(d + vec2(1e-5)); vec2 nm = vec2(-dn.y, dn.x);
    q = (cn.x < 0.0 ? a0 : a1) + nm * cn.y * 0.7; vKind = 2.0; vCol = vec4(TEAL, act ? 0.6 * webK : 0.0);
  } else {
    vec2 dummy; vec2 pen = chain(u, 19, dummy);                      // all harmonics up to K only
    vec2 pk = vec2(0.0); { float thp = u * 6.2831853; for (int m = 0; m < 19; m++) { if (float(m) >= K) break; vec4 z = ZKU[m]; float c = cos(z.x * thp), s = sin(z.x * thp); pk += vec2(z.y * c - z.z * s, z.y * s + z.z * c); } }
    q = rotc(pk) + cn * 4.0; vKind = 1.0; vCol = vec4(PAPER, (on && l == 0) ? webK : 0.0);
  }
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(q, 0.014), 1.0);
}
"""
    fs = r"""
in vec4 vCol; in vec2 vQ; in float vKind; in float vR; out vec4 x3d_FragColor;
void main(){
  float a = vCol.a;
  if (vKind < 0.5) a *= smoothstep(1.2, 0.3, abs(length(vQ) - vR));
  else if (vKind < 1.5) a *= smoothstep(1.0, 0.55, length(vQ));
  if (a < 0.004) discard; x3d_FragColor = vec4(vCol.rgb, a);
}
"""
    quad_shader("EpiShader", "the epicycles", vs, fs, 19 * 3, at, fields=zf)
    # the pen trail as a ribbon
    ns = 119; coords, idx, av = [], [], []
    for q in range(ns + 1):
        for side in (-1, 1): coords.append("0 0 0"); av.append(f"{q / ns:.5f} {side} 0 0")
    for q in range(ns):
        a0 = 2 * q; idx.append(f"{a0} {a0+1} {a0+3} {a0+2} -1")
    vs = LIB + VERT_IN + FPRE + r"""
uniform ivec4 x3d_Viewport;
in vec4 aA; out vec4 vCol;
void main(){
  tl(); float t = t_; float uu = aA.x, side = aA.y;
  bool on = t >= TF && t < TPC; float u = fU() * uu;
  float K = fK(u); vec2 pk = vec2(0.0); float thp = u * 6.2831853;
  for (int m = 0; m < 19; m++) { if (float(m) >= K) break; vec4 z = ZKU[m]; float c = cos(z.x * thp), s = sin(z.x * thp); pk += vec2(z.y * c - z.z * s, z.y * s + z.z * c); }
  vec2 px = rotc(pk);
  float u2 = max(0.0, u - 0.004); thp = u2 * 6.2831853; float K2 = fK(u2); vec2 p2 = vec2(0.0);
  for (int m = 0; m < 19; m++) { if (float(m) >= K2) break; vec4 z = ZKU[m]; float c = cos(z.x * thp), s = sin(z.x * thp); p2 += vec2(z.y * c - z.z * s, z.y * s + z.z * c); }
  vec2 d = px - rotc(p2); vec2 nm = normalize(vec2(-d.y, d.x) + vec2(1e-6));
  vec2 q = px + nm * side * 1.0;
  vCol = vec4(GOLD, on ? 0.85 * webK : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(q, 0.015), 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("PenShader", lfields() + "\n" + zf, vs, fs)
    add("the pen trail of the epicycles",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedFaceSet solid='false' coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/>\n      <FloatVertexAttribute name='aA' numComponents='4' value='{' '.join(av)}'/>\n    </IndexedFaceSet></Shape>")
    SHADERS.append("PenShader")
    # spectrum bars
    def at(i, ci):
        cx, cy = ((0, 0), (1, 0), (1, 1), (0, 1))[ci]; return {"aA": (i, cx, cy, ZK[i]["mag"])}
    vs = LIB + VERT_IN + FPRE + r"""
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); float t = t_; int l = int(aA.x); vQ = vec2(0.0); vKind = 0.0;
  bool on = t >= TF && t < TPC; float K = fK(fU());
  float hgt = min(90.0, aA.w * 1.6);
  vec2 q = vec2(300.0 + float(l) * 20.0 + aA.y * 12.0, 560.0 - aA.z * hgt);
  bool act = float(l) < K;
  vCol = vec4(act ? GOLD : PAPER, on ? (act ? 0.8 : 0.25) * webK : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(q, 0.012), 1.0);
}
"""
    quad_shader("SpectrumShader", "the spectrum bars |c_k|", vs, SOLID_FS, 19, at, fields=zf)
    ATL.add("f_spec", "|ĉₖ| · սպեկտր · spectrum, k = −9 … 9", 20)
    label("f_spec", 300, 450, col=C_PAPER, a=0.6, baseline=True, ts=TF, te=TPC, fi=0.01, fo=0.01, mode="web")
    ATL.add("f_k", "k = " + ", ".join(str(z["k"]) for z in ZK[:3]) + " …", 20)
    label("f_k", 300, 585, col=C_TEAL, a=0.8, baseline=True, ts=TF, te=TPC, fi=0.01, fo=0.01, mode="web")
    st = []
    for q in range(17):
        ts = TF + q * 7.2 / 17; te = TF + (q + 1) * 7.2 / 17 if q < 16 else TPC
        st.append((ts, te, str(3 + q if q < 17 else 19)))
    st[-1] = (st[-1][0], st[-1][1], "19"); 
    caption3("Fourier · էպիցիկլեր · epicycles redraw the PageRank shape · ", [(a_, b_, f"{3 + q}" if 3 + q < 20 else "19") for q, (a_, b_, _) in enumerate(st)], " of 19 harmonics", key="cfo")

def poincare():
    TPC, TSV = D["TPC"], D["TSV"]
    # boundary of the disk
    def at(i, ci): cx, cy = CORN[ci]; return {"aA": (cx, cy, 0, 0)}
    vs = LIB + VERT_IN + r"""
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); vec2 cn = aA.xy; vQ = cn * 262.0; vKind = 0.0;
  bool on = t_ >= TPC && t_ < TSV; vCol = vec4(GOLD, on ? 1.0 : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(vec2(960.0, 345.0) + cn * 262.0, 0.013), 1.0);
  vKind = poinK;
}
"""
    fs = r"""
in vec4 vCol; in vec2 vQ; in float vKind; out vec4 x3d_FragColor;
const vec3 GOLD = vec3(0.88235, 0.67843, 0.4);
void main(){
  float r = length(vQ);
  float a = 0.4 * smoothstep(1.4, 0.3, abs(r - 250.0));
  float ang = atan(vQ.y, vQ.x) * 200.0;
  a += 0.15 * smoothstep(1.4, 0.3, abs(r - 200.0)) * (mod(ang, 8.0) < 2.0 ? 1.0 : 0.0);
  a *= vCol.a * vKind;
  if (a < 0.003) discard; x3d_FragColor = vec4(GOLD, a);
}
"""
    quad_shader("DiskShader", "the Poincare disk boundary", vs, fs, 1, at)
    # geodesic chords: 17 samples per pair, drawn as line strips
    pairs = [(i, j) for i in range(N) for j in range(i + 1, N)]
    coords, idx = [], []
    for (i, j) in pairs:
        base = len(coords)
        for q in range(17): coords.append(f"{i} {j} {q / 16:.4f}")
        idx.append(" ".join(str(base + q) for q in range(17)) + " -1")
    vs = LIB + ATTLIB + VERT_IN + r"""
out vec4 vCol;
vec2 geo(vec2 p, vec2 q, float u){
  float pp2 = dot(p, p); vec2 pp = p / pp2;
  float a1 = 2.0 * (q.x - p.x), b1 = 2.0 * (q.y - p.y), c1 = dot(q, q) - pp2;
  float a2 = 2.0 * (pp.x - p.x), b2 = 2.0 * (pp.y - p.y), c2 = dot(pp, pp) - pp2;
  float det = a1 * b2 - a2 * b1;
  if (abs(det) < 1e-6 || abs(p.x * q.y - p.y * q.x) < 1e-3) return mix(p, q, u);
  vec2 c = vec2((c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det);
  float rho = length(p - c), s0 = atan(p.y - c.y, p.x - c.x);
  float dl = atan(q.y - c.y, q.x - c.x) - s0;
  if (dl > PI) dl -= 6.2831853; if (dl < -PI) dl += 6.2831853;
  return c + rho * vec2(cos(s0 + u * dl), sin(s0 + u * dl));
}
void main(){
  tl(); float t = t_; int i = int(x3d_Vertex.x), j = int(x3d_Vertex.y); float u = x3d_Vertex.z;
  vec3 pi_ = lstate(i, t).pos, pj = lstate(j, t).pos;
  vec2 p = (vec2(pi_.x * 100.0 + 960.0, 540.0 - pi_.y * 100.0) - vec2(960.0, 345.0)) / 250.0, q = (vec2(pj.x * 100.0 + 960.0, 540.0 - pj.y * 100.0) - vec2(960.0, 345.0)) / 250.0;
  vec2 g = geo(p, q, u);
  float w = (attn(i, j) + attn(j, i)) * 0.5;
  float al = (0.025 + 0.42 * w * w) * webK; vec3 col = GOLD;
  vCol = vec4(col, min(1.0, al * 1.7) * poinK);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(vec2(960.0, 345.0) + g * 250.0, -0.003), 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("GeodesicShader", lfields() + "\n" + sfnode_tex("ATT", "glyphs/att.png", nearest=True), vs, fs)
    add("the chords as hyperbolic geodesics, orthogonal to the boundary",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("GeodesicShader")
    ATL.add("p_cap", "Poincaré · հիպերբոլական ներդրում · hyperbolic embedding · chords become geodesics ⟂ the boundary · curvature −1", 20)
    label("p_cap", 960, 612, col=C_PAPER, a=0.6, baseline=True, align="c", ts=TPC, te=TSV, fi=0.01, fo=0.01, mode="web")

def svd():
    TSV, TSV2 = D["TSV"], D["TSV2"]; KM = D["KM"]
    for (x, y, w_, h_) in ((700, 345, 520, 1), (960, 120, 1, 450)): label("solid", x, y, col=C_PAPER, a=0.18, mode="svd", wpx=w_, hpx=h_)
    ATL.add("v_u2", "u₂", 20); ATL.add("v_u3", "u₃", 20)
    label("v_u2", 1226, 350, col=C_PAPER, a=0.5, baseline=True, mode="svd"); label("v_u3", 966, 116, col=C_PAPER, a=0.5, baseline=True, mode="svd")
    # k-means centroids (crosses) and the thread from each letter to its centroid
    cent = ", ".join(f"{f(c['x'])} {f(c['y'])}" for it in KM for c in it["cent"])
    kf = f"        <field name='KMC' type='MFVec2f' accessType='inputOutput' value='{cent}'/>"
    CLS = ", ".join(" ".join(f(v / 255) for v in c[1]) for c in D["CLASSES"])
    kf += f"\n        <field name='CLSC' type='MFVec3f' accessType='inputOutput' value='{CLS}'/>"
    pre = "uniform vec2 KMC[28]; uniform vec3 CLSC[4];\n"
    # crosses: 4 centroids x 2 strokes as thin quads
    def at(i, ci):
        k, st_ = divmod(i, 2); cx, cy = CORN[ci]; return {"aA": (k, st_, cx, cy)}
    vs = LIB + VERT_IN + pre + r"""
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){
  tl(); int k = int(aA.x); float st_ = aA.y; vec2 cn = aA.zw; vQ = cn; vKind = 0.0;
  bool on = svdJ >= 0.0; int j = int(max(svdJ, 0.0));
  vec2 c = KMC[j * 4 + k];
  vec2 dir = st_ < 0.5 ? vec2(1.0, 1.0) : vec2(1.0, -1.0); vec2 nm = vec2(-dir.y, dir.x) / 1.4142;
  vec2 q = c + dir / 1.4142 * cn.x * 14.1 + nm * cn.y * 1.0;
  vCol = vec4(CLSC[k], on ? 0.9 * svdK : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(W(q, 0.014), 1.0);
}
"""
    quad_shader("CentroidShader", "k-means centroids", vs, SOLID_FS, 8, at, fields=kf)
    coords, idx = [], []
    for i in range(N):
        base = len(coords); coords.append(f"{i} 0 0"); coords.append(f"{i} 1 0"); idx.append(f"{base} {base+1} -1")
    vs = LIB + VERT_IN + pre + r"""
out vec4 vCol;
void main(){
  tl(); int i = int(x3d_Vertex.x); bool on = svdJ >= 0.0; int j = int(max(svdJ, 0.0));
  int a = (int(LD[i].w) >> (2 * j)) & 3;
  vec3 pw = lstate(i, t_).pos; vec2 c = KMC[j * 4 + a];
  vCol = vec4(CLSC[a], on ? 0.22 * svdK : 0.0);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(x3d_Vertex.y < 0.5 ? pw : W(c, 0.0), 1.0);
}
"""
    fs = "in vec4 vCol; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003) discard; x3d_FragColor = vCol; }\n"
    sh = shader("ClusterShader", lfields() + "\n" + kf, vs, fs)
    add("threads from each letter to its k-means centroid",
        f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
        f"    <IndexedLineSet coordIndex='{' '.join(idx)}'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append("ClusterShader")
    # caption states: sampled every 0.25 s, identical neighbours merged
    states = []
    for q in range(40):
        tau = q * 0.25 + 0.01; R = 1 + min(5, int(tau / 10 * 6)); J = max(0, min(6, int(math.floor(tau - 3))))
        txt = f"SVD · W ≈ Σ σₗ uₗ vₗᵀ · rank k = {R} · ‖W − Wₖ‖_F = {cm(D['WKres'][R])}" + f" · k-means k = 4 · iteration {J} · inertia {round(KM[J]['inertia'] / 1000)}k"
        if states and states[-1][2] == txt: states[-1] = (states[-1][0], TSV + (q + 1) * 0.25, txt)
        else: states.append((TSV + q * 0.25, TSV + (q + 1) * 0.25, txt))
    states[-1] = (states[-1][0], TSV2, states[-1][2])
    caption_full(states, key="csv")


def plate():
    S_ = D["S"]; TT_ = D["TT"]
    vs = rect_vs(590, 586, 81, 81, 0.02, "out float vFade; out float vSpot;", "vFade = (spot >= 0.0) ? min(1.0, spotK * 4.0) * (1.0 - cl((spotK - 0.85) / 0.15)) : 0.0; vSpot = spot;", kill="vFade <= 0.0")
    fs = r"""
in vec2 vP; in float vA; in float vFade; in float vSpot; out vec4 x3d_FragColor;
const vec3 TEAL = vec3(0.78824, 0.93725, 0.91373), PAPER = vec3(0.9529, 0.9490, 0.9490), GROUND = vec3(0.10588, 0.10196, 0.10196);
void main(){
  if (vFade <= 0.0) discard;
  vec2 p = (vP - vec2(590.0, 586.0)) / 81.0;
  float n = mod(vSpot, 9.0) + 1.0, m = floor(vSpot / 9.0) + 1.0;
  float f = (n == m) ? cos(n * 3.14159265 * p.x) * cos(m * 3.14159265 * p.y) : cos(n * 3.14159265 * p.x) * cos(m * 3.14159265 * p.y) - cos(m * 3.14159265 * p.x) * cos(n * 3.14159265 * p.y);
  float sand = exp(-pow(f / 0.16, 2.0));
  float edge = min(min(p.x, 1.0 - p.x), min(p.y, 1.0 - p.y)) * 81.0;
  vec3 col = mix(GROUND, TEAL, sand * 0.85); float a = 0.55 + 0.4 * sand;
  if (edge < 1.0) { col = PAPER; a = 0.3; }
  x3d_FragColor = vec4(col, a * vFade);
}
"""
    rect_shape("PlateShader", "the spotlit letter as a Chladni figure of the stone: mode (n, m) = (column + 1, row + 1)", vs, fs)
    for k in range(N):
        n, m = k % 9 + 1, k // 9 + 1
        ATL.add(f"pl_{k}", f"ձայն · mode ({n}, {m}) · f ∝ √{n * n + m * m}", 20)
        ts = TT_ + k * S_
        label(f"pl_{k}", 590 + 81 + 14, 630, col=C_TEAL, a=0.7, baseline=True, ts=ts, te=ts + S_, fi=S_ * 0.25, fo=S_ * 0.15)


# =====================================================================================================================
# 9. the medieval interludes: the Lord's Prayer in Grabar, letters are numbers, Shirakatsi's table
# =====================================================================================================================
def measure_slots(lines, size, y0, pitch, wght=400, spacing=4.0):
    from landing_text import font as _f
    ft = _f("arm", size, wght); slots = []; word = 0
    for li, line in enumerate(lines):
        chars = list(line); widths = [ft.getlength(ch) / SC + spacing for ch in chars]; total = sum(widths) - spacing
        x = 960 - total / 2
        for ch, w_ in zip(chars, widths):
            if ch == " ": word += 1
            else: slots.append(dict(ch=ch, x=x + (w_ - spacing) / 2, y=y0 + li * pitch, src=LET.index(ch) if ch in LET else -1, word=word))
            x += w_
        word += 1
    return slots

PRAYER = ["ՀԱՅՐ ՄԵՐ, ՈՐ ՅԵՐԿԻՆՍ ԵՍ,", "ՍՈՒՐԲ ԵՂԻՑԻ ԱՆՈՒՆ ՔՈ,", "ԵԿԵՍՑԷ ԱՐՔԱՅՈՒԹԻՒՆ ՔՈ,", "ԵՂԻՑԻՆ ԿԱՄՔ ՔՈ, ՈՐՊԷՍ ՅԵՐԿԻՆՍ ԵՒ ՅԵՐԿՐԻ,",
          "ԵՒ ԹՈՂ ՄԵԶ ԶՊԱՐՏԻՍ ՄԵՐ,", "ՈՐՊԷՍ ԵՒ ՄԵՔ ԹՈՂՈՒՄՔ ՄԵՐՈՑ ՊԱՐՏԱՊԱՆԱՑ,", "ԵՒ ՄԻ ՏԱՆԻՐ ԶՄԵԶ Ի ՓՈՐՁՈՒԹԻՒՆ,", "ԱՄԷՆ։"]
PRAYER = [ln.replace("։", ",") for ln in PRAYER]              # the glyph atlas has the comma as its only punctuation tile
PGDT = 0.055

def prayer():
    slots = measure_slots(PRAYER, 34, 140, 42)
    NG = len(slots)
    writing_act("P", slots, PGDT, PRAYER_DUR, "T_", PRA0, PRA1, 24.0, 34.0, ns=9, nprev=2)
    json.dump(dict(slots=slots, PRA0=PRA0, PRA1=PRA1, GDT=PGDT), open("scratch/prayer.json", "w", encoding="utf-8"), ensure_ascii=False)
    t_title = PRA0 + 0.2
    ATL.add("pr_en1", "Our Father, who art in heaven, hallowed be thy name; thy kingdom come;", 22)
    ATL.add("pr_en2", "thy will be done, as in heaven, so on earth; and forgive us our debts, as we forgive our debtors;", 22)
    ATL.add("pr_en3", "and lead us not into temptation. Amen.", 22)
    ATL.add("pr_ref", "Հայր մեր · Matthew 6:9–13 · Classical Armenian (Grabar) · one line is left out: its Օ is one of two letters added in the Middle Ages, not among Mashtots' 36", 18)
    ts = PRA0 + 1 + NG * PGDT + 0.9; te = PRA1 - 0.3
    for q, (key, y, col, a) in enumerate((("pr_en1", 472, C_PAPER, 0.75), ("pr_en2", 498, C_PAPER, 0.75), ("pr_en3", 524, C_PAPER, 0.75), ("pr_ref", 554, C_GOLD, 0.8))):
        label(key, 960, y, col=col, a=a, baseline=True, align="c", clock=2, ts=ts + q * 0.5, te=te, fi=1.0, fo=1.0)

def numerals():
    ts, te = NUM0 + 0.3, NUM1 - 0.2
    ATL.add("n_title", "Տառերը թվեր են", 64, wght=300)
    label("n_title", 144, 150, baseline=True, clock=2, ts=ts, te=te, fi=0.9, fo=1.0, rise=14, ease_in=True)
    for q, ln in enumerate(("Letters are numbers — the alphabet of 405", "was already a cipher: nine units, nine tens,", "nine hundreds, nine thousands")):
        ATL.add(f"n_sub{q}", ln, 22); label(f"n_sub{q}", 144, 196 + q * 28, col=NEUTRAL(165), baseline=True, clock=2, ts=ts + 0.3, te=te, fi=0.9, fo=1.0)
    for i in range(N):
        val = str((i % 9 + 1) * 10 ** (i // 9)); key = f"n_v{i}"; ATL.add(key, val, 20)
        hi = LET[i] in "ՆԵ"
        label(key, 30, -ATL.size(key)[1] / 2, col=C_PAPER if hi else C_GOLD, a=0.85 if hi else 0.7, anchor=i, clock=2, ts=ts + 0.6, te=te, fi=0.8, fo=1.0)
    for k, (n, en) in enumerate(EQS):
        ATL.add(f"n_eq{k}", f"{n} = {to_arm(n)}", 34, wght=300); ATL.add(f"n_en{k}", en, 20)
        y = 226 + k * 92
        label(f"n_eq{k}", 1250, y, baseline=True, clock=2, ts=EQ_T[k], te=te, fi=0.6, fo=1.0, rise=10, ease_in=True)
        label(f"n_en{k}", 1250, y + 30, col=NEUTRAL(165), baseline=True, clock=2, ts=EQ_T[k] + 0.2, te=te, fi=0.6, fo=1.0)

def shirakatsi():
    ts, te = SHI0 + 0.3, SHI1 - 0.2
    ATL.add("s_title", "Շիրակացու աղյուսակը", 56, wght=300)
    label("s_title", 144, 150, baseline=True, clock=2, ts=ts, te=te, fi=0.9, fo=1.0, rise=14, ease_in=True)
    for q, ln in enumerate(("Shirakatsi's table — Anania Shirakatsi's", "multiplication, 7th c., recomputed in his", "numerals; his arithmetic survives in the", "Matenadaran's oldest paper manuscript (971)")):
        ATL.add(f"s_sub{q}", ln, 22); label(f"s_sub{q}", 144, 196 + q * 28, col=NEUTRAL(165), baseline=True, clock=2, ts=ts + 0.3, te=te, fi=0.9, fo=1.0)
    x0, y0, cw, ch = 560, 112, 84, 44
    for r in range(10):
        for c in range(10):
            txt = "×" if r == 0 and c == 0 else to_arm(r or c) if (r == 0 or c == 0) else to_arm(r * c)
            key = f"sh_{txt}"; ATL.add(key, txt, 27, wght=300)
            col = C_GOLD if (r == 0 or c == 0) and (r or c) else C_PAPER if (r == 0 and c == 0) else C_TEAL if r == c else C_PAPER
            label(key, x0 + c * cw + cw / 2, y0 + r * ch + 31, col=col, a=0.9 if r == c or r == 0 or c == 0 else 0.78, baseline=True, align="c", clock=2, ts=SHI0 + 0.9 + (r * 10 + c) * 0.045, te=te, fi=0.25, fo=0.9)
    for k in range(11):                         # a faint ruling of the table
        label("solid", x0, y0 + k * ch - 2, col=C_PAPER, a=0.10, clock=2, ts=SHI0 + 0.6, te=te, fi=0.8, fo=0.9, wpx=10 * cw, hpx=1)
        label("solid", x0 + k * cw, y0 - 2, col=C_PAPER, a=0.10, clock=2, ts=SHI0 + 0.6, te=te, fi=0.8, fo=0.9, wpx=1, hpx=10 * ch + 2)


# =====================================================================================================================
# 10. the pre-training finale: 20 bars at 128 BPM. the bill, one word in many shapes, the law (the drop), the Armenian-only floor
# =====================================================================================================================
def curve_shape(name, comment, pts, t0, t1, win, color="GOLD", alpha=0.85, dashed=False, z=0.021):
    """a polyline (world x, y per point) revealed from its first point to its last between real times t0 and t1; visible only inside win=(ta, tb)"""
    n = len(pts)
    coords = [f"{f(x)} {f(y)} {k}" for k, (x, y) in enumerate(pts)]
    vs = LIB + VERT_IN + f"""
out vec4 vCol; out float vK;
void main(){{
  tl();
  float p = cl((T_ - {t0:.4f}) / {t1 - t0:.4f}), win = cl((T_ - {win[0]:.4f}) / 0.3) * (1.0 - cl((T_ - ({win[1]:.4f} - 0.5)) / 0.5));
  float a = x3d_Vertex.z <= p * {n - 1}.0 ? {alpha} * win : 0.0;
  vK = x3d_Vertex.z; vCol = vec4({color}, a);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(x3d_Vertex.xy, {z}, 1.0);
}}
"""
    fs = "in vec4 vCol; in float vK; out vec4 x3d_FragColor;\nvoid main(){ if (vCol.a < 0.003 " + ("|| mod(vK, 2.0) > 1.0 " if dashed else "") + ") discard; x3d_FragColor = vCol; }\n"
    sh = shader(name, lfields(), vs, fs)
    add(comment, f"    <Shape bboxCenter='0 0 0' bboxSize='40 24 16'><Appearance alphaMode='BLEND'>\n      <Material/>\n{sh}    </Appearance>\n"
                 f"    <IndexedLineSet coordIndex='{' '.join(str(k) for k in range(n))} -1'><Coordinate point='{', '.join(coords)}'/></IndexedLineSet></Shape>")
    SHADERS.append(name)

def dots_shape(name, comment, items, win):
    """discs with a ring: items = (x_world, y_world, t_on, hi). Appear at t_on, stay until the window ends."""
    def at(i, ci):
        x, y, t_on, hi = items[i]; cx, cy = CORN[ci]; return {"aA": (x, y, t_on, hi), "aB": (cx, cy, 0, 0)}
    vs = LIB + VERT_IN + f"""
in vec4 aA; in vec4 aB; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){{
  tl(); vec2 cn = aB.xy; vQ = cn; vKind = 2.0;
  float on = cl((T_ - aA.z) / 0.25) * (1.0 - cl((T_ - ({win[1]:.4f} - 0.5)) / 0.5));
  vCol = vec4(aA.w > 0.5 ? TEAL : GOLD, 0.9 * on);
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(aA.xy + cn * 0.11, 0.024, 1.0);
}}
"""
    fs = r"""
in vec4 vCol; in vec2 vQ; in float vKind; out vec4 x3d_FragColor;
void main(){ float r = length(vQ); float a = vCol.a * (smoothstep(1.0, 0.8, r) * (0.35 + 0.65 * smoothstep(0.55, 0.85, r))); if (a < 0.004) discard; x3d_FragColor = vec4(vCol.rgb, a); }
"""
    quad_shader(name, comment, vs, fs, len(items), at)

def moving_dot(name, comment, pts, t0, t1, win):
    n = len(pts)
    pf = f"        <field name='PTS' type='MFVec2f' accessType='inputOutput' value='{', '.join(f'{f(x)} {f(y)}' for x, y in pts)}'/>"
    def at(i, ci): cx, cy = CORN[ci]; return {"aA": (cx, cy, 0, 0)}
    vs = LIB + VERT_IN + f"""
uniform vec2 PTS[{n}];
in vec4 aA; out vec4 vCol; out vec2 vQ; out float vKind;
void main(){{
  tl(); vec2 cn = aA.xy; vQ = cn; vKind = 1.0;
  float p = cl((T_ - {t0:.4f}) / {t1 - t0:.4f}) * {n - 1}.0; int k0 = int(floor(p)), k1 = min({n - 1}, k0 + 1);
  vec2 b = mix(PTS[k0], PTS[k1], p - floor(p));
  float on = cl((T_ - {win[0]:.4f}) / 0.3) * (1.0 - cl((T_ - ({win[1]:.4f} - 0.5)) / 0.5));
  vCol = vec4(TEAL, 0.85 * on * (0.8 + 0.2 * kick));
  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(b.x + cn.x * 0.2, b.y + cn.y * 0.2, 0.026, 1.0);
}}
"""
    quad_shader(name, comment, vs, SOLID_FS, 1, at, fields=pf)

def finale():
    B, T0 = BAR, FIN0
    W_ = lambda b: T0 + b * B
    def fl(key, x, y, b0, b1, fi=0.5, fo=0.5, **kw): label(key, x, y, clock=2, ts=W_(b0), te=W_(b1), fi=fi, fo=fo, **kw)
    def txt(key, text, size, **kw): ATL.add(key, text, size, **kw)
    def tag(key, text): ATL.add(key, text, 18, tag=(None, 9, 3))
    # ---------- F0, bars 0-2: the title card; the letters scatter into noise ----------
    txt("f0_t", "Նախաուսուցում", 104, wght=300); txt("f0_s", "Pre-training, in Armenian", 44)
    fl("f0_t", 960, 336, 0.0, 2.0, baseline=True, align="c", fi=0.6, fo=0.9, rise=18, ease_in=True)
    fl("f0_s", 960, 398, 0.2, 2.0, col=NEUTRAL(190), baseline=True, align="c", fi=0.6, fo=0.9)
    # ---------- F1, bars 2-6: the bill ----------
    txt("f1_t", "Նույն փաստաթուղթը, այլ հաշիվ", 50, wght=300); txt("f1_s", "The same document, a different bill — Armenian ÷ English tokens, Universal Declaration", 22)
    tag("f1_g", "Չափված · Measured")
    fl("f1_t", 144, 134, 2.0, 6.0, baseline=True, fi=0.4, fo=0.7, rise=12, ease_in=True)
    fl("f1_s", 144, 168, 2.1, 6.0, col=NEUTRAL(165), baseline=True, fi=0.4, fo=0.7)
    fl("f1_g", 144, 184, 2.2, 6.0, col=C_ACC, fi=0.4, fo=0.7)
    BILL = [("o200k · GPT-4o, gpt-oss", 1.51, 0), ("Mistral Tekken", 1.74, 0), ("Gemma 3/4 · arm-gemma-ի հիմքը", 2.67, 1), ("DeepSeek V3/V4", 2.87, 0), ("Qwen 2.5/3", 5.41, 0), ("Llama 3.1", 8.73, 0), ("cl100k · GPT-4", 10.15, 0)]
    for i, (nm, v, hi) in enumerate(BILL):
        y = 238 + i * 46; b0 = 2.2 + 0.46 * i
        txt(f"f1_n{i}", nm, 20); fl(f"f1_n{i}", 144, y + 20, b0, 6.0, baseline=True, fi=0.3, fo=0.7, col=C_GOLD if hi else NEUTRAL(200))
        fl("solid", 540, y, b0, 6.0, col=C_GOLD if hi else C_PAPER, a=0.9 if hi else 0.5, grow=1, wpx=v * 100, hpx=26, fi=0.55, fo=0.7, ease_in=True)
        vt = f"{v:.2f}×".replace(".", ",")
        if hi:
            txt(f"f1_v{i}", vt + " — 25 լեզուներից ամենաթանկը · the highest premium of 25 languages", 20); fl(f"f1_v{i}", 540 + v * 100 + 14, y + 20, b0 + 0.3, 6.0, baseline=True, col=C_GOLD, fi=0.3, fo=0.7)
        else:
            txt(f"f1_v{i}", vt, 22); fl(f"f1_v{i}", 540 + v * 100 + 14, y + 20, b0 + 0.3, 6.0, baseline=True, col=C_PAPER, a=0.85, fi=0.3, fo=0.7)
    fl("solid", 640, 226, 2.3, 6.0, col=C_PAPER, a=0.25, wpx=1, hpx=336, fi=0.5, fo=0.7)
    txt("f1_ref", "անգլերեն = 1× · English", 18); fl("f1_ref", 652, 556, 2.4, 6.0, col=NEUTRAL(165), baseline=True, fi=0.4, fo=0.7)
    txt("f1_c1", "Անգլերենը՝ ~2 000 թոքեն, հայերենը՝ 3 038-ից 20 404․ հայերենն ասում է նույնը 1 352 բառով՝ 1 712-ի դիմաց։", 20)
    txt("f1_c2", "English ≈2,000 tokens, Armenian 3,038 to 20,404 — in 1,352 words to English's 1,712. The cost is the dictionary. §3.2.", 20)
    fl("f1_c1", 144, 604, 4.4, 6.0, col=C_PAPER, a=0.6, baseline=True, fi=0.5, fo=0.7); fl("f1_c2", 144, 630, 4.6, 6.0, col=NEUTRAL(165), baseline=True, fi=0.5, fo=0.7)
    # ---------- F2, bars 6-10: one word, many shapes ----------
    txt("f2_t", "Մի բառ, շատ կերպարանք", 50, wght=300); txt("f2_s", "One word, many shapes — արքայութիւն, ‘kingdom’, under six tokenizers", 22)
    tag("f2_g", "Չափված · Measured")
    fl("f2_t", 144, 134, 6.0, 10.0, baseline=True, fi=0.4, fo=0.7, rise=12, ease_in=True)
    fl("f2_s", 144, 168, 6.1, 10.0, col=NEUTRAL(165), baseline=True, fi=0.4, fo=0.7)
    fl("f2_g", 144, 184, 6.2, 10.0, col=C_ACC, fi=0.4, fo=0.7)
    from PIL import ImageDraw as _ID
    box = Image.new("L", (int(38 * SC), int(34 * SC)), 0); _ID.Draw(box).rounded_rectangle((1, 1, box.width - 2, box.height - 2), radius=int(4 * SC), outline=255, width=max(1, int(round(SC))))
    ATL.add_image("f2_box", box); ATL.rects["f2_box"][4:6] = [38, 34]
    TOK = [("o200k · GPT-4o, gpt-oss", ["ար", "ք", "այ", "ութիւն"], 4), ("Mistral Tekken", None, 6), ("Gemma 3/4", None, 7), ("Qwen 2.5/3 · մեկ տառ = մեկ թոքեն", list("արքայութիւն"), 11),
           ("Llama 3.1", None, 19), ("cl100k · GPT-4 · մեկ բայթ = մեկ թոքեն", None, 22)]
    for i, (nm, pieces, n) in enumerate(TOK):
        y = 226 + i * 54; b0 = 6.25 + 0.5 * i
        txt(f"f2_n{i}", nm, 18); fl(f"f2_n{i}", 144, y + 24, b0, 10.0, baseline=True, col=NEUTRAL(200), fi=0.3, fo=0.7)
        x = 600
        for q in range(n):
            if pieces:
                key = f"f2_p_{pieces[q]}"; ATL.add(key, pieces[q], 22, tag=(None, 9, 3)); w_ = ATL.size(key)[0]
            else: key = "f2_box"; w_ = 38
            fl(key, x, y + 2, b0 + 0.02 * q, 10.0, col=C_GOLD if pieces else C_PAPER, a=0.9 if pieces else 0.45, fi=0.15, fo=0.7)
            x += w_ + 6
        txt(f"f2_c{i}", str(n), 30); fl(f"f2_c{i}", 1620, y + 28, b0 + 0.3, 10.0, baseline=True, align="r", col=C_GOLD, fi=0.3, fo=0.7)
    txt("f2_s1", "19 910 vs 10 311 · տարբեր բառաձև 70 000 բառի մեջ՝ հայերեն և անգլերեն · distinct word forms in 70,000 words, Armenian vs English", 20)
    txt("f2_s2", "1,82 vs 2,64 tokens per word — an 8,000-slot tokenizer trained on 94,000 Armenian words (one novel) vs the best commercial one", 20)
    fl("f2_s1", 144, 604, 8.6, 10.0, col=C_PAPER, a=0.7, baseline=True, fi=0.5, fo=0.7); fl("f2_s2", 144, 630, 8.8, 10.0, col=NEUTRAL(185), baseline=True, fi=0.5, fo=0.7)
    # ---------- F3, bars 10-16: THE DROP. the law on log paper; the letters organise; the attention map sharpens; the corpus streams past ----------
    ts3, te3 = W_(10.0), W_(16.0)
    X0, X1, Y0, Y1 = 150.0, 1050.0, 530.0, 230.0
    gx = lambda lg: X0 + (lg - 11.0) / 2.5 * (X1 - X0); gy = lambda L_: Y0 - (L_ - 1.7) / 0.4 * (Y0 - Y1)
    E_, B_, be = 1.69, 410.7, 0.28
    Lf = lambda lg: E_ + B_ / 10 ** (lg * be)
    txt("f3_t", "Օրենքը", 52, wght=300); txt("f3_s", "The law — loss falls as a power of the data", 22); txt("f3_f", "L(D) = E + B·D⁻ᵝ", 30)
    fl("f3_t", 144, 134, 10.0, 16.0, baseline=True, fi=0.4, fo=0.7, rise=12, ease_in=True); fl("f3_s", 144, 168, 10.1, 16.0, col=NEUTRAL(165), baseline=True, fi=0.4, fo=0.7)
    fl("f3_f", 640, 134, 10.2, 16.0, col=C_GOLD, baseline=True, fi=0.4, fo=0.7)
    for L_ in (1.8, 1.9, 2.0, 2.1):
        fl("solid", X0, gy(L_), 10.1, 16.0, col=C_PAPER, a=0.08, wpx=X1 - X0, hpx=1, fi=0.4, fo=0.7)
        txt(f"f3_y{L_}", f"{L_:.1f}".replace(".", ","), 16); fl(f"f3_y{L_}", X0 - 12, gy(L_) + 5, 10.1, 16.0, col=NEUTRAL(150), baseline=True, align="r", fi=0.4, fo=0.7)
    fl("solid", X0, Y0, 10.0, 16.0, col=C_PAPER, a=0.3, wpx=X1 - X0, hpx=1, fi=0.4, fo=0.7); fl("solid", X0, Y1, 10.0, 16.0, col=C_PAPER, a=0.3, wpx=1, hpx=Y0 - Y1, fi=0.4, fo=0.7)
    for lg, nm in ((11, "10¹¹"), (12, "10¹²"), (13, "10¹³")):
        txt(f"f3_x{lg}", nm, 16); fl(f"f3_x{lg}", gx(lg), Y0 + 22, 10.1, 16.0, col=NEUTRAL(150), baseline=True, align="c", fi=0.4, fo=0.7)
    txt("f3_xu", "թոքեն · tokens", 16); fl("f3_xu", X1, Y0 + 22, 10.1, 16.0, col=NEUTRAL(150), baseline=True, align="r", fi=0.4, fo=0.7)
    curve = [(wxy(gx(11 + 2.5 * k / 99), gy(Lf(11 + 2.5 * k / 99)))) for k in range(100)]
    lg2 = math.log10(1.6e12); k2 = int(round((lg2 - 11) / 2.5 * 99))
    ta, tb = ts3 + 0.2 * B, te3 + 0.1
    curve_shape("LawCurveShader", "the data-scaling law L(D) = E + B D^-beta, drawn as the model trains", curve[:k2 + 1], ts3 + 0.3 * B, ts3 + 3.5 * B, (ta, tb))
    curve_shape("LawProjShader", "the projection beyond System 2 (dashed)", curve[k2:], ts3 + 3.5 * B, ts3 + 5.2 * B, (ta, tb), color="PAPER", alpha=0.55, dashed=True)
    moving_dot("LawDotShader", "the training run's current position on the curve", curve, ts3 + 0.3 * B, ts3 + 5.2 * B, (ta, tb))
    pts3 = [(1, 2e11, "Համակարգ 1 · 2024", "start"), (2, 1.6e12, "Համակարգ 2 · այս երեկո · tonight", "c"), (3, 2e13, "Համակարգ 3 · նախագիծ · projected", "r")]
    items = []
    for q, lgx, lab, al_ in [(a_, math.log10(b_), c_, d_) for a_, b_, c_, d_ in pts3]:
        x, y = gx(lgx), gy(Lf(lgx)); prog = (lgx - 11) / 2.5
        t_on = ts3 + 0.3 * B + prog * (5.2 - 0.3) * B + 0.1
        items.append((*wxy(x, y), t_on, 1 if q == 2 else 0))
        ATL.add(f"f3_p{q}", lab, 18)
        label(f"f3_p{q}", x, y - 26, clock=2, ts=t_on, te=te3, fi=0.3, fo=0.7, col=C_GOLD if q == 2 else C_PAPER, baseline=True, align="l" if al_ == "start" else "c" if al_ == "c" else "r")
    dots_shape("LawPointsShader", "the three points of the law (System 1, tonight, projected)", items, (ts3, te3))
    # the counter: tokens seen and loss, about 8 a second
    nst = int((5.2 - 0.3) * B * 6)
    for q in range(nst):
        ta_ = ts3 + 0.3 * B + q / 6.0; frac = min(1.0, (q + 0.5) / 6.0 / ((5.2 - 0.3) * B)); lgx = 11 + 2.5 * frac; Dv = 10 ** lgx
        e = int(math.floor(lgx)); m = Dv / 10 ** e; sup = {11: "¹¹", 12: "¹²", 13: "¹³"}[e]
        s_ = f"D = {m:.1f}·10{sup} թոքեն · L = {Lf(lgx):.3f}".replace(".", ",")
        ATL.add(f"f3_k{q}", s_, 20)
        label(f"f3_k{q}", X1, 262, clock=2, ts=ta_, te=ta_ + 1 / 6.0 + 0.001 if q < nst - 1 else te3, fi=0.01, fo=0.01, col=C_GOLD, baseline=True, align="r")
    txt("f3_cap", "E = 1,69 · B = 410,7 · β = 0,28 — տվյալների մասշտաբավորման հրատարակված համադրումը (Hoffmann et al., 2022)։", 18)
    txt("f3_cap2", "The published data-scaling fit; the three points are placeholders until the launch runs are final.", 18)
    fl("f3_cap", 144, 604, 12.0, 16.0, col=C_PAPER, a=0.6, baseline=True, fi=0.5, fo=0.7); fl("f3_cap2", 144, 628, 12.1, 16.0, col=NEUTRAL(165), baseline=True, fi=0.5, fo=0.7)
    # the corpus streaming past: the vocabulary of the 36 words, scrolling at different speeds
    words = [d[3] for d in DATA]
    for q, (sp, y_) in enumerate(((110, 62), (-90, 78), (80, 642), (-120, 658))):
        rot = words[q * 9:] + words[:q * 9]
        keyA, keyB = f"f3_w{q}a", f"f3_w{q}b"
        ATL.add(keyA, "  ·  ".join(rot[:18]) + "  ·  ", 16, wght=300); ATL.add(keyB, "  ·  ".join(rot[18:]) + "  ·  ", 16, wght=300)
        wA, wB = ATL.size(keyA)[0], ATL.size(keyB)[0]; x0 = (1920 - (wA + wB)) if sp > 0 else 0
        for key, xx in ((keyA, x0), (keyB, x0 + wA)):
            label(key, xx, y_, col=C_GOLD, a=0.16, clock=2, ts=ts3, te=te3 + B, fi=0.6, fo=1.2, grow=2, rise=sp)
    # ---------- F4, bars 16-20: the Armenian-only floor ----------
    ts4, te4 = W_(16.0), W_(20.0)
    X4 = lambda lg: 150.0 + (lg - 7.7) / 2.6 * 900.0; Y4 = lambda b_: 530.0 - (b_ - 0.42) / 0.34 * 300.0
    bpb = lambda lg: 4.9e5 * 10 ** (-0.795 * lg) + 0.439
    txt("f4_t", "Որքան մեծ կարող է լինել հայկական ուղեղը", 44, wght=300); txt("f4_s", "How big an Armenian-only model can be — bits per byte against parameters", 22); txt("f4_f", "bpb(N) = 4,9·10⁵·N⁻⁰·⁷⁹⁵ + 0,439", 28)
    tag("f4_g1", "Հաստատված · Established"); tag("f4_g2", "Գնահատական · Estimate")
    fl("f4_t", 144, 134, 16.0, 20.0, baseline=True, fi=0.4, fo=0.8, rise=12, ease_in=True); fl("f4_s", 144, 166, 16.1, 20.0, col=NEUTRAL(165), baseline=True, fi=0.4, fo=0.8)
    fl("f4_f", 1740, 134, 16.2, 20.0, col=C_GOLD, baseline=True, align="r", fi=0.4, fo=0.8)
    fl("f4_g1", 144, 182, 16.2, 20.0, col=C_ACC, fi=0.4, fo=0.8); fl("f4_g2", 144 + ATL.size("f4_g1")[0] + 10, 182, 16.3, 20.0, col=C_ACC, fi=0.4, fo=0.8)
    for b_ in (0.45, 0.55, 0.65, 0.75):
        fl("solid", 150, Y4(b_), 16.1, 20.0, col=C_PAPER, a=0.08, wpx=900, hpx=1, fi=0.4, fo=0.8)
        txt(f"f4_y{b_}", f"{b_:.2f}".replace(".", ","), 16); fl(f"f4_y{b_}", 138, Y4(b_) + 5, 16.1, 20.0, col=NEUTRAL(150), baseline=True, align="r", fi=0.4, fo=0.8)
    fl("solid", 150, 530, 16.0, 20.0, col=C_PAPER, a=0.3, wpx=900, hpx=1, fi=0.4, fo=0.8); fl("solid", 150, 230, 16.0, 20.0, col=C_PAPER, a=0.3, wpx=1, hpx=300, fi=0.4, fo=0.8)
    for lg, nm in ((8, "10⁸"), (9, "10⁹"), (10, "10¹⁰")):
        ATL.add(f"f4_x{lg}", nm, 16); fl(f"f4_x{lg}", X4(lg), 552, 16.1, 20.0, col=NEUTRAL(150), baseline=True, align="c", fi=0.4, fo=0.8)
    txt("f4_xu", "N, պարամետր · parameters", 16); fl("f4_xu", 1050, 552, 16.1, 20.0, col=NEUTRAL(150), baseline=True, align="r", fi=0.4, fo=0.8)
    fit = [wxy(X4(7.845 + (9.0 - 7.845) * k / 59), Y4(bpb(7.845 + (9.0 - 7.845) * k / 59))) for k in range(60)]
    ext = [wxy(X4(9.0 + (10.3 - 9.0) * k / 40), Y4(bpb(9.0 + (10.3 - 9.0) * k / 40))) for k in range(41)]
    curve_shape("FloorFitShader", "the Armenian-only scaling fit, bits per byte against parameters", fit, ts4 + 0.4 * B, ts4 + 1.8 * B, (ts4, te4))
    curve_shape("FloorExtShader", "its extrapolation beyond the fitted range (dashed)", ext, ts4 + 1.8 * B, ts4 + 2.8 * B, (ts4, te4), color="PAPER", alpha=0.55, dashed=True)
    fl("solid", 150, Y4(0.439), 16.9, 20.0, col=C_TEAL, a=0.5, grow=1, wpx=900, hpx=1, fi=0.8, fo=0.8)
    txt("f4_fl", "հատակը՝ 0,439 · the data floor", 18); fl("f4_fl", 156, Y4(0.439) - 8, 17.1, 20.0, col=C_TEAL, baseline=True, fi=0.4, fo=0.8)
    xl = X4(math.log10(2.3e9)); fl("solid", xl, 232, 17.2, 20.0, col=C_PAPER, a=0.3, wpx=1, hpx=298, fi=0.5, fo=0.8)
    txt("f4_lm", "տվյալների սահմանը ≈ 2,3 մլրդ · the data limit", 18); fl("f4_lm", xl + 10, 252, 17.3, 20.0, col=NEUTRAL(185), baseline=True, fi=0.4, fo=0.8)
    P4 = [(7e7, "70 M", 1, 14, -14, "l", 17.0), (1e9, "1 B · համադրման եզր · fit range", 0, -14, -14, "r", 17.3), (1.3e9, "1,3 B · չափված 0,47", 1, -14, 24, "r", 17.6), (4.7e9, "4,7 B · ×2 → 0,005", 0, 14, -10, "l", 17.9)]
    items = []
    for q, (N_, lab, hi, dx, dy, al_, bb) in enumerate(P4):
        lg = math.log10(N_); x, y = X4(lg), Y4(bpb(lg)); items.append((*wxy(x, y), W_(bb), 1 if q == 2 else 0))
        ATL.add(f"f4_p{q}", lab, 18)
        label(f"f4_p{q}", x + dx, y + dy, clock=2, ts=W_(bb), te=te4, fi=0.3, fo=0.8, col=C_GOLD if q == 2 else C_PAPER, baseline=True, align="l" if al_ == "l" else "r")
    dots_shape("FloorPointsShader", "the measured and projected models on the floor curve", items, (ts4, te4))
    txt("f4_c1", "Համադրումը՝ [1], 70 մլն–1 մլրդ պարամետր․ եզրից դուրս՝ գնահատական։ Նոր տվյալները շարժում են հատակը, նոր պարամետրերը՝ ոչ։", 18)
    txt("f4_c2", "Beyond the fitted range, an estimate. New data moves the floor; parameters do not. §4.7.", 18)
    fl("f4_c1", 144, 604, 17.6, 18.55, col=C_PAPER, a=0.6, baseline=True, fi=0.5, fo=0.5); fl("f4_c2", 144, 628, 17.7, 18.55, col=NEUTRAL(165), baseline=True, fi=0.5, fo=0.5)
    txt("f4_h", "Սրբազան լեզուն կարող է դառնալ ծրագրավորման լեզու", 34, wght=300); txt("f4_he", "A sacred language can become a domain programming language — conjecture, testable", 22)
    fl("f4_h", 960, 614, 18.6, 20.0, baseline=True, align="c", fi=0.6, fo=0.7, rise=10, ease_in=True); fl("f4_he", 960, 650, 18.8, 20.0, col=C_GOLD, baseline=True, align="c", fi=0.6, fo=0.7)


def colophon():
    ts, te = COL0 + 0.4, COL1 - 0.3
    ATL.add("col_t", "Շնորհակալություն", 76, wght=300)
    ATL.add("col_a", f"Գրեցաւ ի թուին Հայոց {to_arm(2026 - 551)}, յԵրեւան, ի Մատենադարանի․ Մաշտոց Համակարգ 2։", 30, wght=300)
    ATL.add("col_e", "Written in the Armenian year 1475 — 2026 — at the Matenadaran, Yerevan. Mashtots System 2.", 22)
    label("col_t", 960, 300, baseline=True, align="c", clock=2, ts=ts, te=te, fi=1.0, fo=1.0, rise=14, ease_in=True)
    label("col_a", 960, 364, baseline=True, align="c", clock=2, ts=ts + 0.5, te=te, fi=1.0, fo=1.0)
    label("col_e", 960, 404, col=NEUTRAL(170), baseline=True, align="c", clock=2, ts=ts + 0.9, te=te, fi=1.0, fo=1.0)

# =====================================================================================================================
# assemble
# =====================================================================================================================
backdrop()
letters()
effects()
tour()
writing()
prayer()
numerals()
shirakatsi()
finale()
colophon()
plate()
space()
web()
pulses()
descent()
walk()
fourier()
poincare()
svd()
build_labels_A()
labels_mesh()


SECTIONS = [("stone", "Քար", "The stone", 0.0), ("helix", "Աստղագետի պարույրը", "The astronomer's helix", timeline.hold_start(SEGS, "lift")[0]),
            ("tour", "Տառ առ տառ", "The tour of 36", timeline.hold_start(SEGS, "tour")[0]), ("writing", "Գրությունը", "Writing 405", timeline.hold_start(SEGS, "write")[0]),
            ("prayer", "Հայր մեր", "The Lord's Prayer", PRA0), ("numbers", "Թվեր", "Letters are numbers", NUM0), ("embedding", "Տարածություն", "Embedding space", timeline.hold_start(SEGS, "space")[0]),
            ("graph", "Գրաֆ", "The alphabet as a graph", timeline.hold_start(SEGS, "web")[0]), ("pretraining", "Նախաուսուցում", "Pre-training in Armenian", FIN0),
            ("return", "Տուն", "Return", timeline.hold_start(SEGS, "line2")[0])]
json.dump(dict(cycle=CYCLE_REAL, bpm=timeline.BPM, sections=[dict(id=i, hy=h, en=e, t=round(t, 3)) for i, h, e, t in SECTIONS], shaders=sorted(set(SHADERS)),
               segments=[dict(name=g["name"], t=round(g["r0"], 3), dur=round(g["dur"], 3)) for g in SEGS]), open("sections.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

json.dump(dict(cycle=CYCLE_REAL, segs=SEGS, NUM0=NUM0, NUM1=NUM1, SHI0=SHI0, SHI1=SHI1, PRA0=PRA0, PRA1=PRA1, FIN0=FIN0, FIN1=FIN1, COL0=COL0, COL1=COL1, EQ_T=EQ_T, EQS=[e[0] for e in EQS],
               bpm=timeline.BPM, bar=timeline.BAR), open("scratch/timeline_real.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
out = []; w = out.append
w("<?xml version='1.0' encoding='UTF-8'?>")
w("<X3D profile='Immersive' version='4.0' xmlns:xsd='http://www.w3.org/2001/XMLSchema-instance' xsd:noNamespaceSchemaLocation='https://www.web3d.org/specifications/x3d-4.0.xsd'>")
w("  <head>\n    <component name='Shaders' level='1'/>\n    <component name='Texturing' level='2'/>\n    <component name='Sound' level='1'/>\n    <component name='ParticleSystems' level='3'/>")
w("    <meta name='title' content='mashtots-landing.x3d'/>")
w("    <meta name='description' content='Mashtots System 2, the landing page, as X3D: the 36 letters leave the painted stone, settle into a gilt line, lift into a turning helix inside the astronomer globe, and the alphabet is read as a graph. One TimeSensor fraction drives every shader; the numbers are the original JavaScript, run in Node and baked. No Script node.'/>")
w("    <meta name='creator' content='port of MashtotsLanding.dc.html; X3D by Claude for the x3d.io project, in the style of hagopjay Gobbler 3'/>")
w("    <meta name='generator' content='make_landing.py, landing_glsl.py, extract_landing_data.js'/>")
w("  </head>\n  <Scene>")
w(f"    <WorldInfo title='Mashtots System 2' info='&quot;the landing page as X3D, {CYCLE:.2f} s loop&quot;'/>")
w("    <NavigationInfo DEF='Nav' type='&quot;NONE&quot;' headlight='false'/>")
cam = " ".join(map(str, ARGS.cam)) if ARGS.cam else "0 0 15"
w(f"    <Viewpoint DEF='Cam' position='{cam}' fieldOfView='{FOV:.5f}' description='slide'/>")
w("    <Viewpoint DEF='CamHelix' position='7.5 3.2 7.5' orientation='-0.3331 0.9395 0.0793 0.4963' fieldOfView='0.8' description='the helix from the side'/>")
w("    <Viewpoint DEF='CamRing' position='0 0.6 8' orientation='1 0 0 0.0749' fieldOfView='0.8' description='the ring up close'/>")
w("    <Viewpoint DEF='CamStone' position='-1 1.2 6' orientation='-0.8941 -0.4477 -0.0149 0.0744' fieldOfView='0.8' description='the painted stone'/>")
w("    <Background skyColor='0.102 0.098 0.098'/>")
live = ARGS.freeze is None
w("    <!-- Both clocks start at load: a huge ProximitySensor fires when the viewer is in the scene, and its enterTime becomes their startTime. -->")
w("    <ProximitySensor DEF='Boot' size='100000 100000 100000'/>")
w(f"    <TimeSensor DEF='Clock' cycleInterval='{CYCLE_REAL:.3f}' loop='true'{' enabled=' + chr(39) + 'false' + chr(39) if live else ''}/>")
w(f"    <TimeSensor DEF='Intro' cycleInterval='{INTRO:.0f}' loop='true'{' enabled=' + chr(39) + 'false' + chr(39) if live else ''}/>")
if os.path.exists("landing_score.mp3") and os.environ.get("X3D_SOUND"):
    w("    <!-- The score (make_music.py), 193.31 s, the same length as the loop. It starts with the clocks; the viewer page turns the intensity up on the first click (browsers keep audio muted until then). -->")
    w("    <Sound DEF='ScoreSound' intensity='0' spatialize='false' maxBack='1000' maxFront='1000' minBack='1000' minFront='1000'><AudioClip DEF='Score' url='&quot;landing_score.mp3&quot;' loop='true' description='Mashtots landing score'/></Sound>")
w("    <!-- Seek input for the page's section tabs: a disabled TimeSensor whose cycleInterval (an event source SAI can write) is ROUTEd to every shader's toff. -->")
w("    <TimeSensor DEF='Seek' enabled='false' cycleInterval='0.001' loop='false'/>")
shader_names = SHADERS
_skip = [x for x in os.environ.get('SKIP', '').split(',') if x]
for comment, xml in shapes:
    if any(f"DEF='{x}'" in xml for x in _skip): continue
    w(f"    <!-- {comment} -->"); w(xml)
if ARGS.freeze is None:
    for n in shader_names:
        w(f"    <ROUTE fromNode='Clock' fromField='elapsedTime' toNode='{n}' toField='etime'/>")
    w("    <ROUTE fromNode='Intro' fromField='elapsedTime' toNode='LabelShader' toField='itime'/>")
    if os.path.exists("landing_score.mp3") and os.environ.get("X3D_SOUND"): w("    <ROUTE fromNode='Boot' fromField='enterTime' toNode='Score' toField='set_startTime'/>")
    for n in sorted(set(shader_names)): w(f"    <ROUTE fromNode='Seek' fromField='cycleInterval' toNode='{n}' toField='toff'/>")
    for ck in ("Clock", "Intro"):
        w(f"    <ROUTE fromNode='Boot' fromField='enterTime' toNode='{ck}' toField='set_startTime'/>")
        w(f"    <ROUTE fromNode='Boot' fromField='isActive' toNode='{ck}' toField='set_enabled'/>")
w("  </Scene>\n</X3D>")
open(ARGS.out, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("loop %.2f s (the deck's act time %.2f s); %d bytes -> %s" % (CYCLE_REAL, CYCLE, sum(len(s) + 1 for s in out), ARGS.out))
