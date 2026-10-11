"""Struck and plucked metal/wood: music box, celesta, glockenspiel, bells,
sleigh bells, wind chimes, finger cymbal and the pumpkin xylophone.

All are modal (additive) models: a set of damped, mostly inharmonic sinusoids
per note with velocity-dependent brightness, plus a short strike transient.
"""
from __future__ import annotations

import numpy as np

from .core import SR, hz, ns, rng, tvec, Track, to_stereo
from .effects import chain, filt, eq, convolve

NYQ_SAFE = 9500.0  # keep the highs soft: nothing synthesised above this


def modal(f0, partials, length, attack=0.0004, damp_at=None, damp_t60=0.2, seed=0, phase_rand=False):
    """Sum of damped sinusoids. partials = [(ratio, amp, t60), ...].
    damp_at: seconds after which every partial decays with damp_t60 (dampers)."""
    n = ns(length)
    t = tvec(n)
    out = np.zeros(n)
    r = rng("modal", f0, seed) if phase_rand else None
    for ratio, amp, t60 in partials:
        f = f0 * ratio
        if f >= NYQ_SAFE or amp <= 0:
            continue
        # fade partials gently as they approach the safe ceiling
        if f > 6000:
            amp *= np.cos((f - 6000) / (NYQ_SAFE - 6000) * np.pi / 2) ** 2
        ph = r.uniform(0, 2 * np.pi) if r is not None else 0.0
        env = np.exp(-6.9078 * t / max(t60, 1e-3))
        if damp_at is not None:
            k = ns(damp_at)
            if k < n:
                env[k:] = env[k] * np.exp(-6.9078 * (t[k:] - t[k]) / damp_t60)
        out += amp * env * np.sin(2 * np.pi * f * t + ph)
    if attack > 0:
        out *= 1 - np.exp(-t / attack)
    return out


def _noise_burst(n_s, lo, hi, r, decay):
    n = ns(n_s)
    x = r.standard_normal(n) * np.exp(-tvec(n) / decay)
    return filt(x, chain(("hp", lo, 0.7), ("lp", hi, 0.7)))


def _pad_to(a, n):
    return a[:n] if a.shape[0] >= n else np.pad(a, (0, n - a.shape[0]))


# ----------------------------------------------------------------- instruments

def music_box(p, v=0.7, dur=None, seed=0):
    f0 = float(hz(p))
    r = rng("mbox", round(p * 4), seed)
    rp = rng("mbox-tooth", round(p * 4))  # per-tooth constants
    T = float(np.clip(4.2 * (523.0 / f0) ** 0.6, 1.0, 6.5))
    bright = 0.55 + 0.45 * v
    m2 = rp.uniform(5.75, 6.35)
    parts = [
        (1.0, 1.0, T),
        (1.0 * 2 ** (rp.uniform(1.2, 3.2) / 1200), 0.5, T * 0.85),  # twin tooth -> slow beating
        (2.0, 0.05 * bright, T * 0.22),
        (3.0, 0.015 * bright, T * 0.12),
        (m2, 0.20 * bright ** 1.5, T * 0.16),
        (m2 * 1.003, 0.07 * bright ** 1.5, T * 0.13),
        (17.3, 0.045 * bright ** 2, T * 0.05),
    ]
    length = min(T * 1.6, 9.0)
    x = modal(f0, parts, length, attack=0.0003)
    # pin release tick and a tiny wooden thock from the comb base
    tick = _noise_burst(0.006, 1800, 6500, r, 0.0012) * 0.05 * v
    thock = modal(r.uniform(260, 330), [(1, 1, 0.05), (2.3, 0.4, 0.03)], 0.08) * 0.05 * v
    n = x.shape[0]
    x[: tick.shape[0]] += tick
    x[: thock.shape[0]] += thock
    return x * (0.35 + 0.65 * v)


