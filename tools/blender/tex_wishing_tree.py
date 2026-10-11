# SPDX-License-Identifier: MIT
"""Grows the wishing tree's outline and paints its textures (used by wishing-tree.py).
Needs numpy, Pillow, scipy and OpenCV (cv2, for tracing the outline).

outline  JSON: the board's outline loops in metres (x right, z up, trunk base at x = 0, z = 0),
         and the leaf anchors (position on the branch edge, leaf direction in the board plane).
board    1024 x 1024: white painted board over the outline's bounding box.
hedge    1024 x 1024 tileable boxwood (1 m per tile) + its normal map.
pompom   256 x 64: four pom-pom colours side by side.
"""

import json
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

import texlib as T

sp = T.spec()
rng = np.random.default_rng(sp.get("seed", 4))
segs = []      # x0, z0, x1, z1, w0, w1, depth
MIN_W = 0.055


def branch(x, z, ang, length, w, depth):
    n = 4
    a = ang
    wc = w
    pts = []
    for i in range(n):
        a += rng.normal(0, 0.06)
        if depth >= 2:
            a *= sp.get("tropism", 0.95)      # branches turn upward, as on a sea fan
        a = max(-1.45, min(1.45, a))
        l = length / n
        x1, z1 = x + math.sin(a) * l, z + math.cos(a) * l
        w1 = w * (1 - 0.14 * (i + 1) / n)
        segs.append((x, z, x1, z1, wc, w1, depth))
        pts.append((x, z, a, wc))
        x, z, wc = x1, z1, w1
    # little side twigs along longer branches
    if depth >= 2 and w > 0.07:
        for _ in range(rng.integers(0, 3)):
            px, pz, pa, pw = pts[rng.integers(1, n)]
            sa = pa + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9)
            tl = rng.uniform(0.15, 0.32)
            branch_tip(px, pz, sa, tl, max(pw * 0.42, MIN_W), depth + 2)
    if depth >= sp["max_depth"] or wc < MIN_W * 1.25:
        return
    k = 3 if (depth <= 3 and rng.random() < 0.4) else 2
    spread = math.radians(max(28 - depth * 2, 15))
    for j in range(k):
        off = (j - (k - 1) / 2) * spread * (1.0 if k == 3 else 1.15)
        ca = a + off + rng.normal(0, 0.08)
        # keep the fan: nothing points below the horizontal
        ca = max(-1.42, min(1.42, ca))
        cw = wc * (0.74 if k == 2 else 0.64) * rng.uniform(0.92, 1.08)
        cl = length * rng.uniform(0.80, 0.95)
        branch(x, z, ca, cl, max(cw, MIN_W), depth + 1)


def branch_tip(x, z, ang, length, w, depth):
    x1, z1 = x + math.sin(ang) * length, z + math.cos(ang) * length
    segs.append((x, z, x1, z1, w, w * 0.85, depth))


# trunk with a flared foot, then four great limbs fanning out
segs.append((0.0, 0.0, 0.0, 0.5, 0.62, 0.5, 0))
segs.append((0.0, 0.5, 0.0, 1.0, 0.5, 0.46, 0))
for ang, w, l in sp["limbs"]:
    branch(0.0, 0.95, ang, l, w, 1)

S = np.array(segs)
xmin, xmax = min(S[:, 0].min(), S[:, 2].min()), max(S[:, 0].max(), S[:, 2].max())
zmax = max(S[:, 1].max(), S[:, 3].max())
sx = sp["width"] / ((xmax - xmin) + 0.2)
sz = sp["height"] / (zmax + 0.1)
sc = min(sx, sz)
S[:, :4] *= sc
S[:, 4:6] *= max(sc, 1.0) ** 0.3  # widths stay close to the designed ones

# rasterise (3 mm per pixel), round the forks, trace
res = 0.003
x0, x1 = min(S[:, 0].min(), S[:, 2].min()) - 0.3, max(S[:, 0].max(), S[:, 2].max()) + 0.3
z0, z1 = -0.05, max(S[:, 1].max(), S[:, 3].max()) + 0.3
W, H = int((x1 - x0) / res), int((z1 - z0) / res)
mask = np.zeros((H, W), np.uint8)


