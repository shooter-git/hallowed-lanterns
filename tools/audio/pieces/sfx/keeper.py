"""keeper-rise: the giant octopus (the Keeper of the Deep) rising out of the dark - no music, just
the sea moving: a deep surge of displaced water building for six seconds, a rush of bubbles
streaming up as it comes, and a long, low groan, as if something enormous were stretching.

Made from Joseph Sardin's recordings (BigSoundBank, CC0): his foley "Wind", slowed right down
into the water's surge, and the creak of "Bones cracking #3" (a stick of celery), slowed into
the groan. The bubbles are synthesised, like the Deep's own."""
import numpy as np

from hlaudio.core import SR, ns, rng, Track
from hlaudio.effects import chain, filt, reverb
from hlaudio import nature as NA, nb
from hlaudio.piece import finish_sfx, update_manifest
from hlaudio.recordings import WIND, declick, entry, lock_cc0, original

CELERY = ("1409", "https://bigsoundbank.com/bones-cracking-3-s1409.html")
LENGTH = 9.0


def slower(x, k):
    from scipy.signal import resample_poly
    return resample_poly(x, int(round(100 * k)), 100)


def surge(seed):
    """Displaced water: the foley wind four times slower (two octaves down), its band rising as
    the Keeper comes up, swelling to the top of the rise and settling."""
    r = rng("keeper-surge", seed)
    air = declick(original("0595")[None])[0]
    a = ns(r.uniform(5, 60))
    x = slower(air[a: a + ns(LENGTH / 4 + 0.5)], 4.0)[: ns(LENGTH)]
    n = len(x)
    t = np.arange(n) / SR
    u = np.clip(t / 6.0, 0, 1)
    fc = 70 + 380 * u ** 1.4
    y = nb.svf(x, fc, 0.9, 1)
    env = np.sin(np.pi / 2 * u) ** 1.6 * np.where(t < 6.0, 1.0, np.exp(-(t - 6.0) / 1.2))
    y = y / (np.max(np.abs(y)) + 1e-9) * env
    return filt(y, chain(("hp", 28, 0.7), ("lp", 700, 0.7)))


def groan(seed):
    """The celery's creak, six times slower: a low, organic groan in two long breaths."""
    r = rng("keeper-groan", seed)
    x = original(CELERY[0])
    c = x[ns(0.08): ns(0.26)]
    out = np.zeros(ns(LENGTH))
    for at, k, g in ((1.4, r.uniform(5.5, 6.5), 1.0), (4.3, r.uniform(6.5, 7.5), 0.8)):
        y = slower(c, k)
        y = filt(y, chain(("lp", 600, 0.7), ("hp", 40, 0.7)))
        y = y / (np.max(np.abs(y)) + 1e-9)
        m = len(y)
        y *= np.sin(np.pi * np.arange(m) / m) ** 0.8
        i = ns(at)
        y = y[: len(out) - i]
        out[i: i + len(y)] += g * y
    return out


def keeper_rise(seed):
    tr = Track(LENGTH)
    s = surge(seed)
    tr.add(0.0, s, gain=0.9, width=1.0)
    tr.add(0.0, groan(seed), gain=0.45, pan=0.1)
    bub = Track(LENGTH)
    r = rng("keeper-bubbles", seed)
    t = 1.0
    while t < 6.5:
        NA.bubble_stream(bub, t, dur=r.uniform(0.8, 1.6), rate=r.uniform(14, 26), f=(380, 900),
                         level=0.06 * min(1.0, t / 4.0), seed=int(t * 10) + seed, pan=float(r.uniform(-0.6, 0.6)))
        t += r.uniform(0.35, 0.8)
    tr.mix(filt(bub.buf.astype(np.float64), chain(("lp", 2200, 0.7))) * 0.8)
    y = tr.buf.astype(np.float64)
    wet = reverb(y, "underwater")
    y = y + 0.35 * wet[:, : y.shape[1]]
    k = ns(1.5)
    y[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return y


def render():
    update_manifest("sfx", "keeper-rise", [])
    name = "keeper-rise"
    finish_sfx("keeper-rise", name, keeper_rise(1), -3.0, stereo=True, max_s=LENGTH, kbps=128)
    made = entry(name, WIND["0595"][1], "Wind and Bones cracking #3 (slowed into the sea's surge and a groan)")
    made["also"] = CELERY[1]
    lock_cc0([made], ("keeper-rise",))


if __name__ == "__main__":
    render()
