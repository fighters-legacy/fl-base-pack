#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Build the F-5E Tiger II mesh set from published dimensions.

    blender --background --python aircraft/f5e/f5e_build.py -- --out aircraft/f5e

Emits, per docs/modding/3d-models.md:
    f5e.glb          base mesh; root node `f5e`, damage-state node `f5e_b`
    f5e_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    f5e_shadow.glb   convex hull, no materials
    f5e_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
PROVENANCE — read this before changing a single number.
═══════════════════════════════════════════════════════════════════════════════════════════════════
This airframe is generated ENTIRELY FROM PUBLISHED DIMENSIONS. Nothing here is traced from, derived
from, or "cleaned up" out of another simulator, game, or commercial 3D model. See
docs/legal/aircraft-likeness.md in the engine repo, and SOURCES.md alongside this file.

That is possible because NASA's spin-tunnel report (NTRS 19980227417, Table I) publishes the complete
planform, and it CLOSES: root chord 3.5735 m, tip chord 0.6840 m and span 8.13 m give a trapezoid of
17.307 m^2 against the published wing area of 17.30 m^2 — 0.04%. The wing is a simple trapezoid and
every dimension of it is in the public record. Same for both tails.

Where a dimension is genuinely NOT published (fuselage cross-section, canopy shape, intake geometry),
it is marked [E] and shaped to the published length, height and the known fuselage width at the tail.
Those are the only judgement calls in this file, and they are visual only — nothing the flight model
consumes comes from here.

NO MARKINGS. Policy §4: no unit insignia, squadron badges, nose art or operator liveries. Bare metal
with a generic aggressor-grey scheme, applied via external .ktx2 textures, never baked geometry.

═══════════════════════════════════════════════════════════════════════════════════════════════════
CONVENTIONS (docs/modding/3d-models.md — get these wrong and validate-mesh rejects the file)
═══════════════════════════════════════════════════════════════════════════════════════════════════
  * Engine axes: +X forward (nose), +Y up, +Z starboard, metres.
    Blender's glTF exporter maps Blender +X -> glTF +X, Blender +Z -> glTF +Y, Blender -Y -> glTF +Z.
    So we build with NOSE ALONG BLENDER +X, UP = +Z, STARBOARD = -Y. Do not "fix" this.
  * Winding CCW from outside, normals outward. The opaque pipeline is single-sided; an inside-out
    face is invisible from the outside and validate-mesh errors on it.
  * Node and material names: lowercase with underscores. No hyphens, no spaces, no uppercase.
  * NO EMBEDDED IMAGE DATA. Textures are external .ktx2 URIs, pre-wired here so the references exist
    before tex-compress has ever run.
