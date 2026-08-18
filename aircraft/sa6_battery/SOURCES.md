# 2K12 Kub (SA-6) battery element — data provenance

Every number in `entities/sa6_battery.toml`, `weapons/3m9m.toml`, `sensors/1s91.toml`,
`sensors/3m9m_seeker.toml` and `tools/groundlib/src/fl_groundlib/sa6.py` traces to a row in this
file.

**Clean-room rule.** Public sources only. **No value in this unit is taken from any flight
simulator, game, or commercial 3D model** — not DCS, not War Thunder, not Arma, and not a wiki that
copied one of them. The mesh is not traced from a scale plan, a 3-view or a cutaway. The likeness
policy in `docs/legal/aircraft-likeness.md` (engine repo) was written for aircraft; it is applied
here unchanged, because nothing in its reasoning is about wings.

Each row is tagged:

- **P** — *published*: read directly from a named source.
- **D** — *derived*: computed from published values by a stated method. Reproducible.
- **E** — *engineering estimate*: not published and not derivable. A judgement call, flagged as such.

## Primary sources

| Key | Document |
|---|---|
| **KUB-WIKI** | Wikipedia, *2K12 Kub* — <https://en.wikipedia.org/wiki/2K12_Kub> (specification block for the 3M9 missile and the system's 1973 combat record) |

⚠ **One source, and that is worth stating plainly.** The aircraft in this pack are backed by
declassified manuals, reference annuals and manufacturer material. This unit has one general
reference. Everything it does not publish is marked [E] below rather than sourced somewhere weaker,
and the [E] rows are the majority of the *system* even though the missile itself is well published.

## The 3M9 missile — the well-published part

| Value | Tag | Source / method |
|---|---|---|
| Length 5,800 mm | P | KUB-WIKI. Drives `MISSILE_LEN` in the builder. |
| Diameter 335 mm | P | KUB-WIKI. `MISSILE_DIA`. |
| Wingspan 1.245 m | P | KUB-WIKI. `MISSILE_SPAN`; the fin span is derived as `(span − diameter) / 2`. |
| Mass 599 kg | P | KUB-WIKI → `weight_lb = 1320`. |
| Warhead 59 kg Frag-HE | P | KUB-WIKI → `blast_radius_ft = 48` by scaling the R-27R1's 42 ft at 39 kg [D], and `damage = 110` [E] as a gameplay value above the R-27R1's 92. |
| Operational range 24 km | P | KUB-WIKI → `max_range_nm = 13.0`. |
| Maximum speed Mach 2.8 | P | KUB-WIKI → `max_speed_kts = 1610` [D] at ~295 m/s local sound speed. |
| Flight altitude max 14,000 m / min 100 m | P | KUB-WIKI. Not directly consumed — the engine has no per-weapon altitude envelope — recorded because it is the only published *minimum* of any kind. |
| Propulsion: integral rocket motor/ramjet booster and sustainer | P | KUB-WIKI. The TYPE is published; the burn split is not, so `motor_burn_time_s = 22` is [E]. |
| Minimum range ~3.7 km | **E** | **Not published.** Estimated from the published propulsion (a boost phase must complete before guidance). It is the largest minimum in the pack and it is what the ZSU-23-4 exists to cover. |
| `max_g = 18`, seeker lobes, countermeasure susceptibilities | E | No published figures. Reasoned against the pack's own R-27R1 and AIM-7M — see the comments in each file, which state the comparison rather than asserting a source. |

## The 1S91 SURN — where the record thins out

| Value | Tag | Source / method |
|---|---|---|
| Two radars on one vehicle: 1S11 acquisition + 1S31 continuous-wave illuminator | P | KUB-WIKI, quoted in `sensors/1s91.toml`. This is why the def uses the engine's search/track lobe pair — two real antennas, not one antenna's two modes. |
| Acquisition range 50 km against an F-4 Phantom | P | KUB-WIKI → `search.max_range_nm = 27.0`. ⚠ The source quotes it against an F-4; the engine quotes ranges against a baseline (rcs 1.0) fighter. Recorded in the file rather than silently converted. |
| Tracking range ~28 km | **E** | **Not published in the cited source.** Bounded, not guessed: it must exceed the missile's published 24 km (or the battery could not support its own shot) and sit well under 50 km (or the 1S11 would be redundant). |
| Omnidirectional coverage, `emitter = true` | P/E | The acquisition radar's role is published; the 180° lobe angles are the engine's convention for an omni sensor [E]. |
| `eccm = 0.40`, PoDs, `lock_hold_s` | E | No published basis. Placed between the pack's aircraft radars and the engine's builtin ground radar, with the reasoning in the file. |
| 1973: Israeli RWRs "did not alert the pilot to the fact that he was being illuminated"; the system "caused the most Israeli losses of any Egyptian anti-aircraft missile" | P | KUB-WIKI. **Deliberately NOT modelled** — the engine's `emitter` is a bool, so this pack cannot express "emits, but period RWRs miss it". The file records the gap instead of faking it. |

## The 2P25 TEL and the mesh

| Value | Tag | Source / method |
|---|---|---|
| Carries 3 missiles | P | KUB-WIKI. This is why `weapons/3m9m.toml` has `rounds = 3` on ONE station — the engine fires only the selected station and never advances it, so three hardpoints would fire once. |
| Crew 3; system weight 19.5 t (TEL) / 20.3 t (SURN, 4 crew) | P | KUB-WIKI. Context for the hull estimate; the engine models neither. |
| Hull length 7.39 m, width 3.18 m, and every panel of its shape | **E** | **Not published in the cited source.** Sized to carry three 5.8 m rounds at the published weight class. The MISSILES are the part of this model worth checking against a photograph; the vehicle under them is an estimate and the builder says so. |
| `max_hp`, signatures, `[ai] skill`/`reaction`, damage pools | E | Gameplay values. Reasoned against the engine's builtin surface units and the pack's own aircraft, with the comparison stated in `entities/sa6_battery.toml`. |

## What this unit deliberately is not

`entities/sa6_battery.toml` is ONE entity carrying both the radar's sensing and the launcher's
three rounds. A real Kub battery is several vehicles. The abstraction is forced by the engine —
ground units have no datalink, and a controller engages strictly off its own contact table — and
the reasoning is recorded in that file's header rather than here, because it is a modelling
decision rather than a provenance one.
