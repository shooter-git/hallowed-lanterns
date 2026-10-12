"""Pasture ambience (deep night, open field): a wide carpet of crickets, the
vast quiet of the night air, a faint low hum (D and A, beating slowly, like the
field itself breathing) and a far owl."""
import numpy as np

from hlaudio.core import tvec, ns, SR
from hlaudio import nature as NA
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    crick = mix.track()
    NA.crickets(crick, 0, LOOP, count=14, level=0.03, distance=(0.35, 1.0), rate=(1.3, 3.0), seed=41, pan=1.0)
    NA.tree_crickets(crick, 0, LOOP, count=3, level=0.009, seed=42, pan=1.0)
    mix.add(crick, 1.0, {"field": 0.6})

    # The wind sits under the details now (it was louder than everything else, and levelling
    # the whole ambience pushed it up): the rest stays where it was, the wind comes down.
    air = mix.track()
    NA.wind_whoosh(air, level=0.0087, seed=43, cutoff=900, rate=0.04)
    mix.add(air, 1.0)

    hum = mix.track()
    n = hum.n
    t = tvec(n)
    # whole cycles per loop so it wraps cleanly
    f1, f2 = round(73.42 * LOOP) / LOOP, round(110.0 * LOOP) / LOOP
    beat = round(0.11 * LOOP) / LOOP
    h = 0.6 * np.sin(2 * np.pi * f1 * t) + 0.35 * np.sin(2 * np.pi * f2 * t) + 0.25 * np.sin(2 * np.pi * (f2 + beat) * t)
    h *= 0.75 + 0.25 * np.sin(2 * np.pi * (round(0.05 * LOOP) / LOOP) * t)
    hum.add(0, np.vstack([h, np.roll(h, ns(0.013))]), gain=0.012)
    mix.add(hum, 1.0, {"field": 0.3})

    owl = mix.track()
    NA.owl(owl, 33.0, level=0.03, seed=44, pan=0.5)
    mix.add(owl, 1.0, {"field": 1.0})

    out = mix.render({"field": {"seed": 41}})
    return finish_loop("ambience", "pasture", out, LOOP, 3, -22.4, 96, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
