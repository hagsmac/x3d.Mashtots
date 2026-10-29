#!/usr/bin/env python3
"""Shared timeline + Bezier control points of Mashtots slide 1 (port of reveal.js: seed 405, begin 0.9, stagger 0.075, flight 2.8, cubic ease).
Imported by make_reveal.py (GPU shader version) and make_reveal_classic.py (interpolator version)."""
import math, sys
LET = "ԱԲԳԴԵԶԷԸԹԺԻԼԽԾԿՀՁՂՃՄՅՆՇՈՉՊՋՌՍՎՏՐՑՒՓՔ"
N = len(LET); assert N == 36, N
def mulberry32(a):
    a &= 0xFFFFFFFF
    def f():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a; t = ((t ^ (t >> 15)) * (1 | t)) & 0xFFFFFFFF
        t = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF ^ t
        return (((t ^ (t >> 14)) & 0xFFFFFFFF)) / 4294967296
    return f
rnd = mulberry32(405)
src = dict(x=700, y=330, w=110, h=280); row = dict(x=144, y=700, w=1632)
begin, stagger, flight, hold = 0.9, 0.075, 2.8, 4.0
total = begin + (N - 1) * stagger + flight
CYC = total + hold + total       # out, hold on the line, back to the stone
S = 0.01; W, H = 19.2, 10.8
def wx(x): return round((x - W * 50) * S, 4)
def wy(y): return round((H * 50 - y) * S, 4)
ease = lambda p: 4*p**3 if p < .5 else 1 - (-2*p + 2)**3 / 2
def bez(p, e):
    u = 1 - e
    return (u**3*p["sx"] + 3*u*u*e*p["c1x"] + 3*u*e*e*p["c2x"] + e**3*p["tx"],
            u**3*p["sy"] + 3*u*u*e*p["c1y"] + 3*u*e*e*p["c2y"] + e**3*p["ty"])
P = []
for i, ch in enumerate(LET):
    col, r = i % 4, i // 4
    sx = src["x"] + (col + .5) / 4 * src["w"]; sy = src["y"] + (r + .5) / 9 * src["h"]
    tx = row["x"] + (i + .5) / N * row["w"]; ty = row["y"]
    c1x = sx + (tx - sx) * .12 + (rnd() - .5) * 240; c1y = sy - 380 - rnd() * 300
    c2x = tx + (rnd() - .5) * 200; c2y = ty - 200 - rnd() * 220; rnd()
    P.append(dict(ch=ch, sx=sx, sy=sy, tx=tx, ty=ty, c1x=c1x, c1y=c1y, c2x=c2x, c2y=c2y, t0=begin + i * stagger))
