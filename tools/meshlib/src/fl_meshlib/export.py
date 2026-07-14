# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""glTF export and GLB post-processing. Requires Blender (bpy) except patch_textures (pure)."""

import json
import struct
from pathlib import Path

import bpy

_GLB_MAGIC = 0x46546C67
_CHUNK_JSON = 0x4E4F534A


def select_only(objs) -> None:
    """Select exactly `objs` in the current scene, deselecting everything else."""
    objset = set(objs)
    for o in bpy.context.scene.objects:
        o.select_set(o in objset)


def export_glb(path, objs, animations=False) -> None:
    """Export `objs` (and only them) to a binary glTF at `path`.

    Images are NEVER embedded — validate-mesh errors on embedded image data, and the engine
    consumes external .ktx2 URIs wired in by patch_textures. Animations are off by default; the
    articulated build turns them on.
    """
    select_only(objs)
    kwargs = dict(
        filepath=str(path), export_format="GLB",
        export_image_format="NONE",
        export_normals=True, export_tangents=True, export_texcoords=True,
        export_extras=True,          # carry marker-empty custom props to glTF node `extras`
        use_selection=True,
    )
    if animations:
        kwargs.update(export_animations=True, export_animation_mode="NLA_TRACKS")
    bpy.ops.export_scene.gltf(**kwargs)


def patch_textures(path, diffuse_uri, orm_uri) -> None:
    """Wire external base-colour and ORM .ktx2 URIs into a GLB's JSON chunk. Pure Python.

    validate-mesh checks only that no image is EMBEDDED; it does not require the .ktx2 to exist yet,
    so references can be pre-wired before tex-compress has run. This is the single place the texture
    URI convention lives — the engine's final convention (fighters-legacy#833) changes only here.
    """
    path = Path(path)
    raw = path.read_bytes()
    if struct.unpack_from("<I", raw, 0)[0] != _GLB_MAGIC:
        raise ValueError(f"not a GLB: {path}")
    jlen = struct.unpack_from("<I", raw, 12)[0]
    g = json.loads(raw[20:20 + jlen])
    tail = raw[20 + jlen:]

    g["images"] = [{"uri": diffuse_uri}, {"uri": orm_uri}]
    g["textures"] = [{"source": 0}, {"source": 1}]
    for mat in g.get("materials", []):
        pbr = mat.setdefault("pbrMetallicRoughness", {})
        pbr["baseColorTexture"] = {"index": 0}
        pbr["metallicRoughnessTexture"] = {"index": 1}
        mat["occlusionTexture"] = {"index": 1}

    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    path.write_bytes(struct.pack("<III", _GLB_MAGIC, 2, 12 + 8 + len(js) + len(tail))
                     + struct.pack("<II", len(js), _CHUNK_JSON) + js + tail)


def decimate(obj, ratio, name):
    """A decimated copy of `obj` named `name`, the modifier applied. For separate-file LODs."""
    lod = obj.copy()
    lod.data = obj.data.copy()
    lod.name = lod.data.name = name
    bpy.context.collection.objects.link(lod)
    m = lod.modifiers.new("dec", "DECIMATE")
    m.ratio = ratio
    bpy.context.view_layer.objects.active = lod
    bpy.ops.object.modifier_apply(modifier="dec")
    return lod
