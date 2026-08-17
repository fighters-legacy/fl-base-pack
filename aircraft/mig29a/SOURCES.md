# MiG-29A Fulcrum-A (izdeliye 9.12) — data provenance

Every number in `mig29a.toml` and `mig29a.expect.toml` traces to a row in this file.

**Clean-room rule.** Public sources only: manufacturer publications, declassified government
documents, and published reference annuals. **No value in this aircraft is taken from any flight
simulator, game, or commercial 3D model** — not DCS, not War Thunder, not X-Plane, and not a wiki
that copied one of them. Where a figure could only be found in such a source, it is recorded here
as *rejected*, with the reason. See `docs/legal/aircraft-likeness.md` in the engine repo.

Each row is tagged:

- **P** — *published*: read directly from a primary or named secondary source.
- **D** — *derived*: computed from published values by a stated method. Reproducible.
- **E** — *engineering estimate*: not published and not derivable. A judgement call, flagged as such.

## The provenance caveat this aircraft was filed with — and how it actually resolved

Issue #43 predicted the record would be "better than the MiG-21, not as good as the F-16", and that
is exactly how it came out — but for a different reason than expected. The issue expected the
post-1990 German Luftwaffe operation of ex-NVA Fulcrums to be the source. It is not: the German
evaluation produced a great deal of published *tactical assessment* (see "Realism context" below)
and almost no published *numbers*.

What carries this aircraft instead is **a manufacturer specification table**. RAC MiG published a
per-variant performance table for the MiG-29 / MiG-29UB / MiG-29SE family on its own corporate site.
That is a stronger class of source than the MiG-21bis had for its performance rows, and stronger
than the B-1B's AF-via-Wikipedia chain: it is the design bureau's successor company publishing
figures for its own product.

What is still missing is the same thing that was missing for the MiG-21: **there is no public
aerodynamic database.** No CL/CD tables, no lift-curve data, no engine SFC deck. Every
*aerodynamic* row in the flight model will be **D** or **E**, and the `[aero]` block will be
derived, not read. That is the honest state of the record and it is unchanged from #41.

## The aircraft modelled is the **9.12**, and the manufacturer table's column is the **9.12B**

The same variant discipline the B-1B applied to B-1A documents, and the MiG-21bis applied to the
F-13 manual, applies here — but it costs much less, and the reason matters.

RAC MiG's table column is labelled **"MiG-29 vers. B"** — the 9.12B, the downgraded-avionics export
variant sold outside the Warsaw Pact. The aircraft this issue models is the 9.12 (and its Warsaw
Pact 9.12A sibling, which is what East Germany flew).

**The differences between 9.12, 9.12A and 9.12B are radar, optoelectronics, IFF and nuclear
wiring — not aerodynamics, not structure, not the engine.** All three share the airframe, the
RD-33, the fuel system and the flight envelope. So the manufacturer's dimensions, weights, speeds,
ceiling, g limit and ferry ranges are used as **P** for the 9.12 without qualification; only the
*sensor* rows are variant-sensitive, and those are taken from the 9.12-specific text instead
(N019 Rubin, OEPS-29, Shchel-3UM — see "Sensors").

---

## Primary sources

| Key | Document |
|---|---|
| **RAC-MIG** | Russian Aircraft Corporation "MiG", *MiG-29/MiG-29UB/MiG-29SE* product page, performance table (page 2 of 2), dated 08 December 2014 — read via the Internet Archive capture of 18 May 2016 of `migavia.ru` — <http://www.migavia.ru/index.php/en/production/the-mig-29-fighters-family/mig-29-mig-29ub-mig-29se> — **manufacturer** |
| **GORDON via WIKI** | Wikipedia, *Mikoyan MiG-29*, where referenced to Gordon, *Mikoyan MiG-29* (Famous Russian Aircraft, Midland, 2006) — cited pages given per row — <https://en.wikipedia.org/wiki/Mikoyan_MiG-29> |
| **JAU via WIKI** | Same article, where referenced to *Jane's Aircraft Upgrades*, "MiG-29", 10 July 2009 (subscription) |
| **FLUGREVUE via WIKI** | Same article's climb-rate row, referenced to *Flug Revue*, "MIG MAPO MiG-29", 1 September 1998 |
| **RAFH via WIKI** | Same article's flight-control text, referenced to *Russia Air Force Handbook*, International Business Publications USA, 2007, p. 180 |
| **RD33-WIKI** | Wikipedia, *Klimov RD-33* — engine dimensions, mass, pressure ratio, bypass ratio |
| **JAWA-MIRROR** | *Jane's All the World's Aircraft 2007–2008* MiG-29 entry, mirrored at `janes.migavia.com` — **the data block there is the MiG-29K**, and is used ONLY for wing planform angles (see the geometry section) |
| **R27-WIKI / R73-WIKI / GSH-WIKI** | Wikipedia, *R-27 (air-to-air missile)*, *R-73 (missile)*, *Gryazev-Shipunov GSh-30-1* |

