# SPDX-License-Identifier: MIT
"""Skeletons for the Kraken's Wreck and the treasure: two skeleton pirates in ragged clothes with
carved jack-o'-lantern heads (reference/kraken-1.jpg, kraken-2.jpg) and plain bleached
skeletons (reference/video-9604.mov).

    blender -b --factory-startup -P tools/blender/skeletons.py [-- only=sit,stand,skeleton,climb]

Writes public/models/skeleton-pirate-sit.glb, skeleton-pirate-stand.glb, skeleton.glb and
skeleton-climb.glb (all about 1.72 m tall standing).

Each skeleton is posed procedurally: joint positions from a few frames (pelvis, chest, head) and
two-bone IK for the limbs, every bone a small loft (knobbly long bones, ribs, vertebrae, a pelvis
ring, finger and toe bones), the skull a smooth union of ellipsoids with dented sockets and a
painted face, the jack-o'-lanterns ribbed pumpkins whose carved faces are separate glowing
patches following the skin.

Nodes: root `skeleton` (bones and clothes; origin on the ground) -> `head` (pivot at the top of the
neck: skull + jaw, or pumpkin + carving + hair/bandana); the seated pirate also has `oar`
(pivot at its upper hand). skeleton-pirate-sit sits on a seat 0.36 m high: its origin is on
the floor under the seat point (glTF (0, 0.36, 0)), feet forward (+Z); rowboat.glb marks where
it goes with `crew_0` / `crew_1`. skeleton-climb faces a
trunk (radius 0.2 m) whose axis is the vertical line through its origin; it faces -Z in glTF
(into the trunk) and its lowest foot is at y = 0: lift it to any height.

Materials: `bone`, `pirate_cloth` (atlas, double-sided), `pumpkin_skin`, `glow_carving`.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Euler, Matrix, Vector, geometry  # noqa: E402

ARGS = dict(a.split("=", 1) for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
ONLY = set(ARGS["only"].split(",")) if "only" in ARGS else None

V = Vector
L_UP, L_FORE, L_HAND = 0.30, 0.26, 0.18
L_THIGH, L_SHIN = 0.44, 0.42

# rest landmarks in the pelvis frame (pelvis centre at the origin, facing -Y)
HIP = {"R": V((0.085, 0.0, -0.04)), "L": V((-0.085, 0.0, -0.04))}
WAIST = V((0, 0.03, 0.12))            # the upper body bends about here
SHOULDER = {"R": V((0.172, 0.035, 0.465)), "L": V((-0.172, 0.035, 0.465))}
NECK_TOP = V((0, 0.02, 0.60))         # the head turns about here
SKULL_C = V((0, 0.0, 0.672))


def rot(deg):
    return Euler([math.radians(a) for a in deg], "XYZ").to_matrix().to_4x4()


def two_bone(S, W, l1, l2, pole):
    d = W - S
    D = min(max(d.length, 1e-4), (l1 + l2) * 0.999)
    dn = d.normalized()
    W = S + dn * D
    a = (l1 * l1 - l2 * l2 + D * D) / (2 * D)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = V(pole) - dn * dn.dot(V(pole))
    p = p.normalized() if p.length > 1e-6 else V((0, 0, 1))
    return S + dn * a + p * h, W


# --------------------------------------------------------------------------------------------
# Texture regions
# --------------------------------------------------------------------------------------------

def uv_bone(s, a):
    return ((s * 3.0) % 1.0 * 0.98 + 0.01, 0.135 + 0.35 * a)


def uv_skull(u, v):
    return (u, 0.5 + 0.5 * v)


def uv_teeth(s, a):
    fv = 0.25 + 0.5 * abs(a - 0.5) * 2
    return (s * 1.2, 0.125 * (1 - fv))


def cloth_tile(col, row):
    def m(t, a):
        return ((col * 512 + (a % 1.0) * 512) / 1024, 1 - (row * 256 + min(max(t, 0), 1) * 255) / 1024)
    return m


TILES = {"shirt": (0, 0), "vest": (1, 0), "sleeve": (0, 1), "sash": (1, 1), "breeches": (0, 2), "hair": (1, 2),
         "bandana": (0, 3), "canvas": (1, 3)}


def uv_pumpkin(u, v):
    return (u, 0.25 + 0.75 * v)


def uv_stem(s, a):
    return (a, 0.25 * (1 - s))


# --------------------------------------------------------------------------------------------
# Bones
# --------------------------------------------------------------------------------------------

def long_bone(mb, A, B, r, k0=0.9, k1=0.9, n=6, mat=0, offset=None):
    def sec(t):
        rr = r * (1 + k0 * math.exp(-(t / 0.08) ** 2) + k1 * math.exp(-((1 - t) / 0.08) ** 2))
        return {"rx": rr, "ry": rr * 0.92}
    d = (B - A)
    up = V((0, 0, 1)) if abs(d.normalized().z) < 0.9 else V((1, 0, 0))
    Loft([A, A.lerp(B, 0.5), B], sec, n=n, seg=max(d.length / 7, 0.012), frame="up", up=up,
         cap0="dome", cap1="dome", cap0_len=r * 1.2, cap1_len=r * 1.2, cap_rings=2).build(mb, uvmap=uv_bone, mat=mat)


def chain(mb, pts, r0, r1, n=4, mat=0, up=(0, 0, 1)):
    if len(pts) < 2:
        return
    Loft(pts, lambda t: {"rx": r0 + (r1 - r0) * t, "ry": (r0 + (r1 - r0) * t) * 0.9}, n=n, seg=0.028,
         frame="up", up=up, cap0="dome", cap1="dome", cap0_len=r0, cap1_len=r1, cap_rings=1).build(mb, uvmap=uv_bone, mat=mat)


def lumpy(mb, c, size, M=None, mat=0, seed=0):
    lib.lump(mb, c, 1.0, scale=size, seed=seed, rough=0.12, nu=8, nv=5, M=M, uvmap=lambda u, v: uv_bone(u, v),
             mat=mat, flat_bottom=False)


def hand(mb, W, h, palm, curl, thumb_side, mat=0, scale=1.0):
    h = h.normalized()
    pn = (palm - h * h.dot(palm)).normalized()
    s = h.cross(pn).normalized()
    lumpy(mb, W + h * 0.022 * scale, (0.024 * scale, 0.02 * scale, 0.012 * scale),
          M=Matrix((s, h, pn)).transposed(), mat=mat, seed=3)
    offs = [0.027, 0.009, -0.009, -0.026]
    lens = [0.95, 1.05, 1.0, 0.80]
    for i, (o, ln) in enumerate(zip(offs, lens)):
        o *= thumb_side * scale
        base = W + h * 0.03 * scale + s * o * 0.6
        K = W + h * 0.095 * scale + s * o
        chain(mb, [base, K], 0.0045 * scale, 0.005 * scale, mat=mat)
        pts = [K]
        d = h.copy()
        for seg, ang in zip((0.042, 0.027, 0.02), (0.6, 0.9, 0.7)):
            a = math.radians(curl * 75 * ang + 4)
            axis = d.cross(pn)
            d = (d * math.cos(a) + axis.cross(d) * math.sin(a)).normalized() if axis.length > 1e-6 else d
            pts.append(pts[-1] + d * seg * ln * scale)
        chain(mb, pts, 0.0052 * scale, 0.0038 * scale, mat=mat)
    # thumb
    tb = W + h * 0.02 * scale + s * 0.03 * thumb_side * scale
    d = (h * 0.75 + s * 0.55 * thumb_side + pn * 0.35).normalized()
    pts = [tb]
    for seg in (0.040, 0.032, 0.025):
        pts.append(pts[-1] + d * seg * scale)
        a = math.radians(curl * 40)
        axis = d.cross(pn)
        if axis.length > 1e-6:
            d = (d * math.cos(a) + axis.normalized().cross(d) * math.sin(a)).normalized()
    chain(mb, pts, 0.006 * scale, 0.0042 * scale, mat=mat)


def foot(mb, A, f, mat=0, up=V((0, 0, 1))):
    f = (f - up * up.dot(f)).normalized()
    s = f.cross(up).normalized()
    lumpy(mb, A - f * 0.035 - up * 0.035, (0.026, 0.05, 0.03), M=Matrix((s, f, up)).transposed(), mat=mat, seed=5)
    lumpy(mb, A + f * 0.025 - up * 0.045, (0.034, 0.045, 0.022), M=Matrix((s, f, up)).transposed(), mat=mat, seed=6)
    for i, o in enumerate((-0.03, -0.015, 0.0, 0.015, 0.03)):
        ln = 1.0 - 0.06 * abs(i - 1)
        p0 = A + f * 0.045 - up * 0.05 + s * o * 0.5
        p1 = A + f * (0.13 * ln) - up * 0.065 + s * o
        p2 = A + f * (0.17 * ln) - up * 0.068 + s * o * 1.05
        p3 = A + f * (0.195 * ln) - up * 0.07 + s * o * 1.08
        chain(mb, [p0, p1], 0.0065, 0.006, mat=mat)
        chain(mb, [p1, p2, p3], 0.0062, 0.0045, mat=mat)


def ribcage(mb, Mc, mat=0):
    for k in range(10):
        f = k / 9
        z = 0.445 - 0.235 * f
        W = 0.075 + 0.075 * math.sin(math.pi * min(f * 1.25 + 0.12, 1.0)) ** 0.7
        Dp = 0.085 + 0.012 * f
        end = math.pi if k < 7 else (0.80 * math.pi if k < 9 else 0.6 * math.pi)
        for side in (-1, 1):
            pts = []
            m = 12
            for i in range(m + 1):
                ph = 0.12 + (end - 0.12) * i / m
                x = side * W * math.sin(ph)
                y = -0.025 + Dp * math.cos(ph) + 0.01
                zz = z - 0.065 * (1 - math.cos(ph)) / 2 - 0.02 * math.sin(ph)
                pts.append(Mc @ V((x, y, zz)))
            if k < 7:
                pts.append(Mc @ V((side * 0.018, -0.112, 0.43 - 0.024 * k)))
            Loft(pts, lambda t: {"rx": 0.0042, "ry": 0.0075}, n=4, seg=0.045, frame="up", up=Mc.to_3x3() @ V((0, 0, 1)),
                 cap0="flat", cap1="flat").build(mb, uvmap=uv_bone, mat=mat)
    # sternum, clavicles, shoulder blades
    Loft([Mc @ V((0, -0.112, 0.45)), Mc @ V((0, -0.116, 0.36)), Mc @ V((0, -0.110, 0.27))],
         lambda t: {"rx": 0.016 * (1 - 0.4 * t), "ry": 0.006}, n=6, seg=0.03, frame="up",
         up=Mc.to_3x3() @ V((0, -1, 0)), cap0="dome", cap1="point", cap0_len=0.01, cap1_len=0.02).build(mb, uvmap=uv_bone, mat=mat)
    for side in (-1, 1):
        chain(mb, [Mc @ V((side * 0.02, -0.105, 0.462)), Mc @ V((side * 0.08, -0.09, 0.475)),
                   Mc @ V((side * 0.15, -0.02, 0.48))], 0.0065, 0.0075, n=5, mat=mat)
        a, b, c = Mc @ V((side * 0.055, 0.105, 0.44)), Mc @ V((side * 0.16, 0.07, 0.46)), Mc @ V((side * 0.085, 0.11, 0.30))
        nrm = (b - a).cross(c - a).normalized()
        if nrm.dot(Mc.to_3x3() @ V((0, 1, 0))) < 0:
            b, c = c, b
        for off, flip in ((0.0, False), (-0.008, True)):
            o = (b - a).cross(c - a).normalized() * off
            ids = [mb.v(p + o) for p in (a, b, c)]
            uv = [uv_bone(0.1, 0.2), uv_bone(0.3, 0.2), uv_bone(0.2, 0.8)]
            mb.f(ids[::-1] if flip else ids, uv[::-1] if flip else uv, None, mat)


def spine(mb, pts, mat=0):
    def sec(t):
        r = lerp_keys([(0, 0.018), (0.3, 0.017), (0.6, 0.013), (0.85, 0.011), (1, 0.010)], t)
        return {"rx": r, "ry": r}
    lo = Loft(pts, sec, n=6, seg=0.0105, frame="up", up=V((0, -1, 0.001)), cap0="dome", cap1="dome",
              cap0_len=0.012, cap1_len=0.01, cap_rings=2,
              offset=lambda t, a, s: 0.005 * math.cos(math.tau * 21 * t) - 0.002)
    lo.build(mb, uvmap=uv_bone, mat=mat)


def pelvis(mb, Mp, mat=0):
    pts = []
    m = 28
    for i in range(m):
        ph = math.tau * i / m          # 0 = front (-Y)
        x = 0.125 * math.sin(ph) * (1 + 0.12 * math.cos(ph))
        y = -0.075 * math.cos(ph) + 0.01
        z = -0.035 * (0.5 + 0.5 * math.cos(ph)) ** 2 + 0.02
        pts.append(Mp @ V((x, y, z)))

    def sec(t):
        ph = math.tau * t
        side = abs(math.sin(ph))
        back = max(0.0, -math.cos(ph))
        h = 0.018 + 0.05 * side ** 1.5 + 0.012 * back
        return {"rx": 0.009, "ry": h, "oy": h * 0.45}
    Loft(pts, sec, n=6, seg=0.03, closed=True, frame="up", up=Mp.to_3x3() @ V((0, 0, 1))).build(mb, uvmap=uv_bone, mat=mat)
    R = Mp.to_3x3()
    lumpy(mb, Mp @ V((0, 0.07, -0.005)), (0.04, 0.025, 0.06), M=R, mat=mat, seed=8)
    for side in (-1, 1):
        lumpy(mb, Mp @ (HIP["R"] * side if side > 0 else HIP["L"]), (0.026, 0.026, 0.026), M=R, mat=mat, seed=9)
        lumpy(mb, Mp @ V((side * 0.07, -0.04, -0.065)), (0.03, 0.02, 0.022), M=R, mat=mat, seed=10)


# skull: a smooth union of ellipsoids around SKULL_C (head frame), u = 0.75 faces forward
SKULL_BLOBS = [
    (V((0, 0.012, 0.022)), V((0.071, 0.092, 0.078))),     # cranium
    (V((0, -0.046, -0.042)), V((0.050, 0.050, 0.046))),    # face / upper jaw
    (V((0.050, -0.052, -0.018)), V((0.024, 0.025, 0.017))),  # cheekbones
    (V((-0.050, -0.052, -0.018)), V((0.024, 0.025, 0.017))),
]


def skull_radius(d, k=0.012):
    hits = []
    for c, r in SKULL_BLOBS:
        q = V((-c.x / r.x, -c.y / r.y, -c.z / r.z))
        e = V((d.x / r.x, d.y / r.y, d.z / r.z))
        A, B, C = e.dot(e), q.dot(e), q.dot(q) - 1
        disc = B * B - A * C
        if disc > 0:
            t = (-B + math.sqrt(disc)) / A
            if t > 0:
                hits.append(t)
    if not hits:
        return 0.05
    m = max(hits)
    return m + k * math.log(sum(math.exp((h - m) / k) for h in hits))


def skull(mb, mat=0):
    nu, nv = 26, 16

    def pt(u, v):
        th, ph = math.tau * u, math.pi * v
        d = V((math.cos(th) * math.sin(ph), math.sin(th) * math.sin(ph), -math.cos(ph)))
        r = skull_radius(d)
        du = ((u - 0.75 + 0.5) % 1) - 0.5
        for ex in (-0.075, 0.075):
            r -= 0.016 * math.exp(-(((du - ex) / 0.045) ** 2 + ((v - 0.50) / 0.07) ** 2))
        r -= 0.010 * math.exp(-((du / 0.025) ** 2 + ((v - 0.37) / 0.05) ** 2))
        if v < 0.2:
            r *= 0.85 + 0.75 * v
        return SKULL_C + d * r
    lib.grid_patch(mb, pt, nu, nv, uvmap=uv_skull, mat=mat, closed_u=True, outward=lambda u, v: pt(u, v) - SKULL_C)
    # the jaw
    c = SKULL_C
    pts = [c + V((-0.047, 0.012, -0.03)), c + V((-0.046, -0.005, -0.075)), c + V((-0.036, -0.05, -0.098)),
           c + V((0, -0.078, -0.102)), c + V((0.036, -0.05, -0.098)), c + V((0.046, -0.005, -0.075)),
           c + V((0.047, 0.012, -0.03))]
    Loft(pts, lambda t: {"rx": 0.0065, "ry": 0.016}, n=6, seg=0.012, frame="rmf", up=V((0, 0, 1)),
         cap0="dome", cap1="dome", cap0_len=0.008, cap1_len=0.008, cap_rings=1).build(mb, uvmap=uv_teeth, mat=mat)


# --------------------------------------------------------------------------------------------
# Poses
# --------------------------------------------------------------------------------------------

POSES = {
    "stand": {   # relaxed, weight on one leg
        "pelvis": ((0, 0, 0.965), (0, 2, 4)),
        "chest": (-3, -2, -6), "head": (6, 3, 12),
        "arm_R": {"wrist": (0.24, -0.08, -0.06), "pole": (0.3, 1, 0), "hand": (0.1, -0.3, -1), "palm": (-1, 0, 0), "curl": 0.4},
        "arm_L": {"wrist": (-0.23, -0.04, -0.08), "pole": (-0.3, 1, 0), "hand": (-0.05, -0.2, -1), "palm": (1, 0, 0), "curl": 0.3},
        "leg_R": {"ankle": (0.12, 0.02, -0.89), "pole": (0.05, -1, 0), "foot": (0.18, -1, 0)},
        "leg_L": {"ankle": (-0.11, -0.06, -0.875), "pole": (-0.05, -1, 0), "foot": (-0.2, -1, 0)},
    },
    "pirate_stand": {   # one hand up and open (a hail), the other on the hip
        "pelvis": ((0, 0, 0.965), (0, -3, -6)),
        "chest": (-4, 3, 8), "head": (-8, -6, -14),
        "arm_R": {"wrist": (0.40, -0.26, 0.50), "pole": (0.4, 0.4, -1), "hand": (0.35, -0.3, 1), "palm": (0, -1, 0.2), "curl": 0.12},
        "arm_L": {"wrist": (-0.15, -0.05, 0.07), "pole": (-1, 0.5, 0), "hand": (0.6, -0.1, -0.6), "palm": (0.3, 0.4, 1), "curl": 0.55},
        "leg_R": {"ankle": (0.17, -0.06, -0.885), "pole": (0.2, -1, 0), "foot": (0.3, -1, 0)},
        "leg_L": {"ankle": (-0.10, 0.04, -0.895), "pole": (-0.05, -1, 0), "foot": (-0.15, -1, 0)},
    },
    "pirate_sit": {   # on a seat 0.36 m high, both hands on an oar held across the body
        "pelvis": ((0, 0, 0.465), (-6, 0, 0)),
        "chest": (10, 0, -4), "head": (-4, 5, 10),
        "oar": {"top": (-0.16, -0.28, 0.50), "dir": (0.85, -0.12, -0.48), "len": 2.0, "hands": (0.15, 0.50)},
        "arm_L": {"pole": (-1, 0.4, -0.6), "hand": (0.2, -1, -0.2), "palm": (0.6, 0, 0.8), "curl": 0.85},
        "arm_R": {"pole": (1, 0.4, -0.5), "hand": (-0.1, -1, 0.1), "palm": (-0.6, 0, -0.8), "curl": 0.85},
        "leg_R": {"ankle": (0.15, -0.46, -0.395), "pole": (0.1, -1, 0.6), "foot": (0.1, -1, 0)},
        "leg_L": {"ankle": (-0.13, -0.40, -0.395), "pole": (-0.1, -1, 0.6), "foot": (-0.1, -1, 0)},
    },
    "climb": {   # hugging a trunk of radius 0.2 at the origin, facing it (+Y)
        "pelvis": ((0.0, -0.33, 0.93), (8, 0, 180)),
        "chest": (12, 4, 6), "head": (-25, 0, -15),
        "arm_R": {"wrist_w": (-0.17, -0.10, 1.62), "pole_w": (-0.6, -0.6, -0.4), "hand_w": (0.2, 0.9, 0.3), "palm_w": (0.9, 0.3, 0), "curl": 0.8},
        "arm_L": {"wrist_w": (0.16, -0.11, 1.86), "pole_w": (0.7, -0.6, -0.2), "hand_w": (-0.2, 0.8, 0.5), "palm_w": (-0.9, 0.3, 0), "curl": 0.8},
        "leg_R": {"ankle_w": (-0.17, -0.20, 0.47), "pole_w": (-0.3, -1, 0.3), "foot_w": (-0.1, 1, 0.4)},
        "leg_L": {"ankle_w": (0.14, -0.30, 0.07), "pole_w": (0.2, -1, 0.1), "foot_w": (0.1, 1, -0.3)},
    },
}


class Rig:
    def __init__(self, pose):
        P = POSES[pose]
        loc, prot = P["pelvis"]
        self.Mp = Matrix.Translation(loc) @ rot(prot)
        self.Mc = self.Mp @ Matrix.Translation(WAIST) @ rot(P["chest"]) @ Matrix.Translation(-WAIST)
        self.Mh = self.Mc @ Matrix.Translation(NECK_TOP) @ rot(P["head"]) @ Matrix.Translation(-NECK_TOP)
        Rc, Rp = self.Mc.to_3x3(), self.Mp.to_3x3()
        self.arms, self.legs = {}, {}
        self.oar = None
        if "oar" in P:
            o = P["oar"]
            top = self.Mc @ V(o["top"])
            d = (Rc @ V(o["dir"])).normalized()
            self.oar = (top, d, o["len"])
            grips = {"L": top + d * o["hands"][0], "R": top + d * o["hands"][1]}
        for side in ("R", "L"):
            a = P["arm_" + side]
            S = self.Mc @ SHOULDER[side]
            if "wrist_w" in a:
                Wt, pole, hd, pm = V(a["wrist_w"]), V(a["pole_w"]), V(a["hand_w"]), V(a["palm_w"])
            elif "wrist" in a:     # chest-frame target
                Wt = self.Mc @ V(a["wrist"])
                pole, hd, pm = Rc @ V(a["pole"]), Rc @ V(a["hand"]), Rc @ V(a["palm"])
            else:
                hd, pm = Rc @ V(a["hand"]), Rc @ V(a["palm"])
                Wt = grips[side] - hd.normalized() * 0.07 - (pm.normalized()) * 0.025
                pole = Rc @ V(a["pole"])
            E, W = two_bone(S, Wt, L_UP, L_FORE, pole)
            self.arms[side] = {"S": S, "E": E, "W": W, "hand": hd.normalized(), "palm": pm.normalized(),
                               "curl": a["curl"], "thumb": 1 if side == "R" else -1}
        for side in ("R", "L"):
            lg = P["leg_" + side]
            H = self.Mp @ HIP[side]
            if "ankle_w" in lg:
                At, pole, fd = V(lg["ankle_w"]), V(lg["pole_w"]), V(lg["foot_w"])
            else:                  # relative to the pelvis position, world axes (feet stay planted)
                At = V(loc) + V(lg["ankle"])
                pole, fd = V(lg["pole"]), V(lg["foot"])
            K, A = two_bone(H, At, L_THIGH, L_SHIN, pole)
            self.legs[side] = {"H": H, "K": K, "A": A, "foot": fd.normalized()}

    def spine_pts(self):
        Mp, Mc, Mh = self.Mp, self.Mc, self.Mh
        return [Mp @ V((0, 0.055, -0.02)), Mp @ V((0, 0.035, 0.07)), Mc @ V((0, 0.045, 0.20)), Mc @ V((0, 0.07, 0.33)),
                Mc @ V((0, 0.055, 0.45)), Mc @ V((0, 0.03, 0.53)), Mh @ V((0, 0.02, 0.60))]


def build_bones(mb, rig, mat=0, dressed=None):
    """dressed: None (all bones), "vest" (ribs show at the open front; spine and pelvis are
    hidden), "shirt" (only the neck shows)."""
    if dressed is None:
        spine(mb, rig.spine_pts(), mat)
        pelvis(mb, rig.Mp, mat)
    else:
        spine(mb, rig.spine_pts()[4:], mat)
    if dressed in (None, "vest"):
        ribcage(mb, rig.Mc, mat)
    for side, a in rig.arms.items():
        S, E, W = a["S"], a["E"], a["W"]
        long_bone(mb, S, E, 0.0105, k0=1.1, k1=0.8, mat=mat)
        lat = (E - S).cross(W - E)
        lat = lat.normalized() * 0.009 if lat.length > 1e-6 else V((0.009, 0, 0))
        long_bone(mb, E + lat, W + lat * 1.3, 0.0068, k0=0.9, k1=0.6, n=5, mat=mat)
        long_bone(mb, E - lat, W - lat * 0.7, 0.0062, k0=0.7, k1=0.9, n=5, mat=mat)
        hand(mb, W, a["hand"], a["palm"], a["curl"], a["thumb"], mat=mat)
    for side, lg in rig.legs.items():
        H, K, A = lg["H"], lg["K"], lg["A"]
        long_bone(mb, H, K, 0.0145, k0=1.0, k1=1.1, mat=mat)
        lat = (K - H).cross(V((0, 0, 1)))
        lat = lat.normalized() * 0.018 if lat.length > 1e-6 else V((0.018, 0, 0))
        long_bone(mb, K, A, 0.013, k0=1.1, k1=0.7, mat=mat)
        long_bone(mb, K + lat * (1 if side == "R" else -1) * 0.8, A + lat * (1 if side == "R" else -1) * 0.5, 0.0055,
                  k0=0.8, k1=0.8, n=5, mat=mat)
        lumpy(mb, K + lg["foot"] * 0.022, (0.02, 0.012, 0.022), mat=mat, seed=12)   # kneecap
        foot(mb, A, lg["foot"], mat=mat)


# --------------------------------------------------------------------------------------------
# Jack-o'-lantern heads
# --------------------------------------------------------------------------------------------

def pumpkin_head(mb, mats, face, rx=0.165, rz=0.135, ribs=8, seed=1):
    C = SKULL_C + V((0, -0.01, 0.01))
    kw = dict(ribs=ribs, groove=0.10, groove_sharp=0.4, top_dimple=0.25, bottom_dimple=0.2, wobble=0.04, seed=seed)
    lib.pumpkin(mb, C, rx, rz, nu=ribs * 5, nv=14, uvmap=uv_pumpkin, mat=mats["skin"], **kw)
    point = lib.pumpkin_surface(C, rx, rz, **kw)
    top = point(0, 1.0)
    st = [top - V((0, 0, 0.03)), top + V((0.004, 0.0, 0.035)), top + V((0.02, 0.01, 0.07))]
    Loft(st, lambda t: {"rx": 0.022 - 0.006 * t, "ry": 0.02 - 0.005 * t}, n=7, seg=0.02, frame="up", up=V((0, -1, 0)),
         cap0="open", cap1="flat", offset=lambda t, a, s: 0.003 * math.cos(math.tau * 5 * a)).build(mb, uvmap=uv_stem, mat=mats["skin"])
    carve(mb, point, C, rx, rz, face, mats["glow"])
    return point, C


def face_point(point, C, rx, rz, x, y, lift):
    q = 1 - (x / rx) ** 2 - (y / rz) ** 2
    d = V((x / rx, -math.sqrt(max(q, 0.0)), y / rz))
    u = (math.atan2(d.y, d.x) / math.tau) % 1.0
    v = math.acos(min(max(-d.z, -1.0), 1.0)) / math.pi
    p = point(u, v)
    n = lib.surface_normal(point, u, v)
    return p + n * lift


def carve(mb, point, C, rx, rz, face, mat):
    """Glowing cut-out shapes following the skin (a thin raised patch)."""
    for poly in face:
        vec = [V((x, y, 0)) for x, y in poly]
        tris = geometry.tessellate_polygon([vec])
        # subdivide in 2-D until small, then wrap onto the pumpkin
        work = [(tuple(poly[a]), tuple(poly[b]), tuple(poly[c])) for a, b, c in tris]
        out = []
        while work:
            a, b, c = work.pop()
            e = max(math.dist(a, b), math.dist(b, c), math.dist(c, a))
            if e > 0.022:
                ab = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                bc = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2)
                ca = ((c[0] + a[0]) / 2, (c[1] + a[1]) / 2)
                work += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
            else:
                out.append((a, b, c))
        cache = {}

        def vid(p):
            k = (round(p[0], 6), round(p[1], 6))
            if k not in cache:
                cache[k] = mb.v(face_point(point, C, rx, rz, p[0], p[1], 0.0035))
            return cache[k]
        for a, b, c in out:
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross < 0:
                b, c = c, b
            uv = [(0.5 + p[0] * 3, 0.5 + p[1] * 3) for p in (a, b, c)]
            # x right, y up seen from the front (-Y): counter-clockwise faces -Y
            mb.f((vid(a), vid(b), vid(c)), uv, None, mat)


def grin(w=0.105, top=-0.018, bottom=-0.082, teeth=4, curve=0.045, seed=0):
    """A jagged jack-o'-lantern grin outline (x right, y up), counter-clockwise."""
    up, low = [], []
    n = teeth * 2 + 1
    for i in range(n + 1):
        x = -w + 2 * w * i / n
        f = (x / w) ** 2
        y = top + curve * f
        if 0 < i < n and i % 2 == 1:
            y -= 0.016 * (1 - 0.5 * f)
        up.append((x, y))
    for i in range(n + 1):
        x = w - 2 * w * i / n
        f = (x / w) ** 2
        y = bottom + (curve + 0.025) * f
        if 0 < i < n and i % 3 == 1:
            y += 0.014 * (1 - f)
        low.append((x, y))
    pts = up[::-1] + low[::-1]
    pts = [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 1e-4]
    if sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) < 0:
        pts.reverse()
    return pts


