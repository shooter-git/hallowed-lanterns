# SPDX-License-Identifier: MIT
"""Paints the Sweet Hollow candy textures (used by candy.py).

Every texture keeps its right-most 32 px column for the shared bits: the top half is the white
plastic of sticks and poles, the bottom half the green of pumpkin stems.

bucket    2048 x 1024: rows 0-767 the outside (u around, rim at the top), painted orange with
          the jack-o'-lantern face; rows 768-1023 the inside (darker, scuffed).
handle    256 x 64: the glowing tube wound round the handle.
corn      512 x 1024: candy-corn board (u across, v up).
gummy     512 x 512: neutral grey gummy skin with painted highlights (tinted by the material's
          colour factor); the dark eyes in the bottom-left corner.
lollipop  1024 x 512: rainbow swirl round the stem pole (v = 1).
skewer    512 x 256: beach-ball wedges, u around (10 lobes).
cakepop   512 x 512: red glitter, dipped dark green at the bottom.
"""

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

import texlib as T

sp = T.spec()


def misc_column(img):
    H = img.shape[0]
    img[: H // 2, -32:] = T.hexrgb("#f4f2ec")
    img[H // 2:, -32:] = T.hexrgb("#3f7a2a")
    return img


def grid(W, H):
    yy, xx = np.mgrid[0:H, 0:W]
    return (xx + 0.5) / W, 1 - (yy + 0.5) / H


def bucket():
    W, H = 2048, 1024
    img = np.zeros((H, W, 3))
    b = sp["bucket"]
    rx, rz, vcut, ribs = b["rx"], b["rz"], b["vcut"], b["ribs"]
    # outside
    Ho = 768
    u, vf = grid(W, Ho)
    v = vf * vcut
    R = rx * np.sin(np.pi * v) ** 0.85
    zm = rz * (1 - np.cos(np.pi * v))
    xm = ((u - 0.75 + 0.5) % 1.0 - 0.5) * 2 * np.pi * np.maximum(R, 1e-3)
    g = u * ribs
    dg = np.abs(g - np.round(g))
    lobe = T.smoothstep(0.0, 0.35, dg)
    base = T.mix(T.hexrgb("#a83a12"), T.hexrgb("#ec6a22"), lobe)
    base = T.mix(base, T.hexrgb("#f68a3a"), T.smoothstep(0.3, 0.5, dg) * 0.35 * np.sin(np.pi * v))
    mott = T.fbm((Ho, W), (6, 40), 4, seed=1)
    base = base * (0.88 + 0.2 * mott[..., None])
    dirt = T.smoothstep(0.35, 0.0, zm / (2 * rz)) * T.fbm((Ho, W), (10, 60), 3, seed=2)
    base = T.mix(base, T.hexrgb("#5a3418"), dirt * 0.6)
    scuff = np.clip((T.fbm((Ho, W), (40, 300), 2, seed=3) - 0.78) * 5, 0, 1)
    base = T.mix(base, T.hexrgb("#f4a070"), scuff * 0.2)
    # the face, drawn in (x, z) metres on a canvas and looked up
    C = 1024
    ext = (-1.3, 1.3, 0.0, 2.0)
    cv = Image.new("L", (C, C), 0)
    d = ImageDraw.Draw(cv)

    def P(x, z):
        return ((x - ext[0]) / (ext[1] - ext[0]) * C, (1 - (z - ext[2]) / (ext[3] - ext[2])) * C)
    for poly in b["face"]:
        d.polygon([P(x, z) for x, z in poly], fill=255)
    face = np.asarray(cv, dtype=float) / 255
    face_soft = T.blur(face, 2.0)
    cx = (xm - ext[0]) / (ext[1] - ext[0]) * C
    cz = (1 - (zm - ext[2]) / (ext[3] - ext[2])) * C
    fm = ndimage.map_coordinates(face, [cz.ravel(), cx.ravel()], order=1, mode="constant").reshape(Ho, W)
    fe = ndimage.map_coordinates(face_soft, [cz.ravel(), cx.ravel()], order=1, mode="constant").reshape(Ho, W)
    front = (np.abs(xm) < 1.3)
    fm *= front
    fe *= front
    ink = T.mix(T.hexrgb("#151012"), T.hexrgb("#2a1c18"), T.fbm((Ho, W), (20, 60), 3, seed=4))
    base = T.mix(base, T.hexrgb("#5a2410"), np.clip(fe * 1.6 - fm, 0, 1) * 0.6)
    base = T.mix(base, ink, fm)
    img[:Ho] = base
    # inside
    u2, v2 = grid(W, H - Ho)
    n = T.fbm((H - Ho, W), (6, 40), 4, seed=5)
    img[Ho:] = T.mix(T.hexrgb("#6a2a0e"), T.hexrgb("#b04a18"), n)
    T.save(misc_column(img), sp["out"]["bucket"], quality=90)
    # glowing handle tube: white with soft rainbow tints along its length
    hu, hv = grid(256, 64)
    hue = np.stack([0.5 + 0.5 * np.cos(2 * np.pi * (hu * 3 + k / 3)) for k in range(3)], -1)
    tint = T.smoothstep(0.55, 0.9, np.abs(np.sin(hu * np.pi * 5)))
    h = T.mix(np.ones(3) * 0.95, 0.4 + 0.6 * hue, tint * 0.6)
    T.save(h, sp["out"]["handle"], quality=92)


def corn():
    W, H = 512, 1024
    u, v = grid(W, H)
    wob = 0.012 * np.sin(u * 9 + 1) + 0.006 * np.sin(u * 23)
    yel, ora, wht = T.hexrgb("#f7c22e"), T.hexrgb("#f08422"), T.hexrgb("#f6f3ea")
    c = np.where((v < sp["corn_bands"][0] + wob)[..., None], yel,
                 np.where((v < sp["corn_bands"][1] + wob)[..., None], ora, wht))
    brush = T.fbm((H, W), (60, 6), 4, seed=11)
    blot = T.fbm((H, W), (6, 4), 4, seed=12)
    c = c * (0.9 + 0.12 * brush[..., None]) * (0.95 + 0.08 * blot[..., None])
    grime = T.smoothstep(0.12, 0.0, v) * T.fbm((H, W), (10, 20), 3, seed=13)
    c = T.mix(c, T.hexrgb("#6a5030"), grime * 0.5)
    T.save(misc_column(c), sp["out"]["corn"], quality=90)


def gummy():
    S = 512
    u, v = grid(S, S)
    n = T.fbm((S, S), (6, 6), 4, seed=21)
    c = np.ones((S, S, 3)) * (0.78 + 0.18 * n[..., None])
    rib = np.abs(np.sin(u * np.pi * 8))
    c = c * (0.82 + 0.18 * rib[..., None] ** 0.4)
    # painted highlights: short white strokes, as in the photo
    hl = np.zeros((S, S))
    rng = np.random.default_rng(22)
    im = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(im)
    for _ in range(30):
        x, y = rng.uniform(0, S), rng.uniform(S * 0.2, S * 0.85)
        ln = rng.uniform(10, 40)
        d.line([(x, y), (x + ln * 0.3, y - ln)], fill=255, width=int(rng.uniform(4, 9)))
    hl = T.blur(np.asarray(im, dtype=float) / 255, 1.5)
    c = T.mix(c, np.ones(3) * 1.6, hl * 0.7)
    c = np.clip(c, 0, 1)
    c[int(S * 0.85):, :64] = 0.04   # eyes and nose
    T.save(misc_column(c), sp["out"]["gummy"], quality=90)


def lollipop():
    W, H = 1024, 512
    u, v = grid(W, H)
    pole = 1 - v                     # 0 at the stem pole, 1 at the far side
    ang = (u + 0.9 * pole) % 1.0     # the swirl
    k = (ang * 12).astype(int) % 6
    cols = np.array([T.hexrgb(h) for h in ("#e8282a", "#f88a1a", "#f8d82a", "#3ab84a", "#2a6ae8", "#8a3ac8")])
    c = cols[k]
    edge = np.abs((ang * 12) % 1 - 0.5)
    c = c * (0.85 + 0.15 * T.smoothstep(0.5, 0.3, edge)[..., None])
    brush = T.fbm((H, W), (20, 80), 3, seed=31)
    c = c * (0.9 + 0.15 * brush[..., None])
    star_r = 0.10 + 0.05 * np.abs(np.sin(u * np.pi * 7))
    star = T.smoothstep(star_r + 0.01, star_r - 0.01, pole)
    c = T.mix(c, T.hexrgb("#f6f2ea"), star)
    T.save(misc_column(c), sp["out"]["lollipop"], quality=90)


def skewer():
    W, H = 512, 256
    u, v = grid(W, H)
    lobes = sp["skewer_ribs"]
    k = np.floor(u * lobes).astype(int) % lobes
    seq = ["#2fae4a", "#f6d02a", "#2a7ae0", "#e8402a", "#8a3ac8", "#f88a1a", "#2fae4a", "#f6d02a", "#2a7ae0", "#e8402a"]
    cols = np.array([T.hexrgb(seq[i % len(seq)]) for i in range(lobes)])
    c = cols[k]
    g = u * lobes
    dg = np.abs(g - np.round(g))
    c = c * (0.7 + 0.3 * T.smoothstep(0.0, 0.25, dg)[..., None])
    c = c * (0.9 + 0.15 * T.fbm((H, W), (10, 40), 3, seed=41)[..., None])
    T.save(misc_column(c), sp["out"]["skewer"], quality=90)


def cakepop():
    S = 512
    u, v = grid(S, S)
    drip = 0.36 + 0.04 * np.sin(u * np.pi * 14) + 0.03 * np.sin(u * np.pi * 6 + 1)
    red = T.mix(T.hexrgb("#7a0a14"), T.hexrgb("#d8202e"), T.fbm((S, S), (8, 8), 3, seed=51))
    grn = T.mix(T.hexrgb("#0f3a1a"), T.hexrgb("#2a6a32"), T.fbm((S, S), (8, 8), 3, seed=52))
    c = np.where((v < drip)[..., None], grn, red)
    glit = np.clip((T.fbm((S, S), (200, 200), 1, seed=53) - 0.62) * 6, 0, 1)
    c = T.mix(c, np.ones(3), glit * 0.55)
    T.save(misc_column(c), sp["out"]["cakepop"], quality=90)


bucket()
corn()
gummy()
lollipop()
skewer()
cakepop()
