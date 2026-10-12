# SPDX-License-Identifier: MIT
"""Paints the textures of the giant Venus flytrap (venus-flytrap.py; reference/venus-flytrap.jpg).

kinds (params["kind"]):

- "trap": 1024 x 1024 base + 512 x 512 emission, three regions shared by three materials:
    outer (rows 0-511): a lobe's outside, u = angle round the half-disc (0 and 1 on the hinge),
      v = from the hinge's middle (v = 0, top of the region) to the rim (v = 1): soft teal-green
      with darker grooves between eight segments radiating from the hinge, lighter toward the
      rim; emission a dim copy (it is lit by green LEDs).
    inner (rows 512-895): the inside, same mapping: deep red, darker veins, three trigger hairs
      on each segment; emission a strong red.
    teeth (rows 896-1023): u along a tooth (base -> tip), v round it: pale pink at the base to
      cream at the tip; dim emission.
- "plant": 1024 x 1024: stem (rows 0-255; u along, v round: green with pale streaks) and leaf
  (rows 256-767; u along the blade from the base, v across: a green blade, pale midrib and
  veins, reddish toward the base). Rows 768-1023: the bare midrib green (the trap's hinge).
- "fly": 512 x 512 RGBA: body (rows 0-255; u round, v along: glossy black with a blue-green
  sheen, segment rings, bristle specks), eyes (256-511 x 0-255: dark red facets) and the wing
  (256-511 x 256-511: smoky translucent membrane, alpha ~0.3, with dark veins).
"""

import math

import numpy as np

import texlib as T


def out(sp, kind):
    for k, v in sp["out"].items():
        if k == kind or k.startswith(kind + "_"):
            return v
    raise KeyError(kind)


def grid(h, w):
    y, x = np.mgrid[0:h, 0:w]
    return (x + 0.5) / w, (y + 0.5) / h


def trap(sp):
    S = 1024
    img = np.zeros((S, S, 3))
    em = np.zeros((S, S, 3))
    segs = sp.get("segments", 8)
    # outer
    u, v = grid(512, S)
    f = (u * segs) % 1.0
    groove = np.exp(-(np.minimum(f, 1 - f) / 0.06) ** 2) * T.smoothstep(0.05, 0.25, v)
    n = T.fbm((512, S), (8, 24), 4, seed=3)
    fine = T.fbm((512, S), (60, 120), 3, seed=4)
    teal = T.hexrgb("#4f8f84")
    col = teal * (0.80 + 0.25 * v[..., None] + 0.14 * (n[..., None] - 0.5) + 0.08 * (fine[..., None] - 0.5))
    col = T.mix(col, T.hexrgb("#24524a"), 0.65 * groove[..., None])
    col = T.mix(col, T.hexrgb("#7fb8a8"), 0.35 * T.smoothstep(0.85, 1.0, v)[..., None])
    img[:512] = col
    em[:512] = col * 0.30
    # inner
    u, v = grid(384, S)
    f = (u * segs) % 1.0
    n = T.fbm((384, S), (8, 24), 4, seed=5)
    red = T.hexrgb("#c4161a") * (0.82 + 0.25 * (n[..., None] - 0.5))
    vein = np.exp(-(np.minimum(f, 1 - f) / 0.03) ** 2) * T.smoothstep(0.05, 0.3, v)
    vein2 = np.exp(-((((u * segs * 3) % 1.0) - 0.5) / 0.04) ** 2) * T.smoothstep(0.3, 0.6, v) * 0.6
    col = T.mix(red, T.hexrgb("#6a080c"), np.clip(vein + vein2, 0, 1)[..., None] * 0.6)
    col = T.mix(col, T.hexrgb("#ff4a3a"), 0.4 * T.smoothstep(0.8, 1.0, v)[..., None])     # paler toward the rim
    rng = np.random.default_rng(6)
    for k in range(segs):
        for j in range(3):
            cu = (k + 0.25 + 0.25 * j) / segs + rng.uniform(-0.01, 0.01)
            cv = rng.uniform(0.35, 0.6)
            d = np.hypot((u - cu) * S, (v - cv) * 384)
            col = np.where((d < 4)[..., None], T.hexrgb("#3a0406"), col)
    img[512:896] = col
    em[512:896] = col * 0.95
    # teeth
    u, v = grid(128, S)
    tooth = T.mix(T.hexrgb("#e8a8a0"), T.hexrgb("#f4ead6"), T.smoothstep(0.0, 0.6, u)[..., None])
    n = T.fbm((128, S), (4, 40), 3, seed=7)
    tooth = tooth * (0.9 + 0.15 * (n[..., None] - 0.5)) * (0.85 + 0.15 * np.cos(v * 2 * np.pi)[..., None] ** 2)
    img[896:] = tooth
    em[896:] = tooth * 0.18
    T.save(np.clip(img, 0, 1), out(sp, "base"), quality=90)
    T.save(np.clip(em.reshape(512, 2, 512, 2, 3).mean(axis=(1, 3)), 0, 1), out(sp, "emit"), quality=90)


