# Radio voice lines — the key contract, and how these were made

The engine speaks over the radio through **stable voice keys**. A key resolves to the asset name
`radio/<key>`, which `FolderContentPack` reads from `audio/radio/<key>.ogg`
(`docs/modding/formats.md` → "Radio voice lines"). There is no manifest and nothing to register:
**the filename is the binding**. Ship a file and the line is spoken; ship nothing and it degrades to
the subtitle, which is what the pack did until now.

This pack ships all **42** keys the engine emits today, across five speaking roles.

| Role | Keys | Voice | Dataset licence |
|---|---|---|---|
| Tower | `atc.*` (8) | `en_US-ljspeech-high` | public domain |
| LSO ("Paddles") | `lso.*` (7) | `en_US-bryce-medium` | public domain |
| Crew chief | `crew.*` (7) | `en_US-joe-medium` | CC0 |
| Wingman ("TWO") | `wingman.*` (13) | `en_US-libritts_r-medium`, speaker 92 | CC BY 4.0 (LibriTTS-R) |
| Flight lead | `lead.*` (7) | `en_US-john-medium` | public domain |

## These are generated assets, and that is disclosed on purpose

The lines are synthesised locally with [piper](https://github.com/OHF-Voice/piper1-gpl), an
open-weight TTS engine, by [`tools/voicegen/gen_voice_lines.py`](../../tools/voicegen/gen_voice_lines.py).

That is permitted by a **specific, dated exception**: the project's AI content policy
(fighters-legacy/fighters-legacy#932, ratified 2026-07-27) put voice packs on the human-authored
side of the line, and the decision record of **2026-08-17**
(fighters-legacy/fighters-legacy#1200) superseded it **for audio only**, under four conditions —
open-weight and self-hosted, regenerable from a recorded model and prompt, marked **CC0** rather than
the pack's `CC-BY-4.0`, and disclosed player-facing. This file and the pack README are that
disclosure. Art, story campaigns and mission prose remain human-authored.

Every model is pinned by sha256 in the generator, and `SOURCES.md` in this directory records what
each file was made from.

## Regenerating

```bash
pip install piper-tts                                    # plus ffmpeg on PATH
python tools/voicegen/gen_voice_lines.py                 # rewrite audio/radio/*.ogg
python tools/voicegen/gen_voice_lines.py --check         # committed OGGs still match the synthesis
python tools/voicegen/gen_voice_lines.py --check-assets  # coverage + format only (ffmpeg, no models)
python tools/voicegen/gen_voice_lines.py --verify-speech # transcribe them back and compare the words
```

**Synthesis is deterministic here, deliberately.** Piper's default sampling (`--noise-scale 0.667
--noise-w-scale 0.8`) is stochastic — the same text and model produced three different waveforms of
1.649 s, 1.741 s and 1.753 s on three consecutive runs, so a line that was word-perfect could come
back mangled on the next regeneration. The generator zeroes both noise scales, which makes the output
byte-identical run to run and is what makes "regenerable" mean anything.

## Format

- OGG Vorbis, **mono, 22.05 kHz** (every voice's native rate — nothing is resampled).
- **Recorded DRY.** The engine applies the radio treatment itself: band-limiting, a leading click and
  a squelch tail (`applyRadioTreatment`, engine #925). Filtering here would filter it twice.
- Trimmed, faded and level-matched to a common RMS so no call is twice as loud as the next.
- Under 4 s each; `--check-assets` fails anything over 6 s.

## Spoken text vs subtitle text

The audio says the line; the subtitle names the speaker. `lso.high` renders as
`Paddles: you're HIGH.` on screen and says *"you are high"* — the prefix is shown, not spoken.

Two lines depart further, because the synthesiser could not say them intelligibly otherwise:
`lso.on_glideslope` is spoken as "on glide slope" (as one word it came back as "on the light slope"),
and the `you're` contractions are spoken as "you are" ("you're high" came back as "see you honey").
The subtitle is unaffected — the engine owns that text.

## Verification, and the limits of it

Three checks run over these files, and only one of them can catch the failure that actually matters:

1. `--check-assets` — every key has a file; it decodes; it is mono 22.05 kHz Vorbis, non-silent, and
   under the length ceiling. Cheap, runs in CI.
2. `--check` — re-synthesise and compare duration and level against the committed OGG. Catches a
   file that no longer matches the table that claims to describe it.
3. `--verify-speech` — **transcribe every file and compare it to the words it is supposed to say.**
   Neither of the other two would notice a clip that plays perfectly and says something else, and
   that is not hypothetical: an early take of `lso.good_trap` was a well-formed 3.6 s file that
   transcribed as *"children try and and and and and that"*.

⚠ **The transcriber is an instrument with its own error rate**, and on isolated sub-second clips that
rate is not small. When the five candidate voices were each made to speak all 42 lines, all of them
"failed" the same handful of words — the signature of transcriber bias, not of five independent
synthesis bugs. So a `DISPUTED` line is a question, not a verdict: listen before re-recording. The
current set transcribes 40/42 exactly; the two disagreements are orthography (`shut down` heard as
"shutdown", `R T B` as "rtb") and are aliased in the checker with that reasoning written down.

The voice assignment above was itself chosen by that measurement rather than by ear:
`en_US-norman-medium` was dropped because 9 of 13 wingman lines came back wrong, including "copy"
heard as "the".
