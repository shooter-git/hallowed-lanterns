"""The passage between chapters: passage-d, -b, -g, -a and -fs, one for each key a chapter's music
is in (the way into a chapter is in that chapter's key, so it hands over to its music cleanly).

Bittersweet: glad you're here, sorry the night is passing. The fog closes in for 2.6 s, one bar of
eight eighths grouped 3+3+2, and the next chapter blooms on the downbeat:

  - the bar rises over the key's relative chord - its minor for a major key (an ache under the
    lift), its major for a minor one - a soft heartbeat of low timpani and the concert bass drum
    on the 3+3+2 accents, a rising pizzicato arpeggio, string tremolo from nothing, a suspended
    cymbal's crescendo and a rush of real recorded wind (Joseph Sardin, BigSoundBank, CC0), a
    reversed shimmer drawing in and a harp glissando in the last half-second;
  - on the downbeat it resolves home: one soft, deep hit, then soft horns and the organ on the
    chord, and a solo violin sighing down a step above them (the sixth falling to the fifth; in a
    minor key the fourth to the third), three glockenspiel notes falling away, and the pulse
    answering twice, falling, in the pizzicato as it fades.

Orchestra: VSCO 2 Community Edition (CC0, Versilian Studios), in the same hall as the music."""
from __future__ import annotations

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from hlaudio.core import SR, ns, rng, tvec, smoothstep
from hlaudio.effects import chain, filt, reverb
from hlaudio.orch import Stage
from hlaudio.piece import finish_sfx
from hlaudio.sampler import Curve
from hlaudio.score import N
from hlaudio import nb
from hlaudio.recordings import declick, _read as recording
from hlaudio.sampler import VSCO

E = 0.325          # one eighth: the bar of eight lasts the fog's 2.6 s
DOWN = 8 * E       # the downbeat, when the next chapter appears
LENGTH = 9.0

# Each key's home note (MIDI, around middle C) and mode: D major for the Arbor, Pasture and Hollow,
# B minor for the Grove, G major for the Garden and the Marigold Garden, A major for the Snow, and
# F# minor (Dorian) for the Deep.
KEYS = {"d": (62, "major"), "b": (59, "minor"), "g": (55, "major"), "a": (57, "major"), "fs": (54, "minor")}


def _wav(rel):
    """A VSCO sample by its path, as stereo at SR."""
    rate, d = wavfile.read(VSCO / rel)
    x = d.astype(np.float64)
    if d.dtype.kind == "i":
        x /= float(np.iinfo(d.dtype).max)
    x = np.atleast_2d(x.T) if x.ndim > 1 else np.vstack([x, x])
    if x.shape[0] == 1:
        x = np.vstack([x[0], x[0]])
    return resample_poly(x, SR, rate, axis=1) if rate != SR else x


def _peak_at(x, win=0.05):
    """Where a swelling sample is loudest (s)."""
    e = np.convolve(np.mean(x ** 2, axis=0), np.ones(ns(win)) / ns(win), "same")
    return float(np.argmax(e)) / SR


def _sub(home):
    """The sub under the downbeat: the root between 40 and 62 Hz, its pitch settling as it booms."""
    f = 440 * 2 ** ((home - 69) / 12)
    while f >= 62:
        f /= 2
    n = ns(1.8)
    t = tvec(n)
    fr = f * (1 + 0.25 * np.exp(-t / 0.05))
    y = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.55) * (1 - np.exp(-t / 0.004))
    return y


def _air(seed):
    """Recorded wind swept into a rush: band-passed, the band rising, swelling to the downbeat and
    spilling a little past it, circling from one side to the other."""
    x = declick(recording("0595"))[0]
    r = rng("passage-air", seed)
    start = ns(r.uniform(5, 70))
    n = ns(DOWN + 1.6)
    x = x[start: start + n]
    t = tvec(n)
    u = np.clip(t / DOWN, 0, 1)
    fc = 280 * (9 ** (u ** 1.5))
    swell = smoothstep(u) ** 2.2 * np.where(t < DOWN, 1.0, np.exp(-(t - DOWN) / 0.5))
    out = np.zeros((2, n))
    for ch, seg in enumerate((x, np.roll(x, ns(0.35)))):
        y = nb.svf(seg, fc * (1 + 0.08 * ch), 1.2, 1)
        y = y / (np.std(y[: ns(DOWN)]) + 1e-9)
        side = 0.5 + 0.5 * np.sin(np.pi * (1.4 * u - 0.2) + ch * np.pi)
        out[ch] = y * swell * (0.4 + 0.6 * side)
    return filt(out, chain(("hp", 120, 0.7), ("lp", 6000, 0.7)))


