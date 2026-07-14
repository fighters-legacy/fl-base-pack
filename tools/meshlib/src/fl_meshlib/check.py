# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: MIT
"""Cheap local sanity checks on a generated .glb. Pure Python; no Blender.

This is a fast pre-flight an author (or a build script) can run without the engine toolchain. It is
NOT a substitute for the engine's ``validate-mesh``, which is the authority and runs in CI; it
exists to catch the obvious mistakes in the same process that just wrote the file.
"""

import json
import struct

_GLB_MAGIC = 0x46546C67
_CHUNK_JSON = 0x4E4F534A


def read_glb_json(path_or_bytes):
    """Parse and return the JSON chunk of a binary glTF (.glb) as a dict."""
    raw = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else \
        __import__("pathlib").Path(path_or_bytes).read_bytes()
    if struct.unpack_from("<I", raw, 0)[0] != _GLB_MAGIC:
        raise ValueError("not a GLB (bad magic)")
    jlen = struct.unpack_from("<I", raw, 12)[0]
    ctype = struct.unpack_from("<I", raw, 16)[0]
    if ctype != _CHUNK_JSON:
        raise ValueError("first chunk is not JSON")
    return json.loads(raw[20:20 + jlen])


def node_names(gltf):
    """All node names declared in the glTF, in declaration order."""
    return [n.get("name", "") for n in gltf.get("nodes", [])]


def check(path_or_bytes):
    """Return a list of (level, message) findings. level is 'error' | 'warn'.

    An empty list means no local problems were found.
    """
    findings = []
    gltf = read_glb_json(path_or_bytes)
    names = [n for n in node_names(gltf) if n]

    # Node names: lowercase_underscore. The engine lowercases asset names before resolving them;
    # a capital in a node name is a latent silent miss.
    for n in names:
        if any(c.isupper() for c in n):
            findings.append(("warn", f"node name '{n}' is not lowercase"))
        if " " in n or "-" in n:
            findings.append(("warn", f"node name '{n}' has a space or hyphen"))

    # Damage `_b` nodes must be paired with a base node of the same stem in the same file.
    have = set(names)
    for n in names:
        if n.endswith("_b") and n[:-2] not in have:
            findings.append(("warn", f"damage node '{n}' has no base node '{n[:-2]}'"))

    # No embedded image data: the engine consumes external .ktx2 URIs; an embedded image (a data:
    # URI, or a bufferView-backed image) is a validate-mesh error.
    for i, img in enumerate(gltf.get("images", [])):
        uri = img.get("uri", "")
        if "bufferView" in img:
            findings.append(("error", f"image[{i}] is embedded in a bufferView"))
        elif uri.startswith("data:"):
            findings.append(("error", f"image[{i}] is an embedded data: URI"))

    # Skins and morph targets are not rigid articulation; the engine rejects them.
    if gltf.get("skins"):
        findings.append(("error", "file contains skins (rigid node animation only)"))
    for m in gltf.get("meshes", []):
        for p in m.get("primitives", []):
            if p.get("targets"):
                findings.append(("error", f"mesh '{m.get('name','')}' has morph targets"))
                break

    return findings