FACES = {
    "angry": [
        [(0.028, 0.030), (0.098, 0.022), (0.074, 0.078)],
        [(-0.028, 0.030), (-0.074, 0.078), (-0.098, 0.022)],
        [(-0.016, -0.004), (0.016, -0.004), (0.0, 0.026)],
        grin(0.108, -0.024, -0.090, teeth=5),
    ],
    "grin": [
        [(0.030, 0.026), (0.092, 0.026), (0.080, 0.050), (0.062, 0.070), (0.044, 0.052)],
        [(-0.030, 0.026), (-0.044, 0.052), (-0.062, 0.070), (-0.080, 0.050), (-0.092, 0.026)],
        [(-0.014, 0.0), (0.014, 0.0), (0.0, 0.020)],
        grin(0.112, -0.020, -0.075, teeth=4, curve=0.05),
    ],
}


# --------------------------------------------------------------------------------------------
# Clothes
# --------------------------------------------------------------------------------------------

def cloth_patch(mb, loft, tile, mat, t0=0.0, t1=1.0, a0=0.0, a1=1.0, jag=0.0, seed=0, nu=None, nv=None, lift=0.0,
                u_range=(0.0, 1.0), v_range=(0.0, 1.0), flip=False):
    """A piece of cloth on a loft between t0..t1 (the end at t1 ragged by `jag`, metres) and around
    a0..a1. UVs: along -> tile rows (t1 at the hem), around -> u_range of the tile."""
    rng = lib.seeded(seed)
    nu = nu or max(8, int((a1 - a0) * 16))
    nv = nv or max(3, int((t1 - t0) * loft.L / 0.05))
    jags = [rng.random() for _ in range(nu + 1)]
    uvm = cloth_tile(*TILES[tile])

    def fn(u, v):
        i = int(round(u * nu))
        j = jags[i % (nu + 1)] if (a1 - a0) < 0.999 else jags[i % nu]
        tend = t1 - (jag / loft.L) * (0.25 + 0.75 * j) * (1 if i % 2 else 0.55)
        t = t0 + (tend - t0) * v
        a = a0 + (a1 - a0) * u
        return loft.surface(min(max(t, 0.0), 1.0), a % 1.0, lift=lift)[0]

    def uv(u, v):
        vv = v_range[0] + (v_range[1] - v_range[0]) * v
        return uvm(1 - vv if flip else vv, u_range[0] + (u_range[1] - u_range[0]) * u)
    lib.grid_patch(mb, fn, nu, nv, uvmap=uv, mat=mat, closed_u=(a1 - a0) > 0.999)


