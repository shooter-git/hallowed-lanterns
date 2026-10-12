"""Hollow ambience: an old oak at night, creaking slowly; its leaves; crickets;
and now and then a faint twinkle, as if the candy were humming to itself."""
from hlaudio.core import rng
from hlaudio import nature as NA, mallets as ML, recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0
TWINKLE = [86, 88, 90, 93, 95, 98]  # D6 E6 F#6 A6 B6 D7 (D pentatonic, like the pumpkins)


def render():
    mix = Mix(LOOP, circular=True)
    oak = mix.track()
    r = rng("oak")
    for i, t in enumerate([6.0, 27.5, 44.0]):
        oak.add(t, NA.creak(seed=i, dur=r.uniform(0.8, 1.6)), gain=0.06, pan=float(r.uniform(-0.4, 0.4)))
    # Recorded wind in the oak's leaves, under the creaks.
    RW.wind(oak, "0907", 40.0, -46.0, bands=(("lp", 7000, 0.7),), swap=True)
    mix.add(oak, 1.0, {"forest": 0.3})

    crick = mix.track()
    NA.crickets(crick, 0, LOOP, count=6, level=0.035, distance=(0.3, 1.0), seed=52)
    NA.tree_crickets(crick, 0, LOOP, count=1, level=0.008, seed=53)
    mix.add(crick, 1.0, {"forest": 0.4})

    tw = mix.track()
    t = 2.0
    while t < LOOP:
        p = float(r.choice(TWINKLE))
        tw.add(t, ML.bell(p, r.uniform(0.2, 0.45), seed=int(t * 7), tone="tiny"), gain=0.05,
               pan=float(r.uniform(-0.7, 0.7)))
        t += r.uniform(2.5, 7.0)
    mix.add(tw, 1.0, {"hall": 0.6})

    out = mix.render({"forest": {"seed": 51}, "hall": {"seed": 52}})
    return finish_loop("ambience", "hollow", out, LOOP, 3, -24.6, 128, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
