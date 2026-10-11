# SPDX-License-Identifier: MIT
"""Shared helpers for the Hallowed Lanterns model scripts.

Runs inside Blender (3.4+, headless). Each model script does::

    import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lib

Conventions (the engine depends on them): metres, Blender +Z up, the model's front faces -Y
(glTF +Z after export), ground at z = 0, origin at the footprint centre.

Blender's bundled Python here has no numpy, so textures are painted by small numpy/Pillow
scripts (`tex_*.py`) that `paint()` runs with an external `python3` (or `$HL_PYTHON`). They are
cached in `.cache/` and only repainted when the painter or its parameters change.
"""

import bisect
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
MODELS = os.path.join(ROOT, "public", "models")
CACHE = os.path.join(HERE, ".cache")
PREVIEW = os.path.join(HERE, "preview")
TAU = math.tau


def ensure_numpy():
    """Blender's glTF add-on needs numpy. Debian's Blender runs on the system Python, which may
    not have it: then use a numpy built for this Python version from $HL_BLENDER_PYLIB or
    .cache/pylib<ver>/ (e.g. `python3.11 -m pip install --target tools/blender/.cache/pylib311 numpy`)."""
    try:
        import numpy  # noqa: F401
        return
    except ImportError:
        pass
    ver = f"{sys.version_info.major}{sys.version_info.minor}"
    for d in (os.environ.get("HL_BLENDER_PYLIB"), os.path.join(CACHE, "pylib" + ver)):
        if d and os.path.isdir(os.path.join(d, "numpy")):
            sys.path.insert(0, d)
            import numpy  # noqa: F401
            return
    raise SystemExit(f"Blender's Python {sys.version.split()[0]} has no numpy (the glTF add-on needs it). "
                     f"Install one with: python{sys.version_info.major}.{sys.version_info.minor} -m pip install "
                     f"--target {os.path.join(CACHE, 'pylib' + ver)} numpy")


ensure_numpy()
import numpy as _np  # noqa: E402

for _alias, _type in (("bool", bool), ("int", int), ("float", float), ("object", object), ("str", str)):
    if _alias not in _np.__dict__:
        setattr(_np, _alias, _type)  # Blender 3.4's glTF importer still uses the old numpy aliases


# ----------------------------------------------------------------------------------------------
# Scene
# ----------------------------------------------------------------------------------------------