def torso_loft(rig, scale=1.0, depth=1.0):
    Mp, Mc = rig.Mp, rig.Mc
    ctrl = [Mp @ V((0, 0.0, -0.02)), Mp @ V((0, -0.005, 0.10)), Mc @ V((0, -0.01, 0.25)), Mc @ V((0, 0.0, 0.40)),
            Mc @ V((0, 0.02, 0.475)), Mc @ V((0, 0.025, 0.53))]
    keys = [(0.0, (0.165, 0.115)), (0.2, (0.16, 0.11)), (0.45, (0.175, 0.125)), (0.72, (0.20, 0.12)),
            (0.84, (0.185, 0.105)), (0.93, (0.13, 0.085)), (1.0, (0.075, 0.065))]

    def sec(t):
        rx, ry = lerp_keys(keys, t)
        return {"rx": rx * scale, "ry": ry * scale * depth, "p": 2.3}
    up = Mc.to_3x3() @ V((0, -1, 0))
    return Loft(ctrl, sec, n=20, seg=0.03, frame="up", up=up, cap0="open", cap1="open")


def limb_loft(A, B, r0, r1, extra=None):
    pts = [A, A.lerp(B, 0.5), B] if extra is None else [A] + extra + [B]
    d = (B - A).normalized()
    up = V((0, 0, 1)) if abs(d.z) < 0.85 else V((0, -1, 0))
    return Loft(pts, lambda t: {"rx": r0 + (r1 - r0) * t, "ry": (r0 + (r1 - r0) * t) * 0.95}, n=12, seg=0.04,
                frame="up", up=up, cap0="open", cap1="open")


