# SPDX-License-Identifier: MIT
"""The pirate props of the Kraken's Wreck and the treasure (reference/kraken-1.jpg, kraken-2.jpg,
reference/video-9604.mov).

    blender -b --factory-startup -P tools/blender/treasure.py [-- only=rowboat,chest,palm,barrel]

Writes public/models/rowboat.glb, treasure-chest.glb, pumpkin-palm.glb and barrel.glb.

- rowboat: a weathered lapstrake rowboat (3.2 m) with a transom stern, two thwarts, floorboards,
  oarlocks and a pair of oars lying inside. Empties `crew_0`, `crew_1` mark where
  skeleton-pirate-sit's origin goes (on the floorboards under each thwart, facing the stern).
- treasure-chest: the big open chest (2 m) on its low dark platform (3.5 x 1.4 x 0.45 m, people sit
  on its front edge), heaped with coins, gems and pearls, a crown, a skull and a pale pumpkin, a
  little skull for a lock, chains holding the lid. `lid` is a separate node with its pivot on the
  hinge line: its mesh is modelled closed and the node carries the open angle (-110 deg about X),
  so rotation 0 closes it. `chains` is separate so it can be hidden when the lid moves.
- pumpkin-palm: five stacked pumpkins for a trunk and a crown of glowing green fronds (2.2 m).
- barrel: an oak barrel (0.9 m) lying on its side.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
import skeletons as SK  # noqa: E402

ARGS = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
ONLY = set(ARGS["only"].split(",")) if "only" in ARGS else None
V = Vector
WOOD_TILE = 2.0
ROWS = 8


def wood(name, base, seed, row_tones=None, **kw):
    params = dict(size=1024, rows=ROWS, tile_m=WOOD_TILE, base=base, seed=seed, grain=0.7, groove=0.7, wear=0.07,
                  dirt=0.3, knots=1, joints=1, nails=True)
    if row_tones:
        params["row_tones"] = row_tones
    params.update(kw)
    out = lib.paint_named("tex_wood.py", params, {"color": f"{name}.jpg", "normal": f"{name}-n.jpg"})
    return out["color"], out["normal"]


def row_uv(row, u_m, fv):
    return (u_m / WOOD_TILE, 1.0 - (row % ROWS + 0.05 + 0.9 * min(max(fv, 0), 1)) / ROWS)


def plank_uv(row, across=0.2):
    """uv(face_axis, x, y) for lib.beam: the grain along the beam's x."""
    def f(ax, x, y):
        if ax == 0:      # end grain
            return row_uv(row, 0.02 + y * 0.1, 0.5 + x / across * 0.5)
        return row_uv(row, x + 0.37 * row, 0.5 + y / across)
    return f


def shell(mb, pts_out, pts_in, uvs, mat):
    """A plank with thickness from grids of outer/inner points [i along][j across] (+ its edges)."""
    ni, nj = len(pts_out), len(pts_out[0])
    O = [[mb.v(p) for p in row] for row in pts_out]
    I = [[mb.v(p) for p in row] for row in pts_in]
    for i in range(ni - 1):
        for j in range(nj - 1):
            mb.f((O[i][j], O[i + 1][j], O[i + 1][j + 1], O[i][j + 1]),
                 [uvs[i][j], uvs[i + 1][j], uvs[i + 1][j + 1], uvs[i][j + 1]], None, mat)
            mb.f((I[i][j + 1], I[i + 1][j + 1], I[i + 1][j], I[i][j]),
                 [uvs[i][j + 1], uvs[i + 1][j + 1], uvs[i + 1][j], uvs[i][j]], None, mat)
    for i in range(ni - 1):
        for j, flip in ((0, False), (nj - 1, True)):
            q = [O[i][j], I[i][j], I[i + 1][j], O[i + 1][j]]
            uv = [uvs[i][j], uvs[i][j], uvs[i + 1][j], uvs[i + 1][j]]
            mb.f(q[::-1] if flip else q, uv[::-1] if flip else uv, None, mat)
    for i, flip in ((0, True), (ni - 1, False)):
        for j in range(nj - 1):
            q = [O[i][j], O[i][j + 1], I[i][j + 1], I[i][j]]
            uv = [uvs[i][j], uvs[i][j + 1], uvs[i][j + 1], uvs[i][j]]
            mb.f(q[::-1] if flip else q, uv[::-1] if flip else uv, None, mat)


# --------------------------------------------------------------------------------------------
# Rowboat
# --------------------------------------------------------------------------------------------

RB = {"L": 3.2, "B": 0.64, "strakes": 5, "thick": 0.022}
FLOOR_Z = 0.11
THWART_Z = 0.47
THWARTS = (1.05, 2.05)


