"""Bowed strings: lush ensemble sections and an expressive solo cello.

Every player is a band-limited sawtooth line (see lines.py) with its own
detune, timing, vibrato and intonation, a level-dependent low-pass (louder =
brighter) and rosin/bow noise. A section's players are summed and passed
through a stereo modal body IR (violin/viola/cello/bass), then EQ'd.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from . import nb
from .core import SR, ns, rng, Track
from .effects import chain, filt, convolve
from .body import stereo_body
from .lines import LineStyle, phrases, curves, wt_osc, saw_amps

SECTIONS = {
    "violins":  dict(body="violin", players=7, pan=(-0.75, -0.15), detune=7, vib=(5.5, 13), bright=1.0,
                     attack=0.22, release=0.6, noise=0.012, eq=[("hp", 180, 0.7), ("peak", 2800, 0.8, -2), ("hs", 6000, 0.7, -5)]),
    "violins2": dict(body="violin", players=6, pan=(-0.35, 0.15), detune=7, vib=(5.3, 12), bright=0.9,
                     attack=0.25, release=0.6, noise=0.010, eq=[("hp", 160, 0.7), ("peak", 2800, 0.8, -2), ("hs", 6000, 0.7, -5)]),
    "violas":   dict(body="viola", players=5, pan=(0.0, 0.45), detune=6, vib=(5.2, 12), bright=0.8,
                     attack=0.25, release=0.6, noise=0.010, eq=[("hp", 110, 0.7), ("hs", 5000, 0.7, -5)]),
    "cellos":   dict(body="cello", players=5, pan=(0.25, 0.7), detune=5, vib=(5.0, 11), bright=0.75,
                     attack=0.25, release=0.7, noise=0.008, eq=[("hp", 50, 0.7), ("peak", 250, 1.0, 1.5), ("hs", 4000, 0.7, -5)]),
    "basses":   dict(body="bass", players=3, pan=(0.35, 0.8), detune=4, vib=(4.6, 8), bright=0.6,
                     attack=0.3, release=0.8, noise=0.006, eq=[("hp", 30, 0.7), ("lp", 3000, 0.7)]),
    "solo_cello": dict(body="cello", players=1, pan=(0.05, 0.05), detune=0, vib=(5.4, 17), bright=0.95,
                       attack=0.14, release=0.55, noise=0.02, eq=[("hp", 55, 0.7), ("peak", 300, 1.0, 1.5), ("peak", 2200, 1.0, -1.5), ("hs", 5000, 0.7, -4)]),
    "solo_violin": dict(body="violin", players=1, pan=(-0.15, -0.15), detune=0, vib=(5.7, 16), bright=0.9,
                        attack=0.12, release=0.5, noise=0.018, eq=[("hp", 190, 0.7), ("peak", 2800, 0.8, -2.5), ("hs", 5500, 0.7, -5)]),
}


def split_voices(notes):
    """Assign (possibly polyphonic) notes to monophonic voices. Notes starting
    together are ranked by pitch so chord voices stay connected."""
    if all("voice" in n.x for n in notes):
        vs = {}
        for n in notes:
            vs.setdefault(n.x["voice"], []).append(n)
        return list(vs.values())
    groups = {}
    for n in sorted(notes, key=lambda n: (round(n.t, 3), n.p)):
        groups.setdefault(round(n.t, 3), []).append(n)
    voices: list[list] = []
    for t in sorted(groups):
        g = groups[t]
        # a voice can take this note if its last note started earlier and has
        # ended (or overlaps by less than a legato second): chords stay connected
        free = [i for i, v in enumerate(voices) if v[-1].t < t - 1e-6 and v[-1].t + v[-1].d <= t + 1.0]
        # assign by rank among free voices ordered by their last pitch
        free.sort(key=lambda i: voices[i][-1].p)
        for k, n in enumerate(g):
            if k < len(free):
                # pick the free voice whose last pitch is closest
                best = min(free, key=lambda i: abs(voices[i][-1].p - n.p))
                free.remove(best)
                voices[best].append(n)
            else:
                voices.append([n])
    return voices


def _player(ph, sec, style, r, seed, bright):
    t0, f, amp, onset = curves(ph, style, seed)
    n = f.shape[0]
    osc = wt_osc(f, saw_amps, ceiling=8500, phase0=r.uniform())
    lvl = np.clip(amp, 0, 1.2)
    fc = f * (2.0 + 6.5 * bright * lvl ** 0.8) + 300.0
    fc = np.minimum(fc, 8000.0)
    y = nb.svf(osc, fc, 0.6, 0)
    # bow/rosin noise follows the bow pressure (level), more on attacks
    nz = r.standard_normal(n)
    nz = filt(nz, chain(("hp", 1800, 0.7), ("lp", 6500, 0.7)))
    on = np.zeros(n)
    for i in np.nonzero(onset)[0]:
        k = min(n - i, ns(0.06))
        on[i:i + k] += np.exp(-np.arange(k) / ns(0.015))
    noise = nz * (sec["noise"] * lvl ** 1.5 + 0.025 * on * lvl)
    return t0, amp * y + noise


def strings(track: Track, notes, section="violins", gain=1.0, seed=0, players=None, style_over=None,
            body=True, pan_center=None):
    """Render notes (seconds; may be chords) for a string section into track."""
    sec = SECTIONS[section]
    P = players or sec["players"]
    stem = track.like()
    voices = split_voices(notes)
    for vi, voice in enumerate(voices):
        for pl in range(P):
            r = rng("str", section, seed, vi, pl)
            style = LineStyle(attack=sec["attack"], release=sec["release"], glide=0.05 if P > 1 else 0.09,
                              gap=0.07, vib_rate=sec["vib"][0] * r.uniform(0.92, 1.08),
                              vib_depth=sec["vib"][1] * r.uniform(0.75, 1.25), vib_delay=r.uniform(0.18, 0.4),
                              vib_ramp=0.5, drift=2.5, intonation=4.0 if P > 1 else 2.5, dip=0.12 if P == 1 else 0.06,
                              swell=0.12, detune=r.normal(0, sec["detune"]) if P > 1 else 0.0,
                              vel_curve=1.3)
            if style_over:
                for k, v in style_over.items():
                    setattr(style, k, v)
            jitter = (lambda: r.normal(0, 0.018)) if P > 1 else (lambda: 0.0)
            pv = [replace(n, t=n.t + jitter(), v=float(np.clip(n.v * r.uniform(0.9, 1.05), 0.02, 1)), x=dict(n.x))
                  for n in voice]
            for ph in phrases(pv, style.gap):
                t0, y = _player(ph, sec, style, r, seed * 100 + vi * 10 + pl, sec["bright"])
                lo, hi = sec["pan"]
                pan = pan_center if pan_center is not None else lo + (hi - lo) * (pl + 0.5) / P
                stem.add(t0, y, gain=gain / np.sqrt(P) * 0.5, pan=float(np.clip(pan + r.normal(0, 0.05), -1, 1)))
    if body:
        ir = stereo_body(sec["body"], seed)
        y = np.vstack([convolve(stem.buf[0], ir[0], stem.circular), convolve(stem.buf[1], ir[1], stem.circular)])
        stem.buf = y[:, : stem.n].astype(np.float32)
    stem.buf = filt(stem.buf, chain(*sec["eq"]), stem.circular).astype(np.float32)
    track.mix(stem)
    return track
