# SPDX-License-Identifier: MIT
"""Paints the glow textures of the Kraken's Wreck inflatables (used by kraken.py).

Part kinds (each in its own pixel rectangle of one square texture):

- "tube": a lofted tentacle. u runs along it (caps included), v around it, as lib.Loft lays it
  out. Orange nylon panels lit from inside (brightest in the panel middles and low down, where
  the light sits), sewn seams pinched at the same places as the geometry (long seams down the
  back, ring seams across), small dark tie-down tabs where they cross, and a brighter lemon
  band along the inner edge whose border is scalloped: one lobe reaching out under each sucker.
- "pumpkin": a ribbed inflatable pumpkin (u around, v from the bottom pole up): one gore per
  rib, seams in the grooves, a collar seam round the stem and one near the ground, a dark vent.
- "stem": a lofted stem: darker brown-orange fabric, a seam along it.
- "sucker": the puffy sucker discs, seen from above: pale coral middle, a deeper rim and the
  coffee-bean crease across it.
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


def ramp(E, stops):
    """Colour ramp: stops = [[value, '#rrggbb'], ...] (sorted)."""
    xs = np.array([s[0] for s in stops])
    cs = np.array([T.hexrgb(s[1]) for s in stops])
    return np.stack([np.interp(E, xs, cs[:, c]) for c in range(3)], -1)


def rect_pixels(rect, size, pad):
    x, y, w, h = rect
    xs = np.arange(max(x - pad, 0), min(x + w + pad, size))
    ys = np.arange(max(y - pad, 0), min(y + h + pad, size))
    X, Y = np.meshgrid(xs, ys)
    return X, Y, (X + 0.5 - x) / w, (Y + 0.5 - y) / h


def loft_t(dims, s_norm):
    L, c0, c1 = dims["L"], dims["c0"], dims["c1"]
    total = c0 + L + c1
    s = np.clip(s_norm, 0, 1) * total
    t = np.where(s < c0, s / max(c0, 1e-9) - 1.0,
                 np.where(s <= c0 + L, (s - c0) / L, 1.0 + (s - c0 - L) / max(c1, 1e-9)))
    circ_tab = np.array(dims["circ"])
    tc = np.clip(t, 0, 1) * (len(circ_tab) - 1)
    circ = np.interp(tc, np.arange(len(circ_tab)), circ_tab)
    phi = np.where(t < 0, -t, np.where(t > 1, t - 1, 0.0)) * (np.pi / 2)
    circ = np.maximum(circ * np.cos(np.clip(phi, 0, np.pi / 2)), 1e-3)
    return t, circ


def pillow(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 2


def tube(img, p, S, grain, fine, sp):
    X, Y, s_norm, a = rect_pixels(p["rect"], S, p.get("pad", 6))
    a = a % 1.0
    d = p["dims"]
    L = d["L"]
    t, circ = loft_t(d, s_norm)
    tt = np.clip(t, 0, 1)
    pos = tt * L
    # ring seams (all the way round) and the long seams down the back
    rings = np.array(sorted(set([0.0, 1.0] + list(p["rings"]))))
    idx = np.clip(np.searchsorted(rings, tt, side="right") - 1, 0, len(rings) - 2)
    r0, r1 = rings[idx] * L, rings[idx + 1] * L
    d_ring = np.minimum(pos - r0, r1 - pos)
    h_ring = 0.5 * (r1 - r0)
    d_ring = np.where(t < 0, -t * d["c0"], np.where(t > 1, (t - 1) * d["c1"], d_ring))
    h_ring = np.where(t < 0, d["c0"], np.where(t > 1, d["c1"], h_ring))
    longs = np.array(p["long"])
    da_l = np.abs(((a[..., None] - longs[None, None, :]) + 0.5) % 1.0 - 0.5).min(-1) * circ
    # half-size of the long panels: the narrow back strip vs the big side panel
    back = (a > longs.min()) & (a < longs.max())
    h_long = np.where(back, 0.5 * (longs.max() - longs.min()), 0.5 * (1 - longs.max() + longs.min())) * circ
    P = pillow(d_ring / np.maximum(h_ring, 1e-6)) * pillow(da_l / np.maximum(h_long, 1e-6))
    dseam = np.minimum(d_ring, da_l)
    lw = sp.get("line_width", 0.012)
    line = np.exp(-(dseam / lw) ** 2)
    crease = np.exp(-(dseam / sp.get("crease_width", 0.06)) ** 2)

    # the lemon band along the inner edge with its scalloped border
    band = p["band"]
    dlat = (((a - band["a"]) + 0.5) % 1.0 - 0.5) * circ
    bk = band["w"]
    w0 = np.interp(tt, [k[0] for k in bk], [k[1] for k in bk])
    w0 = np.where(t > 1, w0 * np.clip(1 - (t - 1) * 1.5, 0, 1), w0)
    reach_p = np.zeros_like(w0)
    reach_m = np.zeros_like(w0)
    for (tl, side, ln, amp) in band["lobes"]:
        sl = tl * L
        f = np.clip(1 - ((pos - sl) / ln) ** 2, 0, 1)
        f = np.sqrt(f) * (t <= 1)
        if side > 0:
            reach_p = np.maximum(reach_p, amp * f)
        else:
            reach_m = np.maximum(reach_m, amp * f)
    W = w0 + np.where(dlat >= 0, reach_p, reach_m)
    inside = np.abs(dlat) - W        # < 0 inside the band
    bline = np.exp(-(inside / (lw * 0.9)) ** 2)
    inb = T.smoothstep(lw * 0.6, -lw * 0.6, inside)

    prof = p["bright"]
    B = np.interp(tt, [k[0] for k in prof], [k[1] for k in prof])
    B = np.where(t > 1, B * (1 - 0.15 * np.clip(t - 1, 0, 1)), B)
    g = grain[Y, X] - 0.5
    f = fine[Y, X] - 0.5
    # fabric: panels puff and glow in their middles, darken into the seams
    E = B * (0.84 + 0.16 * np.sqrt(P)) * (1 - 0.08 * crease) * (1 + 0.06 * g + 0.03 * f)
    Eo = E * (1 - 0.20 * line * (1 - inb))
    Eb = E * band.get("boost", 1.10) * (1 - 0.10 * line)
    body = ramp(Eo, sp["orange"])
    lemon = ramp(Eb, sp["lemon"])
    col = T.mix(body, lemon, inb)
    col = T.mix(col, T.hexrgb(sp.get("band_seam", "#e47a14")), 0.55 * bline)
    # tie-down tabs: little dark triangles on the long seams at every ring seam
    if p.get("tabs", True):
        for rt in p["rings"]:
            ds = pos - rt * L
            for lo in longs:
                dc = (((a - lo) + 0.5) % 1.0 - 0.5) * circ
                tri = (ds > 0) & (ds < 0.075) & (np.abs(dc) < 0.032 * (1 - ds / 0.075)) & (t >= 0) & (t <= 1)
                col = np.where(tri[..., None], T.hexrgb("#3a1c06"), col)
    img[Y, X] = col


def pumpkin(img, p, S, grain, fine, sp):
    X, Y, u, vv = rect_pixels(p["rect"], S, p.get("pad", 6))
    u = u % 1.0
    v = np.clip(1 - vv, 0, 1)
    ribs = p["ribs"]
    rx, rz = p["r"]
    circ = np.maximum(2 * np.pi * rx * np.sin(np.pi * v), 1e-3)
    x = (u * ribs) % 1.0
    d_g = np.minimum(x, 1 - x) / ribs * circ          # metres to the nearest groove seam
    h_g = 0.5 / ribs * circ
    merid = np.pi * 0.5 * (rx + rz)                   # pole-to-pole arc length
    seams_v = np.array(p["rings"])
    dv = np.abs(v[..., None] - seams_v[None, None, :]).min(-1) * merid
    lo = np.where(v < seams_v.min(), 0.0, seams_v.min())
    hi = np.where(v < seams_v.min(), seams_v.min(), np.where(v > seams_v.max(), 1.0, seams_v.max()))
    h_v = 0.5 * (hi - lo) * merid
    P = pillow(d_g / np.maximum(h_g, 1e-6)) * pillow(dv / np.maximum(h_v, 1e-6))
    dseam = np.minimum(np.where(v > 0.97, 1e9, d_g), dv)
    lw = sp.get("line_width", 0.012)
    line = np.exp(-(dseam / lw) ** 2)
    crease = np.exp(-(np.minimum(d_g, dv) / 0.10) ** 2)
    prof = p["bright"]
    B = np.interp(v, [k[0] for k in prof], [k[1] for k in prof])
    g = grain[Y, X] - 0.5
    f = fine[Y, X] - 0.5
    E = B * (0.78 + 0.22 * np.sqrt(P)) * (1 - 0.20 * crease) * (1 + 0.06 * g + 0.03 * f) * (1 - 0.45 * line)
    col = ramp(E, sp["pumpkin"])
    # grime: a few dark specks and smudges low on the gores
    rng = np.random.default_rng(p.get("seed", 3))
    for _ in range(p.get("specks", 26)):
        su, sv = rng.random(), rng.uniform(0.2, 0.75)
        rr = rng.uniform(0.008, 0.03)
        du = (((u - su) + 0.5) % 1 - 0.5) * circ
        dd = np.hypot(du, (v - sv) * merid)
        col = T.mix(col, col * 0.45, np.exp(-(dd / rr) ** 2) * 0.8)
    # the vent: a dark round port with a lighter ring
    vu, vvv, vr = p["vent"]
    du = (((u - vu) + 0.5) % 1 - 0.5) * circ
    dd = np.hypot(du, (v - vvv) * merid)
    col = T.mix(col, T.hexrgb("#5a1a04"), T.smoothstep(vr * 1.25, vr * 1.05, dd) * 0.6)
    col = T.mix(col, T.hexrgb("#1a0702"), T.smoothstep(vr * 1.0, vr * 0.9, dd))
    img[Y, X] = col


def stem(img, p, S, grain, fine, sp):
    X, Y, s_norm, a = rect_pixels(p["rect"], S, p.get("pad", 6))
    a = a % 1.0
    t, circ = loft_t(p["dims"], s_norm)
    da = np.abs(((a - 0.5) + 0.5) % 1.0 - 0.5) * circ
    line = np.exp(-(da / 0.010) ** 2)
    ridge = 0.5 + 0.5 * np.cos(2 * np.pi * 5 * a)
    g = grain[Y, X] - 0.5
    E = (0.85 + 0.15 * ridge) * (1 - 0.4 * line) * (1 + 0.08 * g)
    E = E * np.interp(np.clip(t, -1, 2), [-1, 0, 1, 2], [0.75, 0.85, 1.0, 0.95])
    img[Y, X] = ramp(E, sp["stem"])


def sucker(img, p, S, grain, fine, sp):
    X, Y, u, v = rect_pixels(p["rect"], S, 0)
    x, y = u * 2 - 1, v * 2 - 1                       # x along the tentacle
    r = np.hypot(x, y)
    rim = T.smoothstep(0.55, 0.98, r)
    E = 1.0 - 0.35 * rim
    # the crease: a curved slit across the middle, along the tentacle
    yc = y - 0.10 * (1 - x * x)
    slit = np.exp(-(yc / 0.06) ** 2) * T.smoothstep(0.78, 0.5, np.abs(x))
    col = ramp(E, sp["sucker"])
    col = T.mix(col, T.hexrgb(sp.get("sucker_crease", "#a8402a")), 0.85 * slit)
    hl = np.exp(-((x + 0.15) ** 2 + (y + 0.35) ** 2) / 0.08) * 0.25
    col = np.clip(col + hl[..., None] * np.array([1, 0.9, 0.85]), 0, 1)
    img[Y, X] = col


KINDS = {"tube": tube, "pumpkin": pumpkin, "stem": stem, "sucker": sucker}


def main():
    sp = T.spec()
    S = sp["size"]
    img = np.zeros((S, S, 3))
    mask = np.zeros((S, S), bool)
    grain = T.fbm((S, S), (24, 96), 4, seed=sp.get("seed", 7))      # long soft wrinkles across
    fine = T.fbm((S, S), 280, 3, seed=11)
    for p in sp["parts"]:
        KINDS[p["kind"]](img, p, S, grain, fine, sp)
        x, y, w, h = p["rect"]
        mask[y:y + h, x:x + w] = True
    img = T.fill_from_mask(img, mask)
    T.save(img, out(sp, "tex"), quality=sp.get("quality", 90))


main()
