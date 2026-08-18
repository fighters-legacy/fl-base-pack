# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Forward fuel depot — three storage tanks, a pump house, a pad, and the pipework between them.

⚑ THE ONLY MESH IN THIS PACK WITH NOTHING TO CITE, AND THAT IS THE HONEST POSITION. Every other
model here — every aircraft, both air-defence vehicles, the truck — is a specific piece of
equipment with published dimensions in a SOURCES.md. A field fuel depot has no type designation,
no manufacturer and no specification: it is whatever tankage the engineers put up. So its
dimensions are stated as design intent rather than dressed up as research, and its SOURCES.md says
exactly that.

The design intent, since that is what a reviewer can actually check:

  * READ FROM 15,000 FT. It is a target in a strike mission. Three light cylinders on a dark pad
    are recognisable from altitude and from any heading, which a cluster of huts would not be.
  * NO COVER, BY CONSTRUCTION. Fuel is stored in the open with space between tanks so that one
    fire does not take the site. That is real practice AND it is what makes the target honest —
    the difficulty of this mission is the SA-6 and the Shilka, not finding the thing.
  * NOTHING THAT LOOKS DEFENDED. No revetments, no gun pits. What defends this site is parked
    beside it as separate entities, so a mission author can choose to leave it undefended.

Axes: nose +X (the pad's long axis), up +Z, starboard -Y. Origin at ground level.
"""

from fl_meshlib import prims

from . import common

TANK_RADIUS = 4.5   # [E] a ~500 m3 field storage tank
TANK_HEIGHT = 7.0   # [E]
TANK_SPACING = 12.5 # [E] roughly two diameters between shells — fire separation
PAD = (26.0, 38.0)  # [E] the concrete apron everything sits on. The tank line runs along
                    #     Y, so the pad is LONG in Y — the first cut had it the other way
                    #     round and the outer two tanks stood half off their own pad.


def build(bm):
    # The pad: a thin slab, and the reason the site reads as ONE object from the air rather than
    # three unrelated cylinders.
    prims.box(bm, (0.0, 0.0, 0.12), (PAD[0], PAD[1], 0.24))

    tank_z = 0.24 + TANK_HEIGHT * 0.5
    for i in (-1, 0, 1):
        y = i * TANK_SPACING
        prims.cylinder(bm, (2.0, y, tank_z), TANK_RADIUS, TANK_HEIGHT, axis="z", segments=20)
        # A shallow domed top, drawn as a short cone: flat-topped cylinders read as oil drums.
        prims.cylinder(bm, (2.0, y, 0.24 + TANK_HEIGHT + 0.45), TANK_RADIUS, 0.90, axis="z",
                       segments=20, radius_b=TANK_RADIUS * 0.45)

    # Pump house and manifold, at the near end where a road would come in.
    prims.box(bm, (-9.0, 0.0, 0.24 + 1.60), (7.0, 4.6, 3.20))
    prims.box(bm, (-9.0, 0.0, 0.24 + 3.35), (7.6, 5.2, 0.30))   # a flat roof slab with an overhang

    # Pipework: one run along the tank line at manifold height, plus a stub to each tank. Cheap
    # geometry that does more for "this is a fuel site" than any amount of tank detail.
    prims.cylinder(bm, (-4.5, 0.0, 1.30), 0.28, 2.0 * TANK_SPACING + 3.0, axis="y", segments=8)
    for i in (-1, 0, 1):
        prims.cylinder(bm, (-2.0, i * TANK_SPACING, 1.30), 0.22, 5.0, axis="x", segments=8)


def run_cli():
    common.run("fuel_depot", build, colour=common.SAND, damage_seed=19)
