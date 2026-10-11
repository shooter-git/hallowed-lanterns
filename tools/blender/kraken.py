# SPDX-License-Identifier: MIT
"""The Kraken's Wreck: giant glowing inflatable tentacles, the tentacle wrapping a wrecked hull,
and the big inflatable pumpkin (reference/kraken-1.jpg, kraken-2.jpg).

    blender -b --factory-startup -P tools/blender/kraken.py [-- only=a,b,c,arch,pumpkin]

Writes public/models/kraken-tentacle-a.glb (6.5 m), kraken-tentacle-b.glb (5 m),
kraken-tentacle-c.glb (4 m, the tip curled right over), kraken-arch.glb and
inflatable-pumpkin.glb.

The tentacles are orange nylon tubes lit from inside, rising out of the ground in an S and
curling over at the tip. Their inner edge (the concave side of the curl, +X at the root) is a
brighter lemon band with a scalloped border, and a zigzag of puffy coral suckers runs along it.
A black blower port sits low on the back of each one.

Nodes: one mesh `tentacle` (root, pivot at the footprint centre on the ground) with a second UV
set `along` (TEXCOORD_1: u = 0 at the root -> 1 at the tip; the suckers and the port carry the
value of where they sit), so the engine can sway and curl it in a vertex shader.
kraken-arch: root `wreck` (empty) -> `hull` (static) and `tentacle` (pivot where it leaves
the ground, `along` as above).

Materials: `glow_inflatable` (one texture as base colour and emission), `glow_suckers`,
`blower_port` (black plastic); the hull adds `hull_wood`.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

TEX = 1024
ARGS = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
ONLY = set(ARGS["only"].split(",")) if "only" in ARGS else None

ORANGE = [[0.30, "#6e2403"], [0.62, "#c9500a"], [0.80, "#f07414"], [0.92, "#ff8c1c"],
          [1.02, "#ff9e2a"], [1.15, "#ffb848"], [1.35, "#ffd47a"]]
LEMON = [[0.50, "#d08a10"], [0.80, "#f0c020"], [1.00, "#ffdc30"], [1.15, "#ffe850"], [1.40, "#fff49a"]]
SUCKER = [[0.55, "#c84a30"], [0.80, "#ec6e4e"], [1.00, "#fb9c80"]]
PAINT = {"orange": ORANGE, "lemon": LEMON, "sucker": SUCKER, "line_width": 0.012, "crease_width": 0.07,
         "band_seam": "#e88a18",
         "pumpkin": [[0.30, "#5a1402"], [0.60, "#b83008"], [0.80, "#e44a0c"], [0.95, "#ff6a18"],
                     [1.10, "#ff8a30"], [1.30, "#ffb060"]],
         "stem": [[0.5, "#4a1e06"], [0.8, "#8a3a0c"], [1.0, "#b04e14"], [1.2, "#d06a20"]]}

UP_FRONT = (0, -1, 0)   # loft frame: a = 0.5 faces the viewer (-Y), a = 0.25 is the inner edge
BAND_A = 0.285          # the band's middle: on the inner edge, turned a little toward the viewer


# --------------------------------------------------------------------------------------------
# Tentacles
# --------------------------------------------------------------------------------------------

# ctrl: spine control points (x, y, z) in metres; curl: (length, start radius, end radius) of the
# tip curl, turning clockwise as seen from the front; radius keys (t, r).
TENTACLES = {
    "a": {
        "ctrl": [(0, 0, 0), (-0.05, 0.0, 0.50), (-0.45, 0.04, 1.50), (-1.05, 0.08, 2.60), (-1.42, 0.10, 3.62),
                 (-1.45, 0.08, 4.55), (-1.12, 0.04, 5.38), (-0.62, 0.0, 5.95)],
        "curl": (1.15, 1.05, 0.40),
        "radius": [(0.0, 0.84), (0.025, 0.74), (0.07, 0.68), (0.25, 0.62), (0.5, 0.50), (0.7, 0.36),
                   (0.85, 0.22), (0.95, 0.11), (1.0, 0.035)],
        "port": (0.035, 0.66),
        "seed": 1,
    },
    "b": {
        "ctrl": [(0, 0, 0), (-0.03, 0.0, 0.50), (-0.28, -0.04, 1.38), (-0.66, -0.06, 2.32), (-0.84, -0.05, 3.20),
                 (-0.70, -0.03, 4.00), (-0.32, 0.0, 4.58)],
        "curl": (1.0, 0.85, 0.30),
        "radius": [(0.0, 0.70), (0.03, 0.60), (0.08, 0.54), (0.25, 0.50), (0.5, 0.40), (0.7, 0.29),
                   (0.85, 0.18), (0.95, 0.09), (1.0, 0.03)],
        "port": (0.04, 0.70),
        "seed": 2,
    },
    "c": {
        "ctrl": [(0, 0, 0), (0.0, 0.0, 0.42), (-0.19, 0.05, 1.17), (-0.42, 0.08, 1.96), (-0.45, 0.08, 2.65),
                 (-0.19, 0.05, 3.23), (0.23, 0.02, 3.60)],
        "curl": (2.0, 0.62, 0.16),
        "radius": [(0.0, 0.66), (0.03, 0.56), (0.08, 0.50), (0.25, 0.46), (0.5, 0.37), (0.7, 0.27),
                   (0.85, 0.17), (0.95, 0.085), (1.0, 0.03)],
        "port": (0.045, 0.64),
        "seed": 3,
    },
}


def spine(ctrl, curl, axis=(0, 1, 0)):
    pts = [Vector(p) for p in ctrl]
    if curl:
        L, r0, r1 = curl
        head = (pts[-1] - pts[-2]).normalized()
        cp = lib.curl(pts[-1], head, Vector(axis), L, r0, r1, step=0.025)
        k = max(1, int(round(0.22 / 0.025)))
        sparse = cp[k - 1::k]
        if (sparse[-1] - cp[-1]).length > 0.03:
            sparse.append(cp[-1])
        pts += sparse
    return pts


def tentacle_offset(rad, layout_dims, rings, band_a=BAND_A):
    """Fabric puff (panels bulge, seams pinch) and a slightly flattened inner edge."""
    layout = lib.panel_layout([0.62, 0.88], rings)
    puff = lib.puff_offset(layout, layout_dims, depth=0.10, cap=0.03)

    def off(t, a, sec):
        o = puff(t, a, sec)
        da = ((a - band_a) + 0.5) % 1.0 - 0.5
        o -= 0.10 * rad(t) * math.exp(-(da / 0.09) ** 2)
        return o
    return off


class Tentacle:
    """One lofted tentacle with its band, suckers and blower port."""

    def __init__(self, ctrl, curl, radius_keys, *, axis=(0, 1, 0), up=UP_FRONT, frame="up", n=28, seg=0.075,
                 ring_step=1.45, port=None, seed=1, sucker_scale=1.0, flat_root=True):
        self.pts = spine(ctrl, curl, axis)
        self.radius_keys = radius_keys

        def rad(t):
            return lerp_keys(radius_keys, t)
        self.rad = rad

        def sec(t):
            r = rad(t)
            return {"rx": r * 0.96, "ry": r, "p": 2.0}
        probe = Loft(self.pts, sec, n=n, seg=seg, frame=frame, up=up)
        L = probe.L
        nr = max(1, int(round(L / ring_step)))
        self.rings = [k / (nr + 1) for k in range(1, nr + 1)]
        self.loft = Loft(self.pts, sec, n=n, seg=seg, frame=frame, up=up, extra_t=self.rings,
                         cap0="flat" if flat_root else "dome", cap1="point", cap1_len=0.06)
        self.loft.offset = tentacle_offset(rad, self.loft.nominal, self.rings)
        self.L = self.loft.L
        self.port = port
        self.seed = seed
        self.sucker_scale = sucker_scale
        self._suckers()

    def band_w(self, t):
        # half width of the lemon band (metres)
        return 0.23 * self.rad(t) + 0.01

    def _suckers(self):
        """A zigzag of suckers along the inner edge: (t, side, radius)."""
        out = []
        rng = lib.seeded(self.seed)
        t = 0.06
        side = 1
        while t < 0.975:
            r = self.rad(t)
            rs = max(0.034, 0.24 * r) * self.sucker_scale
            out.append((t, side, rs * rng.uniform(0.94, 1.06)))
            t += (rs * 2.35) / self.L
            side = -side
        self.suckers = out

    def lobe_amp(self, t, rs):
        return rs * 1.5 + 0.05 * self.rad(t)

    def lobes(self):
        lob = []
        for t, side, rs in self.suckers:
            lob.append([t, side, rs * 1.9, self.lobe_amp(t, rs)])
        return lob

    def tex_part(self, rect, bright):
        return {"kind": "tube", "rect": rect, "dims": self.loft.nominal, "long": [0.62, 0.88],
                "rings": self.rings, "pad": 0,
                "band": {"a": BAND_A, "w": [[k / 20, self.band_w(k / 20)] for k in range(21)], "lobes": self.lobes(),
                         "boost": 1.10},
                "bright": bright}

    def build(self, mb, uvmap, mats=(0, 1, 2), sucker_uv=None):
        start = len(mb.verts)
        self.loft.build(mb, uvmap=uvmap, mat=mats[0], along=True)
        mb.clamp_z(0.0, start)
        for t, side, rs in self.suckers:
            circ = lib.lerp_circ(self.loft.nominal["circ"], t)
            reach = self.band_w(t) + 0.62 * self.lobe_amp(t, rs)
            a = BAND_A + side * reach / circ
            p, nrm = self.loft.surface(t, a)
            lat = (self.loft.surface(t, a + 0.01)[0] - p).normalized() * side
            T = self.loft.frame_at(t)[1]
            # lean each disc out toward its side of the zigzag so it shows past the edge
            axis = (nrm + lat * 0.45).normalized()
            sucker(mb, p - nrm * rs * 0.10, axis, T, rs, t, sucker_uv, mats[1])
        if self.port:
            t, a = self.port
            p, nrm = self.loft.surface(t, a)
            blower_port(mb, p, nrm, t, mats[2])


def sucker(mb, c, n, tdir, r, along, uvm, mat, nu=14, nv=5):
    """A puffy oval cushion (the sucker), its underside on the skin at c, facing n."""
    n = n.normalized()
    x = (tdir - n * tdir.dot(n)).normalized()
    y = n.cross(x)
    rx, ry, h = r * 1.08, r * 0.92, r * 0.80
    rows = []
    for j in range(nv + 1):
        v = j / nv                     # 0 = bottom pole (on the skin), 1 = top pole
        ph = math.pi * v
        sp_ = math.sin(ph) ** 0.55
        z = (1 - math.cos(ph)) * 0.5 * h
        if j in (0, nv):
            rows.append([(mb.v(c + n * z), (0.5, 0.5))])
            continue
        row = []
        for i in range(nu):
            th = math.tau * i / nu
            px, py = math.cos(th) * rx * sp_, math.sin(th) * ry * sp_
            row.append((mb.v(c + x * px + y * py + n * z), (0.5 + 0.48 * math.cos(th) * sp_, 0.5 + 0.48 * math.sin(th) * sp_)))
        rows.append(row)
    al = [(along, 1.0)]
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            if j == 0:
                vs = [rows[0][0], rows[1][i2], rows[1][i]]
            elif j == nv - 1:
                vs = [rows[j][i], rows[j][i2], rows[nv][0]]
            else:
                vs = [rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]]
            mb.f([q[0] for q in vs], [uvm(*q[1]) for q in vs], al * len(vs), mat)


def blower_port(mb, p, n, along, mat):
    """The black round fan port low on the tentacle: a short drum with a rim and a recess."""
    n = n.normalized()
    ref = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    x = ref.cross(n).normalized()
    y = n.cross(x)
    seg = 18
    al = [(along, 1.0)]

    def ring(r, d):
        return [mb.v(p + n * d + (x * math.cos(math.tau * i / seg) + y * math.sin(math.tau * i / seg)) * r)
                for i in range(seg)]
    rs = [ring(0.165, -0.06), ring(0.165, 0.07), ring(0.150, 0.09), ring(0.120, 0.09), ring(0.115, 0.05)]
    for A, Bq in zip(rs, rs[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            mb.f((A[i], A[j], Bq[j], Bq[i]), [(0, 0)] * 4, al * 4, mat)
    c = mb.v(p + n * 0.05)
    last = rs[-1]
    for i in range(seg):
        j = (i + 1) % seg
        mb.f((last[i], last[j], c), [(0, 0)] * 3, al * 3, mat)


def materials(tex, sucker_tex):
    glow = lib.material("glow_inflatable", base_tex=tex, emission_tex=tex, roughness=0.62, specular=0.3)
    suck = lib.material("glow_suckers", base_tex=sucker_tex, emission_tex=sucker_tex, roughness=0.5, specular=0.3)
    port = lib.material("blower_port", color="#0b0b0c", roughness=0.45, specular=0.4)
    return glow, suck, port


SUCKER_RECT = (0, 0, 256, 256)


def sucker_texture():
    out = lib.paint_named("tex_kraken.py", dict(PAINT, size=256, parts=[{"kind": "sucker", "rect": list(SUCKER_RECT)}]),
                    {"tex": "kraken-sucker.jpg"})
    return out["tex"]


def ident_uv(u, v):
    return (u, v)


def build_tentacle(key):
    lib.reset()
    spec = TENTACLES[key]
    ten = Tentacle(spec["ctrl"], spec["curl"], spec["radius"], port=spec["port"], seed=spec["seed"])
    bright = [[0.0, 1.15], [0.08, 1.25], [0.25, 1.12], [0.5, 0.98], [0.75, 0.88], [1.0, 0.80]]
    tex = lib.paint_named("tex_kraken.py", dict(PAINT, size=TEX, seed=10 + spec["seed"],
                                          parts=[ten.tex_part([0, 0, TEX, TEX], bright)]),
                    {"tex": f"kraken-tentacle-{key}.jpg"})["tex"]
    glow, suck, port = materials(tex, sucker_texture())
    mb = MB(along=True)
    ten.build(mb, uvmap=lambda s, a: (s, 1.0 - a), sucker_uv=lambda u, v: (u, v))
    obj = mb.object("tentacle", [glow, suck, port], origin=(0, 0, 0))
    hi = max(v[2] for v in mb.verts)
    xs = [v[0] for v in mb.verts]
    print(f"  tentacle-{key}: {lib.tri_count(obj)} tris, height {hi:.2f} m, x {min(xs):.2f}..{max(xs):.2f}, "
          f"{len(ten.suckers)} suckers, spine {ten.L:.2f} m")
    return lib.export(f"kraken-tentacle-{key}")


# --------------------------------------------------------------------------------------------
# The wreck: a broken ship's hull, heeled over and bow-up, and the tentacle arching over it
# --------------------------------------------------------------------------------------------

HULL = {"L": 5.6, "B": 1.25, "D": 1.75, "strakes": 9, "thick": 0.05}
WOOD_TILE = 4.0      # metres of plank per texture repeat
WOOD_ROWS = 8


def hull_point(x, f, side):
    """Outer hull surface: x from the broken end (0) to the bow stem (L), f the girth fraction from
    the keel (0) to the gunwale (1), side +-1."""
    L, B0, D0 = HULL["L"], HULL["B"], HULL["D"]
    u = min(max(x / L, 0.0), 1.0)
    B = B0 * max(1 - u ** 3.2, 0.0) ** 0.55
    keel = 0.95 * max(0.0, (u - 0.40) / 0.60) ** 2.0
    D = D0 + 0.55 * u ** 2
    th = f * math.pi / 2
    e = 2 / 2.6
    y = B * math.sin(th) ** e
    z = keel + (D - keel) * (1 - math.cos(th) ** e)
    return Vector((x, side * y, z))


def hull_normal(x, f, side):
    e = 1e-3
    p = hull_point(x, f, side)
    dx = hull_point(x + e, f, side) - hull_point(x - e, f, side)
    df = hull_point(x, min(f + e, 1), side) - hull_point(x, max(f - e, 0), side)
    n = dx.cross(df) * side
    if n.length < 1e-9:
        return Vector((0, side, 0))
    n.normalize()
    if n.dot(Vector((0, side, -0.3))) < 0:
        n = -n
    return n


def wood_uv(row, u_m, fv):
    """UV into the tileable plank texture: plank `row`, u_m metres along, fv 0..1 across."""
    r = row % WOOD_ROWS
    return (u_m / WOOD_TILE, 1.0 - (r + 0.06 + 0.88 * fv) / WOOD_ROWS)


def shell_strip(mb, pts_out, pts_in, uvs, mat):
    """A plank of thickness: grids of outer and inner points [i along][j across] + edges."""
    ni, nj = len(pts_out), len(pts_out[0])
    O = [[mb.v(p) for p in row] for row in pts_out]
    I = [[mb.v(p) for p in row] for row in pts_in]
    for i in range(ni - 1):
        for j in range(nj - 1):
            mb.f((O[i][j], O[i + 1][j], O[i + 1][j + 1], O[i][j + 1]),
                 [uvs[i][j], uvs[i + 1][j], uvs[i + 1][j + 1], uvs[i][j + 1]], None, mat)
            mb.f((I[i][j + 1], I[i + 1][j + 1], I[i + 1][j], I[i][j]),
                 [uvs[i][j + 1], uvs[i + 1][j + 1], uvs[i + 1][j], uvs[i][j]], None, mat)
    for i in range(ni - 1):        # long edges
        for j, flip in ((0, False), (nj - 1, True)):
            q = (O[i][j], I[i][j], I[i + 1][j], O[i + 1][j])
            uv = [uvs[i][j], (uvs[i][j][0], uvs[i][j][1] - 0.01), (uvs[i + 1][j][0], uvs[i + 1][j][1] - 0.01), uvs[i + 1][j]]
            if flip:
                q, uv = q[::-1], uv[::-1]
            mb.f(q, uv, None, mat)
    for i, flip in ((0, True), (ni - 1, False)):   # end grain
        for j in range(nj - 1):
            q = (O[i][j], O[i][j + 1], I[i][j + 1], I[i][j])
            uv = [uvs[i][j], uvs[i][j + 1], (uvs[i][j + 1][0] + 0.01, uvs[i][j + 1][1]), (uvs[i][j][0] + 0.01, uvs[i][j][1])]
            if flip:
                q, uv = q[::-1], uv[::-1]
            mb.f(q, uv, None, mat)


def build_hull(mb, mat):
    rng = lib.seeded(41)
    L, N, th = HULL["L"], HULL["strakes"], HULL["thick"]
    for side in (-1, 1):
        for k in range(N):
            f0, f1 = k / N, (k + 1) / N
            # the broken end: every strake snapped off at its own place, its end split and pointed
            xs = rng.uniform(0.0, 1.3) if k not in (N - 1,) else rng.uniform(0.2, 0.6)
            if k == 0:
                xs = 0.35
            tip = rng.uniform(-0.35, 0.35)
            row = rng.randrange(WOOD_ROWS)
            nx = max(8, int((L - xs) / 0.28))
            nj = 3
            out, inn, uvs = [], [], []
            for i in range(nx + 1):
                ro, ri, ru = [], [], []
                for j in range(nj):
                    fj = j / (nj - 1)
                    # the snapped end is ragged: a point at one side of the plank
                    x0 = xs + max(0.0, tip * (fj - 0.5) * 2) + 0.12 * abs(fj - 0.5)
                    x = x0 + (L - x0) * (i / nx) ** 1.0
                    f = f0 + (f1 - f0) * fj
                    p = hull_point(x, f, side)
                    n = hull_normal(x, f, side)
                    ro.append(p)
                    ri.append(p - n * th)
                    ru.append(wood_uv(row, x + 3.1 * k, fj))
                out.append(ro)
                inn.append(ri)
                uvs.append(ru)
            shell_strip(mb, out, inn, uvs, mat)
    # keel and stem post
    keel = [hull_point(x, 0.0, 1) - Vector((0, 0, 0.06)) for x in [0.5 + (L - 0.5) * i / 14 for i in range(15)]]
    keel.append(hull_point(L, 1.0, 1) + Vector((0.10, 0, 0.25)))
    Loft(keel, lambda t: {"rx": 0.07, "ry": 0.09, "p": 4.0}, n=8, seg=0.2, frame="up", up=(0, 1, 0.0001),
         cap0="flat", cap1="flat").build(mb, uvmap=lambda s_, a: wood_uv(3, s_ * 6.0, a), mat=mat)
    # gunwale rails
    for side in (-1, 1):
        rail = [hull_point(x, 1.0, side) + Vector((0, 0, 0.04)) for x in [0.4 + (L - 0.45) * i / 16 for i in range(17)]]
        Loft(rail, lambda t: {"rx": 0.08, "ry": 0.05, "p": 4.0}, n=8, seg=0.25, frame="up", up=(0, 0, 1),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s_, a: wood_uv(5, s_ * 6.0, a), mat=mat)
    # ribs (frames) inside, some broken off at the snapped end
    for xr in (0.18, 0.62, 1.15, 1.75, 2.45, 3.2, 3.95):
        fmax = 1.0 if xr > 1.0 else rng.uniform(0.35, 0.9)
        pts = []
        for side, fs in ((-1, [fmax - (fmax) * i / 6 for i in range(7)]), (1, [fmax * i / 6 for i in range(1, 7)])):
            for f in fs:
                pts.append(hull_point(xr, f, side) - hull_normal(xr, f, side) * (th + 0.045))
        Loft(pts, lambda t: {"rx": 0.045, "ry": 0.05, "p": 4.0}, n=6, seg=0.18, frame="up", up=(1, 0, 0),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s_, a: wood_uv(6, s_ * 4.0, a), mat=mat)
    # two thwarts across the top
    for xt in (2.3, 3.6):
        a_, b_ = hull_point(xt, 0.97, -1), hull_point(xt, 0.97, 1)
        Loft([a_, b_], lambda t: {"rx": 0.11, "ry": 0.035, "p": 4.0}, n=6, seg=0.4, frame="up", up=(0, 0, 1),
             cap0="flat", cap1="flat").build(mb, uvmap=lambda s_, a: wood_uv(2, s_ * 3.0, a), mat=mat)


def hull_matrix():
    L, D = HULL["L"], HULL["D"]
    return (Matrix.Translation((0.45, 0.55, 1.05)) @ Matrix.Rotation(math.radians(14), 4, "Y")
            @ Matrix.Rotation(math.radians(-38), 4, "X") @ Matrix.Rotation(math.pi, 4, "Z")
            @ Matrix.Translation((-L * 0.5, 0, -D * 0.5)))


ARCH = {
    "ctrl": [(-1.55, -1.45, 0.0), (-1.50, -1.38, 0.55), (-1.30, -1.15, 1.70), (-0.95, -0.80, 2.85),
             (-0.30, -0.25, 3.70), (0.45, 0.30, 3.98), (1.12, 0.82, 3.55), (1.52, 1.22, 2.80),
             (1.62, 1.42, 2.05)],
    "curl": (1.7, 0.55, 0.16),
    "radius": [(0.0, 0.80), (0.02, 0.70), (0.06, 0.64), (0.3, 0.58), (0.55, 0.50), (0.75, 0.38),
               (0.88, 0.25), (0.96, 0.12), (1.0, 0.035)],
}


def wood_textures(name, base, seed, **kw):
    params = dict(size=1024, rows=WOOD_ROWS, tile_m=WOOD_TILE, base=base, seed=seed, grain=0.7, groove=0.7,
                  wear=0.06, dirt=0.35, knots=1, joints=1, nails=True)
    params.update(kw)
    out = lib.paint_named("tex_wood.py", params, {"color": f"{name}.jpg", "normal": f"{name}-n.jpg"})
    return out["color"], out["normal"]


def build_arch():
    lib.reset()
    spec = ARCH
    d = Vector(spec["ctrl"][-1]) - Vector(spec["ctrl"][0])
    d.z = 0
    d.normalize()
    up = Vector((d.y, -d.x, 0))          # the arch's plane normal, toward the viewer
    ten = Tentacle(spec["ctrl"], spec["curl"], spec["radius"], axis=-up, up=up, port=(0.03, 0.70), seed=7)
    bright = [[0.0, 1.12], [0.06, 1.22], [0.3, 1.1], [0.55, 1.0], [0.8, 0.9], [1.0, 0.82]]
    tex = lib.paint_named("tex_kraken.py", dict(PAINT, size=TEX, seed=17, parts=[ten.tex_part([0, 0, TEX, TEX], bright)]),
                    {"tex": "kraken-arch.jpg"})["tex"]
    glow, suck, port = materials(tex, sucker_texture())
    wc, wn = wood_textures("kraken-hull", ["#4a3f36", "#3e352e", "#56483c", "#463a30"], 41, dirt=0.45)
    wood = lib.material("hull_wood", base_tex=wc, normal_tex=wn, roughness=0.85, specular=0.25)
    root = lib.empty("wreck")
    hm = MB()
    build_hull(hm, 0)
    hm.transform(hull_matrix())
    zs = [v[2] for v in hm.verts]
    hull = hm.object("hull", [wood], origin=(0, 0, 0), auto_smooth=50)
    lib.set_parent(hull, root)
    mb = MB(along=True)
    ten.build(mb, uvmap=lambda s_, a: (s_, 1.0 - a), sucker_uv=lambda u, v: (u, v))
    tobj = mb.object("tentacle", [glow, suck, port], origin=spec["ctrl"][0])
    lib.set_parent(tobj, root)
    print(f"  arch: hull {lib.tri_count(hull)} tris (z {min(zs):.2f}..{max(zs):.2f}), tentacle {lib.tri_count(tobj)} tris, "
          f"{len(ten.suckers)} suckers, spine {ten.L:.2f} m")
    return lib.export("kraken-arch")


# --------------------------------------------------------------------------------------------
# The inflatable pumpkin
# --------------------------------------------------------------------------------------------

PUMPKIN = {"rx": 1.62, "rz": 1.22, "ribs": 10}


def build_pumpkin():
    lib.reset()
    rx, rz, ribs = PUMPKIN["rx"], PUMPKIN["rz"], PUMPKIN["ribs"]
    pv = 768

    def pumpkin_uv(u, v):
        return (u, 1.0 - (1.0 - v) * pv / TEX)
    # stem: rises out of the dimple, then curls over sideways like a hook
    top_z = 2 * rz - 0.30 * rz * 1.6 * 0.5
    base = Vector((0.0, 0.05, 2 * rz - 0.32))
    ctrl = [base, base + Vector((0.02, 0.0, 0.32)), base + Vector((0.10, 0.02, 0.58))]
    head = (ctrl[-1] - ctrl[-2]).normalized()
    cp = lib.curl(ctrl[-1], head, Vector((0, 1, 0)), 0.85, 0.30, 0.16, step=0.02)
    ctrl += cp[9::10]

    def sec(t):
        r = lerp_keys([(0, 0.24), (0.12, 0.19), (0.5, 0.17), (0.9, 0.15), (1, 0.14)], t)
        return {"rx": r, "ry": r}
    stem = Loft(ctrl, sec, n=20, seg=0.05, frame="rmf", up=(0, -1, 0), cap0="open", cap1="dome", cap1_len=0.08,
                offset=lambda t, a, s_: 0.012 * math.cos(math.tau * 5 * a))
    parts = [
        {"kind": "pumpkin", "rect": [0, 0, TEX, pv], "ribs": ribs, "r": [rx, rz], "rings": [0.16, 0.86],
         "vent": [0.70, 0.56, 0.06], "bright": [[0, 0.62], [0.16, 0.9], [0.45, 1.06], [0.75, 1.02], [1, 0.85]],
         "pad": 0, "seed": 5},
        {"kind": "stem", "rect": [0, pv, TEX, TEX - pv], "dims": stem.nominal, "pad": 0},
    ]
    tex = lib.paint_named("tex_kraken.py", dict(PAINT, size=TEX, seed=23, parts=parts), {"tex": "inflatable-pumpkin.jpg"})["tex"]
    glow = lib.material("glow_inflatable", base_tex=tex, emission_tex=tex, roughness=0.62, specular=0.3)
    mb = MB()
    lib.pumpkin(mb, (0, 0, rz), rx, rz, ribs=ribs, groove=0.14, groove_sharp=0.5, top_dimple=0.30,
                bottom_dimple=0.06, nu=ribs * 8, nv=34, uvmap=pumpkin_uv, mat=0, wobble=0.03, seed=4,
                rib_phase=0.0)
    mb.clamp_z(0.0)
    stem.build(mb, uvmap=lambda s_, a: (s_, 1.0 - (pv + a * (TEX - pv)) / TEX), mat=0)
    obj = mb.object("pumpkin", [glow], origin=(0, 0, 0))
    hi = max(v[2] for v in mb.verts)
    print(f"  inflatable-pumpkin: {lib.tri_count(obj)} tris, height {hi:.2f} m")
    return lib.export("inflatable-pumpkin")


def main():
    for key in ("a", "b", "c"):
        if ONLY is None or key in ONLY:
            build_tentacle(key)
    if ONLY is None or "arch" in ONLY:
        build_arch()
    if ONLY is None or "pumpkin" in ONLY:
        build_pumpkin()


if __name__ == "__main__":
    main()
