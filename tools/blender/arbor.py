# SPDX-License-Identifier: MIT
"""The Arbor of Faces (reference/arbor-of-faces.jpg): one bay of the jack-o'-lantern pergola,
plus a rough cedar fence post and a strand of barbed wire.

    blender -b --factory-startup -P tools/blender/arbor.py

Writes public/models/arbor.glb, fence-post.glb and barbed-wire.glb.

arbor        one 4 m bay, the lane running along Blender Y (glTF -Z..+Z: the bay spans
             z = -2..+2 in glTF), 4.6 m between the posts' centres, 3.2 m to the top of the posts.
             Repeat bays end to end every 4 m along the lane. `arbor` (root) holds the posts and
             header at the near end (y = -2), the long beams, braces and the pumpkin wires;
             its child `end_frame` holds the posts and header at the far end (y = +2): show it
             only on the last bay. `hang_points` holds `hang_<wire>_<n>` empties, 0.5 m apart
             along each of the 8 wires, where the pumpkins hang (the instanced pumpkins are not
             modelled). Materials `timber`, `wire`.
fence-post   a rough split cedar post, 1.45 m out of the ground, about 0.13 m thick (`cedar`).
barbed-wire  a 3 m strand along X (x = -1.5..1.5) at z = 0: two twisted wires with four-point
             barbs every 12 cm (`wire`). Place it at the fence's wire heights.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils import noise as mnoise  # noqa: E402

Z = Vector((0, 0, 1))
BAY = 4.0
HALF_W = 2.3          # post centres at x = +-2.3
POST = 0.15
POST_H = 3.2
WIRES_X = [-1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75]


def timber_uv(u0, v0):
    """beam() uv: metres along the beam's local x -> u (2 m per tile), across -> v (0.5 m)."""
    def m(ax, fx, fy):
        if ax == 0:
            return (u0 + fx * 2.0, v0 + fy * 2.0)
        return (u0 + fx / 2.0, v0 + fy / 0.5)
    return m


def weathered_beam(mb, center, size, M=None, seed=0, mat=0):
    rng = lib.seeded(seed)
    lib.beam(mb, center, size, M=M, chamfer=0.008, uv=timber_uv(rng.random(), rng.random()), mat=mat)


def frame_at(mb, y, mat, seed):
    """Two posts and the header across the lane at y."""
    rng = lib.seeded(seed)
    for sx in (-1, 1):
        tilt = Matrix.Rotation(rng.uniform(-0.006, 0.006), 3, "X") @ Matrix.Rotation(rng.uniform(-0.006, 0.006), 3, "Y")
        weathered_beam(mb, (sx * HALF_W, y, POST_H / 2), (POST_H, POST, POST),
                       M=tilt @ Matrix.Rotation(math.pi / 2, 3, "Y"), seed=seed * 10 + sx, mat=mat)
        # knee braces from the post up to the header
        p0 = Vector((sx * (HALF_W - 0.06), y, POST_H - 0.85))
        p1 = Vector((sx * (HALF_W - 0.62), y, POST_H - 0.30))
        mid = (p0 + p1) / 2
        d = (p1 - p0)
        ang = math.atan2(d.z, d.x)
        weathered_beam(mb, mid, (d.length, 0.09, 0.09), M=Matrix.Rotation(-ang, 3, "Y"), seed=seed * 10 + 5 + sx,
                       mat=mat)
    # header: a doubled beam across the lane, bolted to the posts' faces
    for dy in (-0.12, 0.12):
        weathered_beam(mb, (0, y + dy, POST_H - 0.17), (2 * HALF_W + 0.6, 0.06, 0.24), seed=seed * 10 + 8 + int(dy > 0),
                       mat=mat)


def build_arbor(tex):
    lib.reset()
    timber = lib.material("timber", base_tex=tex["timber"], normal_tex=tex["timber_n"], normal_strength=0.8,
                          roughness=0.85, specular=0.3)
    wire = lib.material("wire", color="#3c3a38", roughness=0.5, metallic=0.8)
    mb = MB()
    frame_at(mb, -BAY / 2, 0, 1)
    # long beams on top, along the lane, over the posts (run past the far end to meet the next bay)
    for sx in (-1, 1):
        weathered_beam(mb, (sx * HALF_W, 0, POST_H + 0.12), (BAY, 0.09, 0.24),
                       M=Matrix.Rotation(math.pi / 2, 3, "Z"), seed=20 + sx, mat=0)
    # purlins across the top, carrying the wires
    for k, y in enumerate((-1.0, 0.0, 1.0)):
        weathered_beam(mb, (0, y, POST_H + 0.28), (2 * HALF_W + 0.3, 0.06, 0.09), seed=30 + k, mat=0)
    # the pumpkin wires along the lane, sagging a little between the headers
    hp = []
    for i, x in enumerate(WIRES_X):
        pts = []
        for k in range(17):
            f = k / 16
            y = -BAY / 2 + f * BAY
            pts.append(Vector((x, y, POST_H + 0.20 - 0.05 * 4 * f * (1 - f) * 0)))
        sag = [Vector((p.x, p.y, POST_H + 0.22 - 0.06 * math.sin(math.pi * ((p.y + BAY / 2) % 1.0)))) for p in pts]
        Loft(sag, lambda t: {"rx": 0.003, "ry": 0.003}, n=4, seg=0.25, frame="up", up=Z, cap0="flat",
             cap1="flat").build(mb, uvmap=lambda s, a: (0.5, 0.5), mat=1)
        for n in range(8):
            y = -BAY / 2 + 0.25 + n * 0.5
            z = POST_H + 0.22 - 0.06 * math.sin(math.pi * ((y + BAY / 2) % 1.0))
            hp.append((f"hang_{i}_{n}", Vector((x, y, z))))
    root = mb.object("arbor", [timber, wire], origin=(0, 0, 0), auto_smooth=40)
    end = MB()
    frame_at(end, BAY / 2, 0, 2)
    end_o = end.object("end_frame", [timber], origin=(0, BAY / 2, 0), auto_smooth=40)
    lib.set_parent(end_o, root)
    hroot = lib.empty("hang_points", (0, 0, 0))
    lib.set_parent(hroot, root)
    for name, p in hp:
        e = lib.empty(name, p, size=0.03)
        lib.set_parent(e, hroot)
    print(f"  arbor: {lib.tri_count(root)} + end_frame {lib.tri_count(end_o)} tris, {len(hp)} hang points")
    lib.export("arbor")