def rb_point(x, f, side):
    L = RB["L"]
    u = min(max(x / L, 0.0), 1.0)
    if u >= 0.45:
        B = RB["B"] * max(1 - ((u - 0.45) / 0.55) ** 2, 0.0) ** 0.62
        D = 0.62 + 0.11 * ((u - 0.45) / 0.55) ** 2
    else:
        B = RB["B"] - 0.17 * ((0.45 - u) / 0.45) ** 1.6
        D = 0.62 + 0.04 * ((0.45 - u) / 0.45) ** 2
    keel = 0.05 + 0.34 * max(0.0, (u - 0.62) / 0.38) ** 2.2 + 0.07 * max(0.0, (0.22 - u) / 0.22) ** 1.5
    th = f * math.pi / 2
    e = 2 / 3.2
    y = B * math.sin(th) ** e * (0.84 + 0.16 * f)
    z = keel + (D - keel) * (1 - math.cos(th) ** e)
    return V((x, side * y, z))


def rb_normal(x, f, side):
    e = 1e-3
    dx = rb_point(x + e, f, side) - rb_point(x - e, f, side)
    df = rb_point(x, min(f + e, 1), side) - rb_point(x, max(f - e, 0), side)
    n = dx.cross(df)
    if n.length < 1e-9:
        return V((0, side, 0))
    n.normalize()
    if n.dot(V((0, side, -0.2))) < 0:
        n = -n
    return n


def half_width_at(x, z):
    lo, hi = 0.0, 1.0
    for _ in range(30):
        m = (lo + hi) / 2
        if rb_point(x, m, 1).z < z:
            lo = m
        else:
            hi = m
    return rb_point(x, lo, 1).y


def build_rowboat():
    lib.reset()
    wc, wn = wood("rowboat-wood", ["#5e5248", "#544a42", "#675a4c", "#4c443e"], 61, dirt=0.4, wear=0.1)
    wmat = lib.material("boat_wood", base_tex=wc, normal_tex=wn, roughness=0.85, specular=0.25)
    iron = lib.material("iron", color="#2a2826", roughness=0.55, metallic=0.7)
    mb = MB()
    L, N, th = RB["L"], RB["strakes"], RB["thick"]
    for side in (-1, 1):
        for k in range(N):
            f0, f1 = k / N, (k + 1) / N
            nx, nj = 22, 3
            out, inn, uvs = [], [], []
            for i in range(nx + 1):
                x = L * i / nx
                ro, ri, ru = [], [], []
                for j in range(nj):
                    fj = j / (nj - 1)
                    f = f0 + (f1 - f0) * fj
                    p = rb_point(x, f, side)
                    n = rb_normal(x, f, side)
                    p = p + n * (0.010 * (1 - fj) if k > 0 else 0.0)     # lapstrake: each strake laps the one below
                    ro.append(p)
                    ri.append(p - n * th)
                    ru.append(row_uv(k + (0 if side > 0 else 3), x + 0.7 * k, fj))
                out.append(ro)
                inn.append(ri)
                uvs.append(ru)
            shell(mb, out, inn, uvs, 0)
    # transom: a board closing the stern
    sec = [rb_point(0.0, 1 - i / 10, -1) for i in range(11)] + [rb_point(0.0, i / 10, 1) for i in range(1, 11)]
    from mathutils import geometry
    flat = [V((p.y, p.z, 0)) for p in sec]
    tris = geometry.tessellate_polygon([flat])
    for xo, flip in ((-0.03, True), (0.012, False)):
        ids = [mb.v(V((xo, p.y, p.z))) for p in sec]
        for a, b, c in tris:
            pa, pb, pc = flat[a], flat[b], flat[c]
            cr = (pb.x - pa.x) * (pc.y - pa.y) - (pb.y - pa.y) * (pc.x - pa.x)
            tri = (a, b, c) if (cr > 0) != flip else (a, c, b)
            mb.f([ids[t] for t in tri], [row_uv(6, 0.3 + sec[t].y, 0.5 + sec[t].z * 1.5) for t in tri], None, 0)
    # keel, stem, gunwales, risers
    keel = [rb_point(L * i / 16, 0.0, 1) - V((0, 0, 0.025)) for i in range(17)]
    keel.append(rb_point(L, 1.0, 1) + V((0.03, 0, 0.06)))
    Loft(keel, lambda t: {"rx": 0.035, "ry": 0.04, "p": 4}, n=6, seg=0.15, frame="up", up=V((0, 1, 0.0001)),
         cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: row_uv(5, s * 3.6, a), mat=0)
    for side in (-1, 1):
        rail = [rb_point(L * i / 18, 1.0, side) + V((0, 0, 0.015)) for i in range(18)] + [rb_point(L * 0.995, 1.0, side) + V((0, 0, 0.015))]
        Loft(rail, lambda t: {"rx": 0.045, "ry": 0.03, "p": 4}, n=6, seg=0.15, frame="up", up=V((0, 0, 1)),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: row_uv(2, s * 3.4, a), mat=0)
        riser = []
        for i in range(13):
            x = 0.35 + (2.6 - 0.35) * i / 12
            riser.append(V((x, side * (half_width_at(x, THWART_Z - 0.04) - 0.03), THWART_Z - 0.045)))
        Loft(riser, lambda t: {"rx": 0.012, "ry": 0.03, "p": 4}, n=4, seg=0.2, frame="up", up=V((0, 0, 1)),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: row_uv(4, s * 2.3, a), mat=0)
    # thwarts and floorboards
    for x in THWARTS:
        w = half_width_at(x, THWART_Z) - 0.02
        lib.beam(mb, (x, 0, THWART_Z - 0.015), (2 * w, 0.22, 0.03), M=Matrix.Rotation(math.pi / 2, 3, "Z"),
                 chamfer=0.004, uv=plank_uv(1, 0.22))
    lib.beam(mb, (0.30, 0, THWART_Z - 0.03), (2 * (half_width_at(0.3, THWART_Z) - 0.02), 0.45, 0.03),
             M=Matrix.Rotation(math.pi / 2, 3, "Z"), chamfer=0.004, uv=plank_uv(3, 0.45))   # stern seat
    for yy in (-0.2, 0.0, 0.2):
        lib.beam(mb, (1.5, yy, FLOOR_Z - 0.012), (2.3, 0.14, 0.024), chamfer=0.003, uv=plank_uv(7, 0.14))
    # oarlocks on the gunwales between the thwarts
    for side in (-1, 1):
        p = rb_point(1.55, 1.0, side) + V((0, 0, 0.03))
        pts = [p + V((-0.035, 0, 0.0)), p + V((-0.035, 0, 0.07)), p + V((-0.02, 0, 0.1)), p + V((0.02, 0, 0.1)),
               p + V((0.035, 0, 0.07)), p + V((0.035, 0, 0.0))]
        Loft(pts, lambda t: {"rx": 0.007, "ry": 0.007}, n=5, seg=0.02, frame="up", up=V((0, 1, 0)),
             cap0="flat", cap1="flat").build(mb, mat=1)
        Loft([p - V((0, 0, 0.05)), p], lambda t: {"rx": 0.009, "ry": 0.009}, n=5, seg=0.05, frame="up", up=V((1, 0, 0)),
             cap0="flat", cap1="flat").build(mb, mat=1)
    # two oars lying inside, blades forward, resting on the thwarts
    for side in (-1, 1):
        top = V((0.25, side * 0.13, THWART_Z + 0.025))
        d = V((1.0, -side * 0.02, 0.06)).normalized()
        SK.oar(mb, top, d, 2.35, 0)
    mb.transform(Matrix.Translation((-L / 2, 0, 0)))     # the hull spans x 0..L: centre it
    obj = mb.object("rowboat", [wmat, iron], origin=(0, 0, 0), auto_smooth=45)
    for i, x in enumerate(THWARTS):
        lib.empty(f"crew_{i}", location=(x - L / 2, 0, FLOOR_Z), rotation=(0, 0, -math.pi / 2), parent=obj)
    print(f"  rowboat: {lib.tri_count(obj)} tris")
    return lib.export("rowboat")


