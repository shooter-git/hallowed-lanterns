# SPDX-License-Identifier: MIT
"""The giant fly-eating Venus flytrap of Sweet Hollow (reference/venus-flytrap.jpg): a huge trap
head (2.6 m across) leaning out over the path on a thick curving stem from a rosette of leaves,
half-closed on a giant fly, vines trailing from it; two smaller traps lower down for scale.

    blender -b --factory-startup -P tools/blender/venus-flytrap.py

Writes public/models/venus-flytrap.glb: 3.4 x 4.1 x 3.1 m (glTF x, y, z; the head's top 4.1 m
up, its underside 2.7 m). The origin is the middle of the rosette on the ground; the big head
leans out over the front (glTF +Z).

Trap design (all three traps): two lobes hinged on a midrib that runs along the trap's local X;
the mouth opens toward local -Y in Blender (glTF +Z), the upper lobe above, the lower below.
Each lobe: a cupped half-disc shell, teal-green outside with eight segments radiating from the
hinge (`trap_outer`, base colour + a dim emission), deep red inside (`glow_trap`), and along
its rim a row of long pale teeth (`teeth`) curving across the gap; the two rows interlock.
The lobes are modelled half-open, 13 deg each side of the closed plane (16 on the small traps).

Nodes (axes below are glTF / three.js; the hinge is the same X axis in Blender):
- `venus_flytrap` (root: main stem, small traps' stems, rosette leaves)
  - `trap` (pivot at the middle of the hinge; midrib and the trailing vines)
    - `lobe_upper`, `lobe_lower`: pivots on the hinge line. Rotating about their local X closes
      them: lobe_upper by +13 deg, lobe_lower by -13 deg (opposite signs open them wider).
    - `fly` (pivot in its thorax) -> `wing_L`, `wing_R` (pivots at the wing roots: flap them
      about their local Z in glTF, which is the fly's body axis)
  - `trap_small_1`, `trap_small_2` (pivots at their hinges) -> `trap_small_<n>_upper`,
    `trap_small_<n>_lower` (same rule: upper +X closes, lower -X closes, 16 deg each)

Materials: `stem`, `leaf`, `trap_outer`, `glow_trap`, `teeth`, `fly_body`, `fly_wing` (alpha
BLEND, double-sided), `vine` (alpha MASK, double-sided).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

V = Vector
STEM, LEAF, OUTER, GLOW, TEETH, FLY, WING, VINE = range(8)


# --------------------------------------------------------------------------------------------
# UV regions
# --------------------------------------------------------------------------------------------

def uv_outer(a, r):
    return (a, 1 - (2 + r * 506) / 1024)


def uv_inner(a, r):
    return (a, 1 - (514 + r * 378) / 1024)


def uv_teeth(s, a):
    return (min(max(s, 0.0), 1.0), 1 - (898 + (a % 1.0) * 124) / 1024)


def uv_stem(s, a):
    return (s, 1 - (2 + (a % 1.0) * 252) / 1024)


def uv_leaf(s, w):
    return (s, 1 - (260 + w * 504) / 1024)


def uv_midrib(s, a):
    return (s, 1 - (770 + (a % 1.0) * 250) / 1024)


def uv_body(u, v):
    return (u, 1 - (2 + v * 252) / 512)


def uv_eye(u, v):
    return ((2 + u * 252) / 512, 1 - (258 + (1 - v) * 252) / 512)


def uv_wing(u, v):
    return ((258 + u * 252) / 512, 1 - (258 + (1 - v) * 252) / 512)


# --------------------------------------------------------------------------------------------
# Traps
# --------------------------------------------------------------------------------------------

class Lobe:
    """A cupped half-disc on the hinge (local X): angle a in [0, pi] round it (0 and pi on the
    hinge), r in [0, 1] from the hinge's middle to the rim. sgn +1 upper, -1 lower."""

    def __init__(self, sgn, phi, HX, W, B, t, segs=8, groove=0.10):
        self.sgn, self.phi, self.HX, self.W, self.B, self.t = sgn, phi, HX, W, B, t
        self.segs, self.groove = segs, groove
        self.d = V((0, -math.cos(phi), sgn * math.sin(phi)))       # chord, hinge -> rim
        self.n = V((0, math.sin(phi), sgn * math.cos(phi)))        # outward (the convex side)

    def point(self, a, r, inner=False):
        px = self.HX * math.cos(a) * r
        pw = self.W * math.sin(a) * r
        b = self.B * (1 - r * r) * (r * math.sin(a)) ** 0.5
        if not inner:
            f = ((a / math.pi) * self.segs) % 1.0
            b -= self.groove * self.B * math.exp(-(min(f, 1 - f) / 0.07) ** 2) * min(1.0, r / 0.25) * (1 - r * r) ** 0.3
        p = V((px, 0, 0)) + self.d * pw + self.n * b
        if inner:
            p -= self.n * self.t * (0.35 + 0.65 * math.sin(math.pi * min(r, 1.0)) ** 0.3)
        return p

    def build(self, mb, na, nr, n_teeth, tooth_len, tooth_r, teeth_phase):
        def patch(inner, mat, uvm):
            rows = [[mb.v(self.point(0, 0, inner))]]
            for j in range(1, nr + 1):
                r = j / nr
                rows.append([mb.v(self.point(math.pi * i / na, r, inner)) for i in range(na + 1)])
            # outward = +n for the outer skin, -n for the inner one (facing into the mouth)
            flip = inner

            def face(ids, uvs):
                if flip:
                    ids, uvs = ids[::-1], uvs[::-1]
                mb.f(ids, uvs, None, mat)
            for i in range(na):
                a0, a1 = i / na, (i + 1) / na
                face([rows[0][0], rows[1][i + 1], rows[1][i]], [uvm((a0 + a1) / 2, 0), uvm(a1, 1 / nr), uvm(a0, 1 / nr)])
            for j in range(1, nr):
                for i in range(na):
                    a0, a1, r0, r1 = i / na, (i + 1) / na, j / nr, (j + 1) / nr
                    face([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]],
                         [uvm(a0, r0), uvm(a1, r0), uvm(a1, r1), uvm(a0, r1)])
            return rows
        out = patch(False, OUTER, uv_outer)
        inn = patch(True, GLOW, uv_inner)
        # the rim band and the two hinge edges close the shell
        for i in range(na):
            o0, o1, i0, i1 = out[nr][i], out[nr][i + 1], inn[nr][i], inn[nr][i + 1]
            mb.f((o0, i0, i1, o1), [uv_outer(i / na, 1)] * 2 + [uv_outer((i + 1) / na, 1)] * 2, None, OUTER)
        for col, rev in ((0, False), (na, True)):
            for j in range(nr):
                c0 = 0 if j == 0 else col
                q = [out[j][c0], inn[j][c0], inn[j + 1][col], out[j + 1][col]]
                mb.f(q[::-1] if rev else q, [uv_outer(0.0, j / nr)] * 4, None, OUTER)
        # teeth along the rim, curving across the gap toward the other lobe
        for k in range(n_teeth):
            a = math.pi * (k + 0.5 + teeth_phase) / n_teeth
            if a < 0.10 * math.pi or a > 0.90 * math.pi:
                continue
            p0 = (self.point(a, 1.0) + self.point(a, 1.0, inner=True)) / 2
            tang = (self.point(a, 1.0) - self.point(a, 0.97)).normalized()
            L = tooth_len * (0.55 + 0.45 * math.sin(a))
            pts = [p0 - tang * tooth_r * 0.5]
            for s in (0.33, 0.66, 1.0):
                pts.append(p0 + tang * (L * s) - self.n * (L * 0.38 * s * s))
            rim_t = (self.point(a + 0.01, 1.0) - self.point(a - 0.01, 1.0)).normalized()
            up = rim_t.cross(tang).normalized()
            Loft(pts, lambda t, r0=tooth_r: {"rx": r0 * 1.35 * (1 - 0.55 * t), "ry": r0 * 0.5 * (1 - 0.45 * t)}, n=8,
                 seg=L / 5, frame="up", up=up, cap0="flat", cap1="dome", cap1_len=tooth_r * 0.9, cap_rings=2).build(
                     mb, uvmap=uv_teeth, mat=TEETH)
        return out


