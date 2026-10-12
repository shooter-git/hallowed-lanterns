# SPDX-License-Identifier: MIT
"""The magical well of the Candle Grove (reference/video-magic-well.mov): a round fieldstone
well with a capstone rim, two rough posts wound with ivy under a little shingled roof, a
windlass with a coil of rope and a crank, the rope hanging into a shaft lit red from below.

    blender -b --factory-startup -P tools/blender/magic-well.py

Writes public/models/magic-well.glb: 1.3 m across the stones (2.0 m with the roof), the wall
0.85 m high, the roof ridge 2.5 m.

Nodes: `magic_well` (root: wall, capstones, shaft, posts, roof, hanging rope, ivy) with
- `windlass` (the drum, its axle and the coiled rope) and `crank` (the handle on the +X end):
  both pivot on the axle, which runs left-right along X at 1.55 m (crank pivot glTF (0.82, 1.55,
  0), windlass (0, 1.55, 0)): turn them about their local X (three.js rotation.x) together.
- `fog_source`: empty at the shaft's centre 0.3 m below the rim (the engine pours fog from it).
- `coin_drop`: empty 0.45 m above the middle of the opening.

Materials: `stone` (+ normal map), `wood` (+ normal map), `shingle`, `ivy` (alpha MASK,
double-sided), `rope`, `glow_well_inner` (the shaft: red emission strongest just under the rim).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils import noise as mn  # noqa: E402

V = Vector
R_FACE = 0.63          # outer face of the wall stones
R_CORE = 0.585         # the mortar core behind them
R_IN = 0.40            # the shaft
RIM_Z = 0.85
CAP_H = 0.13
SHAFT_Z0 = 0.02        # the shaft's floor (the fog hides it; nothing goes below the ground)
AXLE_Z = 1.55
POST_X = 0.72
EAVE_Z, RIDGE_Z = 2.06, 2.47
ROOF_HX, ROOF_HY = 0.95, 0.68


def rock(mb, c, half, M, mat, uvm, seed, e1=0.45, e2=0.45, nu=10, nv=6, rough=0.10):
    """A rounded block: a superellipsoid (half sizes along M's x, y, z) with noisy lumps."""
    off = V((seed * 1.31, seed * 0.77, seed * 2.03))
    R = M.to_3x3() if hasattr(M, "to_3x3") else M

    def sp(a, e):
        return math.copysign(abs(a) ** e, a)

    def pt(u, v):
        th, ph = math.tau * u, math.pi * (v - 0.5)
        cx, sx = math.cos(th), math.sin(th)
        cp, spp = math.cos(ph), math.sin(ph)
        d = V((sp(cp, e1) * sp(cx, e2), sp(cp, e1) * sp(sx, e2), sp(spp, e1)))
        n = V((d.x / half[0], d.y / half[1], d.z / half[2]))
        p = V((d.x * half[0], d.y * half[1], d.z * half[2]))
        k = 1 + rough * mn.noise(p * 6 + off) + 0.5 * rough * mn.noise(p * 15 + off)
        return c + R @ (p * k)
    rows = []
    for j in range(nv + 1):
        v = j / nv
        if j in (0, nv):
            rows.append([mb.v(pt(0, v))])
        else:
            rows.append([mb.v(pt(i / nu, v)) for i in range(nu)])
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            u0, u1, v0, v1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
            if j == 0:
                mb.f((rows[0][0], rows[1][i2], rows[1][i]), [uvm(u0, v0), uvm(u1, v1), uvm(u0, v1)], None, mat)
            elif j == nv - 1:
                mb.f((rows[j][i], rows[j][i2], rows[nv][0]), [uvm(u0, v0), uvm(u1, v0), uvm(u0, v1)], None, mat)
            else:
                mb.f((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]),
                     [uvm(u0, v0), uvm(u1, v0), uvm(u1, v1), uvm(u0, v1)], None, mat)


def stone_uv(rng):
    ou, ov = rng.random(), rng.random() * 0.35

    def m(u, v):
        return ((ou + u * 0.6) % 1.0, 1 - (ov + v * 0.4) * 0.75)
    return m