### Source-access caveats — read before trusting a **P** tag

- **RAC-MIG was read through the Internet Archive**, because `migavia.ru` no longer serves the page.
  The capture is a complete rendered page with the table intact, not a fragment. Note for future
  work in this repo: **`web.archive.org` is not fetchable by the WebFetch tool** and had to be
  retrieved with `curl`.
- **`af.mil` returns HTTP 403 to every non-browser request**, base mirrors included. The National
  Museum of the USAF fact sheet for the MiG-29A therefore could **not** be read, and nothing in this
  file is sourced to it. This is the same wall the B-1B lane hit; it is a property of the host, not
  a transient failure. If a human opens it in a browser, its rows are worth cross-checking here.
- *Jane's Aircraft Upgrades* is subscription-gated and was not read directly; the one row taken
  from it is tagged **P (JAU via WIKI)**.

---

## Geometry

| Row | Value | Tag | Source / method |
|---|---|---|---|
| Length overall | **17.32 m** | P | RAC-MIG |
| Wing span | **11.36 m** | P | RAC-MIG |
| Height | **4.73 m** | P | RAC-MIG |
| Wing reference area | **38.0 m²** | P | Wikipedia spec block (`wing area sqm = 38`) |
| Aspect ratio | **3.396** | D | `11.36² / 38.0` — reproduces the widely published "3.4" exactly, so span and area are mutually consistent |
| Wing LE sweep, outer panel | **42°** | P | JAWA-MIRROR |
| LERX LE sweep | **73° 30′** | P | JAWA-MIRROR |
| Airfoil | *not established* | — | see below |

⚑ **The two sweep angles come from the Jane's MiG-29K block, and that needs saying plainly.** The K
is a navalised derivative with a *larger* wing (11.99 m span, 42.0 m² area) — so its **span and area
are NOT used here**, and the RAC-MIG/Wikipedia figures for the 9.12 are used instead. What is
carried across is the **planform angles**, which are a shape property the K inherited unchanged from
the land-based wing. This is the same admissibility rule the MiG-21bis applied to the F-13 manual
(geometry crosses variants, performance does not) and the B-1B applied to the B-1A NTRS documents.

⚑ **REJECTED — Wikipedia's design text says the LERXs are "swept at around 40°".** That is not a
LERX angle; 40° is the *wing* sweep, and the figure appears to be a garbled restatement of the 42°
outer-panel value. A leading-edge root extension that generates the vortex lift this aircraft is
famous for is necessarily a highly swept surface, and Jane's 73° 30′ is the physically sensible
number. The 40° figure must not be restored.

**Airfoil is an open item.** Lednicer's *Incomplete Guide to Airfoil Usage* — the source used for
the MiG-21bis — has no MiG-29 entry reachable in the copy read. No Soviet airfoil designation for
this wing was found in any admissible source. The flight model will therefore derive its lift curve
from planform (LERX-augmented, per the vortex-lift treatment the MiG-21bis's Polhamus method
established) rather than from a named section, and `mig29a.toml` will say so. **This is an [E], and
it will be labelled [E] in the file, not quietly assumed.**

---

## Masses

