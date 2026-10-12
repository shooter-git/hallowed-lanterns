"""Sounds for the added scenes.

guitar-1..6      a big magical guitar's open strings, D3 A3 D4 F#4 A4 B4 (stereo):
                 the Ember's motif D B A F# A is strings 3 6 5 4 5. Sampled: the
                 VSCO 2 CE harp through a guitar body, fairly dry
                 (render_instruments() renders just these)
owl-hoot-1..2    a soft, friendly great horned owl with a little shimmer
web-stretch-1..2 a cobweb stretched and plucked: a soft elastic twang and silk rustle
spider-scurry    many tiny feet pattering (light and cute)
mantis-click     a few soft insect clicks
kraken-groan     a deep, warm, friendly groan of a giant sea creature (stereo)
tentacle-curl    a wet whoosh and a rubbery stretch
water-lap        small waves lapping a wooden boat (stereo, 4 s, loops seamlessly)
chest-open       an old chest creaking open, a cascade of coins, magical glitter
coins-1..3       little coin jingles
"""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec, Track, smoothstep, colored, smooth_random
from hlaudio.effects import chain, filt, reverb, eq, shimmer
from hlaudio.score import N
from hlaudio.lines import wt_osc
from hlaudio import mallets as ML, plucked as PL, voice as VO, nature as NA, perc as PC, nb, theme as TH
from hlaudio.core import m
from hlaudio.piece import finish_sfx
from hlaudio import sfxkit as K


def _wet(y, space, amt, keep, shimmer_amt=0.0):
    y = np.atleast_2d(np.asarray(y, dtype=float))
    if y.shape[0] == 1:
        y = np.vstack([y[0], y[0]])
    n = ns(keep)
    out = np.zeros((2, max(n, y.shape[1])))
    out[:, : y.shape[1]] += y
    layers = [(reverb(y, space), amt)]
    if shimmer_amt:
        layers.append((shimmer(y, "hall", gens=1, fb=0.35), shimmer_amt))
    for w, a in layers:
        k = min(out.shape[1], w.shape[1])
        out[:, :k] += a * w[:, :k]
    return out[:, :n]


# ----------------------------------------------------------------- guitar strings

def guitar_string(p, i):
    st = K.stage(4.5)
    K.play(st, "guitar", [N(0.01, 4.0, float(p), 0.72)], "harp", seed=200 + i, pan=-0.15 + 0.06 * i, width=0.5,
           extra={"shimmer:concert": 0.04})
    K.guitar_body(st, "guitar", 0.8, seed=i)
    return K.finish(st, {"shimmer:concert": {"seed": 8, "gens": 1, "fb": 0.35}})


# ----------------------------------------------------------------- owls and wings

def owl_hoot(i):
    """Great horned owl: hoo, h'hoo — hoo — hoo, low and soft."""
    r = rng("ghowl", i)
    f0 = [285.0, 255.0][i]
    pattern = [(0.0, 0.32, 1.0), (0.52, 0.11, 0.7), (0.66, 0.34, 0.95), (1.2, 0.36, 0.85), (1.78, 0.42, 0.8)]
    n = ns(2.4)
    y = np.zeros(n)
    for (t0, d, a) in pattern:
        L = ns(d)
        u = tvec(L) / d
        f = f0 * (1 + 0.035 * np.sin(np.pi * u) - 0.04 * u) * (1 + 0.003 * np.sin(2 * np.pi * 6 * u * d))
        ph = 2 * np.pi * np.cumsum(f) / SR
        env = smoothstep(u / 0.18) * smoothstep((1 - u) / 0.35)
        tone = np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.04 * np.sin(3 * ph)
        br = filt(r.standard_normal(L), chain(("bp", f0 * 2, 1.5))) * 0.05
        i0 = ns(t0)
        y[i0:i0 + L] += a * env * (tone + br)
    # a gentle magical shimmer: two faint glass tones high above, after the call
    t = tvec(n)
    for k, (tt, mult) in enumerate([(0.65, 4.0), (1.25, 5.0)]):
        e = np.where(t > tt, np.exp(-(t - tt) / 0.6) * (1 - np.exp(-(t - tt) / 0.05)), 0)
        y += 0.05 * e * np.sin(2 * np.pi * f0 * mult * t)
    y = filt(y, chain(("hp", 120, 0.7), ("lp", 3500, 0.7)))
    return _wet(y, "forest", 0.4, 3.2)