def frame_at(theta, z):
    """Tangent (x), outward (y), up (z) at angle theta round the well (right-handed)."""
    out = V((math.cos(theta), math.sin(theta), 0))
    tan = V((math.sin(theta), -math.cos(theta), 0))
    return Matrix((tan, out, V((0, 0, 1)))).transposed()


def cylinder(mb, r, z0, z1, n, mat, uvm, inward=False, cap_bottom=False):
    rings = []
    for z in (z0, z1):
        rings.append([mb.v((r * math.cos(math.tau * i / n), r * math.sin(math.tau * i / n), z)) for i in range(n)])
    for i in range(n):
        j = (i + 1) % n
        q = [rings[0][i], rings[0][j], rings[1][j], rings[1][i]]
        uv = [uvm(i / n, 0), uvm((i + 1) / n, 0), uvm((i + 1) / n, 1), uvm(i / n, 1)]
        if inward:
            q, uv = q[::-1], uv[::-1]
        mb.f(q, uv, None, mat)
    if cap_bottom:
        c = mb.v((0, 0, z0))
        for i in range(n):
            j = (i + 1) % n
            tri = (c, rings[0][j], rings[0][i])
            if inward:
                tri = (c, rings[0][i], rings[0][j])
            mb.f(tri, [uvm(0.5, 0.0)] * 3, None, mat)


def wood_row(row, rows=8, tile=2.0):
    def m(s, a):
        return (s / tile, 1 - (row + 0.05 + 0.9 * (a % 1.0)) / rows)
    return m


def rough_post(mb, a, b, r, mat, row, seed):
    off = V((seed * 3.1, 0.7, seed))

    def wob(t, a_, s):
        return 0.012 * mn.noise(V((t * 6, a_ * 4, 0)) + off)
    L = (V(b) - V(a)).length
    Loft([V(a), V(a).lerp(V(b), 0.5) + V((0.01, 0.0, 0)), V(b)], lambda t: {"rx": r, "ry": r * 0.92, "p": 3.0},
         n=8, seg=0.12, frame="up", up=V((0, -1, 0.0001)) if abs((V(b) - V(a)).normalized().z) > 0.9 else V((0, 0, 1)),
         cap0="flat", cap1="flat", offset=wob).build(mb, uvmap=lambda s, a_: wood_row(row)(s * L, a_), mat=mat)


def ivy_leaf(mb, p, n, up, size, mat, rng):
    """One ivy-leaf card at p facing n (alpha cut-out), its tip roughly along `up`."""
    n = n.normalized()
    t = (up - n * up.dot(n))
    t = t.normalized() if t.length > 1e-6 else V((0, 0, 1))
    ang = rng.uniform(-0.7, 0.7)
    t = (t * math.cos(ang) + n.cross(t) * math.sin(ang)).normalized()
    s = t.cross(n)
    h = size / 2
    q = [p - s * h - t * h * 0.6, p + s * h - t * h * 0.6, p + s * h + t * h * 1.4, p - s * h + t * h * 1.4]
    ids = [mb.v(x + n * 0.006) for x in q]
    mb.f(ids, [(0, 0), (1, 0), (1, 1), (0, 1)], None, mat)