def build_trap(scale, phi, res):
    """The midrib and the two lobes of one trap, in its local frame (hinge on X through the
    origin, mouth toward -Y). Returns (midrib MB, upper MB, lower MB, lobes)."""
    HX, W, B, t = 1.30 * scale, 1.08 * scale, 0.72 * scale, 0.07 * scale
    na, nr, nt = res
    lobes = []
    mbs = []
    for sgn, phase in ((1, 0.0), (-1, 0.5)):
        lb = Lobe(sgn, phi, HX, W, B, t)
        mb = MB()
        lb.build(mb, na, nr, nt, 0.36 * scale, 0.068 * scale, phase)
        mbs.append(mb)
        lobes.append(lb)
    mid = MB()
    Loft([V((-HX * 1.03, 0.02 * scale, 0)), V((0, 0.03 * scale, 0)), V((HX * 1.03, 0.02 * scale, 0))],
         lambda tt: {"rx": 0.075 * scale * (0.7 + 0.3 * math.sin(math.pi * tt)), "ry": 0.075 * scale * (0.7 + 0.3 * math.sin(math.pi * tt))},
         n=10, seg=0.15 * scale, frame="up", up=V((0, 0, 1)), cap0="dome", cap1="dome").build(
             mid, uvmap=lambda s, a: uv_midrib(s, a), mat=STEM)
    return mid, mbs[0], mbs[1], lobes