def web_stretch(i):
    """Silk drawn tight (a rising elastic tone), then let go: a soft twang."""
    r = rng("web", i)
    n = ns(1.4)
    t = tvec(n)
    st = 0.45 + 0.1 * i
    f_lo, f_hi = [(170.0, 300.0), (210.0, 360.0)][i]
    f = np.where(t < st, f_lo + (f_hi - f_lo) * smoothstep(t / st), f_hi * (1 + 0.03 * np.exp(-(t - st) / 0.05)))
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 7.5 * t) * (t > st))
    ph = 2 * np.pi * np.cumsum(f) / SR
    stretch_env = np.where(t < st, 0.18 * smoothstep(t / 0.1), 0.0)
    twang_env = np.where(t >= st, np.exp(-(t - st) / 0.28) * (1 - np.exp(-(t - st) / 0.002)), 0.0)
    tone = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)) * (stretch_env + twang_env)
    rustle = filt(r.standard_normal(n), chain(("bp", 2500, 1.2), ("lp", 5000, 0.7))) * \
        (0.08 * smoothstep(t / 0.1) * (t < st + 0.1) + 0.03 * twang_env)
    y = tone + rustle
    return _wet(y, "room", 0.2, 1.3)[0]


def spider_scurry():
    r = rng("spider")
    n = ns(1.3)
    y = np.zeros(n)
    t = 0.02
    while t < 1.05:
        # an eight-legged step: a quick ripple of four tiny taps
        for j in range(4):
            tt = t + j * r.uniform(0.008, 0.016)
            L = ns(0.012)
            tv = tvec(L)
            f = r.uniform(1600, 2600)
            tap = np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.003) * (1 - np.exp(-tv / 0.0004))
            i0 = ns(tt)
            if i0 + L < n:
                y[i0:i0 + L] += tap * r.uniform(0.3, 1.0) * (0.6 + 0.4 * np.sin(np.pi * t / 1.05))
        t += r.uniform(0.07, 0.1)
    y = filt(y, chain(("hp", 700, 0.7), ("lp", 3500, 0.7), ("lp", 4200, 0.7)))
    return _wet(y, "room", 0.15, 1.3)[0]


def mantis_click():
    r = rng("mantis")
    n = ns(0.9)
    y = np.zeros(n)
    for k, t in enumerate([0.02, 0.16, 0.24, 0.52]):
        L = ns(0.03)
        tv = tvec(L)
        f = r.uniform(2400, 3000)
        c = (np.sin(2 * np.pi * f * tv) * np.exp(-tv / 0.004) + 0.5 * np.sin(2 * np.pi * 950 * tv) * np.exp(-tv / 0.006)) \
            * (1 - np.exp(-tv / 0.0005))
        i0 = ns(t)
        y[i0:i0 + L] += c * [1.0, 0.7, 0.55, 0.85][k]
    y = filt(y, chain(("hp", 500, 0.7), ("lp", 5000, 0.7)))
    return _wet(y, "room", 0.15, 0.85)[0]


# ----------------------------------------------------------------- sea creatures

def kraken_groan():
    """A slow, friendly 'hmmm?' from something enormous: a low moan that lifts
    at the end, a little wooden creak in its throat, deep water around it."""
    dur = 3.0
    y = VO.whale_call(72.0, dur, contour=[(0.0, -2.0), (0.35, 1.5), (0.7, 0.5), (0.92, 4.0), (1.0, 3.5)],
                      seed=5, rough=0.12, bright=0.7)
    y += 0.45 * VO.whale_call(108.0, dur, contour=[(0.0, -2.0), (0.35, 1.5), (0.7, 0.5), (0.92, 4.0), (1.0, 3.5)],
                              seed=6, rough=0.08, bright=0.5)
    cr = NA.creak(seed=40, dur=1.6, rate=(9, 16), res=(180, 320, 520))
    cr = filt(cr, chain(("lp", 1200, 0.7)))
    out = np.zeros(ns(dur + 0.2))
    out[: y.size] += y / (np.max(np.abs(y)) + 1e-9)
    i0 = ns(0.5)
    out[i0:i0 + cr.size] += 0.12 * cr / (np.max(np.abs(cr)) + 1e-9)
    out = filt(out, chain(("hp", 40, 0.7), ("lp", 1500, 0.7)))
    return _wet(out, "underwater", 0.5, 3.6)


