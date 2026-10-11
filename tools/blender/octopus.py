# SPDX-License-Identifier: MIT
"""The Keeper of the Deep: a giant octopus with a purple pumpkin for a mantle
(reference/octopus-1.jpg, octopus-2.jpg).

    blender -b --factory-startup -P tools/blender/octopus.py

Writes public/models/octopus.glb (about 6 m tall, 8 m across the arms).

Nodes: `body` (root: pumpkin mantle, stem, the head with its eye sockets) with children
`eye_L`, `eye_R` (pivots at the eyeball centres; the pupils look straight ahead, +Z in glTF, at
rest: aim the node to make the eye look at something) and `tentacle_0` ... `tentacle_7` (pivots
at the arm roots, inside the body). Every tentacle carries a second UV set (TEXCOORD_1, Blender
"along") whose u runs 0 at the root -> 1 at the tip, for bending in a vertex shader; the suckers
carry the `along` value of the place they sit.

Materials: `glow_uvpaint` (painted skin; its emissive map is the fluorescent paint: ring spots,
suckers, the piping along the arms, the stem) and `glow_eyes` (the orange pupils).
The surrounding fabric waves with LED dots are done in code.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

S = 2048
REGIONS = {  # x, y, w, h in pixels, rows from the top
    "pumpkin": (0, 0, 1024, 1024),
    "body": (1024, 0, 1024, 1024),
    "arm": (0, 1024, 2048, 768),
    "stem": (0, 1792, 512, 256),
    "sucker": (512, 1792, 256, 256),
}
RIBS = 10
PUMPKIN_C = Vector((0, 0.50, 3.92))
PUMPKIN_R = (1.75, 1.60, 1.36)
PUMPKIN_M = Matrix.Rotation(math.radians(10), 3, "Y") @ Matrix.Rotation(math.radians(-13), 3, "X")
SCALE = 1.1  # everything above is drawn at 1/SCALE; the Keeper stands about 6 m tall
BODY_C = Vector((0, -0.35, 2.30))
EYE_R = 0.34
# L/R as seen from the front (viewer's left/right), the convention of all these models: _R is on +X
EYES = {"eye_R": Vector((0.60, -1.12, 2.80)), "eye_L": Vector((-0.60, -1.12, 2.80))}


def region_uv(name):
    x, y, w, h = REGIONS[name]

    def m(u, v):
        return ((x + u * w) / S, 1.0 - (y + (1.0 - v) * h) / S)
    return m


# --------------------------------------------------------------------------------------------
# The head/body: a star-shaped smooth union of ellipsoids around BODY_C, spherical UVs
# --------------------------------------------------------------------------------------------

def blobs():
    out = [
        (Vector((0, -0.55, 2.35)), Vector((0.95, 0.80, 0.80))),   # head (between the eyes)
        (Vector((0, -0.20, 1.50)), Vector((1.00, 1.00, 0.55))),   # arm crown
        (Vector((0, 0.05, 2.95)), Vector((0.95, 0.85, 0.60))),    # neck into the mantle
        (Vector((0, -0.95, 1.85)), Vector((0.55, 0.50, 0.50))),   # chin/funnel
    ]
    for e in EYES.values():
        d = (BODY_C - e).normalized()
        out.append((e + d * 0.14, Vector((0.39, 0.39, 0.39))))   # eye sockets
    return out


BLOBS = blobs()


def body_radius(d, k=0.09):
    hits = []
    for c, r in BLOBS:
        q = Vector(((BODY_C.x - c.x) / r.x, (BODY_C.y - c.y) / r.y, (BODY_C.z - c.z) / r.z))
        e = Vector((d.x / r.x, d.y / r.y, d.z / r.z))
        A = e.dot(e)
        B = q.dot(e)
        Cq = q.dot(q) - 1
        disc = B * B - A * Cq
        if disc > 0:
            t = (-B + math.sqrt(disc)) / A
            if t > 0:
                hits.append(t)
    if not hits:
        return 0.3
    m = max(hits)
    return m + k * math.log(sum(math.exp((h - m) / k) for h in hits))


def body_dir(u, v):
    th = (u - 0.5) * math.tau
    ph = math.pi * v
    return Vector((math.sin(th) * math.sin(ph), -math.cos(th) * math.sin(ph), -math.cos(ph)))


def build_body(mb, mat):
    nu, nv = 72, 44
    uvm = region_uv("body")
    rows = []
    for j in range(nv + 1):
        v = j / nv
        if j in (0, nv):
            d = body_dir(0, v)
            rows.append([mb.v(BODY_C + d * body_radius(d))])
        else:
            row = []
            for i in range(nu):
                d = body_dir(i / nu, v)
                row.append(mb.v(BODY_C + d * body_radius(d)))
            rows.append(row)
    for j in range(nv):
        v0, v1 = j / nv, (j + 1) / nv
        for i in range(nu):
            u0, u1 = i / nu, (i + 1) / nu
            i2 = (i + 1) % nu
            # winding: u increases toward +X from the front, v upward -> (i, j), (i, j+1), ... outward
            if j == 0:
                mb.f((rows[0][0], rows[1][i2], rows[1][i]), [uvm((u0 + u1) / 2, v0), uvm(u1, v1), uvm(u0, v1)], None, mat)
            elif j == nv - 1:
                mb.f((rows[j][i], rows[j][i2], rows[nv][0]), [uvm(u0, v0), uvm(u1, v0), uvm((u0 + u1) / 2, v1)], None, mat)
            else:
                mb.f((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]),
                     [uvm(u0, v0), uvm(u1, v0), uvm(u1, v1), uvm(u0, v1)], None, mat)


# --------------------------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------------------------

# psi: direction (degrees from the front, + toward the octopus' left, +X); profile: (out, z)
# points in the arm's vertical plane; then a curl (length, start and end radius); sway: sideways.
ARMS = [
    (25, [(0.30, 1.60), (0.95, 1.80), (1.55, 1.45), (1.95, 0.70), (2.35, 0.24), (2.95, 0.20), (3.45, 0.24)], (1.7, 0.55, 0.12), 0.35),
    (-28, [(0.30, 1.60), (0.80, 2.00), (1.45, 2.20), (2.05, 1.80), (2.40, 0.95), (2.70, 0.30), (3.20, 0.20)], (1.5, 0.50, 0.10), -0.30),
    (72, [(0.30, 1.50), (1.00, 1.25), (1.80, 0.50), (2.60, 0.22), (3.40, 0.20), (3.90, 0.28)], (1.4, 0.45, 0.10), 0.30),
    (-76, [(0.30, 1.50), (1.10, 1.20), (1.90, 0.45), (2.70, 0.21), (3.30, 0.24)], (1.3, 0.42, 0.10), -0.25),
    (122, [(0.30, 1.60), (1.10, 1.20), (1.80, 0.70), (2.40, 0.88), (2.75, 1.80), (2.80, 2.90), (2.60, 3.80)], (1.6, 0.48, 0.10), 0.25),
    (-125, [(0.30, 1.60), (1.00, 1.15), (1.70, 0.68), (2.30, 0.95), (2.65, 1.90), (2.60, 2.90), (2.40, 3.40)], (1.5, 0.45, 0.10), -0.25),
    (160, [(0.30, 1.50), (1.00, 1.00), (1.70, 0.30), (2.50, 0.20), (3.10, 0.24)], (1.2, 0.40, 0.09), 0.30),
    (-163, [(0.30, 1.50), (1.00, 0.95), (1.80, 0.28), (2.50, 0.20), (3.00, 0.26)], (1.1, 0.38, 0.09), -0.30),
]
ARM_R0 = 0.42


def arm_radius(t):
    return ARM_R0 * (1 - 0.92 * t ** 1.6) + 0.01


def arm_ctrl(psi, profile, curl_spec, sway):
    a = math.radians(psi)
    out = Vector((math.sin(a), -math.cos(a), 0))
    n_p = Vector((math.cos(a), math.sin(a), 0))
    base = Vector((0, -0.05, 0))
    pts = []
    N = len(profile)
    for i, (r, z) in enumerate(profile):
        f = i / (N - 1)
        pts.append(base + out * r + Vector((0, 0, z)) + n_p * (sway * math.sin(math.pi * f)))
    head = (pts[-1] - pts[-2]).normalized()
    # ground arms curl up off the ground; rising arms curl over toward the body
    target = Vector((0, 0, 1)) if head.z < 0.7 else -out
    axis = head.cross(target).normalized()
    L, r0, r1 = curl_spec
    cpts = lib.curl(pts[-1], head, axis, L, r0, r1, step=0.05)
    pts += cpts[1::2]
    return pts, n_p


def sucker(mb, p, n, tdir, r, along, uvm, mat):
    """A raised ring sucker (a washer) on the skin at p, facing n."""
    n = n.normalized()
    x = (tdir - n * tdir.dot(n)).normalized()
    y = n.cross(x)
    seg = 8
    rings = {"ob": (1.0, -0.35, 0.48), "ot": (0.92, 0.30, 0.42), "it": (0.52, 0.30, 0.26), "ib": (0.42, 0.06, 0.18)}
    idx = {}
    for key, (rf, hf, uvr) in rings.items():
        idx[key] = []
        for i in range(seg):
            ang = math.tau * i / seg
            q = p + (x * math.cos(ang) + y * math.sin(ang)) * (r * rf) + n * (r * hf)
            idx[key].append((mb.v(q), (0.5 + uvr * math.cos(ang), 0.5 + uvr * math.sin(ang))))
    c = mb.v(p + n * (r * 0.02))
    al = (along, 1.0)  # glTF v = 0
    for a, b in (("ob", "ot"), ("ot", "it"), ("it", "ib")):
        for i in range(seg):
            j = (i + 1) % seg
            vs = [idx[a][i], idx[a][j], idx[b][j], idx[b][i]]
            mb.f([q[0] for q in vs], [uvm(*q[1]) for q in vs], [al] * 4, mat)
    for i in range(seg):
        j = (i + 1) % seg
        vs = [idx["ib"][i], idx["ib"][j]]
        mb.f([vs[0][0], vs[1][0], c], [uvm(*vs[0][1]), uvm(*vs[1][1]), uvm(0.5, 0.5)], [al] * 3, mat)


def build_arm(k, mat):
    psi, profile, curl_spec, sway = ARMS[k]
    pts, n_p = arm_ctrl(psi, profile, curl_spec, sway)
    root = pts[0]

    def sec(t):
        r = arm_radius(t)
        return {"rx": r * 1.04, "ry": r, "ry2": r * 0.96, "p": 2.0}
    loft = Loft(pts, sec, n=14, seg=0.05, frame="up", up=n_p, cap0="dome", cap1="point",
                cap0_len=0.25, cap1_len=0.03)
    mb = MB(along=True)
    loft.build(mb, uvmap=region_uv("arm"), mat=mat, along=True)
    mb.clamp_z(0.0)  # where the arm lies on the ground it flattens a little
    # suckers: two staggered rows near the root, one row toward the tip, on the a = 0.25 side
    uvs = region_uv("sucker")
    t = 0.10
    i = 0
    while t < 0.965:
        r = arm_radius(t)
        sr = r * (0.36 if r > 0.17 else 0.5)
        if r > 0.17:
            a = 0.25 + (0.055 if i % 2 == 0 else -0.055)
        else:
            a = 0.25
        p, n = loft.surface(t, a)
        tdir = loft.frame_at(t)[1]
        sucker(mb, p - n * 0.01, n, tdir, sr, t, uvs, mat)
        step = (sr * 1.25 if r > 0.17 else sr * 2.3) / loft.L
        t += step
        i += 1
    return mb, root


# --------------------------------------------------------------------------------------------

def build_pumpkin(mb, mat):
    uvm = region_uv("pumpkin")
    top = lib.pumpkin(mb, PUMPKIN_C, PUMPKIN_R[0], PUMPKIN_R[2], ry=PUMPKIN_R[1], ribs=RIBS, groove=0.13,
                      groove_sharp=0.45, top_dimple=0.30, bottom_dimple=0.10, nu=RIBS * 8, nv=34,
                      M=PUMPKIN_M, uvmap=uvm, mat=mat, wobble=0.04, seed=3)
    # stem: rises from the dimple, curving to the octopus' left and back
    up = PUMPKIN_M @ Vector((0, 0, 1))
    side = PUMPKIN_M @ Vector((1, 0, 0))
    back = PUMPKIN_M @ Vector((0, 1, 0))
    base = top - up * 0.10
    ctrl = [base, base + up * 0.32 + side * 0.04, base + up * 0.58 + side * 0.22 + back * 0.05,
            base + up * 0.72 + side * 0.48 + back * 0.10]

    def sec(t):
        r = lerp_keys([(0, 0.20), (0.15, 0.15), (0.6, 0.13), (1, 0.12)], t)
        return {"rx": r, "ry": r}

    def ridges(t, a, s):
        return 0.012 * math.cos(math.tau * 6 * a)
    stem = Loft(ctrl, sec, n=24, seg=0.04, frame="rmf", up=side, cap0="open", cap1="dome", cap1_len=0.05,
                offset=ridges)
    stem.build(mb, uvmap=region_uv("stem"), mat=mat)


def build_eye(name, mat):
    mb = MB()
    E = EYES[name]
    # sphere with its poles on Z, u = 0.75 looking at -Y (the front): the pupil is painted there
    lib.pumpkin(mb, E, EYE_R, EYE_R, ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0, nu=32, nv=18,
                fullness=1.0, mat=mat)
    return mb


def spots(seed, n, u_range, v_range, r_range, min_gap, metric):
    rng = lib.seeded(seed)
    out = []
    tries = 0
    while len(out) < n and tries < 5000:
        tries += 1
        u = rng.uniform(*u_range) % 1.0
        v = rng.uniform(*v_range)
        r = rng.uniform(*r_range)
        ok = True
        for (u2, v2, r2, *_rest) in out:
            if metric(u, v, u2, v2) < (r + r2) + min_gap:
                ok = False
                break
        if ok:
            out.append((u, v, r, rng.choice([5, 6, 7]), rng.uniform(0, 6.28)))
    return out


def main():
    lib.reset()
    PR = (PUMPKIN_R[0] + PUMPKIN_R[1]) / 2

    def pm(u, v, u2, v2):
        du = ((u - u2 + 0.5) % 1 - 0.5) * 2 * math.pi * PR * max(math.sin(math.pi * (v + v2) / 2), 0.2)
        return math.hypot(du, (v - v2) * math.pi * PUMPKIN_R[2])

    def bm(u, v, u2, v2):
        du = ((u - u2 + 0.5) % 1 - 0.5) * 2 * math.pi * 1.0 * max(math.sin(math.pi * (v + v2) / 2), 0.2)
        return math.hypot(du, (v - v2) * math.pi * 1.0)
    p_spots = spots(11, 14, (0.0, 1.0), (0.20, 0.86), (0.22, 0.33), 0.30, pm)
    b_spots = spots(12, 10, (0.15, 0.85), (0.30, 0.75), (0.10, 0.15), 0.18, bm)
    tex = lib.paint("tex_octopus.py", {"size": S, "regions": REGIONS, "ribs": RIBS,
                                       "pumpkin_r": [PR, (PUMPKIN_R[2] + PR) / 2], "body_r": 1.0,
                                       "pumpkin_spots": p_spots, "body_spots": b_spots},
                    {"base": "octopus-base.jpg", "emit": "octopus-emit.jpg",
                     "eye_base": "octopus-eye-base.jpg", "eye_emit": "octopus-eye-emit.jpg"})
    skin = lib.material("glow_uvpaint", base_tex=tex["base"], emission_tex=tex["emit"], roughness=0.55,
                        specular=0.4)
    eyes = lib.material("glow_eyes", base_tex=tex["eye_base"], emission_tex=tex["eye_emit"], roughness=0.25,
                        specular=0.6)

    SM = Matrix.Scale(SCALE, 4)
    mb = MB()
    build_body(mb, 0)
    build_pumpkin(mb, 0)
    mb.transform(SM)
    body = mb.object("body", [skin], origin=(0, 0, 0))
    print(f"  body: {lib.tri_count(body)} tris")
    for name in EYES:
        emb = build_eye(name, 0)
        emb.transform(SM)
        e = emb.object(name, [eyes], origin=EYES[name] * SCALE)
        lib.set_parent(e, body)
    total = lib.tri_count(body) + 2 * lib.tri_count(e)
    for k in range(len(ARMS)):
        amb, root = build_arm(k, 0)
        amb.transform(SM)
        o = amb.object(f"tentacle_{k}", [skin], origin=root * SCALE)
        lib.set_parent(o, body)
        total += lib.tri_count(o)
        print(f"  tentacle_{k}: {lib.tri_count(o)} tris")
    print(f"  total {total} tris")
    lib.export("octopus")


main()
