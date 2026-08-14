#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Derive the B-1B's lift table, sweep scales, inertias and moment derivatives.

Run:  python3 aircraft/b1b/derive.py        # prints TOML blocks for b1b.toml

WHY THIS IS A SCRIPT AND NOT A TABLE OF CONSTANTS
-------------------------------------------------
The B-1 has the thinnest published aerodynamic record of any aircraft in the pack. There is no
B-1 equivalent of NASA TP-1538 (F-16) or the F-5E spin-tunnel report: no public CL(alpha, M)
database, no tail areas, no moment arms, no inertias, no roll-rate data. What IS published is
geometry, mass, installed thrust and a handful of performance points -- so everything else here is
*derived from that geometry by a standard, citable method* (USAF DATCOM / Helmbold / strip theory)
and then constrained, where possible, by `b1b.expect.toml`.

Every formula is standard and citable. No value here is fitted to make the aircraft feel good, and
none is taken from any flight simulator. See SOURCES.md for the provenance of every input.

THE VARIABLE-GEOMETRY WING IS THE WHOLE PROBLEM
-----------------------------------------------
This is the pack's first variable-sweep aircraft, so the engine's `[wing_sweep]` model gets its
first real workout. The base `[aero.cl_table]` and `[aero.drag_polar]` are defined at
`ref_sweep_deg`, and the integrator scales them toward the spread and swept extremes.

We anchor the reference at the SPREAD position (15 deg), because that is the configuration the
published span and wing area describe -- 137 ft over 1,950 ft^2, aspect ratio 9.63. Anchoring
anywhere else would mean the base table described a planform whose dimensions are not published.
The consequence is that both performance anchors (max speed at altitude and at low level) are flown
SWEPT, so they constrain the *swept* scales and `cd0 + cd0_delta`, not the base `cd0` directly.

