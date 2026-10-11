# SPDX-License-Identifier: MIT
"""Paints the pufferfish (used by pufferfish.py).

skin  1024 x 512: the pumpkin body (u around, rib grooves at u = k / ribs; v bottom -> top) in
      the left 768 px, painted lime UV paint with darker green and violet spots, a paler belly;
      the right 256 px hold the fins (teal with darker rays, u along the fin) and the stem and
      lips swatches. Emission = the same at half strength (UV paint under black light).
eye   256 x 128 equirectangular eye: the pupil looks along u = 0.75 (the eye's outward axis):
      a dark pupil, a pale iris and the glowing red-orange ring round it.
"""

import numpy as np

import texlib as T

sp = T.spec()
W, H = 1024, 512
BW = 768
img = np.zeros((H, W, 3))
yy, xx = np.mgrid[0:H, 0:BW]
u = (xx + 0.5) / BW
v = 1 - (yy + 0.5) / H
ribs = sp["ribs"]
g = u * ribs
dg = np.abs(g - np.round(g))
lime, deep, pale = T.hexrgb("#8af03a"), T.hexrgb("#2f9a3a"), T.hexrgb("#d6ff8a")
col = T.mix(deep, lime, T.smoothstep(0.0, 0.3, dg))
col = T.mix(col, pale, T.smoothstep(0.45, 0.2, v) * 0.45)          # paler belly
col = col * (0.9 + 0.15 * T.fbm((H, BW), (6, 24), 4, seed=1)[..., None])
rng = np.random.default_rng(3)
for k in range(26):
    cu, cv = rng.uniform(0, 1), rng.uniform(0.35, 0.9)
    r = rng.uniform(0.025, 0.05)
    du = ((u - cu + 0.5) % 1.0 - 0.5) * 2 * np.sin(np.pi * np.clip(v, 0.05, 0.95))
    d = np.hypot(du, (v - cv) * 0.5)
    wob = 1 + 0.2 * np.sin(np.arctan2(v - cv, du) * 5 + k)
    m = T.smoothstep(r * wob, r * wob * 0.8, d)
    tone = T.hexrgb("#7a4ad8") if k % 3 == 0 else T.hexrgb("#1f6a2a")
    col = T.mix(col, tone, m * 0.9)
img[:, :BW] = col
# fins: teal membrane with rays, u along the fin (root -> edge)
fy, fx = np.mgrid[0:H // 2, 0:256]
fu, fv = (fx + 0.5) / 256, (fy + 0.5) / (H // 2)
rays = np.abs(np.sin(fv * np.pi * 9)) ** 3
fin = T.mix(T.hexrgb("#3ad6c0"), T.hexrgb("#a8fff0"), fu * 0.6) * (1 - 0.35 * rays[..., None])
img[:H // 2, BW:] = fin
img[H // 2:H * 3 // 4, BW:] = T.hexrgb("#4a8a2a")                  # stem
img[H * 3 // 4:, BW:] = T.hexrgb("#ff6aa8")                          # lips
T.save(img, sp["out"]["skin"], quality=90)
T.save(img * 0.5, sp["out"]["skin_e"], quality=90)

EW, EH = 256, 128
ey, ex = np.mgrid[0:EH, 0:EW]
eu, ev = (ex + 0.5) / EW, 1 - (ey + 0.5) / EH
# angular distance from the eye's axis (u = 0.75, v = 0.5)
lon = (eu - 0.75) * 2 * np.pi
lat = (ev - 0.5) * np.pi
ang = np.arccos(np.clip(np.cos(lat) * np.cos(lon), -1, 1))
pupil = T.smoothstep(0.42, 0.38, ang)
ring = T.smoothstep(0.62, 0.56, ang) * (1 - T.smoothstep(0.48, 0.42, ang))
iris = T.smoothstep(0.80, 0.74, ang)
base = T.mix(T.hexrgb("#3ad6c0"), T.hexrgb("#f4f0e0"), iris)
base = T.mix(base, T.hexrgb("#ff4a1a"), ring)
base = T.mix(base, T.hexrgb("#120a14"), pupil)
glint = T.smoothstep(0.08, 0.04, np.hypot(lon - 0.15, lat - 0.15))
base = T.mix(base, np.ones(3), glint)
emis = T.hexrgb("#ff5a1a") * ring[..., None] + T.hexrgb("#ffb070") * (iris * (1 - ring) * (1 - pupil) * 0.25)[..., None]
T.save(base, sp["out"]["eye"], quality=92)
T.save(emis, sp["out"]["eye_e"], quality=92)
