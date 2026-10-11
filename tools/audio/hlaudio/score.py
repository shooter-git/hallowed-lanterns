"""Notes, a tiny text notation, chords and voice-leading, tempo clocks.

Notation used by `seq` (durations in the piece's beat unit, e.g. eighths):

    "D5:1 | B5:2 A5:1 F#5:1 A5:2 | r:3 (D4 F#4 A4):3"

  * `NOTE:DUR` a note, `r:DUR` a rest, `(A B C):DUR` a chord, `|` is ignored
  * suffix `!` accent, `?` ghost (soft), `~` tie into the next note of the same pitch
  * durations may be fractions (`1/2`) or decimals (`1.5`)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from fractions import Fraction

import numpy as np

from .core import m, name, rng


@dataclass
class N:
    t: float          # start (beats until converted, then seconds)
    d: float          # duration
    p: float          # MIDI pitch (float allowed)
    v: float = 0.7    # velocity 0..1
    x: dict = field(default_factory=dict)  # extras: articulation, bend, ...

    def __repr__(self):
        return f"N({self.t:.2f},{self.d:.2f},{name(self.p)},{self.v:.2f})"


def _dur(s: str) -> float:
    return float(Fraction(s)) if "/" in s else float(s)


def seq(text: str, start: float = 0.0, vel: float = 0.7, transpose: float = 0.0, **extra):
    """Parse the notation above into a list of N (times in beats)."""
    out: list[N] = []
    t = start
    toks = re.findall(r"\([^)]*\):[\d./]+[!?~]*|\S+", text)
    pending_tie = {}
    for tok in toks:
        if tok == "|":
            continue
        acc = 0.0
        tie = False
        while tok and tok[-1] in "!?~":
            if tok[-1] == "!":
                acc += 0.15
            elif tok[-1] == "?":
                acc -= 0.25
            else:
                tie = True
            tok = tok[:-1]
        if ":" not in tok:
            raise ValueError(f"bad token {tok!r}")
        head, ds = tok.rsplit(":", 1)
        d = _dur(ds)
        if head.lower() == "r":
            t += d
            continue
        pitches = head.strip("()").split() if head.startswith("(") else [head]
        for ptxt in pitches:
            p = m(ptxt) + transpose
            if p in pending_tie:
                nn = pending_tie.pop(p)
                nn.d += d
                if tie:
                    pending_tie[p] = nn
                continue
            nn = N(t, d, p, float(np.clip(vel + acc, 0.05, 1.0)), dict(extra))
            out.append(nn)
            if tie:
                pending_tie[p] = nn
        t += d
    return out


def shift(notes, dt=0.0, dp=0.0, dv=0.0, vmul=1.0):
    return [replace(n, t=n.t + dt, p=n.p + dp, v=float(np.clip(n.v * vmul + dv, 0.02, 1)), x=dict(n.x))
            for n in notes]


def end_of(notes):
    return max((n.t + n.d for n in notes), default=0.0)


# ----------------------------------------------------------------- chords

_Q = {
    "": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10],
    "maj7": [0, 4, 7, 11], "M7": [0, 4, 7, 11], "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9],
    "sus2": [0, 2, 7], "sus4": [0, 5, 7], "7sus4": [0, 5, 7, 10], "add9": [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14], "9": [0, 4, 7, 10, 14], "maj9": [0, 4, 7, 11, 14], "m9": [0, 3, 7, 10, 14],
    "dim": [0, 3, 6], "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10], "aug": [0, 4, 8],
    "5": [0, 7], "6add9": [0, 4, 7, 9, 14], "maj7#11": [0, 4, 7, 11, 18], "m11": [0, 3, 7, 10, 17],
}
_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _pc(s):
    v = _PC[s[0].upper()]
    for c in s[1:]:
        v += 1 if c == "#" else -1 if c == "b" else 0
    return v % 12


def chord(sym: str):
    """'G', 'D/F#', 'Em7', 'A7sus4', 'Bbmaj7' -> (root_pc, intervals, bass_pc)."""
    bass = None
    if "/" in sym:
        sym, b = sym.split("/")
        bass = _pc(b)
    mt = re.match(r"^([A-G][#b]?)(.*)$", sym)
    root, q = mt.group(1), mt.group(2)
    if q not in _Q:
        raise ValueError(f"unknown chord quality {q!r} in {sym}")
    r = _pc(root)
    return r, _Q[q], (r if bass is None else bass)


def chord_pcs(sym):
    r, iv, b = chord(sym)
    return sorted({(r + i) % 12 for i in iv}), b, r


def prog(text: str, start: float = 0.0):
    """'G:6 D/F#:6 Em7:3 A7:3' -> [(t, d, sym)] in beats."""
    out = []
    t = start
    for tok in text.split():
        if tok == "|":
            continue
        sym, d = tok.rsplit(":", 1)
        d = _dur(d)
        out.append((t, d, sym))
        t += d
    return out


def chord_at(pr, t):
    for (t0, d, s) in pr:
        if t0 <= t < t0 + d:
            return s
    return pr[-1][2]


def voicing(sym, low, high, n, prev=None, include_bass=False):
    """Pick n chord tones in [low, high] (MIDI), close to prev voicing if given."""
    pcs, bass, root = chord_pcs(sym)
    cands = [p for p in range(int(low), int(high) + 1) if p % 12 in pcs]
    if not cands:
        return []
    best, best_cost = None, 1e9
    r = rng("voicing", sym, low, high, n, tuple(prev or []))
    for _ in range(600):
        pick = sorted(r.choice(cands, size=min(n, len(cands)), replace=False))
        pcset = {p % 12 for p in pick}
        cost = 0.0
        cost += 6.0 * (len(pcs[:n]) - len(pcset & set(pcs))) if n >= len(pcs) else 0
        if root not in pcset:
            cost += 4
        gaps = np.diff(pick)
        cost += 3.0 * np.sum(gaps < 2) + 0.15 * np.sum(np.maximum(gaps - 7, 0))
        if pick and pick[0] < 52 and len(pick) > 1 and gaps[0] < 5:
            cost += 3  # muddy low thirds
        if prev and len(prev) == len(pick):
            cost += 0.35 * np.sum(np.abs(np.array(pick) - np.array(sorted(prev))))
        else:
            cost += 0.05 * abs(np.mean(pick) - (low + high) / 2)
        if cost < best_cost:
            best, best_cost = pick, cost
    return [int(p) for p in best]


def pad(pr, low, high, n, vel=0.5, legato=0.0, **x):
    """Voice-led sustained chords from a progression (list of N per chord tone)."""
    out = []
    prev = None
    for (t, d, s) in pr:
        v = voicing(s, low, high, n, prev)
        prev = v
        for p in v:
            out.append(N(t, d + legato, float(p), vel, dict(x)))
    return out


def bass_line(pr, octave_low=36, vel=0.6, pattern=None, unit=1.0, period=None):
    """Root/bass note per chord in [octave_low, octave_low+11]; pattern = list of
    (offset_beats, dur_beats, 'r'|'5'|'8') repeated every `period` beats
    through each chord."""
    out = []
    for (t, d, s) in pr:
        pcs, bass, root = chord_pcs(s)
        b = octave_low + ((bass - octave_low) % 12)
        if pattern is None:
            out.append(N(t, d, float(b), vel))
            continue
        k = 0.0
        while k < d - 1e-6:
            for (off, dd, kind) in pattern:
                if k + off >= d - 1e-6:
                    break
                if kind == "5":
                    # the chord's own fifth (not a fifth above a slash bass), near the bass
                    p = b + ((root + 7 - b) % 12)
                    if p > octave_low + 14:
                        p -= 12
                else:
                    p = b + (12 if kind == "8" else 0)
                out.append(N(t + k + off, min(dd, d - k - off), float(p), vel))
            k += period if period else max(pt[0] + pt[1] for pt in pattern)
    return out


def arpeggio(pr, low, high, step, pattern, vel=0.55, dur=None, n_tones=4, accent_every=None):
    """Arpeggiate each chord: `pattern` indexes into the voiced chord tones
    (0 = lowest); a step of `step` beats per note."""
    out = []
    prev = None
    for (t, d, s) in pr:
        v = voicing(s, low, high, n_tones, prev)
        prev = v
        k = 0
        tt = t
        while tt < t + d - 1e-6:
            idx = pattern[k % len(pattern)]
            if idx is not None:
                p = v[idx % len(v)] + 12 * (idx // len(v))
                vv = vel
                if accent_every and k % accent_every == 0:
                    vv = min(1.0, vel + 0.12)
                out.append(N(tt, dur if dur else step * 1.8, float(p), vv))
            tt += step
            k += 1
    return out


def humanize(notes, seed, t_jit=0.012, v_jit=0.06, unit_seconds=True):
    r = rng("hum", seed)
    out = []
    for n in notes:
        nn = replace(n, x=dict(n.x))
        nn.t = n.t + r.normal(0, t_jit)
        nn.v = float(np.clip(n.v * (1 + r.normal(0, v_jit)), 0.02, 1.0))
        out.append(nn)
    return out


# ----------------------------------------------------------------- tempo

class Clock:
    """Beat -> seconds. `points` = [(beat, bpm), ...]; bpm is interpolated
    linearly between points (ritardando/accelerando). `unit` is how many beats
    of the notation make one metronome beat (e.g. 3 eighths per dotted quarter)."""

    def __init__(self, bpm=None, points=None, unit=1.0, rubato=None):
        """rubato = (phrase_beats, amount): a gentle breath per phrase, slower at
        phrase starts/ends and a touch faster mid-phrase, with zero net drift
        (phrase boundaries, and so loop lengths, are unchanged)."""
        self.unit = unit
        self.rubato = rubato
        if points is None:
            points = [(0.0, bpm)]
        self.points = sorted(points)
        last = self.points[-1][0]
        self.grid = np.linspace(0, last + 1e4, int((last + 1e4) * 8) + 2) if len(self.points) > 1 else None
        if self.grid is not None:
            bp = np.interp(self.grid, [p[0] for p in self.points], [p[1] for p in self.points])
            spb = 60.0 / bp / unit  # seconds per notation beat
            self.cum = np.concatenate([[0], np.cumsum(0.5 * (spb[1:] + spb[:-1]) * np.diff(self.grid))])

    def s(self, beat):
        if self.grid is None:
            spb = 60.0 / self.points[0][1] / self.unit
            out = beat * spb
            if self.rubato:
                P, a = self.rubato
                out += a * spb * P / (2 * np.pi) * np.sin(2 * np.pi * beat / P)
            return out
        return float(np.interp(beat, self.grid, self.cum))

    def notes(self, notes, legato_scale=1.0):
        out = []
        for n in notes:
            t0 = self.s(n.t)
            t1 = self.s(n.t + n.d)
            out.append(replace(n, t=t0, d=(t1 - t0) * legato_scale, x=dict(n.x)))
        return out


def describe(notes, limit=200):
    """Readable note list (for checking melodies are what we meant)."""
    return " ".join(f"{name(n.p)}@{n.t:g}" for n in sorted(notes, key=lambda n: n.t)[:limit])


_SHARP = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def transpose_sym(sym, semis):
    """Transpose a chord symbol ('D/F#', 'Bm7') by semitones."""
    def tr(root):
        return _SHARP[(_pc(root) + semis) % 12]
    bass = None
    if "/" in sym:
        sym, bass = sym.split("/")
    mt = re.match(r"^([A-G][#b]?)(.*)$", sym)
    out = tr(mt.group(1)) + mt.group(2)
    if bass:
        out += "/" + tr(bass)
    return out


def transpose_prog(pr, semis, stretch=1.0, start=0.0):
    """Transpose (and optionally augment) a progression [(t, d, sym)]."""
    t0 = pr[0][0] if pr else 0.0
    return [(start + (t - t0) * stretch, d * stretch, transpose_sym(s, semis)) for (t, d, s) in pr]
