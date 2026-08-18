# Forward fuel depot — data provenance

**There is nothing to cite, and that is the entry.**

Every other model in this pack is a specific piece of equipment whose dimensions are published
somewhere, and each has a SOURCES.md that traces its numbers to a document. A field fuel depot has
no type designation, no manufacturer, no specification sheet and no published dimensions: it is
whatever tankage was put up at the time. Writing a table of citations for it would be theatre.

So this file records the DESIGN INTENT instead, which is the thing a reviewer can actually check,
and every number in `entities/fuel_depot.toml` and
`tools/groundlib/src/fl_groundlib/depot.py` is **[E]** without exception.

## What was designed for, and why

| Decision | Reasoning |
|---|---|
| Three cylindrical tanks, ~4.5 m radius × 7 m tall, on a concrete pad | A recognisable fuel-storage silhouette from any heading and from altitude. A cluster of huts would not be identifiable from a strike aircraft's flight path, and this entity exists to be identified and hit. |
| ~12.5 m between tank centres (roughly two diameters of clear space) | Fire separation is real practice for bulk fuel storage, and it is what makes the site sprawl rather than clump — which is what makes it legible from above. |
| No revetments, no berms, no gun pits | What defends this site is parked next to it as separate entities (`sa6_battery`, `zsu23_4`), so a mission author can choose to leave it undefended. A target that looks defended when it is not is a lie told by geometry. |
| `max_hp = 400` | Sized against the pack's own Mk 82 (200 damage): a two-bomb target on direct hits, more with the blast falloff a real delivery gets. Half the engine builtin static target's 800, because thin steel tanks full of fuel are not a hardened bunker. |
| Signatures rcs 12 / ir 2 / visual 9 | The easiest thing in the pack to find by every channel. The problem this target poses is getting to it, not seeing it. |
| One damage subsystem pool (`fuel`) | A depot has no avionics and no controls. Inventing pools so the table looks symmetrical would be modelling furniture. |

## The clean-room rule still applies

Nothing here is traced from, derived from, or "cleaned up" out of any simulator, game or commercial
3D model. It is boxes and cylinders from `fl_meshlib.prims`, sized as above.
