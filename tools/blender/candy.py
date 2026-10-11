# SPDX-License-Identifier: MIT
"""Sweet Hollow's candy props (reference/candy-hollow.jpg).

    blender -b --factory-startup -P tools/blender/candy.py

Writes public/models/candy-bucket.glb, candy-corn.glb, gummy-bear.glb, lollipop.glb,
skewer.glb and cake-pop.glb. Each stands on z = 0 with its origin at the base centre.

candy-bucket  giant jack-o'-lantern candy bucket (2.2 m wide), open top; child `handle` (pivot
              at the rim centre): black pipe wound with a glowing tube (`glow_handle`).
candy-corn    a thick painted candy-corn board, 2.5 m.
gummy-bear    a pumpkin sculpted into a gummy bear, 0.6 m. Material `gummy` = a neutral map x
              baseColorFactor (blue): set the material colour to make other colours.
lollipop      a pumpkin painted with a rainbow swirl on a white stick, 1.6 m.
skewer        nine beach-ball-painted pumpkins on a white pole, 2.6 m.
cake-pop      a red glittery pumpkin dipped in green, on a stick, 1.4 m.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

Z = Vector((0, 0, 1))
BUCKET = dict(rx=1.10, rz=0.92, vcut=0.763, ribs=12)
SKEWER_RIBS = 10
CORN_H, CORN_W = 2.5, 0.55
CORN_BANDS = (0.40, 0.70)


def tex_uv(w, cols=32):
    """Maps (u, v) into the part of a texture left of its 32 px shared column."""
    k = (w - cols) / w

    def m(u, v):
        return (u * k, v)
    return m


def misc(w, kind):
    u = 1 - 16 / w
    return (u, 0.75) if kind == "white" else (u, 0.25)


def stick(mb, a, b, r, w, mat=0, n=10):
    uv = misc(w, "white")
    Loft([a, b], lambda t: {"rx": r, "ry": r}, n=n, seg=0.2, frame="up", up=Vector((0, 1, 0)),
         cap0="flat", cap1="dome", cap1_len=r).build(mb, uvmap=lambda s, q: uv, mat=mat)


def stem(mb, base, d, length, r, w, mat=0):
    uv = misc(w, "green")
    d = Vector(d).normalized()
    side = d.cross(Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))).normalized()
    pts = [base - d * 0.02, base + d * length * 0.5 + side * r * 0.3, base + d * length + side * r]
    Loft(pts, lambda t: {"rx": r * (1.3 - 0.4 * t), "ry": r * (1.3 - 0.4 * t)}, n=8, seg=0.01, frame="rmf",
         up=side, cap0="flat", cap1="dome", cap1_len=r * 0.5, offset=lambda t, a, s: r * 0.12 * math.cos(a * 6.283 * 5)
         ).build(mb, uvmap=lambda s, q: uv, mat=mat)


# --------------------------------------------------------------------------------------------

def bucket_face():
    eyeL = [(-0.52, 1.42), (-0.78, 1.11), (-0.49, 1.05)]
    eyeR = [(0.52, 1.42), (0.49, 1.05), (0.78, 1.11)]
    nose = [(0.0, 0.98), (-0.17, 0.66), (0.17, 0.66)]
    upper = [(x / 10 * 0.76, 0.52 - 0.15 * (1 - (x / 10) ** 2)) for x in range(-10, 11)]
    lower = [(0.73, 0.47), (0.58, 0.22), (0.40, 0.34), (0.20, 0.11), (0.0, 0.25), (-0.20, 0.11), (-0.40, 0.34),
             (-0.58, 0.22), (-0.73, 0.47)]
    return [eyeL, eyeR, nose, upper + lower]


def build_bucket():
    lib.reset()
    W = 2048
    b = BUCKET
    tex = TEX
    paint = lib.material("bucket_paint", base_tex=tex["bucket"], roughness=0.45, specular=0.45)
    black = lib.material("handle_black", color="#111113", roughness=0.4, metallic=0.3)
    glow = lib.material("glow_handle", base_tex=tex["handle"], emission_tex=tex["handle"], roughness=0.3)
    rx, rz, vcut, ribs = b["rx"], b["rz"], b["vcut"], b["ribs"]
    C = Vector((0, 0, rz))
    point = lib.pumpkin_surface(C, rx, rz, ribs=ribs, groove=0.06, groove_sharp=0.45, top_dimple=0.0,
                                bottom_dimple=0.05, wobble=0.015, seed=4, fullness=0.85)
    mb = MB()
    km = tex_uv(W)
    nu, nv = ribs * 6, 26
    vf = 0.30  # the inside floor

    def ring(v, scale=1.0):
        out = []
        for i in range(nu):
            p = point(i / nu, v)
            q = Vector((p.x * scale, p.y * scale, p.z))
            out.append(mb.v(q))
        return out
    rows = [[mb.v(point(0, 0))]] + [ring(j / nv * vcut) for j in range(1, nv + 1)]

    def ouv(u, v):
        return km(u, 0.25 + 0.75 * v / vcut)
    for j in range(nv):
        v0, v1 = j / nv * vcut, (j + 1) / nv * vcut
        for i in range(nu):
            i2 = (i + 1) % nu
            u0, u1 = i / nu, (i + 1) / nu
            if j == 0:
                mb.f((rows[0][0], rows[1][i2], rows[1][i]), [ouv((u0 + u1) / 2, v0), ouv(u1, v1), ouv(u0, v1)], None, 0)
            else:
                mb.f((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]),
                     [ouv(u0, v0), ouv(u1, v0), ouv(u1, v1), ouv(u0, v1)], None, 0)
    # inside wall (faces inward) and the floor
    nvi = 12
    inner = [ring(vf + (vcut - vf) * j / nvi, 0.94) for j in range(nvi + 1)]

    def iuv(u, v):
        return km(u, 0.24 * (v - vf) / (vcut - vf))
    for j in range(nvi):
        v0, v1 = vf + (vcut - vf) * j / nvi, vf + (vcut - vf) * (j + 1) / nvi
        for i in range(nu):
            i2 = (i + 1) % nu
            u0, u1 = i / nu, (i + 1) / nu
            mb.f((inner[j][i], inner[j + 1][i], inner[j + 1][i2], inner[j][i2]),
                 [iuv(u0, v0), iuv(u0, v1), iuv(u1, v1), iuv(u1, v0)], None, 0)
    fc = mb.v((0, 0, point(0, vf).z))
    for i in range(nu):
        i2 = (i + 1) % nu
        mb.f((fc, inner[0][i], inner[0][i2]), [km(0.5, 0.02), km(i / nu, 0.0), km((i + 1) / nu, 0.0)], None, 0)
    # rolled rim
    rim = []
    for i in range(nu):
        p = point(i / nu, vcut)
        rim.append(Vector((p.x * 0.97, p.y * 0.97, p.z + 0.005)))
    Loft(rim, lambda t: {"rx": 0.04, "ry": 0.035}, n=8, seg=0.05, closed=True, frame="up", up=Z).build(
        mb, uvmap=lambda s, a: ouv(s, vcut * 0.98), mat=0)
    body = mb.object("candy-bucket", [paint], origin=(0, 0, 0))
    # the handle: two posts down into the bucket and an arch, wound with a glowing tube
    hy, hw, z0, z1 = 0.05, 0.64, 0.95, 2.62
    path = [Vector((-hw, hy, z0)), Vector((-hw, hy, z1 - 0.4))]
    for k in range(25):
        a = math.pi - math.pi * k / 24
        path.append(Vector((hw * math.cos(a), hy, z1 + hw * math.sin(a) * 1.05)))
    path.append(Vector((hw, hy, z1 - 0.4)))
    path.append(Vector((hw, hy, z0)))
    hmb = MB()
    pole = Loft(path, lambda t: {"rx": 0.028, "ry": 0.028}, n=8, seg=0.05, frame="rmf", up=Vector((0, 1, 0)),
                cap0="flat", cap1="flat", res=8)
    pole.build(hmb, mat=0)
    spiral = []
    L = pole.L
    s = 0.02
    while s < L - 0.02:
        P, T, N, B = pole.frame_at(s / L)
        ang = math.tau * s / 0.14
        spiral.append(P + (N * math.cos(ang) + B * math.sin(ang)) * 0.043)
        s += 0.02
    Loft(spiral, lambda t: {"rx": 0.013, "ry": 0.013}, n=5, seg=0.04, frame="rmf", up=Z, res=4).build(
        hmb, uvmap=lambda s, a: (s, a), mat=1)
    pivot = Vector((0, hy, point(0, vcut).z))
    handle = hmb.object("handle", [black, glow], origin=pivot)
    lib.set_parent(handle, body)
    print(f"  candy-bucket: {lib.tri_count(body)} + handle {lib.tri_count(handle)} tris")
    lib.export("candy-bucket")


def build_corn():
    lib.reset()
    mat = lib.material("candy_corn", base_tex=TEX["corn"], roughness=0.6, specular=0.35)
    mb = MB()
    km = tex_uv(512)
    # straight tapered sides, tangent to a round tip
    rt = 0.17
    cz = CORN_H - rt
    th_t = 0.0
    for k in range(2000):   # the tangent point on the tip circle, seen from the bottom corner
        th = k / 2000 * math.pi / 2
        px, pz = rt * math.cos(th), cz + rt * math.sin(th)
        if (px - CORN_W) * math.cos(th) + pz * math.sin(th) <= 0:
            th_t = th
            break
    tx, tz = rt * math.cos(th_t), cz + rt * math.sin(th_t)
    right = [(CORN_W + (tx - CORN_W) * k / 24, tz * k / 24) for k in range(24)]
    arc = [(rt * math.cos(a), cz + rt * math.sin(a)) for a in
           [th_t + (math.pi - 2 * th_t) * k / 16 for k in range(17)]]
    outline = right + arc + [(-x, z) for x, z in reversed(right)]
    # bottom edge points (so the loop is closed along the base)
    outline = outline + [(-CORN_W * 0.5, 0.0), (0.0, 0.0), (CORN_W * 0.5, 0.0)]
    n = len(outline)
    th, ch = 0.14, 0.025

    def inset(i, d):
        x, z = outline[i]
        xp, zp = outline[i - 1]
        xn, zn = outline[(i + 1) % n]
        tx, tz = xn - xp, zn - zp
        L = math.hypot(tx, tz) or 1.0
        nx, nz = tz / L, -tx / L   # outward for a counter-clockwise loop
        return x - nx * d, z - nz * d
    # orientation: make the loop counter-clockwise seen from the front (-Y), i.e. in (x, z)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1] for i in range(n))
    if area < 0:
        outline.reverse()
    rings = []
    for y, d in ((-th / 2, ch), (-th / 2 + ch, 0.0), (th / 2 - ch, 0.0), (th / 2, ch)):
        rings.append([mb.v((inset(i, d)[0], y, max(inset(i, d)[1], 0.0))) for i in range(n)])

    def uvp(x, z):
        return km(0.5 + x / (2.2 * CORN_W), z / CORN_H)
    pts2 = {k: [inset(i, d) for i in range(n)] for k, d in ((0, ch), (1, 0.0))}
    for r in range(3):
        for i in range(n):
            i2 = (i + 1) % n
            a, b2 = outline[i], outline[i2]
            mb.f((rings[r][i], rings[r + 1][i], rings[r + 1][i2], rings[r][i2]),
                 [uvp(*a), uvp(*a), uvp(*b2), uvp(*b2)], None, 0)
    for r, flip in ((0, True), (3, False)):
        c = mb.v((0.0, -th / 2 if r == 0 else th / 2, CORN_H * 0.35))
        for i in range(n):
            i2 = (i + 1) % n
            p, q = pts2[0][i], pts2[0][i2]
            f = (c, rings[r][i], rings[r][i2]) if flip else (c, rings[r][i2], rings[r][i])
            u = [uvp(0, CORN_H * 0.35), uvp(*p), uvp(*q)] if flip else [uvp(0, CORN_H * 0.35), uvp(*q), uvp(*p)]
            mb.f(f, u, None, 0)
    o = mb.object("candy-corn", [mat], origin=(0, 0, 0), auto_smooth=40)
    print(f"  candy-corn: {lib.tri_count(o)} tris")
    lib.export("candy-corn")


def build_gummy():
    lib.reset()
    mat = lib.material("gummy", base_tex=TEX["gummy"], color_factor="#2f62e0", roughness=0.16, specular=0.65)
    mb = MB()
    km = tex_uv(512)
    dark = (0.04, 0.04)
    lib.pumpkin(mb, Vector((0, 0, 0.235)), 0.19, 0.21, ry=0.16, ribs=8, groove=0.06, nu=40, nv=16, seed=2,
                top_dimple=0.05, bottom_dimple=0.05, uvmap=lambda u, v: km(u, 0.15 + 0.7 * v))
    lib.pumpkin(mb, Vector((0, -0.01, 0.50)), 0.15, 0.125, ry=0.13, ribs=8, groove=0.06, nu=40, nv=14, seed=3,
                top_dimple=0.06, bottom_dimple=0.05, uvmap=lambda u, v: km(u, 0.15 + 0.7 * v))
    parts = [((0.10, 0.0, 0.60), 0.05, (1, 0.6, 1), 0), ((-0.10, 0.0, 0.60), 0.05, (1, 0.6, 1), 0),
             ((0.0, -0.12, 0.47), 0.06, (1, 0.7, 0.75), 0),
             ((0.165, -0.07, 0.30), 0.06, (0.8, 0.8, 1.4), 0.4), ((-0.165, -0.07, 0.30), 0.06, (0.8, 0.8, 1.4), -0.4),
             ((0.10, -0.10, 0.055), 0.07, (0.9, 1.2, 0.7), 0), ((-0.10, -0.10, 0.055), 0.07, (0.9, 1.2, 0.7), 0)]
    for i, (p, r, sc, tilt) in enumerate(parts):
        lib.lump(mb, Vector(p), r, sc, seed=10 + i, rough=0.06, nu=12, nv=8, M=Matrix.Rotation(tilt, 3, "Y"),
                 uvmap=lambda u, v: km(u, 0.2 + 0.6 * v), flat_bottom=False)
    for p, r in (((0.055, -0.118, 0.535), 0.016), ((-0.055, -0.118, 0.535), 0.016), ((0.0, -0.17, 0.485), 0.02)):
        lib.lump(mb, Vector(p), r, (1, 0.6, 1), seed=1, rough=0.0, nu=8, nv=5, uvmap=lambda u, v: dark,
                 flat_bottom=False)
    o = mb.object("gummy-bear", [mat], origin=(0, 0, 0))
    print(f"  gummy-bear: {lib.tri_count(o)} tris")
    lib.export("gummy-bear")


def build_lollipop():
    lib.reset()
    W = 1024
    mat = lib.material("lollipop", base_tex=TEX["lollipop"], roughness=0.35, specular=0.5)
    mb = MB()
    km = tex_uv(W)
    C = Vector((0, 0, 1.36))
    M = Matrix.Rotation(math.radians(90), 3, "X")   # stem pole toward the front (-Y)
    top = lib.pumpkin(mb, C, 0.25, 0.19, ribs=12, groove=0.07, nu=72, nv=20, M=M, seed=6, top_dimple=0.25,
                      bottom_dimple=0.12, uvmap=lambda u, v: km(u, v))
    stem(mb, top + Vector((0, 0.02, 0)), (0, -1, 0.1), 0.06, 0.022, W)
    stick(mb, Vector((0, 0.03, 0)), Vector((0, 0.03, 1.22)), 0.018, W)
    o = mb.object("lollipop", [mat], origin=(0, 0, 0))
    print(f"  lollipop: {lib.tri_count(o)} tris")
    lib.export("lollipop")


def build_skewer():
    lib.reset()
    W = 512
    mat = lib.material("skewer", base_tex=TEX["skewer"], roughness=0.4, specular=0.5)
    mb = MB()
    km = tex_uv(W)
    rng = lib.seeded(9)
    stick(mb, Vector((0, 0, 0)), Vector((0, 0, 2.6)), 0.02, W)
    for i in range(9):
        off = rng.randrange(SKEWER_RIBS) / SKEWER_RIBS
        r = rng.uniform(0.14, 0.16)
        lib.pumpkin(mb, Vector((0, 0, 0.40 + i * 0.25)), r, 0.112, ribs=SKEWER_RIBS, groove=0.08, nu=30, nv=10,
                    seed=20 + i, top_dimple=0.2, bottom_dimple=0.15,
                    M=Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "X") @ Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "Y")
                    @ Matrix.Rotation(off * math.tau, 3, "Z"),
                    uvmap=km)
    o = mb.object("skewer", [mat], origin=(0, 0, 0))
    print(f"  skewer: {lib.tri_count(o)} tris")
    lib.export("skewer")


def build_cakepop():
    lib.reset()
    W = 512
    mat = lib.material("cake_pop", base_tex=TEX["cakepop"], roughness=0.32, specular=0.7)
    mb = MB()
    km = tex_uv(W)
    top = lib.pumpkin(mb, Vector((0, 0, 1.12)), 0.20, 0.24, ribs=10, groove=0.07, nu=50, nv=18, seed=8,
                      top_dimple=0.15, bottom_dimple=0.1, profile=lambda v: (0.72 + 0.28 * min(1.0, v * 1.6), 1.0),
                      uvmap=lambda u, v: km(u, v))
    stem(mb, top, (0.1, 0, 1), 0.07, 0.022, W)
    uvg = misc(W, "green")
    for k in range(5):
        a = k * math.tau / 5
        lib.lump(mb, top + Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.005)), 0.035, (1.6, 0.8, 0.25), seed=k,
                 rough=0.2, nu=8, nv=4, M=Matrix.Rotation(a, 3, "Z"), uvmap=lambda u, v: uvg)
    stick(mb, Vector((0, 0, 0)), Vector((0, 0, 0.95)), 0.018, W)
    o = mb.object("cake-pop", [mat], origin=(0, 0, 0))
    print(f"  cake-pop: {lib.tri_count(o)} tris")
    lib.export("cake-pop")


TEX = None


def main():
    global TEX
    lib.reset()
    TEX = lib.paint("tex_candy.py", {"bucket": dict(BUCKET, face=bucket_face()), "corn_bands": list(CORN_BANDS),
                                     "skewer_ribs": SKEWER_RIBS},
                    {"bucket": "candy-bucket.jpg", "handle": "candy-handle.jpg", "corn": "candy-corn.jpg",
                     "gummy": "candy-gummy.jpg", "lollipop": "candy-lollipop.jpg", "skewer": "candy-skewer.jpg",
                     "cakepop": "candy-cakepop.jpg"})
    build_bucket()
    build_corn()
    build_gummy()
    build_lollipop()
    build_skewer()
    build_cakepop()


main()
