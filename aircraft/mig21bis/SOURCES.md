# MiG-21bis Fishbed — data provenance

Every number in `mig21bis.toml` and `mig21bis.expect.toml` traces to a row in this file.

**Clean-room rule.** Public sources only: declassified government documents, published reference
annuals, and manufacturer-lineage material. **No value in this aircraft is taken from any flight
simulator, game, or commercial 3D model** — not DCS, not War Thunder, not X-Plane, and not a wiki
that copied one of them. Where a figure could only be found in such a source, it is recorded here
as *rejected*, with the reason. See `docs/legal/aircraft-likeness.md` in the engine repo.

Each row is tagged:

- **P** — *published*: read directly from a primary or named secondary source.
- **D** — *derived*: computed from published values by a stated method. Reproducible.
- **E** — *engineering estimate*: not published and not derivable. A judgement call, flagged as such.

## The provenance caveat this aircraft was filed with — and how it actually resolved

Issue #41 said it up front: there is no NASA-grade public aero database for the MiG-21 — nothing
like TP-1538 for the F-16 or the T.O. charts for the F-5E. That is still true, but the record is
better than feared, because two primary-source classes exist:

1. **A declassified Soviet manual.** The CIA Reading Room holds an English translation of the
   *MiG-21F-13 Technical Description, Book I — Flight Characteristics* (1963). It publishes the
   airframe geometry to the millimetre, structural placards, weights, climb and range tables.
2. **A well-cited reference-annual spec block.** Wikipedia's MiG-21bis specification block is
   referenced to *Jane's All the World's Aircraft 1992–93* — a citation chain, like the B-1B's
   AF-via-WIKI rows, but a chain to a named page range of a named annual.

The `derived`/`estimated` tags still dominate the *aerodynamics* (no public CL/CD database), and
that is the honest state of the record.

## The aircraft modelled is the **MiG-21bis**, not the MiG-21F-13

The same discipline the B-1B applied to B-1A documents applies here, because **the best primary
source is for the wrong variant.** The F-13 (1963) and the bis (1972) share the delta wing and
basic layout, but the bis has a longer radar nose, the wide-chord fin, the saddle-tank spine, a
different engine (R-25-300 vs R-11F-300) and different weights.

The rule applied throughout this file: **F-13 manual data is used for wing/control-surface
geometry (unchanged across the family), structural-placard *structure*, and realism context —
never for bis performance, masses, or fuselage length.** Every F-13-sourced row says so.

---

## Primary sources

