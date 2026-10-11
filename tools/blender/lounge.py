# SPDX-License-Identifier: MIT
"""The lantern lounge (reference/lantern-lounge-1.jpg, -2.jpg) and the lantern garden's props.

    blender -b --factory-startup -P tools/blender/lounge.py

Writes public/models/pallet-sofa.glb, pallet.glb, hay-bale.glb, reed-fence.glb,
shepherd-hook.glb and red-lantern.glb.

pallet-sofa    two pallets as a base, two hay bales as the seat, an upright pallet as the back,
               a dragon-and-cloud throw draped over the left half (cloth-simulated), two red
               cushions. 2.4 x 1.0 m, back 1.0 m high, seat 0.5 m.
pallet         a plain 1.2 x 1.0 x 0.144 m pallet.
hay-bale       a small square bale, 0.92 x 0.46 x 0.36 m, with two twines.
reed-fence     a 4 m x 1.9 m panel of split reeds (alpha-tested), repeatable end to end along X;
               `fairy_lights` holds two strands (`strand_0`, `strand_1`), each a row of empties
               `bulb_<strand>_<nnn>` in order along the wire, in front of the reeds.
shepherd-hook  a black metal hook, 2.2 m; empty `hang_point` where a lantern's ring sits.
red-lantern    a round red lantern (0.35 m) that hangs from its origin (the top of its ring; the
               lantern is below y = 0): `glow_lantern` lights the red skin and the slits, a gold
               cap, and the child `tassel` (pivot at the bottom cap) to swing.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import lib  # noqa: E402
from lib import MB, Loft  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils import noise as mnoise  # noqa: E402

Z = Vector((0, 0, 1))
LANTERN_RIBS = 16
TEX = None
MATS = {}


def mats():
    MATS["wood"] = lib.material("wood", base_tex=TEX["wood"], roughness=0.85, specular=0.3)
    MATS["hay"] = lib.material("hay", base_tex=TEX["hay"], normal_tex=TEX["hay_n"], normal_strength=1.0,
                               roughness=0.9, specular=0.3)
    MATS["throw"] = lib.material("throw", base_tex=TEX["throw"], roughness=0.9, specular=0.3, double_sided=True)
    MATS["cushion"] = lib.material("cushion", color="#a8121c", roughness=0.8, specular=0.3)
    return MATS


# --------------------------------------------------------------------------------------------
# Pallets and bales
# --------------------------------------------------------------------------------------------

def wood_uv(row, length, u0=0.0):
    """beam() uv: grain along the beam's local x; `row` picks one of the 8 boards in the texture."""
    v_lo, v_hi = 1 - (row + 1) / 8, 1 - row / 8

    def m(ax, fx, fy):
        if ax == 0:
            u, w = u0 + 0.01, fy
        else:
            u, w = u0 + (fx + length / 2) / 1.2 * 0.98, fy
        vv = v_lo + (0.5 + w / 0.11) * (v_hi - v_lo)
        return (u, min(max(vv, v_lo + 0.003), v_hi - 0.003))
    return m


def pallet(mb, center, M=None, seed=0, size=(1.2, 1.0), mat=0):
    """A stringer pallet: three stringers along x, seven deck boards across on top, three below."""
    R = (M.to_3x3() if hasattr(M, "to_3x3") else M) if M is not None else Matrix.Identity(3)
    C = Vector(center)
    L, D = size
    rng = lib.seeded(seed)

    def put(p, sz, rot_z=0.0, row=None):
        row = rng.randrange(8) if row is None else row
        Mb = R @ Matrix.Rotation(rot_z, 3, "Z")
        lib.beam(mb, C + R @ Vector(p), sz, M=Mb, chamfer=0.003,
                 uv=wood_uv(row, sz[0], rng.uniform(0, max(0.0, 1.0 - sz[0] / 1.2))), mat=mat)
    for y in (-D / 2 + 0.03, 0.0, D / 2 - 0.03):
        put((0, y, 0.022 + 0.045), (L, 0.05, 0.09), 0.0, row=rng.randrange(8))
    n = max(5, int(round(L / 0.165)) + 1)
    for i in range(n):
        x = -L / 2 + 0.05 + i * (L - 0.1) / (n - 1)
        put((x + rng.uniform(-0.005, 0.005), 0, 0.122 + 0.011), (D, 0.1, 0.022), math.pi / 2 + rng.uniform(-0.01, 0.01))
    for x in (-L / 2 + 0.05, 0.0, L / 2 - 0.05):
        put((x, 0, 0.011), (D, 0.1, 0.022), math.pi / 2)


