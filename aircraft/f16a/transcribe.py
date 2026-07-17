#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Transcribe the F-16A's aero tables from NASA TP-1538 onto the engine schema.

Run:  python3 aircraft/f16a/transcribe.py            # prints the TOML blocks for f16a.toml
      python3 aircraft/f16a/transcribe.py --check    # hard-asserts every invariant, prints report
      python3 aircraft/f16a/transcribe.py --audit    # engine-independent gate arithmetic

THIS IS THE OPPOSITE OF THE F-5E'S derive.py, AND THAT IS THE POINT
-------------------------------------------------------------------
derive.py SYNTHESISES derivatives from geometry (DATCOM), because no published F-5E aero
data exists. This script TRANSCRIBES published data: NASA TP-1538 (Nguyen, Ogburn, Gilbert,
Kibler, Brown, Deal, 1979 -- ntrs.nasa.gov/citations/19800005879) tabulates the F-16's
complete nonlinear aero database: CX/CZ/Cm over alpha -20..90 deg, beta -30..30 deg and five
stabilator settings, the lateral tables, all control increments, the dynamic derivatives,
and the F100 thrust deck (Table VI). Nothing here is derived from geometry; everything is a
PROJECTION of the published tables onto the engine's schema, and every dropped term is named
in the --check report. If fm-trim disagrees with published F-16A performance, suspect the
ENGINE's aerodynamics before this data -- that inversion is fl-base-pack#19's whole purpose.

