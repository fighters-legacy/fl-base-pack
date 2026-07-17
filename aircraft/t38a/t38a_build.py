#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the T-38A Talon mesh set from published dimensions.

    blender --background --python aircraft/t38a/t38a_build.py -- --out aircraft/t38a

Emits, per docs/modding/3d-models.md:
    t38a.glb          base mesh; root node `t38a`, damage-state node `t38a_b`
    t38a_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    t38a_shadow.glb   convex hull, no materials
    t38a_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
This file is DATA ONLY. The geometry ALGORITHM lives in fl_aircraftlib.n156 — the shared Northrop
N-156 airframe-family builder, the SAME loft that produces the F-5E (aircraft/f5e/f5e_build.py). The
T-38 and the F-5 are one airframe family; this file supplies only the T-38's dimensions and its three
airframe deltas: a slimmer RADAR-LESS nose, a longer TWO-SEAT TANDEM canopy, and NO wingtip rails and
NO hardpoints (the trainer is unarmed).

═══════════════════════════════════════════════════════════════════════════════════════════════════
PROVENANCE — read this before changing a single number. See SOURCES.md alongside this file.
═══════════════════════════════════════════════════════════════════════════════════════════════════
[P] published   [D] derived from published values by a stated method   [E] estimate

The PLANFORM is fully published and closes: wing area 170 ft^2 (15.79 m^2), AR 3.75, taper 0.20,
quarter-chord sweep 24 deg, NACA 65A004.8 root-to-tip, MAC 92.76 in — all [P] from the AFFTC
Category II test report (DTIC AD0263411) and the AFIT geometry compilation (DTIC ADA496748, Table 15,
from Northrop CAD). Root chord 134.65 in (3.420 m) and tip chord 26.93 in (0.684 m) reproduce the
published area to within a per cent. Both tails are dimensioned in AD0263411.

The FUSELAGE CROSS-SECTION and the CANOPY are [E]. Unlike the F-5E — whose forebody was traced off
NASA's dimensioned spin-tunnel 3-view — NO dimensioned T-38 side view was obtained from a primary
source (the T.O. 1T-38A-1 General Arrangement shows the two-cockpit layout but carries no station
dimensions; see SOURCES.md, "forebody gap"). So the station table below is shaped BY HAND to the
published overall length (46 ft 4 in), height (12 ft 11 in), the known slender area-ruled "coke-bottle"
fuselage, and the two-seat tandem canopy — nothing here is traced from any drawing, photo, sim or
model. It is VISUAL ONLY: the flight model (t38a.toml) reads nothing from this file. This is the
T-38's single largest [E] and it is recorded as such rather than dressed up as a trace.

