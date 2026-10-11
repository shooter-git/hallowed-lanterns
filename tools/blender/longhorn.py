# SPDX-License-Identifier: MIT
"""The giant glowing inflatable Texas longhorns of the Pasture of Giants (reference/longhorns.jpg).

    blender -b --factory-startup -P tools/blender/longhorn.py

Writes public/models/longhorn-standing.glb, longhorn-grazing.glb, longhorn-lying.glb and
longhorn-blower.glb.

Each longhorn is sewn from lofted fabric tubes (torso, legs, hooves, tail, neck, head, one horn
tube running across the poll, ears). Panel seams are pinched into the geometry and painted, at
the same places, into the glow texture (tex_inflatable.py). All three poses share one UV layout
and an identical texture, so the engine can load it once.

Nodes: `body` (root, origin at the centre of the torso footprint) and its child `head` (neck,
head, horns, ears, eyes), whose pivot is at the base of the neck inside the chest: rotate it about
its local X axis (glTF: positive lowers the head) and Y axis (turns it) to make it look around.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB, Loft, lerp_keys  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

TEX_SIZE = 2048
# The shapes below are drawn at 1/SCALE: the owner's note is that these bulls are huge (standing:
# head top ~4.6 m, horn tips ~6 m, horn span ~8.3 m; a person's eyes reach the belly line).
SCALE = 1.38

# --------------------------------------------------------------------------------------------
# Shapes (standing pose, Blender coordinates: the animal faces -Y, +X is its left side)
# --------------------------------------------------------------------------------------------

BODY_KEYS = [  # t: (half width, top half height, bottom half height)
    (0.00, (0.62, 0.55, 0.52)),
    (0.15, (0.78, 0.68, 0.70)),
    (0.40, (0.82, 0.66, 0.74)),
    (0.62, (0.84, 0.62, 0.74)),
    (0.82, (0.80, 0.62, 0.64)),
    (1.00, (0.66, 0.54, 0.46)),
]

HEAD_KEYS = [  # t (poll -> muzzle): (half width, face-side half depth, jaw-side half depth)
    (0.00, (0.46, 0.32, 0.36)),
    (0.12, (0.55, 0.36, 0.42)),
    (0.30, (0.54, 0.34, 0.42)),
    (0.52, (0.37, 0.28, 0.35)),
    (0.74, (0.26, 0.25, 0.28)),
    (0.90, (0.30, 0.27, 0.29)),
    (1.00, (0.30, 0.26, 0.28)),
]
HEAD_CTRL = [(0, -1.80, 2.92), (0, -2.03, 2.58), (0, -2.30, 2.16), (0, -2.58, 1.75)]
HEAD_UP = (0, -1, 0.35)          # the face looks forward and up
NECK_END = (0, -1.78, 2.66)      # where the neck disappears into the back of the head

HORN_HALF = [(0, 0, 0), (0.45, 0, 0.02), (0.98, 0.02, 0.05), (1.55, 0.05, 0.14), (2.06, 0.07, 0.30),
             (2.48, 0.07, 0.55), (2.80, 0.04, 0.90), (2.98, 0.0, 1.25)]
HORN_R = [(0.0, 0.24), (0.12, 0.23), (0.3, 0.19), (0.5, 0.145), (0.7, 0.10), (0.85, 0.06),
          (0.95, 0.03), (1.0, 0.012)]

# Panel layouts: long seams (around, a) and ring seams (along, t) per band.
L64 = [k / 64 for k in (0, 13, 24, 32, 40, 51)]
BODY_BANDS = [[0.45], [0.22, 0.58, 0.84], [0.30, 0.68], [0.30, 0.68], [0.22, 0.58, 0.84], [0.45]]
LAYOUTS = {
    "body": (64, L64, BODY_BANDS),
    "neck": (40, [0.25, 0.75], []),
    "head": (48, [k / 48 for k in (0, 14, 24, 34)], [0.20, 0.80]),
    "leg": (32, [0.25, 0.75], [0.66]),
    "hoof": (32, [0, 0.5], []),
    "horns": (20, [0.25, 0.75], [0.44, 0.5, 0.56]),
    "ear": (16, [0, 0.5], []),
    "tail": (16, [0, 0.5], [0.5]),
    "rim": (12, [], []),
}
BRIGHT = {
    "body": {"base": 0.95, "bottom": 0.05},
    "neck": {"base": 0.94},
    "head": {"profile": [[0, 0.9], [0.5, 0.96], [1, 0.98]]},
    "leg": {"profile": [[0, 0.88], [1, 1.02]]},
    "hoof": {"base": 1.0},
    "horns": {"profile": [[0, 0.5], [0.12, 0.6], [0.35, 0.78], [0.5, 0.9], [0.65, 0.78], [0.88, 0.6], [1, 0.5]]},
    "ear": {"base": 0.86},
    "tail": {"base": 0.85},
    "rim": {"base": 0.9},
}


def sec_keys(keys, p=2.5):
    def f(t):
        rx, ry, ry2 = lerp_keys(keys, t)
        return {"rx": rx, "ry": ry, "ry2": ry2, "p": p}
    return f


def round_sec(keys, flat=1.0):
    def f(t):
        r = lerp_keys(keys, t)
        return {"rx": r, "ry": r * flat}
    return f


# --------------------------------------------------------------------------------------------
# Poses
# --------------------------------------------------------------------------------------------

def head_matrix(target_poll, pitch=0.0, yaw=0.0):
    """Rigid transform of the standing head: rotate about the poll, then move the poll."""
    P0 = Vector(HEAD_CTRL[0])
    return (Matrix.Translation(Vector(target_poll)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
            @ Matrix.Rotation(math.radians(pitch), 4, "X") @ Matrix.Translation(-P0))


POSES = {
    "standing": {
        "lift": 0.12,
        "body_dz": 0.0,
        "legs": {
            "leg_FL": [(0.46, -0.85, 1.75), (0.49, -0.88, 1.15), (0.51, -0.93, 0.62), (0.52, -0.90, 0.30)],
            "leg_FR": [(-0.46, -0.85, 1.75), (-0.49, -0.88, 1.15), (-0.51, -0.93, 0.62), (-0.52, -0.90, 0.30)],
            "leg_HL": [(0.46, 0.95, 1.75), (0.50, 1.05, 1.15), (0.52, 1.18, 0.66), (0.52, 1.06, 0.30)],
            "leg_HR": [(-0.46, 0.95, 1.75), (-0.50, 1.05, 1.15), (-0.52, 1.18, 0.66), (-0.52, 1.06, 0.30)],
        },
        "hooves": {  # bottom centre, axis direction
            "leg_FL": ((0.52, -0.90, 0.0), (0, 0, 1)), "leg_FR": ((-0.52, -0.90, 0.0), (0, 0, 1)),
            "leg_HL": ((0.52, 1.06, 0.0), (0, 0, 1)), "leg_HR": ((-0.52, 1.06, 0.0), (0, 0, 1)),
        },
        "neck_base": (0, -1.0, 1.95),
        "neck_mid": (0, -1.40, 2.30),
        "head": head_matrix(HEAD_CTRL[0]),
        "tail": [(0, 1.45, 2.25), (0, 1.75, 2.42), (0, 1.92, 2.70), (0, 1.82, 2.95), (0, 1.62, 2.98)],
    },
    "grazing": {
        "lift": 0.12,
        "body_dz": -0.04,
        "legs": {
            "leg_FL": [(0.48, -0.85, 1.71), (0.62, -0.97, 1.12), (0.84, -1.10, 0.62), (0.98, -1.18, 0.30)],
            "leg_FR": [(-0.48, -0.85, 1.71), (-0.62, -0.97, 1.12), (-0.84, -1.10, 0.62), (-0.98, -1.18, 0.30)],
            "leg_HL": [(0.46, 0.95, 1.71), (0.52, 1.05, 1.13), (0.58, 1.18, 0.66), (0.60, 1.06, 0.30)],
            "leg_HR": [(-0.46, 0.95, 1.71), (-0.52, 1.05, 1.13), (-0.58, 1.18, 0.66), (-0.60, 1.06, 0.30)],
        },
        "hooves": {
            "leg_FL": ((0.99, -1.18, 0.0), (0, 0, 1)), "leg_FR": ((-0.99, -1.18, 0.0), (0, 0, 1)),
            "leg_HL": ((0.60, 1.06, 0.0), (0, 0, 1)), "leg_HR": ((-0.60, 1.06, 0.0), (0, 0, 1)),
        },
        "neck_base": (0, -1.0, 1.88),
        "neck_mid": (0, -1.55, 1.85),
        "head": head_matrix((0, -2.05, 1.72), pitch=30),
        "tail": [(0, 1.45, 2.21), (0, 1.75, 2.40), (0, 1.94, 2.68), (0, 1.86, 2.95), (0, 1.66, 3.00)],
    },
    "lying": {
        "body_dz": -1.07,
        "legs": {
            "leg_FL": [(0.46, -0.85, 0.70), (0.53, -0.97, 0.32), (0.52, -1.38, 0.27), (0.50, -1.80, 0.27)],
            "leg_FR": [(-0.46, -0.85, 0.70), (-0.53, -0.97, 0.32), (-0.53, -1.30, 0.27), (-0.52, -1.62, 0.27)],
            "leg_HL": [(0.50, 0.95, 0.72), (0.82, 1.05, 0.45), (0.94, 1.12, 0.28), (0.96, 0.62, 0.27), (0.94, 0.22, 0.27)],
            "leg_HR": [(-0.50, 0.95, 0.72), (-0.70, 1.25, 0.42), (-0.78, 1.75, 0.30), (-0.80, 2.12, 0.28)],
        },
        "hooves": {
            "leg_FL": ((0.50, -2.10, 0.30), (0, 1, 0)), "leg_FR": ((-0.52, -1.92, 0.30), (0, 1, 0)),
            "leg_HL": ((0.94, -0.08, 0.30), (0, 1, 0)), "leg_HR": ((-0.80, 2.42, 0.30), (0, -1, 0)),
        },
        "neck_base": (0, -1.0, 0.82),
        "neck_mid": (0, -1.42, 1.25),
        "head": head_matrix((0.08, -1.92, 2.05), pitch=4, yaw=14),
        "tail": [(0, 1.45, 1.18), (0, 1.72, 1.02), (-0.1, 1.95, 0.75), (-0.25, 2.1, 0.45), (-0.4, 2.15, 0.2)],
    },
}


# --------------------------------------------------------------------------------------------
# Building
# --------------------------------------------------------------------------------------------

NOMINAL = {}


def make_parts(pose):
    """All the lofts of one pose: {name: (loft, layout kind, group)}."""
    P = POSES[pose]
    lift = P.get("lift", 0.0)  # raises everything above the hooves (longer legs)
    dz = P["body_dz"] + lift
    parts = {}

    def up(p, k=1.0):
        return (p[0], p[1], p[2] + lift * k)

    def add(name, kind, group, ctrl, section, **kw):
        n, longs, bands = LAYOUTS[kind]
        layout = lib.panel_layout(longs, bands)
        extra = sorted(set(t for b in layout["bands"] for t in b))
        loft = Loft(ctrl, section, n=n, extra_t=extra, nominal=NOMINAL.get(name), **kw)
        loft.offset = lib.puff_offset(layout, loft.nominal, depth=0.09, cap=0.035) if kind != "rim" else None
        parts[name] = (loft, kind, group, layout)
        return loft

    body_ctrl = [(0, -1.30, 1.86), (0, -0.70, 1.90), (0, 0.0, 1.84), (0, 0.70, 1.86), (0, 1.35, 1.92)]
    add("body", "body", "body", [(x, y, z + dz) for x, y, z in body_ctrl], sec_keys(BODY_KEYS, 2.5),
        seg=0.05, cap0_len=0.42, cap1_len=0.36, cap_rings=8)
    for name, ctrl in P["legs"].items():
        ctrl = [up(c, c[2] / 1.75) for c in ctrl]
        hind = name.startswith("leg_H")
        keys = ([(0, 0.48), (0.3, 0.38), (0.65, 0.30), (1, 0.29)] if hind
                else [(0, 0.42), (0.35, 0.36), (0.7, 0.30), (1, 0.29)])
        add(name, "leg", "body", ctrl, round_sec(keys), seg=0.05, frame="up", up=(0, -1, 0.001),
            cap0_len=0.3, cap1_len=0.15)
        base, axis = P["hooves"][name]
        base, axis = Vector(base), Vector(axis)
        add("hoof_" + name[4:], "hoof", "body", [base, base + axis * 0.36],
            round_sec([(0, 0.34), (0.7, 0.34), (1, 0.32)]), seg=0.06, frame="up",
            up=(0, -1, 0.001) if abs(axis.z) > 0.5 else (0, 0, 1), cap0="flat", cap1="dome", cap1_len=0.10)
    tail = [up(c) for c in P["tail"]]
    add("tail", "tail", "body", tail, round_sec([(0, 0.14), (0.5, 0.12), (1, 0.10)]), seg=0.05,
        frame="rmf", up=(1, 0, 0))

    # head group (rigid transform of the standing head)
    M = Matrix.Translation((0, 0, lift)) @ P["head"]
    R = M.to_3x3()
    head = add("head", "head", "head", [M @ Vector(p) for p in HEAD_CTRL], sec_keys(HEAD_KEYS, 3.0),
               seg=0.04, frame="up", up=R @ Vector(HEAD_UP), cap0_len=0.30, cap1_len=0.15, cap_rings=8)
    neck_end = M @ Vector(NECK_END)
    add("neck", "neck", "head", [up(P["neck_base"]), up(P["neck_mid"]), neck_end],
        lambda t: {"rx": lerp_keys([(0, 0.56), (0.5, 0.50), (1, 0.44)], t),
                   "ry": lerp_keys([(0, 0.66), (0.5, 0.56), (1, 0.46)], t), "p": 2.2},
        seg=0.05, frame="up", up=(0, 0, 1), cap0_len=0.45, cap1_len=0.3)
    # horns: one tube across the poll, from the right tip (-X) to the left tip (+X)
    hp, hn = head.frame_at(0.0)[0], head.frame_at(0.0)[2]
    ht = head.frame_at(0.0)[1]
    centre = hp + hn * 0.12 - ht * 0.12
    up_h = R @ Vector((0, 0, 1))
    side = R @ Vector((1, 0, 0))
    fwd = R @ Vector((0, 1, 0))
    half = [centre + side * x + fwd * y + up_h * z for x, y, z in HORN_HALF]
    halfR = [centre - side * x + fwd * y + up_h * z for x, y, z in HORN_HALF]
    ctrl = list(reversed(halfR[1:])) + half

    def horn_sec(t):
        r = lerp_keys(HORN_R, abs(2 * t - 1))
        return {"rx": r * 0.92, "ry": r * 1.1}
    add("horns", "horns", "head", ctrl, horn_sec, seg=0.055, frame="rmf", up=up_h,
        cap0="point", cap1="point", cap0_len=0.03, cap1_len=0.03)
    # ears: below the horns, sticking out sideways and a little down and back
    for name, a in (("ear_R", 0.24), ("ear_L", 0.76)):
        root, nrm = head.surface(0.15, a)
        root = root - nrm * 0.10
        d = (nrm + up_h * -0.55 + fwd * -0.35).normalized()
        ctrl = [root, root + d * 0.32, root + d * 0.64 - up_h * 0.06]
        add(name, "ear", "head", ctrl,
            lambda t: {"rx": lerp_keys([(0, 0.15), (0.5, 0.17), (1, 0.12)], t),
                       "ry": lerp_keys([(0, 0.10), (0.5, 0.115), (1, 0.08)], t)},
            seg=0.04, frame="up", up=up_h, cap0_len=0.1, cap1_len=0.10)
    # eye rims: an almond outline lifted off the head
    for name, ac in (("rim_R", EYE_A), ("rim_L", 1 - EYE_A)):
        pts = []
        for i in range(28):
            ang = TAU_ * i / 28
            u = math.cos(ang)
            v = math.sin(ang) * (1 - u * u) ** 0.35
            pts.append(head.surface(EYE_T + u * (EYE_DT + 0.012), ac + v * (EYE_DA + 0.006) * (1 if ac < 0.5 else -1),
                                    lift=0.010)[0])
        add(name, "rim", "head", pts, lambda t: {"rx": 0.034, "ry": 0.034}, seg=0.03, closed=True,
            frame="rmf", up=(0, 0, 1))
    return parts


TAU_ = math.tau
EYE_T, EYE_A, EYE_DT, EYE_DA = 0.27, 0.36, 0.12, 0.038   # eye centre (t, a) and half sizes


def eye_patches(parts, mb, mat):
    """Dark almond eyes, nostrils and the mouth line (material `eye_dark`)."""
    head = parts["head"][0]
    for ac in (EYE_A, 1 - EYE_A):
        sgn = 1 if ac < 0.5 else -1

        def fn(u, v, ac=ac, sgn=sgn):
            uu = u * 2 - 1
            w = (1 - uu * uu) ** 0.55
            vv = (v * 2 - 1) * w
            return head.surface(EYE_T + uu * EYE_DT, ac + vv * EYE_DA * sgn, lift=0.016)[0]
        lib.grid_patch(mb, fn, 12, 4, mat=mat, outward=head.surface(EYE_T, ac)[1])
    # nostrils: two dark commas on the muzzle front; the mouth: a dark line under it
    for side in (1, -1):
        def fn(u, v, side=side):
            t = 1.42 + (u - 0.5) * 0.36
            w = math.sin(math.pi * u) ** 0.6
            a = 0.5 + side * (0.115 + (v - 0.5) * 0.07 * w + (u - 0.5) * 0.05)
            return head.surface_ext(t, a, lift=0.012)[0]
        lib.grid_patch(mb, fn, 6, 3, mat=mat, outward=head.surface_ext(1.42, 0.5 + side * 0.115)[1])

    # mouth: along the jaw side of the muzzle dome (a from 0.75 through 0 to 0.25)
    def mouth2(u, v):
        a = (0.80 + u * 0.40) % 1.0
        t = 1.42 + (v - 0.5) * 0.05
        return head.surface_ext(t, a, lift=0.008)[0]
    lib.grid_patch(mb, mouth2, 12, 1, mat=mat, outward=lambda u, v: head.surface_ext(1.42, (0.80 + u * 0.40) % 1.0)[1])


def build_pose(pose, atlas, tex_path):
    lib.reset()
    parts = make_parts(pose)
    glow = lib.material("glow_inflatable", base_tex=tex_path, emission_tex=tex_path, roughness=0.65,
                        specular=0.3)
    dark = lib.material("eye_dark", color="#0a0a0d", roughness=0.35)
    mbs = {"body": MB(), "head": MB()}
    for name, (loft, kind, group, layout) in parts.items():
        loft.build(mbs[group], uvmap=atlas.mapper(name), mat=0)
    eye_patches(parts, mbs["head"], 1)
    for mb in mbs.values():
        mb.transform(Matrix.Scale(SCALE, 4))
    if pose in ("lying", "grazing"):
        mbs["body"].clamp_z(0.0)
        mbs["head"].clamp_z(0.0)
    body = mbs["body"].object("body", [glow], origin=(0, 0, 0))
    nb = POSES[pose]["neck_base"]
    pivot = Vector((nb[0], nb[1], nb[2] + POSES[pose].get("lift", 0.0))) * SCALE
    head = mbs["head"].object("head", [glow, dark], origin=pivot)
    lib.set_parent(head, body)
    for o in (body, head):
        print(f"  {pose}/{o.name}: {lib.tri_count(o)} tris")
    return lib.export("longhorn-" + pose)


def build_atlas():
    """Atlas from the standing pose's part sizes (shared by all poses), and the glow texture."""
    lib.reset()
    parts = make_parts("standing")
    for name, (loft, *_rest) in parts.items():
        NOMINAL[name] = loft.nominal
    atlas = lib.Atlas(TEX_SIZE, pad=6)
    for name, (loft, *_rest) in parts.items():
        atlas.add(name, loft.total(), loft.nominal["C"])
    atlas.pack()
    print(f"[atlas] {atlas.density:.0f} px/m")
    spec_parts = []
    for name, (loft, kind, group, layout) in parts.items():
        spec_parts.append({"name": name, "rect": atlas.rects[name], "dims": loft.nominal,
                           "layout": layout, "bright": BRIGHT[kind], "pad": 6})
    out = lib.paint("tex_inflatable.py", {"size": TEX_SIZE, "parts": spec_parts, "quality": 88,
                                          "line_width": 0.0045, "line_depth": 0.45,
                                          "crease_width": 0.035, "crease_depth": 0.12},
                    {"glow": "longhorn-glow.jpg"})
    return atlas, out["glow"]