def clothes(mb, rig, kind, mat):
    Mp = rig.Mp
    if kind == "shirt":
        tl = torso_loft(rig)
        cloth_patch(mb, tl, "shirt", mat, 0.0, 1.0, 0.0, 1.0, nu=20, flip=True)
        for side, a in rig.arms.items():
            S, E, W = a["S"], a["E"], a["W"]
            end = E.lerp(W, 0.35)
            sl = limb_loft(S + (S - E).normalized() * 0.02 + V((0, 0, -0.015)), end, 0.066, 0.075, [S.lerp(E, 0.5)])
            cloth_patch(mb, sl, "shirt", mat, 0.0, 1.0, 0.0, 1.0, jag=0.07, seed=3 if side == "R" else 4, nu=12)
    if kind == "vest":
        tl = torso_loft(rig, scale=1.04)
        # the right front panel carries the skull and crossbones on the chest
        cloth_patch(mb, tl, "vest", mat, 0.0, 0.42, 0.27, 0.455, nu=6, nv=4, u_range=(0.0, 0.1), flip=True)
        cloth_patch(mb, tl, "vest", mat, 0.42, 0.86, 0.27, 0.455, nu=6, nv=6, u_range=(0.30, 0.70), flip=True)
        cloth_patch(mb, tl, "vest", mat, 0.86, 0.93, 0.27, 0.455, nu=6, nv=1, u_range=(0.0, 0.1), flip=True)
        cloth_patch(mb, tl, "vest", mat, 0.0, 0.93, 0.545, 1.27, nu=16, u_range=(0.0, 0.10), flip=True)
        for side, a in rig.arms.items():   # tattered sleeves from the shoulder to mid forearm
            S, E, W = a["S"], a["E"], a["W"]
            sl = limb_loft(S + (S - E).normalized() * 0.03, E.lerp(W, 0.55), 0.058, 0.064, [S.lerp(E, 0.5), E])
            cloth_patch(mb, sl, "sleeve", mat, 0.0, 1.0, 0.0, 1.0, jag=0.12, seed=7 if side == "R" else 8, nu=12)
    # breeches: hips and two ragged legs
    hip = Loft([Mp @ V((0, -0.005, 0.10)), Mp @ V((0, 0.0, -0.02)), Mp @ V((0, 0.005, -0.10))],
               lambda t: {"rx": 0.172 - 0.01 * t, "ry": 0.118 - 0.005 * t, "p": 2.3}, n=18, seg=0.03, frame="up",
               up=Mp.to_3x3() @ V((0, -1, 0)), cap0="open", cap1="dome", cap1_len=0.05)
    hip.build(mb, uvmap=lambda s, a: cloth_tile(*TILES["breeches"])(s * 0.4, a), mat=mat)
    for side, lg in rig.legs.items():
        H, K, A = lg["H"], lg["K"], lg["A"]
        end = K.lerp(A, 0.22)
        ll = limb_loft(H + (H - K).normalized() * 0.03, end, 0.082, 0.064, [H.lerp(K, 0.55), K])
        cloth_patch(mb, ll, "breeches", mat, 0.0, 1.0, 0.0, 1.0, jag=0.09, seed=11 if side == "R" else 12, nu=12)
    # the sash round the waist with two tails at the left hip
    ring = []
    for i in range(24):
        ph = math.tau * i / 24
        ring.append(Mp @ V((0.178 * math.sin(ph), -0.124 * math.cos(ph) + 0.004, 0.045 + 0.012 * math.sin(ph))))
    Loft(ring, lambda t: {"rx": 0.008, "ry": 0.04}, n=4, seg=0.03, closed=True, frame="up",
         up=Mp.to_3x3() @ V((0, 0, 1))).build(mb, uvmap=lambda s, a: cloth_tile(*TILES["sash"])(a, s), mat=mat)
    for k, (dx, ln) in enumerate(((0.0, 0.30), (0.035, 0.24))):
        top = Mp @ V((-0.15 + dx, -0.075, 0.03))
        bot = top + V((-0.03 - dx, -0.02, -ln))
        wv = (Mp.to_3x3() @ V((0.6, 0.8, 0))).normalized() * 0.04
        ids = []
        for j in range(4):
            p = top.lerp(bot, j / 3) + V((0, -0.01 * math.sin(j * 1.7), 0))
            ids.append((mb.v(p - wv), mb.v(p + wv)))
        uvm = cloth_tile(*TILES["sash"])
        for j in range(3):
            mb.f((ids[j][0], ids[j + 1][0], ids[j + 1][1], ids[j][1]),
                 [uvm(0.2, j / 3), uvm(0.2, (j + 1) / 3), uvm(0.8, (j + 1) / 3), uvm(0.8, j / 3)], None, mat)