"""

import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

# ═══ PUBLISHED GEOMETRY — NASA spin-tunnel report (NTRS 19980227417), Table I ═══════════════ [P] ═
LENGTH        = 14.68     # m   overall
SPAN          = 8.13      # m   wing span, without tip missiles
WING_AREA     = 17.30     # m^2 (checked: the trapezoid below reproduces this to 0.04%)
ROOT_CHORD    = 3.5735    # m
TIP_CHORD     = 0.6840    # m
SWEEP_C4      = 24.0      # deg wing quarter-chord sweep
THICKNESS     = 0.048     # NACA 65A004.8 — symmetric, 4.8% thick

HT_SPAN       = 4.30      # m   horizontal tail, tip to tip
HT_TIP_CHORD  = 0.508     # m
HT_TAPER      = 0.33
HT_SWEEP_C4   = 25.0      # deg
HT_DIHEDRAL   = -4.0      # deg — ANHEDRAL. The F-5's tailplane droops; it is not a typo.

VT_TIP_CHORD  = 0.7112    # m   vertical tail
VT_TAPER      = 0.25
VT_SWEEP_C4   = 25.0      # deg
VT_AREA       = 3.85      # m^2 exposed
VT_AR         = 1.22      # on the exposed span

# ═══ FUSELAGE STATIONS — traced from NASA Figure 1 (the published 3-view) ══════════ [P/D] ═
#
# NASA's spin-tunnel report includes Figure 1, a dimensioned three-view of the F-5E (1/20 scale,
# dimensions in cm). docs/legal/aircraft-likeness.md explicitly permits declassified 3-views as
# references. The side-view contour below was SAMPLED OFF THAT DRAWING programmatically (column
# scan of the page ink; scale anchored to the printed 73.15 cm overall length and cross-checked
# against the printed 12.88 cm fin height and the printed MAC bar, 12.27 cm = 2.454 m vs the
# published 2.456). Method and verification overlays: the f5e_trace work recorded in SOURCES.md.
#
# Each station: (x/L, z_upper, z_lower, y_half), metres full scale, z from the fuselage reference
# line (= the drawing's own datum; the nose tip sits on it).
#   z_upper  [P] traced. In the canopy span it is the CANOPY top; under the fin (x/L > 0.78,
#            where the fin occludes the spine) and at two dimension-line-polluted stations it is
#            interpolated [D], marked below.
#   z_lower  [P] traced (the belly, including the aft boat-tail).
#   y_half   nose region [P] traced; mid/aft [D] from the twin-J85 packaging and NASA's own
#            tail-span arithmetic: exposed h-tail span 2.97 = 4.30 tip-to-tip - 2*0.665, so the
#            fuselage half-width AT THE TAILPLANE IS 0.665 -- published numbers, one subtraction.
#            The planform confirms the aft body stays broad to the nozzles (two engines abreast).
STATIONS_FUS = [
    # x/L    z_up    z_lo   y_half
    (0.000,  0.015, -0.015, 0.038),   # radome tip, on the reference line
    (0.030,  0.008, -0.307, 0.060),
    (0.060, -0.008, -0.369, 0.161),   # slight nose droop -- traced, it is real
    (0.100,  0.077, -0.438, 0.315),
    (0.140,  0.192, -0.499, 0.438),
    (0.190,  0.323, -0.553, 0.530),
    (0.240,  0.453, -0.584, 0.580),   # windshield base
    (0.290,  0.950, -0.561, 0.590),   # [D] canopy rise (dim-line polluted; interp of neighbours)
    (0.340,  1.020, -0.538, 0.590),   # [D] canopy peak (same)
    (0.400,  1.007, -0.523, 0.590),   # aft canopy fairing [P]
    (0.460,  0.937, -0.499, 0.645),   # intake fairing region, widest
    (0.520,  0.853, -0.469, 0.620),   # area-rule waist begins
    (0.580,  0.780, -0.553, 0.600),   # [D] (dimension-stem mask; interp)
    (0.640,  0.707, -0.561, 0.600),
    (0.700,  0.638, -0.561, 0.620),
    (0.760,  0.791, -0.553, 0.640),   # spine kick-up at the fin fillet
    (0.815,  0.700, -0.530, 0.665),   # [D] under the fin: spine interp; width = tail-span arith
    (0.860,  0.580, -0.499, 0.660),   # [D]
    (0.910,  0.460, -0.553, 0.630),   # [D]
    (0.960,  0.340, -0.400, 0.580),   # [D] boat-tail
    (1.000,  0.280, -0.200, 0.520),   # nozzle station
]
CANOPY_SPAN  = (0.245, 0.435)  # x/L range where z_up is canopy glass, not fuselage spine
CANOPY_HALFW = 0.34            # m [E] canopy width from the planform outline
NOZZLE_R     = 0.28            # m [D] from the front view; two, side by side
PITOT_LEN    = 0.55            # m [P] visible on the 3-view

# Surface placement stations (planform work, unchanged from the validated planform build)
WING_X_LE     = 5.95      # m   wing leading-edge root station
WING_Z        = -0.12     # m   low-mid wing
HT_X_C4       = 13.10     # m   horizontal tail quarter-chord station
VT_X_C4       = 11.90     # m   vertical tail quarter-chord station
TIP_RAIL_LEN  = 2.10      # m   wingtip AIM-9 rail (part of the airframe; see SOURCES.md)

MAT_AIRFRAME  = "f5e_airframe"
TEX_DIFFUSE   = "../../textures/f5e_diffuse.ktx2"
TEX_ORM       = "../../textures/f5e_orm.ktx2"


# ─── Airfoil ──────────────────────────────────────────────────────────────────────────────────────
def naca_symmetric(x: float, t: float) -> float:
    """Half-thickness of a symmetric NACA section at chord fraction x, thickness ratio t.

    The standard NACA thickness distribution. NASA gives the section as 65A004.8 — a symmetric
    4.8%-thick laminar-flow series. This reproduces its thickness envelope closely enough for a
    game mesh; the 6-series' exact camber-line mathematics buy nothing a player can see.
    """
    x = min(max(x, 0.0), 1.0)
    return 5.0 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x
                      + 0.2843 * x ** 3 - 0.1015 * x ** 4)


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for item in list(block):
            block.remove(item)


# ─── Lifting surfaces ─────────────────────────────────────────────────────────────────────────────
def _panel(bm, x_c4_root, semi_span, root_c, tip_c, sweep_c4, thick, dihedral=0.0,
           vertical=False, z0=0.0, sections=9):
    """One trapezoidal lifting surface, mirrored to both sides unless `vertical`.

    Positioned by its QUARTER-CHORD line, because that is how the source data is published:
        x_c4(y) = x_c4_root + y*tan(sweep_c4)      and      x_le(y) = x_c4(y) - 0.25*c(y)
    Building from the leading edge instead would mean back-computing a number NASA already gives us.
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
                    y = -side * span_pos                      # -Y is starboard, see the header
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


