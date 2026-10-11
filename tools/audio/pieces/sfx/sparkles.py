"""Small magic: xylo-1..8 (the pumpkin xylophone, D pentatonic, contains the
motif), sprinkle-burst, snowflake-1..5, bubble-1..4, wish-hang, fog-swirl-1..2
and ui-tap."""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec, Track, smoothstep
from hlaudio.effects import chain, filt, reverb, eq, shimmer
from hlaudio.score import N
from hlaudio import mallets as ML, voice as VO, nature as NA, bowed as BW, nb, theme as TH
from hlaudio.core import m
from hlaudio.piece import finish_sfx


def _verb(y, space, amt, keep):
    y = np.atleast_2d(np.asarray(y, dtype=float))
    if y.shape[0] == 1:
        y = np.vstack([y[0], y[0]])
    wet = reverb(y, space)
    n = ns(keep)
    y = np.pad(y, ((0, 0), (0, max(0, wet.shape[1] - y.shape[1]))))
    return (y[:, : wet.shape[1]] + amt * wet)[:, :n]


def xylo(p):
    return _verb(ML.pumpkin_xylo(p, 0.75, seed=int(p)), "room", 0.15, 1.6)


def sprinkle_burst():
    r = rng("sprinkle")
    tr = Track(3.0)
    pent = [86, 88, 90, 93, 95, 98, 100, 102]  # D6..F#7
    t = 0.0
    k = 0
    while t < 1.3:
        p = float(r.choice(pent))
        tr.add(t, ML.glockenspiel(p, r.uniform(0.3, 0.7), seed=k), gain=0.25 * (1 - t / 1.6),
               pan=float(r.uniform(-0.9, 0.9)))
        t += r.exponential(0.02 + 0.06 * t)
        k += 1
    # the 'pop' of the burst
    n = ns(0.25)
    tt = tvec(n)
    pop = nb.svf(r.standard_normal(n), 600 + 2400 * smoothstep(tt / 0.15), 2.0, 1) * np.exp(-tt / 0.06)
    pop = filt(pop, chain(("lp", 3500, 0.7)))
    tr.add(0, pop, gain=0.35)
    y = tr.buf.astype(float)
    wet = shimmer(y, "hall", gens=1, fb=0.35)
    y = np.pad(y, ((0, 0), (0, wet.shape[1] - y.shape[1]))) + 0.3 * wet
    return eq(y, ("hs", 6000, 0.7, -3))[:, : ns(3.2)]


def snowflake(p, i):
    y = ML.bell(p, 0.55, seed=i, tone="tiny")
    hi = ML.bell(p + 12, 0.3, seed=i + 10, tone="tiny")
    k = min(y.size, hi.size)
    y[:k] += 0.15 * hi[:k]
    return _verb(y, "hall", 0.3, 2.2)


def bubble(i):
    r = rng("bub", i)
    tr = Track(0.6)
    k = [1, 2, 3, 2][i]
    for j in range(k):
        tr.add(j * r.uniform(0.05, 0.12), NA.bubble(r.uniform(800, 1700), seed=i * 10 + j, decay=r.uniform(0.012, 0.03),
                                                    rise=r.uniform(0.15, 0.4)), gain=r.uniform(0.6, 1.0))
    y = eq(tr.buf.astype(float), ("lp", 4000, 0.7))
    return _verb(y, "room", 0.12, 0.6)


def wish_hang():
    """A sparkle running up, then a warm G major chord (glass, strings, choir)."""
    tr = Track(4.5)
    for k, p in enumerate([79, 83, 86, 91, 95, 98]):  # G5 B5 D6 G6 B6 D7
        tr.add(0.03 * k + 0.02, ML.celesta(p, 0.45 + 0.05 * k, dur=1.5, seed=k), gain=0.32, pan=-0.5 + 0.2 * k)
    chord = [N(0.25, 2.0, float(p), 0.55, {"attack": 0.35, "release": 1.4}) for p in (55, 62, 67, 71, 74)]
    VO.glass_pad(tr, chord, gain=0.5, seed=3, attack=0.35, release=1.6, glide=0.1)
    BW.strings(tr, [N(0.2, 2.0, float(p), 0.5, {"attack": 0.4, "release": 1.3}) for p in (55, 59, 62, 67)], "violas",
               gain=0.35, seed=4)
    y = tr.buf.astype(float)
    wet = shimmer(y, "hall", gens=1, fb=0.35)
    y = np.pad(y, ((0, 0), (0, wet.shape[1] - y.shape[1]))) + 0.3 * wet
    return eq(y, ("hs", 6000, 0.7, -3))[:, : ns(4.8)]


def fog_swirl(i):
    """Chapter-change whoosh: soft noise that swirls across the stereo field,
    a faint glass glissando inside it, and a shimmer tail."""
    r = rng("fog", i)
    dur = 2.0
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    env = np.sin(np.pi * u) ** 1.6
    fc = 300 + 1500 * np.sin(np.pi * u) ** 2 * (1.0 if i == 0 else 0.8)
    out = np.zeros((2, n))
    for ch in range(2):
        x = nb.svf(rng("fog", i, ch).standard_normal(n), fc * (1 + 0.1 * ch), 1.6, 1)
        x = filt(x, chain(("lp", 3000, 0.7), ("lp", 3800, 0.7)))
        pan = 0.5 + 0.5 * np.sin(2 * np.pi * (0.6 if i == 0 else -0.6) * u + ch * np.pi)
        out[ch] = x * env * (0.35 + 0.65 * pan)
    # glass glissando up (i=0) or down (i=1)
    p0, p1 = (74.0, 93.0) if i == 0 else (93.0, 74.0)
    f = 440 * 2 ** ((p0 + (p1 - p0) * smoothstep(u) - 69) / 12)
    gl = np.sin(2 * np.pi * np.cumsum(f) / SR) * env * 0.08
    out += np.vstack([gl, gl])
    wet = shimmer(out, "cathedral", gens=1, fb=0.3)
    y = np.pad(out, ((0, 0), (0, wet.shape[1] - n))) + 0.35 * wet
    return eq(y, ("hp", 80, 0.7), ("hs", 5000, 0.7, -4))[:, : ns(4.0)]


def ui_tap():
    n = ns(0.12)
    t = tvec(n)
    y = np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.012) * 0.5
    y += np.sin(2 * np.pi * 2900 * t) * np.exp(-t / 0.006) * 0.15
    y += np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.02) * 0.4
    y *= 1 - np.exp(-t / 0.0004)
    return y


def render():
    for i, nm in enumerate(TH.XYLO_NOTES):
        finish_sfx("xylo", f"xylo-{i + 1}", xylo(m(nm)), -3.0, max_s=1.0)
    finish_sfx("sprinkle-burst", "sprinkle-burst", sprinkle_burst(), -3.0, stereo=True, max_s=1.7)
    for i, p in enumerate([93, 97, 100, 102, 105]):  # A6 C#7 E7 F#7 A7 (snow's A major)
        finish_sfx("snowflake", f"snowflake-{i + 1}", snowflake(p, i), -5.0, max_s=1.4)
    for i in range(4):
        finish_sfx("bubble", f"bubble-{i + 1}", bubble(i), -5.0)
    finish_sfx("wish-hang", "wish-hang", wish_hang(), -3.0, stereo=True, max_s=2.1)
    for i in range(2):
        finish_sfx("fog-swirl", f"fog-swirl-{i + 1}", fog_swirl(i), -4.0, stereo=True, max_s=1.9)
    finish_sfx("ui-tap", "ui-tap", ui_tap(), -9.0)


if __name__ == "__main__":
    render()
