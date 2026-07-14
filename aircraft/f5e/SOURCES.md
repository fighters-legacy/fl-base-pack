# F-5E Tiger II — data provenance

Every number in `f5e.toml` and `f5e.expect.toml` traces to a row in this file.

**Clean-room rule.** Public sources only: USAF technical orders, NASA technical reports, and
manufacturer/USAF characteristics charts. **No value in this aircraft is taken from any flight
simulator, game, or commercial 3D model** — not DCS, not Falcon, not War Thunder, not X-Plane.
Where a figure could only be found in such a source, it is recorded here as *rejected*, with the
reason. See `docs/legal/aircraft-likeness.md` in the engine repo.

Each row is tagged:

- **P** — *published*: read directly from a primary source.
- **D** — *derived*: computed from published values by a stated method. Reproducible.
- **E** — *engineering estimate*: not published and not derivable. A judgement call, flagged as such.

The aircraft modelled is the **pre-IHQ F-5E** — the configuration the NASA geometry and the
T.O. performance charts both describe. Later blocks add a shark nose and wing leading-edge
extensions (LEX); the T.O. states these "improve lift and maximum turn rate" but **publishes no
quantified change**, and the LEX wing area is not published anywhere. Modelling them would require
inventing numbers, so we do not.

---

## Primary sources

