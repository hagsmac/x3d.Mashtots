#!/usr/bin/env python3
"""Makes the re-timed generator from the APPROVED one, without touching it: reads ../../make_landing.py and ../../landing_glsl.py,
applies the patches below (each must match exactly once, or this stops), writes make_landing_retimed.py and landing_glsl.py here,
and copies landing_text.py unchanged. Re-run after any change to the originals; the diff stays small and readable.

What the patches do
  timeline    import timeline_retimed (presets, speed ramps) instead of timeline; the GLSL warp gains a rate at the END of each piece
              (act time is quadratic inside a piece, so slow motion eases in and out).
  vowels act  a new hold inside the spectral cut (preset "graph-expanded": 4 bars). Its factor vowK crossfades
                - the letters' drop from the deck's Fiedler value (LD.z) to the measured highest mode of the Grabar graph (LE.z, unused so far),
                - the chords' weights from the authored attention to the measured bigram weights (a 21st tile of att.png),
                - which chords cross the cut and the node colours,
                - the captions (graded "Measured", with the corpus and the one letter that disagrees).
              Data: ../data-graph/out/graph.json (run ../data-graph/grabar_graph.py first).
  helix       (the two helix fixes now live in make_landing.py itself, 28 Oct)
  output      default --out mashtots-landing-retimed.x3d; every other output (glyphs/, scratch/, sections.json) goes to the working
              directory, which build.sh sets to ./build, never the Landing folder.
"""
import os, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

def patch(src, dst, subs, replace_all=()):
    s = open(os.path.join(ROOT, src), encoding="utf-8").read()
    for old, new in subs:
        n = s.count(old)
        if n != 1: raise SystemExit(f"{src}: expected 1 match, found {n}: {old[:90]!r}")
        s = s.replace(old, new)
    for old, new, n_expected in replace_all:
        n = s.count(old)
        if n != n_expected: raise SystemExit(f"{src}: expected {n_expected} matches, found {n}: {old[:90]!r}")
        s = s.replace(old, new)
    open(os.path.join(HERE, dst), "w", encoding="utf-8").write(s)
    print(f"{src} -> {dst}: {len(subs)} patches")

