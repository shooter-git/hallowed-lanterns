"""Loudness (EBU R128 / BS.1770-4), true peak, glue compression, a true-peak
aware limiter, MP3 encoding with ffmpeg and post-encode verification."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

from . import nb
from .core import SR, ns, db, undb
from .effects import chain, filt


# ----------------------------------------------------------------- measurement

def _k_weight(x):
    # BS.1770 K-weighting, coefficients re-derived for 44.1 kHz (pyloudnorm method)
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    K = np.tan(np.pi * fc / SR)
    Vh = 10 ** (G / 20)
    Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    y = signal.lfilter(b, a, x, axis=-1)
    fc2, Q2 = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * fc2 / SR)
    a0 = 1 + K / Q2 + K * K
    b = [1, -2, 1]
    a = [1, 2 * (K * K - 1) / a0, (1 - K / Q2 + K * K) / a0]
    return signal.lfilter(b, a, y, axis=-1)


def lufs(x):
    """Integrated loudness in LUFS of (2,n) or (n,) audio."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    y = _k_weight(x)
    blk, hop = ns(0.4), ns(0.1)
    n = y.shape[1]
    if n < blk:
        y = np.pad(y, ((0, 0), (0, blk - n)))
        n = blk
    c = np.concatenate([np.zeros((y.shape[0], 1)), np.cumsum(y ** 2, axis=1)], axis=1)
    starts = np.arange(0, n - blk + 1, hop)
    z = ((c[:, starts + blk] - c[:, starts]) / blk).sum(axis=0)
    lk = -0.691 + 10 * np.log10(np.maximum(z, 1e-20))
    z1 = z[lk > -70]
    if z1.size == 0:
        return -70.0
    rel = -0.691 + 10 * np.log10(z1.mean()) - 10
    z2 = z[lk > rel]
    return float(-0.691 + 10 * np.log10(max(z2.mean(), 1e-20)))


def true_peak_db(x):
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    up = signal.resample_poly(x, 4, 1, axis=-1)
    return float(db(np.max(np.abs(up))))


