# SPDX-License-Identifier: MIT
"""Paints the textures of The Web (web.py): the pumpkin spider, the praying mantis and the
web-wrapped pumpkin (reference/spider.jpg, reference/video-9602.mov).

kinds (params["kind"]):

- "spider": 2048 x 2048 base colour + 1024 x 1024 emission (the UV-reactive paint). Regions
  (pixels, rows from the top):
    abdomen (0, 0, 1024, 1024): dark maroon pumpkin, u round the ribs, v up; on the upper half of
        every lobe a jagged lightning patch: neon green outline round a zigzag orange fill.
    head (1024, 0, 1024, 768): the same maroon pumpkin skin, plain.
    stems (1024, 768, 1024, 256): dark green-black stem.
    leg (0, 1024, 1024, 256): u along a leg (root -> foot), v around: dark maroon femur
        (0-0.42), dark knee segment with cream polka dots (0.42-0.62), pale mustard lower leg.
    fang (0, 1280, 256, 256): cream.
    baby_head (256, 1280, 512, 384): green pumpkin with a kawaii face (u = 0.75 forward).
    baby_body (768, 1280, 512, 384): blue pumpkin.
    pale (1280, 1280, 256, 256): pale yellow-orange (the baby's legs).
- "eyes": 512 x 512: the spiral eye (pink disc, purple spiral), planar, centre at the middle.
- "mantis": 1024 x 1024 base (+ emission = base): regions
    tube (0, 0, 1024, 256): neon lime foam tube, faint ribs across, darker toward its ends.
    spines (0, 256, 1024, 256): lime with a blue zigzag of spines along the middle of v.
    antenna (0, 512, 1024, 128): lime with close ridges.
    abdomen (0, 640, 1024, 384): orange segmented gourd (u round, v along).
- "mantis_eye": 256 x 256: orange-red with a soft highlight (planar).
- "webpumpkin": 1024 x 1024: tan pumpkin skin (rows 0-767, u round, v up), stem (768-1023).
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


def grid(h, w):
    y, x = np.mgrid[0:h, 0:w]
    return (x + 0.5) / w, (y + 0.5) / h


def tri(x):
    return 2 * np.abs(x - np.floor(x + 0.5))


def pumpkin_skin(h, w, base, groove, ribs, seed, light=0.14):
    u, yy = grid(h, w)
    v = 1 - yy
    f = (u * ribs) % 1.0
    lobe = np.sin(np.pi * f)
    g = np.exp(-(np.minimum(f, 1 - f) / 0.07) ** 2)
    n = T.fbm((h, w), (8, 32), 4, seed=seed)
    s = T.fbm((h, w), (40, 6), 3, seed=seed + 1)
    col = T.hexrgb(base) * (0.82 + light * lobe[..., None] + 0.12 * (n[..., None] - 0.5) + 0.06 * (s[..., None] - 0.5))
    col = T.mix(col, T.hexrgb(groove), 0.6 * g)
    pole = T.smoothstep(0.86, 1.0, v) + T.smoothstep(0.12, 0.0, v)
    col = T.mix(col, T.hexrgb(groove), 0.4 * pole)
    return col, u, v, f


def spider(sp):
    S = 2048
    img = np.zeros((S, S, 3))
    em = np.zeros((S, S, 3))
    ribs = sp.get("ribs", 10)
    # abdomen with lightning patches
    col, u, v, f = pumpkin_skin(1024, 1024, "#3a1424", "#1c0810", ribs, 3)
    x = (f - 0.5) * 2                       # -1..1 across the lobe
    k = np.floor(u * ribs).astype(int)
    rng = np.random.default_rng(4)
    v0 = rng.uniform(0.46, 0.56, ribs)[k]
    v1 = rng.uniform(0.88, 0.94, ribs)[k]
    wmax = rng.uniform(0.46, 0.60, ribs)[k]
    # patches on the lobes that face up and to the front and sides (as on the real one); none behind
    show = np.array([1, 1, 0, 1, 0, 1, 1, 1, 1, 0][:ribs] + [1] * max(0, ribs - 10), bool)[k]
    t = np.clip((v - v0) / (v1 - v0), 0, 1)
    w = wmax * np.sin(np.pi * t) ** 0.45 * ((v > v0) & (v < v1)) * show
    jag = 0.10 * (tri(v * 90) - 0.5) + 0.06 * (tri(v * 21 + 0.3) - 0.5)
    edge = np.abs(x) - (w + jag)
    green_l = (edge < 0) & (edge > -0.08) & (w > 0.05)
    # the fill: orange zigzag hatching (lightning strokes running round the lobe)
    strokes = np.zeros_like(x, dtype=bool)
    for c, ph, fr in ((-0.42, 0.0, 52), (0.0, 0.33, 47), (0.42, 0.66, 57)):
        xc = c * w + 0.16 * w * (tri(v * fr + ph) - 0.5) * 2
        strokes |= np.abs(x - xc) < 0.055 + 0.05 * w
    orange = strokes & (edge < -0.12) & (w > 0.12)
    gcol, ocol = T.hexrgb("#7cff3a"), T.hexrgb("#ff8a24")
    col = np.where(green_l[..., None], gcol, col)
    col = np.where(orange[..., None], ocol, col)
    e = np.zeros_like(col)
    e = np.where(green_l[..., None], gcol, e)
    e = np.where(orange[..., None], ocol * 0.9, e)
    img[0:1024, 0:1024] = col
    em[0:1024, 0:1024] = e
    # head pumpkin
    col, *_ = pumpkin_skin(768, 1024, "#3e1626", "#1e0912", ribs, 5)
    img[0:768, 1024:2048] = col
    # stems
    u2, y2 = grid(256, 1024)
    sn = T.fbm((256, 1024), (4, 40), 4, seed=9)
    ridge = 0.5 + 0.5 * np.cos(u2 * 2 * np.pi * 6)
    img[768:1024, 1024:2048] = T.hexrgb("#1a1a14") * (0.7 + 0.4 * ridge[..., None] + 0.3 * (sn[..., None] - 0.5))
    # leg strip
    u3, y3 = grid(256, 1024)
    n3 = T.fbm((256, 1024), (6, 30), 4, seed=12)
    dark = T.hexrgb("#2e1018") * (0.85 + 0.3 * (n3[..., None] - 0.5))
    pale = T.hexrgb("#ead27e") * (0.85 + 0.25 * (n3[..., None] - 0.5))
    pale = T.mix(pale, T.hexrgb("#8a6a2a"), 0.3 * T.smoothstep(0.6, 0.85, T.fbm((256, 1024), (3, 12), 3, seed=13))[..., None])
    leg = np.where((u3 < 0.62)[..., None], dark, pale)
    # polka dots on the knee segment (0.42..0.62), two rings of them
    dots = np.zeros(u3.shape, bool)
    for cu in (0.47, 0.52, 0.575):
        for cv in np.arange(0.0625, 1.0, 0.125) + (0.0625 if cu == 0.52 else 0.0):
            d = np.hypot((u3 - cu) * 1024 / 256 * 0.25 * 4, ((y3 - cv + 0.5) % 1.0 - 0.5))
            dots |= d < 0.038
    leg = np.where(dots[..., None], T.hexrgb("#e8d48a"), leg)
    img[1024:1280, 0:1024] = leg
    le = np.where((u3 >= 0.62)[..., None], pale * 0.35, 0.0)
    le = np.where(dots[..., None], T.hexrgb("#e8d48a") * 0.6, le)
    em[1024:1280, 0:1024] = le
    # fangs
    nf = T.fbm((256, 256), 8, 3, seed=14)
    img[1280:1536, 0:256] = T.hexrgb("#e8dcc0") * (0.9 + 0.15 * (nf[..., None] - 0.5))
    em[1280:1536, 0:256] = T.hexrgb("#e8dcc0") * 0.25
    # baby head: green pumpkin with a kawaii face
    col, u4, v4, f4 = pumpkin_skin(384, 512, "#2fa84a", "#1a6a2c", 8, 15, light=0.2)
    du = ((u4 - 0.75 + 0.5) % 1.0) - 0.5
    e4 = np.zeros_like(col)
    for s in (-1, 1):
        d = np.hypot((du - s * 0.085) / 0.065, (v4 - 0.52) / 0.13)
        rim = (d < 1.0) & (d > 0.78)
        pupil = d < 0.78
        hl = np.hypot((du - s * 0.085 + 0.02) / 0.022, (v4 - 0.57) / 0.045) < 1
        col = np.where(rim[..., None], T.hexrgb("#ffb21e"), col)
        col = np.where(pupil[..., None], T.hexrgb("#1a0c08"), col)
        col = np.where(hl[..., None], T.hexrgb("#ffffff"), col)
        e4 = np.where(rim[..., None], T.hexrgb("#ffb21e"), e4)
        e4 = np.where(hl[..., None], T.hexrgb("#ffffff") * 0.6, e4)
        blush = np.hypot((du - s * 0.13) / 0.035, (v4 - 0.40) / 0.05) < 1
        col = np.where(blush[..., None], T.hexrgb("#ff6a7a"), col)
    mouth = (np.hypot(du / 0.04, (v4 - 0.40) / 0.07) < 1) & (v4 < 0.40)
    col = np.where(mouth[..., None], T.hexrgb("#ff8a1a"), col)
    e4 = np.where(mouth[..., None], T.hexrgb("#ffa020"), e4)
    img[1280:1664, 256:768] = col
    # the baby is UV paint too: the green and blue glow, the face brightest
    em[1280:1664, 256:768] = np.maximum(e4, col * 0.55)
    col, *_ = pumpkin_skin(384, 512, "#1e48b8", "#0e2460", 8, 16, light=0.2)
    img[1280:1664, 768:1280] = col
    em[1280:1664, 768:1280] = col * 0.5
    img[1280:1536, 1280:1536] = T.hexrgb("#f2c27a")
    em[1280:1536, 1280:1536] = T.hexrgb("#f2c27a") * 0.5
    T.save(img, out(sp, "base"), quality=88)
    # emission at half resolution
    small = em.reshape(1024, 2, 1024, 2, 3).mean(axis=(1, 3))
    T.save(small, out(sp, "emit"), quality=88)


def eyes(sp):
    S = 512
    u, yy = grid(S, S)
    x, y = u * 2 - 1, yy * 2 - 1
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    # an Archimedean spiral line: r = a * theta, three turns
    turns = 3.0
    phase = (r * turns - th / (2 * np.pi)) % 1.0
    line = (np.abs(phase - 0.5) < 0.16) & (r > 0.05) & (r < 0.93)
    pink = T.hexrgb("#ff8ce0") * (0.92 + 0.12 * (1 - r[..., None]))
    col = np.where(line[..., None], T.hexrgb("#6a1e8a"), pink)
    col = np.where((r > 0.95)[..., None], T.hexrgb("#d06ac0"), col)
    T.save(col, out(sp, "tex"), quality=92)


def mantis(sp):
    S = 1024
    img = np.zeros((S, S, 3))
    lime = T.hexrgb("#b6ff4a")
    u, yy = grid(256, 1024)
    n = T.fbm((256, 1024), (6, 40), 4, seed=21)
    ribs = 0.5 + 0.5 * np.cos(u * 2 * np.pi * 40)
    tube = lime * (0.86 + 0.08 * ribs[..., None] + 0.14 * (n[..., None] - 0.5))
    ends = T.smoothstep(0.08, 0.0, u) + T.smoothstep(0.92, 1.0, u)
    tube = T.mix(tube, T.hexrgb("#e8ff70"), 0.6 * ends)
    img[0:256] = tube
    # spines: a blue zigzag along the middle (v ~ 0.5 = the inside of the foreleg)
    zz = np.abs(yy - 0.5 - 0.08 * (tri(u * 26) - 0.5) * 2) < 0.035
    teeth = (np.abs(yy - 0.5) < 0.11) & (tri(u * 26) < 0.35) & (np.abs(yy - 0.5) > 0.03)
    sp_img = np.where((zz | teeth)[..., None], T.hexrgb("#1e3ad8"), tube)
    img[256:512] = sp_img
    u5, y5 = grid(128, 1024)
    ridges = 0.5 + 0.5 * np.cos(u5 * 2 * np.pi * 70)
    img[512:640] = lime * (0.8 + 0.25 * ridges[..., None])
    # abdomen: orange gourd, ribs round, segment rings along
    u6, y6 = grid(384, 1024)
    f = (y6 * 8) % 1.0
    lobe = np.sin(np.pi * f)
    seg = 0.5 + 0.5 * np.cos(u6 * 2 * np.pi * 9)
    n6 = T.fbm((384, 1024), (8, 24), 4, seed=23)
    ab = T.hexrgb("#ff7a1a") * (0.78 + 0.18 * lobe[..., None] + 0.08 * seg[..., None] + 0.12 * (n6[..., None] - 0.5))
    ab = T.mix(ab, T.hexrgb("#b0400a"), 0.5 * np.exp(-(np.minimum(f, 1 - f) / 0.08) ** 2)[..., None])
    img[640:1024] = ab
    T.save(img, out(sp, "tex"), quality=90)


def mantis_eye(sp):
    S = 256
    u, yy = grid(S, S)
    x, y = u * 2 - 1, yy * 2 - 1
    r = np.hypot(x, y)
    col = T.hexrgb("#ff4a1a") * (0.85 + 0.15 * (1 - r[..., None]))
    n = T.fbm((S, S), 24, 3, seed=31)
    col = col * (0.92 + 0.16 * (n[..., None] - 0.5))
    hl = np.exp(-((x + 0.3) ** 2 + (y + 0.35) ** 2) / 0.03)
    col = col + hl[..., None] * np.array([0.5, 0.4, 0.3])
    T.save(np.clip(col, 0, 1), out(sp, "tex"), quality=92)


def webpumpkin(sp):
    S = 1024
    img = np.zeros((S, S, 3))
    col, *_ = pumpkin_skin(768, 1024, "#b08a68", "#6e4e36", sp.get("ribs", 9), 41, light=0.16)
    blot = T.smoothstep(0.55, 0.8, T.fbm((768, 1024), (4, 10), 4, seed=42))
    col = T.mix(col, T.hexrgb("#5e4232"), 0.35 * blot)
    img[:768] = col
    u, yy = grid(256, 1024)
    ridge = 0.5 + 0.5 * np.cos(u * 2 * np.pi * 6)
    img[768:] = T.hexrgb("#5a6a3a") * (0.75 + 0.35 * ridge[..., None])
    T.save(img, out(sp, "tex"), quality=88)


KINDS = {"spider": spider, "eyes": eyes, "mantis": mantis, "mantis_eye": mantis_eye, "webpumpkin": webpumpkin}


def main():
    sp = T.spec()
    KINDS[sp["kind"]](sp)


main()