def celesta(p, v=0.6, dur=1.0, seed=0):
    f0 = float(hz(p))
    r = rng("cel", round(p * 4), seed)
    T = float(np.clip(3.0 * (523.0 / f0) ** 0.5, 0.9, 4.5))
    b = 0.5 + 0.5 * v
    parts = [
        (1.0, 1.0, T),
        (1.0007, 0.35, T * 0.9),
        (2.0, 0.035 * b, T * 0.3),
        (2.76, 0.09 * b ** 1.5, T * 0.13),
        (5.40, 0.03 * b ** 2, T * 0.05),
        (8.93, 0.01 * b ** 2, T * 0.03),
    ]
    damp = max(dur, 0.25)
    length = min(damp + 0.6, T * 1.8)
    x = modal(f0, parts, length, attack=0.0012, damp_at=damp, damp_t60=0.45)
    # resonator bloom: the wooden box reinforces the fundamental a moment later
    t = tvec(x.shape[0])
    bloom = 0.25 * (1 - np.exp(-t / 0.018)) * np.exp(-6.9 * t / (T * 0.7)) * np.sin(2 * np.pi * f0 * t)
    x += bloom
    th = _noise_burst(0.012, 120, 1400, r, 0.003) * 0.06 * v
    x[: th.shape[0]] += th
    return x * (0.3 + 0.7 * v)


def glockenspiel(p, v=0.6, dur=None, seed=0, soft=True):
    f0 = float(hz(p))
    r = rng("glock", round(p * 4), seed)
    T = float(np.clip(4.0 * (900.0 / f0) ** 0.45, 1.2, 5.5))
    b = (0.4 if soft else 0.65) + 0.45 * v
    parts = [
        (1.0, 1.0, T),
        (1.0004, 0.2, T),
        (2.71, 0.30 * b, T * 0.35),
        (5.15, 0.10 * b ** 1.5, T * 0.14),
        (8.43, 0.04 * b ** 2, T * 0.06),
    ]
    x = modal(f0, parts, min(T * 1.5, 7.0), attack=0.0006 if soft else 0.0002)
    clk = _noise_burst(0.004, 2000, 7000, r, 0.0008) * 0.04 * v
    x[: clk.shape[0]] += clk
    return x * (0.3 + 0.7 * v)


def bell(p, v=0.6, dur=None, seed=0, length=None, tone="hand"):
    """Small tuned bell (handbell-like: strong twelfth), sweet and clear."""
    f0 = float(hz(p))
    r = rng("bell", round(p * 4), seed)
    T = float(np.clip(3.5 * (800.0 / f0) ** 0.5, 0.8, 6.0))
    if tone == "hand":
        parts = [(1.0, 1.0, T), (1.0011, 0.4, T * 0.95), (2.0, 0.05, T * 0.4), (3.0, 0.32, T * 0.45),
                 (3.004, 0.12, T * 0.4), (5.04, 0.09, T * 0.2), (6.8, 0.04, T * 0.12)]
    else:  # "tiny": brighter, more inharmonic fairy bell
        parts = [(1.0, 1.0, T * 0.7), (1.0016, 0.5, T * 0.7), (2.41, 0.28, T * 0.35), (3.86, 0.14, T * 0.2),
                 (5.43, 0.07, T * 0.12)]
    x = modal(f0, parts, length or min(T * 1.4, 7.0), attack=0.0005)
    clk = _noise_burst(0.003, 2500, 8000, r, 0.0006) * 0.025 * v
    x[: clk.shape[0]] += clk
    return x * (0.3 + 0.7 * v)


def jingle(v=0.6, seed=0, shake=0.09, n_bells=7, bright=1.0):
    """One shake of a strap of sleigh bells (stereo)."""
    r = rng("jingle", seed)
    L = ns(shake + 0.6)
    out = np.zeros((2, L))
    for b in range(n_bells):
        base = r.uniform(2300, 3600) * bright
        ratios = [1.0, r.uniform(1.45, 1.6), r.uniform(2.05, 2.3), r.uniform(2.6, 2.9)]
        amps = [1.0, 0.5, 0.25, 0.12]
        pan = r.uniform(-0.6, 0.6)
        hits = r.integers(2, 5)
        for h in range(hits):
            t0 = r.uniform(0, shake) + h * r.uniform(0.008, 0.02)
            parts = [(ra, am * r.uniform(0.6, 1.0), r.uniform(0.07, 0.22)) for ra, am in zip(ratios, amps)]
            x = modal(base, parts, 0.45, attack=0.0002, phase_rand=True, seed=b * 10 + h)
            x *= r.uniform(0.3, 1.0) * (0.85 ** h)
            s = ns(t0)
            k = min(L - s, x.shape[0])
            st = to_stereo(x[:k], pan)
            out[:, s:s + k] += st
    out = eq(out, ("hp", 1200, 0.7), ("lp", 7500, 0.7), ("hs", 5000, 0.7, -3))
    return out * v * 0.25


