#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Derive the F-5E's lift table and moment derivatives from published geometry.

Run:  python3 aircraft/f5e/derive.py        # prints TOML blocks for f5e.toml

WHY THIS IS A SCRIPT AND NOT A TABLE OF CONSTANTS
-------------------------------------------------
Two inputs below are NOT published (tail moment arms) and one is AMBIGUOUS in the
source (whether NASA's tail areas are gross or exposed). Those uncertainties
propagate straight into Cm_alpha, and the difference is not small -- see the
sensitivity report this script prints. When the ambiguity is resolved, change the
constant and re-run; do not hand-patch f5e.toml.

Every formula is a standard, citable method (USAF DATCOM / Helmbold / strip theory).
No value here is fitted to make the aircraft feel good, and none is taken from any
flight simulator. See SOURCES.md.

WHAT THE MOMENT DERIVATIVES ARE AND ARE NOT
-------------------------------------------
NOTHING in f5e.expect.toml constrains them. The published turn, Ps and max-speed
data test lift, drag and thrust only -- no published F-5E source gives a single
stability derivative. So these numbers are not "verified"; they are *derived from
geometry by a standard method*, sign-checked, and magnitude-checked against the
known fighter range. They are the widest error bars in this model, and they should
be stated that way rather than dressed up.

The one exception, pending: published ROLL RATE would constrain Cl_p and Cl_da.
That is an open research item.
"""

import math

# ─── Published geometry — NASA spin-tunnel report (NTRS 19980227417), Table I ────
S      = 17.30    # m^2   wing area                                        [P]
B      = 8.13     # m     wing span, without tip missiles                  [P]
MAC    = 2.456    # m     mean aerodynamic chord                           [P]
AR     = B * B / S  #     3.82 -- matches NASA's stated value              [P]
TAPER  = 0.19     #       wing taper ratio                                 [P]
SWEEP  = 24.0     # deg   wing quarter-chord sweep                         [P]

S_H    = 3.07     # m^2   horizontal tail, EXPOSED -- resolved, see below  [P]
AR_H   = 2.88     #       horizontal tail aspect ratio, on EXPOSED span    [P]
S_V    = 3.85     # m^2   vertical tail, exposed                           [P]
AR_V   = 1.22     #       vertical tail aspect ratio, on exposed span      [P]
S_AIL  = 0.86     # m^2   aileron area, both surfaces                      [P]
S_RUD  = 0.60     # m^2   rudder area                                      [P]

CG     = 0.166    # x/c   CG position, NASA Table II "clean, 55% fuel"     [P]
AC     = 0.25     # x/c   wing aerodynamic centre (thin-airfoil, standard)

# ─── NOT PUBLISHED — engineering estimates. These dominate the uncertainty. ─────
L_H    = 5.9      # m     wing AC -> horizontal tail AC moment arm         [E]
L_V    = 5.6      # m     wing AC -> vertical tail AC moment arm           [E]
Z_V    = 1.5      # m     vertical tail AC height above CG                 [E]
ETA_H  = 0.90     #       horizontal tail dynamic-pressure efficiency      [E]
ETA_V  = 0.90     #       vertical tail dynamic-pressure efficiency        [E]
DEPS   = 0.45     #       downwash gradient d(eps)/d(alpha)                [E]
TAU_A  = 0.45     #       aileron flap effectiveness (~25% chord)          [E]
TAU_R  = 0.45     #       rudder flap effectiveness (~25% chord)           [E]
CN_FUS = -0.10    # /rad  fuselage yaw destabilisation                     [E]

# RESOLVED (2026-07-14). NASA Table I LOOKS self-contradictory: horizontal tail span 4.30 m,
# "area (exposed)" 3.07 m^2, aspect ratio 2.88 -- yet 4.30^2 / 3.07 = 6.02, not 2.88. The
# tempting reading is that AR is quoted on a GROSS area of 6.42 m^2, which would change
# cm_alpha by 75% and cm_q by 109%.
#
# That reading is WRONG. Reading the table off the page image (not the OCR): area, taper ratio
# AND aspect ratio are each explicitly labelled "(exposed)", while the 4.30 m span row is NOT.
# The aspect ratio is computed on the EXPOSED span -- the panels outboard of the fuselage --
# not on the tip-to-tip span. Everything is then consistent:
#
#   exposed span   = sqrt(2.88 * 3.07)          = 2.97 m
#   => fuselage width at the tail = 4.30 - 2.97 = 1.33 m   (plausible for the twin-J85 tail)
#   independent check via the taper ratio (which does not involve AR at all):
#     root chord   = tip / taper = 0.508 / 0.33 = 1.539 m
#     exposed area = 2.97 * (1.539 + 0.508)/2   = 3.04 m^2  vs published 3.07  -- 0.9% agreement
#   the same check on the vertical tail is exact: 2.17 * (2.845 + 0.711)/2 = 3.85 m^2 == published
#
# So the exposed-area reading is right, and the gross hypothesis is refuted by a cross-check that
# never touches the aspect ratio. Kept below only so the sensitivity stays visible: if anyone ever
# "fixes" S_H to 6.42, this is what it costs.
S_H_GROSS = (4.30 ** 2) / AR_H     # 6.42 m^2 -- the REFUTED gross-area reading. Do not use.

# ─── Calibration anchor — from f5e.expect.toml, drag-independent ────────────────
CLMAX_M060 = 1.255   # [D] from the published 5.2 G max-lift point at 15k / M0.60


def lift_slope(ar: float, mach: float = 0.0) -> float:
    """Lift-curve slope, per radian.

    Subsonic: Helmbold's low-aspect-ratio relation with Prandtl-Glauert compressibility,
              CL_a = 2*pi*AR / (2 + sqrt(AR^2 * beta^2 + 4)),  beta^2 = 1 - M^2.
              Reduces to the classic 2*pi*AR/(2+sqrt(AR^2+4)) at M=0.
    Supersonic: 2-D Ackeret 4/beta with the standard finite-span correction.
    """
    if mach < 0.95:
        b2 = 1.0 - mach * mach
        return 2 * math.pi * ar / (2 + math.sqrt(ar * ar * b2 + 4))
    if mach < 1.05:                                 # transonic: no valid linear theory
        return lift_slope(ar, 0.94)                 # hold; the table is authored, not trusted here
    beta = math.sqrt(mach * mach - 1.0)
    return (4.0 / beta) * (1.0 - 1.0 / (2.0 * ar * beta))


A_W = lift_slope(AR, 0.0)
A_H = lift_slope(AR_H, 0.0)
A_V = lift_slope(AR_V, 0.0)


def moments(s_h: float) -> dict:
    """The nine derivatives, per radian. `s_h` selects the tail-area reading."""
    # Pitch — reference length MAC
    cm_a = A_W * (CG - AC) \
        - A_H * ETA_H * (s_h / S) * (L_H / MAC) * (1.0 - DEPS)
    cm_q = -2.0 * ETA_H * A_H * (s_h / S) * (L_H / MAC) ** 2
    cm_de = -ETA_H * A_H * (s_h / S) * (L_H / MAC)      # all-moving tail: tau = 1.0

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


# Sign conventions the engine's validator ENFORCES as errors, and the magnitude
# range a conventional fighter should land in. A derivation that violates either
# is wrong, not interesting.
BOUNDS = {
    "cm_alpha": (-2.00, -0.30), "cm_q":   (-25.0, -3.0), "cm_de":  (-2.00, -0.30),
    "cl_beta":  (-0.25, -0.02), "cl_p":   (-0.60, -0.20), "cl_da":  (0.03, 0.20),
    "cn_beta":  (0.05, 0.30),   "cn_r":   (-0.60, -0.08), "cn_dr":  (-0.20, -0.02),
}

ALPHA = [-10, -5, 0, 2.5, 5, 7.5, 10, 12.5, 15, 17, 22, 30]   # peak at alpha_stall (see below)
# 2.5-deg steps through the attached range (0..17) since the fm-trim #826 gate rows went live:
# CD(alpha) is CONVEX, so bilinear interpolation across the old 5-deg cells systematically
# OVERSTATED drag between nodes -- by up to ~25% of CD at the trim alphas of the published
# Ps-ladder and turn points (9-19 m/s of Ps; 0.5 g of sustained turn at M 0.75). The model was
# failing gates against the very chart its drag table is fitted to, purely through grid
# resolution. The negative range stays coarse: the polar is symmetric and nothing calibrates it.
MACH  = [0.2, 0.6, 0.75, 0.9, 1.2, 1.6]
# 0.75 added for the same reason: the T.O. quotes turn performance AT M 0.75, and a linear
# 0.6 -> 0.9 interpolation drags CL_max(0.75) down toward the shock-stall column (~1.08) --
# understating the published instantaneous turn (which reaches the 7.33 g structural limit
# there, requiring CL_max >= 1.133) and paying M 0.9 separation drag at M 0.75.

# CL_max envelope vs Mach.
#
# ONLY the M 0.60 value is published (derived from the 5.2 G max-lift point). The rest of
# this curve is an ENGINEERING ESTIMATE [E], and it is the second-largest uncertainty in
# the model after the thrust deck.
#
# It cannot simply be `slope(M) * alpha_stall`: the compressible lift slope RISES with
# Mach, so a fixed stall alpha would give CL_max = 1.54 at M 0.9 -- HIGHER than the
# measured 1.255 at M 0.6. Real wings do the opposite. Above roughly M 0.6, shock-induced
# separation makes CL_max FALL, and it falls hard supersonically. The stall alpha
# therefore DECREASES with Mach; it is not a constant.
CLMAX_VS_MACH = {
    0.2: 1.20,    # [E] thin 4.8% symmetric section, no flaps -- modest
    0.6: 1.255,   # [D] the published anchor. The only honest number in this row.
    0.75: 1.21,   # [D] pinned by the T.O.'s two M 0.75 turn points, jointly:
                  #     * instantaneous turn is quoted AT the 7.33 g structural limit
                  #       (15,000 ft, 6137 kg), which requires CL_max(0.75) >= 7.33*W/(q*S) = 1.133
                  #     * sustained 4.3 g requires the separation-drag term (keyed to CL/CL_max)
                  #       to leave <= T - D at CL 0.664, which with the ladder-fitted k1/k2
                  #       implies CL_max(0.75) ~= 1.20-1.22
                  #     A plateau to ~M 0.75 followed by shock-stall collapse toward 0.9 is also
                  #     the physically expected shape for a thin 4.8% section; the previous
                  #     straight line to 1.10 was the [E] guess this data replaces.
    0.9: 1.10,    # [E] shock stall
    1.2: 0.85,    # [E]
    1.6: 0.70,    # [E]
}


def cl_table() -> tuple[float, list[list[float]]]:
    """CL(alpha, mach), row-major over alpha.

    Linear at the compressible lift slope, capped by the CL_max envelope above, then a
    post-stall collapse. The engine does NOT clamp CL anywhere -- the table must carry the
    stall itself, or the aircraft will happily fly at 40 deg alpha (see engine #816).

    alpha_stall is quoted at M 0.60, the Mach of the published anchor, and MUST use the
    compressible slope there: using CL_a(M=0) would put the stall ~2 deg too high and
    silently contradict the one lift measurement we have.
    """
    a_stall_rad = CLMAX_M060 / lift_slope(AR, 0.60)
    a_stall = math.degrees(a_stall_rad)

    rows = []
    for a_deg in ALPHA:
        row = []
        for m in MACH:
            slope = lift_slope(AR, m)
            clmax = CLMAX_VS_MACH[m]
            a_peak = math.degrees(clmax / slope)        # stall alpha at THIS Mach
            mag = abs(a_deg)
            if mag <= a_peak:
                cl = slope * math.radians(mag)
            else:
                cl = clmax * max(0.45, 1.0 - 0.035 * (mag - a_peak))
            row.append(round(math.copysign(cl, a_deg), 4))
        rows.append(row)
    return a_stall, rows


if __name__ == "__main__":
    print(f"AR = {AR:.3f}   CL_a(M=0)   wing {A_W:.3f}  htail {A_H:.3f}  vtail {A_V:.3f}  /rad\n")

    print("── NASA tail-area reading: RESOLVED as exposed. Cost of getting it wrong: ──")
    exposed, gross = moments(S_H), moments(S_H_GROSS)
    print(f"{'derivative':<11} {'S_h=3.07 (CORRECT)':>19} {'S_h=6.42 (refuted)':>19} {'delta':>8}")
    for kk in ("cm_alpha", "cm_q", "cm_de"):
        d = abs(gross[kk] - exposed[kk]) / abs(exposed[kk]) * 100
        print(f"{kk:<11} {exposed[kk]:>19.3f} {gross[kk]:>19.3f} {d:>7.0f}%")
    print("Confirmed exposed via the taper-ratio cross-check, which never touches AR.\n")

    m = moments(S_H)
    print("── [aero.moments] ───────────────────────────────────────────────────────")
    ok = True
    for kk, v in m.items():
        lo, hi = BOUNDS[kk]
        good = lo <= v <= hi
        ok &= good
        print(f"{kk:<10} = {v:>8.3f}   {'OK ' if good else 'OUT'} (fighter range {lo} .. {hi})")
    print(f"\nall derivatives in range: {ok}\n")

    a_stall, rows = cl_table()
    print("── [aero.cl_table] ──────────────────────────────────────────────────────")
    print(f"alpha_stall = {a_stall:.1f} deg   (CL_max {CLMAX_M060} / slope {lift_slope(AR,0.60):.3f} at M0.60)")
    print(f"alpha  = {ALPHA}")
    print(f"mach   = {MACH}")
    print("values = [")
    for a_deg, row in zip(ALPHA, rows):
        print(f"  {', '.join(f'{c:7.4f}' for c in row)},   # alpha {a_deg:>3}")
    print("]")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# DRAG: fit CD(CL) to the published Ps ladder  (engine #820's [aero.cd_table])
# ═══════════════════════════════════════════════════════════════════════════════════════════════
#
# The T.O. gives specific excess power at five load factors, 15,000 ft / M 0.60, max thrust:
#     n = 1.0, 2.0, 3.3, 4.0, 5.2   ->   Ps = 240, 190, 0, -225, -870 ft/s
#
# Ps = V*(T - D)/W with T constant, so D(n) = T - Ps(n)*W/V. And at n = 3.3, Ps = 0 BY DEFINITION,
# which means D(3.3) = T exactly. So the ladder pins the SHAPE of CD(CL) with no thrust assumption
# whatsoever -- only its absolute level rides on T, and that is one unknown, not a curve.
#
# We solve for CD(CL) = cd0 + k1*CL^2 + k2*CL^4, with cd0 anchored at the published 0.0200
# (NASA SP-468) and the thrust level X = CD(CL at n=3.3) left free. Three unknowns (X, k1, k2),
# five equations, least squares. The CL^4 term is what the parabola could not have.

PS_LADDER = [(1.0, 240.0), (2.0, 190.0), (3.3, 0.0), (4.0, -225.0), (5.2, -870.0)]  # (n, Ps ft/s)
CD0_PUB = 0.0200          # [P?] NASA SP-468 App. A Table V
ALT_PS, MACH_PS = 4572.0, 0.60
W_COMBAT_N = 6137 * 9.80665


def isa(h):
    T = 288.15 - 0.0065 * h
    P = 101325.0 * (T / 288.15) ** 5.2559
    return P / (287.05 * T), math.sqrt(1.4 * 287.05 * T)


def fit_drag():
    rho, a = isa(ALT_PS)
    V = MACH_PS * a
    q = 0.5 * rho * V * V
    qS = q * S

    # Rows of  [1, CL^2, CL^4] * [X, -k1, -k2]^T  ... rearranged:
    #   X + dCD_i = cd0 + k1*CL_i^2 + k2*CL_i^4
    #   =>  X - k1*CL^2 - k2*CL^4 = cd0 - dCD_i
    A, b = [], []
    for n, ps_ft in PS_LADDER:
        cl = n * W_COMBAT_N / qS
        dcd = -(ps_ft * 0.3048) * (W_COMBAT_N / V) / qS      # (D(n) - D(3.3)) / qS
        A.append([1.0, -cl**2, -cl**4])
        b.append(CD0_PUB - dcd)

    # Normal equations, 3x3 -- solved by hand to keep this dependency-free.
    ATA = [[sum(A[i][r] * A[i][c] for i in range(len(A))) for c in range(3)] for r in range(3)]
    ATb = [sum(A[i][r] * b[i] for i in range(len(A))) for r in range(3)]
    M = [ATA[r] + [ATb[r]] for r in range(3)]
    for i in range(3):                                        # Gaussian elimination
        p = max(range(i, 3), key=lambda r: abs(M[r][i]))
        M[i], M[p] = M[p], M[i]
        for r in range(3):
            if r != i:
                f = M[r][i] / M[i][i]
                for c in range(i, 4):
                    M[r][c] -= f * M[i][c]
    X, k1, k2 = (M[i][3] / M[i][i] for i in range(3))
    return X, k1, k2, qS, V


POST_STALL_CD_RISE = 0.03   # [E] per degree past the stall, as a fraction of the stall-point CD


def cd_table(k1, k2):
    """CD(alpha, mach) on the SAME grid as cl_table.

    TWO CORRECTIONS over the naive CD = f(CL), both of which matter:

    1. SEPARATION DRAG SCALES WITH THE LIFT FRACTION, NOT WITH CL.
       The fitted CL^4 term is not classical induced drag -- it is the drag rise as the wing
       approaches ITS OWN stall. CL_max falls with Mach (1.255 at M0.6, 1.10 at M0.9), so at high
       Mach the wing is far closer to stalling at the same CL, and its separation drag is
       correspondingly higher. Applying the M0.6 coefficient unchanged at M0.9 would understate it.
       So the quartic term is written in the LIFT FRACTION lam = CL / CL_max(M), which reduces
       exactly to the fitted form at M 0.60 and behaves correctly everywhere else:

           CD = cd0 + k1*CL^2  +  k2 * CL_max(0.6)^4 * lam^4
                     ^classical induced   ^separation, keyed to how close to the stall we are

    2. PAST THE STALL, DRAG KEEPS RISING WHILE LIFT COLLAPSES.
       CD = f(CL) would have drag FOLLOW lift back down -- the table would say a fully stalled wing
       is cleaner than one at its lift peak, which is nonsense and would let a departed aircraft
       accelerate. Post-stall the flow is separated: lift dies, drag climbs. So beyond the stall
       alpha we hold the stall-point CD and keep it increasing.

       This region is [E] -- there is no published F-5E post-stall drag data. But monotonic-rising
       is the only defensible shape, and monotonic-falling is definitely wrong.

    Zero-lift Mach drag rise is [aero.cd_wave], added on top by the engine. Not double-counted here.
    """
    _, cl_rows = cl_table()
    a_stall_ref = CLMAX_M060 / lift_slope(AR, 0.60)          # rad

    rows = []
    for a_deg, cl_row in zip(ALPHA, cl_rows):
        row = []
        for m, cl in zip(MACH, cl_row):
            clmax = CLMAX_VS_MACH[m]
            a_peak = math.degrees(clmax / lift_slope(AR, m))
            mag = abs(a_deg)
            lam = min(abs(cl) / clmax, 1.0)
            cd_attached = CD0_PUB + k1 * cl * cl + k2 * (CLMAX_M060 ** 4) * lam ** 4
            if mag <= a_peak:
                cd = cd_attached
            else:
                cd_at_stall = CD0_PUB + k1 * clmax ** 2 + k2 * CLMAX_M060 ** 4
                cd = cd_at_stall * (1.0 + POST_STALL_CD_RISE * (mag - a_peak))
            row.append(round(cd, 5))
        rows.append(row)
    return rows
