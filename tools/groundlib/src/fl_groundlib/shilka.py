# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""ZSU-23-4 Shilka — tracked hull, box turret, four barrels, and the dish that names it.

PROVENANCE: dimensions published (SHILKA-WIKI, in aircraft/zsu23_4/SOURCES.md). As with the SA-6,
the SIZE and ARRANGEMENT are sourced and the surface detail is [E] — boxes and cylinders, not a
traced outline. Nothing here comes from a game, a simulator or a commercial model.

The one shape worth getting right is the RADAR: "Gun Dish" is what NATO called the RPK-2 because
the dish is the vehicle's identifying feature from any angle, and a Shilka drawn without it is
just a small tank. It is drawn deployed (up), which is the pose that matches the entity — the
vehicle carries sensors/rpk2.toml and is emitting whenever it is looking.

Axes: nose +X, up +Z, starboard -Y. Origin at the ground contact point.
"""

import math

from fl_meshlib import prims

from . import common

LENGTH = 6.535     # [P] hull length, m (SHILKA-WIKI)
WIDTH = 3.125      # [P]
HEIGHT_RADAR = 3.572  # [P] over the elevated radar; 2.576 with it stowed. The mesh draws it
                      #     DEPLOYED, so this is the height to check a render against.
BARREL_LEN = 2.01  # [E] 2A7 barrel length — not published in the cited source; sized off the
                   #     published 23x152B calibre and the vehicle's published length
ELEV_DEG = 22.0    # [E] a plausible ready elevation. The gun does not slew in the engine
                   #     (engine #969/#971 — AaaFireController fires along the vehicle's fixed
                   #     nose), so this pose is cosmetic and the mission's `heading` is what
                   #     actually decides what the vehicle can hit. See entities/zsu23_4.toml.


def _barrels(bm, x0, y0, z0, elev_deg):
    """Four 23 mm barrels in a 2x2 cluster, elevated together with their cradle."""
    verts = []
    for (dy, dz) in ((0.17, 0.13), (-0.17, 0.13), (0.17, -0.13), (-0.17, -0.13)):
        verts += prims.cylinder(bm, (x0 + BARREL_LEN * 0.5, y0 + dy, z0 + dz),
                                0.055, BARREL_LEN, axis="x", segments=8)
    # The cradle the four sit in — without it they read as loose pipes.
    verts += prims.box(bm, (x0 - 0.35, y0, z0), (0.90, 0.70, 0.62))
    prims.rotate(bm, verts, -math.radians(elev_deg), axis=(0.0, 1.0, 0.0), pivot=(x0 - 0.35, y0, z0))
    return verts


def build(bm):
    deck = common.tracked_hull(bm, LENGTH, WIDTH, height=0.85, z_ground=0.0,
                               track_width=0.48, track_height=0.62)

    # Turret: a tapered box, narrower at the front, which is the Shilka's actual plan shape and the
    # cheapest way to stop it reading as a packing crate.
    turret_z = deck + 0.52
    prims.taper(bm, (-0.20, 0.0, turret_z), (2.05, 1.02), (2.55, 1.02), 2.90, axis="x")
    turret_top = turret_z + 0.51

    _barrels(bm, 1.35, 0.0, turret_z + 0.10, ELEV_DEG)

    # RPK-2 "Gun Dish": a short mast, a shallow dish FACING FORWARD, and the feed horn ahead of it.
    # ⚠ The first cut built the dish as a disc lying FLAT on top of a tall thin mast, with the feed
    # horn sticking up above it — a lollipop, not a radar. A parabolic tracking dish looks where
    # the gun looks, so it opens along +X, and the mast is short because the real one folds.
    mast_h = 0.55
    prims.cylinder(bm, (-1.30, 0.0, turret_top + mast_h * 0.5), 0.18, mast_h, axis="z", segments=8)
    dish_z = turret_top + mast_h + 0.62
    prims.cylinder(bm, (-1.30, 0.0, dish_z), 0.30, 0.55, axis="x", segments=16, radius_b=0.72)
    prims.cylinder(bm, (-0.85, 0.0, dish_z), 0.09, 0.55, axis="x", segments=8)   # feed horn


def run_cli():
    common.run("zsu23_4", build, colour=common.OLIVE, damage_seed=13)
