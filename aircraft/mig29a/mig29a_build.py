#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the MiG-29A Fulcrum-A mesh set from published dimensions.

    blender --background --python aircraft/mig29a/mig29a_build.py -- --out aircraft/mig29a

Emits, per docs/modding/3d-models.md:
    mig29a.glb          base mesh; root node `mig29a`, damage node `mig29a_b`
    mig29a_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    mig29a_shadow.glb   convex hull, no materials
    mig29a_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
This file is DATA ONLY. The geometry ALGORITHM lives in fl_aircraftlib.mig29 — the MiG-29 FAMILY
builder, per the one-family-one-builder rule the T-38A established (fl-base-pack#20).
**fl-base-pack#45 (MiG-29S) reuses this mesh VERBATIM** — it is a data-only variant, so it forks
the flight model, entity, sensors and weapons, and never this builder.

═══════════════════════════════════════════════════════════════════════════════════════════════════
PROVENANCE — read this before changing a single number.
═══════════════════════════════════════════════════════════════════════════════════════════════════
Nothing here is traced from, derived from, or "cleaned up" out of another simulator, game, or
commercial 3D model, and nothing is traced from a scale plan, 3-view or cutaway — see
docs/legal/aircraft-likeness.md and SOURCES.md alongside this file.

WHAT CLOSES FROM PUBLISHED DATA, AND WHAT DOES NOT
--------------------------------------------------
Published [P]: overall length, span, height, wing reference area, the outer-panel leading-edge
sweep (42 deg) and the LERX sweep (73 deg 30 min). The wing root and tip chords CLOSE from the
published area and span at the [E] taper ratio of 0.25 — and that taper is deliberately the SAME
number derive.py assumes for its MAC, so the mesh and the flight model describe one wing rather
than two similar ones. Changing it in one place without the other is a real defect.

Everything else — body station shapes, nacelle spacing and profile, empennage chords and arms,
canopy and spine — is [E]. That is a WEAKER footing than the MiG-21bis's mesh had: the bis's
geometry was shaped against an 84-item PD reference set and its wing/empennage AREAS were
published outright. See the reference-set note below.

⚠ THE REFERENCE SET IS THIN, AND THAT IS A KNOWN LIMITATION
------------------------------------------------------------
`~/src/fighters-legacy/mig29-reference/` holds only **five** usable PD/CC0 photographs, against 84
for the MiG-21bis and 31 for the B-1B. The harvest is recorded in that directory's MANIFEST.md
along with everything it rejected and why.

⚑ The harvest also produced a lesson worth carrying: **magic-byte validation is necessary but not
sufficient.** The B-1B lane learned to validate magic bytes because Commons returns an HTML error
page with a .jpg name when rate-limited. This harvest returned five perfectly valid JPEGs that
were MiG-15s and an F-16 — the search matched "Mikoyan-Gurevich" and "cockpit". A file can be a
valid image of the wrong aircraft, and no byte-level check catches that. They were rejected by
inspection, not by the harvester.

NO MARKINGS. Policy §4: no unit insignia, squadron badges, or operator liveries — and the
reference photographs are full of all three. Bare grey, applied via external .ktx2 textures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "aircraftlib" / "src"))

from fl_aircraftlib.mig29 import Mig29Config, run_cli  # noqa: E402

# Published dimensions — SOURCES.md. [P] unless noted in the config's own field docs.
MIG29A = Mig29Config(
    ident="mig29a",
    length=17.32,        # [P] RAC MiG, excluding the pitot boom
    span=11.36,          # [P] RAC MiG
    wing_area=38.0,      # [P] Wikipedia spec block
    height=4.73,         # [P] RAC MiG
    sweep_le=42.0,       # [P] Jane's (planform ANGLE only — see SOURCES.md on the K's block)
    sweep_lerx=73.5,     # [P] Jane's, 73 deg 30 min
    wing_taper=0.25,     # [E] — MUST match derive.py's TAPER; one wing, two consumers
)

if __name__ == "__main__":
    run_cli(MIG29A)
