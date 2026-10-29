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
uniform float toff;       // seek offset in seconds, set by the page's section tabs
const int NSEG = @NSEG@;  // the real-time timeline: segments of real time mapped onto the deck's act time (see timeline.py)
const float RB[@NSEG1@] = float[@NSEG1@](@RB@);
const float SA[@NSEG@] = float[@NSEG@](@SA@);
const float SRT[@NSEG@] = float[@NSEG@](@SRT@);
const float CYCLER = @CYCLER@;
const float BAR = @BAR@;
const float COL0 = @COL0@, COL1 = @COL1@;
const float NUM0 = @NUM0@, NUM1 = @NUM1@, SHI0 = @SHI0@, SHI1 = @SHI1@, FIN0 = @FIN0@, FIN1 = @FIN1@, ORG0 = @ORG0@, ORG1 = @ORG1@, BEAT = @BEAT@;
float warp(float tr, out float hold){
  for (int i = 0; i < NSEG; i++) { if (tr < RB[i + 1] || i == NSEG - 1) { hold = SRT[i] == 0.0 ? 1.0 : 0.0; return SA[i] + (tr - RB[i]) * SRT[i]; } }
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
float numK, shiK, finK, orgK, kick, finDim, finMap, colK;
float t_, T_, hold_, mapK, veil, shrink, spaceK, webK, specK, poinK, svdK, svdR, svdJ, spot, spotK;
bool inHelix;
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
  mapK = max(veil * (1.0 - hold_), finMap);                                                                // the attention map hides while an interlude holds act time
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
      p = mix(h, rw, webK); p.y -= specK * LD[i].z * 0.95; o.s = mix(1.0, 1.1, webK); o.zpx = zpx * (1.0 - webK);
      if (poinK > 0.0) { p.x = mix(p.x, p.x * 0.8, poinK); p.y = mix(p.y, 1.95 + (p.y - 1.95) * 0.8, poinK); }
      if (svdK > 0.0) { p.xy = mix(p.xy, W(LE[i].xy, 0.0).xy, svdK); }
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
