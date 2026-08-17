<!--
SPDX-FileCopyrightText: Contributors to fl-base-pack
SPDX-License-Identifier: CC-BY-4.0
-->

# Provenance — `audio/radio/`

Required by the AI content policy's audio exception (decision record 2026-08-17,
fighters-legacy/fighters-legacy#1200): a generated asset ships only if what generated it is recorded
here, and a committed generator can reproduce it.

**Generated 2026-08-17** by [`tools/voicegen/gen_voice_lines.py`](../../tools/voicegen/gen_voice_lines.py)
using [piper](https://github.com/OHF-Voice/piper1-gpl) 1.7.0 (MIT), CPU, `onnxruntime` 1.28.0.

Sampling is deterministic — `--noise-scale 0` and `--noise-w-scale 0` — so re-running the generator
against the pinned models below reproduces these files. Piper's *default* sampling is stochastic and
would not.

## Models

| Voice | Dataset | Dataset licence | Model sha256 |
|---|---|---|---|
| `en_US-ljspeech-high` | LJ Speech | public domain | `5d4f08ba6a2a48c44592eed3ce56bf85e9de3dd4e20df90541ae68a8310c029a` |
| `en_US-libritts_r-medium`, speaker 92 | LibriTTS-R | CC BY 4.0 | `10bb85e071d616fcf4071f369f1799d0491492ab3c5d552ec19fb548fac13195` |
| `en_US-joe-medium` | OHF-Voice / joe | CC0 | `58afce0321b8d9c46d7cdf9c16500cc55a793b4220212dba6b70fb788b3baf06` |
| `en_US-bryce-medium` | OHF-Voice / bryce | public domain | `dc9caa6c313199ffb5ac698b6e542fa6cba388aeaf2731e25262e33b9810aef1` |
| `en_US-john-medium` | OHF-Voice / john | public domain | `789c6c875726e627ddee93d51d8727859abe9c091c3d141591f4b83c2072e988` |

Models are piper voice releases from
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) (models MIT); the licence column
is the *training dataset's*. LibriTTS-R is CC BY 4.0 — attribution: "LibriTTS-R: A Restored
Multi-Speaker Text-to-Speech Corpus" (Koizumi et al., 2023), derived from LibriTTS (Zen et al.,
2019), itself built from LibriVox public-domain audiobooks.

## Output licence

Every `.ogg` here is **CC0-1.0**, annotated in the repository-root `REUSE.toml` rather than taking
the pack default `CC-BY-4.0`. A purely model-generated work carries no copyright the project can
assert, so asserting one would make the pack's licence metadata false.

## Lines

Spoken text, not subtitle text — the engine owns the subtitle, including the speaker prefix.

