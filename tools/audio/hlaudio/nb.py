"""Sample-by-sample DSP kernels compiled with numba (strings, filters, dynamics)."""
from __future__ import annotations

import math

import numpy as np
from numba import njit

SR = 44100.0


@njit(cache=True, fastmath=True)
def ks_string(n, exc, delay, gain, lp, ap_coef, ap_stages):
    """Extended Karplus-Strong string.

    exc     excitation (added into the loop), any length <= n
    delay   per-sample loop delay in samples (already tuned for filter delays)
    gain    per-sample loop gain (decay; lower it to damp the string)
    lp      one-pole loop low-pass coefficient (0 = no damping of highs)
    ap_coef first-order all-pass coefficient for stiffness (dispersion)
    """
    size = 1
    mx = 0.0
    for i in range(n):
        if delay[i] > mx:
            mx = delay[i]
    while size < int(mx) + 16:
        size *= 2
    mask = size - 1
    buf = np.zeros(size)
    out = np.zeros(n)
    lps = 0.0
    ap_x = np.zeros(8)
    ap_y = np.zeros(8)
    ne = exc.shape[0]
    w = 0
    for i in range(n):
        rp = w - delay[i]
        ip = math.floor(rp)
        fr = rp - ip
        ii = int(ip)
        x0 = buf[(ii - 1) & mask]
        x1 = buf[ii & mask]
        x2 = buf[(ii + 1) & mask]
        x3 = buf[(ii + 2) & mask]
        # 4-point Lagrange interpolation at fr in [0,1) between x1 and x2
        c0 = -fr * (fr - 1.0) * (fr - 2.0) / 6.0
        c1 = (fr + 1.0) * (fr - 1.0) * (fr - 2.0) / 2.0
        c2 = -(fr + 1.0) * fr * (fr - 2.0) / 2.0
        c3 = (fr + 1.0) * fr * (fr - 1.0) / 6.0
        y = c0 * x0 + c1 * x1 + c2 * x2 + c3 * x3
        lps = (1.0 - lp) * y + lp * lps
        v = lps
        for k in range(ap_stages):
            yy = ap_coef * v + ap_x[k] - ap_coef * ap_y[k]
            ap_x[k] = v
            ap_y[k] = yy
            v = yy
        v *= gain[i]
        if i < ne:
            v += exc[i]
        buf[w & mask] = v
        out[i] = v
        w += 1
    return out


@njit(cache=True, fastmath=True)
def svf(x, fc, q, mode):
    """Time-varying TPT state-variable filter. mode 0=LP 1=BP 2=HP 3=notch.
    fc is per-sample cutoff in Hz (array, same length as x)."""
    n = x.shape[0]
    out = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 1.0 / q
    for i in range(n):
        f = fc[i]
        if f < 10.0:
            f = 10.0
        if f > 0.45 * SR:
            f = 0.45 * SR
        g = math.tan(math.pi * f / SR)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            out[i] = v2
        elif mode == 1:
            out[i] = v1
        elif mode == 2:
            out[i] = x[i] - k * v1 - v2
        else:
            out[i] = x[i] - k * v1
    return out


@njit(cache=True, fastmath=True)
def comb_var(x, period, fb, damp):
    """Feedback comb with a time-varying period (samples) and damped feedback.
    Used to make breath noise 'sing' at the pitch of a flute tube."""
    n = x.shape[0]
    size = 1
    mx = 0.0
    for i in range(n):
        if period[i] > mx:
            mx = period[i]
    while size < int(mx) + 8:
        size *= 2
    mask = size - 1
    buf = np.zeros(size)
    out = np.empty(n)
    lp = 0.0
    w = 0
    for i in range(n):
        rp = w - period[i]
        ip = math.floor(rp)
        fr = rp - ip
        ii = int(ip)
        y = buf[ii & mask] * (1.0 - fr) + buf[(ii + 1) & mask] * fr
        lp = (1.0 - damp) * y + damp * lp
        v = x[i] + fb * lp
        buf[w & mask] = v
        out[i] = v
        w += 1
    return out


@njit(cache=True, fastmath=True)
def follow(x, att, rel):
    """Peak envelope follower with one-pole attack/release coefficients."""
    n = x.shape[0]
    out = np.empty(n)
    e = 0.0
    for i in range(n):
        v = x[i]
        if v > e:
            e = att * e + (1.0 - att) * v
        else:
            e = rel * e + (1.0 - rel) * v
        out[i] = e
    return out


@njit(cache=True, fastmath=True)
def release_smooth(g, rel):
    """Gain smoothing: instant drops, one-pole recovery (limiter release)."""
    n = g.shape[0]
    out = np.empty(n)
    s = 1.0
    for i in range(n):
        v = g[i]
        if v < s:
            s = v
        else:
            s = rel * s + (1.0 - rel) * v
        out[i] = s
    return out


@njit(cache=True, fastmath=True)
def onepole(x, a):
    n = x.shape[0]
    out = np.empty(n)
    s = x[0] if n else 0.0
    for i in range(n):
        s = a * s + (1.0 - a) * x[i]
        out[i] = s
    return out


@njit(cache=True, fastmath=True)
def vdelay(x, d):
    """Read x through a variable delay d (samples, >= 1) with cubic interpolation.
    x is treated as zero before its start."""
    n = x.shape[0]
    out = np.zeros(n)
    for i in range(n):
        rp = i - d[i]
        ip = math.floor(rp)
        fr = rp - ip
        ii = int(ip)
        if ii - 1 < 0 or ii + 2 >= n:
            continue
        x0 = x[ii - 1]
        x1 = x[ii]
        x2 = x[ii + 1]
        x3 = x[ii + 2]
        c0 = -fr * (fr - 1.0) * (fr - 2.0) / 6.0
        c1 = (fr + 1.0) * (fr - 1.0) * (fr - 2.0) / 2.0
        c2 = -(fr + 1.0) * fr * (fr - 2.0) / 2.0
        c3 = (fr + 1.0) * fr * (fr - 1.0) / 6.0
        out[i] = c0 * x0 + c1 * x1 + c2 * x2 + c3 * x3
    return out
