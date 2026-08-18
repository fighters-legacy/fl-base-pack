# fl-base-pack

Community content for [Fighters Legacy](https://github.com/fighters-legacy/fighters-legacy) — a free,
open-licensed collection of aircraft, terrain, missions, audio, and AI scripts playable with no
proprietary content required.

All assets are licensed under [CC-BY 4.0](LICENSES/CC-BY-4.0.txt). Contributions require a
DCO sign-off.

---

## Asset categories

| Directory | Contents |
|---|---|
| `aircraft/` | glTF 2.0 models + TOML flight data |
| `terrain/` | Heightmaps + surface class definitions |
| `missions/` | YAML mission files |
| `audio/sfx/` | CC0 OGG sound effects (procedurally synthesised, `tools/sfxgen`) |
| `audio/radio/` | Radio voice lines — **synthesised speech**, see below |
| `audio/music/` | Music tracks + `data/playlist.toml` |
| `ai/` | Lua 5.4 AI behaviour scripts |

---

## Installation

**Automatic (recommended):** On first run, the Fighters Legacy engine offers to download and
install fl-base-pack automatically.

**Manual:** Download the latest release archive from the
[Releases](https://github.com/fighters-legacy/fl-base-pack/releases) page and extract it into your
`mods/` directory so the result is `mods/fl-base-pack/manifest.toml`.

New to the game? The engine's
[installation guide](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/user-guide/installation.md)
covers system requirements and first run.

---

## Building audio

Audio sfx (`.ogg`) and terrain assets need no build step — they are used directly by the engine.

Music tracks are stored as MIDI source files alongside a FluidSynth render script:

```bash
# Linux / macOS
bash audio/music/<name>-render.sh

# Windows — use WSL or Git Bash
```

The rendered `.ogg` output is committed alongside the source `.mid` and render script.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for asset submission workflow, naming conventions,
licensing requirements, and review criteria.

---

## License

All assets in this repository are licensed under
[Creative Commons Attribution 4.0 International (CC-BY 4.0)](LICENSES/CC-BY-4.0.txt) unless an
individual asset carries a `<filename>.license` sidecar declaring CC0-1.0, or is covered by a path
rule in [`REUSE.toml`](REUSE.toml) — as the generated voice lines in `audio/radio/` are, at CC0-1.0.

### Generated audio — what it is, and where it stops

**The 42 radio voice lines in `audio/radio/` are synthesised speech, not recorded actors.** They are
produced locally by [piper](https://github.com/OHF-Voice/piper1-gpl), an open-weight text-to-speech
model, from the script and pinned models recorded in
[`audio/radio/SOURCES.md`](audio/radio/SOURCES.md). Anyone can regenerate them byte-for-byte.

Nothing else in this pack is model-generated. Aircraft, missions, flight models, mission prose and
the sound effects are authored — the SFX by a procedural synthesis script, the aircraft by parametric
mesh builders, both human-written. The engine's AI content policy
([decision record 2026-08-17](https://github.com/fighters-legacy/fighters-legacy/blob/main/docs/developer/architecture.md#decision-records))
permits generated **audio** in a shipped pack under four conditions and continues to rule out
generated art, campaigns and story prose. This section exists because one of those four conditions is
that players are told, in the product, rather than in a pull request they will never read.

The fl-base-pack name and the Fighters Legacy project are not affiliated with any commercial
flight simulation product.