def tentacle_curl():
    r = rng("tentacle")
    n = ns(1.4)
    t = tvec(n)
    env = np.sin(np.pi * np.clip(t / 1.0, 0, 1)) ** 1.4
    fc = 300 + 700 * smoothstep(t / 0.8)
    whoosh = filt(nb.svf(r.standard_normal(n), fc, 1.5, 1), chain(("lp", 1800, 0.7), ("lp", 2200, 0.7))) * env
    y = 0.6 * whoosh
    # wet squelches: little resonant slurps dropping in pitch
    for k in range(7):
        tt = r.uniform(0.1, 0.9)
        L = ns(0.06)
        tv = tvec(L)
        f = r.uniform(500, 1100) * (1 - 0.5 * tv / 0.06)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tv / 0.015) * (1 - np.exp(-tv / 0.001))
        i0 = ns(tt)
        y[i0:i0 + L] += 0.25 * s * r.uniform(0.5, 1.0)
    # rubbery stretch: a friction squeak gliding up
    L = ns(0.45)
    tv = tvec(L)
    f = 210 * (1 + 0.55 * smoothstep(tv / 0.45)) * (1 + 0.05 * np.sin(2 * np.pi * 23 * tv))
    sq = wt_osc(f, lambda k: 1.0 / k ** 1.2 if k < 8 else 0.0, ceiling=3500)
    sq = nb.svf(sq, np.full(L, 900.0), 2.0, 1) * np.sin(np.pi * tv / 0.45) ** 1.5
    i0 = ns(0.45)
    y[i0:i0 + L] += 0.35 * sq
    return _wet(y, "underwater", 0.25, 1.5)[0]


def water_lap(seconds=4.0):
    """Seamless loop: gentle water movement and small waves slapping a hull."""
    tr = Track(seconds, circular=True)
    n = tr.n
    r = rng("lap")
    bed = np.vstack([colored(n, rng("lap", c), -4.0, lo=150, hi=1000) for c in range(2)])
    mod = 0.6 + 0.4 * smooth_random(n, r, 1.2, circular=True) * 2
    tr.mix(bed * np.clip(mod, 0.1, 1.3) * 0.05)
    for k, t0 in enumerate([0.35, 1.7, 2.95]):
        L = ns(0.5)
        tv = tvec(L)
        slap = filt(r.standard_normal(L), chain(("lp", 1300, 0.7), ("lp", 1600, 0.7), ("hp", 200, 0.7))) * \
            np.exp(-tv / 0.09) * (1 - np.exp(-tv / 0.012))
        hull = (np.sin(2 * np.pi * 135 * tv) + 0.5 * np.sin(2 * np.pi * 262 * tv)) * np.exp(-tv / 0.12) * \
            (1 - np.exp(-tv / 0.004))
        tr.add(t0, slap * 0.55 + hull * 0.2, pan=float([-0.3, 0.25, -0.05][k]))
        for j in range(int(r.integers(4, 8))):
            tr.add(t0 + r.uniform(0.15, 0.7), NA.bubble(r.uniform(900, 2200), seed=k * 20 + j,
                                                       decay=r.uniform(0.006, 0.015), rise=0.3),
                   gain=0.06, pan=float(r.uniform(-0.6, 0.6)))
    y = tr.buf.astype(float)
    y = eq(y, ("lp", 3500, 0.7), circular=True)
    wet = reverb(y, "room", circular=True)
    return y + 0.25 * wet


# ----------------------------------------------------------------- treasure

