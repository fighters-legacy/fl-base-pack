#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Parametric Rockwell B-1 airframe-family builder.

The B-1A and B-1B share one airframe: a long blended wing-body with a fixed glove, variable-sweep
outer panels, four engines in two underslung nacelle pairs, and a cruciform tail. This module holds
the authored GEOMETRY ALGORITHM once; each aircraft supplies only DATA (a `B1Config` of published
dimensions). See `aircraft/b1b/b1b_build.py` — the only user today.

It is a SIBLING of `n156.py`, not a derivative: nothing about a slender area-ruled fighter fuselage
with cheek intakes and a trapezoidal wing carries over to a blended body with swing wings. The
conventions below are shared; the geometry is not.

Emits, per docs/modding/3d-models.md:
    <id>.glb          base mesh; root node `<id>`, damage-state node `<id>_b`, animated wing nodes
    <id>_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    <id>_shadow.glb   convex hull, no materials
    <id>_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
THE SWING WING — the first articulated mesh in this pack
═══════════════════════════════════════════════════════════════════════════════════════════════════
No pack aircraft before this one authored an animation clip at all, so the engine's `sweep` channel
has never had a content-side consumer. The contract (docs/modding/3d-models.md, "Animation
channels"): the clip's NAME is the channel name, the runtime SCRUBS it at t = value x duration, and
for `sweep` the value is 0 at `[wing_sweep] min_deg` and 1 at `max_deg`. So this build emits ONE
NLA track called `sweep` holding a two-keyframe rotation of the two outer panels — nothing plays it,
the flight model's sweep state indexes it.

The outer panels are therefore SEPARATE OBJECTS parented to the airframe, with their origins at the
wing pivot. Everything else is one mesh.

═══════════════════════════════════════════════════════════════════════════════════════════════════
CONVENTIONS (docs/modding/3d-models.md — get these wrong and validate-mesh rejects the file)
═══════════════════════════════════════════════════════════════════════════════════════════════════
  * Authored nose along Blender +X, then a +90-deg yaw about Z puts the nose at Blender -Y, which
    the exporter emits as glTF +Z; the engine rotates +Z -> +X on import (engine#906). A sweep
    rotation is also about Z, and rotations about a common axis commute, so animating the panel
    objects about their own Z after the mesh data has been yawed gives exactly the same result as
    sweeping first and yawing after. Do not "fix" this.
  * `panel()`'s axes: nose +X, up +Z, **starboard -Y**.
  * Winding CCW from outside, normals outward; the opaque pipeline is single-sided.
  * Node and material names: lowercase with underscores.
  * NO EMBEDDED IMAGE DATA — external .ktx2 URIs only.
"""

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

# bpy before bmesh/mathutils — see the note in n156.py; the pip `bpy` wheel needs this order.
import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "meshlib" / "src"))
from fl_meshlib import damage, export, loft, scene  # noqa: E402
from fl_meshlib.airfoil import naca_symmetric  # noqa: E402
from fl_meshlib.stations import interp_table  # noqa: E402


@dataclass
class B1Config:
    """Published dimensions for one B-1 variant. Everything here is [P] unless marked."""

    ident: str
    length: float               # m  overall
    span_spread: float          # m  wings at min sweep
    span_swept: float           # m  wings at max sweep
    height: float               # m  overall
    sweep_min: float            # deg
    sweep_max: float            # deg

    # Wing pivot: y offset from the centreline. [E] — not published; chosen at the glove/panel
    # junction visible in the PD planform photographs. It must sit OUTBOARD of the fuselage
    # half-width at that station, or the glove is buried inside the body and the aircraft renders
    # as a plain tube with wings — which is exactly what a pivot of 3.5 m against a 5.75 m body
    # half-width produced. The panel length and its built-in span-axis
    # angle are then DERIVED from it so that BOTH published spans are reproduced (see _wing_solve).
    pivot_y: float = 6.0
    pivot_x_frac: float = 0.44  # [E] pivot station as a fraction of length
    panel_root_c: float = 6.2   # m  [E] outer-panel root chord
    panel_tip_c: float = 2.0    # m  [E] outer-panel tip chord
    panel_thick: float = 0.09   # t/c [E]
    # Extra leading-edge rake ON TOP of the span-axis angle phi — without it the spread wing
    # renders as a straight plank rather than the swept panel the photographs show. It is NOT
    # geometrically free: _wing_solve has to account for it, or the swept span comes out wrong.
    panel_extra_sweep: float = 13.0   # deg [E]

    glove_root_c: float = 19.0  # m  [E] fixed glove root chord
    glove_sweep: float = 60.0   # deg [E] glove leading-edge sweep
    glove_thick: float = 0.10

    # Cruciform tail. All [E] — the B-1's tail areas are not published anywhere public.
    vt_area: float = 50.0
    vt_ar: float = 1.6
    vt_taper: float = 0.35
    vt_sweep_c4: float = 45.0
    vt_x_c4_frac: float = 0.80
    ht_span: float = 13.7
    ht_taper: float = 0.35
    ht_sweep_c4: float = 40.0
    ht_x_c4_frac: float = 0.90
    ht_dihedral: float = -5.0
    tail_thick: float = 0.07

    # Nacelle pairs, under the glove. [E] from the PD planform and front-view photographs.
    nac_y: float = 2.85         # m  centre of each pair, from the centreline
    nac_x0_frac: float = 0.46
    nac_len: float = 11.0
    nac_w: float = 3.60         # m  full width of a pair
    nac_h: float = 2.05
    nac_z: float = -1.9

    cockpit_x_frac: float = 0.115
    cockpit_z: float = 1.35

    # Fuselage stations: (x/L, z_up, z_lo, y_half). [E] — shaped to the published length, height
    # and the span/glove blend visible in the reference photographs. Nothing the flight model
    # consumes comes from here.
    stations: list = field(default_factory=lambda: [
        (0.000, 0.10, -0.10, 0.06),
        (0.030, 0.70, -0.65, 0.75),
        (0.075, 1.25, -1.05, 1.40),
        (0.130, 1.70, -1.30, 1.95),
        (0.200, 1.85, -1.50, 2.30),
        (0.300, 1.95, -1.70, 3.05),
        (0.400, 2.00, -1.85, 3.70),
        (0.470, 2.00, -2.00, 3.95),
        (0.550, 1.95, -2.05, 3.90),
        (0.640, 1.85, -1.90, 3.35),
        (0.730, 1.70, -1.65, 2.55),
        (0.820, 1.60, -1.35, 1.95),
        (0.910, 1.45, -1.10, 1.35),
        (1.000, 1.00, -0.60, 0.35),
    ])


def _wing_solve(cfg):
    """Derive the outer panel's length and built-in span-axis angle from the two published spans.

    The naive model — a panel perpendicular to the fuselage at minimum sweep, rotating by
    (sweep_max - sweep_min) — CANNOT reproduce both published spans: it demands a pivot at
    y = -1.72 m, i.e. behind the centreline. The panel's span axis is already angled aft at the
    spread position, so with pivot p, panel length L and span-axis angle phi:

        p + L*cos(phi)          = span_spread / 2
        p + L*cos(phi + dsweep) = span_swept  / 2

    Two equations, and with p chosen from the photographs the remaining two solve exactly.

    ⚠ THE EXTRA LEADING-EDGE RAKE IS NOT FREE, despite the obvious argument that span depends only
    on the panel's lateral extent. It is free at the SPREAD position, and that is what makes the
    claim so tempting — but the rake moves the tip AFT, and an aft tip rotates to a different
    lateral position under sweep. Ignoring it built a 41.758 m / 18.5 m aircraft against a published
    41.758 / 24.079. So the tip's post-rotation lateral position is solved directly:

        y'(theta) = L*(sin(phi) + cos(phi)*tan(eps))*sin(theta) - L*cos(phi)*cos(theta)

    with |y'(0)| = a and |y'(dsweep)| = b, where a and b are the two published semi-spans less the
    pivot. Solving for L*sin(phi) and dividing by L*cos(phi) = a gives phi in closed form.
    """
    d = math.radians(cfg.sweep_max - cfg.sweep_min)
    eps = math.radians(cfg.panel_extra_sweep)
    a = cfg.span_spread / 2.0 - cfg.pivot_y
    b = cfg.span_swept / 2.0 - cfg.pivot_y
    l_sin = (a * (math.cos(d) - math.tan(eps) * math.sin(d)) - b) / math.sin(d)
    phi = math.atan2(l_sin, a)
    length = a / math.cos(phi)
    return length, math.degrees(phi)


def _ring(bm, x, z_up, z_lo, y_half, steps=16, power=2.4):
    """One superellipse fuselage station ring, returned as a closed vertex loop.

    A superellipse (not an ellipse) because the B-1's blended body is markedly flat-sided and
    flat-bottomed through the weapons-bay section — an ellipse there reads as a tube.
    """
    verts = []
    for i in range(steps):
        a = 2.0 * math.pi * i / steps
        c, s = math.cos(a), math.sin(a)
        y = y_half * math.copysign(abs(c) ** (2.0 / power), c)
        z = (z_up if s >= 0 else -z_lo) * math.copysign(abs(s) ** (2.0 / power), s)
        verts.append(bm.verts.new(Vector((x, y, z))))
    return verts


def _fuselage(cfg, bm):
    rings = []
    for (t, z_up, z_lo, y_half) in cfg.stations:
        rings.append(_ring(bm, t * cfg.length, z_up, z_lo, y_half))
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                bm.faces.new((a[j], b[j], b[k], a[k]))
            except ValueError:
                pass
    for cap, rev in ((rings[0], True), (rings[-1], False)):
        try:
            bm.faces.new(list(reversed(cap)) if rev else cap)
        except ValueError:
            pass


def _glove(cfg, bm):
    """The FIXED inner wing. It does not move with sweep, which is why it is in the body mesh.

    Its TIP chord must COINCIDE with the outer panel's ROOT chord, or the two simply do not meet and
    the aircraft carries a gap at the pivot — 5.3 m of it, when the glove was positioned from its own
    leading edge instead. `panel()` positions by quarter-chord and the outer panel's root
    quarter-chord sits exactly at the pivot, so the glove's root quarter-chord is worked BACK from
    the pivot along the sweep line. Then the glove's tip chord is `panel_root_c` centred on the
    pivot, which is the outer panel's root chord exactly, and the surfaces are continuous at every
    sweep angle because the panel rotates about that shared chord.
    """
    semi = cfg.pivot_y + 0.35
    x_c4_root = cfg.pivot_x_frac * cfg.length - semi * math.tan(math.radians(cfg.glove_sweep))
    loft.panel(bm, x_c4_root, semi, cfg.glove_root_c, cfg.panel_root_c, cfg.glove_sweep,
               cfg.glove_thick, z0=-0.35)


def _nacelles(cfg, bm):
    """Two underslung pairs, each a flat-sided box-loft with a rounded intake lip and a nozzle."""
    x0 = cfg.nac_x0_frac * cfg.length
    prof = [(0.00, 0.55), (0.10, 1.00), (0.55, 1.00), (0.80, 0.92), (1.00, 0.80)]
    for side in (1.0, -1.0):
        yc = -side * cfg.nac_y
        rings = []
        for (f, scale) in prof:
            x = x0 + f * cfg.nac_len
            hw, hh = 0.5 * cfg.nac_w * scale, 0.5 * cfg.nac_h * scale
            ring = []
            steps = 12
            for i in range(steps):
                a = 2.0 * math.pi * i / steps
                c, s = math.cos(a), math.sin(a)
                y = yc + hw * math.copysign(abs(c) ** 0.7, c)
                z = cfg.nac_z + hh * math.copysign(abs(s) ** 0.7, s)
                ring.append(bm.verts.new(Vector((x, y, z))))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for j in range(n):
                k = (j + 1) % n
                try:
                    f = (a[j], b[j], b[k], a[k]) if side > 0 else (a[j], a[k], b[k], b[j])
                    bm.faces.new(f)
                except ValueError:
                    pass
        for cap, rev in ((rings[0], side > 0), (rings[-1], side < 0)):
            try:
                bm.faces.new(list(reversed(cap)) if rev else cap)
            except ValueError:
                pass


def _tail(cfg, bm):
    vt_h = math.sqrt(cfg.vt_ar * cfg.vt_area)
    vt_root = math.sqrt(cfg.vt_area / cfg.vt_ar) / ((1.0 + cfg.vt_taper) / 2.0)
    loft.panel(bm, cfg.vt_x_c4_frac * cfg.length, vt_h, vt_root, vt_root * cfg.vt_taper,
               cfg.vt_sweep_c4, cfg.tail_thick, vertical=True, z0=1.2)

    ht_root = 4.6
    loft.panel(bm, cfg.ht_x_c4_frac * cfg.length, cfg.ht_span / 2.0, ht_root, ht_root * cfg.ht_taper,
               cfg.ht_sweep_c4, cfg.tail_thick, dihedral=cfg.ht_dihedral, z0=0.9)


def _outer_panel(cfg, side, name):
    """One variable-sweep outer panel as its OWN object, origin at the wing pivot.

    Authored with the panel running outboard along the span axis at the spread position; the object
    is then placed at the pivot and rotated about its own Z by the sweep clip.
    """
    length, phi = _wing_solve(cfg)
    bm = bmesh.new()
    sections, steps = 8, 14
    rings = []
    for i in range(sections + 1):
        f = i / sections
        span_pos = f * length
        chord = cfg.panel_root_c + (cfg.panel_tip_c - cfg.panel_root_c) * f
        # `span_pos` runs along the panel's OWN span axis, which is angled aft by phi — so it
        # decomposes into lateral and streamwise components. Placing the vertices at the full
        # lateral distance instead is the bug that measured 33.3 m swept against a published
        # 24.1 m: it makes the panel longer than _wing_solve solved for, and the sweep rotation
        # then starts from the wrong geometry. Measure the built span before trusting this.
        #
        # +X is AFT here: the fuselage is laid out nose-at-origin extending +X, so the nose points
        # down -X (which the final +90-deg yaw sends to -Y == glTF +Z forward). Angling the tip
        # along -X would rake it FORWARD, and the sweep rotation then UNSWEEPS the panel — the
        # second span bug, measuring 33.0 m where 24.1 m was wanted. Both components below are
        # part of what _wing_solve solved against; changing either without re-deriving breaks the
        # published spans. ALWAYS re-measure the built mesh (see the span check in the PR).
        x = (span_pos * math.sin(math.radians(phi))
             + span_pos * math.cos(math.radians(phi))
             * math.tan(math.radians(cfg.panel_extra_sweep)))
        y = -side * span_pos * math.cos(math.radians(phi))
        ring = []
        for j in range(steps + 1):
            xc = j / steps
            ring.append((x - 0.25 * chord + xc * chord, naca_symmetric(xc, cfg.panel_thick) * chord))
        for j in range(steps - 1, 0, -1):
            xc = j / steps
            ring.append((x - 0.25 * chord + xc * chord, -naca_symmetric(xc, cfg.panel_thick) * chord))
        rings.append([bm.verts.new(Vector((px, y, pz))) for (px, pz) in ring])

    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                f = (a[j], b[j], b[k], a[k]) if side > 0 else (a[j], a[k], b[k], b[j])
                bm.faces.new(f)
            except ValueError:
                pass
    try:
        bm.faces.new(rings[-1] if side > 0 else list(reversed(rings[-1])))
    except ValueError:
        pass

    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), verts=bm.verts,
                     matrix=Matrix.Rotation(math.pi / 2.0, 4, 'Z'))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    obj = scene.finish_mesh(bm, name)
    # Pivot location, carried through the same +90-deg yaw as the geometry.
    px, py = cfg.pivot_x_frac * cfg.length, -side * cfg.pivot_y
    obj.location = Vector((-py, px, -0.35))
    return obj


def build_airframe(cfg, name):
    """Build the body mesh and the two swing-wing panels. Returns (body, [wing_l, wing_r])."""
    bm = bmesh.new()
    _fuselage(cfg, bm)
    _glove(cfg, bm)
    _nacelles(cfg, bm)
    _tail(cfg, bm)

    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), verts=bm.verts,
                     matrix=Matrix.Rotation(math.pi / 2.0, 4, 'Z'))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = scene.finish_mesh(bm, name)
    scene.principled_material(body, "airframe_grey", (0.32, 0.34, 0.36, 1.0), 0.15, 0.55)

    wings = [_outer_panel(cfg, 1.0, f"{name}_wing_r"), _outer_panel(cfg, -1.0, f"{name}_wing_l")]
    for w in wings:
        scene.principled_material(w, "airframe_grey", (0.32, 0.34, 0.36, 1.0), 0.15, 0.55)
        w.parent = body
        w.matrix_parent_inverse = body.matrix_world.inverted()
    return body, wings


def author_sweep_clip(cfg, wings):
    """The `sweep` channel: one NLA track, two keyframes, both panels.

    0 -> min_deg, 1 -> max_deg (docs/modding/3d-models.md). The runtime scrubs this; it never plays
    it, so the frame range is only a parameterisation — frame 0 is spread, frame 1 is fully swept.
    """
    delta = math.radians(cfg.sweep_max - cfg.sweep_min)
    for w in wings:
        # Starboard (-Y in authoring axes) sweeps one way, port the other.
        sign = 1.0 if w.name.endswith("_wing_r") else -1.0
        w.rotation_mode = "XYZ"
        w.animation_data_create()
        action = bpy.data.actions.new(name=f"{w.name}_sweep")
        w.animation_data.action = action
        w.rotation_euler = (0.0, 0.0, 0.0)
        w.keyframe_insert(data_path="rotation_euler", frame=0, index=2)
        w.rotation_euler = (0.0, 0.0, sign * delta)
        w.keyframe_insert(data_path="rotation_euler", frame=1, index=2)
        w.rotation_euler = (0.0, 0.0, 0.0)
        # The exporter names the glTF animation after the NLA TRACK, and the channel contract is
        # that the clip name IS the channel name.
        track = w.animation_data.nla_tracks.new()
        track.name = "sweep"
        track.strips.new("sweep", 0, action)
        w.animation_data.action = None


def main(cfg, argv=None):
    ap = argparse.ArgumentParser(description=f"Build the {cfg.ident} mesh set.")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv if argv is not None else sys.argv[sys.argv.index("--") + 1:])
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    ident = cfg.ident

    scene.clear_scene()
    body, wings = build_airframe(cfg, ident)
    author_sweep_clip(cfg, wings)

    dmg = damage.battle_damage(body, "airframe_grey", seed=7)
    dmg.name = f"{ident}_b"
    dmg.parent = body

    export.export_glb(out / f"{ident}.glb", [body, dmg] + wings, animations=True)
    export.patch_textures(out / f"{ident}.glb", f"../../textures/{ident}_diffuse.ktx2",
                          f"../../textures/{ident}_orm.ktx2")

    for i, ratio in enumerate((0.50, 0.20, 0.05)):
        lod_parts = [export.decimate(body, ratio, f"{ident}_lod{i}")]
        lod_parts += [export.decimate(w, ratio, f"{w.name}_lod{i}") for w in wings]
        # animations=True for the LODs TOO, and not as a nicety. Without it the exporter falls back
        # to its default ACTIONS mode and names each clip after the action — `b1b_wing_l_sweep`
        # rather than `sweep` — which validate-mesh flags as "not a known articulation channel; it
        # will never play". A distant B-1 would then fly with its wings frozen while the near one
        # swept.
        export.export_glb(out / f"{ident}_lod{i}.glb", lod_parts, animations=True)
        export.patch_textures(out / f"{ident}_lod{i}.glb", f"../../textures/{ident}_diffuse.ktx2",
                              f"../../textures/{ident}_orm.ktx2")
        for p in lod_parts:
            bpy.data.objects.remove(p, do_unlink=True)

    hull = scene.convex_hull(body, f"{ident}_shadow")
    export.export_glb(out / f"{ident}_shadow.glb", [hull])

    anchor = scene.empty("camera_anchor",
                         (0.0, -cfg.cockpit_x_frac * cfg.length, cfg.cockpit_z))
    export.export_glb(out / f"{ident}_cockpit.glb", [anchor])
    print(f"{ident}: wrote mesh set to {out}")


def run_cli(cfg):
    main(cfg)
