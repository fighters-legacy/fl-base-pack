# T-38A Talon — data provenance

Every number in `t38a.toml`, `t38a.expect.toml` and the mesh (`t38a_build.py`) traces to a row in
this file.

**Clean-room rule.** Public sources only: USAF technical orders, DTIC/AFFTC flight-test reports, NASA
technical reports, and manufacturer/USAF characteristics charts. **No value in this aircraft is taken
from any flight simulator, game, or commercial 3D model** — not DCS, not Falcon, not War Thunder, not
X-Plane. Where a figure could only be found in such a source it is *rejected*, with the reason. See
`docs/legal/aircraft-likeness.md` in the engine repo.

Each row is tagged:

- **P** — *published*: read directly from a primary source.
- **D** — *derived*: computed from published values by a stated method. Reproducible.
- **E** — *engineering estimate*: not published and not derivable. A judgement call, flagged as such.

The aircraft modelled is the **early T-38A** with the **J85-GE-5** engine — the configuration the
1960s T.O. and AFFTC reports describe. (Later Propulsion Modernization Program engines re-rated the
thrust; not modelled.)

---

## The T-38 as an F-5 sibling — what carries over and what does not

The T-38A and the F-5E (`aircraft/f5e/`) are the same Northrop **N-156 airframe family**, so the two
share their build script (`fl_aircraftlib.n156`), their aerodynamic derivation *method* (`derive.py`),
and — where a T-38 datum is genuinely absent — the F-5E's value as the closest published analog. That
inheritance is stated explicitly at each point below; it is never silent.

**The calibration inverts.** This is the single most important fact about the model:

