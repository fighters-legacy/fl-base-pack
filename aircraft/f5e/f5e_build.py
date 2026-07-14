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

# ═══ NOT PUBLISHED — visual only. Nothing the flight model reads comes from here. ══════════ [E] ═
#
# The F-5E's fuselage is SLIM and WAISTED, then WIDENS AGAIN AT THE TAIL for the two side-by-side
# J85s. That is not a stylistic reading -- FUS_TAIL_W below is derived, not guessed, and it is wider
# than the forward fuselage. Getting this wrong makes a slab, which is exactly what the first cut of
# this script produced.
FUS_FWD_W     = 0.56      # m   half-width of the forward fuselage (slim -- it holds a small radar)
FUS_INTAKE_W  = 0.88      # m   half-width across the intake fairings, the widest point
FUS_TAIL_W    = 0.665     # m   half-width at the tail — DERIVED: NASA's exposed h-tail span (2.97 m)
                          #     subtracted from its tip-to-tip span (4.30 m), halved.
FUS_MAX_H     = 0.72      # m   half-height at the cockpit
NOSE_LEN      = 3.30      # m   radome + forward fuselage to the intake lips
PITOT_LEN     = 0.55      # m   the F-5E really does carry a nose pitot boom
WING_X_LE     = 5.95      # m   wing leading-edge root station aft of the nose
WING_Z        = -0.12     # m   low-mid wing, blended into the fuselage side
HT_X_C4       = 13.10     # m   horizontal tail quarter-chord station
VT_X_C4       = 11.90     # m   vertical tail quarter-chord station
CANOPY_X0     = 3.10      # m
CANOPY_X1     = 5.55      # m
TIP_RAIL_LEN  = 2.10      # m   the AIM-9 launch rail is part of the airframe, not a store
NOZZLE_R      = 0.30      # m   J85 exhaust radius; two of them, side by side

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