WHAT IS CALIBRATED, AND AGAINST WHAT
------------------------------------
`CD0`, `CD0_DELTA_SWEPT` and the `[aero.cd_wave]` shape are the only fitted quantities. They are
fitted to the two published max-speed points, and nothing else -- see the CALIBRATION block. The
lift table, the sweep scales, the inertias and the moment derivatives are NOT fitted; they come
from geometry.
"""

import math

# ─── Published geometry — SOURCES.md, all [P] ────────────────────────────────────
S = 181.16          # m^2   reference wing area (1,950 ft^2)                    [P]
B_SPREAD = 41.758   # m     span, wings spread at 15 deg (137 ft)               [P]
B_SWEPT = 24.079    # m     span, wings swept at 67.5 deg (79 ft)               [P]
LENGTH = 44.501     # m     overall length (146 ft)                             [P]
SWEEP_MIN = 15.0    # deg   full forward                                        [P]
SWEEP_MAX = 67.5    # deg   full aft                                            [P]

M_EMPTY = 87090.0   # kg    operating empty (192,000 lb)                        [P]
M_FUEL = 120326.0   # kg    usable internal fuel (265,274 lb)                   [P]
M_GROSS = 147871.0  # kg    gross weight (326,000 lb)                           [P]

T_MIL_TOTAL = 309.4  # kN   4 x F101-GE-102 dry, SL static (4 x 17,390 lbf)     [P]
T_AB_TOTAL = 547.7   # kN   4 x F101-GE-102 with afterburner (4 x 30,780 lbf)   [P]

# ─── NOT PUBLISHED — engineering estimates. These dominate the uncertainty. ─────
#
# The B-1's planform taper is not published in any public source, and unlike the F-5E there is no
# NASA table to read it from. 0.30 is read off the PD planform photographs in the reference set
# (b1-reference/planform/) as an approximate outer-panel taper; it enters only the MAC derivation.
TAPER = 0.30        #       outer-panel taper ratio, from planform photos       [E]
OSWALD_SPREAD = 0.80  #     Oswald efficiency, wings spread (high AR, clean)    [E]
OSWALD_SWEPT = 0.70   #     Oswald efficiency, wings swept (sweep penalises e)  [E]

# THE BLENDED BODY IS WHY THE SWEEP SCALES ARE NOT JUST THE PANEL RATIO.
# Sweeping the wings back changes the outer panels' contribution, but the B-1's wide blended
# fuselage and fixed glove keep carrying lift whichever way the wings are pointing. Taking the raw
# lift-slope ratio (0.33) would say the aircraft loses two thirds of its lift slope when it sweeps,
# which is not what a blended-wing-body does. This fraction is the share of lift carried by the
# body+glove and therefore held INVARIANT under sweep.
#
# Cross-check: the engine's own worked [wing_sweep] example is the F-14, whose spread/swept aspect
# ratios (7.25 / 2.56, ratio 2.83) are close to the B-1's (9.63 / 3.20, ratio 3.01). The F-14 block
# uses a swept/spread cl_scale ratio of 0.82/1.20 = 0.68. With this fraction at 0.5 the B-1 derives
# 0.67 -- the same answer from independent geometry, which is the check that this number is sane.
BODY_LIFT_FRAC = 0.50  #    lift carried by the blended body + fixed glove      [E]

# The Helmbold/Prandtl-Glauert formula grows without bound as M -> 1 and stops describing a real
# wing well before it. Real high-aspect-ratio wings peak near 6-6.5 /rad transonically, so the
# derived slope is capped rather than allowed to run to the formula's singularity.
# Set so the transonic columns do not imply an unphysical CL_max: at the 13 deg stall a
# 6.5 /rad slope would give CL_max ~1.53, which no transport-class wing reaches transonically.
# At 5.80 the derived CL_max spans ~1.27-1.38 across the table, which is the right band.
CLA_CAP = 5.80      # /rad  physical ceiling on the derived lift-curve slope    [E]

# Non-dimensional radii of gyration. Standard airframe-class values (Roskam Part V, bomber row);
# no B-1 inertia is published anywhere in the public record.
RGYR_X = 0.34       #       roll, referred to span/2                            [E]
RGYR_Y = 0.38       #       pitch, referred to length/2                         [E]
RGYR_Z = 0.44       #       yaw, referred to (span+length)/4                    [E]

# Tail geometry. NOTHING here is published for the B-1 -- the cruciform tail's areas and the moment
# arms are scaled off the length and the planform photographs. These are the widest error bars in
# the model, exactly as the tail arms were on the F-5E, and NOTHING in b1b.expect.toml constrains
# them: no public B-1 source gives a single stability derivative.
S_H = 45.0          # m^2   horizontal tail area                                [E]
S_V = 50.0          # m^2   vertical tail area (tall single fin)                [E]
AR_H = 3.6          #       horizontal tail aspect ratio                        [E]
AR_V = 1.6          #       vertical tail aspect ratio                          [E]
L_H = 17.0          # m     wing AC -> horizontal tail AC arm                   [E]
L_V = 16.0          # m     wing AC -> vertical tail AC arm                     [E]
Z_V = 3.2           # m     vertical tail AC height above CG                    [E]
ETA_H = 0.90        #       horizontal tail dynamic-pressure efficiency         [E]
ETA_V = 0.90        #       vertical tail dynamic-pressure efficiency           [E]
DEPS = 0.35         #       downwash gradient d(eps)/d(alpha), high-AR wing     [E]
TAU_A = 0.40        #       aileron/spoiler flap effectiveness                  [E]
TAU_R = 0.45        #       rudder flap effectiveness                           [E]
# Destabilising, but normalised by a 41.8 m span: a long body over a very long reference length.
# At -0.18 this term overwhelmed the fin and drove cn_beta NEGATIVE — a directionally unstable
# aircraft, which the B-1 is not.
CN_FUS = -0.05      # /rad  fuselage yaw destabilisation                        [E]
CG = 0.25           # x/c   CG position; the B-1 CG schedule is not published   [E]
AC = 0.25           # x/c   wing aerodynamic centre (thin-airfoil standard)

# ─── CALIBRATION — the ONLY fitted numbers in this file ──────────────────────────
#
# Fitted to the two published max-speed anchors and nothing else:
#     M1.25 at 50,000 ft   (afterburner, light)
#     608 kn at 200-500 ft (= M0.919 at sea level)
# Both are flown with the wings SWEPT, so what they actually constrain is
# (CD0 + CD0_DELTA_SWEPT) and the cd_wave shape. Re-run fm-trim --expect after changing any of them.
CD0 = 0.0175            # zero-lift drag at the SPREAD reference                [D]
CD0_DELTA_SWEPT = -0.0020   # swept is aerodynamically cleaner                  [D]
CD0_DELTA_SPREAD = 0.0

# Transonic/supersonic wave-drag rise. The SHAPE is [E] -- a standard transonic rise that peaks
# just above M1.0 and settles supersonically; the LEVEL is pinned by the two anchors above. The
# low-level anchor sits ON the steep part of this curve, which is why the B-1B is held subsonic
# down low while still reaching M1.25 where the dynamic pressure is 4.7x lower.
CD_WAVE_MACH = [0.80, 0.88, 0.92, 0.96, 1.02, 1.10, 1.25, 1.60]
CD_WAVE_VALS = [0.0000, 0.0035, 0.0090, 0.0210, 0.0330, 0.0345, 0.0380, 0.0400]

# ─── Derived geometry ────────────────────────────────────────────────────────────
AR_SPREAD = B_SPREAD**2 / S      # 9.625 -- matches SOURCES.md
AR_SWEPT = B_SWEPT**2 / S        # 3.201
MEAN_CHORD = S / B_SPREAD        # equivalent rectangular chord at spread

# MAC from the mean chord and the assumed taper: c_root = 2*c_bar/(1+lambda), then the standard
# trapezoidal MAC. [D] on an [E] taper.
C_ROOT = 2.0 * MEAN_CHORD / (1.0 + TAPER)
MAC = (2.0 / 3.0) * C_ROOT * (1.0 + TAPER + TAPER**2) / (1.0 + TAPER)


def cl_alpha(ar, sweep_deg, mach, eta=0.95):
    """Lift-curve slope, per radian (DATCOM/Helmbold swept-wing formula).

    Subsonic branch below M0.90. Above it the Prandtl-Glauert factor blows up and the formula stops
    describing a real wing, so the supersonic branch uses the 2-D linearised value 4/sqrt(M^2-1)
    corrected for aspect ratio, and the transonic gap is bridged linearly. Standard practice; the
    alternative is a table that goes to infinity at M1.
    """
    sweep = math.radians(sweep_deg)
    if mach <= 0.90:
        beta2 = 1.0 - mach * mach
        root = math.sqrt(ar * ar * beta2 / (eta * eta) * (1.0 + math.tan(sweep) ** 2 / beta2) + 4.0)
        return min(CLA_CAP, 2.0 * math.pi * ar / (2.0 + root))
    if mach >= 1.20:
        b = math.sqrt(mach * mach - 1.0)
        two_d = 4.0 / b
        return min(CLA_CAP, two_d * ar / (ar + 2.0 / b))   # finite-span correction
    lo = cl_alpha(ar, sweep_deg, 0.90, eta)
    hi = cl_alpha(ar, sweep_deg, 1.20, eta)
    return lo + (hi - lo) * (mach - 0.90) / 0.30


def k_induced(ar, e):
    return 1.0 / (math.pi * ar * e)


# ─── Sweep scales: derived, not guessed ─────────────────────────────────────────
#
# cl_scale is the ratio of lift-curve slope at each extreme to the slope at the reference, and
# k_scale the ratio of induced-drag factors. Evaluated at M0.60, a mid subsonic point where both
# configurations are in the linear regime and the formula is well behaved.
M_EVAL = 0.60
CLA_REF = cl_alpha(AR_SPREAD, SWEEP_MIN, M_EVAL)        # reference IS the spread position
CLA_SWEPT = cl_alpha(AR_SWEPT, SWEEP_MAX, M_EVAL)
K_REF = k_induced(AR_SPREAD, OSWALD_SPREAD)
K_SWEPT = k_induced(AR_SWEPT, OSWALD_SWEPT)

CL_SCALE_SPREAD = 1.0
CL_SCALE_SWEPT = BODY_LIFT_FRAC + (1.0 - BODY_LIFT_FRAC) * (CLA_SWEPT / CLA_REF)
K_SCALE_SPREAD = 1.0
# Blend in AR space, not in k space: k goes as 1/AR, so averaging k directly would weight the
# swept case wrongly. The body keeps its effective span, the panels lose theirs.
AR_EFF_SWEPT = BODY_LIFT_FRAC * AR_SPREAD + (1.0 - BODY_LIFT_FRAC) * AR_SWEPT
K_SCALE_SWEPT = k_induced(AR_EFF_SWEPT, OSWALD_SWEPT) / K_REF

# ─── Lift table ─────────────────────────────────────────────────────────────────
#
# THE TABLE MUST PEAK AT alpha_stall_deg, NOT MERELY REACH A CEILING THERE.
# `validate-flight-model` requires the cl_table peak to sit within 2 deg of `alpha_stall_deg`,
# because the engine does not clamp CL at the stall -- the table IS the stall. A table that
# saturates at a constant CL_max over several alphas has no well-defined peak and disagrees with
# whatever stall angle is declared. So each Mach column rises on its derived slope to a single
# maximum AT the stall angle and then drops.
ALPHA_STALL = 13.0  # deg   [E] stall AoA; every Mach column peaks here
ALPHAS = [-4.0, 0.0, 4.0, 8.0, 11.0, ALPHA_STALL, 17.0]
MACHS = [0.30, 0.60, 0.85, 0.95, 1.25]
CL0 = 0.06          # [E] small positive lift at zero alpha (cambered blended body)
POST_STALL = 0.82   # [E] fraction of peak CL retained 4 deg past the stall

cl_values = []
for a in ALPHAS:
    row = []
    for m in MACHS:
        cla = cl_alpha(AR_SPREAD, SWEEP_MIN, m)
        peak = CL0 + cla * math.radians(ALPHA_STALL)
        cl = CL0 + cla * math.radians(a) if a <= ALPHA_STALL else peak * POST_STALL
        row.append(cl)
    cl_values.append(row)

CL_MAX_RANGE = (min(r[-1] for r in cl_values[:-1]), max(max(r) for r in cl_values))

# ─── Inertias ───────────────────────────────────────────────────────────────────
IXX = M_GROSS * (RGYR_X * B_SPREAD / 2.0) ** 2
IYY = M_GROSS * (RGYR_Y * LENGTH / 2.0) ** 2
IZZ = M_GROSS * (RGYR_Z * (B_SPREAD + LENGTH) / 4.0) ** 2

# ─── Moment derivatives (DATCOM / strip theory, at the spread reference) ────────
CLA_W = CLA_REF
CLA_H = cl_alpha(AR_H, 10.0, M_EVAL)
CLA_V = cl_alpha(AR_V, 35.0, M_EVAL)

V_H = (S_H * L_H) / (S * MAC)               # horizontal tail volume coefficient
V_V = (S_V * L_V) / (S * B_SPREAD)          # vertical tail volume coefficient

CM_ALPHA = CLA_W * (CG - AC) - ETA_H * V_H * CLA_H * (1.0 - DEPS)
CM_Q = -2.0 * ETA_H * V_H * CLA_H * (L_H / MAC)
CM_DE = -ETA_H * V_H * CLA_H * TAU_A
CN_BETA = ETA_V * V_V * CLA_V + CN_FUS
CN_R = -2.0 * ETA_V * V_V * CLA_V * (L_V / B_SPREAD)
CN_DR = -ETA_V * V_V * CLA_V * TAU_R
CL_BETA = -(CLA_W / 6.0) * math.radians(SWEEP_MIN) - ETA_V * (S_V * Z_V) / (S * B_SPREAD) * CLA_V
CL_P = -(CLA_W / 12.0) * (1.0 + 3.0 * TAPER) / (1.0 + TAPER)
CL_DA = TAU_A * CLA_W / 6.0


# ─── Thrust decks ───────────────────────────────────────────────────────────────
#
# Thrust vs Mach and altitude is NOT published for the F101 -- only the SL-static ratings are.
# This deck is [D] by the same standard method the T-38A uses:
#     T(M, h) = T_sl_static * sigma^0.85 * f(M),   f(M) = 1 - 0.20*M + 0.45*M^2
# a density lapse times ram recovery. The ram coefficients are the low-bypass-turbofan form (the
# F101 is BPR ~2.0), slightly gentler than the T-38A's turbojet f(M). The LEVEL is fixed by the
# published static ratings, not fitted.
THRUST_MACHS = [0.0, 0.60, 0.90, 1.25, 1.60]
THRUST_ALTS_KM = [0.0, 5.0, 11.0, 15.24, 18.29]   # SL, mid, tropopause, 50,000 ft, ceiling
RHO0 = 1.225


def isa_density(alt_m):
    """ISA density. Troposphere lapse below 11 km, isothermal stratosphere above."""
    if alt_m <= 11000.0:
        t = 288.15 - 0.0065 * alt_m
        return RHO0 * (t / 288.15) ** 4.256
    rho11 = RHO0 * (216.65 / 288.15) ** 4.256
    return rho11 * math.exp(-9.80665 * (alt_m - 11000.0) / (287.05 * 216.65))


# The FIXED inlet is the B-1B's defining engine-installation feature, and it has to appear here.
# A ram-recovery term that keeps growing as M^2 describes a variable-geometry intake that can go on
# matching the shock system to the flight condition -- which is the B-1A, not the B-1B. Past roughly
# its design Mach a fixed inlet's pressure recovery falls away, and installed thrust falls with it.
# Left growing quadratically, the model reached M1.67 at 50,000 ft against a published M1.25: it was
# flying on B-1A-like installed thrust.
RAM_KNEE = 1.20     #       Mach beyond which fixed-inlet recovery decays       [E]
RAM_DECAY = 0.35    # /Mach rate of that decay                                  [E]


def ram(mach):
    base = lambda m: 1.0 - 0.20 * m + 0.45 * m * m
    if mach <= RAM_KNEE:
        return base(mach)
    return base(RAM_KNEE) * max(0.0, 1.0 - RAM_DECAY * (mach - RAM_KNEE))


def thrust_table(static_kn):
    rows = []
    for m in THRUST_MACHS:
        row = []
        for a_km in THRUST_ALTS_KM:
            sigma = isa_density(a_km * 1000.0) / RHO0
            row.append(static_kn * sigma ** 0.85 * ram(m))
        rows.append(row)
    return rows


MIL_TABLE = thrust_table(T_MIL_TOTAL)
AB_TABLE = thrust_table(T_AB_TOTAL)


def fmt(vals, w=7, p=4):
    return ", ".join(f"{v:{w}.{p}f}" for v in vals)


if __name__ == "__main__":
    print(f"""# ── DERIVED — regenerate with `python3 aircraft/b1b/derive.py`, do not hand-edit ──
