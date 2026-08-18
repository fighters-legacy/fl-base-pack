# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Radio voice-line generator for fl-base-pack (pack issue #13).

Everyone who talks on the radio in this engine does so through a stable VOICE KEY. A key resolves to
the asset name `radio/<key>`, which `FolderContentPack` reads from `<pack>/audio/radio/<key>.ogg`
(docs/modding/formats.md, "Radio voice lines"). Ship the file and the line is spoken; ship nothing
and it degrades to the subtitle. There is no manifest and no registration -- the FILENAME IS THE
BINDING, which is why the key table below is a contract rather than a convention.

This script synthesises the pack's 42 lines with piper (local, open-weight TTS), one voice per
speaking role so the tower, the LSO, the crew chief, your wingman and your flight lead are
distinguishable on the same radio net.

    role      key prefix    voice                       dataset licence
    tower     atc.*         en_US-ljspeech-high         public domain
    LSO       lso.*         en_US-bryce-medium          public domain
    crew      crew.*        en_US-joe-medium            CC0
    wingman   wingman.*     en_US-libritts_r-medium #92 CC BY 4.0 (LibriTTS-R)
    lead      lead.*        en_US-john-medium           public domain

Those five were chosen by measurement, not by ear-picking: every candidate voice was made to speak
every line and the result was transcribed back (see "Verification" in audio/radio/README.md).
en_US-norman-medium was dropped that way -- it renders "copy" as something a transcriber hears as
"the", and 9 of the 13 wingman lines came back wrong.

