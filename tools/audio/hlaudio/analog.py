"""Vintage analog synthesis: the 1980s synth-score sound (sequencers through
resonant ladder filters, pulsing basses, brassy pad swells) for the one place
where synths are the point, the Deep.

Built the way the old polysynths and modulars were, so it sounds like warm
gear rather than a plug-in preset:

  * oscillators are band-limited by polyBLEP (saw and pulse; the pulse can be
    width-modulated), two or three per voice, slightly detuned, each with
    its own slow random pitch drift (a few cents, like warm VCOs);
  * a 4-pole transistor-ladder low-pass (zero-delay-feedback, trapezoidal
    one-pole stages, resonance fed back from the fourth stage, a soft tanh
    at its input so it saturates rather than clips), per-sample cutoff:
    a slow sweep (the piece's tide) times a per-note envelope and key
    tracking;
  * per-note amplitude and filter ADSRs, velocity to level and brightness,
    and gentle output saturation.

Chorus, tape wobble and the plate or hall are added on the stem
(effects.chorus / wow_flutter, the Stage's sends).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numba import njit

from .core import SR, hz, ns, rng, tvec, smooth_random, adsr, Track


@njit(cache=True, fastmath=True)
def _blep(t, dt):
    if t < dt:
        t = t / dt
        return t + t - t * t - 1.0
    if t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit(cache=True, fastmath=True)
def osc(freq, kind, pw, phase0):
    """polyBLEP oscillator following a per-sample frequency (Hz): kind 0 =
    saw, 1 = pulse with per-sample width `pw` (0..1)."""
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        dt = freq[i] / SR
        if dt > 0.49:
            dt = 0.49
        if kind == 0:
            v = 2.0 * ph - 1.0 - _blep(ph, dt)
        else:
            w = pw[i]
            v = 1.0 if ph < w else -1.0
            v += _blep(ph, dt)
            t2 = ph - w
            if t2 < 0.0:
                t2 += 1.0
            v -= _blep(t2, dt)
            v -= 2.0 * w - 1.0          # remove the DC of an asymmetric pulse
        out[i] = v
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


@njit(cache=True, fastmath=True)
def ladder(x, fc, k, drive):
    """4-pole ladder low-pass, zero-delay feedback (Zavalishin's TPT
    structure) with a tanh at the input: resonance k 0..4 (4 = self
    oscillation), per-sample cutoff fc (Hz)."""
    n = x.shape[0]
    y = np.empty(n)
    s1 = 0.0
    s2 = 0.0
    s3 = 0.0
    s4 = 0.0
    for i in range(n):
        f = fc[i]
        if f > 0.42 * SR:
            f = 0.42 * SR
        if f < 10.0:
            f = 10.0
        g = math.tan(math.pi * f / SR)
        G = g / (1.0 + g)
        m = 1.0 - G
        S = G * G * G * m * s1 + G * G * m * s2 + G * m * s3 + m * s4
        G4 = G * G * G * G
        y4 = (G4 * x[i] + S) / (1.0 + k * G4)
        u = x[i] - k * y4
        u = math.tanh(drive * u) / drive
        v = (u - s1) * G
        y1 = v + s1
        s1 = y1 + v
        v = (y1 - s2) * G
        y2 = v + s2
        s2 = y2 + v
        v = (y2 - s3) * G
        y3 = v + s3
        s3 = y3 + v
        v = (y3 - s4) * G
        yy = v + s4
        s4 = yy + v
        y[i] = yy * (1.0 + 0.45 * k)      # keep the passband level as resonance rises
    return y


@dataclass
class Patch:
    """One synth voice. oscs: (kind 'saw'|'pulse', cents, octave, level, pw)."""
    oscs: list = field(default_factory=lambda: [("saw", -4.0, 0, 1.0, 0.5), ("saw", 4.0, 0, 0.9, 0.5)])
    drift: float = 3.0          # cents of slow random wander per oscillator
    pwm: float = 0.0            # pulse-width modulation depth (0..0.4)
    pwm_rate: float = 0.35
    noise: float = 0.0
    cutoff: float = 800.0       # Hz (multiplied by the sweep curve if one is given)
    res: float = 0.3            # 0..1 (1 = on the edge of self-oscillation)
    env_oct: float = 2.0        # filter envelope depth (octaves)
    keytrack: float = 0.5       # cutoff follows pitch (1 = fully)
    vel_bright: float = 0.6     # octaves of cutoff per full velocity
    a: float = 0.005
    d: float = 0.3
    s: float = 0.6
    r: float = 0.25
    fa: float = 0.003
    fd: float = 0.25
    fs: float = 0.0
    fr: float = 0.3
    drive: float = 1.4          # ladder input drive
    sat: float = 1.3            # output saturation
    pre: float = 0.45           # level into the filter
    fmax: float = 7000.0
    level: float = 0.5
    vel_db: float = 18.0


def _vgain(v, range_db):
    return float(10 ** (-range_db * (1 - np.clip(v, 0, 1)) ** 1.3 / 20))


def voice(midi, dur, vel, p: Patch, seed=0, sweep=None, t_abs=0.0):
    """Render one note (mono) -> array (dur + release tail)."""
    r = rng("analog", seed)
    n = ns(dur + p.r * 5 + 0.02)
    t = tvec(n)
    f0 = float(hz(midi))
    mix = np.zeros(n)
    for j, (kind, cents, octv, lvl, pw) in enumerate(p.oscs):
        rj = rng("analog", seed, j)
        dr = p.drift * smooth_random(n, rj, 0.3) if p.drift else 0.0
        f = f0 * 2.0 ** (octv + (cents + dr) / 1200.0)
        f = np.asarray(f, dtype=np.float64) * np.ones(n)
        if kind == "saw":
            y = osc(f, 0, np.zeros(1), float(rj.uniform()))
        else:
            w = np.full(n, float(pw))
            if p.pwm:
                w = w + p.pwm * np.sin(2 * np.pi * p.pwm_rate * (t_abs + t) + 1.7 * j)
            y = osc(f, 1, np.clip(w, 0.05, 0.95), float(rj.uniform()))
        mix += lvl * y
    if p.noise:
        mix += p.noise * r.standard_normal(n)
    aenv = adsr(n, p.a, p.d, p.s, p.r, hold=dur)
    fenv = adsr(n, p.fa, p.fd, p.fs, p.fr, hold=dur)
    base = sweep(t_abs + t) if callable(sweep) else np.full(n, float(sweep or 1.0))
    fc = p.cutoff * base * 2.0 ** (p.keytrack * (midi - 60) / 12.0 + p.env_oct * fenv + p.vel_bright * (vel - 0.6))
    fc = np.clip(fc, 30.0, p.fmax)
    y = ladder(mix * p.pre, fc, 4.0 * p.res * 0.97, p.drive)
    y = np.tanh(p.sat * y) / np.tanh(p.sat)
    return y * aenv * _vgain(vel, p.vel_db) * p.level


def play(track: Track, notes, p: Patch, gain=1.0, seed=0, sweep=None, pan=0.0, pan_spread=0.0):
    """Notes (seconds) through the patch into a track; sweep(t_abs) scales
    the cutoff (the slow filter movement), or None."""
    r = rng("analog-play", seed)
    for i, nt in enumerate(notes):
        y = voice(nt.p, nt.d, nt.v, p, seed=f"{seed}-{i}", sweep=sweep, t_abs=nt.t)
        pn = pan + nt.x.get("pan", 0.0) + (r.uniform(-pan_spread, pan_spread) if pan_spread else 0.0)
        track.add(nt.t, y, gain=gain, pan=float(np.clip(pn, -1, 1)))
    return track


# ----------------------------------------------------------------- patches

# a dark pulsing bass: saw + pulse + a square an octave down, short filter blip
BASS = Patch(oscs=[("saw", 0.0, 0, 1.0, 0.5), ("pulse", 5.0, 0, 0.6, 0.42), ("pulse", -3.0, -1, 0.55, 0.5)],
             drift=2.5, cutoff=150.0, res=0.32, env_oct=2.6, keytrack=0.35, vel_bright=1.2,
             a=0.003, d=0.22, s=0.55, r=0.07, fa=0.002, fd=0.11, fs=0.0, fr=0.1,
             drive=1.8, sat=1.5, pre=0.5, fmax=2400.0, level=0.55, vel_db=14.0)
# the sequencer: two detuned saws and a narrow pulse, resonant, a bright blip per note
SEQ = Patch(oscs=[("saw", -5.0, 0, 1.0, 0.5), ("saw", 6.0, 0, 0.85, 0.5), ("pulse", 0.0, -1, 0.35, 0.3)],
            drift=3.0, pwm=0.12, cutoff=420.0, res=0.6, env_oct=1.6, keytrack=0.6, vel_bright=0.8,
            a=0.002, d=0.16, s=0.25, r=0.12, fa=0.001, fd=0.13, fs=0.0, fr=0.15,
            drive=1.6, sat=1.3, pre=0.45, fmax=6000.0, level=0.42, vel_db=18.0)
# the brassy pad swell (an OB/Prophet-style poly): slow attack, filter opening with it
SWELL = Patch(oscs=[("saw", -7.0, 0, 1.0, 0.5), ("saw", 7.0, 0, 1.0, 0.5), ("pulse", 0.0, 0, 0.5, 0.35)],
              drift=4.0, pwm=0.15, pwm_rate=0.22, cutoff=360.0, res=0.18, env_oct=2.0, keytrack=0.4,
              vel_bright=0.8, a=1.8, d=2.0, s=0.85, r=2.6, fa=2.6, fd=3.0, fs=0.55, fr=2.5,
              drive=1.3, sat=1.2, pre=0.4, fmax=4500.0, level=0.3, vel_db=16.0)
# the old arpeggio voice, re-voiced: soft saw + triangle-ish pulse, gentle resonance
ARP = Patch(oscs=[("saw", -3.0, 0, 0.7, 0.5), ("pulse", 3.0, 0, 0.6, 0.5)],
            drift=2.5, cutoff=520.0, res=0.42, env_oct=1.6, keytrack=0.5, vel_bright=0.8,
            a=0.003, d=0.28, s=0.2, r=0.18, fa=0.002, fd=0.2, fs=0.0, fr=0.2,
            drive=1.4, sat=1.2, pre=0.45, fmax=5500.0, level=0.5, vel_db=20.0)
