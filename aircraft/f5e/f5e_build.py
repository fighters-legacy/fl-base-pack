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
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

# Shared procedural-mesh helpers. The library lives in the repo, not on Blender's Python path, so
# add it from this file's location (aircraft/f5e/ -> repo root -> tools/meshlib/src). No install
# step; works under `blender --background`.
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "meshlib" / "src"))
from fl_meshlib import export, loft, scene, uvatlas  # noqa: E402
from fl_meshlib.curves import smoothstep as _smoothstep  # noqa: E402
from fl_meshlib.damage import battle_damage  # noqa: E402
from fl_meshlib.stations import interp_table  # noqa: E402

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
NOSE_BLEND_T = 0.16            # x/L [E] radome (circular) -> traced forebody. See _nose_section.
SILL_EASE    = 2.2             # [E] cockpit-sill ease-in exponent. See _spine_top: 1.0 (linear)
                               #     is what made the canopy a flat ridge instead of a bubble.
WINDSCREEN_F = 0.14            # [E] fraction of the canopy span the windscreen occupies

# ═══ LATERAL AIR INTAKES ═══════════════════════════════════════════════════════════════════ [E] ═
#
# The F-5E's signature feature, and until now entirely absent: the loft ran smooth past the intake
# station and the aircraft read as a blob with wings.
#
# NASA Table I does not dimension the inlets, and the 3-view's own planform outline ALREADY INCLUDES
# the intake fairing -- the traced y_half peaks at 0.645 m at x/L 0.46, which is exactly the "intake
# fairing region, widest" note in STATIONS_FUS. So the body is already as wide as it should be;
# adding a nacelle on top of that would double-count the width. What the traced outline CANNOT carry
# is the sharp-edged detail: the cowl lip, and the dark recessed aperture behind it.
#
# These are therefore [E] -- judgement calls, shaped to the published outline and cross-checked
# against public-domain photography (Northrop assembly-line shots and CC0 museum walk-arounds; see
# SOURCES.md). Like the canopy and the fuselage cross-section, they are VISUAL ONLY: the flight model
# reads nothing from this file.
#
# Modelled as a closed solid overlapping the fuselage loft, not a boolean cut: both are closed and
# outward-facing, so the buried inboard faces are simply never seen.
INTAKE_X0     = 0.415   # x/L  cowl lip. Just aft of the canopy, ahead of the wing root.
INTAKE_X1     = 0.660   # x/L  where the fairing has faded back into the flank.
INTAKE_ZC     = 0.28    # m    aperture centre, above the fuselage reference line
INTAKE_HZ     = 0.33    # m    aperture half-height
INTAKE_HY     = 0.20    # m    cowl half-width; the inboard half stays buried in the fuselage
INTAKE_PROUD  = 0.13    # m    how far the cowl lip stands proud of the traced flank
INTAKE_DEPTH  = 0.26    # m    how far the inlet face is recessed behind the lip -- this is what
                        #      makes the aperture read as a hole rather than a painted-on panel
# The boundary-layer splitter gap between cowl and fuselage is NOT modelled: it is a few centimetres
# across and vanishes at any gameplay range. The lip and the recess are what make the jet readable.

# Surface placement stations (planform work, unchanged from the validated planform build)
WING_X_LE     = 5.95      # m   wing leading-edge root station
WING_Z        = -0.12     # m   low-mid wing
HT_X_C4       = 13.10     # m   horizontal tail quarter-chord station
VT_X_C4       = 11.90     # m   vertical tail quarter-chord station
TIP_RAIL_LEN  = 2.10      # m   wingtip AIM-9 rail (part of the airframe; see SOURCES.md)

MAT_AIRFRAME  = "f5e_airframe"
TEX_DIFFUSE   = "../../textures/f5e_diffuse.ktx2"
TEX_ORM       = "../../textures/f5e_orm.ktx2"


# ─── Fuselage station lookup ────────────────────────────────────────────────────────────────────
def _fus_at(t):
    """Interpolate the traced station table at x/L = t. Returns (z_up, z_lo, y_half)."""
    return interp_table(STATIONS_FUS, t)


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

    # NOT linear. A straight ramp from the windshield base (0.50 m) to the aft fairing (0.97 m)
    # climbs at the same rate as the glass above it, so the canopy never stands proud -- the loft
    # produced one long flat-topped ridge merging into the spine, with no bubble and no windscreen.
    # The real skin stays low along the cockpit sill and only rises BEHIND the cockpit, into the
    # dorsal decking ahead of the intakes (USAF 74-00513, a clean side view). Ease-in does that:
    # slow under the canopy, steep at the aft end, and it still meets the traced skin exactly at
    # both ends -- so no traced value is overridden, only the curve BETWEEN them.
    return a + (b - a) * ((t - c0) / (c1 - c0)) ** SILL_EASE