FLOW_DEF = '\n# =====================================================================================================================\n# explore/retime: rank as light flowing along the chords (message passing from Ճ, then PageRank). Flows are the deck\'s own numbers:\n#   message passing  h(l+1)_i = sum_j W_ij h(l)_j      -> the flow j -> i in layer l is W_ij h(l)_j\n#   PageRank         r(k+1)_i = (1-d)/N + d sum_j r(k)_j W_ji   -> the flow j -> i in iteration k is d r(k)_j W_ji\n# The 90 heaviest directed chords of each act carry 5 particles each; a texture holds every chord\'s flow per layer / iteration.\n# The particles move in ACT time, so a speed ramp of the act slows or rushes them with everything else.\n# =====================================================================================================================\ndef flow():\n    import numpy as np\n    W = np.array(D["A"]["mean"]); PR = np.array(D["PR"]); MSG = np.array(D["MSG"]); d = 0.85\n    fm = np.array([[W[i, j] * MSG[l][j] for j in range(N)] for l in range(6) for i in range(N)]).reshape(6, N, N)       # fm[l, i, j]: j -> i\n    fp = np.array([[d * PR[k][j] * W[j, i] for j in range(N)] for k in range(15) for i in range(N)]).reshape(15, N, N)  # fp[k, i, j]: j -> i\n    pick = lambda F, n: [tuple(x) for x in np.argwhere(F.max(0) >= np.sort(F.max(0), axis=None)[-n])[:n]]\n    edges = [(i, j, 2) for i, j in pick(fm, 90)] + [(i, j, 1) for i, j in pick(fp, 90)]\n    im = Image.new("L", (len(edges), 21))\n    for e, (i, j, kind) in enumerate(edges):\n        for l in range(6): im.putpixel((e, l), int(round(255 * (fm[l, i, j] / fm.max()) ** 0.6)))\n        for k in range(15): im.putpixel((e, 6 + k), int(round(255 * (fp[k, i, j] / fp.max()) ** 0.6)))\n    im.save("glyphs/flow.png")\n    P_ = 5\n    def at(q, ci):\n        e, s_ = divmod(q, P_); i, j, kind = edges[e]; cx, cy = ((-1, -1), (1, -1), (1, 1), (-1, 1))[ci]\n        return {"aA": (j, i, e, s_ / P_), "aB": (cx, cy, kind, 0)}\n    coords, idx, attrs = quads(len(edges) * P_, at)\n    vs = LIB + VERT_IN + r"""\nuniform sampler2D FLOW;\nin vec4 aA; in vec4 aB;\nout vec4 vCol; out vec2 vQ; out float vMode;\nvoid main(){\n  tl(); float t = t_;\n  int j = int(aA.x), i = int(aA.y), e = int(aA.z); float off = aA.w, kind = aB.z; vec2 cn = aB.xy;\n  float w = 0.0, u = 0.0; vec3 col = GOLD;\n  if (kind > 1.5 && t >= TB2 && t < TSP) {                                   // message passing: a wave per layer, from j to i\n    float x = (t - TB2) / 1.5; int l = int(min(5.0, floor(x))); float mf = x - floor(x);\n    w = texelFetch(FLOW, ivec2(e, l), 0).r * cl((t - TB2) / 0.4) * (1.0 - cl((t - (TSP - 0.6)) / 0.6));\n    u = cl(mf * 1.35 - off * 0.35); col = TEAL; w *= sin(PI * u);\n  } else if (kind < 1.5 && t >= TP && t < TA) {                              // PageRank: a stream along each chord, iteration by iteration\n    float pk = min(14.0, (t - TP) / 6.0 * 14.0); int k0 = int(floor(pk)), k1 = min(14, k0 + 1);\n    w = mix(texelFetch(FLOW, ivec2(e, 6 + k0), 0).r, texelFetch(FLOW, ivec2(e, 6 + k1), 0).r, pk - floor(pk)) * cl((t - TP) / 0.5) * (1.0 - cl((t - (TA - 0.8)) / 0.8));\n    u = fract((t - TP) * 0.55 + off); w *= sin(PI * u);\n  }\n  vCol = vec4(col, min(1.0, 1.25 * pow(w, 0.8)) * webK); vQ = cn; vMode = 0.0;\n  vec3 a = lstate(j, t).pos, b = lstate(i, t).pos;\n  vec3 pos = mix(a, b, u) + vec3(cn * (4.5 + 6.0 * w) * 0.01, 0.01);\n  gl_Position = x3d_ProjectionMatrix * x3d_ModelViewMatrix * vec4(pos, 1.0);\n}\n"""\n    fx_shape("FlowShader", "rank as light flowing along the chords: message passing from Ճ, then PageRank (explore/retime)", vs, HEAD_NONE + POINT_FS, coords, idx, attrs,\n             fields=sfnode_tex("FLOW", "glyphs/flow.png", nearest=True))\n\n'

