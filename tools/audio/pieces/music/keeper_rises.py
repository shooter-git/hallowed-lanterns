"""Stinger: the Keeper of the Deep rises (~17 s, one-shot).

From the deep's F# minor: a low drone and a slow heartbeat, glass gliding
upwards like light through water, strings and choir swelling through D major
and E to a wide A major, where the horns and sopranos sing the motif (A F# E
C# E) under a shimmer, then everything settles and glows."""
import numpy as np

from hlaudio.core import ns, rng, tvec, smoothstep
from hlaudio.score import N, seq, shift
from hlaudio.theme import motif
from hlaudio.arrange import legato
from hlaudio import mallets as ML, bowed as BW, voice as VO, wind as WI, perc as PC, effects as FX
from hlaudio.piece import Mix, finish_oneshot

CH = [(0.0, 4.5, (42, 49, 54, 57, 61)),      # F#m (add9 later)
      (4.5, 2.6, (38, 50, 54, 57, 62)),      # D
      (7.1, 2.3, (40, 52, 56, 59, 64)),      # E
      (9.4, 5.6, (33, 45, 52, 57, 61, 64))]  # A


def render():
    mix = Mix(17.0, circular=False)

    st = mix.track()
    for i, (t, d, ps) in enumerate(CH):
        v = [0.18, 0.4, 0.6, 0.8][i]
        low = [N(t, d + 0.3, float(p), v, {"attack": 1.5 if i == 0 else 0.4, "release": 2.5}) for p in ps if p < 48]
        mid = [N(t, d + 0.3, float(p), v, {"attack": 1.8 if i == 0 else 0.4, "release": 2.5}) for p in ps if 48 <= p < 60]
        hi = [N(t, d + 0.3, float(p + 12), v * 0.9, {"attack": 2.0 if i == 0 else 0.5, "release": 2.5})
              for p in ps if p >= 57]
        BW.strings(st, low, "basses", gain=0.3, seed=10 + i)
        BW.strings(st, mid, "cellos", gain=0.28, seed=20 + i)
        BW.strings(st, hi, "violins", gain=0.3, seed=30 + i)
    mix.add(st, 1.0, {"underwater": 0.4, "hall": 0.3}, name="strings")

    ch = mix.track()
    for i, (t, d, ps) in enumerate(CH):
        v = [0.15, 0.38, 0.58, 0.8][i]
        notes = [N(t + 0.2, d + 0.3, float(p), v, {"attack": 2.0 if i == 0 else 0.5, "release": 3.0})
                 for p in ps if 45 <= p <= 64]
        VO.choir(ch, [n for n in notes if n.p < 55], "tenor", singers=8, vowel=("u", "a"), morph=0.2 + 0.2 * i,
                 gain=0.45, seed=40 + i)
        VO.choir(ch, [n for n in notes if n.p >= 55], "alto", singers=8, vowel=("u", "a"), morph=0.2 + 0.2 * i,
                 gain=0.45, seed=50 + i)
    sop = motif(9.0, "A4", 0.42, vel=0.8)
    for k, n in enumerate(sop):
        n.d = (sop[k + 1].t - n.t + 0.05) if k + 1 < len(sop) else 3.6
    VO.choir(ch, sop, "soprano", singers=10, vowel=("o", "a"), morph=0.7, gain=0.6, seed=60,
             style_over={"glide": 0.15, "release": 3.0})
    mix.add(ch, 1.0, {"underwater": 0.3, "shimmer:cathedral": 0.3, "hall": 0.3}, name="choir")

    hn = mix.track()
    WI.horn(hn, shift(sop, dp=-12, vmul=0.85), gain=0.9, pan=0.25, seed=70, players=3)
    mix.add(hn, 1.0, {"hall": 0.5}, name="horns")

    gl = mix.track()
    # light rising through the water: a glass line gliding up two octaves
    VO.glass_pad(gl, legato([N(1.0 + i * 1.1, 1.2, float(p), 0.45) for i, p in enumerate([54, 61, 66, 69, 73, 78, 81])],
                            0.3), gain=0.35, seed=80, glide=0.7, attack=1.0, release=3.0)
    for i, t in enumerate([0.3, 2.3, 4.3, 6.0, 7.4]):
        gl.add(t, PC.heartbeat(46.0, 0.3 + 0.12 * i, seed=i), gain=0.5)
    ML.render(gl, [N(11.6 + 0.08 * k, 3.0, float(p), 0.45) for k, p in enumerate([81, 85, 88, 93])], ML.celesta,
              gain=0.35, pan_by_pitch=0.4, center_pitch=86)
    mix.add(gl, 1.0, {"underwater": 0.5, "shimmer:cathedral": 0.2}, name="glass+drum")

    out = mix.render({"underwater": {"seed": 111}, "hall": {"seed": 112},
                      "shimmer:cathedral": {"seed": 113, "gens": 2, "fb": 0.45}})
    out = FX.eq(out, ("lp", 6500, 0.6))
    out = out[:, : ns(16.0)]
    k = ns(3.0)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return finish_oneshot("music", "keeper-rises", out, -16.0, 128,
                          meta={"title": "The Keeper Rises", "key": "F# minor -> A major", "stinger": True})


if __name__ == "__main__":
    render()
