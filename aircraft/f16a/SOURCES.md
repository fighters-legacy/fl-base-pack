# F-16A Fighting Falcon (ADF) — data provenance

Every number in `f16a.toml`, `f16a.expect.toml`, `entities/f16a.toml` and the related weapon and
sensor files traces to a row here. Governed by `fighters-legacy/docs/legal/aircraft-likeness.md`.

**The clean-room rule.** Public sources only. Nothing in this aircraft comes from DCS, Falcon
BMS, War Thunder, X-Plane, or any other simulator's data files, in any form. Where a number
could not be sourced or defensibly derived, it is tagged as the estimate it is.

**Tags:** **[P]** published · **[D]** derived from published values by a stated method ·
**[E]** engineering estimate.

---

## Why this aircraft is different: transcription, not derivation

The F-5E's nine moment derivatives are DATCOM-derived — defensible, and unverifiable in
isolation. The F-16's are **published**: NASA TP-1538 tabulates the complete nonlinear
aerodynamic database of the F-16 — the only military jet with one in the public domain — and
this model is a *projection* of those tables onto the engine schema, performed by
`transcribe.py` (auditable, re-runnable, with `--check` invariants including a mandatory
confirmation that the raw data is relaxed-stability at its reference CG).

That inverts the burden of proof, which is fl-base-pack#19's entire purpose: **if `fm-trim`
disagrees with published F-16A performance, suspect the engine before this content.** It has
already paid out — see "Engine findings" at the bottom.

## Primary sources

| Key | Document |
|---|---|
| TP-1538 | Nguyen, Ogburn, Gilbert, Kibler, Brown, Deal — *Simulator Study of Stall/Post-Stall Characteristics of a Fighter Airplane With Relaxed Longitudinal Static Stability*, NASA Technical Paper 1538, Dec 1979. <https://ntrs.nasa.gov/citations/19800005879>. Public domain (US Government work). Fetched, not vendored; lives in the out-of-repo `f16-reference/` stash with `MANIFEST.md`. |
| TO-1 | T.O. 1F-16A-1 *Flight Manual, USAF/EPAF Series Aircraft, F-16A/B Blocks 10 and 15* (declassified; archive.org `f-16ab-flight-manual`). Image-only scan — limits and systems reference. |
| S&L | Stevens & Lewis, *Aircraft Control and Simulation* — used **only as an errata cross-check** on typed table cells (its appendix reprints the same TP-1538 database). No S&L-only value ships. |

TP-1538's Table VI (thrust) is dual-printed in SI and US customary units; the two agree to the
newton (21,420 lbf × 4.448 = 95,276 N), an internal cross-check that the transcription source
itself is consistent.

## Configuration statement

- **Variant: F-16A ADF (Air Defense Fighter).** The only F-16A that could employ the AIM-7
  (APG-66(V)1 with CW illumination) — and #23 requires a radar-missile host. Aerodynamically
  the ADF is a Block 15: TP-1538's data applies unchanged. Its visible deltas (IFF "bird
  slicer" antennas) are sub-visual at gameplay range and are not modelled.
- **Leading-edge flaps: flown on the schedule.** TP-1538's base tables are the LEF-deployed
  (25°) configuration; its `*_lef` tables are retracted; Appendix A (p. 34) publishes the FLCS
  schedule `dlef = 1.38·alpha − 9.05·(qbar/ps) + 1.45`. Every alpha row of the pack tables is
  evaluated **at its scheduled LEF** — retracted in cruise (cd0 = 0.0216, not the deployed
  0.049), deployed at high alpha (CL_max 1.89, not the retracted ~1.6). This is how the
  aeroplane actually flies, and it is the report's own blend equation (pp. 37–39).

## Geometry, mass, inertia

