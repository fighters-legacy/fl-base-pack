# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""fl_aircraftlib — parametric airframe-FAMILY builders for fl-base-pack.

Where `fl_meshlib` holds GENERIC procedural-mesh primitives (loft, curves, damage, export)
usable by any airframe, `fl_aircraftlib` holds family-specific PARAMETRIC AIRFRAMES: one
authored geometry algorithm shared across the variants of a real airframe family, driven by a
per-aircraft config of published dimensions.

    n156 — the Northrop N-156 family (F-5A/B/E/F Freedom Fighter / Tiger II, T-38 Talon).

No submodule is imported here: the module imports `bpy`, and importing this package must stay
cheap and Blender-free for any tool that only wants the package marker.
"""