def hair(mb, mat, C):
    ctrl = [C + V((0, 0.035, 0.11)), C + V((0, 0.06, 0.0)), C + V((0, 0.075, -0.14)), C + V((0, 0.07, -0.25))]
    lo = Loft(ctrl, lambda t: {"rx": lerp_keys([(0, 0.13), (0.3, 0.172), (1, 0.165)], t),
                                "ry": lerp_keys([(0, 0.09), (0.3, 0.125), (1, 0.10)], t)}, n=16, seg=0.03, frame="up",
              up=V((0, 1, 0)), cap0="open", cap1="open")
    cloth_patch(mb, lo, "hair", mat, 0.0, 1.0, 0.22, 0.78, jag=0.10, seed=21, nu=16, nv=8)
    # a fringe over the top of the pumpkin
    for i in range(7):
        a = -0.6 + 1.2 * i / 6
        p0 = C + V((0.13 * math.sin(a), 0.13 * math.cos(a) * 0.6 + 0.02, 0.12))
        p1 = C + V((0.18 * math.sin(a * 1.2), 0.15 * math.cos(a) + 0.02, -0.05))
        side = V((math.cos(a), -math.sin(a), 0)) * 0.035
        uvm = cloth_tile(*TILES["hair"])
        ids = [mb.v(p0 - side), mb.v(p0 + side), mb.v(p1 + side * 1.4), mb.v(p1 - side * 1.4)]
        mb.f(ids, [uvm(0, 0.1 * i), uvm(0, 0.1 * i + 0.1), uvm(1, 0.1 * i + 0.1), uvm(1, 0.1 * i)], None, mat)


