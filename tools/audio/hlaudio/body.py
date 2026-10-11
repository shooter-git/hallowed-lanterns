"""Instrument body impulse responses (modal): the wooden resonators that make a
string sound like a violin, cello, guitar, harp or zither.

Each IR has a few strong low 'signature' modes and a dense, jagged field of
higher modes; with vibrato, harmonics sweep across those peaks, which is a
large part of what makes a bowed string sound alive rather than synthetic.
Mode gains are specified as peak gains (dB) with a Q, and the whole response
is normalised so its median gain is 0 dB.
"""
from __future__ import annotations

import numpy as np

from .core import SR, ns, rng, tvec

BODIES = {
    # signature modes (Hz, peak dB, Q), dense field range, count, bridge hill (Hz, dB), tilt dB/oct above 1k
    "violin": dict(modes=[(275, 9, 9), (405, 5, 12), (460, 8, 12), (530, 7, 12), (700, 4, 10)],
                   dense=(800, 7500), count=80, hill=(2600, 4), tilt=-1.5),
    "viola": dict(modes=[(230, 9, 9), (350, 5, 12), (390, 8, 12), (450, 7, 12), (600, 4, 10)],
                  dense=(650, 6500), count=80, hill=(2200, 3), tilt=-2.0),
    "cello": dict(modes=[(98, 8, 7), (170, 5, 10), (195, 7, 10), (220, 6, 10), (300, 4, 9)],
                  dense=(350, 5500), count=90, hill=(1500, 2), tilt=-2.5),
    "bass": dict(modes=[(57, 7, 6), (98, 5, 8), (115, 6, 8), (140, 4, 8)],
                 dense=(180, 4000), count=80, hill=(900, 2), tilt=-3.0),
    "guitar": dict(modes=[(98, 9, 9), (204, 8, 14), (245, 4, 12), (390, 5, 14), (450, 4, 14), (560, 3, 14)],
                   dense=(650, 6000), count=70, hill=(2400, 1), tilt=-1.5),
    "harp": dict(modes=[(140, 6, 8), (250, 7, 10), (410, 5, 10), (560, 3, 10)],
                 dense=(700, 6000), count=70, hill=(2000, 1), tilt=-1.0),
    "piano": dict(modes=[(105, 5, 6), (190, 6, 8), (290, 5, 8), (420, 4, 9), (600, 3, 9)],
                  dense=(700, 6000), count=80, hill=(2000, 1), tilt=-2.0),
    "zheng": dict(modes=[(120, 6, 9), (210, 7, 11), (330, 6, 11), (470, 4, 11), (650, 3, 11)],
                  dense=(800, 7000), count=80, hill=(3000, 2), tilt=-1.0),
}


def _response(h, nfft=1 << 15):
    H = np.abs(np.fft.rfft(h, nfft))
    f = np.fft.rfftfreq(nfft, 1 / SR)
    return f, H


def body_ir(kind="violin", seed=0, length=0.2):
    p = BODIES[kind]
    r = rng("body", kind, seed)
    n = ns(length)
    t = tvec(n)
    h = np.zeros(n)
    h[0] = 1.0

    def mode(f, gdb, Q):
        d = Q / (np.pi * f)
        A = 2 * (10 ** (gdb / 20)) / d / SR  # peak gain ~ A*d*SR/2
        return A * np.exp(-t / d) * np.sin(2 * np.pi * f * t)

    for f, gdb, Q in p["modes"]:
        h += mode(f * r.uniform(0.97, 1.03), gdb, Q)
    lo, hi = p["dense"]
    fs = np.exp(r.uniform(np.log(lo), np.log(hi), p["count"]))
    hc, hg = p["hill"]
    for f in fs:
        g = r.uniform(-4, 4) + hg * np.exp(-0.5 * (np.log2(f / hc) / 0.6) ** 2)
        g += p["tilt"] * max(0.0, np.log2(f / 1000))
        sign = r.choice([-1, 1])
        h += sign * mode(f, g, r.uniform(18, 40))
    f, H = _response(h)
    band = (f > 80) & (f < 8000)
    med = np.median(H[band])
    h /= med
    k = ns(0.02)
    h[-k:] *= np.linspace(1, 0, k)
    return h


def stereo_body(kind, seed=0, length=0.2):
    """Two decorrelated body IRs (left/right) -> natural stereo width."""
    return np.vstack([body_ir(kind, seed * 2 + 1, length), body_ir(kind, seed * 2 + 2, length)])