| Row | Value | Tag | Source / method |
|---|---|---|---|
| Normal take-off weight | **14,900 kg** | P | RAC-MIG ("Take-off weight — standard") |
| Maximum take-off weight | **18,000 kg** | P | RAC-MIG ("Take-off weight — maximum") |
| Internal fuel, volume | **4,300 L** | P | GORDON via WIKI p. 341 — **Fulcrum-A specific**: six tanks, four fuselage + one per wing |
| Internal fuel, mass | **3,500 kg** | P | Wikipedia spec block (`fuel capacity = 3500 kg internal`) |
| Implied fuel density | **0.814 kg/L** | D | `3500 / 4300` — inside the normal range for T-1/TS-1 kerosene (~0.78–0.81), so the volume and mass rows corroborate each other rather than merely coexisting |
| Empty weight | **10,900–11,000 kg** | P | **conflicted, see below** |
| Wing loading at normal TO | **392.1 kg/m²** | D | `14,900 / 38.0` |
| Thrust-to-weight at normal TO | **1.114** | D | `2 × 81.40 kN / (14,900 × 9.80665 N)` |

⚑ **Empty weight is the one genuinely unresolved mass.** Wikipedia's spec block says 11,000 kg;
aerospaceweb.org says 10,900 kg. Neither states a datum (equipped? with gun? with pilot?), the two
are within 1%, and **RAC MiG does not publish an empty weight at all**. Nothing here can settle it.
The flight model will use the value that closes the mass budget against the two figures the
manufacturer *does* publish (14,900 kg normal TO and 3,500 kg internal fuel) and will state the
closure — the same method that resolved the MiG-21bis's empty weight against its 8,725 kg gross.

⚑ **REJECTED — Wikipedia's own `wing loading = 403 kg/m²` and `thrust/weight = 1.09` rows are not
consistent with the gross weight stated four lines above them in the same template.**
`403 × 38.0 = 15,314 kg` and `162.8 kN / 1.09 = 15,230 kg`, but the block's own `gross weight kg`
is **14,900**. Both derived rows are computed against a ~15,240–15,310 kg aircraft — which is
aerospaceweb's "normal takeoff 15,240 kg", not the manufacturer's 14,900 kg. **Neither derived row
is used.** Wing loading and T/W are recomputed here from the manufacturer's own mass. This is
exactly the class of error the pack's measurement rules exist to catch: a plausible number that
silently describes a different aeroplane from the one in the next row.

---

## Powerplant — 2 × Klimov RD-33 (series 2/3)

| Row | Value | Tag | Source / method |
|---|---|---|---|
| Take-off thrust, per engine | **8,300 kgf** | P | RAC-MIG ("Take-off thrust, kgf: 2×8300") |
| Take-off thrust, per engine (SI) | **81.40 kN** | D | `8,300 × 9.80665` |
| Total AB thrust | **162.79 kN** | D | `2 × 81.40` |
| Dry (military) thrust, per engine | **49.42 kN** | P | GORDON via WIKI p. 335 |
| Engine dry mass | **1,055 kg** | P | RD33-WIKI |
| Overall pressure ratio | **21:1** | P | RD33-WIKI |
| Bypass ratio | **0.49** | P | RD33-WIKI |
| Engine length / max diameter | **4,229 mm / 1,040 mm** | P | RD33-WIKI |
| Dry-to-AB thrust ratio | **0.607** | D | `49.42 / 81.40` |

The RD-33 article's own figures (50.0 kN dry, 81.3 kN AB) agree with the manufacturer's 8,300 kgf
and with Gordon to well inside 1.5%. **The manufacturer's kgf figure is the one used**, because it
is the only one stated by the party that builds the engine, and because it is quoted for the same
airframe column as the rest of the performance table.

