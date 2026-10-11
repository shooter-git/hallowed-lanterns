# SPDX-License-Identifier: MIT
"""The Día de los Muertos ofrenda of the Marigold Garden (reference/ofrenda.jpg).

    blender -b --factory-startup -P tools/blender/ofrenda.py

Writes public/models/ofrenda.glb (about 5.4 m tall, 5.4 m wide, 2.6 m deep).

A teal frame with a lime border round a window onto stacked hay bales, the glowing cut-out
crest on top, marigold garlands, three purple tiers with fruit baskets, bottles, skulls,
bouquets in glowing vases, little glowing pumpkins, papel picado and rows of marigolds.

Nodes: `ofrenda` (root, everything static), `crest` (the glowing cut-out sign, material
`glow_crest`), `candle_template` (one drippy white candle, pivot at its base) with child
`flame_template` (flame + the glow in the candle's cup, `glow_flame`), and `candle_spots`
with children `candle_000`... (empties where candles stand; their scale is the candle's size
relative to the template). candle_template stands on candle_000.
Materials: ofrenda_paint, glow_crest, papel_picado (alpha MASK, double sided), glow_lights
(little pumpkins, vases, bottles), candle_wax, glow_flame.
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
PW, PH = 2048, 1024
REGIONS = {
    "teal": (0, 0, 512, 512), "lime": (512, 0, 256, 256), "purple": (768, 0, 512, 512),
    "hay": (1280, 0, 768, 512), "runner": (0, 512, 512, 256), "marigold": (512, 512, 768, 256),
    "basket": (1280, 512, 256, 256),
    "apple_red": (1536, 512, 128, 128), "apple_green": (1664, 512, 128, 128), "orange": (1792, 512, 128, 128),
    "banana": (1920, 512, 128, 128), "grape": (1536, 640, 128, 128), "pear": (1664, 640, 128, 128),
    "glass": (1792, 640, 128, 128), "skull": (1792, 768, 256, 256),
}
FRAME_W, FRAME_Z0, FRAME_Z1 = 1.65, 1.20, 3.80
WIN_W, WIN_Z0, WIN_Z1 = 1.12, 1.45, 3.48
TIERS = [  # half width, front y, top z
    (2.70, -1.70, 0.40),
    (2.60, -1.12, 0.80),
    (2.20, -0.56, 1.20),
]
BACK_Y = 0.25


def reg(name, u, v):
    x, y, w, h = REGIONS[name]
    u = min(max(u, 0.0), 1.0)
    v = min(max(v, 0.0), 1.0)
    return ((x + u * w) / PW, 1.0 - (y + (1.0 - v) * h) / PH)


def rect_uv(name, sx, sy, ox=0.5, oy=0.5):
    """beam() uv callback: local metres -> a region, sx/sy metres across it."""
    def m(ax, fx, fy):
        return reg(name, ox + fx / sx, oy + fy / sy)
    return m


# --------------------------------------------------------------------------------------------
# Crest silhouette (crest-local x right, z up from the frame top)
# --------------------------------------------------------------------------------------------

def crest_top(x):
    ax = abs(x)
    zs = [0.0]
    if ax <= 1.40:
        zs.append(0.45)
    elif ax <= 1.65:
        zs.append(0.18 + math.sqrt(max(0.27 ** 2 - (ax - 1.40) ** 2, 0.0)))
    for cx, cz, r in ((0.80, 0.86, 0.45), (0.0, 1.12, 0.45)):
        d = ax - cx
        if abs(d) <= r:
            zs.append(cz + math.sqrt(r * r - d * d))
    return max(zs)


def crest_outline(step=0.01):
    xs = [-1.65 + i * step for i in range(int(round(3.3 / step)) + 1)]
    return [(x, crest_top(x)) for x in xs]


def build_crest(mat):
    mb = MB()
    pts = crest_outline(0.02)
    zmax = max(z for _, z in pts)
    box = (-1.65, 1.65, 0.0, zmax)
    y0, y1 = -0.025, 0.025

    def uv(x, z):
        return ((x - box[0]) / (box[1] - box[0]), (z - box[2]) / (box[3] - box[2]))
    back = (0.004, 0.996)
    fr, bk = [], []
    for x, z in pts:
        fr.append((mb.v((x, y0, 0.0)), mb.v((x, y0, z))))
        bk.append((mb.v((x, y1, 0.0)), mb.v((x, y1, z))))
    for i in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        a0, a1 = fr[i]
        b0, b1 = fr[i + 1]
        mb.f((a0, b0, b1, a1), [uv(x0, 0), uv(x1, 0), uv(x1, z1), uv(x0, z0)], None, mat)
        c0, c1 = bk[i]
        d0, d1 = bk[i + 1]
        mb.f((c0, c1, d1, d0), [back] * 4, None, mat)
        mb.f((a1, b1, d1, c1), [back] * 4, None, mat)       # top edge
        mb.f((a0, c0, d0, b0), [back] * 4, None, mat)       # bottom edge
    mb.f((fr[0][0], fr[0][1], bk[0][1], bk[0][0]), [back] * 4, None, mat)
    mb.f((fr[-1][0], bk[-1][0], bk[-1][1], fr[-1][1]), [back] * 4, None, mat)
    return mb, box


# --------------------------------------------------------------------------------------------
# Structure: tiers, frame, hay wall, runner
# --------------------------------------------------------------------------------------------

def build_structure(mb, mat):
    z0 = 0.0
    for hw, fy, top in TIERS:
        depth = BACK_Y - fy
        lib.beam(mb, (0, (fy + BACK_Y) / 2, (z0 + top) / 2), (2 * hw, depth, top - z0), chamfer=0.01,
                 uv=rect_uv("purple", 2 * hw + 0.2, 1.6), mat=mat)
        z0 = top
    y0, y1 = 0.0, 0.14
    yc, d = (y0 + y1) / 2, y1 - y0
    tuv = rect_uv("teal", 3.5, 2.8)
    sw = FRAME_W - WIN_W
    for sx in (-1, 1):
        lib.beam(mb, (sx * (WIN_W + sw / 2), yc, (FRAME_Z0 + FRAME_Z1) / 2), (sw, d, FRAME_Z1 - FRAME_Z0),
                 chamfer=0.008, uv=tuv, mat=mat)
    lib.beam(mb, (0, yc, (WIN_Z1 + FRAME_Z1) / 2), (2 * WIN_W, d, FRAME_Z1 - WIN_Z1), chamfer=0.008, uv=tuv, mat=mat)
    lib.beam(mb, (0, yc, (FRAME_Z0 + WIN_Z0) / 2), (2 * WIN_W, d, WIN_Z0 - FRAME_Z0), chamfer=0.008, uv=tuv, mat=mat)
    # the seam between the two halves of the frame
    lib.beam(mb, (0, y0 - 0.002, (FRAME_Z0 + FRAME_Z1) / 2), (0.012, 0.006, FRAME_Z1 - FRAME_Z0), chamfer=0.0,
             uv=lambda ax, fx, fy: reg("purple", 0.1, 0.1), mat=mat)
    # lime border round the window
    b, bd = 0.085, 0.03
    luv = rect_uv("lime", 2.5, 2.5)
    yb = y0 - bd / 2 + 0.005
    for sx in (-1, 1):
        lib.beam(mb, (sx * (WIN_W + b / 2), yb, (WIN_Z0 + WIN_Z1) / 2), (b, bd, WIN_Z1 - WIN_Z0 + 2 * b),
                 chamfer=0.006, uv=luv, mat=mat)
    for z in (WIN_Z0 - b / 2, WIN_Z1 + b / 2):
        lib.beam(mb, (0, yb, z), (2 * WIN_W, bd, b), chamfer=0.006, uv=luv, mat=mat)
    # the hay wall behind the window
    rng = lib.seeded(5)
    huv = rect_uv("hay", 1.0, 0.6)
    bale = (0.92, 0.46, 0.36)
    for row in range(10):
        zc = bale[2] / 2 + row * bale[2]
        shift = (0.23 if row % 2 else -0.15) + rng.uniform(-0.05, 0.05)
        for k in range(-1, 2):
            x = k * bale[0] + shift
            if abs(x) > 1.45:
                continue
            lib.beam(mb, (x, 0.42 + rng.uniform(-0.03, 0.03), zc), (bale[0] - 0.02, bale[1], bale[2] - 0.01),
                     M=Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, "Z"), chamfer=0.05,
                     uv=rect_uv("hay", 1.0, 0.6, 0.5, rng.uniform(0.45, 0.55)), mat=mat)
    # table runner on the top tier, draping over its front edge
    hw, fy, top = TIERS[2]
    xs = [-1.1, 1.1]
    pts = [(fy + 0.45, top + 0.004), (fy + 0.02, top + 0.004), (fy - 0.012, top - 0.02), (fy - 0.012, top - 0.14)]
    s_tot = 0.0
    seg = []
    for (ya, za), (yb2, zb) in zip(pts, pts[1:]):
        seg.append(s_tot)
        s_tot += math.hypot(yb2 - ya, zb - za)
    seg.append(s_tot)
    rows = [[mb.v((x, y, z)) for x in xs] for y, z in pts]
    for j in range(len(pts) - 1):
        a, b2 = seg[j] / s_tot, seg[j + 1] / s_tot
        mb.f((rows[j][0], rows[j + 1][0], rows[j + 1][1], rows[j][1]),
             [reg("runner", a, 0), reg("runner", b2, 0), reg("runner", b2, 1), reg("runner", a, 1)], None, mat)


# --------------------------------------------------------------------------------------------
# Marigolds
# --------------------------------------------------------------------------------------------

def marigold_rope(mb, pts, r, mat, variant=0, seg=0.03, n=8, seed=0):
    u0 = variant / 3 + 0.02

    def sec(t):
        return {"rx": r, "ry": r}

    def lumpy(t, a, s):
        q = Vector((math.cos(a * 6.283), math.sin(a * 6.283), t * 60 + seed))
        return r * (0.35 * mnoise.noise(q * 1.3) + 0.25 * mnoise.noise(q * 3.1))
    loft = Loft(pts, sec, n=n, seg=seg, frame="rmf", up=Z, offset=lumpy, cap0="dome", cap1="dome")
    loft.build(mb, uvmap=lambda s, a: reg("marigold", u0 + 0.30 * a, 1 - abs((s * loft.L * 3) % 2.0 - 1)), mat=mat)


def marigold_head(mb, p, r, mat, variant=0, seed=0):
    u0 = variant / 3 + 0.03
    lib.lump(mb, p, r, (1.0, 1.0, 0.75), seed=seed, rough=0.35, nu=8, nv=5, mat=mat,
             uvmap=lambda u, v: reg("marigold", u0 + 0.27 * u, v))


def catenary(a, b, sag, n=24):
    a, b = Vector(a), Vector(b)
    return [a.lerp(b, i / n) - Z * (sag * 4 * (i / n) * (1 - i / n)) for i in range(n + 1)]


def build_garlands(mb, mat):
    yf = -0.035
    top = FRAME_Z1 - 0.03
    # along the top edge, then swags hanging from it
    marigold_rope(mb, [(-FRAME_W, yf, top), (0, yf - 0.01, top + 0.01), (FRAME_W, yf, top)], 0.05, mat, seed=1)
    hooks = [-1.62, -0.82, 0.0, 0.82, 1.62]
    for i, (xa, xb) in enumerate(zip(hooks, hooks[1:])):
        marigold_rope(mb, catenary((xa, yf - 0.01, top - 0.02), (xb, yf - 0.01, top - 0.02), 0.24), 0.048, mat,
                      seed=2 + i)
        marigold_rope(mb, catenary((xa, yf - 0.02, top - 0.03), (xb, yf - 0.02, top - 0.03), 0.12), 0.042, mat,
                      variant=1, seed=7 + i)
    # down the sides, flowing outward toward the bottom
    for s in (-1, 1):
        pts = []
        for i in range(12):
            f = i / 11
            x = s * (FRAME_W + 0.04 + 0.10 * f * f + 0.03 * math.sin(f * 9))
            z = top - f * (top - TIERS[2][2] - 0.12)
            pts.append((x, yf + 0.02 * math.sin(f * 7), z))
        marigold_rope(mb, pts, 0.05, mat, seed=20 + s)
    # petals along the ground in front of the bottom tier
    hw, fy, _ = TIERS[0]
    marigold_rope(mb, [(-hw - 0.05, fy - 0.10, 0.03), (0, fy - 0.12, 0.03), (hw + 0.05, fy - 0.10, 0.03)], 0.055,
                  mat, seg=0.035, seed=30)


# --------------------------------------------------------------------------------------------
# Offerings
# --------------------------------------------------------------------------------------------

def fruit(mb, p, kind, r, mat, seed):
    rng = lib.seeded(seed)
    if kind == "banana":
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized()
        side = d.cross(Z)
        for k in range(3):
            o = side * (k - 1) * 0.022
            pts = [p + o + d * (-0.09) + Z * 0.02, p + o + Z * 0.0, p + o + d * 0.09 + Z * 0.025]
            Loft(pts, lambda t: {"rx": 0.019 * (1 - 0.5 * abs(2 * t - 1) ** 2), "ry": 0.016}, n=6, seg=0.03,
                 frame="up", up=Z, cap0="point", cap1="point").build(mb, uvmap=lambda s, a: reg("banana", a, s), mat=mat)
        return
    if kind == "grape":
        for k in range(7):
            q = p + Vector((rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), rng.uniform(0, 0.05)))
            lib.lump(mb, q, 0.024, seed=seed + k, rough=0.05, nu=6, nv=4, mat=mat,
                     uvmap=lambda u, v: reg("grape", u, v), flat_bottom=False)
        return
    name = {"apple": rng.choice(["apple_red", "apple_red", "apple_green"]), "orange": "orange", "pear": "pear"}[kind]
    sc = (1, 1, 1.25) if kind == "pear" else (1, 1, 0.92)
    lib.lump(mb, p + Z * r * 0.8, r, sc, seed=seed, rough=0.04, nu=8, nv=6, mat=mat,
             uvmap=lambda u, v, name=name: reg(name, u, v), flat_bottom=False)


def basket(mb, c, w, d, mat, seed, round_=True):
    rng = lib.seeded(seed)
    h = 0.09
    if round_:
        Loft([c, c + Z * h], lambda t: {"rx": w * (0.82 + 0.18 * t), "ry": d * (0.82 + 0.18 * t)}, n=16, seg=0.05,
             frame="up", up=Vector((0, 1, 0)), cap0="flat", cap1="open").build(
                 mb, uvmap=lambda s, a: reg("basket", a, s), mat=mat)
        Loft([c + Vector((w * math.cos(math.tau * i / 16), d * math.sin(math.tau * i / 16), h)) for i in range(16)],
             lambda t: {"rx": 0.014, "ry": 0.014}, n=5, seg=0.06, closed=True, frame="rmf", up=Z).build(
                 mb, uvmap=lambda s, a: reg("basket", s, a), mat=mat)
    else:
        lib.beam(mb, c + Z * (h / 2), (2 * w, 2 * d, h), chamfer=0.01, uv=rect_uv("basket", 0.5, 0.25), mat=mat)
    kinds = ["apple", "apple", "orange", "pear", "banana", "grape"]
    n = 11 if round_ else 13
    for k in range(n):
        layer = 0 if k < n * 0.6 else 1
        q = c + Vector((rng.uniform(-w * 0.65, w * 0.65), rng.uniform(-d * 0.55, d * 0.55),
                        h * 0.55 + layer * 0.06 + rng.uniform(0, 0.03)))
        fruit(mb, q, rng.choice(kinds), rng.uniform(0.042, 0.056), mat, seed * 10 + k)


def skull(mb, p, mat, yaw=0.0, s=1.0):
    R = Matrix.Rotation(yaw, 3, "Z")
    base = len(mb.verts)
    lib.lump(mb, p + R @ (Vector((0, 0.01, 0.085)) * s), 0.075 * s, (0.92, 1.1, 0.95), seed=3, rough=0.03, nu=12, nv=8,
             mat=mat, flat_bottom=False)
    lib.lump(mb, p + R @ (Vector((0, -0.045, 0.04)) * s), 0.05 * s, (1.0, 0.75, 0.85), seed=4, rough=0.03, nu=10, nv=6,
             mat=mat, flat_bottom=True)
    # front-projected face: re-map the UVs of the faces just added
    Rinv = R.inverted()
    for fi in range(len(mb.faces)):
        f = mb.faces[fi]
        if f[0] < base:
            continue
        uvs = []
        for vi in f:
            q = Rinv @ (Vector(mb.verts[vi]) - p) / s
            if q.y > 0.02:
                uvs.append(reg("skull", 0.04, 0.96))
            else:
                uvs.append(reg("skull", 0.5 + q.x / 0.17, 0.5 + (q.z - 0.075) / 0.15))
        mb.uv[fi] = uvs


def bottle(mb, p, mat, h=0.32):
    keys = [(0, 0.046), (0.55, 0.048), (0.68, 0.03), (0.75, 0.017), (1, 0.016)]
    Loft([p, p + Z * h], lambda t: {"rx": lib.lerp_keys(keys, t), "ry": lib.lerp_keys(keys, t)}, n=14, seg=0.02,
         frame="up", up=Vector((0, 1, 0)), cap0="flat", cap1="flat").build(
             mb, uvmap=lambda s, a: (0.5 + 0.45 * a, 0.05 + 0.4 * s), mat=mat)


def vase_bouquet(mb, glow_mb, p, mat, glow_mat, seed, scale=1.0):
    rng = lib.seeded(seed)
    h, r = 0.26 * scale, 0.085 * scale
    Loft([p, p + Z * h], lambda t: {"rx": r * (1 - 0.15 * math.sin(t * math.pi)), "ry": r * (1 - 0.15 * math.sin(t * math.pi))},
         n=14, seg=0.03, frame="up", up=Vector((0, 1, 0)), cap0="flat", cap1="flat").build(
             glow_mb, uvmap=lambda s, a: (0.05 + 0.4 * a, 0.05 + 0.4 * s), mat=glow_mat)
    top = p + Z * (h + 0.04 * scale)
    for k in range(18):
        ang = rng.uniform(0, math.tau)
        rr = rng.uniform(0, 0.16 * scale)
        q = top + Vector((math.cos(ang) * rr, math.sin(ang) * rr, 0.09 * scale - rr * 0.5 + rng.uniform(0, 0.06)))
        marigold_head(mb, q, rng.uniform(0.05, 0.075) * scale, mat, variant=rng.choice([0, 0, 1, 2]), seed=seed + k)


def glow_pumpkin(glow_mb, p, r, q, mat, seed):
    lib.pumpkin(glow_mb, p + Z * r * 0.85, r, r * 0.82, ribs=8, groove=0.12, nu=24, nv=10, mat=mat, seed=seed,
                top_dimple=0.15, uvmap=lambda u, v: ((q + u) / 4, 0.5 + 0.5 * v))
    Loft([p + Z * r * 1.45, p + Z * r * 1.75 + Vector((0.01, 0, 0))], lambda t: {"rx": r * 0.12, "ry": r * 0.12},
         n=6, seg=0.05, frame="up", up=Vector((0, 1, 0)), cap0="flat", cap1="flat").build(
             glow_mb, uvmap=lambda s, a: (0.6, 0.1), mat=mat)


def build_offerings(mb, glow_mb, papel_mb, mat, glow_mat, papel_mat, spots):
    rng = lib.seeded(11)
    # tier 2 (fruit): baskets along it, marigold heads between, along the front edge
    hw, fy, top = TIERS[1]
    xs = [-2.15, -1.45, -0.75, 0.0, 0.75, 1.45, 2.15]
    for i, x in enumerate(xs):
        basket(mb, Vector((x + rng.uniform(-0.08, 0.08), fy + 0.30, top)), rng.uniform(0.16, 0.22), rng.uniform(0.11, 0.15),
               mat, seed=100 + i, round_=(i % 3 != 1))
    for k in range(52):
        x = -hw + 0.1 + k * (2 * hw - 0.2) / 51
        marigold_head(mb, Vector((x, fy + 0.07 + rng.uniform(-0.02, 0.02), top + 0.03)), rng.uniform(0.045, 0.06), mat,
                      variant=rng.choice([0, 0, 1]), seed=200 + k)
    # tier 3 (top): bouquets, bottles and skulls at both ends
    hw3, fy3, top3 = TIERS[2]
    for s in (-1, 1):
        vase_bouquet(mb, glow_mb, Vector((s * 1.95, fy3 + 0.30, top3)), mat, glow_mat, seed=300 + s, scale=1.2)
        vase_bouquet(mb, glow_mb, Vector((s * 1.45, fy3 + 0.40, top3)), mat, glow_mat, seed=310 + s, scale=1.0)
        bottle(glow_mb, Vector((s * 2.08, fy3 + 0.12, top3)), glow_mat)
        skull(mb, Vector((s * 1.25, fy3 + 0.18, top3)), mat, yaw=-s * 0.3, s=1.1)
        for k in range(5):
            marigold_head(mb, Vector((s * (1.3 + k * 0.17), fy3 + 0.06, top3 + 0.03)), 0.05, mat, variant=0, seed=320 + k * s)
        # tier 2 end bouquets and bottles
        vase_bouquet(mb, glow_mb, Vector((s * 2.40, fy + 0.40, top)), mat, glow_mat, seed=330 + s, scale=1.1)
        bottle(glow_mb, Vector((s * 2.12, fy + 0.45, top)), glow_mat, h=0.34)
    # tier 1: papel picado on the riser above it, glowing pumpkins and skulls among the candle spots
    hw1, fy1, top1 = TIERS[0]
    flags = 14
    span = 2 * hw - 0.2
    yflag = fy - 0.012
    for k in range(flags):
        x0 = -span / 2 + k * span / flags + 0.01
        x1 = x0 + span / flags - 0.02
        cell = k % 3
        cu, cv = (cell % 2) * 0.5, 1.0 - (cell // 2) * 0.5
        ztop, zbot = top - 0.015, top - 0.38
        sway = rng.uniform(-0.012, 0.012)
        a = papel_mb.v((x0, yflag, ztop))
        b = papel_mb.v((x1, yflag, ztop))
        c = papel_mb.v((x1 + sway, yflag - 0.01, zbot))
        d = papel_mb.v((x0 + sway, yflag - 0.01, zbot))
        papel_mb.f((a, d, c, b), [(cu, cv), (cu, cv - 0.5), (cu + 0.5, cv - 0.5), (cu + 0.5, cv)], None, papel_mat)
    Loft([(-hw - 0.02, yflag - 0.004, top - 0.012), (hw + 0.02, yflag - 0.004, top - 0.012)],
         lambda t: {"rx": 0.004, "ry": 0.004}, n=4, seg=1.0, frame="up", up=Z).build(
             mb, uvmap=lambda s, a: reg("basket", 0.5, 0.5), mat=mat)
    # candle spots along tier 1, with pumpkins and skulls in some of the gaps
    k = 0
    x = -hw1 + 0.12
    while x < hw1 - 0.1:
        y = fy1 + 0.22 + rng.uniform(-0.06, 0.06)
        roll = rng.random()
        if roll < 0.2:
            glow_pumpkin(glow_mb, Vector((x, y, top1)), rng.uniform(0.09, 0.12), rng.randrange(4), glow_mat, seed=400 + k)
        elif roll < 0.24:
            skull(mb, Vector((x, y, top1)), mat, yaw=rng.uniform(-0.4, 0.4), s=0.85)
        else:
            spots.append((Vector((x, y, top1)), rng.uniform(0.55, 1.35)))
        if rng.random() < 0.5:
            marigold_head(mb, Vector((x + 0.09, fy1 + 0.06, top1 + 0.03)), rng.uniform(0.04, 0.055), mat,
                          variant=1, seed=500 + k)
        x += rng.uniform(0.17, 0.24)
        k += 1
    # a second, back row of tall candles on tier 1 against the papel picado
    x = -hw1 + 0.3
    while x < hw1 - 0.3:
        spots.append((Vector((x, fy1 + 0.45, top1)), rng.uniform(1.0, 1.5)))
        x += rng.uniform(0.45, 0.7)
    # tier 3: candles in front of the frame's bottom corners
    for s in (-1, 1):
        for j in range(4):
            spots.append((Vector((s * (1.0 + j * 0.13) + rng.uniform(-0.02, 0.02), fy3 + 0.12 + 0.12 * (j % 2), top3)),
                          rng.uniform(0.7, 1.3)))
    # monarchs resting on the hay wall and above the bouquets
    for j in range(8):
        cu, cv = 0.5 + (j % 2) * 0.25, 0.5 - (j // 2 % 2) * 0.25
        if j < 5:
            p = Vector((rng.uniform(-1.0, 1.0), 0.18, rng.uniform(1.7, 3.3)))
            nrm = Vector((0, -1, 0))
        else:
            s = (-1) ** j
            p = Vector((s * rng.uniform(1.5, 2.0), fy3 + 0.3, 1.95 + rng.uniform(0, 0.25)))
            nrm = Vector((rng.uniform(-0.3, 0.3), -1, 0.4)).normalized()
        sz = 0.07
        R = nrm.to_track_quat("-Y", "Z").to_matrix() @ Matrix.Rotation(rng.uniform(-0.5, 0.5), 3, "Y")
        corners = [R @ Vector((-sz, 0, -sz)), R @ Vector((sz, 0, -sz)), R @ Vector((sz, 0, sz)), R @ Vector((-sz, 0, sz))]
        idx = [papel_mb.v(p + c) for c in corners]
        papel_mb.f(idx, [(cu, cv - 0.25), (cu + 0.25, cv - 0.25), (cu + 0.25, cv), (cu, cv)], None, papel_mat)


# --------------------------------------------------------------------------------------------
# The template candle
# --------------------------------------------------------------------------------------------

def build_candle():
    mb = MB()
    r, h = 0.05, 0.24
    rng = lib.seeded(3)
    drips = [(rng.uniform(0, 1), rng.uniform(0.15, 0.55), rng.uniform(0.04, 0.07)) for _ in range(7)]

    def off(t, a, sec):
        o = 0.0
        for da, ln, w in drips:
            d = abs(((a - da + 0.5) % 1.0) - 0.5)
            if d < w and t > 1 - ln:
                f = (t - (1 - ln)) / ln
                o += r * 0.13 * math.cos(d / w * math.pi / 2) ** 2 * min(1.0, f * 4) * (0.6 + 0.4 * math.sin(f * 9))
        return o + r * 0.02 * mnoise.noise(Vector((a * 7, t * 9, 1.3)))
    Loft([(0, 0, 0), (0, 0, h)], lambda t: {"rx": r, "ry": r}, n=24, seg=0.012, frame="up", up=Vector((0, 1, 0)),
         cap0="flat", cap1="open", offset=off).build(mb, mat=0)
    # the melted rim and the cup
    ring = [(r * 0.97 * math.cos(math.tau * i / 24), r * 0.97 * math.sin(math.tau * i / 24),
             h + 0.006 * math.sin(i * 1.7)) for i in range(24)]
    Loft(ring, lambda t: {"rx": 0.009, "ry": 0.011}, n=6, seg=0.02, closed=True, frame="rmf", up=Z).build(mb, mat=0)
    Loft([(0, 0, h + 0.004), (0, 0, h - 0.035)], lambda t: {"rx": r * 0.92 - 0.01 * t, "ry": r * 0.92 - 0.01 * t},
         n=20, seg=0.02, frame="up", up=Vector((0, 1, 0)), cap0="open", cap1="flat").build(mb, mat=0)
    # flame + the glow in the cup (the "lit" part)
    fmb = MB()
    fz = h - 0.034
    Loft([(0, 0, fz + 0.005), (0, 0, fz + 0.03), (0.002, 0, fz + 0.075)],
         lambda t: {"rx": 0.013 * math.sin(math.pi * min(0.999, 0.15 + 0.85 * t)) ** 0.8 * (1 - 0.3 * t),
                    "ry": 0.010 * math.sin(math.pi * min(0.999, 0.15 + 0.85 * t)) ** 0.8 * (1 - 0.3 * t)},
         n=10, seg=0.006, frame="up", up=Vector((0, 1, 0)), cap0="dome", cap1="point", cap0_len=0.004).build(
             fmb, uvmap=lambda s, a: (0.5, s), mat=0)
    Loft([(0, 0, fz + 0.001), (0, 0, fz + 0.002)], lambda t: {"rx": r * 0.86, "ry": r * 0.86}, n=20, seg=0.01,
         frame="up", up=Vector((0, 1, 0)), cap0="open", cap1="flat").build(fmb, uvmap=lambda s, a: (0.5, 0.1), mat=0)
    return mb, fmb


def main():
    lib.reset()
    outline = crest_outline(0.01)
    zmax = max(z for _, z in outline)
    stars = [(-0.12, 1.42, 0.035), (0.13, 1.45, 0.03), (-0.25, 1.25, 0.03), (0.25, 1.28, 0.035), (-0.17, 1.12, 0.022),
             (0.19, 1.10, 0.025), (-0.32, 1.05, 0.02), (0.33, 1.0, 0.022), (-0.06, 1.55, 0.018), (0.07, 1.20, 0.018),
             (-0.55, 0.98, 0.025), (0.56, 0.95, 0.025), (-1.05, 1.12, 0.02), (1.06, 1.12, 0.02)]
    tex = lib.paint("tex_ofrenda.py", {"crest_box": [-1.65, 1.65, 0.0, zmax], "crest_outline": outline,
                                       "stars": stars, "regions": REGIONS, "paint_size": [PW, PH]},
                    {"crest_base": "ofrenda-crest-base.jpg", "crest_emit": "ofrenda-crest-emit.jpg",
                     "papel": "ofrenda-papel.png", "paint": "ofrenda-paint.jpg", "lights": "ofrenda-lights.jpg",
                     "flame": "ofrenda-flame.jpg"})
    paint = lib.material("ofrenda_paint", base_tex=tex["paint"], roughness=0.8, specular=0.3)
    crest_m = lib.material("glow_crest", base_tex=tex["crest_base"], emission_tex=tex["crest_emit"], roughness=0.6)
    papel = lib.material("papel_picado", base_tex=tex["papel"], roughness=0.7, alpha_clip=0.5, double_sided=True)
    lights = lib.material("glow_lights", base_tex=tex["lights"], emission_tex=tex["lights"], roughness=0.3)
    wax = lib.material("candle_wax", color="#f1ebdd", roughness=0.55, specular=0.4)
    flame = lib.material("glow_flame", base_tex=tex["flame"], emission_tex=tex["flame"], roughness=1.0)

    mb, glow_mb, papel_mb = MB(), MB(), MB()
    build_structure(mb, 0)
    build_garlands(mb, 0)
    spots = []
    build_offerings(mb, glow_mb, papel_mb, 0, 1, 2, spots)
    mb.extend(glow_mb)
    mb.extend(papel_mb)
    root = mb.object("ofrenda", [paint, lights, papel], origin=(0, 0, 0))
    total = lib.tri_count(root)
    cmb, box = build_crest(0)
    crest = cmb.object("crest", [crest_m], origin=(0, 0, 0))
    crest.location = (0, 0.07, FRAME_Z1)
    lib.set_parent(crest, root)
    total += lib.tri_count(crest)
    spot_root = lib.empty("candle_spots", (0, 0, 0))
    lib.set_parent(spot_root, root)
    for i, (p, s) in enumerate(spots):
        e = lib.empty(f"candle_{i:03d}", p, size=0.05)
        e.scale = (s, s, s)
        lib.set_parent(e, spot_root)
    cand, fl = build_candle()
    p0, s0 = spots[0]
    c_obj = cand.object("candle_template", [wax], origin=(0, 0, 0))
    c_obj.location = p0
    c_obj.scale = (s0, s0, s0)
    f_obj = fl.object("flame_template", [flame], origin=(0, 0, 0))
    f_obj.location = p0
    f_obj.scale = (s0, s0, s0)
    lib.set_parent(c_obj, root)
    lib.set_parent(f_obj, c_obj)
    total += lib.tri_count(c_obj) + lib.tri_count(f_obj)
    print(f"  ofrenda: {total} tris, {len(spots)} candle spots; candle {lib.tri_count(c_obj)} + flame {lib.tri_count(f_obj)}")
    lib.export("ofrenda")


main()
