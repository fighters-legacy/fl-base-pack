# B-1B Lancer — data provenance

Every number in `b1b.toml` and `b1b.expect.toml` traces to a row in this file.

**Clean-room rule.** Public sources only: USAF fact sheets, NASA technical reports, and
manufacturer characteristics data. **No value in this aircraft is taken from any flight simulator,
game, or commercial 3D model** — not DCS, not Falcon, not War Thunder, not X-Plane. Where a figure
could only be found in such a source, it is recorded here as *rejected*, with the reason. See
`docs/legal/aircraft-likeness.md` in the engine repo.

Each row is tagged:

- **P** — *published*: read directly from a primary source.
- **D** — *derived*: computed from published values by a stated method. Reproducible.
- **E** — *engineering estimate*: not published and not derivable. A judgement call, flagged as such.

## The aircraft modelled is the **B-1B**, not the B-1A

This matters more here than on any previous aircraft in the pack, because **most of the public
NASA/NTRS paper trail is B-1A flight test** and the two aircraft do not share a performance
envelope. The B-1A had variable-geometry inlets and was flown to high supersonic Mach; the B-1B
replaced them with fixed inlets (lower RCS, lower top speed) and raised maximum takeoff weight.

The rule applied throughout this file: **B-1A documents are used for airframe geometry, structural
and aeroelastic context, and for realistic flight-test conditions — never for B-1B performance.**
Every B-1A-sourced row says so.

---

## Primary sources

| Key | Document |
|---|---|
| **AF** | USAF B-1B Lancer fact sheet — <https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104500/b-1b-lancer/> ⚠ see *Source-access caveat* below |
| **BA** | Boeing, *B-1 Lancer* product page (manufacturer) — <https://www.boeing.com/defense/fighters-and-bombers/b-1-lancer> |
| **WIKI** | Wikipedia, *Rockwell B-1 Lancer* specification block, which cites **AF**, Jenkins (1999), Pace, and Lee — <https://en.wikipedia.org/wiki/Rockwell_B-1_Lancer> |
| **SMCS-S** | *Flight test and analyses of the B-1 structural mode control system at supersonic flight conditions*, NASA CR, 1983 (Rockwell Intl. under NAS4-2932) — <https://ntrs.nasa.gov/citations/19840005129> — **B-1A, A/C-3** |
| **SMCS** | *Analyses and tests of the B-1 aircraft structural mode control system*, 1980 — <https://ntrs.nasa.gov/citations/19800006814> — **B-1A** |
| **FLUT** | *Determination of subcritical frequency and damping from B-1 flight flutter test data*, 1979 — <https://ntrs.nasa.gov/citations/19790017255> — **B-1A** |

The three NTRS documents are held as PDFs in the out-of-repo reference set
(`~/src/fighters-legacy/b1-reference/documents/`) and were read directly. Photographic reference
and its licence provenance are in that set's `MANIFEST.md`.

### ⚠ Source-access caveat — read before trusting a **P** tag

`af.mil` (and its base mirrors) return **HTTP 403 to every non-browser request**, so the USAF fact
sheet could not be read directly while compiling this file. Rows tagged **P (AF via WIKI)** are
therefore published values reached through **WIKI**'s spec block, which names the fact sheet as its
source alongside Jenkins/Pace/Lee — a citation chain, not a direct read.

They are not invented, and the ones that can be cross-checked against **BA** (a manufacturer
primary source, read directly) agree. But the chain is one link longer than this project's standard,
so: **before `b1b.toml` is finalised, a human with browser access should open the fact sheet and
confirm the rows below.** This note stays until that happens.

---

## Geometry — **P**