⚑ **SPECIFIC FUEL CONSUMPTION IS NOT PUBLISHED and was not found in any admissible source.** The
MiG-21bis had a per-regime SFC table (via the R-25 article's leteckemotory.cz citation); the RD-33
has no equivalent in the public record. Fuel flow will therefore be **[E]**, anchored by working
backwards from the two published range figures (1,430 km on internal fuel, and the 700–900 km
combat radius with a stated stores fit) rather than assumed from a comparable engine. That method
is stated here so the eventual number is reproducible and arguable.

---

## Performance — the flight-model anchors

| Row | Value | Tag | Source / method |
|---|---|---|---|
| Max speed at altitude | **2,400 km/h** | P | RAC-MIG |
| Max Mach number | **2.25** | P | RAC-MIG |
| — consistency check | 2,400 km/h = 666.7 m/s; at ≥11 km ISA, `a = 295.07 m/s` → **M 2.259** | D | the two manufacturer rows are self-consistent to 0.4% |
| Max speed near ground | **1,500 km/h** | P | RAC-MIG |
| — as a Mach number at SL | **M 1.224** | D | `416.67 / 340.294` |
| — as calibrated airspeed | **810 KEAS** | D | at SL, EAS = TAS = 416.67 m/s = 809.9 kn |
| — as dynamic pressure | **106.3 kPa** | D | `½ × 1.225 × 416.67²` |
| Service ceiling | **18,000 m** | P | RAC-MIG |
| Max g | **+9** | P | RAC-MIG |
| Rate of climb | **330 m/s** | P | FLUGREVUE via WIKI |
| Range, max internal fuel | **1,430 km** | P | JAU via WIKI |
| Ferry range, clean | **1,500 km** | P | RAC-MIG |
| Ferry range, 1 drop tank | **2,100 km** | P | RAC-MIG |
| Combat range, 2×R-27 + 4×R-73, high altitude | **700–900 km** | P | GORDON via WIKI pp. 66, 377 |

⚑ **The 1,500 km/h low-level figure is a dynamic-pressure placard, and this aircraft is the pack's
second `max_keas` customer.** 810 KEAS sits exactly in the class band the B-1B lane established
(the F-5E and T-38A carry the same "710 KEAS or M#" pairing, and the F-16's structural limit is
800 KEAS). It is **not** a thrust limit: this airframe has ample thrust at sea level. The B-1B
proved that drag cannot substitute for a q placard without breaking the high-altitude anchor
(engine #1181, shipped in v0.3.17), so `[aero.limits] max_keas = 810` is the right expression and
the low-level row can be gated from the start — unlike the B-1B, which had to wait for a release.

⚑ **REJECTED — aerospaceweb.org's "max speed at sea level 1,200 km/h (Mach 1.06)".** It contradicts
the manufacturer by 20%, and the manufacturer's figure is the one that is internally consistent
(810 KEAS is a credible fighter placard; 1,200 km/h at SL is 648 KEAS, well *below* the class and
implausibly conservative for a 9-g air-superiority fighter).

⚑ **REJECTED — aerospaceweb.org's "ferry range 2,900 km".** That figure is traceable: RAC-MIG's own
table gives 2,900 km for the **MiG-29SE with THREE drop tanks**. The 9.12 has one centreline wet
station and cannot carry three tanks, so the figure describes a different aircraft. Recorded here
because the misattribution is instructive, not because the number is in doubt.

⚑ **REJECTED — aerospaceweb.org's "thrust 36,600 lb (162.8 kN) per engine".** 162.8 kN is the
**total for both engines** (`2 × 81.4`), mislabelled as per-engine. Taken at face value it would
double this aircraft's thrust. Flagged loudly because it is the exact shape of error that survives
a sanity check — the number is right, the label is wrong.

⚑ **NOTED — Wikipedia's `max speed kmh = 2450` and `max speed mach = 2.3+`** disagree slightly with
the manufacturer's 2,400 / 2.25. The manufacturer's pair is used. The difference is inside the
noise of "clean, ISA, which mass?", but there is no reason to prefer the looser figure.

---

## Flight controls — the `has_fbw = false` case this aircraft exists to prove

Issue #43's central claim is confirmed by the record, and precisely:

- **"The MiG-29 has hydraulic controls and a SAU-451 three-axis autopilot but, unlike the Su-27, no
  fly-by-wire control system."** — Wikipedia design section. **P.**
- **"The controls have 'soft' limiters to prevent the pilot from exceeding g and alpha limits, but
  the limiters can be disabled manually."** — RAFH via WIKI. **P.**
- Airframe **"stressed for up to 9 g"** — same section, and RAC-MIG's table row agrees (`Maximum
  G-load 9`). **P.**

This is exactly the `has_fbw = false` half of engine #816. A *disableable soft* limiter is not a
flight-control-system G limiter: it does not have final authority over the pilot, and the engine's
`has_fbw = true` path (which does) would be the wrong model. The F-16A in this pack is the
protected case; this aircraft is the pilot-limited one, and the pair is what exercises both sides
of #816. `mig29a.toml` will carry `has_fbw = false` with this paragraph's sources cited inline.

---

## Sensors — 9.12-specific, and the one that matters for #17

| Row | Value | Tag | Source |
|---|---|---|---|
| Fire-control system | **RLPK-29**, incl. N019 *Sapfir-29* radar + Ts100.02-02 digital computer | P | GORDON via WIKI p. 58 |
| Radar type | coherent pulse-Doppler, look-down/shoot-down; twisted-polarisation Cassegrain antenna (not a planar array) | P | Wikipedia sensors section |
| Radar design goal | ≥100 km detection and tracking vs a fighter-sized target | P | same |
| Radar achieved range | **NOT PUBLISHED** — the design goal was explicitly *not* attained | P | same |
| IRST | **OEPS-29** optoelectronic system (S-31E2 KOLS head) | P | Wikipedia variants section |
| RWR | SPO-15 *Beryoza* | P | Wikipedia avionics |
| Helmet-mounted sight | Shchel-3UM | P | Wikipedia variants section |

⚑ **The N019's real range is not in the public record, and the pack must not invent one.** What *is*
published is unusually useful: the radar was specified for ≥100 km, **failed to reach it**, reverted
to Sapfir-23ML analogue architecture, and was described as unable to support the R-27 at that
missile's own reach. So the honest treatment is the **RP-22 precedent from #41**: bracket the
sensor between two anchors the pack already ships rather than cite an enthusiast figure. Here the
bracket is well-formed — floor at the pack's APG-66 (30 nm search), ceiling below the stated-and-
missed 100 km — and the resulting def is tagged **[E] BRACKETED** exactly as `rp22.toml` is.

⚑ **This aircraft is the host `irst.toml` has been waiting for.** Pack #17's remaining scope is
`sam_radar` (needs ground units) and a standalone passive IRST (needs a host airframe); the OEPS-29
is that host, and it is the first genuine IRST in the pack — the two existing `ir` defs are missile
seeker heads, not a search sensor. `sensors/oeps29.toml` rides this aircraft's entity stage and
advances #17, the same way `rp22.toml` and `r60m_seeker.toml` did on #41.

---

## Armament

| Row | Value | Tag | Source |
|---|---|---|---|
| External stations | **6** | P | RAC-MIG ("Number of external stations 6") |
| Gun | **GSh-301** 30 mm | P | RAC-MIG |
| — cartridge / rate / muzzle velocity / mass | 30×165 mm / 1,500–1,800 rpm / 900 m/s / 46 kg | P | GSH-WIKI |
| — magazine | **150 rounds** on early variants, reduced to 100 later | P | Wikipedia armament |
| Medium-range AAM | **2 × R-27R1** (semi-active radar homing) | P | RAC-MIG |
| — mass / length / diameter / span / warhead | 253 kg / 4.08 m / 230 mm / 772 mm / 39 kg | P | R27-WIKI |
| — range, R-27R1 | up to **75 km** | P | R27-WIKI |
| Short-range AAM | **6 × R-73E** (all-aspect IR) | P | RAC-MIG |
| — mass / length / diameter / span / warhead / speed | 105 kg / 2.93 m / 165 mm / 510 mm / 7.4 kg / M2.5 | P | R73-WIKI |
| — range, R-73E | **30 km** | P | R73-WIKI |

⚑ **Station count: the manufacturer says SIX, Wikipedia says seven (6 underwing + 1 fuselage).**
Both are right about a different thing. The fuselage station is the centreline **wet** point for the
1,500 L drop tank; it is not a weapons station on the 9.12. The entity will model **six weapon
stations** per the manufacturer, and the centreline is out of scope until a tank store exists — the
same ruling the MiG-21bis made about its fuel-plumbed fifth station.

⚑ **The R-27R1 gives this aircraft the pack's second SARH shooter**, opposite the F-16A's AIM-7M.
That is the radar-vs-radar engagement #43 was filed to make possible, and it reuses the #23
pattern directly (`role = "seeker"` on the seeker head, `emitter = false` — a receiver, not an
emitter). The R-27's 39 kg warhead against the AIM-7M's is the asymmetry worth preserving.

**Not modelled** (recorded so the omissions are deliberate, not forgotten): R-60/R-60M — the pack
ships `r60m` for the MiG-21bis and the Fulcrum could carry it, but the R-73 is the 9.12's defining
missile and the reason its DACT record reads the way it does; air-to-ground stores (S-5/S-8/S-24
rockets, FAB/RBK bombs) — real for this aircraft but outside the air-superiority slice #43 asks for.

---

## Realism context — what the German evaluation actually established

Not flight-model data, but it constrains the `[ai]` and `[signatures]` blocks and is worth having
on the record, because it is the best-documented Western assessment of any aircraft in this pack.
All from the Wikipedia article's operational-history section, referenced to *Code One* (July 1995),
*Air & Space/Smithsonian*, and Lake 1997 p. 70:

- The Fulcrum was **more manoeuvrable at slow speed** than the F-15, F-16, F-14 and F/A-18 of the
  day, and the **R-73 with the Shchel-3UM helmet sight was superior to the contemporary AIM-9** —
  Luftwaffe pilots achieved lock on anything the pilot could see, out to nearly 45° off boresight.
- **Beyond visual range it was the weaker aircraft.** German pilots found it hard to lock and fire
  the R-27 while defending against longer-ranged American radars and the AIM-120.
- The Luftwaffe's own conclusion: **best used as a point-defence interceptor**, not for fighter
  sweeps over hostile airspace.

That is a coherent brief for the entity: high `[ai]` skill is not the differentiator, and the
aircraft should not be given a radar that flatters it. The BVR weakness is a *sensor* property, and
modelling it honestly is the same discipline that kept the MiG-21bis's RP-22 short.

---

## Open items — status after stage 2 (the flight model)

1. ✅ **Airfoil** — still no admissible source, and resolved as planned: the lift curve is derived
   from planform by the Polhamus method with a LERX vortex term (`derive.py`), not from a named
   section. The vortex constant `KV0 = 1.80` is the single most consequential [E] in the aircraft.
2. ✅ **Empty weight** — **11,000 kg**. Mass closure was run and it does **not** discriminate:
   11,000 closes to +0.2% of the published normal take-off weight and 10,900 to −0.5%, both well
   inside the unstated-datum ambiguity. Since closure cannot choose, the pack takes the **heavier**
   figure — where the record is silent, do not flatter the aircraft.
3. ⚠️ **RD-33 SFC** — **NOT resolved, and the promised method failed.** This file said it would be
   "backed out of the published range figures". It cannot be: the model's specific range at the
   class SFC is 286 m/kg against the 409 m/kg the published 1,430 km implies — about 30% thirstier —
   and the published range states no profile, altitude or reserves to back anything out of. Rather
   than invent an implausibly efficient engine to fit an unconditioned number, the flows stay
   honestly **[E]** and range is **not gated**. The discrepancy is in the conservative direction.
4. ✅ **MAC** — **3.746 m [D]**, the reference-trapezoid MAC at an assumed 0.25 taper ratio. It is a
   [D] resting on an [E], which is weaker than the MiG-21bis's published 4.002 m, and says so.
5. ⏳ **N019 range** — unchanged; still to be bracketed [E] at the sensor stage (stage 4).
6. ⏳ **NMUSAF fact sheet** — unchanged; `af.mil` 403s every non-browser request. Worth a human
   cross-check.

### New from stage 2

7. **Oswald factor is calibrated against another MODEL, not a publication.** No public MiG-29
   energy-manoeuvrability data exists, and neither speed anchor constrains induced drag at all. At
   the geometric `e = 0.75` the aircraft out-sustained the F-16A's published-data model 8.6 g to
   7.1 g — contradicting the Luftwaffe assessment above, which is explicit that the Fulcrum's edge
   was nose authority at low speed and that it *lost* the energy fight. `e = 0.62` brings sustained
   turn to parity (17.7 vs 17.3 deg/s) while instantaneous stays well ahead (27.6 vs 22.0). No turn
   row is gated, because gating one would test the model against a number derived from another model.
8. **Installed vs uninstalled thrust is not identifiable here.** The published RD-33 ratings are
   uninstalled brochure figures; the F-16A's deck is TP-1538 installed data. Applying a 6%
   installation loss and re-fitting `cd0` to hold the M2.25 anchor returns the sustained turn
   unchanged and drives `cd0` to 0.0235 — below the F-16A's *published* 0.0216 for a bigger
   twin-engine airframe. One anchor cannot separate two unknowns, so the published rating stands
   and the uncertainty is carried in the Oswald factor instead.
