#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Cross-check the T-38A expect targets against pure kinematics — no flight model involved.

The T-38 has NO published turn triples (unlike the F-5E, whose verify_targets.py cross-checked the
manual's turn/radius/rate consistency). So the independent checks here are the ones the trainer data
actually supports:

  1. The two stall rows must back-solve to the SAME CL_max (Vs ~ sqrt(W) falls out, it is not
     imposed) — the test that the stall pair is internally consistent.
  2. The sea-level EAS placard (710 KEAS) vs the published max level Mach — the airframe limit and
     the aero limit should be consistent at sea level.

Nothing here uses t38a.toml; these are source-vs-source checks, run before trusting the model.
"""
import math

G = 9.80665
R_AIR, GAMMA, T0, P0, L = 287.05, 1.4, 288.15, 101325.0, 0.0065


def isa(h):
    T = T0 - L * h
    P = P0 * (T / T0) ** 5.2559
    rho = P / (R_AIR * T)
    return rho, math.sqrt(GAMMA * R_AIR * T)


S = 15.79  # m^2, published wing area

print("── 1. CL_max from the two published-derived stall rows (must be constant) ──")
rho0, a0 = isa(0.0)
for w_lb, vs_mps in ((11800.0, 67.5), (10000.0, 62.2)):
    W = w_lb * 0.45359237 * G
    clmax = 2.0 * W / (rho0 * vs_mps * vs_mps * S)
    print(f"  {w_lb:>7.0f} lb, Vs {vs_mps:.1f} m/s  ->  CL_max = {clmax:.3f}")
print("  (the two should agree; the lift table's CL_max(M0.2) = 1.19 is set from the heavier row)\n")

print("── 2. Sea-level EAS placard vs published max level Mach ──")
# 710 KEAS placard -> EAS in m/s; at sea level EAS == TAS, so Mach = V / a(0).
keas = 710.0
eas = keas * 0.514444
m_placard = eas / a0
print(f"  710 KEAS = {eas:.0f} m/s EAS -> M {m_placard:.3f} at sea level")
print(f"  published max level Mach at SL = 1.08  ->  the placard ({m_placard:.2f}) is the binding limit\n")

print("── 3. FAI time-to-climb records (upper bound; MAX thrust, light, record profile) ──")
# Maj. W.F. Daniel, T-38A 61-0849, Feb 1962. Average rate over each leg (NOT a steady-state ROC).
records = [(3000, 35.6), (6000, 51.4), (9000, 64.8), (12000, 95.6)]
prev_h, prev_t = 0.0, 0.0
for h, t in records:
    avg = (h - prev_h) / (t - prev_t)
    print(f"  {h:>6d} m in {t:5.1f} s   segment avg {avg:5.1f} m/s")
    prev_h, prev_t = h, t
print("  (a record-profile upper bound — the model's steady MIL climb must be well BELOW these)")
