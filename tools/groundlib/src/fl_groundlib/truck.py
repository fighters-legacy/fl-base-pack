# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Ural-375D 6x6 — cab, bonnet, canvas-tilt bed, six wheels. The pack's soft target.

PROVENANCE: dimensions published (URAL-WIKI, in aircraft/ural375/SOURCES.md); shape is [E] boxes
at the published proportions. Not traced from anything.

It is the simplest mesh in the pack, and it should be: it exists to be shot at from a diving
aircraft, and every triangle spent on a door handle is a triangle a mission with a dozen of them
pays for twelve times over.

Axes: nose +X, up +Z, starboard -Y. Origin at the ground contact point.
"""

from fl_meshlib import prims

from . import common

LENGTH = 7.35      # [P] 7,350 mm overall (URAL-WIKI)
WIDTH = 2.96       # [P] 2,960 mm
HEIGHT = 2.98      # [P] 2,980 mm with the tilt up — which is how this one is drawn
WHEEL_R = 0.61     # [D] from the published "360-510 mm" tyre size: a 510 mm rim (radius 0.255 m)
                   #     plus a ~360 mm section height


def build(bm):
    chassis_z = WHEEL_R + 0.18
    prims.box(bm, (0.0, 0.0, chassis_z), (LENGTH * 0.94, WIDTH * 0.62, 0.28))

    # Bonnet and cab forward: the 375's blunt nose and its square cab.
    prims.box(bm, (2.55, 0.0, chassis_z + 0.62), (1.55, WIDTH * 0.80, 0.96))
    prims.box(bm, (1.30, 0.0, chassis_z + 0.88), (1.35, WIDTH * 0.88, 1.48))

    # Bed with its canvas tilt — a taper, higher at the front, so it reads as fabric over hoops
    # rather than a second cab.
    prims.taper(bm, (-1.75, 0.0, chassis_z + 0.95), (WIDTH * 0.94, 1.62), (WIDTH * 0.94, 1.44),
                3.85, axis="x")

    # 6x6: one front axle, a rear bogie of two. Wheels are cylinders on Y — see common.road_wheels
    # on why they are deliberately coarse.
    for side in (1.0, -1.0):
        y = side * (WIDTH * 0.5 - 0.22)
        for x in (2.35, -0.95, -2.35):
            prims.cylinder(bm, (x, y, WHEEL_R), WHEEL_R, 0.42, axis="y", segments=10)


def run_cli():
    common.run("ural375", build, colour=common.OLIVE, damage_seed=17)
