# SPDX-License-Identifier: MIT
"""Texture-painting helpers for the tex_*.py painters (plain python3 with numpy, Pillow, scipy).

Images are float arrays in [0, 1], shape (H, W, C), row 0 at the top (as in the saved file).
Blender UV (u, v) maps to pixel (u * W, (1 - v) * H).
"""

import json
import sys

import numpy as np
from PIL import Image, ImageFile
from scipy import ndimage

ImageFile.MAXBLOCK = 1 << 26  # lets optimize=True JPEG encoding work on big images


def spec():
    with open(sys.argv[1]) as f:
        return json.load(f)


def save(arr, path, quality=90):
    a = np.clip(arr, 0, 1)
    if a.ndim == 2:
        a = a[..., None]
    a = (a * 255 + 0.5).astype(np.uint8)
    mode = {1: "L", 3: "RGB", 4: "RGBA"}[a.shape[2]]
    im = Image.fromarray(a[..., 0] if mode == "L" else a, mode)
    if path.lower().endswith((".jpg", ".jpeg")):
        im.convert("RGB").save(path, quality=quality, optimize=True, subsampling=0 if quality >= 92 else 2)
    else:
        im.save(path, optimize=True)
    print("[texlib] wrote", path, im.size)


def noise(shape, cells, seed=0, order=3):
    """Tileable value noise in [0, 1]: `cells` (cy, cx) random lattice points across the image."""
    rng = np.random.default_rng(seed)
    if isinstance(cells, (int, float)):
        cells = (int(cells), int(cells))
    g = rng.random((max(int(cells[0]), 1), max(int(cells[1]), 1)))
    z = ndimage.zoom(g, (shape[0] / g.shape[0], shape[1] / g.shape[1]), order=order,
                     mode="grid-wrap", grid_mode=True)
    z = z[:shape[0], :shape[1]]
    if z.shape != tuple(shape[:2]):
        z = np.pad(z, ((0, shape[0] - z.shape[0]), (0, shape[1] - z.shape[1])), mode="wrap")
    return z


def fbm(shape, cells, octaves=5, seed=0, gain=0.5, lacunarity=2.0):
    if isinstance(cells, (int, float)):
        cells = (cells, cells)
    total = np.zeros(shape[:2])
    amp, norm = 1.0, 0.0
    cy, cx = cells
    for o in range(octaves):
        total += amp * noise(shape, (cy, cx), seed + 101 * o)
        norm += amp
        amp *= gain
        cy, cx = cy * lacunarity, cx * lacunarity
    return total / norm


def blur(a, sigma, wrap=False):
    mode = "wrap" if wrap else "reflect"
    if a.ndim == 3:
        return np.stack([ndimage.gaussian_filter(a[..., c], sigma, mode=mode) for c in range(a.shape[2])], -1)
    return ndimage.gaussian_filter(a, sigma, mode=mode)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = np.asarray(t, dtype=float)
    if t.ndim == 2 and (np.ndim(a) in (1, 3) or np.ndim(b) in (1, 3)):
        t = t[..., None]
    return a * (1 - t) + b * t


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def fill_from_mask(img, mask):
    """Replaces pixels outside `mask` with the nearest pixel inside it (padding for mipmaps)."""
    if mask.all():
        return img
    _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
    return img[iy, ix]


def normal_from_height(h, strength=1.0, wrap=True):
    """Tangent-space normal map (OpenGL, +Y up as Blender and glTF expect) from a height field."""
    mode = "wrap" if wrap else "nearest"
    dx = ndimage.sobel(h, axis=1, mode=mode) / 8.0
    dy = ndimage.sobel(h, axis=0, mode=mode) / 8.0
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5], -1)


def polar_grid(h, w):
    y, x = np.mgrid[0:h, 0:w]
    return (x + 0.5) / w, (y + 0.5) / h
