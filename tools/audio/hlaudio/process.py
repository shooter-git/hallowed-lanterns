"""Compositional processes for the rescore (Glass / Zimmer / Martinez ways of
working): the Ember's motif as a CELL in a mode, its transformations
(inversion, retrograde, augmentation, diminution, fragments, displacement),
additive rhythmic processes, cycling arpeggios that change one note at a
time, canons and stretti, hockets and interlocking ostinati, ticking figures.

Everything works in scale degrees of a Mode and returns score.N lists (times
in the piece's beat unit), so pieces can be written as processes.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .core import rng
from .score import N

SCALES = {
    "ionian": [0, 2, 4, 5, 7, 9, 11], "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10], "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
}
# the Ember's motif, D B A F# A = degrees 1-6-5-3-5 (0-based) in a 7-note mode
CELL = [0, 5, 4, 2, 4]
CELL_RHYTHM = [1, 2, 1, 1, 2]  # in eighths


class Mode:
    def __init__(self, root, scale="ionian"):
        self.root = float(root)          # MIDI of degree 0
        self.steps = SCALES[scale]
        self.n = len(self.steps)

    def p(self, d):
        """MIDI pitch of scale degree d (any integer, octaves wrap)."""
        o, k = divmod(int(d), self.n)
        return self.root + 12 * o + self.steps[k]

    def deg(self, midi):
        """Nearest scale degree of a MIDI pitch."""
        best, bd = 0, 1e9
        base = int(np.floor((midi - self.root) / 12.0)) * self.n
        for d in range(base - self.n, base + 2 * self.n):
            dist = abs(self.p(d) - midi)
            if dist < bd:
                best, bd = d, dist
        return best


def cell(form="P", length=5):
    """Degrees of the cell relative to its first note: P (prime), I (inversion),
    R (retrograde), RI (retrograde inversion); `length` < 5 gives a fragment
    (from the start; negative from the end)."""
    c = list(CELL)
    if form in ("I", "RI"):
        c = [-x for x in c]
    if form in ("R", "RI"):
        c = c[::-1]
        c = [x - c[0] for x in c]
    if length >= 0:
        c = c[:length]
    else:
        c = c[length:]
        c = [x - c[0] for x in c]
    return c


def realize(degs, mode: Mode, start_deg, t0, durs, vel=0.6, accents=None, legato=1.0, x=None):
    """Turn relative degrees into notes from `start_deg`; durs is a number or
    a list (cycled)."""
    out = []
    t = t0
    dl = durs if isinstance(durs, (list, tuple)) else [durs]
    for i, d in enumerate(degs):
        dur = dl[i % len(dl)]
        v = vel * (accents[i % len(accents)] if accents else 1.0)
        out.append(N(t, dur * legato, float(mode.p(start_deg + d)), float(np.clip(v, 0.02, 1)), dict(x or {})))
        t += dur
    return out


def additive(seq_degs, groups, mode: Mode, start_deg, t0, step, vel=0.6, accent=1.15, legato=0.95):
    """Philip Glass additive process: for each group size g in `groups`, play
    the first g notes of the sequence; the first note of every group is
    accented. e.g. groups=[2, 2, 3, 3, 4, 4, 5, 5]."""
    out = []
    t = t0
    for g in groups:
        for i in range(g):
            d = seq_degs[i % len(seq_degs)]
            v = vel * (accent if i == 0 else 1.0)
            out.append(N(t, step * legato, float(mode.p(start_deg + d)), float(np.clip(v, 0.02, 1))))
            t += step
    return out, t


def cycling(voicings, pattern, step, t0, reps_per_change, vel=0.55, accents=None, legato=1.0):
    """Glass-style cycling broken chords: a figure (`pattern` indexes the
    current pitch set) repeats; between successive target voicings ONE note
    changes per figure repetition until the next chord is reached.
    `voicings`: list of (target pitch list, number of figure repetitions)."""
    out = []
    cur = list(voicings[0][0])
    t = t0
    for vi, (target, reps) in enumerate(voicings):
        target = list(target)
        for r_ in range(reps):
            # move one voice towards the target per repetition
            if r_ % reps_per_change == 0 and cur != target:
                diffs = [(abs(c - g), k) for k, (c, g) in enumerate(zip(cur, target)) if c != g]
                if diffs:
                    _, k = min(diffs)
                    cur[k] = target[k]
            for i, idx in enumerate(pattern):
                if idx is not None:
                    p = cur[idx % len(cur)] + 12 * (idx // len(cur))
                    v = vel * (accents[i % len(accents)] if accents else 1.0)
                    out.append(N(t, step * legato, float(p), float(np.clip(v, 0.02, 1))))
                t += step
    return out, t


def canon(subject, entries):
    """Copies of `subject` (notes) at (time offset, semitone or degree
    transposition fn, velocity multiplier) entries. Transposition may be a
    number (semitones) or a callable(pitch) -> pitch (e.g. a modal shift)."""
    voices = []
    for (dt, tr, vm) in entries:
        v = []
        for n in subject:
            p = tr(n.p) if callable(tr) else n.p + tr
            v.append(replace(n, t=n.t + dt, p=float(p), v=float(np.clip(n.v * vm, 0.02, 1)), x=dict(n.x)))
        voices.append(v)
    return voices


def modal_shift(mode: Mode, steps):
    """A transposition that moves by scale steps (stays in the mode)."""
    return lambda p: mode.p(mode.deg(p) + steps)


def augment(notes, k, t0=None):
    t0 = notes[0].t if t0 is None else t0
    return [replace(n, t=t0 + (n.t - t0) * k, d=n.d * k, x=dict(n.x)) for n in notes]


def displace(notes, dt):
    return [replace(n, t=n.t + dt, x=dict(n.x)) for n in notes]


def hocket(notes, parts=2):
    """Split a line between parts note by note (interlocking)."""
    out = [[] for _ in range(parts)]
    for i, n in enumerate(sorted(notes, key=lambda n: n.t)):
        out[i % parts].append(n)
    return out


def loop_figure(fig, t0, t1, period, vel_curve=None):
    """Repeat a figure (notes starting at 0) every `period` beats in [t0, t1)."""
    out = []
    t = t0
    while t < t1 - 1e-6:
        for n in fig:
            if t + n.t < t1 - 1e-6:
                v = n.v * (vel_curve(t + n.t) if vel_curve else 1.0)
                out.append(replace(n, t=t + n.t, v=float(np.clip(v, 0.02, 1)), x=dict(n.x)))
        t += period
    return out


def ticking(pitches, t0, t1, step, accents, vel=0.55, vel_curve=None):
    """Zimmer-style ticking ostinato: a pitch cycle in even steps with an
    accent pattern (e.g. [1.2, .7, .7, 1.1, .7, .7, 1.0, .7] for 3+3+2)."""
    out = []
    t = t0
    i = 0
    while t < t1 - 1e-6:
        v = vel * accents[i % len(accents)] * (vel_curve(t) if vel_curve else 1.0)
        out.append(N(t, step * 0.9, float(pitches[i % len(pitches)]), float(np.clip(v, 0.02, 1))))
        t += step
        i += 1
    return out


def thin(notes, keep, seed=0):
    """Subtractive process: keep each note with probability keep(t)."""
    r = rng("thin", seed)
    return [n for n in notes if r.uniform() < keep(n.t)]


def pedal_hold(notes, changes):
    """Sustain-pedal blur: hold every note until the next pedal change."""
    cs = sorted(changes)
    out = []
    for n in notes:
        nxt = next((c for c in cs if c > n.t + 1e-6), None)
        d = max(n.d, (nxt - n.t) if nxt is not None else n.d)
        out.append(replace(n, d=d, x=dict(n.x)))
    return out


def fit(notes, pr, extra=(2,), avoid_bass_m2=True):
    """Keep canon/fugue lines consonant with the harmony without losing their
    shape: chord tones, 9ths and 6ths (11ths and 7ths over minor chords, #11 over
    major sevenths) are allowed; over open fifths and sus chords anything
    goes except a semitone against the bass, root or fifth. Other notes are
    nudged to the nearest allowed pitch. Checked at the note's middle."""
    from .score import chord_pcs, chord_at, chord
    out = []
    for n in notes:
        sym = chord_at(pr, n.t + n.d * 0.5)
        pcs, bass, root = chord_pcs(sym)
        _, iv, _ = chord(sym)
        q = sym.split("/")[0]
        if q.endswith("5") or "sus" in q:
            frame = {bass, root, (root + 7) % 12}
            ok = set(range(12)) - {(f + 1) % 12 for f in frame}
            ok |= set(pcs)
        else:
            ok = set(pcs) | {(root + e) % 12 for e in extra} | {(root + 9) % 12, bass}
            if 3 in iv:
                ok |= {(root + 5) % 12, (root + 10) % 12}
            if 11 in iv:
                ok |= {(root + 6) % 12}
        if avoid_bass_m2:
            ok -= {(bass + 1) % 12}
        p = int(round(n.p))
        if p % 12 in ok:
            out.append(n)
            continue
        best = None
        for d in (-1, 1, -2, 2, -3, 3):
            if (p + d) % 12 in ok:
                best = p + d
                break
        out.append(replace(n, p=float(best if best is not None else p), x=dict(n.x)))
    return out
