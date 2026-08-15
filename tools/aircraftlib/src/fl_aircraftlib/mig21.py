#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Parametric Mikoyan MiG-21 airframe-family builder.

The MiG-21 family (F-13, PF/PFM, M/MF, SMT, bis, and the two-seat U/UM) shares one layout: a
circular-section fuselage with a nose intake and translating shock cone, a 57-degree tailed delta,
an all-moving swept stabilator, and a swept fin over a dorsal spine whose PROFILE is the main
thing that changes between variants. This module holds the authored GEOMETRY ALGORITHM once; each
aircraft supplies only DATA (a `Mig21Config` of published dimensions). See
`aircraft/mig21bis/mig21bis_build.py` — the only user today.

It is a SIBLING of `n156.py` and `b1.py`, not a derivative: nothing about a cheek-intake
trapezoidal-wing fighter or a blended swing-wing bomber carries over to a nose-intake tailed
delta. The conventions are shared; the geometry is not.

FAMILY-VARIANT KNOBS (for fl-base-pack#42 and friends, per the one-family-one-builder rule):
the nose length (`nose_stretch` — the F-13 fuselage is 13.46 m, PF-onward 14.10 m, both datum-
checked against the declassified manual; SOURCES.md), the spine profile (`spine_top`, the bis
saddle vs the earlier fairings), the fin (`fin_area`/chords — narrow F-13 4.45 m² vs the wide
5.32 m²), and the canopy stations (a second dome for the U). None of this is speculative
support: the knobs exist because they are exactly what differs between the variants already
filed as issues.

Emits, per docs/modding/3d-models.md:
    <id>.glb          base mesh; root node `<id>`, damage-state node `<id>_b`
    <id>_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    <id>_shadow.glb   convex hull, no materials
    <id>_cockpit.glb  contains the node `camera_anchor`

No articulation: the delta is fixed geometry, so unlike `b1.py` there is no animation clip and
every part lives in the one body mesh.

CONVENTIONS (docs/modding/3d-models.md — get these wrong and validate-mesh rejects the file):
  * Authored nose along +X from the intake LIP at x = 0 (the pitot boom extends x < 0 and is
    EXCLUDED from the length datum, exactly as the sources exclude it); a +90-deg yaw about Z
    at the end puts the nose at Blender -Y == glTF +Z (engine#906).
  * `loft.panel()` axes: nose +X, up +Z, starboard -Y.
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


@dataclass
class Mig21Config:
    """Published dimensions for one MiG-21 variant. [P] unless marked."""

    ident: str
    length: float               # m  nose lip -> tail, EXCLUDING pitot boom
    span: float                 # m
    wing_area: float            # m^2, to the centreline
    sweep_le: float             # deg, wing leading edge
    dihedral: float             # deg (negative: anhedral)

    # Wing planform closure. The tip chord is [E] (small clipped tip, from the reference
    # photographs); the CENTRELINE root chord is then DERIVED from the published area and span:
    #     c_root = 2S/b - c_tip
    # The check that this closes: with c_root 5.97, c_tip 0.46 and the published 57-deg leading
    # edge, the TRAILING edge comes out straight to within 2 mm over the semi-span — which is
    # what every photograph of the aircraft shows. The planform closes from published data the
    # way the F-5E's did, and the B-1's could not.
    wing_tip_c: float = 0.46    # m [E]
    wing_thick: float = 0.05    # t/c [P] TsAGI S-12, 4.2% root / 5% tip — one value used
    wing_x_le_root: float = 5.20   # m [E] root LE station, from the side-view photographs
    wing_z: float = -0.10       # m [E] mid-mounted, slightly below the axis

    # Stabilator. Area and exposed span are [P] (F13-TD: 3.94 m^2, 2.6 m exposed); chords [E]
    # shaped so the exposed area reproduces the published figure against the fuselage width.
    # ⚠ The manual's 57-deg sweep with the published span puts the tips a metre past the
    # fuselage end, which every photograph contradicts — the built surface keeps the published
    # AREA and SPAN and takes the photograph-consistent sweep. Recorded as an [E] departure.
    stab_semi: float = 1.87     # m  0.55 carry-through + 1.3 exposed [P] per side
    stab_root_c: float = 2.50   # m [E]
    stab_tip_c: float = 0.90    # m [E]
    stab_sweep_c4: float = 42.0  # deg [E] photo-consistent (tips reach the nozzle plane)
    stab_x_c4: float = 11.80    # m [E]

    # Fin. Area [P] per variant (bis 5.32, F-13 4.45); chords/height [E] closing on that area.
    # ⚠ The manual's 60-deg sweep is the F-13's NARROW fin; the bis wide-chord fin the
    # photographs show has a visibly shallower leading edge (~48 deg) and a broad tip with the
    # antenna fairing. Built to the photographs; the published AREA is what is held.
    fin_root_c: float = 3.50    # m [E]
    fin_tip_c: float = 1.35     # m [E] broad bis tip
    fin_height: float = 2.19    # m [E] above the spine top; (3.50+1.35)/2 * 2.19 = 5.31 m^2 [P]
    fin_sweep_c4: float = 42.0  # deg [E] photo-consistent (LE ~48 deg)
    fin_x_c4: float = 11.00     # m [E]
    fin_z0: float = 0.70        # m [E] rooted IN the spine so the two blend, as photographed

    # Ventral fin — the small blade under the tail, [E] from the side-view photographs.
    vent_root_c: float = 1.50
    vent_tip_c: float = 0.90
    vent_depth: float = 0.42
    vent_x_c4: float = 12.60

    # Intake and shock cone, [E] from the front-view photographs (MG-127 front, Gatow).
    lip_r: float = 0.46         # m  intake lip outer radius == station-0 radius
    cone_apex_x: float = -0.10  # m  the cone pokes just proud of the lip at rest
    cone_base_x: float = 0.55
    cone_base_r: float = 0.34

    # Canopy dome and dorsal spine. The bis saddle spine runs nearly level from the canopy to
    # the fin root — this is THE bis recognition feature and the main family variable.
    canopy_x: float = 3.90      # m [E] dome centre
    canopy_len: float = 1.55    # m [E] half-length of the dome
    canopy_w: float = 0.38      # m [E] half-width — NARROWER than the fuselage: the dome must
                                #     stand proud of the deck, not ridge across it (the F-5E
                                #     canopy lesson, fl-base-pack#29)
    canopy_h: float = 0.72      # m [E] rise above the deck line
    canopy_z: float = 0.50      # m [E] deck height at the cockpit
    spine_x0: float = 4.90      # m [E] spine start (canopy fairing)
    spine_x1: float = 11.90     # m [E] spine end (fin root fairing)
    spine_w: float = 0.34       # m [E] half-width
    spine_z: float = 0.45       # m [E] ring centre height; rings rise ~0.35 above it

    # Pitot boom (excluded from the length datum).
    boom_len: float = 1.40      # m [E]
    boom_r: float = 0.028
    boom_z: float = 0.20        # m [E] mounted above the lip on the bis

    cockpit_z: float = 1.05     # camera anchor height above the axis

    # Fuselage stations: (x/L, z_up, z_lo, y_half). [E] — a circular-section body shaped to the
    # published length and the reference photographs. Nothing the flight model consumes comes
    # from here. Station 0 IS the intake lip (see lip_r); the loft starts there.
    stations: list = field(default_factory=lambda: [
        (0.000, 0.46, -0.46, 0.46),
        (0.050, 0.51, -0.52, 0.52),
        (0.120, 0.56, -0.58, 0.58),
        (0.200, 0.60, -0.62, 0.62),
        (0.280, 0.62, -0.63, 0.63),
        (0.360, 0.62, -0.64, 0.64),
        (0.500, 0.60, -0.63, 0.63),
        (0.650, 0.58, -0.60, 0.60),
        (0.800, 0.55, -0.55, 0.55),
        (0.900, 0.50, -0.48, 0.48),
        (0.970, 0.46, -0.42, 0.42),
        (1.000, 0.44, -0.40, 0.40),
    ])


def _wing_chords(cfg):
    """Centreline root chord from the published area and span (see the dataclass note)."""
    c_root = 2.0 * cfg.wing_area / cfg.span - cfg.wing_tip_c
    semi = cfg.span / 2.0
    # Straight-trailing-edge closure check, printed by the build for the record.
    te_root = cfg.wing_x_le_root + c_root
    te_tip = cfg.wing_x_le_root + semi * math.tan(math.radians(cfg.sweep_le)) + cfg.wing_tip_c
    return c_root, semi, te_tip - te_root


def _ring(bm, x, z_up, z_lo, y_half, steps=20, power=2.05):
    """One near-circular fuselage station ring (power ~2 == ellipse; the MiG-21 is a tube)."""
    verts = []
    for i in range(steps):
        a = 2.0 * math.pi * i / steps
        c, s = math.cos(a), math.sin(a)
        y = y_half * math.copysign(abs(c) ** (2.0 / power), c)
        z = (z_up if s >= 0 else -z_lo) * math.copysign(abs(s) ** (2.0 / power), s)
        verts.append(bm.verts.new(Vector((x, y, z))))
    return verts


def _skin(bm, rings, cap_front=False, cap_rear=True):
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                bm.faces.new((a[j], b[j], b[k], a[k]))
            except ValueError:
                pass
    if cap_front:
        try:
            bm.faces.new(list(reversed(rings[0])))
        except ValueError:
            pass
    if cap_rear:
        try:
            bm.faces.new(rings[-1])
        except ValueError:
            pass


def _fuselage(cfg, bm):
    rings = [_ring(bm, t * cfg.length, z_up, z_lo, y_half)
             for (t, z_up, z_lo, y_half) in cfg.stations]
    # Intake mouth: recess the lip inward and aft, so the cone sits in a real annular inlet
    # rather than on a flat face. The recess rings shrink toward the duct and the last one is
    # capped behind the cone base, where it is never seen.
    mouth = [rings[0]]
    for (x, r) in ((0.10, 0.40), (0.35, 0.365)):
        mouth.append(_ring(bm, x, r, -r, r))
    mouth_rev = [list(reversed(m)) for m in mouth]   # interior surface: reverse the winding
    _skin(bm, mouth_rev, cap_front=False, cap_rear=True)
    _skin(bm, rings, cap_front=False, cap_rear=True)


def _cone(cfg, bm):
    """The translating shock cone, apex just proud of the lip."""
    apex = bm.verts.new(Vector((cfg.cone_apex_x, 0.0, 0.0)))
    rings = []
    for f in (0.35, 0.70, 1.00):
        x = cfg.cone_apex_x + f * (cfg.cone_base_x - cfg.cone_apex_x)
        r = f * cfg.cone_base_r
        rings.append(_ring(bm, x, r, -r, r, steps=16))
    n = len(rings[0])
    for j in range(n):
        k = (j + 1) % n
        try:
            bm.faces.new((apex, rings[0][j], rings[0][k]))
        except ValueError:
            pass
    _skin(bm, rings, cap_front=False, cap_rear=True)


def _canopy(cfg, bm):
    """The one-piece dome, standing PROUD of the deck — not a full-width ridge (see dataclass).

    Hand-lofted latitude rings, NOT `bmesh.ops.create_uvsphere`: the sphere operator's output
    face order is not stable across processes, and it was the one part of this builder that made
    two builds differ byte-for-byte (everything hand-lofted is deterministic). Found by bisecting
    the determinism test's failure; do not put the operator back.
    """
    lats, steps = 6, 14
    rings = []
    for i in range(1, lats):                     # open at the bottom; buried in the fuselage
        th = math.pi * i / lats                  # pole-to-pole angle
        r, z = math.sin(th), math.cos(th)
        ring = []
        for j in range(steps):
            a = 2.0 * math.pi * j / steps
            ring.append(bm.verts.new(Vector((
                cfg.canopy_x + cfg.canopy_len * z,
                cfg.canopy_w * r * math.sin(a),
                cfg.canopy_z + cfg.canopy_h * r * math.cos(a)))))
        ring.reverse()                           # wind so recalc keeps normals outward
        rings.append(ring)
    apex_f = bm.verts.new(Vector((cfg.canopy_x + cfg.canopy_len, 0.0, cfg.canopy_z)))
    apex_a = bm.verts.new(Vector((cfg.canopy_x - cfg.canopy_len, 0.0, cfg.canopy_z)))
    n = len(rings[0])
    for j in range(n):
        k = (j + 1) % n
        try:
            bm.faces.new((apex_f, rings[0][j], rings[0][k]))
        except ValueError:
            pass
    _skin(bm, rings, cap_front=False, cap_rear=False)
    for j in range(n):
        k = (j + 1) % n
        try:
            bm.faces.new((apex_a, rings[-1][k], rings[-1][j]))
        except ValueError:
            pass


def _spine(cfg, bm):
    """The dorsal spine as its own slender loft over the fuselage top."""
    xs = [cfg.spine_x0, cfg.spine_x0 + 0.8, (cfg.spine_x0 + cfg.spine_x1) / 2.0,
          cfg.spine_x1 - 0.8, cfg.spine_x1]
    heights = [0.62, 0.56, 0.50, 0.44, 0.35]
    rings = []
    for x, h in zip(xs, heights):
        r = _ring(bm, x, cfg.spine_z + h, -0.05, cfg.spine_w, steps=10)
        rings.append(r)
    _skin(bm, rings, cap_front=True, cap_rear=True)


def _vertical_blade(bm, x_c4_root, extent, root_c, tip_c, sweep_c4, thick, z0):
    """A vertical surface growing UP (extent > 0) or DOWN (extent < 0) from z0.

    `loft.panel(vertical=True)` only grows upward; the ventral fin needs the mirror. Same
    quarter-chord positioning convention.
    """
    sections, steps = 6, 12
    rings = []
    for i in range(sections + 1):
        f = i / sections
        z = z0 + f * extent
        chord = root_c + (tip_c - root_c) * f
        x_c4 = x_c4_root + abs(f * extent) * math.tan(math.radians(sweep_c4))
        x_le = x_c4 - 0.25 * chord
        ring = []
        for j in range(steps + 1):
            xc = j / steps
            ring.append((x_le + xc * chord, naca_symmetric(xc, thick) * chord))
        for j in range(steps - 1, 0, -1):
            xc = j / steps
            ring.append((x_le + xc * chord, -naca_symmetric(xc, thick) * chord))
        rings.append([bm.verts.new(Vector((px, py, z))) for (px, py) in ring])
    flip = extent < 0
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                f4 = (a[j], a[k], b[k], b[j]) if flip else (a[j], b[j], b[k], a[k])
                bm.faces.new(f4)
            except ValueError:
                pass
    try:
        bm.faces.new(list(reversed(rings[-1])) if flip else rings[-1])
    except ValueError:
        pass


def _boom(cfg, bm):
    """The pitot boom: a plain 8-sided cylinder above the lip, extending x < 0 (off-datum)."""
    rings = []
    for x in (-cfg.boom_len, 0.60):
        ring = []
        for i in range(8):
            a = 2.0 * math.pi * i / 8
            ring.append(bm.verts.new(Vector((x, cfg.boom_r * math.cos(a),
                                             cfg.boom_z + cfg.boom_r * math.sin(a)))))
        rings.append(ring)
    _skin(bm, rings, cap_front=True, cap_rear=True)


def build_airframe(cfg, name):
    c_root, semi, te_skew = _wing_chords(cfg)
    print(f"{cfg.ident}: wing closes at c_root {c_root:.3f} m, TE skew {te_skew * 1000:+.0f} mm "
          f"over the semi-span (straight TE == photographs)")

    bm = bmesh.new()
    _fuselage(cfg, bm)
    _cone(cfg, bm)
    _canopy(cfg, bm)
    _spine(cfg, bm)
    _boom(cfg, bm)

    # The delta. Positioned by the root quarter-chord derived from the LE station used by the
    # closure check, so the printed planform IS the built planform.
    sweep_c4 = math.degrees(math.atan(
        math.tan(math.radians(cfg.sweep_le))
        - 0.25 * (c_root - cfg.wing_tip_c) / semi))
    x_c4_root = cfg.wing_x_le_root + 0.25 * c_root
    loft.panel(bm, x_c4_root, semi, c_root, cfg.wing_tip_c, sweep_c4,
               cfg.wing_thick, dihedral=cfg.dihedral, z0=cfg.wing_z)

    # Stabilator (all-moving slab — no articulation authored; the FM owns pitch).
    loft.panel(bm, cfg.stab_x_c4, cfg.stab_semi, cfg.stab_root_c, cfg.stab_tip_c,
               cfg.stab_sweep_c4, 0.06, z0=0.05)

    # Fin over the spine, and the ventral blade below the tail.
    loft.panel(bm, cfg.fin_x_c4, cfg.fin_height, cfg.fin_root_c, cfg.fin_tip_c,
               cfg.fin_sweep_c4, 0.07, vertical=True, z0=cfg.fin_z0)
    _vertical_blade(bm, cfg.vent_x_c4, -cfg.vent_depth, cfg.vent_root_c, cfg.vent_tip_c,
                    30.0, 0.08, z0=-0.40)

    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), verts=bm.verts,
                     matrix=Matrix.Rotation(math.pi / 2.0, 4, 'Z'))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = scene.finish_mesh(bm, name)
    scene.principled_material(body, "airframe_grey", (0.32, 0.34, 0.36, 1.0), 0.15, 0.55)
    return body


