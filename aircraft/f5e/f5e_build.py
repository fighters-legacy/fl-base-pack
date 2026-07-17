#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the F-5E Tiger II mesh set from published dimensions.

    blender --background --python aircraft/f5e/f5e_build.py -- --out aircraft/f5e

Emits, per docs/modding/3d-models.md:
    f5e.glb          base mesh; root node `f5e`, damage-state node `f5e_b`
    f5e_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    f5e_shadow.glb   convex hull, no materials
    f5e_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
This file is DATA ONLY. The geometry ALGORITHM lives in fl_aircraftlib.n156 (the shared Northrop
N-156 airframe-family builder); the F-5E is the same airframe family as the T-38A (see
aircraft/t38a/t38a_build.py), so they share one authored loft and differ only in the config below.
The shared module was extracted from this script's original monolithic form and produces
byte-identical output.

═══════════════════════════════════════════════════════════════════════════════════════════════════
PROVENANCE — read this before changing a single number.
═══════════════════════════════════════════════════════════════════════════════════════════════════
This airframe is generated ENTIRELY FROM PUBLISHED DIMENSIONS. Nothing here is traced from, derived
from, or "cleaned up" out of another simulator, game, or commercial 3D model. See
docs/legal/aircraft-likeness.md in the engine repo, and SOURCES.md alongside this file.

That is possible because NASA's spin-tunnel report (NTRS 19980227417, Table I) publishes the complete
planform, and it CLOSES: root chord 3.5735 m, tip chord 0.6840 m and span 8.13 m give a trapezoid of
17.307 m^2 against the published wing area of 17.30 m^2 — 0.04%. The wing is a simple trapezoid and
every dimension of it is in the public record. Same for both tails.

Where a dimension is genuinely NOT published (fuselage cross-section, canopy shape, intake geometry),
it is marked [E] and shaped to the published length, height and the known fuselage width at the tail.
Those are the only judgement calls in this file, and they are visual only — nothing the flight model
consumes comes from here.

NO MARKINGS. Policy §4: no unit insignia, squadron badges, nose art or operator liveries. Bare metal
with a generic aggressor-grey scheme, applied via external .ktx2 textures, never baked geometry.

