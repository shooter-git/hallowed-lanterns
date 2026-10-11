# SPDX-License-Identifier: MIT
"""Paints the lantern lounge's textures (used by lounge.py).

wood     1024 x 1024: eight weathered pallet boards, one per 128 px row (u along the board,
         1024 px = 1.2 m); some grey, some stained red-brown, one painted blue.
hay      1024 x 1024 straw (u along the bale) + normal map; the right-most 64 px are twine.
throw    1024 x 1024: black fleece with coral-red dragons, waves and auspicious clouds.
reed     1024 x 1024 RGBA: 1 m x 2 m of split reed fencing; alpha = the gaps and ragged tops.
lantern  512 x 256: the red lantern's skin (u around, v up) with its glowing slits.
"""

import math

import numpy as np
from PIL import Image, ImageDraw

import texlib as T

sp = T.spec()


def wood():
    N = 1024
    img = np.zeros((N, N, 3))
    rng = np.random.default_rng(1)
    tones = [("#7d6a55", "#a8927a"), ("#6f4a36", "#9a6a4e"), ("#8a8378", "#b5ad9e"), ("#5a3a2c", "#84584a"),
             ("#7a705e", "#a6977c"), ("#2f4f8a", "#4a6aa8"), ("#6a5240", "#94765c"), ("#7f7a70", "#aaa396")]
    for r, (c0, c1) in enumerate(tones):
        h = 128
        grain = T.fbm((h, N), (40, 3), 5, seed=10 + r)
        rings = np.sin((np.linspace(0, 1, h)[:, None] * rng.uniform(8, 16) + 2.5 * T.fbm((h, N), (4, 2), 3, seed=30 + r)) * np.pi * 2) * 0.5 + 0.5
        c = T.mix(T.hexrgb(c0), T.hexrgb(c1), grain)
        c = c * (0.85 + 0.15 * rings[..., None])
        weather = T.fbm((h, N), (6, 4), 4, seed=50 + r)
        c = T.mix(c, T.hexrgb("#8e8a82"), T.smoothstep(0.55, 0.8, weather) * 0.45)
        yy, xx = np.mgrid[0:h, 0:N]
        for _ in range(4):   # knots and nail holes
            cx, cy = rng.uniform(0, N), rng.uniform(10, h - 10)
            d = ((xx - cx) / rng.uniform(8, 18)) ** 2 + ((yy - cy) / rng.uniform(5, 9)) ** 2
            c = T.mix(c, T.hexrgb("#3a2618"), T.smoothstep(1.0, 0.2, d) * 0.85)
        for cx in (40, N // 2, N - 40):
            for cy in (h * 0.3, h * 0.7):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) / 16
                c = T.mix(c, T.hexrgb("#1a1410"), T.smoothstep(1.0, 0.3, d))
        # darker edges (the board's arrises)
        edge = T.smoothstep(6, 0, np.minimum(yy, h - 1 - yy))
        c = c * (1 - 0.3 * edge[..., None])
        img[r * h:(r + 1) * h] = c
    T.save(img, sp["out"]["wood"], quality=90)


def hay():
    N = 1024
    SS = 2
    rng = np.random.default_rng(2)
    im = Image.new("RGB", (N * SS, N * SS), (88, 76, 50))
    hm = Image.new("L", (N * SS, N * SS), 40)
    d = ImageDraw.Draw(im)
    dh = ImageDraw.Draw(hm)
    W = (N - 64) * SS
    for layer in range(4):
        for _ in range(9000):
            x, y = rng.uniform(-60, W + 60), rng.uniform(-20, N * SS + 20)
            a = rng.normal(0, 0.18 + 0.1 * (layer == 3))
            ln = rng.uniform(40, 160) * SS
            g = rng.uniform(0.5, 1.0) * (0.6 + 0.13 * layer)
            col = (int(128 * g + 62), int(110 * g + 52), int(72 * g + 28))
            w = int(rng.uniform(1.5, 3.2) * SS)
            pts = [(x, y), (x + math.cos(a) * ln, y + math.sin(a) * ln)]
            d.line(pts, fill=col, width=w)
            dh.line(pts, fill=int(80 + 45 * layer * g), width=w)
    im = im.resize((N, N), Image.LANCZOS)
    hm = hm.resize((N, N), Image.LANCZOS)
    c = np.asarray(im, dtype=float) / 255
    h = np.asarray(hm, dtype=float) / 255
    # flakes: the compressed slices of a bale, every ~11 cm along it
    u = (np.arange(N) + 0.5) / N
    flake = np.abs(np.sin(u * np.pi * 8 + 0.6 * np.sin(u * 23)))[None, :] ** 0.25
    c = c * (0.75 + 0.25 * flake[..., None])
    h = h * (0.7 + 0.3 * flake)
    c = c * (0.85 + 0.3 * T.fbm((N, N), (6, 6), 3, seed=3)[..., None])
    # twine
    tw = np.zeros((N, 64, 3))
    yy, xx = np.mgrid[0:N, 0:64]
    twist = np.abs(np.sin((yy + xx * 0.6) * 0.5))
    tw[:] = T.mix(T.hexrgb("#b07a34"), T.hexrgb("#e2b060"), twist)
    c[:, N - 64:] = tw
    h[:, N - 64:] = twist * 0.6
    T.save(c, sp["out"]["hay"], quality=88)
    T.save(T.normal_from_height(T.blur(h, 0.7), strength=5.0, wrap=False)[::2, ::2], sp["out"]["hay_n"], quality=90)