| Field | Value | Source |
|---|---|---|
| length | 44.501 m (146 ft) | **P** BA, AF via WIKI (agree) |
| `wingspan_m`, wings **spread** (15°) | 41.758 m (137 ft) | **P** BA, AF via WIKI (agree) |
| wingspan, wings **swept** (67.5°) | 24.079 m (79 ft) | **P** BA, AF via WIKI (agree) |
| height | 10.363 m (34 ft) | **P** BA, AF via WIKI (agree) |
| `wing_area_m2` | 181.16 m² (1,950 ft²) | **P** WIKI |
| airfoil | NACA 69-190-2 | **P** WIKI |
| aspect ratio, spread | 9.625 | **D** b²/S = 41.758²/181.16 |
| aspect ratio, swept (on the same reference area) | 3.201 | **D** 24.079²/181.16 |
| `mac_m` | — | **not published**; to be derived in Stage 2 from the planform actually built. See *Gaps*. |

`wing_area_m2` is the **reference** area used with the spread span; the engine's `[wing_sweep]`
model keeps one reference area and scales the aero coefficients with sweep, so the physical area
change as the wings tuck into the glove is carried by `cl_scale`/`k_scale`, not by this field.

## Wing sweep — **P**

| Field | Value | Source |
|---|---|---|
| `min_deg` | 15.0 | **P** WIKI (cites Withington 2006 p.16) |
| `max_deg` | 67.5 | **P** WIKI (cites Withington 2006 p.16); corroborated by **SMCS-S**, which describes A/C-3 at "sweep position of 67°" |
| AR ratio spread→swept | 3.007 | **D** 9.625 / 3.201 — the basis for the `[wing_sweep]` `k_scale` derivation in Stage 2 |

Usage, published: forward settings for takeoff, landing and high-altitude cruise; aft settings for
high subsonic and supersonic flight (**P** WIKI). Intermediate settings are normal — the widely
published in-flight photograph set includes a 20° cruise configuration.

## Mass — **P**

| Field | Value | Source |
|---|---|---|
| empty weight | 87,090 kg (192,000 lb) | **P** WIKI. **BA** says "approximately 190,000 lb" — a rounded manufacturer figure, not a conflict |
| gross weight | 147,871 kg (326,000 lb) | **P** WIKI |
| max takeoff weight | 216,364 kg (477,000 lb) | **P** BA, AF via WIKI (agree exactly) |
| `fuel_kg` (max internal) | 120,326 kg (265,274 lb) | **P** AF via WIKI |
| fuel fraction of MTOW | 0.556 | **D** 265,274 / 477,000 |
| wing loading at gross | 816.2 kg/m² (167.2 lb/ft²) | **D** 326,000/1,950; WIKI publishes 167 — agrees |

Real B-1A flight-test weights, useful as sanity anchors for the mass range actually flown:
251,670 lb, 284,160 lb and 296,940 lb (**P** SMCS-S, **B-1A** — context only, not B-1B limits).

## Propulsion — **P**

Four General Electric **F101-GE-102** afterburning turbofans.

| Field | Value | Source |
|---|---|---|
| thrust, dry, per engine | 77.35 kN (17,390 lbf) | **P** WIKI |
| thrust, afterburner, per engine | 136.92 kN (30,780 lbf) | **P** WIKI; **BA** says "30,000-plus lb", consistent |
| total thrust, dry | 309.4 kN (69,560 lbf) | **D** ×4 |
| total thrust, afterburner | 547.7 kN (123,120 lbf) | **D** ×4 |
| T/W at gross weight | 0.378 | **D** 123,120/326,000; WIKI publishes 0.38 — agrees |
| T/W at MTOW | 0.258 | **D** 123,120/477,000 |

## Performance — the `b1b.expect.toml` anchors — **P**

| Quantity | Value | Source |
|---|---|---|
| max speed at altitude | M1.25 / 721 kn TAS at 50,000 ft | **P** WIKI (cites Pace) |
| max speed at low level | 608 kn at 200–500 ft | **P** WIKI |
| service ceiling | 18,288 m (60,000 ft) | **P** WIKI |
| rate of climb | 28.85 m/s (5,678 ft/min) | **P** WIKI |
| range | 5,100 nmi | **P** WIKI |
| combat range | 2,993 nmi | **P** WIKI |

### The two published speeds are self-consistent — and they falsify a third