| Key | Document |
|---|---|
| **TO** | *T.O. 1F-5E-1, USAF Series F-5E/F Flight Manual*, 1 Aug 1978 (and 1984 rev.) — <https://archive.org/details/F5EFFlightManual> |
| **NASA-SPIN** | *Spin-Tunnel Investigation of a 1/20-Scale Model of the Northrop F-5E Airplane*, NASA Langley, 28 Jun 1977 — <https://ntrs.nasa.gov/citations/19980227417> |
| **TO-84** | T.O. 1F-5E-1, 1984 rev. (page-image scan; the charts are graphics, so several numbers below were read off the rendered page, not the OCR) — <https://archive.org/details/T.O.1F5E11984OCR> |
| **SP-468** | Loftin, *Quest for Performance*, NASA SP-468, App. A Table V — original host dead; **unverified at source** |
| **WIKI** | Wikipedia, *Northrop F-5* (cites Jane's 1976–77 pp. 344–346) — cross-check only |

---

## Geometry — all **P**, from NASA-SPIN Table I

NASA-SPIN is the best public F-5E geometry source and it is a NASA document, which is why it is
preferred over the Jane's/Wikipedia spec block wherever the two differ.

| Field | Value | Source |
|---|---|---|
| `wing_area_m2` | 17.30 (186.20 ft²) | **P** NASA-SPIN Table I |
| `wingspan_m` | 8.13 (26.67 ft), **without** tip missiles | **P** NASA-SPIN Table I |
| `mac_m` | 2.456 (96.68 in) | **P** NASA-SPIN Table I |
| aspect ratio | 3.82 | **P** NASA-SPIN (WIKI says 3.86 — NASA preferred) |
| quarter-chord sweep | 24.0° | **P** NASA-SPIN Table I |
| taper ratio | 0.19 | **P** NASA-SPIN Table I |
| airfoil | NACA 65A004.8 (mod.) | **P** NASA-SPIN Table I |

Overall length 14.68 m, tail areas and control-surface areas are in NASA-SPIN Table I and are used
for the DATCOM moment derivation (below), though the schema has no field for them.

### The tail-area trap, and why it is not a trap

NASA Table I *looks* self-contradictory for the horizontal tail: span 4.30 m, "area (exposed)"
3.07 m², aspect ratio 2.88 — yet 4.30² / 3.07 = 6.02, not 2.88. The tempting reading is that the
AR is quoted on a **gross** area of 6.42 m², and taking it would change `cm_alpha` by **75%** and
`cm_q` by **109%**.

That reading is **wrong**, and the table is not inconsistent. Read off the page image rather than
the OCR, *area, taper ratio and aspect ratio are each explicitly labelled "(exposed)"*, while the
4.30 m span row is not. The AR is computed on the **exposed span** — the panels outboard of the
fuselage — not tip-to-tip. Everything then reconciles:

    exposed span = sqrt(2.88 x 3.07) = 2.97 m  =>  fuselage width at tail = 1.33 m  (plausible)

and an independent cross-check **that never touches the aspect ratio** confirms it: root chord =
tip / taper = 0.508 / 0.33 = 1.539 m, so exposed area = 2.97 x (1.539 + 0.508)/2 = **3.04 m²**
against the published **3.07** — 0.9%. The same check on the vertical tail is exact (3.85 m²).

`derive.py` still prints the cost of the wrong reading, so that if anyone ever "fixes" `S_H` to
6.42 they see immediately what it does.

**The tail moment arm remains NOT PUBLISHED** — verified against the page image, not just the OCR.
NASA prints no fuselage stations and no CG-to-tail distance. It stays an estimate, and it is the
single largest input uncertainty in the moment derivatives.

---

## Mass

| Field | Value | Source |
|---|---|---|
| `mass_kg` | **4832** (10,650 lb) | **D** — see below |
| `fuel_kg` | **1996** (4,400 lb) | **P** TO "Fuel Quantity Data": 677 gal usable × 6.5 lb/gal (JP-4). The manual states the density, so no assumption is made. |

**`mass_kg` derivation (D).** The schema defines effective mass as `mass_kg + fuel + stores`, so
`mass_kg` is the operating empty weight. TO Section I gives a typical gross weight of **15,050 lb**
(with wingtip launcher rails, no pylons; includes pilot, oil, full ballast, **full internal JP-4**,
no ammunition). Subtracting full usable internal fuel:

    10,650 lb = 15,050 lb (TO typical gross, full fuel) − 4,400 lb (TO full usable internal)

Cross-check: WIKI's empty weight of 9,583 lb plus pilot, oil, ballast and tip rails lands in the same
place. The two agree, from independent sources.

> Aircraft modified per T.O. 1F-5-921 carry **694 gal usable (4,511 lb)**. We model the unmodified
> tank set. Stated here because two different internal fuel loads exist and the difference is real.

## Moments of inertia — all **P**, from NASA-SPIN Table II

Inertias are almost never published. NASA-SPIN gives full-scale Ix/Iy/Iz for four real loadings,
which removes the usual radius-of-gyration guesswork entirely.

| Field | Value | Source |
|---|---|---|
| `ixx_kg_m2` | 4610 (3,400 slug·ft²) | **P** NASA-SPIN Table II |
| `iyy_kg_m2` | 52063 (38,400) | **P** NASA-SPIN Table II |
| `izz_kg_m2` | 55317 (40,800) | **P** NASA-SPIN Table II |

**Which loading (D).** NASA-SPIN tabulates four. The engine holds inertia fixed (it does not vary
with fuel or stores), so the right choice is the one nearest the aircraft's fighting state. We take
**"clean, 55% internal fuel, ammunition fired — 13,000 lb"**, because the TO's own turn and Ps charts
are flown at *2× AIM-9, full ammo, one-half internal fuel* ≈ **13,530 lb** (derived below), and
13,000 lb is the closest published match.

Note NASA-SPIN's *"with missiles"* loading has **Ix = 7,118** — 54% higher, because wingtip missiles
are a long way out on the roll axis. The engine cannot express a store-dependent inertia today, so
roll acceleration with tip missiles will be optimistic. Recorded as a known limitation, not hidden.

---

## Propulsion

Two General Electric **J85-GE-21** afterburning turbojets (**P**, TO Section I). The TO never names a
sub-variant (-21A / -21B); the block→sub-variant mapping is **not published** and is not asserted here.

| | Per engine | Total (×2) | Source |
|---|---|---|---|
| Military (dry), SL static | **3,250 lbf** = 14.457 kN | **28.91 kN** | **P** TO Section I |
| Maximum (AB), SL static | **4,650 lbf** = 20.684 kN | **41.37 kN** | **P** TO Section I |

> ### The most important trap in this data set
>
> Wikipedia, GE's own marketing, and essentially every website give **3,500 / 5,000 lbf**. Those are
> the **bare-engine (uninstalled)** ratings. The TO's **3,250 / 4,650 lbf** are the **installed**
> ratings — inlet, nozzle and bleed losses included — and they are what the aircraft's published
> performance charts were computed from. Using the popular figure would bake a **~7% thrust error**
> into every derived value in this model while appearing perfectly well-sourced.

### Fuel flow — published, and the afterburner number is chart-read but validated

| Field | Value | Source |
|---|---|---|
| `fuel_flow_idle_kg_s` | **0.136** (18 lb/min) | **P** TO-84 chart FA3-1, printed as text: *"FUEL FLOW — (2) ENGINES: GROUND TAXI 18 LB/MIN"* |
| `fuel_flow_mil_kg_s` | **0.900** (119 lb/min) | **P** same box: *"STATIC MIL THRUST 119 LB/MIN"* |
| `fuel_flow_ab_kg_s` | **2.840** (~375 lb/min) | **D** chart FA8-1 (Combat Fuel Allowance), SL / 0.2 IMN — the lowest Mach curve published. ±3%. |

There is **no printed static AB fuel flow anywhere in the manual**, so the AB figure had to be read
off FA8-1. That read is validated against printed values on the same chart: its MIL panel reads
121 lb/min against the printed 119 (**1.7%**), and 157 lb/min at 0.8 IMN against the manual's own
worked example of 158 (**0.6%**). The implied AB/MIL fuel ratio is ~3.0, which is physically sane
for a J85 with afterburner.

**TSFC is not published** — the TO gives specific *range* (nm/lb), an airframe+engine quantity, and
never publishes thrust, so TSFC cannot be derived from within the document.

**Thrust vs Mach and altitude is NOT published.** Confirmed: the TO's entire performance appendix is
built on a drag-index + fuel-flow methodology and contains **no net-thrust curves**. The only NASA
J85-21 report is a compressor-rig study with no installed thrust deck. The `[engine.mil_thrust]` and
`[engine.ab_thrust]` tables in `f5e.toml` are therefore **D/E** — a derived turbojet model anchored to
the published SL static thrust above and calibrated against the published performance points in
`f5e.expect.toml`. The method is documented inline in `f5e.toml`. This is the single largest source of
uncertainty in the model and it is stated plainly rather than buried.

---

## Aerodynamics

**There is no public lift curve, drag polar, CL_max, or stability derivative set for the F-5E.**
Checked NTRS by API, not merely by web search. The only F-5E aero document on NTRS is NASA-SPIN,
which has geometry and inertia but **no force or moment coefficients**. NASA CR-2144 (*Aircraft
Handling Qualities Data*, the classic public derivative compendium) contains **no F-5 at all**.

Near-misses, recorded so nobody re-runs this search:

- **NASA TM X-62,339** — static aero of a 1/7-scale **F-5A** at M 0.20, α 0–90°. Exactly the right
  kind of data, but the *F-5A*, and subsonic only. Cited as Ref. 3 of NASA-SPIN; **full text could
  not be retrieved from NTRS.** Worth a document request — it would materially improve this model.
- **F-5E Shaped Sonic Boom Demonstrator** NASA reports exist, but that aircraft has a deliberately
  reshaped forebody. Not stock F-5E aero.

| Field | Value | Source |
|---|---|---|
| `CL_max` @ M 0.60 | **1.255** | **D** — from the TO's published max-lift point (5.2 G at 15,000 ft / M 0.60). Pure lift; no drag or thrust assumption. **Independently confirmed — see below.** |
| `alpha_stall_deg` | **17** | **D** — CL_max ÷ the lift-curve slope *at M 0.60* (4.247 /rad, Helmbold + Prandtl-Glauert) = 16.9°. It must use the compressible slope: the calibration point is at M 0.60, and the incompressible slope would put the stall ~2° too high. |
| `cd0` | 0.0200 | **P?** SP-468 App. A Table V — **cited via WIKI, unverified at source** (NASA's host is dead). The one drag number with a NASA lineage. Treat with caution. |
| max L/D | 10.0 | **P?** SP-468, same caveat |
| `[aero.moments]` (9 derivatives) | — | **D** — USAF DATCOM, from the NASA-SPIN geometry. Method documented inline in `f5e.toml`. |
| `[aero.cd_table]` | — | **D** — fitted to the TO's published Ps ladder. See the note below. |

### CL_max is confirmed by two unrelated documents

This is the strongest result in the data set and it is worth stating plainly.

`CL_max = 1.255` was derived from the **max-lift turn point** (5.2 G, 15,000 ft, M 0.60) — a combat
performance chart. Separately, the **stall-speed nomogram** (TO-84 Fig. 6-1, basis: *flight test,
idle thrust*) was traced and back-solved for CL_max at three gross weights:

| Gross weight | Vs clean (KIAS) | implied CL_max |
|---|---|---|
| 11,000 lb | 118 | 1.253 |
| 13,500 lb | 131 | 1.248 |
| 20,000 lb | 159 | 1.255 |

A different chart, a different flight condition, a different physical measurement, idle thrust
versus max thrust — and the answer agrees to **0.4%**. The `Vs ∝ √W` relation also falls out of the
trace rather than being imposed, which a misread nomogram would not do.

Both stall-speed points are now **gate rows in `f5e.expect.toml`**, which closes
fighters-legacy#54's named Phase-4 criterion ("flight model stall speed ... match design spec").

### Rejected: the LEX CL_max figures

The widely-circulated claim that the F-5E's LEX adds ~25% to CL_max (and the F-5A's ~10%) traces
back to a **DCS World flight-manual PDF**. It is not in the TO, not in NASA-SPIN, and not in any
primary source. **Rejected under the clean-room rule.** If you find these numbers quoted elsewhere,
assume sim-derived until proven otherwise.

## Control surfaces — all published, and two of them are surprising

T.O. 1F-5E-1 Section I, pp. 1-79/1-80. Both surprises change how the aircraft handles:

**The aileron limiter.** Full travel is 35° up / 25° down — but the manual states an *aileron
limiter, mechanically positioned by retraction of the landing gear, limits the aileron to* **one-half
travel**, and full travel requires *"additional stick force ... to override the aileron spring stop."*
Gear up — that is, all combat flight — normal authority is **half**. Section V additionally lists
"continuous 360° rolls with more than half aileron" and "exceeding the aileron spring stop except
for spin recovery" as **structural limits**.

So `max_aileron_deg = 17.5`, not 35. Authoring the placard maximum would give the player an F-5E
that rolls about twice as fast as the real one, in every fight, and it would look perfectly
well-sourced.

**The stabilator is asymmetric: 17° nose-up, 5° nose-down.** The schema has one scalar per axis and
cannot express that, so `max_elevator_deg = 17` (the nose-up figure — the one that governs pitch
authority and the G limit), and nose-down authority is consequently modelled 3.4× too generous.
Engine issue filed.

Rudder is 30° either side of neutral, though the manual notes in-flight deflection is
dynamic-pressure limited.

The **auto-flap schedule** is also fully published (Fig. 1-53: UP / 0-8 / 12-8 / 18-16 / 24-20,
scheduled on AOA and KIAS with hysteresis). The schema has no maneuvering-flap concept, so it is
recorded here and not modelled.

## Roll: the one thing nobody can check

**Roll rate is NOT PUBLISHED.** Confirmed against the complete Appendix I chart inventory — there is
no roll chart in any part of the manual — and against the entire NTRS F-5E corpus. The manual is
qualitative only: *"use of aileron (to the spring stop) produces high roll rates, particularly in
the 0.80 to 0.95 Mach region."*

So `cl_p` and `cl_da` are the only numbers in this model with **nothing whatsoever to check them
against**. They are DATCOM-derived from geometry and that is all. Roll-rate figures circulating
online do not trace to any primary source — treat them as rejected until someone produces a document.

Partial consolation: NASA *does* publish the roll inertia (Ixx), so once `cl_p`/`cl_da` are chosen,
the resulting roll rate is at least *computable* and can be sanity-checked against the manual's
qualitative claim. Note also that NASA's loading 4 (wing stores) has **Ixx 4.7× higher** than clean —
which is the real reason a loaded F-5E feels so different in roll, and which the engine cannot
currently express.

## Drag — a table, not a polar, and why

The engine's original drag model was a strictly parabolic polar (`cd0 + k·CL²`). The F-5E's published
Ps ladder **cannot be fitted by any value of `k`**: the implied induced-drag coefficient rises by a
factor of **3.5×** from 1 G to max lift, because a real wing's drag grows far faster than CL² as it
approaches stall. Fitting `k` to cruise gives an aircraft that sustains 3.9 G where the manual says
3.3; fitting it to the turn overstates cruise drag and wrecks range. That is what motivated
`[aero.cd_table]` (engine #820) — and it is also the form NASA publishes real aero data in.

### The fit is a measurement, not a tuning

`Ps = V·(T − D)/W`, and at **n = 3.3 the manual states Ps = 0**, which means **D = T exactly** there.
So the ladder pins the *shape* of CD(CL) **with no thrust assumption whatsoever** — only its absolute
level rides on T, and that is one scalar, not a curve.

Least squares over the five points, with `cd0` anchored at SP-468's published 0.0200:

    CD = 0.0200 + 0.0792·CL² + 0.1223·CL⁴          (within 2.9% at all five points)

| n | CL | CD fitted | CD published | err | best-fit parabola |
|---|---|---|---|---|---|
| 1.0 | 0.241 | 0.02503 | 0.02577 | 2.9% | 0.02892 |
| 2.0 | 0.483 | 0.04511 | 0.04480 | 0.7% | 0.05567 |
| 3.3 | 0.797 | 0.11955 | 0.11710 | 2.1% | 0.11711 |
| 4.0 | 0.966 | 0.20024 | 0.20273 | 1.2% | 0.16268 |
| 5.2 | 1.255 | 0.44866 | 0.44819 | 0.1% | 0.26113 |

**At max lift the real jet's drag is ~70% above what the best parabola predicts.** That gap is the
whole reason `[aero.cd_table]` exists.

### An independent cross-check that could have failed and did not

The fitted thrust level implies **T_ab(15,000 ft, M 0.60) = 29.19 kN**. The thrust deck — built from
*published sea-level static thrust and a standard turbojet lapse*, a different document and a
different method entirely — gives **29.25 kN**. **0.2% apart.** The drag model and the thrust model
were derived independently and they agree.

### Two corrections beyond the raw fit, both physical

**Separation drag is keyed to the lift fraction, not to CL.** The CL⁴ term is not classical induced
drag — it is the drag rise as the wing nears *its own* stall. CL_max falls with Mach (1.255 at M 0.6,
~1.10 at M 0.9), so at high Mach the wing is much closer to stalling at the same CL. The quartic term
is therefore written in `λ = CL / CL_max(M)`, which reduces exactly to the fitted form at M 0.60.

**Past the stall, drag keeps rising while lift collapses.** A naive `CD = f(CL)` would have drag
*follow lift back down* — claiming a fully stalled wing is cleaner than one at its lift peak, which
would let a departed aircraft accelerate. The post-stall region is **E** (no published F-5E post-stall
drag exists), but monotonic-rising is the only defensible shape and monotonic-falling is simply wrong.

### Validation against the published top speed

Scanning the full envelope at 36,000 ft, clean, afterburner: the model reaches **M 1.619** against the
T.O.'s published **1.63** — **0.7%**. (`fm-trim` currently reports this as "cannot hold level flight"
because of engine bug #825, which stops its speed search at the back side of the power curve. The
model is right; the tool is not, and the fix is filed.)

---

## Mesh — `f5e_build.py`

The airframe is **generated from published dimensions**, not modelled from a reference. Nothing in it
is traced from, derived from, or cleaned up out of another simulator, game, or commercial 3D model.
Run it with:

    blender --background --python aircraft/f5e/f5e_build.py -- --out aircraft/f5e

### What is published, and therefore correct

The **entire planform** is in NASA Table I, and it closes: root chord 3.5735 m, tip chord 0.6840 m
and span 8.13 m give a trapezoid of **17.307 m²** against the published wing area of **17.30 m²** —
0.04%. So the wing is not an interpretation; it is the published shape. Same for both tails: the
horizontal tail's 25° sweep, 0.33 taper and −4° **anhedral** (it droops — that is real), and the
fin's exposed area and aspect ratio.

The wingtip **launch rails are part of the airframe**, not stores. The T.O. quotes max level Mach for
"launcher rails only" (1.63) *and* "with tip missiles" (1.57) — the rails are present in both, so they
belong to the aeroplane. The missiles are stores and are not in the mesh.

### What is NOT published, and is therefore an estimate

Fuselage cross-sections, canopy shape and intake geometry. NASA gives length, and the tail width falls
out of the exposed-vs-total tail span (1.33 m) — but the cross-sections do not exist in any public
table. These are shaped by eye to the published length, height and tail width, and they are marked
**E** in `f5e_build.py`.

**They are the weakest part of this aircraft, and the side profile is not good enough.** From above the
model reads correctly, because that view is driven by the published planform. In profile it reads as a
dart rather than a Tiger: the belly line is wrong and the canopy is a blister.

### The fix, and why it is also better provenance

NASA's spin-tunnel report contains **Figure 1: a dimensioned 3-view drawing**. The likeness policy
explicitly permits *"declassified 3-view drawings and general-arrangement diagrams"* as references. So
the fuselage should be built from **stations sampled off that published 3-view**, rather than from the
superellipses currently in `f5e_build.py`.

That is both better-looking and better-sourced: it moves the fuselage from **E** to **P**, which is the
direction the policy wants. Tracked as a follow-up.

Nothing the flight model reads comes from the mesh, so this does not affect a single number above.

### No markings

Policy §4. No unit insignia, squadron badges, nose art or operator liveries. A generic aggressor-grey
scheme, applied through external `.ktx2` textures, never baked into geometry.

### Update: fuselage now traced from NASA Figure 1 — moved from E to P/D

The follow-up landed. The fuselage side profile is now **sampled programmatically off NASA Figure 1**
(the report's dimensioned 3-view, 1/20 scale in cm): column-scan of the drawing ink, dimension lines
and leader text masked, verified against overlay renders at every pass. Scale anchored to the printed
**73.15 cm overall length**; cross-checked against the printed MAC bar (12.27 cm = 2.454 m vs the
published 2.456 m, 0.1%) and the printed fin height (read 2.46 m vs printed 2.576 m — 4.5%, the fin
tip arrowhead is ambiguous in the scan; the fin itself is built from published area/AR, not the trace).

`STATIONS_FUS` in `f5e_build.py` is the result: 21 stations of (z_upper, z_lower, y_half), each tagged
**P** (traced), **D** (interpolated across a dimension-line pollution or under the fin, or the tail
width from NASA's own tail-span arithmetic), with the canopy span and its glass bump measured rather
than invented. The only remaining **E** values in the whole mesh: canopy half-width (~0.34 m, read
from the planform outline), the superellipse cross-section roundness, and surface placement stations.
