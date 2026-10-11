"""Plucked strings with extended Karplus-Strong: harp, guzheng (zither, with
pitch-bend ornaments), nylon guitar and pizzicato strings.

Each note runs two slightly detuned string polarisations (double decay and a
gentle beat), with a pluck-position comb on the excitation, a finger/pick
low-pass that opens with velocity, loop damping for frequency-dependent decay,
optional stiffness (all-pass dispersion), then a modal body IR per stem.
"""
from __future__ import annotations

import numpy as np

from . import nb
from .core import SR, hz, ns, rng, tvec, Track, smoothstep
from .effects import chain, filt, convolve
from .body import stereo_body

KINDS = {
    #          t60 at 220Hz, lp (loop damping), pos, exc softness, dispersion, stages, body
    "harp":   dict(t60=6.0, lp=0.28, pos=0.42, harm=5.0, disp=0.0, stages=0, body="harp", t60_exp=0.55),
    "zheng":  dict(t60=6.5, lp=0.16, pos=0.13, harm=9.0, disp=-0.12, stages=2, body="zheng", t60_exp=0.5),
    "guitar": dict(t60=3.8, lp=0.34, pos=0.16, harm=5.0, disp=-0.03, stages=1, body="guitar", t60_exp=0.6),
    "big_guitar": dict(t60=7.5, lp=0.24, pos=0.17, harm=6.0, disp=-0.04, stages=1, body="guitar", t60_exp=0.45),
    "pizz":   dict(t60=0.9, lp=0.45, pos=0.22, harm=4.0, disp=0.0, stages=0, body="violin", t60_exp=0.35),
    "pizz_low": dict(t60=1.8, lp=0.42, pos=0.22, harm=3.5, disp=0.0, stages=0, body="cello", t60_exp=0.35),
}


def _phase_delay_onepole(p, w):
    return np.arctan2(p * np.sin(w), 1 - p * np.cos(w)) / w


def _phase_delay_ap(a, w):
    # H = (a + z^-1)/(1 + a z^-1)
    z = np.exp(-1j * w)
    H = (a + z) / (1 + a * z)
    return -np.angle(H) / w


def pitch_curve(f0, n, bends=None, vib=None, seed=0):
    """Frequency per sample. bends = [(t_s, semitones, glide_s), ...] absolute
    offsets from f0 reached at t over glide; vib = (cents, rate, start_s)."""
    t = tvec(n)
    semi = np.zeros(n)
    cur = 0.0
    for (tb, s, g) in (bends or []):
        semi += (s - cur) * smoothstep((t - tb) / max(g, 1e-3))
        cur = s
    if vib:
        c, rate, st = vib
        env = smoothstep((t - st) / 0.25)
        semi += c / 100 * env * np.sin(2 * np.pi * rate * np.maximum(t - st, 0))
    return f0 * 2 ** (semi / 12)


