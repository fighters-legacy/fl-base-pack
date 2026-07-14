# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Battle-damage variant generation. Requires Blender (bpy, mathutils)."""

import random

import bpy
from mathutils import Vector


def battle_damage(obj, material_name=None, seed=5, jitter_prob=0.22, max_disp=0.05):
    """The `_b` damage-state node: same topology as `obj`, torn and dented deterministically.

    validate-mesh requires that a `_b` node have a base node of the same stem in the SAME .glb, so
    the caller exports this alongside the base object, not separately.

    Material: with `material_name` None (the default) the copied mesh keeps `obj`'s material slots
    and per-face assignment — the right choice for a multi-slot airframe, whose damage variant must
    render with the same skin/canopy/nozzle split. Pass a name to collapse to a single slot.

    Determinism: the RNG is seeded explicitly and every vertex consumes exactly one `random()` for
    the jitter test, so the sequence is fixed for a given `seed`. Do not reorder the draws.
    """
    rng = random.Random(seed)
    me = obj.data.copy()
    dmg = bpy.data.objects.new(obj.name + "_b", me)
    bpy.context.collection.objects.link(dmg)
    for v in me.vertices:
        if rng.random() < jitter_prob:
            s = max_disp * rng.random()
            v.co += Vector((rng.uniform(-s, s), rng.uniform(-s, s), rng.uniform(-s, s)))
    if material_name is not None:
        me.materials.clear()
        me.materials.append(bpy.data.materials[material_name])
    return dmg
