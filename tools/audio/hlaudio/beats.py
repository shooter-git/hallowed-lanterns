"""Beats for the swells: a low, syncopated percussion pulse that is born
with a swell, grows with it and leaves with it - never a drum loop that runs
all the time (Zimmer's Interstellar / Inception builds, Dunkirk's ticking,
Glass's additive process applied to a groove).

A groove is a figure of hits over one period (a bar or two), each hit with
a weight (how strong it is in the figure) and a gate (how far the swell must
have grown before it plays). The swell is a curve over the piece, 0..1:
while it is low only the strongest hits sound, softly; as it grows the
syncopations and then the ghost notes join in (additively), louder; as it
falls they drop out again in reverse. So the pattern enters and leaves
gracefully, and its length is the swell's.

    figure = [(offset, part, pitch, weight, gate), ...]   offsets in beats;
                                     pitch may be a function of time (follow the bass)
    groove(t0, t1, period, figure, swell) -> {part: [N, ...]}

The parts are routed by the piece (timpani, the concert bass drum, a
woodblock); `seat` adds the bass drum's place on the stage.
"""
from __future__ import annotations

import numpy as np

from . import orch
from .core import smoothstep
from .score import N

orch.SEAT.setdefault("bass_drum", dict(pan=-0.08, width=0.8, depth=0.84))


def drum_pitch(pr, low=38, high=50, fifth=False):
    """A timpani pitch that follows a progression [(t, d, sym)]: the bass (or
    its fifth) placed within the drums' range low..high."""
    from .score import chord_at, chord_pcs

    def f(t):
        pcs, bass, root = chord_pcs(chord_at(pr, t))
        pc = bass
        if fifth:   # the fifth over the bass (a pedal's fifth) if the chord has it, else the root's
            pc = (bass + 7) % 12 if (bass + 7) % 12 in pcs else (root + 7) % 12
        p = low + ((pc - low) % 12)
        return float(p if p <= high else p - 12)
    return f


def groove(t0, t1, period, figure, swell, vel=(0.22, 0.9), fade_in=0.18, dur=2.0):
    """Hits of `figure` repeated every `period` beats in [t0, t1). A hit sounds
    when swell(t) >= its gate; its velocity is weight * (lo + (hi - lo) * swell)
    and it fades in over the first `fade_in` of swell above its gate, so a
    newly admitted ghost note arrives at a whisper."""
    out: dict = {}
    lo, hi = vel
    t = t0
    while t < t1 - 1e-9:
        for (off, part, pitch, w, gate) in figure:
            tt = t + off
            if not (t0 <= tt < t1):
                continue
            s = float(swell(tt))
            if s < gate or s <= 0:
                continue
            v = w * (lo + (hi - lo) * s) * (0.45 + 0.55 * smoothstep((s - gate) / max(fade_in, 1e-6)))
            pp = pitch(tt) if callable(pitch) else pitch
            out.setdefault(part, []).append(N(tt, dur, float(pp), float(np.clip(v, 0.03, 1.0))))
        t += period
    return out