# --------------------------------------------------------------------------------------------
# Treasure chest
# --------------------------------------------------------------------------------------------

PLAT = (3.5, 1.4, 0.45)
CHEST = {"W": 2.0, "D": 1.0, "H": 0.95, "rise": 0.34, "y": 0.18}
LID_OPEN = -110.0


def treasure_uv(cell):
    """A cell (col, row) of the 4 x 4 treasure atlas (rows 0-1 of cells are the top half)."""
    c, r = cell

    def m(u, v):
        return ((c + 0.08 + 0.84 * u) / 4, 1 - (r + 0.08 + 0.84 * (1 - v)) / 4)
    return m


COIN, GOLD, RUBY, EMERALD, SAPPHIRE, AMETHYST, PEARL, SILVER = (0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1)


def coin(mb, c, n, r, mat, rng, sides=8):
    n = n.normalized()
    ref = V((1, 0, 0)) if abs(n.x) < 0.9 else V((0, 1, 0))
    x = n.cross(ref).normalized()
    y = n.cross(x)
    t = r * 0.16
    ph = rng.uniform(0, math.tau)
    top, bot = [], []
    uvc = treasure_uv(COIN)
    for i in range(sides):
        a = ph + math.tau * i / sides
        d = x * math.cos(a) + y * math.sin(a)
        top.append((mb.v(c + d * r + n * t), uvc(0.5 + 0.5 * math.cos(a - ph), 0.5 + 0.5 * math.sin(a - ph))))
        bot.append((mb.v(c + d * r - n * t), uvc(0.5 + 0.5 * math.cos(a - ph), 0.5 + 0.5 * math.sin(a - ph))))
    for ring, flip in ((top, False), (bot, True)):
        for i in range(1, sides - 1):
            tri = [ring[0], ring[i], ring[i + 1]]
            if flip:
                tri = tri[::-1]
            mb.f([q[0] for q in tri], [q[1] for q in tri], None, mat)
    ug = treasure_uv(GOLD)
    for i in range(sides):
        j = (i + 1) % sides
        mb.f((bot[i][0], bot[j][0], top[j][0], top[i][0]), [ug(0.1, 0.1), ug(0.9, 0.1), ug(0.9, 0.3), ug(0.1, 0.3)], None, mat)


