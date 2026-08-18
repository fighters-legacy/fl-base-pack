# Ural-375D truck — data provenance

Every number in `entities/ural375.toml` and `tools/groundlib/src/fl_groundlib/truck.py` traces to a
row in this file.

**Clean-room rule.** Public sources only; nothing from a simulator, game or commercial model, and
the mesh is not traced from a scale plan or 3-view. Tags: **P** published · **D** derived ·
**E** engineering estimate.

## Primary sources

| Key | Document |
|---|---|
| **URAL-WIKI** | Wikipedia, *Ural-375* — <https://en.wikipedia.org/wiki/Ural-375D> (the 375D redirects into the Ural-375 article; its specification block is what is cited here) |

## Vehicle

| Value | Tag | Source / method |
|---|---|---|
| Length 7,350 mm | P | URAL-WIKI → `LENGTH = 7.35` |
| Width 2,960 mm | P | → `WIDTH = 2.96` |
| Height 2,980 mm **with tent** | P | → `HEIGHT = 2.98`; the mesh draws the tilt up, which is the configuration that figure describes. |
| 6×6 drive; 5-speed manual + 2-speed transfer case | P | The wheel layout the builder places: one front axle, a rear bogie of two. |
| Tyres 360–510 mm | P | → `WHEEL_R = 0.61` [D]: a 510 mm rim (radius 0.255 m) plus a ~360 mm section height. |
| Curb weight 8,400 kg; payload 4,800 kg | P | Context; the engine models neither for a unit with no flight model. |
| Engine: 7.0 L ZIL-375Ya V8 petrol, 130 kW (180 PS) | P | Context. Recorded because it is the reason a Ural-375 is a *petrol* vehicle among diesels, which is a real detail if this unit ever grows a fire model beyond the current damage pools. |
| Roles: BM-21 Grad platform, troop carrier, supply carrier; replaced the ZIL-157 as the standard Soviet Army truck in 1979 | P | Why this vehicle rather than another: it is the truck that would actually be parked at the site the pack's other three ground units defend. |
| Cab, bonnet and bed proportions | E | Not published individually. Boxes laid out inside the published overall dimensions. |
| `max_hp = 60`, signatures, `[ai] skill`/`reaction`, damage pools | E | Gameplay values. The softest unit in the pack by a wide margin, and the lowest signatures — reasoned in `entities/ural375.toml` against the pack's two air-defence vehicles. |
