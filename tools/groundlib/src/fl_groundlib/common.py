# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Shared build run and shared sub-assemblies for the pack's ground units. Requires Blender."""

import argparse
import sys
from pathlib import Path

import bmesh
import bpy

from fl_meshlib import damage, export, prims, scene, uvatlas

# Flat colours, and no texture URIs at all — which is a DEPARTURE from the aircraft builders and a
# deliberate one. Every aircraft here calls `export.patch_textures` to point at
# `textures/<ident>_diffuse.ktx2`; the pack ships no `textures/` directory, so those references
# resolve to nothing and the renderer falls back. Repeating that on four new meshes would be
# copying a wart. These units carry an honest base colour instead, and when a texture set exists
# they can be wired to it in the same change that adds it.
OLIVE = (0.20, 0.23, 0.15, 1.0)     # Soviet-era vehicle green
SAND = (0.62, 0.60, 0.50, 1.0)      # unpainted / weathered concrete and steel
RUBBER = (0.06, 0.06, 0.06, 1.0)    # not used as a material yet — see the one-material note below


def road_wheels(bm, count, x0, spacing, y, z, radius, width, segments=10):
    """A row of `count` road wheels along +X at `y`, `z`. Returns nothing; adds geometry.

    Wheels are cylinders on the Y axis. `segments = 10` is deliberately coarse: at any range where
    a player can resolve a road wheel they can also read the vehicle's whole silhouette, and a
    smooth wheel costs triangles on every one of them.

    ⚠ WHEELED VEHICLES ONLY. Both tracked units here called this in their first cut and neither
    render showed a single wheel: a track run wraps AROUND its road wheels, so they sit entirely
    inside the track box and are invisible from every angle a player will ever have. That was
    ~200 triangles apiece rendering nothing. If you are building something with tracks, the track
    run IS the wheels.
    """
    for i in range(count):
        prims.cylinder(bm, (x0 + i * spacing, y, z), radius, width, axis="y", segments=segments)


def tracked_hull(bm, length, width, height, z_ground, track_width=0.5, track_height=0.7):
    """A tracked chassis: a hull box between two track runs. The shared half of both AFVs here."""
    track_z = z_ground + track_height * 0.5
    for side in (1.0, -1.0):
        prims.box(bm, (0.0, side * (width * 0.5 - track_width * 0.5), track_z),
                  (length, track_width, track_height))
    hull_z = z_ground + track_height + height * 0.5
    prims.box(bm, (0.0, 0.0, hull_z), (length * 0.92, width - track_width * 0.6, height))
    return hull_z + height * 0.5   # the deck height, for whatever gets mounted on it


def finish(bm, ident, colour):
    """Commit the bmesh, apply one material and planar UVs, and hand back the object."""
    prims.recalc_normals(bm)
    obj = scene.finish_mesh(bm, ident)
    # ONE material per vehicle, like the aircraft. The engine's mesh convention names materials
    # lowercase-underscored (validate-mesh applyConventionChecks) and a second material would buy
    # nothing until there is a texture set to hang off it.
    scene.principled_material(obj, f"{ident}_paint", colour, metallic=0.0, roughness=0.85)
    dims = obj.dimensions
    uvatlas.planar_uvs(obj, max(dims.x, 1.0), max(dims.y, 1.0))
    return obj


def run(ident, build_fn, colour=OLIVE, argv=None, damage_seed=11):
    """The whole build for one ground unit: geometry, damage variant, shadow hull, export.

    ⚑ NO LOD FILES, AND THAT IS A DECISION RATHER THAN AN OMISSION. An aircraft here emits
    lod0/1/2 at 50/20/5 percent because a 30,000-triangle airframe is worth simplifying. These
    vehicles are a few hundred triangles as authored — already below what an aircraft's COARSEST
    LOD costs — so decimating them would spend build time and four more files to save nothing
    measurable, and a 5%-decimated box stops being box-shaped. `validate-mesh` discovers LOD
    siblings when they exist and requires nothing when they do not (mesh_validator.cpp:582).
    Revisit if a mission ever fields these by the dozen.
    """
    ap = argparse.ArgumentParser(description=f"Build the {ident} mesh set.")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv if argv is not None else sys.argv[sys.argv.index("--") + 1:])
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    scene.clear_scene()
    bm = bmesh.new()
    build_fn(bm)
    body = finish(bm, ident, colour)

    # The battle-damage variant is the `<ident>_b` NODE inside the base glb, parented to the base
    # node — not a separate file. (The F-5E's validate-entity lesson: a `damage_mesh` file is a
    # different convention and this pack does not use it.)
    dmg = damage.battle_damage(body, f"{ident}_paint", seed=damage_seed)
    dmg.name = f"{ident}_b"
    dmg.parent = body

    export.export_glb(out / f"{ident}.glb", [body, dmg])

    hull = scene.convex_hull(body, f"{ident}_shadow")
    export.export_glb(out / f"{ident}_shadow.glb", [hull])

    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"{ident}: wrote mesh set to {out} ({len(body.data.polygons)} faces, ~{tris} triangles)")
    bpy.data.objects.remove(hull, do_unlink=True)
