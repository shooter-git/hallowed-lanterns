"""Vintage analog synthesis: the 1980s synth-score sound (sequencers through
resonant ladder filters, pulsing basses, brassy pad swells) for the places
where synths are the point: the Deep, and the Marigold Garden's swell, whose
lead SINGS (`sing`: a legato line gliding into each note, its vibrato growing
and its filter blooming on the long notes).

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


def sing(track: Track, notes, p: Patch, gain=1.0, seed=0, gap=0.3, glide=0.16, vib=0.16, vib_rate=5.0,
         bloom=0.7, dip=0.22, sweep=None, pan=0.0):
    """A singing mono line, the lead of a synth ballad. Notes that touch are one phrase: the pitch glides
    into each new note the way a voice does (starting just before it, slower across a wide leap); each
    note is re-articulated with a small dip in level, so the melody is heard as notes rather than a
    siren; the vibrato waits, then grows, deepest on the longest notes (`vib` semitones at 3 s and up);
    and the filter follows the line's loudness and BLOOMS - opens slowly, up to `bloom` octaves - while
    a long note is held. One amplitude envelope per phrase (the patch's a/d/s/r)."""
    from .lines import phrases
    from .core import smoothstep
    for pi, ph in enumerate(phrases(sorted(notes, key=lambda n: n.t), gap)):
        r = rng("sing", seed, pi)
        t0 = ph[0].t
        end = max(nt.t + nt.d for nt in ph)
        n = ns(end - t0 + p.r * 5 + 0.05)
        t = tvec(n)
        semi = np.full(n, float(ph[0].p))
        for k in range(1, len(ph)):
            step = ph[k].p - ph[k - 1].p
            g = glide * (0.7 + 0.06 * min(abs(step), 12.0))
            semi += step * smoothstep((t - (ph[k].t - t0 - 0.4 * g)) / g)
        vel = np.full(n, float(ph[0].v))
        vibd = np.zeros(n)
        blo = np.zeros(n)
        art = np.ones(n)
        for k, nt in enumerate(ph):
            a = ns(nt.t - t0)
            b = min(n, ns(nt.t + nt.d - t0)) if k + 1 < len(ph) else n
            tt = t[a:b] - (nt.t - t0)
            vel[a:] = nt.v
            depth = vib * float(np.clip((nt.d - 0.5) / 2.5, 0.15, 1.0))
            vibd[a:b] = depth * smoothstep((tt - 0.3) / (0.5 + 0.3 * nt.d))
            held = float(np.clip((nt.d - 0.8) / 2.0, 0.0, 1.0))
            blo[a:b] = bloom * held * smoothstep(tt / max(nt.d, 0.5))
            if k:
                art[a:b] *= 1 - dip * np.exp(-np.maximum(tt, 0) / 0.07)
        # smooth the per-note steps (a hand on the expression pedal, not a switch)
        k1 = np.exp(-1 / (0.06 * SR))
        from . import nb
        vel = nb.onepole(vel, k1)
        vibd = nb.onepole(vibd, np.exp(-1 / (0.12 * SR)))
        drift = 1 + 0.05 * np.sin(2 * np.pi * 0.6 * t + r.uniform(0, 6))
        vphase = 2 * np.pi * np.cumsum(vib_rate * drift) / SR + r.uniform(0, 6)
        semi_v = semi + vibd * np.sin(vphase)
        f0 = 440.0 * 2.0 ** ((semi_v - 69.0) / 12.0)
        mix = np.zeros(n)
        for j, (kind, cents, octv, lvl, pw) in enumerate(p.oscs):
            rj = rng("sing", seed, pi, j)
            dr = p.drift * smooth_random(n, rj, 0.3) if p.drift else 0.0
            f = f0 * 2.0 ** (octv + (cents + dr) / 1200.0)
            if kind == "saw":
                y = osc(f, 0, np.zeros(1), float(rj.uniform()))
            else:
                w = np.full(n, float(pw))
                if p.pwm:
                    w = w + p.pwm * np.sin(2 * np.pi * p.pwm_rate * (t0 + t) + 1.7 * j)
                y = osc(f, 1, np.clip(w, 0.05, 0.95), float(rj.uniform()))
            mix += lvl * y
        if p.noise:
            mix += p.noise * r.standard_normal(n)
        hold = end - t0
        aenv = adsr(n, p.a, p.d, p.s, p.r, hold=hold)
        fenv = adsr(n, p.fa, p.fd, p.fs, p.fr, hold=hold)
        base = sweep(t0 + t) if callable(sweep) else np.full(n, float(sweep or 1.0))
        fc = p.cutoff * base * 2.0 ** (p.keytrack * (semi - 60) / 12.0 + p.env_oct * fenv +
                                       p.vel_bright * (vel - 0.6) + blo)
        fc = np.clip(fc, 30.0, p.fmax)
        y = ladder(mix * p.pre, fc, 4.0 * p.res * 0.97, p.drive)
        y = np.tanh(p.sat * y) / np.tanh(p.sat)
        lvl = 10 ** (-p.vel_db * (1 - np.clip(vel, 0, 1)) ** 1.3 / 20)
        track.add(t0, y * aenv * art * lvl * p.level, gain=gain, pan=pan)
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
# the Marigold's singing lead: a saw and a slowly-modulated pulse, a soft saw an octave below for body,
# a gentle filter that tracks the line up (it is never thin at the top nor dull at the bottom)
SINGER = Patch(oscs=[("saw", -4.0, 0, 0.8, 0.5), ("pulse", 4.0, 0, 0.5, 0.42), ("saw", 2.0, -1, 0.28, 0.5)],
               drift=2.5, pwm=0.08, pwm_rate=0.3, cutoff=640.0, res=0.14, env_oct=0.5, keytrack=0.7,
               vel_bright=1.2, a=0.14, d=0.9, s=0.86, r=1.4, fa=0.12, fd=1.0, fs=0.3, fr=1.2,
               drive=1.1, sat=1.15, pre=0.4, fmax=4800.0, level=0.5, vel_db=14.0)
