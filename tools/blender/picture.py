# SPDX-License-Identifier: MIT
"""The picture show in the clearing (reference/movie-clearing.jpg): the projection screen on its
silver box truss, the white folding benches and the low stage of hay bales in front of the
screen.

    blender -b --factory-startup -P tools/blender/picture.py [-- only=screen,bench,stage]

Writes public/models/movie-screen.glb, bench.glb and hay-stage.glb.

- movie-screen: a 6 x 3.6 m screen (bottom edge 0.55 m up) stretched in a frame of 290 mm
  aluminium box truss: two towers, a top span, base plates and raked back props. The screen is
  its own node `screen` (one quad grid; UV 0..1 across it: u left -> right and v bottom -> top as
  seen from the front; material `screen`, plain white: the film is drawn by the engine).
  Root `movie_screen` (truss, material `truss`).
- bench: a white plastic folding bench, 1.83 m long, seat 0.43 m high, on folding steel legs
  (`plastic_white`, `steel`).
- hay-stage: a row of small square bales two deep (the back row stacked two high), 4.8 m wide
  (`hay`: the same hay texture as hay-bale.glb, painted by tex_lounge.py).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils import noise as mnoise  # noqa: E402

ARGS = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
ONLY = set(ARGS["only"].split(",")) if "only" in ARGS else None
V = Vector


def pipe(mb, a, b, r, mat, n=6, caps=("flat", "flat")):
    a, b = V(a), V(b)
    d = (b - a).normalized()
    up = V((0, 0, 1)) if abs(d.z) < 0.9 else V((1, 0, 0))
    Loft([a, b], lambda t: {"rx": r, "ry": r}, n=n, seg=max((b - a).length, 0.05), frame="up", up=up,
         cap0=caps[0], cap1=caps[1]).build(mb, uvmap=lambda s, t: (s, t), mat=mat)


# --------------------------------------------------------------------------------------------
# Movie screen
# --------------------------------------------------------------------------------------------

TW = 0.29          # truss width (chord centres)
CHORD_R, LACE_R = 0.024, 0.008
SCREEN_W, SCREEN_H, SCREEN_Z0 = 6.0, 3.6, 0.55
TOWER_X = 3.20
TOWER_H = 4.55


def box_truss(mb, a, b, mat, ref_up=V((0, 0, 1)), bay=0.30):
    """A square box truss from a to b: four chords and zigzag lacing on every face."""
    a, b = V(a), V(b)
    d = (b - a)
    L = d.length
    d.normalize()
    u = ref_up - d * d.dot(ref_up)
    if u.length < 1e-6:
        u = V((0, 1, 0)) - d * d.y
    u.normalize()
    w = d.cross(u)
    h = TW / 2
    corners = [u * h + w * h, -u * h + w * h, -u * h - w * h, u * h - w * h]
    for c in corners:
        pipe(mb, a + c, b + c, CHORD_R, mat, n=6)
    n = max(1, int(round(L / bay)))
    for k in range(4):
        c0, c1 = corners[k], corners[(k + 1) % 4]
        for i in range(n):
            p0 = a + d * (L * i / n) + (c0 if i % 2 == 0 else c1)
            p1 = a + d * (L * (i + 1) / n) + (c1 if i % 2 == 0 else c0)
            pipe(mb, p0, p1, LACE_R, mat, n=4)
    # end frames
    for p in (a, b):
        for k in range(4):
            pipe(mb, p + corners[k], p + corners[(k + 1) % 4], LACE_R * 1.3, mat, n=4)


def build_screen():
    lib.reset()
    m_truss = lib.material("truss", color="#c9ccd2", roughness=0.32, metallic=0.9, specular=0.5)
    m_screen = lib.material("screen", color="#f4f4f2", roughness=0.9, specular=0.2)
    mb = MB()
    yb = 0.0
    for sx in (-1, 1):
        x = sx * TOWER_X
        box_truss(mb, (x, yb, 0.02), (x, yb, TOWER_H - TW / 2), 0, ref_up=V((0, -1, 0)))
        lib.beam(mb, (x, yb, 0.01), (0.6, 0.6, 0.02), chamfer=0.003, uv=lambda ax, a, b: (a, b))     # base plate
        # raked back prop: a pipe from high on the tower to a ground plate behind
        top = V((x, yb + TW / 2, 3.2))
        foot = V((x + sx * 0.3, yb + 1.9, 0.02))
        pipe(mb, top, foot, 0.03, 0, n=8)
        lib.beam(mb, foot + V((0, 0, -0.005)), (0.3, 0.3, 0.02), chamfer=0.003, uv=lambda ax, a, b: (a, b))
    box_truss(mb, (-TOWER_X - TW / 2, yb, TOWER_H), (TOWER_X + TW / 2, yb, TOWER_H), 0, ref_up=V((0, 0, 1)))
    # the screen's bottom tension bar and side bungee bars
    zb = SCREEN_Z0 - 0.04
    pipe(mb, (-SCREEN_W / 2 - 0.05, yb - TW / 2 - 0.04, zb), (SCREEN_W / 2 + 0.05, yb - TW / 2 - 0.04, zb), 0.022, 0, n=8)
    for sx in (-1, 1):
        for z in (SCREEN_Z0 + 0.5, SCREEN_Z0 + 1.6, SCREEN_Z0 + 2.7):
            pipe(mb, (sx * SCREEN_W / 2, yb - TW / 2 - 0.035, z), (sx * (TOWER_X - TW / 2), yb - TW / 2, z), 0.006, 0, n=4)
    root = mb.object("movie_screen", [m_truss], origin=(0, 0, 0))
    # the screen: a slightly slack quad grid, UV 0..1 left->right, bottom->top
    sm = MB()
    ys = yb - TW / 2 - 0.035

    def fn(u, v):
        sag = 0.012 * math.sin(math.pi * u) * math.sin(math.pi * v)
        return V((-SCREEN_W / 2 + SCREEN_W * u, ys + sag, SCREEN_Z0 + SCREEN_H * v))
    lib.grid_patch(sm, fn, 12, 8, uvmap=lambda u, v: (u, v), mat=0, outward=V((0, -1, 0)))
    screen = sm.object("screen", [m_screen], origin=(0, ys, SCREEN_Z0 + SCREEN_H / 2))
    lib.set_parent(screen, root)
    print(f"  movie-screen: {lib.tri_count(root) + lib.tri_count(screen)} tris")
    return lib.export("movie-screen")


# --------------------------------------------------------------------------------------------
# Folding bench
# --------------------------------------------------------------------------------------------

def build_bench():
    lib.reset()
    m_pl = lib.material("plastic_white", color="#ecebe6", roughness=0.45, specular=0.5)
    m_st = lib.material("steel", color="#3a3c40", roughness=0.4, metallic=0.8)
    mb = MB()
    L, W, T, H = 1.83, 0.28, 0.045, 0.43
    lib.beam(mb, (0, 0, H - T / 2), (L, W, T), chamfer=0.012, uv=lambda ax, a, b: (a, b), mat=0)
    # the moulded lip under the seat's edge
    for sy in (-1, 1):
        lib.beam(mb, (0, sy * (W / 2 - 0.012), H - T - 0.02), (L - 0.04, 0.02, 0.04), chamfer=0.005,
                 uv=lambda ax, a, b: (a, b), mat=0)
    for sx in (-1, 1):
        lib.beam(mb, (sx * (L / 2 - 0.012), 0, H - T - 0.02), (0.02, W - 0.04, 0.04), chamfer=0.005,
                 uv=lambda ax, a, b: (a, b), mat=0)
    # legs: at each end a splayed U frame, a foot bar, and a folding brace to the middle
    for sx in (-1, 1):
        xt, xb = sx * (L / 2 - 0.22), sx * (L / 2 - 0.08)
        for sy in (-1, 1):
            pipe(mb, (xt, sy * 0.10, H - T), (xb, sy * 0.115, 0.015), 0.0125, 1, n=8)
            pipe(mb, (xb, sy * 0.115, 0.03), (xb, sy * 0.115, 0.0), 0.017, 1, n=8)     # rubber foot
        pipe(mb, (xt, -0.10, H - T - 0.01), (xt, 0.10, H - T - 0.01), 0.0125, 1, n=8)
        pipe(mb, (xb * 0.985, -0.115, 0.07), (xb * 0.985, 0.115, 0.07), 0.011, 1, n=8)
        mid = (xt + xb) / 2
        pipe(mb, (mid, 0, 0.24), (sx * 0.28, 0, H - T - 0.01), 0.009, 1, n=6)
        pipe(mb, (mid, -0.11, 0.24), (mid, 0.11, 0.24), 0.008, 1, n=6)
    obj = mb.object("bench", [m_pl, m_st], origin=(0, 0, 0), auto_smooth=40)
    print(f"  bench: {lib.tri_count(obj)} tris")
    return lib.export("bench")


# --------------------------------------------------------------------------------------------
# Hay stage
# --------------------------------------------------------------------------------------------

BALE = (0.92, 0.46, 0.36)


def bale(mb, center, rot_z=0.0, seed=0, mat=0):
    """A small square bale (as hay-bale.glb: the same UV layout on the shared hay texture), lighter."""
    L, D, H = BALE
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(L, D, H), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.045, segments=2, affect="EDGES", profile=0.5, clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for _ in range(1):
        e = [e for e in bm.edges if e.calc_length() > 0.30]
        if not e:
            break
        bmesh.ops.subdivide_edges(bm, edges=e, cuts=1)
        bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")
    kx = 0.92 * 960 / 1024
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            x, y, z = lp.vert.co
            if ax == 0:
                lp[uvl].uv = (0.04 + (y / D + 0.5) * 0.4, 0.5 + z)
            elif ax == 1:
                lp[uvl].uv = ((x / L + 0.5) * kx, 0.5 + z * 0.9)
            else:
                lp[uvl].uv = ((x / L + 0.5) * kx, 0.05 + (y / D + 0.5) * 0.4)
    off = V((seed * 3.1, seed * 1.7, 0.3))
    for v in bm.verts:
        d = 0.012 * mnoise.noise(v.co * 7 + off) + 0.006 * mnoise.noise(v.co * 19 + off)
        v.co += v.normal * d
    R = Matrix.Rotation(rot_z, 3, "Z")
    C = V(center)
    base = len(mb.verts)
    bm.verts.index_update()
    for v in bm.verts:
        mb.v(C + R @ v.co)
    for f in bm.faces:
        mb.f([base + v.index for v in f.verts], [tuple(l[uvl].uv) for l in f.loops], None, mat)
    bm.free()
    for tx in (-0.24, 0.26):
        pts = []
        for k in range(16):
            a = math.tau * k / 16
            cy, cz = math.cos(a), math.sin(a)
            yy = math.copysign(abs(cy) ** 0.25, cy) * (D / 2 + 0.006)
            zz = math.copysign(abs(cz) ** 0.25, cz) * (H / 2 + 0.006)
            pts.append(C + R @ V((tx, yy, zz)))
        Loft(pts, lambda t: {"rx": 0.004, "ry": 0.004}, n=3, seg=0.08, closed=True, frame="rmf", up=R @ V((1, 0, 0))
             ).build(mb, uvmap=lambda s, a: (0.97, s), mat=mat)


def build_stage():
    lib.reset()
    # the hay texture shared with hay-bale.glb (painted by the first modeller's tex_lounge.py)
    tex = lib.paint("tex_lounge.py", {"lantern_ribs": 16},
                    {"wood": "lounge-wood.jpg", "hay": "lounge-hay.jpg", "hay_n": "lounge-hay-n.jpg",
                     "throw": "lounge-throw.jpg", "reed": "lounge-reed.png", "lantern": "lounge-lantern.jpg",
                     "lantern_e": "lounge-lantern-e.jpg"})
    m_hay = lib.material("hay", base_tex=tex["hay"], normal_tex=tex["hay_n"], normal_strength=1.0, roughness=0.9,
                         specular=0.3)
    rng = lib.seeded(31)
    mb = MB()
    L, D, H = BALE
    k = 0
    # back row, two high (brick-bonded); front row one high
    for layer, (y, xs) in enumerate(((0.24, [-2.0, -1.0, 0.0, 1.0, 2.0]), (0.24, [-1.5, -0.5, 0.5, 1.5]),
                                     (-0.24, [-2.0, -1.0, 0.0, 1.0, 2.0]))):
        z = H / 2 + (H if layer == 1 else 0.0)
        for x in xs:
            bale(mb, (x * 0.96 + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), z),
                 rot_z=rng.uniform(-0.04, 0.04), seed=k, mat=0)
            k += 1
    # two odd bales at the right end, turned across, as in the clearing
    bale(mb, (2.62, 0.05, H / 2), rot_z=math.pi / 2 + 0.05, seed=k, mat=0)
    bale(mb, (2.60, 0.05, H * 1.5), rot_z=math.pi / 2 - 0.08, seed=k + 1, mat=0)
    xs_, ys_ = [v[0] for v in mb.verts], [v[1] for v in mb.verts]
    mb.transform(Matrix.Translation((-(min(xs_) + max(xs_)) / 2, -(min(ys_) + max(ys_)) / 2, 0)))   # footprint centre
    obj = mb.object("hay_stage", [m_hay], origin=(0, 0, 0), auto_smooth=50)
    print(f"  hay-stage: {lib.tri_count(obj)} tris, {k + 2} bales")
    return lib.export("hay-stage")


def main():
    for key, fn in (("screen", build_screen), ("bench", build_bench), ("stage", build_stage)):
        if ONLY is None or key in ONLY:
            fn()


if __name__ == "__main__":
    main()
