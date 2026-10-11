"""Creatures: giant-low-1..2 (a deep gentle low that blooms into a cello note),
gummy-squeak-1..3, puffer-puff, octopus-wave (watery whoosh + chime) and
butterflies (fluttering, stereo)."""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec, Track, smoothstep
from hlaudio.effects import chain, filt, reverb, eq
from hlaudio.score import N
from hlaudio.lines import wt_osc
from hlaudio import mallets as ML, bowed as BW, voice as VO, nature as NA, nb
from hlaudio.piece import finish_sfx


def giant_low(i):
    """A longhorn's low: a soft nasal 'mmm-ooo' hum (formant voice) that rises
    a little into a cello note, which takes over and rings on."""
    r = rng("giant", i)
    target = [45.0, 50.0][i]  # A2, D3
    dur = 3.6
    n = ns(dur)
    t = tvec(n)
    f_start = 440 * 2 ** ((target - 3.2 - 69) / 12)
    f_end = 440 * 2 ** ((target - 69) / 12)
    f = f_start + (f_end - f_start) * smoothstep(t / 1.1)
    f *= 1 + 0.004 * np.sin(2 * np.pi * 4.6 * t) * smoothstep((t - 0.4) / 0.5)
    src = wt_osc(f, lambda k: 1.0 / k ** 1.5, ceiling=3500)
    src += 0.03 * r.standard_normal(n)
    # 'mmm' (nasal: low F1, closed) morphing to 'ooo'
    m_v = nb.svf(src, np.full(n, 260.0), 3.0, 1) + 0.3 * nb.svf(src, np.full(n, 1100.0), 6.0, 1)
    o_v = nb.svf(src, np.full(n, 330.0), 4.0, 1) + 0.25 * nb.svf(src, np.full(n, 700.0), 5.0, 1)
    u = smoothstep((t - 0.15) / 0.5)
    voice = (1 - u) * m_v + u * o_v
    env = smoothstep(t / 0.35) * np.exp(-np.maximum(t - 1.0, 0) / 0.45)
    voice *= env
    tr = Track(dur + 1.0)
    tr.add(0.0, voice, gain=0.7)
    BW.strings(tr, [N(0.75, 2.2, target, 0.62, {"release": 1.1, "attack": 0.45})], "solo_cello", gain=0.9, seed=30 + i)
    y = tr.buf.astype(float)
    y = eq(y, ("hp", 45, 0.7), ("lp", 3500, 0.7))
    wet = reverb(y, "field")[:, : y.shape[1] + ns(1.5)]
    y = np.pad(y, ((0, 0), (0, wet.shape[1] - y.shape[1]))) + 0.35 * wet
    return y


def gummy_squeak(i):
    """A rubbery, wobbly squeak with a little jelly 'boing'."""
    r = rng("gummy", i)
    dur = [0.32, 0.4, 0.28][i]
    n = ns(dur + 0.25)
    t = tvec(n)
    f0 = [1050, 820, 1300][i]
    contour = 1 + 0.35 * np.sin(np.pi * np.clip(t / dur, 0, 1)) * [1, -0.6, 0.8][i]
    wob = 1 + 0.06 * np.sin(2 * np.pi * r.uniform(28, 40) * t)
    f = f0 * contour * wob
    y = wt_osc(f, lambda k: 1.0 / k ** 1.3 if k < 6 else 0.0, ceiling=6000)
    y = nb.svf(y, np.full(n, 2200.0), 1.5, 0)
    env = smoothstep(t / 0.02) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.03))
    env *= 1 + 0.4 * np.sin(2 * np.pi * 11 * t)
    y *= env
    # jelly boing: a low wobbling body tone
    boing = np.sin(2 * np.pi * 180 * t * (1 + 0.15 * np.exp(-t / 0.1))) * np.exp(-t / 0.12) * \
        (1 + 0.5 * np.sin(2 * np.pi * 14 * t))
    return y * 0.6 + 0.35 * boing


