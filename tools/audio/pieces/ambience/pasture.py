"""Pasture ambience (deep night, open field): only what an open field at night sounds like, and
all of it recorded - a soft breeze (Joseph Sardin's "Wind", a clean wind with nothing rustling in
it, kept low and gentle, easing and swelling slowly) over a country meadow at night (his "Campaign
at Night #4": field crickets and, rarely, a frog). No leaves: there are no trees in a field."""
from hlaudio import recordings as RW
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    # the night meadow: its steadiest minute (crickets, no events), its brightest top eased
    meadow = mix.track()
    RW.wind(meadow, "1880", 223.0, -41.0, bands=(("hs", 7000, 0.7, -3.0),), clicks=None)
    mix.add(meadow, 1.0)
    # the breeze over it: slight, dark (no hiss), breathing slowly (its swells far apart)
    air = mix.track()
    RW.wind(air, "0595", 24.0, -41.0, bands=(("lp", 1800, 0.7), ("hs", 900, 0.7, -3.0)), swap=True, gust=0.03,
            seed=5)
    mix.add(air, 1.0)
    out = mix.render({})
    # the level: its bed 8 dB under the chapter's music as heard in the game (the music's group at 0.6,
    # the ambience's at 0.5), its crickets and wind never more than 2 dB over the music's own highs
    return finish_loop("ambience", "pasture", out, LOOP, 3, -26.3, 128, glue=False, tilt_hs_db=-1.5)


if __name__ == "__main__":
    render()