# --------------------------------------------------------------------------------------------
# The blower (the yellow fan that keeps them inflated)
# --------------------------------------------------------------------------------------------

def build_blower():
    lib.reset()
    yellow = lib.material("plastic_yellow", color="#e2cb22", roughness=0.42, specular=0.5)
    black = lib.material("plastic_black", color="#141414", roughness=0.6)
    fabric = lib.material("fabric", color="#e9e9e4", roughness=0.8)
    mb = MB()
    # volute: a fat disc, axis along X, standing on a base
    cz = 0.215
    vol = Loft([(-0.10, 0, cz), (0.10, 0, cz)], lambda t: {"rx": 0.185, "ry": 0.185}, n=28, seg=0.2,
               frame="up", up=(0, 0, 1), cap0="flat", cap1="flat")
    vol.build(mb, mat=0)
    # rounded edge rings
    for x in (-0.10, 0.10):
        ring = Loft([(x, 0.185 * math.cos(TAU_ * i / 28), cz + 0.185 * math.sin(TAU_ * i / 28)) for i in range(28)],
                    lambda t: {"rx": 0.014, "ry": 0.014}, n=6, seg=0.05, closed=True, frame="rmf", up=(1, 0, 0))
        ring.build(mb, mat=0)
    # motor housing and base
    lib.box(mb, (0.0, 0.07, 0.11), (0.24, 0.26, 0.20), mat=0)
    lib.box(mb, (0.0, 0.0, 0.012), (0.26, 0.40, 0.024), mat=1)
    # handle on top
    hpts = [(-0.06, 0.04, cz + 0.17), (-0.05, 0.04, cz + 0.24), (0.05, 0.04, cz + 0.24), (0.05, 0.04, cz + 0.17)]
    Loft(hpts, lambda t: {"rx": 0.016, "ry": 0.016}, n=8, seg=0.02, frame="up", up=(0, 1, 0)).build(mb, mat=1)
    # intake grille: black disc with raised rings on the +X face
    Loft([(0.101, 0, cz), (0.112, 0, cz)], lambda t: {"rx": 0.13, "ry": 0.13}, n=24, seg=0.1, frame="up",
         up=(0, 0, 1), cap0="flat", cap1="flat").build(mb, mat=1)
    for r in (0.04, 0.075, 0.11):
        Loft([(0.116, r * math.cos(TAU_ * i / 20), cz + r * math.sin(TAU_ * i / 20)) for i in range(20)],
             lambda t: {"rx": 0.005, "ry": 0.005}, n=4, seg=0.05, closed=True, frame="rmf",
             up=(1, 0, 0)).build(mb, mat=0)
    # outlet spout toward -Y at the bottom, then a fabric tube lying on the ground
    lib.box(mb, (0.0, -0.20, 0.12), (0.16, 0.12, 0.16), mat=0)
    tube = Loft([(0.0, -0.24, 0.12), (0.0, -0.40, 0.12), (0.03, -0.60, 0.11), (0.08, -0.85, 0.11)],
                lambda t: {"rx": 0.11 + 0.012 * math.sin(t * 9), "ry": 0.085, "oy": -0.015 * t}, n=16, seg=0.04,
                frame="up", up=(0, 0, 1), cap0="open", cap1="dome", cap1_len=0.07)
    tube.build(mb, mat=2)
    obj = mb.object("blower", [yellow, black, fabric], origin=(0, 0, 0), auto_smooth=40)
    print(f"  blower: {lib.tri_count(obj)} tris")
    return lib.export("longhorn-blower")


def main():
    atlas, tex = build_atlas()
    for pose in ("standing", "grazing", "lying"):
        build_pose(pose, atlas, tex)
    build_blower()


main()