def reset():
    """An empty scene (nothing from the startup file)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _images.clear()
    for d in (MODELS, CACHE, PREVIEW):
        os.makedirs(d, exist_ok=True)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def empty(name, location=(0, 0, 0), rotation=(0, 0, 0), parent=None, size=0.1):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = size
    obj.location = location
    obj.rotation_euler = rotation
    link(obj)
    if parent is not None:
        set_parent(obj, parent)
    return obj


def set_parent(child, parent):
    """Parents keeping the world transform, with an identity parent-inverse (clean glTF nodes)."""
    bpy.context.view_layer.update()
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.matrix_basis = parent.matrix_world.inverted() @ world
    return child


# ----------------------------------------------------------------------------------------------
# Colour and materials
# ----------------------------------------------------------------------------------------------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgba(c, alpha=1.0):
    """'#rrggbb' or an sRGB (r, g, b) tuple 0..1 -> linear RGBA."""
    if isinstance(c, str):
        c = c.lstrip("#")
        c = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return (*[srgb_to_linear(v) for v in c[:3]], alpha)


_images = {}


def image(path, non_color=False):
    key = (os.path.abspath(path), non_color)
    try:
        cached = _images.get(key)
        valid = cached is not None and cached.name in bpy.data.images
    except ReferenceError:
        valid = False
    if not valid:
        img = bpy.data.images.load(os.path.abspath(path), check_existing=False)
        if non_color:
            img.colorspace_settings.name = "Non-Color"
        _images[key] = img
    return _images[key]


def material(name, color="#ffffff", roughness=0.5, metallic=0.0, specular=0.5,
             base_tex=None, emission=None, emission_tex=None, emission_strength=1.0,
             normal_tex=None, normal_strength=1.0, alpha_clip=None, alpha_blend=False,
             double_sided=False, color_factor=None):
    """A Principled BSDF material the glTF exporter understands.

    base_tex / emission_tex / normal_tex are image paths (the same path may be used for base and
    emission: one image). alpha_clip=0.5 uses the base texture's alpha as a cut-out (MASK).
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Specular"].default_value = specular
    nodes = {}

    def tex(path, non_color=False, x=-400, y=0):
        k = (path, non_color)
        if k not in nodes:
            n = nt.nodes.new("ShaderNodeTexImage")
            n.image = image(path, non_color)
            n.location = (x, y)
            nodes[k] = n
        return nodes[k]

    if base_tex:
        n = tex(base_tex, y=300)
        if color_factor is not None:
            # glTF baseColorFactor x texture: a MULTIPLY mix with a constant colour
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            mix.inputs[7].default_value = rgba(color_factor)
            nt.links.new(n.outputs["Color"], mix.inputs[6])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
            nt.links.new(n.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha_clip is not None or alpha_blend:
            nt.links.new(n.outputs["Alpha"], bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = rgba(color)
    if emission_tex:
        n = tex(emission_tex, y=0)
        nt.links.new(n.outputs["Color"], bsdf.inputs["Emission"])
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    elif emission is not None:
        bsdf.inputs["Emission"].default_value = rgba(emission)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if normal_tex:
        n = tex(normal_tex, non_color=True, y=-300)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-150, -300)
        nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if alpha_clip is not None:
        mat.blend_method = "CLIP"
        mat.shadow_method = "CLIP"
        mat.alpha_threshold = alpha_clip
    elif alpha_blend:
        mat.blend_method = "BLEND"
    mat.use_backface_culling = not double_sided
    return mat


# ----------------------------------------------------------------------------------------------
# Texture painting (external python with numpy + Pillow + scipy)
# ----------------------------------------------------------------------------------------------

_python = None


def _find_python():
    global _python
    if _python:
        return _python
    candidates = [os.environ.get("HL_PYTHON"), shutil.which("python3"), shutil.which("python"),
                  "/usr/bin/python3"]
    for c in candidates:
        if not c:
            continue
        try:
            r = subprocess.run([c, "-c", "import numpy, PIL, scipy.ndimage"], capture_output=True)
        except OSError:
            continue
        if r.returncode == 0:
            _python = c
            return c
    raise SystemExit("Texture painting needs a python3 with numpy, Pillow and scipy: "
                     "set HL_PYTHON=/path/to/python3")


def paint(painter, params, outputs):
    """Runs tools/blender/<painter> with a JSON params file; returns the output paths.

    `outputs` are file names in .cache/; they are passed to the painter as params["out"].
    Cached: repainted only when the painter source, texlib.py or the params change.
    """
    os.makedirs(CACHE, exist_ok=True)
    outs = {k: os.path.join(CACHE, v) for k, v in outputs.items()}
    params = dict(params, out=outs)
    blob = json.dumps(params, sort_keys=True).encode()
    h = hashlib.sha1(blob)
    for src in (painter, "texlib.py"):
        with open(os.path.join(HERE, src), "rb") as f:
            h.update(f.read())
    stamp = os.path.join(CACHE, os.path.splitext(painter)[0] + "-" + "-".join(sorted(outputs)) + ".stamp")
    digest = h.hexdigest()
    fresh = (os.path.exists(stamp) and open(stamp).read() == digest
             and all(os.path.exists(p) for p in outs.values()))
    if not fresh:
        spec = os.path.join(CACHE, os.path.splitext(painter)[0] + "-" + "-".join(sorted(outputs)) + ".json")
        with open(spec, "wb") as f:
            f.write(blob)
        print(f"[paint] {painter} -> {', '.join(outputs.values())}")
        r = subprocess.run([_find_python(), os.path.join(HERE, painter), spec])
        if r.returncode != 0:
            raise SystemExit(f"painter {painter} failed")
        with open(stamp, "w") as f:
            f.write(digest)
    return outs


# ----------------------------------------------------------------------------------------------
# Mesh building
# ----------------------------------------------------------------------------------------------

class MB:
    """Accumulates vertices and faces with per-corner UVs (UVMap) and optional `along` UVs."""

    def __init__(self, along=False):
        self.verts = []
        self.faces = []
        self.uv = []
        self.uv2 = []
        self.mat = []
        self.along = along

    def v(self, co):
        self.verts.append((float(co[0]), float(co[1]), float(co[2])))
        return len(self.verts) - 1

    def f(self, idx, uv=None, uv2=None, mat=0):
        self.faces.append(tuple(idx))
        self.uv.append(list(uv) if uv else [(0.0, 0.0)] * len(idx))
        self.uv2.append(list(uv2) if uv2 else [(0.0, 0.0)] * len(idx))
        self.mat.append(mat)

    def extend(self, other, mat_offset=0):
        base = len(self.verts)
        self.verts += other.verts
        for f, uv, uv2, m in zip(other.faces, other.uv, other.uv2, other.mat):
            self.f([i + base for i in f], uv, uv2, m + mat_offset)

    def transform(self, M, start=0):
        for i in range(start, len(self.verts)):
            self.verts[i] = tuple(M @ Vector(self.verts[i]))

    def clamp_z(self, z0=0.0, start=0):
        for i in range(start, len(self.verts)):
            x, y, z = self.verts[i]
            if z < z0:
                self.verts[i] = (x, y, z0)

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def object(self, name, materials, origin=(0, 0, 0), smooth=True, auto_smooth=None):
        """Creates the object, its origin (pivot) at `origin` (world)."""
        o = Vector(origin)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(Vector(v) - o) for v in self.verts], [], self.faces)
        uvl = mesh.uv_layers.new(name="UVMap")
        flat = [c for face in self.uv for uv in face for c in uv]
        uvl.data.foreach_set("uv", flat)
        if self.along:
            al = mesh.uv_layers.new(name="along")
            al.data.foreach_set("uv", [c for face in self.uv2 for uv in face for c in uv])
        for m in materials:
            mesh.materials.append(m)
        mesh.polygons.foreach_set("material_index", self.mat)
        mesh.polygons.foreach_set("use_smooth", [smooth] * len(self.faces))
        if auto_smooth is not None:
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = math.radians(auto_smooth)
        mesh.validate(clean_customdata=False)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        obj.location = o
        link(obj)
        return obj


# ----------------------------------------------------------------------------------------------
# Curves and lofts
# ----------------------------------------------------------------------------------------------

def _cr(p0, p1, p2, p3, t, alpha=0.5):
    """Centripetal Catmull-Rom between p1 and p2."""
    def tj(ti, a, b):
        return ti + max((b - a).length, 1e-6) ** alpha
    t0 = 0.0
    t1 = tj(t0, p0, p1)
    t2 = tj(t1, p1, p2)
    t3 = tj(t2, p2, p3)
    t = t1 + (t2 - t1) * t
    a1 = p0 * ((t1 - t) / (t1 - t0)) + p1 * ((t - t0) / (t1 - t0))
    a2 = p1 * ((t2 - t) / (t2 - t1)) + p2 * ((t - t1) / (t2 - t1))
    a3 = p2 * ((t3 - t) / (t3 - t2)) + p3 * ((t - t2) / (t3 - t2))
    b1 = a1 * ((t2 - t) / (t2 - t0)) + a2 * ((t - t0) / (t2 - t0))
    b2 = a2 * ((t3 - t) / (t3 - t1)) + a3 * ((t - t1) / (t3 - t1))
    return b1 * ((t2 - t) / (t2 - t1)) + b2 * ((t - t1) / (t2 - t1))


