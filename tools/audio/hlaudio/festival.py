"""The Lantern Garden's festival colour: the VCSL instruments (CC0, see
sampler.py) on the stage, and the guzheng's idioms written as note
decorations.

Importing this module seats the new instruments (orch.SEAT) and gives each
its tone chain (orch.TONE), the way the orchestra's own are set up:

  * the dan tranh (a Vietnamese zither, close cousin of the guzheng) sits
    near and a little right, like a soloist; its pluck is the character, so
    only a light transient softener, warm low mids, the 2-6 kHz edge tamed;
  * the ocarina (standing in for the xun, the clay flute) a little behind,
    its breath rolled off on top;
  * the temple gong, finger cymbals and woodblock far back in the hall,
    where they colour rather than knock.

Guzheng idioms, as functions that decorate notes (they set x["bend"] and
x["vib"], which the sampler turns into a pitch curve):

  * slide_in  - the press from the string below up into the note (hua yin),
  * vibrato   - the left hand's pressed vibrato on a long note (rou xian),
  * press     - pluck, press up a step and let it fall back (an yin),
  * gliss_up / gliss_down - the sweep over all the strings, placed so the
    top of the sweep lands on the beat.
"""
from __future__ import annotations

from dataclasses import replace

from . import orch
from .score import N

orch.SEAT.update({
    "zither": dict(pan=0.2, width=0.5, depth=0.5),
    "zither_low": dict(pan=0.28, width=0.45, depth=0.56),
    "ocarina": dict(pan=-0.16, width=0.35, depth=0.64),
    "gong": dict(pan=0.06, width=0.9, depth=0.9),
    "finger_cymbal": dict(pan=0.34, width=0.4, depth=0.84),
    "woodblock": dict(pan=-0.32, width=0.3, depth=0.8),
})

orch.TONE.update({
    # the dan tranh's steel strings are bright: the pluck's click above 4 kHz is
    # softened and rolled off, so it sings like silk strings in the hall
    "zither": dict(soften=0.5, eq=[("peak", 230, 0.8, 1.5), ("peak", 2900, 0.9, -3.0), ("peak", 5000, 1.2, -5.0),
                                   ("hs", 4000, 0.7, -6.0), ("lp", 7500, 0.7)]),
    "zither_trem": dict(soften=0.4, eq=[("peak", 230, 0.8, 1.2), ("peak", 2900, 0.9, -3.0), ("peak", 5000, 1.2, -5.0),
                                        ("hs", 4000, 0.7, -6.0), ("lp", 7500, 0.7)]),
    "zither_gliss_up": dict(soften=0.45, eq=[("peak", 230, 0.8, 1.0), ("peak", 2900, 0.9, -3.0),
                                             ("peak", 5000, 1.2, -5.0),
                                             ("hs", 4000, 0.7, -6.0), ("lp", 7500, 0.7)]),
    "zither_gliss_down": dict(soften=0.45, eq=[("peak", 230, 0.8, 1.0), ("peak", 2900, 0.9, -3.0),
                                               ("peak", 5000, 1.2, -5.0),
                                               ("hs", 4000, 0.7, -6.0), ("lp", 7500, 0.7)]),
    "ocarina": dict(soften=0.3, eq=[("peak", 300, 0.8, 1.0), ("peak", 2600, 0.9, -2.0), ("hs", 5000, 0.7, -6.0),
                                    ("lp", 7000, 0.7)]),
    "ocarina_vib": dict(soften=0.3, eq=[("peak", 300, 0.8, 1.0), ("peak", 2600, 0.9, -2.0), ("hs", 5000, 0.7, -6.0),
                                        ("lp", 7000, 0.7)]),
    "gong": dict(soften=0.35, eq=[("peak", 120, 0.8, 1.0), ("peak", 2500, 0.9, -2.0), ("hs", 5000, 0.7, -5.0)]),
    "finger_cymbal": dict(soften=0.6, eq=[("hs", 4000, 0.7, -5.0), ("lp", 6000, 0.7), ("lp", 7000, 0.7)]),
    "woodblock": dict(soften=0.55, eq=[("peak", 2600, 0.9, -3.0), ("hs", 5000, 0.7, -6.0), ("lp", 7000, 0.7)]),
})

# the up-glissando (Gliss_Up_Med_mf) reaches its top string 1.35 s into the
# sample; played a major third down (B pentatonic -> G pentatonic) it is
# slower by 2^(4/12)
GLISS_UP_ARRIVAL = 1.35
GLISS_TOP = 71.0          # the sample's own top (B), see sampler.INSTRUMENTS


def slide_in(n: N, frm=-2.0, wait=0.03, glide=0.2):
    """The note is reached by pressing the string below up into it."""
    x = dict(n.x)
    x["bend"] = [(0.0, frm), (wait, frm), (wait + glide, 0.0)]
    return replace(n, x=x)


def vibrato(n: N, depth=0.22, rate=5.2, delay=0.35, rise=0.5, up=0.75):
    """Pressed vibrato on a long note (mostly above the pitch, as the finger
    presses the string behind the bridge)."""
    x = dict(n.x)
    x["vib"] = dict(depth=depth, rate=rate, delay=delay, rise=rise, up=up)
    return replace(n, x=x)


def press(n: N, at=0.35, semis=2.0, up=0.18, hold=0.25, down=0.25):
    """Pluck, then press the string up `semis` and let it fall back."""
    x = dict(n.x)
    x["bend"] = [(0.0, 0.0), (at, 0.0), (at + up, semis), (at + up + hold, semis), (at + up + hold + down, 0.0)]
    return replace(n, x=x)


def gliss_up(t_arrive_s, key=67.0, v=0.5, dur=4.0):
    """An upward sweep (seconds) whose top string lands on t_arrive_s; `key`
    is the pentatonic tonic the strings are tuned to (67 = G)."""
    ratio = 2 ** ((key - GLISS_TOP) / 12)
    return N(t_arrive_s - GLISS_UP_ARRIVAL / ratio, dur, float(key), v)


def gliss_down(t_start_s, key=67.0, v=0.45, dur=3.5):
    """A downward sweep from the top string at t_start_s."""
    return N(t_start_s, dur, float(key), v)
