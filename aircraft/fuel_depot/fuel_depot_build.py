#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the forward fuel depot mesh set.

    blender --background --python aircraft/fuel_depot/fuel_depot_build.py -- --out aircraft/fuel_depot

Emits:
    fuel_depot.glb          base mesh; root node `fuel_depot`, damage node `fuel_depot_b`
    fuel_depot_shadow.glb   convex hull, no materials

No LOD files and no cockpit file — see fl_groundlib.common.run (a ground unit is already below an
aircraft's coarsest LOD budget) and note that nothing here is flyable, so there is no camera anchor
to place.

This file is DATA AND INVOCATION ONLY. The geometry lives in fl_groundlib.depot, and its
provenance is recorded there and in SOURCES.md alongside this file.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "groundlib" / "src"))

from fl_groundlib.depot import run_cli  # noqa: E402

if __name__ == "__main__":
    run_cli()
