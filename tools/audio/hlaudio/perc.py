"""Gentle percussion: frame drum / taiko heartbeat, shaker, soft knocks."""
from __future__ import annotations

import numpy as np

from .core import SR, ns, rng, tvec
from .effects import chain, filt

BESSEL = [1.0, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501]


def drum(f0=90.0, v=0.7, seed=0, decay=0.45, bend=0.08, mallet=0.004, damp=1.0, length=None, brightness=1.0):
    """Membrane drum (frame drum ~ 90-140 Hz, taiko ~ 50-70 Hz)."""
    r = rng("drum", seed, round(f0))
    length = length or decay * 2.2
    n = ns(length)
    t = tvec(n)
    pitch = 1 + bend * v * np.exp(-t / 0.05)
    ph = np.cumsum(f0 * pitch) / SR
    y = np.zeros(n)
    for k, ratio in enumerate(BESSEL):
        a = (1.0 if k == 0 else 0.55 / (k ** 0.7)) * (brightness ** k if k else 1)
        dk = decay / (1 + 0.9 * k) * damp
        y += a * np.exp(-t / dk) * np.sin(2 * np.pi * ratio * ph + r.uniform(0, 0.3))
    y *= 1 - np.exp(-t / mallet)
    thud = filt(r.standard_normal(n) * np.exp(-t / 0.012), chain(("lp", 900 * brightness, 0.7), ("hp", 40, 0.7)))
    y += 0.35 * thud
    return y * v


def heartbeat(f0=55.0, v=0.7, seed=0, gap=0.28):
    a = drum(f0, v, seed, decay=0.5, bend=0.12, mallet=0.006, brightness=0.6)
    b = drum(f0 * 0.97, v * 0.65, seed + 1, decay=0.45, bend=0.1, mallet=0.007, brightness=0.55)
    n = max(a.shape[0], ns(gap) + b.shape[0])
    y = np.zeros(n)
    y[: a.shape[0]] += a
    y[ns(gap): ns(gap) + b.shape[0]] += b
    return y


def shaker(v=0.5, seed=0, length=0.14, grains=110, lo=2500, hi=7000):
    """One shake: many tiny bead impacts under a swelling envelope."""
    r = rng("shaker", seed)
    n = ns(length + 0.05)
    y = np.zeros(n)
    times = np.sort(r.beta(2.2, 2.8, grains) * length)
    for tt in times:
        i = ns(tt)
        k = min(n - i, 60)
        y[i:i + k] += r.standard_normal(k) * np.exp(-np.arange(k) / 9.0) * r.uniform(0.2, 1)
    y = filt(y, chain(("hp", lo, 0.7), ("lp", hi, 0.7), ("hs", 5000, 0.7, -3)))
    return y * v * 0.3


def knock(f0=180.0, v=0.7, seed=0, hollow=1.0):
    """Warm wooden knock (a knuckle on a pumpkin or a beam)."""
    r = rng("knock", seed, round(f0))
    n = ns(0.35)
    t = tvec(n)
    y = np.zeros(n)
    for ratio, a, d in [(1, 1, 0.07 * hollow), (1.72, 0.6, 0.045), (2.61, 0.35, 0.03), (3.9, 0.2, 0.018),
                        (5.3, 0.1, 0.012)]:
        y += a * np.exp(-t / d) * np.sin(2 * np.pi * f0 * ratio * r.uniform(0.98, 1.02) * t)
    y *= 1 - np.exp(-t / 0.0012)
    y += 0.25 * filt(r.standard_normal(n) * np.exp(-t / 0.004), chain(("lp", 2500, 0.7), ("hp", 200, 0.7)))
    return y * v
