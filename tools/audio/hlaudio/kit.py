"""A soft electronic drum kit for the neo-classical beat (the way Ólafur Arnalds puts a beat under
piano and strings: close, round and quiet, never a pop kit): a round kick, a crisp snare meant to be
sent long into the hall, tiny dark hats, a woody rim tick, and a hat flutter (a glitch: the hat
stuttering in 32nds as it fades), and a sub boom for the big moments. Every hit is a little different
(seeded)."""
from __future__ import annotations

import numpy as np

from .core import SR, ns, rng, tvec
from .effects import chain, filt


def kick(v=0.8, seed=0, f_hi=105.0, f_lo=46.0, decay=0.34):
    """A round kick: a sine falling fast from f_hi to f_lo, a soft knock on top, gently saturated."""
    r = rng("kick", seed)
    n = ns(decay * 3)
    t = tvec(n)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.045)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR + r.uniform(0, 0.2)) * np.exp(-t / decay)
    y *= 1 - np.exp(-t / 0.0015)
    knock = filt(r.standard_normal(n) * np.exp(-t / 0.006), chain(("bp", 1800, 0.9), ("lp", 4000, 0.7)))
    y = np.tanh(1.5 * (y + 0.12 * knock)) / np.tanh(1.5)
    return y * v


def snare(v=0.8, seed=0, tone=190.0, decay=0.16):
    """A crisp snare: two body tones and a burst of bright noise (the wires), a soft attack."""
    r = rng("snare", seed)
    n = ns(decay * 4)
    t = tvec(n)
    body = (np.sin(2 * np.pi * tone * r.uniform(0.98, 1.02) * t) * np.exp(-t / 0.07) +
            0.5 * np.sin(2 * np.pi * tone * 1.71 * t) * np.exp(-t / 0.05))
    wires = filt(r.standard_normal(n), chain(("hp", 1500, 0.7), ("lp", 8000, 0.7), ("peak", 4500, 0.8, 3.0)))
    wires *= np.exp(-t / decay)
    y = 0.55 * body + 0.8 * wires
    y *= 1 - np.exp(-t / 0.0012)
    return y * v * 0.6


def hat(v=0.5, seed=0, open_=False):
    """A tiny dark hat: metal (six square-ish partials at the old drum machines' ratios) and noise,
    high-passed, closed (a tick) or open (a short wash)."""
    r = rng("hat", seed)
    decay = 0.16 if open_ else 0.028
    n = ns(decay * 4 + 0.01)
    t = tvec(n)
    metal = np.zeros(n)
    for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0):
        metal += np.sign(np.sin(2 * np.pi * f * 1.9 * r.uniform(0.995, 1.005) * t + r.uniform(0, 6)))
    y = 0.5 * metal / 6 + r.standard_normal(n)
    y = filt(y, chain(("hp", 6500, 0.7), ("lp", 11000, 0.7)))
    y *= np.exp(-t / decay) * (1 - np.exp(-t / 0.0008))
    return y * v * 0.35


def rim(v=0.6, seed=0, f0=1650.0):
    """A woody rim tick: a few short partials, very dry."""
    r = rng("rim", seed)
    n = ns(0.08)
    t = tvec(n)
    y = np.zeros(n)
    for ratio, a, d in ((1.0, 1.0, 0.012), (1.47, 0.5, 0.008), (2.3, 0.25, 0.005)):
        y += a * np.exp(-t / d) * np.sin(2 * np.pi * f0 * ratio * r.uniform(0.99, 1.01) * t)
    y += 0.2 * filt(r.standard_normal(n) * np.exp(-t / 0.002), chain(("hp", 2000, 0.7)))
    return y * v * 0.5


def flutter(v=0.45, seed=0, hits=4, step=0.052):
    """The hat stuttering in 32nds as it fades: a small glitch at the end of a phrase."""
    out = np.zeros(ns(hits * step + 0.15))
    for k in range(hits):
        h = hat(v * (0.9 - 0.18 * k), seed * 10 + k)
        a = ns(k * step)
        out[a: a + len(h)] += h[: len(out) - a]
    return out


def boom(f, v=0.8, seed=0, dive=12.0, glide=0.09, decay=1.8, drift=-0.35):
    """A sub boom: a sine diving `dive` semitones onto `f` Hz in about `glide` s, then sinking a little
    (`drift` semitones over its length), dying away over `decay` s; warmed (a second and a third harmonic) so
    it is felt on small speakers too, with a soft thud at the front."""
    r = rng("boom", seed)
    n = ns(decay * 1.6)
    t = tvec(n)
    semis = dive * np.exp(-t / glide) + drift * t / decay
    ph = 2 * np.pi * np.cumsum(f * 2.0 ** (semis / 12)) / SR
    y = np.sin(ph) * np.exp(-t / (decay / 2.6)) * (1 - np.exp(-t / 0.002))
    y = np.tanh(1.8 * (y + 0.12 * np.sin(2 * ph))) / np.tanh(1.8)
    thud = filt(r.standard_normal(n) * np.exp(-t / 0.008), chain(("lp", 600, 0.7), ("hp", 40, 0.7)))
    return (y + 0.2 * thud) * v


VOICES = {"kick": kick, "snare": snare, "hat": hat, "ohat": lambda v, seed: hat(v, seed, True), "rim": rim,
          "flutter": flutter}


def play(track, notes, part, gain=1.0, pan=0.0, pan_spread=0.0, seed=0):
    """Hits (notes in seconds; only their time and velocity count) of one kit voice into a track."""
    r = rng("kit-play", part, seed)
    for i, n in enumerate(notes):
        y = VOICES[part](n.v, seed * 1000 + i)
        track.add(n.t, y, gain=gain, pan=float(np.clip(pan + r.uniform(-pan_spread, pan_spread), -1, 1)))
    return track
