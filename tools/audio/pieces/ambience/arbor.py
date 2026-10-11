"""Arbor ambience: the last birds of sunset (a fluting thrush, a robin far
off), the first crickets, a breeze through the pergola and a faint, happy
murmur of people far down the lane (formant babble, never words)."""
from hlaudio.core import Track
from hlaudio import nature as NA, effects as FX
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    birds = mix.track()
    NA.birds(birds, 0, LOOP, "thrush", every=(6.5, 11), level=0.10, distance=0.45, seed=1, pan=0.7)
    NA.birds(birds, 3, LOOP, "thrush", every=(9, 15), level=0.07, distance=0.75, seed=2, pan=0.9)
    NA.birds(birds, 5, LOOP, "robin", every=(12, 20), level=0.05, distance=0.7, seed=3, pan=0.9)
    mix.add(birds, 1.0, {"forest": 0.55})

    crick = mix.track()
    NA.crickets(crick, 0, LOOP, count=5, level=0.035, distance=(0.45, 1.0), rate=(1.0, 2.2), seed=4)
    NA.tree_crickets(crick, 0, LOOP, count=1, level=0.010, seed=5)
    mix.add(crick, 1.0, {"forest": 0.4})

    crowd = mix.track()
    NA.murmur(crowd, 0, LOOP, speakers=16, level=0.05, seed=6, laugh=0.2, lp=1100)
    mix.add(crowd, 1.0, {"field": 0.8})

    air = mix.track()
    NA.wind_leaves(air, level=0.022, seed=7, crackle=0.5, low=0.6, gust_rate=0.05)
    mix.add(air, 1.0, {"forest": 0.2})

    out = mix.render({"forest": {"seed": 11}, "field": {"seed": 12}})
    return finish_loop("ambience", "arbor", out, LOOP, 3, -20.0, 96, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