| Key | Document |
|---|---|
| **F13-TD** | *English Translation of a Soviet Manual Entitled Aircraft MIG-21F-13, Technical Description, Book I, Flight Characteristics* (1963), CIA Reading Room, declassified 2014 — <https://www.cia.gov/readingroom/docs/CIA-RDP80T00246A030200200001-3.pdf> — **F-13, not bis** |
| **JAWA via WIKI** | Wikipedia, *Mikoyan-Gurevich MiG-21* specification block, referenced to *Jane's All the World's Aircraft 1992–93* (Lambert/Munson/Taylor eds., pp. 214–216) — <https://en.wikipedia.org/wiki/Mikoyan-Gurevich_MiG-21> |
| **GORDON via WIKI** | Same article's design/development text where referenced to Gordon, *Mikoyan MiG-21* (Famous Russian Aircraft, Midland, 2008) |
| **R25-WIKI** | Wikipedia, *Tumansky R-25*, whose thrust/SFC table cites leteckemotory.cz — <https://en.wikipedia.org/wiki/Tumansky_R-25> |
| **MOD-BROCHURE** | *MiG-21bis — top of MiG-21 aircraft evolution*, modernization-programme brochure (manufacturer-lineage narrative of the bis's design requirements) — <https://www.generalequipment.info/MIG%2021%20Modernization%20PDF.pdf> |
| **MIG21DE** | mig-21.de, *Technical Overview* (German MiG-21 reference site, per-variant data tables) — <https://www.mig-21.de/english/technicaldata.htm> |
| **AIRFOIL** | Lednicer, *The Incomplete Guide to Airfoil Usage*, UIUC — <https://m-selig.ae.illinois.edu/ads/aircraft.html> |
| **R60-WIKI** | Wikipedia, *R-60 (missile)* (cites Mladenov, *International Air Power Review* vol. 14) |
| **GSH-WIKI** | Wikipedia, *Gryazev-Shipunov GSh-23* |
| **RP21-WIKI** | Wikipedia, *RP-21 Sapfir* |

The F13-TD manual is held as a PDF in the out-of-repo reference set
(`~/src/fighters-legacy/mig21-reference/documents/`) and was read directly. Photographic reference
and its licence provenance are in that set's `MANIFEST.md`.

### Source-access caveats — read before trusting a **P** tag

- *Jane's All the World's Aircraft 1992–93* was not read directly; those rows are **P (JAWA via
  WIKI)** — published values reached through the cited spec block. Same standing as the B-1B's
  AF-via-WIKI rows: one link longer than this project's standard, recorded as such.
- **MOD-BROCHURE** carries no publisher imprint in the copy read; its claims are used only where
  independently corroborated or where they describe the bis design *requirements* narrative.
- The **F13-TD figures (Figs 1–3, general-view drawings)** are official-document drawings, the
  same class as the NASA report 3-view the F-5E was built from — *not* a modelling-magazine scale
  plan. They are nevertheless used as **dimensional cross-check only**, not traced.

---

## Geometry

Wing and control surfaces are common to the family and taken from the manual (**P F13-TD** unless
noted); fuselage dimensions are bis-specific.

| Field | Value | Source |
|---|---|---|
| `wingspan_m` | 7.154 m | **P** JAWA via WIKI; F13-TD gives 7.150 — agree |
| `wing_area_m2` | 23.0 m² | **P** F13-TD and JAWA via WIKI — agree exactly |
| `mac_m` | 4.002 m | **P** F13-TD. *Published*, unlike the B-1B's, which had to be derived |
| aspect ratio | 2.225 | **D** 7.154²/23.0 — a true tailed delta, the lowest AR in the pack by far (F-5E: 3.86) |
| leading-edge sweep | 57° | **P** F13-TD |
| dihedral | −2° | **P** F13-TD |
| wing incidence | 0° | **P** F13-TD |
| airfoil | TsAGI S-12: 4.2% root, 5% tip | **P** AIRFOIL (via WIKI) |
| ailerons, total | 1.18 m², ±20° | **P** F13-TD |
| flaps, total | 1.87 m², 24.5° T-O/landing | **P** F13-TD |
| speed brakes | fwd pair 0.76 m² total, rear 0.47 m² | **P** F13-TD (manual: 25° fwd deflection; the WIKI design text says 35° — not a modelled quantity, recorded only) |
| stabilator | 3.94 m², span 2.6 m, 57° sweep, +7.5°/−16.5° | **P** F13-TD |
| fin area | 5.32 m² (bis, wide-chord) | **P** WIKI design text. ⚠ The F-13 manual gives **4.45 m²** for the F-13's narrow fin, so the WIKI text's "earlier 3.8 m²" is wrong somewhere — but the bis value is the one modelled, and 5.32 is the consistently published wide-chord figure |
| rudder deflection | ±25° | **P** F13-TD |
| height | 4.1 m | **P** JAWA via WIKI; F13-TD 4.10 (parked, F-13); MIG21DE 4.12 — agree |
| wheel track / wheelbase | 2.69 m / 4.81 m | **P** F13-TD |
| main tyres | 800×200 mm | **P** WIKI design text (bis-family; only F variants used 660×200) |
| `length_m` (excl. pitot boom) | **see the conflict below** | — |

### ✅ RESOLVED: fuselage length is **14.10 m** excluding pitot — by datum-consistency

The two bis sources disagreed by 0.6 m:

- **JAWA via WIKI**: 14.7 m "excluding pitot boom".
- **MIG21DE**: 14.10 m "without pitot tube".
- **F13-TD** (F-13, primary): **13.46 m** without pitot, 15.76 m with.

**The test that settled it (Stage 3):** MIG21DE's per-generation table lists the F-13 at
**13.46 m — the CIA manual's exact published figure, to the centimetre.** That proves the site's
length datum is the same one the primary source uses, and in that same datum it lists every
PF-generation-onward fuselage (PFM, MF, bis) at **14.10 m** — the radar nose added ~0.64 m,
consistent with the photographs. Jane's 14.7 m has no stated datum and no anchor that can be
checked against the primary; it is the outlier and is not used. Corroborating detail: the
Chinese J-7 rows in the same table follow the identical pattern (J-7 I, the F-13 airframe,
13.46 m; J-7 III, the MF-class airframe, 14.10 m).

`mig21bis` meshes are built to **14.10 m** nose lip to tail, pitot boom excluded from
`length` accounting exactly as the sources exclude it.

## Mass

| Field | Value | Source |
|---|---|---|
| empty weight | 5,895 kg | **P** MIG21DE — and it is the only empty-weight candidate that survives the closure check below |
| gross weight (2× R-3S) | 8,725 kg | **P** JAWA via WIKI |
| max takeoff weight | 8,800 kg unprepared / metal-planking runway | **P** JAWA via WIKI |
|  | 9,800 kg paved runway, standard wheels | **P** JAWA via WIKI |
|  | 10,400 kg paved runway, larger wheels/tyres | **P** JAWA via WIKI (MIG21DE's "10,100 kg max" sits inside this ladder) |
| internal fuel volume | 2,880 L | **P** MOD-BROCHURE ("fuselage spine fairing construction was again changed reducing fuel tanks volume to 2880 l") |
| `fuel_kg` | 2,390 kg | **D** 2,880 L × 0.83 kg/L — the density the Soviet manual itself uses (**P** F13-TD: "fuel density = 0.83 gr/cm³") |
| F-13 anchors (context only) | T-O 7,370 kg; fuel 2,080 kg; min landing 5,217 kg; CG 31–35% MAC | **P** F13-TD — **F-13, not bis** |

### The closure check that picked the empty weight

Empty-weight figures floating around for the bis include 5,350, 5,450 and 5,895 kg (the first two
are almost certainly earlier-variant figures). Only one closes against the well-sourced gross:

    5,895 empty + 2,390 fuel + ~210 two armed R-3S with rails [E]
                + ~90 pilot [E] + ~70 gun ammunition, 200 rds [E]  =  8,655 kg  ≈  8,725 published

A 5,450 kg empty weight leaves a ~450 kg hole; 5,350 kg leaves ~550 kg. The [E] terms are
plausibility allowances, not modelled values — but the check discriminates at the half-tonne
level, which is what it is for. (MIG21DE's 2,750 L fuel figure — likely usable rather than total —
also closes ~110 kg worse than 2,880 L. Recorded, not used.)

## Propulsion — one Tumansky R-25-300 afterburning turbojet

| Field | Value | Source |
|---|---|---|
| thrust, dry | 40.18 kN | **P** JAWA via WIKI; R25-WIKI gives 40.3 — agree to 0.3% |
| thrust, full afterburner | 69.58 kN | **P** JAWA via WIKI; R25-WIKI 69.6; MOD-BROCHURE's design requirement "7,100 kgp" = 69.6 kN — all agree |
| thrust, ЧР emergency mode | 97.1 kN, below 2,000 m, 2-minute limit | **P** R25-WIKI table; GORDON via WIKI gives 97.4 kN "under 2,000 m", 2 min — agree to 0.3% |
| SFC: idle / military / AB / ЧР | 93 / 98 / 229 / 340 kg/(h·kN) | **P** R25-WIKI |
| T/W at gross | 0.76 | **P** JAWA via WIKI; slightly >1 on ЧР at combat weight (**P** GORDON via WIKI) |

**On the ЧР (emergency) rating and whether the model carries it:** the sources scatter — 96.5 kN
(R25-WIKI prose), 97.1 (its table), 97.4 (Gordon), and the *requirement* was 9,600 kgp = 94.1 kN
for "up to 3 min" (MOD-BROCHURE). The engine's `[thrust]` schema has no time-limited war-emergency
regime, and inventing a fourth throttle stop is out of scope for this aircraft. **Decision: model
dry + full AB only; do not fold ЧР thrust into the AB deck.** The 254 m/s ЧР climb figure is
therefore *deliberately not gated* (see the expect-gate section). If a time-limited rating ever
earns an engine RFC, the numbers are here.

## Performance — the `mig21bis.expect.toml` anchors

| Quantity | Value | Source |
|---|---|---|
| max speed at altitude | 2,175 km/h / **M2.05** at 13,000 m | **P** JAWA via WIKI |
| max speed at sea level | 1,300 km/h / M1.06 | **P** JAWA via WIKI — an IAS placard, see below |
| service ceiling | 17,500 m | **P** JAWA via WIKI |
| climb rate, combat-loaded | **235 m/s** | **P** GORDON via WIKI (46,250 ft/min; "not far short of the later F-16A") |
| climb rate on ЧР | 254 m/s | **P** GORDON via WIKI — **not gated** (no ЧР regime in the model) |
| time to 17,000 m | 8 min 30 s | **P** JAWA via WIKI |
| landing speed | 250 km/h | **P** JAWA via WIKI; F-13: 260–270 (**P** F13-TD) |
| takeoff run (AB) | 830 m | **P** JAWA via WIKI; F-13: 800 m (**P** F13-TD) |
| landing run (SPS + chute) | 550 m | **P** JAWA via WIKI |

F-13 performance context (**P** F13-TD, never gated for the bis): max 2,125 km/h at
12.5–18.5 km; static ceiling 19,000 m at M1.85; SL climb 130–140 m/s AB / 70–80 m/s military;
time to 5,000/10,000/15,000 m = 2.0/3.2/5.5 min with AB; best-range condition at 11,000 m is
925 km/h TAS at 1.01–1.12 kg/km.

### The sea-level figure is a placard, not a thrust limit

The F-13 manual publishes the structural-limitations table outright (**P** F13-TD, F-13 values):
maximum operational load factor **7.0**, maximum indicated speed **1,250 km/h**, maximum Mach
**2.35**, maximum head pressure **7,500 kg/m²** (= 73.6 kPa dynamic pressure). That is exactly the
`max_keas`-placard structure fighters-legacy#1181 added for the B-1B, and the bis's published
1,300 km/h at sea level (M1.06) is the same kind of number — the airframe's indicated-speed
placard, quoted at the altitude where it binds. 1,300 km/h IAS ≈ **702 KEAS**; the T-38A and
F-5E placards (710 KEAS) are near-identical, which is corroborating rather than coincidental —
same class, same era.

`mig21bis.toml` therefore declares `max_keas = 702.0` — but unlike the B-1B, **the sea-level row
is gateable today**: the calibrated model trims to M1.04 at sea level on drag alone, because the
bis sits at its placard and its transonic drag wall at almost the same speed (the B-1B was 11%
apart; that is why its row waits on an engine release and this one does not). The
`mig21bis.expect.toml` row gates M1.06 ±4% as a transonic-drag anchor now; when a release ships
fighters-legacy#1181 the placard activates at the same speed and the row keeps passing unchanged.

### ❌ NOT USED: the Jane's range figures — 660 km "clean"

The spec block lists range 660 km clean at 11,000 m / 604 km with two R-3S / 793 km with two
R-3S and an 800 L drop tank. These are **not used**, and the conflict is recorded rather than
quietly resolved:

- The F-13 manual — same wing, same tankage class (2,080 kg), an *earlier and thirstier-per-kN
  regime aircraft* — publishes **1,400 km** practical range at 11,000 m clean, from its own
  km-consumption tables (1.12 kg/km × 1,330 kg cruise fuel + climb credit). MIG21DE gives
  **1,225 km** for the bis without drop tanks.
- 660 km at 11,000 m would demand ~3.6 kg/km from an aircraft whose predecessor measured 1.12 —
  not a bis-vs-F-13 delta, a different quantity. These are almost certainly **mission-profile
  radius/range figures** (intercept profile with combat allowances) transcribed into a "Range"
  field.

The model is not calibrated to any of the three; range is constrained indirectly by the SFC rows
(**P** R25-WIKI) and fuel mass, and no range row is gated. Recorded so nobody "fixes" cruise fuel
burn to reproduce 660 km later.

### What the expect gate covers

Four rows shipped (one more than the B-1B), following the T-38A pattern of no invented EM data:
`max_level_mach` at 13,000 m (the M2.05 anchor, the calibration target), `max_level_mach` at sea
level (M1.06 — gateable now, see above), `roc_mps` at the 235 m/s combat-loaded point (mass
inferred at 7,200 kg and stated as such — at the published 8,725 kg gross the model gives
193 m/s, so "combat-loaded" is evidently a part-fuel condition), and ceiling-as-roc at 17,500 m
(which the model reaches at ~8,100 kg — near gross, the honest shape of a heavy delta's
ceiling). Turn/Ps/specific-range rows deliberately absent: no public bis EM charts exist,
exactly as the issue predicted. The **time-to-17,000 m = 8.5 min** figure serves as a non-gated
cross-check on the climb integral. The gate was **proved to fail** before it was believed:
cd0 +20% and a supersonic wave-drag bump each turn it red (the M2.05 trim is razor-sensitive to
parasite drag — +20% cd0 collapses it to M1.51, because at M2 the thrust and drag curves run
nearly parallel).

---

## Armament and sensor reference (for the entity/weapon/sensor defs, Stages 4–5)

New defs this aircraft introduces, and where their numbers come from:

**GSh-23L cannon** (internal, 200 rounds — **P** JAWA via WIKI): 23×115 mm, twin-barrel Gast
action, 50 kg, 1,537 mm with muzzle brake, muzzle velocity 715 m/s (**P** GSH-WIKI). Rate of fire
3,400–3,600 rds/min is flagged citation-needed on GSH-WIKI — treat as **E** until the def is
authored and bring a better source if one surfaces.

**R-60 / R-60M** (NATO AA-8 Aphid — **P** R60-WIKI, citing Mladenov): launch mass 44 kg (M: 45),
length 2,090 mm (M: +42), Ø120 mm, span 390 mm, 3.0 kg expanding-rod warhead (M: 3.5 kg
continuous-rod), M2.47, brochure range 8 km at altitude, practical ~4 km, minimum 300 m (M:
200 m), IR seeker (R-60: uncooled Komar; R-60M: nitrogen-cooled, ±20° gimbal, limited
all-aspect). Launch at up to 9 g. The pack models the **R-60M** fit typical of late bis service.

**Radar — RP-22M / Sapfir-21M** (S-21M; NATO "Jay Bird"): identity **P** MOD-BROCHURE +
RP21-WIKI. Published performance specifics for the RP-22 are thin; the RP-21 baseline (fighter
target: 20 km theoretical / 13 km practical detection, 10 / 7 km lock — **P** RP21-WIKI) brackets
it from below. Per issue #41's scope ruling the def is a short-range search/track set with **no
radar-missile capability**; a dedicated sourcing pass happens when `sensors/rp22.toml` is
authored, and its numbers must land between the RP-21 floor and clearly under the F-16A's APG-66.

**Stations** (**P** JAWA via WIKI + MOD-BROCHURE): 5 hardpoints — 4 underwing, 1 ventral
reserved for a drop tank. Late-bis fit put paired R-60 rails on the outboard pylons (six missiles
total). The pack keeps the fighter.lua station convention (0 = gun, 1 = IR missile) and models
the simple four-pylon R-60M fit; the paired-rail option is recorded, not modelled.

**Countermeasures:** the Soviet-production bis had **no built-in chaff/flare dispensers**
(retrofits and export upgrades added them). Honest default is `chaff_count = 0`,
`flare_count = 0` — the same honesty ruling that keeps the T-38A at zero. If a specific
dispenser retrofit is ever modelled it needs its own sourced row here.

---

## Gaps — what is **D** or **E**, and how each will be resolved (Stage 2)

No public source gives any of these. All will be produced by `derive.py`; this table records the
method commitments made now, values to be filled by the derivation.

| Quantity | Why it is missing | Method |
|---|---|---|
| `ixx/iyy/izz` inertias | Never published | **E** — radii-of-gyration method as on the B-1B, fighter-class constants, at gross weight |
| `[aero.cl_table]` | No public CL(α, M) database | **D** — 57° delta at AR 2.23: lift slope from slender/delta-wing theory (Helmbold badly overestimates a delta this slender), **vortex-lift increment** per Polhamus leading-edge-suction analogy, peak at `alpha_stall_deg` by construction (the validator requires the table peak within 2° of stall). The delta's high α_stall and soft break are the whole aerodynamic point of this aircraft — get them from the method, not from a sim |
| `alpha_stall_deg` | Not published as a single number | **E** — delta-typical, expected high (>20°); constrained by the 250 km/h landing speed at landing weight, which is a **P** anchor the CL_max must reproduce |
| `[aero.drag_polar]` k | Not published | **D** — 1/(π·AR·e) with delta-appropriate **E** Oswald (~0.5–0.6 with vortex lift accounted); the delta's brutal induced drag at low speed is issue #41's stated reason this airframe stresses the pipeline |
| `cd0`, `[aero.cd_wave]` | Not published | **D** — the only fitted quantities, calibrated against the M2.05/13,000 m anchor and the 235 m/s climb point, exactly as the B-1B fitted cd0/cd_wave to its two anchors |
| `[aero.moments]` | Tail arms/areas published (F13-TD) but derivatives are not | **E** inputs → **D** derivatives, DATCOM methods. ⚠ The wing AC must be the **slender-delta ~0.33 MAC**, not the thin-airfoil 0.25: with 0.25 the derived cm_alpha was −0.01 — no pitch stiffness at all — and the aircraft flew itself into the ground on its first headless spawn while every validator and all four expect rows stayed green. A trim-plausible model can still be unflyable; only the probe sees it |
| `cl_p`, `cl_da` | No public roll data | **E** — strip theory; nothing checks these, exactly as on the F-5E/T-38A/B-1B |
| `max_g_structural` | bis-specific limit not in the accepted sources | **E** — the F-13 manual's 7.0 operational (**P**, F-13) is the floor; the strengthened bis airframe is widely credited with 8.5 g subsonic but no accepted source states it, so the model ships 7.0 until one does. `has_fbw = false`; it is a real, breakable limit |
| thrust vs Mach/altitude | Only SL-static ratings published | **D** — density lapse × ram recovery as on the B-1B, but the ram term must serve a **M2.05 shock-cone inlet**, not decay like the B-1B's fixed pitot inlet; level fixed by the published static ratings and the ceiling anchor |

## Reference imagery

Photographic reference lives **outside this repository** at
`~/src/fighters-legacy/mig21-reference/` (83 images + 2 documents) with a per-file provenance
`MANIFEST.md` (licence read from the Wikimedia Commons API at download time,
magic-byte-validated, PD/CC0 only). Buckets: planform, side, front, nose-radar, cockpit, gear,
engine, stores, skin-detail, static walk-arounds (three complete Finnish museum airframes:
MG-116, MG-127, MG-130), and documents. ⚠ Some geometry references are earlier family variants
— the manifest tags each; the delta wing is common, the nose/fin/spine are not.

**No scale plans, no cutaways, no line drawings** were collected or used: the harvest excludes
Commons' drawings/diagram categories outright, because a mesh traced from a modelling-magazine
plan or a cutaway is a derivative of that drawing regardless of any licence tag on the scan. The
F13-TD manual's official general-view figures are the one sanctioned dimensional cross-check, per
the likeness policy's NASA-3-view precedent.

Per `aircraft-likeness.md` §4, the markings and insignia visible in reference photographs are
**not** reproduced on the airframe — the pack ships clean grey.
