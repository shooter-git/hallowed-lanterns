"""Stinger: the Ember is born (~6.5 s, one-shot, D major).

A candle-flame bloom of air, a harp glissando lifting through D major's
pentatonic notes, the Ember's motif on the felt piano with a glass voice an
octave above it, a low pizzicato D, and a short, soft string swell on D
major add 9 under the soft organ, all in the big hall with a shimmer."""
import numpy as np

from hlaudio.core import ns, rng, tvec, smoothstep
from hlaudio.score import N
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import electro as EL, effects as FX, nb
from hlaudio.piece import finish_oneshot
from hlaudio import lead as LD


def render():
    st = Stage(9.0, circular=False)
    r = rng("ember-born")

    fl = st.stem("flame", {"concert": 0.35}, depth=0.6)
    n = ns(0.9)
    t = tvec(n)
    fc = 250 * (8 ** smoothstep(t / 0.5))
    bloom = nb.svf(r.standard_normal(n), fc, 1.4, 1) * smoothstep(t / 0.08) * np.exp(-t / 0.3)
    fl.add(0.0, bloom, gain=0.18)

    gl_notes = [N(0.05 + i * 0.05, 2.2, float(p), 0.42 + 0.02 * i)
                for i, p in enumerate([50, 54, 57, 62, 64, 66, 69, 71, 74, 76, 78, 81])]
    st.play("harp", gl_notes, "harp", seed=1, gain_db=-1)
    u = 0.19                                   # one eighth of the motif
    t0 = 0.72
    mot = [(0, 1, 74), (1, 2, 83), (3, 1, 81), (4, 1, 78), (5, 6, 81)]
    pn = [N(t0 + a * u, b * u + 0.4, float(p), 0.58 + (0.06 if k == 1 else 0.0)) for k, (a, b, p) in enumerate(mot)]
    pn[-1].d = 3.0
    st.play("piano", pn, "piano", seed=2, gain_db=8, layer_bias=-0.1, release=2.0)
    gl = st.stem("glass", {"shimmer:cathedral2": 0.4, "concert": 0.5}, depth=0.6)
    gn = [N(n.t + 0.01, n.d, n.p + 12, 0.45) for n in pn]
    for x in gn:
        x.x["attack"] = 0.03
        x.x["release"] = 2.0
    EL.glass(gl, gn, gain=0.35, seed=3, bright=0.5, pan_spread=0.3, breath=0.05)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4500, 0.7)).astype("float32")

    sw = Curve([(0.4, 0.2), (1.8, 0.62), (3.5, 0.55), (5.5, 0.3)])
    shape = {"attack": 0.9, "swell": 0.2, "taper": 2.5}
    # a short string swell, only a very quiet bed far back, under the organ
    st.play("violins", [N(0.45, 4.6, float(p), 0.55) for p in (74, 78, 81, 88)], "violins", seed=4, dyn=sw,
            gain_db=-23, shape=shape, layer_bias=-0.2, **LD.bed())
    st.play("violas", [N(0.5, 4.5, float(p), 0.5) for p in (62, 69)], "violas", seed=5, dyn=sw, gain_db=-16,
            shape=shape, **LD.bed())
    st.play("cellos", [N(0.5, 4.5, float(p), 0.5) for p in (38, 50)], "cellos", seed=6, dyn=sw, gain_db=-16,
            shape=shape, **LD.bed())
    st.play("cellos_pizz", [N(0.02, 1.5, 38.0, 0.6), N(0.02, 1.5, 50.0, 0.45)], "cellos_pizz", seed=9, gain_db=0)
    st.play("organ", [N(0.3, 5.2, 38.0, 0.45)], "organ_soft_pedal", seed=7, dyn=sw, gain_db=-8)
    st.play("organ", [N(0.6, 4.8, float(p), 0.42) for p in (57, 62, 66)], "organ_soft", seed=8, dyn=sw, gain_db=-11)

    out = st.render({"concert": {"seed": 101}, "cathedral2": {"seed": 102},
                     "shimmer:cathedral2": {"seed": 103, "gens": 2, "fb": 0.42}}, warmth=0.3)
    out = out[:, : ns(7.5)]
    k = ns(2.5)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return finish_oneshot("music", "ember-born", out, -16.0, 192, max_s=6.5, end_fade=2.0,
                          meta={"title": "The Ember", "key": "D major", "stinger": True})


if __name__ == "__main__":
    render()
