"""GLSL shared by every shader of the Landing port.

One number, `etime` (TimeSensor.elapsedTime, folded into the 193.31 s cycle), is the only input. Everything below derives the state of the
whole piece from it: the same timeline constants and easing as MashtotsLanding.dc.html, the helix (here in true 3D), the ring,
the letter layouts of every act, the tour spotlight. Shaders that need to know where a letter is (letters, chords, arcs, walkers,
labels) all call lstate().

Units: positions are computed in the deck's 1920 x 1080 pixel space (y down) and converted with W() to world units
(1 unit = 100 px, y up, the slide plane is z = 0, camera at z = 15 with fieldOfView 0.6913 so that plane maps 1:1 to the canvas).
"""

LIB = r"""
uniform float etime;      // seconds since load (TimeSensor.elapsedTime); the loop repeats every CYCLER s of real time
uniform float toff;
uniform float eyeX;       // explore: the stereo eye, routed from the Eye TimeSensor (1 = centre; left and right are 1 -+ half the separation)       // seek offset in seconds, set by the page's section tabs
const int NSEG = @NSEG@;  // the real-time timeline: segments of real time mapped onto the deck's act time (see timeline.py)
const float RB[@NSEG1@] = float[@NSEG1@](@RB@);
const float SA[@NSEG@] = float[@NSEG@](@SA@);
const float SRT[@NSEG@] = float[@NSEG@](@SRT@);
const float SRE[@NSEG@] = float[@NSEG@](@SRE@);      // rate at the END of each piece (re-timed build: speed ramps)
const float CYCLER = @CYCLER@;
const float BAR = @BAR@;
const float COL0 = @COL0@, COL1 = @COL1@;
const float VOW0 = @VOW0@, VOW1 = @VOW1@;   // the measured-vowels act (a hold inside the spectral cut), real time; -1 = none
const float NUM0 = @NUM0@, NUM1 = @NUM1@, SHI0 = @SHI0@, SHI1 = @SHI1@, FIN0 = @FIN0@, FIN1 = @FIN1@, ORG0 = @ORG0@, ORG1 = @ORG1@, BEAT = @BEAT@;
float warp(float tr, out float hold){
  for (int i = 0; i < NSEG; i++) { if (tr < RB[i + 1] || i == NSEG - 1) { float d = max(RB[i + 1] - RB[i], 1e-4), tau = tr - RB[i];
    hold = (SRT[i] == 0.0 && SRE[i] == 0.0) ? 1.0 : 0.0; return SA[i] + tau * (SRT[i] + 0.5 * (SRE[i] - SRT[i]) * tau / d); } }
  hold = 0.0; return 0.0;
}
const float CYCLE=@CYCLE@, T1=@T1@, TL=@TL@, TT=@TT@, TC=@TC@, TW2=@TW2@, TS2=@TS2@, TB2=@TB2@, TSP=@TSP@, TP=@TP@, TA=@TA@, TD=@TD@, TD2=@TD2@, TF=@TF@, TPC=@TPC@, TSV=@TSV@, TSV2=@TSV2@, TH=@TH@, T2=@T2@, T3=@T3@;
const float BEGIN=@BEGIN@, FLIGHT=@FLIGHT@, FLIGHTR=@FLIGHTR@, PACE=@PACE@;
const float PI=3.14159265;
const vec3 GOLD=vec3(0.88235,0.67843,0.4), DEEP=vec3(0.76078,0.55294,0.25490), TEAL=vec3(0.78824,0.93725,0.91373), PAPER=vec3(0.95294,0.94902,0.94902), GROUND=vec3(0.10588,0.10196,0.10196);
const vec2 HC=vec2(@HCX@, @HCY@);
const float HR=@HR@, HHH=@HHH@, HF=@HF@, RG=@RG@;
float ease(float p){ float q = -2.0 * p + 2.0; return p < 0.5 ? 4.0 * p * p * p : 1.0 - 0.5 * q * q * q; }
float cl(float v){ return clamp(v, 0.0, 1.0); }
vec3 W(vec2 px, float z){ return vec3((px.x - 960.0) * 0.01, (540.0 - px.y) * 0.01, z); }

uniform vec4 LA[36];   // stone cell xy, gilt-line slot xy                                  (px)
uniform vec4 LB[36];   // Bezier handle 1 xy, handle 2 xy                                    (px)
uniform vec4 LC[36];   // flight start t0, return start r0, phase ph, class (0 vowel 1 voiced 2 voiceless 3 aspirated)
uniform vec4 LD[36];   // embedding-space xy (px), Fiedler value, k-means assignments packed base 4 (7 iterations)
uniform vec4 LE[36];   // SVD-plane xy (px), unused

// ---- the timeline, evaluated once per vertex ----
float numK, shiK, finK, orgK, kick, finDim, finMap, colK, vowK;
float t_, T_, hold_, mapK, veil, shrink, spaceK, webK, specK, poinK, svdK, svdR, svdJ, spot, spotK;
bool inHelix;

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
void tl(){
  float tr = mod(etime + toff, CYCLER); T_ = tr;                                            // real time: rotations, shimmer
  float t = warp(tr, hold_); t_ = t;                                                         // act time: the deck's windows and flights
  inHelix = t >= TL && t < TH;
  veil = t < TL ? 0.0 : t < TT ? ease((t - TL) / 2.0) : t < TSV2 ? 1.0 : t < TH ? 1.0 - ease((t - TSV2) / 2.0) : 0.0;
  shrink = (t >= TC && t < TW2) ? ease(cl((t - TC) / 1.2)) * (1.0 - ease(cl((t - (TW2 - 1.2)) / 1.2))) : 0.0;
  spaceK = (t >= TW2 && t < TS2) ? ease(cl((t - TW2) / 1.6)) * (1.0 - ease(cl((t - (TS2 - 1.4)) / 1.4))) : 0.0;
  webK = (t >= TS2 && t < TSV2) ? ease(cl((t - TS2) / 1.6)) * (1.0 - ease(cl((t - (TSV2 - 1.4)) / 1.4))) : 0.0;
  poinK = (t >= TPC && t < TSV) ? ease(cl((t - TPC) / 1.4)) * (1.0 - ease(cl((t - (TSV - 1.2)) / 1.2))) : 0.0;
  svdK = (t >= TSV && t < TSV2) ? ease(cl((t - TSV) / 1.6)) * (1.0 - ease(cl((t - (TSV2 - 1.4)) / 1.4))) : 0.0;
  specK = (t >= TSP && t < TP) ? ease(cl((t - TSP) / 1.2)) * (1.0 - ease(cl((t - (TP - 1.0)) / 1.0))) : 0.0;
  svdR = (t >= TSV && t < TSV2) ? 1.0 + min(5.0, floor((t - TSV) / 10.0 * 6.0)) : 0.0;
  svdJ = (t >= TSV && t < TSV2) ? max(0.0, min(6.0, floor(t - TSV - 3.0))) : -1.0;
  spot = (t >= TT && t < TC) ? min(35.0, floor((t - TT) / PACE)) : -1.0;
  spotK = (t >= TT && t < TC) ? mod(t - TT, PACE) / PACE : 0.0;
  numK = (T_ >= NUM0 && T_ < NUM1) ? ease(cl((T_ - NUM0) / 1.4)) * (1.0 - ease(cl((T_ - (NUM1 - 1.4)) / 1.4))) : 0.0;
  shiK = (T_ >= SHI0 && T_ < SHI1) ? ease(cl((T_ - SHI0) / 1.0)) * (1.0 - ease(cl((T_ - (SHI1 - 1.0)) / 1.0))) : 0.0;
  finK = (T_ >= FIN0 && T_ < FIN1) ? ease(cl((T_ - FIN0) / 1.0)) * (1.0 - ease(cl((T_ - (FIN1 - 1.6)) / 1.6))) : 0.0;
  orgK = ease(cl((T_ - ORG0) / (ORG1 - ORG0)));
  kick = (T_ >= FIN0 && T_ < FIN1) ? pow(1.0 - fract((T_ - FIN0) / BEAT), 5.0) : 0.0;
  finDim = (T_ >= FIN0 && T_ < FIN1) ? max(ease(cl((T_ - (FIN0 + 1.6 * BAR)) / (0.4 * BAR))) * (1.0 - ease(cl((T_ - (FIN0 + 9.5 * BAR)) / (0.5 * BAR)))), 0.5 * ease(cl((T_ - (FIN0 + 16.0 * BAR)) / (0.5 * BAR)))) : 0.0;
  finMap = (T_ >= FIN0 && T_ < FIN1) ? ease(cl((T_ - (FIN0 + 9.8 * BAR)) / (0.6 * BAR))) * (1.0 - ease(cl((T_ - (FIN0 + 17.6 * BAR)) / (0.8 * BAR)))) : 0.0;
  colK = (T_ >= COL0 && T_ < COL1) ? ease(cl((T_ - COL0) / 0.9)) * (1.0 - ease(cl((T_ - (COL1 - 1.3)) / 1.3))) : 0.0;
  vowK = (T_ >= VOW0 && T_ < VOW1) ? ease(cl((T_ - VOW0) / BAR)) * (1.0 - ease(cl((T_ - (VOW1 - BAR)) / BAR))) : 0.0;
  mapK = max(veil * (1.0 - hold_), finMap);                                                                // the attention map hides while an interlude holds act time
  camera(); spectral();
}

// ---- where is letter i (and how big, how far back) at cycle time tt ----
struct Ls { vec3 pos; float s; float zpx; float pr; float st; };   // st: 0 at the stone, 1 flying out, 2 set, 3 flying home
vec3 helix3(int i, float sh, float T, out float zpx){
  float r = HR * (1.0 - 0.5 * sh), hh = HHH * (1.0 - 0.5 * sh), cy = HC.y + 108.0 * sh;
  float a = float(i) / 36.0 * PI * 8.0 + T * 0.22, X = r * cos(a), Z = r * sin(a), Y = (float(i) / 35.0 - 0.5) * hh;
  zpx = Z;
  return vec3((HC.x + X - 960.0) * 0.01, (540.0 - (cy + Y)) * 0.01, -(HR + Z) * 0.01);
}
vec2 ringPx(int i, float T){ float a = float(i) / 36.0 * 6.283 - PI / 2.0 + T * 0.08; return vec2(960.0 + 250.0 * cos(a), 345.0 + 228.0 * sin(a)); }
Ls lstate_base(int i, float tt){
  vec4 a = LA[i], b = LB[i], c = LC[i];
  Ls o; o.s = 1.0; o.zpx = 0.0; o.pr = 1.0; o.st = 2.0;
  bool flightPh = tt < T1, restPh = tt >= T3, retPh = tt >= T2 && tt < T3;
  if (flightPh || restPh) {
    if (tt < c.x || restPh) { o.pr = 0.0; o.st = 0.0; }
    else if (tt < c.x + FLIGHT) { o.pr = ease((tt - c.x) / FLIGHT); o.st = 1.0; }
  } else if (retPh) {
    if (tt < c.y) { o.pr = 1.0; }
    else if (tt < c.y + FLIGHTR) { o.pr = 1.0 - ease((tt - c.y) / FLIGHTR); o.st = 3.0; }
    else { o.pr = 0.0; o.st = 0.0; }
  }
  if (o.st == 0.0) { o.pos = W(a.xy, 0.0); return o; }
  if (inHelix) {
    float zpx; vec3 h = helix3(i, shrink, T_, zpx);
    float k = t_ < TT ? ease((t_ - TL) / 2.0) : (t_ >= TSV2 ? 1.0 - ease((t_ - TSV2) / 2.0) : 1.0);
    vec3 p = mix(W(a.zw, 0.0), h, k); o.s = 1.0; o.zpx = zpx;
    if (spaceK > 0.0) { p = mix(h, W(LD[i].xy, 0.0), spaceK); o.s = mix(1.0, 1.05, spaceK); o.zpx = zpx * (1.0 - spaceK); }
    if (webK > 0.0) {
      vec2 rp = ringPx(i, T_); vec3 rw = W(rp, 0.0);
      p = mix(h, rw, webK); p.y -= specK * mix(LD[i].z, LE[i].z, vowK) * 0.95; o.s = mix(1.0, 1.1, webK); o.zpx = zpx * (1.0 - webK);
      if (poinK > 0.0) { p.x = mix(p.x, p.x * 0.8, poinK); p.y = mix(p.y, 1.95 + (p.y - 1.95) * 0.8, poinK); }
      if (svdK > 0.0) { p.xy = mix(p.xy, W(LE[i].xy, 0.0).xy, svdK); }
      if (rankZ > 0.0) p.z += rankZ * 1.4 * LM[i].w * cl((t_ - TP) / 6.0);       // explore: rank as height, rising as PageRank converges
    }
    o.pos = p; return o;
  }
  float u = 1.0 - o.pr;
  vec2 q = u*u*u*a.xy + 3.0*u*u*o.pr*b.xy + 3.0*u*o.pr*o.pr*b.zw + o.pr*o.pr*o.pr*a.zw;
  o.pos = W(q, 0.0); return o;
}
vec2 numPx(int i){ return vec2(660.0 + float(i / 9) * 160.0, 175.0 + float(i - (i / 9) * 9) * 46.0); }       // the numeral matrix: decades are columns, digits are rows
vec2 scatterPx(int i, float T){
  vec2 h = fract(sin(vec2(float(i) * 12.9898, float(i) * 78.233)) * 43758.5453), h2 = fract(sin(vec2(float(i) * 39.346, float(i) * 11.135)) * 24634.6345);
  return vec2(300.0 + h.x * 1320.0, 130.0 + h.y * 440.0) + 28.0 * vec2(sin(T * (0.6 + h2.x) + h2.y * 6.28), cos(T * (0.5 + h2.y) + h.x * 6.28));
}
Ls lstate(int i, float tt){
  Ls o = lstate_base(i, tt);
  if (o.st > 1.5) {
    if (numK > 0.0) { o.pos = mix(o.pos, W(numPx(i), 0.04), numK); o.s = mix(o.s, 1.0, numK); o.zpx *= (1.0 - numK); }
    if (finK > 0.0) { vec2 e_ = LD[i].xy; e_.x = 1020.0 + (e_.x - 330.0) * 0.56; vec2 tgt = mix(scatterPx(i, T_), e_, orgK); o.pos = mix(o.pos, W(tgt, 0.02), finK); o.zpx *= (1.0 - finK); }
  }
  return o;
}
"""

import re


def lib(consts):
    s = LIB
    for k, v in consts.items():
        s = s.replace("@" + k + "@", repr(float(v)) if not isinstance(v, str) else v)
    assert "@" not in s, re.findall(r"@\w+@", s)
    return s
