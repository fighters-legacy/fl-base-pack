#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Derive the MiG-21bis's lift table, inertias and moment derivatives.

Run:  python3 aircraft/mig21bis/derive.py        # prints TOML blocks for mig21bis.toml

WHY THIS IS A SCRIPT AND NOT A TABLE OF CONSTANTS
-------------------------------------------------
No public CL(alpha, M) database exists for the MiG-21 (SOURCES.md says why), so the aerodynamics
are derived from published geometry by standard, citable methods and then pinned by the published
performance anchors in mig21bis.expect.toml. The geometry inputs are UNUSUALLY good for this pack:
the declassified F-13 manual publishes the wing, control-surface and empennage geometry to the
millimetre, including the MAC (4.002 m) and the CG range (31-35% MAC) -- numbers the B-1B had to
estimate.

THE TAILED DELTA IS THE WHOLE POINT OF THIS AIRCRAFT (fl-base-pack#41)
----------------------------------------------------------------------
At aspect ratio 2.23 with a 57 deg leading edge, nothing in the pack flies like this wing, and two
standard-method choices follow from it:

1. LIFT IS POLHAMUS, NOT JUST HELMBOLD. A slender delta carries a large nonlinear vortex-lift
   increment: CL = Kp sin(a) cos^2(a) + Kv cos(a) sin^2(a) (Polhamus leading-edge-suction
   analogy). Kp is the potential-flow slope (Helmbold at half-chord sweep); Kv ~ pi for a slender
   delta. That is what gives the delta its high stall angle and soft break -- encoding it in the
   cl_table is the difference between a MiG-21 and a re-skinned F-5E. The vortex term fades as the
   leading edge approaches sonic (M_n = M cos(sweep_LE) -> 1 at M ~ 1.84).

2. INDUCED DRAG IS BRUTAL AND THAT IS CORRECT. k = 1/(pi AR e) at AR 2.23 with a delta-typical
   Oswald factor is several times the F-5E's k. The delta bleeding speed in any turning fight is
   the aircraft's published character (Gordon), not a modelling error. Do not "fix" k.

WHAT IS CALIBRATED, AND AGAINST WHAT
------------------------------------
CD0 and the [aero.cd_wave] shape are the only fitted quantities, pinned by the M2.05/13,000 m
anchor with the ceiling and climb rows as cross-checks. Everything else is geometry.
"""

import math

# ─── Published geometry — SOURCES.md, all [P] (F13-TD manual unless noted) ───────
S = 23.0            # m^2   wing area (F13-TD and JAWA agree)                    [P]
B = 7.154           # m     span (JAWA; F13-TD 7.150)                            [P]
MAC = 4.002         # m     mean aerodynamic chord -- PUBLISHED, not derived     [P]
SWEEP_LE = 57.0     # deg   leading-edge sweep                                   [P]
LENGTH = 14.10      # m     bis fuselage excl. pitot [P MIG21DE] -- the 14.7 m
                    #       conflict is open (SOURCES.md); enters only the [E]
                    #       inertia arms, where 4% is far inside the method noise
S_H = 3.94          # m^2   stabilator area                                      [P]
B_H = 2.6           # m     stabilator span                                      [P]
S_V = 5.32          # m^2   bis wide-chord fin                                   [P]
AIL_MAX = 20.0      # deg   aileron deflection                                   [P]
RUD_MAX = 25.0      # deg   rudder deflection                                    [P]
STAB_MAX = 16.5     # deg   stabilator max (nose-down throw; up is 7.5)          [P]
CG = 0.32           # x/c   mid of the manual's practical 31-35% MAC range       [P]

M_EMPTY = 5895.0    # kg    empty weight                                         [P]
M_FUEL = 2390.0     # kg    2,880 L at the manual's own 0.83 kg/L                [D]
M_GROSS = 8725.0    # kg    with two R-3S                                        [P]

T_MIL = 40.18       # kN    R-25-300 dry, SL static                              [P]
T_AB = 69.58        # kN    R-25-300 full afterburner, SL static                 [P]
# The 97.1-97.4 kN emergency (ЧР) rating is deliberately NOT modelled -- the engine has no
# time-limited regime and inventing a fourth throttle stop is out of scope. SOURCES.md.

# ─── NOT PUBLISHED — engineering estimates ──────────────────────────────────────
OSWALD = 0.55       #       delta-typical span efficiency with vortex flow       [E]
KV0 = math.pi       # /1    Polhamus vortex-lift constant, slender delta         [E]
ALPHA_STALL = 24.0  # deg   usable-lift peak. Not published as one number; the
                    #       bis's operational AoA limit and the 250 km/h landing
                    #       speed both sit consistently with a peak here (the
                    #       cross-check below prints the implied landing margin)  [E]
POST_STALL = 0.85   #       fraction of peak CL retained 4 deg past the peak     [E]
CL0 = 0.0           #       thin (4.2-5%) near-symmetric section at 0 incidence  [E]
CLA_CAP = 5.80      # /rad  cap on the derived slope (as on the B-1B)            [E]

# Fighter-class non-dimensional radii of gyration (Roskam Part V, fighter row).
RGYR_X = 0.25       #       roll, referred to span/2                             [E]
RGYR_Y = 0.36       #       pitch, referred to length/2                          [E]
RGYR_Z = 0.40       #       yaw, referred to (span+length)/4                     [E]

# Tail arms and efficiencies. AREAS are published (above); the ARMS are not -- read off the
# reference planform photography against the known fuselage length.
L_H = 4.60          # m     wing AC -> stabilator AC arm                         [E]
L_V = 4.40          # m     wing AC -> fin AC arm                                [E]
Z_V = 1.30          # m     fin AC height above CG                               [E]
AR_V = 1.10         #       fin aspect ratio (broad chord, moderate height)      [E]
ETA_H = 0.90        #       stabilator dynamic-pressure efficiency               [E]
ETA_V = 0.90        #       fin dynamic-pressure efficiency                      [E]
DEPS = 0.40         #       downwash gradient at the tail, low-AR delta          [E]
TAU_R = 0.45        #       rudder flap effectiveness                            [E]
# The stabilator is ALL-MOVING: its control effectiveness is the full surface slope, tau = 1.
TAU_E = 1.00        #       slab-tail effectiveness                              [P]
CN_FUS = -0.10      # /rad  fuselage yaw destabilisation -- a long nose over a
                    #       7 m span normalises to a big number                  [E]
AC = 0.33           # x/c   wing aerodynamic centre. NOT the thin-airfoil 0.25: a slender
                    #       57-deg delta carries its lift centroid well aft — slender-wing
                    #       theory puts the subsonic AC near a third of the MAC, moving
                    #       further aft transonically. 0.25 here derived cm_alpha ~ -0.01,
                    #       an aircraft with no pitch stiffness at all: the headless probe
                    #       flew it into the ground on the FIRST spawn while every
                    #       validator and all four expect rows stayed green.        [D]

# ─── CALIBRATION — the ONLY fitted numbers in this file ──────────────────────────
# Fitted against the published anchors in mig21bis.expect.toml:
#     M2.05 at 13,000 m (AB, the headline anchor -- pins cd0 + the supersonic wave level)
#     235 m/s SL climb, full AB, combat-loaded (pins the AB deck + subsonic drag level)
#     17,500 m service ceiling (cross-checks the lapse law at altitude)
# Re-run fm-trim --expect after changing ANY of these.
CD0 = 0.0185            # zero-lift drag, subsonic                               [D]
CD_WAVE_MACH = [0.85, 0.92, 0.98, 1.05, 1.15, 1.40, 1.70, 2.05]
CD_WAVE_VALS = [0.0000, 0.0060, 0.0180, 0.0330, 0.0350, 0.0300, 0.0255, 0.0225]

# ─── Derived geometry ────────────────────────────────────────────────────────────
AR = B * B / S                       # 2.225 -- matches SOURCES.md
# Half-chord sweep of a (near-)pure delta: tan(c/2) = tan(LE) - 2(1-lam)/(AR(1+lam)), lam ~ 0.
SWEEP_C2 = math.degrees(math.atan(math.tan(math.radians(SWEEP_LE)) - 2.0 / AR))

# LE goes sonic when M cos(LE sweep) = 1; the vortex term fades linearly M1.0 -> there.
M_LE_SONIC = 1.0 / math.cos(math.radians(SWEEP_LE))     # ~1.84


def cl_alpha(ar, sweep_c2_deg, mach, eta=0.95):
    """Potential-flow lift-curve slope /rad (DATCOM/Helmbold; supersonic 4/beta AR-corrected)."""
    sweep = math.radians(sweep_c2_deg)
    if mach <= 0.90:
        beta2 = 1.0 - mach * mach
        root = math.sqrt(ar * ar * beta2 / (eta * eta) * (1.0 + math.tan(sweep) ** 2 / beta2) + 4.0)
        return min(CLA_CAP, 2.0 * math.pi * ar / (2.0 + root))
    if mach >= 1.20:
        b = math.sqrt(mach * mach - 1.0)
        return min(CLA_CAP, (4.0 / b) * ar / (ar + 2.0 / b))
    lo = cl_alpha(ar, sweep_c2_deg, 0.90, eta)
    hi = cl_alpha(ar, sweep_c2_deg, 1.20, eta)
    return lo + (hi - lo) * (mach - 0.90) / 0.30


def kv(mach):
    """Polhamus vortex-lift constant, faded as the leading edge approaches sonic."""
    if mach <= 1.0:
        return KV0
    if mach >= M_LE_SONIC:
        return 0.0
    return KV0 * (M_LE_SONIC - mach) / (M_LE_SONIC - 1.0)


def cl_polhamus(alpha_deg, mach):
    a = math.radians(alpha_deg)
    kp = cl_alpha(AR, SWEEP_C2, mach)
    return CL0 + kp * math.sin(a) * math.cos(a) ** 2 + kv(mach) * math.cos(a) * math.sin(a) ** 2


K_INDUCED = 1.0 / (math.pi * AR * OSWALD)

# ─── Lift table ─────────────────────────────────────────────────────────────────
# Each Mach column follows the Polhamus curve to a single peak AT the declared stall angle, then
# drops: validate-flight-model requires the table peak within 2 deg of alpha_stall_deg, because
# the engine does not clamp CL -- the table IS the stall. Within this alpha range the Polhamus
# curve is monotonic for every Mach column (its analytic peak sits above 30 deg), so the
# constructed peak-at-stall does not distort the curve below it.
ALPHAS = [-4.0, 0.0, 4.0, 8.0, 12.0, 16.0, 20.0, ALPHA_STALL, 28.0]
MACHS = [0.30, 0.60, 0.90, 1.10, 1.50, 2.05]

cl_values = []
for a in ALPHAS:
    row = []
    for m in MACHS:
        if a <= ALPHA_STALL:
            cl = cl_polhamus(a, m)
        else:
            cl = cl_polhamus(ALPHA_STALL, m) * POST_STALL
        row.append(cl)
    cl_values.append(row)

# Landing-speed closure check (printed, not gated): the published 250 km/h landing speed should
# come out at a normal 1.1-1.2x the 1-g stall speed at landing weight.
M_LANDING = 6800.0      # kg [E]: empty + reserve fuel + pilot
CL_MAX_LAND = cl_polhamus(ALPHA_STALL, 0.30)
V_STALL = math.sqrt(2.0 * M_LANDING * 9.80665 / (1.225 * CL_MAX_LAND * S))
LANDING_RATIO = (250.0 / 3.6) / V_STALL

# ─── Inertias ───────────────────────────────────────────────────────────────────
IXX = M_GROSS * (RGYR_X * B / 2.0) ** 2
IYY = M_GROSS * (RGYR_Y * LENGTH / 2.0) ** 2
IZZ = M_GROSS * (RGYR_Z * (B + LENGTH) / 4.0) ** 2

# ─── Moment derivatives (DATCOM / strip theory) ─────────────────────────────────
M_EVAL = 0.60
CLA_W = cl_alpha(AR, SWEEP_C2, M_EVAL)
AR_H = B_H * B_H / S_H              # 1.716 -- from PUBLISHED area and span
CLA_H = cl_alpha(AR_H, SWEEP_LE, M_EVAL)   # stabilator is swept like the wing (57 deg)
CLA_V = cl_alpha(AR_V, 60.0, M_EVAL)       # fin LE sweep 60 deg [P]

V_H = (S_H * L_H) / (S * MAC)
V_V = (S_V * L_V) / (S * B)

CM_ALPHA = CLA_W * (CG - AC) - ETA_H * V_H * CLA_H * (1.0 - DEPS)
CM_Q = -2.0 * ETA_H * V_H * CLA_H * (L_H / MAC)
CM_DE = -ETA_H * V_H * CLA_H * TAU_E
CN_BETA = ETA_V * V_V * CLA_V + CN_FUS
CN_R = -2.0 * ETA_V * V_V * CLA_V * (L_V / B)
CN_DR = -ETA_V * V_V * CLA_V * TAU_R
# Sweep contribution dominates cl_beta on a 57 deg delta; -2 deg anhedral slightly offsets it.
CL_BETA = -(CLA_W / 6.0) * math.radians(SWEEP_LE) \
    - ETA_V * (S_V * Z_V) / (S * B) * CLA_V \
    + (2.0 / 57.3) * (CLA_W / 8.0)          # dihedral term, NEGATIVE dihedral (-2 deg) [P]
CL_P = -(CLA_W / 12.0)                       # low-AR delta, taper ~0
CL_DA = 0.40 * CLA_W / 6.0                   # aileron effectiveness tau=0.40 [E]

# ─── Thrust decks ───────────────────────────────────────────────────────────────
# Only SL-static ratings are published. Same standard method as the T-38A/B-1B:
#     T(M, h) = T_sl_static * sigma^0.85 * f(M),   f(M) = 1 - 0.20*M + 0.45*M^2
# f(M) is the TURBOJET ram form -- and unlike the B-1B's fixed pitot inlet, the MiG-21's
# translating shock cone is DESIGNED to match the shock system up to ~M2: the quadratic ram growth
# is the physics of this installation, so it is kept, with a decay only past the cone's design
# point. That growth is what makes M2.05 reachable on 69.6 kN of static thrust.
THRUST_MACHS = [0.00, 0.60, 0.90, 1.30, 1.70, 2.05]
THRUST_ALTS_KM = [0.0, 5.0, 11.0, 13.0, 17.5]   # 13 km = the max-speed anchor; 17.5 = ceiling
RAM_KNEE = 2.10     #       cone design point; recovery decays past it           [E]
RAM_DECAY = 0.60    # /Mach                                                      [E]
RHO0 = 1.225


def isa_density(alt_m):
    if alt_m <= 11000.0:
        t = 288.15 - 0.0065 * alt_m
        return RHO0 * (t / 288.15) ** 4.256
    rho11 = RHO0 * (216.65 / 288.15) ** 4.256
    return rho11 * math.exp(-9.80665 * (alt_m - 11000.0) / (287.05 * 216.65))


def ram(mach):
    base = lambda m: 1.0 - 0.20 * m + 0.45 * m * m
    if mach <= RAM_KNEE:
        return base(mach)
    return base(RAM_KNEE) * max(0.0, 1.0 - RAM_DECAY * (mach - RAM_KNEE))


def thrust_table(static_kn):
    return [[static_kn * (isa_density(a * 1000.0) / RHO0) ** 0.85 * ram(m)
             for a in THRUST_ALTS_KM] for m in THRUST_MACHS]


MIL_TABLE = thrust_table(T_MIL)
AB_TABLE = thrust_table(T_AB)

# Fuel flows are [D] from the PUBLISHED R-25 SFC (93 / 98 / 229 kg/(h*kN)) at the static ratings.
FF_IDLE = 93.0 * 3.5 / 3600.0        # idle thrust ~3.5 kN [E]
FF_MIL = 98.0 * T_MIL / 3600.0
FF_AB = 229.0 * T_AB / 3600.0


def fmt(vals, w=7, p=4):
    return ", ".join(f"{v:{w}.{p}f}" for v in vals)


if __name__ == "__main__":
    print(f"""# ── DERIVED — regenerate with `python3 aircraft/mig21bis/derive.py`, do not hand-edit ──
# Geometry: AR {AR:.3f}, half-chord sweep {SWEEP_C2:.1f} deg, LE sonic at M{M_LE_SONIC:.2f}
# CL_alpha potential (M{M_EVAL}): {CLA_W:.3f} /rad; Polhamus peak CL {CL_MAX_LAND:.3f} at {ALPHA_STALL:.0f} deg
# Landing check: Vs(1g, {M_LANDING:.0f} kg) = {V_STALL * 3.6:.0f} km/h -> published 250 km/h = {LANDING_RATIO:.2f} Vs
# k = 1/(pi*AR*e) = {K_INDUCED:.4f} with e = {OSWALD} [E] -- the delta's defining induced drag

[flight_model]
mass_kg      = {M_EMPTY:.0f}
wing_area_m2 = {S:.2f}
wingspan_m   = {B:.3f}
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
k             = {K_INDUCED:.4f}
speedbrake_cd = 0.0300
gear_cd       = 0.0200

[aero.cd_wave]
mach   = [{fmt(CD_WAVE_MACH, 5, 2)}]
values = [{fmt(CD_WAVE_VALS, 7, 4)}]

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

# fuel flows [D] from published R-25 SFC: idle {FF_IDLE:.3f}  mil {FF_MIL:.3f}  ab {FF_AB:.3f} kg/s
""")
