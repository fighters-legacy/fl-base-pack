#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the 2K12 Kub (SA-6) battery element mesh set.

    blender --background --python aircraft/sa6_battery/sa6_battery_build.py -- --out aircraft/sa6_battery

Emits:
    sa6_battery.glb          base mesh; root node `sa6_battery`, damage node `sa6_battery_b`
    sa6_battery_shadow.glb   convex hull, no materials

No LOD files and no cockpit file — see fl_groundlib.common.run (a ground unit is already below an
aircraft's coarsest LOD budget) and note that nothing here is flyable, so there is no camera anchor
to place.

This file is DATA AND INVOCATION ONLY. The geometry lives in fl_groundlib.sa6, and its
provenance is recorded there and in SOURCES.md alongside this file.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "groundlib" / "src"))

from fl_groundlib.sa6 import run_cli  # noqa: E402

if __name__ == "__main__":
    run_cli()
