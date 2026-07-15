# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Procedural weapon SFX generator for fl-base-pack.

The engine plays a fixed preset vocabulary of weapon sounds (docs/modding/formats.md, "Weapon SFX
presets"). Each preset resolves to a content-pack OGG asset name if one exists, else to a compiled-in
procedural fallback. This script synthesises the five override OGGs the pack ships:

    preset          asset name       file
    sfx.gunfire  -> sfx/gunfire   -> audio/sfx/gunfire.ogg
    sfx.launch   -> sfx/launch    -> audio/sfx/launch.ogg
    sfx.release  -> sfx/release   -> audio/sfx/release.ogg
    sfx.impact   -> sfx/impact    -> audio/sfx/impact.ogg
    sfx.explosion-> sfx/explosion -> audio/sfx/explosion.ogg

They are COMMITTED ARTIFACTS -- like the aircraft .glb meshes, they live in the repo and CI does not
rebuild them. This script is the author-side tool to regenerate them; it is not run by the engine or
by CI, and its only external dependency is ffmpeg (for OGG Vorbis encoding) plus numpy.

Determinism: every clip is seeded, so the synthesised PCM is byte-identical on a regen. The OGG
Vorbis CONTAINER is not byte-reproducible (libvorbis varies framing), so --check compares the
committed OGG's DECODED audio against a fresh synthesis within a lossy-codec tolerance, not raw
bytes. Keep the clips SHORT (< 1 s) -- long audio belongs to the streaming/music path, not here.

    python tools/sfxgen/gen_sfx.py            # writes audio/sfx/*.ogg
    python tools/sfxgen/gen_sfx.py --check    # verify the committed OGGs still match the synthesis
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100  # 44.1 kHz, the engine's SFX rate (docs/modding/formats.md, Audio)
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "audio" / "sfx"


# ── synthesis helpers (pure numpy) ───────────────────────────────────────────────────────────────

def _t(dur_s: float) -> np.ndarray:
    return np.linspace(0.0, dur_s, int(SR * dur_s), endpoint=False, dtype=np.float64)


def _noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, n)


def _onepole_lp(x: np.ndarray, a) -> np.ndarray:
    """Cheap one-pole low-pass; coefficient a in (0,1), smaller = duller. `a` may be a scalar or a
    per-sample array (for a sweeping cutoff)."""
    y = np.empty_like(x)
    av = np.broadcast_to(np.asarray(a, dtype=np.float64), x.shape)
    acc = 0.0
    for i in range(x.size):
        acc += av[i] * (x[i] - acc)
        y[i] = acc
    return y


def _fade(x: np.ndarray, in_s: float = 0.004, out_s: float = 0.02) -> np.ndarray:
    """Click-free edges: short raised-cosine in, longer out."""
    n = x.size
    ni, no = min(int(SR * in_s), n // 2), min(int(SR * out_s), n // 2)
    if ni:
        x[:ni] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, ni))
    if no:
        x[-no:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, no))
    return x


def _norm(x: np.ndarray, peak: float = 0.89) -> np.ndarray:
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


# ── one synth function per preset ────────────────────────────────────────────────────────────────

def gunfire() -> np.ndarray:
    """~90 ms: a sharp noise crack over a short low-frequency thump. A single 20 mm report; the
    server's rate limiter retriggers it into a burst."""
    rng = np.random.default_rng(101)
    t = _t(0.09)
    crack = _onepole_lp(_noise(t.size, rng), 0.6) * np.exp(-t * 55.0)
    thump = np.sin(2 * np.pi * 140.0 * t) * np.exp(-t * 40.0)
    return _fade(_norm(crack * 0.8 + thump * 0.5), out_s=0.03)


def launch() -> np.ndarray:
    """~420 ms: a rocket-motor whoosh -- band-limited noise whose pitch and level rise as the motor
    lights, then settle. The missile leaving the rail."""
    rng = np.random.default_rng(202)
    t = _t(0.42)
    env = np.clip(t / 0.05, 0, 1) * np.exp(-t * 2.0) + 0.15
    body = _onepole_lp(_noise(t.size, rng), 0.25 + 0.35 * np.clip(t / 0.3, 0, 1))
    rumble = np.sin(2 * np.pi * (90.0 + 40.0 * t) * t) * 0.3
    return _fade(_norm((body + rumble) * env), in_s=0.006, out_s=0.08)


