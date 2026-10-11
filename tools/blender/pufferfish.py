# SPDX-License-Identifier: MIT
"""A pumpkin pufferfish for the Deep (reference/jellyfish-path.jpg).

    blender -b --factory-startup -P tools/blender/pufferfish.py

Writes public/models/pufferfish.glb: a round pumpkin (about 0.5 m) painted lime UV paint with
dark spots, short spines, two big glowing eyes and pink lips, facing the front (-Y in Blender,
+Z in glTF).

It floats, so unlike the standing models its origin is the centre of the body: scale the root
`pufferfish` node about it to puff it up. Children: `tail` (pivot at the tail's root: rotate
about its local Z (glTF Y) to wag), `fin_L`, `fin_R` (pivots at their roots: flap them) and
`hang_point` (top of the stem, where its string goes). L/R as seen from the front.
Materials: `glow_uvpaint` (the painted skin; emissive = the fluorescent paint) and `glow_eyes`.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

RIBS = 10
RX, RY, RZ = 0.24, 0.25, 0.21
SW = 1024
BODY_U = 768 / SW


def skin_uv(u, v):
    return (u * BODY_U * 0.999, v)


def fin_uv(u, v):
    return ((768 + 4 + u * 248) / SW, 0.5 + 0.004 + v * 0.49)


STEM_UV = ((768 + 128) / SW, 0.375)
LIPS_UV = ((768 + 128) / SW, 0.125)


def fan(mb, root, axis_out, axis_up, length, height, mat, lobes=3):
    """A two-sided fin fanning out from `root` along axis_out, spread along axis_up."""
    out = axis_out.normalized()
    up = axis_up.normalized()

    def fn(u, v):
        a = (v - 0.5) * 1.6
        r = 0.02 + u * length * (1 - 0.18 * abs(math.cos(a * lobes * 1.2)))
        return root + (out * math.cos(a) + up * math.sin(a) * height / length) * r
    nrm = out.cross(up)
    lib.grid_patch(mb, fn, 4, 6, uvmap=fin_uv, mat=mat, outward=nrm)
    lib.grid_patch(mb, lambda u, v: fn(u, v) - nrm * 0.004, 4, 6, uvmap=fin_uv, mat=mat, outward=-nrm)


def main():
    lib.reset()
    tex = lib.paint("tex_pufferfish.py", {"ribs": RIBS}, {"skin": "puffer-skin.jpg", "skin_e": "puffer-skin-e.jpg",
                                                           "eye": "puffer-eye.jpg", "eye_e": "puffer-eye-e.jpg"})
    skin = lib.material("glow_uvpaint", base_tex=tex["skin"], emission_tex=tex["skin_e"], roughness=0.5, specular=0.4)
    eyes = lib.material("glow_eyes", base_tex=tex["eye"], emission_tex=tex["eye_e"], roughness=0.2, specular=0.6)
    C = Vector((0, 0, 0))
    kw = dict(ry=RY, ribs=RIBS, groove=0.08, groove_sharp=0.4, top_dimple=0.25, bottom_dimple=0.12, seed=4,
              wobble=0.03)
    point = lib.pumpkin_surface(C, RX, RZ, **kw)
    mb = MB()
    top = lib.pumpkin(mb, C, RX, RZ, nu=RIBS * 4, nv=14, uvmap=skin_uv, mat=0, **kw)
    # stem
    Loft([top - Vector((0, 0, 0.02)), top + Vector((0.005, 0.01, 0.04)), top + Vector((0.02, 0.025, 0.065))],
         lambda t: {"rx": 0.018 * (1 - 0.3 * t), "ry": 0.018 * (1 - 0.3 * t)}, n=6, seg=0.03, frame="rmf",
         up=Vector((1, 0, 0)), cap0="flat", cap1="dome", cap1_len=0.008).build(mb, uvmap=lambda s, a: STEM_UV, mat=0)
    # eyes: big spheres set into the sides, a little forward and up
    eye_mb = MB()
    for u in (0.93, 0.57):
        v = 0.6
        p = point(u, v)
        n = lib.surface_normal(point, u, v)
        d = (n + Vector((0, -0.25, 0.05))).normalized()
        R = d.to_track_quat("-Y", "Z").to_matrix()
        lib.pumpkin(eye_mb, p - n * 0.025, 0.068, 0.068, ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0,
                    nu=14, nv=8, fullness=1.0, M=R, mat=0)
    # lips: a pink ring at the front
    p = point(0.75, 0.42)
    n = lib.surface_normal(point, 0.75, 0.42)
    ring = [p + (Vector((math.cos(a), 0, math.sin(a) * 0.7)) * 0.032) for a in [k * math.tau / 12 for k in range(12)]]
    Loft(ring, lambda t: {"rx": 0.012, "ry": 0.012}, n=5, seg=0.025, closed=True, frame="rmf", up=n).build(
        mb, uvmap=lambda s, a: LIPS_UV, mat=0)
    # spines: short cones over the back and sides
    rng = lib.seeded(9)
    placed = []
    while len(placed) < 34:
        u, v = rng.random(), rng.uniform(0.25, 0.88)
        q = point(u, v)
        if any((q - e).length < 0.06 for e in placed):
            continue
        if (q - point(0.93, 0.6)).length < 0.11 or (q - point(0.57, 0.6)).length < 0.11 or (q - point(0.75, 0.42)).length < 0.08:
            continue
        placed.append(q)
        nn = lib.surface_normal(point, u, v)
        Loft([q - nn * 0.005, q + nn * 0.04], lambda t: {"rx": 0.009 * (1 - t) + 1e-4, "ry": 0.009 * (1 - t) + 1e-4},
             n=4, seg=0.05, frame="up", up=Vector((0, 0, 1)) if abs(nn.z) < 0.9 else Vector((0, 1, 0)),
             cap0="open", cap1="open").build(mb, uvmap=lambda s, a: fin_uv(0.9, 0.5), mat=0)
    body = mb.object("pufferfish", [skin, eyes], origin=(0, 0, 0))
    eye_mb_obj = eye_mb.object("eyes_tmp", [eyes], origin=(0, 0, 0))
    # join the eyes into the body (second material)
    import bpy
    bpy.ops.object.select_all(action="DESELECT")
    eye_mb_obj.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    # tail and side fins
    tmb = MB()
    troot = point(0.25, 0.5) + Vector((0, -0.02, 0))
    fan(tmb, troot, Vector((0, 1, 0.1)), Vector((0, 0, 1)), 0.13, 0.11, 0)
    tail = tmb.object("tail", [skin], origin=troot)
    lib.set_parent(tail, body)
    tris = lib.tri_count(body) + lib.tri_count(tail)
    for name, u in (("fin_R", 0.02), ("fin_L", 0.48)):
        fmb = MB()
        root = point(u, 0.45)
        n = lib.surface_normal(point, u, 0.45)
        fan(fmb, root - n * 0.01, (n * 0.6 + Vector((0, 1, 0))).normalized(), Vector((0, 0, 1)), 0.08, 0.05, 0, lobes=2)
        f = fmb.object(name, [skin], origin=root)
        lib.set_parent(f, body)
        tris += lib.tri_count(f)
    hp = lib.empty("hang_point", top + Vector((0.02, 0.025, 0.07)), size=0.02)
    lib.set_parent(hp, body)
    print(f"  pufferfish: {tris} tris")
    lib.export("pufferfish")


main()
