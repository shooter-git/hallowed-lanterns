"""Electronic layers for the rescore (the only synthesised parts): glassy
cristal-baschet-like tones, slow filtered arpeggios, warm detuned analog pads,
a soft pulsing sub, and the synthetic half of a 'braam'.

All functions render notes (times in seconds) into a Track; on circular
Tracks everything wraps, and global modulation curves should be periodic.
"""
from __future__ import annotations

import numpy as np

from . import nb
from .core import SR, hz, ns, rng, tvec, Track, smoothstep, smooth_random
from .effects import chain, filt
from .lines import wt_osc


def vgain(v, range_db=24.0):
    """Velocity -> amplitude on a dB curve (like the sampler's)."""
    return float(10 ** (-range_db * (1 - np.clip(v, 0, 1)) ** 1.3 / 20))


def _adsr(n, a, rel_start, rel, curve=1.0):
    t = tvec(n)
    env = smoothstep(t / max(a, 1e-3)) ** curve
    if rel_start < n / SR:
        k = t >= rel_start
        env[k] *= np.exp(-(t[k] - rel_start) / max(rel / 4.0, 1e-3))
    return env


def glass(track: Track, notes, gain=1.0, seed=0, attack=0.35, release=2.5, bright=1.0, pan_spread=0.6,
          breath=0.15, glide=None, detune=4.0, trem=0.25):
    """Cristal-baschet / bowed-glass tone: a pure fundamental with a few soft
    harmonics, a faint inharmonic shimmer, two detuned rods beating slowly,
    a breathy resonant bow noise and a slow tremolo."""
    r0 = rng("glass", seed)
    for i, nt in enumerate(sorted(notes, key=lambda n: n.t)):
        r = rng("glass", seed, i)
        a = nt.x.get("attack", attack)
        rel = nt.x.get("release", release)
        n = ns(nt.d + rel * 1.5)
        t = tvec(n)
        f0 = float(hz(nt.p))
        pitch = np.ones(n)
        if glide and i > 0:
            pass
        vib = 1 + 0.0015 * np.sin(2 * np.pi * r.uniform(4.2, 5.2) * t + r.uniform(0, 6)) * smoothstep((t - 0.4) / 0.8)
        y = np.zeros(n)
        parts = [(1.0, 1.0), (2.0, 0.28 * bright), (3.0, 0.09 * bright), (4.0, 0.035 * bright), (2.76, 0.03 * bright)]
        for k, (ratio, amp) in enumerate(parts):
            f = f0 * ratio
            if f > 9000:
                continue
            for d in (-1, 1):
                fd = f * 2 ** (d * detune * r.uniform(0.6, 1.2) / 1200)
                ph = 2 * np.pi * np.cumsum(fd * vib) / SR + r.uniform(0, 6)
                y += 0.5 * amp * np.sin(ph) * (1.0 if k == 0 else np.exp(-t / (2.5 + 2 * r.uniform())))
        if breath:
            nz = nb.svf(r.standard_normal(n), np.full(n, f0), 35.0, 1)
            nz /= np.std(nz) + 1e-9
            y += breath * 0.15 * nz
        env = _adsr(n, a, nt.d, rel)
        env *= 1 + trem * 0.15 * np.sin(2 * np.pi * r.uniform(0.25, 0.6) * t + r.uniform(0, 6))
        y *= env * vgain(nt.v, 16.0) * 0.3
        pan = nt.x.get("pan", r0.uniform(-pan_spread, pan_spread))
        track.add(nt.t, y, gain=gain, pan=float(np.clip(pan, -1, 1)))
    return track