def spiral_pts(cx, cy, r0, turns, sgn=1, n=60):
    pts = []
    for k in range(n):
        t = k / (n - 1)
        a = sgn * t * turns * math.tau
        r = r0 * (1 - 0.85 * t)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def throw():
    N = 1024
    SS = 2
    S = N * SS
    rng = np.random.default_rng(7)
    im = Image.new("RGB", (S, S), (14, 11, 20))
    d = ImageDraw.Draw(im)
    coral = (232, 110, 92)
    red = (196, 40, 44)
    pink = (238, 168, 150)
    dark = (14, 11, 20)
    # background waves: thin navy and coral swirl lines
    for _ in range(26):
        cx, cy = rng.uniform(0, S), rng.uniform(0, S)
        pts = spiral_pts(cx, cy, rng.uniform(60, 180) * SS / 2, rng.uniform(1.2, 2.2), rng.choice([-1, 1]))
        d.line(pts, fill=(40, 46, 92), width=3 * SS)
    for _ in range(40):
        x0, y0 = rng.uniform(0, S), rng.uniform(0, S)
        a = rng.uniform(0, math.tau)
        pts = [(x0 + k * 14 * SS * math.cos(a) + 18 * SS * math.sin(k * 0.6), y0 + k * 14 * SS * math.sin(a) + 18 * SS * math.cos(k * 0.6))
               for k in range(14)]
        d.line(pts, fill=(150, 60, 60), width=2 * SS)

    # auspicious clouds: clusters of round lobes, each ending in a curl
    def cloud(cx, cy, s):
        lobes = [(-1.0, 0.1, 0.55), (-0.45, -0.35, 0.65), (0.25, -0.4, 0.7), (0.9, 0.0, 0.6), (0.3, 0.35, 0.55),
                 (-0.4, 0.4, 0.5)]
        for lx, ly, lr in lobes:
            r = lr * s
            d.ellipse([cx + lx * s - r, cy + ly * s - r, cx + lx * s + r, cy + ly * s + r], fill=pink)
        for lx, ly, lr in lobes:
            r = lr * s
            d.arc([cx + lx * s - r, cy + ly * s - r, cx + lx * s + r, cy + ly * s + r], 180, 360, fill=dark, width=3 * SS)
            d.line(spiral_pts(cx + lx * s, cy + ly * s, r * 0.75, 1.3, 1, 40), fill=(200, 110, 100), width=3 * SS)
    for _ in range(5):
        cloud(rng.uniform(0.1, 0.9) * S, rng.uniform(0.1, 0.9) * S, rng.uniform(70, 120) * SS)

    # dragons: a long S-curved body with belly scales and a spiny back, a maned head
    def dragon(x0, y0, ang, L, w, seed):
        r = np.random.default_rng(seed)
        pts = []
        a = ang
        x, y = x0, y0
        for k in range(120):
            a += 0.06 * math.sin(k * 0.11 + seed) + r.normal(0, 0.01)
            x += math.cos(a) * L / 120
            y += math.sin(a) * L / 120
            pts.append((x, y, a))
        for k in range(len(pts) - 1):   # spines
            if k % 4 == 0 and 4 < k < len(pts) - 8:
                x, y, a = pts[k]
                ww = w * (1 - 0.7 * k / len(pts))
                nx, ny = -math.sin(a), math.cos(a)
                tip = (x + nx * ww * 1.3 + math.cos(a) * ww * 0.6, y + ny * ww * 1.3 + math.sin(a) * ww * 0.6)
                d.polygon([(x + nx * ww * 0.4 - math.cos(a) * ww * 0.35, y + ny * ww * 0.4 - math.sin(a) * ww * 0.35),
                           tip, (x + nx * ww * 0.4 + math.cos(a) * ww * 0.35, y + ny * ww * 0.4 + math.sin(a) * ww * 0.35)],
                          fill=red)
        for k in range(len(pts)):       # the body
            x, y, a = pts[k]
            ww = w * (1 - 0.7 * k / len(pts))
            d.ellipse([x - ww * 0.55, y - ww * 0.55, x + ww * 0.55, y + ww * 0.55], fill=coral)
        for k in range(0, len(pts), 2):  # scales
            x, y, a = pts[k]
            ww = w * (1 - 0.7 * k / len(pts))
            nx, ny = -math.sin(a), math.cos(a)
            for j in (-0.3, 0.0, 0.3):
                cx, cy = x + nx * ww * j, y + ny * ww * j
                rr = ww * 0.16
                d.arc([cx - rr, cy - rr, cx + rr, cy + rr], math.degrees(a) + 90, math.degrees(a) + 270, fill=red, width=2 * SS)
        for k in range(len(pts)):       # belly line
            if k % 3 == 0:
                x, y, a = pts[k]
                ww = w * (1 - 0.7 * k / len(pts))
                nx, ny = -math.sin(a), math.cos(a)
                d.line([(x - nx * ww * 0.5, y - ny * ww * 0.5), (x - nx * ww * 0.28, y - ny * ww * 0.28)], fill=pink, width=3 * SS)
        # head at the start: a blunt wedge, eye, mane of flame curls, whiskers
        x, y, a = pts[0]
        ca, sa = math.cos(a), math.sin(a)
        hw = w * 0.75

        def P(u, v):
            return (x + (-u) * ca * hw - v * sa * hw, y + (-u) * sa * hw + v * ca * hw)
        d.polygon([P(-0.4, -0.7), P(1.5, -0.5), P(1.9, -0.1), P(1.7, 0.35), P(0.6, 0.7), P(-0.4, 0.6)], fill=coral)
        d.polygon([P(1.2, 0.0), P(1.95, 0.1), P(1.6, 0.4)], fill=red)
        ex, ey = P(0.7, 0.25)
        d.ellipse([ex - hw * 0.14, ey - hw * 0.1, ex + hw * 0.14, ey + hw * 0.1], fill=(255, 220, 120))
        d.ellipse([ex - hw * 0.05, ey - hw * 0.05, ex + hw * 0.05, ey + hw * 0.05], fill=dark)
        for k in range(7):
            sx, sy = P(-0.2, -0.6 + k * 0.2)
            d.line(spiral_pts(sx - ca * hw * 0.6, sy - sa * hw * 0.6, hw * 0.6, 0.9, 1 if k % 2 else -1, 30),
                   fill=red, width=5 * SS)
        for sgn in (-1, 1):
            wx, wy = P(1.7, 0.1 * sgn)
            d.line([(wx, wy)] + [P(1.9 + 0.5 * t, sgn * (0.3 + 0.6 * t) + 0.25 * math.sin(t * 6)) for t in np.linspace(0, 1, 10)],
                   fill=pink, width=3 * SS)
        # claws: three little feet along the body
        for k in (30, 60, 90):
            x2, y2, a2 = pts[k]
            ww = w * (1 - 0.7 * k / len(pts))
            nx, ny = math.sin(a2), -math.cos(a2)
            fx, fy = x2 + nx * ww * 0.9, y2 + ny * ww * 0.9
            d.line([(x2, y2), (fx, fy)], fill=coral, width=int(ww * 0.3))
            for j in (-1, 0, 1):
                d.line([(fx, fy), (fx + nx * ww * 0.35 + math.cos(a2) * j * ww * 0.25, fy + ny * ww * 0.35 + math.sin(a2) * j * ww * 0.25)],
                       fill=red, width=3 * SS)
    dragon(0.15 * S, 0.30 * S, 0.25, 1.15 * S, 90 * SS, 3)
    dragon(0.90 * S, 0.78 * S, math.pi + 0.35, 1.05 * S, 80 * SS, 5)
    # flames / fire pearls
    for _ in range(6):
        cx, cy = rng.uniform(0.1, 0.9) * S, rng.uniform(0.1, 0.9) * S
        for k in range(5):
            a = -math.pi / 2 + (k - 2) * 0.35
            d.line([(cx, cy), (cx + math.cos(a) * 60 * SS, cy + math.sin(a) * 60 * SS)], fill=red, width=6 * SS)
        d.ellipse([cx - 22 * SS, cy - 22 * SS, cx + 22 * SS, cy + 22 * SS], fill=coral)
    im = im.resize((N, N), Image.LANCZOS)
    c = np.asarray(im, dtype=float) / 255
    fuzz = T.fbm((N, N), (200, 200), 2, seed=9)
    c = c * (0.85 + 0.25 * fuzz[..., None])
    # hem
    yy, xx = np.mgrid[0:N, 0:N]
    hem = (np.minimum(np.minimum(xx, N - 1 - xx), np.minimum(yy, N - 1 - yy)) < 10)
    c[hem] = c[hem] * 0.5 + np.array([0.6, 0.25, 0.2]) * 0.5
    T.save(c, sp["out"]["throw"], quality=90)


