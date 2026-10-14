"""The Ember's chime: the five-note motif, quick (~1.5 s), in each chapter's
key, so it always sits inside the music. Magical and soft: real samples
(VSCO 2 CE harp, felt piano, marimba, glockenspiel, bell tree) with a faint
glass halo, fairly dry (the game adds its world reverb). Nothing reedy.

  arbor     vibraphone + glass, B minor      grove     three gentle variations, D in B minor:
  garden    harp + glass halo, G               1 harp, 2 harp an octave up (harmonic-like),
  pasture   felt piano low + harp above, D     3 felt piano with a soft bell-tree shimmer
  hollow    marimba + glass halo, D          snow      harp + a soft glockenspiel, A
  deep      harp under water + glass, A      marigold  the big guitar (harp + guitar body) with a
                                                       quiet felt-piano unison, G
"""
import numpy as np

from hlaudio.score import N
from hlaudio.theme import motif
from hlaudio import sfxkit as K, electro as EL, effects as FX
from hlaudio.piece import finish_sfx

E = 0.15  # seconds per eighth: the motif lasts ~1.05 s, then rings


def _halo(st, m, up=12, gain=0.18, send=0.15):
    """A faint glass shimmer doubling the motif an octave up."""
    gl = st.stem("glass", {st.hall: send}, depth=K.DEPTH)
    notes = [N(n.t + 0.01, max(n.d, 0.3), n.p + up, 0.4) for n in m]
    for x in notes:
        x.x["attack"] = 0.04
        x.x["release"] = 1.2
    EL.glass(gl, notes, gain=gain, seed=11, bright=0.35, pan_spread=0.25, breath=0.03)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4000, 0.7)).astype(np.float32)


def _m(root, unit=E, vel=0.6, last=1.6, minor=False):
    m = motif(0.02, root, unit, vel=vel, minor=minor)
    m[-1].d = last
    return m


def arbor():
    # the motif as Sundown's vibraphone sings it (D, then B A F# A, falling), quicker: the Ember's signature
    st = K.stage(3.5)
    u = 0.25
    # D and B a touch firmer, as in Sundown, so both stay in the vibraphone's brighter recording (it changes at a
    # velocity of 0.5)
    m = [N(0.02 + a * u, d * u + 0.6, float(p), (0.53, 0.57)[k] if k < 2 else 0.48)
         for k, (a, d, p) in enumerate([(0, 1, 74), (1, 2, 71), (3, 1, 69), (4, 1, 66), (5, 2, 69)])]
    m[-1].d = 2.0
    K.play(st, "vibes", m, "vibes", release=1.5, pan=0.0, width=0.5)
    _halo(st, m)
    return K.finish(st)


def grove_1():
    st = K.stage(3.5)
    m = _m("D5", vel=0.55, last=1.8)
    K.play(st, "harp", m, "harp", pan=0.0, width=0.5)
    _halo(st, m, gain=0.14)
    return K.finish(st)


def grove_2():
    """Harp an octave up, very soft and dark, like harmonics."""
    st = K.stage(3.5)
    m = _m("D6", E * 1.1, vel=0.42, last=1.8)
    K.play(st, "harp", m, "harp", pan=0.05, width=0.5)
    h = st.stems["harp"]
    h.buf = FX.eq(h.buf.astype(np.float64), ("hs", 2500, 0.7, -4.0), ("lp", 4500, 0.7)).astype(np.float32)
    _halo(st, m, up=0, gain=0.12)
    return K.finish(st)


def grove_3():
    """Felt piano with a soft, dark bell-tree shimmer before it."""
    st = K.stage(3.5)
    m = motif(0.18, "D5", E, vel=0.52)
    m[-1].d = 1.6
    K.play(st, "piano", m, "piano", layer_bias=-0.2, release=1.0, pan=0.0, width=0.5)
    K.play(st, "belltree", [N(0.0, 1.5, 0, 0.3)], "belltree", pan=-0.2, width=0.6, send=0.15, gain_db=-12)
    b = st.stems["belltree"]
    b.buf = FX.eq(b.buf.astype(np.float64), ("hs", 3000, 0.7, -6.0), ("lp", 5000, 0.7)).astype(np.float32)
    return K.finish(st)


def garden():
    st = K.stage(3.5)
    m = _m("G4", E * 1.05, vel=0.62, last=1.8)
    K.play(st, "harp", m, "harp", pan=0.0, width=0.5)
    _halo(st, m)
    return K.finish(st)


def pasture():
    st = K.stage(3.5)
    m = _m("D4", E * 1.1, vel=0.58, last=1.8)
    K.play(st, "piano", m, "piano", layer_bias=-0.15, release=1.2, pan=0.0, width=0.5)
    K.play(st, "harp", [N(n.t + 0.004, n.d, n.p + 12, 0.42) for n in m], "harp", pan=0.1, width=0.4, gain_db=-5)
    return K.finish(st)


def hollow():
    st = K.stage(3.0)
    m = _m("D5", vel=0.62, last=1.2)
    K.play(st, "marimba", m, "marimba", pan=0.0, width=0.5)
    _halo(st, m, gain=0.14)
    return K.finish(st)


def snow():
    st = K.stage(3.5)
    m = _m("A4", E * 1.1, vel=0.6, last=1.8)
    K.play(st, "harp", m, "harp", pan=0.0, width=0.5)
    K.play(st, "glock", [N(n.t + 0.005, n.d, n.p + 12, 0.3) for n in m], "glock", pan=0.0, width=0.4, send=0.15)
    return K.finish(st)


def deep():
    st = K.stage(3.5, hall="underwater")
    m = _m("A4", E * 1.15, vel=0.58, last=1.8)
    K.play(st, "harp", m, "harp", pan=0.0, width=0.5, send=0.16)
    h = st.stems["harp"]
    h.buf = FX.eq(h.buf.astype(np.float64), ("lp", 3200, 0.7)).astype(np.float32)
    _halo(st, m, gain=0.16, send=0.2)
    return K.finish(st)


def marigold():
    st = K.stage(3.5)
    m = _m("G4", E * 1.1, vel=0.66, last=1.8)
    K.play(st, "guitar", m, "harp", pan=0.0, width=0.5)
    K.guitar_body(st, "guitar", 0.8, seed=3)
    # a quiet felt-piano unison rounds the plucked string's hollow (odd-heavy) tone
    K.play(st, "piano", [N(n.t + 0.003, n.d, n.p, 0.5) for n in m], "piano", layer_bias=-0.2, pan=0.0,
           width=0.4, gain_db=-1)
    return K.finish(st)


CHIMES = {
    "ember-chime-arbor": arbor, "ember-chime-grove": grove_1, "ember-chime-grove-2": grove_2,
    "ember-chime-grove-3": grove_3, "ember-chime-garden": garden, "ember-chime-pasture": pasture,
    "ember-chime-hollow": hollow, "ember-chime-snow": snow, "ember-chime-deep": deep,
    "ember-chime-marigold": marigold,
}


def render():
    for name, fn in CHIMES.items():
        group = name if not name.startswith("ember-chime-grove") else "ember-chime-grove"
        finish_sfx(group, name, fn(), -3.0, stereo=True, max_s=2.4)


if __name__ == "__main__":
    render()
