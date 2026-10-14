"""Stinger: the Ember is born (~8 s, one-shot, B minor), in Sundown's own voice.

A candle-flame bloom of air, then the Ember's motif exactly as Sundown's
vibraphone sings it (D, then B A F# A, falling; a beat a note), on the
soft-mallet vibraphone; the bowed vibraphone and glass hold its long notes;
under it all a soft, far string bed on B minor. No beat of its own (it floats
over the music, whose triplets go on underneath), and no other tune.
"""
import numpy as np

from hlaudio.core import ns, rng, tvec, smoothstep
from hlaudio.score import N
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import electro as EL, effects as FX, nb
from hlaudio.piece import finish_oneshot
from hlaudio import lead as LD

BEAT = 1.0                                  # Sundown's beat (dotted quarter = 60)
# the motif as Sundown's vibraphone plays it: (beats from the pickup, beats, MIDI) - D, then B A F# A
MOTIF = [(0, 1, 74), (1, 2, 71), (3, 1, 69), (4, 1, 66), (5, 2, 69)]


def render():
    st = Stage(10.0, circular=False)
    r = rng("ember-born")

    fl = st.stem("flame", {"concert": 0.35}, depth=0.6)
    n = ns(0.9)
    t = tvec(n)
    fc = 250 * (8 ** smoothstep(t / 0.5))
    bloom = nb.svf(r.standard_normal(n), fc, 1.4, 1) * smoothstep(t / 0.08) * np.exp(-t / 0.3)
    fl.add(0.0, bloom, gain=0.18)

    t0 = 0.45
    vib = [N(t0 + a * BEAT, b * BEAT + 2.0, float(p), 0.55 if k == 1 else 0.48) for k, (a, b, p) in enumerate(MOTIF)]
    st.play("vibes", vib, "vibes", seed=2, gain_db=4, release=2.0, depth=0.45,
            sends={"plate": 0.15, "concert": 0.35})
    held = [N(t0 + a * BEAT, b * BEAT + 1.5, float(p), 0.5) for a, b, p in MOTIF if b == 2]
    st.play("bowed", held, "vibes_bowed", seed=3, gain_db=-2, release=2.5, depth=0.7,
            sends={"concert": 0.5, "shimmer:cathedral2": 0.15})
    gl = st.stem("glass", {"shimmer:cathedral2": 0.4, "concert": 0.5}, depth=0.7)
    gn = [N(n.t + 0.01, n.d, n.p + 12, 0.4) for n in held]
    for x in gn:
        x.x["attack"] = 0.4
        x.x["release"] = 2.5
    EL.glass(gl, gn, gain=0.2, seed=4, bright=0.5, pan_spread=0.3, breath=0.05)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4500, 0.7)).astype("float32")

    # a soft string bed far back on B minor 7, only a bed
    sw = Curve([(0.4, 0.15), (2.5, 0.45), (5.5, 0.4), (8.0, 0.2)])
    shape = {"attack": 1.2, "swell": 0.15, "taper": 2.5}
    st.play("violins", [N(0.5, 7.0, float(p), 0.5) for p in (71, 74, 78)], "violins", seed=5, dyn=sw,
            gain_db=-24, shape=shape, layer_bias=-0.2, **LD.bed())
    st.play("cellos", [N(0.6, 6.8, float(p), 0.5) for p in (47, 54)], "cellos", seed=6, dyn=sw, gain_db=-17,
            shape=shape, **LD.bed())

    out = st.render({"concert": {"seed": 101}, "cathedral2": {"seed": 102}, "plate": {},
                     "shimmer:cathedral2": {"seed": 103, "gens": 2, "fb": 0.42}}, warmth=0.3)
    out = out[:, : ns(9.0)]
    k = ns(2.5)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return finish_oneshot("music", "ember-born", out, -16.0, 192, max_s=9.0, end_fade=2.0,
                          meta={"title": "The Ember", "key": "B minor", "stinger": True})


if __name__ == "__main__":
    render()
