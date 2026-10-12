# SPDX-License-Identifier: MIT
"""Paints the textures of the magic well (magic_well.py; reference/video-magic-well.mov).

kinds (params["kind"]):

- "stone": 1024 x 1024 colour + normal. Rows 0-767: fieldstone faces (dark grey-green, mottled,
  lichen specks, moss in the hollows); rows 768-1023: the dark mortar between them.
- "inner": 512 x 512 base + emission: the inside of the shaft, u round it, v from the rim
  (row 0) down params["depth"] metres (row 511): courses of rounded stones, lit red from below:
  the emission is strongest just under the rim (the red fog light) and fades into the dark
  shaft, with a faint red glow again at the very bottom.
- "rope": 256 x 256: tan hemp, three strands twisting along u.
- "ivy": 256 x 256 RGBA: one ivy leaf (three to five lobes, pale veins), alpha cut-out.
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


def stone(sp):
    S = 1024
    img = np.zeros((S, S, 3))
    hgt = np.zeros((S, S))
    H = 768
    n1 = T.fbm((H, S), 8, 5, seed=3)
    n2 = T.fbm((H, S), 40, 4, seed=4)
    n3 = T.fbm((H, S), 120, 3, seed=5)
    base = T.hexrgb("#4c5048")
    warm = T.hexrgb("#5a5446")
    col = T.mix(base, warm, n1[..., None]) * (0.8 + 0.35 * (n2[..., None] - 0.5) + 0.2 * (n3[..., None] - 0.5))
    moss = T.smoothstep(0.56, 0.72, T.fbm((H, S), 12, 4, seed=6))
    col = T.mix(col, T.hexrgb("#2c4024") * (0.85 + 0.3 * n3[..., None]), 0.75 * moss[..., None])
    rng = np.random.default_rng(7)
    lich = T.smoothstep(0.83, 0.88, T.fbm((H, S), 90, 2, seed=8))
    col = T.mix(col, T.hexrgb("#8a907a"), 0.25 * lich[..., None])
    img[:H] = col
    hgt[:H] = 0.6 * n2 + 0.3 * n3 + 0.2 * moss
    m1 = T.fbm((S - H, S), 30, 4, seed=9)
    img[H:] = T.hexrgb("#1c1a16") * (0.7 + 0.6 * m1[..., None])
    hgt[H:] = 0.3 * m1
    T.save(np.clip(img, 0, 1), out(sp, "color"), quality=88)
    T.save(T.normal_from_height(T.blur(hgt, 1.0), strength=5.0, wrap=False), out(sp, "normal"), quality=90)


def inner(sp):
    S = 512
    u, v = grid(S, S)
    D = sp.get("depth", 1.8)
    depth = v * D                                          # metres below the rim
    circ = 2 * math.pi * 0.40
    x, y = u * circ, depth
    # courses of stones ~0.15 m high, 0.24-0.34 m long, brick-bonded with jitter
    ch = 0.15
    row = np.floor(y / ch)
    fy = y / ch - row
    rng = np.random.default_rng(3)
    shift = rng.uniform(0, 1, 64)[row.astype(int) % 64]
    L = circ / 9                                          # nine stones round: tiles seamlessly in u
    wob = 0.18 * (T.fbm((S, S), (16, 8), 3, seed=12) - 0.5)
    fy = (fy + wob * 0.6) % 1.0
    sx = (x / L + shift * 3.7 + wob) % 9
    k = np.floor(sx)
    fx = sx - k
    dx = np.minimum(fx, 1 - fx) * L
    dy = np.minimum(fy, 1 - fy) * ch
    d = np.minimum(dx, dy)
    face = T.smoothstep(0.004, 0.022, d)
    n = T.fbm((S, S), (24, 12), 4, seed=11)
    base = T.hexrgb("#3a3632") * (0.6 + 0.5 * n[..., None]) * (0.35 + 0.65 * face[..., None])
    glow = np.exp(-depth / 0.30) + 0.10 * np.exp(-((depth - D) / 0.15) ** 2)
    red = T.hexrgb("#ff2a14")
    em = red * glow[..., None] * (0.35 + 0.65 * face[..., None]) * (0.8 + 0.4 * n[..., None])
    base = T.mix(base, T.hexrgb("#6a1a10") * (0.6 + 0.4 * face[..., None]), np.clip(glow, 0, 1)[..., None] * 0.6)
    T.save(np.clip(base, 0, 1), out(sp, "base"), quality=90)
    T.save(np.clip(em, 0, 1), out(sp, "emit"), quality=90)


def rope(sp):
    S = 256
    u, v = grid(S, S)
    strands = 3
    ph = (v * strands - u * 6.0) % 1.0               # helical strands: 6 twists per tile length
    edge = np.abs(ph - 0.5) * 2
    shade = 0.55 + 0.45 * np.sqrt(np.clip(1 - edge ** 2, 0, 1))
    fib = 0.5 + 0.5 * np.sin((v * 40 - u * 90) * 2 * np.pi * 0.5)
    n = T.fbm((S, S), 16, 3, seed=2)
    col = T.hexrgb("#a88a5c") * (shade * (0.9 + 0.1 * fib) * (0.85 + 0.3 * n))[..., None]
    T.save(np.clip(col, 0, 1), out(sp, "tex"), quality=90)


def ivy(sp):
    S = 256
    u, v = grid(S, S)
    X, Y = (u - 0.5) * 2, (0.5 - v) * 2              # leaf tip toward +Y (the top of the image)
    r = np.hypot(X, Y + 0.25)
    th = np.arctan2(X, Y + 0.25)                     # 0 = toward the tip
    lobes = sp.get("lobes", 5)
    shape = 0.70 + 0.30 * np.abs(np.cos(th * lobes / 2)) ** 1.3
    shape = shape * np.where(np.abs(th) > 2.4, 0.55, 1.0)
    leaf = r < 0.78 * shape
    vein = ((np.abs(np.sin(th * lobes / 2)) < 0.05) | (np.abs(X) < 0.025)) & (r < 0.7 * shape)
    g1, g2 = T.hexrgb(sp.get("color", "#2e5a2a")), T.hexrgb(sp.get("dark", "#173a18"))
    n = T.fbm((S, S), 12, 3, seed=sp.get("seed", 4))
    col = T.mix(g2, g1, np.clip(0.4 + 0.6 * (1 - r) + 0.3 * (n - 0.5), 0, 1)[..., None])
    col = np.where(vein[..., None], T.hexrgb(sp.get("vein", "#8aa878")), col)
    stalk = (np.abs(X) < 0.03) & (Y < -0.35) & (Y > -0.98)
    a = (leaf | stalk).astype(float)
    col = np.where(stalk[..., None], g2, col)
    img = np.zeros((S, S, 4))
    img[..., :3] = T.fill_from_mask(col, a > 0.5)
    img[..., 3] = a
    T.save(img, out(sp, "tex"))


KINDS = {"stone": stone, "inner": inner, "rope": rope, "ivy": ivy}


def main():
    sp = T.spec()
    KINDS[sp["kind"]](sp)


main()