def _smoothstep(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def _lerp(a, b, u):
    return a + (b - a) * _smoothstep(u)


def _fus_at(t):
    """Interpolate the traced station table at x/L = t. Returns (z_up, z_lo, y_half)."""
    pts = STATIONS_FUS
    t = min(max(t, 0.0), 1.0)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
            return tuple(a[k] + (b[k] - a[k]) * u for k in (1, 2, 3))
    return pts[-1][1:]


def _spine_top(t):
    """The fuselage TOP at x/L = t, i.e. z_up with the canopy glass excluded.

    Inside the canopy span the traced z_up is the glass, not the skin; the skin is the smooth
    line between the windshield base and the aft fairing, so blend linearly across the span.
    The canopy bubble is then built separately, exactly as tall as the difference.
    """
    c0, c1 = CANOPY_SPAN
    z_up, _, _ = _fus_at(t)
    if t <= c0 or t >= c1:
        return z_up
    a = _fus_at(c0)[0]
    b = _fus_at(c1)[0]
    return a + (b - a) * (t - c0) / (c1 - c0)


def _fuselage(bm, sections=44):
    """Loft the traced NASA Figure 1 stations. See STATIONS_FUS for provenance.

    Cross-section: superellipse spanning [z_lo, spine_top] with the traced half-width. The
    section is asymmetric top-to-bottom exactly as the drawing is -- centreline and half-height
    fall out of the traced upper/lower contours; nothing here is shaped by eye any more except
    the superellipse roundness itself.
    """
    rings = []
    for i in range(sections + 1):
        t = i / sections
        x = t * LENGTH
        top = _spine_top(t)
        _, lo, w = _fus_at(t)
        cz = (top + lo) / 2.0
        hh = max((top - lo) / 2.0, 0.02)
        w = max(w, 0.02)
        n = 2.05 + 0.4 * _smoothstep(t / 0.25)          # round nose, flatter-sided body
        ring = []
        steps = 16
        for j in range(steps):
            th = 2.0 * math.pi * j / steps
            c, sn = math.cos(th), math.sin(th)
            y = w * math.copysign(abs(c) ** (2.0 / n), c)
            z = hh * math.copysign(abs(sn) ** (2.0 / n), sn)
            ring.append(bm.verts.new(Vector((x, y, cz + z))))
        rings.append(ring)

    for i in range(sections):
        a, b = rings[i], rings[i + 1]
        m = len(a)
        for j in range(m):
            k = (j + 1) % m
            try:
                bm.faces.new((a[j], a[k], b[k], b[j]))
            except ValueError:
                pass
    try:
        bm.faces.new(list(reversed(rings[0])))
    except ValueError:
        pass

    # Twin J85 nozzles, from the front view: two abreast at the tail.
    for side in (1.0, -1.0):
        y0 = -side * 0.30
        prev = None
        for i in range(4):
            f = i / 3.0
            x = LENGTH - 0.30 + f * 0.30
            r = NOZZLE_R * (1.0 - 0.15 * f)
            ring = [bm.verts.new(Vector((x, y0 + r * math.cos(2 * math.pi * j / 10),
                                         0.04 + r * math.sin(2 * math.pi * j / 10))))
                    for j in range(10)]
            if prev:
                for j in range(10):
                    k = (j + 1) % 10
                    try:
                        f4 = (prev[j], prev[k], ring[k], ring[j]) if side > 0 else \
                             (prev[j], ring[j], ring[k], prev[k])
                        bm.faces.new(f4)
                    except ValueError:
                        pass
            prev = ring

    # Pitot boom -- visible on the 3-view, part of the silhouette.
    pb = []
    for i in range(2):
        x = -PITOT_LEN + i * PITOT_LEN
        r = 0.016 if i == 0 else 0.028
        pb.append([bm.verts.new(Vector((x, r * math.cos(2 * math.pi * j / 6),
                                        r * math.sin(2 * math.pi * j / 6))))
                   for j in range(6)])
    for j in range(6):
        k = (j + 1) % 6
        try:
            bm.faces.new((pb[0][j], pb[0][k], pb[1][k], pb[1][j]))
        except ValueError:
            pass


def _tip_rails(bm):
    """Wingtip AIM-9 launch rails. Part of the AIRFRAME, not a store.

    This matters for more than art: the T.O. quotes max level Mach 1.63 for "launcher rails only"
    and 1.57 "with tip missiles", so the rails are present in BOTH published conditions. They belong
    to the aeroplane. The missiles themselves are stores and are not modelled here.
    """
    y_tip = SPAN / 2.0
    x_c4_tip = WING_X_LE + 0.25 * ROOT_CHORD + (SPAN / 2.0) * math.tan(math.radians(SWEEP_C4))
    x0 = x_c4_tip - 0.25 * TIP_CHORD - 0.55
    for side in (1.0, -1.0):
        y = -side * y_tip
        rings = []
        for i in range(7):
            f = i / 6.0
            x = x0 + f * TIP_RAIL_LEN
            r = 0.085 * (1.0 - 0.55 * abs(2.0 * f - 1.0) ** 3)   # tapered nose and tail
            ring = []
            for j in range(8):
                th = 2.0 * math.pi * j / 8
                ring.append(bm.verts.new(Vector((x, y + r * math.cos(th), r * math.sin(th)))))
            rings.append(ring)
        for i in range(6):
            a, b = rings[i], rings[i + 1]
            for j in range(8):
                k = (j + 1) % 8
                try:
                    f = (a[j], a[k], b[k], b[j]) if side > 0 else (a[j], b[j], b[k], a[k])
                    bm.faces.new(f)
                except ValueError:
                    pass


def _canopy(bm):
    """Canopy glass: exactly the bump the trace measured -- z_up minus the blended spine.

    Width is the one [E] left in the canopy: the planform outline reads ~0.34 m half-width.
    """
    c0, c1 = CANOPY_SPAN
    rings = []
    steps = 14
    for i in range(steps + 1):
        f = i / steps
        t = c0 + f * (c1 - c0)
        x = t * LENGTH
        z_glass = _fus_at(t)[0]
        z_skin = _spine_top(t)
        h = max(z_glass - z_skin, 0.0) + 0.02
        w = CANOPY_HALFW * math.sin(min(max(f, 0.04), 0.96) * math.pi) ** 0.5
        ring = []
        for j in range(10):
            th = math.pi * j / 9.0
            ring.append(bm.verts.new(Vector((x, w * math.cos(th), z_skin - 0.05 + h * math.sin(th)))))
        rings.append(ring)
    for i in range(steps):
        a, b = rings[i], rings[i + 1]
        for j in range(9):
            try:
                bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
            except ValueError:
                pass


# ─── Assembly ─────────────────────────────────────────────────────────────────────────────────────
def build_airframe(name: str) -> bpy.types.Object:
    bm = bmesh.new()

    _fuselage(bm)
    _canopy(bm)

    # Wing — positioned by its published quarter-chord line.
    _panel(bm, WING_X_LE + 0.25 * ROOT_CHORD, SPAN / 2.0, ROOT_CHORD, TIP_CHORD,
           SWEEP_C4, THICKNESS, dihedral=0.0, z0=WING_Z)
    _tip_rails(bm)

    # Horizontal tail — all-moving, and it droops 4 degrees.
    ht_exposed_span = math.sqrt(2.88 * 3.07)                       # 2.97 m, from NASA's exposed AR
    ht_root = HT_TIP_CHORD / HT_TAPER                              # 1.539 m at the fuselage side
    # Extrapolate the taper line inboard to the centreline so the surface meets the fuselage.
    w_tail = _fus_at(HT_X_C4 / LENGTH)[2]          # 0.665 -- NASA tail-span arithmetic
    f_side = w_tail / (HT_SPAN / 2.0)
    ht_c0 = (ht_root - HT_TIP_CHORD * f_side) / (1.0 - f_side)
    _panel(bm, HT_X_C4, HT_SPAN / 2.0, ht_c0, HT_TIP_CHORD, HT_SWEEP_C4, 0.04,
           dihedral=HT_DIHEDRAL, z0=0.10)

    # Vertical tail — exposed AR 1.22 on exposed area 3.85 m^2.
    vt_height = math.sqrt(VT_AR * VT_AREA)                          # 2.167 m
    vt_root = VT_TIP_CHORD / VT_TAPER                               # 2.845 m
    _panel(bm, VT_X_C4, vt_height, vt_root, VT_TIP_CHORD, VT_SWEEP_C4, 0.04,
           vertical=True, z0=0.55)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)               # outward: CCW from outside
    return _commit(bm, name)


