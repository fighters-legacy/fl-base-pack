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
| ~~service ceiling~~ | ~~18,288 m (60,000 ft)~~ | **P** WIKI — ❌ **REJECTED**, see below |
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

### ❌ REJECTED: the 60,000 ft service ceiling — **WIKI**

Rejected **2026-08-16**, and unlike the Boeing figure above this one had already been written into
the flight model's gate, where it passed for two days. The full sequence is worth keeping, because
the failure mode is more interesting than the number.

- The USAF fact sheet — the **primary** source, and the one every other performance row here is
  ultimately traced to — states the ceiling as **"more than 30,000 feet"**. The 60,000 ft figure is
  the Wikipedia infobox's, and the two were never reconciled when this file was first written.
- The physics sides with the fact sheet. At 18,288 m the ISA density is 0.1153 kg/m³; a 100 t B-1B
  on 181.16 m² needs **CL ≈ 0.65 even at its maximum permitted M1.25**. Measured against the
  corrected `fm-trim`, its 1g stall speed at that altitude and weight is **376 m/s = M1.274** —
  above its own `max_mach` of 1.25. **There is no speed at which the aircraft can hold level flight
  at 60,000 ft**, at any weight down to operating empty.
- The B-1A reached far higher, and this is the same B-1A/B-1B confusion the rejected Boeing speed
  came from: variable inlets, M2.2, a different envelope entirely.

**Why it passed the gate anyway, which is the part to remember.** Until
**fighters-legacy#1187** (fixed in engine v0.3.17) `fm-trim` evaluated a variable-geometry aircraft
at `ref_sweep_deg` at every Mach — for this aircraft, wings **spread** at 15°. Spread, the model
does hold 18,288 m and climbs at 3.80 m/s, which is why a row gating "3.8 m/s at 60,000 ft" was
written and believed. It was measuring a configuration the sweep schedule never commands: to stay
above the stall up there the aircraft must fly at M1.2+, and at M1.2+ the schedule commands 67.5°,
which costs it a third of its lift-curve slope. Locking the wing spread and re-running is what
separated the two cases, and the difference is exactly the 3.80 m/s the old row expected.

**Two lessons, both already paid for elsewhere in this pack:** a validator that agrees with a
published number can still be measuring the wrong aircraft, and a figure whose provenance is a
tertiary infobox should be checked against the primary source before it is gated — the fact sheet
disagreed with it in plain text the whole time.

---

## Gaps — what is **D** or **E**, and how each was resolved

No public source gives any of these. All are produced by `derive.py`; the values below are what
shipped in `b1b.toml`.

| Quantity | Why it is missing | How it was resolved |
|---|---|---|
| `ixx/iyy/izz` inertias | Never published for the B-1 in any public document | **E** — radii of gyration (0.34 / 0.38 / 0.44, airframe-class values) about span, length and their mean, at gross weight. 7.45e6 / 1.06e7 / 1.33e7 kg·m² |
| `[aero.cl_table]` | No public CL(α, M) database — no B-1 equivalent of NASA TP-1538 | **D** — DATCOM/Helmbold swept-wing lift slope at the spread reference, capped at 5.80 /rad so the transonic columns do not imply an unphysical CL_max. Each Mach column peaks at the 13° stall by construction, because `validate-flight-model` requires the table peak within 2° of `alpha_stall_deg` |
| `[aero.drag_polar]` `k` | Not published | **D** — 1/(π·AR·e) at the spread AR with an **E** Oswald efficiency of 0.80 → 0.0413 |
| `cd0`, `[aero.cd_wave]` | Not published | **D** — the *only* fitted quantities. `cd0` 0.0175 is pinned by the sea-level MIL climb row (flown subsonic and spread, where the wave curve contributes nothing); the wave curve's supersonic tail is pinned by the M1.25/50,000 ft anchor, measured **swept**. It peaks 0.0330 near M1.02 and decays to 0.0310 at M1.25 and 0.0270 at M1.60 — ⚑ **re-fitted 2026-08-16**, see below |
| `[wing_sweep]` scales | Not published | **D** — lift-slope and effective-AR ratios between the extremes, each blended through the share of lift the body and fixed glove carry regardless of sweep (**E**, 0.50) → cl_scale 0.666, k_scale 1.715. **Cross-checked** against the engine's F-14 example, whose spread/swept AR ratio is nearly identical (2.83 vs 3.01) and which uses 0.68 |
| `mac_m` | Not published | **D** — 4.758 m, from the mean chord (S/b) and an **E** taper of 0.30 read off the PD planform photographs |
| `cl_p`, `cl_da` (roll damping/authority) | No public roll-rate data | **E** — strip theory from geometry. Nothing checks these, exactly as on the F-5E and T-38A |
| `[aero.moments]` generally | The B-1's tail areas, arms and fin height are not published at all | **E** inputs → **D** derivatives. Signs and magnitudes checked (cn_beta +0.154, cm_alpha −2.06, all damping negative). Widest error bars in the model; `b1b.expect.toml` constrains none of them |
| engine thrust vs Mach/altitude | Only SL-static ratings are published | **D** — density lapse σ^0.85 × ram recovery, level fixed by the published static ratings. ⚑ The ram term **decays above M1.20** to model the B-1B's *fixed* inlet; left growing as M², the model reached M1.67 at 50,000 ft — B-1A installed thrust on a B-1B airframe |
| `max_g_structural` | Not published for the B-1B | **E** — 2.50, the middle of the +2.0…+3.0 g bomber band. With `has_fbw = false` there is no limiter, so it is a real, breakable limit |