The PDF is fetched from https://ntrs.nasa.gov/api/citations/19800005879/downloads/19800005879.pdf
and kept OUTSIDE the repo (see ../../..//f16-reference/MANIFEST.md); it is public-domain US
government work. Values below were typed from the report's Table III/VI pages (report page
numbers cited per block; the report interleaves each alpha's beta<0 and beta>=0 rows -- the
beta=0 column is the first value of each alpha block's SECOND printed line).

CONFIGURATION STATEMENT (the LEF question)
------------------------------------------
The base tables C(alpha,beta,dh) are the LEADING-EDGE-FLAP-DEPLOYED (dlef = 25 deg) wind-tunnel
configuration; the *_lef tables are LEF-RETRACTED. TP-1538's total-coefficient equations
(report pp. 37-39) blend them as  C_t = C_base + (C_lef - C_base(dh=0)) * (1 - dlef/25),
and Appendix A (p. 34) publishes the FLCS schedule the real jet flies:

    dlef = 1.38*alpha - 9.05*(qbar/ps) + 1.45      [deg, steady state; max 25]

This transcription evaluates every alpha row AT ITS SCHEDULED dlef (qbar/ps = 0.7*M^2), so the
single table the schema allows describes the jet the way it actually flies -- LEF mostly
retracted in cruise (cd0 benefits), fully deployed above alpha ~17 deg (CL_max benefits).

THE CG DECISION (read before touching XCG_MODEL)
------------------------------------------------
TP-1538 references all moments to 0.35 cbar, where the airplane is RELAXED-STABILITY:
this data's own dCm/dalpha at 0.35 cbar is POSITIVE (the report says so in prose, Appendix A:
"slightly negative static longitudinal stability at low Mach number ... desired static
stability was provided artificially ... by means of angle-of-attack feedback"). The engine
has no pitch SAS -- has_fbw is a G-limiter only (engine #816) -- and the validator hard-rejects
cm_alpha >= 0. The report's own equations carry the standard CG-transfer term
(Cm_t += CZ_t*(xcg_ref - xcg); Cn_t -= CY_t*(xcg_ref - xcg)*cbar/b), so this model flies the
airframe at XCG_MODEL = 0.25 cbar -- the forward edge of the operational envelope -- which is
transcription plus the report's own transfer, not invention. The sensitivity table this
script prints shows exactly what any other CG would give.
"""

import math
import sys

# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — data typed from NASA TP-1538. Do not edit without the report open.
# ═══════════════════════════════════════════════════════════════════════════════════════════

# ── Table I (report p. 43): mass and dimensional characteristics used in simulation ── all [P]
S_M2 = 27.87        # wing area, m^2 (300 ft^2)
B_M = 9.144         # span, m (30 ft)
MAC_M = 3.45        # mean aerodynamic chord, m (11.32 ft)
XCG_REF = 0.35      # reference CG, fraction of cbar
WEIGHT_N = 91188.0  # simulation weight (20,500 lb)
IXX = 12875.0       # kg m^2  (9,496 slug-ft^2)
IYY = 75674.0       # kg m^2  (55,814 slug-ft^2)
IZZ = 85552.0       # kg m^2  (63,100 slug-ft^2)
IXZ = 1331.0        # kg m^2  (982 slug-ft^2) -- NO SCHEMA SLOT; dropped, reported
DH_LIMIT = 25.0     # symmetric horizontal-tail travel, deg
DA_LIMIT = 21.5     # aileron (flaperon) travel, deg
DR_LIMIT = 30.0     # rudder travel, deg
AR = B_M * B_M / S_M2  # 3.0

# ── Table III base tables, beta = 0 column (LEF DEPLOYED configuration) ──────────────────────
ALPHA = [-20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 90]

CX_B0 = {  # CX(alpha, beta=0, dh), report pp. 45-49 (dh = 0 col from p. 47)
    0: [-0.09330, -0.09780, -0.09820, -0.07840, -0.04890, -0.00660, 0.04900, 0.10720,
        0.12830, 0.13000, 0.15360, 0.16050, 0.15520, 0.13820, 0.12810, 0.12000,
        0.11470, 0.10250, 0.08210, 0.08640],
}
CZ_B0 = {  # CZ(alpha, beta=0, dh=0), report p. 54
    0: [1.11600, 0.95900, 0.69200, 0.28700, -0.02500, -0.36700, -0.75000, -1.11200,
        -1.41800, -1.65800, -2.00800, -2.20000, -2.32800, -2.31100, -2.32600, -2.25200,
        -2.20800, -2.13400, -2.00400, -2.14000],
}
CM_B0 = {  # Cm(alpha, beta=0, dh), about 0.35 cbar, report pp. 59-63
    -25: [0.17500, 0.15840, 0.15900, 0.12160, 0.14090, 0.15800, 0.18450, 0.20870,
          0.21520, 0.19780, 0.20220, 0.18140, 0.14780, 0.09220, 0.07450, 0.07130,
          -0.05400, -0.22440, -0.33890, -0.47230],
    -10: [0.08640, 0.03280, 0.00410, 0.00760, 0.04300, 0.05010, 0.05530, 0.07060,
          0.06740, 0.04920, 0.05280, 0.02780, -0.00940, -0.04110, -0.01290, 0.02020,
          -0.07080, -0.31370, -0.42360, -0.57180],
    0: [0.01270, -0.07550, -0.10250, -0.07440, -0.05980, -0.04980, -0.04370, -0.04070,
        -0.03420, -0.05070, -0.04590, -0.06050, -0.08350, -0.09230, -0.08260, -0.07380,
        -0.14140, -0.32160, -0.46780, -0.61840],
    10: [-0.08350, -0.17190, -0.21530, -0.18880, -0.16100, -0.16060, -0.15480, -0.14520,
         -0.12640, -0.15300, -0.14400, -0.14110, -0.14500, -0.14110, -0.10080, -0.06790,
         -0.15560, -0.19830, -0.47210, -0.60830],
    25: [-0.20930, -0.30790, -0.33910, -0.27410, -0.25270, -0.25620, -0.25540, -0.21570,
         -0.21650, -0.23250, -0.17400, -0.14010, -0.13200, -0.11130, -0.12340, -0.09290,
         -0.15840, -0.23030, -0.47160, -0.58860],
}

# ── LEF-retracted tables, beta = 0 (published over alpha -20..+45 only; the schedule has the
#    LEF fully deployed above ~17 deg, so the missing range is never blended) ── pp. 50/57/64
ALPHA_LEF = [-20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
CX_LEF_B0 = [-0.01810, -0.01930, -0.02240, -0.01960, -0.02020, -0.00330, 0.00990, 0.02240,
             0.02210, 0.02780, 0.03010, 0.03050, 0.03280, 0.03090]
CZ_LEF_B0 = [1.25600, 1.03500, 0.72500, 0.24800, -0.10000, -0.42800, -0.77400, -1.13900,
             -1.35500, -1.65000, -1.88300, -2.07700, -2.20400, -2.20800]
CM_LEF_B0 = [-0.05030, -0.10120, -0.06470, -0.03870, -0.02670, -0.01280, -0.00160, 0.03230,
             -0.01610, -0.04550, -0.08710, -0.11510, -0.12060, -0.09790]

# ── 1-D longitudinal tables (report pp. 51/58/65/66) ─────────────────────────────────────────
DCX_SB = [-0.01010, -0.01010, -0.01010, -0.01010, -0.01010, -0.03580, -0.07900, -0.12270,
          -0.18270, -0.18920, -0.19880, -0.20000, -0.18740, -0.16730, -0.14760, -0.13100,
          -0.12790, -0.13250, -0.12500, -0.12500]   # FULL (60 deg) speed brake
CMQ = [-6.84, -6.84, -6.84, -3.42, -5.48, -5.45, -6.02, -6.70, -5.69, -6.00,
       -6.20, -6.40, -6.60, -6.00, -5.50, -5.00, -4.50, -3.50, -5.60, -4.04]
DCMQ_LEF = [-0.367, -0.367, -0.367, 2.88, 0.25, 0.27, -0.21, 0.36, -1.26, -2.51,
            -1.66, -1.72, -1.20, -0.60]             # on ALPHA_LEF
DCM_CORR = [0.019, 0.019, 0.019, 0.019, 0.019, 0.019, 0.02, 0.04, 0.04, 0.05,
            0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06, 0.06]  # dCm(alpha), p. 65
ETA_DH = {-25: 1.00, -10: 1.00, 0: 1.00, 10: 1.00, 25: 0.95}             # p. 65
DCM_DS_DH0 = {40: 0.01, 45: 0.064}  # deep-stall increment at dh=0 (zero for alpha < 40), p. 67

# Dropped 1-D tables, typed for the record (no schema slots): CXq, CZq, dCZ,sb, dCm,sb
CXQ = [0.953, 0.953, 0.953, 1.55, 1.90, 2.46, 2.92, 3.30, 2.76, 2.05,
       1.50, 1.49, 1.83, 1.21, 1.33, 1.61, 0.91, 3.43, 0.617, 0.273]
CZQ = [-23.9, -23.9, -23.9, -29.5, -29.5, -30.5, -31.3, -30.1, -27.7, -28.2,
       -29.0, -29.8, -38.3, -35.3, -32.3, -27.3, -25.2, -27.3, -9.35, -2.16]

# ── 1-D lateral tables (report pp. 81/82/90/91) ──────────────────────────────────────────────
CNR = [-0.517, -0.517, -0.517, -0.461, -0.414, -0.397, -0.373, -0.455, -0.550, -0.582,
       -0.595, -0.637, -1.020, -0.840, -0.541, -0.350, -0.350, -0.070, -0.150, -0.150]
DCNR_LEF = [0.137, 0.137, 0.137, 0.098, 0.037, 0.016, 0.007, 0.014, -0.103, -0.098,
            -0.310, -0.437, 0.167, 0.084]           # on ALPHA_LEF
CLP = [-0.366, -0.366, -0.366, -0.377, -0.345, -0.434, -0.408, -0.388, -0.329, -0.294,
       -0.230, -0.210, -0.120, -0.100, -0.100, -0.120, -0.140, -0.100, -0.150, -0.200]
DCLP_LEF = [0.006, 0.006, 0.006, 0.018, -0.100, 0.020, 0.058, 0.087, 0.027, -0.056,
            -0.082, 0.362, 0.194, 0.097]            # on ALPHA_LEF
CNP = [-0.0006, -0.0006, -0.0006, 0.0424, -0.0075, -0.0214, -0.0320, -0.0320, 0.0500, 0.1500,
       0.1300, 0.1580, 0.2400, 0.1500, 0.0, -0.2, -0.3, 0.15, 0.0, 0.0]     # dropped
CLR = [-0.155, -0.155, -0.155, -0.201, -0.0024, 0.088, 0.205, 0.220, 0.319, 0.437,
       0.680, 0.100, 0.447, -0.330, -0.068, 0.118, 0.0802, 0.0529, 0.0868, -0.0183]  # dropped

# ── beta slopes: values at beta = +4 deg, dh = 0, from the full matrices ─────────────────────
# (report pp. 75 Cn / 84 Cl / 68 CY; the beta=0 baselines print as 0.0000 on all three)
CN_BETA4 = {0: 0.01350, 5: 0.01480, 10: 0.01470, 15: 0.01410}
CL_BETA4 = {0: -0.00670, 5: -0.00810, 10: -0.01370, 15: -0.01880}
CY_BETA4 = {0: -0.07640, 5: -0.08190, 10: -0.07860, 15: -0.07700}

# ── control-deflected TOTAL tables at beta = 0 (increments vs the ~0 base) ── pp. 78/80/87/89
CN_DA20_B0 = {0: -0.01200, 5: -0.01050, 10: -0.00900, 15: -0.00660}
CN_DR30_B0 = {0: -0.04510, 5: -0.04500, 10: -0.04410, 15: -0.04460}
CL_DA20_B0 = {0: -0.04810, 5: -0.05110, 10: -0.04990, 15: -0.04910}
CL_DR30_B0 = {0: 0.01460, 5: 0.01460, 10: 0.01370, 15: 0.01350}

# ── Table VI (report p. 93): thrust values used in simulation, SI (N) ── all [P]
# rows = Mach [0.2 .. 1.0]; cols = altitude m [0 .. 15240]. The report double-prints this
# table in US customary units; 21,420 lbf * 4.448 = 95,276 N -- the two agree, an internal
# cross-check that the typing below is faithful.
T_MACH = [0.2, 0.4, 0.6, 0.8, 1.0]
T_ALT_M = [0.0, 3048.0, 6096.0, 9144.0, 12192.0, 15240.0]
T_MIL_N = [[56401, 40699, 28080, 17970, 10987, 6227],
           [56089, 41420, 29401, 19082, 11565, 6939],
           [56223, 43764, 31536, 20728, 12632, 7384],
           [55111, 45263, 34472, 23663, 14456, 8585],
           [51953, 43804, 35806, 27133, 16902, 10275]]
T_MAX_N = [[95276, 69834, 49929, 32573, 19727, 11565],
           [100970, 74993, 54488, 36269, 22240, 12610],
           [107820, 84112, 61204, 41300, 25354, 14300],
           [115959, 93742, 71057, 49440, 30513, 17570],
           [128485, 103723, 81398, 59977, 38440, 22494]]
# T_idle is ALSO published (negative at high M / low altitude -- ram drag). The engine's
# throttle model is linear throttle*mil with no idle deck, so it is dropped and reported;
# engine enhancement filed from fl-base-pack#19.

# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — the model choices (each one a named, documented decision)
# ═══════════════════════════════════════════════════════════════════════════════════════════

XCG_MODEL = 0.25   # fraction of cbar. Forward edge of the operational envelope; see docstring.

# Pack table axes. Alpha stays on the REPORT'S OWN 5-deg grid -20..45 (the published simulation
# interpolated these same breakpoints linearly, exactly as the engine does -- densifying adds
# no information, unlike the F-5E whose generator was a smooth analytic fit). Rows above 45 deg
# are deliberately not carried: every synthesized high-Mach value there would be fiction, and
# the engine edge-clamps benignly post-departure.
ALPHA_PACK = [-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45]
MACH_PACK = [0.2, 0.6, 0.8, 0.9, 1.2, 1.6, 2.0]

# CL_max envelope vs Mach. M 0.2 comes from the data itself; everything else is [E] pending the
# SAC/EM-chart hunt (the fm-trim gate rows are what validate these -- exactly the F-5E pattern,
# which ended up PINNING its 0.75 value from published turn data. Expect the same here.)
CLMAX_VS_MACH = {0.2: 1.90, 0.6: 1.85, 0.8: 1.45, 0.9: 1.25, 1.2: 1.05, 1.6: 0.90, 2.0: 0.80}

TUNNEL_MACH = 0.15  # TP-1538's static data is low-speed tunnel data; scale slopes from here

DEG = math.pi / 180.0


def interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if x <= xs[i + 1]:
            f = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + f * (ys[i + 1] - ys[i])
    return ys[-1]


def lef_schedule(alpha_deg: float, mach: float) -> float:
    """Appendix A steady-state LEF schedule; qbar/ps = 0.7*M^2."""
    d = 1.38 * alpha_deg - 9.05 * (0.7 * mach * mach) + 1.45
    return max(0.0, min(25.0, d))


def blend(alpha, mach, base_tbl, lef_tbl, base_alpha=ALPHA, lef_alpha=ALPHA_LEF):
    """TP-1538 total-coefficient blend at the scheduled LEF:
       C_t = C_base*f + C_lef*(1 - f),  f = dlef/25   (report pp. 37-39, rearranged)."""
    f = lef_schedule(alpha, mach) / 25.0
    c_base = interp(alpha, base_alpha, base_tbl)
    if f >= 1.0 or alpha > lef_alpha[-1]:
        return c_base
    c_lef = interp(alpha, lef_alpha, lef_tbl)
    return c_base * f + c_lef * (1.0 - f)


def cl_cd_data(alpha, mach=0.2):
    """Wind-axis projection of the blended body-axis data, dh = 0, beta = 0."""
    cx = blend(alpha, mach, CX_B0[0], CX_LEF_B0)
    cz = blend(alpha, mach, CZ_B0[0], CZ_LEF_B0)
    a = alpha * DEG
    cl = cx * math.sin(a) - cz * math.cos(a)
    cd = -cx * math.cos(a) - cz * math.sin(a)
    return cl, cd


def cm_total(alpha, dh=0, mach=0.2, xcg=XCG_MODEL):
    """Published Cm_t at dh, transferred to xcg: Cm*eta + dCm + dCm,ds + CZ*(xcg_ref - xcg)."""
    cm = blend(alpha, mach, CM_B0[dh], CM_LEF_B0) if dh == 0 else interp(alpha, ALPHA, CM_B0[dh])
    cz = blend(alpha, mach, CZ_B0[0], CZ_LEF_B0)  # CZ(dh) omitted: sub-1% of cm_de, reported
    cm = cm * ETA_DH[dh] + interp(alpha, ALPHA, DCM_CORR)
    if dh == 0 and alpha >= 40:
        cm += interp(alpha, [35, 40, 45], [0.0, DCM_DS_DH0[40], DCM_DS_DH0[45]])
    return cm + cz * (XCG_REF - xcg)


def slope_per_rad(f, alphas=(0, 5, 10, 15)):
    """Least-squares slope of f(alpha_deg) over the operational band, per radian."""
    xs = [a * DEG for a in alphas]
    ys = [f(a) for a in alphas]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def helmbold(ar, mach):
    """Compressible lift-slope (same function the F-5E's derive.py uses)."""
    if mach < 0.95:
        b2 = 1.0 - mach * mach
        return 2 * math.pi * ar / (2 + math.sqrt(ar * ar * b2 + 4))
    if mach < 1.05:
        return helmbold(ar, 0.94)
    b = math.sqrt(mach * mach - 1.0)
    return (4.0 / b) * (1.0 - 1.0 / (2.0 * ar * b))


def lef_mean(base, lef_inc, alphas=(0, 5, 10, 15), mach=0.2):
    """Mean over the operational band of base(alpha) + (1 - dlef/25)*inc(alpha)."""
    tot = 0.0
    for a in alphas:
        f = lef_schedule(a, mach) / 25.0
        tot += interp(a, ALPHA, base) + (1.0 - f) * interp(a, ALPHA_LEF, lef_inc)
    return tot / len(alphas)


def damper_table(base, lef_inc, mach=0.2):
    """The LEF-blended damper at each alpha on the -20..45 grid -- the per-alpha form of lef_mean.
    engine#899 gives cm_q/cl_p/cn_r optional alpha tables that OVERRIDE the scalar in computeMoments,
    so the model finally carries the report's alpha-dependence instead of a single band mean. Grid is
    ALPHA_LEF (the range where both the base table and its LEF increment are published); the engine
    interpolates linearly and edge-clamps past 45 deg, which the FBW alpha cap keeps out of anyway."""
    return [interp(a, ALPHA, base) + (1.0 - lef_schedule(a, mach) / 25.0) * interp(a, ALPHA_LEF, lef_inc)
            for a in ALPHA_LEF]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — the nine schema derivatives
# ═══════════════════════════════════════════════════════════════════════════════════════════

def moments():
    m = {}
    # Pitch. cm_alpha at the MODEL CG; the engine has no Cm0 slot, so the (small) offset at
    # alpha = 0 is dropped and quantified in --check.
    m["cm_alpha"] = slope_per_rad(lambda a: cm_total(a, 0))
    m["cm_q"] = lef_mean(CMQ, DCMQ_LEF)
    # cm_de from the +/-10 deg spread (eta = 1.0 both sides; the +/-25 spread is nonlinear --
    # printed for the record in --check). Per radian of stabilator.
    de = [(cm_total(a, 10) - cm_total(a, -10)) / (20.0 * DEG) for a in (0, 5, 10, 15)]
    m["cm_de"] = sum(de) / len(de)
    # Lateral: slopes from the beta = +4 deg columns (the beta = 0 baselines print as zero),
    # mean over alpha 0..15. cl_beta grows strongly with alpha (dihedral effect follows lift);
    # the band mean is the honest scalar and the spread is printed in --check.
    m["cl_beta"] = sum(CL_BETA4[a] / (4.0 * DEG) for a in (0, 5, 10, 15)) / 4.0
    m["cn_beta"] = sum(CN_BETA4[a] / (4.0 * DEG) for a in (0, 5, 10, 15)) / 4.0
    # Yaw CG transfer (the report's own term): Cn_t -= CY_t*(xcg_ref - xcg)*cbar/b.
    cy_beta = sum(CY_BETA4[a] / (4.0 * DEG) for a in (0, 5, 10, 15)) / 4.0
    m["cn_beta"] -= cy_beta * (XCG_REF - XCG_MODEL) * (MAC_M / B_M)
    m["cl_p"] = lef_mean(CLP, DCLP_LEF)
    m["cn_r"] = lef_mean(CNR, DCNR_LEF)
    # Controls. TP-1538's positive aileron gives NEGATIVE Cl (its deflection sign is opposite
    # the engine's normalized right-roll command); the engine wants cl_da > 0, so the mapping
    # is |dCl|/da. Increments are the deflected-total tables minus the ~zero beta=0 base.
    m["cl_da"] = -sum(CL_DA20_B0[a] for a in (0, 5, 10, 15)) / 4.0 / (20.0 * DEG)
    m["cn_dr"] = sum(CN_DR30_B0[a] for a in (0, 5, 10, 15)) / 4.0 / (30.0 * DEG)
    return m


# Dropped-but-computed lateral cross terms, for the record and the engine schema-gap issue.
def dropped_controls():
    cn_da = sum(CN_DA20_B0[a] for a in (0, 5, 10, 15)) / 4.0 / (20.0 * DEG)  # adverse yaw
    cl_dr = sum(CL_DR30_B0[a] for a in (0, 5, 10, 15)) / 4.0 / (30.0 * DEG)
    return cn_da, cl_dr


# Sign conventions the validator enforces, and fighter-magnitude bands. cm_alpha's floor is
# WIDER than the F-5E's (-0.15 vs -0.30): a relaxed-stability airframe transferred to its
# forward CG limit is honestly weaker in pitch stiffness than a conventionally stable jet,
# and that weakness is the aircraft's signature, not an authoring error.
BOUNDS = {
    "cm_alpha": (-2.00, -0.15), "cm_q": (-25.0, -3.0), "cm_de": (-2.00, -0.30),
    "cl_beta": (-0.30, -0.02), "cl_p": (-0.60, -0.20), "cl_da": (0.03, 0.20),
    "cn_beta": (0.05, 0.35), "cn_r": (-0.60, -0.08), "cn_dr": (-0.20, -0.02),
}


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — cl_table / cd_table on the pack grid
# ═══════════════════════════════════════════════════════════════════════════════════════════
# M 0.2 column: the blended data, verbatim projection [P].
# Higher columns: the linear range scales by the Helmbold slope ratio (the F-5E's exact
# method), capped by the CL_max envelope with the F-5E's documented post-peak collapse; CD
# scales its lift-dependent part by (CL_M/CL_data)^2 and holds monotone-rising past the peak.
# Zero-lift compressible drag rise lives ONLY in [aero.cd_wave] -- never double-counted here.

def cl_table():
    # The data's own lift-curve slope, for locating each scaled column's envelope intercept.
    cla_data = slope_per_rad(lambda a: cl_cd_data(a)[0])
    rows = []
    for a in ALPHA_PACK:
        row = []
        for m in MACH_PACK:
            cl_data, _ = cl_cd_data(a, 0.2)
            if m <= 0.2:
                cl = cl_data  # the [P] column: blended data, verbatim -- its own envelope
            else:
                r = helmbold(AR, m) / helmbold(AR, TUNNEL_MACH)
                clmax = CLMAX_VS_MACH[m]
                a_peak = math.degrees(clmax / (cla_data * r))  # where the scaled line meets it
                cl = cl_data * r
                if abs(a) <= a_peak:
                    cl = math.copysign(min(abs(cl), clmax), cl) if cl != 0 else 0.0
                else:
                    # past this column's envelope: the F-5E collapse shape [E]
                    cl = math.copysign(
                        clmax * max(0.45, 1.0 - 0.035 * (abs(a) - a_peak)), cl if cl else 1.0)
            row.append(round(cl, 4))
        rows.append(row)
    return rows


def cd_table():
    _, cd0 = cl_cd_data(0.0, 0.2)
    cls = cl_table()
    rows = []
    for i, a in enumerate(ALPHA_PACK):
        cl_data, cd_data = cl_cd_data(a, 0.2)
        row = []
        for j, m in enumerate(MACH_PACK):
            cl_m = cls[i][j]
            if abs(cl_data) > 1e-6:
                cd = cd0 + (cd_data - cd0) * (cl_m / cl_data) ** 2
            else:
                cd = cd_data
            row.append(cd)
        rows.append(row)
    # Past each column's CL peak, CD must keep rising while CL collapses (the data itself does
    # this at M 0.2; the scaled columns need it enforced).
    for j in range(len(MACH_PACK)):
        peak_i = max(range(len(ALPHA_PACK)), key=lambda i: cls[i][j])
        for i in range(peak_i + 1, len(ALPHA_PACK)):
            if ALPHA_PACK[i] > 0 and rows[i][j] < rows[i - 1][j] * 1.03:
                rows[i][j] = rows[i - 1][j] * 1.03
    return [[round(v, 5) for v in row] for row in rows]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — thrust deck
# ═══════════════════════════════════════════════════════════════════════════════════════════
# Table VI verbatim for M 0.2..1.0 [P]. Extension to M 1.2/1.6/2.0 is [E]: each altitude row
# starts from its own last published Mach-interval growth ratio, DECAYED by 0.6 per further
# 0.2-Mach step -- the F-16's fixed ventral inlet is sized for the transonic regime and its
# pressure recovery falls off above M ~1.6, so raw geometric continuation (which would put
# M 2.0 thrust at altitude ABOVE sea-level static) is physically wrong in the direction that
# matters. The extension is FROZEN BEFORE cd_wave is fitted, so the single published M 2.05
# point is spent once, on cd_wave -- never twice.

MACH_EXT = [1.2, 1.6, 2.0]
RAM_DECAY = 0.6  # [E] per-0.2-Mach decay of the growth ratio's excess over 1.0


def thrust_deck(tbl):
    cols = len(T_ALT_M)
    deck = {m: [tbl[i][c] for c in range(cols)] for i, m in enumerate(T_MACH)}
    for c in range(cols):
        excess = tbl[4][c] / tbl[3][c] - 1.0  # T(1.0)/T(0.8) per altitude row
        prev = tbl[4][c]
        last = 1.0
        for m in MACH_EXT:
            steps = round((m - last) / 0.2)
            for _ in range(steps):
                excess *= RAM_DECAY
                prev *= 1.0 + excess
            deck.setdefault(m, [0.0] * cols)[c] = prev
            last = m
    return deck


# ═══════════════════════════════════════════════════════════════════════════════════════════
# SECTION 6/7/8 — checks, audit, output
# ═══════════════════════════════════════════════════════════════════════════════════════════

def isa(h):
    T = 288.15 - 0.0065 * min(h, 11000.0)
    if h <= 11000.0:
        p = 101325.0 * (T / 288.15) ** 5.2559
    else:
        p11 = 101325.0 * (216.65 / 288.15) ** 5.2559
        p = p11 * math.exp(-9.80665 * (h - 11000.0) / (287.05 * 216.65))
    return p / (287.05 * T), math.sqrt(1.4 * 287.05 * T)


def checks():
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + msg)
        ok = ok and cond

    # RSS confirmation: the transcription is only faithful if the data is UNSTABLE at 0.35c.
    raw = slope_per_rad(lambda a: cm_total(a, 0, xcg=XCG_REF))
    check(raw > 0, f"dCm/dalpha at 0.35c = {raw:+.3f}/rad -- RSS confirmed (must be > 0)")
    cla = slope_per_rad(lambda a: cl_cd_data(a)[0])
    check(3.0 <= cla <= 5.0, f"CL_alpha = {cla:.3f}/rad in [3, 5]")
    x_ac = XCG_REF - raw / cla
    check(0.28 <= x_ac <= 0.36, f"x_ac = {x_ac:.3f} cbar (transfer target sanity)")

    m = moments()
    for k, v in m.items():
        lo, hi = BOUNDS[k]
        check(lo <= v <= hi, f"{k} = {v:+.4f} in [{lo}, {hi}]")

    cls, cds = cl_table(), cd_table()
    col0 = [r[0] for r in cls]
    peak_i = max(range(len(col0)), key=lambda i: col0[i])
    check(30 <= ALPHA_PACK[peak_i] <= 40,
          f"CL peak (M0.2) = {col0[peak_i]:.3f} at alpha {ALPHA_PACK[peak_i]} (expect 30..40)")
    gpeak = max(max(r) for r in cls)
    check(abs(gpeak - col0[peak_i]) < 1e-9,
          "global CL argmax is in the [P] column (validator stall rule keys on it)")
    for j, mach in enumerate(MACH_PACK):
        col = [r[j] for r in cls]
        pi = max(range(len(col)), key=lambda i: col[i])
        mono = all(col[i] < col[i + 1] for i in range(ALPHA_PACK.index(0), pi))
        check(mono, f"CL monotone over [0, peak] at M {mach} (FBW limiter bisects here)")
    check(all(v > 0 for r in cds for v in r), "cd_table strictly positive")
    _, cd0 = cl_cd_data(0.0, 0.2)
    check(0.015 <= cd0 <= 0.05, f"cd0 (scheduled LEF, alpha 0) = {cd0:.4f} in [0.015, 0.05]")
    for tbl, nm in ((T_MIL_N, "mil"), (T_MAX_N, "max")):
        check(all(tbl[i][c] > tbl[i][c + 1] for i in range(5) for c in range(5)),
              f"T_{nm} monotone decreasing with altitude")

    # Dropped-term report
    cn_da, cl_dr = dropped_controls()
    cm0 = cm_total(0.0, 0)
    print(f"""
  NOW MODELED (schema slots added in engine#899/#900/#901 -- were dropped through v0.3.4):
    Cm0 at the model CG        = {cm0:+.4f}   (zero-elevator trim alpha shift ~ {-cm0 / m['cm_alpha'] / DEG:+.1f} deg) -> [aero.moments].cm0
    Ixz                        = {IXZ:.0f} kg m^2 (report Table I) -> [flight_model].ixz_kg_m2
    engine angular momentum He = 216.9 kg m^2/s (report p. 40) -> [flight_model].engine_ang_momentum
    adverse yaw cn_da          = {cn_da:+.4f}/rad -> [aero.moments].cn_da
    rudder roll cl_dr          = {cl_dr:+.4f}/rad -> [aero.moments].cl_dr
    cm_q / cl_p / cn_r alpha   = the LEF-blended tables -> [aero.moments].{{cm_q,cl_p,cn_r}}_table (override the scalars)
    FLCS AoA cap 25.5 deg      = TP-1538 App. A -> [aero.limits].alpha_limit_deg (engine#900)
    single-engine damage       = one F100, total-thrust-loss, no yaw -> [damage.subsystems.engine] (engine#901)

  STILL DROPPED (no clean source typed / no scalar reduction), quantified:
    CXq / CZq, Cnp / Clr       = typed, alpha-dependent; no schema slot (axial/secondary damping)
    dCm,sb / dCZ,sb            = speed-brake pitch/lift increments are alpha-tables; only dCX_SB
                                 (drag) is typed, and it is already carried by speedbrake_cd
    T_idle deck                = published (Table VI, incl. negative ram-drag cells) but NOT yet
                                 typed here; author the idle row before filling [engine.idle_thrust]
    dCl_beta / dCn_beta corr   = negligible (<= 0.001 at 3 alphas)
    cm_de +/-25 spread         = {sum((cm_total(a, 25) - cm_total(a, -25)) / (50 * DEG) for a in (0, 5, 10, 15)) / 4:+.3f}/rad vs +/-10 {m['cm_de']:+.3f}/rad (nonlinear falloff)
    cl_beta alpha-dependence   = {CL_BETA4[0] / (4 * DEG):+.3f} .. {CL_BETA4[15] / (4 * DEG):+.3f}/rad over alpha 0..15 (band mean shipped)
""")
    print("CG sensitivity (the transfer is one constant -- this is what any other choice costs):")
    print(f"  {'xcg/c':>6} {'cm_alpha':>9} {'static margin':>14}")
    for x in (0.25, 0.28, 0.30, 0.33, 0.35, 0.39):
        s = slope_per_rad(lambda a: cm_total(a, 0, xcg=x))
        print(f"  {x:>6.2f} {s:>+9.3f} {(x_ac - x) * 100:>+13.1f}%")
    return ok


def fmt_table(alpha, mach, rows, prec):
    out = [f"alpha = {alpha}", f"mach  = {mach}", "values = ["]
    for a, row in zip(alpha, rows):
        out.append("  " + ", ".join(f"%{prec + 3}.{prec}f" % v for v in row) + f",   # alpha {a:g}")
    out.append("]")
    return "\n".join(out)


def main():
    if "--check" in sys.argv:
        sys.exit(0 if checks() else 1)

    m = moments()
    cm0 = cm_total(0.0, 0)
    cn_da, cl_dr = dropped_controls()
    print("# Generated by transcribe.py from NASA TP-1538 -- do not hand-edit. Re-run and paste.\n")
    print("[aero.moments]")
    for k in ("cm_alpha", "cm_q", "cm_de", "cl_beta", "cl_p", "cl_da", "cn_beta", "cn_r", "cn_dr"):
        print(f"{k:<9}= {m[k]:+.3f}")
    # Cross/constant terms -- schema slots added in engine#899 (were dropped, quantified in --check).
    print(f"{'cm0':<9}= {cm0:+.4f}   # zero-elevator pitching moment at the model CG")
    print(f"{'cn_da':<9}= {cn_da:+.4f}   # adverse yaw from aileron")
    print(f"{'cl_dr':<9}= {cl_dr:+.4f}   # roll from rudder")
    # Alpha-dependent dampers (engine#899): each OVERRIDES its scalar above at runtime. The scalar
    # is retained as the required fallback and stays the band mean of the table.
    for tname, base, inc in (("cm_q_table", CMQ, DCMQ_LEF),
                             ("cl_p_table", CLP, DCLP_LEF),
                             ("cn_r_table", CNR, DCNR_LEF)):
        vals = damper_table(base, inc)
        print(f"\n[aero.moments.{tname}]")
        print(f"alpha  = {ALPHA_LEF}")
        print("values = [" + ", ".join(f"{v:+.4f}" for v in vals) + "]")
    print("\n[aero.cl_table]")
    print(fmt_table(ALPHA_PACK, MACH_PACK, cl_table(), 4))
    print("\n[aero.cd_table]")
    print(fmt_table(ALPHA_PACK, MACH_PACK, cd_table(), 5))

    for name, tbl in (("mil_thrust", T_MIL_N), ("ab_thrust", T_MAX_N)):
        deck = thrust_deck(tbl)
        machs = T_MACH + MACH_EXT
        print(f"\n[engine.{name}]")
        print(f"mach   = {machs}")
        print(f"alt_km = {[a / 1000.0 for a in T_ALT_M]}")
        print("values = [")
        for mm in machs:
            print("  " + ", ".join(f"{v / 1000.0:7.2f}" for v in deck[mm]) + f",   # M {mm:g}")
        print("]")


if __name__ == "__main__":
    main()