def passage(key):
    home, mode = KEYS[key]
    minor = mode == "minor"
    r = rng("passage", home)
    st = Stage(LENGTH, circular=False)
    low = home - 12
    third = 3 if minor else 4
    # The chord the bar rises over: the relative minor (vi) of a major key, the relative major of a
    # minor one (VI in B minor; III, A major, in the Deep's F# Dorian, whose VI isn't in the mode).
    rel = {"b": home + 8 - 12, "fs": home + 3 - 12}.get(key, home + 9 - 12)
    rel_third = 4 if minor else 3
    acc = (0, 3, 6)  # the 3+3+2 accents

    # A soft heartbeat: timpani and bass drum on the accents, two ghost notes leading in, and a
    # gentle downbeat. (A pulse for one bar only: it marks this moment and goes.)
    timp, bd = [], []
    for k, i in enumerate(acc):
        v = 0.34 + 0.1 * k
        timp.append(N(i * E, 1.2, float(rel - 12), v))
        bd.append(N(i * E, 1.4, 0.0, v - 0.14))
    for g, t in ((0.24, 7 * E), (0.32, 7.5 * E)):
        timp.append(N(t, 0.6, float(rel - 12), g))
    timp.append(N(DOWN, 2.5, float(low), 0.74))
    bd.append(N(DOWN, 3.0, 0.0, 0.6))
    st.play("timpani", timp, "timpani", seed=1, gain_db=-2)
    st.play("drums", bd, "bass_drum", seed=2, gain_db=-6, seat="bass_drum")
    sub = st.stem("sub", {}, depth=0.1)
    sub.add(DOWN, _sub(home), gain=0.24)

    # The arpeggio: the relative chord climbing through the bar, voices added as it goes.
    arp = [0, 7, 12 + rel_third, 7, 12, 14, 12 + rel_third, 19]
    pz = [N(i * E, 0.6, float(rel - 12 + arp[i]), 0.32 + 0.04 * i + (0.1 if i in acc else 0)) for i in range(8)]
    st.play("cellos_pizz", pz + [N(DOWN, 1.4, float(low - 12 if low - 12 >= 36 else low), 0.66)],
            "cellos_pizz", seed=3)
    st.play("violas_pizz", [N(n.t, n.d, n.p + 12, n.v * 0.85) for n in pz[3:]] + [N(DOWN, 1.2, float(low + 7), 0.5)],
            "violas_pizz", seed=4, gain_db=-3)
    st.play("violins_pizz", [N(n.t, n.d, n.p + 24, n.v * 0.8) for n in pz[5:]], "violins_pizz", seed=5, gain_db=-4)
    # ... and answered twice, falling, as the bloom fades: the pulse's afterglow.
    st.play("cellos_pizz", [N(DOWN + 3 * E, 1.0, float(low + 7), 0.4), N(DOWN + 6 * E, 1.4, float(low), 0.3)],
            "cellos_pizz", seed=6)

    # The swell: tremolo strings from nothing to the downbeat, on the relative chord.
    rise = Curve([(0.15, 0.08), (1.4, 0.3), (2.45, 0.7), (2.62, 0.72)])
    st.play("violins", [N(0.15, DOWN - 0.12, float(p), 0.55) for p in (rel + 12, rel + 12 + rel_third)], "violins_trem",
            seed=7, dyn=rise, gain_db=-6, shape={"attack": 0.6, "swell": 0.1, "taper": 0.12})
    st.play("cellos", [N(0.2, DOWN - 0.16, float(rel - 12), 0.55)], "cellos_trem", seed=8, dyn=rise, gain_db=-7,
            shape={"attack": 0.6, "swell": 0.1, "taper": 0.12})

    # A suspended cymbal swelling into the downbeat, and the rush of air.
    cym = _wav("Percussion/susCymb1-cresc-Short_v1.wav")
    peak = _peak_at(cym)
    cym = cym[:, : ns(peak + 0.25)]
    k = ns(0.25)
    cym[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    cym = filt(cym, chain(("lp", 8000, 0.7), ("hs", 5000, 0.7, -4.0)))
    st.stem("cymbal", depth=0.7).add(DOWN - peak, cym, gain=0.38)
    st.stem("air", {st.hall: 0.4}, depth=0.4).add(0.0, _air(home), gain=0.05)

    # A reversed shimmer drawing in: the home chord's reverb, backwards, ending on the beat.
    chord = Stage(4.5, circular=False)
    chord.play("glock", [N(0.0, 1.5, float(home + 24 + iv), 0.45) for iv in (0, 7, 14)], "glock", seed=9,
               sends={})
    g = chord.render({}, warmth=0.0, air=None)
    wet = reverb(g, "cathedral2")[:, : ns(3.6)]
    st.stem("reverse", {}, depth=0.3).add(DOWN - wet.shape[1] / SR, wet[:, ::-1], gain=0.45)

    # A harp glissando up through the relative chord, landing home on the beat.
    gl = [rel + o + iv for o in (-12, 0, 12) for iv in (0, rel_third, 7)] + [home + 12]
    st.play("harp", [N(DOWN - 0.44 + i * 0.44 / len(gl), 2.0, float(p), 0.32 + 0.022 * i) for i, p in enumerate(gl)],
            "harp", seed=10, gain_db=-4)

    # The bloom: soft horns and the organ on the home chord (no section strings), and above them a
    # solo violin's sigh, a step down.
    bloom = Curve([(DOWN, 0.36), (DOWN + 0.4, 0.55), (DOWN + 2.5, 0.42), (LENGTH - 1.0, 0.1)])
    st.play("organ", [N(DOWN, 5.4, float(p), 0.48) for p in (low, low + 7, home, home + 2, home + third + 12)],
            "organ_soft", seed=11, dyn=bloom, gain_db=-10)
    st.play("organ_ped", [N(DOWN, 5.6, float(low - 12 if low - 12 >= 29 else low), 0.48)], "organ_soft_pedal",
            seed=12, dyn=bloom, gain_db=-11, seat="organ")
    st.play("horns", [N(DOWN + 0.05, 4.8, float(p), 0.42) for p in (low + 7, low + 12 + third)], "horns", seed=13,
            dyn=bloom, gain_db=-9, shape={"attack": 0.35, "swell": 0.1, "taper": 2.2})
    sigh = (home + 17, home + 15) if minor else (home + 21, home + 19)
    st.play("solo_violin", [N(DOWN + 0.12, 1.15, float(sigh[0]), 0.5), N(DOWN + 1.27, 3.2, float(sigh[1]), 0.44)],
            "solo_violin", seed=14, gain_db=-5, shape={"attack": 0.25, "swell": 0.15, "taper": 1.6})
    # Three glockenspiel notes falling away: fifth, third, root, high up.
    falls = [N(DOWN + 0.45 + 0.42 * i, 1.8, float(home + iv), 0.3 - 0.05 * i) for i, iv in enumerate((31, 24 + third, 24))]
    st.play("glock", falls, "glock", seed=16, gain_db=-7, sends={"shimmer:cathedral2": 0.3, st.hall: 0.6})
    bow = _wav("Percussion/susCymb1-bow-2.wav")
    bow = filt(bow, chain(("hp", 400, 0.7), ("lp", 8000, 0.7)))
    fade = np.minimum(1, np.linspace(0, 6, bow.shape[1]))
    st.stem("bowed", depth=0.85).add(DOWN + 0.05, bow * fade, gain=0.18)

    out = st.render({"concert": {"seed": 31}, "cathedral2": {"seed": 32},
                     "shimmer:cathedral2": {"seed": 33, "gens": 2, "fb": 0.4}}, warmth=0.3)
    out = out[:, : ns(LENGTH)]
    k = ns(1.5)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return out


def render():
    for key in KEYS:
        finish_sfx(f"passage-{key}", f"passage-{key}", passage(key), -2.0, stereo=True, kbps=128, max_s=LENGTH)


if __name__ == "__main__":
    render()
