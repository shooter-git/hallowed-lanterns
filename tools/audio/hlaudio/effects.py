"""Effects: biquad EQ, generated-impulse convolution reverbs, shimmer, chorus,
tape wow/flutter, saturation and echoes.

Every function takes stereo arrays of shape (2, n) (or mono (n,)) and a
`circular` flag. Circular processing treats the signal as one period of an
endless loop, so filters, reverbs and modulations wrap around seamlessly.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from . import nb
from .core import SR, ns, rng, tvec, smooth_random


# ----------------------------------------------------------------- biquads (RBJ)

def _biquad(b0, b1, b2, a0, a1, a2):
    return np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]])


def bq(kind, f, q=0.7071, gain_db=0.0):
    f = min(max(f, 5.0), 0.49 * SR)
    w = 2 * np.pi * f / SR
    cw, sw = np.cos(w), np.sin(w)
    A = 10 ** (gain_db / 40)
    al = sw / (2 * q)
    if kind == "lp":
        return _biquad((1 - cw) / 2, 1 - cw, (1 - cw) / 2, 1 + al, -2 * cw, 1 - al)
    if kind == "hp":
        return _biquad((1 + cw) / 2, -(1 + cw), (1 + cw) / 2, 1 + al, -2 * cw, 1 - al)
    if kind == "bp":
        return _biquad(al, 0, -al, 1 + al, -2 * cw, 1 - al)
    if kind == "peak":
        return _biquad(1 + al * A, -2 * cw, 1 - al * A, 1 + al / A, -2 * cw, 1 - al / A)
    if kind in ("ls", "hs"):
        sq = 2 * np.sqrt(A) * al
        if kind == "ls":
            return _biquad(A * ((A + 1) - (A - 1) * cw + sq), 2 * A * ((A - 1) - (A + 1) * cw),
                           A * ((A + 1) - (A - 1) * cw - sq), (A + 1) + (A - 1) * cw + sq,
                           -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sq)
        return _biquad(A * ((A + 1) + (A - 1) * cw + sq), -2 * A * ((A - 1) + (A + 1) * cw),
                       A * ((A + 1) + (A - 1) * cw - sq), (A + 1) - (A - 1) * cw + sq,
                       2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sq)
    raise ValueError(kind)


def chain(*bands):
    """bands: tuples like ('lp', 8000), ('peak', 300, 1.0, -3), ('hs', 6000, 0.7, -4)."""
    sos = []
    for b in bands:
        kind, f = b[0], b[1]
        q = b[2] if len(b) > 2 else 0.7071
        g = b[3] if len(b) > 3 else 0.0
        sos.append(bq(kind, f, q, g))
    return np.vstack(sos)


def filt(x, sos, circular=False, warm=1.0):
    """Apply an SOS filter along the last axis; circular wraps the filter state."""
    x = np.asarray(x)
    if not circular:
        return signal.sosfilt(sos, x, axis=-1)
    w = min(ns(warm), x.shape[-1])
    pre = x[..., -w:]
    y = signal.sosfilt(sos, np.concatenate([pre, x], axis=-1), axis=-1)
    return y[..., w:]


def eq(x, *bands, circular=False):
    return filt(x, chain(*bands), circular)


def zero_phase_lowpass(x, f, order=4):
    sos = signal.butter(order, f, fs=SR, output="sos")
    return signal.sosfiltfilt(sos, x, axis=-1)


def dc_block(x, circular=False):
    return filt(x, chain(("hp", 18.0, 0.6)), circular, warm=2.0)


# ----------------------------------------------------------------- convolution

def convolve(x, h, circular=False):
    """Convolve (…, n) by (…, m). Circular = period-n circular convolution (h is
    folded if longer than n). Non-circular returns length n + m - 1."""
    x = np.asarray(x, dtype=np.float64)
    h = np.asarray(h, dtype=np.float64)
    n = x.shape[-1]
    if circular:
        m = h.shape[-1]
        if m > n:
            k = int(np.ceil(m / n))
            hp = np.zeros(h.shape[:-1] + (k * n,))
            hp[..., :m] = h
            h = hp.reshape(h.shape[:-1] + (k, n)).sum(axis=-2)
        X = np.fft.rfft(x, n)
        H = np.fft.rfft(h, n)
        return np.fft.irfft(X * H, n)
    return signal.oaconvolve(x, h, axes=-1) if x.ndim == h.ndim else signal.fftconvolve(x, h)


def stereo_convolve(x, ir, circular=False, cross=0.55):
    """x (2,n) through a 4-channel IR (LL, RR, LR, RL); cross sets channel bleed."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.vstack([x, x])
    LL = convolve(x[0], ir[0], circular)
    RR = convolve(x[1], ir[1], circular)
    LR = convolve(x[0], ir[2], circular)
    RL = convolve(x[1], ir[3], circular)
    return np.vstack([LL + cross * RL, RR + cross * LR])