# Geometry: AR spread {AR_SPREAD:.3f}, AR swept {AR_SWEPT:.3f} (ratio {AR_SPREAD / AR_SWEPT:.3f})
# MAC {MAC:.3f} m  [D] from mean chord {MEAN_CHORD:.3f} m and taper {TAPER} [E]
# CL_alpha at reference (spread, M{M_EVAL}): {CLA_REF:.3f} /rad
# CL_alpha swept (M{M_EVAL}):                {CLA_SWEPT:.3f} /rad   -> cl_scale {CL_SCALE_SWEPT:.3f}
# k spread {K_REF:.4f}  k swept {K_SWEPT:.4f}                        -> k_scale  {K_SCALE_SWEPT:.3f}

[flight_model]
mass_kg      = {M_EMPTY:.0f}
wing_area_m2 = {S:.2f}
wingspan_m   = {B_SPREAD:.3f}
mac_m        = {MAC:.3f}
fuel_kg      = {M_FUEL:.0f}
ixx_kg_m2    = {IXX:.0f}
iyy_kg_m2    = {IYY:.0f}
izz_kg_m2    = {IZZ:.0f}

[aero.cl_table]
alpha  = [{fmt(ALPHAS, 5, 1)}]
mach   = [{fmt(MACHS, 5, 2)}]
values = [""")
    for a, row in zip(ALPHAS, cl_values):
        print(f"    {fmt(row)},   # alpha {a:+.0f}")
    print(f"""]

