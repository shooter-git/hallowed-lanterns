"""Deep ambience: underwater. A slow low rumble, distant whale-like calls
(never too close), and streams of bubbles rising past."""
from hlaudio.core import rng
from hlaudio.effects import chain, filt
from hlaudio import nature as NA, voice as VO
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    bed = mix.track()
    NA.underwater_bed(bed, level=0.12, seed=71)
    mix.add(bed, 1.0, {"underwater": 0.3})

    wh = mix.track()
    r = rng("deep-whales")
    for i, t in enumerate([4.0, 23.0, 41.0]):
        y = VO.whale_call(r.uniform(140, 260), r.uniform(2.5, 4.5), seed=i, rough=0.2, bright=0.8)
        wh.add(t, y, gain=0.05, pan=float(r.uniform(-0.8, 0.8)))
    wh.buf = filt(wh.buf, chain(("lp", 1100, 0.7)), True).astype("float32")
    mix.add(wh, 0.6, {"underwater": 1.0})

    bub = mix.track()
    t = 1.0
    i = 0
    while t < LOOP:
        NA.bubble_stream(bub, t, dur=r.uniform(0.6, 2.2), rate=r.uniform(6, 16), f=(700, 1700), level=0.03,
                         seed=i, pan=float(r.uniform(-0.8, 0.8)))
        t += r.uniform(3.0, 8.0)
        i += 1
    bub.buf = filt(bub.buf, chain(("lp", 2600, 0.7)), True).astype("float32")
    mix.add(bub, 1.0, {"underwater": 0.4})

    out = mix.render({"underwater": {"seed": 71}})
    return finish_loop("ambience", "deep", out, LOOP, 3, -20.0, 128, glue=False, tilt_hs_db=-2.0)


if __name__ == "__main__":
    render()