def ks_note(p, v=0.7, dur=None, kind="harp", seed=0, length=None, bends=None, vib=None,
            damp_at=None, damp_t60=0.12, bright=1.0):
    k = KINDS[kind]
    r = rng("ks", kind, round(p * 8), seed)
    f0 = float(hz(p))
    t60 = k["t60"] * (220.0 / f0) ** k["t60_exp"]
    t60 = float(np.clip(t60, 0.25, 12))
    if length is None:
        length = min(t60 * 1.3 + 0.1, 10.0)
        if damp_at is not None:
            length = min(length, damp_at + damp_t60 * 1.5 + 0.05)
    n = ns(length)
    f = pitch_curve(f0, n, bends, vib) if (bends or vib) else np.full(n, f0)
    w0 = 2 * np.pi * f0 / SR
    lp = float(np.clip(k["lp"] * (1.15 - 0.3 * v) / bright, 0.0, 0.9))
    disp = k["disp"]
    stages = k["stages"]
    tau = _phase_delay_onepole(lp, w0) + (stages * _phase_delay_ap(disp, w0) if stages else 0)
    Hmag = (1 - lp) / np.sqrt(1 - 2 * lp * np.cos(w0) + lp * lp)
    g = 0.001 ** (1 / (f0 * t60)) / Hmag
    gain = np.full(n, min(g, 0.99995))
    if damp_at is not None:
        kk = ns(damp_at)
        if kk < n:
            gd = 0.001 ** (1 / (f0 * damp_t60)) / Hmag
            ramp = smoothstep((np.arange(n - kk)) / ns(0.02))
            gain[kk:] = gain[kk:] * (1 - ramp) + gd * ramp
    period = SR / f0
    # excitation: one period of shaped noise + a smooth pulse, pluck-position comb
    N = int(period)
    e = r.standard_normal(N) * 0.6
    pulse_w = max(2, int(N * 0.18))
    pulse = np.hanning(pulse_w)
    e[:pulse_w] += pulse * 1.6
    cut = min(7000.0, f0 * (1.5 + k["harm"] * (0.4 + 0.6 * v) * bright))
    e = filt(e, chain(("lp", max(300.0, cut), 0.6), ("lp", max(300.0, cut * 1.3), 0.6)))
    pd = max(1, int(round(k["pos"] * N)))
    e = e - np.concatenate([np.zeros(pd), e[:-pd]]) * 0.92
    e = e / (np.max(np.abs(e)) + 1e-9)
    out = np.zeros(n)
    for pol, (dc, gw) in enumerate([(0.0, 0.62), (r.uniform(0.25, 0.8), 0.38)]):
        ff = f * 2 ** (dc / 1200)
        delay = SR / ff - tau
        gg = gain * (1.0 if pol == 0 else 0.9997)
        y = nb.ks_string(n, e * gw, delay, gg, lp, disp, stages)
        out += y
    out = filt(out, chain(("hp", 30.0, 0.7)))
    t = tvec(n)
    out *= 1 - np.exp(-t / 0.0006)
    fadeout = np.ones(n)
    kf = min(n, ns(0.05))
    fadeout[-kf:] = np.linspace(1, 0, kf)
    return out * fadeout * (0.25 + 0.75 * v) * 0.5


def render_plucked(track: Track, notes, kind="harp", gain=1.0, pan=0.0, pan_by_pitch=0.0, center=60,
                   seed=0, body=True, body_mix=1.0, players=1, spread=0.012, detune=4.0, let_ring=True,
                   pan_spread=0.0):
    """Render plucked notes (seconds) into a stem, then through a stereo body IR."""
    stem = track.like()
    for i, nt in enumerate(notes):
        for pl in range(players):
            r = rng("pl", seed, i, pl)
            dt = r.normal(0, spread) if players > 1 else 0.0
            dp = r.normal(0, detune) / 100 if players > 1 else 0.0
            damp = None if (let_ring and not nt.x.get("damp")) else nt.d
            x = ks_note(nt.p + dp, nt.v * r.uniform(0.9, 1.0) if players > 1 else nt.v, kind=kind,
                        seed=seed * 7919 + i * 13 + pl, bends=nt.x.get("bends"), vib=nt.x.get("vib"),
                        damp_at=damp, bright=nt.x.get("bright", 1.0))
            pn = pan + pan_by_pitch * (nt.p - center) / 24.0 + (r.uniform(-pan_spread, pan_spread) if pan_spread else 0)
            stem.add(nt.t + dt, x, gain=gain / np.sqrt(players) * nt.x.get("gain", 1.0),
                     pan=float(np.clip(pn, -1, 1)))
    if body:
        ir = stereo_body(KINDS[kind]["body"], seed)
        y = np.vstack([convolve(stem.buf[0], ir[0], stem.circular), convolve(stem.buf[1], ir[1], stem.circular)])
        if not stem.circular:
            y = y[:, : stem.n]
        stem.buf = ((1 - body_mix) * stem.buf + body_mix * y).astype(np.float32)
    track.mix(stem)
    return track