def bmesh_into(mb, bm, uv_fn, mat, M=None, offset=(0, 0, 0)):
    R = (M.to_3x3() if hasattr(M, "to_3x3") else M) if M is not None else Matrix.Identity(3)
    O = Vector(offset)
    base = len(mb.verts)
    bm.verts.index_update()
    for v in bm.verts:
        mb.v(O + R @ v.co)
    uvl = bm.loops.layers.uv.active
    for f in bm.faces:
        mb.f([base + v.index for v in f.verts], [tuple(l[uvl].uv) for l in f.loops], None, mat)


def bale(mb, center, M=None, seed=0, mat=0):
    L, D, H = 0.92, 0.46, 0.36
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(L, D, H), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.045, segments=2, affect="EDGES", profile=0.5,
                    clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for _ in range(4):
        e = [e for e in bm.edges if e.calc_length() > 0.11]
        if not e:
            break
        bmesh.ops.subdivide_edges(bm, edges=e, cuts=1)
        bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    uvl = bm.loops.layers.uv.new("UVMap")
    kx = 0.92 * 960 / 1024
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            x, y, z = lp.vert.co
            if ax == 0:
                lp[uvl].uv = (0.04 + (y / D + 0.5) * 0.4, 0.5 + z)
            elif ax == 1:
                lp[uvl].uv = ((x / L + 0.5) * kx, 0.5 + z * 0.9)
            else:
                lp[uvl].uv = ((x / L + 0.5) * kx, 0.05 + (y / D + 0.5) * 0.4)
    off = Vector((seed * 3.1, seed * 1.7, 0.3))
    for v in bm.verts:
        d = 0.012 * mnoise.noise(v.co * 7 + off) + 0.006 * mnoise.noise(v.co * 19 + off)
        v.co += v.normal * d
    R = (M.to_3x3() if hasattr(M, "to_3x3") else M) if M is not None else Matrix.Identity(3)
    C = Vector(center)
    bmesh_into(mb, bm, None, mat, R, C)
    bm.free()
    # two twines round the bale
    for tx in (-0.24, 0.26):
        pts = []
        for k in range(24):
            a = math.tau * k / 24
            cy, cz = math.cos(a), math.sin(a)
            # a rounded rectangle just outside the bale's section
            yy = math.copysign(abs(cy) ** 0.25, cy) * (D / 2 + 0.006)
            zz = math.copysign(abs(cz) ** 0.25, cz) * (H / 2 + 0.006)
            pts.append(C + R @ Vector((tx, yy, zz)))
        Loft(pts, lambda t: {"rx": 0.004, "ry": 0.004}, n=4, seg=0.05, closed=True, frame="rmf", up=R @ Vector((1, 0, 0))
             ).build(mb, uvmap=lambda s, a: (0.97, s), mat=mat)


def cushion(mb, center, M, size=0.5, thick=0.16, mat=0, seed=0):
    R = M.to_3x3() if hasattr(M, "to_3x3") else M
    C = Vector(center)
    n = 14
    for side in (1, -1):
        def fn(u, v, side=side):
            x, y = u * 2 - 1, v * 2 - 1
            pinch = 1 - 0.07 * (1 - y * y) * x * x - 0.07 * (1 - x * x) * y * y
            puff = (max(1 - x * x, 0) ** 0.55) * (max(1 - y * y, 0) ** 0.55)
            wob = 0.01 * mnoise.noise(Vector((x * 2, y * 2, seed + side)))
            p = Vector((x * size / 2 * pinch, y * size / 2 * pinch, side * (thick / 2 * puff + wob * puff)))
            return C + R @ p
        lib.grid_patch(mb, fn, n, n, mat=mat, outward=R @ Vector((0, 0, side)),
                       uvmap=lambda u, v: (u, v))


def build_pallet():
    lib.reset()
    m = mats()
    mb = MB()
    pallet(mb, (0, 0, 0), seed=3)
    o = mb.object("pallet", [m["wood"]], origin=(0, 0, 0), auto_smooth=35)
    print(f"  pallet: {lib.tri_count(o)} tris")
    lib.export("pallet")