def main(cfg, argv=None):
    ap = argparse.ArgumentParser(description=f"Build the {cfg.ident} mesh set.")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv if argv is not None else sys.argv[sys.argv.index("--") + 1:])
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    ident = cfg.ident

    scene.clear_scene()
    body = build_airframe(cfg, ident)

    dmg = damage.battle_damage(body, "airframe_grey", seed=7)
    dmg.name = f"{ident}_b"
    dmg.parent = body

    export.export_glb(out / f"{ident}.glb", [body, dmg])
    export.patch_textures(out / f"{ident}.glb", f"../../textures/{ident}_diffuse.ktx2",
                          f"../../textures/{ident}_orm.ktx2")

    for i, ratio in enumerate((0.50, 0.20, 0.05)):
        lod = export.decimate(body, ratio, f"{ident}_lod{i}")
        export.export_glb(out / f"{ident}_lod{i}.glb", [lod])
        export.patch_textures(out / f"{ident}_lod{i}.glb", f"../../textures/{ident}_diffuse.ktx2",
                              f"../../textures/{ident}_orm.ktx2")
        bpy.data.objects.remove(lod, do_unlink=True)

    hull = scene.convex_hull(body, f"{ident}_shadow")
    export.export_glb(out / f"{ident}_shadow.glb", [hull])

    anchor = scene.empty("camera_anchor", (0.0, -cfg.canopy_x, cfg.cockpit_z))
    export.export_glb(out / f"{ident}_cockpit.glb", [anchor])
    print(f"{ident}: wrote mesh set to {out}")


def run_cli(cfg):
    main(cfg)
