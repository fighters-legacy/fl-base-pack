#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Generate the F-16A mesh set from published dimensions (fl-base-pack#19).

Run (GUI):       blender --python aircraft/f16a/f16a_build.py
Run (headless):  blender --background --python aircraft/f16a/f16a_build.py -- --out aircraft/f16a
                 python3 f16a_build.py -- --out aircraft/f16a       (with the pip `bpy` module)

Provenance: `generated` — this script is the mesh's source of truth, byte-reproducible (the
meshlib determinism gate builds it twice and diffs). Geometry sources, per the likeness policy
(fighters-legacy docs/legal/aircraft-likeness.md): NASA TP-1538's published dimensions
(Table I: span 9.144 m, S 27.87 m^2, MAC 3.45 m) and its Figure 2 three-view (printed anchors:
length 15.09 m incl. probe, height 5.01 m, span-with-rails 9.45 m), plus public-domain USAF
photography for judgement calls. NO scale plans, NO other sim's geometry.

HONESTY NOTE vs the F-5E: the F-5E's station table was sampled off its NASA drawing
PROGRAMMATICALLY (column-scanning the ink). TP-1538's Figure 2 is a small line sketch —
the station table below is proportions read MANUALLY off it, anchored to the printed
dimensions, and is tagged [E] accordingly. The published numbers close the planform anyway:
c_root = 2S/(b(1+lambda)) = 5.03 m with the published 16.5 ft/3.5 ft chords, and the trapezoid
MAC comes out 3.48 vs the published 3.45 (0.8%) — the wing, at least, cannot be very wrong.

