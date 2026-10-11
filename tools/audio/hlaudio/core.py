"""Core helpers: sample rate, pitch names, envelopes, noise, panning and the Track buffer.

Everything in the library works on float64 numpy arrays while a sound is being
made and stores finished parts in float32 Tracks of shape (2, n).
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

SR = 44100

_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NAME_RE = re.compile(r"^([A-Ga-g])([#b]*)(-?\d+)$")


def m(name) -> float:
    """MIDI number from a note name ("D5", "F#4", "Bb3") or pass a number through."""
    if isinstance(name, (int, float, np.integer, np.floating)):
        return float(name)
    mt = _NAME_RE.match(name.strip())
    if not mt:
        raise ValueError(f"bad note name {name!r}")
    letter, acc, octv = mt.groups()
    v = _NOTE[letter.upper()] + acc.count("#") - acc.count("b")
    return float(12 * (int(octv) + 1) + v)


def hz(midi) -> float:
    return 440.0 * 2.0 ** ((np.asarray(midi, dtype=float) - 69.0) / 12.0)


def name(midi: float) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    mi = int(round(midi))
    return f"{names[mi % 12]}{mi // 12 - 1}"


def ns(seconds: float) -> int:
    return int(round(seconds * SR))


def db(a):
    return 20.0 * np.log10(np.maximum(np.abs(a), 1e-12))


def undb(d):
    return 10.0 ** (np.asarray(d, dtype=float) / 20.0)


def rng(*parts) -> np.random.Generator:
    """Deterministic random generator from any printable seed parts."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))


def tvec(n: int) -> np.ndarray:
    return np.arange(n, dtype=float) / SR


# ----------------------------------------------------------------- envelopes

def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2, hold=None, curve=3.0):
    """Attack/decay/sustain/release envelope of n samples. `hold` is the note-on
    time in seconds (default: n minus release)."""
    t = tvec(n)
    hold = (n / SR - r) if hold is None else hold
    env = np.empty(n)
    a = max(a, 1e-4)
    att = np.clip(t / a, 0, 1)
    env = np.sin(att * np.pi / 2) ** 2  # smooth start
    dec = np.where(t > a, s + (1 - s) * np.exp(-curve * (t - a) / max(d, 1e-4)), 1.0)
    env = np.where(t < a, env, dec)
    rel_t = t - hold
    level_at_hold = np.interp(hold, t, env) if n else 0.0
    rel = level_at_hold * np.exp(-6.9 * np.clip(rel_t, 0, None) / max(r, 1e-4))
    env = np.where(t >= hold, np.minimum(env, rel), env)
    return env