SPACES = {
    # name: rt60 per band (Hz edges below), predelay, early reflections, character
    "room": dict(rt=[0.7, 0.65, 0.6, 0.55, 0.45, 0.35, 0.25], pre=0.006, er=14, er_span=0.03,
                 build=0.01, length=1.6, hi=9000),
    "forest": dict(rt=[1.6, 1.6, 1.5, 1.3, 1.0, 0.7, 0.45], pre=0.012, er=22, er_span=0.09,
                   build=0.03, length=3.2, hi=7000, sparse=0.5),
    "field": dict(rt=[2.2, 2.0, 1.6, 1.2, 0.8, 0.5, 0.3], pre=0.02, er=6, er_span=0.15,
                  build=0.05, length=4.0, hi=6000, sparse=0.7),
    "hall": dict(rt=[2.6, 2.5, 2.3, 2.1, 1.7, 1.2, 0.8], pre=0.018, er=24, er_span=0.07,
                 build=0.035, length=5.0, hi=9000),
    "cathedral": dict(rt=[5.5, 5.4, 5.0, 4.3, 3.2, 2.2, 1.4], pre=0.035, er=30, er_span=0.12,
                      build=0.07, length=8.5, hi=8000),
    "underwater": dict(rt=[4.5, 4.2, 3.4, 2.2, 1.2, 0.6, 0.3], pre=0.03, er=10, er_span=0.08,
                       build=0.12, length=7.0, hi=3500),
    "plate": dict(rt=[3.2, 3.2, 3.0, 2.8, 2.4, 1.9, 1.3], pre=0.004, er=0, er_span=0.01,
                  build=0.005, length=6.0, hi=10000),
    "scoring": dict(rt=[2.9, 2.7, 2.4, 2.1, 1.7, 1.2, 0.8], pre=0.022, er=36, er_span=0.09, build=0.03,
                    length=5.5, hi=9000),
    "epic": dict(rt=[4.4, 4.1, 3.6, 3.0, 2.3, 1.5, 0.9], pre=0.03, er=40, er_span=0.12, build=0.05,
                 length=7.5, hi=8500),
    # the rescore's halls: dense smooth tails, darker tops, real pre-delay
    "concert": dict(rt=[3.6, 3.4, 3.0, 2.6, 2.0, 1.35, 0.85], pre=0.026, er=34, er_span=0.09, build=0.06,
                    length=8.0, hi=5800, er_lp=0.5),
    "cathedral2": dict(rt=[6.2, 6.0, 5.2, 4.2, 3.0, 1.9, 1.1], pre=0.038, er=36, er_span=0.14, build=0.1,
                       length=11.0, hi=4800, er_lp=0.6),
    "chamber": dict(rt=[1.6, 1.5, 1.35, 1.2, 0.95, 0.7, 0.45], pre=0.012, er=30, er_span=0.045, build=0.02,
                    length=3.0, hi=6500, er_lp=0.4),
    "sky": dict(rt=[7.5, 7.2, 6.8, 6.0, 4.8, 3.4, 2.2], pre=0.06, er=8, er_span=0.2,
                build=0.25, length=11.0, hi=7500),
}
_BAND_EDGES = [150, 400, 1000, 2500, 5000, 9000]  # 7 bands


