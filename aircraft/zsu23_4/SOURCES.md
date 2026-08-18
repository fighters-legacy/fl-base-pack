# ZSU-23-4 Shilka — data provenance

Every number in `entities/zsu23_4.toml`, `weapons/azp23.toml`, `sensors/rpk2.toml` and
`tools/groundlib/src/fl_groundlib/shilka.py` traces to a row in this file.

**Clean-room rule.** Public sources only. **No value in this unit is taken from any flight
simulator, game, or commercial 3D model**, and the mesh is not traced from a scale plan, a 3-view
or a cutaway. Tags: **P** published · **D** derived by a stated method · **E** engineering estimate.

## Primary sources

| Key | Document |
|---|---|
| **SHILKA-WIKI** | Wikipedia, *ZSU-23-4 Shilka* — <https://en.wikipedia.org/wiki/ZSU-23-4_Shilka> |

This unit is better served than the SA-6 battery: the vehicle's dimensions, its gun and its
ammunition load are all published, and only the radar's tracking envelope is missing.

## Vehicle

| Value | Tag | Source / method |
|---|---|---|
| Length 6.535 m | P | SHILKA-WIKI → `LENGTH` in the builder |
| Width 3.125 m | P | → `WIDTH` |
| Height 2.576 m radar stowed, **3.572 m radar elevated** | P | The mesh draws the radar DEPLOYED, so 3.572 m is the figure a render should be checked against. |
| Mass 19 t (to 21 t on late modifications); crew 4 (commander, driver, gunner, radar operator) | P | Context; the engine models neither. The four-man crew is why `[ai] skill` is not a lone gunner's. |
| Hull/turret panel shape, track run, cradle and mast geometry | E | Not published. Boxes and cylinders at the published overall dimensions. |
| `max_hp = 120`, signatures, damage pools | E | Gameplay values, reasoned against the engine's builtin AAA emplacement (also 120 hp) and the pack's other ground units. |

## AZP-23 "Amur" gun

| Value | Tag | Source / method |
|---|---|---|
| 4 × 23 mm 2A7 autocannons, AZP-23 "Amur", firing 23×152B | P | SHILKA-WIKI. Aggregated into ONE engine weapon def — the engine models a gun as one station with a rate and a magazine. |
| Cyclic 850–1,000 rpm per gun; **3,400–4,000 rpm combined** | P | → `rate_of_fire_rpm = 3400`, the low end, stated as such in the file. |
| Muzzle velocity 970–980 m/s | P | → `max_speed_kts = 1885` [D] from the low end (970 m/s). |
| 2,000 rounds stowed aboard | P | → `[load] rounds = 2000`; `weight_lb = 1984` [D] at ~0.45 kg per linked round. |
| Max horizontal range 7 km · max vertical 5.1 km · **effective vertical 1.5 km** | P | Three published ranges; the engine has one `max_range_nm` field. Authored at ~2,500 m and tagged **[E]**, with the reasoning in `weapons/azp23.toml` rather than attributed to any one of the three. |
| `damage = 12` per round, `blast_radius_ft = 4.0` | E | Gameplay values, set marginally above the pack's GSh-23L (23×115) because this is the heavier 23×152B round. |
| Barrel length 2.01 m | E | Not published in the cited source; sized against the vehicle's published length. |

## RPK-2 "Tobol" (Gun Dish) radar

| Value | Tag | Source / method |
|---|---|---|
| **Ku band** | P | SHILKA-WIKI. (An earlier draft of this def said J band — from memory rather than from the source. It was corrected before the PR, which is the whole reason this table exists.) |
| Detection "up to 20 km" | P | → `search.max_range_nm = 10.8` |
| Tracking range ~8 km | **E** | **Not published.** Bounded: comfortably beyond the gun's own reach, well inside the published 20 km detection range. |
| "Picks up many false returns (ground clutter) under 60 m (200 ft) of altitude" | P | **Cannot be modelled** — the engine has no ground clutter in its detection path, so this vehicle is more dangerous to a low ingress here than the real one was. Recorded in `sensors/rpk2.toml` so the limitation is visible rather than silently absent. |
| `eccm = 0.15`, PoDs, `lock_hold_s` | E | No published basis. Lowest ECCM in the pack; the file states the reasoning. |
