"""Quality checks we can do without ears: spectrogram pictures, loudness,
peaks, DC, high-frequency share, clipping and loop seams."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .core import SR, db, name
from . import master as M


def stats(x):
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    mono = x.mean(axis=0)
    spec = np.abs(np.fft.rfft(mono * np.hanning(mono.size))) ** 2 if mono.size < 2 ** 24 else None
    if spec is None:
        seg = mono[: 2 ** 23]
        spec = np.abs(np.fft.rfft(seg * np.hanning(seg.size))) ** 2
    f = np.fft.rfftfreq((spec.size - 1) * 2, 1 / SR)
    tot = spec.sum() + 1e-20
    return dict(
        lufs=round(M.lufs(x), 2),
        tp=round(M.true_peak_db(x), 2),
        peak=round(float(db(np.max(np.abs(x)))), 2),
        dc=float(np.max(np.abs(x.mean(axis=1)))),
        hf8k_db=round(float(10 * np.log10(spec[f > 8000].sum() / tot + 1e-20)), 1),
        hf4k_db=round(float(10 * np.log10(spec[f > 4000].sum() / tot + 1e-20)), 1),
        low100_db=round(float(10 * np.log10(spec[f < 100].sum() / tot + 1e-20)), 1),
        clipped=int(np.sum(np.abs(x) >= 0.999)),
        seconds=round(x.shape[1] / SR, 2),
    )


def spectrogram_png(x, path, title="", fmax=11000, nfft=4096, hop=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    mono = x.mean(axis=0)
    hop = hop or max(512, mono.size // 1600)
    win = np.hanning(nfft)
    nfr = max(1, (mono.size - nfft) // hop)
    idx = np.arange(nfft)[None, :] + hop * np.arange(nfr)[:, None]
    S = np.abs(np.fft.rfft(mono[idx] * win, axis=1)).T
    f = np.fft.rfftfreq(nfft, 1 / SR)
    keep = f <= fmax
    Sd = 20 * np.log10(S[keep] + 1e-9)
    Sd -= Sd.max()
    t = np.arange(nfr) * hop / SR
    fig, ax = plt.subplots(2, 1, figsize=(14, 7), gridspec_kw=dict(height_ratios=[4, 1]), sharex=True)
    ax[0].imshow(np.clip(Sd, -90, 0), aspect="auto", origin="lower", extent=[0, t[-1] if nfr > 1 else 1, 0, fmax],
                 cmap="magma")
    ax[0].axhline(8000, color="c", lw=0.5)
    ax[0].set_ylabel("Hz")
    ax[0].set_title(title)
    rms = np.sqrt(np.mean(mono[idx] ** 2, axis=1) + 1e-12)
    ax[1].plot(t, 20 * np.log10(rms), lw=0.6)
    ax[1].set_ylim(-70, 0)
    ax[1].set_ylabel("dB rms")
    ax[1].set_xlabel("s")
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=70)
    plt.close(fig)


def estimate_pitch(x, t0, dur=0.25):
    """Strongest spectral peak (Hz, note name, cents off) in a window."""
    x = np.atleast_2d(x).mean(axis=0)
    a = int(t0 * SR)
    seg = x[a:a + int(dur * SR)]
    n = 1 << 16
    S = np.abs(np.fft.rfft(seg * np.hanning(seg.size), n))
    f = np.fft.rfftfreq(n, 1 / SR)
    S[f < 60] = 0
    k = int(np.argmax(S))
    if 0 < k < S.size - 1:
        al, be, ga = np.log(S[k - 1] + 1e-12), np.log(S[k] + 1e-12), np.log(S[k + 1] + 1e-12)
        k = k + 0.5 * (al - ga) / (al - 2 * be + ga)
    fr = k * SR / n
    midi = 69 + 12 * np.log2(fr / 440)
    return fr, name(midi), round(100 * (midi - round(midi)), 1)
