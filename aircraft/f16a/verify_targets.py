#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Kinematic cross-checks for F-16A gate candidates — no aero, no thrust, just physics.

Run: python3 aircraft/f16a/verify_targets.py

The F-5E's verify_targets.py caught its T.O. printing a turn rate 2% inconsistent with its own
g and radius. Every F-16A number admitted to f16a.expect.toml passes through here first; today
the file mostly documents the 9-g corner arithmetic that any future EM-chart row must satisfy,
and the one active gate's condition.
"""

import math

G0 = 9.80665


def isa(h):
    t = 288.15 - 0.0065 * min(h, 11000.0)
    p = 101325.0 * (t / 288.15) ** 5.2559 if h <= 11000.0 else \
        101325.0 * (216.65 / 288.15) ** 5.2559 * math.exp(-G0 * (h - 11000.0) / (287.05 * 216.65))
    return p / (287.05 * t), math.sqrt(1.4 * 287.05 * t)


def turn(n, v):
    w = G0 * math.sqrt(n * n - 1.0) / v
    return math.degrees(w), v / w


def main():
    print("F-16A kinematic reference (mass 8,920 kg = combat + 2x AIM-9):\n")
    w = 8920.0 * G0

    # The 9-g corner: any future instantaneous-turn row must satisfy omega = g*sqrt(n^2-1)/V.
    for alt in (0.0, 4572.0):
        rho, a = isa(alt)
        # corner speed for n = 9 at CL_max 1.89 (the transcribed deployed-LEF peak):
        v = math.sqrt(2 * 9.0 * w / (rho * 1.89 * 27.87))
        rate, radius = turn(9.0, v)
        print(f"  {alt:>6.0f} m: 9-g corner V = {v:5.1f} m/s (M {v / a:.2f})"
              f"  rate = {rate:5.1f} deg/s  radius = {radius:5.0f} m")

    # The active gate: M 2.05 at 40,000 ft. Kinematics has nothing to check on a max-speed
    # point; what IS checkable is that the CL it implies sits far inside the envelope.
    rho, a = isa(12192.0)
    v = 2.05 * a
    cl = w / (0.5 * rho * v * v * 27.87)
    print(f"\n  M 2.05 @ 12,192 m: 1-g CL = {cl:.3f} (envelope at M 2.0 is ~0.8 -- deep margin,"
          f" the point is thrust/drag-limited as it should be)")


if __name__ == "__main__":
    main()
