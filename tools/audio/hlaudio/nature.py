"""Ambience generators: crickets, birds, a distant happy murmur, wind in
leaves, reeds, fog, creaking wood, snow hush, underwater rumble, bubbles.

All generators write into a Track; with a circular Track the result loops.
Continuous beds use periodic (FFT-built) noise and modulators so they wrap
seamlessly; events are placed modulo the loop length.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from . import nb
from .core import SR, hz, ns, rng, tvec, Track, colored, smooth_random, smoothstep, to_stereo
from .effects import chain, filt, eq
from .lines import wt_osc


# ----------------------------------------------------------------- insects

def cricket_chirp(carrier=4300.0, syllables=3, syl=0.016, gap=0.011, seed=0, harm=0.03):
    r = rng("chirp", seed)
    n = ns(syllables * (syl + gap) + 0.02)
    y = np.zeros(n)
    for s in range(syllables):
        L = ns(syl * r.uniform(0.85, 1.15))
        t = tvec(L)
        f = carrier * (1 + 0.02 * (1 - t / syl)) * r.uniform(0.995, 1.005)
        ph = 2 * np.pi * np.cumsum(f) / SR
        env = np.sin(np.pi * np.clip(t / syl, 0, 1)) ** 1.5
        seg = env * (np.sin(ph) + harm * np.sin(2 * ph + 0.3))
        i = ns(s * (syl + gap))
        k = min(L, n - i)
        y[i:i + k] += seg[:k] * (0.8 + 0.2 * (s == 0))
    return y


def crickets(track: Track, start, dur, count=6, carrier=(3900, 4800), rate=(1.2, 2.6), level=0.05,
             distance=(0.3, 1.0), seed=0, syllables=(2, 4), pan=0.9):
    """A field of chirping crickets at various distances."""
    for c in range(count):
        r = rng("crickets", seed, c)
        car = r.uniform(*carrier)
        syl = int(r.integers(syllables[0], syllables[1] + 1))
        tmpl = cricket_chirp(car, syl, seed=seed * 100 + c)
        d = r.uniform(*distance)
        lp = 6500 - 4000 * d
        tmpl = filt(tmpl, chain(("lp", lp, 0.7), ("hp", 1500, 0.7)))
        g = level * (1.0 - 0.75 * d) * r.uniform(0.6, 1.0)
        pn = r.uniform(-pan, pan)
        period = 1.0 / r.uniform(*rate)
        t = start + r.uniform(0, period)
        # crickets pause now and then
        active = True
        next_toggle = t + r.uniform(4, 15)
        while t < start + dur:
            if t > next_toggle:
                active = not active
                next_toggle = t + (r.uniform(5, 20) if active else r.uniform(1.5, 6))
            if active:
                track.add(t, tmpl * r.uniform(0.75, 1.0), gain=g, pan=pn)
            t += period * r.uniform(0.96, 1.04)
    return track


def tree_crickets(track: Track, start, dur, count=3, carrier=(2500, 3100), pulse=(38, 55), level=0.03,
                  seed=0, pan=0.8):
    """Soft continuous trills (snowy tree crickets): the 'magical' night hum."""
    n_total = ns(dur)
    for c in range(count):
        r = rng("treecr", seed, c)
        n = n_total
        t = tvec(n)
        car = r.uniform(*carrier)
        pr = r.uniform(*pulse)
        if track.circular and abs(dur - track.seconds) < 1e-6:
            pr = max(1, round(pr * dur)) / dur
            car = max(1, round(car * dur)) / dur
        pulses = (0.5 + 0.5 * np.sin(2 * np.pi * pr * t)) ** 4
        y = np.sin(2 * np.pi * car * t) * pulses
        sw = smooth_random(n, r, 0.08, circular=track.circular) * 2
        env = np.clip(0.55 + 0.6 * sw, 0, 1)
        y = filt(y * env, chain(("lp", 6000, 0.7)), track.circular)
        track.add(start, y, gain=level * r.uniform(0.6, 1.0), pan=r.uniform(-pan, pan))
    return track


# ----------------------------------------------------------------- birds

def thrush_phrase(seed=0, base=None):
    """Hermit-thrush-like song: a pure held intro note, then a fluting cascade
    with a second voice."""
    r = rng("thrush", seed)
    base = base or r.uniform(2300, 3400)
    parts = []
    t = 0.0
    dur0 = r.uniform(0.22, 0.36)
    parts.append((t, dur0, base, base * r.uniform(0.98, 1.0), 1.0))
    t += dur0 + r.uniform(0.02, 0.05)
    k = int(r.integers(4, 8))
    hi = base * r.uniform(1.15, 1.45)
    for i in range(k):
        f0 = hi * r.uniform(0.85, 1.12)
        d = r.uniform(0.04, 0.075)
        parts.append((t, d, f0, f0 * r.uniform(0.9, 1.06), r.uniform(0.45, 0.85)))
        t += d + r.uniform(0.005, 0.02)
    n = ns(t + 0.1)
    y = np.zeros(n)
    for (t0, d, fa, fb, a) in parts:
        L = ns(d)
        tt = tvec(L)
        f = fa + (fb - fa) * tt / d
        ph = 2 * np.pi * np.cumsum(f) / SR
        env = np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 0.8
        seg = env * (np.sin(ph) + 0.08 * np.sin(2 * ph))
        # two-voiced syrinx: a second tone a fifth-ish above on the cascade
        if t0 > 0:
            seg += 0.35 * env * np.sin(ph * r.uniform(1.42, 1.52))
        i = ns(t0)
        y[i:i + L] += a * seg[: n - i]
    return y


def robin_phrase(seed=0):
    r = rng("robin", seed)
    k = int(r.integers(3, 6))
    t = 0.0
    segs = []
    for i in range(k):
        d = r.uniform(0.13, 0.24)
        f1, f2, f3 = r.uniform(1900, 2400), r.uniform(2600, 3300), r.uniform(1800, 2500)
        segs.append((t, d, f1, f2, f3))
        t += d + r.uniform(0.08, 0.16)
    n = ns(t + 0.1)
    y = np.zeros(n)
    for (t0, d, f1, f2, f3) in segs:
        L = ns(d)
        u = tvec(L) / d
        f = np.where(u < 0.4, f1 + (f2 - f1) * u / 0.4, f2 + (f3 - f2) * (u - 0.4) / 0.6)
        ph = 2 * np.pi * np.cumsum(f) / SR
        env = np.sin(np.pi * u) ** 1.2
        i = ns(t0)
        y[i:i + L] += env * (np.sin(ph) + 0.15 * np.sin(2 * ph))
    return y


def birds(track: Track, start, dur, kind="thrush", every=(5, 10), level=0.05, distance=0.5, seed=0, pan=0.8):
    r = rng("birds", kind, seed)
    t = start + r.uniform(0, every[0])
    i = 0
    pn = r.uniform(-pan, pan)
    while t < start + dur:
        y = thrush_phrase(seed * 1000 + i) if kind == "thrush" else robin_phrase(seed * 1000 + i)
        y = filt(y, chain(("lp", 8000 - 4000 * distance, 0.7), ("hp", 1200, 0.7)))
        track.add(t, y, gain=level * (1 - 0.6 * distance) * r.uniform(0.7, 1.0),
                  pan=float(np.clip(pn + r.normal(0, 0.1), -1, 1)))
        t += r.uniform(*every)
        i += 1
        if r.uniform() < 0.25:
            pn = r.uniform(-pan, pan)
    return track


def owl(track: Track, t, level=0.03, seed=0, pan=0.0):
    """A soft distant owl: hoo ... hoo-hoo."""
    r = rng("owl", seed)
    f0 = r.uniform(330, 400)
    for k, (dt, d, a) in enumerate([(0.0, 0.42, 1.0), (0.75, 0.18, 0.7), (1.0, 0.5, 0.9)]):
        L = ns(d)
        u = tvec(L) / d
        f = f0 * (1 + 0.04 * np.sin(np.pi * u) - 0.03 * u)
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) ** 0.7
        y += 0.06 * np.sin(4 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u)
        track.add(t + dt, y, gain=level * a, pan=pan)
    return track


# ----------------------------------------------------------------- voices far away

_VOWELS = {"a": (750, 1200, 2600), "e": (480, 1900, 2600), "i": (320, 2300, 3000),
           "o": (480, 850, 2500), "u": (360, 800, 2400), "@": (520, 1450, 2500)}


def murmur(track: Track, start, dur, speakers=14, level=0.02, seed=0, laugh=0.15, lp=1400.0):
    """A distant, happy crowd: formant-synthesised babble (no words), the odd
    laugh, heavily low-passed by distance. Never intelligible."""
    total = ns(dur)
    for s in range(speakers):
        r = rng("murmur", seed, s)
        female = r.uniform() < 0.5
        f_base = r.uniform(190, 250) if female else r.uniform(100, 140)
        fscale = 1.15 if female else 1.0
        n = total
        f0 = np.full(n, f_base)
        F = np.zeros((3, n))
        amp = np.zeros(n)
        t = r.uniform(0, 2.0)
        vow = list(_VOWELS)
        cur = np.array(_VOWELS["@"]) * fscale
        while t < dur:
            # an utterance of a few 'words'
            words = int(r.integers(2, 7))
            u_start = t
            for w in range(words):
                syl = int(r.integers(1, 4))
                for sy in range(syl):
                    d = r.uniform(0.11, 0.23)
                    a = ns(t)
                    b = min(n, ns(t + d))
                    if a >= n:
                        break
                    v = np.array(_VOWELS[vow[r.integers(len(vow))]]) * fscale * r.uniform(0.95, 1.05)
                    F[:, a:b] = v[:, None]
                    L = b - a
                    env = np.sin(np.pi * np.linspace(0, 1, L)) ** 0.6 * r.uniform(0.6, 1.0)
                    amp[a:b] = np.maximum(amp[a:b], env)
                    t += d + r.uniform(0.0, 0.04)
                t += r.uniform(0.04, 0.15)
            # pitch: declination over the utterance with a lift on stress
            a, b = ns(u_start), min(n, ns(t))
            if b > a:
                L = b - a
                f0[a:b] = f_base * (1.12 - 0.22 * np.linspace(0, 1, L)) * (1 + 0.08 * np.sin(np.linspace(0, r.uniform(3, 9), L)))
            # sometimes a laugh
            if r.uniform() < laugh:
                hs = int(r.integers(3, 7))
                for h in range(hs):
                    d = r.uniform(0.09, 0.13)
                    a = ns(t)
                    b = min(n, ns(t + d))
                    if a >= n:
                        break
                    F[:, a:b] = (np.array(_VOWELS["a"]) * fscale)[:, None]
                    f0[a:b] = f_base * (1.35 - 0.06 * h)
                    amp[a:b] = np.maximum(amp[a:b], np.sin(np.pi * np.linspace(0, 1, b - a)) * (1 - 0.1 * h))
                    t += d + 0.06
            t += r.uniform(0.5, 3.5)
        # smooth formant tracks and amplitude a little
        k = ns(0.03)
        ker = np.hanning(2 * k + 1)
        ker /= ker.sum()
        for i in range(3):
            F[i] = signal.oaconvolve(np.where(F[i] > 0, F[i], cur[i]), ker, "same")
        amp = signal.oaconvolve(amp, ker, "same")
        src = wt_osc(f0, lambda kk: 1.0 / kk ** 1.2, ceiling=4000)
        src += 0.15 * r.standard_normal(n)
        y = (nb.svf(src, F[0], 5.0, 1) + 0.5 * nb.svf(src, F[1], 7.0, 1) + 0.15 * nb.svf(src, F[2], 9.0, 1)) * amp
        track.add(start, y, gain=level / np.sqrt(speakers) * 3, pan=r.uniform(-0.7, 0.7))
    track.buf = eq(track.buf, ("lp", lp, 0.6), ("lp", lp * 1.2, 0.6), ("hp", 150, 0.7), circular=track.circular).astype(np.float32)
    return track


# ----------------------------------------------------------------- air and leaves

def _gust(n, r, rate=0.07, base=0.35, depth=0.65, circular=True):
    g = smooth_random(n, r, rate, circular=circular) * 2
    return np.clip(base + depth * (0.5 + 0.5 * np.tanh(1.5 * g)), 0, 1.2)


def wind_leaves(track: Track, level=0.05, seed=0, crackle=1.0, low=0.5, gust_rate=0.07, bright=1.0):
    """Wind in leaves: gusting rustle, sparse leaf crackles, a low wind body."""
    n = track.n
    circ = track.circular
    r = rng("leaves", seed)
    gust = _gust(n, r, gust_rate, circular=circ)
    out = np.zeros((2, n))
    for ch in range(2):
        rc = rng("leaves", seed, ch)
        rust = colored(n, rc, -2.5, lo=500, hi=4200 * bright)
        flutter = 0.6 + 0.4 * np.abs(smooth_random(n, rc, 9.0, circular=circ)) * 2
        g = np.roll(gust, ns(0.6) * ch)
        out[ch] += rust * g ** 1.6 * flutter * 0.5
        # leaf crackles: impulses with density following the gust
        dens = 120 * g ** 2 * crackle  # per second
        p = dens / SR
        hits = rc.uniform(size=n) < p
        imp = hits * rc.uniform(-1, 1, n) * (0.3 + 0.7 * rc.uniform(size=n))
        cr = filt(imp, chain(("bp", 2600 * bright, 1.5), ("lp", 4500, 0.7)), circ)
        out[ch] += cr * 1.5
        bodyw = colored(n, rc, -6.0, lo=40, hi=400)
        out[ch] += low * bodyw * g ** 1.3 * 0.6
    out = filt(out, chain(("lp", 5500, 0.7), ("hs", 3500, 0.7, -3)), circ)
    track.mix(out * level)
    return track


def fog_hush(track: Track, level=0.02, seed=0, cutoff=2200.0, rate=0.05):
    n = track.n
    r = rng("fog", seed)
    breath = 0.6 + 0.4 * smooth_random(n, r, rate, circular=track.circular) * 2
    out = np.vstack([colored(n, rng("fog", seed, c), -3.0, lo=150, hi=cutoff) for c in range(2)])
    track.mix(out * np.clip(breath, 0.1, 1.2) * level)
    return track


def reeds(track: Track, level=0.04, seed=0, swishes=0.25, knocks=0.08):
    """Rustling reed fence: dry swishes in gusts and an occasional reed tap."""
    n = track.n
    r = rng("reeds", seed)
    gust = _gust(n, r, 0.06, circular=track.circular)
    out = np.zeros((2, n))
    for ch in range(2):
        rc = rng("reeds", seed, ch)
        hiss = colored(n, rc, -2.0, lo=1000, hi=4500)
        out[ch] += hiss * gust ** 2 * 0.35
    track.mix(out * level)
    secs = track.seconds
    t = 0.0
    k = 0
    while t < secs:
        t += r.exponential(1 / max(swishes, 1e-3))
        d = r.uniform(0.35, 0.9)
        L = ns(d)
        u = np.linspace(0, 1, L)
        env = np.sin(np.pi * u ** r.uniform(0.6, 1.4)) ** 2
        sw = filt(r.standard_normal(L), chain(("bp", r.uniform(1600, 3200), 1.2), ("lp", 4500, 0.7))) * env
        track.add(t, sw, gain=level * 0.5 * r.uniform(0.4, 1), pan=r.uniform(-0.8, 0.8))
        if r.uniform() < knocks * 5:
            from .perc import knock
            kn = knock(r.uniform(600, 950), 0.4, seed=k, hollow=0.4)
            track.add(t + r.uniform(0, d), filt(kn, chain(("hp", 400, 0.7))), gain=level * 0.25,
                      pan=r.uniform(-0.8, 0.8))
        k += 1
    return track


def creak(seed=0, dur=1.0, rate=(25, 60), res=(380, 900)):
    """Slow wooden creak: stick-slip pulses through body resonances."""
    r = rng("creak", seed)
    n = ns(dur)
    t = tvec(n)
    rt = rate[0] + (rate[1] - rate[0]) * (0.5 + 0.5 * np.sin(np.pi * t / dur * r.uniform(0.6, 1.4)))
    ph = np.cumsum(rt) / SR
    pulses = np.diff(np.floor(ph), prepend=0) > 0
    imp = pulses * r.uniform(0.5, 1.0, n)
    y = np.zeros(n)
    for f in res:
        y += filt(imp, chain(("bp", f * r.uniform(0.9, 1.1), 6.0)))
    y += 0.3 * filt(imp, chain(("bp", 1600, 3.0)))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.7
    return y * env


def snow_hush(track: Track, level=0.02, seed=0):
    n = track.n
    r = rng("snow", seed)
    out = np.vstack([colored(n, rng("snow", seed, c), -4.5, lo=80, hi=1100) for c in range(2)])
    g = 0.7 + 0.3 * smooth_random(n, r, 0.04, circular=track.circular) * 2
    track.mix(out * g * level)
    return track


def wind_whoosh(track: Track, level=0.03, seed=0, cutoff=700.0, rate=0.05, whistle=0.0):
    """Soft, muffled wind (snow, open fields): band-limited noise in slow gusts,
    optionally with a faint resonant whistle that slides with the gust."""
    n = track.n
    circ = track.circular
    r = rng("whoosh", seed)
    gust = _gust(n, r, rate, base=0.15, depth=0.9, circular=circ)
    out = np.zeros((2, n))
    for ch in range(2):
        rc = rng("whoosh", seed, ch)
        x = colored(n, rc, -5.0, lo=60, hi=cutoff)
        out[ch] = x * np.roll(gust, ns(0.8) * ch) ** 1.5
        if whistle:
            fc = 500 + 500 * np.roll(gust, ns(0.8) * ch)
            w = nb.svf(rc.standard_normal(n), fc, 25.0, 1)
            out[ch] += whistle * w / (np.std(w) + 1e-9) * gust ** 3 * 0.3
    track.mix(out * level)
    return track


# ----------------------------------------------------------------- water

def bubble(f0=1400.0, seed=0, decay=0.018, rise=0.25):
    r = rng("bubble", seed)
    n = ns(decay * 7)
    t = tvec(n)
    f = f0 * (1 + rise * t / (decay * 3))
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay) * (1 - np.exp(-t / 0.0008))
    return y * r.uniform(0.6, 1.0)


def bubble_stream(track: Track, t, dur=1.5, rate=12, f=(900, 1800), level=0.03, seed=0, pan=0.0):
    r = rng("bstream", seed)
    base = r.uniform(*f)
    tt = t
    i = 0
    while tt < t + dur:
        fb = base * r.uniform(0.8, 1.25)
        track.add(tt, bubble(fb, seed * 1000 + i, r.uniform(0.01, 0.03)), gain=level * r.uniform(0.4, 1),
                  pan=float(np.clip(pan + r.normal(0, 0.1), -1, 1)))
        tt += r.exponential(1 / rate)
        i += 1
    return track


def underwater_bed(track: Track, level=0.05, seed=0):
    """Deep, slow rumble and a faint moving 'water hiss'."""
    n = track.n
    circ = track.circular
    r = rng("deepbed", seed)
    swell = 0.6 + 0.4 * smooth_random(n, r, 0.05, circular=circ) * 2
    out = np.zeros((2, n))
    for ch in range(2):
        rc = rng("deepbed", seed, ch)
        out[ch] += colored(n, rc, -7.0, lo=25, hi=180) * swell
        out[ch] += 0.08 * colored(n, rc, -3.0, lo=200, hi=1200) * np.roll(swell, ns(2.0))
    track.mix(out * level)
    return track
