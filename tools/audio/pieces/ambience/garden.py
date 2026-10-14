"""Garden ambience (nightfall in the lantern tunnel): rustling reed fences,
soft wind chimes tuned to the garden's G pentatonic, crickets, a warm breeze."""
import numpy as np

from hlaudio.core import rng
from hlaudio import nature as NA, mallets as ML, recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0
CHIME_NOTES = [79, 81, 83, 86, 88, 91, 93]  # G5 A5 B5 D6 E6 G6 A6


def render():
    mix = Mix(LOOP, circular=True)
    reed = mix.track()
    NA.reeds(reed, level=0.05, seed=31, swishes=0.35, knocks=0.06, hiss=0.0)
    mix.add(reed, 1.0, {"forest": 0.2})

    air = mix.track()
    # Recorded wind in the trees and the reed fences.
    RW.wind(air, "0907", 116.0, -39.5, bands=(("hs", 4000, 0.7, -1.5),))
    mix.add(air, 1.0)

    ch = mix.track()
    r = rng("garden-chimes")
    t = 1.0
    while t < LOOP:
        # little clusters when the breeze catches the chimes
        k = int(r.integers(1, 5))
        for i in range(k):
            p = float(r.choice(CHIME_NOTES))
            ch.add(t + i * r.uniform(0.12, 0.45), ML.wind_chime(p, r.uniform(0.25, 0.6), seed=int(t * 10) + i),
                   gain=0.10, pan=float(r.uniform(-0.5, 0.5)))
        t += r.uniform(4.0, 9.0)
    from hlaudio.effects import eq
    ch.buf = eq(ch.buf, ("hs", 5000, 0.7, -5), ("lp", 7500, 0.7), circular=True).astype("float32")
    mix.add(ch, 1.0, {"hall": 0.35})

    crick = mix.track()
    NA.crickets(crick, 0, LOOP, count=6, level=0.035, distance=(0.3, 1.0), seed=33)
    NA.tree_crickets(crick, 0, LOOP, count=1, level=0.008, seed=34)
    mix.add(crick, 1.0, {"forest": 0.35})

    out = mix.render({"forest": {"seed": 31}, "hall": {"seed": 32}})
    # the level: its bed 8 dB under the chapter's music as heard in the game (the music's group at 0.6,
    # the ambience's at 0.5), its crickets and wind never more than 2 dB over the music's own highs
    return finish_loop("ambience", "garden", out, LOOP, 3, -24.7, 128, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