| Field | Value | Source |
|---|---|---|
| `wing_area_m2` | 27.87 | **[P]** TP-1538 Table I (300 ft²) |
| `wingspan_m` | 9.144 | **[P]** Table I (30 ft, clean); Fig. 2's 9.45 m includes the tip rails |
| `mac_m` | 3.45 | **[P]** Table I (11.32 ft) |
| `ixx/iyy/izz_kg_m2` | 12 875 / 75 674 / 85 552 | **[P]** Table I, at the 20,500 lb simulation weight. Fixed inertia is an engine limitation (the F-5E records the same one). |
| `ixz_kg_m2` | 1 331 | **[P]** 982 slug·ft², Table I — roll/yaw inertial coupling, now carried (engine#899). |
| `engine_ang_momentum` | 216.9 | **[P]** He, p. 40 — the F100 rotor's gyroscopic coupling (engine#899). |
| `mass_kg` | 7 167 | **[E]** 15,800 lb operating-empty-class. TP-1538 publishes only its 20,500 lb sim weight; 15,800 + ~55–65 % internal fuel is consistent with it. **Pending the SAC/T.O. weights hunt** — the honest current state. |
| `fuel_kg` | 3 162 | **[P]-class** 6,972 lb internal JP-4, widely published for the A/B |

## The CG chapter

TP-1538 references all moments to **0.35 c̄**, where the airframe is **relaxed-stability**: the
report says so in prose (App. A: *"slightly negative static longitudinal stability at low Mach
number ... desired static stability was provided artificially by means of angle-of-attack
feedback"*), and the data says so itself — `transcribe.py --check` **asserts**
dCm/dα(0.35 c̄) > 0 and measures **+0.059/rad** (scheduled-LEF blend, α 0–15°).

The engine has no pitch SAS: `has_fbw` is a G-limiter only (engine #816), and the validator
hard-rejects an unstable `cm_alpha`. The report's own total-moment equations carry the standard
CG transfer (`Cm_t += CZ_t·(xcg_ref − xcg)`; `Cn_t −= CY_t·(xcg_ref − xcg)·c̄/b`, pp. 38–39), so
the model flies the airframe at **xcg = 0.25 c̄ — the forward edge of the operational envelope**
— via that published transfer. Transcription plus the report's own arithmetic; not invention.

Sensitivity (printed by `transcribe.py --check`; x_ac = 0.335 c̄, CLα = 3.86/rad):

| xcg/c̄ | cm_alpha (/rad) | static margin |
|---|---|---|
| 0.25 | **−0.331** (shipped) | +8.5 % |
| 0.30 | −0.136 | +3.5 % |
| 0.35 | +0.059 | −1.5 % (the real jet, FLCS-stabilised) |

`cm_alpha = −0.33` is weaker than a conventional fighter's (the F-5E's is −1.01). That is the
RSS airframe's honest signature at its forward CG, not a soft number.

## Aerodynamics

All from TP-1538 Table III unless noted; report page numbers per block. The report interleaves
each alpha's β<0 and β≥0 rows — the β=0 column is the first value of each alpha block's second
printed line. Typed cells were spot-checked against the S&L reprint (errata check only).

| Block | Source & method |
|---|---|
| `cl_table` / `cd_table`, M 0.2 column | **[P]** CX(α,β=0,δh=0) p. 47 and CZ p. 54, LEF-scheduled blend (base pp. 45–63 + `*_lef` pp. 50/57/64), wind-axis projection CL = CX·sinα − CZ·cosα, CD = −CX·cosα − CZ·sinα. The α axis is the report's own 5° grid −10..45 (its simulation interpolated the same breakpoints; densifying adds no information). Rows above 45° deliberately not carried. |
| `cl_table`, M ≥ 0.6 columns | **[D/E]** Helmbold/Ackeret slope scaling (the F-5E's method) with an **[E]** CL_max envelope (1.85/1.45/1.25/1.05/0.90/0.80 at M 0.6/0.8/0.9/1.2/1.6/2.0) and the F-5E's post-peak collapse. TP-1538 is a low-speed database; these columns are validated only by the fm-trim gates until EM charts land. |
| `cd_table`, M ≥ 0.6 | **[D/E]** lift-dependent part scaled by (CL_M/CL_data)², monotone-rising past each column's peak (a stalled wing is never cleaner than one at its lift peak). |
| `cd_wave` | Shape **[E]** (area-ruled, modest rise); **level anchored to the published max level Mach 2.05** after the thrust extension was frozen — the one published supersonic point, spent once. |
| `cm_alpha` | **[P→D]** Cm(α, δh=0) p. 61 + ΔCm correction p. 65, η=1.0, transferred to 0.25 c̄ (above) |
| `cm_q` | **[P]** Cmq(α) p. 66 + scheduled ΔCmq,lef; mean α 0–15° = −5.82 |
| `cm_de` | **[P]** (Cm(δh=+10) − Cm(δh=−10))/20° from pp. 60/62, η=1.0 over that range (p. 65): −0.602/rad. The ±25° spread gives −0.465 (nonlinear falloff — the schema takes one scalar; the linear-range value is the FBW-relevant one). |
| `cl_beta` | **[P]** Cl(α, β=+4°) p. 84; strongly α-dependent (−0.10 at α0 → −0.27 at 15°); band mean −0.169 shipped, the spread recorded |
| `cn_beta` | **[P→D]** Cn(α, β=+4°) p. 75 (+0.20/rad) plus the report's yaw CG-transfer using CY_β = −1.12/rad from p. 68: **+0.247** |
| `cl_p` | **[P]** Clp(α) p. 91 + scheduled ΔClp,lef: −0.406 |
| `cn_r` | **[P]** Cnr(α) p. 81 + scheduled ΔCnr,lef: −0.397 |
| `cl_da` | **[P]** ΔCl(δa=20°) p. 87: 0.142/rad. TP-1538's positive aileron gives negative Cl; the engine's normalized right-roll command takes the magnitude (sign mapping documented in transcribe.py). |
| `cn_dr` | **[P]** ΔCn(δr=30°) p. 80: −0.085/rad |
| `alpha_stall_deg` | **[P]** 35° — the transcribed table's own CL peak (1.894): the AERODYNAMIC stall. Distinct from `alpha_limit_deg` below — this is where the wing actually stalls. |
| `alpha_limit_deg` | **[P]** 25.5° — the FLCS AoA cap (App. A). engine#900 makes `has_fbw` enforce it, so the model no longer flies past the real jet's computer-limited AoA. |
| `max_g_structural` / `min_g` | **[P]** +9.0/−3.0, the F-16's design limits (TO-1 Sec. V class) |
| `max_mach` | **[P]** 2.05 placard |
| `[aero.controls]` | **[P]** Table I deflection limits: δh ±25° **symmetric** (no `max_elevator_neg_deg` — that absence is data), flaperons ±21.5°, rudder ±30°. The differential tail (±5.375° at 4:1) has no schema slot. |
| `speedbrake_cd` | **[P]** 0.0101 — ΔCX,sb at low α, full 60° brake (p. 51). A *published* speedbrake number; the F-5E's is an estimate. |
| `gear_cd` | **[E]** 0.020 |

## Propulsion

**The deck is published**: TP-1538 Table VI (p. 93), idle/mil/max thrust over M 0.2–1.0 ×
0–15,240 m, transcribed verbatim into `[engine.mil_thrust]`/`[engine.ab_thrust]` (kN).

- **Installed-vs-brochure verdict** (the F-5E's ~7 % lesson): Table VI's sea-level M 0.2 values
  are 95.3 kN max / 56.4 kN mil against the F100-PW-200's ~106/64.9 kN static brochure ratings.
  The published simulation deck is installed-grade data — the right thing — so no correction
  factor is applied or needed.
- **M 1.2/1.6/2.0 extension [E]:** each altitude row continues at its own last published
  Mach-interval growth ratio, decayed 0.6 per further 0.2 M step — the fixed ventral inlet's
  pressure recovery falls off above M ~1.6, and raw geometric continuation would exceed
  sea-level static at altitude (wrong in the flattering direction). Frozen **before** cd_wave
  was anchored.
- **T_idle is published too** (including negative ram-drag cells at high M / low altitude) but
  the engine throttle model is linear `throttle × mil` with no idle deck — dropped, and filed
  as an engine enhancement from #19.
- **Fuel flows [D]:** SL deck thrust × public F100 TSFC-class figures — mil 12,680 lbf × 0.71
  lb/lbf/hr = 1.135 kg/s; max AB 21,420 × 2.48 = 6.69 kg/s. Idle 0.13 **[E]**.
  `spool_time_s = 3.0` **[D]** — the report models thrust response as a first-order lag
  (fig. 66(c)).

## Performance gate (`f16a.expect.toml`) and the document hunt

One active row: **max level Mach 2.05 at 40,000 ft with 2× AIM-9** (tolerance 5 %); the model
gives 2.06. Everything else is held back with reasons in the expect file itself:
the **T.O. 1F-16A-1-1 performance manual** (EM/Ps/turn charts, cruise data) has not been located
in the public record yet — TO-1 (in hand) is the flight manual, limits and systems only. When
the -1-1 or SAC charts land, sustained-g and Ps rows join the gate, F-5E-ladder style.
Stall rows are **deliberately absent**: published F-16 minimum speeds are FLCS angle-of-attack
limiter speeds, not aerodynamic stalls — a gate row would compare two different quantities.

Model predictions recorded now for future comparison (fm-trim, full gross 10,329 kg):
SL: Vs(1g aero) 56 m/s, max M 1.16, ROC(AB) 238 m/s, sustained 7.6 g;
36k ft: max M 1.92 clean.

## Known limits — stated rather than hidden

Engine **#907** (v0.3.5) closed most of the gaps this deck had to drop through v0.3.4; the list
below is split into what is now modelled and what is still out.

**Now modelled (engine#899/#900/#901), un-dropped from the published data:**

- **FLCS AoA cap** — `alpha_limit_deg = 25.5` (App. A). `has_fbw` now holds the jet to it, plus a
  **negative-g limiter** against `min_g_structural` (#900). The sim F-16A no longer visits the
  25–35° range the real flight-control computer forbids.
- **α-dependent dampers** — cm_q/cl_p/cn_r now ship as the report's α **tables** (which override
  the scalars), so the α-dependence is carried, not band-averaged away (#899).
- **Cm₀** (−0.019 at the model CG, ≈ −3.3° zero-elevator trim shift), **Ixz** (1,331 kg·m²),
  **engine angular momentum He** (216.9 kg·m²/s), **adverse yaw** cn_da (−0.027) and **rudder
  roll** cl_dr (+0.027) — all now have schema slots and are authored (#899).
- **Single-engine damage** — `[damage.subsystems.engine]`: one F100, total thrust loss, no yaw
  (#901), replacing the tier-thrust-factor stopgap.

**Still out:**

1. **The FLCS itself is not modelled.** The real jet is unstable at 0.35 c̄ and stabilised by its
   analog FBW; this model gets stability from its forward CG instead (see the CG chapter), so
   pitch feel is stiffer than the real aircraft's. The envelope protections above are now real,
   but roll-rate command shaping (308°/s) and high-α rudder fadeout are not.
2. **Mach synthesis above 0.6** — TP-1538 is low-speed; the high-M columns are [D/E].
3. **Secondary dampers dropped** — CXq, CZq, CYp, CYr, Clr, Cnp are published but have no schema
   slots (axial and cross-axis rate damping).
4. **Speed-brake pitch/lift increments** (ΔCm,sb, ΔCZ,sb) not authored — only the drag increment
   (dCX_SB) is typed, and it is already carried by `speedbrake_cd`. #907 added `speedbrake_cl` /
   `cm_speedbrake` slots, but the lift/pitch α-tables are not yet reduced to honest scalars here.
5. **Idle-thrust deck** — Table VI publishes it (incl. negative ram-drag cells) and #898 added the
   `[engine.idle_thrust]` slot, but the idle row is **not yet typed** in `transcribe.py` (the PDF
   is reference-only, not vendored). Authoring the idle row is the one remaining un-drop; until
   then part-throttle rides the linear `throttle × mil` path.
6. **Deep stall not represented**: the table ends at 45° and edge-clamps — and with the 25.5° AoA
   cap now enforced, the jet does not reach the report's own ~60° deep-stall subject anyway.
7. **Fixed inertia** at the 20,500 lb loading; `mass_kg` is [E] pending the weights hunt.

## Mesh — `f16a_build.py`

**Mesh provenance: `generated`.** Build command:
`blender --background --python aircraft/f16a/f16a_build.py -- --out aircraft/f16a`.
Byte-reproducible (meshlib determinism gate, now parametrized over every generated aircraft).

Geometry sources: TP-1538 Table I dimensions **[P]**, Figure 2's dimensioned three-view
(printed anchors: 15.09 m incl. probe, 5.01 m height, 9.45 m span over rails) — and an honesty
note: unlike the F-5E's programmatically ink-traced NASA drawing, Figure 2 is a small line
sketch, so the station table is **manual proportion reads against the printed anchors [E]**.
The planform closes against the published numbers regardless: c_root = 2S/(b(1+λ)) with the
published 16.5/3.5 ft chords reproduces the published MAC to 0.8 %, and the trailing edge
comes out −1.6° (near-straight), as the real wing is. Cross-checked visually against
public-domain USAF photography (see reference imagery). No scale plans, no other model's
geometry, no markings in the geometry.

Deliberate simplifications, recorded: ADF bird-slicer IFF antennas omitted (sub-visual);
boundary-layer diverter not modelled; strake is a straight-taper panel rather than the real
ogival curve; single material/primitive until engine #839.

## Textures — `f16a_textures.py`

**Texture provenance: `generated`.** Deterministic procedural masters (seeds 61/62), `--check`
drift gate. Generic two-grey scheme; panel grid matches the build script's feature stations.
**No markings, no insignia, no manufacturer marks** (policy §4). No external reference image
was used; nothing to license.

## Reference imagery

Kept out-of-repo in `f16-reference/` with per-file licence rows in its `MANIFEST.md`
(PD/CC0 only). Current contents: NASA TP-1538 (PD, NTRS), T.O. 1F-16A-1 (declassified,
archive.org). Photographic walk-around references consulted via public-domain USAF imagery;
any image used for a future mesh iteration gets a MANIFEST row before it is used.

## Engine findings this aircraft produced (#19's purpose, receipts attached)

1. **fm-trim's negative-trim-alpha sentinel** (fighters-legacy#896): the cambered,
   LEF-scheduled deck trims 1 g at negative alpha above M ~0.65 at sea level; fm-trim's −1
   sentinel read that as "cannot fly" and reported a top speed that fell as fuel burned.
   Every symmetric-table aircraft was blind to it.
2. **Kind-typed hardpoints could not describe this airframe** (fighters-legacy#895): the wet
   stations carry bombs OR rocket pods OR tanks; stations are now allowed-driven.
3. **Idle-thrust deck, α-dependent dampers, Ixz, engine angular momentum, adverse-yaw/rudder-roll
   slots, Cm₀, FLCS AoA + negative-g limiting, single-engine damage** — schema gaps surfaced by
   transcription, filed as engine enhancements and **all closed in engine#907** (v0.3.5). This
   deck now authors every one of them except the idle row (published, not yet typed) and the
   speed-brake lift/pitch increments (published as α-tables, not yet reduced to scalars).
