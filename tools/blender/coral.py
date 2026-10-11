# SPDX-License-Identifier: MIT
"""Painted cut-out coral boards for the Deep (reference/jellyfish-path.jpg).

    blender -b --factory-startup -P tools/blender/coral.py

Writes public/models/coral-1.glb (orange staghorn, ~1.0 m), coral-2.glb (pink candelabra,
~1.25 m) and coral-3.glb (lime kelp, ~1.0 m): 2 cm plywood boards cut to shape, standing in the
ground, facing the front (-Y in Blender, +Z in glTF). One material, `glow_uvpaint`, whose
emissive map is the fluorescent paint (the engine scales it under the Deep's black light).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import MB  # noqa: E402

S = 1024


def main():
    lib.reset()
    tex = lib.paint("tex_coral.py", {"seed": 5}, {"outline": "coral.json", "atlas": "coral.jpg", "atlas_e": "coral-e.jpg"})
    with open(tex["outline"]) as f:
        data = json.load(f)
    for name, d in data.items():
        lib.reset()
        mat = lib.material("glow_uvpaint", base_tex=tex["atlas"], emission_tex=tex["atlas_e"], roughness=0.6,
                           specular=0.35)
        x0, x1, z0, z1 = d["box"]
        rx, ry, rw, rh = d["rect"]
        sc = rw / (x1 - x0)

        def uv(x, z):
            return ((rx + (x - x0) * sc) / S, 1.0 - (ry + (z1 - z) * sc) / S)
        mb = lib.extrude_loops(MB(), d["loops"], 0.02, uv, mat=0)
        o = mb.object(name, [mat], origin=(0, 0, 0), auto_smooth=30)
        print(f"  {name}: {lib.tri_count(o)} tris, {x1 - x0:.2f} x {z1:.2f} m")
        lib.export(name)


main()
