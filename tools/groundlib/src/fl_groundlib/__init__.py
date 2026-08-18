# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""fl_groundlib — parametric builders for the pack's GROUND units.

The third tier of the pack's mesh toolchain, and the newest (fl-base-pack#17):

    fl_meshlib      generic procedural primitives — loft, prims, damage, export. Any shape.
    fl_aircraftlib  airframe FAMILY builders — one geometry algorithm per real airframe family,
                    shared across its variants (the MiG-21, the MiG-29, the N-156).
    fl_groundlib    ground units — one module per vehicle.

⚑ WHY THIS IS NOT `fl_aircraftlib`, AND WHY IT IS NOT ONE MODULE PER *FAMILY*. Aircraft come in
families because the pack ships variants of them: the MiG-29A and the MiG-29S are one builder and
two configs. A SAM launcher, an anti-aircraft gun, a fuel depot and a truck share no geometry
algorithm at all — they share PRIMITIVES, which is what fl_meshlib is for. So the unit here is the
vehicle, not the family, and the shared code in `common` is the BUILD RUN (damage variant, shadow
hull, export), not the shape.

⚠ THE MESHES STILL LAND IN `aircraft/`. The engine resolves every Mesh asset under `aircraft/`
whatever its category (engine `AssetPaths.cpp:12` — one directory per asset TYPE, and Mesh is one
type). A ground vehicle's glb therefore lives at `aircraft/<id>/<id>.glb` next to the jets. That
reads oddly and it is not a pack choice; do not "tidy" it into a new directory the engine will not
look in.

No submodule is imported here: they import `bpy`, and importing this package must stay cheap and
Blender-free for any tool that only wants the package marker.
"""