def wind_chime(p, v=0.5, seed=0):
    f0 = float(hz(p))
    T = float(np.clip(7.0 * (1000.0 / f0) ** 0.5, 2.5, 10.0))
    r = rng("chime", round(p * 4), seed)
    parts = [(1.0, 1.0, T), (1.0006, 0.35, T), (2.756, 0.45, T * 0.5), (2.759, 0.15, T * 0.45),
             (5.404, 0.18, T * 0.22), (8.933, 0.06, T * 0.1)]
    x = modal(f0, parts, min(T * 1.2, 11.0), attack=0.0003)
    clk = _noise_burst(0.003, 3000, 8000, r, 0.0005) * 0.03 * v
    x[: clk.shape[0]] += clk
    return x * v


def finger_cymbal(v=0.5, seed=0, f1=1650.0):
    r = rng("tingsha", seed)
    ratios = [1.0, 1.0012, 1.47, 1.472, 2.09, 2.56, 2.853, 3.6, 4.1]
    parts = [(ra, a, T) for ra, a, T in zip(ratios, [1, 0.8, 0.5, 0.4, 0.35, 0.22, 0.2, 0.08, 0.05],
                                            [5.0, 5.2, 3.5, 3.4, 2.4, 1.8, 1.6, 0.9, 0.7])]
    x = modal(f1, parts, 6.0, attack=0.0002, phase_rand=True, seed=seed)
    clk = _noise_burst(0.004, 3000, 8000, r, 0.0007) * 0.06
    x[: clk.shape[0]] += clk
    return x * v * 0.5


def pumpkin_xylo(p, v=0.7, seed=0):
    """Tuned wooden bar over a hollow pumpkin: marimba-like partials plus a
    warm hollow 'bonk' from the gourd."""
    f0 = float(hz(p))
    r = rng("xylo", round(p * 4), seed)
    T = float(np.clip(1.1 * (587.0 / f0) ** 0.35, 0.5, 1.6))
    b = 0.5 + 0.5 * v
    parts = [
        (1.0, 1.0, T),
        (3.98, 0.20 * b, T * 0.22),
        (9.85, 0.04 * b ** 2, T * 0.08),
    ]
    x = modal(f0, parts, T * 1.6, attack=0.0009)
    t = tvec(x.shape[0])
    x += 0.45 * (1 - np.exp(-t / 0.006)) * np.exp(-6.9 * t / (T * 1.25)) * np.sin(2 * np.pi * f0 * t)
    body = modal(r.uniform(165, 185), [(1, 1, 0.16), (1.83, 0.55, 0.09), (3.05, 0.25, 0.05), (4.4, 0.1, 0.03)], 0.3,
                 attack=0.0015)
    x[: body.shape[0]] += 0.32 * body * v
    th = _noise_burst(0.01, 150, 2200, r, 0.002) * 0.08 * v
    x[: th.shape[0]] += th
    return x * (0.35 + 0.65 * v)


# ----------------------------------------------------------------- box resonance

def box_ir(seed=0, freqs=(420, 640, 870, 1340, 1720, 2100, 2900, 3600), decay=0.05, length=0.12):
    """Short modal impulse response of a small wooden box (music box body)."""
    r = rng("box", seed)
    n = ns(length)
    t = tvec(n)
    h = np.zeros(n)
    for f in freqs:
        f = f * r.uniform(0.95, 1.05)
        h += r.uniform(0.3, 1.0) * np.exp(-t / (decay * r.uniform(0.5, 1.2) * (800 / f) ** 0.3)) * np.sin(
            2 * np.pi * f * t + r.uniform(0, 6))
    h /= np.sqrt(np.sum(h ** 2))
    h *= 0.6
    h[0] += 1.0
    return h


