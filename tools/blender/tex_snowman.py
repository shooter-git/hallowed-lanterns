# SPDX-License-Identifier: MIT
"""Paints the snowman's textures (used by snowman.py).

gourd   painted at 2048 x 1024, stored at 1024 x 512, u = around (rib grooves at u = k / ribs), v = bottom -> top.
        Carnival squash: creamy white with dark green stripes down the grooves (ragged,
        widest at the waist), thinner broken stripes on some lobes, green flecks, foam pits.
props   painted at 2048 x 1024, stored at 1024 x 512: an atlas (regions in the params): bark, mossy bark, pallet wood, corn-cob
        kernels, carrot, hat felt, coal.
Both with tangent-space normal maps (half resolution).
"""

import numpy as np

import texlib as T

sp = T.spec()


def gourd():
    W, H = 2048, 1024
    ribs = sp["ribs"]
    yy, xx = np.mgrid[0:H, 0:W]
    u = (xx + 0.5) / W
    v = 1 - (yy + 0.5) / H
    lat = np.sin(np.pi * v)
    rng = np.random.default_rng(3)
    # distance (in ribs) to the nearest groove
    g = u * ribs
    dg = np.abs(g - np.round(g))
    k = np.round(g).astype(int) % ribs
    ragged = T.fbm((H, W), (40, 220), 4, seed=5) - 0.5
    ragged2 = T.fbm((H, W), (160, 600), 2, seed=6) - 0.5
    width = np.array([rng.uniform(0.11, 0.22) for _ in range(ribs)])[k]
    width = width * (0.55 + 0.6 * lat ** 0.7)
    stripe = T.smoothstep(width + 0.015, width - 0.01, dg + 0.09 * ragged + 0.03 * ragged2)
    # secondary broken stripes along some lobe centres
    lob = np.abs(g - np.floor(g) - 0.5)
    has = np.array([rng.random() < 0.6 for _ in range(ribs)])[(np.floor(g).astype(int)) % ribs]
    brk = T.fbm((H, W), (6, 40), 3, seed=8)
    stripe2 = T.smoothstep(0.045, 0.02, lob + 0.03 * ragged) * has * T.smoothstep(0.45, 0.6, brk) * lat
    # flecks: small elongated green dashes on the white
    fl = T.fbm((H, W), (70, 500), 2, seed=9)
    fl2 = T.fbm((H, W), (300, 900), 1, seed=10)
    flecks = np.clip((fl - 0.62) * 10, 0, 1) * np.clip((fl2 - 0.45) * 5, 0, 1)
    green = T.hexrgb("#123a20")
    green2 = T.hexrgb("#215a31")
    cream = T.hexrgb("#f0eedb")
    cream2 = T.hexrgb("#e2dfc3")
    mott = T.fbm((H, W), (8, 30), 4, seed=11)
    col = T.mix(cream2, cream, mott)
    gtone = T.mix(green, green2, T.fbm((H, W), (10, 60), 3, seed=12))
    m = np.clip(stripe + stripe2 + flecks * 0.9, 0, 1)
    col = T.mix(col, gtone, m)
    # stripes fade into blotches near the poles (blossom/stem ends are greener)
    pole = T.smoothstep(0.12, 0.0, np.minimum(v, 1 - v))
    col = T.mix(col, gtone, pole * 0.7)
    # foam pits: tiny dark pores
    pores = np.clip((T.fbm((H, W), (400, 1600), 1, seed=13) - 0.72) * 6, 0, 1)
    col = col * (1 - 0.35 * pores[..., None])
    T.save(col, sp["out"]["gourd"], quality=90, scale=0.5)
    # height: pores dent in, paint slightly raised, gentle lumps
    hgt = (-0.8 * pores + 0.25 * m + 0.6 * (T.fbm((H, W), (30, 120), 3, seed=14) - 0.5))
    hs = hgt[::2, ::2]
    T.save(T.normal_from_height(hs, strength=2.5), sp["out"]["gourd_n"], quality=92)