| | F-5E (fighter manual) | T-38A (trainer manual) |
|---|---|---|
| Specific-excess-power (Ps) ladder | **published** — pins the CL⁴ separation drag | **absent** |
| Sustained / instantaneous turn charts | **published** | **absent** |
| Sea-level rate of climb | not trustworthy (rejected Wikipedia's 34,500 fpm) | **published** (MIL, 2.0 min to 15 k ft) |
| Stall speeds vs weight | 2 points | chart image (numeric table not retrievable) |
| Max level Mach | 1 point (M1.63 @ 36 k) | 2 points (M1.08 SL, M1.3 @ 30 k) |

So the F-5E anchored **drag** on a turn ladder; the T-38 anchors **drag** on climb + max Mach, and
**inherits** the CL⁴ separation-drag coefficient from the F-5E because it has no high-CL datum of its
own. Full reasoning in `derive.py`.

---

## Primary sources

| Key | Document |
|---|---|
| **TO** | *T.O. 1T-38A-1, USAF Series T-38A Flight Manual* (1960s; Change 2, 1 Nov 1967) — geometry, limits, engine ratings, climb/cruise charts |
| **AD0263411** | AFFTC *T-38A Category II Stability & Control Tests*, 1961 — Appendix "Dimension and Design Data" (planform, tail areas, airfoil, CG) — <https://apps.dtic.mil/sti/tr/pdf/AD0263411.pdf> |
| **ADA496748** | AFIT thesis (Williams, 2009), Table 15 "T-38 Aircraft and Model Dimensions" (from Northrop CAD) — <https://apps.dtic.mil/sti/tr/pdf/ADA496748.pdf> |
| **FACT** | USAF T-38 fact sheet (af.mil #104569; authenticated GPO copy) — dimensions, installed thrust, ceiling |
| **NASA-SPIN** | *Spin-Tunnel Investigation of a 1/20-Scale F-5E*, NASA TM SX-3556 / NTRS 19980227417, Table II — the F-5E inertia analog — <https://ntrs.nasa.gov/citations/19980227417> |
| **FAI** | FAI time-to-climb records, T-38A 61-0849, Edwards AFB, Feb 1962 (cross-check only) |
| **WIKI** | Wikipedia, *Northrop T-38 Talon* — cross-check only; flags 33,600 fpm as "probably incorrect" |

**Rejected:** flugzeuginfo.net (47 ft 3 in length / 172 ft² wing — disagrees with every primary
source). Any DCS/Falcon/X-Plane figure. The 33,600 ft/min sea-level climb (a peak/zoom number, not a
sustained MIL rate).

---

## Geometry — **P** unless noted, from AD0263411 / ADA496748

| Field | Value | Source |
|---|---|---|
| `length` (mesh) | 14.13 m (46 ft 4 in) | **P** TO / ADA496748 |
| `wingspan_m` | 7.70 m (25 ft 3 in) | **P** AD0263411 |
| `wing_area_m2` | 15.79 m² (170.0 ft²) | **P** AD0263411 / ADA496748 |
| aspect ratio | 3.75 | **P** AD0263411 |
| taper ratio | 0.20 | **P** AD0263411 |
| quarter-chord sweep | 24° | **P** ADA496748 |
| airfoil | NACA 65A004.8 (mod.), root→tip | **P** AD0263411 / ADA496748 |
| `mac_m` | 2.356 m (92.76 in) | **P** ADA496748 |
| root chord | 3.420 m (134.65 in) | **P** ADA496748 |
| tip chord | 0.684 m (26.93 in) | **P** ADA496748 |
| h-tail area (exposed) / AR / taper | 3.10 m² / 2.82 / 0.33 | **P** AD0263411 |
| v-tail area (exposed) / AR / taper | 3.82 m² / 1.21 / 0.25 | **P** AD0263411 |
| design CG | 20% MAC | **P** AD0263411 / ADA496748 |

Tail **sweep** angles and the exact tail **spans** are not published; the mesh's tail sweep is an
`[E]` family value and its spans are `[D]` from the published exposed AR·area. The flight model reads
none of the mesh geometry.

### The forebody gap — the mesh's largest [E]

Unlike the F-5E (whose forebody was traced off NASA's *dimensioned* spin-tunnel 3-view), **no
dimensioned T-38 side view was obtained from any primary source**. The T.O. General Arrangement shows
the two-cockpit tandem layout but carries no station dimensions, and no NASA/NTRS T-38 3-view exists.
So the fuselage cross-section and the tandem canopy in `t38a_build.py` (`stations_fus`, `canopy_span`)
are **[E]** — shaped by hand to the published length (46 ft 4 in), height (12 ft 11 in), the known
slender area-ruled "coke-bottle" fuselage and the two-seat canopy. Nothing is traced from any drawing,
photo, sim or model. This is the mesh's single largest estimate and it is **visual only** — the flight
model consumes nothing from the mesh. Recorded here so nobody mistakes the T-38 forebody for a trace
the way the F-5E's genuinely is.

*Modelling limitation (recorded, not hidden):* the shared N-156 canopy builder renders the tandem
canopy as one long transparency. It cannot render a distinct inter-cockpit bow/frame — but that
detail is below the single-material / single-primitive pipeline floor (engine#839), and the F-5E's
canopy has no framing either.

---

## Masses & fuel

| Field | Value | Tag | Source |
|---|---|---|---|
| `mass_kg` (operating empty) | 3,270 kg (~7,200 lb) | **D** | FACT lineage; no clean T.O./SAC W&B page was machine-readable. Wing loading 3270/15.79 = **207 kg/m²**, inside the trainer band. |
| `fuel_kg` (usable internal) | 1,770 kg (~3,900 lb, JP-4) | **D** | period Northrop data (≈600 US gal @ 6.5 lb/gal); the oft-quoted 1,133 gal is internal+external, **not** used |
| design gross | 5,443 kg (12,000 lb) | P | TO |
| max takeoff | 5,485 kg (12,093 lb) | P | FACT |

The unarmed T-38 carries no ammunition and no stores, so `mass_kg` is a true operating-empty weight —
unlike the F-5E's `mass_kg`, which bundled gun ammunition and two AIM-9s.

### Moments of inertia — **KEY FINDING: no primary T-38 source exists**

A thorough NTRS/DTIC search found **no T-38 spin-tunnel, mass-properties or inertia report** — no
T-38 equivalent of the F-5E's NASA-SPIN. NASA CR-2144 (the standard inertia compilation) does not
include the T-38. AD0263411 is handling-qualities data with no inertia tensor. The absence is
confirmed, not merely "not found," so nobody re-runs this search expecting a hit.

The values in `t38a.toml` are therefore **[E]**, scaled from the F-5E's NASA-SPIN clean loading
(TM SX-3556 Table II: Ixx 4610, Iyy 52063, Izz 55317 kg·m² at 13,000 lb) by the mass ratio
(~12,000/13,000 lb) and the geometry ratio (I ∝ m·L² — span² for roll, length² for pitch, the mean
for yaw). Result: Ixx 3820, Iyy 44520, Izz 46950. Nothing in `t38a.expect.toml` tests these, and the
model's *static* performance (which the gates check) does not depend on them.

---

## Propulsion — 2× General Electric J85-GE-5

| Rating | Per engine | Total | Tag | Source |
|---|---|---|---|---|
| Bare-engine, military (dry) | 2,680 lbf / 11.92 kN | 23.84 kN | **P** | TO Sec. V (Wikipedia J85 table cross-checks) |
| Bare-engine, maximum (AB) | 3,850 lbf / 17.13 kN | 34.25 kN | **P** | TO Sec. V |
| **Installed, used in the deck** | ~9.2 / 14.3 kN | **18.4 / 28.6 kN** | **D** | LEVEL calibrated to the published climb + max Mach (below); lands near the FACT installed ratings (2,050 / 2,900 lbf), ~20% under bare |

As on the F-5E, the aircraft's published performance was computed from **installed** thrust, which is
below the bare-engine rating. The deck's SL-static level (18.4 kN MIL / 28.6 kN AB total) is the level
that reproduces the two published performance anchors below; it is close to the USAF fact-sheet
installed figures and well under the bare-engine T.O. numbers. Lapse with Mach and altitude is the
standard turbojet law `T = T_sl·σ^0.85·(1 − 0.25M + 0.55M²)` — **[D]**, no net-thrust curves are
published. This is the model's largest single uncertainty.

**Fuel flows** (`fuel_flow_*`) are **[E]**: no J85-GE-5-specific fuel-flow data was found (the
candidate engine report AD0266168 was rate-limited, not retrieved). Scaled from the F-5E's
J85-GE-21 flows by the thrust ratio; the resulting AB/MIL ratio (~3.4) is physically sane for a J85.

---

## Performance anchors (what `t38a.expect.toml` gates)

| Metric | Value | Tag | Source / note |
|---|---|---|---|
| max level Mach @ SL | **M1.08** | **P** | FACT; also bounded by the 710 KEAS placard (~M1.07) |
| max level Mach @ 30,000 ft | **M1.3** | **P** | FACT — the headline number |
| SL rate of climb (MIL) | ~46 m/s | **D** | from the published MIL climb SL→15,000 ft in **2.0 min** (TO chart FA3-1). The 33,600 fpm figure is **rejected** (peak/zoom, WIKI-flagged) |
| 1-g clean stall @ 11,800 lb | ~131 KIAS (67.5 m/s) | **D** | from the published takeoff speed 154 KIAS (~1.15–1.2 Vs); the numeric stall table (chart image / AD0425650) was not retrievable → back-solves CL_max ≈ 1.19 |
| structural g (light / full fuel) | +7.33 / +6.0, −3.0 / −2.4 | **P** | TO Sec. V — **fuel-dependent**; the model uses the light-weight limit |
| max Mach placard | 710 KEAS or M1.3 | **P** | TO Sec. V |

`verify_targets.py` cross-checks these by pure kinematics (the two stall rows back-solve to the same
CL_max; the EAS placard and the SL max Mach agree; the FAI records bound the climb from above).

### Energy-maneuverability / Ps / turn data — confirmed ABSENT

T.O. 1T-38A-1 Appendix I contains **only** takeoff, climb, cruise/range, endurance, descent and
landing charts — a trainer manual. There is **no Ps ladder and no turn chart anywhere** in the
published T-38A record (the 1961 AFFTC reports predate Boyd's EM methodology). This is why
`t38a.expect.toml` deliberately omits the `ps_mps` / `sustained_g` / `sustained_turn_deg_s` /
`instant_turn_deg_s` / `max_lift_g` rows the F-5E gates: the fighter manual publishes them, the
trainer manual does not, and inventing them would be a lie.

---

## Signatures & damage (entity def)

All **[E]** — no T-38 signature data is public. Reasoned down from the F-5E baseline: the T-38 is
smaller, cleaner (no wingtip rails, no stores), with smaller J85-GE-5 engines rarely in burner. The
`visual` value reflects the **grey** airframe the pack ships (policy §4), not the real T-38's usual
high-visibility white, which would raise it. See `entities/t38a.toml` for the per-value reasoning.
