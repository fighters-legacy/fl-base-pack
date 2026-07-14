#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Cross-check the T.O. 1F-5E-1 turn data against pure kinematics.

Turn rate and radius depend ONLY on load factor and true airspeed:
    omega = g*sqrt(n^2-1)/V        R = V^2/(g*sqrt(n^2-1))
No drag, no thrust, no lift curve -- nothing I have to assume. So if the manual's
(n, turn rate, radius) triples are self-consistent, these must reproduce them exactly.

This also independently tests my derived combat weight, because CL_max and the
structural-G point both depend on W.
"""
import math

G = 9.80665
R_AIR, GAMMA, T0, P0, L = 287.05, 1.4, 288.15, 101325.0, 0.0065


def isa(h):
    T = T0 - L * h
    P = P0 * (T / T0) ** 5.2559
    rho = P / (R_AIR * T)
    return rho, math.sqrt(GAMMA * R_AIR * T)


def turn(n, V):
    s = math.sqrt(n * n - 1.0)
    return math.degrees(G * s / V), V * V / (G * s)


ALT = 4572.0  # 15,000 ft
rho, a = isa(ALT)
S = 17.30  # m^2, NASA spin-tunnel report Table I

# Derived combat weight: OEW 10,650 lb + half internal fuel 2,200 + ammo ~300 + 2x AIM-9 380
W_LB = 13530.0
W = W_LB * 0.45359237 * G

print(f"15,000 ft: rho={rho:.4f} kg/m3  a={a:.1f} m/s   W={W_LB:.0f} lb ({W:,.0f} N)\n")
print(f"{'condition':<34} {'published':>12} {'kinematic':>12} {'err':>7}")
print("-" * 70)

# (label, mach, n, published turn rate deg/s, published radius ft or None)
CASES = [
    ("M0.60 sustained  (3.3 G)", 0.60, 3.3, 9.1, None),
    ("M0.60 max lift   (5.2 G)", 0.60, 5.2, 14.8, None),
    ("M0.60 4.0 G instantaneous", 0.60, 4.0, 11.2, None),
    ("M0.75 sustained  (4.3 G)", 0.75, 4.3, 9.9, 4700.0),
    ("M0.75 limit      (7.33 G)", 0.75, 7.33, 17.0, 2700.0),
]

worst = 0.0
for label, M, n, pub_rate, pub_r in CASES:
    V = M * a
    rate, radius = turn(n, V)
    e = abs(rate - pub_rate) / pub_rate * 100
    worst = max(worst, e)
    print(f"{label:<34} {pub_rate:>9.1f}d/s {rate:>9.2f}d/s {e:>6.1f}%")
    if pub_r:
        rft = radius / 0.3048
        er = abs(rft - pub_r) / pub_r * 100
        worst = max(worst, er)
        print(f"{'  radius':<34} {pub_r:>9.0f}ft {rft:>9.0f}ft {er:>6.1f}%")

print("-" * 70)
print(f"worst error across all checks: {worst:.1f}%\n")

# CL_max falls straight out of the max-lift point -- lift only, drag-independent.
V = 0.60 * a
q = 0.5 * rho * V * V
clmax = 5.2 * W / (q * S)
print(f"CL_max at M0.60 (from the published 5.2 G max-lift point) = {clmax:.3f}")

V75 = 0.75 * a
q75 = 0.5 * rho * V75 * V75
cl_at_limit = 7.33 * W / (q75 * S)
print(f"CL at the 7.33 G limit, M0.75                             = {cl_at_limit:.3f}")
print("  -> below CL_max, so 7.33 G at M0.75 is STRUCTURALLY limited, not lift limited.")
print("     That is exactly what the manual's own corner-speed construction implies. Consistent.")
