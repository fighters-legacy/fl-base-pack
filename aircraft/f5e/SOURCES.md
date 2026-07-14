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
| `CL_max` @ M 0.60 | **1.255** | **D** — from the TO's published max-lift point (5.2 G at 15,000 ft / M 0.60). Pure lift; no drag or thrust assumption. Derivation and cross-checks in `f5e.expect.toml`. |
| `alpha_stall_deg` | **19** | **D** — CL_max ÷ lift-curve slope. Slope from the low-AR Helmbold relation, `CL_α = 2π·AR/(2+√(AR²+4))` = 3.80 /rad = 0.0664 /deg for AR 3.82; 1.255 / 0.0664 = 18.9°. Symmetric airfoil, so α₀ = 0. |
| `cd0` | 0.0200 | **P?** SP-468 App. A Table V — **cited via WIKI, unverified at source** (NASA's host is dead). The one drag number with a NASA lineage. Treat with caution. |
| max L/D | 10.0 | **P?** SP-468, same caveat |
| `[aero.moments]` (9 derivatives) | — | **D** — USAF DATCOM, from the NASA-SPIN geometry. Method documented inline in `f5e.toml`. |
| `[aero.cd_table]` | — | **D** — fitted to the TO's published Ps ladder. See the note below. |

### Rejected: the LEX CL_max figures

The widely-circulated claim that the F-5E's LEX adds ~25% to CL_max (and the F-5A's ~10%) traces
back to a **DCS World flight-manual PDF**. It is not in the TO, not in NASA-SPIN, and not in any
primary source. **Rejected under the clean-room rule.** If you find these numbers quoted elsewhere,
assume sim-derived until proven otherwise.

### Why the drag model is a table, not a polar

The engine's original drag model was a strictly parabolic polar (`cd0 + k·CL²`). The F-5E's published
Ps ladder **cannot be fitted by any value of `k`**: the implied induced-drag coefficient rises by a
factor of **3.5×** from 1 G to max lift, because a real wing's drag grows far faster than CL² as it
approaches stall. Fitting `k` to cruise gives an aircraft that sustains 3.9 G where the manual says
3.3; fitting it to the turn overstates cruise drag and wrecks range.

This is what motivated `[aero.cd_table]` (engine issue #820) — a `CD(α, Mach)` table, which is also
the form NASA publishes real aerodynamic data in. The F-5E's table is fitted to the TO points in
`f5e.expect.toml`.