NO MARKINGS. Policy §4: no unit insignia or liveries. Generic clean grey via external .ktx2 textures.
(The real T-38 usually wears high-visibility white; the pack ships the grey airframe — see the entity
def's `visual` signature note.)

CONVENTIONS (axes, winding, naming): see fl_aircraftlib.n156's header.
"""

import sys
from pathlib import Path

# The shared N-156 builder and the generic mesh library both live in the repo, not on Blender's
# Python path; add them from this file's location (aircraft/t38a/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "aircraftlib" / "src"))
from fl_aircraftlib.n156 import N156Config, run_cli  # noqa: E402

# ═══ THE T-38A TALON — published dimensions. [P] published, [D] derived, [E] estimate. ════════════
T38A = N156Config(
    aircraft_id="t38a",
    mat_skin="t38a_skin",                    # liverable slot name (fighters-legacy#845)
    tex_diffuse="../../textures/t38a_diffuse.ktx2",
    tex_orm="../../textures/t38a_orm.ktx2",

    length=14.13,                            # [P] m (46 ft 4 in) — T.O. 1T-38A-1 / ADA496748
    span=7.70,                               # [P] m (25 ft 3 in) — AD0263411
    wing_area=15.79,                         # [P] m^2 (170.0 ft^2) — AD0263411 / ADA496748

    root_chord=3.420,                        # [P] m (134.65 in, theoretical CL) — ADA496748
    tip_chord=0.684,                         # [P] m (26.93 in) — ADA496748
    sweep_c4=24.0,                           # [P] deg quarter-chord sweep — ADA496748
    thickness=0.048,                         # [P] NACA 65A004.8 — symmetric, 4.8% thick
    wing_x_le=6.55,                          # [E] m root LE station (visual placement; longer T-38
                                             #     forebody sets the wing further aft than the F-5E's)
    wing_z=-0.14,                            # [E] m low-mid wing

    # Horizontal tail (all-moving stabilator): total 59.0 ft^2, exposed 33.34 ft^2, exposed AR 2.82,
    # exposed taper 0.33 — AD0263411. Exposed span sqrt(2.82*3.10)=2.96 m [D]; tip chord ~0.52 m and
    # tip-to-tip span ~3.80 m follow from the taper and the slim tail-cone width. Sweep NOT published.
    ht_span=3.80,                            # [D] m tip to tip
    ht_tip_chord=0.520,                      # [D] m
    ht_taper=0.33,                           # [P]
    ht_sweep_c4=25.0,                        # [E] deg (not published; F-5 family value)
    ht_dihedral=-4.0,                        # [E] deg slight anhedral, as on the F-5 family
    ht_x_c4=12.45,                           # [E] m stabilator quarter-chord station
    ht_z0=0.05,

    # Vertical tail: total 41.42 ft^2, exposed 41.07 ft^2, exposed AR 1.21, exposed taper 0.25 —
    # AD0263411. Height sqrt(1.21*3.82)=2.15 m; root=tip/0.25. Nearly identical to the F-5E's fin.
    vt_tip_chord=0.711,                      # [D] m
    vt_taper=0.25,                           # [P]
    vt_sweep_c4=25.0,                        # [E] deg (not published; F-5 family value)
    vt_area=3.82,                            # [P] m^2 exposed
    vt_ar=1.21,                              # [P] on the exposed span
    vt_x_c4=11.35,                           # [E] m fin quarter-chord station
    vt_z0=0.45,

    # Fuselage side-view stations — [E] throughout (no dimensioned T-38 3-view; see the header). A
    # slender area-ruled body: a long slim RADAR-LESS ogive nose, a two-seat TANDEM canopy, lateral
    # intakes at the wing root, a waisted mid-body and twin-nozzle boat-tail. Shaped to the published
    # 14.13 m length and 3.93 m height. (x/L, z_upper, z_lower, y_half) m, z from the reference line.
    stations_fus=[
        # x/L    z_up    z_lo   y_half
        (0.000,  0.020, -0.020, 0.028),   # sharp ogive tip (no radome)
        (0.030,  0.045, -0.110, 0.075),
        (0.060,  0.075, -0.175, 0.130),
        (0.100,  0.120, -0.240, 0.205),
        (0.140,  0.160, -0.295, 0.275),
        (0.190,  0.215, -0.340, 0.360),   # forward fuselage, ahead of the front cockpit
        (0.230,  0.300, -0.360, 0.410),   # front windshield base
        (0.270,  0.760, -0.360, 0.435),   # front cockpit canopy (glass)
        (0.320,  0.845, -0.355, 0.450),   # inter-cockpit / peak of the tandem canopy (glass)
        (0.380,  0.775, -0.350, 0.460),   # rear cockpit canopy (glass)
        (0.420,  0.545, -0.345, 0.485),   # aft canopy fairing / dorsal spine; intake lip begins
        (0.470,  0.500, -0.365, 0.520),   # intake fairing region, widest
        (0.520,  0.475, -0.385, 0.520),   # wing root; area-rule waist begins
        (0.580,  0.450, -0.400, 0.500),
        (0.640,  0.420, -0.400, 0.500),
        (0.700,  0.400, -0.380, 0.500),
        (0.760,  0.475, -0.360, 0.475),   # spine kick-up at the fin fillet
        (0.820,  0.420, -0.340, 0.455),
        (0.880,  0.350, -0.300, 0.420),
        (0.940,  0.280, -0.235, 0.355),   # boat-tail
        (1.000,  0.220, -0.140, 0.300),   # nozzle station
    ],
    nose_blend_t=0.14,                       # [E] x/L slim ogive -> body blend (sharper than F-5E)
    sill_ease=2.2,                           # [E] cockpit-sill ease-in exponent
    fus_n0=2.05, fus_dn=0.4, fus_n_ramp=0.25,  # forebody superellipse ramp (family value)
    pitot_len=0.50,                          # [E] m nose boom
    nozzle_r=0.25,                           # [E] m one J85-GE-5 nozzle (smaller than the F-5E's -21)

    canopy_span=(0.235, 0.420),              # [E] x/L — TANDEM: longer than the F-5E's single bubble
    canopy_halfw=0.32,                       # [E] m tandem canopy plan half-width
    windscreen_f=0.11,                       # [E] windscreen fraction (front of a long canopy)

    # Lateral air intakes [E] — small, at the wing root, ahead of the leading edge.
    intake_x0=0.415,                         # x/L cowl lip
    intake_x1=0.630,                         # x/L where the fairing has faded into the flank
    intake_zc=0.22,                          # m aperture centre above the reference line
    intake_hz=0.26,                          # m aperture half-height
    intake_hy=0.15,                          # m cowl half-width
    intake_proud=0.09,                       # m how far the cowl lip stands proud of the flank
    intake_depth=0.20,                       # m how far the inlet face is recessed behind the lip

    tip_rails=False,                         # the trainer has NO wingtip rails
    # hardpoint_markers left at None: the T-38A is UNARMED — no gun, no pylons, no markers.

    cockpit_span_frac=0.16,                  # [E] anchor near the FRONT cockpit of the tandem canopy
    cockpit_z_station=0.27,
    cockpit_z_drop=0.25,
)


if __name__ == "__main__":
    run_cli(T38A)