Axes: +X aft (nose at x=0), +Y port, +Z up. Blender's glTF exporter converts.
"""

import argparse
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))

from fl_meshlib import export, loft, scene, uvatlas             # noqa: E402
from fl_meshlib.curves import smoothstep as _smoothstep         # noqa: E402
from fl_meshlib.damage import battle_damage                     # noqa: E402
from fl_meshlib.stations import interp_table                    # noqa: E402

# ═══ Published dimensions ══════════════════════════════════════════════════════════ [P] ═
LENGTH   = 14.55      # m  fuselage, nose tip to nozzle (Fig 2's 15.09 minus the probe) [D]
PROBE    = 0.54       # m  pitot boom ahead of the radome [D from the same subtraction]
SPAN     = 9.144      # m  clean span, TP-1538 Table I
SPAN_RAIL = 9.45      # m  with tip rails, Fig 2's printed front-view dimension
WING_AREA = 27.87     # m^2 TP-1538 Table I
ROOT_CHORD = 5.03     # m  16.5 ft, closes 2S/(b(1+taper)) to 0.1%
TIP_CHORD  = 1.07     # m  3.5 ft
TAPER      = TIP_CHORD / ROOT_CHORD
SWEEP_LE   = 40.0     # deg leading edge
# tan(c4) = tan(LE) - (4*0.25/AR)*((1-taper)/(1+taper)); AR = 3.0
SWEEP_C4   = math.degrees(math.atan(math.tan(math.radians(SWEEP_LE))
                                    - (1.0 / 3.0) * ((1 - TAPER) / (1 + TAPER))))   # 31.9
THICKNESS  = 0.04     # NACA 64A204's 4% — the F-16's famously thin biconvex-ish section

WING_X_LE  = 6.85     # m  wing LE root station [E, Fig 2 planform proportion ~0.47 L]
WING_Z     = 0.05     # m  mid-mounted, blended

# Strake / LERX: the F-16's defining planform feature. A thin, highly swept panel from the
# forebody flank into the wing root; the fuselage half-width blends over the same span so the
# join reads blended rather than stuck-on. All [E] off the Fig 2 planform.
STRAKE_X_APEX = 3.85
STRAKE_SEMI   = 1.18
STRAKE_ROOT_C = 3.10
STRAKE_TIP_C  = 0.25
STRAKE_TH     = 0.05

HT_SPAN    = 5.58     # m  stabilator tip-to-tip [D widely published 18.3 ft]
HT_ROOT_C  = 2.45     # m  [E]
HT_TIP_C   = 0.75     # m  [E]
HT_SWEEP_C4 = 28.0    # deg [E]
HT_DIHEDRAL = -10.0   # deg ANHEDRAL — clearly visible in Fig 2's front view
HT_X_C4    = 13.35    # m  [E]

VT_HEIGHT  = 2.85     # m  exposed fin above the spine [D: Fig 2's 5.01 total height minus
                      #    belly depth and spine height at the fin]
VT_ROOT_C  = 3.20     # m  [E]
VT_TIP_C   = 1.05     # m  [E]
VT_SWEEP_C4 = 41.0    # deg [E]
VT_X_C4    = 12.75    # m  [E]

VF_SEMI    = 0.70     # m  ventral fins, each [E]
VF_ROOT_C  = 1.35
VF_TIP_C   = 0.55
VF_DIHEDRAL = -73.0   # deg: canted sharply down-and-out
VF_X_C4    = 10.60

NOZZLE_R   = 0.52     # m  single F100 [E, front view proportion]

CANOPY_SPAN  = (0.125, 0.305)  # x/L — the F-16's bubble sits far forward
CANOPY_HALFW = 0.42            # m [E] wide single-piece bubble
WINDSCREEN_F = 0.18
SILL_EASE    = 1.8

# Ventral inlet — the F-16's chin intake. One centred cowl under the belly: sharp lip, recessed
# throat (the visible dark hole), outer shell fading into the belly aft. All [E] off Fig 2.
INTAKE_X0    = 0.295   # x/L of the lip
INTAKE_X1    = 0.56    # x/L where the cowl is buried in the belly
INTAKE_ZC    = -1.02   # m  aperture centre
INTAKE_HY    = 0.50    # m  aperture half-width
INTAKE_HZ    = 0.34    # m  aperture half-height
INTAKE_DEPTH = 0.30    # m  throat recess behind the lip

TIP_RAIL_LEN = 2.90    # m  wingtip AIM-9 rail — part of the airframe (stations 1/9 carry
                       #    launchers in the published configuration; Fig 2 draws them)

TEX_DIFFUSE  = "../../textures/f16a_diffuse.ktx2"
TEX_ORM      = "../../textures/f16a_orm.ktx2"

# ═══ FUSELAGE STATIONS — proportions read off TP-1538 Figure 2, anchored to its printed
# dimensions. [E] except where a printed number pins them; see the honesty note up top. ═══
# (x/L, z_upper, z_lower, y_half), metres, z from the drawing's nose-tip reference line.
STATIONS_FUS = [
    # x/L    z_up    z_lo   y_half
    (0.000,  0.010, -0.010, 0.030),   # radome tip
    (0.040,  0.105, -0.150, 0.170),
    (0.090,  0.230, -0.300, 0.330),
    (0.125,  0.430, -0.390, 0.450),   # windscreen base; canopy span begins
    (0.180,  1.010, -0.480, 0.550),   # canopy peak — the F-16 bubble stands tall and forward
    (0.240,  0.980, -0.560, 0.620),
    (0.305,  0.860, -0.930, 0.640),   # canopy fairs into the spine; inlet lip arrives below
    (0.380,  0.800, -1.060, 0.700),   # inlet/duct: the deepest fuselage station
    (0.480,  0.780, -1.010, 0.680),   # wing-root region (the strake panel adds the shelf --
    (0.580,  0.750, -0.930, 0.660),   #  the BODY itself stays slim, as the front view shows)
    (0.680,  0.720, -0.800, 0.640),
    (0.780,  0.700, -0.680, 0.620),   # spine runs level into the fin base
    (0.880,  0.620, -0.570, 0.560),
    (0.950,  0.540, -0.480, 0.510),   # boat-tail
    (1.000,  0.420, -0.330, 0.420),   # nozzle station
]

MAT_SKIN = "f16a_skin"


def _fus_at(t):
    return interp_table(STATIONS_FUS, t)


def _spine_top(t):
    """Fuselage top with the canopy glass excluded (the F-5E's sill-ease pattern)."""
    c0, c1 = CANOPY_SPAN
    z_up, _, _ = _fus_at(t)
    if t <= c0 or t >= c1:
        return z_up
    a = _fus_at(c0)[0]
    b = _fus_at(c1)[0]
    return a + (b - a) * ((t - c0) / (c1 - c0)) ** SILL_EASE


NOSE_BLEND_T = 0.10


def _nose_section(t, top, lo, w):
    """Radome as a body of revolution blending into the traced sections (F-5E pattern —
    a radome is a fairing over a circular antenna; its sections are circular, full stop)."""
    cz_tr = (top + lo) / 2.0
    hh_tr = max((top - lo) / 2.0, 0.02)
    if t >= NOSE_BLEND_T:
        return cz_tr, hh_tr
    top_b = _spine_top(NOSE_BLEND_T)
    lo_b = _fus_at(NOSE_BLEND_T)[1]
    cz_rd = ((top_b + lo_b) / 2.0) * (t / NOSE_BLEND_T)
    hh_rd = max(w, 0.02)
    u = _smoothstep(t / NOSE_BLEND_T)
    return cz_rd + (cz_tr - cz_rd) * u, hh_rd + (hh_tr - hh_rd) * u


def _fuselage(bm, sections=46):
    rings = []
    for i in range(sections + 1):
        t = i / sections
        x = t * LENGTH
        top = _spine_top(t)
        _, lo, w = _fus_at(t)
        w = max(w, 0.02)
        cz, hh = _nose_section(t, top, lo, w)
        n = 2.1 + 0.5 * _smoothstep(t / 0.30)     # round nose; flatter, blended mid-body
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

    # Pitot boom — Fig 2 draws it; its length is the 15.09 printed length minus the fuselage.
    pb = []
    for i in range(2):
        x = -PROBE + i * PROBE
        r = 0.015 if i == 0 else 0.026
        pb.append([bm.verts.new(Vector((x, r * math.cos(2 * math.pi * j / 6),
                                        r * math.sin(2 * math.pi * j / 6))))
                   for j in range(6)])
    for j in range(6):
        k = (j + 1) % 6
        try:
            bm.faces.new((pb[0][j], pb[0][k], pb[1][k], pb[1][j]))
        except ValueError:
            pass


def _inlet_ring(bm, t, scale=1.0, dx=0.0, steps=14):
    """One rounded-rectangle ring of the ventral cowl, centred under the belly."""
    fade = 1.0 - _smoothstep((t - INTAKE_X0) / (INTAKE_X1 - INTAKE_X0))
    lo = _fus_at(t)[1]
    hz = INTAKE_HZ * (0.30 + 0.70 * fade)
    # aperture centre rides just under the local belly line, standing proud at the lip
    cz = min(INTAKE_ZC, lo - hz * 0.55)
    hy = INTAKE_HY * (0.55 + 0.45 * fade)
    x = t * LENGTH + dx
    ring = []
    n = 3.0
    for j in range(steps):
        th = 2.0 * math.pi * j / steps
        c, sn = math.cos(th), math.sin(th)
        y = hy * scale * math.copysign(abs(c) ** (2.0 / n), c)
        z = hz * scale * math.copysign(abs(sn) ** (2.0 / n), sn)
        ring.append(bm.verts.new(Vector((x, y, cz + z))))
    return ring


def _inlet(bm, stations=7):
    """The chin inlet: the F-5E's cowl recipe rotated under the belly, one centred copy."""
    lip = _inlet_ring(bm, INTAKE_X0)
    prev = lip
    for i in range(1, stations + 1):
        t = INTAKE_X0 + (INTAKE_X1 - INTAKE_X0) * (i / stations)
        ring = _inlet_ring(bm, t)
        loft.bridge(bm, prev, ring, False)
        prev = ring
    try:
        bm.faces.new(prev)
    except ValueError:
        pass
    throat = _inlet_ring(bm, INTAKE_X0, scale=0.74, dx=INTAKE_DEPTH)
    loft.bridge(bm, lip, throat, True)
    try:
        bm.faces.new(list(reversed(throat)))
    except ValueError:
        pass


def _nozzle(bm):
    """Single F100 nozzle: one centred ring stack with a slight convergent boat-tail."""
    prev = None
    for i in range(4):
        f = i / 3.0
        x = LENGTH - 0.45 + f * 0.45
        r = NOZZLE_R * (1.0 - 0.18 * f)
        ring = [bm.verts.new(Vector((x, r * math.cos(2 * math.pi * j / 12),
                                     0.03 + r * math.sin(2 * math.pi * j / 12))))
                for j in range(12)]
        if prev:
            for j in range(12):
                k = (j + 1) % 12
                try:
                    bm.faces.new((prev[j], prev[k], ring[k], ring[j]))
                except ValueError:
                    pass
        prev = ring


def _tip_rails(bm):
    """Wingtip launch rails — airframe, not stores; Fig 2 draws them and its 9.45 m span
    dimension INCLUDES them (Table I's 9.144 m excludes them; the difference is the rails)."""
    y_tip = SPAN / 2.0
    x_c4_tip = WING_X_LE + 0.25 * ROOT_CHORD + y_tip * math.tan(math.radians(SWEEP_C4))
    x0 = x_c4_tip - 0.25 * TIP_CHORD - 0.65
    for side in (1.0, -1.0):
        y = side * (SPAN_RAIL / 2.0 - 0.09)
        rings = []
        for i in range(7):
            f = i / 6.0
            x = x0 + f * TIP_RAIL_LEN
            r = 0.090 * (1.0 - 0.55 * abs(2.0 * f - 1.0) ** 3)
            ring = []
            for j in range(8):
                th = 2.0 * math.pi * j / 8
                ring.append(bm.verts.new(Vector((x, y + r * math.cos(th), WING_Z + r * math.sin(th)))))
            rings.append(ring)
        for i in range(6):
            a, b = rings[i], rings[i + 1]
            for j in range(8):
                k = (j + 1) % 8
                try:
                    f4 = (a[j], a[k], b[k], b[j]) if side > 0 else (a[j], b[j], b[k], a[k])
                    bm.faces.new(f4)
                except ValueError:
                    pass


def _canopy(bm):
    """The bubble. Same recipe as the F-5E's, wider and taller — the F-16's canopy is its
    second most recognisable feature after the inlet."""
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
        w = CANOPY_HALFW * _smoothstep(f / WINDSCREEN_F) * (1.0 - 0.78 * _smoothstep((f - 0.72) / 0.28))
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


def build_airframe(name: str) -> bpy.types.Object:
    bm = bmesh.new()

    _fuselage(bm)
    _inlet(bm)
    _canopy(bm)

    # Strake/LERX first, so the wing overlaps it at the root.
    loft.panel(bm, STRAKE_X_APEX + 0.25 * STRAKE_ROOT_C + 0.9, STRAKE_SEMI, STRAKE_ROOT_C,
               STRAKE_TIP_C, 62.0, STRAKE_TH / STRAKE_ROOT_C, dihedral=0.0, z0=WING_Z + 0.10)

    # Wing — cropped delta, positioned by its quarter-chord; the published trapezoid.
    loft.panel(bm, WING_X_LE + 0.25 * ROOT_CHORD, SPAN / 2.0, ROOT_CHORD, TIP_CHORD,
               SWEEP_C4, THICKNESS, dihedral=0.0, z0=WING_Z)
    _tip_rails(bm)

    # Stabilators — anhedral, all-moving.
    loft.panel(bm, HT_X_C4, HT_SPAN / 2.0, HT_ROOT_C, HT_TIP_C, HT_SWEEP_C4, 0.035,
               dihedral=HT_DIHEDRAL, z0=0.05)

    # Fin + the ventral pair.
    loft.panel(bm, VT_X_C4, VT_HEIGHT, VT_ROOT_C, VT_TIP_C, VT_SWEEP_C4, 0.04,
               vertical=True, z0=0.65)
    loft.panel(bm, VF_X_C4, VF_SEMI, VF_ROOT_C, VF_TIP_C, 30.0, 0.05,
               dihedral=VF_DIHEDRAL, z0=-0.55)

    _nozzle(bm)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _commit(bm, name)


def _commit(bm, name: str) -> bpy.types.Object:
    obj = scene.finish_mesh(bm, name)
    scene.principled_material(obj, MAT_SKIN, (0.45, 0.47, 0.50, 1.0), 0.15, 0.55)
    uvatlas.planar_uvs(obj, LENGTH, SPAN)
    return obj


def _hardpoint_markers(aid: str):
    """Marker empties for the 10 stations, derived from the same constants that build the
    geometry (engine ignores them today — fighters-legacy#844). Port +Y, starboard -Y.
    Slot map matches entities/f16a.toml: 0 gun, 1/2 tips, 3/4 outboard, 5/6 mid (the ADF's
    Sparrow stations), 7/8 inboard wet, 9 centreline."""
    marks = []
    # Slot 0 — the M61A1 sits in the left wing-root shoulder, gun port beside the canopy sill.
    marks.append(scene.empty("hardpoint_0",
                             location=(0.40 * LENGTH, 0.62, 0.45),
                             extras={"fl_marker": "hardpoint", "fl_slot": 0}))
    x_c4_tip = WING_X_LE + 0.25 * ROOT_CHORD + (SPAN / 2.0) * math.tan(math.radians(SWEEP_C4))
    x_tip = x_c4_tip - 0.25 * TIP_CHORD + 0.35
    for slot, sgn in ((1, 1.0), (2, -1.0)):
        marks.append(scene.empty(f"hardpoint_{slot}",
                                 location=(x_tip, sgn * SPAN / 2.0, WING_Z),
                                 extras={"fl_marker": "hardpoint", "fl_slot": slot}))
    # Underwing pylons at 45% local chord, below the wing. Span fractions: outboard/mid/inboard.
    for slot, sgn, s in ((3, 1.0, 0.76), (4, -1.0, 0.76),
                         (5, 1.0, 0.52), (6, -1.0, 0.52),
                         (7, 1.0, 0.30), (8, -1.0, 0.30)):
        yhalf = s * SPAN / 2.0
        x_le = WING_X_LE + yhalf * math.tan(math.radians(SWEEP_LE))
        chord = ROOT_CHORD + (TIP_CHORD - ROOT_CHORD) * s
        marks.append(scene.empty(f"hardpoint_{slot}",
                                 location=(x_le + 0.45 * chord, sgn * yhalf, WING_Z - 0.28),
                                 extras={"fl_marker": "hardpoint", "fl_slot": slot}))
    # Slot 9 — centreline, behind the inlet.
    marks.append(scene.empty("hardpoint_9",
                             location=(0.58 * LENGTH, 0.0, -1.15),
                             extras={"fl_marker": "hardpoint", "fl_slot": 9}))
    return marks


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="aircraft/f16a")
    ap.add_argument("--id", default="f16a")
    ap.add_argument("--blend", metavar="PATH",
                    help="also save a Blender project for artist polish (never committed for a "
                         "generated aircraft; not byte-stable)")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    aid = args.id

    scene.clear_scene()
    body = build_airframe(aid)
    tris = len(body.data.polygons)

    dmg = battle_damage(body)
    markers = _hardpoint_markers(aid)
    export.export_glb(out / f"{aid}.glb", [body, dmg, *markers])
    export.patch_textures(out / f"{aid}.glb", TEX_DIFFUSE, TEX_ORM)
    bpy.data.objects.remove(dmg)

    for i, ratio in enumerate((0.50, 0.20, 0.05)):
        lod = export.decimate(body, ratio, f"{aid}_lod{i}")
        export.export_glb(out / f"{aid}_lod{i}.glb", [lod])
        export.patch_textures(out / f"{aid}_lod{i}.glb", TEX_DIFFUSE, TEX_ORM)
        bpy.data.objects.remove(lod)

    shadow = scene.convex_hull(body, f"{aid}_shadow")
    export.export_glb(out / f"{aid}_shadow.glb", [shadow])

    anchor = scene.empty("camera_anchor", location=(
        (CANOPY_SPAN[0] + 0.38 * (CANOPY_SPAN[1] - CANOPY_SPAN[0])) * LENGTH, 0.0,
        _fus_at(0.19)[0] - 0.30))
    export.export_glb(out / f"{aid}_cockpit.glb", [anchor])

    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.blend).resolve()))
        print(f"  wrote Blender project -> {args.blend}")

    print(f"\n  {aid}: {tris} faces")
    print(f"  wrote {aid}.glb (+ _b, +10 hardpoint markers), _lod0/1/2, _shadow, _cockpit -> {out}")
    return 0


if __name__ == "__main__":
    rc = main()
    if bpy.app.background:
        sys.exit(rc)
    for o in bpy.context.scene.objects:
        if o.name.endswith("_shadow") or o.name == "camera_anchor":
            o.hide_set(True)
