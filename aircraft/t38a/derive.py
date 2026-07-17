#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Derive the T-38A's lift table, drag table and moment derivatives from published geometry.

Run:  python3 aircraft/t38a/derive.py        # prints TOML blocks for t38a.toml

THE CALIBRATION INVERTS vs THE F-5E (aircraft/f5e/derive.py) — read this first.
-------------------------------------------------------------------------------
The F-5E and the T-38A publish COMPLEMENTARY, non-overlapping performance data, and it flips the
whole drag calibration:

  * The F-5E had a combat EM appendix — a specific-excess-power (Ps) LADDER and turn charts — which
    pinned its CL^4 separation-drag term (the reason a tabulated polar exists) with no thrust
    assumption at all, but it had NO trustworthy rate-of-climb.
  * The T-38A is a TRAINER: its T.O. (1T-38A-1) and Category-II performance report publish a
    rate-of-climb, stall speeds across weights, and a max level Mach — but NO Ps ladder and NO turn
    charts whatsoever (verified against the full chart inventory; see SOURCES.md). There is no
    published high-CL drag datum for the T-38 at all.

So the T-38 CANNOT fit its separation-drag term to a turn ladder the way the F-5E did. Instead:

  * cd0 (the zero-lift drag LEVEL) is calibrated to the published MIL-thrust climb and the max level
    Mach — the drag the airframe actually shows in level and climbing flight.
  * k1 (classical induced, ~1/(pi*AR*e)) is scaled from the F-5E's fitted value by the AR ratio;
    AR barely moves (3.75 vs 3.82), so k1 barely moves.
  * k2 (the CL^4 separation term) is INHERITED from the F-5E as [D]-by-family-analogy: same NACA
    65A004.8 section family, near-identical AR and 24 deg sweep, a plain thin wing with no
    maneuvering-flap schedule. It is the T-38's WIDEST drag error bar and is labelled as such.

A plain parabola is NOT used: the F-5E work already PROVED the parabola fails for this wing near max
lift, and the T-38's wing is the same wing. Using one would misrepresent the aerodynamics and make
the trainer diverge from its own airframe sibling for no physical reason.

WHAT THE MOMENT DERIVATIVES ARE AND ARE NOT
-------------------------------------------
As with the F-5E, NOTHING in t38a.expect.toml constrains them — no public T-38 source gives a stability
derivative (the AFFTC S&C report AD0263411 is handling-qualities data, not derivatives). They are
DERIVED from geometry by standard USAF DATCOM / Helmbold / strip-theory methods, sign-checked, and
magnitude-checked against the known range. They are the widest error bars in the model.

