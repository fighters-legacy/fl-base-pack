# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Music generator for fl-base-pack (pack issue #5).

The engine plays one music track per game state, driven by `data/playlist.toml`
(docs/modding/formats.md → "Music Playlist"). ⚠ Without that file the engine plays its compiled-in
procedural music and pack tracks are never heard, so the playlist and these OGGs ship together.

Tracks are generated locally with [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) (MIT), an
open-weight text-to-music model, under the audio exception to the AI content policy (decision record
2026-08-17, fighters-legacy/fighters-legacy#1200): open-weight and self-hosted, regenerable from the
model, prompt and seed recorded here and in `audio/music/SOURCES.md`, marked CC0 in `REUSE.toml`
rather than the pack's CC-BY-4.0, and disclosed player-facing in the pack README.

⚠ THE SEED ALONE DOES NOT MAKE THIS REPRODUCIBLE, and the CLI does not tell you so. Two runs at the
same seed produced different music until `lm_temperature = 0.0` was set as well, because the 5Hz LM
that lays out the audio tokens samples independently of the diffusion seed. With both fixed, two runs
here were byte-identical. See `_generate_wav` for the full set and why each is there.

Even then, determinism holds for a fixed model version, precision and device: a different GPU or a
model update can produce different music from the same inputs. The committed OGG is the artifact of
record; this script reproduces it, it does not define it.

Prerequisites (author-side only -- CI never runs generation):
  1. git clone https://github.com/ace-step/ACE-Step-1.5 && install its requirements
  2. point --acestep-dir at that checkout (or set ACESTEP_DIR)
  3. ffmpeg on PATH
Weights (~10 GB) download on first run to the ACE-Step checkout's default cache.

    python tools/musicgen/gen_music.py --acestep-dir ~/src/ACE-Step-1.5   # write audio/music/*.ogg
    python tools/musicgen/gen_music.py --check-assets                     # format + playlist coverage
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import wave
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "audio" / "music"
PLAYLIST = REPO_ROOT / "data" / "playlist.toml"

SR = 48000          # ACE-Step's native rate; the engine resamples nothing
OGG_QUALITY = "4"   # ~128 kbps stereo -- music is the one place stereo earns its bytes
TRIM_REL_THRESHOLD = 0.02  # -34 dB below the track's own peak counts as silence at the edges
TRIM_PAD_S = 0.15          # musical air kept either side of the cut
EDGE_FADE_S = 0.05         # fade over the cuts so a loop point cannot click
MAX_EDGE_SILENCE_S = 1.5   # what --check-assets tolerates before calling a track's edges broken

MIN_TRACK_S = 20.0
MAX_TRACK_S = 180.0  # a pack track longer than this is a mistake, not a mood

# ── the track table ──────────────────────────────────────────────────────────────────────────────
#
# name -> (game state, caption/prompt, duration_s, seed)
#
# The state column must agree with data/playlist.toml; --check-assets enforces that both ways, so a
# track added here and forgotten there (or the reverse) fails rather than silently never playing.
#
# Prompts are tag-style, which is what the model is conditioned on, and all are INSTRUMENTAL: the
# engine ducks music under radio traffic, and a vocal line fighting a wave-off call is the wrong
# mix. Keep them period-plausible for the pack's 1970s-80s airframes -- orchestral and analogue
# synth, not modern EDM.
TRACKS: dict[str, tuple[str, str, float, int]] = {
    "menu_theme": (
        "Menu",
        "cinematic orchestral, military, restrained, slow build, strings and low brass, "
        "atmospheric pad, instrumental",
        75.0, 101,
    ),
    "patrol_01": (
        "FlightPatrol",
        "ambient orchestral, sparse, wide, quiet tension, sustained strings, soft analogue synth, "
        "slow, instrumental",
        100.0, 202,
    ),
    "patrol_02": (
        "FlightPatrol",
        "ambient electronic, cold, minimal pulse, distant brass, high altitude atmosphere, "
        "slow, instrumental",
        100.0, 303,
    ),
    "combat_01": (
        "FlightCombat",
        "driving orchestral action, urgent low strings ostinato, taiko and snare percussion, "
        "brass stabs, tense, instrumental",
        100.0, 404,
    ),
    "victory": (
        "MissionSuccess",
        "triumphant orchestral brass fanfare, resolving, warm, short, instrumental",
        35.0, 505,
    ),
    "debrief": (
        "Debrief",
        "reflective orchestral, quiet piano and strings, sombre, slow, instrumental",
        60.0, 606,
    ),
}


def _acestep_dir(arg: str | None) -> Path:
    raw = arg or os.environ.get("ACESTEP_DIR")
    if not raw:
        raise SystemExit(
            "error: pass --acestep-dir (or set ACESTEP_DIR) to an ACE-Step 1.5 checkout.\n"
            "       git clone https://github.com/ace-step/ACE-Step-1.5"
        )
    path = Path(raw).expanduser().resolve()
    if not (path / "cli.py").exists():
        raise SystemExit(f"error: {path} has no cli.py -- not an ACE-Step 1.5 checkout")
    return path


def _generate_wav(name: str, state: str, prompt: str, duration: float, seed: int,
                  acestep: Path, work: Path) -> Path:
    """Drive the ACE-Step CLI through a config file and return the WAV it wrote."""
    out_dir = work / name
    out_dir.mkdir(parents=True, exist_ok=True)
    config = work / f"{name}.toml"
    # Every line below that is not the prompt is here for determinism, and each was found the hard
    # way by running the same config twice and diffing the output:
    #
    #   seeds/use_random_seed  `seed = N` is SILENTLY IGNORED by this CLI -- it takes `seeds = [N]`
    #                          and `use_random_seed = false`. With `seed` alone the run reports a
    #                          random seed (2733836368 on the run that caught it) and the track is
    #                          unreproducible.
    #   lm_temperature = 0.0   Fixing the seed is NOT enough. The 5Hz LM that lays out the audio
    #                          tokens samples at 0.85 by default, so two runs at seed 101 produced
    #                          different music. At 0.0 the whole pipeline is byte-identical.
    #   thinking = false       With thinking on, the CLI writes a draft prompt to a file and BLOCKS
    #                          on an interactive editor (`input()`), which is an EOFError in any
    #                          non-interactive run and a hand-edited prompt in an interactive one --
    #                          neither is reproducible.
    #   backend = "pt"         The vllm backend is optional and heavier; pt is the portable path.
    config.write_text(
        f'caption = "{prompt}"\n'
        f'duration = {duration}\n'
        f'instrumental = true\n'
        f'seeds = [{seed}]\n'
        f'use_random_seed = false\n'
        f'lm_temperature = 0.0\n'
        f'thinking = false\n'
        f'batch_size = 1\n'
        f'audio_format = "wav"\n'
        f'save_dir = "{out_dir}"\n'
        f'backend = "pt"\n'
    )
    subprocess.run([sys.executable, "cli.py", "-c", str(config)], cwd=acestep, check=True)
    wavs = sorted(out_dir.glob("**/*.wav"))
    if not wavs:
        raise SystemExit(f"error: ACE-Step wrote no wav for {name} (looked under {out_dir})")
    return wavs[0]


def _decode_stereo(path: Path) -> np.ndarray:
    """Decode to float32 stereo, shape (samples, 2)."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float32).reshape(-1, 2)


def _trim_and_fade(x: np.ndarray) -> np.ndarray:
    """Cut the model's leading/trailing silence and fade the cuts.

    ⚠ THIS IS NOT COSMETIC. Every track came out of the model with 4-9 s of silence on the tail
    (`combat_01` also had 2.3 s on the head), and four of these six LOOP. A looping track with a six
    second silent tail plays six seconds of dead air on every cycle, which sounds exactly like the
    music system breaking. The engine's 3 s crossfade covers state CHANGES, not the loop point.
    """
    mono = x.mean(axis=1)
    peak = float(np.max(np.abs(mono)))
    if peak <= 0:
        return x
    loud = np.flatnonzero(np.abs(mono) > peak * TRIM_REL_THRESHOLD)
    if loud.size:
        pad = int(TRIM_PAD_S * SR)
        x = x[max(0, loud[0] - pad): min(len(x), loud[-1] + pad)]

    n = min(int(EDGE_FADE_S * SR), len(x) // 2)
    if n > 0:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
        x = x.copy()
        x[:n] *= ramp
        x[-n:] *= ramp[::-1]
    return x


def _encode_ogg(src: Path, dest: Path) -> None:
    trimmed = _trim_and_fade(_decode_stereo(src))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    try:
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(trimmed, -1.0, 1.0) * 32767.0).astype("<i2").tobytes())
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
             "-c:a", "libvorbis", "-q:a", OGG_QUALITY, "-ar", str(SR), str(dest)],
            check=True,
        )
    finally:
        wav.unlink(missing_ok=True)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,channels,sample_rate",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return json.loads(out)


def _playlist_tracks() -> dict[str, list[str]]:
    """state id -> asset names, straight from the shipped playlist."""
    data = tomllib.loads(PLAYLIST.read_text())
    return {s["id"]: list(s["tracks"]) for s in data.get("states", [])}


def cmd_generate(acestep: Path) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for name, (state, prompt, duration, seed) in TRACKS.items():
            wav = _generate_wav(name, state, prompt, duration, seed, acestep, work)
            dest = OUT_DIR / f"{name}.ogg"
            _encode_ogg(wav, dest)
            dur = float(_probe(dest)["format"]["duration"])
            print(f"  {name:12s} {state:15s} seed={seed:<5d} {dur:6.1f}s  {dest.name}")
    return 0


def cmd_check_assets() -> int:
    """Format + BOTH-WAYS playlist coverage, with ffmpeg and the stdlib only.

    The two-way check is the point. A track file with no playlist entry never plays, and a playlist
    entry with no file is worse -- the engine logs a load failure and that state goes silent, which
    is exactly the kind of thing that ships unnoticed because nothing else looks at either file.
    """
    fail = 0
    playlist = _playlist_tracks()
    referenced = {t for tracks in playlist.values() for t in tracks}

    for state, tracks in playlist.items():
        if not tracks:
            print(f"ERROR: playlist state {state} lists no tracks", file=sys.stderr)
            fail = 1

    for asset in sorted(referenced):
        if not asset.startswith("music/"):
            print(f"ERROR: playlist references {asset!r}, which is not a music asset", file=sys.stderr)
            fail = 1
            continue
        path = OUT_DIR / f"{asset.removeprefix('music/')}.ogg"
        if not path.exists():
            print(f"ERROR: playlist references {asset!r} but {path.relative_to(REPO_ROOT)} is missing",
                  file=sys.stderr)
            fail = 1
            continue
        info = _probe(path)
        stream = info["streams"][0]
        dur = float(info["format"]["duration"])
        problems = []
        if stream["codec_name"] != "vorbis":
            problems.append(f"codec {stream['codec_name']}, expected vorbis")
        if int(stream["sample_rate"]) != SR:
            problems.append(f"{stream['sample_rate']} Hz, expected {SR}")
        if not MIN_TRACK_S <= dur <= MAX_TRACK_S:
            problems.append(f"{dur:.0f}s outside [{MIN_TRACK_S:.0f}, {MAX_TRACK_S:.0f}]")
        # Edge silence, checked because it is invisible to every other check and audible on every
        # loop: the raw model output carried 4-9 s of it and nothing but listening would have caught
        # the regression if the trim step were ever dropped.
        pcm = _decode_stereo(path).mean(axis=1)
        peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
        if peak <= 0:
            problems.append("silent")
        else:
            loud = np.flatnonzero(np.abs(pcm) > peak * TRIM_REL_THRESHOLD)
            head, tail = loud[0] / SR, (len(pcm) - loud[-1]) / SR
            if head > MAX_EDGE_SILENCE_S or tail > MAX_EDGE_SILENCE_S:
                problems.append(f"edge silence head={head:.1f}s tail={tail:.1f}s "
                                f"(max {MAX_EDGE_SILENCE_S}s -- a looping track would play it as dead air)")
        if problems:
            print(f"ERROR: {asset}: {'; '.join(problems)}", file=sys.stderr)
            fail = 1
        else:
            print(f"  {asset:22s} {dur:6.1f}s  {stream['channels']}ch  ok")

    for path in sorted(OUT_DIR.glob("*.ogg")):
        asset = f"music/{path.stem}"
        if asset not in referenced:
            print(f"ERROR: {path.name} is in no playlist state -- it can never play", file=sys.stderr)
            fail = 1

    table_states = {state for state, _p, _d, _s in TRACKS.values()}
    if table_states - set(playlist):
        print(f"ERROR: this script targets states the playlist does not define: "
              f"{sorted(table_states - set(playlist))}", file=sys.stderr)
        fail = 1

    if not fail:
        print(f"\n  {len(referenced)} tracks across {len(playlist)} states, all present and well-formed.")
    return fail


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate fl-base-pack music tracks.")
    ap.add_argument("--check-assets", action="store_true",
                    help="format + playlist coverage check on the committed OGGs (ffmpeg only)")
    ap.add_argument("--acestep-dir", help="path to an ACE-Step 1.5 checkout (or set ACESTEP_DIR)")
    args = ap.parse_args()
    if args.check_assets:
        return cmd_check_assets()
    return cmd_generate(_acestep_dir(args.acestep_dir))


if __name__ == "__main__":
    raise SystemExit(main())