| Key | Spoken text | Voice | length_scale | Duration |
|---|---|---|---|---|
| `atc.hold_short` | "hold short. Traffic on the runway." | `en_US-ljspeech-high` | 1.00 | 2.15 s |
| `atc.cleared_takeoff` | "cleared for takeoff" | `en_US-ljspeech-high` | 0.95 | 1.18 s |
| `atc.cleared_to_land` | "cleared to land" | `en_US-ljspeech-high` | 0.95 | 1.10 s |
| `atc.go_around` | "go around, runway occupied" | `en_US-ljspeech-high` | 0.95 | 1.97 s |
| `atc.contact_approach` | "radar contact, continue inbound" | `en_US-ljspeech-high` | 0.95 | 2.42 s |
| `atc.roger` | "roger." | `en_US-ljspeech-high` | 1.00 | 0.59 s |
| `atc.unable` | "unable" | `en_US-ljspeech-high` | 0.95 | 0.59 s |
| `atc.taxi_to_parking` | "clear of the runway, taxi to parking" | `en_US-ljspeech-high` | 0.95 | 2.43 s |
| `lso.on_glideslope` | "on glide slope, on speed" | `en_US-bryce-medium` | 1.00 | 2.15 s |
| `lso.high` | "you are high" | `en_US-bryce-medium` | 1.00 | 0.97 s |
| `lso.low` | "you are low, power" | `en_US-bryce-medium` | 1.00 | 1.50 s |
| `lso.fast` | "you are fast" | `en_US-bryce-medium` | 1.00 | 1.19 s |
| `lso.slow` | "you are slow, power" | `en_US-bryce-medium` | 1.00 | 1.58 s |
| `lso.wave_off` | "wave off! wave off!" | `en_US-bryce-medium` | 1.00 | 1.90 s |
| `lso.good_trap` | "good trap." | `en_US-bryce-medium` | 1.00 | 0.94 s |
| `crew.say_again` | "say again?" | `en_US-joe-medium` | 1.00 | 0.60 s |
| `crew.no_aircraft` | "you don't have an aircraft" | `en_US-joe-medium` | 1.00 | 1.22 s |
| `crew.shut_down_first` | "shut down on the ramp first" | `en_US-joe-medium` | 1.00 | 1.36 s |
| `crew.no_base` | "nobody out here. Get to a base" | `en_US-joe-medium` | 1.00 | 2.22 s |
| `crew.refueled` | "fueled and topped off" | `en_US-joe-medium` | 1.00 | 1.24 s |
| `crew.rearmed` | "rearmed. pins pulled." | `en_US-joe-medium` | 1.20 | 1.35 s |
| `crew.repaired` | "patched up. She will fly." | `en_US-joe-medium` | 1.10 | 1.49 s |
| `wingman.check_in` | "on your wing" | `en_US-libritts_r-medium #92` | 0.95 | 0.60 s |
| `wingman.no_joy` | "no joy" | `en_US-libritts_r-medium #92` | 0.95 | 0.58 s |
| `wingman.no_flight` | "no flight assigned" | `en_US-libritts_r-medium #92` | 0.95 | 0.81 s |
| `wingman.unavailable` | "two is down" | `en_US-libritts_r-medium #92` | 0.95 | 0.66 s |
| `wingman.say_again` | "say again?" | `en_US-libritts_r-medium #92` | 0.95 | 0.57 s |
| `wingman.not_lead` | "you are not the flight lead" | `en_US-libritts_r-medium #92` | 0.95 | 0.93 s |
| `wingman.engaged` | "engaged" | `en_US-libritts_r-medium #92` | 0.90 | 0.62 s |
| `wingman.engaging` | "engaging" | `en_US-libritts_r-medium #92` | 0.90 | 0.59 s |
| `wingman.rejoining` | "rejoining" | `en_US-libritts_r-medium #92` | 0.95 | 0.57 s |
| `wingman.covering` | "covering" | `en_US-libritts_r-medium #92` | 0.95 | 0.48 s |
| `wingman.weapons_hold` | "weapons hold" | `en_US-libritts_r-medium #92` | 0.95 | 0.67 s |
| `wingman.rtb` | "R T B" | `en_US-libritts_r-medium #92` | 0.95 | 0.58 s |
| `wingman.copy` | "copy" | `en_US-libritts_r-medium #92` | 0.95 | 0.44 s |
| `lead.attack_my_target` | "attack my target" | `en_US-john-medium` | 0.90 | 1.15 s |
| `lead.engage_bandits` | "engage bandits" | `en_US-john-medium` | 0.90 | 1.43 s |
| `lead.rejoin` | "rejoin" | `en_US-john-medium` | 1.00 | 0.74 s |
| `lead.cover_me` | "cover me" | `en_US-john-medium` | 0.90 | 0.57 s |
| `lead.hold_fire` | "hold fire" | `en_US-john-medium` | 0.90 | 0.82 s |
| `lead.return_to_base` | "return to base" | `en_US-john-medium` | 0.95 | 1.17 s |
| `lead.say_again` | "say again?" | `en_US-john-medium` | 0.95 | 0.79 s |