### What the gate actually covers

`b1b.expect.toml` gates four rows: max level Mach at 50,000 ft (the calibration anchor), max level
Mach at 107 m (the `max_keas` placard), sea-level MIL rate of climb, and "still climbing at
50,000 ft" at a light weight. The gate was **proved to fail** before it was believed — perturbing
the supersonic wave drag by ±0.0030 drives the anchor to M1.003 and M1.315 respectively, both well
outside its 4% band.

### ⚑ The 2026-08-16 re-calibration — what moved, and why

Engine **v0.3.17** shipped **fighters-legacy#1187**, which makes `fm-trim` resolve wing sweep from
the Mach-driven schedule instead of evaluating every point at `ref_sweep_deg`. This aircraft is the
only one in the pack with a `[wing_sweep]` block, so it is the only one affected — the other four
were re-checked against the released binaries and are byte-identical in their results (F-5E 12/12,
F-16A 1/1, T-38A 5/5, MiG-21bis 4/4).

Against the corrected tool the model went from 3/3 met to 1 missed plus a non-convergent row, and
both failures were real. Three things changed in response:

1. **The supersonic `cd_wave` tail came down** (0.0345/0.0380/0.0400 → 0.0325/0.0310/0.0270 at
   M1.10/1.25/1.60). Flown swept, `k_scale` 1.715 supplies far more induced drag than the spread
   wing the curve had been fitted against, so the wave-drag level that reproduces M1.25 is lower.
   The old shape *rose* monotonically past its peak, which no area-ruled body does and no other
   aircraft in this pack does — that was the visible fingerprint of the defect, and it went unread.
   `cd0` did **not** move: it is pinned by a subsonic, spread-wing row that the fix does not touch.
2. **The sweep schedule was corrected** to the B-1B's four published detents (15° takeoff/loiter,
   25° cruise, 55° subsonic penetration, 67.5° dash). It previously commanded 45° at M0.85 — near
   mid-sweep at the aircraft's own cruise Mach. Worth 3.84 → 7.50 m/s of climb at 17,000 m; it does
   **not** move the calibration anchor, since both schedules command 67.5° at M1.25, and that was
   verified by measurement rather than assumed.
3. **The 60,000 ft ceiling row was rejected and replaced** — see the rejected-figures section above.

✅ **The published low-level limit (608 kn at 200–500 ft) is now MODELLED.** It is a
dynamic-pressure placard rather than a thrust limit, and `[aero.limits]` had no way to say so — only
`max_mach` — so this model was knowingly ~11% fast down low. Drag could not substitute: a `cd_wave`
steep enough to hold M0.92 at sea level walls off the transonic climb at 50,000 ft and makes the
M1.25 anchor unreachable, because one Mach-dependent term cannot serve both a sea-level q limit and
a stratospheric thrust limit.

**fighters-legacy#1181** added `max_keas`, and `b1b.toml` declares `max_keas = 608.0`. The field
reached the pack in engine **v0.3.17**, so the row is no longer commented out: `b1b.expect.toml`
now **gates** the low-level anchor, and the model trims **M0.924** against the published M0.919,
measured with the released v0.3.17 binaries rather than a local main build.

Also filed: **fighters-legacy#1182** — `validate-flight-model` applies no plausibility bands to
non-fighter roles at all, so nothing in this file is range-checked and a unit error would pass
silently.

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
