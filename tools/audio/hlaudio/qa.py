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


def short_term(x, win=3.0, hop=1.0):
    """Short-term loudness series (LUFS, 3 s windows): the shape of the arc."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    y = M._k_weight(x)
    w, h = int(win * SR), int(hop * SR)
    c = np.concatenate([np.zeros((y.shape[0], 1)), np.cumsum(y ** 2, axis=1)], axis=1)
    starts = np.arange(0, y.shape[1] - w + 1, h)
    z = ((c[:, starts + w] - c[:, starts]) / w).sum(axis=0)
    return -0.691 + 10 * np.log10(np.maximum(z, 1e-20))


def arc_summary(x):
    st = short_term(x)
    return dict(st_min=round(float(st.min()), 1), st_p10=round(float(np.percentile(st, 10)), 1),
                st_p95=round(float(np.percentile(st, 95)), 1), st_max=round(float(st.max()), 1),
                lra=round(float(np.percentile(st, 95) - np.percentile(st, 10)), 1))


def click_scan(x, thresh=6.0, frame=0.004):
    """Find click-like events: frames whose high-passed (second difference)
    energy jumps far above the local median. Returns [(time_s, ratio)]."""
    from scipy.ndimage import median_filter
    m = np.atleast_2d(np.asarray(x, dtype=np.float64)).mean(axis=0)
    d2 = np.diff(m, 2)
    f = int(frame * SR)
    n = len(d2) // f
    e = np.sqrt(np.mean(d2[: n * f].reshape(n, f) ** 2, axis=1) + 1e-20)
    med = median_filter(e, size=int(0.6 / frame), mode="wrap")
    r = e / (med + 1e-12)
    idx = np.nonzero(r > thresh)[0]
    out = []
    for i in idx:
        if not out or i * frame - out[-1][0] > 0.05:
            out.append((round(i * frame, 3), round(float(r[i]), 1)))
    return out


def third_octave(x, lo=63.0, hi=12500.0):
    """Third-octave band levels (dB) of a signal: (centres, levels)."""
    m = np.atleast_2d(np.asarray(x, dtype=np.float64)).mean(axis=0)
    seg = m  # the whole signal (a part may only play late in the loop)
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    cs = lo * 2 ** (np.arange(0, int(np.log2(hi / lo) * 3) + 1) / 3)
    lv = []
    for c in cs:
        k = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        lv.append(10 * np.log10(S[k].sum() + 1e-20))
    return cs, np.array(lv)


def tone_check(x):
    """Brightness check against a gently falling reference: above 4 kHz no
    third-octave band should be louder than the band an octave below it.
    Returns the worst excess in dB (<= 0 passes) and where."""
    cs, lv = third_octave(x)
    worst, at = -99.0, 0.0
    for i, c in enumerate(cs):
        if c >= 4000 and i >= 3:
            ex = lv[i] - lv[i - 3]
            if ex > worst:
                worst, at = ex, c
    return round(float(worst), 1), int(at)


def reed_check(x, lo=1000.0, hi=4000.0, win=0.12, hop=0.04):
    """Listen-proxy for a reedy, harmonica/square-like tone: in each clearly
    pitched frame (YIN), compare the energy of the odd harmonics (3, 5, 7 ...)
    with the even ones (2, 4, 6 ...) inside lo..hi Hz. A clarinet or a square
    wave reads about +8 dB or more; harp, piano, mallets and glass sit near
    or below 0. Returns (median, worst) odd-minus-even dB over pitched,
    loud frames (None when nothing is clearly pitched)."""
    from .sampler import _yin
    m = np.atleast_2d(np.asarray(x, dtype=np.float64)).mean(axis=0)
    w, h = int(win * SR), int(hop * SR)
    if len(m) < 2 * w:
        return None
    rms = np.array([np.sqrt(np.mean(m[i:i + w] ** 2)) for i in range(0, len(m) - 2 * w, h)])
    n_fft = 1 << 15
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    vals = []
    for j, i in enumerate(range(0, len(m) - 2 * w, h)):
        if rms[j] < rms.max() * 0.2:
            continue
        seg = m[i:i + 2 * w]
        f0, ap = _yin(seg, 60.0, 2000.0)
        if ap > 0.2 or f0 <= 0:
            continue
        S = np.abs(np.fft.rfft(seg[:w] * np.hanning(w), n_fft)) ** 2
        odd = even = 0.0
        for k in range(2, 60):
            fk = k * f0
            if fk < lo:
                continue
            if fk > hi:
                break
            sel = (f > fk * 0.985) & (f < fk * 1.015)
            e = float(S[sel].max()) if sel.any() else 0.0
            if k % 2:
                odd += e
            else:
                even += e
        if odd > 0 and even > 0:
            vals.append(10 * np.log10(odd / even))
    if not vals:
        return None
    return round(float(np.median(vals)), 1), round(float(np.max(vals)), 1)
