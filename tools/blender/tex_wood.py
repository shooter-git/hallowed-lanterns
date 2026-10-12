# SPDX-License-Identifier: MIT
"""Paints tileable plank textures (colour + normal map) for the pirate props (kraken.py,
treasure.py): ship hull strakes, rowboat planking, barrel staves, the treasure chest and its
platform.

The tile has `rows` planks stacked down the image (one plank per row band), the grain running
along u. Each plank gets its own tone, a long fibrous grain, a few knots, butt joints at random
places, worn lighter edges, darker grooves between planks, and optional nail heads near the
butt joints. The tile repeats in u (and v), so a model maps u = metres along / tile length.

params: size, rows, tile_m (tile length in metres, for feature sizes), base ['#hex', ...]
(plank tones to pick from), grain (0..1), groove (darkness), wear (light edges), dirt, knots
(per plank), joints (butt joints per plank), nails (bool), seed, row_tones (optional: the index
into base of each row's tone, to keep two woods in one tile).
"""

import numpy as np

import texlib as T


def out(sp, kind):
    """The output path for `kind` ("tex", "base", "color", ...): the key itself or kind_<name>
    (callers give each texture its own key so that lib.paint's cache stamps don't collide)."""
    for k, v in sp["out"].items():
        if k == kind or k.startswith(kind + "_"):
            return v
    raise KeyError(kind)


def main():
    sp = T.spec()
    S = sp["size"]
    H = sp.get("height", S)
    rows = sp["rows"]
    tile_m = sp.get("tile_m", 2.0)
    rng = np.random.default_rng(sp.get("seed", 1))
    px_m = S / tile_m
    yy, xx = np.mgrid[0:H, 0:S]
    row = (yy * rows) // H
    fy = (yy + 0.5) / H * rows - row                # 0..1 across the plank
    tones = [T.hexrgb(c) for c in sp["base"]]
    col = np.zeros((H, S, 3))
    height = np.zeros((H, S))
    # long fibrous grain: noise stretched hard along u
    g1 = T.fbm((H, S), (rows * 10, 3), 5, seed=sp.get("seed", 1) + 3)
    g2 = T.fbm((H, S), (rows * 40, 8), 3, seed=sp.get("seed", 1) + 5)
    blot = T.fbm((H, S), (rows * 2, 6), 4, seed=sp.get("seed", 1) + 9)
    grain = sp.get("grain", 0.5)
    for r in range(rows):
        sel = row == r
        if sp.get("row_tones"):   # explicit tone per row (index into base)
            tone = tones[sp["row_tones"][r % len(sp["row_tones"])]] * rng.uniform(0.92, 1.06)
        else:
            tone = tones[rng.integers(len(tones))] * rng.uniform(0.88, 1.10)
        # the grain lines wave along the plank
        phase = rng.uniform(0, 6.28)
        wave = np.sin((xx / S) * 6.28 * rng.integers(1, 3) + phase) * 0.15
        lines = 0.5 + 0.5 * np.sin((fy + wave + g1 * 0.6) * 6.28 * rng.uniform(5, 9))
        shade = 1 + grain * (0.22 * (lines - 0.5) + 0.35 * (g2 - 0.5)) + 0.18 * (blot - 0.5)
        c = tone[None, None, :] * shade[..., None]
        col = np.where(sel[..., None], c, col)
        h = 0.5 + 0.08 * (lines - 0.5) + 0.05 * (g2 - 0.5)
        height = np.where(sel, h, height)
        # knots
        for _ in range(sp.get("knots", 1)):
            if rng.random() < 0.6:
                kx = rng.uniform(0, S)
                ky = (r + rng.uniform(0.3, 0.7)) * H / rows
                kr = rng.uniform(0.012, 0.025) * px_m
                dx = ((xx - kx + S / 2) % S - S / 2) / 2.2
                d = np.hypot(dx, yy - ky) / kr
                k = np.exp(-d ** 2)
                ring = 0.5 + 0.5 * np.sin(d * 9)
                col = np.where((sel & (d < 3))[..., None], col * (1 - 0.45 * k[..., None] - 0.1 * (ring * np.exp(-(d / 2) ** 2))[..., None]), col)
                height = np.where(sel & (d < 3), height - 0.15 * k, height)
        # butt joints across the plank
        for _ in range(sp.get("joints", 1)):
            jx = rng.uniform(0, S)
            dj = np.abs((xx - jx + S / 2) % S - S / 2)
            jw = 0.004 * px_m + 0.8
            m = sel & (dj < jw * 4)
            j = np.exp(-(dj / jw) ** 2)
            col = np.where(m[..., None], col * (1 - 0.6 * j[..., None]), col)
            height = np.where(m, height - 0.4 * j, height)
            if sp.get("nails"):
                for ny in (0.25, 0.75):
                    for side in (-1, 1):
                        nx = jx + side * 0.03 * px_m
                        dn = np.hypot((xx - nx + S / 2) % S - S / 2, yy - (r + ny) * H / rows)
                        nm = sel & (dn < 0.012 * px_m)
                        col = np.where(nm[..., None], T.hexrgb(sp.get("nail", "#2a2522")), col)
                        height = np.where(nm, height + 0.2, height)
    # grooves between planks and worn edges
    edge = np.minimum(fy, 1 - fy) * (H / rows) / px_m      # metres to the plank edge
    gw = sp.get("groove_m", 0.005)
    groove = np.exp(-(edge / gw) ** 2)
    wear = np.exp(-(edge / (gw * 3)) ** 2) * (1 - groove)
    col = col * (1 - sp.get("groove", 0.75) * groove[..., None]) + sp.get("wear", 0.08) * wear[..., None]
    height = height - 0.6 * groove + 0.05 * wear
    # dirt and weathering
    dirt = T.smoothstep(0.55, 0.8, T.fbm((H, S), (4, 8), 4, seed=sp.get("seed", 1) + 21))
    dc = T.hexrgb(sp.get("dirt_color", "#2a241e"))
    col = T.mix(col, dc, sp.get("dirt", 0.3) * dirt)
    T.save(np.clip(col, 0, 1), out(sp, "color"), quality=sp.get("quality", 88))
    if any(k == "normal" or k.startswith("normal_") for k in sp["out"]):
        T.save(T.normal_from_height(T.blur(height, 0.7, wrap=True), strength=sp.get("normal_strength", 3.0)),
               out(sp, "normal"), quality=92)


main()