def release() -> np.ndarray:
    """~200 ms: a mechanical rack/clunk -- a store leaving a pylon. Registered but not yet routed to
    an EffectType in the engine; shipped for the preset contract."""
    rng = np.random.default_rng(303)
    t = _t(0.20)
    clunk = np.sin(2 * np.pi * 220.0 * t) * np.exp(-t * 30.0)
    tick = _onepole_lp(_noise(t.size, rng), 0.5) * np.exp(-t * 90.0)
    return _fade(_norm(clunk * 0.7 + tick * 0.6), out_s=0.04)


def impact() -> np.ndarray:
    """~150 ms: a hard, bright crack -- a round connecting with metal."""
    rng = np.random.default_rng(404)
    t = _t(0.15)
    crack = _noise(t.size, rng) * np.exp(-t * 70.0)
    ring = np.sin(2 * np.pi * 900.0 * t) * np.exp(-t * 45.0) * 0.4
    return _fade(_norm(crack * 0.9 + ring), out_s=0.04)


def explosion() -> np.ndarray:
    """~800 ms: a low boom with a long noisy decay -- a warhead detonation."""
    rng = np.random.default_rng(505)
    t = _t(0.80)
    boom = np.sin(2 * np.pi * (70.0 - 30.0 * np.clip(t / 0.4, 0, 1)) * t) * np.exp(-t * 3.2)
    body = _onepole_lp(_noise(t.size, rng), 0.2) * np.exp(-t * 4.5)
    return _fade(_norm(boom * 0.7 + body * 0.8), in_s=0.003, out_s=0.18)


PRESETS = {
    "gunfire": gunfire,
    "launch": launch,
    "release": release,
    "impact": impact,
    "explosion": explosion,
}


# ── encode ───────────────────────────────────────────────────────────────────────────────────────

def _write_ogg(samples: np.ndarray, dest: Path) -> None:
    """int16 PCM -> WAV (stdlib) -> OGG Vorbis (ffmpeg libvorbis, quality 5, mono)."""
    pcm = np.clip(samples, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype("<i2")
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
             "-c:a", "libvorbis", "-q:a", "5", "-ac", "1", str(dest)],
            check=True,
        )
    finally:
        wav_path.unlink(missing_ok=True)


def _decode_pcm(path: Path) -> np.ndarray:
    """Decode an OGG to mono float PCM in [-1, 1] via ffmpeg (f32le)."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return np.frombuffer(raw, dtype="<f4").astype(np.float64)


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2))) if x.size else 0.0


# Sample-wise waveform equality is the wrong test for a lossy codec: Vorbis reproduces noise-heavy
# clips (the launch whoosh) perceptually, not sample-for-sample, and adds encoder delay. So --check
# compares alignment-insensitive summaries -- duration and overall RMS level -- which still trip on a
# real synth edit or a corrupt/empty file, without false-flagging codec noise decorrelation.
CHECK_DUR_TOL_S = 0.060     # Vorbis pads a clip out to its block boundary (up to ~1 long block), so
                            # a short clip decodes a little longer than source -- this band absorbs
                            # that while still tripping on a genuinely wrong length.
CHECK_RMS_RATIO = 0.15      # decoded RMS within 15% of the source's


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate fl-base-pack weapon SFX OGGs.")
    ap.add_argument("--check", action="store_true",
                    help="verify the committed OGGs still match the synthesis in level+duration (no writes)")
    args = ap.parse_args()

    if args.check:
        drift = 0
        for name, fn in PRESETS.items():
            committed = OUT_DIR / f"{name}.ogg"
            if not committed.exists():
                print(f"MISSING: {name}.ogg is not committed", file=sys.stderr)
                drift = 1
                continue
            src = fn()
            dec = _decode_pcm(committed)
            d_dur = abs(dec.size - src.size) / SR
            src_rms, dec_rms = _rms(src), _rms(dec)
            ratio = abs(dec_rms - src_rms) / src_rms if src_rms else 1.0
            status = "ok" if (d_dur <= CHECK_DUR_TOL_S and ratio <= CHECK_RMS_RATIO) else "DRIFT"
            print(f"  {name:9s} d_dur={d_dur*1000:4.0f}ms rms {src_rms:.3f}->{dec_rms:.3f} ({ratio*100:.0f}%)  {status}",
                  file=sys.stderr if status == "DRIFT" else sys.stdout)
            if status == "DRIFT":
                drift = 1
        return drift

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in PRESETS.items():
        dest = OUT_DIR / f"{name}.ogg"
        samples = fn()
        _write_ogg(samples, dest)
        print(f"  {name:9s} -> {dest.relative_to(REPO_ROOT)}  ({samples.size / SR * 1000:.0f} ms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
