"""The Ember's motif and the full "Hallowed Lanterns" theme.

THE MOTIF (the Ember's chime), in D major:

    D5 (pickup) | B5 -- A5  F#5  A5 --
    scale degrees 1 - 6 - 5 - 3 - 5
    rhythm in eighths: 1 | 2 1 1 2   ("ti | TAA ti ti TAA")
    intervals from the first note: 0, +9, +7, +4, +7 semitones

A rising major sixth (the flame leaps out), a sigh down a step, a dip to the
third and a lift back to the fifth: it ends open, like "this way!". All five
notes are in the D major pentatonic scale, so it can be played on the eight
pumpkin-xylophone pitches D5 E5 F#5 A5 B5 D6 E6 F#6 (pumpkins 1, 5, 4, 3, 4).

THE THEME (6/8, D major; durations in eighths, one bar = 6) is built from the
motif: A states it, answers it with a sequence a step lower, restates it and
climbs to the high D; B (relative minor, a borrowed G minor colour) rises in
motif-shaped steps and turns back to the pickup.
"""
from __future__ import annotations

from .score import seq, prog, shift

KEY = "D major"
MOTIF_NOTES = ["D5", "B5", "A5", "F#5", "A5"]
MOTIF_EIGHTHS = [1, 2, 1, 1, 2]
MOTIF_INTERVALS = [0, 9, 7, 4, 7]
MOTIF_DEGREES = [1, 6, 5, 3, 5]
XYLO_NOTES = ["D5", "E5", "F#5", "A5", "B5", "D6", "E6", "F#6"]

# --- melody, D major, eighth-note units; bar 0 is the pickup bar (5 eighths rest)
THEME_A = (
    "r:5 D5:1 | "
    "B5:2 A5:1 F#5:1 A5:2 | A5:5 C#5:1 | A5:2 G5:1 E5:1 G5:2 | G5:3 F#5:2 D5:1 | "
    "B5:2 A5:1 F#5:1 A5:2 | D6:4 C#6:1 B5:1 | A5:2 F#5:1 E5:1 F#5:2 | D5:6"
)
CHORDS_A = ("D:6 | G:3 D/F#:3 | Bm7:3 A:3 | Em7:3 A7sus4:3 | A7:3 D:3 | "
            "G:3 D/F#:3 | Bm:3 Gmaj7:3 | D/A:3 A7:3 | D:6")

THEME_B = (
    "F#5:2 G5:1 A5:3 | B5:2 A5:1 F#5:3 | E5:2 F#5:1 G5:3 | A5:2 G5:1 E5:3 | "
    "F#5:2 G5:1 A5:2 D6:1 | D6:2 C#6:1 Bb5:2 A5:1 | A5:2 G5:1 F#5:2 E5:1 | E5:5 D5:1"
)
CHORDS_B = ("Bm:3 Bm/A:3 | Gmaj7:3 D/F#:3 | Em7:3 C:3 | A7sus4:3 A7:3 | "
            "Bm:3 F#m:3 | G:3 Gm6:3 | D/A:3 Em7:3 | A7sus4:3 A7:3")

# A-section ending that closes instead of leading on (for the finale)
THEME_A_END = "B5:2 A5:1 F#5:1 A5:2 | D6:4 C#6:1 B5:1 | A5:2 F#5:1 E5:1 F#5:2 | E5:3 D5:3"


def motif(start=0.0, root="D5", unit=1.0, vel=0.7, transpose=0.0, minor=False, rhythm=None):
    """The five notes starting at `start` (beats); `unit` scales the eighth
    durations (e.g. 0.5 for a quick chime in quarter-note beats)."""
    from .core import m
    from .score import N
    r0 = m(root) + transpose
    iv = [0, 8, 7, 3, 7] if minor else MOTIF_INTERVALS
    durs = rhythm or MOTIF_EIGHTHS
    out = []
    t = start
    for i, (d, k) in enumerate(zip(durs, iv)):
        v = vel + (0.08 if i == 1 else 0.0) - (0.06 if i == 3 else 0.0)
        out.append(N(t, d * unit, r0 + k, v))
        t += d * unit
    return out


def theme_a(start=0.0, transpose=0.0, vel=0.7):
    return seq(THEME_A, start, vel, transpose)


def theme_b(start=0.0, transpose=0.0, vel=0.7):
    return seq(THEME_B, start, vel, transpose)


def chords_a(start=0.0):
    return prog(CHORDS_A, start)


def chords_b(start=0.0):
    return prog(CHORDS_B, start)


def manifest_entry():
    return {
        "key": KEY,
        "notes": MOTIF_NOTES,
        "degrees": MOTIF_DEGREES,
        "rhythm": "6/8: eighth pickup | quarter, eighth, eighth, quarter (held)",
        "durationsEighths": MOTIF_EIGHTHS,
        "intervalsSemitones": MOTIF_INTERVALS,
        "xyloNotes": XYLO_NOTES,
        "xylo": [XYLO_NOTES.index(n) for n in MOTIF_NOTES],
    }
