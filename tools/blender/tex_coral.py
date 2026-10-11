# SPDX-License-Identifier: MIT
"""Draws, traces and paints the cut-out coral boards (used by coral.py). Needs OpenCV (cv2).

coral-1  orange staghorn coral, about 1.0 m tall
coral-2  pink candelabra coral, about 1.25 m
coral-3  lime kelp: four wavy, knobbly blades from one foot, about 1.0 m

outline  JSON: per coral its outline loops (metres, x right, z up, foot at x = 0, z = 0), its
         bounding box and its rectangle in the atlas.
atlas    1024 x 1024: the three boards side by side (colour + emission at half strength): bright
         UV paint with brush marks, a darker painted outline round each edge and a pale highlight.
"""

import json
import math

import cv2
import numpy as np

import texlib as T

sp = T.spec()
RES = 0.002   # metres per pixel when drawing
W_M, H_M = 1.3, 1.45


def canvas():
    return np.zeros((int(H_M / RES), int(W_M / RES)), np.uint8)


def P(x, z):
    return int(round((x + W_M / 2) / RES)), int(round((H_M - z) / RES))


def limb(img, pts, w0, w1):
    n = len(pts)
    for i in range(n - 1):
        f0, f1 = i / (n - 1), (i + 1) / (n - 1)
        wa, wb = w0 + (w1 - w0) * f0, w0 + (w1 - w0) * f1
        a, b = pts[i], pts[i + 1]
        cv2.circle(img, P(*a), max(1, int(wa / 2 / RES)), 255, -1)
        dx, dz = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dz) or 1e-6
        nx, nz = -dz / L, dx / L
        quad = [P(a[0] + nx * wa / 2, a[1] + nz * wa / 2), P(b[0] + nx * wb / 2, b[1] + nz * wb / 2),
                P(b[0] - nx * wb / 2, b[1] - nz * wb / 2), P(a[0] - nx * wa / 2, a[1] - nz * wa / 2)]
        cv2.fillConvexPoly(img, np.array(quad, np.int32), 255)
    cv2.circle(img, P(*pts[-1]), max(1, int(w1 / 2 / RES)), 255, -1)


def path(x, z, ang, length, curve, rng, n=8):
    pts = [(x, z)]
    for i in range(n):
        ang += curve + rng.normal(0, 0.05)
        x += math.sin(ang) * length / n
        z += math.cos(ang) * length / n
        pts.append((x, z))
    return pts, ang


def staghorn(rng):
    img = canvas()

    def br(x, z, ang, length, w, depth):
        pts, a = path(x, z, ang, length, -ang * 0.04, rng)
        limb(img, pts, w, w * 0.72)
        if depth == 0:
            return
        for k, frac in enumerate((0.45, 0.8)):
            px, pz = pts[int(frac * (len(pts) - 1))]
            side = 1 if (k + depth) % 2 else -1
            br(px, pz, a + side * rng.uniform(0.45, 0.75), length * rng.uniform(0.55, 0.7), w * 0.75, depth - 1)
        br(pts[-1][0], pts[-1][1], a + rng.normal(0, 0.2), length * 0.55, w * 0.7, depth - 1)
    br(0.0, -0.02, 0.0, 0.5, 0.13, 3)
    return img


def candelabra(rng):
    img = canvas()
    trunk, a = path(0.0, -0.02, 0.05, 0.38, 0.0, rng, 6)
    limb(img, trunk, 0.12, 0.10)
    tx, tz = trunk[-1]
    for side in (-1, 1):
        # a Y: out sideways, then up
        pts = [(tx, tz)]
        x, z = tx, tz
        ang = side * 1.25
        for i in range(10):
            ang -= side * 0.13
            x += math.sin(ang) * 0.05
            z += math.cos(ang) * 0.05
            pts.append((x, z))
        limb(img, pts, 0.09, 0.07)
        up, _ = path(x, z, side * 0.1, 0.45, -side * 0.01, rng, 6)
        limb(img, up, 0.07, 0.055)
        for frac in (0.35, 0.75):
            px, pz = up[int(frac * (len(up) - 1))]
            twig, _ = path(px, pz, -side * 0.9, 0.17, side * 0.12, rng, 5)
            limb(img, twig, 0.05, 0.04)
            twig2, _ = path(px, pz, side * 0.95, 0.15, -side * 0.12, rng, 5)
            limb(img, twig2, 0.045, 0.038)
    mid, _ = path(tx, tz, 0.0, 0.6, 0.0, rng, 8)
    limb(img, mid, 0.08, 0.06)
    return img


