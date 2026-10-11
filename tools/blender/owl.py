# SPDX-License-Identifier: MIT
"""The great pumpkin owl (reference/owl.jpg): a huge orange pumpkin head with carved eyes, an
ivy-covered egg of a body studded with carved pumpkins (placed by the engine), and two enormous
wings of overlapping pale blue feather cut-outs.

    blender -b --factory-startup -P tools/blender/owl.py

Writes public/models/pumpkin-owl.glb: ~4.5 m tall, ~9.4 m across the wings.

Nodes: `owl` (root: the ivy body) -> `head` (pivot at the neck: pumpkin, carved eye sockets,
teal pupils, beak, ear tufts, curly stem), `wing_L` / `wing_R` (pivots at the shoulders; _R on
+X), and `body_spots` -> `spot_00` ... (where the engine puts glowing carved pumpkins: in glTF
each spot's local +Z points out of the body (the pumpkin's face), +Y up along the body; its
uniform scale is the suggested pumpkin diameter in metres).

Materials: `pumpkin_skin` (head), `ivy` (+ normal map), `glow_eyes` (sockets and pupils),
`glow_uv` (beak, ear tufts, stem), `glow_feathers` (the wings; double-sided).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402

V = Vector
BODY_C = V((0, 0.05, 1.50))
BODY_R = (0.92, 0.74, 1.52)
HEAD_C = V((0, -0.06, 3.56))
HEAD_R = (0.62, 0.56, 0.58)
NECK = V((0, 0.0, 2.98))
SHOULDER = V((0.80, 0.14, 2.62))


def egg_point(u, v):
    """The body: an egg, fullest a little above the middle, with leafy lumps."""
    th, ph = math.tau * u, math.pi * v
    k = 1.0 + 0.10 * math.sin(math.pi * v) * (v - 0.35)
    d = V((math.cos(th) * math.sin(ph), math.sin(th) * math.sin(ph), -math.cos(ph)))
    p = V((d.x * BODY_R[0] * k, d.y * BODY_R[1] * k, d.z * BODY_R[2]))
    bump = 1 + 0.035 * noise.noise(d * 3.0 + V((1.3, 2.1, 0.4))) + 0.02 * noise.noise(d * 7.0)
    q = BODY_C + p * bump
    if q.z < 0:
        q.z = 0.0
    return q


def eyes_uv(rect):
    x0, y0, w, h = rect

    def m(u, v):
        return ((x0 + u * w) / 512, 1 - (y0 + (1 - v) * h) / 512)
    return m


UV_SOCKET = eyes_uv((0, 0, 256, 512))
UV_PUPIL = eyes_uv((256, 0, 256, 256))


def lime(u, v):
    return (0.75, 0.35)


def teal(u, v):
    return (0.75, 0.10)


def dish(mb, p, n, r, depth, uvm, mat, up=V((0, 0, 1)), nu=24, nv=5):
    """A round dish (depth > 0 sinks in, < 0 bulges out) facing n, planar UVs."""
    n = n.normalized()
    x = up.cross(n).normalized()
    y = n.cross(x)
    rows = []
    for j in range(nv + 1):
        f = j / nv
        rr = r * (1 - f)
        z = -depth * math.sin(f * math.pi / 2)
        if j == nv:
            rows.append([(mb.v(p + n * z), (0.5, 0.5))])
            continue
        rows.append([(mb.v(p + (x * math.cos(a) + y * math.sin(a)) * rr + n * z),
                      (0.5 + 0.5 * (1 - f) * math.cos(a), 0.5 + 0.5 * (1 - f) * math.sin(a)))
                     for a in (math.tau * i / nu for i in range(nu))])
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            vs = [rows[j][i], rows[j][i2], rows[nv][0]] if j == nv - 1 else [rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]]
            mb.f([q[0] for q in vs], [uvm(*q[1]) for q in vs], None, mat)


def build_head(mats):
    mb = MB()
    kw = dict(ribs=12, groove=0.08, groove_sharp=0.45, top_dimple=0.26, bottom_dimple=0.18, wobble=0.03, seed=4)
    lib.pumpkin(mb, HEAD_C, HEAD_R[0], HEAD_R[2], ry=HEAD_R[1], nu=72, nv=28, uvmap=lambda u, v: (u, 0.25 + 0.75 * v),
                mat=mats["skin"], **kw)
    pt = lib.pumpkin_surface(HEAD_C, HEAD_R[0], HEAD_R[2], ry=HEAD_R[1], **kw)
    rx, ry, rz = HEAD_R

    def front(x, z, lift=0.0):
        """The skin point seen straight from the front at (x, z), and its normal."""
        q = 1 - (x / rx) ** 2 - ((z - HEAD_C.z) / rz) ** 2
        d = V((x / rx, -math.sqrt(max(q, 0.0)), (z - HEAD_C.z) / rz))
        u = (math.atan2(d.y, d.x) / math.tau) % 1.0
        v = math.acos(min(max(-d.z, -1.0), 1.0)) / math.pi
        n = lib.surface_normal(pt, u, v)
        return pt(u, v) + n * lift, n
    # carved eye sockets: the cut follows the skin, the glowing flesh dish sinks in behind it,
    # a rim of skin round it; the teal pupils sit low and toward the beak
    er, ez = 0.25, HEAD_C.z + 0.10
    for sx in (-1, 1):
        ex = sx * 0.265
        nu, nv = 28, 5
        rows = []
        for j in range(nv + 1):
            f = j / nv
            row = []
            for i in range(nu):
                a = math.tau * i / nu
                x, z = ex + er * math.cos(a), ez + er * math.sin(a)
                # the glowing flesh follows the skin (the pumpkin is not cut), just proud of it
                p, _ = front(ex + er * (1 - f) * math.cos(a), ez + er * (1 - f) * math.sin(a), 0.012)
                row.append((mb.v(p), (0.5 + 0.5 * (1 - f) * math.cos(a), 0.5 + 0.5 * (1 - f) * math.sin(a))))
            rows.append(row)
        for j in range(nv):
            for i in range(nu):
                i2 = (i + 1) % nu
                vs = [rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]]
                mb.f([q[0] for q in vs], [UV_SOCKET(*q[1]) for q in vs], None, mats["eyes"])
        ring = [front(ex + (er + 0.012) * math.cos(a), ez + (er + 0.012) * math.sin(a), 0.006)[0]
                for a in (math.tau * i / 30 for i in range(30))]
        Loft(ring, lambda t: {"rx": 0.026, "ry": 0.02}, n=6, seg=0.06, closed=True, frame="rmf", up=V((0, -1, 0))).build(
            mb, uvmap=lambda s_, a: (s_, 0.3), mat=mats["skin"])
        pc, _ = front(ex - sx * 0.05, ez - 0.07, 0.0)
        dish(mb, pc, V((sx * 0.15, -1, -0.1)), 0.125, -0.07, UV_PUPIL, mats["eyes"])
    # beak: a green three-sided wedge pointing down between the eyes
    tl, _ = front(-0.12, ez - 0.02, -0.01)
    tr, _ = front(0.12, ez - 0.02, -0.01)
    tip, _ = front(0.0, ez - 0.36, 0.0)
    apex = (tl + tr) / 2 * 0.45 + tip * 0.55 + V((0, -0.16, 0.0))
    tip = tip + V((0, -0.05, 0))
    ids = [mb.v(q) for q in (tl, tr, tip, apex)]
    pts_ = (tl, tr, tip, apex)
    for tri_ in ((3, 0, 1), (3, 1, 2), (3, 2, 0)):
        a_, b_, c_ = (pts_[k] for k in tri_)
        nrm = (b_ - a_).cross(c_ - a_)
        if nrm.dot((a_ + b_ + c_) / 3 - HEAD_C) < 0:
            tri_ = (tri_[0], tri_[2], tri_[1])
        mb.f([ids[k] for k in tri_], [lime(0, 0)] * 3, None, mats["uv"])
    # ear tufts: pointed green horns at the top corners, leaning out
    for sx in (-1, 1):
        u, v = 0.75 + sx * 0.16, 0.86
        p = pt(u, v)
        n = lib.surface_normal(pt, u, v)
        d = (V((sx * 0.45, -0.1, 1.0))).normalized()
        Loft([p - n * 0.05, p + d * 0.18, p + d * 0.36 + V((sx * 0.04, 0, 0))],
             lambda t: {"rx": 0.11 * (1 - 0.92 * t), "ry": 0.05 * (1 - 0.8 * t)}, n=10, seg=0.04, frame="up",
             up=V((0, -1, 0)), cap0="flat", cap1="point", cap1_len=0.02).build(mb, uvmap=lime, mat=mats["uv"])
    # the curly stem
    top = pt(0, 1.0)
    pts = [top - V((0, 0, 0.06)), top + V((0, 0.01, 0.12))]
    pts += lib.curl(pts[-1], V((0.1, 0, 1)), V((0, -1, 0)), 0.55, 0.16, 0.05, step=0.03)[::2]
    Loft(pts, lambda t: {"rx": 0.065 * (1 - 0.6 * t), "ry": 0.06 * (1 - 0.6 * t)}, n=8, seg=0.03, frame="rmf",
         up=V((0, -1, 0)), cap0="open", cap1="dome", cap1_len=0.02,
         offset=lambda t, a, s: 0.008 * math.cos(math.tau * 5 * a)).build(mb, uvmap=teal, mat=mats["uv"])
    return mb


def feather(mb, P, out, up_dir, normal, length, width, curl, mat, rng):
    """One flat pointed feather cut-out: base at P, pointing along `out` (in the wing plane)."""
    out = out.normalized()
    side = normal.cross(out).normalized()
    pts = []
    n = 9
    for i in range(n + 1):
        t = i / n
        f = math.sin(math.pi * (0.16 + 0.84 * t)) ** 0.75
        if t > 0.92:
            f *= (1 - t) / 0.08 * 0.6 + 0.0
        c = P + out * (length * t) + normal * (curl * t * t)
        sag = side * (-0.06 * width * t * t)
        pts.append((c + sag + side * (0.5 * width * f), c + sag - side * (0.45 * width * f), t))
    ids = [(mb.v(a), mb.v(b), t) for a, b, t in pts]
    for i in range(n):
        a0, b0, t0 = ids[i]
        a1, b1, t1 = ids[i + 1]
        uv = [(t0, 0.02), (t0, 0.98), (t1, 0.98), (t1, 0.02)]
        mb.f((a0, b0, b1, a1), [(uv[0][0], 1 - uv[0][1]), (uv[1][0], 1 - uv[1][1]), (uv[2][0], 1 - uv[2][1]),
                                (uv[3][0], 1 - uv[3][1])], None, mat)


def wing_edges(s):
    """Top and bottom of the wing (z, metres) at s metres out from the shoulder."""
    top = 3.05 + 0.95 * (s / 3.9) ** 1.2 - 0.25 * max(0.0, (s - 3.5) / 0.4) ** 2
    bot = 0.95 + 1.05 * (s / 3.9) ** 1.4 + 0.5 * max(0.0, (s - 3.3) / 0.6) ** 2
    return top, bot


def build_wing(sx, mat, seed):
    rng = lib.seeded(seed)
    mb = MB()
    cols = 12
    S_MAX = 3.9
    for c in range(cols):
        s = 0.05 + (S_MAX - 0.45) * c / (cols - 1)
        top, bot = wing_edges(s)
        step = 0.27
        z = bot + 0.05 + (step / 2 if c % 2 else 0.0)
        row = 0
        while z < top:
            f = (z - bot) / max(top - bot, 1e-3)
            ang = math.radians(-32 + 70 * f ** 1.6 + rng.uniform(-8, 8))
            ln = rng.uniform(0.66, 0.80) * (1.0 + 0.12 * s / S_MAX)
            wd = rng.uniform(0.32, 0.40)
            # the wing plane sweeps a little forward toward the tips and is cupped
            depth = -0.022 * (cols - c) - 0.006 * (row % 3) - 0.10 * (s / S_MAX) ** 1.5
            base = V((sx * (SHOULDER.x + s), SHOULDER.y - 0.18 * s / S_MAX + depth, z))
            out = V((sx * math.cos(ang), -0.08 * math.cos(ang), math.sin(ang)))
            normal = V((0, -1, 0))
            feather(mb, base, out, V((0, 0, 1)), normal, ln, wd, rng.uniform(-0.05, 0.02), mat, rng)
            z += step + rng.uniform(-0.02, 0.02)
            row += 1
    # a ragged fringe of spiky feathers along the top edge, pointing up and out
    for i in range(15):
        s = 0.2 + (S_MAX - 0.2) * i / 14
        top, _ = wing_edges(s)
        ang = math.radians(rng.uniform(42, 72))
        base = V((sx * (SHOULDER.x + s), SHOULDER.y - 0.18 * s / S_MAX - 0.10, top - 0.15))
        out = V((sx * math.cos(ang), -0.05, math.sin(ang)))
        feather(mb, base, out, V((0, 0, 1)), V((0, -1, 0)), rng.uniform(0.6, 0.75), rng.uniform(0.28, 0.34), -0.03, mat, rng)
    return mb


def spot_matrix(p, n):
    """An empty at p whose glTF +Z (Blender -Y) points along n and glTF +Y (Blender +Z) up."""
    n = n.normalized()
    up = V((0, 0, 1)) - n * n.z
    up = up.normalized() if up.length > 1e-6 else V((0, 1, 0))
    yb = -n
    zb = up
    xb = yb.cross(zb).normalized()
    return Matrix((xb, yb, zb)).transposed().to_4x4()


def main():
    lib.reset()
    skin_t = lib.paint_named("tex_pirates.py", {"kind": "pumpkin", "ribs": 12, "color": "#f29a4c", "groove": "#c0682a",
                                         "stem": "#3a8a6a", "seed": 6}, {"tex": "owl-pumpkin.jpg"})["tex"]
    eye_t = lib.paint_named("tex_owl.py", {"kind": "eyes"}, {"tex": "owl-eyes.jpg"})["tex"]
    ivy = lib.paint_named("tex_owl.py", {"kind": "ivy", "seed": 7}, {"color": "owl-ivy.jpg", "normal": "owl-ivy-n.jpg"})
    fea_t = lib.paint_named("tex_owl.py", {"kind": "feather"}, {"tex": "owl-feather.jpg"})["tex"]
    m_skin = lib.material("pumpkin_skin", base_tex=skin_t, roughness=0.55, specular=0.35)
    m_ivy = lib.material("ivy", base_tex=ivy["color"], normal_tex=ivy["normal"], roughness=0.7, specular=0.3)
    m_eyes = lib.material("glow_eyes", base_tex=eye_t, emission_tex=eye_t, roughness=0.4, specular=0.4)
    m_uv = lib.material("glow_uv", base_tex=eye_t, emission_tex=eye_t, roughness=0.5, specular=0.3)
    m_fea = lib.material("glow_feathers", base_tex=fea_t, emission_tex=fea_t, roughness=0.65, specular=0.3, double_sided=True)
    # body
    mb = MB()
    lib.grid_patch(mb, egg_point, 64, 36, uvmap=lambda u, v: (u * 5, v * 4), mat=0, closed_u=True,
                   outward=lambda u, v: egg_point(u, v) - BODY_C)
    body = mb.object("owl", [m_ivy], origin=(0, 0, 0), auto_smooth=70)
    total = lib.tri_count(body)
    hm = build_head({"skin": 0, "eyes": 1, "uv": 2})
    head = hm.object("head", [m_skin, m_eyes, m_uv], origin=NECK, auto_smooth=50)
    lib.set_parent(head, body)
    total += lib.tri_count(head)
    for sx, name, seed in ((1, "wing_R", 11), (-1, "wing_L", 12)):
        wm = build_wing(sx, 0, seed)
        w = wm.object(name, [m_fea], origin=V((sx * SHOULDER.x, SHOULDER.y, SHOULDER.z)))
        lib.set_parent(w, body)
        total += lib.tri_count(w)
    # pumpkin spots in rows round the front and sides of the body
    spots = lib.empty("body_spots", parent=body)
    k = 0
    rows = [(0.30, 0.40), (0.68, 0.44), (1.06, 0.46), (1.44, 0.46), (1.82, 0.45), (2.20, 0.42), (2.56, 0.38)]
    for j, (z, size) in enumerate(rows):
        v = math.acos(min(max(-(z - BODY_C.z) / BODY_R[2], -1), 1)) / math.pi
        ring_r = egg_point(0.75, v) - V((0, 0, egg_point(0.75, v).z))
        circ_r = (abs(egg_point(0.75, v).y - BODY_C.y) + abs(egg_point(0.0, v).x)) / 2
        span = math.radians(118)
        n_s = max(2, int(2 * span * circ_r / (size + 0.06)))
        for i in range(n_s + 1):
            az = -span + 2 * span * i / n_s + (0.5 * (size + 0.06) / circ_r if j % 2 else 0.0)
            if az > span + 1e-3:
                continue
            u = 0.75 + az / math.tau
            p = egg_point(u, v)
            n = lib.surface_normal(egg_point, u, v)
            e = lib.empty(f"spot_{k:02d}", parent=spots)
            e.matrix_world = Matrix.Translation(p + n * size * 0.28) @ spot_matrix(p, n) @ Matrix.Scale(size, 4)
            k += 1
    hi = max(v[2] for v in hm.verts)
    print(f"  pumpkin-owl: {total} tris, {k} spots, top {hi:.2f} m")
    lib.export("pumpkin-owl")


if __name__ == "__main__":
    main()