def _tp_env(x):
    """Per-sample true-peak envelope (max of |x| over 4x oversampled points)."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    up = signal.resample_poly(x, 4, 1, axis=-1)
    n = x.shape[1]
    a = np.abs(up[:, : 4 * n]).reshape(x.shape[0], n, 4).max(axis=2)
    return a.max(axis=0)


# ----------------------------------------------------------------- dynamics

def compress(x, thresh_db=-18.0, ratio=2.0, attack=0.03, release=0.35, knee=6.0, rms_ms=30):
    """Feed-forward glue compressor on the stereo-linked RMS level."""
    x = np.asarray(x, dtype=np.float64)
    lvl = np.sqrt(uniform_filter1d(np.mean(np.atleast_2d(x) ** 2, axis=0), ns(rms_ms / 1000)) + 1e-12)
    ldb = db(lvl)
    over = ldb - thresh_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    att = np.exp(-1 / (attack * SR))
    rel = np.exp(-1 / (release * SR))
    grs = nb.follow(gr, att, rel)
    return x * undb(-grs)


def limit(x, ceiling_db=-2.0, lookahead=0.004, release=0.12):
    """Look-ahead brick-wall limiter driven by the true-peak envelope."""
    x = np.asarray(x, dtype=np.float64)
    ceil = undb(ceiling_db)
    env = _tp_env(x)
    need = np.minimum(1.0, ceil / np.maximum(env, 1e-12))
    la = max(1, ns(lookahead))
    g = minimum_filter1d(need, size=2 * la + 1, mode="nearest")
    g = nb.release_smooth(g, np.exp(-1 / (release * SR)))
    g = uniform_filter1d(g, la, mode="nearest")
    g = np.minimum(g, minimum_filter1d(need, size=2 * la + 1, mode="nearest") * 1.0 + 0)
    y = x * g
    # safety pass for anything the smoothing let through
    env2 = _tp_env(y)
    if env2.max() > ceil:
        need2 = np.minimum(1.0, ceil / np.maximum(env2, 1e-12))
        g2 = minimum_filter1d(need2, size=2 * la + 1, mode="nearest")
        g2 = uniform_filter1d(g2, la, mode="nearest")
        g2 = np.minimum(g2, minimum_filter1d(need2, size=3, mode="nearest"))
        y = y * g2
    return y


def _circ_wrap(fn, x, circular, warm_s=6.0):
    if not circular:
        return fn(x)
    n = x.shape[-1]
    w = min(ns(warm_s), n)
    xx = np.concatenate([x[..., -w:], x, x[..., :w]], axis=-1)
    return fn(xx)[..., w:w + n]


def master(x, target_lufs=-16.0, ceiling_db=-2.0, circular=False, glue=True,
           glue_ratio=1.8, glue_gr_db=2.0, lowcut=28.0, tilt_hs_db=-1.0):
    """Mastering chain: low cut, gentle high-shelf, glue compression, loudness
    normalisation and a true-peak limiter. Iterates until loudness lands."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    x = filt(x, chain(("hp", lowcut, 0.6), ("hs", 9000, 0.7, tilt_hs_db)), circular, warm=2.0)
    x = x - x.mean(axis=-1, keepdims=True)
    if glue:
        # threshold set so the loud parts get about glue_gr_db of reduction
        lvl = np.sqrt(uniform_filter1d(np.mean(x ** 2, axis=0), ns(0.4)) + 1e-12)
        loud = db(np.percentile(lvl, 95))
        thr = loud - glue_gr_db * glue_ratio / max(glue_ratio - 1, 1e-3)
        x = _circ_wrap(lambda s: compress(s, thr, glue_ratio, 0.03, 0.4), x, circular)
    g = target_lufs - lufs(x)
    y = x
    for _ in range(4):
        y = _circ_wrap(lambda s: limit(s * undb(g), ceiling_db), x, circular)
        err = target_lufs - lufs(y)
        if abs(err) < 0.1:
            break
        g += err
    return y


# ----------------------------------------------------------------- I/O

FFMPEG = "ffmpeg"


def write_wav(path, x):
    from scipy.io import wavfile
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    x = np.atleast_2d(np.asarray(x, dtype=np.float32))
    wavfile.write(str(path), SR, x.T if x.shape[0] <= 2 else x)


def encode_mp3(x, path, kbps=128, mono=False):
    x = np.atleast_2d(np.asarray(x, dtype=np.float32))
    if mono and x.shape[0] == 2:
        x = x.mean(axis=0, keepdims=True)
    ch = x.shape[0]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    data = np.ascontiguousarray(x.T).tobytes()
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(SR),
           "-ac", str(ch), "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", f"{kbps}k",
           "-ar", str(SR), "-ac", str(ch), "-map_metadata", "-1", "-id3v2_version", "0",
           "-write_id3v1", "0", str(path)]
    subprocess.run(cmd, input=data, check=True)


def measure_file(path):
    """(integrated LUFS, true peak dBTP) of an encoded file via ffmpeg ebur128."""
    cmd = [FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
           "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    txt = p.stderr
    summ = txt[txt.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summ).group(1).replace("-inf", "-99"))
    m = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summ)
    tp = float(m.group(1).replace("-inf", "-99")) if m else 0.0
    return I, tp


def decode(path):
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(path), "-f", "f32le",
           "-ar", str(SR), "-"]
    p = subprocess.run(cmd, capture_output=True, check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels",
                            "-of", "json", str(path)], capture_output=True, text=True)
    ch = json.loads(probe.stdout)["streams"][0]["channels"]
    return np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, ch).T


def loop_correlation(y, loop_n, tail_n):
    a = y[..., :tail_n].ravel()
    b = y[..., loop_n:loop_n + tail_n].ravel()
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
