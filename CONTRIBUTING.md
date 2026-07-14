# Contributing to fl-base-pack

Thank you for contributing! This document covers everything you need to submit assets.

---

## License

All contributions must be **CC-BY 4.0** or more permissive (CC0-1.0).

The project-level `REUSE.toml` covers all assets as CC-BY-4.0 by default — you do not need to
add `SPDX-License-Identifier` comments to individual files, and binary files (`.glb`, `.ogg`,
`.png`, `.mid`) cannot carry in-file headers anyway. The only case requiring a sidecar file is
when an asset is CC0-1.0 (more permissive than the project default): create a
`<filename>.license` file alongside the asset containing:

```
SPDX-License-Identifier: CC0-1.0
SPDX-FileCopyrightText: <Your Name>
```

**DCO sign-off is required on every commit.** Add `-s` to your commit command:

```bash
git commit -s -m "add(aircraft): F/A-18C Hornet flight model"
```

The DCO GitHub App checks every PR and blocks merges if any commit lacks a `Signed-off-by:`
trailer.

---

## Filename conventions (cross-platform)

Inconsistent casing causes silent failures across operating systems — Linux (ext4) is
case-sensitive while Windows and macOS are not.

- **Lowercase with hyphens only** — `fa-18c`, not `FA18C` or `fa_18C`
- **No spaces** in any filename
- **No Windows reserved names** as the file stem: `con`, `nul`, `prn`, `aux`, `com1`–`com9`,
  `lpt1`–`lpt9` — these cause hangs or errors on Windows regardless of extension
- **Forward slashes only** in all asset reference paths inside TOML and YAML files —
  backslashes break Linux and macOS

---

## Asset categories

### `aircraft/<name>/`

One directory per aircraft. Directory name must match the asset-name stem, and **asset names
include the subdirectory** — the F-5E's mesh is `f5e/f5e`, not `f5e` (get this wrong and the engine
silently falls back to a builtin placeholder). A complete aircraft is a set of files, not one:

```
aircraft/
  f5e/
    f5e.glb            ← base model; root node `f5e`, damage-state node `f5e_b` (same file)
    f5e_lod0.glb       ← ~50% triangle budget   ┐ LODs are SEPARATE FILES, not nodes.
    f5e_lod1.glb       ← ~20%                    │ (An earlier version of this doc said nodes;
    f5e_lod2.glb       ← ~5%                     ┘  it was wrong. The renderer loads them by file.)
    f5e_shadow.glb     ← convex hull, no materials
    f5e_cockpit.glb    ← contains a node named `camera_anchor`
    f5e.toml           ← flight model data       (see aircraft/<name>/*.expect.toml for the CI gate)
    f5e_build.py       ← the generator (see "Mesh provenance" below)
    derive.py          ← generates the aero tables
    SOURCES.md         ← required provenance manifest (docs/legal/aircraft-likeness.md)
```

The entity definition, sensors and weapons live in the top-level `entities/`, `sensors/` and
`weapons/` directories (namespaced def-ids, e.g. `fl-base:f5e`), not under `aircraft/`.

