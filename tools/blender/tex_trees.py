# SPDX-License-Identifier: MIT
"""Paints the night-woods trees' textures (used by trees.py).

bark    512 x 1024 (+ normal map), tileable: furrowed grey-brown oak bark, u around (one tile =
        0.6 m of circumference), v along (one tile = 1.5 m).
leaves  1024 x 1024 RGBA: four leaf clusters (2 x 2 cells), each a twig with ~45 oak-ish leaves,
        mostly deep green with some olive and a few October yellows; alpha = leaves and twigs.
        Each cluster's twig starts at the bottom centre of its cell.
"""

import math

import numpy as np
from PIL import Image, ImageDraw

import texlib as T

sp = T.spec()


def bark():
    H, W = 1024, 512
    # vertical ridges and furrows, broken into plates
    ridge = T.fbm((H, W), (6, 14), 5, seed=1)
    ridge2 = T.fbm((H, W), (14, 30), 3, seed=2)
    furrow = np.abs(ridge - 0.5) * 2
    plates = T.smoothstep(0.15, 0.45, furrow + 0.25 * (ridge2 - 0.5))
    cross = T.smoothstep(0.62, 0.7, T.fbm((H, W), (40, 8), 3, seed=3))   # horizontal cracks between plates
    plates = plates * (1 - 0.7 * cross)
    c = T.mix(T.hexrgb("#2a241f"), T.hexrgb("#7a7268"), plates)
    lich = T.smoothstep(0.62, 0.75, T.fbm((H, W), (10, 6), 4, seed=4)) * plates
    c = T.mix(c, T.hexrgb("#8a9070"), lich * 0.45)
    c = c * (0.85 + 0.25 * T.fbm((H, W), (60, 30), 2, seed=5)[..., None])
    T.save(c, sp["out"]["bark"], quality=88)
    h = plates + 0.3 * ridge2
    T.save(T.normal_from_height(h, strength=6.0)[::2, ::2], sp["out"]["bark_n"], quality=90)


def leaf_poly(cx, cy, ang, ln, wd, lobes, rng):
    """An oak-ish leaf outline (pixel coords): a midrib with rounded lobes each side."""
    pts_l, pts_r = [], []
    n = 24
    for k in range(n + 1):
        t = k / n
        w = wd * math.sin(math.pi * min(t * 1.1, 1.0)) ** 0.8
        w *= 1 + 0.35 * max(0.0, math.sin(t * math.pi * lobes)) - 0.12
        x = t * ln
        pts_l.append((x, w))
        pts_r.append((x, -w * rng.uniform(0.9, 1.1)))
    ca, sa = math.cos(ang), math.sin(ang)
    out = pts_l + list(reversed(pts_r))
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in out]


def leaves():
    N = 1024
    SS = 2
    S = N * SS
    cell = S // 2
    rgba = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(rgba)
    rng = np.random.default_rng(7)
    palette = [(34, 62, 26), (44, 78, 30), (58, 90, 36), (72, 96, 40), (90, 98, 44), (120, 112, 46), (150, 120, 40)]
    weights = np.array([3, 4, 4, 3, 2, 1, 0.6])
    weights = weights / weights.sum()
    for ci in range(4):
        ox, oy = (ci % 2) * cell, (ci // 2) * cell
        base = (ox + cell / 2, oy + cell - 8 * SS)
        # twigs: a main stem up the cell, side twigs branching off
        tw = []
        x, y = base
        a = -math.pi / 2 + rng.normal(0, 0.15)
        main = [(x, y)]
        for k in range(10):
            a += rng.normal(0, 0.12)
            x += math.cos(a) * cell * 0.075
            y += math.sin(a) * cell * 0.075
            main.append((x, y))
        tw.append((main, 5 * SS))
        tips = [main[-1]]
        for k in range(2, 10):
            px, py = main[k]
            for side in (-1, 1):
                if rng.random() < 0.55:
                    continue
                b = -math.pi / 2 + side * rng.uniform(0.6, 1.1)
                pts = [(px, py)]
                qx, qy = px, py
                for j in range(4):
                    b += rng.normal(0, 0.15)
                    qx += math.cos(b) * cell * 0.06
                    qy += math.sin(b) * cell * 0.06
                    pts.append((qx, qy))
                tw.append((pts, 3 * SS))
                tips += pts[1:]
        for pts, w in tw:
            d.line(pts, fill=(52, 40, 30, 255), width=w)
        # leaves along the twigs, from the back layer to the front
        anchors = [p for pts, _ in tw for p in pts[1:]]
        for k in range(48):
            ax, ay = anchors[rng.integers(len(anchors))]
            ang = rng.uniform(0, math.tau)
            ln = rng.uniform(0.11, 0.17) * cell
            wd = ln * rng.uniform(0.26, 0.36)
            cx, cy = ax + rng.normal(0, 0.02 * cell), ay + rng.normal(0, 0.02 * cell)
            col = palette[rng.choice(len(palette), p=weights)]
            shade = rng.uniform(0.75, 1.1)
            col = tuple(int(min(255, c * shade)) for c in col) + (255,)
            poly = leaf_poly(cx, cy, ang, ln, wd, rng.integers(3, 5), rng)
            # keep inside the cell
            poly = [(min(max(x, ox + 2), ox + cell - 3), min(max(y, oy + 2), oy + cell - 3)) for x, y in poly]
            d.polygon(poly, fill=col)
            vein = (int(col[0] * 0.75), int(col[1] * 0.8), int(col[2] * 0.7), 255)
            d.line([(cx, cy), (cx + math.cos(ang) * ln * 0.9, cy + math.sin(ang) * ln * 0.9)], fill=vein, width=SS)
    im = rgba.resize((N, N), Image.LANCZOS)
    a = np.asarray(im, dtype=float) / 255
    rgb = T.fill_from_mask(a[..., :3], a[..., 3] > 0.5)
    T.save(np.concatenate([rgb, a[..., 3:4]], -1), sp["out"]["leaves"])


bark()
leaves()