def arp(track: Track, notes, gain=1.0, seed=0, cutoff=None, res=2.2, decay=0.35, shape=0.5, pan=0.0,
        pan_wobble=0.3, sub_osc=0.0):
    """Soft plucked synth for slow hypnotic arpeggios. `cutoff` is a callable
    of absolute time (s) -> Hz (the filter movement), or a number."""
    r = rng("arp", seed)
    for i, nt in enumerate(notes):
        n = ns(min(nt.d, 1.2) + decay * 3)
        t = tvec(n)
        f0 = float(hz(nt.p))
        saw = wt_osc(np.full(n, f0 * 2 ** (r.normal(0, 3) / 1200)), lambda k: 1.0 / k, ceiling=7000)
        tri = wt_osc(np.full(n, f0), lambda k: (1.0 / k ** 2) * (1 if k % 2 else 0), ceiling=7000)
        x = shape * saw + (1 - shape) * tri * 1.6
        if sub_osc:
            x += sub_osc * np.sin(np.pi * f0 * t)
        c = cutoff(nt.t + t) if callable(cutoff) else np.full(n, cutoff or 2000.0)
        fenv = 1 + 1.5 * np.exp(-t / (decay * 0.5))
        x = nb.svf(x, np.clip(c * fenv * (0.6 + 0.6 * nt.v), 80, 9000), res, 0)
        env = (1 - np.exp(-t / 0.004)) * np.exp(-t / decay)
        rel = t > nt.d
        env[rel] *= np.exp(-(t[rel] - nt.d) / 0.08)
        y = x * env * vgain(nt.v, 24.0) * 0.35
        p = pan + pan_wobble * np.sin(i * 0.9)
        track.add(nt.t, y, gain=gain, pan=float(np.clip(p, -1, 1)))
    return track


def pad(track: Track, notes, gain=1.0, seed=0, voices=5, detune=12.0, cutoff=900.0, res=0.8, attack=2.0,
        release=3.0, drift=0.3, lfo=0.07, width=0.8, curve=None):
    """Warm detuned analog-style pad: several saws per note, slowly drifting,
    through a gently moving low-pass. `curve` (callable of time -> 0..1) can
    open the filter over a section."""
    for i, nt in enumerate(notes):
        r = rng("pad", seed, i)
        n = ns(nt.d + release * 1.5)
        t = tvec(n)
        f0 = float(hz(nt.p))
        out = np.zeros((2, n))
        for v in range(voices):
            dc = (v - (voices - 1) / 2) / max(1, (voices - 1) / 2) * detune * r.uniform(0.7, 1.1)
            f = f0 * 2 ** ((dc + drift * 6 * smooth_random(n, r, 0.25)) / 1200)
            x = wt_osc(f, lambda k: 1.0 / k, ceiling=6000, phase0=r.uniform())
            pn = (v - (voices - 1) / 2) / max(1, (voices - 1) / 2) * width
            gl, gr = np.cos((pn + 1) * np.pi / 4), np.sin((pn + 1) * np.pi / 4)
            out[0] += x * gl
            out[1] += x * gr
        mod = 1 + 0.25 * np.sin(2 * np.pi * lfo * (nt.t + t) + r.uniform(0, 6))
        open_ = curve(nt.t + t) if curve else 0.5
        fc = np.clip(cutoff * mod * (0.5 + open_) * (0.6 + 0.6 * nt.v), 120, 7000)
        for c in range(2):
            out[c] = nb.svf(out[c], fc, res, 0)
        env = _adsr(n, nt.x.get("attack", attack), nt.d, release)
        out *= env * vgain(nt.v, 22.0) * 0.12 / np.sqrt(voices)
        track.add(nt.t, out, gain=gain)
    return track


def sub_pulse(track: Track, notes, gain=1.0, seed=0, decay=0.45, drive=1.4):
    """Soft pulsing sub: a sine an octave or two down, short swell per pulse,
    a little saturation so it reads on small speakers."""
    for i, nt in enumerate(notes):
        n = ns(min(nt.d, 2.0) + decay * 4)
        t = tvec(n)
        f0 = float(hz(nt.p))
        ph = 2 * np.pi * f0 * t
        x = np.sin(ph) + 0.15 * np.sin(2 * ph)
        x = np.tanh(drive * x) / np.tanh(drive)
        env = (1 - np.exp(-t / 0.02)) * np.exp(-t / decay)
        track.add(nt.t, x * env * vgain(nt.v, 18.0) * 0.5, gain=gain)
    return track