def coin(seed, v=0.6):
    r = rng("coin", seed)
    base = r.uniform(2100, 3300)
    parts = [(1.0, 1.0, r.uniform(0.15, 0.35)), (r.uniform(1.5, 1.65), 0.55, r.uniform(0.1, 0.25)),
             (r.uniform(2.15, 2.3), 0.3, r.uniform(0.06, 0.15)), (r.uniform(2.85, 3.0), 0.15, 0.05)]
    return ML.modal(base, parts, 0.45, attack=0.0002, phase_rand=True, seed=seed) * v


def coins(i):
    r = rng("coins", i)
    n = ns(0.9)
    y = np.zeros(n)
    t = 0.01
    for k in range([4, 6, 5][i]):
        c = coin(i * 100 + k, r.uniform(0.35, 0.9))
        i0 = ns(t)
        L = min(c.size, n - i0)
        y[i0:i0 + L] += c[:L]
        t += r.exponential(0.07)
    y = filt(y, chain(("hs", 5000, 0.7, -4), ("lp", 8000, 0.7)))
    return _wet(y, "room", 0.2, 0.9)[0]


def chest_open():
    r = rng("chest")
    tr = Track(3.6)
    # the hinge: a slow creak rising in pitch as the lid lifts
    cr = NA.creak(seed=77, dur=0.9, rate=(28, 60), res=(850, 1500, 2300))
    cr = filt(cr, chain(("hp", 400, 0.7), ("lp", 3000, 0.7), ("lp", 3600, 0.7)))
    tr.add(0.0, cr / (np.max(np.abs(cr)) + 1e-9), gain=0.4)
    tr.add(0.92, PC.knock(125.0, 0.7, seed=3, hollow=1.4), gain=0.5)
    # coins spill: dense at first, thinning out
    t = 1.0
    k = 0
    while t < 2.3:
        tr.add(t, coin(500 + k, r.uniform(0.25, 0.8)), gain=0.32, pan=float(r.uniform(-0.5, 0.5)))
        t += r.exponential(0.012 + 0.05 * (t - 1.0))
        k += 1
    # glitter
    pent = [86, 88, 90, 93, 95, 98]
    t = 1.05
    while t < 2.4:
        tr.add(t, ML.glockenspiel(float(r.choice(pent)), r.uniform(0.25, 0.5), seed=k), gain=0.12,
               pan=float(r.uniform(-0.7, 0.7)))
        t += r.uniform(0.05, 0.16)
        k += 1
    y = eq(tr.buf.astype(float), ("hs", 5500, 0.7, -4), ("lp", 8000, 0.7))
    return _wet(y, "room", 0.2, 3.3, shimmer_amt=0.12)


def render_instruments():
    for i, nm in enumerate(TH.GUITAR_NOTES):
        finish_sfx("guitar", f"guitar-{i + 1}", guitar_string(m(nm), i), -3.0, stereo=True, max_s=4.0)


def render():
    render_instruments()
    for i in range(2):
        finish_sfx("owl-hoot", f"owl-hoot-{i + 1}", owl_hoot(i), -4.0, max_s=3.0)
    for i in range(2):
        finish_sfx("web-stretch", f"web-stretch-{i + 1}", web_stretch(i), -5.0, max_s=1.3)
    finish_sfx("spider-scurry", "spider-scurry", spider_scurry(), -6.0, max_s=1.3)
    finish_sfx("mantis-click", "mantis-click", mantis_click(), -6.0, max_s=0.85)
    finish_sfx("kraken-groan", "kraken-groan", kraken_groan(), -3.0, stereo=True, max_s=3.5)
    finish_sfx("tentacle-curl", "tentacle-curl", tentacle_curl(), -4.0, max_s=1.5)
    finish_sfx("water-lap", "water-lap", water_lap(4.0), -6.0, stereo=True, loop=True)
    finish_sfx("chest-open", "chest-open", chest_open(), -3.0, max_s=3.3)
    for i in range(3):
        finish_sfx("coins", f"coins-{i + 1}", coins(i), -5.0, max_s=0.9)


if __name__ == "__main__":
    render()
