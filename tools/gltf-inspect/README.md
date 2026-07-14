<!--
SPDX-FileCopyrightText: Contributors to fl-base-pack
SPDX-License-Identifier: CC-BY-4.0
-->
# gltf-inspect — a stopgap mesh viewer

A single-page, offline glTF viewer for **catching geometry and node-naming mistakes** while
authoring aircraft. It runs in a browser with no build step; three.js is vendored under `vendor/`.

## Why this exists, and when it goes away

The F-5E shipped with three geometry defects (a blade-shaped radome, absent intakes, a flat canopy)
that no one caught because the only way to look at a content mesh was to boot `fl-server` plus the
client and fly a camera to it — a path that was itself broken three ways at the time. All three
defects were plainly visible *shape* problems.

This tool is the cheap, immediate answer to that: drop a `.glb` in, orbit it, read the node tree.
It is **not** the game renderer, and it must never be mistaken for one — it shows three.js's own
materials and lighting, ignores the engine's grey-material reality, KTX2 textures and LOD selection,
and it cannot reproduce how the aircraft will actually look in `fighters-legacy`.

It is deliberately temporary. The real answer is the standalone `fl-viewer` that reuses the engine's
own renderer (**fighters-legacy#838**); retire this tool when that ships.

## Use

Serve the pack root over http so the viewer can fetch sibling assets:

    cd <fl-base-pack>
    python3 -m http.server 8000
    # open http://localhost:8000/tools/gltf-inspect/

- **Open** a `.glb`/`.gltf`, click **F-5E** to load `aircraft/f5e/f5e.glb`, or drag a file onto the
  viewport. (Opening `index.html` directly as a `file://` page works for **Open** and drag-drop; the
  **F-5E** shortcut needs http, because a `file://` page cannot fetch a sibling.)
- **Wireframe / Normals / Flat grey** overlays; **backface tint** to spot inverted winding.
- The **node tree** lists every named node; click one to highlight its bounds. `_b` damage nodes are
  flagged.
- **Animation clips** (once aircraft carry them, fighters-legacy#840) get a scrub slider each,
  driven the way the engine will: `t = value × duration`. Clips whose names end in `spin` loop
  instead of scrubbing.
- **Convention checks** run a small local subset (uppercase node names, unpaired `_b` nodes, clip
  name style, skins/morphs). The authority is `validate-mesh` in CI — this panel is a hint, not a
  gate.

## Vendored code

`vendor/three/` is three.js r160 (MIT), committed so the tool works offline. It is the only
non-`CC-BY-4.0` content in the pack; see the `tools/gltf-inspect/vendor/**` annotation in
`REUSE.toml`. To update, re-download the same file set at a new tag.