def _nose_section(t, top, lo, w):
    """Section centre and half-height at x/L = t, with the RADOME treated as a body of revolution.

    The raw trace disagrees with itself at the nose. At x/L 0.03 it gives a section 0.12 m wide and
    0.315 m TALL -- a vertical blade -- because the plan-view half-width and the side-view contour
    were sampled independently and do not agree that close to the tip, where both are a few pixels of
    ink. Lofted, that produced a nose whose belly plunged into a hanging chin within the first half
    metre while the spine stayed flat. Public-domain photography (USAF 73-02896, and the CC0
    walk-arounds) shows the opposite: a slender, near-conical radome with only a gentle droop.

    A radome CANNOT be a blade -- it is a fairing over a circular radar antenna, so its sections are
    circular. That is a physical fact, not a styling choice, and it is the constraint used here: in
    the radome region the half-height is taken from the traced PLAN half-width (the more trustworthy
    of the two near the tip, since the planform is what NASA's Table I closes against), and the
    section centre rides a smooth droop line from the tip. By NOSE_BLEND_T the fuselage is deep and
    genuinely non-circular -- gun bay, nose-gear well, cockpit floor -- and the trace is trusted
    fully again. Between the two, blend.
    """
    cz_tr = (top + lo) / 2.0
    hh_tr = max((top - lo) / 2.0, 0.02)
    if t >= NOSE_BLEND_T:
        return cz_tr, hh_tr

    top_b = _spine_top(NOSE_BLEND_T)
    lo_b = _fus_at(NOSE_BLEND_T)[1]
    cz_rd = ((top_b + lo_b) / 2.0) * (t / NOSE_BLEND_T)   # droop: 0 at the tip -> traced centreline
    hh_rd = max(w, 0.02)                                  # circular: half-height = half-width

    u = _smoothstep(t / NOSE_BLEND_T)
    return cz_rd + (cz_tr - cz_rd) * u, hh_rd + (hh_tr - hh_rd) * u


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
        w = max(w, 0.02)
        cz, hh = _nose_section(t, top, lo, w)
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


def _intake_section(t, steps=12):
    """Cross-section of the intake cowl at x/L = t: (centre_y, centre_z, half_y, half_z, ring_uv).

    The cowl hugs the flank. Its OUTER surface sits `INTAKE_PROUD` beyond the traced half-width at
    the lip and fades back to flush by INTAKE_X1; its inboard half is buried inside the fuselage.
    """
    w = _fus_at(t)[2]                                        # traced fuselage half-width here
    fade = 1.0 - _smoothstep((t - INTAKE_X0) / (INTAKE_X1 - INTAKE_X0))
    outer = w + INTAKE_PROUD * fade
    hy = INTAKE_HY
    hz = INTAKE_HZ * (0.35 + 0.65 * fade)                    # tall at the lip, faded into the flank aft
    return outer - hy, INTAKE_ZC, hy, max(hz, 0.02)


def _intake_ring(bm, t, side, scale=1.0, dx=0.0, steps=12):
    """One rounded-rectangle ring of the cowl, on `side` (+1 port, -1 starboard in Blender -Y)."""
    cy, cz, hy, hz = _intake_section(t)
    x = t * LENGTH + dx
    ring = []
    for j in range(steps):
        th = 2.0 * math.pi * j / steps
        c, sn = math.cos(th), math.sin(th)
        n = 3.2                                              # rounded rectangle, like the real lip
        y = hy * scale * math.copysign(abs(c) ** (2.0 / n), c)
        z = hz * scale * math.copysign(abs(sn) ** (2.0 / n), sn)
        ring.append(bm.verts.new(Vector((x, side * (cy + y), cz + z))))
    return ring


