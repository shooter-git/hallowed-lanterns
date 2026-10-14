"""Grove ambience (blue hour): wind moving through the leaves overhead,
crickets near and far, the soft breathy hush of the ankle-deep fog, and once
in a while a far-off owl. The wind and the fog's hush are real recordings."""
from hlaudio import nature as NA, recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    # Recorded wind in leaves, a little softened by distance (it's overhead), under the details.
    air = mix.track()
    RW.wind(air, "0907", 0.0, -44.5, bands=(("lp", 6500, 0.7), ("hs", 4000, 0.7, -2.0)))
    mix.add(air, 1.0, {"forest": 0.25})

    # The fog's hush: a soft recorded wind, muffled.
    fog = mix.track()
    RW.wind(fog, "0595", 6.0, -49.0, bands=(("lp", 1800, 0.7),), gust=0.04, seed=22)
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
    # the level: its bed 8 dB under the chapter's music as heard in the game (the music's group at 0.6,
    # the ambience's at 0.5), its crickets and wind never more than 2 dB over the music's own highs
    return finish_loop("ambience", "grove", out, LOOP, 3, -26.6, 128, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
