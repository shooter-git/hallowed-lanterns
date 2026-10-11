# SPDX-License-Identifier: MIT
"""The gourd snowman of October Snow (reference/snowman.jpg).

    blender -b --factory-startup -P tools/blender/snowman.py

Writes public/models/snowman.glb (about 2.6 m tall, on a 1.2 x 1.0 m pallet).

Three stacked carnival squashes (white with dark green stripes), a black top hat, a carrot nose,
coal eyes, smile and buttons, gnarled branch arms and clumps of snow, on a snowy pallet.

Nodes: `body` (root) with children `arm_L` and `arm_R` (pivots at the shoulders) and `mug`
(child of `arm_R`, pivot at the mug's centre). L/R are as seen from the front, as in the photo:
`arm_R` is on +X and holds the corn-cob mug; rotate it about its local Y axis (glTF Z... see
README) to raise the mug in a toast.
Materials: `gourd`, `snowman_props` (atlas: bark, pallet wood, corn, carrot, felt, coal), `snow`.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils import noise as mnoise  # noqa: E402

RIBS = 11
AW, AH = 2048, 1024
REGIONS = {  # props atlas, pixels, rows from the top
    "bark": (0, 0, 2048, 256),
    "bark_moss": (0, 256, 2048, 256),
    "wood": (0, 512, 1024, 512),
    "corn": (1024, 512, 512, 512),
    "carrot": (1536, 512, 256, 256),
    "felt": (1792, 512, 256, 256),
    "coal": (1536, 768, 256, 256),
}
Z_AXIS = Vector((0, 0, 1))


def region_uv(name, swap=False):
    x, y, w, h = REGIONS[name]

    def m(u, v):
        if swap:
            u, v = v, u
        return ((x + u * w) / AW, 1.0 - (y + (1.0 - v) * h) / AH)
    return m


GOURDS = [  # centre, rx, rz, rotation, u offset (whole ribs keep the stripes on the grooves), seed, nu, nv
    dict(center=(0, 0, 0.62), rx=0.62, rz=0.46, M=Matrix.Identity(3), off=0, seed=1, nu=RIBS * 8, nv=30,
         top_dimple=0.15, bottom_dimple=0.08),
    dict(center=(0, 0.02, 1.40), rx=0.45, rz=0.41, M=Matrix.Rotation(math.radians(3), 3, "X"), off=3, seed=2,
         nu=RIBS * 8, nv=28, top_dimple=0.15, bottom_dimple=0.10),
    dict(center=(0, 0.0, 1.99), rx=0.29, rz=0.26,
         M=Matrix.Rotation(math.radians(-14), 3, "Z") @ Matrix.Rotation(math.radians(4), 3, "Y"),
         off=7, seed=3, nu=RIBS * 6, nv=24, top_dimple=0.12, bottom_dimple=0.10),
]


def gourd_point(g):
    return lib.pumpkin_surface(Vector(g["center"]), g["rx"], g["rz"], ribs=RIBS, groove=0.085,
                               groove_sharp=0.42, top_dimple=g["top_dimple"], bottom_dimple=g["bottom_dimple"],
                               M=g["M"], wobble=0.035, seed=g["seed"], fullness=0.82)


def build_gourds(mb, mat):
    for g in GOURDS:
        off = g["off"] / RIBS
        lib.pumpkin(mb, Vector(g["center"]), g["rx"], g["rz"], ribs=RIBS, groove=0.085, groove_sharp=0.42,
                    top_dimple=g["top_dimple"], bottom_dimple=g["bottom_dimple"], M=g["M"], wobble=0.035,
                    seed=g["seed"], fullness=0.82, nu=g["nu"], nv=g["nv"], mat=mat,
                    uvmap=lambda u, v, off=off: (u + off, v))


def coal(mb, point, u, v, r, h, mat, seed):
    p = point(u, v)
    n = lib.surface_normal(point, u, v)
    rng = lib.seeded(seed)
    sq = rng.uniform(0.9, 1.1)

    def sec(t):
        return {"rx": r * sq, "ry": r / sq}

    def bumpy(t, a, s):
        return r * 0.06 * mnoise.noise(Vector((math.cos(a * 6.283) * 2, math.sin(a * 6.283) * 2, seed)))
    Loft([p - n * 0.02, p + n * h], sec, n=14, seg=h, frame="up", up=Z_AXIS if abs(n.z) < 0.9 else Vector((0, 1, 0)),
         cap0="flat", cap1="dome", cap1_len=h * 0.45, cap_rings=3, offset=bumpy).build(mb, uvmap=region_uv("coal"), mat=mat)


def build_face(mb, mat):
    head = gourd_point(GOURDS[2])
    for i, du in enumerate((-0.078, 0.078)):
        coal(mb, head, 0.75 + du, 0.655, 0.07, 0.035, mat, 10 + i)
    for i in range(6):
        f = i / 5
        u = 0.665 + f * 0.17
        v = 0.385 - 0.07 * (1 - ((u - 0.75) / 0.09) ** 2)
        coal(mb, head, u, v, 0.040 + 0.004 * math.sin(i * 2.1), 0.025, mat, 20 + i)
    # carrot nose
    p = head(0.745, 0.53)
    n = lib.surface_normal(head, 0.745, 0.53)
    side = n.cross(Z_AXIS).normalized()
    d = (n * 0.85 + side * 0.30 - Z_AXIS * 0.25).normalized()
    ctrl = [p - n * 0.03, p + d * 0.08, p + d * 0.16 + side * 0.01 - Z_AXIS * 0.008, p + d * 0.235 + side * 0.02 - Z_AXIS * 0.02]
    Loft(ctrl, lambda t: {"rx": 0.050 * (1 - 0.86 * t) + 0.004, "ry": 0.046 * (1 - 0.86 * t) + 0.004},
         n=14, seg=0.02, frame="up", up=Z_AXIS, cap0="flat", cap1="point", cap1_len=0.01,
         offset=lambda t, a, s: 0.003 * math.sin(t * 60)).build(mb, uvmap=region_uv("carrot", swap=True), mat=mat)
    mid = gourd_point(GOURDS[1])
    for i, v in enumerate((0.75, 0.53, 0.31)):
        coal(mb, mid, 0.75, v, 0.095, 0.045, mat, 30 + i)


def build_hat(mb, mat, snow_mb, snow_mat):
    base = Vector((0.01, 0.01, 2.165))
    M = Matrix.Rotation(math.radians(-7), 3, "X") @ Matrix.Rotation(math.radians(5), 3, "Y")
    up = M @ Z_AXIS
    felt = region_uv("felt")
    Loft([base, base + up * 0.022], lambda t: {"rx": 0.30, "ry": 0.30}, n=40, seg=0.03, frame="up",
         up=M @ Vector((0, 1, 0)), cap0="flat", cap1="flat").build(mb, uvmap=felt, mat=mat)
    Loft([base + up * 0.01, base + up * 0.42],
         lambda t: {"rx": 0.175 + 0.012 * t, "ry": 0.165 + 0.012 * t}, n=32, seg=0.05, frame="up",
         up=M @ Vector((0, 1, 0)), cap0="open", cap1="dome", cap1_len=0.018, cap_rings=3).build(mb, uvmap=felt, mat=mat)
    # snow: a cap on the crown and clumps on the brim
    top = base + up * 0.425
    lib.lump(snow_mb, top, 0.15, (1.15, 1.1, 0.28), seed=3, rough=0.22, nu=14, nv=6, M=M, mat=snow_mat)
    rng = lib.seeded(7)
    for k in range(6):
        ang = k * 1.1 + rng.uniform(-0.2, 0.2)
        rr = rng.uniform(0.21, 0.26)
        q = base + up * 0.03 + (M @ Vector((math.cos(ang), math.sin(ang), 0))) * rr
        lib.lump(snow_mb, q, rng.uniform(0.04, 0.06), (1.3, 1.0, 0.5), seed=40 + k, rough=0.3, nu=8, nv=5,
                 M=M @ Matrix.Rotation(ang, 3, "Z"), mat=snow_mat)


def gnarl(seed, amp=0.18):
    def off(t, a, s):
        r = s["rx"]
        q = Vector((math.cos(a * 6.283) * 0.6, math.sin(a * 6.283) * 0.6, t * 9 + seed))
        bump = 0.0
        for kt, ka in ((0.22, 0.3), (0.47, 0.8), (0.71, 0.55)):
            bump += 0.35 * math.exp(-((t - kt) / 0.035) ** 2) * max(0.0, math.cos((a - ka) * 6.283)) ** 2
        return r * (amp * mnoise.noise(q) + bump)
    return off


def branch(mb, ctrl, r0, r1, mat, uvname, seed, seg=0.025, n=12, cap1="dome", along_t0=0.0):
    keys = [(0, r0), (0.5, (r0 + r1) / 2 * 1.05), (1, r1)]
    loft = Loft(ctrl, lambda t: {"rx": lerp_keys(keys, t), "ry": lerp_keys(keys, t) * 0.92}, n=n, seg=seg,
                frame="up", up=Z_AXIS, cap0="dome", cap1=cap1, cap0_len=r0 * 0.6, cap1_len=r1 * 0.8,
                cap_rings=3, offset=gnarl(seed))
    loft.build(mb, uvmap=region_uv(uvname), mat=mat)
    return loft


def build_arm(side, mat, snow_mat):
    mb = MB()
    s = 1 if side == "R" else -1
    if side == "L":   # resting its claw of a hand on the bottom gourd
        ctrl = [(-0.34, 0.02, 1.55), (-0.62, -0.02, 1.52), (-0.92, -0.08, 1.34), (-0.98, -0.18, 1.14),
                (-0.74, -0.32, 1.00), (-0.48, -0.36, 0.95)]
        fingers = [((-0.48, -0.36, 0.95), [(0.10, -0.04, -0.02), (0.19, -0.07, -0.06), (0.26, -0.08, -0.13)]),
                   ((-0.49, -0.36, 0.95), [(0.07, -0.08, -0.03), (0.12, -0.15, -0.08), (0.15, -0.19, -0.16)]),
                   ((-0.52, -0.35, 0.96), [(0.02, -0.10, -0.01), (0.03, -0.18, -0.06), (0.03, -0.22, -0.14)]),
                   ((-0.58, -0.34, 0.97), [(0.02, -0.09, -0.05), (0.03, -0.15, -0.12), (0.02, -0.17, -0.20)])]
        uvname = "bark_moss"
    else:             # elbow out, forearm up, the hand around the mug
        ctrl = [(0.36, 0.02, 1.53), (0.64, 0.04, 1.49), (0.97, 0.06, 1.34), (1.04, -0.02, 1.52),
                (0.86, -0.14, 1.75), (0.66, -0.22, 1.83)]
        fingers = [((0.66, -0.22, 1.83), [(-0.05, -0.06, 0.03), (-0.12, -0.10, 0.04), (-0.18, -0.10, 0.06)]),
                   ((0.66, -0.22, 1.83), [(-0.04, 0.02, -0.03), (-0.10, 0.05, -0.05), (-0.17, 0.06, -0.04)]),
                   ((0.67, -0.21, 1.84), [(-0.03, -0.03, 0.08), (-0.08, -0.05, 0.14), (-0.13, -0.06, 0.15)])]
        uvname = "bark"
    loft = branch(mb, ctrl, 0.11, 0.06, mat, uvname, seed=1 if side == "L" else 2, seg=0.025, n=14)
    for i, (h, offs) in enumerate(fingers):
        h = Vector(h)
        pts = [h] + [h + Vector(o) for o in offs]
        branch(mb, pts, 0.036, 0.009, mat, "bark", seed=10 + i + (5 if side == "R" else 0), seg=0.02, n=8,
               cap1="point")
    # a small side twig
    bp = loft.surface(0.4, 0.5)[0]
    branch(mb, [bp, bp + Vector((0.02 * s, -0.06, 0.09)), bp + Vector((0.05 * s, -0.08, 0.17))], 0.022, 0.006,
           mat, "bark", seed=30 + (1 if side == "R" else 0), seg=0.02, n=6, cap1="point")
    # snow along the top of the upper arm (and the forearm on the left)
    rng = lib.seeded(50 if side == "L" else 60)
    ts = [0.12, 0.24, 0.36, 0.5, 0.64, 0.78] if side == "L" else [0.14, 0.27, 0.40, 0.52]
    for t in ts:
        p, n = loft.surface(t, 0.5)
        T = loft.frame_at(t)[1]
        ang = math.atan2(T.y, T.x)
        lib.lump(mb, p - Z_AXIS * 0.012, rng.uniform(0.065, 0.09), (1.6, 0.95, 0.85), seed=int(t * 100) + 7 * s,
                 rough=0.32, nu=10, nv=6, M=Matrix.Rotation(ang, 3, "Z"), mat=1)
    return mb, Vector(ctrl[0])


def build_mug(mat):
    mb = MB()
    c = Vector((0.49, -0.27, 1.86))
    h, r = 0.20, 0.098
    corn = region_uv("corn")
    Loft([c - Z_AXIS * h / 2, c + Z_AXIS * h / 2], lambda t: {"rx": r * (1 - 0.06 * (t - 0.5) ** 2 * 4), "ry": r},
         n=32, seg=0.02, frame="up", up=Vector((0, 1, 0)), cap0="flat", cap1="open").build(
             mb, uvmap=lambda s, a: corn(a, s), mat=mat)
    # rim and the cocoa inside
    Loft([c + Vector((r * 0.96 * math.cos(math.tau * i / 24), r * 0.96 * math.sin(math.tau * i / 24), h / 2))
          for i in range(24)], lambda t: {"rx": 0.008, "ry": 0.008}, n=6, seg=0.03, closed=True, frame="rmf",
         up=Z_AXIS).build(mb, uvmap=lambda s, a: corn(0.5, 0.05), mat=mat)
    Loft([c + Z_AXIS * (h / 2 - 0.03), c + Z_AXIS * (h / 2 - 0.029)], lambda t: {"rx": r * 0.95, "ry": r * 0.95},
         n=24, seg=0.01, frame="up", up=Vector((0, 1, 0)), cap0="open", cap1="flat").build(
             mb, uvmap=region_uv("coal"), mat=mat)
    # handle, on the side toward the hand
    hc = c + Vector((r + 0.03, 0.01, 0.0))
    pts = [hc + Vector((-0.03, 0, 0.06)), hc + Vector((0.02, 0, 0.055)), hc + Vector((0.035, 0, 0.0)),
           hc + Vector((0.02, 0, -0.055)), hc + Vector((-0.03, 0, -0.06))]
    Loft(pts, lambda t: {"rx": 0.013, "ry": 0.018}, n=8, seg=0.015, frame="up", up=Vector((0, 1, 0)),
         cap0="dome", cap1="dome").build(mb, uvmap=lambda s, a: corn(a, 0.5 + 0.1 * s), mat=mat)
    return mb, c


def build_base(mb, wood_mat, snow_mb, snow_mat):
    """A pallet (1.2 x 1.0 x 0.144 m) under a blanket of snow."""
    wood = REGIONS["wood"]
    rng = lib.seeded(77)

    def wood_uv(length):
        u0 = rng.uniform(0, max(0.0, 1.2 - length))
        v0 = rng.uniform(0.0, 0.5)

        def m(ax, fx, fy):
            x, y, w, h = wood
            if ax == 2 or ax == 1:   # top/bottom and the long sides: grain along local x
                u, v = (fx + length / 2 + u0) / 1.2, v0 + fy * 0.8 + 0.05
            else:
                u, v = 0.02 + (fy + 0.1) * 0.2, v0 + fx * 0.8
            return ((x + u * w) / AW, 1.0 - (y + (1 - v) * h) / AH)
        return m
    for i in range(7):   # top deck boards across x
        y = -0.45 + i * 0.15
        lib.beam(mb, (rng.uniform(-0.01, 0.01), y, 0.133), (1.2, 0.10, 0.022),
                 M=Matrix.Rotation(rng.uniform(-0.01, 0.01), 3, "Z"), chamfer=0.003, uv=wood_uv(1.2), mat=wood_mat)
    for x in (-0.55, 0.0, 0.55):  # stringers along y
        lib.beam(mb, (x, 0, 0.078), (1.0, 0.045, 0.09), M=Matrix.Rotation(math.pi / 2, 3, "Z"), chamfer=0.003,
                 uv=wood_uv(1.0), mat=wood_mat)
    for y in (-0.45, 0.0, 0.45):  # bottom boards
        lib.beam(mb, (0, y, 0.0165), (1.2, 0.10, 0.022), chamfer=0.003, uv=wood_uv(1.2), mat=wood_mat)
    # the snow blanket: lumpy, drifted up against the bottom gourd, drooping over the edges
    W, D = 1.30, 1.10
    off = Vector((3.1, 1.7, 0.4))

    def fn(u, v):
        x, y = (u - 0.5) * W, (v - 0.5) * D
        edge = min(u, 1 - u) * W, min(v, 1 - v) * D
        e = min(edge)
        r = math.hypot(x, y)
        z = 0.168 + 0.018 * mnoise.noise(Vector((x * 4, y * 4, 0)) + off) + 0.01 * mnoise.noise(Vector((x * 11, y * 11, 1)) + off)
        z += 0.07 * math.exp(-((r - 0.52) / 0.12) ** 2)
        if e < 0.07:
            z -= (0.07 - e) * 1.1
        return Vector((x, y, z))
    lib.grid_patch(snow_mb, fn, 40, 34, mat=snow_mat, outward=Z_AXIS)


def build_body_snow(snow_mb, snow_mat):
    rng = lib.seeded(91)
    mid = gourd_point(GOURDS[1])
    bot = gourd_point(GOURDS[0])
    places = [(mid, 0.50, 0.80, 0.15), (mid, 0.46, 0.70, 0.12), (mid, 0.57, 0.86, 0.11), (mid, 0.42, 0.88, 0.09),
              (mid, 0.02, 0.80, 0.12), (mid, 0.96, 0.72, 0.09), (mid, 0.08, 0.88, 0.08),
              (bot, 0.40, 0.84, 0.09), (bot, 0.16, 0.86, 0.08), (bot, 0.62, 0.88, 0.07)]
    for i, (pt, u, v, r) in enumerate(places):
        p = pt(u, v)
        n = lib.surface_normal(pt, u, v)
        up = (n + Z_AXIS * 1.5).normalized()
        R = up.to_track_quat("Z", "Y").to_matrix()
        lib.lump(snow_mb, p - n * 0.02, r, (1.5, 1.2, 0.6), seed=100 + i, rough=0.3, nu=10, nv=6, M=R, mat=snow_mat)


def main():
    lib.reset()
    tex = lib.paint("tex_snowman.py", {"ribs": RIBS, "regions": REGIONS},
                    {"gourd": "snowman-gourd.jpg", "gourd_n": "snowman-gourd-n.jpg",
                     "props": "snowman-props.jpg", "props_n": "snowman-props-n.jpg"})
    gourd = lib.material("gourd", base_tex=tex["gourd"], normal_tex=tex["gourd_n"], normal_strength=0.6,
                         roughness=0.62, specular=0.4)
    props = lib.material("snowman_props", base_tex=tex["props"], normal_tex=tex["props_n"], normal_strength=0.8,
                         roughness=0.75, specular=0.35)
    snow = lib.material("snow", color="#f4f7fb", roughness=0.85, specular=0.35)

    body = MB()
    build_gourds(body, 0)
    build_face(body, 1)
    snow_mb = MB()
    build_hat(body, 1, snow_mb, 2)
    build_base(body, 1, snow_mb, 2)
    build_body_snow(snow_mb, 2)
    body.extend(snow_mb)
    body_o = body.object("body", [gourd, props, snow], origin=(0, 0, 0))
    total = lib.tri_count(body_o)
    for side in ("L", "R"):
        amb, shoulder = build_arm(side, 0, 1)
        arm = amb.object("arm_" + side, [props, snow], origin=shoulder)
        lib.set_parent(arm, body_o)
        total += lib.tri_count(arm)
        if side == "R":
            mmb, c = build_mug(0)
            mug = mmb.object("mug", [props], origin=c)
            lib.set_parent(mug, arm)
            total += lib.tri_count(mug)
    print(f"  snowman: {total} tris")
    lib.export("snowman")


main()
