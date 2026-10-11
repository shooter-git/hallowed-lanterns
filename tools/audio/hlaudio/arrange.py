"""Arranging helpers used by the piece scripts."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .score import N, voicing, chord_pcs


def ranks(notes, groups):
    """Split chord notes (same start) by pitch rank: groups = [[0,1],[2,3]] ->
    list of note lists (lowest note is rank 0)."""
    by_t = {}
    for n in notes:
        by_t.setdefault(round(n.t, 4), []).append(n)
    out = [[] for _ in groups]
    for t, g in by_t.items():
        g = sorted(g, key=lambda n: n.p)
        for gi, idxs in enumerate(groups):
            for i in idxs:
                if i < len(g):
                    out[gi].append(g[i])
    return out


def vel_ramp(notes, t0, t1, v0, v1):
    """Scale velocities by a linear ramp between beats t0..t1 (multiplier)."""
    out = []
    for n in notes:
        if t0 <= n.t <= t1:
            u = (n.t - t0) / max(t1 - t0, 1e-9)
            out.append(replace(n, v=float(np.clip(n.v * (v0 + (v1 - v0) * u), 0.02, 1)), x=dict(n.x)))
        else:
            out.append(n)
    return out


def set_vel(notes, v):
    return [replace(n, v=v, x=dict(n.x)) for n in notes]


def window(notes, t0, t1):
    return [n for n in notes if t0 <= n.t < t1]


def legato(notes, overlap=0.0, max_gap=1.01):
    """Extend each note to the next note's start (+overlap) for smooth lines,
    unless the gap to the next note is longer than max_gap (a real rest)."""
    s = sorted(notes, key=lambda n: n.t)
    out = []
    for i, n in enumerate(s):
        if i + 1 < len(s) and s[i + 1].t - (n.t + n.d) <= max_gap:
            out.append(replace(n, d=max(n.d, s[i + 1].t - n.t + overlap), x=dict(n.x)))
        else:
            out.append(n)
    return out


def tag(notes, **x):
    out = []
    for n in notes:
        nx = dict(n.x)
        nx.update(x)
        out.append(replace(n, x=nx))
    return out


def counter_thirds(melody, pr, below=True, scale_pcs=None):
    """A simple harmony line: for each melody note pick the nearest chord tone
    a third-ish (3..5 semitones) below (or above)."""
    out = []
    for n in melody:
        sym = None
        for (t0, d, s) in pr:
            if t0 <= n.t < t0 + d:
                sym = s
                break
        if sym is None:
            continue
        pcs, bass, root = chord_pcs(sym)
        cands = []
        for k in range(3, 10):
            p = n.p - k if below else n.p + k
            if int(p) % 12 in pcs:
                cands.append((abs(k - 4), p))
        if cands:
            p = sorted(cands)[0][1]
            out.append(replace(n, p=float(p), x=dict(n.x)))
    return out


def stretch(notes, k, t0=0.0):
    """Scale times and durations by k around t0 (augmentation)."""
    return [replace(n, t=t0 + (n.t - t0) * k, d=n.d * k, x=dict(n.x)) for n in notes]


def shape(notes, dyn, bar_len):
    """Per-section velocity multipliers: dyn = [(bar0, bar1, mult), ...]."""
    out = []
    for n in notes:
        b = n.t / bar_len
        k = 1.0
        for (b0, b1, mult) in dyn:
            if b0 <= b < b1:
                k = mult
                break
        out.append(replace(n, v=float(np.clip(n.v * k, 0.02, 1.0)), x=dict(n.x)))
    return out


def comp(pr, offsets, period, low, high, n=3, dur=0.5, vel=0.5, accent=None):
    """Rhythmic chord stabs: voiced chord tones at `offsets` within every
    `period` beats of each chord (e.g. off-beat pizzicato chords)."""
    from .score import N, voicing
    out = []
    prev = None
    for (t0, d, s) in pr:
        v = voicing(s, low, high, n, prev)
        prev = v
        k = 0.0
        while k < d - 1e-6:
            for i, off in enumerate(offsets):
                if k + off >= d - 1e-6:
                    continue
                vv = vel * (accent[i % len(accent)] if accent else 1.0)
                for p in v:
                    out.append(N(t0 + k + off, dur, float(p), vv))
            k += period
    return out
