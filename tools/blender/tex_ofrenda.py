# SPDX-License-Identifier: MIT
"""Paints the ofrenda's textures (used by ofrenda.py).

crest   2048 x 1024: the cut-out crest art, drawn in crest metres (x right, z up) over the
        crest's bounding box. Base colour + emission (teal-green, brighter toward the bottom,
        greener on the left and bluer on the right as under the LED wash in the photo).
papel   1024 x 1024: three papel-picado flags (black paper, lace cut-outs, a monarch with
        coloured tissue wings) and a cell of four monarch butterflies. RGBA (alpha = paper).
paint   2048 x 2048 atlas of everything opaque (regions in the params).
lights  512 x 512 emissive atlas: little glowing pumpkins, vase glow, bottle glass.
flame   32 x 128 flame gradient (v up).
"""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

import texlib as T

sp = T.spec()
SS = 2  # supersampling for drawn art


# ----------------------------------------------------------------------------------------------
# Crest
# ----------------------------------------------------------------------------------------------

def crest():
    W, H = 2048, 1024
    x0, x1, z0, z1 = sp["crest_box"]
    Wp, Hp = W * SS, H * SS

    def P(x, z):
        return ((x - x0) / (x1 - x0) * Wp, (1 - (z - z0) / (z1 - z0)) * Hp)

    sx = Wp / (x1 - x0)

    def new():
        im = Image.new("L", (Wp, Hp), 0)
        return im, ImageDraw.Draw(im)

    def ell(d, cx, cz, rx, rz, fill=255):
        a, b = P(cx - rx, cz + rz), P(cx + rx, cz - rz)
        d.ellipse([a, b], fill=fill)

    def poly(d, pts, fill=255):
        d.polygon([P(x, z) for x, z in pts], fill=fill)

    def line(d, pts, w, fill=255):
        d.line([P(x, z) for x, z in pts], fill=fill, width=max(1, int(w * sx)), joint="curve")

    # silhouette
    sil, ds = new()
    poly(ds, [tuple(q) for q in sp["crest_outline"]] + [(x1, z0), (x0, z0)])
    light, dl = new()     # light (raised) art shapes
    holes, dh = new()     # cut-through holes (dark)

    # --- centre: the pumpkin skull ---
    cx, cz = 0.0, 0.50
    for lx, lz, rx, rz in ((0, 0, 0.42, 0.36), (-0.2, 0.02, 0.27, 0.33), (0.2, 0.02, 0.27, 0.33)):
        ell(dl, cx + lx, cz + lz, rx, rz)
    poly(dl, [(-0.05, cz + 0.30), (0.05, cz + 0.30), (0.04, cz + 0.42), (-0.02, cz + 0.45), (-0.06, cz + 0.40)])

    def heart(d, hx, hz, s):
        ell(d, hx - 0.33 * s, hz + 0.18 * s, 0.36 * s, 0.33 * s)
        ell(d, hx + 0.33 * s, hz + 0.18 * s, 0.36 * s, 0.33 * s)
        poly(d, [(hx - 0.66 * s, hz + 0.12 * s), (hx + 0.66 * s, hz + 0.12 * s), (hx, hz - 0.62 * s)])
    heart(dh, cx - 0.17, cz + 0.08, 0.11)
    heart(dh, cx + 0.17, cz + 0.08, 0.11)
    # nose: a little upside-down heart/triangle
    poly(dh, [(cx - 0.045, cz - 0.04), (cx + 0.045, cz - 0.04), (cx, cz - 0.13)])
    ell(dh, cx - 0.02, cz - 0.05, 0.028, 0.025)
    ell(dh, cx + 0.02, cz - 0.05, 0.028, 0.025)
    # stitched smile
    mz = cz - 0.21
    line(dh, [(cx - 0.20, mz + 0.02), (cx - 0.1, mz - 0.005), (cx, mz - 0.012), (cx + 0.1, mz - 0.005), (cx + 0.2, mz + 0.02)], 0.022)
    for i in range(9):
        t = (i - 4) / 4
        sxp = cx + t * 0.18
        szp = mz - 0.012 * (1 - t * t) + 0.012 * t * t
        line(dh, [(sxp, szp - 0.035), (sxp, szp + 0.035)], 0.014)

    # --- moon and stars in the top lobe ---
    ell(dl, 0.0, 1.33, 0.125, 0.125)
    ell(dl, 0.055, 1.37, 0.105, 0.105, fill=0)   # carve the crescent

    def star(d, x, z, r):
        pts = []
        for k in range(8):
            ang = k * math.pi / 4
            rr = r if k % 2 == 0 else r * 0.28
            pts.append((x + rr * math.sin(ang), z + rr * math.cos(ang)))
        poly(d, pts)
    for x, z, r in sp["stars"]:
        star(dl, x, z, r)

    def rot_ell(d, cx, cz, rx, rz, ang, fill=255, n=40):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pts = []
        for k in range(n):
            t = k / n * math.tau
            x, z = rx * math.cos(t), rz * math.sin(t)
            pts.append((cx + x * ca - z * sa, cz + x * sa + z * ca))
        poly(d, pts, fill)

    # pumpkin lobe lines on the skull
    for sgn in (-1, 1):
        line(dh, [(sgn * (0.16 + 0.05 * math.sin(math.pi * f)), cz - 0.30 + 0.62 * f) for f in [k / 12 for k in range(13)]], 0.012)

    # --- butterflies in the side lobes (seen from the side, wings raised, facing the centre) ---
    for side in (-1, 1):
        bx, bz = side * 0.80, 0.86

        def S(x, z):
            return bx - side * x, bz + z   # local x points toward the centre

        def rel(d, x, z, rx, rz, ang, fill=255):
            px, pz = S(x, z)
            rot_ell(d, px, pz, rx, rz, -side * ang, fill)
        rel(dl, -0.03, 0.08, 0.11, 0.25, -18)        # forewing
        rel(dl, 0.02, -0.13, 0.10, 0.085, 35)        # hindwing
        for (x, z, rx, rz, ang) in ((-0.13, 0.20, 0.038, 0.14, -30), (-0.19, 0.10, 0.032, 0.12, -52), (-0.21, 0.0, 0.028, 0.10, -74)):
            rel(dl, x, z, rx, rz, ang)               # the far wings, feathered
        rel(dl, 0.03, -0.07, 0.026, 0.13, -30)       # body
        for (x, z) in ((-0.10, 0.27), (-0.15, 0.13), (-0.03, 0.30), (-0.13, 0.02)):
            line(dh, [S(0.02, -0.10), S(x, z)], 0.011)
        line(dh, [S(0.02, -0.10), S(0.08, -0.20)], 0.011)
        line(dl, [S(-0.02, 0.04), S(-0.10, 0.12)], 0.010)   # antennae
        line(dl, [S(-0.02, 0.04), S(-0.06, 0.15)], 0.010)
        # flower (cempasuchil) below the butterfly
        fx, fz = side * 0.92, 0.30
        for k in range(6):
            a = k * math.pi / 3 + 0.3
            px, pz = fx + math.cos(a) * 0.17, fz + math.sin(a) * 0.17
            ell(dl, px, pz, 0.12, 0.12)
        ell(dh, fx, fz, 0.085, 0.085)
        ell(dl, fx, fz, 0.06, 0.06)
        for k in range(6):
            a = k * math.pi / 3 + 0.3 + math.pi / 6
            line(dh, [(fx + math.cos(a) * 0.09, fz + math.sin(a) * 0.09), (fx + math.cos(a) * 0.29, fz + math.sin(a) * 0.29)], 0.014)
            a2 = a - math.pi / 6
            line(dh, [(fx + math.cos(a2) * 0.20, fz + math.sin(a2) * 0.20), (fx + math.cos(a2) * 0.27, fz + math.sin(a2) * 0.27)], 0.008)
        # leaves: serrated lenses, the outer ones pointing out and up, the inner ones toward the skull
        for lx, lz, ln, ang in ((side * 1.36, 0.13, 0.23, side * 12), (side * 0.50, 0.11, 0.18, -side * 8)):
            rot_ell(dl, lx, lz, ln, 0.065, ang)
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            line(dh, [(lx - ln * 0.9 * ca, lz - ln * 0.9 * sa), (lx + ln * 0.9 * ca, lz + ln * 0.9 * sa)], 0.009)
            for k in range(-3, 4):
                f = k / 4 * ln * 0.8
                bx2, bz2 = lx + f * ca, lz + f * sa
                line(dh, [(bx2, bz2), (bx2 + 0.05 * ca - 0.05 * sa, bz2 + 0.05 * sa + 0.05 * ca)], 0.008)

    def arr(im):
        return np.asarray(im.resize((W, H), Image.LANCZOS), dtype=float) / 255.0

    silA, lightA, holesA = arr(sil), arr(light), arr(holes)
    # cut lines: a thin dark outline around every light shape and the inner border of the panel
    lb = lightA > 0.5
    edge = (ndimage.binary_dilation(lb, iterations=3) & ~ndimage.binary_erosion(lb, iterations=2)).astype(float)
    edge = T.blur(edge, 0.8)
    sb = silA > 0.5
    inner = ndimage.binary_erosion(sb, iterations=26)
    border = (inner & ~ndimage.binary_erosion(sb, iterations=31)).astype(float)
    border = T.blur(border, 0.8)

    yy, xx = np.mgrid[0:H, 0:W]
    fx = xx / W
    fz = 1 - yy / H
    tint = T.mix(T.hexrgb("#33d9a0"), T.hexrgb("#3aa8e8"), T.smoothstep(0.15, 0.95, fx))
    lift = 0.55 + 0.45 * T.smoothstep(0.9, 0.05, fz)
    panel = tint * (0.42 * lift)[..., None]
    art = T.mix(tint, np.array([0.85, 1.0, 0.95]), 0.45) * (0.75 + 0.35 * lift)[..., None]
    n = T.fbm((H, W), (8, 16), 3, seed=3)
    emis = T.mix(panel, art, lightA * (1 - holesA))
    emis = emis * (1 - 0.85 * np.clip(edge + border + holesA, 0, 1))[..., None]
    emis = emis * (0.9 + 0.2 * n[..., None])
    base = T.mix(T.hexrgb("#1f6f73"), T.hexrgb("#8fd8c8"), lightA * (1 - holesA))
    base = base * (1 - 0.8 * np.clip(edge + border + holesA, 0, 1))[..., None]
    # outside the silhouette: plain panel (used by the back and edges of the board)
    outside = ~sb
    emis[outside] = panel[outside] * 0.6
    base[outside] = T.hexrgb("#1f6f73")
    T.save(base, sp["out"]["crest_base"], quality=90)
    T.save(emis, sp["out"]["crest_emit"], quality=90)


