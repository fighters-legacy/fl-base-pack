# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Scene and object helpers. Requires Blender (bpy, bmesh)."""

import bpy


def clear_scene() -> None:
    """Delete all objects and orphan data so a build starts from an empty scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            block.remove(item)


def finish_mesh(bm, name: str):
    """Commit a bmesh to a new, linked object named `name`. Frees `bm`. Returns the object.

    UVs and materials are applied by the caller afterwards, so this stays aircraft-agnostic.
    """
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    return obj


def principled_material(obj, name, base_color, metallic, roughness):
    """Assign a single Principled-BSDF material named `name` to `obj` (replacing any existing).

    `base_color` is an RGBA 4-tuple. The material carries no image textures — those are wired as
    external URIs after export (see export.patch_textures)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return mat


def convex_hull(source_obj, name: str):
    """A materialless convex-hull object of `source_obj`'s geometry — a shadow proxy."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(source_obj.data)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    return obj


def empty(name: str, location=(0.0, 0.0, 0.0), extras=None):
    """An empty object, exported as a glTF node. `extras` become glTF node `extras` (metadata).

    A marker the renderer looks up by name (a `camera_anchor`, a hardpoint, a hinge pivot) with no
    geometry of its own.
    """
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    if extras:
        for k, v in extras.items():
            obj[k] = v
    bpy.context.collection.objects.link(obj)
    return obj