def px(x, z):
    return (x - x0) / res, (z1 - z) / res


for (xa, za, xb, zb, wa, wb, d) in S:
    dx, dz = xb - xa, zb - za
    L = math.hypot(dx, dz) or 1e-6
    nx, nz = -dz / L, dx / L
    quad = [px(xa + nx * wa / 2, za + nz * wa / 2), px(xb + nx * wb / 2, zb + nz * wb / 2),
            px(xb - nx * wb / 2, zb - nz * wb / 2), px(xa - nx * wa / 2, za - nz * wa / 2)]
    cv2.fillConvexPoly(mask, np.round(np.array(quad)).astype(np.int32), 255)
    for (cx, cz, r) in ((xa, za, wa / 2), (xb, zb, wb / 2)):
        p = px(cx, cz)
        cv2.circle(mask, (int(round(p[0])), int(round(p[1]))), max(1, int(round(r / res))), 255, -1)
# the foot flares into the ground
foot = [px(-0.45, 0.0), px(0.45, 0.0), px(0.27, 0.12), px(0.25, 0.35), px(-0.25, 0.35), px(-0.27, 0.12)]
cv2.fillPoly(mask, [np.round(np.array(foot)).astype(np.int32)], 255)
m = T.blur(mask.astype(float) / 255, 0.02 / res)
mask = (m > 0.45).astype(np.uint8) * 255
mask[int((z1 - 0.0) / res):, :] = 0   # flat bottom at z = 0
contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
loops = []
for c, h in zip(contours, hier[0]):
    if cv2.contourArea(c) < (0.03 / res) ** 2:
        continue
    a = cv2.approxPolyDP(c, 1.2, True)[:, 0, :]
    pts = [[float(x0 + p[0] * res), float(z1 - p[1] * res)] for p in a]
    pts = [[x, max(z, 0.0)] for x, z in pts]
    loops.append({"hole": bool(h[3] >= 0), "pts": pts})

# leaf anchors: along the branches (not the trunk), alternating sides, on the board's edge
anchors = []
grid = {}
spacing = sp["anchor_spacing"]


def free(x, z):
    k = (int(x / 0.1), int(z / 0.1))
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for (ax, az) in grid.get((k[0] + i, k[1] + j), []):
                if (ax - x) ** 2 + (az - z) ** 2 < (spacing * 0.6) ** 2:
                    return False
    return True


side = 1
for (xa, za, xb, zb, wa, wb, d) in S:
    if d == 0 or za < 0.9:
        continue
    dx, dz = xb - xa, zb - za
    L = math.hypot(dx, dz)
    if L < 1e-6:
        continue
    tx, tz = dx / L, dz / L
    nx, nz = -tz, tx
    n = max(1, int(L / spacing))
    for i in range(n):
        f = (i + 0.5) / n
        w = wa + (wb - wa) * f
        side = -side
        x = xa + dx * f + nx * side * w * 0.42
        z = za + dz * f + nz * side * w * 0.42
        ang = math.radians(35)
        lx = nx * side * math.cos(ang) + tx * math.sin(ang)
        lz = nz * side * math.cos(ang) + tz * math.sin(ang)
        if not free(x, z):
            continue
        anchors.append([x, z, lx, lz])
        grid.setdefault((int(x / 0.1), int(z / 0.1)), []).append((x, z))
    # one at each branch tip
    if d >= 3 and wb < 0.06:
        if free(xb + tx * wb * 0.3, zb + tz * wb * 0.3):
            anchors.append([xb + tx * wb * 0.3, zb + tz * wb * 0.3, tx, tz])
            grid.setdefault((int(xb / 0.1), int(zb / 0.1)), []).append((xb, zb))

