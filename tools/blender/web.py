# SPDX-License-Identifier: MIT
"""The Web: the giant pumpkin spider, the neon praying mantis and a web-wrapped pumpkin
(reference/spider.jpg, reference/video-9602.mov). The cobweb curtains are drawn in code.

    blender -b --factory-startup -P tools/blender/web.py [-- only=spider,mantis,webpumpkin]

Writes public/models/pumpkin-spider.glb, praying-mantis.glb and web-pumpkin.glb.

pumpkin-spider (body ~2.9 m tall, legs spanning ~7 m): a dark maroon pumpkin abdomen painted
with neon lightning patches, a second pumpkin for the head with two domed pink spiral eyes and
pale fangs, eight wooden-looking legs (dark femur, a dark knee segment with cream polka dots,
a pale mustard lower leg and a round foot) and a little green baby spider on its back.
Nodes: `spider` (root: both pumpkins, eyes, fangs) -> `leg_0` ... `leg_7` (the femurs, pivots at
the leg roots in the body; 0-3 on the spider's right = viewer's left... see README) -> `tibia_<k>`
(the rest of the leg, pivot at the knee) -> empty `foot_<k>` (the foot's centre); and `baby`
(pivot where it sits). Materials: `glow_uvpaint` (base 2048 + emission 1024: the neon paint,
the pale legs), `glow_eyes` (the spirals).

praying-mantis (~3.2 m with its antennae): a neon lime foam-tube mantis sitting up on its
mid and hind legs, forelegs raised and folded, an orange gourd abdomen resting on the ground,
big orange eyes. Nodes: `mantis` (root: the mesothorax and the four legs it stands on) ->
`abdomen` (pivot where it joins the thorax), `thorax` (the prothorax, pivot at its base) ->
`foreleg_L/_R` (coxa, pivot at the shoulder) -> `femur_L/_R` (pivot at the elbow) -> `tibia_L/_R`
(the claw, pivot at the knee); `thorax` -> `head` (pivot at the neck: head, eyes, palps) ->
`antenna_L/_R` (pivots at their roots). Materials `glow_uv` (lime and the orange abdomen;
emission = base) and `glow_eyes`.

web-pumpkin (0.5 m): a tan pumpkin wrapped in stretched cobweb strands, threads rising to a
`hang_point`, and two tiny neon-green spiders. Materials `pumpkin_skin`, `glow_web`, `glow_uv`.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

ARGS = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
ONLY = set(ARGS["only"].split(",")) if "only" in ARGS else None
V = Vector


def pumpkin_uv(S, rect):
    x, y, w, h = rect

    def m(u, v):
        return ((x + u * w) / S, 1 - (y + (1 - v) * h) / S)
    return m


def strip_uv(S, rect, s0=0.0, s1=1.0):
    x, y, w, h = rect

    def m(s, a):
        ss = s0 + (s1 - s0) * min(max(s, 0.0), 1.0)
        return ((x + ss * w) / S, 1 - (y + (a % 1.0) * h) / S)
    return m


def planar_uv(S, rect):
    x, y, w, h = rect

    def m(u, v):
        return ((x + u * w) / S, 1 - (y + (1 - v) * h) / S)
    return m


def dome(mb, p, n, r, h, uvm, mat, nu=20, nv=4, tangent=V((1, 0, 0))):
    """A shallow lens on the surface at p facing n; planar UVs across it (u along `tangent`)."""
    n = n.normalized()
    x = (tangent - n * tangent.dot(n)).normalized()
    y = n.cross(x)
    rows = []
    for j in range(nv + 1):
        f = j / nv                   # 0 = rim, 1 = centre
        rr = r * math.cos(f * math.pi / 2)
        z = h * math.sin(f * math.pi / 2) - 0.01
        if j == nv:
            rows.append([(mb.v(p + n * z), (0.5, 0.5))])
            continue
        row = []
        for i in range(nu):
            a = math.tau * i / nu
            row.append((mb.v(p + (x * math.cos(a) + y * math.sin(a)) * rr + n * z),
                        (0.5 + 0.5 * math.cos(a) * rr / r, 0.5 + 0.5 * math.sin(a) * rr / r)))
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            if j == nv - 1:
                vs = [rows[j][i], rows[j][i2], rows[nv][0]]
            else:
                vs = [rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]]
            mb.f([q[0] for q in vs], [uvm(*q[1]) for q in vs], None, mat)


# --------------------------------------------------------------------------------------------
# Pumpkin spider
# --------------------------------------------------------------------------------------------

S2 = 2048
R_ABD = (0, 0, 1024, 1024)
R_HEAD = (1024, 0, 1024, 768)
R_STEM = (1024, 768, 1024, 256)
R_LEG = (0, 1024, 1024, 256)
R_FANG = (0, 1280, 256, 256)
R_BABY_H = (256, 1280, 512, 384)
R_BABY_B = (768, 1280, 512, 384)
R_PALE = (1280, 1280, 256, 256)

ABD = {"c": V((0, 0.80, 2.02)), "rx": 1.22, "ry": 1.08, "rz": 0.86}
HEAD = {"c": V((0, -0.52, 1.56)), "rx": 0.76, "ry": 0.68, "rz": 0.56}
LEG_ROOT_C = V((0, 0.10, 1.48))
# azimuth from the front (deg, + toward +X), knee lift, reach (how far out the foot lands)
LEGS = [(38, 1.02, 3.35), (74, 1.00, 3.55), (108, 0.96, 3.45), (146, 0.90, 3.15),
        (-38, 1.04, 3.30), (-74, 0.98, 3.50), (-108, 0.95, 3.50), (-146, 0.92, 3.20)]


def stem(mb, top, up, uvm, mat, length=0.35, r=0.09, bend=V((0.1, 0.05, 0))):
    ctrl = [top - up * 0.08, top + up * (length * 0.5) + bend * 0.3, top + up * length + bend]
    Loft(ctrl, lambda t: {"rx": r * (1 - 0.25 * t), "ry": r * (1 - 0.25 * t)}, n=10, seg=0.05, frame="up",
         up=V((0, -1, 0)), cap0="open", cap1="flat",
         offset=lambda t, a, s: r * 0.12 * math.cos(math.tau * 6 * a)).build(mb, uvmap=uvm, mat=mat)


def leg_points(az, lift, reach):
    a = math.radians(az)
    o = V((math.sin(a), -math.cos(a), 0))
    R = LEG_ROOT_C + o * 0.55
    K = R + o * 1.30 + V((0, 0, lift))
    Q = K + o * 0.55 + V((0, 0, -0.62))
    F = V((o.x * reach, o.y * reach + 0.1, 0.10))
    return R, K, Q, F, o


def build_leg(az, lift, reach, mat):
    """Two parts so the leg can bend: the femur (hip to knee) and the rest (knee to foot)."""
    R, K, Q, F, o = leg_points(az, lift, reach)
    femur = MB()
    lower = MB()
    up = o.cross(V((0, 0, 1))).normalized()

    def sq(r0, r1, p=3.0):
        return lambda t: {"rx": r0 + (r1 - r0) * t, "ry": (r0 + (r1 - r0) * t) * 0.85, "p": p}
    Loft([R - o * 0.25, R.lerp(K, 0.5) + V((0, 0, 0.12)), K], sq(0.11, 0.095), n=8, seg=0.12, frame="up", up=up,
         cap0="flat", cap1="dome", cap1_len=0.06).build(femur, uvmap=strip_uv(S2, R_LEG, 0.0, 0.42), mat=mat)
    Loft([K - (Q - K).normalized() * 0.05, Q], sq(0.095, 0.09), n=8, seg=0.1, frame="up", up=up,
         cap0="dome", cap1="dome", cap0_len=0.05, cap1_len=0.05).build(lower, uvmap=strip_uv(S2, R_LEG, 0.42, 0.62), mat=mat)
    Loft([Q + (F - Q).normalized() * -0.04, Q.lerp(F, 0.5) + o * 0.03, F + V((0, 0, 0.05))], sq(0.08, 0.072, 2.0),
         n=10, seg=0.12, frame="up", up=up, cap0="dome", cap1="flat", cap0_len=0.05).build(
             lower, uvmap=strip_uv(S2, R_LEG, 0.62, 1.0), mat=mat)
    lib.lump(lower, F + V((0, 0, 0.0)), 1.0, scale=(0.11, 0.11, 0.09), seed=int(az) % 7, rough=0.06, nu=10, nv=6,
             uvmap=strip_uv(S2, R_LEG, 0.97, 1.0), mat=mat, flat_bottom=True)
    lower.clamp_z(0.0)
    return femur, lower, R, K, F


def build_spider():
    lib.reset()
    tex = lib.paint_named("tex_web.py", {"kind": "spider"}, {"base": "web-spider.jpg", "emit": "web-spider-e.jpg"})
    eye_t = lib.paint_named("tex_web.py", {"kind": "eyes"}, {"tex": "web-spider-eye.jpg"})["tex"]
    skin = lib.material("glow_uvpaint", base_tex=tex["base"], emission_tex=tex["emit"], roughness=0.55, specular=0.35)
    eyes = lib.material("glow_eyes", base_tex=eye_t, emission_tex=eye_t, roughness=0.35, specular=0.5)
    mb = MB()
    ribs = 10
    kw_a = dict(ribs=ribs, groove=0.12, groove_sharp=0.45, top_dimple=0.28, bottom_dimple=0.12, wobble=0.04, seed=3)
    lib.pumpkin(mb, ABD["c"], ABD["rx"], ABD["rz"], ry=ABD["ry"], nu=ribs * 8, nv=30, uvmap=pumpkin_uv(S2, R_ABD), mat=0, **kw_a)
    pa = lib.pumpkin_surface(ABD["c"], ABD["rx"], ABD["rz"], ry=ABD["ry"], **kw_a)
    stem(mb, pa(0, 1.0), V((0, 0.15, 1)).normalized(), strip_uv(S2, R_STEM), 0, length=0.42, r=0.11, bend=V((0.0, 0.12, 0)))
    kw_h = dict(ribs=ribs, groove=0.12, groove_sharp=0.45, top_dimple=0.26, bottom_dimple=0.14, wobble=0.03, seed=5)
    lib.pumpkin(mb, HEAD["c"], HEAD["rx"], HEAD["rz"], ry=HEAD["ry"], nu=ribs * 8, nv=26, uvmap=pumpkin_uv(S2, R_HEAD), mat=0, **kw_h)
    ph = lib.pumpkin_surface(HEAD["c"], HEAD["rx"], HEAD["rz"], ry=HEAD["ry"], **kw_h)
    stem(mb, ph(0, 1.0), V((0, -0.1, 1)).normalized(), strip_uv(S2, R_STEM), 0, length=0.36, r=0.09, bend=V((0.02, -0.02, 0)))
    # spiral eyes: domed discs on the face
    for du in (-0.072, 0.072):
        u, v = 0.75 + du, 0.60
        p = ph(u, v)
        n = lib.surface_normal(ph, u, v)
        n = (n + V((0, -0.35, 0))).normalized()
        dome(mb, p, n, 0.235, 0.085, planar_uv(512, (0, 0, 512, 512)), 1, tangent=V((1, 0, 0)))
    # fangs: two pale rounded blocks under the face
    for sx in (-1, 1):
        u, v = 0.75 + sx * 0.028, 0.22
        p = ph(u, v)
        n = lib.surface_normal(ph, u, v)
        c = p + n * 0.02 + V((0, -0.04, -0.06))
        lib.lump(mb, c, 1.0, scale=(0.115, 0.075, 0.13), seed=sx + 3, rough=0.05, nu=10, nv=6,
                 M=Matrix.Rotation(math.radians(-20), 3, "X"), uvmap=planar_uv(S2, R_FANG), mat=0, flat_bottom=False)
    body = mb.object("spider", [skin, eyes], origin=(0, 0, 0), auto_smooth=60)
    total = lib.tri_count(body)
    for k, (az, lift, reach) in enumerate(LEGS):
        fm, lm, R, K, F = build_leg(az, lift, reach, 0)
        leg = fm.object(f"leg_{k}", [skin], origin=R, auto_smooth=50)
        lib.set_parent(leg, body)
        tibia = lm.object(f"tibia_{k}", [skin], origin=K, auto_smooth=50)
        lib.set_parent(tibia, leg)
        lib.empty(f"foot_{k}", location=F, parent=tibia)
        total += lib.tri_count(leg) + lib.tri_count(tibia)
    # the baby on the abdomen's front-left shoulder
    u, v = 0.66, 0.80
    base = pa(u, v)
    n = lib.surface_normal(pa, u, v)
    bm = MB()
    fwd = V((0.25, -1, -0.15)).normalized()
    side = fwd.cross(n).normalized()
    bc = base + n * 0.20
    kw_b = dict(ribs=8, groove=0.10, top_dimple=0.2, bottom_dimple=0.2, seed=7)
    Mb = Matrix((side, -fwd, n)).transposed()
    lib.pumpkin(bm, bc - fwd * 0.10, 0.25, 0.21, nu=40, nv=14, M=Mb, uvmap=pumpkin_uv(S2, R_BABY_B), mat=0, **kw_b)
    hc = bc + fwd * 0.25 + n * 0.08
    lib.pumpkin(bm, hc, 0.21, 0.19, nu=40, nv=14, M=Matrix((side, -fwd, n)).transposed(), uvmap=pumpkin_uv(S2, R_BABY_H),
                mat=0, ribs=8, groove=0.10, top_dimple=0.2, bottom_dimple=0.2, seed=8)
    for i in range(6):
        s = -1 if i < 3 else 1
        k = i % 3
        root = bc + side * (s * 0.19) + fwd * (0.08 - 0.11 * k)
        d = (side * s * 0.8 - n * 0.5 + fwd * (0.4 - 0.3 * k)).normalized()
        pts = lib.curl(root, d, (fwd * s).normalized(), 0.52, 0.24, 0.07, step=0.03)
        Loft([root] + pts[::2], lambda t: {"rx": 0.03 * (1 - 0.5 * t), "ry": 0.03 * (1 - 0.5 * t)}, n=6, seg=0.04,
             frame="rmf", up=n, cap0="dome", cap1="dome", cap0_len=0.02, cap1_len=0.012).build(
                 bm, uvmap=strip_uv(S2, R_PALE), mat=0)
    baby = bm.object("baby", [skin], origin=base, auto_smooth=50)
    lib.set_parent(baby, body)
    total += lib.tri_count(baby)
    print(f"  pumpkin-spider: {total} tris")
    return lib.export("pumpkin-spider")


# --------------------------------------------------------------------------------------------
# Praying mantis
# --------------------------------------------------------------------------------------------

S1 = 1024
M_TUBE = (0, 0, 1024, 256)
M_SPINE = (0, 256, 1024, 256)
M_ANT = (0, 512, 1024, 128)
M_ABD = (0, 640, 1024, 384)
NECK = V((0, -0.30, 2.12))
PRO = V((0, -0.08, 1.30))   # the base of the prothorax, where it sits in the mesothorax


def tube(mb, pts, r0, r1, rect=M_TUBE, mat=0, n=10, caps=("dome", "dome"), up=None):
    pts = [V(p) for p in pts]
    d = (pts[-1] - pts[0]).normalized()
    if up is None:
        up = V((0, 0, 1)) if abs(d.z) < 0.85 else V((0, -1, 0))
    L = sum((b - a).length for a, b in zip(pts, pts[1:]))
    Loft(pts if len(pts) > 2 else [pts[0], pts[0].lerp(pts[1], 0.5), pts[1]],
         lambda t: {"rx": r0 + (r1 - r0) * t, "ry": r0 + (r1 - r0) * t}, n=n, seg=max(L / 10, 0.05), frame="up", up=up,
         cap0=caps[0], cap1=caps[1], cap0_len=r0 * 0.8, cap1_len=r1 * 0.8, cap_rings=3).build(mb, uvmap=strip_uv(S1, rect), mat=mat)


def knob(mb, p, r, mat=0):
    lib.pumpkin(mb, p, r, r, ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0, nu=10, nv=6, fullness=1.0,
                uvmap=lambda u, v: strip_uv(S1, M_TUBE)(0.02, v), mat=mat)


def build_mantis():
    lib.reset()
    tex = lib.paint_named("tex_web.py", {"kind": "mantis"}, {"tex": "web-mantis.jpg"})["tex"]
    eye_t = lib.paint_named("tex_web.py", {"kind": "mantis_eye"}, {"tex": "web-mantis-eye.jpg"})["tex"]
    uvm = lib.material("glow_uv", base_tex=tex, emission_tex=tex, roughness=0.6, specular=0.3)
    eyes = lib.material("glow_eyes", base_tex=eye_t, emission_tex=eye_t, roughness=0.3, specular=0.5)
    mb = MB()
    # abdomen: an orange segmented gourd resting on the ground behind
    abm = MB()
    ab = [V((0, 0.22, 1.08)), V((0, 0.62, 0.92)), V((0, 1.05, 0.62)), V((0, 1.45, 0.34)), V((0, 1.72, 0.22))]
    Loft(ab, lambda t: {"rx": lerp_keys([(0, 0.20), (0.3, 0.33), (0.6, 0.31), (1, 0.12)], t),
                        "ry": lerp_keys([(0, 0.20), (0.3, 0.30), (0.6, 0.28), (1, 0.11)], t)},
         n=16, seg=0.05, frame="up", up=V((0, 0, 1)), cap0="dome", cap1="dome", cap0_len=0.12, cap1_len=0.1,
         offset=lambda t, a, s: 0.035 * math.cos(math.tau * 6 * t) if 0.05 < t < 0.95 else 0.0).build(
             abm, uvmap=strip_uv(S1, M_ABD), mat=0)
    abm.clamp_z(0.0)
    # thorax: a short mesothorax (with the legs) and the long prothorax rising to the neck, which
    # rocks and lunges on its own
    tube(mb, [V((0, 0.25, 1.10)), V((0, 0.02, 1.20)), V((0, -0.10, 1.32))], 0.15, 0.13)
    thm = MB()
    tube(thm, [PRO, V((0, -0.18, 1.72)), NECK + V((0, 0.02, -0.04))], 0.12, 0.10)
    # forelegs: coxa down to the elbow, the spined femur back up, the tibia folded down in front;
    # each joint its own node so the strike can open and snap shut
    forelegs = []
    for sx in (-1, 1):
        S = V((sx * 0.10, -0.20, 1.86))
        K1 = V((sx * 0.30, -0.58, 1.12))
        K2 = V((sx * 0.20, -0.66, 1.86))
        K3 = V((sx * 0.17, -0.82, 1.36))
        T = V((sx * 0.15, -0.86, 1.20))
        cm, fm, tm = MB(), MB(), MB()
        tube(cm, [S, K1], 0.075, 0.08)
        knob(cm, K1, 0.10)
        tube(fm, [K1, K2], 0.10, 0.075, rect=M_SPINE, up=V((sx, 0, 0)))
        knob(fm, K2, 0.08)
        tube(tm, [K2, K3], 0.06, 0.05, rect=M_SPINE, up=V((sx, 0, 0)))
        tube(tm, [K3, T], 0.045, 0.03)
        forelegs.append((sx, (cm, S), (fm, K1), (tm, K2)))
    # mid legs: out and up to a high knee, then down to the ground; hind legs the same, further back
    for sx in (-1, 1):
        for (root, knee, foot, toe, r) in (
                (V((sx * 0.12, -0.02, 1.16)), V((sx * 0.78, -0.55, 1.36)), V((sx * 1.18, -0.95, 0.06)), V((sx * 1.30, -1.12, 0.03)), 0.075),
                (V((sx * 0.12, 0.22, 1.10)), V((sx * 0.95, 0.30, 1.62)), V((sx * 1.62, 0.20, 0.07)), V((sx * 1.82, 0.30, 0.03)), 0.08)):
            tube(mb, [root, knee], r, r * 0.9)
            knob(mb, knee, r * 1.15)
            tube(mb, [knee, foot], r * 0.9, r * 0.75)
            knob(mb, foot, r * 0.95)
            tube(mb, [foot, toe], r * 0.7, r * 0.5, caps=("dome", "dome"))
    body = mb.object("mantis", [uvm], origin=(0, 0, 0), auto_smooth=50)
    abdomen = abm.object("abdomen", [uvm], origin=ab[0], auto_smooth=50)
    lib.set_parent(abdomen, body)
    thorax = thm.object("thorax", [uvm], origin=PRO, auto_smooth=50)
    lib.set_parent(thorax, body)
    parts = [body, abdomen, thorax]
    for sx, *joints in forelegs:
        parent = thorax
        for (jm, at), name in zip(joints, ("foreleg", "femur", "tibia")):
            o = jm.object(f"{name}_{'R' if sx > 0 else 'L'}", [uvm], origin=at, auto_smooth=50)
            lib.set_parent(o, parent)
            parts.append(o)
            parent = o
    total = sum(lib.tri_count(o) for o in parts)
    # head: a downward triangle, wide at the eyes, a pointed mouth, antennae, palps and a fuzzy collar
    hm = MB()
    antennae = []
    hpath = [NECK + V((0, -0.13, -0.04)), NECK + V((0, -0.12, 0.16)), NECK + V((0, -0.10, 0.36))]

    def hsec(t):
        return {"rx": lerp_keys([(0, 0.07), (0.45, 0.20), (0.8, 0.29), (1, 0.26)], t),
                "ry": lerp_keys([(0, 0.08), (0.5, 0.12), (1, 0.13)], t), "p": 2.4}
    Loft(hpath, hsec, n=16, seg=0.04, frame="up", up=V((0, -1, 0)), cap0="dome", cap1="dome", cap0_len=0.05,
         cap1_len=0.10, cap_rings=4).build(hm, uvmap=strip_uv(S1, M_TUBE, 0.3, 0.7), mat=0)
    eye_c = []
    for sx in (-1, 1):
        c = NECK + V((sx * 0.29, -0.13, 0.34))
        eye_c.append(c)
        lib.pumpkin(hm, c, 0.17, 0.175, ry=0.15, ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0, nu=18, nv=10,
                    fullness=1.0, uvmap=lambda u, v: (0.5 + 0.45 * math.cos(math.tau * u) * math.sin(math.pi * v),
                                                       0.5 + 0.45 * math.cos(math.pi * v)), mat=1)
        # antenna: up from between the eyes, arching out (its own node, pivot at its root)
        a0 = NECK + V((sx * 0.06, -0.16, 0.44))
        pts = [a0, a0 + V((sx * 0.06, 0.02, 0.25)), a0 + V((sx * 0.22, 0.06, 0.55)), a0 + V((sx * 0.48, 0.10, 0.75)),
               a0 + V((sx * 0.74, 0.12, 0.80))]
        am = MB()
        Loft(pts, lambda t: {"rx": 0.026 - 0.01 * t, "ry": 0.026 - 0.01 * t}, n=6, seg=0.06, frame="up", up=V((0, -1, 0)),
             cap0="dome", cap1="dome", cap0_len=0.02, cap1_len=0.015).build(am, uvmap=strip_uv(S1, M_ANT), mat=0)
        antennae.append((sx, am, a0))
        # fuzzy palps at the mouth
        lib.lump(hm, NECK + V((sx * 0.08, -0.22, -0.02)), 0.075, scale=(1, 1, 0.9), seed=sx + 11, rough=0.35, nu=10, nv=6,
                 uvmap=lambda u, v: strip_uv(S1, M_TUBE)(0.5, u), mat=0, flat_bottom=False)
    # a fuzzy collar at the neck
    lib.lump(hm, NECK + V((0, -0.02, -0.05)), 0.13, scale=(1.3, 1.0, 0.7), seed=17, rough=0.3, nu=12, nv=6,
             uvmap=lambda u, v: strip_uv(S1, M_TUBE)(0.5, u), mat=0, flat_bottom=False)
    # a dark mouth dot is the shadow under the palps
    head = hm.object("head", [uvm, eyes], origin=NECK, auto_smooth=50)
    lib.set_parent(head, thorax)
    total += lib.tri_count(head)
    for sx, am, a0 in antennae:
        o = am.object(f"antenna_{'R' if sx > 0 else 'L'}", [uvm], origin=a0, auto_smooth=50)
        lib.set_parent(o, head)
        total += lib.tri_count(o)
    hi = max(max(v[2] for v in hm.verts), max(v[2] for _, am, _ in antennae for v in am.verts))
    print(f"  praying-mantis: {total} tris, top {hi:.2f} m")
    return lib.export("praying-mantis")


# --------------------------------------------------------------------------------------------
# Web-wrapped pumpkin
# --------------------------------------------------------------------------------------------

def tiny_spider(mb, p, n, fwd, mat, s=1.0):
    n = n.normalized()
    f = (fwd - n * fwd.dot(n)).normalized()
    side = f.cross(n)
    lib.lump(mb, p + n * 0.012 * s - f * 0.02 * s, 1.0, scale=(0.022 * s, 0.03 * s, 0.016 * s),
             M=Matrix((side, f, n)).transposed(), seed=3, rough=0.05, nu=8, nv=5, mat=mat, flat_bottom=False)
    lib.lump(mb, p + n * 0.01 * s + f * 0.018 * s, 1.0, scale=(0.014 * s, 0.016 * s, 0.011 * s),
             M=Matrix((side, f, n)).transposed(), seed=4, rough=0.05, nu=6, nv=4, mat=mat, flat_bottom=False)
    for sx in (-1, 1):
        for k in range(4):
            a = math.radians(-50 + 33 * k)
            root = p + n * 0.01 * s + f * 0.012 * s
            out = (side * sx * math.cos(a) + f * math.sin(a)).normalized()
            knee = root + out * 0.03 * s + n * 0.02 * s
            tip = root + out * 0.06 * s - n * 0.004 * s
            Loft([root, knee, tip], lambda t: {"rx": 0.0028 * s, "ry": 0.0028 * s}, n=4, seg=0.02 * s, frame="up", up=n,
                 cap0="flat", cap1="flat").build(mb, mat=mat)


def build_webpumpkin():
    lib.reset()
    tex = lib.paint_named("tex_web.py", {"kind": "webpumpkin", "ribs": 9}, {"tex": "web-pumpkin.jpg"})["tex"]
    skin = lib.material("pumpkin_skin", base_tex=tex, roughness=0.6, specular=0.3)
    web = lib.material("glow_web", color="#e6e0f2", emission="#c8c0ff", emission_strength=0.3, roughness=0.8,
                       double_sided=True)
    neon = lib.material("glow_uv", color="#7cff3a", emission="#7cff3a", emission_strength=1.0, roughness=0.5)
    rx, rz = 0.25, 0.22
    C = V((0, 0, rz * 0.95))
    kw = dict(ribs=9, groove=0.10, groove_sharp=0.45, top_dimple=0.28, bottom_dimple=0.2, wobble=0.05, seed=12)
    mb = MB()
    lib.pumpkin(mb, C, rx, rz, nu=54, nv=18, uvmap=lambda u, v: (u, 0.25 + 0.75 * v), mat=0, **kw)
    pt = lib.pumpkin_surface(C, rx, rz, **kw)
    hull0 = lib.pumpkin_surface(C, rx * 1.03, rz * 1.03, **dict(kw, groove=0.0))

    def hull(u, v):
        return hull0(u % 1.0, min(max(v, 0.02), 0.98))
    top = pt(0, 1.0)
    Loft([top - V((0, 0, 0.03)), top + V((0.005, 0, 0.04)), top + V((0.02, 0.01, 0.07))],
         lambda t: {"rx": 0.028 - 0.006 * t, "ry": 0.025}, n=7, seg=0.03, frame="up", up=V((0, -1, 0)),
         cap0="open", cap1="flat").build(mb, uvmap=lambda s, a: (a, 0.25 * (1 - s)), mat=0)
    rng = lib.seeded(21)

    def ribbon(pts, w, mat=1):
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            d = (b - a)
            if d.length < 1e-6:
                continue
            nrm = (a - C).normalized()
            side = d.normalized().cross(nrm) * w
            ids = [mb.v(a - side), mb.v(a + side), mb.v(b + side), mb.v(b - side)]
            mb.f(ids, [(0, 0), (1, 0), (1, 1), (0, 1)], None, mat)
    # strands wrapped round, bridging the grooves (stretched over the ribs): many fine ones and a
    # few broader bands of stretched webbing
    for k in range(42):
        u0, v0 = rng.random(), rng.uniform(0.12, 0.92)
        u1, v1 = u0 + rng.uniform(-0.4, 0.4), rng.uniform(0.12, 0.95)
        pts = [hull(u0 + (u1 - u0) * i / 12, v0 + (v1 - v0) * i / 12) for i in range(13)]
        ribbon(pts, rng.uniform(0.0015, 0.004) if k % 6 else rng.uniform(0.008, 0.014))
    # threads rising to the hang point
    hp = top + V((0.0, 0.0, 0.42))
    for k in range(5):
        a = math.tau * k / 5 + 0.3
        start = hull(a / math.tau, 0.80)
        mid = start.lerp(hp, 0.5) + V((0.01 * math.cos(a), 0.01 * math.sin(a), 0))
        ribbon([start, mid, hp], 0.003)
    # two tiny neon spiders
    for (u, v, fu) in ((0.70, 0.55, 0.3), (0.86, 0.38, -0.5)):
        p = pt(u, v)
        n = lib.surface_normal(pt, u, v)
        tiny_spider(mb, p, n, V((math.cos(fu), 0, math.sin(fu) + 0.6)), 2, s=1.0)
    obj = mb.object("web_pumpkin", [skin, web, neon], origin=(0, 0, 0), auto_smooth=50)
    lib.empty("hang_point", location=hp, parent=obj)
    print(f"  web-pumpkin: {lib.tri_count(obj)} tris")
    return lib.export("web-pumpkin")


def main():
    for key, fn in (("spider", build_spider), ("mantis", build_mantis), ("webpumpkin", build_webpumpkin)):
        if ONLY is None or key in ONLY:
            fn()


if __name__ == "__main__":
    main()
