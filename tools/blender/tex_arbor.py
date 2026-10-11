# SPDX-License-Identifier: MIT
"""Paints the arbor's textures (used by arbor.py). All tile seamlessly.

timber  1024 x 1024 (+ normal map): dark weathered, stained timber; u along the grain
        (1 tile = 2 m), v across (1 tile = 0.5 m). Checks (drying cracks) and grey weathering.
cedar   512 x 1024 (+ normal map): a rough split cedar post, u around, v along (1 tile = 1.6 m):
        silver-grey weathered wood with stringy remnants of red-brown bark.
"""

import numpy as np

import texlib as T

sp = T.spec()


def timber():
    H, W = 1024, 1024
    grain = T.fbm((H, W), (64, 4), 5, seed=1)
    fine = T.fbm((H, W), (256, 8), 3, seed=2)
    blot = T.fbm((H, W), (8, 4), 4, seed=3)
    c = T.mix(T.hexrgb("#2a221c"), T.hexrgb("#5a4a3c"), 0.55 * grain + 0.25 * fine + 0.2 * blot)
    weather = T.smoothstep(0.5, 0.8, T.fbm((H, W), (10, 6), 4, seed=4))
    c = T.mix(c, T.hexrgb("#6e675e"), weather * 0.45)
    # checks: thin dark cracks along the grain
    ck = np.abs(T.fbm((H, W), (24, 2), 4, seed=5) - 0.5)
    run = T.smoothstep(0.45, 0.65, T.fbm((H, W), (24, 3), 3, seed=6))
    checks = T.smoothstep(0.012, 0.0, ck) * run
    c = c * (1 - 0.75 * checks[..., None])
    T.save(c, sp["out"]["timber"], quality=88)
    h = 0.5 * grain + 0.3 * fine - 0.9 * checks
    T.save(T.normal_from_height(h, strength=4.0)[::2, ::2], sp["out"]["timber_n"], quality=90)


def cedar():
    H, W = 1024, 512
    streak = T.fbm((H, W), (6, 40), 5, seed=11)
    fine = T.fbm((H, W), (24, 160), 3, seed=12)
    c = T.mix(T.hexrgb("#5e5650"), T.hexrgb("#a49a8e"), 0.6 * streak + 0.4 * fine)
    bark = T.smoothstep(0.55, 0.7, T.fbm((H, W), (10, 12), 4, seed=13))
    stringy = 0.6 + 0.4 * T.fbm((H, W), (40, 220), 2, seed=14)
    c = T.mix(c, T.hexrgb("#5a3a2a") * stringy[..., None], bark * 0.55)
    gro = np.abs(T.fbm((H, W), (4, 30), 4, seed=15) - 0.5)
    grooves = T.smoothstep(0.02, 0.0, gro)
    c = c * (1 - 0.6 * grooves[..., None])
    T.save(c, sp["out"]["cedar"], quality=88)
    h = 0.4 * streak + 0.3 * fine + 0.5 * bark - 0.8 * grooves
    T.save(T.normal_from_height(h, strength=5.0)[::2, ::2], sp["out"]["cedar_n"], quality=90)


timber()
cedar()