def gem(mb, c, r, cell, mat, rng):
    R = Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.5, 0.5), 3, "X")
    pts = [V((1, 0, 0)), V((0, 1, 0)), V((-1, 0, 0)), V((0, -1, 0))]
    top, bot = c + R @ V((0, 0, r * 0.8)), c + R @ V((0, 0, -r * 1.1))
    ring = [c + R @ (p * r) for p in pts]
    uv = treasure_uv(cell)
    for i in range(4):
        j = (i + 1) % 4
        a, b = ring[i], ring[j]
        mb.f((mb.v(a), mb.v(b), mb.v(top)), [uv(0.1, 0.5), uv(0.9, 0.5), uv(0.5, 0.95)], None, mat)
        mb.f((mb.v(b), mb.v(a), mb.v(bot)), [uv(0.9, 0.5), uv(0.1, 0.5), uv(0.5, 0.05)], None, mat)


def pearl(mb, c, r, mat):
    lib.pumpkin(mb, c, r, r, ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0, nu=6, nv=4, fullness=1.0,
                uvmap=lambda u, v: treasure_uv(PEARL)(u, v), mat=mat)


def heap_surface(x0, x1, y0, y1, z0, height, seed, edge_drop=0.05):
    from mathutils import noise as mn
    off = V((seed * 1.7, seed * 0.3, 0))

    def h(x, y):
        fx = (x - (x0 + x1) / 2) / ((x1 - x0) / 2)
        fy = (y - (y0 + y1) / 2) / ((y1 - y0) / 2)
        r = min(1.0, math.hypot(fx * 0.9, fy * 0.8))
        base = height * (1 - r * r) ** 0.8 - edge_drop * r ** 4
        return z0 + base + 0.03 * mn.noise(V((x * 4, y * 4, 0)) + off) + 0.012 * mn.noise(V((x * 13, y * 13, 0)) + off)
    return h


def build_heap(mb, x0, x1, y0, y1, z0, height, seed, mat, n_coins, n_gems, n_pearls, nx=14, ny=8, round_=False):
    h = heap_surface(x0, x1, y0, y1, z0, height, seed)
    rng = lib.seeded(seed)

    def fn(u, v):
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * v
        if round_:   # a round pile: squeeze the rim to the ground
            fx, fy = u * 2 - 1, v * 2 - 1
            r = math.hypot(fx, fy)
            if r > 1:
                x, y = (x0 + x1) / 2 + fx / r * (x1 - x0) / 2, (y0 + y1) / 2 + fy / r * (y1 - y0) / 2
            return V((x, y, max(h(x, y), z0)))
        return V((x, y, h(x, y)))

    def uv(u, v):
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * v
        return (x / 1.0, 0.02 + 0.46 * ((y / 0.5) % 1.0))
    lib.grid_patch(mb, fn, nx, ny, uvmap=uv, mat=mat, outward=V((0, 0, 1)))
    from mathutils import noise as mn

    def place():
        x, y = rng.uniform(x0 + 0.05, x1 - 0.05), rng.uniform(y0 + 0.05, y1 - 0.05)
        if round_ and math.hypot((x - (x0 + x1) / 2) / ((x1 - x0) / 2), (y - (y0 + y1) / 2) / ((y1 - y0) / 2)) > 0.9:
            return None
        return V((x, y, h(x, y)))
    for _ in range(n_coins):
        p = place()
        if p is None:
            continue
        nrm = V((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), 1)).normalized()
        coin(mb, p + V((0, 0, 0.012)), nrm, rng.uniform(0.026, 0.036), mat, rng)
    for _ in range(n_gems):
        p = place()
        if p is None:
            continue
        gem(mb, p + V((0, 0, 0.02)), rng.uniform(0.022, 0.04), rng.choice([RUBY, EMERALD, SAPPHIRE, AMETHYST]), mat, rng)
    for _ in range(n_pearls):
        p = place()
        if p is None:
            continue
        pearl(mb, p + V((0, 0, 0.012)), rng.uniform(0.014, 0.022), mat)
    return h


def chest_planks(mb, cx, cy, z0, W, D, H):
    """The chest body: plank walls, corner posts, straps and the floor (all chest_wood)."""
    t = 0.045
    rows = 4
    ph = H / rows
    for k in range(rows):
        zc = z0 + ph * (k + 0.5)
        for sy in (-1, 1):   # front/back walls along X
            lib.beam(mb, (cx, cy + sy * (D / 2 - t / 2), zc), (W - 0.02, t, ph - 0.008), chamfer=0.006,
                     uv=plank_uv(k % 3, ph))
        for sx in (-1, 1):   # end walls along Y
            lib.beam(mb, (cx + sx * (W / 2 - t / 2), cy, zc), (D - 0.02, t, ph - 0.008), M=Matrix.Rotation(math.pi / 2, 3, "Z"),
                     chamfer=0.006, uv=plank_uv((k + 1) % 3, ph))
    lib.beam(mb, (cx, cy, z0 + 0.02), (W - 0.04, D - 0.04, 0.04), chamfer=0.0, uv=plank_uv(1, D))
    # corner posts and straps, standing a little proud
    for sx in (-1, 1):
        for sy in (-1, 1):
            lib.beam(mb, (cx + sx * (W / 2 - 0.035), cy + sy * (D / 2 - 0.035), z0 + H / 2), (H + 0.01, 0.10, 0.10),
                     M=Matrix.Rotation(math.pi / 2, 3, "Y"), chamfer=0.01, uv=plank_uv(2, 0.1))
    for zc in (z0 + 0.05, z0 + H - 0.05):
        for sy in (-1, 1):
            lib.beam(mb, (cx, cy + sy * (D / 2 + 0.008), zc), (W - 0.16, 0.03, 0.09), chamfer=0.006, uv=plank_uv(5, 0.09))
        for sx in (-1, 1):
            lib.beam(mb, (cx + sx * (W / 2 + 0.008), cy, zc), (D - 0.16, 0.03, 0.09), M=Matrix.Rotation(math.pi / 2, 3, "Z"),
                     chamfer=0.006, uv=plank_uv(5, 0.09))
    for fx in (-0.5, 0.5):
        lib.beam(mb, (cx + fx * W * 0.5, cy - D / 2 - 0.01, z0 + H / 2), (H - 0.18, 0.03, 0.10),
                 M=Matrix.Rotation(math.pi / 2, 3, "Y"), chamfer=0.006, uv=plank_uv(5, 0.10))


