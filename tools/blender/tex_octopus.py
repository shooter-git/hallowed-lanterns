# SPDX-License-Identifier: MIT
"""Paints the octopus atlas (used by octopus.py).

Regions (pixel rects, rows from the top; v = 1 at the top of each region):
  pumpkin  u = longitude (rib grooves at u = k / ribs), v = latitude      purple, ribbed, ring spots
  body     u = azimuth (0.5 = front), v = latitude                         purple, ring spots
  arm      u = along the arm (root -> tip), v = around (0.25 = sucker side) maroon, gold flecks
  stem     u = along, v = around                                          fluorescent green
  sucker   radial disc (centre = hole)                                    pale green
The fluorescent paint (ring spots, suckers, the piping along the arms, the stem) also goes
into the emissive map (half resolution): under the black lights it glows.
"""

import math

import numpy as np
from PIL import Image

import texlib as T

sp = T.spec()
S = sp["size"]
R = sp["regions"]
base = np.zeros((S, S, 3))
emis = np.zeros((S, S, 3))
rng = np.random.default_rng(5)


def region(name):
    x, y, w, h = R[name]
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5) / w
    v = 1.0 - (yy + 0.5) / h
    return (slice(y, y + h), slice(x, x + w)), u, v


def wavy_ring_mask(du_m, dv_m, r0, lobes, phase, width):
    """Distance field of a wavy ring (metres) -> (ring line, inside)."""
    ang = np.arctan2(dv_m, du_m)
    rr = np.hypot(du_m, dv_m)
    rw = r0 * (1 + 0.10 * np.sin(lobes * ang + phase) + 0.04 * np.sin((lobes + 3) * ang + 2 * phase))
    d = rr - rw
    line = np.exp(-(d / width) ** 2)
    inside = T.smoothstep(width, -width, d)
    return line, inside, rr / np.maximum(rw, 1e-6)


def paint_spots(sl, u, v, spots, m_per_u, m_per_v, col, emis_col, fill):
    b = base[sl]
    e = emis[sl]
    for (su, sv, r0, lobes, phase) in spots:
        du = ((u - su + 0.5) % 1.0 - 0.5) * m_per_u(v)
        dv = (v - sv) * m_per_v
        line, inside, rel = wavy_ring_mask(du, dv, r0, lobes, phase, r0 * 0.07)
        inner, _, _ = wavy_ring_mask(du, dv, r0 * 0.55, lobes, phase + 1.3, r0 * 0.05)
        b[:] = T.mix(b, b * 0.75 + fill * 0.25, inside * 0.8)
        b[:] = T.mix(b, col, np.clip(line + 0.5 * inner, 0, 1))
        e[:] = e + emis_col * np.clip(line + 0.45 * inner, 0, 1)[..., None]


# ---- pumpkin ----
sl, u, v = region("pumpkin")
ribs = sp["ribs"]
h, w = u.shape
x = (ribs * math.pi * u) % math.pi
lobe = np.abs(np.sin(x)) ** 0.5
lat = np.sin(np.pi * v)
purple = T.hexrgb("#5a2c92")
dark = T.hexrgb("#24103f")
light = T.hexrgb("#7b4bb8")
mott = T.fbm((h, w), (6, 18), 5, seed=3)
streak = T.fbm((h, w), (3, 160), 3, seed=4)
col = T.mix(dark, purple, T.smoothstep(0.0, 0.55, lobe))
col = T.mix(col, light, 0.35 * T.smoothstep(0.75, 1.0, lobe) * lat)
col = col * (0.85 + 0.25 * mott[..., None]) * (0.93 + 0.12 * streak[..., None])
base[sl] = col
PR = sp["pumpkin_r"]
paint_spots(sl, u, v, sp["pumpkin_spots"],
            lambda vv: 2 * np.pi * PR[0] * np.maximum(np.sin(np.pi * vv), 0.15), np.pi * PR[1],
            T.hexrgb("#7fd3ee"), np.array([0.25, 0.75, 1.0]) * 0.9, T.hexrgb("#8d64d0"))

# ---- body ----
sl, u, v = region("body")
h, w = u.shape
mott = T.fbm((h, w), (8, 16), 5, seed=13)
col = T.mix(T.hexrgb("#4e2484"), T.hexrgb("#6b3aa6"), mott[..., None])
col = col * (0.85 + 0.15 * np.sin(np.pi * v)[..., None])
base[sl] = col
paint_spots(sl, u, v, sp["body_spots"],
            lambda vv: 2 * np.pi * sp["body_r"] * np.maximum(np.sin(np.pi * vv), 0.15), np.pi * sp["body_r"],
            T.hexrgb("#7fd3ee"), np.array([0.25, 0.75, 1.0]) * 0.9, T.hexrgb("#8d64d0"))