def bandana(mb, mat, point):
    uvm = cloth_tile(*TILES["bandana"])

    def fn(u, v):
        vv = 0.66 + 0.30 * v
        p = point(u, vv)
        return p + lib.surface_normal(point, u, vv) * 0.008
    lib.grid_patch(mb, fn, 24, 4, uvmap=lambda u, v: uvm(v, u), mat=mat, closed_u=True)
    # the knot and tails at the back
    k = point(0.25, 0.70) + V((0, 0.02, 0))
    for dx, ln in ((-0.03, 0.16), (0.03, 0.12)):
        a, b = k, k + V((dx, 0.03, -ln))
        w = V((0.03, 0, 0))
        ids = [mb.v(a - w), mb.v(a + w), mb.v(b + w * 0.6), mb.v(b - w * 0.6)]
        mb.f(ids, [uvm(0, 0), uvm(0, 1), uvm(1, 1), uvm(1, 0)], None, mat)


def oar(mb, top, d, length, mat):
    side = d.cross(V((0, 0, 1))).normalized()
    if side.length < 1e-6:
        side = V((1, 0, 0))
    shaft_end = top + d * (length - 0.55)
    Loft([top, top + d * 0.2, shaft_end], lambda t: {"rx": 0.019 if t > 0.05 else 0.017, "ry": 0.019}, n=8, seg=0.3,
         frame="up", up=side, cap0="dome", cap1="flat", cap0_len=0.012).build(
             mb, uvmap=lambda s, a: (s * 4, 0.5 + 0.1 * a), mat=mat)
    blade_n = side.cross(d).normalized()
    Loft([shaft_end - d * 0.05, shaft_end + d * 0.2, top + d * length],
         lambda t: {"rx": 0.03 + 0.055 * min(t * 2.5, 1), "ry": 0.012, "p": 3.0}, n=10, seg=0.08, frame="up", up=blade_n,
         cap0="flat", cap1="dome", cap1_len=0.03).build(mb, uvmap=lambda s, a: (s * 2, 0.5 + 0.1 * a), mat=mat)