class Path:
    """A smooth curve through control points, parametrised by arc length."""

    def __init__(self, ctrl, closed=False, res=20):
        pts = [Vector(p) for p in ctrl]
        self.closed = closed
        dense = []
        if len(pts) == 2:
            for i in range(res + 1):
                dense.append(pts[0].lerp(pts[1], i / res))
        else:
            n = len(pts)
            segs = n if closed else n - 1
            for i in range(segs):
                if closed:
                    p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
                else:
                    p1, p2 = pts[i], pts[i + 1]
                    p0 = pts[i - 1] if i > 0 else p1 * 2 - p2
                    p3 = pts[i + 2] if i + 2 < n else p2 * 2 - p1
                for k in range(res):
                    dense.append(_cr(p0, p1, p2, p3, k / res))
            dense.append(pts[0].copy() if closed else pts[-1].copy())
        self.pts = dense
        self.cum = [0.0]
        for a, b in zip(dense, dense[1:]):
            self.cum.append(self.cum[-1] + (b - a).length)
        self.L = self.cum[-1]

    def at(self, s):
        if self.closed:
            s %= self.L
        s = min(max(s, 0.0), self.L)
        i = min(max(bisect.bisect_right(self.cum, s) - 1, 0), len(self.pts) - 2)
        seg = self.cum[i + 1] - self.cum[i]
        f = (s - self.cum[i]) / seg if seg > 1e-12 else 0.0
        return self.pts[i].lerp(self.pts[i + 1], f)

    def tangent(self, s):
        h = max(self.L * 1e-3, 1e-4)
        if self.closed:
            d = self.at(s + h) - self.at(s - h)
        else:
            a, b = max(s - h, 0.0), min(s + h, self.L)
            d = self.at(b) - self.at(a)
        return d.normalized() if d.length > 1e-12 else Vector((0, 0, 1))


def _sgnpow(v, e):
    return math.copysign(abs(v) ** e, v)


def section_point(sec, theta):
    """A point on a (super)elliptic section: x along the frame's binormal, y along its normal."""
    c, s = math.cos(theta), math.sin(theta)
    e = 2.0 / sec.get("p", 2.0)
    x = sec["rx"] * _sgnpow(c, e)
    ry = sec["ry"] if s >= 0 else sec.get("ry2", sec["ry"])
    y = ry * _sgnpow(s, e)
    return x + sec.get("ox", 0.0), y + sec.get("oy", 0.0)