def build_bale():
    lib.reset()
    m = mats()
    mb = MB()
    bale(mb, (0, 0, 0.18), seed=1)
    o = mb.object("hay-bale", [m["hay"]], origin=(0, 0, 0))
    print(f"  hay-bale: {lib.tri_count(o)} tris")
    lib.export("hay-bale")


# --------------------------------------------------------------------------------------------
# The sofa, with a cloth-simulated throw
# --------------------------------------------------------------------------------------------

def proxy_box(name, center, size):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    m = o.modifiers.new("collision", "COLLISION")
    o.collision.thickness_outer = 0.008
    o.collision.cloth_friction = 12.0
    return o


def drape_throw(x0, x1, y0, y1, z, nx, ny, proxies, frames=90):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=nx, y_subdivisions=ny, size=1.0,
                                    location=((x0 + x1) / 2, (y0 + y1) / 2, z))
    cl = bpy.context.object
    cl.scale = (x1 - x0, y1 - y0, 1)
    bpy.ops.object.transform_apply(scale=True)
    # a little initial ripple so the folds are not perfectly regular
    for v in cl.data.vertices:
        v.co.z += 0.02 * mnoise.noise(Vector((v.co.x * 3, v.co.y * 3, 0.5)))
    mod = cl.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    s.quality = 6
    s.mass = 0.35
    s.tension_stiffness = 12
    s.compression_stiffness = 12
    s.shear_stiffness = 6
    s.bending_stiffness = 0.15
    s.air_damping = 1.5
    mod.collision_settings.distance_min = 0.006
    mod.collision_settings.use_self_collision = False
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = frames
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    for f in range(1, frames + 1):
        scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = cl.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [v.co.copy() for v in me.vertices]
    uvs = {}
    uvl = me.uv_layers.active.data
    faces = []
    for p in me.polygons:
        faces.append((list(p.vertices), [tuple(uvl[li].uv) for li in p.loop_indices]))
    ev.to_mesh_clear()
    bpy.data.objects.remove(cl)
    for o in proxies:
        bpy.data.objects.remove(o)
    return pts, faces


def build_sofa():
    lib.reset()
    m = mats()
    mb = MB()
    # base: two pallets side by side
    pallet(mb, (-0.6, 0, 0), M=Matrix.Rotation(math.pi / 2, 3, "Z"), seed=11, size=(1.0, 1.2))
    pallet(mb, (0.6, 0, 0), M=Matrix.Rotation(math.pi / 2, 3, "Z"), seed=12, size=(1.0, 1.2))
    top = 0.144
    # back: an upright pallet (2.1 x 0.86) standing on the base
    # deck toward the front with its boards horizontal, leaning back 8 degrees
    R_back = Matrix.Rotation(math.radians(82), 3, "X") @ Matrix.Rotation(math.pi / 2, 3, "Z")
    pallet(mb, (0.0, 0.17, top + 0.43), M=R_back, seed=13, size=(0.86, 2.1))
    # seat: two bales
    hay = MB()
    bale(hay, (-0.48, -0.25, top + 0.18), M=Matrix.Rotation(0.02, 3, "Z"), seed=2)
    bale(hay, (0.47, -0.24, top + 0.18), M=Matrix.Rotation(-0.03, 3, "Z"), seed=3)
    # cushions leaning on the back
    cush = MB()
    lean = Matrix.Rotation(math.radians(-72), 3, "X")
    cushion(cush, (0.18, -0.03, top + 0.36 + 0.26), Matrix.Rotation(0.12, 3, "Z") @ lean, seed=1)
    cushion(cush, (0.78, -0.02, top + 0.36 + 0.25), Matrix.Rotation(-0.10, 3, "Z") @ lean @ Matrix.Rotation(0.15, 3, "Z"),
            seed=2)
    # the throw, dropped over the left part and simulated
    proxies = [
        proxy_box("p_base", (0, 0, top / 2), (2.4, 1.0, top)),
        proxy_box("p_bale", (-0.48, -0.25, top + 0.18), (0.92, 0.46, 0.36)),
        proxy_box("p_bale2", (0.47, -0.24, top + 0.18), (0.92, 0.46, 0.36)),
        proxy_box("p_back", (0.0, 0.17, top + 0.43), (2.1, 0.15, 0.86)),
        proxy_box("p_ground", (0, 0, -0.05), (8, 8, 0.1)),
    ]
    # tilt the back proxy like the pallet
    proxies[3].rotation_euler = (math.radians(-8), 0, 0)
    proxies[3].location = (0.0, 0.17 - 0.072, top + 0.43)
    pts, faces = drape_throw(-1.22, 0.30, -1.45, 0.75, 1.25, 42, 60, proxies)
    throw = MB()
    base = len(throw.verts)
    for p in pts:
        throw.v(p)
    for idx, uv in faces:
        throw.f([base + i for i in idx], uv, None, 0)
    throw.clamp_z(0.002)
    mb.extend(hay, mat_offset=1)
    mb.extend(throw, mat_offset=2)
    mb.extend(cush, mat_offset=3)
    o = mb.object("pallet-sofa", [m["wood"], m["hay"], m["throw"], m["cushion"]], origin=(0, 0, 0))
    print(f"  pallet-sofa: {lib.tri_count(o)} tris")
    lib.export("pallet-sofa")