def fade(x, fin=0.0, fout=0.0):
    """Raised-cosine fade in/out (seconds) on the last axis, in place copy."""
    y = np.array(x, dtype=float, copy=True)
    n = y.shape[-1]
    if fin > 0:
        k = min(n, ns(fin))
        y[..., :k] *= np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    if fout > 0:
        k = min(n, ns(fout))
        y[..., n - k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return y


def smoothstep(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def env_points(n, pts, kind="smooth"):
    """Envelope through (time_s, value) points; `smooth` uses cosine segments."""
    t = tvec(n)
    ts = np.array([p[0] for p in pts], float)
    vs = np.array([p[1] for p in pts], float)
    if kind == "linear":
        return np.interp(t, ts, vs)
    idx = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 2)
    t0, t1 = ts[idx], ts[idx + 1]
    v0, v1 = vs[idx], vs[idx + 1]
    u = np.clip((t - t0) / np.maximum(t1 - t0, 1e-9), 0, 1)
    u = 0.5 - 0.5 * np.cos(np.pi * u)
    out = v0 + (v1 - v0) * u
    out[t < ts[0]] = vs[0]
    out[t > ts[-1]] = vs[-1]
    return out


# ----------------------------------------------------------------- noise

def white(n, r: np.random.Generator):
    return r.standard_normal(n)


def colored(n, r: np.random.Generator, slope_db_oct=-3.0, lo=20.0, hi=None):
    """Noise with a spectral slope (−3 pink, −6 brown) between lo and hi Hz."""
    spec = r.standard_normal(n // 2 + 1) + 1j * r.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = 1.0
    g = (f / 1000.0) ** (slope_db_oct / 6.0206)
    g[f < lo] *= (f[f < lo] / lo) ** 4
    if hi:
        g *= 1.0 / np.sqrt(1 + (f / hi) ** 8)
    g[0] = 0
    x = np.fft.irfft(spec * g, n)
    return x / (np.std(x) + 1e-12)


def smooth_random(n, r: np.random.Generator, rate_hz=0.5, circular=False, sr=SR):
    """Slow random wobble in [-1, 1]-ish (std ~0.5), band-limited to rate_hz.
    With circular=True the result loops seamlessly over n samples."""
    if not circular and (n > 4 * sr or sr != SR):
        # cheap path for long one-off curves: cosine-interpolated random points
        step = max(2, int(sr / (rate_hz * 2.2)))
        k = n // step + 3
        pts = r.standard_normal(k)
        pos = np.arange(n) / step
        i = pos.astype(np.int64)
        u = 0.5 - 0.5 * np.cos(np.pi * (pos - i))
        x = pts[i] * (1 - u) + pts[i + 1] * u
        return x * (0.5 / 0.8)
    spec = r.standard_normal(n // 2 + 1) + 1j * r.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / SR)
    g = np.exp(-0.5 * (f / max(rate_hz, 1e-3)) ** 2)
    g[0] = 0
    x = np.fft.irfft(spec * g, n)  # irfft is periodic by construction
    x = x / (np.std(x) + 1e-12) * 0.5
    return x


def periodic_lfo(n, rate_hz, phase=0.0, circular=False):
    """Sine LFO; with circular=True the rate snaps so it completes whole cycles in n."""
    if circular:
        cycles = max(1, round(rate_hz * n / SR))
        rate_hz = cycles * SR / n
    return np.sin(2 * np.pi * rate_hz * tvec(n) + phase)


# ----------------------------------------------------------------- panning

def pan_gains(p: float):
    """Constant-power gains for pan p in [-1, 1]."""
    a = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return np.cos(a), np.sin(a)


def to_stereo(x, pan=0.0, width=1.0):
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        gl, gr = pan_gains(pan)
        return np.vstack([x * gl, x * gr])
    if width != 1.0:
        mid = 0.5 * (x[0] + x[1])
        side = 0.5 * (x[0] - x[1]) * width
        x = np.vstack([mid + side, mid - side])
    if pan:
        gl, gr = pan_gains(pan)
        x = np.vstack([x[0] * gl * 1.4142, x[1] * gr * 1.4142])
    return x


# ----------------------------------------------------------------- tracks

class Track:
    """A stereo buffer. Circular tracks wrap anything written past the end back
    to the start, so a piece rendered into one loops perfectly (the steady state
    of playing it forever)."""

    def __init__(self, seconds: float, circular: bool = False):
        self.n = ns(seconds)
        self.circular = circular
        self.buf = np.zeros((2, self.n), dtype=np.float32)

    @property
    def seconds(self):
        return self.n / SR

    def add(self, start: float, sig, gain: float = 1.0, pan: float = 0.0, width: float = 1.0):
        sig = to_stereo(sig, pan, width) * gain
        s = int(round(start * SR))
        L = sig.shape[1]
        if self.circular:
            s %= self.n
            pos = 0
            while pos < L:
                i = (s + pos) % self.n
                k = min(self.n - i, L - pos)
                self.buf[:, i:i + k] += sig[:, pos:pos + k].astype(np.float32)
                pos += k
        else:
            if s < 0:
                sig = sig[:, -s:]
                L = sig.shape[1]
                s = 0
            end = s + L
            if end > self.n:
                grow = np.zeros((2, end - self.n), dtype=np.float32)
                self.buf = np.concatenate([self.buf, grow], axis=1)
                self.n = end
            self.buf[:, s:end] += sig.astype(np.float32)
        return self

    def mix(self, other, gain=1.0):
        if isinstance(other, Track):
            other = other.buf
        if other.shape[1] != self.n:
            if self.circular:
                raise ValueError("circular track length mismatch")
            if other.shape[1] > self.n:
                self.buf = np.concatenate(
                    [self.buf, np.zeros((2, other.shape[1] - self.n), np.float32)], axis=1)
                self.n = other.shape[1]
            else:
                other = np.pad(other, ((0, 0), (0, self.n - other.shape[1])))
        self.buf += (other * gain).astype(np.float32)
        return self

    def like(self):
        t = Track(0, self.circular)
        t.n = self.n
        t.buf = np.zeros_like(self.buf)
        return t

    def copy_with(self, buf):
        t = Track(0, self.circular)
        t.n = buf.shape[1]
        t.buf = np.asarray(buf, dtype=np.float32)
        return t
