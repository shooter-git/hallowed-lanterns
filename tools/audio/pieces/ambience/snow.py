"""Snow ambience: the muffled hush of falling snow, a faint wind, almost
silence; once, a little snow slides off a branch."""
import numpy as np

from hlaudio.core import rng, ns, tvec
from hlaudio.effects import chain, filt
from hlaudio import nature as NA, mallets as ML, recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    # The hush of the snow and its faint wind: a soft recorded wind, muffled as snow muffles
    # everything, swelling and easing slowly.
    wind = mix.track()
    RW.wind(wind, "0595", 20.0, -38.5, bands=(("lp", 1200, 0.7),), gust=0.035, seed=62)
    mix.add(wind, 1.0, {"hall": 0.2})

    ev = mix.track()
    r = rng("snowfall")
    n = ns(1.4)
    t = tvec(n)
    slide = filt(r.standard_normal(n), chain(("lp", 900, 0.7), ("hp", 120, 0.7))) * np.sin(np.pi * t / 1.4) ** 2
    ev.add(38.0, slide, gain=0.03, pan=0.4)
    for tt, p in [(12.0, 98), (51.0, 93)]:
        ev.add(tt, ML.bell(p, 0.25, seed=int(tt), tone="tiny"), gain=0.02, pan=float(r.uniform(-0.6, 0.6)))
    mix.add(ev, 1.0, {"hall": 0.6})

    out = mix.render({"hall": {"seed": 61}})
    return finish_loop("ambience", "snow", out, LOOP, 3, -27.7, 128, glue=False, tilt_hs_db=-2.0)


if __name__ == "__main__":
    render()
