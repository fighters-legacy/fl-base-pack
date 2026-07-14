# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""UV assignment. Requires Blender (bpy).

Currently only the honest placeholder: a planar projection normalised by overall length and span.
Real per-part atlas islands (PR-follow-up, fighters-legacy texture work) will live here too — the
build scripts call into this module so the UV strategy is changed in one place.
"""


def planar_uvs(obj, length, span, name="uv") -> None:
    """Planar UVs: u = x/length, v = (y + span/2)/span. Deterministic; no unwrap.

    Real texel density needs a proper unwrap; this is honest placeholder mapping, adequate while the
    engine renders every mesh grey (fighters-legacy#833)."""
    me = obj.data
    uv = me.uv_layers.new(name=name)
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / length, (co.y + span / 2.0) / span)
