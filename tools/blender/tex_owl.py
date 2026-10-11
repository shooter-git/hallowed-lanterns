# SPDX-License-Identifier: MIT
"""Paints the textures of the pumpkin owl and the pumpkin guitar (owl.py, guitar.py).

kinds:
- "eyes": 512 x 512. Left half (0..255): the carved eye socket seen face-on (glowing cream
  flesh, warmer toward a peach rim, the knife-cut fibres). Top right (256..511, rows 0..255):
  the teal pupil dome with a highlight. Bottom right: lime (rows 256..383) and teal-green
  (rows 384..511) for the beak, the ear tufts and the stem (used by glow_uv on its own too).
- "ivy": 1024 x 1024 tileable dark ivy (base + normal): overlapping three/five-lobed leaves
  of several greens with pale veins over dark gaps.
- "feather": 512 x 256: one feather cut-out shaded along u (base -> tip) and across v: pale
  blue middle, teal toward the edges, a pale shaft and fine barbs.
"""

import math

import numpy as np

import texlib as T


def out(sp, kind):
    """The output path for `kind` ("tex", "base", "color", ...): the key itself or kind_<name>
    (callers give each texture its own key so that lib.paint's cache stamps don't collide)."""
    for k, v in sp["out"].items():
        if k == kind or k.startswith(kind + "_"):
            return v
    raise KeyError(kind)


def grid(h, w):
    y, x = np.mgrid[0:h, 0:w]
    return (x + 0.5) / w, (y + 0.5) / h


def eyes(sp):
    S = 512
    img = np.zeros((S, S, 3))
    u, v = grid(S, 256)
    x, y = u * 2 - 1, v * 2 - 1
    r = np.hypot(x, y)
    n = T.fbm((S, 256), (40, 10), 3, seed=3)
    cream = T.hexrgb("#ffe8b8")
    peach = T.hexrgb("#ffb066")
    col = T.mix(cream, peach, T.smoothstep(0.45, 0.95, r)[..., None])
    th = np.arctan2(y, x)
    fib = 0.5 + 0.5 * np.sin(th * 60 + n * 8)
    col = col * (0.9 + 0.1 * fib[..., None]) * (1.0 + 0.08 * (1 - r[..., None]))
    img[:, :256] = np.clip(col, 0, 1)
    u2, v2 = grid(256, 256)
    x2, y2 = u2 * 2 - 1, v2 * 2 - 1
    r2 = np.hypot(x2, y2)
    teal = T.hexrgb("#1fb8b0") * (0.75 + 0.3 * (1 - r2[..., None]))
    hl = np.exp(-((x2 + 0.35) ** 2 + (y2 + 0.4) ** 2) / 0.02)
    teal = teal + hl[..., None] * np.array([0.6, 0.7, 0.7])
    img[:256, 256:] = np.clip(teal, 0, 1)
    nn = T.fbm((128, 256), 8, 3, seed=5)
    img[256:384, 256:] = T.hexrgb("#a6ff3a") * (0.9 + 0.2 * (nn[..., None] - 0.5))
    img[384:512, 256:] = T.hexrgb("#38d6a8") * (0.85 + 0.3 * (nn[..., None] - 0.5))
    T.save(img, out(sp, "tex"), quality=90)


def leaf_mask(X, Y, size, ang, lobes):
    """A three- or five-lobed ivy leaf centred at 0, its tip along angle `ang`."""
    c, s = math.cos(ang), math.sin(ang)
    xr = (X * c + Y * s) / size
    yr = (-X * s + Y * c) / size
    r = np.hypot(xr, yr)
    th = np.arctan2(yr, xr)
    shape = 0.62 + 0.38 * np.abs(np.cos(th * lobes / 2)) ** 1.5
    shape = shape * (1 - 0.25 * (np.cos(th) < -0.6))       # notch at the stalk
    return r < shape, r / np.maximum(shape, 1e-3), th


def ivy(sp):
    S = 1024
    rng = np.random.default_rng(sp.get("seed", 7))
    img = np.zeros((S, S, 3)) + T.hexrgb("#0a140c")
    hgt = np.zeros((S, S))
    greens = [T.hexrgb(c) for c in ("#1f4a24", "#2a5a2a", "#183c1e", "#325f2c", "#24502a")]
    yy, xx = np.mgrid[0:S, 0:S]
    for i in range(1400):
        cx, cy = rng.uniform(0, S), rng.uniform(0, S)
        size = rng.uniform(18, 34)
        R = int(size * 1.1) + 2
        x0, y0 = int(cx) - R, int(cy) - R
        ys = (np.arange(y0, y0 + 2 * R)) % S
        xs = (np.arange(x0, x0 + 2 * R)) % S
        X, Y = np.meshgrid(np.arange(x0, x0 + 2 * R) - cx, np.arange(y0, y0 + 2 * R) - cy)
        m, rr, th = leaf_mask(X, Y, size, rng.uniform(0, 6.28), rng.choice([3, 5]))
        if not m.any():
            continue
        g = greens[rng.integers(len(greens))] * rng.uniform(0.8, 1.15)
        vein = (np.abs(np.sin(th * rng.choice([3, 5]) / 2)) < 0.06) | (np.abs(th) < 0.05)
        shade = 0.85 + 0.25 * (1 - rr) + 0.1 * np.cos(th + 0.8)
        c = g[None, None, :] * shade[..., None]
        c = np.where((vein & (rr < 0.85))[..., None], g * 1.6, c)
        sub = img[np.ix_(ys, xs)]
        img[np.ix_(ys, xs)] = np.where(m[..., None], c, sub)
        hs = hgt[np.ix_(ys, xs)]
        hgt[np.ix_(ys, xs)] = np.where(m, 0.4 + 0.5 * (1 - rr) + i / 2800, hs)
    T.save(np.clip(img, 0, 1), out(sp, "color"), quality=88)
    T.save(T.normal_from_height(T.blur(hgt, 1.0, wrap=True), strength=4.0), out(sp, "normal"), quality=90)


def feather(sp):
    H, W = 256, 512
    u, v = grid(H, W)
    y = v * 2 - 1
    base = T.hexrgb("#b4e6f8")
    edge = T.hexrgb("#2aa8c8")
    e = np.abs(y)
    col = T.mix(base, edge, T.smoothstep(0.35, 1.0, e)[..., None])
    col = T.mix(col, T.hexrgb("#e8faff"), np.exp(-(y / 0.04) ** 2)[..., None] * (u[..., None] < 0.9))
    barbs = 0.5 + 0.5 * np.sin((u * 60 - np.abs(y) * 14) * 2 * np.pi * 0.5)
    col = col * (0.92 + 0.08 * barbs[..., None])
    col = col * (0.85 + 0.2 * u[..., None])
    n = T.fbm((H, W), (8, 16), 3, seed=9)
    col = col * (0.94 + 0.12 * (n[..., None] - 0.5))
    T.save(np.clip(col, 0, 1), out(sp, "tex"), quality=90)


KINDS = {"eyes": eyes, "ivy": ivy, "feather": feather}


def main():
    sp = T.spec()
    KINDS[sp["kind"]](sp)


main()
