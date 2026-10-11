"""The Ember's chime: the five-note motif, quick (~1.5 s), on each chapter's
instrument and in each chapter's key, so it always sits inside the music."""
import numpy as np

from hlaudio.core import Track, ns
from hlaudio.score import N, shift
from hlaudio.theme import motif
from hlaudio import mallets as ML, plucked as PL, bowed as BW, voice as VO, effects as FX
from hlaudio.piece import Mix, finish_sfx

E = 0.15  # seconds per eighth: the motif lasts ~1.05 s, then rings


def music_box():
    mix = Mix(4.0, circular=False)
    tr = mix.track()
    ML.render(tr, motif(0.02, "D6", E, vel=0.75), ML.music_box, gain=1.0, pan_by_pitch=0.3, center_pitch=88)
    tr.buf = FX.convolve(tr.buf, np.vstack([ML.box_ir(3)] * 2))[:, : tr.n].astype("float32")
    mix.add(tr, 1.0, {"hall": 0.3})
    return mix.render()


def celesta():
    mix = Mix(4.0, circular=False)
    tr = mix.track()
    m = motif(0.02, "D6", E, vel=0.7)
    m[-1].d = 1.6
    ML.render(tr, m, ML.celesta, gain=1.0, pan_by_pitch=0.3, center_pitch=86)
    mix.add(tr, 1.0, {"forest": 0.35, "hall": 0.2})
    return mix.render()


def zither():
    mix = Mix(4.0, circular=False)
    tr = mix.track()
    m = motif(0.02, "G4", E * 1.05, vel=0.75)
    m[-1].x["vib"] = (22, 5.0, 0.25)      # rou xian on the last note
    PL.render_plucked(tr, m, "zheng", gain=1.0, pan_by_pitch=0.3, center=72)
    mix.add(tr, 1.0, {"forest": 0.3})
    return mix.render()


def cello():
    mix = Mix(4.5, circular=False)
    tr = mix.track()
    m = motif(0.05, "D3", 0.19, vel=0.75)
    for i, n in enumerate(m):
        n.d = (m[i + 1].t - n.t + 0.02) if i + 1 < len(m) else 0.9
    BW.strings(tr, m, "solo_cello", gain=1.0, seed=3)
    mix.add(tr, 1.0, {"hall": 0.35})
    return mix.render()


def glockenspiel():
    mix = Mix(4.0, circular=False)
    tr = mix.track()
    ML.render(tr, motif(0.02, "D6", E, vel=0.65), ML.glockenspiel, gain=1.0, pan_by_pitch=0.3, center_pitch=88)
    mix.add(tr, 1.0, {"room": 0.3, "hall": 0.2})
    return mix.render()


def sleigh():
    mix = Mix(4.0, circular=False)
    tr = mix.track()
    ML.render(tr, motif(0.02, "A5", E * 1.1, vel=0.6), ML.bell, gain=1.0, pan_by_pitch=0.3, center_pitch=84, tone="hand")
    for i, t in enumerate([0.02, 0.35, 0.68, 0.99]):
        tr.add(t, ML.jingle(0.5 if i else 0.7, seed=40 + i, shake=0.08), gain=0.5)
    mix.add(tr, 1.0, {"hall": 0.3})
    return mix.render()


def whale_choir():
    mix = Mix(5.0, circular=False)
    tr = mix.track()
    m = motif(0.05, "A4", 0.2, vel=0.75)
    for i, n in enumerate(m):
        n.d = (m[i + 1].t - n.t + 0.05) if i + 1 < len(m) else 1.2
    VO.choir(tr, m, "soprano", singers=6, vowel=("u", "o"), morph=0.4, gain=1.0, seed=7,
             style_over={"glide": 0.12, "attack": 0.12, "release": 0.8, "vib_delay": 0.15})
    VO.glass_pad(tr, shift(m, dp=-12), gain=0.5, seed=8, glide=0.15, attack=0.15, release=1.0)
    tr.buf = FX.eq(tr.buf, ("lp", 3500, 0.7)).astype("float32")
    mix.add(tr, 1.0, {"underwater": 0.6})
    return mix.render()


def guitar():
    mix = Mix(4.0, circular=False)
    tr = mix.track()
    PL.render_plucked(tr, motif(0.02, "G4", E * 1.1, vel=0.75), "guitar", gain=1.0, pan_by_pitch=0.2, center=67)
    mix.add(tr, 1.0, {"room": 0.25, "hall": 0.2})
    return mix.render()


CHIMES = {
    "arbor": music_box, "grove": celesta, "garden": zither, "pasture": cello,
    "hollow": glockenspiel, "snow": sleigh, "deep": whale_choir, "marigold": guitar,
}


def render():
    for ch, fn in CHIMES.items():
        finish_sfx(f"ember-chime-{ch}", f"ember-chime-{ch}", fn(), -3.0, stereo=True, max_s=1.7)


if __name__ == "__main__":
    render()