⚠ RECORD DRY. The engine applies the radio treatment itself -- band-limiting, a leading click and a
squelch tail (engine #925, `applyRadioTreatment`) -- so anything filtered here gets filtered twice.

⚠ These lines are GENERATED assets under the 2026-08-17 decision record
(fighters-legacy/fighters-legacy#1200), which permits generated audio in a shipped pack only if it is
open-weight and self-hosted, regenerable from a recorded model/prompt/seed, marked CC0 rather than
the pack's CC-BY-4.0, and disclosed player-facing. This script is the "regenerable" half; the model
pins below are the "recorded" half; `audio/radio/README.md` and the pack README are the other two.

Spoken text is the engine's own line with the speaker prefix stripped: the subtitle renders
"Paddles: you're HIGH." while the audio says "you're HIGH" -- the speaker is shown, not spoken.

Prerequisites: `pip install piper-tts` and ffmpeg on PATH. Neither the engine nor pack CI needs them;
the OGGs are committed artifacts, like the aircraft meshes and the weapon SFX.

    python tools/voicegen/gen_voice_lines.py                 # write audio/radio/*.ogg (downloads voices once)
    python tools/voicegen/gen_voice_lines.py --check         # re-synthesise and compare (needs piper + voices)
    python tools/voicegen/gen_voice_lines.py --check-assets  # format/coverage check only (needs ffmpeg)
    python tools/voicegen/gen_voice_lines.py --verify-speech # transcribe them back and compare the words
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

SR = 22050  # every voice below is 22.05 kHz mono; the engine resamples nothing and needs no fixed rate
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "audio" / "radio"
DEFAULT_VOICE_DIR = Path.home() / ".cache" / "fl-base-pack" / "piper-voices"

PIPER_VOICES_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"

# The exact model artifacts these OGGs were generated from. Pinned by sha256 because "regenerable"
# means regenerable from the SAME model: piper voice files are re-uploaded in place, and a silently
# newer checkpoint would re-voice the whole pack on the next regen with no diff to explain it.
VOICES = {
    "ljspeech-high": dict(
        path="ljspeech/high/en_US-ljspeech-high.onnx",
        sha256="5d4f08ba6a2a48c44592eed3ce56bf85e9de3dd4e20df90541ae68a8310c029a",
        dataset="LJ Speech", licence="public domain",
    ),
    "libritts_r-92": dict(
        path="libritts_r/medium/en_US-libritts_r-medium.onnx",
        sha256="10bb85e071d616fcf4071f369f1799d0491492ab3c5d552ec19fb548fac13195",
        dataset="LibriTTS-R", licence="CC BY 4.0", speaker=92,
    ),
    "joe-medium": dict(
        path="joe/medium/en_US-joe-medium.onnx",
        sha256="58afce0321b8d9c46d7cdf9c16500cc55a793b4220212dba6b70fb788b3baf06",
        dataset="OHF-Voice / joe", licence="CC0",
    ),
    "bryce-medium": dict(
        path="bryce/medium/en_US-bryce-medium.onnx",
        sha256="dc9caa6c313199ffb5ac698b6e542fa6cba388aeaf2731e25262e33b9810aef1",
        dataset="OHF-Voice / bryce", licence="public domain",
    ),
    "john-medium": dict(
        path="john/medium/en_US-john-medium.onnx",
        sha256="789c6c875726e627ddee93d51d8727859abe9c091c3d141591f4b83c2072e988",
        dataset="OHF-Voice / john", licence="public domain",
    ),
}

# ── the key table ────────────────────────────────────────────────────────────────────────────────
#
# key -> (spoken text, voice, length_scale)
#
# Every key here is emitted by the engine TODAY, verified against:
#   engine/atc/AtcTypes.cpp        atcPhraseVoiceKey / phraseText          (atc.*)
#   engine/atc/CrewPhrases.cpp     lsoPhraseVoiceKey / lsoPhraseText       (lso.*)
#                                  crewChiefPhraseVoiceKey / ...Text       (crew.*)
#   game/fighters-legacy/WingmanMenu.cpp  wingmanVoiceKey / brevityFor      (wingman.*, lead.*)
#
# ⚠ A key is a PUBLISHED NAME: the engine adds keys rather than renaming them, so re-check these
# four sources when regenerating -- the atc.* set has grown once already (atc.taxi_to_parking,
# engine #1155). `--check-assets` reports coverage against this table, not against the engine.
#
# length_scale is piper's phoneme-duration multiplier: < 1.0 speeds delivery up. Radio brevity is
# clipped, and an urgent call is clipped harder -- a wave-off drawled at conversational pace is the
# wrong sound for the one call that means "you are about to hit the ramp".
LINES: dict[str, tuple[str, str, float]] = {
    # ── tower (engine/atc/AtcTypes.cpp) ──
    "atc.hold_short":        ("hold short. Traffic on the runway.", "ljspeech-high", 1.00),
    "atc.cleared_takeoff":   ("cleared for takeoff", "ljspeech-high", 0.95),
    "atc.cleared_to_land":   ("cleared to land", "ljspeech-high", 0.95),
    "atc.go_around":         ("go around, runway occupied", "ljspeech-high", 0.95),
    "atc.contact_approach":  ("radar contact, continue inbound", "ljspeech-high", 0.95),
    "atc.roger":             ("roger.", "ljspeech-high", 1.00),
    "atc.unable":            ("unable", "ljspeech-high", 0.95),
    "atc.taxi_to_parking":   ("clear of the runway, taxi to parking", "ljspeech-high", 0.95),
    # ── LSO / "Paddles" (engine/atc/CrewPhrases.cpp) ──
    # Spoken text departs from the subtitle where the synth needs it to: "glide slope" as two words
    # and "you are" over "you're" are the two that would not survive otherwise (verified by
    # transcribing the output back -- "on the light slope" and "see you honey" were the failures).
    "lso.on_glideslope":     ("on glide slope, on speed", "bryce-medium", 1.00),
    "lso.high":              ("you are high", "bryce-medium", 1.00),
    "lso.low":               ("you are low, power", "bryce-medium", 1.00),
    "lso.fast":              ("you are fast", "bryce-medium", 1.00),
    "lso.slow":              ("you are slow, power", "bryce-medium", 1.00),
    "lso.wave_off":          ("wave off! wave off!", "bryce-medium", 1.00),
    "lso.good_trap":         ("good trap.", "bryce-medium", 1.00),
    # ── crew chief (engine/atc/CrewPhrases.cpp) ──
    "crew.say_again":        ("say again?", "joe-medium", 1.0),
    "crew.no_aircraft":      ("you don't have an aircraft", "joe-medium", 1.0),
    "crew.shut_down_first":  ("shut down on the ramp first", "joe-medium", 1.0),
    "crew.no_base":          ("nobody out here. Get to a base", "joe-medium", 1.0),
    "crew.refueled":         ("fueled and topped off", "joe-medium", 1.0),
    "crew.rearmed":          ("rearmed. pins pulled.", "joe-medium", 1.20),
    "crew.repaired":         ("patched up. She will fly.", "joe-medium", 1.10),
    # ── wingman, "TWO" (game/fighters-legacy/WingmanMenu.cpp) ──
    "wingman.check_in":      ("on your wing", "libritts_r-92", 0.95),
    "wingman.no_joy":        ("no joy", "libritts_r-92", 0.95),
    "wingman.no_flight":     ("no flight assigned", "libritts_r-92", 0.95),
    "wingman.unavailable":   ("two is down", "libritts_r-92", 0.95),
    "wingman.say_again":     ("say again?", "libritts_r-92", 0.95),
    "wingman.not_lead":      ("you are not the flight lead", "libritts_r-92", 0.95),
    "wingman.engaged":       ("engaged", "libritts_r-92", 0.90),
    "wingman.engaging":      ("engaging", "libritts_r-92", 0.90),
    "wingman.rejoining":     ("rejoining", "libritts_r-92", 0.95),
    "wingman.covering":      ("covering", "libritts_r-92", 0.95),
    "wingman.weapons_hold":  ("weapons hold", "libritts_r-92", 0.95),
    "wingman.rtb":           ("R T B", "libritts_r-92", 0.95),
    "wingman.copy":          ("copy", "libritts_r-92", 0.95),
    # ── flight lead, orders relayed TO you (game/fighters-legacy/WingmanMenu.cpp) ──
    "lead.attack_my_target": ("attack my target", "john-medium", 0.90),
    "lead.engage_bandits":   ("engage bandits", "john-medium", 0.90),
    "lead.rejoin":           ("rejoin", "john-medium", 1.00),
    "lead.cover_me":         ("cover me", "john-medium", 0.90),
    "lead.hold_fire":        ("hold fire", "john-medium", 0.90),
    "lead.return_to_base":   ("return to base", "john-medium", 0.95),
    "lead.say_again":        ("say again?", "john-medium", 0.95),
}

# Post-synthesis conditioning. All three exist because the engine, not the pack, owns the radio
# sound: it prepends a click and appends a squelch tail, so silence the synth left at the head shows
# up as dead air BETWEEN the click and the words.
# Trim threshold is relative to the clip's own PEAK, not to full scale. An absolute gate cannot be
# right for both a shouted wave-off and a murmured "roger": at -45 dBFS it left a breath tail on the
# loud lines (lso.good_trap decoded 3.6 s for two words) while still risking the quiet ones.
TRIM_BELOW_PEAK_DB = -45.0
TRIM_PAD_S = 0.040       # run-up kept before the first loud sample. 10 ms ate the "g" of "go around",
                         # which came back from the transcriber as "though a round"; at 25 ms
                         # "hold short" still decoded as "old short". A consonant starts far quieter
                         # than the vowel behind it, so the gate always opens mid-consonant.
EDGE_FADE_S = 0.008      # fade in/out over the trim points so a hard cut cannot click
TARGET_RMS_DBFS = -20.0  # level every line lands on, so no call is twice as loud as the next
PEAK_CEILING = 0.89      # ~-1 dBFS; the radio filter has headroom to add back

# VITS sampling is STOCHASTIC at piper's defaults (noise-scale 0.667 / noise-w 0.8): the same text
# and model gave three different waveforms on three runs, 1.649 s / 1.741 s / 1.753 s, and a line
# that came back word-perfect from the transcriber could come back mangled on the next regen. Zeroing
# both noise scales makes synthesis byte-identical run to run, which is what "regenerable from a
# recorded model and prompt" has to mean to be worth writing down. It costs a little prosodic
# variation; radio brevity is clipped and flat anyway.
NOISE_SCALE = 0.0
NOISE_W_SCALE = 0.0

CHECK_DUR_TOL_S = 0.12   # a Vorbis clip decodes slightly long (block padding); this absorbs it
CHECK_RMS_RATIO = 0.15   # decoded RMS within 15% of a fresh synthesis
MAX_LINE_S = 6.0         # a radio call longer than this is a bug, not a line
SPEECH_MODEL = "medium.en"  # small.en mis-hears these clips often enough to be useless as a gate


def _voice_file(voice: str, voice_dir: Path) -> Path:
    """Return the local .onnx for `voice`, downloading + sha256-verifying it once."""
    spec = VOICES[voice]
    dest = voice_dir / f"en_US-{voice}.onnx"
    if not dest.exists():
        voice_dir.mkdir(parents=True, exist_ok=True)
        url = f"{PIPER_VOICES_BASE}/{spec['path']}"
        print(f"  fetching {voice} ...", file=sys.stderr)
        urllib.request.urlretrieve(url, dest)
        urllib.request.urlretrieve(url + ".json", dest.with_suffix(".onnx.json"))
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    if digest != spec["sha256"]:
        raise SystemExit(
            f"error: {dest.name} sha256 {digest}\n"
            f"       expected {spec['sha256']}\n"
            "       The pinned voice model changed upstream. Regenerating against a different\n"
            "       checkpoint re-voices the pack, so update the pin deliberately (and re-record\n"
            "       every line it affects) rather than as a side effect."
        )
    return dest


def _synthesise(text: str, voice_path: Path, length_scale: float, speaker: int | None = None) -> np.ndarray:
    """Run piper -> float PCM in [-1, 1] at SR, DETERMINISTICALLY (see NOISE_SCALE)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        cmd = [sys.executable, "-m", "piper", "-m", str(voice_path), "-f", str(wav_path),
               "--length-scale", str(length_scale),
               "--noise-scale", str(NOISE_SCALE), "--noise-w-scale", str(NOISE_W_SCALE)]
        if speaker is not None:
            cmd += ["-s", str(speaker)]  # libritts_r is multi-speaker: the id IS part of the voice
        subprocess.run(cmd, input=text.encode(), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(str(wav_path), "rb") as w:
            if w.getframerate() != SR or w.getnchannels() != 1:
                raise SystemExit(f"error: piper returned {w.getframerate()} Hz / {w.getnchannels()} ch, expected {SR}/1")
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    finally:
        wav_path.unlink(missing_ok=True)
    return pcm.astype(np.float64) / 32768.0


def _condition(x: np.ndarray) -> np.ndarray:
    """Trim head/tail silence, fade the cuts, normalise to a common RMS, cap the peak."""
    if x.size == 0:
        return x
    peak = float(np.max(np.abs(x)))
    thresh = peak * 10.0 ** (TRIM_BELOW_PEAK_DB / 20.0)
    loud = np.flatnonzero(np.abs(x) > thresh)
    if loud.size:
        pad = int(TRIM_PAD_S * SR)
        x = x[max(0, loud[0] - pad): min(x.size, loud[-1] + pad)]

    n_fade = min(int(EDGE_FADE_S * SR), x.size // 2)
    if n_fade > 0:
        ramp = np.linspace(0.0, 1.0, n_fade)
        x[:n_fade] *= ramp
        x[-n_fade:] *= ramp[::-1]

    rms = float(np.sqrt(np.mean(x ** 2)))
    if rms > 0:
        x = x * (10.0 ** (TARGET_RMS_DBFS / 20.0) / rms)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak > PEAK_CEILING:
        x = x * (PEAK_CEILING / peak)
    return x


def _write_ogg(samples: np.ndarray, dest: Path) -> None:
    """float PCM -> WAV (stdlib) -> OGG Vorbis (ffmpeg libvorbis, quality 4, mono)."""
    pcm16 = (np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)
    try:
        with wave.open(str(wav_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm16.tobytes())
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
             "-c:a", "libvorbis", "-q:a", "4", "-ac", "1", "-ar", str(SR), str(dest)],
            check=True,
        )
    finally:
        wav_path.unlink(missing_ok=True)


def _decode_pcm(path: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,channels,sample_rate",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return json.loads(out)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


def cmd_generate(voice_dir: Path) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {v: _voice_file(v, voice_dir) for v in VOICES}
    for key, (text, voice, ls) in LINES.items():
        pcm = _condition(_synthesise(text, paths[voice], ls, VOICES[voice].get("speaker")))
        dest = OUT_DIR / f"{key}.ogg"
        _write_ogg(pcm, dest)
        print(f"  {key:24s} {voice:15s} {pcm.size / SR:4.2f}s  \"{text}\"")
    print(f"\n  {len(LINES)} lines -> {OUT_DIR.relative_to(REPO_ROOT)}/")
    return 0


def cmd_check(voice_dir: Path) -> int:
    """Re-synthesise every line and compare the committed OGG in duration + level."""
    paths = {v: _voice_file(v, voice_dir) for v in VOICES}
    drift = 0
    for key, (text, voice, ls) in LINES.items():
        committed = OUT_DIR / f"{key}.ogg"
        if not committed.exists():
            print(f"MISSING: {key}.ogg is not committed", file=sys.stderr)
            drift = 1
            continue
        src = _condition(_synthesise(text, paths[voice], ls, VOICES[voice].get("speaker")))
        dec = _decode_pcm(committed)
        d_dur = abs(dec.size - src.size) / SR
        src_rms, dec_rms = _rms(src), _rms(dec)
        ratio = abs(dec_rms - src_rms) / src_rms if src_rms else 1.0
        ok = d_dur <= CHECK_DUR_TOL_S and ratio <= CHECK_RMS_RATIO
        status = "ok" if ok else "DRIFT"
        print(f"  {key:24s} d_dur={d_dur*1000:4.0f}ms rms {src_rms:.3f}->{dec_rms:.3f} ({ratio*100:3.0f}%)  {status}",
              file=sys.stderr if not ok else sys.stdout)
        drift |= 0 if ok else 1
    return drift


# Transcriber disagreements that are NOT synthesis defects, calibrated by observing them on lines
# every other check agrees are correct: whisper writes "shut down" as one word and spells "R T B"
# unspaced. Nothing else is aliased -- an alias list is how a speech check quietly stops checking.
SPEECH_ALIASES = [("shut down", "shutdown"), ("r t b", "rtb")]


def cmd_verify_speech() -> int:
    """Transcribe every committed OGG and compare it to the text it is supposed to say.

    This is the only check here that can catch the failure that matters -- a line that plays cleanly
    and says the WRONG WORDS. Nothing else in this repo, and nothing in the engine, would notice: a
    mangled clip is still a well-formed mono Vorbis file of plausible length.

    ⚠ THE TRANSCRIBER IS AN INSTRUMENT WITH ITS OWN ERROR RATE, and on isolated sub-second clips with
    no surrounding context that rate is not small. Treat a mismatch as a question, not a verdict:
    when this was first run against six candidate voices, all six "failed" the same words, which is
    the signature of transcriber bias rather than six independent synthesis bugs. The instrument
    earns its keep on the gross failures, which are unambiguous -- an early take of `lso.good_trap`
    came back as "children try and and and and and that".

    Needs `pip install faster-whisper` (~1.5 GB model download on first run); nothing else does.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("error: --verify-speech needs faster-whisper (pip install faster-whisper)", file=sys.stderr)
        return 2

    def norm(s: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("’", "'")).split())

    def equivalent(want: str, heard: str) -> bool:
        if want == heard:
            return True
        return any(want.replace(a, b) == heard for a, b in SPEECH_ALIASES)

    model = WhisperModel(SPEECH_MODEL, device="cpu", compute_type="int8")
    bad = 0
    for key, (text, _voice, _ls) in LINES.items():
        path = OUT_DIR / f"{key}.ogg"
        if not path.exists():
            print(f"MISSING: {key}.ogg", file=sys.stderr)
            bad += 1
            continue
        segments, _info = model.transcribe(str(path), language="en", beam_size=5)
        heard = norm(" ".join(s.text.strip() for s in segments))
        want = norm(text)
        if equivalent(want, heard):
            print(f"  ok       {key:24s} {heard!r}")
        else:
            bad += 1
            print(f"  DISPUTED {key:24s} want={want!r} heard={heard!r}", file=sys.stderr)
    print(f"\n  {len(LINES) - bad}/{len(LINES)} lines transcribe back to their own text.")
    if bad:
        print("  A disputed line is not automatically wrong -- listen to it before re-recording.", file=sys.stderr)
    return 1 if bad else 0


def cmd_check_assets() -> int:
    """Coverage + format check with no model: every key has a committed, decodable, non-silent,
    correctly-shaped OGG, and nothing extra is lying around in audio/radio/."""
    fail = 0
    for key in LINES:
        path = OUT_DIR / f"{key}.ogg"
        if not path.exists():
            print(f"ERROR: {key}: no {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            fail = 1
            continue
        info = _probe(path)
        stream = info["streams"][0]
        dur = float(info["format"]["duration"])
        problems = []
        if stream["codec_name"] != "vorbis":
            problems.append(f"codec {stream['codec_name']}, expected vorbis")
        if int(stream["channels"]) != 1:
            problems.append(f"{stream['channels']} channels, expected mono")
        if int(stream["sample_rate"]) != SR:
            problems.append(f"{stream['sample_rate']} Hz, expected {SR}")
        if dur > MAX_LINE_S:
            problems.append(f"{dur:.1f}s, longer than the {MAX_LINE_S}s ceiling")
        if _rms(_decode_pcm(path)) < 1e-4:
            problems.append("silent")
        if problems:
            print(f"ERROR: {key}: {'; '.join(problems)}", file=sys.stderr)
            fail = 1
        else:
            print(f"  {key:24s} {dur:4.2f}s  ok")

    committed = {p.stem for p in OUT_DIR.glob("*.ogg")}
    for extra in sorted(committed - set(LINES)):
        # Not fatal on its own, but an OGG no key resolves is dead weight the engine will never play.
        print(f"ERROR: {extra}.ogg matches no voice key in this table", file=sys.stderr)
        fail = 1
    if not fail:
        print(f"\n  all {len(LINES)} voice lines present and well-formed.")
    return fail


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate fl-base-pack radio voice lines.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="re-synthesise and compare the committed OGGs (needs piper + the voices)")
    mode.add_argument("--check-assets", action="store_true",
                      help="coverage + format check on the committed OGGs (needs ffmpeg only)")
    mode.add_argument("--verify-speech", action="store_true",
                      help="transcribe the committed OGGs and compare to their text (needs faster-whisper)")
    ap.add_argument("--voices-dir", type=Path, default=DEFAULT_VOICE_DIR,
                    help=f"where piper voice models are cached (default: {DEFAULT_VOICE_DIR})")
    args = ap.parse_args()

    if args.check_assets:
        return cmd_check_assets()
    if args.verify_speech:
        return cmd_verify_speech()
    if args.check:
        return cmd_check(args.voices_dir)
    return cmd_generate(args.voices_dir)


if __name__ == "__main__":
    raise SystemExit(main())