def puffer_puff():
    r = rng("puffer")
    dur = 0.55
    n = ns(dur + 0.6)
    t = tvec(n)
    fc = 280 * (3.4 ** smoothstep(t / dur))
    env = smoothstep(t / 0.05) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.06))
    infl = filt(nb.svf(r.standard_normal(n), fc, 6.0, 1), chain(("lp", 2500, 0.7))) * env
    infl += 0.4 * np.sin(2 * np.pi * np.cumsum(fc * 0.5) / SR) * env
    pop = NA.bubble(900, seed=3, decay=0.03, rise=0.6)
    chime = ML.bell(85, 0.4, seed=7, tone="tiny")  # C#6: the deep's key
    out = np.zeros(n + ns(1.0))
    out[:n] += infl * 0.5
    i0 = ns(dur)
    out[i0:i0 + pop.size] += pop * 0.6
    k = min(chime.size, out.size - i0)
    out[i0:i0 + k] += chime[:k] * 0.25
    return filt(out, chain(("lp", 4500, 0.7)))


def octopus_wave():
    """A watery whoosh as a tentacle sweeps, then a soft glass chime (A major)."""
    r = rng("octo")
    dur = 1.6
    n = ns(dur)
    t = tvec(n)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    fc = 300 + 900 * np.sin(np.pi * np.clip(t / dur, 0, 1))
    wash = filt(nb.svf(r.standard_normal(n), fc, 1.5, 1), chain(("lp", 2200, 0.7), ("lp", 2600, 0.7))) * env
    wash += 0.5 * filt(r.standard_normal(n), chain(("lp", 250, 0.7))) * env
    tr = Track(dur + 3.0)
    tr.add(0, wash, gain=0.5)
    for k in range(10):
        tr.add(r.uniform(0.2, 1.3), NA.bubble(r.uniform(700, 1500), seed=k, decay=r.uniform(0.01, 0.025)),
               gain=0.12)
    for k, (tt, p) in enumerate([(0.85, 81), (1.05, 85), (1.25, 88)]):  # A5 C#6 E6
        tr.add(tt, ML.celesta(p, 0.5, dur=1.0, seed=k), gain=0.32)
    y = tr.buf.astype(float)
    y = eq(y, ("lp", 4000, 0.7))
    wet = reverb(y, "underwater")
    y = np.pad(y, ((0, 0), (0, wet.shape[1] - y.shape[1]))) + 0.4 * wet
    return y[:, : ns(dur + 3.0)]


def butterflies():
    """Monarchs lifting off: soft wingbeats at different rates and places,
    drifting up and away, with a faint shimmer."""
    tr = Track(3.2)
    for b in range(6):
        r = rng("bfly", b)
        rate = r.uniform(7, 11)
        t = r.uniform(0.0, 0.5)
        pan0, pan1 = r.uniform(-0.8, 0.8), r.uniform(-1, 1)
        life = r.uniform(1.4, 2.4)
        k = 0
        while t < life:
            u = t / life
            L = ns(0.05)
            uu = np.linspace(0, 1, L)
            flap = filt(r.standard_normal(L), chain(("bp", r.uniform(350, 650) * (1 - 0.3 * u), 1.2),
                                                    ("lp", 1500, 0.7), ("lp", 1800, 0.7))) * np.sin(np.pi * uu) ** 2
            g = 0.5 * (1 - u) ** 1.5 * r.uniform(0.6, 1.0)
            tr.add(t, flap, gain=g, pan=float(pan0 + (pan1 - pan0) * u))
            t += 1.0 / rate * r.uniform(0.9, 1.1)
            k += 1
    for k, (tt, p) in enumerate([(0.4, 91), (0.75, 95), (1.1, 98)]):  # G6 B6 D7
        tr.add(tt, ML.bell(p, 0.3, seed=k, tone="tiny"), gain=0.06, pan=[-0.4, 0.3, 0.0][k])
    y = tr.buf.astype(float)
    wet = reverb(y, "forest")
    y = np.pad(y, ((0, 0), (0, wet.shape[1] - y.shape[1]))) + 0.25 * wet
    return y[:, : ns(3.6)]


def render():
    for i in range(2):
        finish_sfx("giant-low", f"giant-low-{i + 1}", giant_low(i), -3.0, max_s=2.7)
    for i in range(3):
        finish_sfx("gummy-squeak", f"gummy-squeak-{i + 1}", gummy_squeak(i), -5.0)
    finish_sfx("puffer-puff", "puffer-puff", puffer_puff(), -4.0, max_s=1.1)
    finish_sfx("octopus-wave", "octopus-wave", octopus_wave(), -3.0, max_s=2.2)
    finish_sfx("butterflies", "butterflies", butterflies(), -5.0, stereo=True, max_s=1.7)


if __name__ == "__main__":
    render()