# --------------------------------------------------------------------------------------------
# The fly
# --------------------------------------------------------------------------------------------

def ellipsoid(mb, c, radii, M, uvm, mat, nu=16, nv=10):
    lib.pumpkin(mb, c, radii[0], radii[2], ry=radii[1], ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0,
                nu=nu, nv=nv, fullness=1.0, M=M, uvmap=uvm, mat=mat)


def build_fly(s=0.92):
    """The fly in its own frame: head toward +Y, up +Z, the thorax at the origin."""
    body = MB()
    AX = Matrix.Rotation(-math.pi / 2, 3, "X")      # pole axis (local z) along +Y
    ellipsoid(body, V((0, 0.0, 0)), (0.15 * s, 0.135 * s, 0.17 * s), AX, uv_body, FLY, 18, 12)                # thorax
    ellipsoid(body, V((0, -0.30 * s, -0.02 * s)), (0.15 * s, 0.12 * s, 0.24 * s), AX, uv_body, FLY, 18, 14)  # abdomen
    ellipsoid(body, V((0, 0.24 * s, 0.0)), (0.12 * s, 0.11 * s, 0.10 * s), AX, uv_body, FLY, 16, 10)          # head
    for sx in (-1, 1):
        ellipsoid(body, V((sx * 0.085 * s, 0.27 * s, 0.03 * s)), (0.075 * s, 0.07 * s, 0.085 * s), None, uv_eye, FLY, 12, 8)
    # legs: three a side, out and down in three joints
    for sx in (-1, 1):
        for k, yb in enumerate((0.08, 0.0, -0.08)):
            root = V((sx * 0.08 * s, yb * s, -0.07 * s))
            fwd = (1 - k) * 0.5
            knee = root + V((sx * 0.20, fwd * 0.12, 0.10)) * s
            ankle = knee + V((sx * 0.10, fwd * 0.15, -0.26)) * s
            foot = ankle + V((sx * 0.06, fwd * 0.08 + 0.02, -0.05)) * s
            Loft([root, knee, ankle, foot], lambda t: {"rx": 0.016 * s * (1 - 0.5 * t), "ry": 0.016 * s * (1 - 0.5 * t)},
                 n=5, seg=0.05 * s, frame="up", up=V((0, 1, 0)), cap0="flat", cap1="dome", cap1_len=0.01).build(
                     body, uvmap=lambda u, v: uv_body(v, 0.95), mat=FLY)
    wings = {}
    for name, sx in (("wing_R", 1), ("wing_L", -1)):
        root = V((sx * 0.06 * s, 0.03 * s, 0.11 * s))
        d = V((sx * 0.42, -0.88, 0.22)).normalized()
        side = V((0, 0, 1)).cross(d).normalized() * sx
        if side.z < 0:
            side = -side
        wm = MB()
        L, Wd = 0.46 * s, 0.17 * s

        def fn(u, v, d=d, side=side, L=L, Wd=Wd):
            w = math.sin(math.pi * min(max(u, 0.02), 0.98)) ** 0.6
            return d * (L * u) + side * (Wd * (v - 0.35) * w * 1.6) + V((0, 0, 0.02 * s * u * u))
        lib.grid_patch(wm, fn, 8, 3, uvmap=lambda u, v: uv_wing(u * 0.96 + 0.02, 0.5 + (v - 0.35) * 0.9), mat=WING)
        wings[name] = (wm, root)
    return body, wings


