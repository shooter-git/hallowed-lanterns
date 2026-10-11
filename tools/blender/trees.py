# SPDX-License-Identifier: MIT
"""Night-woods trees for the candle grove and the hollows (reference/candle-grove-*.jpg).

    blender -b --factory-startup -P tools/blender/trees.py

Writes public/models/tree-oak.glb, tree-tall.glb and tree-young.glb.

Grown by a small recursive branching model (trunk, limbs, branches, twigs as lofted tubes with
a flared, buttressed foot) and dressed with alpha-tested leaf-cluster cards. The cards are
two-sided geometry (one card per side) whose normals point out from the crown's centre, so
the canopy shades as one soft mass when it is lit from below by lanterns.

Nodes: `<name>` (root mesh: material `bark`) with child `foliage` (material `foliage`, alpha
MASK) and `hang_points`: `hang_##` empties under roughly level branches 2.5-6.5 m up, where a
pumpkin can hang (the glTF -Y side of the empty is down along its rope; the points are on the
branch's underside).

tree-oak    a spreading post oak, about 10 m tall and 13 m across, low crooked limbs.
tree-tall   a tall slender hardwood, about 14 m, narrow crown high up.
tree-young  a sapling, about 5 m.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

Z = Vector((0, 0, 1))

VARIANTS = {
    "tree-oak": dict(
        seed=3, trunk_len=3.6, trunk_r=0.30, trunk_lean=(0.05, 0.03), levels=3,
        seg=[0.3, 0.32, 0.38, 0.4], sides=[14, 9, 6, 4],
        nchild=[3, 6, 4], tmin=[0.72, 0.15, 0.25], angle=[(50, 64), (30, 55), (25, 50)],
        lenratio=[1.8, 0.55, 0.55], lenfall=[0.2, 0.55, 0.5], ratio=[0.62, 0.5, 0.45],
        up=[(0.0, 0.0), (0.0, 0.11), (0.04, 0.1), (0.05, 0.1)], wander=[0.04, 0.12, 0.15, 0.18],
        taper=[0.55, 0.3, 0.3, 0.3], rmin=0.012, leaf_min_z=3.2,
        leaf_level=2, card=(0.9, 1.3), card_step=0.22, crown=(0, 0, 7.0), crown_scale=(1.3, 1.3, 1.0)),
    "tree-tall": dict(
        seed=8, trunk_len=13.0, trunk_r=0.19, trunk_lean=(0.03, -0.02), levels=3,
        seg=[0.35, 0.3, 0.32, 0.35], sides=[12, 7, 5, 4],
        nchild=[13, 5, 3], tmin=[0.5, 0.15, 0.25], angle=[(40, 64), (30, 55), (30, 50)],
        lenratio=[0.3, 0.6, 0.55], lenfall=[0.75, 0.5, 0.5], ratio=[0.42, 0.5, 0.5],
        up=[(0.0, 0.0), (0.02, 0.08), (0.04, 0.1), (0.05, 0.1)], wander=[0.035, 0.1, 0.14, 0.18],
        taper=[0.18, 0.3, 0.3, 0.3], rmin=0.01, leaf_min_z=5.5,
        leaf_level=2, card=(1.0, 1.4), card_step=0.2, crown=(0, 0, 10.5), crown_scale=(1, 1, 1.6)),
    "tree-young": dict(
        seed=12, trunk_len=4.6, trunk_r=0.065, trunk_lean=(-0.04, 0.03), levels=2,
        seg=[0.25, 0.25, 0.25], sides=[9, 6, 4],
        nchild=[8, 4], tmin=[0.3, 0.2], angle=[(35, 60), (30, 55)],
        lenratio=[0.45, 0.55], lenfall=[0.7, 0.5], ratio=[0.5, 0.5],
        up=[(0.0, 0.0), (0.03, 0.1), (0.05, 0.12)], wander=[0.05, 0.12, 0.16],
        taper=[0.15, 0.3, 0.3], rmin=0.008,
        leaf_level=1, card=(0.6, 0.9), card_step=0.15, crown=(0, 0, 3.4), crown_scale=(1, 1, 1.3)),
}


class Branch:
    def __init__(self, pts, r0, r1, level):
        self.pts, self.r0, self.r1, self.level = pts, r0, r1, level
        self.cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + (b - a).length)
        self.L = self.cum[-1]

    def at(self, t):
        s = t * self.L
        for i in range(len(self.pts) - 1):
            if self.cum[i + 1] >= s:
                f = (s - self.cum[i]) / max(self.cum[i + 1] - self.cum[i], 1e-9)
                p = self.pts[i].lerp(self.pts[i + 1], f)
                return p, (self.pts[i + 1] - self.pts[i]).normalized()
        return self.pts[-1], (self.pts[-1] - self.pts[-2]).normalized()

    def radius(self, t):
        return self.r0 + (self.r1 - self.r0) * t


def rand_unit(rng):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if 0.01 < v.length <= 1:
            return v.normalized()


def grow(P, rng, out, level, start, d, length, r0):
    nseg = max(3, int(length / P["seg"][level]))
    pts = [start.copy()]
    dd = d.normalized()
    up0, up1 = P["up"][level]
    for i in range(nseg):
        f = i / nseg
        dd = (dd + rand_unit(rng) * P["wander"][level] + Z * (up0 + (up1 - up0) * f)).normalized()
        pts.append(pts[-1] + dd * (length / nseg))
    r1 = max(r0 * P["taper"][level], P["rmin"])
    br = Branch(pts, r0, r1, level)
    out.append(br)
    if level >= P["levels"]:
        return
    n = P["nchild"][level]
    tmin = P["tmin"][level]
    az = rng.uniform(0, math.tau)
    for k in range(n):
        t = tmin + (1 - tmin) * (k + rng.uniform(0.1, 0.9)) / n
        p, tan = br.at(t)
        cr = min(br.radius(t) * P["ratio"][level] * rng.uniform(0.85, 1.1), br.radius(t) * 0.85)
        az += 2.39996 + rng.uniform(-0.35, 0.35)
        perp = tan.cross(Vector((0.3, 0.7, 0.1)) if abs(tan.y) < 0.9 else Vector((1, 0, 0))).normalized()
        perp = Quaternion(tan, az) @ perp
        a0, a1 = P["angle"][level]
        ang = math.radians(rng.uniform(a0, a1))
        cd = (tan * math.cos(ang) + perp * math.sin(ang)).normalized()
        clen = length * P["lenratio"][level] * (1 - P["lenfall"][level] * t) * rng.uniform(0.8, 1.15)
        grow(P, rng, out, level + 1, p - tan * cr * 0.5, cd, clen, cr)


def build_tree(name, tex):
    lib.reset()
    P = VARIANTS[name]
    rng = lib.seeded(P["seed"])
    bark = lib.material("bark", base_tex=tex["bark"], normal_tex=tex["bark_n"], normal_strength=1.0,
                        roughness=0.92, specular=0.25)
    foliage = lib.material("foliage", base_tex=tex["leaves"], roughness=0.75, specular=0.3, alpha_clip=0.5)
    branches = []
    lx, ly = P["trunk_lean"]
    grow(P, rng, branches, 0, Vector((0, 0, -0.15)), Vector((lx, ly, 1)), P["trunk_len"], P["trunk_r"])
    if name == "tree-oak":
        # the oak's crown: the trunk divides into big spreading limbs at its top
        top, tan = branches[0].at(1.0)
        for k in range(3):
            a = k * math.tau / 3 + 0.4
            d = (Vector((math.cos(a), math.sin(a), 0)) * 0.9 + Z * 0.75).normalized()
            grow(P, rng, branches, 1, top - Z * 0.2, d, P["trunk_len"] * 1.7, P["trunk_r"] * 0.6)
    wood = MB()
    for br in branches:
        lvl = br.level
        n = P["sides"][min(lvl, len(P["sides"]) - 1)]
        keys_r = (br.r0, br.r1)
        flare = lvl == 0

        def sec(t, r0=keys_r[0], r1=keys_r[1]):
            r = r0 + (r1 - r0) * t
            return {"rx": r, "ry": r}

        def offset(t, a, s, L=br.L, flare=flare, r0=br.r0):
            if not flare:
                return 0.0
            h = t * L
            return r0 * (0.55 * math.exp(-h / 0.45) * (1 + 0.6 * math.cos(a * math.tau * 5)) + 0.05 * math.sin(h * 3 + a * 9))
        loft = Loft(br.pts, sec, n=n, seg=P["seg"][min(lvl, len(P["seg"]) - 1)], frame="rmf",
                    up=Vector((1, 0, 0)) if abs(br.pts[1].x - br.pts[0].x) < 0.5 else Z,
                    cap0="flat" if lvl == 0 else "open", cap1="point", cap1_len=max(br.r1 * 2, 0.02), offset=offset)
        ka = max(1, round(math.tau * br.r0 / 0.6))
        total = br.L
        loft.build(wood, uvmap=lambda s, a, ka=ka, total=total: (a * ka, s * total / 1.5), mat=0)
    wood.clamp_z(-0.15)
    root = wood.object(name, [bark], origin=(0, 0, 0))
    # leaf cards
    leaves = MB()
    C = Vector(P["crown"])
    cs = Vector(P["crown_scale"])
    cards = 0
    for br in branches:
        if br.level < P["leaf_level"]:
            continue
        step = P["card_step"] / max(br.L, 1e-6)
        t = 0.25 + rng.uniform(0, step)
        while t <= 1.0:
            p, tan = br.at(t)
            if p.z < P.get("leaf_min_z", 0.0):
                t += step
                continue
            out = Vector(((p.x - C.x) / cs.x, (p.y - C.y) / cs.y, (p.z - C.z) / cs.z))
            out = out.normalized() if out.length > 1e-6 else Z.copy()
            upv = (tan * 0.6 + out * 0.5 + rand_unit(rng) * 0.45 + Z * 0.15).normalized()
            size = rng.uniform(*P["card"])
            cell = rng.randrange(4)
            u0, v0 = (cell % 2) * 0.5, 0.5 - (cell // 2) * 0.5
            side0 = upv.cross(rand_unit(rng)).normalized()
            for rot in (0.0, math.pi / 2):
                side = Quaternion(upv, rot) @ side0
                base = p - upv * size * 0.06
                q = [base - side * size / 2, base + side * size / 2,
                     base + side * size / 2 + upv * size, base - side * size / 2 + upv * size]
                uv = [(u0 + 0.004, v0 + 0.004), (u0 + 0.496, v0 + 0.004), (u0 + 0.496, v0 + 0.496), (u0 + 0.004, v0 + 0.496)]
                idx = [leaves.v(c) for c in q]
                leaves.f(idx, uv, None, 0)
                idx2 = [leaves.v(c) for c in q]          # the other side, its own vertices
                leaves.f(list(reversed(idx2)), list(reversed(uv)), None, 0)
            cards += 1
            t += step * rng.uniform(0.7, 1.3)
    fol = leaves.object("foliage", [foliage], origin=(0, 0, 0))
    me = fol.data
    me.use_auto_smooth = True
    me.auto_smooth_angle = math.pi
    normals = []
    for v in me.vertices:
        d = Vector(((v.co.x - C.x) / cs.x, (v.co.y - C.y) / cs.y, (v.co.z - C.z) / cs.z))
        normals.append((d.normalized() + Z * 0.25).normalized() if d.length > 1e-6 else Z)
    me.normals_split_custom_set_from_vertices(normals)
    lib.set_parent(fol, root)
    # hang points under roughly level branches
    hroot = lib.empty("hang_points", (0, 0, 0))
    lib.set_parent(hroot, root)
    pts = []
    for br in branches:
        if br.level not in (1, 2):
            continue
        t = 0.2
        while t < 0.95:
            p, tan = br.at(t)
            if 2.5 < p.z < 6.5 and abs(tan.z) < 0.45 and all((p - q).length > 0.9 for q in pts):
                pts.append(p - Z * br.radius(t))
            t += 0.6 / max(br.L, 0.1)
    for i, p in enumerate(pts):
        e = lib.empty(f"hang_{i:02d}", p, size=0.05)
        lib.set_parent(e, hroot)
    print(f"  {name}: wood {lib.tri_count(root)} tris ({len(branches)} branches), foliage {lib.tri_count(fol)} tris "
          f"({cards} card pairs), {len(pts)} hang points")
    lib.export(name)


def main():
    lib.reset()
    tex = lib.paint("tex_trees.py", {}, {"bark": "trees-bark.jpg", "bark_n": "trees-bark-n.jpg",
                                         "leaves": "trees-leaves.png"})
    for name in VARIANTS:
        build_tree(name, tex)


main()