The FUSELAGE STATIONS below were traced from NASA Figure 1 (the published 3-view): a column scan of
the page ink, scale anchored to the printed 73.15 cm overall length and cross-checked against the
printed 12.88 cm fin height and the printed MAC bar (12.27 cm = 2.454 m vs the published 2.456).
Method and verification overlays: the f5e_trace work recorded in SOURCES.md. Each station is
(x/L, z_upper, z_lower, y_half), metres full scale, z from the fuselage reference line.
"""

import sys
from pathlib import Path

# The shared N-156 builder and the generic mesh library both live in the repo, not on Blender's
# Python path; add them from this file's location (aircraft/f5e/ -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "aircraftlib" / "src"))
from fl_aircraftlib.n156 import N156Config, fighter_hardpoint_markers, run_cli  # noqa: E402

# ═══ THE F-5E TIGER II — published dimensions. [P] published, [D] derived, [E] estimate. ═══════════
# Geometry: NASA spin-tunnel report (NTRS 19980227417), Table I, unless tagged otherwise.
F5E = N156Config(
    aircraft_id="f5e",
    mat_skin="f5e_skin",                     # liverable slot name (fighters-legacy#845)
    tex_diffuse="../../textures/f5e_diffuse.ktx2",
    tex_orm="../../textures/f5e_orm.ktx2",

    length=14.68,                            # [P] m overall
    span=8.13,                               # [P] m wing span, without tip missiles
    wing_area=17.30,                         # [P] m^2 (the trapezoid reproduces this to 0.04%)

    root_chord=3.5735,                       # [P] m
    tip_chord=0.6840,                        # [P] m
    sweep_c4=24.0,                           # [P] deg quarter-chord sweep
    thickness=0.048,                         # [P] NACA 65A004.8 — symmetric, 4.8% thick
    wing_x_le=5.95,                          # m wing leading-edge root station
    wing_z=-0.12,                            # m low-mid wing

    ht_span=4.30,                            # [P] m horizontal tail, tip to tip
    ht_tip_chord=0.508,                      # [P] m
    ht_taper=0.33,                           # [P]
    ht_sweep_c4=25.0,                        # [P] deg
    ht_dihedral=-4.0,                        # [P] deg ANHEDRAL. The F-5's tailplane droops.
    ht_x_c4=13.10,                           # m horizontal tail quarter-chord station
    ht_z0=0.10,

    vt_tip_chord=0.7112,                     # [P] m vertical tail
    vt_taper=0.25,                           # [P]
    vt_sweep_c4=25.0,                        # [P] deg
    vt_area=3.85,                            # [P] m^2 exposed
    vt_ar=1.22,                              # [P] on the exposed span
    vt_x_c4=11.90,                           # m vertical tail quarter-chord station
    vt_z0=0.55,

    # Fuselage side-view trace. z_up [P] traced (CANOPY top inside the canopy span; interpolated [D]
    # under the fin x/L > 0.78 and at two dimension-line-polluted stations). z_lo [P] traced. y_half
    # nose [P] traced; mid/aft [D] from twin-J85 packaging and NASA's tail-span arithmetic (exposed
    # h-tail span 2.97 = 4.30 - 2*0.665, so fuselage half-width at the tailplane is 0.665).
    stations_fus=[
        # x/L    z_up    z_lo   y_half
        (0.000,  0.015, -0.015, 0.038),   # radome tip, on the reference line
        (0.030,  0.008, -0.307, 0.060),
        (0.060, -0.008, -0.369, 0.161),   # slight nose droop -- traced, it is real
        (0.100,  0.077, -0.438, 0.315),
        (0.140,  0.192, -0.499, 0.438),
        (0.190,  0.323, -0.553, 0.530),
        (0.240,  0.453, -0.584, 0.580),   # windshield base
        (0.290,  0.950, -0.561, 0.590),   # [D] canopy rise (dim-line polluted; interp of neighbours)
        (0.340,  1.020, -0.538, 0.590),   # [D] canopy peak (same)
        (0.400,  1.007, -0.523, 0.590),   # aft canopy fairing [P]
        (0.460,  0.937, -0.499, 0.645),   # intake fairing region, widest
        (0.520,  0.853, -0.469, 0.620),   # area-rule waist begins
        (0.580,  0.780, -0.553, 0.600),   # [D] (dimension-stem mask; interp)
        (0.640,  0.707, -0.561, 0.600),
        (0.700,  0.638, -0.561, 0.620),
        (0.760,  0.791, -0.553, 0.640),   # spine kick-up at the fin fillet
        (0.815,  0.700, -0.530, 0.665),   # [D] under the fin: spine interp; width = tail-span arith
        (0.860,  0.580, -0.499, 0.660),   # [D]
        (0.910,  0.460, -0.553, 0.630),   # [D]
        (0.960,  0.340, -0.400, 0.580),   # [D] boat-tail
        (1.000,  0.280, -0.200, 0.520),   # nozzle station
    ],
    nose_blend_t=0.16,                       # x/L [E] radome (circular) -> traced forebody
    sill_ease=2.2,                           # [E] cockpit-sill ease-in exponent
    fus_n0=2.05, fus_dn=0.4, fus_n_ramp=0.25,  # forebody superellipse ramp
    pitot_len=0.55,                          # [P] m visible on the 3-view
    nozzle_r=0.28,                           # [D] m from the front view; two, side by side

    canopy_span=(0.245, 0.435),              # x/L range where z_up is canopy glass, not spine
    canopy_halfw=0.34,                       # [E] m canopy width from the planform outline
    windscreen_f=0.14,                       # [E] fraction of the canopy span the windscreen occupies

    # Lateral air intakes [E] — shaped to the published outline, cross-checked against PD photography.
    intake_x0=0.415,                         # x/L cowl lip, just aft of the canopy, ahead of the wing
    intake_x1=0.660,                         # x/L where the fairing has faded into the flank
    intake_zc=0.28,                          # m aperture centre above the reference line
    intake_hz=0.33,                          # m aperture half-height
    intake_hy=0.20,                          # m cowl half-width; the inboard half stays buried
    intake_proud=0.13,                       # m how far the cowl lip stands proud of the flank
    intake_depth=0.26,                       # m how far the inlet face is recessed behind the lip

    tip_rails=True,
    tip_rail_len=2.10,                       # m wingtip AIM-9 rail (part of the airframe)

    hardpoint_markers=fighter_hardpoint_markers,   # gun + 2 wingtip + 4 pylon (F-5E is armed)
)


if __name__ == "__main__":
    run_cli(F5E)