GLSL = [
 ("const float SRT[@NSEG@] = float[@NSEG@](@SRT@);",
  "const float SRT[@NSEG@] = float[@NSEG@](@SRT@);\nconst float SRE[@NSEG@] = float[@NSEG@](@SRE@);      // rate at the END of each piece (re-timed build: speed ramps)"),
 ("for (int i = 0; i < NSEG; i++) { if (tr < RB[i + 1] || i == NSEG - 1) { hold = SRT[i] == 0.0 ? 1.0 : 0.0; return SA[i] + (tr - RB[i]) * SRT[i]; } }",
  "for (int i = 0; i < NSEG; i++) { if (tr < RB[i + 1] || i == NSEG - 1) { float d = max(RB[i + 1] - RB[i], 1e-4), tau = tr - RB[i];\n"
  "    hold = (SRT[i] == 0.0 && SRE[i] == 0.0) ? 1.0 : 0.0; return SA[i] + tau * (SRT[i] + 0.5 * (SRE[i] - SRT[i]) * tau / d); } }"),
 ("const float COL0 = @COL0@, COL1 = @COL1@;", "const float COL0 = @COL0@, COL1 = @COL1@;\nconst float VOW0 = @VOW0@, VOW1 = @VOW1@;   // the measured-vowels act (a hold inside the spectral cut), real time; -1 = none"),
 ("float numK, shiK, finK, orgK, kick, finDim, finMap, colK;", "float numK, shiK, finK, orgK, kick, finDim, finMap, colK, vowK;"),
 ("  mapK = max(veil * (1.0 - hold_), finMap);",
  "  vowK = (T_ >= VOW0 && T_ < VOW1) ? ease(cl((T_ - VOW0) / BAR)) * (1.0 - ease(cl((T_ - (VOW1 - BAR)) / BAR))) : 0.0;\n"
  "  mapK = max(veil * (1.0 - hold_), finMap);"),
 ("p = mix(h, rw, webK); p.y -= specK * LD[i].z * 0.95;", "p = mix(h, rw, webK); p.y -= specK * mix(LD[i].z, LE[i].z, vowK) * 0.95;"),
]
GEN = [
 ("import timeline\n", "import timeline_retimed as timeline\n"),

 ('ap.add_argument("--out", default="mashtots-landing.x3d")', 'ap.add_argument("--out", default="mashtots-landing-retimed.x3d")'),
 ("_n, _rb, _sa, _srt = timeline.glsl_arrays(SEGS)", "_n, _rb, _sa, _srt, _sre = timeline.glsl_arrays(SEGS)"),
 ("CONSTS.update(NSEG=str(_n), NSEG1=str(_n + 1), RB=_rb, SA=_sa, SRT=_srt, CYCLER=CYCLE_REAL)",
  "CONSTS.update(NSEG=str(_n), NSEG1=str(_n + 1), RB=_rb, SA=_sa, SRT=_srt, SRE=_sre, CYCLER=CYCLE_REAL)\n"
  "try: VOW0, _vd = _hold(\"vowels\"); VOW1 = VOW0 + _vd\n"
  "except KeyError: VOW0 = VOW1 = -1.0\n"
  "CONSTS.update(VOW0=VOW0, VOW1=VOW1)\n"
  "MEAS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), \"../data-graph/out/graph.json\"), encoding=\"utf-8\"))   # Measured: the Grabar letter graph\n"
  "assert MEAS[\"order\"] == \"\".join(d[0] for d in D[\"DATA\"]), \"letter order\""),
 ('LE = [(SVDXY[i]["x"], SVDXY[i]["y"], 0, 0) for i in range(N)]',
  'LE = [(SVDXY[i]["x"], SVDXY[i]["y"], -0.75 * MEAS["fast_mode"][i], 0) for i in range(N)]      # z: the measured highest mode, vowels < 0 so that they RISE (at most 75 px)'),
 ('    att = Image.new("L", (36 * len(tiles), 36))',
  '    _B = MEAS["bigram"]; _P = [[_B[i][j] / max(1, sum(_B[i])) for j in range(N)] for i in range(N)]\n'
  '    tiles.append([[_P[i][j] / max(max(_P[i]), 1e-9) for j in range(N)] for i in range(N)])        # tile 20: measured bigram rows / row maximum\n'
  '    att = Image.new("L", (36 * len(tiles), 36))'),
 ("  float w = (attn(i, j) + attn(j, i)) * 0.5;\n  float al = (0.025 + 0.42 * w * w) * max(webK",
  "  float w = (attn(i, j) + attn(j, i)) * 0.5;\n"
  "  if (vowK > 0.0) w = mix(w, sqrt((texelFetch(ATT, ivec2(20 * 36 + j, i), 0).r + texelFetch(ATT, ivec2(20 * 36 + i, j), 0).r) * 0.5), vowK);\n"
  "  float al = (0.025 + 0.42 * w * w) * max(webK"),
 ("  float fi_ = LD[i].z, fj_ = LD[j].z;\n  if (specK > 0.0 && sign(fi_) != sign(fj_)) { col = PAPER; al = max(al, 0.14 * specK); }",
  "  float fi_ = mix(LD[i].z, LE[i].z, vowK), fj_ = mix(LD[j].z, LE[j].z, vowK);\n"
  "  if (specK > 0.0 && sign(fi_) != sign(fj_)) { col = PAPER; al = max(al, 0.14 * specK * (1.0 - vowK)); }   // measured act: only the real alternations shine"),
 ("col = LD[i].z > 0.0 ? GOLD : TEAL; al = 0.3; }", "col = mix(LD[i].z, LE[i].z, vowK) > 0.0 ? GOLD : TEAL; al = 0.3; }"),
 ("def pulses():", FLOW_DEF + "def pulses():"),
 ("\npulses()\ndescent()\n", "\npulses()\nflow()\ndescent()\n"),
 ("MODES = dict(none=0, veil=1, space=2, web=3, spec=4, poin=5, svd=6)", "MODES = dict(none=0, veil=1, space=2, web=3, spec=4, poin=5, svd=6, vow=7)"),
 ("float k = m < 0.5 ? 1.0 : m < 1.5 ? mapK : m < 2.5 ? spaceK : m < 3.5 ? webK : m < 4.5 ? specK : m < 5.5 ? poinK : svdK;",
  "float k = m < 0.5 ? 1.0 : m < 1.5 ? mapK : m < 2.5 ? spaceK : m < 3.5 ? webK * (1.0 - vowK) : m < 4.5 ? specK * (1.0 - vowK) : m < 5.5 ? poinK : m < 6.5 ? svdK : vowK;"),
 ('    label("spec_pos", 960, 90, col=C_GOLD, a=0.85, baseline=True, align="c", mode="spec"); label("spec_neg", 960, 640, col=C_TEAL, a=0.85, baseline=True, align="c", mode="spec")\n',
  '    label("spec_pos", 960, 90, col=C_GOLD, a=0.85, baseline=True, align="c", mode="spec"); label("spec_neg", 960, 640, col=C_TEAL, a=0.85, baseline=True, align="c", mode="spec")\n'
  '    # ---- the measured act: the Grabar graph\'s highest mode lifts the vowels (a hold inside the cut; every label here is graded Measured) ----\n'
  '    _nl = f"{MEAS[\'letters\']:,}".replace(",", " ")\n'
  '    ATL.add("vow_cap", f"չափված · Measured · Գրաբար, {_nl} տառ (UD CAVaL) · the graph\'s fastest mode alternates: vowel, consonant, vowel", 20)\n'
  '    ATL.add("vow_cap2", f"{round(36 * MEAS[\'fast_mode_agree_with_deck\'])} of 36 agree with the deck · Ւ alone is the consonant w in Grabar · {MEAS[\'bootstrap\'][\'resamples\']} resamples: every vowel on its side every time", 18)\n'
  '    ATL.add("vow_top", "ձայնավոր · vowels", 22); ATL.add("vow_bot", "բաղաձայն · consonants", 22)\n'
  '    label("vow_cap", 960, 612, col=C_PAPER, a=0.7, baseline=True, align="c", mode="vow", ts=TSP, te=TP, fi=0.01, fo=0.01)\n'
  '    label("vow_cap2", 960, 640, col=C_PAPER, a=0.5, baseline=True, align="c", mode="vow", ts=TSP, te=TP, fi=0.01, fo=0.01)\n'
  '    label("vow_top", 1300, 200, col=C_TEAL, a=0.9, baseline=True, mode="vow", ts=TSP, te=TP, fi=0.01, fo=0.01)\n'
  '    label("vow_bot", 1300, 520, col=C_GOLD, a=0.8, baseline=True, mode="vow", ts=TSP, te=TP, fi=0.01, fo=0.01)\n'),
]
# The two helix fixes (the armillary's branch threshold; 1-px lines with alpha x 1.6) were applied to make_landing.py itself on 28 Oct at the
# user's request (backup and checksums in ../helixfix/before/), so they are no longer patched here.
# The load-time fix (distinct placeholder coordinates) is in make_landing.py itself since 28 Oct (dummy()), so it is no longer patched here.
from camspec import GLSL_CAMSPEC, GEN_CAMSPEC        # the world camera and the spectral moments (see camspec.py)
GLSL += GLSL_CAMSPEC; GEN += GEN_CAMSPEC
if __name__ == "__main__":
    patch("landing_glsl.py", "landing_glsl.py", GLSL)
    patch("make_landing.py", "make_landing_retimed.py", GEN)
    shutil.copyfile(os.path.join(ROOT, "landing_text.py"), os.path.join(HERE, "landing_text.py")); print("landing_text.py copied")