def _intakes(bm, stations=7):
    """Lateral inlets: a cowl lofted along the flank, with a recessed aperture behind a sharp lip.

    Built per side as a closed solid that overlaps the fuselage. Two pieces meet at the lip ring:
      * the OUTER shell, lofted aft from the lip until it is buried in the flank at INTAKE_X1;
      * the RECESS, stepping inward and aft from that same lip ring to a capped throat -- the dark
        hole. Without it the lip is just a raised panel line and the jet still reads wrong.
    """
    for side in (1.0, -1.0):
        flip = side < 0.0                                    # mirrored side needs reversed winding
        lip = _intake_ring(bm, INTAKE_X0, side)

        # Outer shell: lip -> aft, fading into the flank.
        prev = lip
        for i in range(1, stations + 1):
            t = INTAKE_X0 + (INTAKE_X1 - INTAKE_X0) * (i / stations)
            ring = _intake_ring(bm, t, side)
            loft.bridge(bm, prev, ring, flip)
            prev = ring
        try:                                                 # aft cap: buried in the fuselage, unseen
            bm.faces.new(prev if not flip else list(reversed(prev)))
        except ValueError:
            pass

        # Recess: the same lip ring, stepped in and aft to a throat, then capped. Winding is the
        # opposite of the outer shell -- these faces are seen from IN FRONT, looking into the duct.
        throat = _intake_ring(bm, INTAKE_X0, side, scale=0.72, dx=INTAKE_DEPTH)
        loft.bridge(bm, lip, throat, not flip)
        try:
            bm.faces.new(list(reversed(throat)) if not flip else throat)
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
        # Plan shape. The old sin(f*pi)^0.5 was a symmetric lens: zero width at BOTH ends, so the
        # canopy came to a point at the front and there was no windscreen at all. A windscreen base
        # is nearly as wide as the canopy itself -- it is a screen, not a spike. So: come up to full
        # width fast over the windscreen, hold it through the glass, then taper into the long aft
        # fairing (which does not reach zero -- it fairs into the spine).
        w = CANOPY_HALFW * _smoothstep(f / WINDSCREEN_F) * (1.0 - 0.80 * _smoothstep((f - 0.70) / 0.30))
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
    _intakes(bm)
    _canopy(bm)

    # Wing — positioned by its published quarter-chord line.
    loft.panel(bm, WING_X_LE + 0.25 * ROOT_CHORD, SPAN / 2.0, ROOT_CHORD, TIP_CHORD,
               SWEEP_C4, THICKNESS, dihedral=0.0, z0=WING_Z)
    _tip_rails(bm)

    # Horizontal tail — all-moving, and it droops 4 degrees.
    ht_exposed_span = math.sqrt(2.88 * 3.07)                       # 2.97 m, from NASA's exposed AR
    ht_root = HT_TIP_CHORD / HT_TAPER                              # 1.539 m at the fuselage side
    # Extrapolate the taper line inboard to the centreline so the surface meets the fuselage.
    w_tail = _fus_at(HT_X_C4 / LENGTH)[2]          # 0.665 -- NASA tail-span arithmetic
    f_side = w_tail / (HT_SPAN / 2.0)
    ht_c0 = (ht_root - HT_TIP_CHORD * f_side) / (1.0 - f_side)
    loft.panel(bm, HT_X_C4, HT_SPAN / 2.0, ht_c0, HT_TIP_CHORD, HT_SWEEP_C4, 0.04,
               dihedral=HT_DIHEDRAL, z0=0.10)

    # Vertical tail — exposed AR 1.22 on exposed area 3.85 m^2.
    vt_height = math.sqrt(VT_AR * VT_AREA)                          # 2.167 m
    vt_root = VT_TIP_CHORD / VT_TAPER                               # 2.845 m
    loft.panel(bm, VT_X_C4, vt_height, vt_root, VT_TIP_CHORD, VT_SWEEP_C4, 0.04,
               vertical=True, z0=0.55)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)               # outward: CCW from outside
    return _commit(bm, name)


def _commit(bm, name: str) -> bpy.types.Object:
    """Finish the airframe bmesh into an object, with the F-5E's placeholder UVs and grey material."""
    obj = scene.finish_mesh(bm, name)
    uvatlas.planar_uvs(obj, LENGTH, SPAN)
    scene.principled_material(obj, MAT_AIRFRAME, (0.42, 0.44, 0.47, 1.0), 0.15, 0.55)
    return obj


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="aircraft/f5e")
    ap.add_argument("--id", default="f5e")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    aid = args.id

    scene.clear_scene()
    body = build_airframe(aid)
    tris = len(body.data.polygons)

    # Base mesh + its damage state, in ONE file. The `_b` node MUST ship beside its base.
    dmg = battle_damage(body, MAT_AIRFRAME)
    export.export_glb(out / f"{aid}.glb", [body, dmg])
    export.patch_textures(out / f"{aid}.glb", TEX_DIFFUSE, TEX_ORM)
    bpy.data.objects.remove(dmg)

    # LODs are separate FILES, not nodes. (fl-base-pack's CONTRIBUTING.md said nodes; it was wrong.)
    for i, ratio in enumerate((0.50, 0.20, 0.05)):
        lod = export.decimate(body, ratio, f"{aid}_lod{i}")
        export.export_glb(out / f"{aid}_lod{i}.glb", [lod])
        export.patch_textures(out / f"{aid}_lod{i}.glb", TEX_DIFFUSE, TEX_ORM)
        bpy.data.objects.remove(lod)

    # Shadow proxy: convex hull, NO materials.
    shadow = scene.convex_hull(body, f"{aid}_shadow")
    export.export_glb(out / f"{aid}_shadow.glb", [shadow])

    # Cockpit: must contain a node named exactly `camera_anchor` -- the renderer looks for it by name.
    anchor = scene.empty("camera_anchor", location=(
        (CANOPY_SPAN[0] + 0.35 * (CANOPY_SPAN[1] - CANOPY_SPAN[0])) * LENGTH, 0.0, _fus_at(0.30)[0] - 0.25))
    export.export_glb(out / f"{aid}_cockpit.glb", [anchor])

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
