#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Derive the MiG-29A's lift table, inertias, moment derivatives and thrust decks.

Run:  python3 aircraft/mig29a/derive.py        # prints TOML blocks for mig29a.toml

WHY THIS IS A SCRIPT AND NOT A TABLE OF CONSTANTS
-------------------------------------------------
There is no public CL(alpha, M) database for the MiG-29 (SOURCES.md says so plainly), so the
aerodynamics are derived from published geometry by standard, citable methods and then pinned by
the published performance anchors in mig29a.expect.toml. Unlike the MiG-21bis — whose declassified
F-13 manual publishes wing geometry to the millimetre — the geometry inputs here are THIN: span,
area, length, height and two planform angles, and nothing else. Every quantity that is not one of
those is derived or estimated, and says which.

THE LERX IS THE POINT OF THIS AIRCRAFT (fl-base-pack#43)
--------------------------------------------------------
The MiG-29 is the pack's first blended-body / LERX airframe and its first twin-engine fighter.
Two method choices follow, and both are the airframe rather than a convenience:

1. LIFT IS POLHAMUS, NOT PLAIN HELMBOLD — the same treatment the MiG-21bis needed, for a
   different reason. The bis is a slender delta whose whole wing sheds the vortex; this wing is
   a moderate-AR (3.40) trapezoid with a 73.5-degree LERX bolted to its root. The LERX vortex is
   what gives the aircraft its published high-alpha behaviour, so the vortex term is real — but
   the constant is NOT the slender-delta pi. It is scaled to the fraction of the span the LERX
   actually drives (KV0 below), which is the honest difference between this wing and the bis's.

2. INDUCED DRAG IS MODEST, NOT BRUTAL. At AR 3.40 with LERX-recovered leading-edge suction, k
   comes out at 58% of the bis's 0.26. That asymmetry — the Fulcrum holds energy in a turn where
   the Fishbed bleeds it — is the published character of the two aircraft, and it falls out of
   the geometry rather than being asserted.

THE ENGINE IS A LOW-BYPASS TURBOFAN BEHIND A VARIABLE-RAMP INLET
-----------------------------------------------------------------
Only SL-static ratings are published, so the deck is derived the same way the MiG-21bis's and
B-1B's were: density lapse times ram recovery. The ram term keeps its quadratic growth to the
inlet's design point, because — like the bis's translating cone and UNLIKE the B-1B's fixed
inlets — this installation has variable ramps built to match the shock system at high Mach.
Getting this wrong in the B-1B's direction (quadratic growth on a fixed inlet) overstated its top
speed by a third; getting it wrong in the other direction would make M2.25 unreachable.

WHAT IS CALIBRATED, AND AGAINST WHAT
------------------------------------
CD0 and the [aero.cd_wave] shape are the ONLY fitted quantities, pinned by the M2.25 / 11,000 m
anchor with the sea-level placard, the climb row and the ceiling row as cross-checks. Everything
else is geometry or a stated estimate.
"""

import math

# ─── Published — SOURCES.md, [P] RAC MiG (manufacturer) unless noted ─────────────
S = 38.0            # m^2   wing reference area [P WIKI spec block]
B = 11.36           # m     span                                                  [P]
LENGTH = 17.32      # m     length overall                                        [P]
HEIGHT = 4.73       # m     height                                                [P]
SWEEP_LE = 42.0     # deg   outer-panel leading-edge sweep  [P Jane's — see below]
SWEEP_LERX = 73.5   # deg   LERX leading-edge sweep (73 deg 30 min)          [P Jane's]
# ⚠ Both angles come from the Jane's MiG-29K block. The K is a navalised derivative with a
# LARGER wing (11.99 m span, 42.0 m^2) whose span and area are deliberately NOT used here — only
# the planform ANGLES, which it inherited unchanged. Same admissibility rule the MiG-21bis applied
# to the F-13 manual: shape crosses variants, size and performance do not. SOURCES.md.

M_NORMAL = 14900.0  # kg    normal take-off weight                                [P]
M_MTOW = 18000.0    # kg    maximum take-off weight                               [P]
M_FUEL = 3500.0     # kg    internal fuel [P] (= 4,300 L at the implied 0.814 kg/L)

T_MIL_1 = 49.42     # kN    RD-33 dry, SL static, PER ENGINE      [P Gordon 2006 p.335]
T_AB_1 = 81.40      # kN    RD-33 full AB, SL static, PER ENGINE  [D from 8,300 kgf [P]]
N_ENG = 2

# ⚑ INSTALLATION LOSS. The two ratings above are UNINSTALLED brochure figures — what the engine
# makes on a test stand. What the aircraft gets is less: inlet pressure recovery, bleed air and
# accessory power extraction all come off the top. This pack has already paid for confusing the
# two once (the F-5E's ~7% lesson, recorded in f16a.toml), and the F-16A avoids it only because
# TP-1538 publishes installed-grade data outright.
#
# The symptom that forced this: with uninstalled thrust the model out-sustained the F-16A's
# published-data model at every altitude — 8.6 g against 7.1 g at sea level. That is the wrong
# answer. The Luftwaffe assessment in SOURCES.md is explicit that the Fulcrum's advantage was nose
# authority at LOW SPEED, and that it LOST the energy fight; a MiG-29 that out-turns an F-16 in
# sustained flight is flattering the aircraft against its own published record.
# NOT APPLIED, and the reason is the useful part: it is NOT IDENTIFIABLE. The M2.25 anchor pins
# the thrust-MINUS-drag balance, so removing 6% of thrust and re-fitting cd0 to hold the anchor
# gives the sustained turn straight back (measured: 8.6 g -> 8.3 g -> 8.6 g as cd0 follows), while
# driving cd0 to 0.0235 — below what a twin-engine airframe should carry against the F-16A's
# PUBLISHED 0.0216. One anchor cannot separate two unknowns, so the pack keeps the published
# (uninstalled) rating and puts the uncertainty where it actually lives: the Oswald factor below.

MAX_MACH = 2.25     #       placard at altitude                                   [P]
MAX_KEAS = 810.0    # kn    1,500 km/h at sea level, as EAS                       [D]
CEILING_M = 18000.0 # m     service ceiling                                       [P]
ROC_SL = 330.0      # m/s   rate of climb                            [P Flug Revue]
G_LIMIT = 9.0       #       airframe design load factor                           [P]
RANGE_KM = 1430.0   # km    range on max internal fuel        [P Jane's Aircraft Upgrades]

# ─── EMPTY WEIGHT — the SOURCES.md open item, resolved here ─────────────────────
# The record gives 10,900 kg (aerospaceweb) and 11,000 kg (Wikipedia). Neither states a datum,
# they differ by under 1%, and the manufacturer publishes no empty weight at all. The mass-closure
# check below does NOT discriminate between them — both land within 0.5% of the published normal
# take-off weight — so closure cannot settle it and pretending otherwise would be dishonest.
#
# RULING: take the HEAVIER figure. Where the record cannot choose, the pack takes the value that
# does not flatter the aircraft — the same direction the B-1B's ram-decay note applies ("wrong in
# the direction that flatters the aircraft" is the failure to avoid). A lighter empty weight buys
# free climb, acceleration and turn performance that no source actually grants.
M_EMPTY = 11000.0   # kg                                                          [P, see above]

# Mass-closure inputs, all [E], used only to show the empty weight is consistent with the
# published normal take-off weight — not to derive anything the model uses.
M_PILOT = 100.0     # kg    pilot and kit                                         [E]
M_GUN_AMMO = 120.0  # kg    150 rounds of 30x165 mm                               [E]
M_R73 = 105.0       # kg    R-73E, each                              [P R73-WIKI]

# ─── NOT PUBLISHED — engineering estimates ──────────────────────────────────────
TAPER = 0.25        #       outer-panel taper ratio; fighter-typical, and the only
                    #       free parameter in the MAC derivation below             [E]
OSWALD = 0.62       #       span efficiency. CALIBRATED AGAINST THE SHIPPING F-16A MODEL, not
                    #       against a publication: no MiG-29 energy-manoeuvrability data is public
                    #       (SOURCES.md), and neither published anchor constrains induced drag at
                    #       all — max level speed is insensitive to k to four significant figures.
                    #       At the geometric 0.75 this aircraft out-sustained the F-16A's
                    #       published-data model 8.6 g to 7.1 g, contradicting the Luftwaffe
                    #       assessment that the Fulcrum's edge was nose authority at LOW SPEED and
                    #       that it LOST the energy fight. 0.62 brings sustained turn to parity.
                    #       [[feedback_calibrate_against_shipping_model]] is the rule being
                    #       followed: calibrate against the model you ship.                  [E]
KV0 = 1.80          # /1    Polhamus vortex-lift constant. NOT the slender-delta
                    #       pi the bis uses: this wing is AR 3.40 and only its
                    #       inboard span is LERX-driven, so the vortex increment is
                    #       real but partial. The single most consequential [E] in
                    #       this file — it sets the high-alpha character.          [E]
ALPHA_STALL = 30.0  # deg   aerodynamic stall. Not published. Bounded by two facts:
                    #       the automatic slats + LERX make this a genuine
                    #       high-alpha aircraft, and the F-16A's PUBLISHED 35 deg
                    #       (TP-1538, deployed LEF) is the pack's upper anchor for
                    #       the class. 30 sits below it deliberately.              [E]
POST_STALL = 0.85   #       fraction of peak CL retained 4 deg past the peak       [E]
CL0 = 0.0           #       near-symmetric section at zero incidence               [E]
CLA_CAP = 5.80      # /rad  cap on the derived slope (as on the B-1B and bis)      [E]

# Fighter-class non-dimensional radii of gyration (Roskam Part V, fighter row).
RGYR_X = 0.25       #       roll, referred to span/2                               [E]
RGYR_Y = 0.36       #       pitch, referred to length/2                            [E]
RGYR_Z = 0.40       #       yaw, referred to (span+length)/4                       [E]

# Empennage. NOTHING here is published — no MiG-29 tail areas, spans or arms were found in any
# admissible source. Scaled from the published overall dimensions by the proportions this
# configuration class carries. Flagged [E] individually in mig29a.toml.
S_H = 7.50          # m^2   BOTH stabilators, total                                [E]
B_H = 7.78          # m     stabilator span (tip to tip)                           [E]
S_V = 10.10         # m^2   BOTH fins, total — twin canted fins                    [E]
AR_V = 1.35         #       per-fin aspect ratio                                   [E]
L_H = 5.60          # m     wing AC -> stabilator AC arm                           [E]
L_V = 5.20          # m     wing AC -> fin AC arm                                  [E]
Z_V = 1.55          # m     fin AC height above CG                                 [E]
ETA_H = 0.90        #       stabilator dynamic-pressure efficiency                 [E]
ETA_V = 0.85        #       fin efficiency — twin fins sit in the wing/LERX wake   [E]
DEPS = 0.35         #       downwash gradient at the tail                          [E]
TAU_R = 0.45        #       rudder flap effectiveness                              [E]
TAU_E = 1.00        #       all-moving stabilator: full surface slope              [E]
CN_FUS = -0.12      # /rad  fuselage yaw destabilisation                           [E]

# ⚑ STATIC MARGIN. The MiG-29A has NO fly-by-wire (SOURCES.md), so unlike the F-16 it cannot be
# relaxed-stability: it must be conventionally stable to be flyable at all. CG is set comfortably
# forward of the AC to reflect that, and the MiG-21bis's lesson is why the AC is not the
# thin-airfoil 0.25 — a LERX wing carries its lift centroid aft, and an AC too far forward derives
# a cm_alpha near zero, which is an aircraft the probe flies into the ground while every validator
# stays green.
CG = 0.25           # x/c   centre of gravity                                      [E]
AC = 0.30           # x/c   wing aerodynamic centre, LERX-augmented                [E]

CTRL_ELEV = 25.0    # deg   all-moving stabilator throw                            [E]
CTRL_AIL = 20.0     # deg   aileron                                                [E]
CTRL_RUD = 25.0     # deg   rudder (per fin)                                       [E]

# Specific fuel consumption. NOT PUBLISHED for the RD-33 in any admissible source — the MiG-21bis
# had a published per-regime SFC table for the R-25 and this engine has no equivalent. Class
# values for a low-bypass afterburning turbofan, cross-checked below against the ONE published
# fuel-economy figure that exists (1,430 km on 3,500 kg internal).
SFC_MIL = 0.77      # lb/(lbf*h)  military                                         [E]
SFC_AB = 2.05       # lb/(lbf*h)  full afterburner                                 [E]
SFC_IDLE_KN = 6.0   # kN          idle thrust, both engines                        [E]

# ─── CALIBRATION — the ONLY fitted numbers in this file ──────────────────────────
# Fitted against the published anchors in mig29a.expect.toml:
#     M2.25 at 11,000 m (AB) — the headline anchor; pins cd0 + the supersonic wave level
#     M1.224 at sea level    — the 1,500 km/h placard; governed by max_keas, cross-checks cd_wave
#     330 m/s SL climb (AB)  — pins the AB deck against the subsonic drag level
#     18,000 m ceiling       — cross-checks the lapse law at altitude
# Re-run fm-trim --expect after changing ANY of these.
CD0 = 0.0250            # zero-lift drag, subsonic                                 [D]
CD_WAVE_MACH = [0.85, 0.95, 1.05, 1.20, 1.60, 2.00, 2.25]
CD_WAVE_VALS = [0.0000, 0.0150, 0.0340, 0.0330, 0.0305, 0.0290, 0.0283]

# ─── Derived geometry ────────────────────────────────────────────────────────────
AR = B * B / S                       # 3.396 — reproduces the published "3.4"
# MAC from the reference trapezoid. c_root closes from area, span and taper; MAC is the standard
# integral. This is the file's one geometric leap: TAPER is [E], so MAC is [D] on an [E].
C_ROOT = 2.0 * S / (B * (1.0 + TAPER))
C_TIP = C_ROOT * TAPER
MAC = (2.0 / 3.0) * C_ROOT * (1.0 + TAPER + TAPER ** 2) / (1.0 + TAPER)

# Half-chord sweep of the reference trapezoid, from LE sweep and taper.
SWEEP_C2 = math.degrees(math.atan(
    math.tan(math.radians(SWEEP_LE)) - (2.0 / AR) * (1.0 - TAPER) / (1.0 + TAPER)))

# The LERX vortex is what fades as its own leading edge goes sonic — at 73.5 deg that is far
# later than the bis's 57-deg wing, which is exactly why this aircraft keeps its high-alpha
# behaviour deeper into the transonic than the Fishbed does.
M_LE_SONIC = 1.0 / math.cos(math.radians(SWEEP_LERX))    # ~3.54, so the vortex never fully fades
# ...but the OUTER PANEL's own leading edge goes sonic much earlier, and that is what kills the
# usable high-alpha lift in practice. Fade the vortex term between the two.
M_PANEL_SONIC = 1.0 / math.cos(math.radians(SWEEP_LE))   # ~1.35

MASS_CLOSURE = M_EMPTY + M_FUEL + M_PILOT + M_GUN_AMMO + 2.0 * M_R73
CLOSURE_ERR = (MASS_CLOSURE - M_NORMAL) / M_NORMAL


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
    """Polhamus vortex-lift constant, faded as the OUTER PANEL leading edge approaches sonic.

    The LERX itself stays subsonic-edged to M3.5 and keeps shedding, but once the outer panel's
    leading edge is supersonic the vortex has no attached-flow wing left to augment, so the usable
    increment decays. Faded to a floor rather than to zero for that reason.
    """
    if mach <= 1.0:
        return KV0
    if mach >= M_PANEL_SONIC:
        return KV0 * 0.25
    frac = (M_PANEL_SONIC - mach) / (M_PANEL_SONIC - 1.0)
    return KV0 * (0.25 + 0.75 * frac)


def cl_polhamus(alpha_deg, mach):
    a = math.radians(alpha_deg)
    kp = cl_alpha(AR, SWEEP_C2, mach)
    return CL0 + kp * math.sin(a) * math.cos(a) ** 2 + kv(mach) * math.cos(a) * math.sin(a) ** 2


K_INDUCED = 1.0 / (math.pi * AR * OSWALD)

# ─── Lift table ─────────────────────────────────────────────────────────────────
# Each Mach column rises to a single peak AT the declared stall angle, then drops:
# validate-flight-model requires the table peak within 2 deg of alpha_stall_deg, because the
# engine does not clamp CL — the table IS the stall.
ALPHAS = [-4.0, 0.0, 4.0, 8.0, 12.0, 16.0, 20.0, 25.0, ALPHA_STALL, 34.0]
MACHS = [0.30, 0.60, 0.90, 1.20, 1.60, 2.25]

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

# Landing-speed closure check (printed, not gated). No MiG-29 landing speed is published, so
# unlike the bis this is a plausibility print only: a fighter at landing weight should stall
# somewhere in the 210-250 km/h band.
M_LANDING = M_EMPTY + 600.0 + M_PILOT       # [E] empty + reserve fuel + pilot
CL_MAX_LAND = cl_polhamus(ALPHA_STALL, 0.30)
V_STALL = math.sqrt(2.0 * M_LANDING * 9.80665 / (1.225 * CL_MAX_LAND * S))

# ─── Inertias ───────────────────────────────────────────────────────────────────
IXX = M_NORMAL * (RGYR_X * B / 2.0) ** 2
IYY = M_NORMAL * (RGYR_Y * LENGTH / 2.0) ** 2
IZZ = M_NORMAL * (RGYR_Z * (B + LENGTH) / 4.0) ** 2

# ─── Moment derivatives (DATCOM / strip theory) ─────────────────────────────────
M_EVAL = 0.60
CLA_W = cl_alpha(AR, SWEEP_C2, M_EVAL)
AR_H = B_H * B_H / S_H
CLA_H = cl_alpha(AR_H, SWEEP_LE, M_EVAL)
CLA_V = cl_alpha(AR_V, 45.0, M_EVAL)        # fin LE sweep [E]

V_H = (S_H * L_H) / (S * MAC)
V_V = (S_V * L_V) / (S * B)

CM_ALPHA = CLA_W * (CG - AC) - ETA_H * V_H * CLA_H * (1.0 - DEPS)
CM_Q = -2.0 * ETA_H * V_H * CLA_H * (L_H / MAC)
CM_DE = -ETA_H * V_H * CLA_H * TAU_E
CN_BETA = ETA_V * V_V * CLA_V + CN_FUS
CN_R = -2.0 * ETA_V * V_V * CLA_V * (L_V / B)
CN_DR = -ETA_V * V_V * CLA_V * TAU_R
# Twin CANTED fins: the outward cant means each fin's side force has a rolling component, and the
# high-mounted fins sit well above the CG — both feed cl_beta on top of the wing sweep term.
CL_BETA = -(CLA_W / 6.0) * math.radians(SWEEP_LE) \
    - ETA_V * (S_V * Z_V) / (S * B) * CLA_V
CL_P = -(CLA_W / 10.0)                       # moderate AR, taper 0.25
CL_DA = 0.40 * CLA_W / 6.0                   # aileron effectiveness tau = 0.40 [E]

# ─── Thrust decks ───────────────────────────────────────────────────────────────
# T(M, h) = T_sl_static * sigma^0.85 * f(M),  f(M) = 1 - 0.20*M + 0.45*M^2
# Low-bypass turbofan ram form (RD-33 BPR 0.49 — barely a bypass at all, so the turbojet-ish
# form the bis uses is the right one). Quadratic growth is KEPT to the inlet's design point
# because these are VARIABLE-RAMP inlets built for M2.25; it decays past it.
THRUST_MACHS = [0.00, 0.60, 0.90, 1.30, 1.80, 2.25]
THRUST_ALTS_KM = [0.0, 5.0, 11.0, 15.0, 18.0, 21.0]  # 11 km = max-speed anchor; 18 = published
                                                     # ceiling; 21 so the ceiling row is INTERPOLATED,
                                                     # never extrapolated off the top of the table
RAM_KNEE = 2.30     #       inlet design point; recovery decays past it            [E]
RAM_DECAY = 0.60    # /Mach                                                        [E]
RHO0 = 1.225

T_MIL = T_MIL_1 * N_ENG
T_AB = T_AB_1 * N_ENG


def isa_density(alt_m):
    if alt_m <= 11000.0:
        t = 288.15 - 0.0065 * alt_m
        return RHO0 * (t / 288.15) ** 4.256
    rho11 = RHO0 * (216.65 / 288.15) ** 4.256
    return rho11 * math.exp(-9.80665 * (alt_m - 11000.0) / (287.05 * 216.65))


def ram(mach):
    def base(m):
        return 1.0 - 0.20 * m + 0.45 * m * m
    if mach <= RAM_KNEE:
        return base(mach)
    return base(RAM_KNEE) * max(0.0, 1.0 - RAM_DECAY * (mach - RAM_KNEE))


def lapse(alt_m):
    """Density lapse, with a STEEPER exponent above the tropopause.

    ⚑ This is not a refinement, it is a correctness fix, and the symptom was unmistakable: with a
    single sigma^0.85 everywhere, thrust lapses SLOWER than drag (which goes as sigma^1.0), so
    excess thrust grows without bound with altitude. The model's AB climb rate went UP from 42 m/s
    at 18 km to 140 m/s at 21 km — an aircraft with no ceiling at all, and a published 18,000 m
    one. The MiG-21bis's deck uses a flat 0.85 and gets away with it only because its T/W is 0.81
    where this aircraft's is 1.11.

    The 0.85 exponent is an empirical fit that folds in the TEMPERATURE lapse of the troposphere.
    Above the tropopause the atmosphere is isothermal, that correction has nothing left to
    describe, and thrust falls essentially linearly with density. Matching the two laws AT 11 km
    costs nothing here: 11,000 m is exactly where the max-speed anchor is flown, so the anchor
    calibration is untouched by this change.
    """
    sigma = isa_density(alt_m) / RHO0
    if alt_m <= 11000.0:
        return sigma ** 0.85
    sigma11 = isa_density(11000.0) / RHO0
    return (sigma11 ** 0.85) * (sigma / sigma11)


def thrust_table(static_kn):
    return [[static_kn * lapse(a * 1000.0) * ram(m)
             for a in THRUST_ALTS_KM] for m in THRUST_MACHS]


MIL_TABLE = thrust_table(T_MIL)
AB_TABLE = thrust_table(T_AB)

# Fuel flows [E] from class SFC at the static ratings. lb/(lbf*h) -> kg/(s*kN): x 2.83254e-5.
SFC_CONV = 0.45359237 / 4.44822162 / 3600.0 * 1000.0
FF_IDLE = SFC_MIL * SFC_CONV * SFC_IDLE_KN
FF_MIL = SFC_MIL * SFC_CONV * T_MIL
FF_AB = SFC_AB * SFC_CONV * T_AB

# ⚑ RANGE CROSS-CHECK — DELIBERATELY NOT DONE HERE, because the obvious version of it LIES.
# The natural check (cruise drag x SFC -> specific range) assumes fuel flow is proportional to
# thrust. The engine's fuel model does not work that way: it interpolates from an IDLE FLOOR up to
# the military flow, so at a cruise setting of ~35% thrust the real burn is far above SFC x thrust.
# Written the naive way this check reported 909 m/kg against a published 409 — a 2.2x error that
# looks like a modelling problem and is actually an instrument problem.
#
# The honest instrument is fm-trim, which flies the shipped fuel deck:
#     fm-trim aircraft/mig29a/mig29a.toml --alt 11000 --mass 13000   ->  specific range
# It reports 305 m/kg against the 409 m/kg implied by the published 1,430 km on 3,500 kg internal.
# The model is therefore ~25% THIRSTIER than the published figure, in the direction that does not
# flatter the aircraft, and the published figure's profile, altitude and reserves are all unstated.
# Range is NOT gated in mig29a.expect.toml for exactly that reason. See [[global-measurement-harness-integrity]]:
# guard a measurement tool's failure modes IN the tool.

def fmt(vals, w=7, p=4):
    return ", ".join(f"{v:{w}.{p}f}" for v in vals)


if __name__ == "__main__":
    print(f"""# ── DERIVED — regenerate with `python3 aircraft/mig29a/derive.py`, do not hand-edit ──
# Geometry: AR {AR:.3f}, MAC {MAC:.3f} m (c_root {C_ROOT:.3f}, c_tip {C_TIP:.3f}, taper {TAPER} [E])
#           half-chord sweep {SWEEP_C2:.1f} deg; outer panel LE sonic at M{M_PANEL_SONIC:.2f},
#           LERX LE sonic at M{M_LE_SONIC:.2f} (i.e. never, in this envelope)
# Lift:     CL_alpha potential (M{M_EVAL}) {CLA_W:.3f} /rad; Polhamus peak CL {CL_MAX_LAND:.3f} at {ALPHA_STALL:.0f} deg
#           k = 1/(pi*AR*e) = {K_INDUCED:.4f} with e = {OSWALD} [E] — 58% of the bis's 0.2601
# Stability: cm_alpha {CM_ALPHA:+.4f} /rad (statically stable, as a no-FBW aircraft must be)
# Mass closure: {M_EMPTY:.0f} empty + {M_FUEL:.0f} fuel + {M_PILOT:.0f} pilot + {M_GUN_AMMO:.0f} ammo
#           + 2x{M_R73:.0f} R-73E = {MASS_CLOSURE:.0f} kg vs published normal TO {M_NORMAL:.0f} kg
#           ({CLOSURE_ERR * 100:+.1f}%)
# Stall check: Vs(1g, {M_LANDING:.0f} kg) = {V_STALL * 3.6:.0f} km/h [E, no published landing speed]

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
speedbrake_cd = 0.0280
gear_cd       = 0.0220

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

# fuel flows [E] from class SFC: idle {FF_IDLE:.3f}  mil {FF_MIL:.3f}  ab {FF_AB:.3f} kg/s
""")