bx0 = min(p[0] for l in loops for p in l["pts"])
bx1 = max(p[0] for l in loops for p in l["pts"])
bz1 = max(p[1] for l in loops for p in l["pts"])
with open(sp["out"]["outline"], "w") as f:
    json.dump({"loops": loops, "anchors": anchors, "box": [bx0, bx1, 0.0, bz1]}, f)
print(f"[wishing-tree] {len(loops)} loops, {sum(len(l['pts']) for l in loops)} points, {len(anchors)} anchors, "
      f"box {bx1 - bx0:.2f} x {bz1:.2f} m")

# ---- board texture: white paint over the bounding box ----
N = 1024
u, v = np.meshgrid((np.arange(N) + 0.5) / N, 1 - (np.arange(N) + 0.5) / N)
brush = T.fbm((N, N), (8, 60), 4, seed=3)
blot = T.fbm((N, N), (6, 6), 4, seed=4)
c = T.mix(T.hexrgb("#e4e0d6"), T.hexrgb("#f7f5ef"), 0.6 * brush + 0.4 * blot)
grime = T.smoothstep(0.12, 0.0, v) * T.fbm((N, N), (10, 30), 3, seed=5)
c = T.mix(c, T.hexrgb("#8a8270"), grime * 0.5)
T.save(c, sp["out"]["board"], quality=90)

# ---- boxwood hedge: overlapping small leaves, tileable ----
N = 1024
SS = 2
im = Image.new("RGB", (N * SS, N * SS), (5, 13, 7))
hm = Image.new("L", (N * SS, N * SS), 0)
d = ImageDraw.Draw(im)
dh = ImageDraw.Draw(hm)
lr = np.random.default_rng(9)
for layer in range(3):
    count = (5000, 6000, 7000)[layer]
    for _ in range(count):
        cx, cy = lr.uniform(0, N * SS), lr.uniform(0, N * SS)
        a = lr.uniform(0, math.pi)
        lw, lh = lr.uniform(7, 11) * SS, lr.uniform(3.5, 5.5) * SS
        g = lr.uniform(0.4, 1.0) * (0.55 + 0.25 * layer)
        col = (int(14 + 34 * g), int(38 + 70 * g), int(14 + 26 * g))
        poly = [(lw * math.cos(t) * math.cos(a) - lh * math.sin(t) * math.sin(a),
                 lw * math.cos(t) * math.sin(a) + lh * math.sin(t) * math.cos(a))
                for t in np.linspace(0, math.tau, 12, endpoint=False)]
        for ox in (-N * SS, 0, N * SS):
            for oy in (-N * SS, 0, N * SS):
                if -40 < cx + ox < N * SS + 40 and -40 < cy + oy < N * SS + 40:   # wrap: tileable
                    q = [(cx + px_ + ox, cy + py_ + oy) for px_, py_ in poly]
                    d.polygon(q, fill=col)
                    dh.polygon(q, fill=int(80 + 60 * layer + 40 * g))
im = im.resize((N, N), Image.LANCZOS)
hm = hm.resize((N, N), Image.LANCZOS)
col = np.asarray(im, dtype=float) / 255
h = T.blur(np.asarray(hm, dtype=float) / 255, 1.0, wrap=True)
T.save(col, sp["out"]["hedge"], quality=90)
T.save(T.normal_from_height(h, strength=4.0), sp["out"]["hedge_n"], quality=92)

# ---- pom-poms: orange, yellow, red, white ----
pw, ph = 256, 64
pu, pv = np.meshgrid((np.arange(pw) + 0.5) / pw, (np.arange(ph) + 0.5) / ph)
k = np.minimum((pu * 4).astype(int), 3)
cols = np.array([T.hexrgb("#ff7a14"), T.hexrgb("#ffc21e"), T.hexrgb("#e2261e"), T.hexrgb("#f4f0e8")])[k]
fl = T.fbm((ph, pw), (16, 64), 3, seed=12)
T.save(cols * (0.7 + 0.4 * fl[..., None]), sp["out"]["pompom"], quality=90)
