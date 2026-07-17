#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Parametric Northrop N-156 airframe-family builder.

The F-5A/B/E/F Freedom Fighter / Tiger II and the T-38 Talon are the SAME Northrop N-156 airframe
family: one slender area-ruled fuselage with lateral cheek intakes, twin GE J85 nozzles, a small
low-mid trapezoidal wing, an all-moving anhedral stabilator and a single fin. This module holds the
authored GEOMETRY ALGORITHM ONCE; each aircraft supplies only DATA (an `N156Config` of published
dimensions). See `aircraft/f5e/f5e_build.py` (the first user, single-seat, armed) and
`aircraft/t38a/t38a_build.py` (two-seat trainer, unarmed, no tip rails) — the algorithm below is
byte-identical to the F-5E's original monolithic build script; it was extracted, not rewritten.

Emits, per docs/modding/3d-models.md:
    <id>.glb          base mesh; root node `<id>`, damage-state node `<id>_b`
    <id>_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    <id>_shadow.glb   convex hull, no materials
    <id>_cockpit.glb  contains the node `camera_anchor`

═══════════════════════════════════════════════════════════════════════════════════════════════════
CONVENTIONS (docs/modding/3d-models.md — get these wrong and validate-mesh rejects the file)
═══════════════════════════════════════════════════════════════════════════════════════════════════
  * Engine BODY axes: +X forward (nose), +Y up, +Z starboard, metres. But content is AUTHORED in the
    standard glTF convention (nose along glTF +Z) and the engine rotates it +Z -> +X on import
    (engine#906). Blender's glTF exporter maps Blender +X -> glTF +X, Blender +Z -> glTF +Y,
    Blender -Y -> glTF +Z. The parametric loft is nose-along-Blender-+X; build_airframe applies a
    +90-deg yaw so the nose ends at Blender -Y == glTF +Z. Do not "fix" this.
  * Winding CCW from outside, normals outward. The opaque pipeline is single-sided; an inside-out
    face is invisible from the outside and validate-mesh errors on it.
  * Node and material names: lowercase with underscores. No hyphens, no spaces, no uppercase.
  * NO EMBEDDED IMAGE DATA. Textures are external .ktx2 URIs, pre-wired here so the references exist
    before tex-compress has ever run.

═══════════════════════════════════════════════════════════════════════════════════════════════════
DATA vs SHARED CODE
═══════════════════════════════════════════════════════════════════════════════════════════════════
Everything below the `N156Config` dataclass is SHARED CODE — the algorithm. Every number that
distinguishes one N-156 variant from another lives in `N156Config`, supplied by the per-aircraft
`<id>_build.py`. Low-level SHAPE constants that define the family "look" (superellipse ring
resolution, canopy width falloff coefficients, nozzle geometry, pitot radii) stay hardcoded here:
they are family-invariant. Where the F-16A copy-and-adapt build proved a constant genuinely varies
per airframe (the forebody superellipse ramp), it is promoted to a config field.
"""

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# bpy must be imported before bmesh/mathutils: under the pip `bpy` wheel (used by the determinism
# CI job) importing bmesh first raises ModuleNotFoundError, because bpy's init registers the sibling
# modules. The Blender binary does not care about order; the wheel does.
import bpy
import bmesh
from mathutils import Matrix, Vector

# Shared procedural-mesh helpers. The library lives in the repo, not on Blender's Python path, so
# add it from THIS file's location (tools/aircraftlib/src/fl_aircraftlib/ -> repo root ->
# tools/meshlib/src). The per-aircraft build script adds it too; adding it here as well keeps this
# module importable on its own. No install step; works under `blender --background`.
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))
from fl_meshlib import export, loft, scene, uvatlas  # noqa: E402
from fl_meshlib.curves import smoothstep as _smoothstep  # noqa: E402
from fl_meshlib.damage import battle_damage  # noqa: E402
from fl_meshlib.stations import interp_table  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# N156Config — the per-aircraft DATA. Every field is a published dimension or an [E] shaping value;
# provenance for each lives in the calling <id>_build.py and its SOURCES.md, not here.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True, kw_only=True)
class N156Config:
    # ── Identity / appearance ──
    aircraft_id: str
    mat_skin: str
    tex_diffuse: str
    tex_orm: str
    base_color: tuple = (0.42, 0.44, 0.47, 1.0)
    mat_metallic: float = 0.15
    mat_roughness: float = 0.55

    # ── Overall ──
    length: float                       # m, overall
    span: float                         # m, wing span (without tip missiles)
    wing_area: float                    # m^2 (provenance/assert only; the loft does not read it)

    # ── Wing ──
    root_chord: float
    tip_chord: float
    sweep_c4: float                     # deg, quarter-chord sweep
    thickness: float                    # t/c fraction (symmetric section)
    wing_x_le: float                    # m, leading-edge root station
    wing_z: float                       # m, wing vertical placement

    # ── Horizontal tail (all-moving) ──
    ht_span: float
    ht_tip_chord: float
    ht_taper: float
    ht_sweep_c4: float
    ht_dihedral: float                  # deg (negative = anhedral)
    ht_x_c4: float
    ht_z0: float = 0.10

    # ── Vertical tail ──
    vt_tip_chord: float
    vt_taper: float
    vt_sweep_c4: float
    vt_area: float                      # m^2 exposed
    vt_ar: float                        # on the exposed span
    vt_x_c4: float
    vt_z0: float = 0.55

    tail_thickness: float = 0.04        # t/c for both tail surfaces

    # ── Fuselage (traced side-view station table) ──
    #   each station: (x/L, z_upper, z_lower, y_half), metres full scale
    stations_fus: list = field(default_factory=list)
    nose_blend_t: float = 0.16          # x/L radome (circular) -> traced forebody
    sill_ease: float = 2.2              # cockpit-sill ease-in exponent (see _spine_top)
    fus_n0: float = 2.05                # forebody superellipse: n = fus_n0 + fus_dn*smoothstep(t/fus_n_ramp)
    fus_dn: float = 0.4
    fus_n_ramp: float = 0.25
    pitot_len: float = 0.55             # m, nose boom (0.0 to omit)
    nozzle_r: float = 0.28              # m, one J85 nozzle radius

    # ── Canopy ──
    canopy_span: tuple                  # (x/L start, x/L end) where z_up is glass, not spine
    canopy_halfw: float                 # m, canopy plan half-width
    windscreen_f: float = 0.14          # fraction of the canopy span the windscreen occupies

    # ── Lateral air intakes ──
    intake_x0: float                    # x/L cowl lip
    intake_x1: float                    # x/L where the fairing has faded into the flank
    intake_zc: float                    # m, aperture centre above the reference line
    intake_hz: float                    # m, aperture half-height
    intake_hy: float                    # m, cowl half-width
    intake_proud: float                 # m, how far the lip stands proud of the flank
    intake_depth: float                 # m, how far the inlet face is recessed behind the lip

    # ── Wingtip rails (airframe on the armed variants; absent on the trainer) ──
    tip_rails: bool = True
    tip_rail_len: float = 2.10          # m

    # ── Cockpit camera anchor placement ──
    cockpit_span_frac: float = 0.35     # into the canopy span
    cockpit_z_station: float = 0.30     # x/L used for the anchor's z reference
    cockpit_z_drop: float = 0.25        # m below that station's spine

    # ── Hardpoint marker layout (metadata nodes; None = unarmed, no markers) ──
    hardpoint_markers: Optional[Callable[["N156Config"], list]] = None


# ─── Fuselage station lookup ────────────────────────────────────────────────────────────────────
def _fus_at(cfg, t):
    """Interpolate the traced station table at x/L = t. Returns (z_up, z_lo, y_half)."""
    return interp_table(cfg.stations_fus, t)


def _spine_top(cfg, t):
    """The fuselage TOP at x/L = t, i.e. z_up with the canopy glass excluded.

    Inside the canopy span the traced z_up is the glass, not the skin; the skin is the smooth
    line between the windshield base and the aft fairing, so blend linearly across the span.
    The canopy bubble is then built separately, exactly as tall as the difference.
    """
    c0, c1 = cfg.canopy_span
    z_up, _, _ = _fus_at(cfg, t)
    if t <= c0 or t >= c1:
        return z_up
    a = _fus_at(cfg, c0)[0]
    b = _fus_at(cfg, c1)[0]

    # NOT linear. A straight ramp from the windshield base to the aft fairing climbs at the same
    # rate as the glass above it, so the canopy never stands proud -- the loft produced one long
    # flat-topped ridge merging into the spine, with no bubble and no windscreen. The real skin
    # stays low along the cockpit sill and only rises BEHIND the cockpit, into the dorsal decking
    # ahead of the intakes. Ease-in does that: slow under the canopy, steep at the aft end, and it
    # still meets the traced skin exactly at both ends -- so no traced value is overridden, only
    # the curve BETWEEN them.
    return a + (b - a) * ((t - c0) / (c1 - c0)) ** cfg.sill_ease


def _nose_section(cfg, t, top, lo, w):
    """Section centre and half-height at x/L = t, with the RADOME treated as a body of revolution.

    The raw trace disagrees with itself at the nose: near the tip the plan-view half-width and the
    side-view contour were sampled independently and do not agree, where both are a few pixels of
    ink. A radome CANNOT be a blade -- it is a fairing over a circular antenna (or, on the trainer,
    a slender ogive), so its sections are circular. In the radome region the half-height is taken
    from the traced PLAN half-width (the more trustworthy of the two near the tip), and the section
    centre rides a smooth droop line from the tip. By nose_blend_t the fuselage is deep and
    genuinely non-circular and the trace is trusted fully again. Between the two, blend.
    """
    cz_tr = (top + lo) / 2.0
    hh_tr = max((top - lo) / 2.0, 0.02)
    if t >= cfg.nose_blend_t:
        return cz_tr, hh_tr

    top_b = _spine_top(cfg, cfg.nose_blend_t)
    lo_b = _fus_at(cfg, cfg.nose_blend_t)[1]
    cz_rd = ((top_b + lo_b) / 2.0) * (t / cfg.nose_blend_t)   # droop: 0 at tip -> traced centreline
    hh_rd = max(w, 0.02)                                      # circular: half-height = half-width

    u = _smoothstep(t / cfg.nose_blend_t)
    return cz_rd + (cz_tr - cz_rd) * u, hh_rd + (hh_tr - hh_rd) * u


def _fuselage(cfg, bm, sections=44):
    """Loft the traced side-view stations into a superellipse-section body.

    Cross-section: superellipse spanning [z_lo, spine_top] with the traced half-width. The
    section is asymmetric top-to-bottom exactly as the drawing is -- centreline and half-height
    fall out of the traced upper/lower contours; nothing here is shaped by eye any more except
    the superellipse roundness itself.
    """
    rings = []
    for i in range(sections + 1):
        t = i / sections
        x = t * cfg.length
        top = _spine_top(cfg, t)
        _, lo, w = _fus_at(cfg, t)
        w = max(w, 0.02)
        cz, hh = _nose_section(cfg, t, top, lo, w)
        n = cfg.fus_n0 + cfg.fus_dn * _smoothstep(t / cfg.fus_n_ramp)  # round nose, flatter body
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

    # Pitot boom -- visible on the 3-view, part of the silhouette.
    if cfg.pitot_len > 0.0:
        pb = []
        for i in range(2):
            x = -cfg.pitot_len + i * cfg.pitot_len
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


def _nozzles(cfg, bm):
    """Twin J85 nozzles, from the front view: two abreast at the tail.

    Built into their own face group so they can carry the dark burnt-metal material slot, separate
    from the skin. The vertices are exactly those the fuselage loft used to emit -- moving them here
    changes no geometry, only which material they answer to.
    """
    for side in (1.0, -1.0):
        y0 = -side * 0.30
        prev = None
        for i in range(4):
            f = i / 3.0
            x = cfg.length - 0.30 + f * 0.30
            r = cfg.nozzle_r * (1.0 - 0.15 * f)
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


def _intake_section(cfg, t, steps=12):
    """Cross-section of the intake cowl at x/L = t: (centre_y, centre_z, half_y, half_z).

    The cowl hugs the flank. Its OUTER surface sits `intake_proud` beyond the traced half-width at
    the lip and fades back to flush by intake_x1; its inboard half is buried inside the fuselage.
    """
    w = _fus_at(cfg, t)[2]                                   # traced fuselage half-width here
    fade = 1.0 - _smoothstep((t - cfg.intake_x0) / (cfg.intake_x1 - cfg.intake_x0))
    outer = w + cfg.intake_proud * fade
    hy = cfg.intake_hy
    hz = cfg.intake_hz * (0.35 + 0.65 * fade)               # tall at the lip, faded into the flank aft
    return outer - hy, cfg.intake_zc, hy, max(hz, 0.02)


def _intake_ring(cfg, bm, t, side, scale=1.0, dx=0.0, steps=12):
    """One rounded-rectangle ring of the cowl, on `side` (+1 port, -1 starboard in Blender -Y)."""
    cy, cz, hy, hz = _intake_section(cfg, t)
    x = t * cfg.length + dx
    ring = []
    for j in range(steps):
        th = 2.0 * math.pi * j / steps
        c, sn = math.cos(th), math.sin(th)
        n = 3.2                                              # rounded rectangle, like the real lip
        y = hy * scale * math.copysign(abs(c) ** (2.0 / n), c)
        z = hz * scale * math.copysign(abs(sn) ** (2.0 / n), sn)
        ring.append(bm.verts.new(Vector((x, side * (cy + y), cz + z))))
    return ring


def _intakes(cfg, bm, stations=7):
    """Lateral inlets: a cowl lofted along the flank, with a recessed aperture behind a sharp lip.

    Built per side as a closed solid that overlaps the fuselage. Two pieces meet at the lip ring:
      * the OUTER shell, lofted aft from the lip until it is buried in the flank at intake_x1;
      * the RECESS, stepping inward and aft from that same lip ring to a capped throat -- the dark
        hole. Without it the lip is just a raised panel line and the jet still reads wrong.
    """
    for side in (1.0, -1.0):
        flip = side < 0.0                                    # mirrored side needs reversed winding
        lip = _intake_ring(cfg, bm, cfg.intake_x0, side)

        # Outer shell: lip -> aft, fading into the flank.
        prev = lip
        for i in range(1, stations + 1):
            t = cfg.intake_x0 + (cfg.intake_x1 - cfg.intake_x0) * (i / stations)
            ring = _intake_ring(cfg, bm, t, side)
            loft.bridge(bm, prev, ring, flip)
            prev = ring
        try:                                                 # aft cap: buried in the fuselage, unseen
            bm.faces.new(prev if not flip else list(reversed(prev)))
        except ValueError:
            pass

        # Recess: the same lip ring, stepped in and aft to a throat, then capped. Winding is the
        # opposite of the outer shell -- these faces are seen from IN FRONT, looking into the duct.
        throat = _intake_ring(cfg, bm, cfg.intake_x0, side, scale=0.72, dx=cfg.intake_depth)
        loft.bridge(bm, lip, throat, not flip)
        try:
            bm.faces.new(list(reversed(throat)) if not flip else throat)
        except ValueError:
            pass


def _tip_rails(cfg, bm):
    """Wingtip AIM-9 launch rails. Part of the AIRFRAME, not a store (armed variants only).

    On the F-5E the T.O. quotes max level Mach for "launcher rails only" AND "with tip missiles", so
    the rails are present in both published conditions -- they belong to the aeroplane. The trainer
    has none.
    """
    y_tip = cfg.span / 2.0
    x_c4_tip = cfg.wing_x_le + 0.25 * cfg.root_chord + (cfg.span / 2.0) * math.tan(math.radians(cfg.sweep_c4))
    x0 = x_c4_tip - 0.25 * cfg.tip_chord - 0.55
    for side in (1.0, -1.0):
        y = -side * y_tip
        rings = []
        for i in range(7):
            f = i / 6.0
            x = x0 + f * cfg.tip_rail_len
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


def _canopy(cfg, bm):
    """Canopy glass: exactly the bump the trace measured -- z_up minus the blended spine.

    Width is the one [E] left in the canopy: the planform outline reads the canopy_halfw half-width.
    A tandem two-seat canopy is expressed purely by a longer canopy_span and its traced z_up: the
    single-lobe plan profile below rises at the windscreen, holds near-full width through the
    cockpit(s), then tapers into the aft fairing -- which reads correctly for both a single bubble
    and a long tandem transparency at this pipeline's silhouette fidelity.
    """
    c0, c1 = cfg.canopy_span
    rings = []
    steps = 14
    for i in range(steps + 1):
        f = i / steps
        t = c0 + f * (c1 - c0)
        x = t * cfg.length
        z_glass = _fus_at(cfg, t)[0]
        z_skin = _spine_top(cfg, t)
        h = max(z_glass - z_skin, 0.0) + 0.02
        # Plan shape: come up to full width fast over the windscreen, hold it through the glass,
        # then taper into the long aft fairing (which does not reach zero -- it fairs into the spine).
        w = cfg.canopy_halfw * _smoothstep(f / cfg.windscreen_f) * (1.0 - 0.80 * _smoothstep((f - 0.70) / 0.30))
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
# ONE material, ONE primitive — DELIBERATELY. glTF splits a mesh into one primitive per material, and
# the engine loads only `meshes[0].primitives[0]` (VkResources.cpp:519) until the node-aware loader
# lands (fighters-legacy#839). A canopy/nozzle material split would move that geometry into
# primitive[1]/[2] and the current engine would simply drop it -- the aircraft would fly with no
# canopy and no nozzles. So the skin/canopy/nozzle split waits behind #839. The material is named
# `<id>_skin` so it is already the liverable slot name a livery will override (fighters-legacy#845).


def build_airframe(cfg, name: str) -> bpy.types.Object:
    bm = bmesh.new()

    _fuselage(cfg, bm)
    _intakes(cfg, bm)
    _canopy(cfg, bm)

    # Wing — positioned by its published quarter-chord line.
    loft.panel(bm, cfg.wing_x_le + 0.25 * cfg.root_chord, cfg.span / 2.0, cfg.root_chord, cfg.tip_chord,
               cfg.sweep_c4, cfg.thickness, dihedral=0.0, z0=cfg.wing_z)
    if cfg.tip_rails:
        _tip_rails(cfg, bm)

    # Horizontal tail — all-moving, and it droops.
    ht_root = cfg.ht_tip_chord / cfg.ht_taper                     # chord at the fuselage side
    # Extrapolate the taper line inboard to the centreline so the surface meets the fuselage.
    w_tail = _fus_at(cfg, cfg.ht_x_c4 / cfg.length)[2]
    f_side = w_tail / (cfg.ht_span / 2.0)
    ht_c0 = (ht_root - cfg.ht_tip_chord * f_side) / (1.0 - f_side)
    loft.panel(bm, cfg.ht_x_c4, cfg.ht_span / 2.0, ht_c0, cfg.ht_tip_chord, cfg.ht_sweep_c4, cfg.tail_thickness,
               dihedral=cfg.ht_dihedral, z0=cfg.ht_z0)

    # Vertical tail — from exposed AR and exposed area.
    vt_height = math.sqrt(cfg.vt_ar * cfg.vt_area)
    vt_root = cfg.vt_tip_chord / cfg.vt_taper
    loft.panel(bm, cfg.vt_x_c4, vt_height, vt_root, cfg.vt_tip_chord, cfg.vt_sweep_c4, cfg.tail_thickness,
               vertical=True, z0=cfg.vt_z0)

    # Twin J85 nozzles: their own function (a group for the future material split), but built into
    # the same bmesh, so the geometry is unchanged.
    _nozzles(cfg, bm)

    # AUTHORING FORWARD IS glTF +Z (engine#906): a content mesh is authored in the standard
    # glTF/Blender convention (nose along Blender's forward, -Y, which the exporter emits as +Z),
    # and the engine rotates it +Z -> +X into its body frame on import. The fuselage is laid out
    # nose-at-origin extending +X (parametric convenience), which points the NOSE down -X, so a
    # +90-deg yaw about Blender Z turns the nose to Blender -Y == glTF +Z. It is a ROTATION, not a
    # mirror, so winding is preserved.
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), verts=bm.verts,
                     matrix=Matrix.Rotation(math.pi / 2.0, 4, 'Z'))

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)               # outward: CCW from outside
    return _commit(cfg, bm, name)


def _fwd(loc):
    """Match an empty's position to the airframe's nose-to-glTF-+Z yaw (+90 deg about Z, engine#906):
    (x,y,z)->(-y, x, z)."""
    x, y, z = loc
    return (-y, x, z)


def _commit(cfg, bm, name: str) -> bpy.types.Object:
    """Finish the airframe bmesh into an object with the single skin material and placeholder UVs."""
    obj = scene.finish_mesh(bm, name)
    scene.principled_material(obj, cfg.mat_skin, cfg.base_color, cfg.mat_metallic, cfg.mat_roughness)
    uvatlas.planar_uvs(obj, cfg.length, cfg.span)
    return obj


def fighter_hardpoint_markers(cfg) -> list:
    """Marker empties for the N-156 fighter's 7 hardpoints (F-5A/B/E/F), positioned FROM the airframe
    geometry (not by eye): one nose gun, two wingtip rails, four underwing pylons.

    Exported as glTF nodes with `extras`; the engine ignores them today (fighters-legacy#844). They
    are forward-compatible metadata whose positions are derived from the same wing/nose constants
    that build the aircraft, so they track the geometry rather than floating free of it. Port is +Y,
    starboard is -Y (see the header's axis note). The trainer variants pass no marker function.
    """
    marks = []
    # Slot 0 — nose cannon, centreline, just under the upper nose line.
    marks.append(scene.empty(f"hardpoint_0", location=_fwd((0.14 * cfg.length, 0.0, _fus_at(cfg, 0.14)[0] - 0.10)),
                             extras={"fl_marker": "hardpoint", "fl_slot": 0, "fl_type": "gun"}))
    # Slots 1,2 — wingtip missile rails (1 = left/port +Y, 2 = right/starboard -Y).
    x_c4_tip = cfg.wing_x_le + 0.25 * cfg.root_chord + (cfg.span / 2.0) * math.tan(math.radians(cfg.sweep_c4))
    x_tip = x_c4_tip - 0.25 * cfg.tip_chord + 0.30
    for slot, sgn in ((1, 1.0), (2, -1.0)):
        marks.append(scene.empty(f"hardpoint_{slot}", location=_fwd((x_tip, sgn * cfg.span / 2.0, 0.0)),
                                 extras={"fl_marker": "hardpoint", "fl_slot": slot, "fl_type": "missile"}))
    # Slots 3-6 — underwing pylons (outboard/inboard each side), at 40% chord, below the wing.
    for slot, sgn, s in ((3, 1.0, 0.55), (4, 1.0, 0.32), (5, -1.0, 0.32), (6, -1.0, 0.55)):
        yhalf = s * cfg.span / 2.0
        x_le = cfg.wing_x_le + yhalf * math.tan(math.radians(cfg.sweep_c4))
        chord = cfg.root_chord + (cfg.tip_chord - cfg.root_chord) * s
        marks.append(scene.empty(f"hardpoint_{slot}", location=_fwd((x_le + 0.40 * chord, sgn * yhalf, cfg.wing_z - 0.25)),
                                 extras={"fl_marker": "hardpoint", "fl_slot": slot, "fl_type": "bomb"}))
    return marks


def main(cfg) -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"aircraft/{cfg.aircraft_id}")
    ap.add_argument("--blend", metavar="PATH",
                    help="also save a Blender project for artist polish (never committed for a "
                         "generated aircraft; not byte-stable). Open it to unwrap UVs, repaint, or "
                         "sculpt, then re-export per docs/CONTRIBUTING.")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    aid = cfg.aircraft_id

    scene.clear_scene()
    body = build_airframe(cfg, aid)
    tris = len(body.data.polygons)

    # Base mesh + its damage state + hardpoint markers, in ONE file. The `_b` node MUST ship beside
    # its base; the marker empties are metadata nodes the engine currently ignores.
    dmg = battle_damage(body)                       # inherit the airframe's skin/canopy/nozzle slots
    markers = cfg.hardpoint_markers(cfg) if cfg.hardpoint_markers else []
    export.export_glb(out / f"{aid}.glb", [body, dmg, *markers])
    export.patch_textures(out / f"{aid}.glb", cfg.tex_diffuse, cfg.tex_orm)
    bpy.data.objects.remove(dmg)

    # LODs are separate FILES, not nodes.
    for i, ratio in enumerate((0.50, 0.20, 0.05)):
        lod = export.decimate(body, ratio, f"{aid}_lod{i}")
        export.export_glb(out / f"{aid}_lod{i}.glb", [lod])
        export.patch_textures(out / f"{aid}_lod{i}.glb", cfg.tex_diffuse, cfg.tex_orm)
        bpy.data.objects.remove(lod)

    # Shadow proxy: convex hull, NO materials.
    shadow = scene.convex_hull(body, f"{aid}_shadow")
    export.export_glb(out / f"{aid}_shadow.glb", [shadow])

    # Cockpit: must contain a node named exactly `camera_anchor` -- the renderer looks for it by name.
    anchor = scene.empty("camera_anchor", location=_fwd((
        (cfg.canopy_span[0] + cfg.cockpit_span_frac * (cfg.canopy_span[1] - cfg.canopy_span[0])) * cfg.length,
        0.0, _fus_at(cfg, cfg.cockpit_z_station)[0] - cfg.cockpit_z_drop)))
    export.export_glb(out / f"{aid}_cockpit.glb", [anchor])

    if args.blend:
        # Artist handoff: the airframe, its markers, the shadow proxy and the camera anchor, in an
        # editable project. Not committed for a generated aircraft.
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.blend).resolve()))
        print(f"  wrote Blender project -> {args.blend}")

    print(f"\n  {aid}: {tris} faces")
    print(f"  wrote {aid}.glb (+ _b, +{len(markers)} hardpoint markers), _lod0/1/2, _shadow, _cockpit -> {out}")
    return 0


def run_cli(cfg) -> None:
    """Standard __main__ epilogue shared by every N-156 build script: run headless-aware, and when
    a GUI is attached leave the scene open but hide the shadow hull and camera anchor for viewing."""
    rc = main(cfg)
    if bpy.app.background:
        sys.exit(rc)          # headless (CI / --background): exit code matters
    for o in bpy.context.scene.objects:
        if o.name.endswith("_shadow") or o.name == "camera_anchor":
            o.hide_set(True)