def lid_mesh(mb, cx, yf, yb, ztop, W, rise):
    """The domed lid, closed: planks running along X over a half-ellipse arch from the front edge
    (yf) to the hinge (yb), arched straps and two end boards. Thickness 0.04."""
    D = yb - yf
    yc = (yf + yb) / 2
    t = 0.04

    def arch(a, grow=0.0):
        # a in [0, 1] from front to back
        ang = math.pi * (1 - a)
        return V((0, yc + (D / 2 + grow) * math.cos(ang), ztop + (rise + grow) * math.sin(ang)))
    n_pl = 7
    for k in range(n_pl):
        a0, a1 = k / n_pl + 0.004, (k + 1) / n_pl - 0.004
        out, inn, uvs = [], [], []
        for i in range(9):
            x = cx - W / 2 + W * i / 8
            ro, ri, ru = [], [], []
            for j in range(3):
                a = a0 + (a1 - a0) * j / 2
                ro.append(arch(a, 0.0) + V((x, 0, 0)))
                ri.append(arch(a, -t) + V((x, 0, 0)))
                ru.append(row_uv(k % 3, x + 0.5 * k, j / 2))
            out.append(ro)
            inn.append(ri)
            uvs.append(ru)
        shell(mb, out, inn, uvs, 0)
    # end boards (half ellipses) at both ends
    for sx in (-1, 1):
        for xo, flip in ((sx * (W / 2), sx < 0), (sx * (W / 2 - 0.04), sx > 0)):
            c = mb.v(V((cx + xo, yc, ztop)))
            ring = [mb.v(arch(i / 12, -0.002) + V((cx + xo, 0, 0))) for i in range(13)]
            for i in range(12):
                tri = (c, ring[i], ring[i + 1])
                if flip:
                    tri = tri[::-1]
                mb.f(tri, [row_uv(4, 0.5, 0.5), row_uv(4, 0.5 + 0.03 * i, 0.9), row_uv(4, 0.53 + 0.03 * i, 0.9)], None, 0)
    # arched straps at the ends and at a third
    for fx in (-0.47, -0.17, 0.17, 0.47):
        x = cx + fx * W
        pts = [arch(i / 14, 0.012) + V((x, 0, 0)) for i in range(15)]
        Loft(pts, lambda t_: {"rx": 0.045, "ry": 0.012, "p": 4}, n=4, seg=0.08, frame="rmf", up=V((0, -1, 0)),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s, a: row_uv(5, s * 1.2, a), mat=0)
    # rim
    for yy in (yf, yb):
        lib.beam(mb, (cx, yy, ztop + 0.025), (W, 0.05, 0.05), chamfer=0.006, uv=plank_uv(5, 0.05))


def chain(mb, a, b, mat, link=0.07):
    d = b - a
    n = max(2, int(d.length / (link * 0.78)))
    dn = d.normalized()
    side = dn.cross(V((0, 0, 1)))
    side = side.normalized() if side.length > 1e-6 else V((1, 0, 0))
    up = side.cross(dn)
    uv = treasure_uv(SILVER)
    for i in range(n):
        c = a + d * ((i + 0.5) / n)
        ax = side if i % 2 == 0 else up
        pts = []
        for k in range(8):
            ang = math.tau * k / 8
            pts.append(c + dn * (math.cos(ang) * link * 0.5) + ax * (math.sin(ang) * link * 0.3))
        Loft(pts, lambda t: {"rx": 0.008, "ry": 0.008}, n=4, seg=0.03, closed=True, frame="rmf",
             up=ax.cross(dn)).build(mb, uvmap=lambda s, a_: uv(s, a_), mat=mat)