# --------------------------------------------------------------------------------------------
# Plant
# --------------------------------------------------------------------------------------------

def stem_loft(mb, pts, r0, r1, flare=1.0):
    def sec(t):
        r = r0 + (r1 - r0) * t
        r *= 1 + (flare - 1) * max(0.0, (t - 0.85) / 0.15) ** 2
        return {"rx": r, "ry": r * 0.88}
    Loft([V(p) for p in pts], sec, n=12, seg=0.12, frame="rmf", up=V((1, 0, 0)), cap0="flat", cap1="dome",
         cap1_len=r1 * 0.5).build(mb, uvmap=lambda s, a: uv_stem(s, a), mat=STEM)


def leaf_blade(mb, az, length, lift, width, rng):
    out = V((math.sin(az), -math.cos(az), 0))
    side = out.cross(V((0, 0, 1)))
    pts = []
    for j in range(13):
        s = j / 12
        p = out * (length * s) + V((0, 0, 0.04 + lift * math.sin(math.pi * min(s * 1.3, 1.0)) * (1 - 0.6 * s) - 0.1 * s * s))
        pts.append(p)
    rows = []
    for j, p in enumerate(pts):
        s = j / 12
        w = width * (0.25 + 0.75 * math.sin(math.pi * min(s * 1.05, 1.0)) ** 0.8) * (1 - s ** 6)
        row = []
        for k in range(5):
            f = k / 4 * 2 - 1
            q = p + side * (w * f) + V((0, 0, 0.05 * width * (1 - f * f) * (1 - s)))
            row.append(mb.v(q))
        rows.append(row)
    for j in range(12):
        for k in range(4):
            q = [rows[j][k], rows[j][k + 1], rows[j + 1][k + 1], rows[j + 1][k]]
            uv = [uv_leaf(j / 12, k / 4), uv_leaf(j / 12, (k + 1) / 4), uv_leaf((j + 1) / 12, (k + 1) / 4),
                  uv_leaf((j + 1) / 12, k / 4)]
            mb.f(q[::-1], uv[::-1], None, LEAF)


def vine(mb, top, length, rng, Minv):
    """A vine hanging from `top` (world), built in the trap's frame (Minv: world -> local)."""
    pts = []
    n = int(length / 0.12) + 2
    ph = rng.uniform(0, 6.28)
    for i in range(n):
        t = i / (n - 1)
        pts.append(top + V((0.06 * math.sin(ph + t * 7), 0.05 * math.cos(ph + t * 5), -length * t)))
    loc = [Minv @ p for p in pts]
    Loft(loc, lambda t: {"rx": 0.010, "ry": 0.010}, n=4, seg=0.1, frame="rmf", up=V((1, 0, 0)), cap0="flat",
         cap1="flat").build(mb, uvmap=lambda s, a: (0.5, 0.15), mat=VINE)
    path = lib.Path(pts)
    s = 0.05
    k = 0
    while s < path.L - 0.02:
        p = path.at(s)
        side = 1 if k % 2 else -1
        ang = rng.uniform(0, math.tau)
        nrm = V((math.cos(ang) * 0.6, -0.8 + math.sin(ang) * 0.3, 0.1)).normalized()
        up = V((side * 0.4, 0, 1)).normalized()
        sz = rng.uniform(0.12, 0.18) * (1 - 0.3 * s / path.L)
        t_ = (up - nrm * up.dot(nrm)).normalized()
        sd = t_.cross(nrm)
        c = p + sd * (side * sz * 0.4)
        h = sz / 2
        quad = [c - sd * h - t_ * h * 0.6, c + sd * h - t_ * h * 0.6, c + sd * h + t_ * h * 1.4, c - sd * h + t_ * h * 1.4]
        ids = [mb.v(Minv @ q) for q in quad]
        mb.f(ids, [(0, 0), (1, 0), (1, 1), (0, 1)], None, VINE)
        s += rng.uniform(0.08, 0.13)
        k += 1


