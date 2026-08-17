#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Parametric Mikoyan MiG-29 airframe-family builder.

The MiG-29 family (9.12 Fulcrum-A, 9.13 Fulcrum-C with its enlarged spine, and the 9.12SE/S export
and upgrade marks) shares one layout, and it is unlike anything else in this pack: a slender
central body carrying the radar and cockpit, TWO WIDELY SPACED engine nacelles under a
lifting centre-section, big 73.5-degree leading-edge root extensions blending nose to wing, a
mid-mounted 42-degree trapezoidal wing rooted ON the nacelle, and twin canted fins standing on
booms outboard of the engines. The space between the nacelles carries lift — that is the whole
aerodynamic idea of the aircraft, and the mesh has to show it.

This module holds the authored GEOMETRY ALGORITHM once; each aircraft supplies only DATA (a
`Mig29Config` of published dimensions), per the one-family-one-builder rule the T-38A established.
`aircraft/mig29a/mig29a_build.py` is the only user today; **fl-base-pack#45 (MiG-29S) is a
DATA-ONLY variant that reuses this mesh verbatim** and must not fork it.

It is a SIBLING of `n156.py`, `mig21.py` and `b1.py`, not a derivative. A nose-intake tailed delta
and a cheek-intake trapezoidal fighter share no geometry with a twin-nacelle blended body; the
CONVENTIONS are shared, the shapes are not.

