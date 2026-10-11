# SPDX-License-Identifier: MIT
"""Re-imports an exported .glb into a fresh scene, reports what the engine will get and renders
preview images — the check that materials, textures, emission, node names and pivots survived.

    blender -b --factory-startup -P tools/blender/preview.py -- <name> [mode] [views] [size]

    name   public/models/<name>.glb
    mode   night | studio | clay      (default: studio)
    views  comma list of front, three, side, back, top, low, iso  or  close@x:y:z:dist:az:el
           (glTF-free Blender coordinates; az 0 = from the front (-Y), 90 = from +X)
    size   pixels (default 640)

Writes tools/blender/preview/<name>-<mode>-<view>.png and prints a report.
A 1.7 m figure stands beside the model for scale (not part of the model).
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import lib  # noqa: E402,F401  (makes numpy available to the glTF importer)

VIEWS = {
    "front": (0, 8, 1.0),
    "three": (35, 16, 1.0),
    "side": (90, 6, 1.0),
    "back": (180, 14, 1.0),
    "top": (0, 85, 1.0),
    "low": (25, 2, 0.9),
    "iso": (-40, 30, 1.0),
    "left": (-90, 6, 1.0),
}


def report(path):
    print("=" * 78)
    print(f"REPORT {os.path.relpath(path, ROOT)}  {os.path.getsize(path) / 1024:.0f} KB")
    total = 0
    objs = sorted(bpy.context.scene.objects, key=lambda o: (o.parent.name if o.parent else "", o.name))

    def walk(o, depth):
        nonlocal total
        loc = o.matrix_world.translation
        gl = (loc.x, loc.z, -loc.y)
        extra = ""
        if o.type == "MESH":
            me = o.data
            me.calc_loop_triangles()
            t = len(me.loop_triangles)
            total += t
            mats = [m.name for m in me.materials if m]
            extra = f" tris={t} mats={mats} uv={[u.name for u in me.uv_layers]}"
        r = o.rotation_quaternion if o.rotation_mode == "QUATERNION" else o.rotation_euler.to_quaternion()
        rot = "" if abs(r.w) > 0.99999 else f" rotq={tuple(round(v, 3) for v in r)}"
        print(f"  {'  ' * depth}{o.name} [{o.type}] pivot(glTF)=({gl[0]:.3f}, {gl[1]:.3f}, {gl[2]:.3f}){rot}{extra}")
        for c in sorted(o.children, key=lambda c: c.name):
            if depth < 2 or not c.name.startswith("anchor_"):
                walk(c, depth + 1)
        anchors = [c for c in o.children if c.name.startswith("anchor_")]
        if anchors and depth >= 2:
            print(f"  {'  ' * (depth + 1)}... {len(anchors)} anchor_ empties")

    roots = [o for o in objs if o.parent is None]
    for o in roots:
        walk(o, 0)
    print(f"  TOTAL tris={total}")
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b is None:
            continue

        def desc(sock):
            if sock.is_linked:
                n = sock.links[0].from_node
                while n.type not in ("TEX_IMAGE",) and n.inputs and any(i.is_linked for i in n.inputs):
                    n = next(i for i in n.inputs if i.is_linked).links[0].from_node
                if n.type == "TEX_IMAGE" and n.image:
                    return f"tex:{n.image.name}({n.image.size[0]}x{n.image.size[1]})"
                return f"linked:{n.type}"
            v = sock.default_value
            try:
                return "(" + ", ".join(f"{x:.3f}" for x in v[:3]) + ")"
            except TypeError:
                return f"{v:.3f}"
        em = b.inputs["Emission"]
        print(f"  material {m.name}: base={desc(b.inputs['Base Color'])} rough={desc(b.inputs['Roughness'])} "
              f"metal={desc(b.inputs['Metallic'])} emission={desc(em)} x{b.inputs['Emission Strength'].default_value:.2f} "
              f"normal={'yes' if b.inputs['Normal'].is_linked else 'no'} blend={m.blend_method} "
              f"double_sided={not m.use_backface_culling}")
    lo, hi = bounds()
    print(f"  bounds (Blender) min=({lo.x:.2f}, {lo.y:.2f}, {lo.z:.2f}) max=({hi.x:.2f}, {hi.y:.2f}, {hi.z:.2f})"
          f"  size=({hi.x - lo.x:.2f} x {hi.y - lo.y:.2f} x {hi.z - lo.z:.2f}) m")
    print("=" * 78)


FIGURE = []


def bounds():
    pts = [o.matrix_world @ Vector(c) for o in bpy.context.scene.objects if o.type == "MESH" for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def setup(mode, lo, hi, model_objs):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    ee = scene.eevee
    ee.taa_render_samples = 32
    ee.use_gtao = True
    ee.gtao_distance = 0.6
    ee.use_soft_shadows = True
    ee.shadow_cube_size = "1024"
    ee.shadow_cascade_size = "2048"
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast" if mode == "night" else "None"
    size = (hi - lo)
    rad = max(size.length / 2, 0.3)
    centre = (lo + hi) / 2
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    scene.world = world

    # ground
    bpy.ops.mesh.primitive_plane_add(size=rad * 30, location=(centre.x, centre.y, min(0.0, lo.z)))
    ground = bpy.context.object
    gm = bpy.data.materials.new("preview_ground")
    gm.use_nodes = True
    gb = gm.node_tree.nodes["Principled BSDF"]
    gb.inputs["Roughness"].default_value = 0.95
    ground.data.materials.append(gm)

    # scale figure (1.7 m) beside the model
    fig_mat = bpy.data.materials.new("preview_figure")
    fig_mat.use_nodes = True
    fig_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.32, 0.45, 1)
    fx, fy, fz = hi.x + 0.6, lo.y + 0.3, min(0.0, lo.z)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.17, depth=1.42, location=(fx, fy, fz + 0.71))
    bpy.context.object.data.materials.append(fig_mat)
    FIGURE.append(bpy.context.object)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(fx, fy, fz + 1.58))
    bpy.context.object.data.materials.append(fig_mat)
    FIGURE.append(bpy.context.object)

    if mode == "night":
        bg.inputs["Color"].default_value = (0.004, 0.006, 0.014, 1)
        bg.inputs["Strength"].default_value = 1.0
        gb.inputs["Base Color"].default_value = (0.05, 0.045, 0.035, 1)
        ee.use_bloom = True
        ee.bloom_threshold = 0.9
        ee.bloom_intensity = 0.06
        ee.bloom_radius = 5.0
        moon = bpy.data.objects.new("moon", bpy.data.lights.new("moon", "SUN"))
        moon.data.energy = 0.08
        moon.data.color = (0.6, 0.7, 1.0)
        moon.rotation_euler = (math.radians(55), 0, math.radians(150))
        scene.collection.objects.link(moon)
        # a couple of warm path lights in front, low
        for i, x in enumerate((-rad * 0.6, rad * 0.6)):
            pl = bpy.data.objects.new(f"path{i}", bpy.data.lights.new(f"path{i}", "POINT"))
            pl.data.energy = 60 * rad
            pl.data.color = (1.0, 0.55, 0.25)
            pl.data.shadow_soft_size = 0.2
            pl.location = (centre.x + x, lo.y - rad * 0.5, 0.4)
            scene.collection.objects.link(pl)
    else:
        bg.inputs["Color"].default_value = (0.62, 0.66, 0.72, 1)
        bg.inputs["Strength"].default_value = 0.9
        gb.inputs["Base Color"].default_value = (0.5, 0.5, 0.48, 1)
        sun = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
        sun.data.energy = 3.5
        sun.data.angle = math.radians(6)
        sun.rotation_euler = (math.radians(48), 0, math.radians(-38))
        scene.collection.objects.link(sun)
        if mode == "clay":
            clay = bpy.data.materials.new("preview_clay")
            clay.use_nodes = True
            clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
            for o in model_objs:
                for i in range(len(o.data.materials)):
                    o.data.materials[i] = clay
    return centre, rad


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name = argv[0]
    mode = argv[1] if len(argv) > 1 else "studio"
    views = argv[2].split(",") if len(argv) > 2 else ["front", "three", "side", "back"]
    if views == ["-"]:
        views = []
    size = int(argv[3]) if len(argv) > 3 else 640
    path = name if name.endswith(".glb") else os.path.join(ROOT, "public", "models", name + ".glb")
    name = os.path.splitext(os.path.basename(path))[0]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    report(path)
    if not views:
        return
    lo, hi = bounds()
    model_objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    centre, rad = setup(mode, lo, hi, model_objs)
    scene = bpy.context.scene
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.lens = 50
    cam.data.clip_start = 0.02
    cam.data.clip_end = 1000
    scene.collection.objects.link(cam)
    scene.camera = cam
    out_dir = os.path.join(HERE, "preview")
    os.makedirs(out_dir, exist_ok=True)
    for v in views:
        if v.startswith("close@"):
            x, y, z, dist, az, el = (float(t) for t in v[6:].split(":"))
            target = Vector((x, y, z))
            label = f"close{len([w for w in views[:views.index(v)] if w.startswith('close@')]) + 1}"
        else:
            az, el, f = VIEWS[v]
            target = centre.copy()
            dist = rad / math.tan(cam.data.angle / 2) * 1.08 * f
            label = v
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = target + d * dist
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        for f in FIGURE:   # the scale figure would stand between a side camera and the model
            f.hide_render = label in ("side",)
        scene.render.filepath = os.path.join(out_dir, f"{name}-{mode}-{label}.png")
        bpy.ops.render.render(write_still=True)
        print("[preview]", scene.render.filepath)


main()
