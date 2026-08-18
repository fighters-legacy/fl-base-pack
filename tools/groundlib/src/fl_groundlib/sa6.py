# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""2K12 Kub (SA-6) battery element — the 2P25 TEL silhouette with three rounds up.

PROVENANCE: dimensions are published (KUB-WIKI, in aircraft/sa6_battery/SOURCES.md). What is NOT
published is the panel-by-panel shape of the chassis, and this builder does not pretend otherwise:
it is the correct SIZE, the correct PROPORTIONS and the correct RECOGNISABLE ARRANGEMENT — a low
tracked hull with a turntable carrying three elevated rails — built from boxes and cylinders. It
is not traced from a scale plan, a 3-view, or any commercial model (docs/legal/aircraft-likeness.md
applies to ground units too; see SOURCES.md).

WHAT IS DRAWN vs WHAT THE ENTITY IS: entities/sa6_battery.toml is a battery ELEMENT — one entity
carrying both the 1S91's sensing and the 2P25's three rounds, because the engine gives ground units
no datalink (see that file's header). The mesh draws the launcher, because that is the silhouette
the system is known by. The radar vehicle is understood to be parked out of frame.

Axes: nose +X, up +Z, starboard -Y. Origin at the ground contact point, so `start: ground` sets it
down on its tracks.
"""

import math

from fl_meshlib import prims

from . import common

# ⚠ THE MISSILE IS PUBLISHED TO THE MILLIMETRE; THE VEHICLE UNDER IT IS NOT. KUB-WIKI gives the
# 3M9's dimensions and mass outright, and gives the 2P25 only its load (3 missiles), its crew (3)
# and its all-up weight (19.5 t). So the hull below is an ESTIMATE sized to carry three 5.8 m
# rounds at that weight class — which is the honest position, and is why the missiles are the part
# of this model worth checking against a photograph.
LENGTH = 7.39      # [E] 2P25 TEL hull length, m — sized from the published missile and weight
WIDTH = 3.18       # [E]
MISSILE_LEN = 5.80 # [P] 3M9 length, 5,800 mm (KUB-WIKI)
MISSILE_DIA = 0.335 # [P] 3M9 diameter, 335 mm
MISSILE_SPAN = 1.245 # [P] 3M9 wingspan, 1.245 m
ELEV_DEG = 15.0    # [E] the travelling/ready elevation the launcher sits at. Not a firing
                   #     solution — the engine's SAM controller does not slew the launcher at all
                   #     (engine #969/#971), so this is a fixed, plausible pose.


def _fin(bm, x_c, y, z, chord, root_r, span, arm_deg, thickness=0.05):
    """One thin fin panel on a missile body, laid on the arm at `arm_deg` about the missile axis.

    Built as a plate standing straight up from the body and then ROTATED onto its arm, because a
    box primitive can only be axis-aligned. The first cut of this file skipped the rotation and
    sized an axis-aligned box to span the diagonal instead — which produced four 0.5 m cubes per
    station, and the render showed a missile wearing crates. Fins are 5 cm thick; say so in the
    geometry rather than in a comment.
    """
    mid = root_r + span * 0.5
    verts = prims.box(bm, (x_c, y, z + mid), (chord, thickness, span))
    prims.rotate(bm, verts, math.radians(arm_deg - 90.0), axis=(1.0, 0.0, 0.0), pivot=(x_c, y, z))
    return verts


def _missile(bm, x_aft, y, z, elev_deg):
    """One 3M9 on its rail: body, nose cone, four wings, four tail fins, then elevated as a unit."""
    verts = []
    r = MISSILE_DIA * 0.5
    body_len = MISSILE_LEN * 0.82
    nose_len = MISSILE_LEN - body_len
    x_mid = x_aft + body_len * 0.5

    verts += prims.cylinder(bm, (x_mid, y, z), r, body_len, axis="x", segments=10)
    # Nose: a truncated cone, not a point — a 3M9 has a blunt radome, and a true point would be a
    # degenerate ring the bridge quietly drops.
    verts += prims.cylinder(bm, (x_aft + body_len + nose_len * 0.5, y, z), r, nose_len,
                            axis="x", segments=10, radius_b=r * 0.30)

    wing_span = (MISSILE_SPAN - MISSILE_DIA) * 0.5   # [D] from the published 1.245 m span
    for i in range(4):                               # cruciform, 45 degrees off vertical
        arm = 45.0 + 90.0 * i
        verts += _fin(bm, x_aft + body_len * 0.58, y, z, 1.25, r, wing_span, arm)
        verts += _fin(bm, x_aft + 0.30, y, z, 0.60, r, wing_span * 0.66, arm)

    prims.rotate(bm, verts, -math.radians(elev_deg), axis=(0.0, 1.0, 0.0), pivot=(x_aft, y, z))
    return verts


def build(bm):
    deck = common.tracked_hull(bm, LENGTH, WIDTH, height=1.05, z_ground=0.0,
                               track_width=0.52, track_height=0.66)

    # Cab forward, turntable aft — the arrangement that makes the vehicle readable from the air.
    prims.box(bm, (2.30, 0.0, deck + 0.55), (2.10, 2.20, 1.10))
    turntable = deck + 0.22
    prims.cylinder(bm, (-0.90, 0.0, turntable), 1.20, 0.44, axis="z", segments=14)

    # The launcher beam the rails ride on. Without it the missiles float above the hull with a
    # visible gap and the vehicle stops reading as a launcher — which is exactly what the first
    # render showed.
    beam_z = turntable + 0.34
    prims.box(bm, (-1.30, 0.0, beam_z), (3.40, 2.40, 0.34))
    for y in (0.0, 1.05, -1.05):
        prims.box(bm, (-1.30, y, beam_z + 0.30), (3.20, 0.34, 0.28))   # the rail itself

    # Three rounds: the centre rail sits higher on the trunnion, which is how a 2P25 carries them
    # and why the vehicle reads as a triangle head-on rather than a flat row.
    rail_z = beam_z + 0.62
    _missile(bm, -3.20, 0.00, rail_z + 0.40, ELEV_DEG)
    _missile(bm, -3.20, 1.05, rail_z, ELEV_DEG)
    _missile(bm, -3.20, -1.05, rail_z, ELEV_DEG)


def run_cli():
    common.run("sa6_battery", build, colour=common.OLIVE, damage_seed=11)
