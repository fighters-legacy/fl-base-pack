# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Tests for the pure-Python GLB checker. No Blender required.

Builds tiny in-memory GLBs (JSON chunk only — the checker never reads geometry) to exercise each
finding, and runs the checker against the committed F-5E if it is present.
"""

import json
import struct
from pathlib import Path

import pytest

from fl_meshlib.check import check, read_glb_json

_MAGIC = 0x46546C67
_JSON = 0x4E4F534A


def _glb(gltf: dict) -> bytes:
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    return (struct.pack("<III", _MAGIC, 2, 12 + 8 + len(js))
            + struct.pack("<II", len(js), _JSON) + js)


def test_clean_file_has_no_findings():
    glb = _glb({"nodes": [{"name": "f5e"}, {"name": "f5e_b"}],
                "images": [{"uri": "../../textures/f5e_diffuse.ktx2"}]})
    assert check(glb) == []


def test_uppercase_node_flagged():
    levels = check(_glb({"nodes": [{"name": "F5E"}]}))
    assert any(lvl == "warn" and "lowercase" in msg for lvl, msg in levels)


def test_unpaired_damage_node_flagged():
    levels = check(_glb({"nodes": [{"name": "wing_b"}]}))
    assert any("no base node" in msg for _, msg in levels)


def test_embedded_data_uri_is_error():
    levels = check(_glb({"nodes": [{"name": "x"}],
                         "images": [{"uri": "data:image/png;base64,AAAA"}]}))
    assert any(lvl == "error" for lvl, _ in levels)


def test_bufferview_image_is_error():
    levels = check(_glb({"nodes": [{"name": "x"}], "images": [{"bufferView": 0}]}))
    assert any(lvl == "error" and "bufferView" in msg for lvl, msg in levels)


def test_skins_are_error():
    levels = check(_glb({"nodes": [{"name": "x"}], "skins": [{"joints": [0]}]}))
    assert any(lvl == "error" and "skin" in msg for lvl, msg in levels)


def test_rejects_non_glb():
    with pytest.raises(ValueError):
        read_glb_json(b"not a glb at all")


def test_committed_f5e_passes_if_present():
    # tools/meshlib/tests -> repo root
    f5e = Path(__file__).resolve().parents[3] / "aircraft" / "f5e" / "f5e.glb"
    if not f5e.exists():
        pytest.skip("committed f5e.glb not present")
    findings = check(f5e)
    errors = [m for lvl, m in findings if lvl == "error"]
    assert errors == [], f"unexpected errors on the shipped F-5E: {errors}"