def sub_swell(track: Track, start, dur, pitch, gain=1.0, attack=1.5, release=2.0):
    """A long sub tone (the low half of a braam)."""
    n = ns(dur + release * 2)
    t = tvec(n)
    f0 = float(hz(pitch))
    ph = 2 * np.pi * f0 * t
    x = np.tanh(1.6 * (np.sin(ph) + 0.25 * np.sin(2 * ph))) / np.tanh(1.6)
    env = _adsr(n, attack, dur, release, curve=1.5)
    track.add(start, x * env * 0.45, gain=gain)
    return track


def growl(track: Track, start, dur, pitch, gain=1.0, attack=0.6, release=1.5, seed=0):
    """Dark distorted saw cluster that thickens a sampled brass braam."""
    r = rng("growl", seed)
    n = ns(dur + release * 2)
    t = tvec(n)
    out = np.zeros(n)
    for k in range(4):
        f = float(hz(pitch)) * 2 ** (r.uniform(-9, 9) / 1200)
        out += wt_osc(np.full(n, f), lambda kk: 1.0 / kk, ceiling=3000, phase0=r.uniform())
    out = np.tanh(2.2 * out / 4)
    env = _adsr(n, attack, dur, release, curve=1.5)
    fc = 180 + 900 * env
    out = nb.svf(out, fc, 0.9, 0) * env
    track.add(start, out * 0.35, gain=gain)
    return track


def riser(track: Track, start, dur, gain=1.0, seed=0, lo=200.0, hi=4000.0):
    """Soft filtered-noise swell into a downbeat."""
    r = rng("riser", seed)
    n = ns(dur + 0.3)
    t = tvec(n)
    u = np.clip(t / dur, 0, 1)
    fc = lo * (hi / lo) ** (u ** 2)
    out = np.vstack([nb.svf(rng("riser", seed, c).standard_normal(n), fc, 1.4, 1) for c in range(2)])
    env = u ** 2.5 * np.where(t > dur, np.exp(-(t - dur) / 0.05), 1.0)
    out = filt(out * env, chain(("lp", 6000, 0.7)))
    track.add(start, out * 0.15, gain=gain)
    return track


def glass_line(track: Track, notes, gain=1.0, seed=0, glide=0.45, attack=0.6, release=3.0, bright=0.8,
               pan=0.0, gap=0.6, vib=0.003, breath=0.12):
    """A singing glass voice that slides between notes (whale-song-like):
    touching notes become one continuous phrase with smooth portamento."""
    from .lines import phrases
    for pi, ph in enumerate(phrases(sorted(notes, key=lambda n: n.t), gap)):
        r = rng("glassline", seed, pi)
        t0 = ph[0].t
        end = max(n.t + n.d for n in ph)
        n = ns(end - t0 + release * 1.5)
        t = tvec(n)
        semi = np.full(n, ph[0].p)
        lvl = np.full(n, vgain(ph[0].v, 16.0))
        for k in range(1, len(ph)):
            a = ph[k].t - t0 - glide * 0.5
            u = smoothstep((t - a) / glide)
            semi += (ph[k].p - ph[k - 1].p) * u
            lvl += (vgain(ph[k].v, 16.0) - vgain(ph[k - 1].v, 16.0)) * u
        f = hz(semi) * (1 + vib * np.sin(2 * np.pi * r.uniform(4.0, 5.0) * t) * smoothstep((t - 0.6) / 1.0))
        y = np.zeros(n)
        for ratio, amp in [(1.0, 1.0), (2.0, 0.3 * bright), (3.0, 0.1 * bright), (4.0, 0.04 * bright)]:
            for d in (-1, 1):
                ph_ = 2 * np.pi * np.cumsum(f * ratio * 2 ** (d * 3.5 / 1200)) / SR + r.uniform(0, 6)
                y += 0.5 * amp * np.sin(ph_)
        if breath:
            nz = nb.svf(r.standard_normal(n), np.clip(f, 60, 8000), 30.0, 1)
            y += breath * 0.15 * nz / (np.std(nz) + 1e-9)
        env = _adsr(n, attack, end - t0, release) * lvl
        track.add(t0, y * env * 0.3, gain=gain, pan=pan)
    return track
