"""Marigold ambience: a night garden. Crickets and soft tree-cricket trills,
a gentle breeze in the flowers, and far-off soft bells, as if from a village
festival somewhere over the hill (tuned to G, like the music)."""
from hlaudio.core import rng
from hlaudio.effects import chain, filt
from hlaudio import nature as NA, mallets as ML, recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0
BELLS = [67, 71, 74, 76, 79]  # G4 B4 D5 E5 G5


def render():
    mix = Mix(LOOP, circular=True)
    crick = mix.track()
    NA.crickets(crick, 0, LOOP, count=8, level=0.035, distance=(0.25, 1.0), carrier=(3600, 4500), seed=81)
    NA.tree_crickets(crick, 0, LOOP, count=2, level=0.012, seed=82)
    mix.add(crick, 1.0, {"forest": 0.4})

    # Recorded wind in the hedges. It sits under the details (it was louder than everything else,
    # and levelling the whole ambience pushed it up): the rest stays where it was.
    air = mix.track()
    RW.wind(air, "0907", 90.0, -45.0, bands=(("hs", 4000, 0.7, -2.0),), swap=True)
    mix.add(air, 1.0)

    bells = mix.track()
    r = rng("far-bells")
    t = 3.0
    while t < LOOP:
        k = int(r.integers(2, 5))
        for i in range(k):
            p = float(r.choice(BELLS))
            bells.add(t + i * r.uniform(0.35, 0.7), ML.bell(p, r.uniform(0.4, 0.7), seed=int(t * 13) + i), gain=0.06,
                      pan=float(r.uniform(-0.3, 0.3)))
        t += r.uniform(9.0, 16.0)
    bells.buf = filt(bells.buf, chain(("lp", 2500, 0.7), ("hp", 250, 0.7)), True).astype("float32")
    mix.add(bells, 0.4, {"cathedral": 1.0})

    out = mix.render({"forest": {"seed": 81}, "cathedral": {"seed": 82}})
    return finish_loop("ambience", "marigold", out, LOOP, 3, -21.0, 128, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