def build_fence_post(tex):
    lib.reset()
    cedar = lib.material("cedar", base_tex=tex["cedar"], normal_tex=tex["cedar_n"], normal_strength=1.0,
                         roughness=0.9, specular=0.25)
    mb = MB()
    H = 1.45
    off = Vector((1.3, 2.7, 0.2))

    def rough(t, a, s):
        q = Vector((math.cos(a * math.tau), math.sin(a * math.tau), t * 3.0)) + off
        # split faces: a couple of flattened sides, plus knobbly noise
        flat = -0.012 * max(0.0, math.cos((a - 0.15) * math.tau)) ** 6 - 0.01 * max(0.0, math.cos((a - 0.6) * math.tau)) ** 6
        return 0.012 * mnoise.noise(q * 2.0) + 0.006 * mnoise.noise(q * 6.0) + flat
    pts = [Vector((0, 0, -0.02)), Vector((0.01, 0, H * 0.5)), Vector((-0.012, 0.006, H))]
    Loft(pts, lambda t: {"rx": 0.068 - 0.012 * t, "ry": 0.062 - 0.01 * t}, n=14, seg=0.06, frame="up",
         up=Vector((0, 1, 0)), cap0="flat", cap1="dome", cap1_len=0.025, cap_rings=3, offset=rough).build(
             mb, uvmap=lambda s, a: (a, s * H / 1.6), mat=0)
    o = mb.object("fence-post", [cedar], origin=(0, 0, 0))
    print(f"  fence-post: {lib.tri_count(o)} tris")
    lib.export("fence-post")


def build_barbed_wire():
    lib.reset()
    wire = lib.material("wire", color="#4a4744", roughness=0.45, metallic=0.85)
    mb = MB()
    L = 3.0
    r = 0.0012
    pitch = 0.09
    # a straight core wire and one wire twisted round it read as the usual twisted pair
    Loft([Vector((-L / 2, 0, 0)), Vector((L / 2, 0, 0))], lambda t: {"rx": r, "ry": r}, n=4, seg=L, frame="up", up=Z,
         cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: (0.5, 0.5), mat=0)
    pts = []
    x = -L / 2
    while x <= L / 2 + 1e-6:
        a = (x + L / 2) / pitch * math.tau
        pts.append(Vector((x, 0.0022 * math.cos(a), 0.0022 * math.sin(a))))
        x += pitch / 6
    Loft(pts, lambda t: {"rx": r, "ry": r}, n=3, seg=pitch / 6, frame="rmf", up=Z, cap0="flat", cap1="flat",
         res=2).build(mb, uvmap=lambda s, a: (0.5, 0.5), mat=0)
    rng = lib.seeded(3)
    x = -L / 2 + 0.06
    while x < L / 2 - 0.03:
        # a barb: two short wires wrapped round the strand, their four points sticking out
        a0 = rng.uniform(0, math.pi)
        for j, a in enumerate((a0, a0 + math.pi / 2)):
            d = Vector((0, math.cos(a), math.sin(a)))
            for sgn in (1, -1):
                base = Vector((x + 0.006 * j, 0, 0))
                tip = base + d * (0.017 * sgn) + Vector((0.005, 0, 0))
                Loft([base, tip], lambda t: {"rx": 0.0012 * (1 - t) + 1e-5, "ry": 0.0012 * (1 - t) + 1e-5}, n=3,
                     seg=0.03, frame="up", up=Vector((1, 0, 0)), cap0="open", cap1="open").build(
                         mb, uvmap=lambda s, a: (0.5, 0.5), mat=0)
        x += 0.125
    o = mb.object("barbed-wire", [wire], origin=(0, 0, 0))
    print(f"  barbed-wire: {lib.tri_count(o)} tris")
    lib.export("barbed-wire")


def main():
    lib.reset()
    tex = lib.paint("tex_arbor.py", {}, {"timber": "arbor-timber.jpg", "timber_n": "arbor-timber-n.jpg",
                                         "cedar": "arbor-cedar.jpg", "cedar_n": "arbor-cedar-n.jpg"})
    build_arbor(tex)
    build_fence_post(tex)
    build_barbed_wire()


main()