def prune(objs):
    for o in objs:
        if o.type != "MESH":
            continue
        used = sorted(set(p.material_index for p in o.data.polygons))
        if len(used) == len(o.data.materials):
            continue
        remap = {old: new for new, old in enumerate(used)}
        keep = [o.data.materials[i] for i in used]
        idx = [remap[p.material_index] for p in o.data.polygons]
        o.data.materials.clear()
        for m in keep:
            o.data.materials.append(m)
        o.data.polygons.foreach_set("material_index", idx)


def outward_normals(o):
    """Makes the faces of each closed shell face outward (the lobes are built with mixed winding)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def place(mb, name, mats, M, parent=None, fix=False):
    o = mb.object(name, mats, origin=(0, 0, 0), auto_smooth=50)
    if fix:
        outward_normals(o)
    o.matrix_world = M
    if parent is not None:
        lib.set_parent(o, parent)
    return o


# trap placements: hinge centre, yaw (deg about Z), tilt (deg about the hinge: + turns the mouth
# down toward the viewer), scale, half-open angle (deg), and which end of the hinge the stem joins
BIG = {"at": V((-0.30, -0.45, 3.50)), "yaw": 0.0, "tilt": -10.0, "scale": 1.0, "phi": 13.0, "end": 1}
SMALL = [
    {"at": V((-0.95, -0.40, 1.42)), "yaw": -28.0, "tilt": -12.0, "scale": 0.36, "phi": 16.0, "end": 1},
    {"at": V((0.92, -0.72, 0.92)), "yaw": 34.0, "tilt": -8.0, "scale": 0.28, "phi": 16.0, "end": -1},
]


def trap_matrix(p):
    return Matrix.Translation(p["at"]) @ Matrix.Rotation(math.radians(p["yaw"]), 4, "Z") @ \
        Matrix.Rotation(math.radians(p["tilt"]), 4, "X")


def main():
    lib.reset()
    trap_t = lib.paint_named("tex_flytrap.py", {"kind": "trap"}, {"base": "flytrap-trap.jpg", "emit": "flytrap-trap-e.jpg"})
    plant_t = lib.paint_named("tex_flytrap.py", {"kind": "plant"}, {"tex": "flytrap-plant.jpg"})["tex"]
    fly_t = lib.paint_named("tex_flytrap.py", {"kind": "fly"}, {"tex": "flytrap-fly.png"})["tex"]
    vine_t = lib.paint_named("tex_well.py", {"kind": "ivy", "color": "#3e7a34", "dark": "#1c401a", "vein": "#9ac080",
                                             "seed": 9}, {"tex": "flytrap-vine.png"})["tex"]
    mats = [
        lib.material("stem", base_tex=plant_t, roughness=0.6, specular=0.35),
        lib.material("leaf", base_tex=plant_t, roughness=0.55, specular=0.35, double_sided=True),
        lib.material("trap_outer", base_tex=trap_t["base"], emission_tex=trap_t["emit"], roughness=0.6, specular=0.3),
        lib.material("glow_trap", base_tex=trap_t["base"], emission_tex=trap_t["emit"], roughness=0.5, specular=0.3),
        lib.material("teeth", base_tex=trap_t["base"], emission_tex=trap_t["emit"], roughness=0.5, specular=0.3),
        lib.material("fly_body", base_tex=fly_t, roughness=0.22, specular=0.7),
        lib.material("fly_wing", base_tex=fly_t, roughness=0.2, specular=0.6, alpha_blend=True, double_sided=True),
        lib.material("vine", base_tex=vine_t, roughness=0.6, specular=0.3, alpha_clip=0.5, double_sided=True),
    ]
    rng = lib.seeded(5)
    root_mb = MB()
    # rosette of leaves
    for i in range(8):
        az = math.tau * i / 8 + rng.uniform(-0.2, 0.2)
        leaf_blade(root_mb, az, rng.uniform(1.0, 1.45), rng.uniform(0.35, 0.6), rng.uniform(0.24, 0.32), rng)
    # stems: each joins its trap's hinge at one end, coming in along the hinge
    traps = [BIG] + SMALL
    stems = [
        [V((0.12, 0.30, 0.0)), V((0.22, 0.42, 0.9)), V((0.52, 0.40, 2.0)), V((0.98, 0.18, 2.95))],
        [V((-0.10, 0.05, 0.0)), V((-0.20, 0.05, 0.55)), V((-0.40, -0.05, 1.10))],
        [V((0.10, -0.12, 0.0)), V((0.25, -0.30, 0.45)), V((0.45, -0.45, 0.80))],
    ]
    radii = [(0.22, 0.13), (0.075, 0.05), (0.06, 0.04)]
    for p, ctrl, (r0, r1) in zip(traps, stems, radii):
        M = trap_matrix(p)
        HX = 1.30 * p["scale"]
        end = M @ V((p["end"] * HX * 1.0, 0.02 * p["scale"], 0))
        approach = M @ V((p["end"] * (HX + 0.35 * p["scale"] + 0.12), 0.06 * p["scale"], -0.05 * p["scale"]))
        stem_loft(root_mb, ctrl + [approach, end], r0, r1, flare=1.25)
    root = root_mb.object("venus_flytrap", mats, origin=(0, 0, 0), auto_smooth=50)
    objs = [root]
    # the big trap
    M = trap_matrix(BIG)
    mid, up_mb, lo_mb, lobes = build_trap(1.0, math.radians(BIG["phi"]), (36, 14, 16))
    Minv = M.inverted()
    for x in (1.18, 0.98, -1.02, -1.20):
        vine(mid, M @ V((x, 0.06, -0.05)), rng.uniform(1.4, 2.3), rng, Minv)
    trap = place(mid, "trap", mats, M, root)
    lu = place(up_mb, "lobe_upper", mats, M, trap, fix=True)
    ll = place(lo_mb, "lobe_lower", mats, M, trap, fix=True)
    objs += [trap, lu, ll]
    # the fly, caught at the top of the mouth, its head inside, wings and abdomen out
    body, wings = build_fly()
    FM = M @ Matrix.Translation((0.12, -0.90, 0.10)) @ Matrix.Rotation(math.radians(-8), 4, "X") @ \
        Matrix.Rotation(math.radians(12), 4, "Z") @ Matrix.Rotation(math.radians(-10), 4, "Y")
    fly = place(body, "fly", mats, FM, trap)
    objs.append(fly)
    for name, (wm, wroot) in wings.items():
        w = place(wm, name, mats, FM @ Matrix.Translation(wroot), fly)
        objs.append(w)
    # small traps
    for k, p in enumerate(SMALL, start=1):
        Ms = trap_matrix(p)
        mid, up_mb, lo_mb, _ = build_trap(p["scale"], math.radians(p["phi"]), (22, 8, 11))
        t = place(mid, f"trap_small_{k}", mats, Ms, root)
        objs += [t, place(up_mb, f"trap_small_{k}_upper", mats, Ms, t, fix=True),
                 place(lo_mb, f"trap_small_{k}_lower", mats, Ms, t, fix=True)]
    prune(objs)
    bpy.context.view_layer.update()
    tris = sum(lib.tri_count(o) for o in objs)
    zs = [(o.matrix_world @ v.co).z for o in objs for v in o.data.vertices]
    print(f"  venus-flytrap: {tris} tris, top {max(zs):.2f} m; " +
          ", ".join(f"{o.name} {lib.tri_count(o)}" for o in objs))
    lib.export("venus-flytrap")


if __name__ == "__main__":
    main()