**Model requirements** (full spec:
[3d-models.md](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/modding/3d-models.md)):
- glTF 2.0 binary (`.glb`). No embedded image data — textures are external `.ktx2` URIs.
- Node/material names lowercase with underscores; winding CCW from outside.
- Damage-state node `<name>_b` in the same file as its base node.
- **One material, one primitive, for now.** The engine loads only `meshes[0].primitives[0]` until
  its node-aware loader lands
  ([fighters-legacy#839](https://github.com/fighters-legacy/fighters-legacy/issues/839)); a
  multi-material split would push geometry into primitives the engine drops. Multiple parts and
  material slots come with that engine work, not before it.
- Run [`validate-mesh`] locally, and preview with `tools/gltf-inspect/` (a stopgap browser viewer)
  — but note it is **not** the game renderer.

**Flight data:** Follow the
[flight model schema](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/modding/flight-model.md)
exactly. The `flight-model-validate` CI job checks every field and range, and `fm-trim --expect`
gates the aircraft against a performance table you author in `<name>.expect.toml`.

**Mesh provenance — every aircraft is `generated` or `authored`:**

- **`generated`** (the F-5E): the source of truth is the build script (`<name>_build.py`), and the
  committed `.glb` files must regenerate **byte-for-byte** from it — that reproducibility is the
  regression check. Never hand-edit a generated `.glb`; change the script and re-run it. No `.blend`
  is committed (Blender projects are not byte-stable).
- **`authored`**: the source of truth is a committed `src/<name>.blend` plus the exported `.glb`
  set. A PR that touches an authored `.glb` must also touch its `.blend`. The byte-identical regen
  check does not apply (Blender export is not byte-stable across versions); `validate-mesh` is the
  gate instead.

An aircraft flips from generated to authored the first time an artist polishes it in Blender: run
the generator with `--blend out.blend` (or import the shipped `.glb`), polish, commit the `.blend`
under `src/`, re-export, and record the flip in `SOURCES.md`. The build script stays in the tree as
the geometry's provenance. Shared generator helpers live in `tools/meshlib/` (`fl_meshlib`).

### `terrain/<id>/`

Terrain uses a streaming chunk format with three LOD levels. Each chunk is a 513×513 16-bit greyscale PNG covering 15,360 m. Chunks are organized by terrain ID, LOD level, and grid coordinates:

```
terrain/
  world/
    lod0/
      chunk_0000_0000.png   ← LOD 0 (513×513, full resolution, ~46 km ring)
      chunk_0001_0000.png
      ...
    lod1/
      chunk_0000_0000.png   ← LOD 1 (257×257, ~77 km ring)
      ...
    lod2/
      chunk_0000_0000.png   ← LOD 2 (129×129, ~107 km ring)
      ...
```

- **Chunk naming**: `chunk_<x>_<y>.png` with 4-digit zero-padded coordinates
- **Terrain ID**: `"world"` is the canonical global terrain; theater packs override individual chunks at higher mod priority via `IContentPack::resolveTerrainChunk()`
- **Surface class map**: companion JSON at `terrain/<id>/surface.json` — maps pixel brightness ranges to surface class IDs (grass, water, urban, etc.) with associated `*.ktx2` textures

See [terrain format documentation](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/modding/formats.md#terrain) for full chunk format spec and the `tools/gen_terrain_chunks.py` tool for converting GeoTIFF/DEM sources.

### `missions/<name>.yaml`

YAML mission files, gated in CI by `validate-mission`. See
[missions.md](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/modding/missions.md).

### `audio/sfx/<name>.ogg`

CC0 OGG sound effects. Recommended sources: [freesound.org](https://freesound.org) (filter by
CC0). Format: OGG Vorbis, 44.1 kHz or 48 kHz, mono or stereo.

### `audio/music/<name>.mid` + `<name>-render.sh`

Public domain MIDI source files alongside a FluidSynth render script that produces the final
`.ogg`. Windows contributors: use WSL or Git Bash to run the script, or submit the `.mid` alone
and request a maintainer render in your PR description.

### `ai/<name>.lua`

Lua 5.4 AI behaviour scripts. The engine AI API is documented in
[ai.md](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/modding/ai.md). Use
`detected_contacts()` (honest sensing) — a script never reads ground truth.

---

## Review criteria

- CI must pass. Required checks are `license-check`, `asset-naming`, `DCO`, `mission-validate`, and
  `mesh-validate`; `flight-model-validate` runs and will become required once an engine release
  ships the post-#823 validator. `meshlib` runs when you touch `tools/meshlib/` or a build script.
- Models must be original work or sourced from a verifiably compatible open licence — include a
  source link in your PR description.
- No copyrighted IP: meshes, markings, or liveries derived from proprietary references without
  documented clearance will be rejected. Reference imagery must be PD or CC0 and is listed in the
  aircraft's `SOURCES.md`; **scale plans and cutaway drawings are copyrighted even when labelled
  "for reference"** — do not use them.

## What the engine renders today (so you are not surprised)

The engine is mid-build. An aircraft that validates and loads will still, right now:

- render in **flat grey** — there is no mesh-texture pipeline yet
  ([#833](https://github.com/fighters-legacy/fighters-legacy/issues/833)); your `.ktx2` references
  are correct and dormant.
- show only its **first primitive** — keep to one material (above).
- **not move** — landing gear, flaps and control surfaces are not animated yet
  ([#837](https://github.com/fighters-legacy/fighters-legacy/issues/837)).

None of these are defects in your asset; author to the documented conventions and the aircraft
lights up as the engine catches up. Preview geometry with `tools/gltf-inspect/`; confirm it actually
loads by booting `fl-server` against a real `mods/` tree (a green validator is not proof it renders).

---

## PR workflow

1. Fork the repository
2. Create a branch: `git checkout -b add/fa-18c`
3. Add your assets following the conventions above
4. Commit with sign-off: `git commit -s -m "add(aircraft): F/A-18C Hornet"`
5. Open a pull request to `main`

---

## Commit format

```
<type>[(<scope>)]: <description>
```

| Type | When to use |
|---|---|
| `add` | New asset |
| `update` | Improvement to an existing asset |
| `fix` | Correction to incorrect data |
| `remove` | Remove an asset |

Examples:
```
add(aircraft): F/A-18C Hornet glTF model and flight data
update(aircraft): tune fa-18c drag polar against NASA TM-86694
fix(missions): correct waypoint coordinates in red-flag-01
add(audio): afterburner ignition sfx (CC0)
```
