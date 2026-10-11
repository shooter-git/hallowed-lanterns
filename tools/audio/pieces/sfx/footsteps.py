"""Footsteps: gravel (the arbor lane), grass, snow and soft sea-floor sand.

Each step is a heel strike and a toe roll. Gravel and snow are granular:
hundreds of tiny impacts (stones knocking, snow crystals fracturing) under
the step's pressure envelope; grass is a soft swish over a muffled thud;
sand is a fine, muffled shuffle.
"""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec
from hlaudio.effects import chain, filt, reverb
from hlaudio.piece import finish_sfx

PEAK = -6.0  # footsteps repeat a lot: keep them modest


def grains(n, times, r, lo, hi, dur=(0.0006, 0.003), amp=(0.2, 1.0), q=2.5):
    y = np.zeros(n)
    for t in times:
        i = ns(t)
        L = ns(r.uniform(*dur))
        if i + L >= n or L < 2:
            continue
        f = np.exp(r.uniform(np.log(lo), np.log(hi)))
        tt = tvec(L)
        g = np.sin(2 * np.pi * f * tt + r.uniform(0, 6)) * np.exp(-tt / (L / SR / 3))
        g += 0.25 * r.standard_normal(L) * np.exp(-tt / (L / SR / 4))
        y[i:i + L] += g * r.uniform(*amp)
    return y


def thud(n, r, f=110.0, decay=0.03, lp=400.0, at=0.0):
    t = tvec(n)
    tt = np.maximum(t - at, 0)
    x = r.standard_normal(n) * np.exp(-tt / decay) * (t >= at)
    x = filt(x, chain(("lp", lp, 0.7), ("lp", lp, 0.7)))
    x += 0.5 * np.sin(2 * np.pi * f * tt) * np.exp(-tt / (decay * 1.3)) * (t >= at)
    return x


def gravel(seed):
    r = rng("gravel", seed)
    n = ns(0.55)
    heel = r.uniform(0.0, 0.005)
    toe = heel + r.uniform(0.11, 0.17)
    y = thud(n, r, r.uniform(90, 130), 0.025, 350, heel) * 0.6
    y += thud(n, r, r.uniform(110, 150), 0.02, 300, toe) * 0.3
    t1 = heel + r.beta(1.6, 4.0, int(r.integers(160, 260))) * 0.16
    t2 = toe + r.beta(1.5, 3.0, int(r.integers(90, 160))) * 0.14
    y += grains(n, t1, r, 700, 4200, amp=(0.05, 0.6))
    y += 0.7 * grains(n, t2, r, 800, 4500, amp=(0.05, 0.5))
    # a few distinct pebble clicks rolling off
    t3 = toe + r.uniform(0.02, 0.2, int(r.integers(3, 8)))
    y += grains(n, t3, r, 1800, 3800, dur=(0.002, 0.006), amp=(0.2, 0.6))
    y = filt(y, chain(("hp", 60, 0.7), ("lp", 5000, 0.7), ("lp", 6000, 0.7), ("hs", 3000, 0.7, -4)))
    return y


def grass(seed):
    r = rng("grass", seed)
    n = ns(0.5)
    t = tvec(n)
    heel = 0.005
    toe = heel + r.uniform(0.1, 0.16)
    y = thud(n, r, r.uniform(80, 110), 0.035, 250, heel) * 1.1
    y += thud(n, r, r.uniform(90, 120), 0.03, 220, toe) * 0.55
    env = np.exp(-np.maximum(t - heel, 0) / 0.07) * (1 - np.exp(-np.maximum(t - heel, 0) / 0.01)) * (t > heel)
    env += 0.6 * np.exp(-np.maximum(t - toe, 0) / 0.09) * (1 - np.exp(-np.maximum(t - toe, 0) / 0.015)) * (t > toe)
    sw = filt(r.standard_normal(n), chain(("bp", r.uniform(1200, 1900), 1.2), ("lp", 3500, 0.7))) * env * 0.3
    y += sw
    stems = heel + r.uniform(0, 0.25, int(r.integers(5, 14)))
    y += grains(n, stems, r, 1000, 3000, dur=(0.001, 0.004), amp=(0.05, 0.2))
    return filt(y, chain(("hp", 50, 0.7), ("lp", 4500, 0.7), ("lp", 5500, 0.7)))


def snow(seed):
    r = rng("snowstep", seed)
    n = ns(0.6)
    heel = 0.005
    toe = heel + r.uniform(0.13, 0.19)
    y = thud(n, r, r.uniform(70, 100), 0.04, 220, heel) * 0.6
    t1 = heel + r.beta(1.4, 2.4, int(r.integers(450, 700))) * 0.2
    t2 = toe + r.beta(1.4, 2.4, int(r.integers(250, 400))) * 0.17
    c = grains(n, t1, r, 500, 3200, dur=(0.0008, 0.003), amp=(0.05, 0.4))
    c += 0.75 * grains(n, t2, r, 600, 3200, dur=(0.0008, 0.003), amp=(0.05, 0.4))
    # cold-snow squeak: a narrow resonance riding the crunch
    sq = filt(c, chain(("bp", r.uniform(900, 1300), 6.0)))
    y += c + 0.6 * sq
    return filt(y, chain(("hp", 50, 0.7), ("lp", 3200, 0.7), ("lp", 4200, 0.7)))


def sand(seed):
    r = rng("sand", seed)
    n = ns(0.6)
    t = tvec(n)
    heel = 0.005
    toe = heel + r.uniform(0.14, 0.2)
    y = thud(n, r, r.uniform(60, 85), 0.05, 200, heel) * 0.8
    y += thud(n, r, r.uniform(70, 95), 0.045, 180, toe) * 0.4
    env = np.exp(-np.maximum(t - heel, 0) / 0.09) * (t > heel) * (1 - np.exp(-np.maximum(t - heel, 0) / 0.02))
    env += 0.7 * np.exp(-np.maximum(t - toe, 0) / 0.1) * (t > toe) * (1 - np.exp(-np.maximum(t - toe, 0) / 0.02))
    sh = filt(r.standard_normal(n), chain(("bp", r.uniform(700, 1100), 0.7))) * env * 0.4
    y += sh
    return filt(y, chain(("hp", 40, 0.7), ("lp", 1800, 0.7), ("lp", 2500, 0.7)))


def _with_space(y, space, amt):
    wet = reverb(y, space)[:, : y.shape[-1] + ns(0.4)]
    dry = np.vstack([y, y])
    dry = np.pad(dry, ((0, 0), (0, wet.shape[1] - dry.shape[1])))
    return dry + amt * wet


def render():
    for i in range(4):
        finish_sfx("step-gravel", f"step-gravel-{i + 1}", _with_space(gravel(i), "room", 0.08), PEAK, max_s=0.5)
        finish_sfx("step-grass", f"step-grass-{i + 1}", _with_space(grass(i), "forest", 0.05), PEAK, max_s=0.45)
        finish_sfx("step-snow", f"step-snow-{i + 1}", _with_space(snow(i), "room", 0.05), PEAK, max_s=0.55)
    for i in range(3):
        finish_sfx("step-sand", f"step-sand-{i + 1}", _with_space(sand(i), "underwater", 0.12), PEAK, max_s=0.5)


if __name__ == "__main__":
    render()