# ----------------------------------------------------------------------------------------------
# Papel picado
# ----------------------------------------------------------------------------------------------

def monarch(d, cx, cy, s, wing_col, vein=(10, 10, 10, 255)):
    """A monarch seen from above, centred at (cx, cy), span ~2s (PIL pixel coords)."""
    for side in (-1, 1):
        fw = [(cx, cy - 0.05 * s), (cx + side * 0.25 * s, cy - 0.62 * s), (cx + side * 0.75 * s, cy - 0.78 * s),
              (cx + side * 1.0 * s, cy - 0.55 * s), (cx + side * 0.9 * s, cy - 0.15 * s), (cx + side * 0.2 * s, cy + 0.02 * s)]
        hw = [(cx, cy + 0.02 * s), (cx + side * 0.75 * s, cy + 0.05 * s), (cx + side * 0.85 * s, cy + 0.42 * s),
              (cx + side * 0.55 * s, cy + 0.72 * s), (cx + side * 0.15 * s, cy + 0.55 * s)]
        d.polygon(fw, fill=wing_col)
        d.polygon(hw, fill=wing_col)
        d.line(fw + [fw[0]], fill=vein, width=max(2, int(s * 0.08)))
        d.line(hw + [hw[0]], fill=vein, width=max(2, int(s * 0.08)))
        for k in range(1, 5):
            f = k / 5
            d.line([(cx + side * 0.1 * s, cy - 0.1 * s), (cx + side * (0.3 + 0.65 * f) * s, cy - (0.75 - 0.5 * f) * s)],
                   fill=vein, width=max(1, int(s * 0.04)))
            d.line([(cx + side * 0.1 * s, cy + 0.08 * s), (cx + side * (0.3 + 0.5 * f) * s, cy + (0.15 + 0.5 * f) * s)],
                   fill=vein, width=max(1, int(s * 0.04)))
        for k in range(6):  # white dots on the wing edges
            f = k / 6
            px = cx + side * (0.55 + 0.4 * f) * s
            py = cy - (0.7 - 0.6 * f) * s
            r = s * 0.025
            d.ellipse([px - r, py - r, px + r, py + r], fill=(250, 250, 240, 255))
    d.ellipse([cx - 0.07 * s, cy - 0.45 * s, cx + 0.07 * s, cy + 0.5 * s], fill=vein)
    d.line([(cx, cy - 0.45 * s), (cx - 0.25 * s, cy - 0.85 * s)], fill=vein, width=max(1, int(s * 0.03)))
    d.line([(cx, cy - 0.45 * s), (cx + 0.25 * s, cy - 0.85 * s)], fill=vein, width=max(1, int(s * 0.03)))