Checked against ISA rather than assumed (`a` = 340.294 m/s at sea level, 295.07 m/s in the
stratosphere):

    721 kn at 50,000 ft  ->  370.9 m/s  ->  M1.257   (published as M1.25 — agrees to 3 d.p.)
    608 kn at 200-500 ft ->  312.8 m/s  ->  M0.919   (the low-level subsonic limit)

Both published figures reproduce their stated Mach numbers, so the pair is internally consistent
and is what the flight model is calibrated to.

### ❌ REJECTED: "900-plus mph (Mach 1.2 at sea level)" — **BA**

Boeing's own product page states a sea-level speed of "900-plus mph (Mach 1.2 at sea level)". It is
**not used**, and the conflict is recorded rather than quietly resolved:

- M1.2 at sea level is **794 kn / 913 mph**. The published low-level figure is **608 kn**. The two
  disagree by **31%** — this is not rounding, it is a different aircraft's envelope.
- The B-1B's **fixed** inlets were the defining change from the B-1A and exist precisely to trade
  top speed for signature. A sea-level supersonic dash contradicts the design rationale.
- The B-1A structural-mode flight tests were flown at **Mach 0.83–0.85 at low altitude**
  (**P** SMCS) — the regime the airframe was actually instrumented and cleared for.
- At 0.378 T/W and 816 kg/m² wing loading, sustained sea-level supersonic flight is not credible for
  this airframe; transonic wave drag at sea-level density would demand far more installed thrust.

**Taking Boeing's number would have produced a flight model that is wrong by 31% in the exact
regime this aircraft is built to fly** — the low-level penetration case. Recorded here so nobody
"corrects" the model back toward it later.

---

## Gaps — everything below will be **D** or **E**, and is Stage 2 work

No public source gives these, and none is derivable from the rows above. Each will be tagged in
`b1b.toml` where it lands:

| Quantity | Why it is missing | Plan |
|---|---|---|
| `ixx/iyy/izz` inertias | Never published for the B-1 in any public document | **E** — scale from the F-5E/F-16A method (mass × characteristic length²) with the method stated inline, exactly as the T-38A did |
| `[aero.cl_table]` | No public CL(α, M) database exists for the B-1 — there is no B-1 equivalent of NASA TP-1538 | **D** — DATCOM-style build for a blended-body VG planform, calibrated so `fm-trim` reproduces the published performance anchors above |
| `[aero.drag_polar]` / `cd0` | Not published | **D** — calibrated to the published max speeds at both altitudes and the published rate of climb |
| `[wing_sweep.spread]` / `[.swept]` scales | Not published | **D** — from the 3.007 AR ratio above; `k_scale` tracks 1/AR, `cl_scale` from the lift-curve-slope change |
| `mac_m` | Not published | **D** — from the planform geometry built in Stage 3 |
| `cl_p`, `cl_da` (roll damping/authority) | No public roll-rate data | **E** — nothing checks these; state that plainly, as the F-5E and T-38A both do |
| engine thrust vs Mach/altitude | Only the SL-static ratings are published | **D** — anchor on the published static ratings, lapse by a standard turbofan law, calibrate the level-flight points to the two published max speeds |

## Reference imagery

Photographic reference lives **outside this repository** at
`~/src/fighters-legacy/b1-reference/` with a per-file provenance `MANIFEST.md` (31 files, all
public domain or CC0, licence read from the Wikimedia Commons API at download time). Buckets cover
planform, both wing-sweep extremes, front views, the bomb bays, the flight deck, gear, engines and
the AN/APQ-164 antenna.

**No scale plans, no cutaways, no line drawings** were collected or used: Commons'
`Rockwell B-1 Lancer drawings` category was deliberately excluded from the harvest, because a mesh
traced from a modelling-magazine plan or a cutaway is a derivative of that drawing regardless of any
licence tag on the scan.

Per `aircraft-likeness.md` §4, the markings, insignia and nose art visible in those photographs are
**not** reproduced on the airframe — the pack ships clean grey.
