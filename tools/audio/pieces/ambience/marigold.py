"""Marigold ambience: a night garden. Crickets and soft tree-cricket trills and
a gentle breeze in the flowers - nothing tuned, so nothing sings against the
music (the far village bells it once had rang their own little tunes over it)."""
from hlaudio import nature as NA, recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


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

    out = mix.render({"forest": {"seed": 81}})
    # the level: its bed 8 dB under the chapter's music as heard in the game (the music's group at 0.6,
    # the ambience's at 0.5), its crickets and wind never more than 2 dB over the music's own highs
    return finish_loop("ambience", "marigold", out, LOOP, 3, -22.9, 128, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