def make_ir(space="hall", seed=0, rt_scale=1.0, **over):
    """Generate a 4-channel (LL, RR, LR, RL) impulse response for `space`.

    Late reverb is decorrelated noise split into 7 bands, each with its own
    exponential decay (highs die first), a diffusion build-up and a pre-delay.
    Early reflections are sparse low-passed taps scattered left/right.
    """
    p = dict(SPACES[space])
    p.update(over)
    r = rng("ir", space, seed)
    length = p["length"] * max(1.0, rt_scale)
    n = ns(length)
    t = tvec(n)
    f = np.fft.rfftfreq(n, 1 / SR)
    edges = [0] + _BAND_EDGES + [SR]
    lf = np.log2(np.maximum(f, 1.0))
    masks = []
    for b in range(7):
        lo, hi = edges[b], edges[b + 1]
        mk = np.ones_like(f)
        if b > 0:
            mk *= 0.5 + 0.5 * np.tanh((lf - np.log2(lo)) * 4)
        if b < 6:
            mk *= 0.5 - 0.5 * np.tanh((lf - np.log2(hi)) * 4)
        masks.append(mk)
    tot = np.sum(masks, axis=0)
    masks = [mk / tot for mk in masks]
    hi_roll = 1.0 / np.sqrt(1 + (f / p["hi"]) ** 4)
    lo_roll = 1.0 / np.sqrt(1 + (60.0 / np.maximum(f, 1.0)) ** 4)
    pre = ns(p["pre"])
    build = 1 - np.exp(-np.maximum(t - p["pre"], 0) / p["build"])
    build[t < p["pre"]] = 0
    out = np.zeros((4, n))
    sparse = p.get("sparse", 0.0)
    for ch in range(4):
        noise = r.standard_normal(n)
        if sparse:
            # forests/fields: clumpy, less dense tails (scattering off trees)
            clump = np.abs(smooth_random(n, r, 30.0)) * 2
            noise *= (1 - sparse) + sparse * clump
        N = np.fft.rfft(noise)
        late = np.zeros(n)
        for b in range(7):
            rt = p["rt"][b] * rt_scale
            band = np.fft.irfft(N * masks[b] * hi_roll * lo_roll, n)
            late += band * np.exp(-6.9078 * t / rt)
        late *= build
        # early reflections
        er = np.zeros(n)
        # reflections arrive after the pre-delay, thicker and duller as they go
        times = np.sort(p["pre"] + r.uniform(0.0, p["er_span"], p["er"]) * (1 + 0.25 * (ch % 2)))
        for k, d in enumerate(times):
            i = ns(d)
            if i < n:
                er[i] += r.choice([-1, 1]) * r.uniform(0.35, 1.0) * np.exp(-(d - p["pre"]) / (p["er_span"] * 0.8 + 1e-3))
        if p["er"]:
            a = p.get("er_lp", 0.35)
            er = signal.lfilter([0.5, 0.5], [1.0], er)
            er = signal.lfilter([1 - a], [1, -a], er)
            er = signal.lfilter([1 - a * 0.6], [1, -a * 0.6], er)
        late_e = np.sqrt(np.sum(late ** 2)) + 1e-12
        er_e = np.sqrt(np.sum(er ** 2)) + 1e-12
        sig = late / late_e + (0.45 * er / er_e if p["er"] else 0)
        if ch >= 2:
            sig *= 0.8
        out[ch] = sig
    out[:, :pre // 2] = 0
    # gentle fade at the very end
    k = ns(0.2)
    out[:, -k:] *= np.linspace(1, 0, k)
    return out


_IR_CACHE: dict = {}


def reverb(x, space="hall", mix=1.0, circular=False, seed=0, rt_scale=1.0, cross=0.55, **over):
    """Wet signal of `space` for x (returns only the wet part, scaled by mix)."""
    key = (space, seed, rt_scale, tuple(sorted(over.items())))
    if key not in _IR_CACHE:
        _IR_CACHE[key] = make_ir(space, seed, rt_scale, **over)
    ir = _IR_CACHE[key]
    y = stereo_convolve(x, ir, circular, cross)
    if not circular:
        return y * mix
    return y * mix


# ----------------------------------------------------------------- pitch / shimmer

def octave_up(x, circular=False, grain=4096):
    """Granular octave-up shifter (soft, slightly chorused: ideal for shimmer)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        return np.vstack([octave_up(x[0], circular, grain), octave_up(x[1], circular, grain + 256)])
    x = zero_phase_lowpass(x, 7000.0)
    n = x.shape[0]
    G = grain
    H = G // 4
    if circular:
        xx = np.concatenate([x, x, x[: 2 * G + H]])
    else:
        xx = np.concatenate([x, np.zeros(2 * G + H)])
    win = np.hanning(G)
    out = np.zeros(n + G + H)
    nk = n // H + 1
    j = np.arange(G)
    for c0 in range(0, nk, 512):
        ks = np.arange(c0, min(nk, c0 + 512))
        starts = ks * H
        idx = starts[:, None] + 2 * j[None, :]
        grains = xx[idx] * win[None, :]
        for row, s in zip(grains, starts):
            out[s:s + G] += row
    out *= 2.0 / 3.0  # hann at 75% overlap sums to 1.5
    if circular:
        y = out[:n].copy()
        y[: G + H] += out[n:n + G + H]
        return y
    return out[:n]


def shimmer(x, space="cathedral", gens=3, fb=0.45, circular=False, seed=0, rt_scale=1.0):
    """Shimmer reverb: reverb, then octave-up of the reverb fed back for a few
    generations, each darker and quieter. Returns wet only."""
    x = np.asarray(x, dtype=np.float64)
    wet = reverb(x, space, 1.0, circular, seed, rt_scale)
    cur = wet
    total = wet.copy()
    n = x.shape[-1]
    for g in range(gens):
        up = octave_up(cur[:, :n] if not circular else cur, circular)
        up = eq(up, ("lp", 6500 - 1200 * g, 0.7), ("hp", 300, 0.7), circular=circular)
        cur = reverb(up, space, 1.0, circular, seed + g + 1, rt_scale) * fb
        if circular:
            total += cur
        else:
            m = max(total.shape[1], cur.shape[1])
            total = np.pad(total, ((0, 0), (0, m - total.shape[1])))
            total[:, :cur.shape[1]] += cur
    return total


# ----------------------------------------------------------------- modulation

def _mod_delay(x, d_samples, circular):
    """Variable delay over a (possibly circular) signal."""
    n = x.shape[0]
    if circular:
        pad = int(np.max(d_samples)) + 8
        xx = np.concatenate([x[-pad:], x])
        dd = np.concatenate([np.full(pad, d_samples[0]), d_samples])
        return nb.vdelay(xx, dd)[pad:]
    return nb.vdelay(x, d_samples)


def chorus(x, rate=0.35, depth_ms=3.0, base_ms=12.0, mix=0.45, circular=False, voices=2, seed=0):
    """Stereo chorus: a few modulated delay taps per side."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.vstack([x, x])
    n = x.shape[1]
    t = tvec(n)
    out = x * (1 - mix * 0.5)
    r = rng("chorus", seed)
    for ch in range(2):
        acc = np.zeros(n)
        for v in range(voices):
            rt = rate * r.uniform(0.7, 1.3)
            if circular:
                rt = max(1, round(rt * n / SR)) * SR / n
            ph = r.uniform(0, 2 * np.pi) + ch * np.pi / 2
            d = (base_ms + v * 4 + depth_ms * np.sin(2 * np.pi * rt * t + ph)) * SR / 1000
            acc += _mod_delay(x[ch], d, circular)
        out[ch] += acc / voices * mix
    return out


def wow_flutter(x, wow=0.0018, flutter=0.0004, circular=False, seed=0):
    """Tape-style pitch wobble: slow wow plus faster flutter (fractions of pitch)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = x[None, :]
    n = x.shape[1]
    r = rng("wow", seed)
    t = tvec(n)
    wr = 0.55
    fr = 6.5
    if circular:
        wr = max(1, round(wr * n / SR)) * SR / n
        fr = max(1, round(fr * n / SR)) * SR / n
    w = smooth_random(n, r, 0.4, circular) * 2 + 0.6 * np.sin(2 * np.pi * wr * t)
    fl = np.sin(2 * np.pi * fr * t + r.uniform(0, 6)) + 0.4 * smooth_random(n, r, 12.0, circular)
    # delay (seconds) whose derivative gives the pitch deviation
    dev = wow * w + flutter * fl
    d = np.cumsum(dev) / SR * SR  # in samples (integral of fractional deviation)
    d = d - d.min() + 16
    if circular:
        # make the delay periodic by removing its linear trend
        trend = (d[-1] - d[0]) * np.arange(n) / n
        d = d - trend
        d = d - d.min() + 16
    out = np.vstack([_mod_delay(x[c], d, circular) for c in range(x.shape[0])])
    return out


def saturate(x, drive=1.5, mix=1.0, even=0.08):
    """Gentle tape-ish saturation with a touch of even harmonics."""
    x = np.asarray(x, dtype=np.float64)
    y = np.tanh(drive * (x + even * x * x)) / np.tanh(drive)
    y = y - np.mean(y, axis=-1, keepdims=True)
    return (1 - mix) * x + mix * y


def echo(x, time=0.375, fb=0.35, mix=0.25, lp=4500, circular=False, pingpong=True, taps=6):
    """Feedback echo, rendered as a finite tap series (works circularly)."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.vstack([x, x])
    n = x.shape[1]
    out = np.zeros((2, n + (0 if circular else ns(time * taps))))
    cur = x
    sos = chain(("lp", lp, 0.6), ("hp", 200, 0.6))
    for k in range(1, taps + 1):
        cur = filt(cur, sos, circular)
        g = fb ** (k - 1)
        src = cur[::-1] if (pingpong and k % 2 == 1) else cur
        d = ns(time * k)
        for ch in range(2):
            if circular:
                out[ch] += np.roll(src[ch], d) * g
            else:
                out[ch, d:d + n] += src[ch] * g
    return out * mix


def soften(x, amount=0.5, circular=False, fast=0.0004, slow=0.010):
    """Transient softener: pulls down the first milliseconds of each attack
    (close-mic click, hammer, mallet) relative to the body of the note."""
    x = np.asarray(x, dtype=np.float64)
    st = np.atleast_2d(x)
    pre = ns(0.3) if circular else 0
    m = np.abs(st).max(axis=0)
    if pre:
        m = np.concatenate([m[-pre:], m])
    ef = nb.follow(m, np.exp(-1 / (fast * SR)), np.exp(-1 / (0.03 * SR)))
    es = nb.follow(m, np.exp(-1 / (slow * SR)), np.exp(-1 / (0.03 * SR)))
    g = np.clip((es + 1e-6) / (ef + 1e-6), 0.2, 1.0) ** amount
    g = nb.onepole(g, np.exp(-1 / (0.0007 * SR)))
    if pre:
        g = g[pre:]
    return (st * g).reshape(x.shape)


def tremulant(x, rate=5.4, amp=0.05, pitch_ms=0.12, circular=False):
    """Organ tremulant: a gentle wavering of level and pitch."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    n = x.shape[1]
    if circular:
        rate = max(1, round(rate * n / SR)) * SR / n
    t = tvec(n)
    lfo = np.sin(2 * np.pi * rate * t)
    out = np.empty_like(x)
    for c in range(x.shape[0]):
        d = (1.0 + pitch_ms * (1 + np.sin(2 * np.pi * rate * t + c * 0.8))) * SR / 1000
        out[c] = _mod_delay(x[c], d, circular)
    return out * (1 + amp * lfo)


def duck(x, times, depth=0.35, attack=0.008, release=0.22, circular=False):
    """Side-chain style pumping: dip x at each time in `times` (seconds)."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    n = x.shape[1]
    g = np.zeros(n)
    k = ns(release * 5)
    tt = np.arange(k) / SR
    shape = (1 - np.exp(-tt / max(attack, 1e-4))) * np.exp(-tt / release)
    shape /= shape.max() + 1e-12
    for t in times:
        i = ns(t)
        if circular:
            idx = (i + np.arange(k)) % n
            g[idx] = np.maximum(g[idx], shape)
        elif i < n:
            e = min(n, i + k)
            g[i:e] = np.maximum(g[i:e], shape[: e - i])
    return x * (1 - depth * g)


def width(x, w=1.0):
    mid = 0.5 * (x[0] + x[1])
    side = 0.5 * (x[0] - x[1]) * w
    return np.vstack([mid + side, mid - side])


def haas(x, ms=8.0, side=1):
    """Mono -> stereo with a small inter-channel delay for width."""
    d = ns(ms / 1000)
    a = np.asarray(x, dtype=np.float64)
    b = np.concatenate([np.zeros(d), a])[: a.shape[0]]
    return np.vstack([a, b]) if side > 0 else np.vstack([b, a])