def _commit(bm, name: str) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.validate()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    _uvs(obj)
    _material(obj)
    return obj


def _uvs(obj) -> None:
    """Planar-ish UVs. Real texel density needs a proper unwrap; this is honest placeholder mapping."""
    me = obj.data
    uv = me.uv_layers.new(name="uv")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / LENGTH, (co.y + SPAN / 2.0) / SPAN)


def _material(obj) -> None:
    mat = bpy.data.materials.get(MAT_AIRFRAME) or bpy.data.materials.new(MAT_AIRFRAME)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.42, 0.44, 0.47, 1.0)   # aggressor grey
        bsdf.inputs["Metallic"].default_value = 0.15
        bsdf.inputs["Roughness"].default_value = 0.55
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def apply_battle_damage(obj, seed: int = 5) -> bpy.types.Object:
    """The `_b` damage-state node: same topology, torn and dented.

    validate-mesh requires that a `_b` node have a base node of the same name in the SAME .glb --
    a damage node with no base is an error. So this is exported alongside f5e, not separately.
    """
    import random
    rng = random.Random(seed)
    me = obj.data.copy()
    dmg = bpy.data.objects.new(obj.name + "_b", me)
    bpy.context.collection.objects.link(dmg)
    for v in me.vertices:
        if rng.random() < 0.22:
            s = 0.05 * rng.random()
            v.co += Vector((rng.uniform(-s, s), rng.uniform(-s, s), rng.uniform(-s, s)))
    me.materials.clear()
    me.materials.append(bpy.data.materials[MAT_AIRFRAME])
    return dmg