def papel():
    N = 1024 * SS
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cell = N // 2
    colours = [(255, 196, 40, 255), (235, 50, 60, 255), (70, 190, 80, 255)]
    rng = np.random.default_rng(7)
    for i, col in enumerate(colours):
        ox, oy = (i % 2) * cell, (i // 2) * cell
        m = int(cell * 0.03)
        w, h = cell - 2 * m, cell - 2 * m
        # paper with a zig-zag bottom edge
        pts = [(ox + m, oy + m), (ox + m + w, oy + m), (ox + m + w, oy + m + h * 0.92)]
        teeth = 12
        for k in range(teeth, -1, -1):
            px = ox + m + w * k / teeth
            py = oy + m + h * (0.92 if k % 2 == 0 else 1.0)
            pts.append((px, py))
        d.polygon(pts, fill=(18, 14, 18, 255))
        # lace: little holes in a border pattern
        for row in range(3):
            for k in range(14):
                px = ox + m + w * (k + 0.5) / 14
                for py in (oy + m + h * (0.05 + 0.04 * row), oy + m + h * (0.84 - 0.04 * row)):
                    r = cell * 0.012
                    d.ellipse([px - r, py - r, px + r, py + r], fill=(0, 0, 0, 0))
        for k in range(10):
            py = oy + m + h * (0.15 + 0.065 * k)
            for px in (ox + m + w * 0.05, ox + m + w * 0.95):
                r = cell * 0.014
                d.polygon([(px, py - r * 1.4), (px + r, py), (px, py + r * 1.4), (px - r, py)], fill=(0, 0, 0, 0))
        # the monarch: coloured tissue wings with black veins
        monarch(d, ox + cell / 2, oy + cell * 0.47, cell * 0.36, col)
        # a few cut-outs around it
        for k in range(16):
            ang = k / 16 * math.tau
            px = ox + cell / 2 + math.cos(ang) * cell * 0.41
            py = oy + cell * 0.47 + math.sin(ang) * cell * 0.33
            r = cell * 0.012
            d.ellipse([px - r, py - r, px + r, py + r], fill=(0, 0, 0, 0))
    # cell 4: four monarchs (orange) for the butterflies that sit on things
    ox, oy = cell, cell
    for j in range(4):
        cx = ox + (j % 2 + 0.5) * cell / 2
        cy = oy + (j // 2 + 0.5) * cell / 2
        monarch(d, cx, cy + cell * 0.04, cell * 0.2, (240, 130, 25, 255))
    im = im.resize((1024, 1024), Image.LANCZOS)
    a = np.asarray(im, dtype=float) / 255.0
    # keep colour where alpha is 0 from bleeding black into mips: fill colour from nearest paper
    rgb = T.fill_from_mask(a[..., :3], a[..., 3] > 0.5)
    T.save(np.concatenate([rgb, a[..., 3:4]], -1), sp["out"]["papel"])


# ----------------------------------------------------------------------------------------------
# Paint atlas
# ----------------------------------------------------------------------------------------------

def paint():
    PW, PH = sp["paint_size"]
    col = np.zeros((PH, PW, 3))
    R = sp["regions"]

    def region(name):
        x, y, w, h = R[name]
        yy, xx = np.mgrid[0:h, 0:w]
        return (slice(y, y + h), slice(x, x + w)), (xx + 0.5) / w, 1 - (yy + 0.5) / h, h, w

    def painted_wood(name, c0, c1, seed):
        sl, u, v, h, w = region(name)
        brush = T.fbm((h, w), (40, 4), 4, seed=seed)
        blot = T.fbm((h, w), (5, 5), 4, seed=seed + 1)
        c = T.mix(T.hexrgb(c0), T.hexrgb(c1), 0.6 * blot + 0.4 * brush)
        grain = T.fbm((h, w), (90, 3), 3, seed=seed + 2)
        col[sl] = c * (0.92 + 0.12 * grain[..., None])
    painted_wood("teal", "#1f7f86", "#2f9aa0", 10)
    painted_wood("lime", "#b9c93a", "#d6e05a", 20)
    painted_wood("purple", "#3a2350", "#5a3a74", 30)

    # hay: straw streaks
    sl, u, v, h, w = region("hay")
    st = T.fbm((h, w), (200, 12), 3, seed=40)
    st2 = T.fbm((h, w), (60, 6), 3, seed=41)
    dark = T.fbm((h, w), (12, 12), 4, seed=42)
    c = T.mix(T.hexrgb("#7a6233"), T.hexrgb("#d9bf7a"), np.clip(st * 1.3 - 0.15, 0, 1))
    c = T.mix(c, T.hexrgb("#a89a5c"), st2 * 0.4)
    c = c * (0.7 + 0.4 * dark[..., None])
    col[sl] = c

    # table runner: dark cloth with an orange papel-picado pattern
    sl, u, v, h, w = region("runner")
    rows = np.abs(np.sin(u * math.pi * 24)) * np.abs(np.sin(v * math.pi * 6))
    patt = (T.smoothstep(0.55, 0.6, rows) * 0.8 + T.smoothstep(0.92, 0.95, np.abs(np.sin(u * math.pi * 48)))) > 0.5
    c = np.where(patt[..., None], T.hexrgb("#d9772a"), T.hexrgb("#1c1418"))
    border = (v < 0.12) | (v > 0.88)
    c = np.where(border[..., None], T.hexrgb("#c85a20"), c)
    col[sl] = T.blur(c, 0.6)

    # marigolds: dense frilly petals, orange with yellow and red variants side by side (u thirds)
    sl, u, v, h, w = region("marigold")
    fr = T.fbm((h, w), (60, 60), 4, seed=50)
    fr2 = T.fbm((h, w), (160, 160), 2, seed=51)
    petals = np.clip((fr - 0.35) * 2.2, 0, 1) * (0.7 + 0.3 * fr2)
    third = np.minimum((u * 3).astype(int), 2)
    lo = np.array([T.hexrgb("#c4500c"), T.hexrgb("#d68a0c"), T.hexrgb("#9c1d14")])[third]
    hi = np.array([T.hexrgb("#ffa21e"), T.hexrgb("#ffd23a"), T.hexrgb("#e8462a")])[third]
    col[sl] = lo * (1 - petals[..., None]) + hi * petals[..., None]

    # basket weave
    sl, u, v, h, w = region("basket")
    wu, wv = u * 12, v * 8
    over = ((np.floor(wu) + np.floor(wv)) % 2).astype(bool)
    strand = np.where(over, np.abs(np.sin(wv * math.pi)), np.abs(np.sin(wu * math.pi)))
    c = T.mix(T.hexrgb("#4a2f16"), T.hexrgb("#b88a4e"), strand ** 0.5)
    col[sl] = c * (0.85 + 0.25 * T.fbm((h, w), (20, 20), 3, seed=60)[..., None])

    # fruit swatches: (name, dark, light)
    for name, c0, c1 in (("apple_red", "#7a0f12", "#d8282a"), ("apple_green", "#4f8a1e", "#a8d84a"),
                         ("orange", "#d0600a", "#ff9a2a"), ("banana", "#c99a10", "#f6dc54"),
                         ("grape", "#2a0f38", "#6b3a8a"), ("pear", "#a8a020", "#e0d860"),
                         ("glass", "#0f3a18", "#2a8a3a"), ("skull", "#bdb8a8", "#f4f1e6")):
        sl, u, v, h, w = region(name)
        seed = sum(map(ord, name))
        n = T.fbm((h, w), (6, 6), 4, seed=seed)
        speck = np.clip((T.fbm((h, w), (60, 60), 2, seed=seed + 1) - 0.65) * 4, 0, 1)
        c = T.mix(T.hexrgb(c0), T.hexrgb(c1), 0.25 + 0.75 * n)
        c = T.mix(c, T.hexrgb(c1) * 1.1, speck * 0.4)
        col[sl] = c
    # skull face: front projection, sockets and nose and teeth (u across, v up)
    sl, u, v, h, w = region("skull")
    c = col[sl]
    eye = np.minimum(((u - 0.32) / 0.13) ** 2 + ((v - 0.52) / 0.12) ** 2, ((u - 0.68) / 0.13) ** 2 + ((v - 0.52) / 0.12) ** 2)
    nose = ((u - 0.5) / 0.05) ** 2 + ((v - 0.36) / 0.07) ** 2
    teeth = (np.abs(v - 0.2) < 0.06) & (np.abs(u - 0.5) < 0.17)
    gaps = teeth & (np.abs(np.sin((u - 0.5) * math.pi * 14)) < 0.18)
    dk = T.hexrgb("#1a1614")
    c = T.mix(c, dk, T.smoothstep(1.0, 0.7, eye))
    c = T.mix(c, dk, T.smoothstep(1.0, 0.6, nose))
    c = np.where(gaps[..., None], dk, c)
    col[sl] = c
    T.save(col, sp["out"]["paint"], quality=90)


def lights():
    S = 512
    yy, xx = np.mgrid[0:S, 0:S]
    u, v = (xx + 0.5) / S, 1 - (yy + 0.5) / S
    col = np.zeros((S, S, 3))
    # four little pumpkins colours in the top half (columns), ribs darker
    quarter = np.minimum((u * 4).astype(int), 3)
    pc = np.array([T.hexrgb("#ff7a1a"), T.hexrgb("#ffc21a"), T.hexrgb("#ff3a1a"), T.hexrgb("#ff9a2a")])[quarter]
    rib = np.abs(np.sin((u * 4 % 1) * math.pi * 8))
    lat = np.sin(np.clip((v - 0.5) * 2, 0, 1) * math.pi)
    top = v >= 0.5
    pumpkin = pc * (0.45 + 0.55 * rib[..., None] ** 0.3) * (0.5 + 0.5 * lat[..., None])
    col[top] = pumpkin[top]
    # bottom-left: vase glow (warm yellow, brighter at the bottom); bottom-right: bottle glass
    vase = (u < 0.5) & ~top
    glow = T.hexrgb("#ffc84a") * (0.4 + 0.6 * (1 - v * 2))[..., None]
    col[vase] = glow[vase]
    bottle = (u >= 0.5) & ~top
    g = T.hexrgb("#1fd04a") * (0.25 + 0.35 * T.fbm((S, S), (8, 8), 3, seed=5))[..., None]
    col[bottle] = g[bottle]
    T.save(col, sp["out"]["lights"], quality=92)
    # flame gradient
    fy = np.linspace(1, 0, 128)[:, None] * np.ones((1, 32))
    fx = np.abs(np.linspace(-1, 1, 32))[None, :] * np.ones((128, 1))
    core = T.smoothstep(0.75, 0.0, fy) * T.smoothstep(1.0, 0.2, fx)
    f = T.mix(T.hexrgb("#ff6a10"), T.hexrgb("#fff2b0"), core)
    T.save(f, sp["out"]["flame"], quality=95)


crest()
papel()
paint()
lights()