def build_chest():
    lib.reset()
    wc, wn = wood("chest-wood", ["#a8947a", "#9a876e", "#b4a086", "#3a3029", "#2c241e"], 71,
                  row_tones=[0, 1, 2, 0, 1, 2, 3, 4], dirt=0.25, wear=0.06)
    tre = lib.paint_named("tex_pirates.py", {"kind": "treasure"}, {"tex": "pirates-treasure.jpg"})["tex"]
    bone_t, _, _ = SK.textures()
    gp = lib.paint_named("tex_pirates.py", {"kind": "pumpkin", "ribs": 10, "color": "#9aa384", "groove": "#5f6a52",
                                      "stem": "#6a5a3a", "seed": 8}, {"tex": "pirates-pumpkin-pale.jpg"})["tex"]
    m_wood = lib.material("chest_wood", base_tex=wc, normal_tex=wn, roughness=0.8, specular=0.3)
    m_gold = lib.material("glow_gold", base_tex=tre, emission_tex=tre, emission_strength=0.35, roughness=0.3,
                          metallic=0.85, specular=0.6)
    m_bone = lib.material("bone", base_tex=bone_t, roughness=0.7, specular=0.35)
    m_pump = lib.material("pumpkin_skin", base_tex=gp, roughness=0.55, specular=0.35)
    mats = [m_wood, m_gold, m_bone, m_pump]
    W, D, H, rise, cy = CHEST["W"], CHEST["D"], CHEST["H"], CHEST["rise"], CHEST["y"]
    pw, pd, ph = PLAT
    z0 = ph
    root = lib.empty("treasure")
    mb = MB()
    # the platform: top boards over a frame of side boards
    n_top = 7
    for k in range(n_top):
        y = -pd / 2 + pd * (k + 0.5) / n_top
        lib.beam(mb, (0, y, ph - 0.025), (pw, pd / n_top - 0.008, 0.05), chamfer=0.006, uv=plank_uv(6 + k % 2, pd / n_top))
    for k in range(3):
        zc = 0.07 + k * 0.13
        for sy in (-1, 1):
            lib.beam(mb, (0, sy * (pd / 2 - 0.02), zc), (pw, 0.04, 0.125), chamfer=0.005, uv=plank_uv(6 + k % 2, 0.125))
        for sx in (-1, 1):
            lib.beam(mb, (sx * (pw / 2 - 0.02), 0, zc), (pd - 0.08, 0.04, 0.125), M=Matrix.Rotation(math.pi / 2, 3, "Z"),
                     chamfer=0.005, uv=plank_uv(7 - k % 2, 0.125))
    chest_planks(mb, 0, cy, z0, W, D, H)
    yf, yb = cy - D / 2, cy + D / 2
    ztop = z0 + H
    # the heap inside, the loose treasure on it, and two spilled piles on the platform
    rng = lib.seeded(5)
    h = build_heap(mb, -W / 2 + 0.05, W / 2 - 0.05, yf + 0.05, yb - 0.05, ztop - 0.02, 0.26, 3, 1, 150, 22, 26, nx=18, ny=9)
    for (x0, x1, y0, y1, hh, sd) in ((-1.68, -1.05, -0.62, 0.15, 0.30, 11), (1.02, 1.70, -0.60, 0.30, 0.34, 12)):
        build_heap(mb, x0, x1, y0, y1, ph, hh, sd, 1, 40, 8, 10, nx=9, ny=9, round_=True)
    # a crown on the heap (right), with gems on its points
    cxr, cyr = 0.52, cy - 0.05
    cz = h(cxr, cyr) - 0.02
    band = []
    for i in range(16):
        a = math.tau * i / 16
        band.append(V((cxr + 0.14 * math.cos(a), cyr + 0.14 * math.sin(a), cz)))
    for i in range(16):
        j = (i + 1) % 16
        lo1, lo2 = band[i], band[j]
        tip = 0.17 if i % 2 == 0 else 0.10
        hi1 = lo1 + V((0, 0, 0.09 if i % 2 else tip))
        hi2 = lo2 + V((0, 0, 0.09 if j % 2 else tip))
        uv = treasure_uv(GOLD)
        for flip in (False, True):
            q = [mb.v(lo1), mb.v(lo2), mb.v(hi2), mb.v(hi1)]
            uq = [uv(0, 0), uv(1, 0), uv(1, 1), uv(0, 1)]
            mb.f(q[::-1] if flip else q, uq[::-1] if flip else uq, None, 1)
        if i % 2 == 0:
            gem(mb, hi1 + V((0, 0, 0.012)), 0.018, [RUBY, EMERALD, SAPPHIRE][i % 3], 1, rng)
    # the pale pumpkin, half sunk in the coins (left)
    px, py = -0.45, cy + 0.1
    lib.pumpkin(mb, (px, py, h(px, py) + 0.05), 0.22, 0.16, ribs=10, groove=0.12, top_dimple=0.25, nu=40, nv=12,
                uvmap=SK.uv_pumpkin, mat=3, seed=5)
    top = V((px, py, h(px, py) + 0.05 + 0.16 * 0.8))
    Loft([top - V((0, 0, 0.03)), top + V((0.01, 0, 0.04)), top + V((0.04, 0.01, 0.08))],
         lambda t: {"rx": 0.025 - 0.006 * t, "ry": 0.022}, n=6, seg=0.03, frame="up", up=V((0, -1, 0)),
         cap0="open", cap1="flat").build(mb, uvmap=SK.uv_stem, mat=3)
    # skulls: one on the heap, and a little one for the lock on the front
    for (pos, sc, rz, rx) in ((V((-0.05, cy - 0.28, 0.0)), 1.0, 0.35, -0.15), (V((0, yf - 0.06, ztop - 0.13)), 0.55, 0.0, 0.0)):
        sm = MB()
        SK.skull(sm, 2)
        if pos.z == 0.0:
            pos.z = h(pos.x, pos.y) + 0.02
        M = (Matrix.Translation(pos) @ Matrix.Rotation(rz, 4, "Z") @ Matrix.Rotation(rx, 4, "X") @ Matrix.Scale(sc, 4)
             @ Matrix.Translation(-SK.SKULL_C + V((0, 0, 0.05))))
        sm.transform(M)
        mb.extend(sm)
    body = mb.object("chest", mats, origin=(0, 0, 0), auto_smooth=40)
    lib.set_parent(body, root)
    # lid: modelled closed around its hinge, then opened on the node
    lm = MB()
    lid_mesh(lm, 0, yf - 0.02, yb + 0.02, ztop, W + 0.04, rise)
    hinge = V((0, yb + 0.02, ztop))
    lid = lm.object("lid", [m_wood], origin=hinge, auto_smooth=40)
    lid.rotation_euler = (math.radians(LID_OPEN), 0, 0)
    lib.set_parent(lid, body)
    # chains from the open lid's front corners down to the chest's front corners
    import bpy
    bpy.context.view_layer.update()
    cm = MB()
    for sx in (-1, 1):
        a = lid.matrix_world @ (V((sx * (W / 2 - 0.02), yf - 0.02, ztop + 0.02)) - hinge)
        b = V((sx * (W / 2 + 0.02), yf + 0.05, ztop - 0.05))
        chain(cm, a, b, 0)
    chains = cm.object("chains", [m_gold], origin=(0, 0, 0))
    lib.set_parent(chains, body)
    tris = sum(lib.tri_count(o) for o in (body, lid, chains))
    print(f"  treasure-chest: {tris} tris (body {lib.tri_count(body)}, lid {lib.tri_count(lid)}, chains {lib.tri_count(chains)})")
    return lib.export("treasure-chest")


