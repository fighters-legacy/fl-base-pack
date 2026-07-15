# Weapon SFX — asset-name contract

The engine's fire path plays positional weapon sound effects from a **fixed preset vocabulary**
(engine #631; `docs/modding/formats.md` → "Weapon SFX presets"). Each preset resolves to a
content-pack OGG **asset name** when the pack ships one, and otherwise to a compiled-in procedural
fallback — so the sandbox has sound with zero content mounted. Ship the asset to override the
fallback.

`FolderContentPack` resolves an audio asset name by prepending `audio/` and appending `.ogg`, so
the asset name `sfx/gunfire` is the file `audio/sfx/gunfire.ogg`. **These names are not free** — the
engine requests exactly these five, so the filenames below are a contract, not a convention.

| Preset (engine) | Asset name | File in this pack | Plays on |
|---|---|---|---|
| `sfx.gunfire` | `sfx/gunfire` | `gunfire.ogg` | every gun round (own gunfire is head-relative) |
| `sfx.launch` | `sfx/launch` | `launch.ogg` | a missile leaving the rails |
| `sfx.release` | `sfx/release` | `release.ogg` | a store dropped (registered; not yet routed to an EffectType) |
| `sfx.impact` | `sfx/impact` | `impact.ogg` | a round connecting |
| `sfx.explosion` | `sfx/explosion` | `explosion.ogg` | a warhead detonation |

## Format

- **OGG Vorbis only** (`.ogg`, magic bytes `OggS`) — the asset validator rejects anything else.
- 44.1 kHz, mono (the engine decodes to PCM and spatialises through a 16-voice steal-oldest pool).
- **Short: < 1 s.** These are one-shots; long clips belong to the streaming/music path
  (`audio/music/`). The ones here run 90 ms (gunfire) to 800 ms (explosion).

## Regenerating

These OGGs are **procedurally synthesised and committed** — like the aircraft `.glb` meshes, they
live in the repo and CI does not rebuild them. The generator is
[`tools/sfxgen/gen_sfx.py`](../../tools/sfxgen/gen_sfx.py) (numpy synthesis → WAV → `ffmpeg`
libvorbis). It needs `numpy` and `ffmpeg`; the engine and CI do not.

    python tools/sfxgen/gen_sfx.py            # rewrite audio/sfx/*.ogg
    python tools/sfxgen/gen_sfx.py --check    # verify the committed OGGs still match the synthesis

To retune a sound, edit its synth function in `gen_sfx.py` and rerun. To replace the procedural clips
with real recordings, drop in OGGs at these exact filenames and record their provenance in
`SOURCES.md` / `REUSE.toml`.
