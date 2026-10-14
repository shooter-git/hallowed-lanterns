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
    chord, and the oboe sighing down a step above them (the sixth falling to the fifth; in a
    minor key the fourth to the third), three glockenspiel notes falling away, and the pulse
    answering twice, falling, in the pizzicato as it fades.

The way into the last chapter, the Marigold Garden, is its own: passage-final, a farewell. No
cymbal and no drum: bubbles rise and a breath of air comes as you surface from the Deep; horns
and the soft organ swell on C major over a soft timpani roll, the harp rising; and on the beat
a bittersweet cadence into the Marigold's E minor, A minor 6 (the minor iv) resolving to E minor,
with the oboe sighing down C, B, G, the marimba rolling, the guitar's slow arpeggio, a far bell,
and two last glockenspiel notes.

Orchestra: VSCO 2 Community Edition (CC0, Versilian Studios), in the same hall as the music; the
far bell is a gong from the Versilian Community Sample Library (CC0)."""
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
from hlaudio import lead as LD
from hlaudio import festival  # noqa: F401  (the gong's seat and tone chain)
from hlaudio import nature as NA
from hlaudio import sfxkit as K

E = 0.325          # one eighth: the bar of eight lasts the fog's 2.6 s
DOWN = 8 * E       # the downbeat, when the next chapter appears
LENGTH = 9.0

# Each key's home note (MIDI, around middle C) and mode: B minor for the Arbor and the Grove, D major for
# the Pasture and Hollow, G major for the Garden, A major for the Snow, and F# minor (Dorian) for the Deep.
# Into the Marigold Garden (E minor), the farewell (final_passage).
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
            seed=7, dyn=rise, gain_db=-13, shape={"attack": 0.6, "swell": 0.1, "taper": 0.12}, **LD.bed())
    st.play("cellos", [N(0.2, DOWN - 0.16, float(rel - 12), 0.55)], "cellos_trem", seed=8, dyn=rise, gain_db=-14,
            shape={"attack": 0.6, "swell": 0.1, "taper": 0.12}, **LD.bed())

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

    # The bloom: soft horns and the organ on the home chord (no section strings), and above them the
    # oboe's sigh, a step down.
    bloom = Curve([(DOWN, 0.36), (DOWN + 0.4, 0.55), (DOWN + 2.5, 0.42), (LENGTH - 1.0, 0.1)])
    st.play("organ", [N(DOWN, 5.4, float(p), 0.48) for p in (low, low + 7, home, home + 2, home + third + 12)],
            "organ_soft", seed=11, dyn=bloom, gain_db=-10)
    st.play("organ_ped", [N(DOWN, 5.6, float(low - 12 if low - 12 >= 29 else low), 0.48)], "organ_soft_pedal",
            seed=12, dyn=bloom, gain_db=-11, seat="organ")
    st.play("horns", [N(DOWN + 0.05, 4.8, float(p), 0.42) for p in (low + 7, low + 12 + third)], "horns", seed=13,
            dyn=bloom, gain_db=-9, shape={"attack": 0.35, "swell": 0.1, "taper": 2.2})
    sigh = (home + 17, home + 15) if minor else (home + 21, home + 19)
    st.play("oboe", [N(DOWN + 0.12, 1.15, float(sigh[0]), 0.5), N(DOWN + 1.27, 3.2, float(sigh[1]), 0.44)],
            "oboe", seed=14, gain_db=1, **LD.lead(st),
            shape={"attack": 0.25, "swell": 0.15, "taper": 1.6})
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


FINAL_LENGTH = 12.0


def final_passage():
    """Into the last chapter: a farewell, arriving in the Marigold Garden's E minor (see the notes at the top)."""
    home, low = 52, 40                       # E3, E2
    st = Stage(FINAL_LENGTH, circular=False)
    t2 = DOWN + 2.2                          # where A minor 6 resolves to E minor

    # Surfacing: bubbles rising and thinning, and a soft breath of air.
    bub = st.stem("bubbles", {st.hall: 0.5}, depth=0.6)
    r = rng("passage-final")
    t = 0.0
    while t < DOWN - 0.3:
        NA.bubble_stream(bub, t, dur=r.uniform(0.5, 1.1), rate=r.uniform(10, 18), f=(500, 1300),
                         level=0.05 * (1 - t / DOWN), seed=int(t * 10) + 7, pan=float(r.uniform(-0.5, 0.5)))
        t += r.uniform(0.3, 0.6)
    st.stem("air", {st.hall: 0.5}, depth=0.5).add(0.0, _air(home), gain=0.035)

    # The rise on C major: horns and the soft organ swelling, a soft timpani roll, the harp.
    rise = Curve([(0.0, 0.1), (1.6, 0.35), (DOWN, 0.6)])
    # (in a smaller room than the cadence, and stopping just short of the beat, so no G is left
    # ringing against the F-sharp of A minor 6)
    st.play("horns_rise", [N(0.1, DOWN - 0.3, float(p), 0.4) for p in (52, 55)], "horns", seed=21, dyn=rise, gain_db=-10,
            shape={"attack": 1.2, "swell": 0.1, "taper": 0.25}, seat="horns", sends={"concert": 0.3}, release=0.2)
    st.play("organ_rise", [N(0.0, DOWN - 0.25, float(p), 0.42) for p in (48, 52, 55, 60)], "organ_soft", seed=22,
            dyn=rise, gain_db=-12, seat="organ", sends={"concert": 0.3}, release=0.2)
    st.play("timpani", [N(0.3, DOWN - 0.6, 40.0, 0.5)], "timpani_roll", seed=23,
            dyn=Curve([(0.3, 0.05), (DOWN - 0.1, 0.4), (DOWN, 0.1)]), gain_db=-12, release=0.6)
    gl = [36 + o + iv for o in (12, 24, 36) for iv in (0, 4, 7)] + [76]
    st.play("harp", [N(DOWN - 0.7 + i * 0.7 / len(gl), DOWN + 0.12 - (DOWN - 0.7 + i * 0.7 / len(gl)), float(p),
                       0.26 + 0.02 * i) for i, p in enumerate(gl)], "harp", seed=24, gain_db=-6, release=0.25)

    # The cadence: A minor 6 on the beat (the minor iv, its F# the Dorian sixth), resolving to E minor.
    bloom = Curve([(DOWN, 0.4), (DOWN + 0.6, 0.55), (t2 + 1.5, 0.5), (FINAL_LENGTH - 1.5, 0.12)])
    st.play("organ", [N(DOWN, t2 - DOWN + 0.1, float(p), 0.45) for p in (45, 52, 54, 60)] +
            [N(t2, FINAL_LENGTH - t2 - 1.2, float(p), 0.45) for p in (40, 47, 52, 55, 59)],
            "organ_soft", seed=25, dyn=bloom, gain_db=-10)
    st.play("organ_ped", [N(DOWN, t2 - DOWN + 0.1, 33.0, 0.45), N(t2, FINAL_LENGTH - t2 - 1.2, 28.0, 0.45)],
            "organ_soft_pedal", seed=26, dyn=bloom, gain_db=-12, seat="organ")
    st.play("horns", [N(DOWN + 0.05, t2 - DOWN, 60.0, 0.4), N(t2, 3.6, 59.0, 0.38), N(DOWN + 0.05, 5.6, 52.0, 0.36)],
            "horns", seed=27, dyn=bloom, gain_db=-10, shape={"attack": 0.4, "swell": 0.1, "taper": 2.4})
    # The oboe's farewell: C, falling to B as the chord turns, then G.
    st.play("oboe", [N(DOWN + 0.2, 2.0, 72.0, 0.5), N(t2, 1.45, 71.0, 0.46), N(t2 + 1.5, 2.9, 67.0, 0.4)],
            "oboe", seed=28, gain_db=1, **LD.lead(st), shape={"attack": 0.3, "swell": 0.12, "taper": 1.8})
    # The marimba, rolling softly on each chord.
    roll, t, k = [], DOWN + 0.1, 0
    while t < t2 + 2.6:
        pair = (64, 72) if t < t2 else (67, 71)
        sw = 0.18 + 0.12 * np.sin(np.pi * min(1.0, (t - DOWN) / 4.6))
        roll.append(N(t, 0.4, float(pair[k % 2]), float(sw)))
        t += 0.085
        k += 1
    st.play("marimba", roll, "marimba", seed=29, gain_db=-8)
    # The guitar's slow arpeggio on E minor (the harp through a guitar body, as the giant guitar's strings).
    arp = [N(t2 + 0.05 + 0.2 * i, 2.6, float(p), 0.42 - 0.02 * i) for i, p in enumerate((40, 47, 52, 55, 59, 64))]
    st.play("guitar", arp, "harp", seed=30, gain_db=-2, seat="harp")
    K.guitar_body(st, "guitar", 0.8, seed=3)
    # A far bell as the chord turns, and two last notes falling away high up.
    st.play("gong", [N(t2, 8.0, 50.0, 0.25)], "gong", seed=31, gain_db=6, tail=10.0, depth=0.95)
    st.play("glock", [N(t2 + 2.4, 1.8, 86.0, 0.22), N(t2 + 3.1, 2.4, 83.0, 0.17)], "glock", seed=32, gain_db=-9,
            sends={"shimmer:cathedral2": 0.3, st.hall: 0.6})
    # Strings, far back, holding the E minor chord under it all.
    st.play("violins", [N(t2, FINAL_LENGTH - t2 - 1.5, float(p), 0.4) for p in (64, 71)], "violins", seed=33,
            dyn=bloom, gain_db=-16, shape={"attack": 0.8, "swell": 0.1, "taper": 2.5}, **LD.bed())

    out = st.render({"concert": {"seed": 41}, "cathedral2": {"seed": 42},
                     "shimmer:cathedral2": {"seed": 43, "gens": 2, "fb": 0.4}}, warmth=0.3)
    out = out[:, : ns(FINAL_LENGTH)]
    k = ns(2.0)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return out


def render():
    for key in KEYS:
        finish_sfx(f"passage-{key}", f"passage-{key}", passage(key), -2.0, stereo=True, kbps=128, max_s=LENGTH)
    finish_sfx("passage-final", "passage-final", final_passage(), -2.0, stereo=True, kbps=128, max_s=FINAL_LENGTH)


if __name__ == "__main__":
    render()
