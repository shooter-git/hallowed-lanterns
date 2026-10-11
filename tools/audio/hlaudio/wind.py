"""Winds: breathy bamboo flute (with chiff and a pitched breath that 'sings' in
the tube) and a soft, dark French horn section."""
from __future__ import annotations

import numpy as np

from . import nb
from .core import SR, ns, rng, Track
from .effects import chain, filt
from .lines import LineStyle, phrases, curves, wt_osc, flute_amps
from .bowed import split_voices


def flute(track: Track, notes, gain=1.0, pan=0.0, seed=0, breath=1.0, style_over=None, tone="bamboo"):
    """Bamboo flute (dizi/bansuri-like, without membrane buzz)."""
    st = LineStyle(attack=0.06, release=0.25, glide=0.045, gap=0.05, vib_rate=5.0, vib_depth=9.0,
                   vib_delay=0.35, vib_ramp=0.4, vib_amp=0.07, drift=4.0, intonation=3.0, scoop=22,
                   scoop_time=0.05, dip=0.25, swell=0.15, vel_curve=1.2, min_note_attack=0.025)
    if style_over:
        for k, v in style_over.items():
            setattr(st, k, v)
    stem = track.like()
    for vi, voice in enumerate(split_voices(notes)):
        for pi, ph in enumerate(phrases(voice, st.gap)):
            r = rng("flute", seed, vi, pi)
            t0, f, amp, onset = curves(ph, st, seed * 31 + vi * 7 + pi)
            n = f.shape[0]
            tone_sig = wt_osc(f, flute_amps, ceiling=8000, phase0=r.uniform())
            lvl = np.clip(amp, 0, 1)
            # pitched breath: noise through a comb tuned to the tube
            nz = r.standard_normal(n)
            pb = nb.comb_var(nz, SR / f, 0.62, 0.35)
            pb = filt(pb, chain(("hp", 500, 0.7), ("lp", 5000, 0.7)))
            pb /= np.std(pb) + 1e-9
            bb = filt(r.standard_normal(n), chain(("hp", 2000, 0.7), ("lp", 5000, 0.7)))
            # chiff on tongued onsets
            ch = np.zeros(n)
            for i in np.nonzero(onset)[0]:
                k = min(n - i, ns(0.07))
                e = np.exp(-np.arange(k) / ns(0.018)) * (1 - np.exp(-np.arange(k) / ns(0.003)))
                ch[i:i + k] += e
            chiff = nb.svf(r.standard_normal(n), np.clip(f * 3.2, 600, 7000), 2.5, 1) * ch
            # softer notes are breathier
            breathy = 0.10 + 0.12 * (1 - lvl)
            y = amp * (0.8 * tone_sig + breath * breathy * 0.35 * pb + breath * 0.012 * bb) + 0.12 * breath * chiff * lvl
            stem.add(t0, y, gain=gain * 0.5, pan=pan)
    stem.buf = filt(stem.buf, chain(("hp", 180, 0.7), ("peak", 1500, 0.8, 1.5), ("hs", 7000, 0.7, -4)),
                    stem.circular).astype(np.float32)
    track.mix(stem)
    return track


def horn(track: Track, notes, gain=1.0, pan=0.2, seed=0, players=2, style_over=None, brass=1.0):
    """Soft French horn section: dark, round, slow-blooming."""
    stem = track.like()
    for vi, voice in enumerate(split_voices(notes)):
        for pl in range(players):
            r = rng("horn", seed, vi, pl)
            st = LineStyle(attack=0.16, release=0.55, glide=0.06, gap=0.06, vib_rate=4.8, vib_depth=3.5,
                           vib_delay=0.6, vib_ramp=0.8, drift=3.0, intonation=3.0, scoop=28, scoop_time=0.08,
                           dip=0.18, swell=0.22, vel_curve=1.5, detune=r.normal(0, 4) if players > 1 else 0)
            if style_over:
                for k, v in style_over.items():
                    setattr(st, k, v)
            for pi, ph in enumerate(phrases(voice, st.gap)):
                jit = r.normal(0, 0.015) if players > 1 else 0
                t0, f, amp, onset = curves(ph, st, seed * 97 + vi * 11 + pl * 3 + pi)
                n = f.shape[0]
                osc = wt_osc(f, lambda k: 1.0 / k ** 0.85, ceiling=7000, phase0=r.uniform())
                lvl = np.clip(amp, 0, 1)
                fc = f * (1.4 + 4.0 * brass * lvl ** 1.6) + 150
                y = nb.svf(osc, np.minimum(fc, 6000), 0.65, 0)
                y = nb.svf(y, np.minimum(fc * 1.6, 7000), 0.6, 0)
                br = filt(r.standard_normal(n), chain(("hp", 300, 0.7), ("lp", 2500, 0.7))) * 0.01 * lvl
                stem.add(t0 + jit, amp * y + br, gain=gain * 0.6 / np.sqrt(players),
                         pan=float(np.clip(pan + r.uniform(-0.15, 0.15), -1, 1)))
    stem.buf = filt(stem.buf, chain(("hp", 45, 0.7), ("peak", 420, 0.9, 3.0), ("peak", 1100, 1.2, 1.0),
                                    ("hs", 3000, 0.7, -6)), stem.circular).astype(np.float32)
    track.mix(stem)
    return track