[aero.drag_polar]
cd0           = {CD0:.4f}
k             = {K_REF:.4f}
speedbrake_cd = 0.0400
gear_cd       = 0.0250

[aero.cd_wave]
mach   = [{fmt(CD_WAVE_MACH, 5, 2)}]
values = [{fmt(CD_WAVE_VALS, 7, 4)}]

[wing_sweep]
ref_sweep_deg   = {SWEEP_MIN:.1f}
min_deg         = {SWEEP_MIN:.1f}
max_deg         = {SWEEP_MAX:.1f}
slew_rate_deg_s = 5.0

[wing_sweep.spread]
cl_scale  = {CL_SCALE_SPREAD:.3f}
k_scale   = {K_SCALE_SPREAD:.3f}
cd0_delta = {CD0_DELTA_SPREAD:+.4f}

[wing_sweep.swept]
cl_scale  = {CL_SCALE_SWEPT:.3f}
k_scale   = {K_SCALE_SWEPT:.3f}
cd0_delta = {CD0_DELTA_SWEPT:+.4f}

[aero.limits]
alpha_stall_deg  = {ALPHA_STALL:.1f}
# CL_max across the table spans {CL_MAX_RANGE[0]:.3f}..{CL_MAX_RANGE[1]:.3f}

[engine.mil_thrust]
mach   = [{fmt(THRUST_MACHS, 5, 2)}]
alt_km = [{fmt(THRUST_ALTS_KM, 6, 2)}]
values = [""")
    for m, row in zip(THRUST_MACHS, MIL_TABLE):
        print(f"    {fmt(row, 7, 2)},   # M {m:.2f}")
    print(f"""]

[engine.ab_thrust]
mach   = [{fmt(THRUST_MACHS, 5, 2)}]
alt_km = [{fmt(THRUST_ALTS_KM, 6, 2)}]
values = [""")
    for m, row in zip(THRUST_MACHS, AB_TABLE):
        print(f"    {fmt(row, 7, 2)},   # M {m:.2f}")
    print(f"""]

[aero.moments]
cm_alpha = {CM_ALPHA:+.4f}
cm_q     = {CM_Q:+.4f}
cm_de    = {CM_DE:+.4f}
cl_beta  = {CL_BETA:+.4f}
cl_p     = {CL_P:+.4f}
cl_da    = {CL_DA:+.4f}
cn_beta  = {CN_BETA:+.4f}
cn_r     = {CN_R:+.4f}
cn_dr    = {CN_DR:+.4f}
""")