def props():
    W, H = 2048, 1024
    col = np.zeros((H, W, 3))
    hgt = np.zeros((H, W))
    R = sp["regions"]

    def region(name):
        x, y, w, h = R[name]
        yy, xx = np.mgrid[0:h, 0:w]
        return (slice(y, y + h), slice(x, x + w)), (xx + 0.5) / w, 1 - (yy + 0.5) / h, h, w

    # bark strips: u along the branch, v around (0.5 = top)
    for name, moss in (("bark", False), ("bark_moss", True)):
        sl, u, v, h, w = region(name)
        streak = T.fbm((h, w), (24, 6), 5, seed=20)
        crev = np.abs(T.fbm((h, w), (40, 10), 4, seed=21) - 0.5) * 2
        crev = T.smoothstep(0.0, 0.25, crev)
        knots = T.fbm((h, w), (6, 3), 3, seed=22)
        c = T.mix(T.hexrgb("#4a3420"), T.hexrgb("#9a7650"), streak)
        c = c * (0.55 + 0.45 * crev[..., None])
        c = T.mix(c, T.hexrgb("#c09a6a"), T.smoothstep(0.7, 0.85, knots) * 0.4)
        hh = 0.6 * crev + 0.3 * streak
        if moss:
            top = np.exp(-((v - 0.5) / 0.28) ** 2)
            amt = T.smoothstep(0.75, 0.15, u) * top
            mn = T.fbm((h, w), (30, 40), 4, seed=23)
            mcol = T.mix(T.hexrgb("#3d5e2c"), T.hexrgb("#8aa860"), mn)
            mm = T.smoothstep(0.35, 0.6, amt + 0.35 * (mn - 0.5))
            c = T.mix(c, mcol, mm)
            hh = hh + 0.4 * mm * mn
        col[sl] = c
        hgt[sl] = hh

    # weathered pallet pine: u along the boards
    sl, u, v, h, w = region("wood")
    grain = T.fbm((h, w), (60, 3), 5, seed=30)
    rings = np.sin((v * 40 + 3 * T.fbm((h, w), (6, 2), 3, seed=31)) * np.pi * 2) * 0.5 + 0.5
    base = T.mix(T.hexrgb("#8c7656"), T.hexrgb("#c2a87e"), grain)
    c = base * (0.82 + 0.18 * rings[..., None])
    weather = T.fbm((h, w), (8, 4), 4, seed=32)
    c = T.mix(c, T.hexrgb("#9b958a"), T.smoothstep(0.5, 0.75, weather) * 0.5)
    yy, xx = np.mgrid[0:h, 0:w]
    rng = np.random.default_rng(33)
    for _ in range(14):  # knots
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        rx, ry = rng.uniform(6, 16), rng.uniform(4, 9)
        d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        c = T.mix(c, T.hexrgb("#5a4028"), T.smoothstep(1.0, 0.3, d) * 0.85)
    col[sl] = c
    hgt[sl] = 0.5 * grain + 0.2 * rings

    # corn-cob kernels: u around (16 columns), v up (11 rows)
    sl, u, v, h, w = region("corn")
    cu, cv = u * 16, v * 11
    cv = cv + 0.5 * (np.floor(cu) % 2)
    fu, fv = np.abs(cu - np.floor(cu) - 0.5) * 2, np.abs(cv - np.floor(cv) - 0.5) * 2
    k = (fu ** 3 + fv ** 3) ** (1 / 3)
    kern = T.smoothstep(1.0, 0.75, k)
    jit = T.fbm((h, w), (11, 16), 2, seed=40)
    c = T.mix(T.hexrgb("#9a6a14"), T.mix(T.hexrgb("#e8b52e"), T.hexrgb("#ffe07a"), (1 - k) * 0.8 + 0.2 * jit), kern)
    col[sl] = c
    hgt[sl] = kern * (1 - k * k) * 1.4

    # carrot: u around, v along (tip at v = 1)
    sl, u, v, h, w = region("carrot")
    ridges = np.abs(np.sin(v * np.pi * 9 + 2 * T.fbm((h, w), (3, 6), 2, seed=50))) ** 6
    c = T.mix(T.hexrgb("#d9541c"), T.hexrgb("#f08a3a"), T.fbm((h, w), (6, 6), 3, seed=51))
    c = c * (1 - 0.35 * ridges[..., None])
    col[sl] = c
    hgt[sl] = -ridges

    # hat felt and coal
    sl, u, v, h, w = region("felt")
    n = T.fbm((h, w), (40, 40), 4, seed=60)
    col[sl] = T.mix(T.hexrgb("#0d0d10"), T.hexrgb("#26262b"), n)
    hgt[sl] = n * 0.3
    sl, u, v, h, w = region("coal")
    n = T.fbm((h, w), (10, 10), 4, seed=61)
    col[sl] = T.mix(T.hexrgb("#101012"), T.hexrgb("#2c2b2e"), n)
    hgt[sl] = n
    T.save(col, sp["out"]["props"], quality=90, scale=0.5)
    T.save(T.normal_from_height(hgt[::2, ::2], strength=3.0, wrap=False), sp["out"]["props_n"], quality=92, scale=0.5)


gourd()
props()
