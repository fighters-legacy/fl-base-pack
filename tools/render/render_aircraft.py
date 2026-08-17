#!/usr/bin/env python3
# SPDX-FileCopyrightText: Contributors to fl-base-pack
# SPDX-License-Identifier: CC-BY-4.0
"""Render orthographic views of a built aircraft glb so a HUMAN CAN LOOK AT THE SHAPE.

    blender --background --python tools/render/render_aircraft.py -- \
        --glb aircraft/mig29a/mig29a.glb --out /tmp/renders --tag mig29a

Writes <tag>_side.png, _front.png, _top.png and _q34.png.

⚑ WHY THIS EXISTS. Every automated check this pack runs proves SCALE and STRUCTURE, never SHAPE:
validate-mesh checks the file is well-formed, the per-vertex measurement checks span and length
against the published datums, and the determinism check proves two builds agree. An aircraft can
pass all three and still look nothing like itself.

That is not hypothetical. It has now happened twice:
  * the B-1B "rendered as a plain tube with wings" — the glove sat entirely inside the fuselage;
  * the MiG-29A shipped with 1.64 m-diameter nacelles starting level with the cockpit and huge
    square intake mouths, and it took a human opening the model to notice.

Both were invisible to measurement and obvious in a render. So: after building an aircraft, RENDER
IT AND LOOK, before opening the PR. Then compare against the PD reference photography in that
aircraft's out-of-repo reference set.

Notes:
  * the damage-state node (`<id>_b`) is hidden, so the clean airframe is what you see;
  * absolute paths only — Blender resolves the render filepath relative to the .blend, not cwd;
  * Blender 5.2 on this box prints benign OpenColorIO and Draco errors at startup on every run.
    Detect failure by MISSING OUTPUT FILES or `Traceback`, never by grepping for "Error".
"""
import bpy, sys, math, os
from mathutils import Vector
argv = sys.argv[sys.argv.index("--")+1:]
glb = argv[argv.index("--glb")+1]; out = argv[argv.index("--out")+1]; tag = argv[argv.index("--tag")+1]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
# hide the damage-state node so we render the clean airframe
for o in objs:
    if o.name.endswith("_b") or ".001" in o.name:
        o.hide_render = True
vis = [o for o in objs if not o.hide_render]
mn = Vector(( 1e9, 1e9, 1e9)); mx = Vector((-1e9,-1e9,-1e9))
for o in vis:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        mn = Vector((min(mn[i], w[i]) for i in range(3)))
        mx = Vector((max(mx[i], w[i]) for i in range(3)))
ctr = (mn+mx)/2.0; size = max((mx-mn)[i] for i in range(3))
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); bpy.context.scene.collection.objects.link(sun)
sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(40))
world = bpy.data.worlds.new("w"); bpy.context.scene.world = world
world.use_nodes = True; world.node_tree.nodes["Background"].inputs[0].default_value = (0.6,0.65,0.7,1)
cam_d = bpy.data.cameras.new("cam"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = size*1.15
cam = bpy.data.objects.new("cam", cam_d); bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x = 1400; sc.render.resolution_y = 900
sc.render.image_settings.file_format = 'PNG'
views = {  # (location offset dir, rotation euler)
 "side":  ((1,0,0), (math.radians(90), 0, math.radians(90))),
 "front": ((0,-1,0), (math.radians(90), 0, 0)),
 "top":   ((0,0,1), (0,0,0)),
 "q34":   ((0.8,-0.9,0.45), None),
}
for name,(d,rot) in views.items():
    v = Vector(d).normalized()
    cam.location = ctr + v*size*3
    if rot: cam.rotation_euler = rot
    else:
        dirv = (ctr - cam.location).normalized()
        cam.rotation_euler = dirv.to_track_quat('-Z','Y').to_euler()
    sc.render.filepath = os.path.join(out, f"{tag}_{name}.png")
    bpy.ops.render.render(write_still=True)
print("rendered", tag)
