#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the MiG-21bis Fishbed mesh set from published dimensions.

    blender --background --python aircraft/mig21bis/mig21bis_build.py -- --out aircraft/mig21bis

Emits, per docs/modding/3d-models.md:
    mig21bis.glb          base mesh; root node `mig21bis`, damage node `mig21bis_b`
    mig21bis_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    mig21bis_shadow.glb   convex hull, no materials
    mig21bis_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
This file is DATA ONLY. The geometry ALGORITHM lives in fl_aircraftlib.mig21 — the MiG-21 FAMILY
builder, per the one-family-one-builder rule the T-38A established (fl-base-pack#20): the U/UM
two-seater (#42) and the earlier-generation fuselages are config knobs there, not future forks.

═══════════════════════════════════════════════════════════════════════════════════════════════════
PROVENANCE — read this before changing a single number.
═══════════════════════════════════════════════════════════════════════════════════════════════════
Nothing here is traced from, derived from, or "cleaned up" out of another simulator, game, or
commercial 3D model, and nothing is traced from a scale plan or a cutaway — see
docs/legal/aircraft-likeness.md and SOURCES.md alongside this file.

THE PLANFORM CLOSES FROM PUBLISHED DATA, like the F-5E's and unlike the B-1's. The declassified
F-13 manual publishes the wing area (23 m²), span (7.15 m), leading-edge sweep (57°), anhedral
(−2°) and the empennage areas outright; with a small [E] clipped tip chord the centreline root
chord follows from area and span, and the closure check is that the trailing edge comes out
STRAIGHT — which the builder prints at build time and the photographs confirm.

The fuselage length is **14.10 m excluding pitot** — the 14.7 m figure was rejected by
datum-consistency against the primary source (SOURCES.md, "RESOLVED: fuselage length").
Fuselage station shapes, the spine profile, the canopy dome and the intake-cone dimensions are
[E], shaped against the PD/CC0 photographs in ~/src/fighters-legacy/mig21-reference/ (front,
side, nose-radar and the three Finnish walk-around sets).

NO MARKINGS. Policy §4: no unit insignia, squadron badges, or operator liveries — and the
reference photographs are full of all three. Bare grey, applied via external .ktx2 textures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "aircraftlib" / "src"))

from fl_aircraftlib.mig21 import Mig21Config, run_cli  # noqa: E402

# Published dimensions — SOURCES.md. [P] unless noted in the config's own field docs.
MIG21BIS = Mig21Config(
    ident="mig21bis",
    length=14.10,        # [P] excluding pitot boom (datum-resolved; SOURCES.md)
    span=7.154,          # [P]
    wing_area=23.0,      # [P]
    sweep_le=57.0,       # [P]
    dihedral=-2.0,       # [P]
)

if __name__ == "__main__":
    run_cli(MIG21BIS)
