# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Determinism test for the F-5E build. Requires Blender-as-a-module (`bpy`).

Skipped automatically where bpy is unavailable, so the pure-math suite still runs everywhere. The
job that installs the bpy wheel exercises this: it builds the F-5E twice and asserts the outputs are
byte-identical, and that they match the committed artifacts. Byte-identical regeneration is the
regression check that a "generated" aircraft's source really is its build script.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("bpy", reason="determinism test needs Blender-as-a-module")

_REPO = Path(__file__).resolve().parents[3]
_BUILD = _REPO / "aircraft" / "f5e" / "f5e_build.py"
_OUTPUTS = ["f5e.glb", "f5e_lod0.glb", "f5e_lod1.glb", "f5e_lod2.glb",
            "f5e_shadow.glb", "f5e_cockpit.glb"]


def _digest(d: Path):
    return {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in _OUTPUTS}


def _build(out: Path):
    # Run the generator in its own bpy process; a bpy module can only be initialised once per
    # process, so two builds in one pytest run must each be a subprocess.
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(_BUILD), "--", "--out", str(out)], check=True)


def test_two_builds_are_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _build(a)
    _build(b)
    assert _digest(a) == _digest(b), "the F-5E build is not deterministic"


@pytest.mark.skipif(
    not os.environ.get("FL_MESHLIB_MATCH_COMMITTED"),
    reason="byte-for-byte match with committed artifacts is Blender-version-specific; "
           "set FL_MESHLIB_MATCH_COMMITTED=1 when running the pinned Blender the pack ships with",
)
def test_build_matches_committed(tmp_path):
    _build(tmp_path)
    committed = _digest(_REPO / "aircraft" / "f5e")
    assert _digest(tmp_path) == committed, \
        "regenerated F-5E differs from the committed artifacts — script and outputs disagree"