# ─── Export ───────────────────────────────────────────────────────────────────────────────────────
def _select_only(objs) -> None:
    for o in bpy.context.scene.objects:
        o.select_set(o in objs)


def _export(path: Path, objs) -> None:
    _select_only(objs)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB",
        export_image_format="NONE",          # NEVER embed images -- validate-mesh errors on it
        export_normals=True, export_tangents=True, export_texcoords=True,
        use_selection=True,
    )


def _patch_textures(path: Path) -> None:
    """Wire external .ktx2 URIs into the GLB's JSON chunk.

    validate-mesh checks only that no image is EMBEDDED; it does not require the .ktx2 to exist yet.
    So the references can be pre-wired before tex-compress has ever run -- which is what lets this
    script produce a validating mesh with no texture pipeline in place.
    """
    raw = path.read_bytes()
    if struct.unpack_from("<I", raw, 0)[0] != 0x46546C67:
        raise ValueError(f"not a GLB: {path}")
    jlen = struct.unpack_from("<I", raw, 12)[0]
    g = json.loads(raw[20:20 + jlen])
    tail = raw[20 + jlen:]

    g["images"] = [{"uri": TEX_DIFFUSE}, {"uri": TEX_ORM}]
    g["textures"] = [{"source": 0}, {"source": 1}]
    for mat in g.get("materials", []):
        pbr = mat.setdefault("pbrMetallicRoughness", {})
        pbr["baseColorTexture"] = {"index": 0}
        pbr["metallicRoughnessTexture"] = {"index": 1}
        mat["occlusionTexture"] = {"index": 1}

    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    path.write_bytes(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + len(tail))
                     + struct.pack("<II", len(js), 0x4E4F534A) + js + tail)


