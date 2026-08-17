<!--
SPDX-FileCopyrightText: Contributors to fl-base-pack
SPDX-License-Identifier: CC-BY-4.0
-->

# Provenance — `audio/music/`

Required by the AI content policy's audio exception (decision record 2026-08-17,
fighters-legacy/fighters-legacy#1200): a generated asset ships only if what generated it is recorded
here, and a committed generator can reproduce it.

**Generated 2026-08-17** by [`tools/musicgen/gen_music.py`](../../tools/musicgen/gen_music.py) using
[ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) (code MIT, weights
[ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5), MIT), `pt` backend, bfloat16,
one NVIDIA RTX 5080, torch 2.10.0+cu128. Components: `acestep-v15-turbo` (DiT),
`acestep-5Hz-lm-1.7B` (audio-token LM), `Qwen3-Embedding-0.6B` (text), `vae`.

## Reproducing these files

    python tools/musicgen/gen_music.py --acestep-dir <your ACE-Step 1.5 checkout>

⚠ **The seed is not sufficient on its own.** Two runs at the same seed produced *different music*
until `lm_temperature = 0.0` was also fixed — the 5Hz LM samples independently of the diffusion
seed, and the CLI reports only the seed, so this looks reproducible when it is not. The generator
sets `seeds`, `use_random_seed = false`, `lm_temperature = 0.0` and `thinking = false` together;
with all four, two runs here were byte-identical. Determinism is still bounded by model version,
precision and device — a different GPU may not reproduce these bytes.

Each track is trimmed of the model's leading/trailing silence (4–9 s of it) and fades over the cuts;
four of the six loop, so that silence would otherwise play as dead air on every cycle.

## Output licence

Every `.ogg` here is **CC0-1.0**, annotated in the repository-root `REUSE.toml` rather than taking
the pack default `CC-BY-4.0`. A purely model-generated work carries no copyright the project can
assert.

## Tracks

| Track | State | Seed | Requested | Shipped | Prompt |
|---|---|---|---|---|---|
| `music/menu_theme` | Menu | 101 | 75 s | 69.0 s | "cinematic orchestral, military, restrained, slow build, strings and low brass, atmospheric pad, instrumental" |
| `music/patrol_01` | FlightPatrol | 202 | 100 s | 94.3 s | "ambient orchestral, sparse, wide, quiet tension, sustained strings, soft analogue synth, slow, instrumental" |
| `music/patrol_02` | FlightPatrol | 303 | 100 s | 94.5 s | "ambient electronic, cold, minimal pulse, distant brass, high altitude atmosphere, slow, instrumental" |
| `music/combat_01` | FlightCombat | 404 | 100 s | 93.8 s | "driving orchestral action, urgent low strings ostinato, taiko and snare percussion, brass stabs, tense, instrumental" |
| `music/victory` | MissionSuccess | 505 | 35 s | 28.4 s | "triumphant orchestral brass fanfare, resolving, warm, short, instrumental" |
| `music/debrief` | Debrief | 606 | 60 s | 51.3 s | "reflective orchestral, quiet piano and strings, sombre, slow, instrumental" |

"Requested" is what the model was asked for; "shipped" is after silence trimming.
