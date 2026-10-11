# SPDX-License-Identifier: MIT
"""Paints the textures of the pirate props (skeletons.py, treasure.py).

kinds (params["kind"]):

- "bone": 512 x 512. Rows 0-255: the skull, mapped by azimuth (u; u = 0.75 looks forward) and
  latitude (v up): sockets, the nose hole, cheek shadows, the teeth of the upper jaw, cranial
  sutures. Rows 256-447: plain bone (ivory with grime). Rows 448-511: a strip of lower teeth.
- "cloth": 1024 x 1024 atlas of fabrics in 256-row bands of two 512 x 256 tiles: linen shirt,
  black vest with a skull-and-crossbones, rust-orange tattered sleeves, red sash with black
  stripes, brown breeches, black hair strands, red bandana with white dots, sack canvas.
- "pumpkin": 512 x 512: orange skin round the ribs (u around, v up; rows 0-383) and the green-
  brown stem (rows 384-511). params: color, groove color, ribs.
- "treasure": 512 x 512 in 4 x 4 cells: gold coin faces, gold, gems (ruby, emerald, sapphire,
  amethyst), pearl, and a heap tile of piled coins (rows 256-511) for the mound.
- "frond": 512 x 512 RGBA: one palm frond (rachis along u, leaflets out to both sides) with
  alpha cut-out; the rest of the alpha is 0.
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


def save(img, sp, key="tex", q=90):
    T.save(img, out(sp, key), quality=q)


def bone(sp):
    S = 512
    img = np.zeros((S, S, 3))
    ivory = T.hexrgb("#e6dcc4")
    grime = T.hexrgb("#7c6a4c")
    n1 = T.fbm((S, S), 12, 5, seed=3)
    n2 = T.fbm((S, S), 60, 3, seed=5)
    base = ivory * (0.92 + 0.12 * (n1[..., None] - 0.5) + 0.06 * (n2[..., None] - 0.5))
    dirt = T.smoothstep(0.55, 0.8, n1)
    img[:] = T.mix(base, grime, 0.35 * dirt)
    # skull map (rows 0..255)
    H = 256
    y, x = np.mgrid[0:H, 0:S]
    u = (x + 0.5) / S
    v = 1 - (y + 0.5) / H
    du = u - 0.75
    sk = img[:H].copy()
    shade = np.zeros((H, S))
    for sgn in (-1, 1):
        # eye sockets: deep rounded squares, darkest in the middle
        ex, ey = 0.075 * sgn, 0.50
        d = np.sqrt(((du - ex) / 0.058) ** 4 + ((v - ey) / 0.085) ** 4) ** 0.25
        shade = np.maximum(shade, T.smoothstep(1.25, 0.75, d) * 0.6 + T.smoothstep(0.95, 0.5, d) * 0.4)
        # cheekbone shadows under the sockets
        d2 = np.hypot((du - 0.11 * sgn) / 0.05, (v - 0.36) / 0.05)
        shade = np.maximum(shade, 0.25 * T.smoothstep(1.4, 0.4, d2))
        # temples
        d3 = np.hypot((du - 0.19 * sgn) / 0.05, (v - 0.52) / 0.10)
        shade = np.maximum(shade, 0.22 * T.smoothstep(1.4, 0.4, d3))
    # the nose: an upside-down heart
    nx, ny = du, v - 0.37
    d = np.hypot(np.abs(nx) / 0.026 - 0.35, ny / 0.05)
    nose = T.smoothstep(1.15, 0.8, d) * (ny < 0.05) * (ny > -0.055)
    shade = np.maximum(shade, nose)
    # upper teeth: a row of little blocks with dark gaps
    tb = (v > 0.205) & (v < 0.275) & (np.abs(du) < 0.09)
    gap = np.abs(((du + 0.5) / 0.018) % 1 - 0.5) < 0.12
    sk = np.where((tb & ~gap)[..., None], T.hexrgb("#efe6cf") * (0.95 + 0.05 * n2[:H, :, None]), sk)
    shade = np.where(tb & gap, 0.7, shade)
    shade = np.where((v > 0.18) & (v < 0.21) & (np.abs(du) < 0.10), np.maximum(shade, 0.45), shade)
    # sutures across the top
    sut = np.exp(-((v - 0.80 - 0.012 * np.sin(du * 140)) / 0.004) ** 2) * (np.abs(du) < 0.22)
    sut += np.exp(-((u - 0.25 + 0.01 * np.sin(v * 120)) / 0.003) ** 2) * (v > 0.62)
    shade = np.maximum(shade, 0.35 * np.clip(sut, 0, 1))
    sk = sk * (1 - 0.92 * shade[..., None]) + np.array([0.04, 0.03, 0.02]) * shade[..., None]
    img[:H] = sk
    # lower teeth strip (rows 448..511): teeth along u on the upper half of the strip
    y2, x2 = np.mgrid[448:512, 0:S]
    fv = (y2 - 448 + 0.5) / 64
    gap = np.abs(((x2 + 0.5) / S / 0.035) % 1 - 0.5) < 0.12
    teeth = (fv < 0.5)
    strip = img[448:512].copy()
    strip = np.where((teeth & ~gap)[..., None], T.hexrgb("#efe6cf"), strip)
    strip = np.where((teeth & gap)[..., None], T.hexrgb("#2a2118"), strip)
    img[448:512] = strip
    save(img, sp)


def weave(H, W, seed, scale=3.0):
    y, x = np.mgrid[0:H, 0:W]
    w = 0.5 + 0.25 * np.sin(x * scale) * np.sin(y * scale)
    return w + 0.3 * (T.fbm((H, W), (H // 8, W // 8), 2, seed=seed) - 0.5)


def tatter(img, H, W, seed, edge="bottom"):
    """Darkens frayed, torn-looking streaks near one edge (the hems are cut in the geometry)."""
    n = T.fbm((H, W), (4, 40), 3, seed=seed)
    y = (np.arange(H) + 0.5)[:, None] / H
    f = y if edge == "bottom" else 1 - y
    m = T.smoothstep(0.75, 1.0, f + 0.25 * (n - 0.5))
    return img * (1 - 0.35 * m[..., None])


def cloth(sp):
    S = 1024
    img = np.zeros((S, S, 3))
    H, W = 256, 512

    def tile(col, seed, contrast=0.18, dirt=0.25, dirt_col="#3a2e22"):
        c = T.hexrgb(col)
        wv = weave(H, W, seed)
        n = T.fbm((H, W), (6, 12), 4, seed=seed + 1)
        t = c * (1 + contrast * (wv[..., None] - 0.5) + 0.2 * (n[..., None] - 0.5))
        d = T.smoothstep(0.5, 0.85, T.fbm((H, W), (3, 6), 4, seed=seed + 2))
        t = T.mix(t, T.hexrgb(dirt_col), dirt * d)
        return t

    # row 0: linen shirt | black vest with the jolly roger
    img[0:H, 0:W] = tatter(tile("#ece6d6", 11, 0.14, 0.35, "#8a7a62"), H, W, 1)
    vest = tile("#1c1a1c", 12, 0.25, 0.15, "#000000")
    y, x = np.mgrid[0:H, 0:W]
    # stitched edges
    vest = np.where(((np.abs(y - 10) < 1.2) | (np.abs(y - H + 10) < 1.2))[..., None] & ((x // 6) % 2 == 0)[..., None],
                    T.hexrgb("#6a6058"), vest)
    # skull and crossbones centred at (W*0.5, H*0.48), white paint
    cx, cy, s = W * 0.5, H * 0.46, H * 0.30
    X, Y = (x - cx) / s, (y - cy) / s
    skull = (np.hypot(X / 0.62, (Y + 0.12) / 0.55) < 1) | ((np.abs(X) < 0.34) & (Y > 0.1) & (Y < 0.55))
    eyes = (np.hypot((np.abs(X) - 0.24) / 0.15, (Y + 0.05) / 0.17) < 1)
    nose = (np.abs(X) < 0.07 * (1 - (Y - 0.18) / 0.16)) & (Y > 0.18) & (Y < 0.34)
    teeth = (Y > 0.42) & (Y < 0.55) & (np.abs(((X + 1) / 0.12) % 1 - 0.5) < 0.1) & (np.abs(X) < 0.3)
    bones = np.zeros_like(skull)
    for sgn in (1, -1):
        # a bone along the diagonal
        tx, ty = (X + sgn * Y * 1.0) / 1.414, (Y - sgn * X) / 1.414
        shaft = (np.abs(ty) < 0.07) & (np.abs(tx) < 0.95)
        knobs = (np.hypot(np.abs(tx) - 0.98, np.abs(ty) - 0.08) < 0.1)
        bones |= shaft | knobs
    bones &= ~(np.hypot(X / 0.62, (Y + 0.12) / 0.55) < 1.05)
    jolly = (skull | bones) & ~eyes & ~nose & ~teeth
    vest = np.where(jolly[..., None], T.hexrgb("#e8e2d0") * (0.92 + 0.08 * weave(H, W, 3)[..., None]), vest)
    img[0:H, W:S] = vest
    # row 1: rust-orange tattered sleeves | red sash with black stripes
    img[H:2 * H, 0:W] = tatter(tile("#b8561e", 13, 0.2, 0.3), H, W, 2)
    sash = tile("#9e1a1a", 14, 0.2, 0.2)
    stripe = (np.abs(((y + 0.5) / H * 5) % 1 - 0.5) < 0.12)
    sash = np.where(stripe[..., None], T.hexrgb("#141012"), sash)
    img[H:2 * H, W:S] = sash
    # row 2: brown breeches | black hair strands
    img[2 * H:3 * H, 0:W] = tatter(tile("#4a3524", 15, 0.2, 0.25), H, W, 3)
    hn = T.fbm((H, W), (2, 160), 3, seed=16)
    hair = T.hexrgb("#141216") * (0.6 + 0.9 * hn[..., None])
    hair = hair + 0.08 * np.exp(-((hn - 0.62) / 0.05) ** 2)[..., None]
    img[2 * H:3 * H, W:S] = hair
    # row 3: red bandana with white dots | sack canvas
    band = tile("#b02020", 17, 0.15, 0.2)
    dots = np.hypot(((x + 0.5) % 32) - 16, ((y + 0.5) % 32) - 16) < 4.5
    band = np.where(dots[..., None], T.hexrgb("#f0e8e0"), band)
    img[3 * H:4 * H, 0:W] = band
    img[3 * H:4 * H, W:S] = tile("#8a7558", 18, 0.35, 0.3)
    save(img, sp)


def pumpkin(sp):
    S = 512
    img = np.zeros((S, S, 3))
    Hs = 384
    y, x = np.mgrid[0:Hs, 0:S]
    u = (x + 0.5) / S
    v = 1 - (y + 0.5) / Hs
    ribs = sp.get("ribs", 8)
    f = (u * ribs) % 1.0
    groove = np.exp(-((np.minimum(f, 1 - f)) / 0.07) ** 2)
    c = T.hexrgb(sp.get("color", "#e8771c"))
    g = T.hexrgb(sp.get("groove", "#a8440c"))
    n = T.fbm((Hs, S), (8, 32), 4, seed=sp.get("seed", 4))
    streak = T.fbm((Hs, S), (40, 6), 3, seed=sp.get("seed", 4) + 1)
    lobe = np.sin(np.pi * f)
    col = c * (0.86 + 0.16 * lobe[..., None] + 0.12 * (n[..., None] - 0.5) + 0.08 * (streak[..., None] - 0.5))
    col = T.mix(col, g, 0.65 * groove)
    # darker toward the poles and a pale blossom/stem scar
    pole = T.smoothstep(0.85, 1.0, v) + T.smoothstep(0.12, 0.0, v)
    col = T.mix(col, g * 0.8, 0.5 * pole)
    img[:Hs] = col
    # stem
    y2, x2 = np.mgrid[Hs:S, 0:S]
    sn = T.fbm((S - Hs, S), (4, 40), 4, seed=9)
    ridge = 0.5 + 0.5 * np.cos((x2 + 0.5) / S * 2 * np.pi * 6)
    stem = T.hexrgb(sp.get("stem", "#6b6a3a")) * (0.7 + 0.35 * ridge[..., None] + 0.25 * (sn[..., None] - 0.5))
    img[Hs:] = stem
    save(img, sp)


def treasure(sp):
    S = 512
    img = np.zeros((S, S, 3))
    C = 128
    y, x = np.mgrid[0:C, 0:C]
    X, Y = (x + 0.5) / C * 2 - 1, (y + 0.5) / C * 2 - 1
    r = np.hypot(X, Y)
    gold = T.hexrgb("#e8b030")
    n = T.fbm((C, C), 8, 3, seed=2)
    # (0,0) coin face: rim, a cross/crown emboss
    coin = gold * (0.85 + 0.25 * (n[..., None] - 0.5))
    rim = (r > 0.80) & (r < 0.95)
    emb = ((np.abs(X) < 0.12) & (np.abs(Y) < 0.55)) | ((np.abs(Y + 0.1) < 0.12) & (np.abs(X) < 0.45))
    coin = np.where((rim | emb)[..., None], gold * 1.15, coin)
    coin = np.where(((r > 0.95) | ((r > 0.76) & (r < 0.80)))[..., None], gold * 0.6, coin)
    img[0:C, 0:C] = coin
    # (0,1) plain gold (crown, coin edges, lock plates)
    img[0:C, C:2 * C] = gold * (0.85 + 0.3 * (n[..., None] - 0.5))
    gems = ["#c0102a", "#10a040", "#1a4ad0", "#8a2ac0"]
    for i, gc in enumerate(gems):
        cc = T.hexrgb(gc)
        facet = 0.75 + 0.35 * np.cos(np.arctan2(Y, X) * 4) * r + 0.4 * np.exp(-((X + 0.3) ** 2 + (Y + 0.3) ** 2) / 0.05)
        cell = np.clip(cc * facet[..., None], 0, 1)
        row, colc = divmod(2 + i, 4)
        img[row * C:(row + 1) * C, colc * C:(colc + 1) * C] = cell
    # (1,2) pearl: soft white with a pink sheen
    pearl = T.hexrgb("#f2ece6") * (0.85 + 0.15 * (1 - r[..., None])) + np.array([0.04, 0.0, 0.03]) * (Y[..., None] > 0)
    img[C:2 * C, 2 * C:3 * C] = np.clip(pearl, 0, 1)
    # (1,3) silver
    img[C:2 * C, 3 * C:4 * C] = T.hexrgb("#b8bcc4") * (0.8 + 0.3 * (n[..., None] - 0.5))
    # rows 256..511: a heap of coins seen from above (tileable)
    H = 256
    heap = np.zeros((H, S, 3)) + gold * 0.35
    hgt = np.zeros((H, S))
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:H, 0:S]
    for _ in range(900):
        cx, cy = rng.uniform(0, S), rng.uniform(0, H)
        rr = rng.uniform(9, 15)
        ell = rng.uniform(0.45, 1.0)
        ang = rng.uniform(0, np.pi)
        dx = (xx - cx + S / 2) % S - S / 2
        dy = (yy - cy + H / 2) % H - H / 2
        ex = dx * np.cos(ang) + dy * np.sin(ang)
        ey = (-dx * np.sin(ang) + dy * np.cos(ang)) / ell
        d = np.hypot(ex, ey) / rr
        m = d < 1
        if not m.any():
            continue
        shade = 0.75 + 0.35 * (1 - d) + 0.15 * np.cos(np.arctan2(ey, ex) - 0.8)
        c = gold * shade[..., None]
        c = np.where((d > 0.82)[..., None], gold * 0.55, c)
        heap = np.where(m[..., None], c, heap)
        hgt = np.where(m, 1 - 0.3 * d, hgt)
    # a few gems and pearls in the heap
    for _ in range(40):
        cx, cy = rng.uniform(0, S), rng.uniform(0, H)
        rr = rng.uniform(6, 10)
        d = np.hypot((xx - cx + S / 2) % S - S / 2, (yy - cy + H / 2) % H - H / 2) / rr
        k = rng.integers(0, 6)
        cc = T.hexrgb((gems + ["#f2ece6", "#f2ece6"])[k])
        heap = np.where((d < 1)[..., None], cc * (0.7 + 0.5 * (1 - d))[..., None], heap)
    img[H:] = np.clip(heap, 0, 1)
    save(img, sp)


def frond(sp):
    S = 512
    img = np.zeros((S, S, 4))
    y, x = np.mgrid[0:S, 0:S]
    u = (x + 0.5) / S            # along the frond (0 base -> 1 tip)
    v = (y + 0.5) / S * 2 - 1    # across (-1 .. 1), rachis at 0
    green = T.hexrgb(sp.get("color", "#3ad24a"))
    dark = T.hexrgb(sp.get("dark", "#127a2a"))
    width = 0.95 * np.sin(np.pi * np.clip(u * 0.92 + 0.04, 0, 1)) ** 0.7
    # leaflets: slanted blades toward the tip
    n_leaf = 26
    ph = (u * n_leaf - np.abs(v) * 2.2) % 1.0
    blade = np.abs(ph - 0.5) < 0.30 * (1 - np.abs(v) / np.maximum(width, 1e-3)) + 0.02
    inside = (np.abs(v) < width) & blade & (u > 0.06)
    rachis = (np.abs(v) < 0.035 * (1.2 - u)) & (u < 0.995)
    a = (inside | rachis).astype(float)
    shade = 0.75 + 0.35 * (1 - np.abs(v)) + 0.1 * np.cos(ph * 2 * np.pi)
    col = T.mix(dark, green, np.clip(shade - 0.3, 0, 1))
    col = np.where(rachis[..., None], T.hexrgb(sp.get("rachis", "#9ae05a")), col)
    img[..., :3] = col
    img[..., 3] = a
    # pad colour into transparent pixels (clean mip edges)
    img[..., :3] = T.fill_from_mask(img[..., :3], a > 0.5)
    T.save(img, out(sp, "tex"))


KINDS = {"bone": bone, "cloth": cloth, "pumpkin": pumpkin, "treasure": treasure, "frond": frond}


def main():
    sp = T.spec()
    KINDS[sp["kind"]](sp)


main()