def _decimate(obj, ratio: float, name: str) -> bpy.types.Object:
    lod = obj.copy()
    lod.data = obj.data.copy()
    lod.name = lod.data.name = name
    bpy.context.collection.objects.link(lod)
    m = lod.modifiers.new("dec", "DECIMATE")
    m.ratio = ratio
    bpy.context.view_layer.objects.active = lod
    bpy.ops.object.modifier_apply(modifier="dec")
    return lod


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="aircraft/f5e")
    ap.add_argument("--id", default="f5e")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    aid = args.id

    _clear_scene()
    body = build_airframe(aid)
    tris = len(body.data.polygons)

    # Base mesh + its damage state, in ONE file. The `_b` node MUST ship beside its base.
    dmg = apply_battle_damage(body)
    _export(out / f"{aid}.glb", [body, dmg])
    _patch_textures(out / f"{aid}.glb")
    bpy.data.objects.remove(dmg)

    # LODs are separate FILES, not nodes. (fl-base-pack's CONTRIBUTING.md said nodes; it was wrong.)
    for i, ratio in enumerate((0.50, 0.20, 0.05)):
        lod = _decimate(body, ratio, f"{aid}_lod{i}")
        _export(out / f"{aid}_lod{i}.glb", [lod])
        _patch_textures(out / f"{aid}_lod{i}.glb")
        bpy.data.objects.remove(lod)

    # Shadow proxy: convex hull, NO materials.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    sh_me = bpy.data.meshes.new(f"{aid}_shadow")
    bm.to_mesh(sh_me)
    bm.free()
    sh_me.materials.clear()
    shadow = bpy.data.objects.new(f"{aid}_shadow", sh_me)
    bpy.context.collection.objects.link(shadow)
    _export(out / f"{aid}_shadow.glb", [shadow])

    # Cockpit: must contain a node named exactly `camera_anchor` -- the renderer looks for it by name.
    anchor = bpy.data.objects.new("camera_anchor", None)
    anchor.location = ((CANOPY_SPAN[0] + 0.35 * (CANOPY_SPAN[1] - CANOPY_SPAN[0])) * LENGTH, 0.0, _fus_at(0.30)[0] - 0.25)
    bpy.context.collection.objects.link(anchor)
    _export(out / f"{aid}_cockpit.glb", [anchor])

    print(f"\n  {aid}: {tris} faces")
    print(f"  wrote {aid}.glb (+ _b), _lod0/1/2, _shadow, _cockpit -> {out}")
    return 0


if __name__ == "__main__":
    rc = main()
    if bpy.app.background:
        sys.exit(rc)          # headless (CI / --background): exit code matters
    # GUI attached: stay open so the scene can be inspected. Tidy it for viewing --
    # the shadow hull otherwise sits on top of the airframe.
    for o in bpy.context.scene.objects:
        if o.name.endswith("_shadow") or o.name == "camera_anchor":
            o.hide_set(True)
