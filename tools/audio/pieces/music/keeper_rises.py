"""Stinger: the Keeper of the Deep rises (~14 s, one-shot).

From the deep's F# (Dorian): a low drone of basses and the organ's pedal and
a slow two-beat pulse on the timpani, quickening; a glass voice glides
upwards like light through water; the strings swell through D and E to a
wide A major (Lydian, the deep's light), where the horns sing the Ember's
motif (A F# E C# E) and a solo violin answers with it an octave higher a
beat later, over the full organ; then everything settles and glows. The
section strings stay soft and far back under the organ."""
import numpy as np

from hlaudio.core import ns
from hlaudio.score import N
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_oneshot

CH = [(0.0, 3.3, (42, 49, 54, 57, 61)),      # F#m
      (3.3, 2.3, (38, 50, 54, 57, 62)),      # D
      (5.6, 2.2, (40, 52, 56, 59, 64)),      # E
      (7.8, 7.2, (33, 45, 52, 57, 61, 64))]  # A


def render():
    st = Stage(17.0, circular=False, hall="underwater")
    shape = {"attack": 0.8, "swell": 0.25, "taper": 2.5}
    sw = Curve([(0, 0.18), (3.3, 0.38), (5.6, 0.55), (7.8, 0.82), (11.0, 0.7), (14.5, 0.35)])
    for i, (t, d, ps) in enumerate(CH):
        low = [N(t, d + 0.3, float(p), 0.6) for p in ps if p < 48]
        mid = [N(t, d + 0.3, float(p), 0.6) for p in ps if 48 <= p < 57]
        hi = [N(t, d + 0.3, float(p + 12), 0.6) for p in ps if p >= 57]
        far = dict(shape=shape, depth=0.8)
        st.play("basses", low, "basses", seed=10 + i, dyn=sw, gain_db=-6, **far)
        st.play("cellos", [N(n.t, n.d, n.p + 12, n.v) for n in low] + mid, "cellos", seed=20 + i, dyn=sw,
                gain_db=-8, **far)
        st.play("violas", [N(n.t, n.d, n.p - 12, n.v) for n in hi], "violas", seed=30 + i, dyn=sw, gain_db=-9,
                **far)
        if i >= 1:
            st.play("violins2", hi, "violins", seed=40 + i, dyn=sw, gain_db=-12, seat="violins2",
                    layer_bias=-0.2, **far)
    st.play("organ", [N(0.0, 7.9, 30.0, 0.5), N(7.8, 7.0, 33.0, 0.55)], "organ_soft_pedal", seed=50, dyn=sw,
            gain_db=-4)
    st.play("organ", [N(t, d + 0.3, float(p), 0.5) for t, d, ps in CH[:3] for p in ps if 49 <= p <= 64],
            "organ_soft", seed=53, dyn=sw, gain_db=-11)
    top = Curve([(7.4, 0.2), (8.2, 0.75), (11.5, 0.65), (14.5, 0.3)])
    st.play("organ", [N(7.8, 6.8, float(p), 0.6) for p in (57, 61, 64, 69, 71, 76)], "organ", seed=51, dyn=top,
            gain_db=-13)
    st.play("organ", [N(7.8, 6.8, 21.0 + 12, 0.6)], "organ_pedal", seed=52, dyn=top, gain_db=-9)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08).astype("float32")
    # the motif: horns, then violins an octave higher a beat later
    u = 0.42
    mot = [(0, 1, 57), (1, 2, 66), (3, 1, 64), (4, 1, 61), (5, 7, 64)]
    hn = [N(7.4 + a * u, b * u + 0.08, float(p), 0.75) for a, b, p in mot]
    st.play("horns", hn, "horns", seed=60, gain_db=2, legato=True, lag=0.02,
            shape={"attack": 0.15, "swell": 0.2, "taper": 2.0}, dyn=Curve([(7.3, 0.6), (8.5, 0.8), (12, 0.6)]))
    vn = [N(n.t + 2 * u, n.d, n.p + 12, 0.6) for n in hn]
    st.play("solo_violin", vn, "solo_violin", seed=61, gain_db=2, legato=True, lag=0.03, slide=0.08,
            shape={"attack": 0.2, "swell": 0.2, "taper": 2.0}, dyn=Curve([(8.0, 0.5), (9.5, 0.65), (13, 0.45)]))
    # the pulse: two-beat timpani, quickening and growing, a roll into the A
    hits = [0.3, 1.9, 3.4, 4.7, 5.8, 6.7]
    tn = []
    for i, t in enumerate(hits):
        tn += [N(t, 1.0, 42.0, 0.3 + 0.06 * i), N(t + 0.28, 1.0, 42.0, 0.22 + 0.05 * i)]
    st.play("timpani", tn, "timpani", seed=70, gain_db=-4)
    st.play("timpani", [N(7.0, 1.0, 45.0, 0.6)], "timpani_roll", seed=71,
            dyn=Curve([(7.0, 0.05), (7.8, 0.6), (7.85, 0.15)]), gain_db=-6, release=0.5)
    st.play("timpani", [N(7.8, 2.0, 45.0, 0.8)], "timpani", seed=72, gain_db=-3)
    # light rising through the water
    gl = st.stem("glass", {"underwater": 0.5, "shimmer:cathedral2": 0.3}, depth=0.7)
    rise = [N(0.8 + i * 0.95, 1.1, float(p), 0.45 + 0.03 * i) for i, p in enumerate([54, 61, 66, 69, 73, 78, 81])]
    EL.glass_line(gl, rise, gain=0.55, seed=80, glide=0.7, attack=1.0, release=3.0, bright=0.5)
    EL.glass(gl, [N(8.0, 5.0, float(p), 0.35) for p in (81, 85, 88)], gain=0.25, seed=81, attack=1.5,
             release=4.0, bright=0.4)
    sb = st.stem("sub", {}, depth=0.3)
    EL.sub_swell(sb, 6.6, 4.0, 33.0, gain=0.16, attack=1.2, release=2.0)

    out = st.render({"underwater": {"seed": 111}, "concert": {"seed": 112}, "cathedral2": {"seed": 114},
                     "shimmer:cathedral2": {"seed": 113, "gens": 2, "fb": 0.42}}, warmth=0.3)
    out = FX.eq(out, ("lp", 7000, 0.6))
    out = out[:, : ns(16.0)]
    k = ns(3.0)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return finish_oneshot("music", "keeper-rises", out, -16.0, 192, max_s=14.0, end_fade=3.0,
                          meta={"title": "The Keeper Rises", "key": "F# dorian -> A lydian", "stinger": True})


if __name__ == "__main__":
    render()