# ---- arm strip ----
sl, u, v = region("arm")
h, w = u.shape
a = v  # around: 0.25 is the sucker side
band = np.abs(((a - 0.25 + 0.5) % 1.0) - 0.5)  # distance (in a) from the sucker-side centre
top = T.hexrgb("#4a1d44")
under = T.hexrgb("#8566c4")
mott = T.fbm((h, w), (10, 40), 4, seed=21)
col = top * (0.8 + 0.4 * mott[..., None])
fleck_n = T.fbm((h, w), (90, 380), 2, seed=22, gain=0.6)
fleck2 = T.fbm((h, w), (200, 800), 1, seed=23)
gold = T.hexrgb("#e0a640")
flecks = np.clip((fleck_n - 0.56) * 9, 0, 1) * np.clip((fleck2 - 0.35) * 4, 0, 1)
flecks *= T.smoothstep(0.10, 0.16, band)
col = T.mix(col, gold * (0.8 + 0.4 * fleck2[..., None]), flecks * 0.9)
uc = T.mix(under * 0.9, under * 1.1, mott[..., None])
inside = T.smoothstep(0.125, 0.115, band)
col = T.mix(col, uc, inside)
pipe = np.exp(-((band - 0.122) / 0.006) ** 2)
pipe_col = T.hexrgb("#e6f2ff")
col = T.mix(col, pipe_col, pipe)
base[sl] = col
emis[sl] = pipe[..., None] * np.array([0.55, 0.75, 1.0]) * 0.9 + flecks[..., None] * gold * 0.12

# ---- stem ----
sl, u, v = region("stem")
h, w = u.shape
ridge = np.abs(np.sin(np.pi * 6 * v))
n1 = T.fbm((h, w), (4, 20), 3, seed=31)
col = T.mix(T.hexrgb("#2f8a3a"), T.hexrgb("#8fe07c"), (ridge ** 0.6 * (0.7 + 0.3 * n1))[..., None])
col = T.mix(col, T.hexrgb("#c8e690"), T.smoothstep(0.85, 1.0, u)[..., None] * 0.6)
base[sl] = col
emis[sl] = col * 0.45

# ---- sucker ----
sl, u, v = region("sucker")
rr = np.hypot(u - 0.5, v - 0.5) * 2
col = T.mix(T.hexrgb("#3f7f5a"), T.hexrgb("#bff5c8"), T.smoothstep(0.3, 0.5, rr)[..., None])
col = T.mix(col, T.hexrgb("#e5ffe6"), T.smoothstep(0.75, 0.86, rr)[..., None] * T.smoothstep(1.0, 0.9, rr)[..., None])
base[sl] = col
emis[sl] = col * np.array([0.6, 0.9, 0.7]) * 0.8

T.save(base, sp["out"]["base"], quality=90)
e = Image.fromarray((np.clip(emis, 0, 1) * 255).astype(np.uint8)).resize((S // 2, S // 2), Image.LANCZOS)
T.save(np.asarray(e) / 255.0, sp["out"]["emit"], quality=90)

# ---- eyes: equirectangular, pupil at u = 0.75 (front), v = 0.5 ----
EW, EH = 512, 256
yy, xx = np.mgrid[0:EH, 0:EW]
u = (xx + 0.5) / EW
v = 1 - (yy + 0.5) / EH
du = (u - 0.75) * 2 * np.pi        # radians of longitude
dv = (v - 0.5) * np.pi             # radians of latitude
wav = 0.022 * np.sin(du * 9 + 0.4) + 0.016 * np.sin(du * 5 + 1)
px = np.abs(du) / 0.80
py = np.abs(dv) / (0.40 - 0.07 * np.exp(-(du / 0.28) ** 2) + wav)   # a soft, slightly waisted slot
pd = (px ** 4 + py ** 4) ** 0.25    # rounded rectangle
pupil = T.smoothstep(1.04, 0.96, pd)
glow_core = T.smoothstep(1.0, 0.2, pd)
eyeball = T.mix(T.hexrgb("#3a1a6e"), T.hexrgb("#5a2e98"), T.fbm((EH, EW), (4, 8), 3, seed=41)[..., None])
iris_ring = np.exp(-((pd - 1.25) / 0.12) ** 2)
eyeball = T.mix(eyeball, T.hexrgb("#2a0f45"), iris_ring[..., None] * 0.7)
pcol = T.mix(T.hexrgb("#ff6a10"), T.hexrgb("#ffd25a"), glow_core[..., None])
eb = T.mix(eyeball, pcol, pupil[..., None])
ee = pcol * pupil[..., None]
T.save(eb, sp["out"]["eye_base"], quality=92)
T.save(ee, sp["out"]["eye_emit"], quality=92)