def lerp_keys(keys, t):
    """Piecewise-linear (smoothstepped) interpolation of [(t, value or tuple)] at t."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            f = f * f * (3 - 2 * f)
            if isinstance(a, (tuple, list)):
                return tuple(x + (y - x) * f for x, y in zip(a, b))
            if isinstance(a, dict):
                return {k: a[k] + (b[k] - a[k]) * f for k in a}
            return a + (b - a) * f
    return keys[-1][1]


class Loft:
    """A tube swept along a smooth spine, with domed/flat/open ends.

    section(t) -> {rx, ry, ry2?, p?, ox?, oy?} gives the cross-section at t in [0, 1] along the
    spine. Around the tube a in [0, 1): a = 0 is the frame's -normal side ("bottom"), 0.25 the
    +binormal side, 0.5 the +normal side ("top"). Frames: 'up' keeps the normal as close to `up`
    as possible; 'rmf' is rotation-minimising (starting from `up`).

    The parametric coordinates of every vertex are kept: s (metres along the surface, caps
    included), a (around), t (0..1 along the spine). `nominal` fixes the UV length mapping so
    that several poses of the same part share one texture layout.
    """

    def __init__(self, ctrl, section, *, n=24, seg=0.05, closed=False, frame="up", up=(0, 0, 1),
                 cap0="dome", cap1="dome", cap0_len=None, cap1_len=None, cap_rings=6,
                 extra_t=(), offset=None, twist=0.0, nominal=None, res=24):
        self.path = Path(ctrl, closed=closed, res=res)
        self.section = section
        self.n = n
        self.closed = closed
        self.frame = frame
        self.up = Vector(up).normalized()
        self.offset = offset
        self.twist = twist
        L = self.path.L
        self.L = L
        m = max(2, int(math.ceil(L / seg)))
        uni = [i / m for i in range(m + (0 if closed else 1))]
        extra = sorted(set(round(e, 6) for e in extra_t if 0.0 <= e <= 1.0))
        ts = [u for u in uni if all(abs(u - e) > 0.4 / m for e in extra)] + extra
        if not closed:
            ts = sorted(set([0.0, 1.0] + ts))
        self.ts = sorted(set(round(t, 6) for t in ts))
        self.P = [self.path.at(t * L) for t in self.ts]
        self.T = [self.path.tangent(t * L) for t in self.ts]
        self.N = self._frames()
        # caps
        self.caps = [cap0 if not closed else "open", cap1 if not closed else "open"]
        self.cap_len = [cap0_len, cap1_len]
        self.cap_rings = cap_rings
        for i, tt in ((0, 0.0), (1, 1.0)):
            if self.cap_len[i] is None:
                sec = section(tt)
                self.cap_len[i] = 0.5 * (sec["rx"] + 0.5 * (sec["ry"] + sec.get("ry2", sec["ry"])))
        self.cap_arc = []
        for i, tt in ((0, 0.0), (1, 1.0)):
            sec = section(tt)
            r = 0.5 * (sec["rx"] + 0.5 * (sec["ry"] + sec.get("ry2", sec["ry"])))
            c = self.cap_len[i]
            if self.caps[i] in ("dome", "point"):
                self.cap_arc.append(0.5 * math.pi * math.sqrt((r * r + c * c) / 2))
            elif self.caps[i] == "flat":
                self.cap_arc.append(r)
            else:
                self.cap_arc.append(0.0)
        self.nominal = nominal or self.dims()

    # -- frames --
    def _frames(self):
        N = []
        if self.frame == "up":
            for T in self.T:
                u = self.up - T * self.up.dot(T)
                if u.length < 1e-6:
                    u = Vector((1, 0, 0)) - T * T.x
                N.append(u.normalized())
            return N
        T0 = self.T[0]
        u = self.up - T0 * self.up.dot(T0)
        if u.length < 1e-6:
            u = Vector((1, 0, 0)) - T0 * T0.x
        r = u.normalized()
        N.append(r)
        for i in range(len(self.P) - 1):
            v1 = self.P[i + 1] - self.P[i]
            c1 = v1.dot(v1)
            if c1 < 1e-14:
                N.append(r)
                continue
            rL = r - v1 * (2 / c1 * v1.dot(r))
            tL = self.T[i] - v1 * (2 / c1 * v1.dot(self.T[i]))
            v2 = self.T[i + 1] - tL
            c2 = v2.dot(v2)
            r = rL - v2 * (2 / c2 * v2.dot(rL)) if c2 > 1e-14 else rL
            r = (r - self.T[i + 1] * r.dot(self.T[i + 1])).normalized()
            N.append(r)
        return N

    def frame_at(self, t):
        t = min(max(t, 0.0), 1.0)
        P = self.path.at(t * self.L)
        T = self.path.tangent(t * self.L)
        if self.frame == "up":
            u = self.up - T * self.up.dot(T)
            N = u.normalized()
        else:
            i = min(max(bisect.bisect_right(self.ts, t) - 1, 0), len(self.ts) - 1)
            N = self.N[i] - T * self.N[i].dot(T)
            N.normalize()
        return P, T, N, T.cross(N)

    def dims(self):
        circ = []
        for k in range(33):
            t = k / 32
            sec = self.section(t)
            pts = [section_point(sec, TAU * j / 48) for j in range(48)]
            c = sum(math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]) for j in range(48))
            circ.append(c)
        return {"L": self.L, "c0": self.cap_arc[0], "c1": self.cap_arc[1], "circ": circ,
                "C": max(circ)}

    def total(self):
        nm = self.nominal
        return nm["c0"] + nm["L"] + nm["c1"]

    def s_norm(self, t):
        """Normalised UV length coordinate for spine t (t < 0 / t > 1 inside the caps)."""
        nm = self.nominal
        if t < 0:
            s = nm["c0"] * (1 + t)  # t in [-1, 0) across cap0
        elif t > 1:
            s = nm["c0"] + nm["L"] + nm["c1"] * (t - 1)
        else:
            s = nm["c0"] + nm["L"] * t
        return s / self.total()

    def ring_point(self, i_or_t, a, P=None, T=None, N=None, scale=1.0, tt=None):
        sec = self.section(tt)
        tw = self.twist(tt) if callable(self.twist) else self.twist * tt
        theta = TAU * a - math.pi / 2 + tw
        x, y = section_point(sec, theta)
        if self.offset is not None:
            o = self.offset(tt, a, sec)
            if o:
                ox, oy = sec.get("ox", 0.0), sec.get("oy", 0.0)
                dx, dy = x - ox, y - oy
                d = math.hypot(dx, dy)
                if d > 1e-9:
                    x += dx / d * o
                    y += dy / d * o
        ox, oy = sec.get("ox", 0.0), sec.get("oy", 0.0)
        x = ox + (x - ox) * scale
        y = oy + (y - oy) * scale
        B = T.cross(N)
        return P + B * x + N * y

    def surface(self, t, a, lift=0.0):
        """World point on the surface (spine t in [0,1], around a) and its normal."""
        P, T, N, B = self.frame_at(t)
        p = self.ring_point(None, a, P, T, N, tt=t)
        eps = 1e-3
        pa = self.ring_point(None, a + eps, P, T, N, tt=t)
        t2 = min(t + eps, 1.0) if t < 1.0 else t - eps
        P2, T2, N2, _ = self.frame_at(t2)
        pt = self.ring_point(None, a, P2, T2, N2, tt=t2)
        da = pa - p
        dt = (pt - p) * (1 if t2 > t else -1)
        nrm = dt.cross(da).normalized()
        return p + nrm * lift, nrm

    def surface_ext(self, t, a, lift=0.0):
        """Like surface(), but t < 0 / t > 1 reach over the domed caps (t = -1 / 2 at the poles)."""
        if 0.0 <= t <= 1.0:
            return self.surface(t, a, lift)
        end = 0 if t < 0 else 1
        phi = 0.5 * math.pi * min(-t if t < 0 else t - 1, 0.995)
        i = 0 if end == 0 else len(self.ts) - 1
        P, T, N, tt = self.P[i], self.T[i], self.N[i], self.ts[i]
        sgn = -1 if end == 0 else 1

        def pt(ph, aa):
            c = P + T * (sgn * math.sin(ph) * self.cap_len[end])
            return self.ring_point(None, aa, c, T, N, scale=math.cos(ph), tt=tt)
        p = pt(phi, a)
        da = pt(phi, a + 1e-3) - p
        dp = pt(phi + 1e-3, a) - p
        nrm = (dp.cross(da) * sgn).normalized()
        return p + nrm * lift, nrm

    def build(self, mb, uvmap=None, mat=0, along=False, along_range=(0.0, 1.0)):
        """Adds the tube to `mb`. uvmap(s_norm, a) -> (u, v) (default: identity)."""
        n = self.n
        uvmap = uvmap or (lambda s, a: (s, a))
        rings = []  # (kind, indices or pole index, t_ext)
        # cap0 rings (from the pole outwards)
        def cap_rings(end):
            out = []
            kind = self.caps[end]
            if kind in ("dome", "point"):
                m = self.cap_rings if kind == "dome" else 2
                i = 0 if end == 0 else len(self.ts) - 1
                P, T, N = self.P[i], self.T[i], self.N[i]
                tt = self.ts[i]
                sgn = -1 if end == 0 else 1
                for j in range(1, m + 1):
                    phi = 0.5 * math.pi * j / m
                    sc = math.cos(phi)
                    c = P + T * (sgn * math.sin(phi) * self.cap_len[end])
                    text = (-(j / m) if end == 0 else 1 + j / m)
                    if j == m:
                        sec = self.section(tt)
                        B = T.cross(N)
                        pole = c + B * sec.get("ox", 0.0) + N * sec.get("oy", 0.0)
                        out.append(("pole", mb.v(pole), text))
                    else:
                        idx = [mb.v(self.ring_point(None, k / n, c, T, N, scale=sc, tt=tt)) for k in range(n)]
                        out.append(("ring", idx, text))
            elif kind == "flat":
                i = 0 if end == 0 else len(self.ts) - 1
                sec = self.section(self.ts[i])
                B = self.T[i].cross(self.N[i])
                c = self.P[i] + B * sec.get("ox", 0.0) + self.N[i] * sec.get("oy", 0.0)
                out.append(("pole", mb.v(c), -1.0 if end == 0 else 2.0))
            return out

        c0 = cap_rings(0)
        rings += list(reversed(c0))
        for i, t in enumerate(self.ts):
            idx = [mb.v(self.ring_point(None, k / n, self.P[i], self.T[i], self.N[i], tt=t)) for k in range(n)]
            rings.append(("ring", idx, t))
        rings += cap_rings(1)
        if self.closed:
            rings.append(("ring", rings[0][1], 1.0))

        a0, a1 = along_range

        def al(t):
            # v = 1 in Blender is v = 0 in glTF (the exporter flips V)
            return (a0 + (a1 - a0) * min(max(t, 0.0), 1.0), 1.0)

        for (k0, i0, t0), (k1, i1, t1) in zip(rings, rings[1:]):
            s0, s1 = self.s_norm(t0), self.s_norm(t1)
            if self.closed and t1 == 1.0 and t0 > t1:
                s1 = 1.0
            for k in range(n):
                ka, kb = k / n, (k + 1) / n
                k2 = (k + 1) % n
                if k0 == "ring" and k1 == "ring":
                    face = (i0[k], i1[k], i1[k2], i0[k2])
                    uv = [uvmap(s0, ka), uvmap(s1, ka), uvmap(s1, kb), uvmap(s0, kb)]
                    uv2 = [al(t0), al(t1), al(t1), al(t0)]
                elif k0 == "pole":
                    face = (i0, i1[k], i1[k2])
                    am = (ka + kb) / 2
                    uv = [uvmap(s0, am), uvmap(s1, ka), uvmap(s1, kb)]
                    uv2 = [al(t0), al(t1), al(t1)]
                else:
                    face = (i0[k], i1, i0[k2])
                    am = (ka + kb) / 2
                    uv = [uvmap(s0, ka), uvmap(s1, am), uvmap(s0, kb)]
                    uv2 = [al(t0), al(t1), al(t0)]
                mb.f(face, uv, uv2 if along else None, mat)
        return mb


# ----------------------------------------------------------------------------------------------
# Inflatable panel seams (shared with tex_inflatable.py, which paints the same layout)
# ----------------------------------------------------------------------------------------------

def panel_layout(long_seams, ring_seams):
    """long_seams: sorted a values in [0,1); ring_seams: one list of spine-t values per band
    (band i lies between long_seams[i] and long_seams[i+1], wrapping), or one list for all."""
    if long_seams and ring_seams and not isinstance(ring_seams[0], (list, tuple)):
        ring_seams = [list(ring_seams)] * len(long_seams)
    return {"long": list(long_seams), "bands": [sorted(b) for b in ring_seams]}


def panel_coords(layout, loft_dims, t, a):
    """Distances (metres) to the nearest ring seam and long seam, and the half-sizes of the
    panel: (d_ring, h_ring, d_long, h_long)."""
    L = loft_dims["L"]
    longs = layout["long"]
    circ = lerp_circ(loft_dims["circ"], min(max(t, 0.0), 1.0))
    if t < 0 or t > 1:
        phi = 0.5 * math.pi * min(-t if t < 0 else t - 1, 1.0)
        circ = max(circ * math.cos(phi), 1e-3)
    if longs:
        nb = len(longs)
        band = nb - 1
        for i in range(nb):
            lo = longs[i]
            hi = longs[(i + 1) % nb] + (1.0 if i == nb - 1 else 0.0)
            aa = a if a >= lo else a + 1.0
            if lo <= aa < hi:
                band = i
                break
        lo = longs[band]
        hi = longs[(band + 1) % nb] + (1.0 if band == nb - 1 else 0.0)
        aa = a if a >= lo else a + 1.0
        d_long = min(aa - lo, hi - aa) * circ
        h_long = 0.5 * (hi - lo) * circ
        rs = layout["bands"][band] if layout["bands"] else []
    else:
        d_long, h_long, rs = 1e9, 1e9, []
    # ring seams always include the cap boundaries t=0 and t=1
    pos = t * L
    seams = sorted(set([0.0, 1.0] + list(rs)))
    best, h = 1e9, 1e9
    for s0, s1 in zip(seams, seams[1:]):
        if s0 * L - 1e-9 <= pos <= s1 * L + 1e-9:
            best = min(pos - s0 * L, s1 * L - pos)
            h = 0.5 * (s1 - s0) * L
            break
    else:
        # inside a cap: distance to the cap boundary, half-size = cap arc
        if t < 0:
            best, h = abs(t) * loft_dims["c0"], loft_dims["c0"]
        else:
            best, h = (t - 1) * loft_dims["c1"], loft_dims["c1"]
    return best, h, d_long, h_long


def lerp_circ(circ, t):
    x = t * (len(circ) - 1)
    i = min(int(x), len(circ) - 2)
    f = x - i
    return circ[i] * (1 - f) + circ[i + 1] * f


def pillow(x):
    x = min(max(x, 0.0), 1.0)
    return 1.0 - (1.0 - x) ** 2


def puff_offset(layout, dims, depth=0.12, cap=0.05):
    """An `offset` callback for Loft: panels bulge, seams pinch in."""
    def off(t, a, sec):
        dr, hr, dl, hl = panel_coords(layout, dims, t, a)
        P = pillow(dr / max(hr, 1e-6)) * pillow(dl / max(hl, 1e-6))
        h = min(hr, hl, 0.6)
        amp = min(depth * h, cap)
        return amp * (P - 0.6)
    return off


# ----------------------------------------------------------------------------------------------
# Atlas packing
# ----------------------------------------------------------------------------------------------

class Atlas:
    """Packs rectangular parametric islands (length x circumference, metres) into one texture."""

    def __init__(self, size=2048, pad=6):
        self.size = size
        self.pad = pad
        self.items = {}
        self.rects = {}

    def add(self, name, w_m, h_m):
        self.items[name] = (w_m, h_m)

    def pack(self):
        S, pad = self.size, self.pad
        lo, hi = 1.0, 4000.0
        best = None
        for _ in range(40):
            d = (lo + hi) / 2
            r = self._shelf(d)
            if r is None:
                hi = d
            else:
                lo, best = d, r
        self.density = lo
        self.rects = best
        return best

    def _shelf(self, d):
        S, pad = self.size, self.pad
        items = sorted(self.items.items(), key=lambda kv: -kv[1][1])
        x = y = 0
        shelf_h = 0
        rects = {}
        for name, (w, h) in items:
            pw, ph = int(math.ceil(w * d)) + 2 * pad, int(math.ceil(h * d)) + 2 * pad
            if pw > S:
                return None
            if x + pw > S:
                x = 0
                y += shelf_h
                shelf_h = 0
            if y + ph > S:
                return None
            rects[name] = (x + pad, y + pad, pw - 2 * pad, ph - 2 * pad)
            x += pw
            shelf_h = max(shelf_h, ph)
        return rects

    def mapper(self, name):
        x, y, w, h = self.rects[name]
        S = self.size

        def m(s, a):
            return ((x + s * w) / S, 1.0 - (y + a * h) / S)
        return m


# ----------------------------------------------------------------------------------------------
# Small primitives
# ----------------------------------------------------------------------------------------------

def box(mb, center, size, uv_scale=1.0, mat=0, M=None):
    """An axis-aligned box (optionally transformed by matrix M) with box-projected UVs (metres)."""
    cx, cy, cz = center
    sx, sy, sz = (s / 2 for s in size)
    corners = [Vector((cx + dx * sx, cy + dy * sy, cz + dz * sz))
               for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    if M is not None:
        corners = [M @ c for c in corners]
    idx = [mb.v(c) for c in corners]

    def I(dx, dy, dz):
        return idx[(dx > 0) * 4 + (dy > 0) * 2 + (dz > 0)]
    faces = [
        ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1), "x"),
        ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1), "x"),
        ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), "y"),
        ((-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1), "y"),
        ((-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1), "z"),
        ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), "z"),
    ]
    for *cs, ax in faces:
        uv = []
        for c in cs:
            px, py, pz = c[0] * sx, c[1] * sy, c[2] * sz
            if ax == "x":
                uv.append((py * uv_scale, pz * uv_scale))
            elif ax == "y":
                uv.append((px * uv_scale, pz * uv_scale))
            else:
                uv.append((px * uv_scale, py * uv_scale))
        mb.f([I(*c) for c in cs], uv, None, mat)


def grid_patch(mb, fn, nu, nv, uvmap=None, mat=0, closed_u=False, outward=None):
    """A quad grid from fn(u, v) -> point, u,v in [0,1]. If `outward` (a vector, or fn(u, v) ->
    vector) is given, the faces are wound so that their normals point that way."""
    uvmap = uvmap or (lambda u, v: (u, v))
    cols = nu if closed_u else nu + 1
    idx = [[mb.v(fn(i / nu, j / nv)) for j in range(nv + 1)] for i in range(cols)]
    flip = False
    if outward is not None:
        i0, j0 = nu // 2, nv // 2
        a = Vector(mb.verts[idx[i0][j0]])
        b = Vector(mb.verts[idx[i0 + 1][j0]])
        c = Vector(mb.verts[idx[i0][j0 + 1]])
        n = (b - a).cross(c - a)
        o = outward((i0 + 0.5) / nu, (j0 + 0.5) / nv) if callable(outward) else Vector(outward)
        flip = n.dot(o) < 0
    for i in range(nu):
        i2 = (i + 1) % cols if closed_u else i + 1
        for j in range(nv):
            f = [idx[i][j], idx[i2][j], idx[i2][j + 1], idx[i][j + 1]]
            uv = [uvmap(i / nu, j / nv), uvmap((i + 1) / nu, j / nv),
                  uvmap((i + 1) / nu, (j + 1) / nv), uvmap(i / nu, (j + 1) / nv)]
            if flip:
                f.reverse()
                uv.reverse()
            mb.f(f, uv, None, mat)
    return idx


# ----------------------------------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------------------------------

def tri_count(obj):
    me = obj.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


def export(name):
    """Exports the whole scene to public/models/<name>.glb and prints a summary."""
    os.makedirs(MODELS, exist_ok=True)
    path = os.path.join(MODELS, name + ".glb")
    for o in list(bpy.context.scene.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=False, export_apply=True,
        export_yup=True, export_cameras=False, export_lights=False, export_animations=False,
        export_extras=False, export_colors=False, export_texcoords=True, export_normals=True,
        export_tangents=False, export_image_format="AUTO")
    tris = sum(tri_count(o) for o in bpy.context.scene.objects if o.type == "MESH")
    size = os.path.getsize(path)
    print(f"[export] {path}  {size / 1024:.0f} KB  {tris} tris")
    return path


def seeded(seed):
    return random.Random(seed)


# ----------------------------------------------------------------------------------------------
# Pumpkins and gourds
# ----------------------------------------------------------------------------------------------

def pumpkin_surface(center, rx, rz, ribs=10, groove=0.10, groove_sharp=0.35, top_dimple=0.22,
                    bottom_dimple=0.10, ry=None, M=None, wobble=0.0, seed=0, fullness=0.85,
                    rib_phase=0.0, profile=None, **_ignored):
    """The surface function point(u, v) of pumpkin() with the same parameters."""
    ry = rx if ry is None else ry
    rng = random.Random(seed)
    lobe_amp = [1.0 + wobble * (rng.random() * 2 - 1) for _ in range(ribs)]
    C = Vector(center)
    M = M or Matrix.Identity(3)
    if hasattr(M, "to_3x3"):
        M = M.to_3x3()

    def point(u, v):
        th = TAU * u
        ph = math.pi * v
        sp = math.sin(ph)
        # lobes: broad and round, grooves narrow
        x = (ribs * th / 2 + rib_phase) % math.pi
        sgr = abs(math.sin(x))
        k = int(((u * ribs) + 0.5) % ribs)
        lobe = (1 - groove * (1 - sgr ** groove_sharp)) * lobe_amp[k]
        rr = sp ** fullness
        z = -math.cos(ph)
        # dimples where stem and blossom end sit
        if v > 1 - 0.18:
            f = (v - (1 - 0.18)) / 0.18
            z -= top_dimple * f * f * 1.6
        if v < 0.14:
            f = (0.14 - v) / 0.14
            z += bottom_dimple * f * f * 1.6
        if profile:
            ps, pz = profile(v)
            rr *= ps
            z *= pz
        p = Vector((math.cos(th) * rx * rr * lobe, math.sin(th) * ry * rr * lobe, z * rz))
        return C + M @ p
    return point


def surface_normal(point, u, v, eps=1e-3):
    """Outward normal of a (u around, v up) surface function like pumpkin_surface()."""
    p = point(u, v)
    du = point(u + eps, v) - p
    dv = point(u, min(v + eps, 1.0)) - point(u, max(v - eps, 0.0))
    n = du.cross(dv)
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))


def pumpkin(mb, center, rx, rz, ribs=10, nu=None, nv=24, uvmap=None, mat=0, **kw):
    """A ribbed pumpkin/gourd. UV: u = longitude (rib k's groove at u = k/ribs), v = latitude
    (0 bottom pole, 1 top pole). M (Matrix) orients it (applied about `center`).
    profile(v) -> (radius scale, z scale) can reshape it (e.g. a long squash).
    Other keywords: see pumpkin_surface(). Returns the top (stem) point."""
    point = pumpkin_surface(center, rx, rz, ribs=ribs, **kw)
    nu = nu or ribs * 6
    rows = []
    for j in range(nv + 1):
        v = j / nv
        if j == 0 or j == nv:
            rows.append([mb.v(point(0, v))])
        else:
            rows.append([mb.v(point(i / nu, v)) for i in range(nu)])
    uvmap = uvmap or (lambda u, v: (u, v))
    for j in range(nv):
        v0, v1 = j / nv, (j + 1) / nv
        for i in range(nu):
            u0, u1 = i / nu, (i + 1) / nu
            i2 = (i + 1) % nu
            if j == 0:
                mb.f((rows[0][0], rows[1][i2], rows[1][i]),
                     [uvmap((u0 + u1) / 2, v0), uvmap(u1, v1), uvmap(u0, v1)], None, mat)
            elif j == nv - 1:
                mb.f((rows[j][i], rows[j][i2], rows[nv][0]),
                     [uvmap(u0, v0), uvmap(u1, v0), uvmap((u0 + u1) / 2, v1)], None, mat)
            else:
                mb.f((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]),
                     [uvmap(u0, v0), uvmap(u1, v0), uvmap(u1, v1), uvmap(u0, v1)], None, mat)
    top = point(0, 1.0)
    return top


def curl(start, direction, plane_normal, length, r0, r1, step=0.04, sense=1):
    """Points of a curling spiral: starts at `start` heading `direction`, turning about
    `plane_normal` (sense +1/-1) with a radius shrinking from r0 to r1."""
    P = Vector(start)
    D = Vector(direction).normalized()
    n = Vector(plane_normal).normalized()
    pts = []
    s = 0.0
    while s < length:
        f = s / length
        R = r0 * (r1 / r0) ** f
        ang = sense * step / R
        D = (Matrix.Rotation(ang, 3, n) @ D).normalized()
        P = P + D * step
        s += step
        pts.append(P.copy())
    return pts


def metaball_mesh(elements, resolution=0.06, threshold=0.6):
    """Builds a mesh object from metaball elements [(type, co, radius, size(xyz) or None,
    rotation quaternion or None, negative)] and returns it (converted, metaball removed)."""
    mb = bpy.data.metaballs.new("mb")
    mb.resolution = resolution
    mb.render_resolution = resolution
    mb.threshold = threshold
    for typ, co, radius, size, rot, neg in elements:
        e = mb.elements.new(type=typ)
        e.co = co
        e.radius = radius
        if size is not None:
            e.size_x, e.size_y, e.size_z = size
        if rot is not None:
            e.rotation = rot
        e.use_negative = neg
    obj = bpy.data.objects.new("mb", mb)
    link(obj)
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.scene.objects:
        o.select_set(o == obj)
    bpy.ops.object.convert(target="MESH")
    out = bpy.context.view_layer.objects.active
    return out


def beam(mb, center, size, M=None, chamfer=0.004, uv=None, mat=0):
    """A chamfered box (timber): size = (length x, width y, height z) in its local frame, M an
    optional 3x3 rotation. uv(face_axis, x, y) -> (u, v) maps local face coordinates in metres
    (x runs along the length on the long faces)."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if chamfer > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=chamfer, segments=1, affect="EDGES",
                        profile=0.5, clamp_overlap=True)
    R = (M.to_3x3() if hasattr(M, "to_3x3") else M) if M is not None else Matrix.Identity(3)
    C = Vector(center)
    hx, hy, hz = (v / 2 for v in size)
    base = len(mb.verts)
    for v in bm.verts:
        mb.v(C + R @ v.co)
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        uvs = []
        for v in f.verts:
            x, y, z = v.co
            if ax == 0:
                fx, fy = y, z
            elif ax == 1:
                fx, fy = x, z
            else:
                fx, fy = x, y
            uvs.append(uv(ax, fx, fy) if uv else (fx, fy))
        mb.f([base + v.index for v in f.verts], uvs, None, mat)
    bm.free()