# --------------------------------------------------------------------------------------------
# Pumpkin palm
# --------------------------------------------------------------------------------------------

def build_palm():
    lib.reset()
    skin = lib.paint_named("tex_pirates.py", {"kind": "pumpkin", "ribs": 8, "color": "#ec7a1e", "groove": "#a4440e"},
                     {"tex": "pirates-pumpkin-palm.jpg"})["tex"]
    frond_t = lib.paint_named("tex_pirates.py", {"kind": "frond", "color": "#46e050", "dark": "#14862e", "rachis": "#a8f06a"},
                        {"tex": "pirates-frond.png"})["tex"]
    m_skin = lib.material("pumpkin_skin", base_tex=skin, roughness=0.55, specular=0.35)
    m_frond = lib.material("glow_fronds", base_tex=frond_t, emission_tex=frond_t, roughness=0.6, alpha_clip=0.5,
                           double_sided=True)
    mb = MB()
    rng = lib.seeded(9)
    z = 0.0
    sizes = [(0.225, 0.172), (0.215, 0.166), (0.207, 0.160), (0.200, 0.155), (0.192, 0.150), (0.185, 0.145)]
    lean = V((0.0, 0.0, 0.0))
    for k, (rx, rz) in enumerate(sizes):
        lean = lean + V((0.018 * math.sin(k * 1.3), -0.012 * k, 0))
        c = V((lean.x, lean.y, z + rz * 0.92))
        M = Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "X") @ Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "Y") @ \
            Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z")
        lib.pumpkin(mb, c, rx, rz, ribs=8, groove=0.11, groove_sharp=0.4, top_dimple=0.28, bottom_dimple=0.22,
                    nu=40, nv=12, uvmap=SK.uv_pumpkin, mat=0, M=M, seed=k + 2, wobble=0.04)
        z += rz * 1.62
    crown = V((lean.x, lean.y, z + 0.02))
    # glowing green "coconuts" (lights) in the crown
    for i in range(3):
        a = math.tau * i / 3 + 0.4
        c = crown + V((0.07 * math.cos(a), 0.07 * math.sin(a), 0.03))
        lib.pumpkin(mb, c, 0.05, 0.045, ribs=1, groove=0.0, top_dimple=0.0, bottom_dimple=0.0, nu=8, nv=5, fullness=1.0,
                    uvmap=lambda u, v: (0.5, 0.5), mat=1)
    # fronds: arching up and out, then drooping, each a gently folded strip
    n_fr = 13
    for i in range(n_fr):
        a = math.tau * i / n_fr * 1.0 + rng.uniform(-0.12, 0.12)
        out = V((math.cos(a), math.sin(a), 0))
        ln = rng.uniform(0.95, 1.2) if i % 2 == 0 else rng.uniform(0.7, 0.9)
        lift = rng.uniform(0.35, 0.65) if i % 2 == 0 else rng.uniform(0.55, 0.8)
        pts = []
        for j in range(9):
            s = j / 8
            pts.append(crown + out * (ln * s) + V((0, 0, lift * math.sin(math.pi * s * 0.75) - 0.35 * s * s * ln)))
        side = out.cross(V((0, 0, 1))).normalized()
        ids = []
        for j, p in enumerate(pts):
            s = j / 8
            w = 0.30 * ln
            fold = V((0, 0, -0.06 * math.sin(math.pi * min(s * 1.2, 1))))
            ids.append((mb.v(p - side * w + fold), mb.v(p), mb.v(p + side * w + fold)))
        for j in range(8):
            u0, u1 = j / 8, (j + 1) / 8
            for k, (va, vb) in enumerate(((0.0, 0.5), (0.5, 1.0))):
                q = [ids[j][k], ids[j + 1][k], ids[j + 1][k + 1], ids[j][k + 1]]
                mb.f(q, [(u0, 1 - va), (u1, 1 - va), (u1, 1 - vb), (u0, 1 - vb)], None, 1)
    obj = mb.object("palm", [m_skin, m_frond], origin=(0, 0, 0), auto_smooth=50)
    hi = max(v[2] for v in mb.verts)
    print(f"  pumpkin-palm: {lib.tri_count(obj)} tris, height {hi:.2f} m")
    return lib.export("pumpkin-palm")