def kelp(rng):
    img = canvas()
    for k, (x0, ang, ln) in enumerate(((-0.12, -0.25, 0.85), (-0.03, -0.05, 1.0), (0.07, 0.12, 0.92), (0.15, 0.3, 0.7))):
        pts = []
        x, z = x0, -0.02
        for i in range(30):
            f = i / 29
            a = ang + 0.35 * math.sin(f * math.pi * 3 + k)
            x += math.sin(a) * ln / 29
            z += math.cos(a) * ln / 29
            pts.append((x, z))
        limb(img, pts, 0.07, 0.045)
        for i in range(2, 29, 3):    # knobbly lobes on alternate sides
            px, pz = pts[i]
            side = 1 if (i // 3) % 2 else -1
            cv2.circle(img, P(px + side * 0.035, pz), int(0.032 / RES), 255, -1)
    cv2.ellipse(img, P(0.02, 0.03), (int(0.17 / RES), int(0.06 / RES)), 0, 0, 360, 255, -1)
    return img


def trace(img):
    m = T.blur(img.astype(float) / 255, 3.0)
    mask = (m > 0.5).astype(np.uint8) * 255
    zr = int((H_M - 0.0) / RES)
    mask[zr:, :] = 0
    contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    loops = []
    for c, h in zip(contours, hier[0]):
        if cv2.contourArea(c) < (0.02 / RES) ** 2:
            continue
        a = cv2.approxPolyDP(c, 1.3, True)[:, 0, :]
        pts = [[float(p[0] * RES - W_M / 2), float(max(H_M - p[1] * RES, 0.0))] for p in a]
        loops.append({"hole": bool(h[3] >= 0), "pts": pts})
    return mask, loops


rng = np.random.default_rng(sp.get("seed", 5))
shapes = [("coral-1", staghorn(rng), "#ff7a2a", "#ffc070"), ("coral-2", candelabra(rng), "#ff4f9a", "#ffb0d8"),
          ("coral-3", kelp(rng), "#9cf02a", "#e0ff8a")]
S = 1024
cw = S // 3
atlas = np.zeros((S, S, 3))
out = {}
for i, (name, img, c0, c1) in enumerate(shapes):
    mask, loops = trace(img)
    xs = [p[0] for l in loops for p in l["pts"]]
    zs = [p[1] for l in loops for p in l["pts"]]
    box = [min(xs) - 0.02, max(xs) + 0.02, 0.0, max(zs) + 0.02]
    # the cell is cw x S pixels; fit the box keeping its aspect
    sc = min(cw / (box[1] - box[0]), S / (box[3] - box[2]))
    rect = [i * cw, 0, (box[1] - box[0]) * sc, (box[3] - box[2]) * sc]
    out[name] = {"loops": loops, "box": box, "rect": rect}
    # paint: sample the mask into the cell
    h, w = S, cw
    yy, xx = np.mgrid[0:h, 0:w]
    x = box[0] + (xx + 0.5) / sc
    z = box[3] - (yy + 0.5) / sc
    px = np.clip(((x + W_M / 2) / RES).astype(int), 0, mask.shape[1] - 1)
    pz = np.clip(((H_M - z) / RES).astype(int), 0, mask.shape[0] - 1)
    inside = mask[pz, px] > 127
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)[pz, px] * RES   # metres to the edge
    brush = T.fbm((h, w), (8, 40), 4, seed=10 + i)
    col = T.mix(T.hexrgb(c0) * 0.82, T.hexrgb(c0), brush)
    col = T.mix(col, T.hexrgb(c1), T.smoothstep(0.03, 0.06, dist) * T.smoothstep(0.1, 0.06, dist) * 0.35)
    col = T.mix(col, T.hexrgb(c0) * 0.45, T.smoothstep(0.012, 0.004, dist))
    col = np.where(inside[..., None], col, T.hexrgb(c0) * 0.45)
    atlas[:, i * cw:(i + 1) * cw] = col
with open(sp["out"]["outline"], "w") as f:
    json.dump(out, f)
T.save(atlas, sp["out"]["atlas"], quality=90)
T.save(atlas * 0.5, sp["out"]["atlas_e"], quality=90)
print("[coral]", {k: (len(v["loops"]), round(v["box"][1] - v["box"][0], 2), round(v["box"][3], 2)) for k, v in out.items()})