def reed():
    N = 1024
    rng = np.random.default_rng(11)
    col = np.zeros((N, N, 3))
    alpha = np.zeros((N, N))
    x = 0.0
    yy = np.arange(N)[:, None]
    while x < N:
        w = rng.uniform(5, 11)
        gap = rng.choice([0, 0, 0, 1, 1, 2, 3])
        x0, x1 = int(x), int(min(x + w, N))
        if x1 <= x0:
            break
        top = int(rng.uniform(0, 34))   # ragged tops (px from the top; 1 px = ~2 mm)
        tone = rng.uniform(0.75, 1.15)
        base = T.mix(T.hexrgb("#a68a5a"), T.hexrgb("#d6bf8c"), rng.uniform(0, 1)) * tone
        split = rng.random() < 0.5   # split reeds show the paler inside
        xs = np.arange(x0, x1)
        f = (xs - x0 + 0.5) / max(x1 - x0, 1)
        shade = 0.72 + 0.28 * np.sin(np.pi * f) ** 0.5
        if split:
            shade = 0.85 + 0.15 * np.sin(np.pi * f)
            base = T.mix(base, T.hexrgb("#e6d6ac"), 0.35)
        nodes = np.zeros(N)
        for ny in np.arange(rng.uniform(0, 140), N, rng.uniform(120, 170)):
            nodes += np.exp(-((np.arange(N) - ny) / 3.0) ** 2)
        c = base[None, None, :] * shade[None, :, None] * (1 - 0.35 * np.clip(nodes, 0, 1))[:, None, None]
        streak = T.fbm((N, x1 - x0), (30, 1), 2, seed=int(x))[..., None]
        c = c * (0.9 + 0.2 * streak)
        col[:, x0:x1] = c
        a = np.ones((N, x1 - x0))
        a[:top] = 0
        if rng.random() < 0.3:   # a slanted cut
            for i in range(x1 - x0):
                a[top:top + int(i * rng.uniform(0.5, 1.5)), i] = 0
        alpha[:, x0:x1] = a
        x += w + gap
    # binding wires, 15 cm below the top and 15 cm above the bottom (y in px: 2 mm each)
    for wy in (90, N - 75):
        band = np.exp(-((np.arange(N) - wy) / 2.0) ** 2)[:, None]
        col = col * (1 - 0.6 * band[..., None]) + np.array([0.12, 0.11, 0.1]) * 0.6 * band[..., None]
        alpha = np.maximum(alpha, (band > 0.3) * 1.0)
    rgb = T.fill_from_mask(col, alpha > 0.5)
    T.save(np.concatenate([rgb, alpha[..., None]], -1), sp["out"]["reed"])