FAMILY-VARIANT KNOBS (for #45 and the 9.13, per the one-family-one-builder rule): the spine
profile (`spine_h` — the Fulcrum-C's enlarged #1 tank is the one visible airframe difference in
the family), the fin chords, and the LERX station. The knobs exist because they are exactly what
differs between the marks already filed as issues — not speculative generality.

Emits, per docs/modding/3d-models.md:
    <id>.glb          base mesh; root node `<id>`, damage-state node `<id>_b`
    <id>_lod0/1/2.glb ~50% / ~20% / ~5% triangle budgets (separate FILES, not nodes)
    <id>_shadow.glb   convex hull, no materials
    <id>_cockpit.glb  contains the node `camera_anchor`

No articulation: the MiG-29 has no variable geometry, so unlike `b1.py` there is no animation clip
and no `sweep` channel. (That channel is also, as of engine#1195, never driven — but that is not
why it is absent here; this airframe simply has nothing to articulate.)

CONVENTIONS (docs/modding/3d-models.md — get these wrong and validate-mesh rejects the file):
  * Authored nose along +X from the radome tip at x = 0; a +90-deg yaw about Z at the end puts the
    nose at Blender -Y == glTF +Z (engine#906).
  * `loft.panel()` axes: nose +X, up +Z, starboard -Y.
  * Winding CCW from outside, normals outward; the opaque pipeline is single-sided.
  * Node and material names: lowercase with underscores.
  * NO EMBEDDED IMAGE DATA — external .ktx2 URIs only.

⚑ HAND-LOFT EVERYTHING. No `bmesh.ops.create_uvsphere` or other primitive operators: their output
face order is not stable across processes, which is what made two MiG-21 builds differ
byte-for-byte (found by bisecting the determinism test). Every ring in this file is authored.
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
class Mig29Config:
    """Published dimensions for one MiG-29 variant. [P] unless marked."""

    ident: str
    length: float               # m  radome tip -> tail, EXCLUDING the pitot boom
    span: float                 # m
    wing_area: float            # m^2, reference (to the centreline)
    height: float               # m  ground line -> fin tip
    sweep_le: float             # deg, wing outer-panel leading edge
    sweep_lerx: float           # deg, LERX leading edge

    # Wing planform. Taper is [E] — the same 0.25 the flight model's MAC derivation assumes, so the
    # mesh and the aerodynamics describe ONE wing. The root chord then closes from area and span.
    wing_taper: float = 0.25        # [E] — must match derive.py's TAPER
    wing_thick: float = 0.05        # t/c [E]
    wing_root_y: float = 1.56       # m [E] wing root = the nacelle's OUTER shoulder
                                    #     (nac_y + nac_r). ⚑ This was once the nacelle CENTRELINE,
                                    #     which put the wing root inside the nacelle and left the
                                    #     LERX no exposed span to be seen in.
    wing_x_le_root: float = 8.60    # m [E] root LE station
    wing_z: float = 0.10            # m [E] mid-mounted on the nacelle shoulder
    dihedral: float = -2.0          # deg [E] slight anhedral, as photographed

    # LERX — the aircraft's signature. Runs from the forward fuselage to the wing root LE at the
    # published 73.5-deg sweep, blending the body into the wing.
    lerx_x0: float = 5.20           # m [E] forward apex of the LERX, beside the cockpit
    lerx_z: float = 0.18            # m [E]
    lerx_thick: float = 0.13        # m [E] half-thickness at the root

    # Engine nacelles. ⚑ THESE NUMBERS WERE WRONG IN THE FIRST BUILD AND THE ERROR WAS ONLY
    # VISIBLE IN A RENDER — every dimension check passed while the aircraft looked nothing like a
    # MiG-29. The nacelles were 1.64 m fat cigars starting level with the COCKPIT and hanging well
    # below the fuselage line, with tall square intake mouths. The real aircraft has SHALLOW WEDGE
    # inlets, roughly twice as wide as they are tall, tucked UNDER the LERX and well aft, feeding
    # nacelles that blend into the wing root rather than hang off it.
    #
    # Rule this cost: measuring span and length proves scale, never SHAPE. Render the built glb and
    # look at it. (The B-1B lane recorded exactly this — "it rendered as a plain tube with wings" —
    # and the lesson did not transfer until a human looked at this aircraft.)
    nac_y: float = 1.02             # m [E] nacelle centreline offset. ⚑ 1.62 then 1.34 both
                                    #     rendered as two DETACHED PODS with a canyon between
                                    #     them. The real aircraft's inlets sit close, low, and
                                    #     either side of a narrow keel — the 'widely spaced'
                                    #     description is about the TUNNEL, not a wide stance.
    nac_x0: float = 7.30            # m [E] intake lip, ~42% of length, UNDER the LERX
                                    #     (was 5.30, level with the cockpit)
    nac_x1: float = 17.32           # m [E] nozzle station (== length by construction)
    nac_r: float = 0.54             # m [E] nacelle radius, around a 1.04 m engine
    intake_w: float = 0.54          # m [E] intake HALF-width -> 1.08 m wide
    intake_h: float = 0.34          # m [E] intake HALF-height -> 0.68 m tall. ⚑ 0.24 was an
                                    #     OVERCORRECTION: the real MiG-29 duct is a big, deep,
                                    #     SHARP-CORNERED rectangle, not a shallow slot.
    intake_power: float = 6.0       #       ring exponent at the lip. ⚑ THE SHAPE, NOT THE SIZE,
                                    #       was what read wrong: at ~3 the mouth rounds off into a
                                    #       lump merged with the fuselage. 6 gives the flat faces
                                    #       and hard corners the photographs show.
    body_power: float = 3.6         #       centre-body section exponent (flattened oval)
    splitter_gap: float = 0.10      # m [E] boundary-layer splitter at the LIP ONLY. ⚑ Applied
                                    #       along the whole nacelle it opens a visible HOLE
                                    #       between duct and body — the real splitter is a
                                    #       forward feature; aft of the intake the nacelle
                                    #       merges into the centre body as one structure.
                                    #       Tapers to zero by the third station.
    intake_z: float = -0.44         # m [E] intake centre height, under the LERX

    # Stabilators — all-moving, mounted on the tail booms outboard of the nozzles.
    stab_root_y: float = 1.60       # m [E]
    stab_semi: float = 2.40         # m [E] exposed semi-span
    stab_root_c: float = 2.60       # m [E]
    stab_tip_c: float = 0.95        # m [E]
    stab_sweep_c4: float = 45.0     # deg [E]
    stab_x_c4: float = 14.20        # m [E] — set so the stabilator TIP TRAILING EDGE
                                    #     closes on the published 17.32 m overall length.
                                    #     At 14.60 the tips reached 17.71 m and the built
                                    #     aircraft was 2.3% too long; only measuring the
                                    #     exported glb showed it.
    stab_z: float = 0.05            # m [E]

    # Twin fins — CANTED OUTWARD, standing on the booms. The cant is the recognition feature.
    fin_root_y: float = 2.10        # m [E] fin root offset
    fin_root_c: float = 3.45        # m [E]
    fin_tip_c: float = 1.35         # m [E]
    fin_height: float = 2.62        # m [E]
    fin_sweep_c4: float = 42.0      # deg [E]
    fin_x_c4: float = 13.80         # m [E] — aft enough that the fin TE sits near the
                                    #     stabilator TE, as photographed. At 13.10 the fin
                                    #     arm was too short to stabilise the aircraft in
                                    #     yaw (derived cn_beta went NEGATIVE).
    fin_z0: float = 0.55            # m [E]
    fin_cant: float = 6.0           # deg [E] outward cant from vertical

    # Ventral fins — the small blades under the tail booms.
    vent_root_c: float = 1.30       # m [E]
    vent_tip_c: float = 0.70        # m [E]
    vent_depth: float = 0.38        # m [E]
    vent_x_c4: float = 14.90        # m [E]
    vent_y: float = 1.55            # m [E]

    # Canopy — the high bubble the type is known for. Stands PROUD of the deck, never a
    # full-width ridge (the F-5E canopy lesson, fl-base-pack#29).
    canopy_x: float = 5.55          # m [E] dome centre
    canopy_len: float = 1.85        # m [E] half-length
    canopy_w: float = 0.46          # m [E] half-width
    canopy_h: float = 0.62          # m [E] rise above the deck — the Fulcrum's high
                                    #     bubble is a recognition feature; the first
                                    #     build rendered it as a small blister
    canopy_z: float = 0.72          # m [E] deck height at the cockpit

    # Dorsal spine — the FAMILY VARIABLE. The 9.12's is slim; the 9.13 Fulcrum-C's enlarged #1
    # fuel tank is the one visible airframe difference across the family.
    spine_x0: float = 6.90          # m [E]
    spine_x1: float = 13.40         # m [E]
    spine_w: float = 0.42           # m [E] half-width
    spine_h: float = 0.34           # m [E] rise above the deck  <-- the 9.13 knob
    spine_z: float = 0.42           # m [E]

    # Pitot boom (excluded from the length datum).
    boom_len: float = 1.20          # m [E]
    boom_r: float = 0.026
    boom_z: float = 0.10            # m [E]

    cockpit_z: float = 1.15         # m  camera anchor height above the axis

    # Central-body stations: (x/L, z_up, z_lo, y_half). [E] — a slender radar/cockpit body
    # forward, blending into the flat lifting centre-section between the nacelles. Nothing the
    # flight model consumes comes from here.
    stations: list = field(default_factory=lambda: [
        # ⚑ The aft half-widths are NOT free. The nacelle inner face sits at nac_y - nac_r
        # (~0.48 m) and its nozzle ring at ~0.58 m; if the body is narrower than that the two
        # lofts never touch and you can see daylight between them from behind. Keep the aft
        # stations >= 0.58 so the centre body always overlaps the nacelles.
        (0.000, 0.05, -0.05, 0.05),
        (0.030, 0.22, -0.20, 0.18),
        (0.080, 0.36, -0.30, 0.32),
        (0.140, 0.46, -0.38, 0.42),
        (0.200, 0.53, -0.42, 0.47),
        (0.280, 0.58, -0.44, 0.52),
        (0.340, 0.60, -0.46, 0.56),
        (0.420, 0.59, -0.50, 0.60),
        (0.520, 0.55, -0.54, 0.63),
        (0.650, 0.51, -0.56, 0.64),
        (0.800, 0.47, -0.54, 0.64),
        (0.900, 0.43, -0.50, 0.62),
        (1.000, 0.36, -0.44, 0.60),
    ])


def _wing_chords(cfg):
    """Root/tip chords from the published area and span at the [E] taper ratio.

    The reference area is to the CENTRELINE, so the trapezoid that closes on it is the reference
    trapezoid — the same one derive.py takes its MAC from. Keeping one taper number in both places
    is what makes the mesh and the flight model describe a single wing rather than two similar ones.
    """
    lam = cfg.wing_taper
    c_root = 2.0 * cfg.wing_area / (cfg.span * (1.0 + lam))
    c_tip = c_root * lam
    mac = (2.0 / 3.0) * c_root * (1.0 + lam + lam * lam) / (1.0 + lam)
    semi = cfg.span / 2.0
    return c_root, c_tip, mac, semi


def _simple_ring(bm, x, z_up, z_lo, y_half, steps=12, power=2.4):
    """A plain superelliptic station ring — used by the small add-on lofts (spine, boom).

    The AIRFRAME does not use this: its sections are the union outline built by _union_ring.
    """
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


def _lerp_table(table, f):
    """Interpolate a station table (fraction-of-length first) at fraction f."""
    if f <= table[0][0]:
        return table[0][1:]
    if f >= table[-1][0]:
        return table[-1][1:]
    for a, b in zip(table, table[1:]):
        if a[0] <= f <= b[0]:
            u = (f - a[0]) / max(1e-9, b[0] - a[0])
            return tuple(av + (bv - av) * u for av, bv in zip(a[1:], b[1:]))
    return table[-1][1:]


def _body_params(cfg, x):
    """Centre-body half-dimensions at station x: (z_up, z_lo, y_half)."""
    return _lerp_table(cfg.stations, x / cfg.length)


def _nac_params(cfg, x):
    """Nacelle bulge at station x: (y_centre, z_centre, half_width, half_height, exponent).

    Returns None ahead of the inlet lip. The bulge starts as a BOXY duct at the lip and relaxes
    to a round nozzle aft — the same wide-shallow-to-round walk the separate nacelle loft used,
    but now expressed as part of the body's own cross-section.
    """
    if x < cfg.nac_x0:
        return None
    f = min(1.0, (x - cfg.nac_x0) / max(1e-6, cfg.nac_x1 - cfg.nac_x0))
    tab = [
        # frac, y_centre, z_centre, half_w, half_h, exponent
        (0.00, cfg.nac_y, cfg.intake_z, cfg.intake_w, cfg.intake_h, cfg.intake_power),
        (0.10, cfg.nac_y, cfg.intake_z + 0.04, cfg.intake_w + 0.02, cfg.intake_h + 0.06, 5.0),
        (0.30, cfg.nac_y, cfg.intake_z + 0.16, cfg.nac_r * 0.94, cfg.nac_r * 0.86, 3.2),
        (0.55, cfg.nac_y, -0.12, cfg.nac_r, cfg.nac_r * 0.98, 2.3),
        (0.85, cfg.nac_y, -0.08, cfg.nac_r * 0.97, cfg.nac_r * 0.97, 2.0),
        (1.00, cfg.nac_y, -0.08, cfg.nac_r * 0.84, cfg.nac_r * 0.84, 2.0),
    ]
    return _lerp_table(tab, f)


def _inside(cfg, x, y, z):
    """Is (y, z) inside the airframe's cross-section at station x?

    The section is the UNION of the centre body and the two nacelle bulges. This is the whole
    point of the rewrite: one union means ONE closed outline per station, so the body and the
    nacelles cannot fail to meet. Previously they were three independent lofts that merely
    overlapped, and wherever the overlap lapsed you could see daylight between them.
    """
    z_up, z_lo, y_half = _body_params(cfg, x)
    if y_half > 1e-6:
        zc = 0.5 * (z_up + z_lo)
        zh = 0.5 * (z_up - z_lo)
        if zh > 1e-6:
            n = cfg.body_power
            if (abs(y / y_half) ** n + abs((z - zc) / zh) ** n) <= 1.0:
                return True
    nac = _nac_params(cfg, x)
    if nac is not None:
        ny, nz, rw, rh, npow = nac
        if rw > 1e-6 and rh > 1e-6:
            for s in (1.0, -1.0):
                if (abs((y - s * ny) / rw) ** npow + abs((z - nz) / rh) ** npow) <= 1.0:
                    return True
    return False


def _union_ring(bm, cfg, x, steps=34, samples=200):
    """One station ring: the outer boundary of the union, sampled radially.

    Sampled rather than solved because the union is NOT star-shaped — a ray heading down and
    outboard leaves the centre body and re-enters a nacelle bulge, so a bisection would stop at
    the first boundary and cut the nacelle off. Taking the LARGEST inside sample along each ray
    gives the true outer outline.
    """
    z_up, z_lo, _ = _body_params(cfg, x)
    z0 = 0.5 * (z_up + z_lo)
    reach = cfg.nac_y + cfg.nac_r + max(abs(z_up), abs(z_lo)) + 0.6
    verts = []
    for i in range(steps):
        th = 2.0 * math.pi * i / steps
        cy, cz = math.cos(th), math.sin(th)
        best = 0.0
        for j in range(1, samples + 1):
            tt = reach * j / samples
            if _inside(cfg, x, cy * tt, z0 + cz * tt):
                best = tt
        verts.append(bm.verts.new(Vector((x, cy * best, z0 + cz * best))))
    return verts


def _body(cfg, bm):
    """The blended airframe: centre body and nacelles as ONE lofted surface.

    Stations are densified around the inlet lip, where the section changes fastest.
    """
    xs = sorted(set(
        [s[0] * cfg.length for s in cfg.stations]
        + [cfg.nac_x0 + d for d in (-0.30, 0.0, 0.25, 0.60, 1.10, 1.90, 3.00, 4.40)]
        + [cfg.nac_x1 - d for d in (2.40, 1.20, 0.45, 0.0)]))
    xs = [x for x in xs if 0.0 <= x <= cfg.length]
    rings = [_union_ring(bm, cfg, x) for x in xs]
    _skin(bm, rings, cap_front=True, cap_rear=True)


def _intake_recess(cfg, bm, side):
    """Recess the inlet mouth so it reads as a duct rather than a painted-on rectangle."""
    ny, nz, rw, rh, npow = _nac_params(cfg, cfg.nac_x0)
    rings = []
    for dx, sc in ((0.0, 1.0), (0.22, 0.86), (0.60, 0.72)):
        ring = []
        for i in range(24):
            a = 2.0 * math.pi * i / 24
            c, s = math.cos(a), math.sin(a)
            yy = side * ny + rw * sc * math.copysign(abs(c) ** (2.0 / npow), c)
            zz = nz + rh * sc * math.copysign(abs(s) ** (2.0 / npow), s)
            ring.append(bm.verts.new(Vector((cfg.nac_x0 + dx, yy, zz))))
        rings.append(list(reversed(ring)))
    _skin(bm, rings, cap_front=False, cap_rear=True)


def _lerx(cfg, bm, side, x_le_root, c_root, y_in):
    """One leading-edge root extension: a thin, highly swept blend from the body to the wing root.

    Its trailing edge MEETS the wing root leading edge, so the two surfaces are continuous — the
    B-1B's second shape bug was exactly this kind of gap (glove tip chord and panel root chord
    placed independently, leaving 5.3 m of daylight at the pivot).
    """
    # ⚑ SPANS FROM THE BODY SIDE (y_in) TO THE WING ROOT, not from the centreline. Built from
    # y = 0 it lies entirely inside the fuselage and never appears in the planform — which is
    # exactly the bug the B-1B hit with its glove ("3.85 m semi-span against a 5.75 m body
    # half-width, so it sat entirely INSIDE the fuselage"), repeated here and caught the same way:
    # by rendering the top view and looking at it.
    y_out = cfg.wing_root_y
    tan_lerx = math.tan(math.radians(cfg.sweep_lerx))
    steps = 7
    rings = []
    for i in range(steps + 1):
        f = i / steps
        y = side * (y_in + f * (y_out - y_in))
        x_le = cfg.lerx_x0 + (f * (y_out - y_in)) * tan_lerx
        x_te = x_le_root + c_root * 0.0 + (x_le_root - x_le) * 0.0 + x_le_root
        # The LERX trailing edge runs to the wing root LE station, closing the blend.
        x_te = x_le_root
        if x_te <= x_le:
            x_te = x_le + 0.05
        half_t = cfg.lerx_thick * (1.0 - 0.65 * f)
        ring = []
        n = 8
        for j in range(n + 1):                      # upper surface, LE -> TE
            xc = j / n
            ring.append((x_le + xc * (x_te - x_le), half_t * math.sin(math.pi * min(1.0, xc * 1.3))))
        for j in range(n - 1, 0, -1):               # lower surface, TE -> LE
            xc = j / n
            ring.append((x_le + xc * (x_te - x_le), -half_t * math.sin(math.pi * min(1.0, xc * 1.3))))
        rings.append([bm.verts.new(Vector((px, y, cfg.lerx_z + pz))) for (px, pz) in ring])
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                f4 = (a[j], b[j], b[k], a[k]) if side < 0 else (a[j], a[k], b[k], b[j])
                bm.faces.new(f4)
            except ValueError:
                pass


def _panel_at(bm, x_c4_root, y_root, semi, root_c, tip_c, sweep_c4, thick,
              z0=0.0, dihedral=0.0, side=1.0, cant=0.0, vertical=False):
    """A lifting surface whose ROOT sits at a lateral offset, optionally CANTED.

    `loft.panel` roots every surface on the plane of symmetry and grows fins straight up. This
    aircraft needs neither: its wings root on the nacelle shoulder and its fins are canted outward
    on booms. Same quarter-chord positioning convention as loft.panel, so planform data still goes
    in the way it is published.
    """
    sections, steps = 9, 14
    ca, sa = math.cos(math.radians(cant)), math.sin(math.radians(cant))
    rings = []
    for i in range(sections + 1):
        f = i / sections
        span_pos = f * semi
        chord = root_c + (tip_c - root_c) * f
        x_c4 = x_c4_root + span_pos * math.tan(math.radians(sweep_c4))
        x_le = x_c4 - 0.25 * chord
        prof = []
        for j in range(steps + 1):
            xc = j / steps
            prof.append((x_le + xc * chord, naca_symmetric(xc, thick) * chord))
        for j in range(steps - 1, 0, -1):
            xc = j / steps
            prof.append((x_le + xc * chord, -naca_symmetric(xc, thick) * chord))
        ring = []
        for (px, half_t) in prof:
            if vertical:
                # Fin: span runs up, canted outward by `cant`; thickness runs across.
                y = side * (y_root + span_pos * sa) + half_t * ca
                z = z0 + span_pos * ca - side * half_t * sa * side
                ring.append(bm.verts.new(Vector((px, y, z))))
            else:
                y = side * (y_root + span_pos)
                z = z0 + span_pos * math.tan(math.radians(dihedral)) + half_t
                ring.append(bm.verts.new(Vector((px, y, z))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            k = (j + 1) % n
            try:
                f4 = (a[j], b[j], b[k], a[k]) if side > 0 else (a[j], a[k], b[k], b[j])
                bm.faces.new(f4)
            except ValueError:
                pass
    try:
        bm.faces.new(rings[-1] if side > 0 else list(reversed(rings[-1])))
    except ValueError:
        pass


def _canopy(cfg, bm):
    """The high bubble canopy. Hand-lofted latitude rings — see the module docstring."""
    lats, steps = 6, 14
    rings = []
    for i in range(1, lats):
        th = math.pi * i / lats
        r, z = math.sin(th), math.cos(th)
        ring = []
        for j in range(steps):
            a = 2.0 * math.pi * j / steps
            ring.append(bm.verts.new(Vector((
                cfg.canopy_x + cfg.canopy_len * z,
                cfg.canopy_w * r * math.sin(a),
                cfg.canopy_z + cfg.canopy_h * r * math.cos(a)))))
        ring.reverse()
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
    xs = [cfg.spine_x0, cfg.spine_x0 + 1.4, (cfg.spine_x0 + cfg.spine_x1) / 2.0,
          cfg.spine_x1 - 1.4, cfg.spine_x1]
    heights = [cfg.spine_h * f for f in (0.55, 1.00, 0.95, 0.75, 0.40)]
    rings = [_simple_ring(bm, x, cfg.spine_z + h, -0.05, cfg.spine_w, steps=10)
             for x, h in zip(xs, heights)]
    _skin(bm, rings, cap_front=True, cap_rear=True)


def _boom(cfg, bm):
    rings = []
    for x in (-cfg.boom_len, 0.50):
        ring = []
        for i in range(8):
            a = 2.0 * math.pi * i / 8
            ring.append(bm.verts.new(Vector((x, cfg.boom_r * math.cos(a),
                                             cfg.boom_z + cfg.boom_r * math.sin(a)))))
        rings.append(ring)
    _skin(bm, rings, cap_front=True, cap_rear=True)


def build_airframe(cfg, name):
    c_root, c_tip, mac, semi = _wing_chords(cfg)
    exposed = semi - cfg.wing_root_y
    print(f"{cfg.ident}: wing closes at c_root {c_root:.3f} m, c_tip {c_tip:.3f} m, "
          f"MAC {mac:.3f} m (taper {cfg.wing_taper}); exposed semi-span {exposed:.3f} m "
          f"from the nacelle at y {cfg.wing_root_y:.2f}")

    # widest body half-width, so the LERX can start where the fuselage actually ends
    body_half = max(s[3] for s in cfg.stations)   # LERX starts where the centre body ends

    bm = bmesh.new()
    _body(cfg, bm)
    _canopy(cfg, bm)
    _spine(cfg, bm)
    _boom(cfg, bm)

    sweep_c4 = math.degrees(math.atan(
        math.tan(math.radians(cfg.sweep_le)) - 0.25 * (c_root - c_tip) / semi))
    x_c4_root = cfg.wing_x_le_root + 0.25 * c_root

    for side in (1.0, -1.0):
        _intake_recess(cfg, bm, side)
        _lerx(cfg, bm, side, cfg.wing_x_le_root, c_root, body_half)
        # Wing panel: rooted ON the nacelle, so only the EXPOSED span is built. The chord at the
        # root station is interpolated on the reference trapezoid, which keeps the built planform
        # identical to the one the closure line above prints.
        c_at_root = c_root + (c_tip - c_root) * (cfg.wing_root_y / semi)
        _panel_at(bm, x_c4_root + cfg.wing_root_y * math.tan(math.radians(sweep_c4)),
                  cfg.wing_root_y, exposed, c_at_root, c_tip, sweep_c4, cfg.wing_thick,
                  z0=cfg.wing_z, dihedral=cfg.dihedral, side=side)
        _panel_at(bm, cfg.stab_x_c4, cfg.stab_root_y, cfg.stab_semi, cfg.stab_root_c,
                  cfg.stab_tip_c, cfg.stab_sweep_c4, 0.06, z0=cfg.stab_z, side=side)
        _panel_at(bm, cfg.fin_x_c4, cfg.fin_root_y, cfg.fin_height, cfg.fin_root_c,
                  cfg.fin_tip_c, cfg.fin_sweep_c4, 0.07, z0=cfg.fin_z0, side=side,
                  cant=cfg.fin_cant, vertical=True)
        _panel_at(bm, cfg.vent_x_c4, cfg.vent_y, cfg.vent_depth, cfg.vent_root_c,
                  cfg.vent_tip_c, 30.0, 0.08, z0=-0.42, side=side,
                  cant=180.0, vertical=True)

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
