#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the B-1B Lancer mesh set from published dimensions.

    blender --background --python aircraft/b1b/b1b_build.py -- --out aircraft/b1b

Emits, per docs/modding/3d-models.md:
    b1b.glb          base mesh; root node `b1b`, damage node `b1b_b`, swing-wing nodes
    b1b_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    b1b_shadow.glb   convex hull, no materials
    b1b_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
This file is DATA ONLY. The geometry ALGORITHM lives in fl_aircraftlib.b1 — a sibling of the N-156
family builder, not a derivative of it: a blended wing-body with swing wings shares no geometry with
a slender fighter fuselage.

═══════════════════════════════════════════════════════════════════════════════════════════════════
PROVENANCE — read this before changing a single number.
═══════════════════════════════════════════════════════════════════════════════════════════════════
Nothing here is traced from, derived from, or "cleaned up" out of another simulator, game, or
commercial 3D model, and nothing is traced from a scale plan or a cutaway — see
docs/legal/aircraft-likeness.md and SOURCES.md alongside this file.

⚠ THE B-1's PLANFORM DOES NOT CLOSE FROM PUBLIC DATA, and that is the honest difference between this
aircraft and the F-5E. NASA's spin-tunnel report publishes the complete F-5E trapezoid — root chord,
tip chord and span reconcile with the published wing area to 0.04%. For the B-1 the public record
gives overall length, height, both spans, the sweep range and a reference wing area, and NOTHING
else: no root or tip chord, no taper, no tail areas, no pivot location. Every chord below is
therefore [E], shaped against the public-domain photographs in ~/src/fighters-legacy/b1-reference/
(planform, front, sweep-spread and sweep-swept buckets) to the published overall dimensions.

WHAT IS NOT AN ESTIMATE: the outer panel's length and the angle its span axis makes at minimum
sweep are DERIVED, not chosen — `fl_aircraftlib.b1._wing_solve` solves them from the two published
spans and the pivot, and they reproduce 41.758 m spread and 24.079 m swept exactly. The naive model
(a panel perpendicular to the fuselage, rotating through the full 52.5 deg) is arithmetically
impossible for this aircraft: it demands a pivot 1.7 m behind the centreline.

NO MARKINGS. Policy §4: no unit insignia, squadron badges, nose art or operator liveries — and the
reference photographs are full of all four. Bare grey, applied via external .ktx2 textures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "aircraftlib" / "src"))

from fl_aircraftlib.b1 import B1Config, run_cli  # noqa: E402

# Published dimensions — SOURCES.md. [P] unless noted.
B1B = B1Config(
    ident="b1b",
    length=44.501,        # [P] 146 ft
    span_spread=41.758,   # [P] 137 ft, wings forward
    span_swept=24.079,    # [P] 79 ft, wings aft
    height=10.363,        # [P] 34 ft
    sweep_min=15.0,       # [P]
    sweep_max=67.5,       # [P]
)

if __name__ == "__main__":
    run_cli(B1B)