# --------------------------------------------------------------------------------------------

def textures():
    bone = lib.paint_named("tex_pirates.py", {"kind": "bone"}, {"tex": "pirates-bone.jpg"})["tex"]
    cloth = lib.paint_named("tex_pirates.py", {"kind": "cloth"}, {"tex": "pirates-cloth.jpg"})["tex"]
    skin = lib.paint_named("tex_pirates.py", {"kind": "pumpkin", "ribs": 8, "color": "#e46f1a", "groove": "#9a3e0c"},
                     {"tex": "pirates-pumpkin.jpg"})["tex"]
    return bone, cloth, skin


def build(name, pose, pirate=None, face=None, carve_color="#ff4f86", extras=()):
    lib.reset()
    bone_t, cloth_t, skin_t = textures()
    mats = [lib.material("bone", base_tex=bone_t, roughness=0.7, specular=0.35)]
    if pirate:
        mats.append(lib.material("pirate_cloth", base_tex=cloth_t, roughness=0.9, specular=0.2, double_sided=True))
        mats.append(lib.material("pumpkin_skin", base_tex=skin_t, roughness=0.55, specular=0.35))
        mats.append(lib.material("glow_carving", color=carve_color, emission=carve_color, emission_strength=1.0,
                                 roughness=0.6))
    rig = Rig(pose)
    body = MB()
    build_bones(body, rig, 0, dressed=pirate)
    if pirate:
        clothes(body, rig, pirate, 1)
    head = MB()
    if pirate:
        point, C = pumpkin_head(head, {"skin": 2, "glow": 3}, FACES[face], seed=len(name))
        if "hair" in extras:
            hair(head, 1, C)
        if "bandana" in extras:
            bandana(head, 1, point)
    else:
        skull(head, 0)
    head.transform(rig.Mh)
    lo = min(v[2] for v in body.verts + head.verts)
    if pose == "climb":
        shift = Matrix.Translation((0, 0, -lo))
        body.transform(shift)
        head.transform(shift)
    root = body.object("skeleton", mats, origin=(0, 0, 0), auto_smooth=60)
    hobj = head.object("head", mats, origin=(rig.Mh @ NECK_TOP) + (V((0, 0, -lo)) if pose == "climb" else V()),
                       auto_smooth=60)
    lib.set_parent(hobj, root)
    total = lib.tri_count(root) + lib.tri_count(hobj)
    if rig.oar:
        om = MB()
        top, d, ln = rig.oar
        oar(om, top, d, ln, 0)
        wood = lib.material("oar_wood", color="#6a5038", roughness=0.8)
        oobj = om.object("oar", [wood], origin=top + d * POSES[pose]["oar"]["hands"][0])
        lib.set_parent(oobj, root)
        total += lib.tri_count(oobj)
    for o in list(bpy_objects()):
        if o.type == "MESH":
            # drop material slots a part doesn't use (keeps the glTF primitives clean)
            used = set(p.material_index for p in o.data.polygons)
            if len(used) < len(o.data.materials):
                remap = {old: new for new, old in enumerate(sorted(used))}
                keep = [o.data.materials[i] for i in sorted(used)]
                idx = [remap[p.material_index] for p in o.data.polygons]
                o.data.materials.clear()
                for m in keep:
                    o.data.materials.append(m)
                o.data.polygons.foreach_set("material_index", idx)
    zs = [v[2] for v in body.verts + head.verts]
    print(f"  {name}: {total} tris, height {max(zs) - (lo if pose == 'climb' else 0):.2f} m, lowest {min(zs):.3f}")
    return lib.export(name)


def bpy_objects():
    import bpy
    return bpy.context.scene.objects


def main():
    jobs = [
        ("sit", "skeleton-pirate-sit", "pirate_sit", dict(pirate="vest", face="angry", carve_color="#ff4c8a", extras=("hair",))),
        ("stand", "skeleton-pirate-stand", "pirate_stand", dict(pirate="shirt", face="grin", carve_color="#ff7a3a", extras=("bandana",))),
        ("skeleton", "skeleton", "stand", {}),
        ("climb", "skeleton-climb", "climb", {}),
    ]
    for key, name, pose, kw in jobs:
        if ONLY is None or key in ONLY:
            build(name, pose, **kw)


if __name__ == "__main__":
    main()
