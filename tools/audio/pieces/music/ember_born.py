"""Stinger: the Ember is born (~8 s, one-shot, D major).

A candle-flame bloom, a harp glissando lifting, the motif on celesta (doubled
by the music box an octave below), a choir 'aah' blooming on D major and a
last sparkle, all washed in shimmer."""
import numpy as np

from hlaudio.core import ns, rng, tvec, smoothstep
from hlaudio.score import N, shift
from hlaudio.theme import motif
from hlaudio import mallets as ML, plucked as PL, voice as VO, effects as FX, nb
from hlaudio.piece import Mix, finish_oneshot


def render():
    mix = Mix(9.0, circular=False)
    r = rng("ember-born")

    fx = mix.track()
    n = ns(0.9)
    t = tvec(n)
    fc = 250 * (8 ** smoothstep(t / 0.5))
    bloom = nb.svf(r.standard_normal(n), fc, 1.4, 1) * smoothstep(t / 0.08) * np.exp(-t / 0.3)
    fx.add(0.0, bloom, gain=0.25)
    mix.add(fx, 1.0, {"hall": 0.3}, name="flame")

    hp = mix.track()
    gl = [N(0.05 + i * 0.045, 2.0, float(p), 0.45 + 0.02 * i)
          for i, p in enumerate([62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86])]
    PL.render_plucked(hp, gl, "harp", gain=0.7, pan=-0.3, pan_by_pitch=0.4, center=74, seed=1)
    mix.add(hp, 1.0, {"hall": 0.4}, name="harp")

    mel = mix.track()
    m = motif(0.75, "D6", 0.17, vel=0.7)
    m[-1].d = 2.0
    ML.render(mel, m, ML.celesta, gain=0.6, pan=0.15, pan_by_pitch=0.2, center_pitch=88)
    ML.render(mel, shift(motif(0.75, "D5", 0.17, vel=0.6)), ML.music_box, gain=0.35, pan=-0.1)
    ML.render(mel, [N(2.05, 2.0, 98.0, 0.45), N(2.12, 2.0, 105.0, 0.35)], ML.glockenspiel, gain=0.25, pan=0.3)
    mix.add(mel, 1.0, {"hall": 0.35, "shimmer:cathedral": 0.3}, name="motif")

    ch = mix.track()
    chord = [N(0.55, 3.0, float(p), 0.55, {"attack": 0.9, "release": 2.5}) for p in (62, 66, 69, 74)]
    VO.choir(ch, chord, "alto", singers=8, vowel=("o", "a"), morph=0.5, gain=0.5, seed=3,
             style_over={"attack": 0.9, "release": 2.5})
    VO.choir(ch, [N(0.55, 3.0, 50.0, 0.5, {"attack": 1.0, "release": 2.5}), N(0.55, 3.0, 57.0, 0.5)], "tenor",
             singers=6, vowel=("o", "a"), morph=0.4, gain=0.4, seed=4, style_over={"attack": 1.0, "release": 2.5})
    VO.glass_pad(ch, [N(0.9, 2.5, float(p), 0.45) for p in (81, 86, 90)], gain=0.3, seed=5, attack=0.8, release=2.5)
    mix.add(ch, 1.0, {"hall": 0.4, "sky": 0.3}, name="choir")

    out = mix.render({"hall": {"seed": 101}, "sky": {"seed": 102},
                      "shimmer:cathedral": {"seed": 103, "gens": 2, "fb": 0.45}})
    out = out[:, : ns(7.5)]
    k = ns(2.5)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return finish_oneshot("music", "ember-born", out, -16.0, 128,
                          meta={"title": "The Ember", "key": "D major", "stinger": True})


if __name__ == "__main__":
    render()
