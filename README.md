# fl-base-pack

Community content for [Fighters Legacy](https://github.com/jomkz/fighters-legacy) — a free,
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
| `audio/sfx/` | CC0 OGG sound effects |
| `audio/music/` | Public domain MIDI + FluidSynth render scripts |
| `ai/` | Lua 5.4 AI behaviour scripts |

---

## Installation

**Automatic (recommended):** On first run, the Fighters Legacy engine offers to download and
install fl-base-pack automatically.

**Manual:** Download the latest release archive from the
[Releases](https://github.com/jomkz/fl-base-pack/releases) page and extract it into your
`mods/` directory so the result is `mods/fl-base-pack/manifest.toml`.

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
individual asset carries a `<filename>.license` sidecar declaring CC0-1.0.

The fl-base-pack name and the Fighters Legacy project are not affiliated with any commercial
flight simulation product.
