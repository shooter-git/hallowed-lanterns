"""Grove ambience (blue hour): wind moving through the leaves overhead,
crickets near and far, the soft breathy hush of the ankle-deep fog, and once
in a while a far-off owl."""
from hlaudio import nature as NA
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    air = mix.track()
    NA.wind_leaves(air, level=0.05, seed=21, crackle=1.0, low=0.5, gust_rate=0.06)
    mix.add(air, 1.0, {"forest": 0.25})

    fog = mix.track()
    NA.fog_hush(fog, level=0.012, seed=22, cutoff=1800, rate=0.04)
    mix.add(fog, 1.0)

    crick = mix.track()
    NA.crickets(crick, 0, LOOP, count=7, level=0.04, distance=(0.2, 1.0), rate=(1.2, 2.6), seed=23)
    NA.tree_crickets(crick, 0, LOOP, count=2, level=0.010, seed=24)
    mix.add(crick, 1.0, {"forest": 0.45})

    owl = mix.track()
    NA.owl(owl, 21.0, level=0.05, seed=25, pan=-0.6)
    NA.owl(owl, 47.5, level=0.035, seed=26, pan=0.7)
    mix.add(owl, 1.0, {"forest": 0.9})

    out = mix.render({"forest": {"seed": 21}})
    return finish_loop("ambience", "grove", out, LOOP, 3, -20.0, 96, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