def plant(sp):
    S = 1024
    img = np.zeros((S, S, 3))
    u, v = grid(256, S)
    n = T.fbm((256, S), (24, 4), 4, seed=11)
    streak = T.fbm((256, S), (60, 3), 3, seed=12)
    stem = T.hexrgb("#3e6e3a") * (0.8 + 0.25 * (n[..., None] - 0.5) + 0.25 * (streak[..., None] - 0.5))
    img[:256] = stem
    u, v = grid(512, S)
    x = (v - 0.5) * 2                                    # across the blade
    n = T.fbm((512, S), (16, 32), 4, seed=13)
    blade = T.hexrgb("#4a8a38") * (0.82 + 0.2 * (1 - np.abs(x[..., None])) + 0.15 * (n[..., None] - 0.5))
    mid = np.exp(-(x / 0.03) ** 2)
    veins = np.exp(-((((u * 14 - np.abs(x) * 2.5) % 1.0) - 0.5) / 0.05) ** 2) * (np.abs(x) > 0.05) * 0.5
    blade = T.mix(blade, T.hexrgb("#a8d088"), np.clip(mid + veins * 0.5, 0, 1)[..., None])
    blade = T.mix(blade, T.hexrgb("#8a3a2a"), 0.45 * T.smoothstep(0.25, 0.0, u)[..., None])
    edge = T.smoothstep(0.9, 1.0, np.abs(x))
    blade = T.mix(blade, T.hexrgb("#2a5a22"), 0.5 * edge[..., None])
    img[256:768] = blade
    u, v = grid(256, S)
    n = T.fbm((256, S), (8, 40), 3, seed=14)
    img[768:] = T.hexrgb("#3a6a52") * (0.8 + 0.3 * (n[..., None] - 0.5))
    T.save(np.clip(img, 0, 1), out(sp, "tex"), quality=88)


def fly(sp):
    S = 512
    img = np.zeros((S, S, 4))
    img[..., 3] = 1.0
    u, v = grid(256, S)
    n = T.fbm((256, S), (16, 32), 3, seed=21)
    base = T.hexrgb("#141418") * (0.8 + 0.4 * n[..., None])
    sheen = 0.5 + 0.5 * np.sin(u * 2 * np.pi * 2 + v * 3)
    base = base + np.array([0.02, 0.06, 0.07]) * sheen[..., None]
    rings = np.exp(-((((v * 7) % 1.0) - 0.5) / 0.08) ** 2) * T.smoothstep(0.0, 0.45, v) * T.smoothstep(0.6, 0.45, v)
    base = base * (1 - 0.5 * rings[..., None])
    rng = np.random.default_rng(22)
    sp_ = rng.random((256, S)) > 0.985
    base = np.where(sp_[..., None], T.hexrgb("#3a3a40"), base)
    img[:256, :, :3] = base
    # eyes: dark red facets
    u, v = grid(256, 256)
    hx = (u * 40 + (np.floor(v * 40) % 2) * 0.5) % 1.0
    hy = (v * 40) % 1.0
    facet = np.hypot(hx - 0.5, hy - 0.5)
    eye = T.hexrgb("#7a1a12") * (0.75 + 0.35 * (0.5 - facet[..., None]))
    hl = np.exp(-((u - 0.35) ** 2 + (v - 0.3) ** 2) / 0.01)
    eye = eye + hl[..., None] * 0.35
    img[256:, :256, :3] = np.clip(eye, 0, 1)
    # wing: membrane with veins, alpha
    u, v = grid(256, 256)
    X, Y = u * 2 - 1, v * 2 - 1
    inside = (X / 0.98) ** 2 + (Y / 0.98) ** 2 < 1
    veins = np.zeros_like(X, bool)
    for k in range(6):
        a = -0.6 + 0.24 * k
        d = np.abs(np.sin(a) * (X + 1) - np.cos(a) * Y) / 1.0
        veins |= (d < 0.018 + 0.01 * (1 - (X + 1) / 2)) & inside
    for c in (-0.2, 0.3):
        veins |= (np.abs(np.hypot(X + 1, Y) - (1.2 + c)) < 0.015) & inside
    col = np.where(veins[..., None], T.hexrgb("#1a1a1e"), T.hexrgb("#9aa4b0"))
    a = np.where(veins, 0.9, 0.28) * inside
    img[256:, 256:, :3] = col
    img[256:, 256:, 3] = a
    T.save(np.clip(img, 0, 1), out(sp, "tex"))


KINDS = {"trap": trap, "plant": plant, "fly": fly}


def main():
    sp = T.spec()
    KINDS[sp["kind"]](sp)


main()