# --------------------------------------------------------------------------------------------
# Reed fence, shepherd hook, red lantern
# --------------------------------------------------------------------------------------------

def build_fence():
    lib.reset()
    reed = lib.material("reed", base_tex=TEX["reed"], roughness=0.7, specular=0.3, alpha_clip=0.5, double_sided=True)
    mb = MB()
    W, H = 4.0, 1.9

    def fn(u, v):
        x = (u - 0.5) * W
        y = 0.025 * math.sin(x * 2.3 + 0.4) + 0.012 * math.sin(x * 5.1)
        return Vector((x, y, v * H))
    lib.grid_patch(mb, fn, 48, 2, mat=0, uvmap=lambda u, v: (u * W, v * 0.95 + 0.025 - 0.0),
                   outward=Vector((0, -1, 0)))
    o = mb.object("reed-fence", [reed], origin=(0, 0, 0))
    root = lib.empty("fairy_lights", (0, 0, 0))
    lib.set_parent(root, o)
    # two strands of fairy lights hung in swags along the front, as in the photo
    for k, (zt, sag, span, phase) in enumerate(((1.62, 0.32, 1.0, 0.0), (1.05, 0.25, 1.33, 0.4))):
        st = lib.empty(f"strand_{k}", (0, 0, 0))
        lib.set_parent(st, root)
        x = -W / 2
        i = 0
        while x <= W / 2 + 1e-6:
            f = ((x + W / 2) / span + phase) % 1.0
            z = zt - sag * 4 * f * (1 - f)
            y = -0.05 + 0.025 * math.sin(x * 2.3 + 0.4)
            e = lib.empty(f"bulb_{k}_{i:03d}", (x, y, z), size=0.02)
            lib.set_parent(e, st)
            x += 0.1
            i += 1
    print(f"  reed-fence: {lib.tri_count(o)} tris")
    lib.export("reed-fence")


def build_hook():
    lib.reset()
    metal = lib.material("metal_black", color="#121214", roughness=0.45, metallic=0.6)
    mb = MB()
    pts = [Vector(p) for p in ((0, 0, 0), (0, 0, 1.0), (0, 0, 2.02), (0.012, 0, 2.12), (0.06, 0, 2.185),
                                (0.115, 0, 2.17), (0.145, 0, 2.11), (0.15, 0, 2.06), (0.162, 0, 2.035))]
    hook = Loft(pts, lambda t: {"rx": 0.0065, "ry": 0.0065}, n=8, seg=0.05, frame="rmf", up=Vector((0, 1, 0)),
                cap0="flat", cap1="dome", cap1_len=0.006)
    hook.build(mb, mat=0)
    # the foot bar for pushing it into the ground
    Loft([Vector((-0.09, 0, 0.30)), Vector((-0.09, 0, 0.26)), Vector((0, 0, 0.24)), Vector((0.09, 0, 0.26)),
          Vector((0.09, 0, 0.30))], lambda t: {"rx": 0.006, "ry": 0.006}, n=6, seg=0.03, frame="rmf",
         up=Vector((0, 1, 0)), cap0="dome", cap1="dome").build(mb, mat=0)
    o = mb.object("shepherd-hook", [metal], origin=(0, 0, 0))
    hp = lib.empty("hang_point", (0.148, 0, 2.05), size=0.03)
    lib.set_parent(hp, o)
    print(f"  shepherd-hook: {lib.tri_count(o)} tris")
    lib.export("shepherd-hook")