Every formula is a standard, citable method. No value here is fitted to feel good, and none is taken
from any flight simulator. See SOURCES.md.
"""

import math

# ─── Published geometry — DTIC AD0263411 / ADA496748 (Northrop CAD, Table 15) ────
S      = 15.79    # m^2   wing area (170.0 ft^2)                          [P]
B      = 7.70     # m     wing span (25 ft 3 in)                          [P]
MAC    = 2.356    # m     mean aerodynamic chord (92.76 in)               [P]
AR     = B * B / S  #     3.755 -- matches the published 3.75             [P]
TAPER  = 0.20     #       wing taper ratio                                [P]
SWEEP  = 24.0     # deg   wing quarter-chord sweep                        [P]

S_H    = 3.10     # m^2   horizontal tail, EXPOSED (33.34 ft^2)           [P]
AR_H   = 2.82     #       horizontal tail aspect ratio, on EXPOSED span   [P]
S_V    = 3.82     # m^2   vertical tail, exposed (41.07 ft^2)             [P]
AR_V   = 1.21     #       vertical tail aspect ratio, on exposed span     [P]
S_AIL  = 0.55     # m^2   aileron area, both surfaces                     [E] (not published; F-5E-scaled)
S_RUD  = 0.50     # m^2   rudder area                                     [E] (not published)

CG     = 0.20     # x/c   design CG position                             [P] AD0263411 / ADA496748
AC     = 0.25     # x/c   wing aerodynamic centre (thin-airfoil, standard)

# ─── NOT PUBLISHED — engineering estimates. These dominate the moment uncertainty. ─────
# The T-38 is more slender and slightly shorter than the F-5E (14.13 m vs 14.68); the tail arms are
# taken a touch shorter than the F-5E's, everything else at the F-5E family values.
L_H    = 5.6      # m     wing AC -> horizontal tail AC moment arm         [E]
L_V    = 5.3      # m     wing AC -> vertical tail AC moment arm           [E]
Z_V    = 1.4      # m     vertical tail AC height above CG                 [E]
ETA_H  = 0.90     #       horizontal tail dynamic-pressure efficiency      [E]
ETA_V  = 0.90     #       vertical tail dynamic-pressure efficiency        [E]
DEPS   = 0.45     #       downwash gradient d(eps)/d(alpha)                [E]
TAU_A  = 0.45     #       aileron flap effectiveness (~25% chord)          [E]
TAU_R  = 0.45     #       rudder flap effectiveness (~25% chord)           [E]
CN_FUS = -0.10    # /rad  fuselage yaw destabilisation                     [E]

# ─── CL_max anchor — from the published stall speed ─────────────────────────────
# The T-38 T.O.'s numeric stall table is a chart image and the AFFTC performance report (AD0425650)
# was not machine-retrievable, so the 1-g clean stall is [D] from the published takeoff speed
# (154 KIAS at 11,800 lb, ~1.15-1.2 Vs => Vs ~= 128-134 KIAS). At 131 KIAS / SL / 11,800 lb:
#   CL_max = 2W/(rho V^2 S) = 2*52486/(1.225*67.4^2*15.79) = 1.19
# This is the T-38's largest lift uncertainty and is [D], pending a readable SAC/AFFTC stall table.
CLMAX_M020 = 1.19    # [D] low-Mach CL_max from the [D] stall speed


def lift_slope(ar: float, mach: float = 0.0) -> float:
    """Lift-curve slope, per radian.

    Subsonic: Helmbold low-AR relation with Prandtl-Glauert compressibility. Supersonic: 2-D Ackeret
    4/beta with the standard finite-span correction. Identical method to the F-5E (same family)."""
    if mach < 0.95:
        b2 = 1.0 - mach * mach
        return 2 * math.pi * ar / (2 + math.sqrt(ar * ar * b2 + 4))
    if mach < 1.05:                                 # transonic: no valid linear theory
        return lift_slope(ar, 0.94)
    beta = math.sqrt(mach * mach - 1.0)
    return (4.0 / beta) * (1.0 - 1.0 / (2.0 * ar * beta))


A_W = lift_slope(AR, 0.0)
A_H = lift_slope(AR_H, 0.0)
A_V = lift_slope(AR_V, 0.0)


def moments() -> dict:
    """The nine derivatives, per radian — USAF DATCOM / Helmbold / strip theory."""
    # Pitch — reference length MAC
    cm_a = A_W * (CG - AC) - A_H * ETA_H * (S_H / S) * (L_H / MAC) * (1.0 - DEPS)
    cm_q = -2.0 * ETA_H * A_H * (S_H / S) * (L_H / MAC) ** 2
    cm_de = -ETA_H * A_H * (S_H / S) * (L_H / MAC)      # all-moving stabilator: tau = 1.0

    # Roll — reference length span
    cl_b = -A_V * (S_V / S) * (Z_V / B) - 0.02          # vertical tail + wing sweep
    cl_p = -A_W * (1.0 + 3.0 * TAPER) / (12.0 * (1.0 + TAPER))   # strip theory
    cl_da = 2.0 * A_W * TAU_A * (S_AIL / S) * (0.75 * B / 2.0 / B)

    # Yaw — reference length span
    cn_b = A_V * ETA_V * (S_V / S) * (L_V / B) + CN_FUS
    cn_r = -2.0 * ETA_V * A_V * (S_V / S) * (L_V / B) ** 2
    cn_dr = -ETA_V * A_V * TAU_R * (S_V / S) * (L_V / B)

    return dict(cm_alpha=cm_a, cm_q=cm_q, cm_de=cm_de,
                cl_beta=cl_b, cl_p=cl_p, cl_da=cl_da,
                cn_beta=cn_b, cn_r=cn_r, cn_dr=cn_dr)


# Sign conventions the validator ENFORCES as errors, and the magnitude range a conventional aircraft
# should land in. Same airframe family as the F-5E, so the same fighter range applies.
BOUNDS = {
    "cm_alpha": (-2.00, -0.30), "cm_q":   (-25.0, -3.0), "cm_de":  (-2.00, -0.30),
    "cl_beta":  (-0.25, -0.02), "cl_p":   (-0.60, -0.20), "cl_da":  (0.03, 0.20),
    "cn_beta":  (0.05, 0.30),   "cn_r":   (-0.60, -0.08), "cn_dr":  (-0.20, -0.02),
}

ALPHA = [-10, -5, 0, 2.5, 5, 7.5, 10, 12.5, 15, 17, 22, 30]
MACH  = [0.2, 0.6, 0.9, 1.1, 1.3]     # the T-38 is placarded ~M1.3; the grid brackets its envelope

# CL_max envelope vs Mach. Only the M 0.20 value is anchored (to the [D] stall speed); the rest is an
# ENGINEERING ESTIMATE [E]. The T-38 has a thin 4.8% symmetric wing with NO maneuvering flaps (unlike
# the F-5E), so its CL_max is modest and falls with Mach through shock-induced separation.
CLMAX_VS_MACH = {
    0.2: 1.19,    # [D] the stall-speed anchor -- the only lift number with a source
    0.6: 1.15,    # [E] thin section, mild fall
    0.9: 1.00,    # [E] shock stall
    1.1: 0.85,    # [E]
    1.3: 0.75,    # [E]
}

# ─── Drag: cd0 calibrated to climb/max-Mach; k1 AR-scaled, k2 inherited (see the header) ────────
CD0        = 0.0180    # [E/D] zero-lift drag, calibrated to the published MIL climb + max Mach.
                       #       The T-38 is a famously clean airframe; a touch below the F-5E's 0.0200.
K1_F5E     = 0.0792    #       the F-5E's fitted induced coefficient (AR 3.82)
AR_F5E     = 3.82
K1         = K1_F5E * (AR_F5E / AR)   # [D] AR-scaled: induced drag ~ 1/AR, and AR barely moves
K2         = 0.1223    # [D] the F-5E's CL^4 SEPARATION term, INHERITED by airframe-family analogy.
                       #     No published T-38 high-CL drag exists to fit it. WIDEST drag error bar.

POST_STALL_CD_RISE = 0.03   # [E] per degree past the stall, as a fraction of the stall-point CD


def cl_table():
    """CL(alpha, mach), row-major over alpha. Linear at the compressible slope, capped by the CL_max
    envelope, then a post-stall collapse. The engine does NOT clamp CL -- the table carries the stall."""
    a_stall_rad = CLMAX_M020 / lift_slope(AR, 0.20)
    a_stall = math.degrees(a_stall_rad)
    rows = []
    for a_deg in ALPHA:
        row = []
        for m in MACH:
            slope = lift_slope(AR, m)
            clmax = CLMAX_VS_MACH[m]
            a_peak = math.degrees(clmax / slope)
            mag = abs(a_deg)
            if mag <= a_peak:
                cl = slope * math.radians(mag)
            else:
                cl = clmax * max(0.45, 1.0 - 0.035 * (mag - a_peak))
            row.append(round(math.copysign(cl, a_deg), 4))
        rows.append(row)
    return a_stall, rows


def cd_table():
    """CD(alpha, mach) on the SAME grid as cl_table.

    Separation drag is keyed to the LIFT FRACTION lam = CL/CL_max(M), not to CL, exactly as the F-5E:
    CL_max falls with Mach, so at high Mach the wing is nearer its stall at the same CL and its
    separation drag is higher. Past the stall, CD keeps RISING while CL collapses (a departed wing is
    not cleaner than one at its lift peak). Zero-lift Mach drag rise is [aero.cd_wave], added by the
    engine on top -- not double-counted here."""
    _, cl_rows = cl_table()
    rows = []
    for a_deg, cl_row in zip(ALPHA, cl_rows):
        row = []
        for m, cl in zip(MACH, cl_row):
            clmax = CLMAX_VS_MACH[m]
            a_peak = math.degrees(clmax / lift_slope(AR, m))
            mag = abs(a_deg)
            lam = min(abs(cl) / clmax, 1.0)
            cd_attached = CD0 + K1 * cl * cl + K2 * (CLMAX_M020 ** 4) * lam ** 4
            if mag <= a_peak:
                cd = cd_attached
            else:
                cd_at_stall = CD0 + K1 * clmax ** 2 + K2 * CLMAX_M020 ** 4
                cd = cd_at_stall * (1.0 + POST_STALL_CD_RISE * (mag - a_peak))
            row.append(round(cd, 5))
        rows.append(row)
    return rows


if __name__ == "__main__":
    print(f"AR = {AR:.3f}   CL_a(M=0)  wing {A_W:.3f}  htail {A_H:.3f}  vtail {A_V:.3f}  /rad")
    print(f"k1 = {K1:.4f} (AR-scaled from F-5E {K1_F5E})   k2 = {K2:.4f} (inherited)   cd0 = {CD0}\n")

    m = moments()
    print("── [aero.moments] ───────────────────────────────────────────────────────")
    ok = True
    for kk, v in m.items():
        lo, hi = BOUNDS[kk]
        good = lo <= v <= hi
        ok &= good
        print(f"{kk:<10} = {v:>8.3f}   {'OK ' if good else 'OUT'} (range {lo} .. {hi})")
    print(f"\nall derivatives in range: {ok}\n")

    a_stall, rows = cl_table()
    print("── [aero.cl_table] ──────────────────────────────────────────────────────")
    print(f"alpha_stall = {a_stall:.1f} deg   (CL_max {CLMAX_M020} / slope {lift_slope(AR,0.20):.3f} at M0.20)")
    print(f"alpha  = {ALPHA}")
    print(f"mach   = {MACH}")
    print("values = [")
    for a_deg, row in zip(ALPHA, rows):
        print(f"  {', '.join(f'{c:8.4f}' for c in row)},   # alpha {a_deg:>3}")
    print("]\n")

    print("── [aero.cd_table] ──────────────────────────────────────────────────────")
    print(f"alpha  = {ALPHA}")
    print(f"mach   = {MACH}")
    print("values = [")
    for a_deg, row in zip(ALPHA, cd_table()):
        print(f"  {', '.join(f'{c:8.5f}' for c in row)},   # alpha {a_deg:>3}")
    print("]")
