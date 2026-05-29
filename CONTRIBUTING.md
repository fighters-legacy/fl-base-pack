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

One directory per aircraft. Directory name must match the asset name stem.

```
aircraft/
  fa-18c/
    fa-18c.glb       ← glTF 2.0 model
    fa-18c.toml      ← flight model data
```

**Model requirements:**
- Format: glTF 2.0 (`.glb` preferred for self-contained files)
- Required node hierarchy and material slots per the engine mesh specification
- Damage-state mesh: `<name>_b` node (e.g. `fa-18c_b`)
- LOD variants: `<name>_lod1`, `<name>_lod2` nodes

**Flight data:** Follow the
[flight model schema](https://github.com/jomkz/fighters-legacy/blob/main/docs/modding/flight-model.md)
exactly. The TOML flight model validator (CI job `flight-model-validate`) will check all fields
and ranges once fighters-legacy#109 ships.

### `terrain/<name>/`

```
terrain/
  nevada/
    nevada.png       ← heightmap (greyscale PNG, power-of-two resolution)
    nevada.json      ← surface class definitions (streaming chunk format)
```

### `missions/<name>.yaml`

YAML mission files. See the mission schema documentation in fighters-legacy
`docs/modding/missions.md` (forthcoming with fighters-legacy#34).

### `audio/sfx/<name>.ogg`

CC0 OGG sound effects. Recommended sources: [freesound.org](https://freesound.org) (filter by
CC0). Format: OGG Vorbis, 44.1 kHz or 48 kHz, mono or stereo.

### `audio/music/<name>.mid` + `<name>-render.sh`

Public domain MIDI source files alongside a FluidSynth render script that produces the final
`.ogg`. Windows contributors: use WSL or Git Bash to run the script, or submit the `.mid` alone
and request a maintainer render in your PR description.

### `ai/<name>.lua`

Lua 5.4 AI behaviour scripts. The engine AI API is documented in fighters-legacy
`docs/modding/ai.md` (forthcoming with fighters-legacy#33).

---

## Review criteria

- CI must pass: `license-check`, `asset-naming`, `DCO`
- Models must be original work or sourced from a verifiably compatible open licence — include a
  source link in your PR description
- No copyrighted IP: meshes, markings, or liveries derived from proprietary references without
  documented clearance will be rejected

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
