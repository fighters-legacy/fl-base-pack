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

# Every generated aircraft, by discovery: aircraft/<id>/<id>_build.py. The F-16A joined the
# F-5E here (fl-base-pack#19); the T-38A and every aircraft after them join for free.
_AIRCRAFT = sorted(p.parent.name for p in _REPO.glob("aircraft/*/*_build.py")
                   if p.stem == f"{p.parent.name}_build")


def _outputs(aid: str):
    return [f"{aid}.glb", f"{aid}_lod0.glb", f"{aid}_lod1.glb", f"{aid}_lod2.glb",
            f"{aid}_shadow.glb", f"{aid}_cockpit.glb"]


def _digest(d: Path, aid: str):
    return {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in _outputs(aid)}


def _build(aid: str, out: Path):
    # Run the generator in its own bpy process; a bpy module can only be initialised once per
    # process, so two builds in one pytest run must each be a subprocess.
    out.mkdir(parents=True, exist_ok=True)
    build = _REPO / "aircraft" / aid / f"{aid}_build.py"
    subprocess.run([sys.executable, str(build), "--", "--out", str(out)], check=True)


@pytest.mark.parametrize("aid", _AIRCRAFT)
def test_two_builds_are_byte_identical(aid, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _build(aid, a)
    _build(aid, b)
    assert _digest(a, aid) == _digest(b, aid), f"the {aid} build is not deterministic"


@pytest.mark.skipif(
    not os.environ.get("FL_MESHLIB_MATCH_COMMITTED"),
    reason="byte-for-byte match with committed artifacts is Blender-version-specific; "
           "set FL_MESHLIB_MATCH_COMMITTED=1 when running the pinned Blender the pack ships with",
)
@pytest.mark.parametrize("aid", _AIRCRAFT)
def test_build_matches_committed(aid, tmp_path):
    _build(aid, tmp_path)
    committed = _digest(_REPO / "aircraft" / aid, aid)
    assert _digest(tmp_path, aid) == committed, \
        f"regenerated {aid} differs from the committed artifacts — script and outputs disagree"