def lump(mb, center, radius, scale=(1, 1, 1), seed=0, rough=0.25, nu=10, nv=6, M=None, uvmap=None,
         mat=0, flat_bottom=True):
    """A lumpy blob (snow clumps, moss): a noise-displaced sphere, optionally flattened below."""
    from mathutils import noise as mn
    R = (M.to_3x3() if hasattr(M, "to_3x3") else M) if M is not None else Matrix.Identity(3)
    C = Vector(center)
    off = Vector((seed * 1.37, seed * 2.11, seed * 0.73))
    uvmap = uvmap or (lambda u, v: (u, v))

    def point(u, v):
        th, ph = TAU * u, math.pi * v
        d = Vector((math.cos(th) * math.sin(ph), math.sin(th) * math.sin(ph), -math.cos(ph)))
        r = radius * (1 + rough * mn.noise(d * 1.8 + off) + 0.5 * rough * mn.noise(d * 4.0 + off))
        p = Vector((d.x * scale[0], d.y * scale[1], d.z * scale[2])) * r
        if flat_bottom and p.z < -0.15 * radius * scale[2]:
            p.z = -0.15 * radius * scale[2] + (p.z + 0.15 * radius * scale[2]) * 0.15
        return C + R @ p
    rows = []
    for j in range(nv + 1):
        v = j / nv
        rows.append([mb.v(point(0, v))] if j in (0, nv) else [mb.v(point(i / nu, v)) for i in range(nu)])
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            u0, u1, v0, v1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
            if j == 0:
                mb.f((rows[0][0], rows[1][i2], rows[1][i]), [uvmap(u0, v0), uvmap(u1, v1), uvmap(u0, v1)], None, mat)
            elif j == nv - 1:
                mb.f((rows[j][i], rows[j][i2], rows[nv][0]), [uvmap(u0, v0), uvmap(u1, v0), uvmap(u0, v1)], None, mat)
            else:
                mb.f((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]),
                     [uvmap(u0, v0), uvmap(u1, v0), uvmap(u1, v1), uvmap(u0, v1)], None, mat)


