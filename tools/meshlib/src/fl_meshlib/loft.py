# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Lofting primitives that build into a bmesh. Requires Blender (bmesh, mathutils)."""

import math

from mathutils import Vector

from .airfoil import naca_symmetric


def panel(bm, x_c4_root, semi_span, root_c, tip_c, sweep_c4, thick, dihedral=0.0,
          vertical=False, z0=0.0, sections=9):
    """One trapezoidal lifting surface, mirrored to both sides unless `vertical`.

    Positioned by its QUARTER-CHORD line, because that is how planform data is published:
        x_c4(y) = x_c4_root + y*tan(sweep_c4)      and      x_le(y) = x_c4(y) - 0.25*c(y)
    Building from the leading edge instead would mean back-computing a number the source already
    gives. Engine axes: nose +X, up +Z, starboard -Y (Blender space; the glTF exporter maps it).
    """
    sides = [1.0] if vertical else [1.0, -1.0]
    for side in sides:
        rings = []
        for i in range(sections + 1):
            f = i / sections
            span_pos = f * semi_span
            chord = root_c + (tip_c - root_c) * f
            x_c4 = x_c4_root + span_pos * math.tan(math.radians(sweep_c4))
            x_le = x_c4 - 0.25 * chord

            ring = []
            steps = 14
            for j in range(steps + 1):                       # upper surface, LE -> TE
                xc = j / steps
                ring.append((x_le + xc * chord, naca_symmetric(xc, thick) * chord))
            for j in range(steps - 1, 0, -1):                # lower surface, TE -> LE
                xc = j / steps
                ring.append((x_le + xc * chord, -naca_symmetric(xc, thick) * chord))

            verts = []
            for (x, half_t) in ring:
                if vertical:
                    # A fin: "span" runs up (+Z), thickness runs across (Y).
                    verts.append(bm.verts.new(Vector((x, half_t, z0 + span_pos))))
                else:
                    y = -side * span_pos                      # -Y is starboard
                    z = z0 + span_pos * math.tan(math.radians(dihedral)) * side * side
                    verts.append(bm.verts.new(Vector((x, y, z + half_t))))
            rings.append(verts)

        for i in range(sections):
            a, b = rings[i], rings[i + 1]
            n = len(a)
            for j in range(n):
                k = (j + 1) % n
                try:
                    # Winding flips with the mirror: keep normals pointing OUT on both wings.
                    f = (a[j], b[j], b[k], a[k]) if side > 0 or vertical else (a[j], a[k], b[k], b[j])
                    bm.faces.new(f)
                except ValueError:
                    pass                                       # duplicate face at a degenerate tip
        # Cap the tip so the surface is closed (validate-mesh wants a manifold, lit solid).
        try:
            bm.faces.new(rings[-1] if side > 0 or vertical else list(reversed(rings[-1])))
        except ValueError:
            pass


def bridge(bm, a, b, flip):
    """Quad-bridge two equal-length rings. `flip` reverses winding for the mirrored side."""
    m = len(a)
    for j in range(m):
        k = (j + 1) % m
        quad = (a[j], a[k], b[k], b[j]) if not flip else (a[j], b[j], b[k], a[k])
        try:
            bm.faces.new(quad)
        except ValueError:
            pass