# ----------------------------------------------------------------- part rendering

def render(track: Track, notes, fn, gain=1.0, pan=0.0, pan_spread=0.0, pan_by_pitch=0.0,
           center_pitch=72.0, seed=0, **kw):
    """Render notes (times in seconds) with a per-note mono instrument function."""
    for i, nt in enumerate(notes):
        try:
            x = fn(nt.p, nt.v, dur=nt.d, seed=seed * 1000 + i, **kw)
        except TypeError:
            x = fn(nt.p, nt.v, seed=seed * 1000 + i, **kw)
        pn = pan + pan_by_pitch * (nt.p - center_pitch) / 24.0
        if pan_spread:
            pn += rng("pan", seed, i).uniform(-pan_spread, pan_spread)
        pn = float(np.clip(pn, -1, 1))
        track.add(nt.t, x, gain=gain * nt.x.get("gain", 1.0), pan=pn)
    return track


def piano(p, v=0.6, dur=0.5, seed=0, detune=3.5, strings=2, bright=1.0, damp_t60=0.14):
    """Upright piano note: stiff-string partials (inharmonic), a hammer spectrum
    that brightens with velocity, a strike-position comb, two-stage decay
    (prompt sound + aftersound), slightly out-of-tune unisons (old upright),
    a felt thump, and dampers at note-off."""
    f0 = float(hz(p))
    r = rng("piano", round(p * 4), seed)
    rk = rng("piano-key", round(p * 4))       # per-key constants (tuning of the unisons)
    B = 0.00025 * (f0 / 261.6) ** 0.8 + 0.00004
    K = int(max(3, min(36, 6500.0 / f0)))
    k = np.arange(1, K + 1, dtype=float)
    fk = k * f0 * np.sqrt(1 + B * k * k)
    keep = fk < 7500
    k, fk = k[keep], fk[keep]
    kc = (2.5 + 9.0 * v ** 1.3) * bright * (440.0 / max(f0, 110.0)) ** 0.25
    amp = (1.0 / k ** 0.8) * np.exp(-(k - 1) / kc) * (0.25 + np.abs(np.sin(np.pi * k / 7.3)))
    amp[fk > 4500] *= np.cos(np.clip((fk[fk > 4500] - 4500) / 3000, 0, 1) * np.pi / 2) ** 2
    T = float(np.clip(7.0 * (261.6 / f0) ** 0.75, 0.7, 14.0))
    t60 = T / (1 + 0.00035 * fk + 0.03 * (k - 1))
    hold = max(dur, 0.05)
    length = min(hold + damp_t60 * 1.6 + 0.05, float(np.max(t60)) * 1.1 + 0.05)
    if p >= 89:  # no dampers in the top octaves
        length = min(float(np.max(t60)) * 1.1, 6.0)
    n = ns(length)
    t = tvec(n)
    env_d = np.ones(n)
    if p < 89:
        kd = ns(hold)
        if kd < n:
            env_d[kd:] = np.exp(-6.9 * (t[kd:] - t[kd]) / damp_t60)
    out = np.zeros(n)
    dets = rk.uniform(-detune, detune, strings)
    dets -= dets.mean()
    for s in range(strings):
        ratio = 2 ** (dets[s] / 1200)
        for kk in range(len(k)):
            tau1 = t60[kk] / 6.9 * 0.18
            tau2 = t60[kk] / 6.9
            e = 0.55 * np.exp(-t / tau1) + 0.45 * np.exp(-t / tau2)
            out += amp[kk] * e * np.sin(2 * np.pi * fk[kk] * ratio * t + r.uniform(0, 0.3))
    out /= strings
    out *= env_d * (1 - np.exp(-t / 0.0007))
    thump = filt(r.standard_normal(min(n, ns(0.03))) * np.exp(-tvec(min(n, ns(0.03))) / 0.006),
                 chain(("lp", 900, 0.7), ("hp", 60, 0.7)))
    out[: thump.size] += thump * 0.12 * v
    return out * (0.2 + 0.8 * v ** 1.2)
