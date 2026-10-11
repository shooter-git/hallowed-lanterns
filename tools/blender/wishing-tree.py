# SPDX-License-Identifier: MIT
"""The Wishing Tree of the Marigold Garden (reference/wishing-tree.jpg).

    blender -b --factory-startup -P tools/blender/wishing-tree.py

Writes public/models/wishing-tree.glb.

A flat white tree cut from a 4 cm board (about 5 m wide and 4 m tall, branching like a sea fan),
standing in front of a boxwood hedge wall with a row of pom-poms along its top.

Nodes: `wishing_tree` (root, origin at the foot of the trunk) with children `tree` (the board,
material `board`), `hedge` (6 m x 2.6 m, materials `hedge` (tiling, 1 m per repeat) and `pompom`)
and `leaf_anchors`, whose children `anchor_000`... mark where leaves can go. Each anchor sits on
the front face of a branch at its edge; in glTF its local +X points along the leaf (outward from
the branch, a little toward the branch tip), local +Z out of the board toward the viewer (the
front) and local +Y completes the frame. The leaves themselves are not modelled.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import lib  # noqa: E402
from lib import MB  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils import noise as mnoise  # noqa: E402

THICK = 0.04
HEDGE = dict(x=6.0, y0=0.32, depth=0.6, h=2.6)


def build_board(data, mat):
    x0, x1, z0, z1 = data["box"]
    return lib.extrude_loops(MB(), data["loops"], THICK,
                             lambda x, z: ((x - x0) / (x1 - x0), (z - z0) / (z1 - z0)), mat=mat)


def build_hedge(hedge_mat, pom_mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    hx, hd, hh, y0 = HEDGE["x"], HEDGE["depth"], HEDGE["h"], HEDGE["y0"]
    bmesh.ops.scale(bm, vec=(hx, hd, hh), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, y0 + hd / 2, hh / 2), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges], offset=0.12, segments=3, affect="EDGES", profile=0.5,
                    clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    # subdivide to ~12 cm and puff it up with noise, as a clipped boxwood hedge is
    for _ in range(8):
        long_edges = [e for e in bm.edges if e.calc_length() > 0.32]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    for v in bm.verts:
        if v.co.z < 0.02:
            continue
        n = v.normal
        d = 0.035 * mnoise.noise(v.co * 3.0) + 0.015 * mnoise.noise(v.co * 9.0 + Vector((3, 1, 2)))
        v.co += n * d
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            x, y, z = lp.vert.co
            lp[uvl].uv = (x, z) if ax == 1 else ((y, z) if ax == 0 else (x, y))
    me = bpy.data.meshes.new("hedge")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(hedge_mat)
    me.materials.append(pom_mat)
    for p in me.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new("hedge", me)
    lib.link(obj)
    # pom-poms along the top front edge
    mb = MB()
    rng = lib.seeded(14)
    x = -hx / 2 + 0.15
    while x < hx / 2 - 0.1:
        q = rng.randrange(4)
        r = rng.uniform(0.065, 0.085)
        lib.lump(mb, Vector((x, y0 + 0.03, hh - 0.02)), r, (1, 1, 0.95), seed=int(x * 100), rough=0.3, nu=10, nv=6,
                 mat=1, flat_bottom=False, uvmap=lambda u, v, q=q: ((q + 0.2 + 0.6 * u) / 4, 0.2 + 0.6 * v))
        x += rng.uniform(0.17, 0.24)
    pm = mb.object("pompoms", [hedge_mat, pom_mat])
    # join the pom-poms into the hedge
    bpy.ops.object.select_all(action="DESELECT")
    pm.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    return obj


def main():
    lib.reset()
    out = lib.paint("tex_wishing_tree.py", {"seed": 4, "width": 5.0, "height": 4.0, "max_depth": 7,
                                            "anchor_spacing": 0.16, "tropism": 0.94,
                                            "limbs": [(-1.30, 0.21, 1.30), (-0.66, 0.24, 1.3), (-0.15, 0.25, 1.4),
                                                      (0.28, 0.25, 1.4), (0.78, 0.24, 1.3), (1.33, 0.21, 1.30)]},
                    {"outline": "wishing-tree.json", "board": "wishing-tree-board.jpg", "hedge": "wishing-tree-hedge.jpg",
                     "hedge_n": "wishing-tree-hedge-n.jpg", "pompom": "wishing-tree-pompom.jpg"})
    with open(out["outline"]) as f:
        data = json.load(f)
    board = lib.material("board", base_tex=out["board"], roughness=0.55, specular=0.4)
    hedge = lib.material("hedge", base_tex=out["hedge"], normal_tex=out["hedge_n"], normal_strength=1.0,
                         roughness=0.8, specular=0.35)
    pom = lib.material("pompom", base_tex=out["pompom"], roughness=0.9, specular=0.2)
    root = lib.empty("wishing_tree", (0, 0, 0))
    tree = build_board(data, 0).object("tree", [board], origin=(0, 0, 0), auto_smooth=40)
    lib.set_parent(tree, root)
    h = build_hedge(hedge, pom)
    lib.set_parent(h, root)
    anchors = lib.empty("leaf_anchors", (0, 0, 0))
    lib.set_parent(anchors, root)
    Y = Vector((0, 1, 0))
    for i, (x, z, lx, lz) in enumerate(data["anchors"]):
        L = Vector((lx, 0, lz)).normalized()
        R = Matrix((L, Y, L.cross(Y))).transposed()
        e = lib.empty(f"anchor_{i:03d}", (x, -THICK / 2 - 0.003, z), R.to_euler(), size=0.04)
        lib.set_parent(e, anchors)
    print(f"  wishing-tree: board {lib.tri_count(tree)} tris, hedge {lib.tri_count(h)} tris, "
          f"{len(data['anchors'])} anchors")
    lib.export("wishing-tree")


main()