def lantern():
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, 1 - (np.arange(H) + 0.5) / H)
    ribs = sp["lantern_ribs"]
    rib = np.abs(np.sin(u * np.pi * ribs))
    lat = np.sin(np.pi * v)
    body = T.mix(T.hexrgb("#a8121e"), T.hexrgb("#f0303a"), (0.55 + 0.45 * rib ** 0.3) * (0.5 + 0.5 * lat))
    # slits: four groups around, five slits each, longest in the middle
    slit = np.zeros((H, W))
    for g in range(4):
        cu = g / 4
        for k in range(5):
            sv = 0.27 + k * 0.115
            half = 0.05 * math.sqrt(max(1 - ((sv - 0.5) / 0.32) ** 2, 0.05)) + 0.012
            du = np.abs(((u - cu + 0.5) % 1.0) - 0.5)
            m = T.smoothstep(half + 0.004, half - 0.004, du) * T.smoothstep(0.019, 0.013, np.abs(v - sv))
            slit = np.maximum(slit, m)
    glow_slit = T.mix(T.hexrgb("#ff9a3a"), T.hexrgb("#ffe08a"), 0.6)
    base = T.mix(body, glow_slit, slit)
    emis = T.mix(body * (0.55 + 0.25 * lat[..., None]), glow_slit, slit)
    T.save(base, sp["out"]["lantern"], quality=92)
    T.save(emis, sp["out"]["lantern_e"], quality=92)


wood()
hay()
throw()
reed()
lantern()