def main():
    lib.reset()
    st = lib.paint_named("tex_well.py", {"kind": "stone"}, {"color": "well-stone.jpg", "normal": "well-stone-n.jpg"})
    inner = lib.paint_named("tex_well.py", {"kind": "inner", "depth": RIM_Z - 0.05 - SHAFT_Z0}, {"base": "well-inner.jpg", "emit": "well-inner-e.jpg"})
    rope_t = lib.paint_named("tex_well.py", {"kind": "rope"}, {"tex": "well-rope.jpg"})["tex"]
    ivy_t = lib.paint_named("tex_well.py", {"kind": "ivy", "color": "#3a6a30", "dark": "#1a3a18", "vein": "#a8c090"},
                            {"tex": "well-ivy.png"})["tex"]
    wood = lib.paint_named("tex_wood.py", dict(size=1024, rows=8, tile_m=2.0, base=["#4a3a2c", "#3e3226", "#55432f"],
                                               seed=101, grain=0.8, groove=0.5, wear=0.05, dirt=0.4, knots=1, joints=0,
                                               nails=False), {"color": "well-wood.jpg", "normal": "well-wood-n.jpg"})
    shing = lib.paint_named("tex_wood.py", dict(size=512, rows=8, tile_m=1.0, base=["#5a4a3a", "#4a3e32", "#66523e", "#3e342a"],
                                                seed=102, grain=0.9, groove=0.8, wear=0.08, dirt=0.5, knots=0, joints=2,
                                                nails=False), {"color": "well-shingle.jpg"})
    m_stone = lib.material("stone", base_tex=st["color"], normal_tex=st["normal"], normal_strength=0.6, roughness=0.9,
                           specular=0.25)
    m_wood = lib.material("wood", base_tex=wood["color"], normal_tex=wood["normal"], roughness=0.85, specular=0.25)
    m_shing = lib.material("shingle", base_tex=shing["color"], roughness=0.9, specular=0.2)
    m_ivy = lib.material("ivy", base_tex=ivy_t, roughness=0.7, specular=0.3, alpha_clip=0.5, double_sided=True)
    m_rope = lib.material("rope", base_tex=rope_t, roughness=0.95, specular=0.2)
    m_glow = lib.material("glow_well_inner", base_tex=inner["base"], emission_tex=inner["emit"], roughness=0.9,
                          specular=0.2)
    STONE, WOOD, SHING, IVY, ROPE, GLOW = range(6)
    rng = lib.seeded(17)
    mb = MB()
    # the wall: the mortar core, five courses of fieldstones, the capstones
    cylinder(mb, R_CORE, 0.0, RIM_Z - CAP_H + 0.02, 40, STONE, lambda u, v: (u * 4, 0.24 * v * 0.3 + 0.01))
    courses = 4
    zc = (RIM_Z - CAP_H) / courses
    seed = 0
    for k in range(courses):
        z = zc * (k + 0.5)
        n = 11 + (k % 2)
        ph = rng.uniform(0, 1) / n
        widths = [rng.uniform(0.7, 1.3) for _ in range(n)]
        tot = sum(widths)
        a = ph * math.tau
        for w in widths:
            span = math.tau * w / tot
            th = a + span / 2
            a += span
            arc = span * R_FACE
            hz = zc * 0.5 * rng.uniform(0.88, 1.06)
            half = (arc * 0.5 * rng.uniform(0.92, 1.0), 0.085, hz)
            c = V((math.cos(th), math.sin(th), 0)) * (R_FACE - 0.07 + rng.uniform(-0.01, 0.012)) + \
                V((0, 0, max(z + rng.uniform(-0.018, 0.018), hz * 0.8)))
            M = frame_at(th, z) @ Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "Y")
            rock(mb, c, half, M, STONE, stone_uv(rng), seed, e1=0.62, e2=0.62, nu=12, nv=7, rough=0.13)
            seed += 1
    ncap = 10
    for i in range(ncap):
        th = math.tau * (i + 0.5) / ncap + 0.05
        rm = (R_IN + R_FACE + 0.02) / 2
        arc = math.tau / ncap * rm
        c = V((math.cos(th) * rm, math.sin(th) * rm, RIM_Z - CAP_H / 2))
        half = (arc * 0.5 * 0.95, (R_FACE + 0.03 - R_IN + 0.02) / 2, CAP_H / 2)
        rock(mb, c, half, frame_at(th, 0), STONE, stone_uv(rng), seed, e1=0.30, e2=0.30, nu=14, nv=8, rough=0.06)
        seed += 1
    # the shaft: lit red under the rim, dark below
    cylinder(mb, R_IN, SHAFT_Z0, RIM_Z - 0.05, 36, GLOW, lambda u, v: (u, v), inward=True, cap_bottom=True)
    # posts, roof frame and shingles
    for sx in (-1, 1):
        rough_post(mb, (sx * POST_X, 0, 0.0), (sx * POST_X, 0, RIDGE_Z - 0.05), 0.055, WOOD, 2 + (sx > 0), sx + 3)
    rough_post(mb, (-ROOF_HX, 0, RIDGE_Z - 0.02), (ROOF_HX, 0, RIDGE_Z - 0.02), 0.05, WOOD, 4, 7)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rough_post(mb, (sx * (POST_X + 0.06), 0, RIDGE_Z), (sx * (POST_X + 0.06), sy * ROOF_HY, EAVE_Z), 0.035, WOOD, 5, 9)
        rough_post(mb, (sx * POST_X, -0.03, 1.95), (sx * POST_X, 0.03, 1.95), 0.03, WOOD, 6, 11)
    for sy in (-1, 1):
        rough_post(mb, (-ROOF_HX, sy * (ROOF_HY - 0.04), EAVE_Z + 0.02), (ROOF_HX, sy * (ROOF_HY - 0.04), EAVE_Z + 0.02),
                   0.03, WOOD, 1, 13)
    slope = V((0, ROOF_HY, EAVE_Z - RIDGE_Z))
    sl = slope.length
    rows = 6
    for sy in (-1, 1):
        dn = V((0, sy * ROOF_HY, EAVE_Z - RIDGE_Z)).normalized()
        nrm = V((0, sy * (RIDGE_Z - EAVE_Z), ROOF_HY)).normalized()
        for r in range(rows):
            f = 1 - (r + 0.5) / rows
            base = V((0, 0, RIDGE_Z + 0.04)) + dn * (sl * f + 0.06)
            x = -ROOF_HX - 0.02 + (0.09 if r % 2 else 0.0)
            while x < ROOF_HX:
                w = rng.uniform(0.15, 0.21)
                xm = min(x + w / 2, ROOF_HX - w / 2 + 0.03)
                p = base + V((xm, 0, 0)) + nrm * (0.012 + 0.016 * r / rows + rng.uniform(0, 0.006))
                M = Matrix((V((1, 0, 0)), dn, nrm)).transposed()
                M = Matrix.Rotation(rng.uniform(-0.04, 0.04), 3, nrm) @ M
                row_ = rng.randrange(8)
                u0 = rng.random()
                lib.beam(mb, p, (w - 0.012, 0.30, 0.018), M=M, chamfer=0.0,
                         uv=lambda ax, a_, b_, row_=row_, u0=u0: ((u0 + b_ / 1.0), 1 - (row_ + 0.5 + a_ * 4.0) / 8), mat=SHING)
                x += w
    # ridge cap: two boards along the top
    for sy in (-1, 1):
        nrm = V((0, sy * (RIDGE_Z - EAVE_Z), ROOF_HY)).normalized()
        dn = V((0, sy * ROOF_HY, EAVE_Z - RIDGE_Z)).normalized()
        M = Matrix((V((1, 0, 0)), dn, nrm)).transposed()
        lib.beam(mb, V((0, 0, RIDGE_Z + 0.075)) + dn * 0.06, (2 * ROOF_HX + 0.08, 0.13, 0.02), M=M, chamfer=0.003,
                 uv=lambda ax, a_, b_: (a_ * 0.5, 1 - (6.5 + b_ * 3) / 8), mat=WOOD)
    # the rope hanging from the coil down into the shaft
    hang_top = V((0.20, -0.095, AXLE_Z - 0.02))
    pts = [hang_top, V((0.205, -0.10, 1.2)), V((0.21, -0.11, 0.8)), V((0.20, -0.10, 0.35))]
    Loft(pts, lambda t: {"rx": 0.017, "ry": 0.017}, n=6, seg=0.08, frame="up", up=V((1, 0, 0)), cap0="flat",
         cap1="dome", cap1_len=0.02).build(mb, uvmap=lambda s, a_: (s * 1.3 / 0.12, a_), mat=ROPE)
    # ivy: a vine winding up each post with leaves, sprigs on the stones
    for sx in (-1, 1):
        vine = []
        for i in range(40):
            t = i / 39
            ang = t * math.tau * 2.2 + (0.0 if sx > 0 else 2.0)
            vine.append(V((sx * POST_X + 0.062 * math.cos(ang), 0.062 * math.sin(ang), 0.05 + t * 2.0)))
        Loft(vine, lambda t: {"rx": 0.007, "ry": 0.007}, n=4, seg=0.06, frame="rmf", up=V((1, 0, 0)), cap0="flat",
             cap1="flat").build(mb, uvmap=lambda s, a_: (0.5, 0.02), mat=IVY)
        for i in range(48):
            t = rng.uniform(0.0, 1.0)
            ang = t * math.tau * 2.2 + (0.0 if sx > 0 else 2.0) + rng.uniform(-0.6, 0.6)
            out = V((math.cos(ang), math.sin(ang), 0.15)).normalized()
            p = V((sx * POST_X, 0, 0.05 + t * 2.0)) + V((math.cos(ang), math.sin(ang), 0)) * 0.07
            ivy_leaf(mb, p, out, V((0, 0, 1)), rng.uniform(0.06, 0.10), IVY, rng)
    for i in range(16):
        th = rng.uniform(0, math.tau)
        z = rng.uniform(0.08, 0.66)
        out = V((math.cos(th), math.sin(th), 0))
        ivy_leaf(mb, out * (R_FACE + 0.01) + V((0, 0, z)), out, V((0, 0, 1)), rng.uniform(0.05, 0.08), IVY, rng)
    root = mb.object("magic_well", [m_stone, m_wood, m_shing, m_ivy, m_rope, m_glow], origin=(0, 0, 0), auto_smooth=45)
    # the windlass: drum and axle between the posts, the coil of rope on it
    axle = V((0, 0, AXLE_Z))
    wm = MB()
    rough_post(wm, (-POST_X - 0.10, 0, AXLE_Z), (POST_X + 0.08, 0, AXLE_Z), 0.025, 0, 1, 21)
    rough_post(wm, (-POST_X + 0.07, 0, AXLE_Z), (POST_X - 0.07, 0, AXLE_Z), 0.072, 0, 0, 23)
    coil = []
    turns, x0, x1 = 9, -0.08, 0.30
    m = turns * 18
    for i in range(m + 1):
        f = i / m
        a = f * turns * math.tau
        r = 0.072 + 0.018 + (0.034 if 0.25 < f < 0.75 else 0.0) * math.sin(math.pi * (f - 0.25) / 0.5) ** 2
        coil.append(V((x0 + (x1 - x0) * f, -math.sin(a) * r, AXLE_Z + math.cos(a) * r)))
    Loft(coil, lambda t: {"rx": 0.018, "ry": 0.018}, n=6, seg=0.03, frame="rmf", up=V((1, 0, 0)), cap0="flat",
         cap1="flat").build(wm, uvmap=lambda s, a_: (s * 8.0 / 0.12 * 0.1, a_), mat=1)
    windlass = wm.object("windlass", [m_wood, m_rope], origin=axle, auto_smooth=45)
    lib.set_parent(windlass, root)
    # the crank on the +X end: an arm off the axle and a grip parallel to it
    cm = MB()
    xe = POST_X + 0.10
    rough_post(cm, (xe - 0.03, 0, AXLE_Z), (xe + 0.02, 0, AXLE_Z), 0.03, 0, 3, 25)
    rough_post(cm, (xe, 0, AXLE_Z + 0.02), (xe, 0, AXLE_Z - 0.24), 0.022, 0, 3, 27)
    rough_post(cm, (xe - 0.01, 0, AXLE_Z - 0.22), (xe + 0.17, 0, AXLE_Z - 0.22), 0.02, 0, 7, 29)
    crank = cm.object("crank", [m_wood], origin=V((xe, 0, AXLE_Z)), auto_smooth=45)    # pivot on the axle line
    lib.set_parent(crank, root)
    lib.empty("fog_source", location=(0, 0, RIM_Z - 0.30), parent=root)
    lib.empty("coin_drop", location=(0, 0, RIM_Z + 0.45), parent=root)
    tris = lib.tri_count(root) + lib.tri_count(windlass) + lib.tri_count(crank)
    print(f"  magic-well: {tris} tris (root {lib.tri_count(root)}, windlass {lib.tri_count(windlass)}, crank {lib.tri_count(crank)})")
    lib.export("magic-well")


if __name__ == "__main__":
    main()