def _fuselage(bm, sections=40):
    """Lofted fuselage — slim forward body, intake fairings, area-ruled waist, twin-engine tail.

    THE SHAPE THAT MATTERS: the F-5E is NOT a slab. Its forward fuselage is slim (it carries a small
    ranging radar, not a big pulse-doppler set), it bulges at the side intakes, waists in behind them
    where the wing joins -- that is the AREA RULE, and it is why 9,300 lbf of thrust gets this
    aeroplane past Mach 1.6 -- and then WIDENS AGAIN at the tail to hold two J85s side by side.

    The width curve below is non-monotonic for exactly that reason. Cross-sections are [E]; the tail
    half-width is derived (see the constants).
    """
    x_intake = NOSE_LEN / LENGTH
    x_wing = WING_X_LE / LENGTH

    def half_width(t):
        if t <= 0.0:
            return 0.03
        if t < x_intake:                                    # radome -> forward fuselage
            return _lerp(0.05, FUS_FWD_W, t / x_intake)
        if t < x_wing:                                      # intake fairings: the widest point
            return _lerp(FUS_FWD_W, FUS_INTAKE_W, (t - x_intake) / (x_wing - x_intake))
        if t < 0.78:                                        # AREA-RULE WAIST behind the intakes
            return _lerp(FUS_INTAKE_W, 0.60, (t - x_wing) / (0.78 - x_wing))
        return _lerp(0.60, FUS_TAIL_W, (t - 0.78) / 0.22)   # widen again for the twin J85s

    def half_height(t):
        if t <= 0.0:
            return 0.03
        if t < 0.20:
            return _lerp(0.05, FUS_MAX_H * 0.92, t / 0.20)
        if t < 0.68:
            return FUS_MAX_H
        return _lerp(FUS_MAX_H, 0.44, (t - 0.68) / 0.32)    # aft body tapers to the nozzles

    def zc(t):
        """Centreline height. THIS is what stops it reading as a dart.

        A real fighter is not a symmetric lens about a straight axis. The belly is roughly FLAT and
        level from the nose to the wing, and the aft fuselage BOAT-TAILS UPWARD to the nozzles. So
        the centreline rises aft. The first cut instead drooped the NOSE, which is what made the
        whole silhouette look like a dart rather than an aeroplane.
        """
        if t < x_intake:
            return _lerp(0.14, 0.0, t / x_intake)           # nose sits slightly HIGH, not low
        if t < 0.68:
            return 0.0
        return _lerp(0.0, 0.20, (t - 0.68) / 0.32)          # boat-tail up toward the exhausts

    def roundness(t):
        # Superellipse exponent: round nose (2.0), flatter mid-body sides where the intakes sit.
        return _lerp(2.05, 2.45, min(t / x_intake, 1.0))

    rings = []
    for i in range(sections + 1):
        t = i / sections
        x = t * LENGTH
        w, h, n = half_width(t), half_height(t), roundness(t)
        cz = zc(t)
        ring = []
        steps = 16
        for j in range(steps):
            th = 2.0 * math.pi * j / steps
            c, s = math.cos(th), math.sin(th)
            y = w * math.copysign(abs(c) ** (2.0 / n), c)
            z = h * math.copysign(abs(s) ** (2.0 / n), s)
            ring.append(bm.verts.new(Vector((x, y, cz + z))))
        rings.append(ring)

    for i in range(sections):
        a, b = rings[i], rings[i + 1]
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                bm.faces.new((a[j], a[k], b[k], b[j]))
            except ValueError:
                pass
    try:
        bm.faces.new(list(reversed(rings[0])))
    except ValueError:
        pass

    # Twin exhaust nozzles, recessed into the tail face rather than a flat cap.
    for side in (1.0, -1.0):
        y0 = -side * (FUS_TAIL_W * 0.48)
        prev = None
        for i in range(4):
            f = i / 3.0
            x = LENGTH - 0.35 + f * 0.35
            r = NOZZLE_R * (1.0 - 0.18 * f)
            ring = [bm.verts.new(Vector((x, y0 + r * math.cos(2 * math.pi * j / 10),
                                         -0.06 + r * math.sin(2 * math.pi * j / 10))))
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

    # Pitot boom. The F-5E genuinely carries one, and its silhouette is part of the aircraft.
    pb = []
    for i in range(2):
        x = -PITOT_LEN + i * PITOT_LEN
        r = 0.018 if i == 0 else 0.030
        pb.append([bm.verts.new(Vector((x, r * math.cos(2 * math.pi * j / 6),
                                        zc(0.0) + r * math.sin(2 * math.pi * j / 6))))
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
    """Bubble canopy. Shape is [E]. A teardrop that RISES from the spine and fairs back into it --
    the first cut was a flat elliptical patch stuck on top, which read as a blister, not a cockpit."""
    rings = []
    steps = 16
    for i in range(steps + 1):
        f = i / steps
        x = CANOPY_X0 + f * (CANOPY_X1 - CANOPY_X0)
        # Rise fast at the windscreen, hold, then fair away long and low into the spine.
        prof = math.sin(min(f * 1.55, 1.0) * math.pi / 2) ** 0.85 * (1.0 - _smoothstep(max(0.0, (f - 0.55) / 0.45)) * 0.92)
        w = 0.40 * prof + 0.03
        h = 0.52 * prof
        base = FUS_MAX_H * 0.72
        ring = []
        for j in range(10):
            th = math.pi * j / 9.0                        # upper half only: it sits ON the spine
            ring.append(bm.verts.new(Vector((x, w * math.cos(th), base + h * math.sin(th)))))
        rings.append(ring)
    for i in range(steps):
        a, b = rings[i], rings[i + 1]
        for j in range(9):
            try:
                bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
            except ValueError:
                pass


def _intakes(bm):
    """Side-mounted intake fairings. [E].

    NOT boxes -- the first cut extruded literal rectangular blocks and they looked exactly like
    rectangular blocks. These are half-teardrops swept along the fuselage side: a sharp lip at the
    front, swelling aft, fairing back into the body ahead of the wing root.
    """
    for side in (1.0, -1.0):
        rings = []
        steps = 14
        x0, x1 = NOSE_LEN - 0.15, WING_X_LE + 0.35
        for i in range(steps + 1):
            f = i / steps
            x = x0 + f * (x1 - x0)
            # Sharp at the lip, fullest at ~60%, faired out at the wing root.
            bulge = math.sin(min(f * 1.25, 1.0) * math.pi) ** 0.6
            r = 0.30 * bulge + 0.02
            y_c = -side * (FUS_FWD_W + 0.16 * bulge)
            ring = []
            for j in range(9):
                th = -math.pi / 2 + math.pi * j / 8.0     # outboard half only; inboard side is the fuselage
                ring.append(bm.verts.new(Vector((x,
                                                 y_c - side * r * 0.75 * math.cos(th),
                                                 -0.02 + r * math.sin(th)))))
            rings.append(ring)
        for i in range(steps):
            a, b = rings[i], rings[i + 1]
            for j in range(8):
                try:
                    f4 = (a[j], a[j + 1], b[j + 1], b[j]) if side > 0 else (a[j], b[j], b[j + 1], a[j + 1])
                    bm.faces.new(f4)
                except ValueError:
                    pass


# ─── Assembly ─────────────────────────────────────────────────────────────────────────────────────
def build_airframe(name: str) -> bpy.types.Object:
    bm = bmesh.new()

    _fuselage(bm)
    _canopy(bm)
    _intakes(bm)

    # Wing — positioned by its published quarter-chord line.
    _panel(bm, WING_X_LE + 0.25 * ROOT_CHORD, SPAN / 2.0, ROOT_CHORD, TIP_CHORD,
           SWEEP_C4, THICKNESS, dihedral=0.0, z0=WING_Z)
    _tip_rails(bm)

    # Horizontal tail — all-moving, and it droops 4 degrees.
    ht_exposed_span = math.sqrt(2.88 * 3.07)                       # 2.97 m, from NASA's exposed AR
    ht_root = HT_TIP_CHORD / HT_TAPER                              # 1.539 m at the fuselage side
    # Extrapolate the taper line inboard to the centreline so the surface meets the fuselage.
    f_side = (FUS_TAIL_W) / (HT_SPAN / 2.0)
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
    anchor.location = ((CANOPY_X0 + CANOPY_X1) / 2.0 - 0.35, 0.0, FUS_MAX_H * 0.55)
    bpy.context.collection.objects.link(anchor)
    _export(out / f"{aid}_cockpit.glb", [anchor])

    print(f"\n  {aid}: {tris} faces")
    print(f"  wrote {aid}.glb (+ _b), _lod0/1/2, _shadow, _cockpit -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
