# SPDX-License-Identifier: MIT
"""The pumpkin guitar (reference/guitar.jpg): a giant single-cutaway guitar body cut from a
board, faced with dark ivy inside a raised wooden rim, standing on its tail; the six glowing
strings are drawn by the engine.

    blender -b --factory-startup -P tools/blender/guitar.py

Writes public/models/pumpkin-guitar.glb: body 2.6 x 3.2 m, 6.3 m to the top tuning pegs.

Nodes: `guitar` (root: board, ivy face, rim, back struts, bridge, the dark neck rods that carry
the strings and the tuning pegs) with empties
- `pumpkin_spots` -> `spot_00` ...: `spot_00`-`spot_15` the big carved pumpkins inside the body,
  then the small ones round the rim. In glTF each spot's local +Z points out of the face (toward
  the viewer), +Y up; its uniform scale is the suggested pumpkin diameter in metres.
- `string_bottom_0..5` (at the bridge, in front of the ivy), `string_bend_0..5` (where each
  string leaves the straight neck and curves out) and `string_top_0..5` (at its tuning peg).
  Strings 0-2 go to the pegs on the left (-X), 3-5 to the right.

Materials: `guitar_wood` (rim, edges, back, struts), `ivy` (+ normal map), `rods` (dark metal).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector, geometry  # noqa: E402

V = Vector
# the body outline (x, z) in metres, counter-clockwise seen from the front, the cutaway horn
# on the right (+X)
OUTLINE = [(0.0, 0.0), (0.74, 0.08), (1.17, 0.47), (1.29, 1.02), (1.14, 1.55), (0.84, 1.90), (0.80, 2.18),
           (0.92, 2.55), (0.93, 2.90), (0.80, 3.10), (0.63, 3.05), (0.48, 2.86), (0.30, 2.78), (0.18, 2.88),
           (0.12, 3.05), (-0.06, 3.16), (-0.33, 3.21), (-0.60, 3.14), (-0.82, 2.93), (-0.90, 2.60),
           (-0.82, 2.22), (-0.82, 1.90), (-1.12, 1.55), (-1.27, 1.02), (-1.16, 0.47), (-0.74, 0.08)]
FACE_Y = -0.03          # the ivy face
BACK_Y = 0.05
RIM_W, RIM_H = 0.11, 0.16
STRING_X = [-0.175 + 0.07 * i for i in range(6)]
BRIDGE_Z = 1.22
BEND_Z = 4.95
PEGS = [(-0.34, 6.22), (-0.33, 5.97), (-0.32, 5.72), (0.32, 5.72), (0.33, 5.97), (0.34, 6.22)]


def smooth_outline(pts, n=160):
    path = lib.Path([V((x, 0, z)) for x, z in pts], closed=True, res=24)
    return [(p.x, p.z) for p in (path.at(path.L * i / n) for i in range(n))]


def offset_poly(pts, d):
    """Moves every vertex of a counter-clockwise polygon inward by d."""
    out = []
    n = len(pts)
    for i in range(n):
        x0, z0 = pts[i - 1]
        x1, z1 = pts[i]
        x2, z2 = pts[(i + 1) % n]
        t = V((x2 - x0, z2 - z0, 0)).normalized()
        inward = V((-t.y, t.x, 0))        # left of the direction of travel = inside for CCW
        out.append((x1 + inward.x * d, z1 + inward.y * d))
    return out


def fill(mb, poly, y, uv, mat, front=True):
    vec = [V((x, z, 0)) for x, z in poly]
    tris = geometry.tessellate_polygon([vec])
    ids = [mb.v((x, y, z)) for x, z in poly]
    for a, b, c in tris:
        pa, pb, pc = poly[a], poly[b], poly[c]
        cr = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        tri = (a, b, c) if (cr > 0) == front else (a, c, b)
        mb.f([ids[k] for k in tri], [uv(*poly[k]) for k in tri], None, mat)


def band(mb, poly, y0, y1, uv_len, mat, outward=True):
    """Connects the polygon at y0 to y1 (a wall along its edge)."""
    n = len(poly)
    a = [mb.v((x, y0, z)) for x, z in poly]
    b = [mb.v((x, y1, z)) for x, z in poly]
    s = 0.0
    for i in range(n):
        j = (i + 1) % n
        ln = math.dist(poly[i], poly[j])
        q = [a[i], a[j], b[j], b[i]]
        uv = [(s, 0.1), (s + ln, 0.1), (s + ln, 0.2), (s, 0.2)]
        uv = [(u / 2.0, v) for u, v in uv]
        if not outward:
            q, uv = q[::-1], uv[::-1]
        mb.f(q, uv, None, mat)
        s += ln


def spot_matrix(p, size):
    # the board faces -Y (glTF +Z) and stands upright, so the spots keep the model's own axes:
    # glTF +Z out of the face, +Y up
    return Matrix.Translation(p) @ Matrix.Scale(size, 4)


def main():
    lib.reset()
    wc = lib.paint_named("tex_wood.py", dict(size=1024, rows=8, tile_m=2.0, base=["#6a4a30", "#5c4029", "#76543a"], seed=91,
                                       grain=0.7, groove=0.6, wear=0.06, dirt=0.3, knots=1, joints=1, nails=True),
                   {"color": "guitar-wood.jpg", "normal": "guitar-wood-n.jpg"})
    ivy = lib.paint_named("tex_owl.py", {"kind": "ivy", "seed": 7}, {"color": "owl-ivy.jpg", "normal": "owl-ivy-n.jpg"})
    m_wood = lib.material("guitar_wood", base_tex=wc["color"], normal_tex=wc["normal"], roughness=0.8, specular=0.3)
    m_ivy = lib.material("ivy", base_tex=ivy["color"], normal_tex=ivy["normal"], roughness=0.7, specular=0.3)
    m_rod = lib.material("rods", color="#141416", roughness=0.45, metallic=0.6)
    mb = MB()
    outer = smooth_outline(OUTLINE)
    inner = offset_poly(outer, RIM_W)
    # the board: ivy face inside the rim, wood back and edge
    fill(mb, inner, FACE_Y, lambda x, z: (x * 0.9, z * 0.9), 1, front=True)
    fill(mb, outer, BACK_Y, lambda x, z: (x * 0.5, z * 0.5), 0, front=False)
    # the rim: a raised wooden lip round the edge
    y_rim = FACE_Y - RIM_H
    ids_o = [mb.v((x, y_rim, z)) for x, z in outer]
    ids_i = [mb.v((x, y_rim, z)) for x, z in inner]
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        q = [ids_o[i], ids_o[j], ids_i[j], ids_i[i]]
        uv = [(outer[i][0] * 0.5, outer[i][1] * 0.5), (outer[j][0] * 0.5, outer[j][1] * 0.5),
              (inner[j][0] * 0.5, inner[j][1] * 0.5), (inner[i][0] * 0.5, inner[i][1] * 0.5)]
        mb.f(q, uv, None, 0)    # faces -Y (front) for a CCW outline seen from the front
    band(mb, outer, BACK_Y, y_rim, 1.0, 0, outward=True)
    band(mb, inner, y_rim, FACE_Y, 1.0, 0, outward=False)
    # back struts propping it up
    for sx in (-0.55, 0.55):
        top = V((sx, BACK_Y + 0.04, 2.1))
        foot = V((sx * 1.1, 1.25, 0.0))
        d = (top - foot).normalized()
        yb = d.cross(V((0, 0, 1))).normalized()
        zb = d.cross(yb)
        lib.beam(mb, (top + foot) / 2, ((top - foot).length, 0.09, 0.06), M=Matrix((d, yb, zb)).transposed(),
                 chamfer=0.006, uv=lambda ax, x, y: (x * 0.5, 0.3 + y))
    # bridge: a dark bar across the strings' feet
    lib.beam(mb, (0, FACE_Y - 0.06, BRIDGE_Z - 0.04), (0.55, 0.08, 0.07), chamfer=0.01, uv=lambda ax, x, y: (x, y), mat=2)
    # the neck: dark rods behind each string, splaying to the pegs; peg discs at the ends
    for i, x in enumerate(STRING_X):
        px, pz = PEGS[i]
        pts = [V((x, FACE_Y - 0.05, 3.0)), V((x, FACE_Y - 0.05, BEND_Z - 0.3)), V((x, FACE_Y - 0.05, BEND_Z)),
               V((x + (px - x) * 0.45, FACE_Y - 0.05, BEND_Z + (pz - BEND_Z) * 0.45)), V((px, FACE_Y - 0.05, pz))]
        Loft(pts, lambda t: {"rx": 0.014, "ry": 0.014}, n=6, seg=0.15, frame="up", up=V((0, -1, 0)),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: (s, a), mat=2)
        Loft([V((px, FACE_Y - 0.09, pz)), V((px, FACE_Y + 0.0, pz))], lambda t: {"rx": 0.045, "ry": 0.045}, n=10,
             seg=0.1, frame="up", up=V((0, 0, 1)), cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: (s, a), mat=2)
    # two flat bars tie the rods into a neck
    for z in (3.4, 4.2):
        lib.beam(mb, (0, FACE_Y - 0.03, z), (0.42, 0.03, 0.05), chamfer=0.004, uv=lambda ax, x, y: (x, y), mat=2)
    root = mb.object("guitar", [m_wood, m_ivy, m_rod], origin=(0, 0, 0), auto_smooth=40)
    # spots: 16 big ones inside (two columns either side of the strings), then the small ones
    # round the rim
    spots = lib.empty("pumpkin_spots", parent=root)
    k = 0
    big = []
    for z, xs in ((0.55, (-0.62, -0.20, 0.22, 0.64)), (1.02, (-0.80, -0.36, 0.40, 0.84)), (1.55, (-0.68, -0.32, 0.34, 0.70)),
                  (2.15, (-0.46, 0.46)), (2.62, (-0.48, 0.52))):
        for x in xs:
            big.append((x, z))
    for x, z in big:
        e = lib.empty(f"spot_{k:02d}", parent=spots)
        e.matrix_world = spot_matrix(V((x, FACE_Y - 0.18, z)), 0.42)
        k += 1
    ring = offset_poly(outer, RIM_W + 0.14)
    path = lib.Path([V((x, 0, z)) for x, z in ring], closed=True, res=8)
    n_small = 40
    for i in range(n_small):
        p = path.at(path.L * (i + 0.5) / n_small)
        if abs(p.x) < 0.25 and p.z > 2.7:
            continue        # leave the neck join clear
        e = lib.empty(f"spot_{k:02d}", parent=spots)
        e.matrix_world = spot_matrix(V((p.x, FACE_Y - 0.13, p.z)), 0.26)
        k += 1
    for i, x in enumerate(STRING_X):
        px, pz = PEGS[i]
        lib.empty(f"string_bottom_{i}", location=(x, FACE_Y - 0.11, BRIDGE_Z), parent=root)
        lib.empty(f"string_bend_{i}", location=(x, FACE_Y - 0.11, BEND_Z), parent=root)
        lib.empty(f"string_top_{i}", location=(px, FACE_Y - 0.11, pz), parent=root)
    print(f"  pumpkin-guitar: {lib.tri_count(root)} tris, {k} spots")
    lib.export("pumpkin-guitar")


if __name__ == "__main__":
    main()