def extrude_loops(mb, loops, thickness, uv_face, uv_edge=None, mat=0, edge_mat=None):
    """A flat board cut along outline loops in the x-z plane, `thickness` deep along y (centred).

    loops: [{"pts": [[x, z], ...], "hole": bool}, ...] (as traced by OpenCV). uv_face(x, z) gives
    the front and back faces' UVs (the back mirrors nothing: it reads the same art), uv_edge(x, z)
    the edge band's (default: the same as the faces)."""
    from mathutils import geometry
    uv_edge = uv_edge or uv_face
    edge_mat = mat if edge_mat is None else edge_mat
    vecs = [[Vector((p[0], p[1], 0.0)) for p in l["pts"]] for l in loops]
    tris = geometry.tessellate_polygon(vecs)
    flat = [p for l in loops for p in l["pts"]]
    yf, yb = -thickness / 2, thickness / 2
    front = [mb.v((x, yf, z)) for x, z in flat]
    back = [mb.v((x, yb, z)) for x, z in flat]
    for a, b, c in tris:
        pa, pb, pc = flat[a], flat[b], flat[c]
        cross = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
        if cross < 0:   # counter-clockwise in (x, z): the normal faces -Y (the front)
            b, c = c, b
            pb, pc = pc, pb
        mb.f((front[a], front[b], front[c]), [uv_face(*pa), uv_face(*pb), uv_face(*pc)], None, mat)
        mb.f((back[a], back[c], back[b]), [uv_face(*pa), uv_face(*pc), uv_face(*pb)], None, mat)
    k = 0
    for l in loops:
        pts = l["pts"]
        n = len(pts)
        area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
        outward_left = (area > 0) != bool(l["hole"])
        for i in range(n):
            j = (i + 1) % n
            fi, fj, bi, bj = front[k + i], front[k + j], back[k + i], back[k + j]
            ui, uj = uv_edge(*pts[i]), uv_edge(*pts[j])
            if outward_left:
                mb.f((fi, bi, bj, fj), [ui, ui, uj, uj], None, edge_mat)
            else:
                mb.f((fi, fj, bj, bi), [ui, uj, uj, ui], None, edge_mat)
        k += n
    return mb