def build_lantern():
    lib.reset()
    glow = lib.material("glow_lantern", base_tex=TEX["lantern"], emission_tex=TEX["lantern_e"], roughness=0.6,
                        specular=0.3)
    gold = lib.material("gold", color="#c99a3a", roughness=0.35, metallic=0.9)
    tas = lib.material("tassel", color="#d9a54a", roughness=0.65, specular=0.3)
    R, Hh = 0.175, 0.30
    top_z = -0.075            # the body's top, below the ring
    bot_z = top_z - Hh
    mb = MB()

    def sec(t):
        s = math.sin(math.pi * (0.10 + 0.80 * t))
        r = R * s ** 0.55
        return {"rx": r, "ry": r}

    def pleats(t, a, s):
        return 0.004 * abs(math.sin(a * math.pi * LANTERN_RIBS)) - 0.002
    body = Loft([(0, 0, bot_z), (0, 0, top_z)], sec, n=48, seg=0.025, frame="up", up=Vector((0, 1, 0)),
                cap0="flat", cap1="flat", offset=pleats)
    body.build(mb, uvmap=lambda s, a: (a, s), mat=0)
    # gold caps and the ring
    for z, r, h in ((top_z - 0.004, 0.068, 0.018), (bot_z - 0.012, 0.05, 0.016)):
        Loft([(0, 0, z), (0, 0, z + h)], lambda t, r=r: {"rx": r * (1 - 0.15 * t), "ry": r * (1 - 0.15 * t)}, n=20,
             seg=0.02, frame="up", up=Vector((0, 1, 0)), cap0="flat", cap1="flat").build(mb, mat=1)
    ring = [Vector((0.022 * math.sin(math.tau * k / 16), 0, -0.04 + 0.034 * math.cos(math.tau * k / 16)))
            for k in range(16)]
    Loft(ring, lambda t: {"rx": 0.003, "ry": 0.003}, n=5, seg=0.02, closed=True, frame="rmf", up=Vector((0, 1, 0))
         ).build(mb, mat=1)
    Loft([(0, 0, -0.072), (0, 0, top_z + 0.01)], lambda t: {"rx": 0.003, "ry": 0.003}, n=5, seg=0.02, frame="up",
         up=Vector((0, 1, 0)), cap0="flat", cap1="flat").build(mb, mat=1)
    root = mb.object("red-lantern", [glow, gold], origin=(0, 0, 0))
    # tassel: cord, knot, wrapped head, then a skirt of strands
    tmb = MB()
    t0 = bot_z - 0.012
    Loft([(0, 0, t0), (0, 0, t0 - 0.05)], lambda t: {"rx": 0.003, "ry": 0.003}, n=5, seg=0.03, frame="up",
         up=Vector((0, 1, 0)), cap0="flat", cap1="flat").build(tmb, mat=0)
    lib.lump(tmb, Vector((0, 0, t0 - 0.058)), 0.011, (1, 1, 0.9), seed=2, rough=0.1, nu=8, nv=5, mat=0,
             flat_bottom=False)
    L = 0.27
    keys = [(0, 0.008), (0.06, 0.013), (0.16, 0.013), (0.2, 0.011), (0.24, 0.013), (1.0, 0.019)]

    def strands(t, a, s):
        return 0.0025 * math.cos(a * math.tau * 12) * min(1.0, t * 4)
    Loft([(0, 0, t0 - 0.066), (0, 0, t0 - 0.066 - L)], lambda t: {"rx": lib.lerp_keys(keys, t), "ry": lib.lerp_keys(keys, t)},
         n=12, seg=0.02, frame="up", up=Vector((0, 1, 0)), cap0="dome", cap1="flat", cap0_len=0.008,
         offset=strands).build(tmb, mat=0)
    tassel = tmb.object("tassel", [tas], origin=(0, 0, t0))
    lib.set_parent(tassel, root)
    print(f"  red-lantern: {lib.tri_count(root)} + tassel {lib.tri_count(tassel)} tris")
    lib.export("red-lantern")


def main():
    global TEX
    lib.reset()
    TEX = lib.paint("tex_lounge.py", {"lantern_ribs": LANTERN_RIBS},
                    {"wood": "lounge-wood.jpg", "hay": "lounge-hay.jpg", "hay_n": "lounge-hay-n.jpg",
                     "throw": "lounge-throw.jpg", "reed": "lounge-reed.png", "lantern": "lounge-lantern.jpg",
                     "lantern_e": "lounge-lantern-e.jpg"})
    build_pallet()
    build_bale()
    build_sofa()
    build_fence()
    build_hook()
    build_lantern()


main()
