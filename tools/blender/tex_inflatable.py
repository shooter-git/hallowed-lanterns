# SPDX-License-Identifier: MIT
"""Paints the glow texture of a sewn inflatable (used by longhorn.py).

Every part is a lofted tube whose UV island is a rectangle: u runs along the tube (caps
included), v around it. The params carry each part's island rectangle, its dimensions and its
panel layout (the same one the geometry pinches its seams with), so the stitched seams land
exactly in the creases. Lit from inside: panel middles glow brightest, the fabric darkens a
little toward each seam and the stitch line itself is a thin grey line.
"""

import numpy as np

import texlib as T


def part_pixels(p, size):
    x, y, w, h = p["rect"]
    pad = p.get("pad", 6)
    xs = np.arange(x - pad, x + w + pad)
    ys = np.arange(y - pad, y + h + pad)
    xs = xs[(xs >= 0) & (xs < size)]
    ys = ys[(ys >= 0) & (ys < size)]
    X, Y = np.meshgrid(xs, ys)
    s_norm = np.clip((X + 0.5 - x) / w, 0, 1)
    a = ((Y + 0.5 - y) / h) % 1.0
    return X, Y, s_norm, a


def panel_fields(p, s_norm, a):
    d = p["dims"]
    L, c0, c1 = d["L"], d["c0"], d["c1"]
    total = c0 + L + c1
    s = s_norm * total
    t = np.where(s < c0, s / max(c0, 1e-9) - 1.0,
                 np.where(s <= c0 + L, (s - c0) / L, 1.0 + (s - c0 - L) / max(c1, 1e-9)))
    circ_tab = np.array(d["circ"])
    tc = np.clip(t, 0, 1) * (len(circ_tab) - 1)
    circ = np.interp(tc, np.arange(len(circ_tab)), circ_tab)
    phi = np.where(t < 0, -t, np.where(t > 1, t - 1, 0.0)) * (np.pi / 2)
    circ = np.maximum(circ * np.cos(np.clip(phi, 0, np.pi / 2)), 1e-3)

    lay = p["layout"]
    longs = np.array(lay["long"])
    nb = len(longs)
    d_long = np.full(a.shape, 1e9)
    h_long = np.full(a.shape, 1e9)
    band = np.zeros(a.shape, dtype=int)
    if nb:
        ext = np.concatenate([longs, [longs[0] + 1.0]])
        aa = np.where(a < longs[0], a + 1.0, a)
        band = np.clip(np.searchsorted(ext, aa, side="right") - 1, 0, nb - 1)
        lo = ext[band]
        hi = ext[band + 1]
        d_long = np.minimum(aa - lo, hi - aa) * circ
        h_long = 0.5 * (hi - lo) * circ

    pos = t * L
    d_ring = np.full(a.shape, 1e9)
    h_ring = np.full(a.shape, 1e9)
    bands = lay["bands"] or [[]]
    for b in range(max(nb, 1)):
        seams = np.array(sorted(set([0.0, 1.0] + list(bands[b] if b < len(bands) else []))))
        sel = (band == b) if nb else np.ones(a.shape, bool)
        idx = np.clip(np.searchsorted(seams, np.clip(t, 0, 1), side="right") - 1, 0, len(seams) - 2)
        s0, s1 = seams[idx] * L, seams[idx + 1] * L
        dr = np.minimum(pos - s0, s1 - pos)
        hr = 0.5 * (s1 - s0)
        d_ring = np.where(sel, dr, d_ring)
        h_ring = np.where(sel, hr, h_ring)
    # caps: the cap boundary is a seam, the pole is the panel middle
    d_ring = np.where(t < 0, -t * c0, np.where(t > 1, (t - 1) * c1, d_ring))
    h_ring = np.where(t < 0, c0, np.where(t > 1, c1, h_ring))
    return t, d_ring, h_ring, d_long, h_long


def pillow(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 2


def main():
    sp = T.spec()
    S = sp["size"]
    img = np.ones((S, S, 3)) * np.array(sp.get("fill", [0.9, 0.9, 0.9]))
    tint = np.array(sp.get("tint", [0.97, 0.98, 1.0]))
    grain = T.fbm((S, S), 48, 4, seed=7) - 0.5
    fine = T.fbm((S, S), 300, 3, seed=11) - 0.5
    line_w = sp.get("line_width", 0.006)
    for p in sp["parts"]:
        X, Y, s_norm, a = part_pixels(p, S)
        t, dr, hr, dl, hl = panel_fields(p, s_norm, a)
        d = np.minimum(dr, dl)
        P = pillow(dr / np.maximum(hr, 1e-6)) * pillow(dl / np.maximum(hl, 1e-6))
        line = np.exp(-(d / line_w) ** 2)
        crease = np.exp(-(d / sp.get("crease_width", 0.05)) ** 2)
        br = p.get("bright", {})
        tt = np.clip(t, 0, 1)
        prof = br.get("profile")  # [[t, value], ...] along the part
        if prof:
            B = np.interp(tt, [k[0] for k in prof], [k[1] for k in prof])
        else:
            B = np.full(t.shape, br.get("base", 1.0))
        B = B * (1 + br.get("bottom", 0.0) * np.cos(2 * np.pi * a))
        E = B * (0.80 + 0.20 * np.sqrt(P)) * (1 - sp.get("crease_depth", 0.22) * crease) * (1 - sp.get("line_depth", 0.55) * line)
        E = E * (1 + 0.05 * grain[Y, X] + 0.03 * fine[Y, X])
        img[Y, X] = E[..., None] * tint
    T.save(np.clip(img, 0, 1), sp["out"]["glow"], quality=sp.get("quality", 90))


main()