# --------------------------------------------------------------------------------------------
# Barrel (lying on its side, axis along X)
# --------------------------------------------------------------------------------------------

def build_barrel():
    lib.reset()
    wc, wn = wood("barrel-wood", ["#7a5a3a", "#6c5034", "#86643f", "#5e4630"], 81, dirt=0.3, joints=0, knots=1, nails=False)
    m_wood = lib.material("barrel_wood", base_tex=wc, normal_tex=wn, roughness=0.75, specular=0.3)
    m_iron = lib.material("iron", color="#56524c", roughness=0.45, metallic=0.8)
    L, r_end, r_mid = 0.9, 0.255, 0.31
    staves = 16
    mb = MB()

    def rad(x):
        f = x / (L / 2)
        return r_end + (r_mid - r_end) * (1 - f * f)
    nx = 10
    for k in range(staves):
        a0, a1 = math.tau * k / staves, math.tau * (k + 1) / staves
        out, inn, uvs = [], [], []
        for i in range(nx + 1):
            x = -L / 2 + L * i / nx
            r = rad(x)
            ro, ri, ru = [], [], []
            for j in range(3):
                a = a0 + (a1 - a0) * (0.02 + 0.96 * j / 2)
                bulge = 1 + 0.012 * math.sin(math.pi * j / 2)
                p = V((x, r * bulge * math.cos(a), r * bulge * math.sin(a)))
                ro.append(p)
                ri.append(V((x, (r - 0.022) * math.cos(a), (r - 0.022) * math.sin(a))))
                ru.append(row_uv(k, x + 0.3 * k, j / 2))
            out.append(ro)
            inn.append(ri)
            uvs.append(ru)
        shell(mb, out, inn, uvs, 0)
    # the heads, set in a little from the ends
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.025)
        c = mb.v(V((x, 0, 0)))
        ring = [mb.v(V((x, (r_end - 0.018) * math.cos(math.tau * i / 16), (r_end - 0.018) * math.sin(math.tau * i / 16)))) for i in range(16)]
        for i in range(16):
            j = (i + 1) % 16
            tri = (c, ring[i], ring[j]) if sx > 0 else (c, ring[j], ring[i])
            pa = [V((0, 0)), V((math.cos(math.tau * i / 16), math.sin(math.tau * i / 16))), V((math.cos(math.tau * j / 16), math.sin(math.tau * j / 16)))]
            uvq = [row_uv(int(3 + p.y * 2.5), 0.5 + p.x * 0.25, 0.5) for p in pa]
            mb.f(tri, uvq if sx > 0 else [uvq[0], uvq[2], uvq[1]], None, 0)
    # hoops
    for x in (-0.40, -0.28, 0.28, 0.40):
        r = rad(x) + 0.006
        pts = [V((x, r * math.cos(math.tau * i / 24), r * math.sin(math.tau * i / 24))) for i in range(24)]
        Loft(pts, lambda t: {"rx": 0.022, "ry": 0.004, "p": 4}, n=4, seg=0.08, closed=True, frame="up",
             up=V((1, 0, 0))).build(mb, mat=1)
    # lying on its side, rolled a little, resting on the ground
    M = Matrix.Translation((0, 0, r_mid + 0.01)) @ Matrix.Rotation(math.radians(12), 4, "X")
    mb.transform(M)
    lo = min(v[2] for v in mb.verts)
    mb.transform(Matrix.Translation((0, 0, -lo)))
    obj = mb.object("barrel", [m_wood, m_iron], origin=(0, 0, 0), auto_smooth=40)
    print(f"  barrel: {lib.tri_count(obj)} tris")
    return lib.export("barrel")


def main():
    for key, fn in (("rowboat", build_rowboat), ("chest", build_chest), ("palm", build_palm), ("barrel", build_barrel)):
        if ONLY is None or key in ONLY:
            fn()


if __name__ == "__main__":
    main()
