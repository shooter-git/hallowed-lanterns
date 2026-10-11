"""Continuous 'line' synthesis shared by sustained instruments (bowed strings,
cello, horn, flute, voices, glass pads).

A monophonic voice is split into phrases (notes that touch or overlap). Each
phrase becomes per-sample curves: frequency (with legato glides, scoops,
delayed vibrato, slow drift and per-note intonation) and amplitude (attack,
legato level changes, bow-change dips, swells, release). Instruments turn
those curves into sound with a band-limited wavetable oscillator and filters.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .core import SR, hz, ns, rng, tvec, smoothstep, smooth_random


@dataclass
class LineStyle:
    attack: float = 0.12        # seconds to full level on a phrase's first note
    release: float = 0.5        # seconds of release after the last note
    glide: float = 0.07         # legato pitch-glide time
    gap: float = 0.06           # notes closer than this are joined legato
    vib_rate: float = 5.3
    vib_depth: float = 12.0     # cents
    vib_delay: float = 0.3
    vib_ramp: float = 0.5
    vib_amp: float = 0.0        # amplitude vibrato (fraction)
    drift: float = 3.0          # slow pitch wander, cents
    intonation: float = 0.0     # per-note random offset, cents
    scoop: float = 0.0          # cents below at onset (horn/voice)
    scoop_time: float = 0.08
    dip: float = 0.0            # amplitude dip at legato note changes (fraction)
    swell: float = 0.0          # crescendo-decrescendo on long notes (fraction)
    vel_curve: float = 1.4      # level = vel ** vel_curve
    min_note_attack: float = 0.03
    detune: float = 0.0         # fixed offset for this player (cents)


def phrases(notes, gap):
    notes = sorted(notes, key=lambda n: n.t)
    out, cur = [], []
    for n in notes:
        if cur and n.t - (cur[-1].t + cur[-1].d) > gap:
            out.append(cur)
            cur = []
        cur.append(n)
    if cur:
        out.append(cur)
    return out


CTRL = 32  # control-rate decimation for pitch/amplitude curves


def curves(ph, st: LineStyle, seed=0):
    """-> (start_seconds, f_hz array, amp array, onset_flags array).
    Curves are computed at a control rate (SR/32) and interpolated to audio
    rate; every per-note shape touches only its own samples."""
    r = rng("line", seed, round(ph[0].t * 1000))
    t0 = ph[0].t - 0.02
    end = max(n.t + n.d for n in ph) + st.release * 1.6
    n = ns(end - t0)
    K = CTRL
    crate = SR / K
    nc = n // K + 2
    t = t0 + np.arange(nc) / crate

    def idx(tt):
        return int(min(max(round((tt - t0) * crate), 0), nc))

    NK = len(ph)
    starts = [idx(nt.t) for nt in ph]
    bounds = [0] + starts[1:] + [nc]
    tgt = [nt.p + (r.normal(0, st.intonation) / 100 if st.intonation else 0.0) for nt in ph]
    lv = [nt.v ** st.vel_curve for nt in ph]
    semis = np.empty(nc)
    lvl = np.empty(nc)
    for k in range(NK):
        semis[bounds[k]:bounds[k + 1]] = tgt[k]
        lvl[bounds[k]:bounds[k + 1]] = lv[k]
    for k in range(1, NK):
        d = tgt[k] - tgt[k - 1]
        if d:
            g = st.glide * (1 + 0.25 * min(abs(d), 12) / 12)
            a, b = idx(ph[k].t - g * 0.5), idx(ph[k].t + g * 0.5)
            if b > a:
                u = smoothstep((t[a:b] - (ph[k].t - g * 0.5)) / g)
                semis[a:b] = tgt[k - 1] + d * u
        dl = lv[k] - lv[k - 1]
        if dl:
            g = st.glide * 1.2
            a, b = idx(ph[k].t - g * 0.5), idx(ph[k].t + g * 0.5)
            if b > a:
                u = smoothstep((t[a:b] - (ph[k].t - g * 0.5)) / g)
                lvl[a:b] = lv[k - 1] + dl * u
    if st.scoop:
        for k, nt in enumerate(ph):
            if k == 0 or nt.x.get("scoop"):
                a, b = idx(nt.t - 0.02), idx(nt.t + 7 * st.scoop_time)
                tau = np.maximum(t[a:b] - nt.t, 0)
                semis[a:b] -= st.scoop / 100 * np.exp(-tau / st.scoop_time)
    first = ph[0]
    att_t = max(st.attack * (1.25 - 0.5 * first.v), st.min_note_attack)
    att_t = first.x.get("attack", att_t)
    amp = lvl
    b = idx(first.t + att_t)
    amp[:b] *= smoothstep((t[:b] - first.t) / att_t) ** 0.8
    last_end = max(nt.t + nt.d for nt in ph)
    rel_time = ph[-1].x.get("release", st.release)
    a = idx(last_end)
    amp[a:] *= np.exp(-5.0 * (t[a:] - last_end) / max(rel_time, 1e-3))
    vib_env = np.zeros(nc)
    for k, nt in enumerate(ph):
        if k > 0 and st.dip and not nt.x.get("slur"):
            a, b = idx(nt.t - 0.15), idx(nt.t + 0.15)
            amp[a:b] *= 1 - st.dip * np.exp(-((t[a:b] - nt.t) / 0.05) ** 2)
        if st.swell and nt.d > 1.2:
            a, b = idx(nt.t), idx(nt.t + nt.d)
            u = np.clip((t[a:b] - nt.t) / nt.d, 0, 1)
            amp[a:b] *= 1 + st.swell * (np.sin(np.pi * u) ** 1.5 - 0.3)
        a, b = starts[k], (starts[k + 1] if k + 1 < NK else nc)
        base = 0.0 if k == 0 else 0.35
        tau = t[a:b] - nt.t
        vib_env[a:b] = base + (1 - base) * smoothstep((tau - st.vib_delay) / st.vib_ramp)
    amp[: idx(first.t - 0.005)] = 0
    rate = st.vib_rate * (1 + 0.06 * smooth_random(nc, r, 0.7, sr=crate) * 2)
    vph = 2 * np.pi * np.cumsum(rate) / crate + r.uniform(0, 2 * np.pi)
    vib = np.sin(vph)
    cents = st.vib_depth * vib_env * vib + st.detune
    if st.drift:
        cents += st.drift * smooth_random(nc, r, 0.4, sr=crate) * 2
    semis += cents / 100
    if st.vib_amp:
        amp *= 1 + st.vib_amp * vib_env * np.sin(vph + 0.6)
    fc = hz(semis)
    pos = np.arange(n, dtype=np.float64) / K
    xc = np.arange(nc, dtype=np.float64)
    f = np.interp(pos, xc, fc)
    amp_a = np.interp(pos, xc, np.maximum(amp, 0))
    onset = np.zeros(n)
    for nt in ph:
        i0 = int(round((nt.t - t0) * SR))
        if 0 <= i0 < n:
            onset[i0] = 1
    return t0, f, amp_a, onset


# ----------------------------------------------------------------- oscillator

_TABLES: dict = {}


def harmonic_table(amps, size=4096):
    key = (tuple(np.round(amps, 6)), size)
    if key not in _TABLES:
        k = np.arange(1, len(amps) + 1)
        ph = np.arange(size) / size
        tab = np.zeros(size)
        for kk, a in zip(k, amps):
            if a:
                tab += a * np.sin(2 * np.pi * kk * ph)
        _TABLES[key] = np.concatenate([tab, tab[:1]])
        if len(_TABLES) > 400:
            _TABLES.clear()
    return _TABLES[key]


def wt_osc(f, amps_fn, fmax=None, ceiling=9000.0, phase0=0.0, size=4096):
    """Band-limited wavetable oscillator following frequency curve f (Hz).
    amps_fn(k) -> amplitude of harmonic k (k = 1..K)."""
    fmax = float(np.max(f)) if fmax is None else fmax
    K = max(1, int(min(ceiling, 0.45 * SR) / max(fmax, 1.0)))
    K = min(K, size // 2 - 1)
    amps = np.array([amps_fn(k) for k in range(1, K + 1)], dtype=float)
    tab = harmonic_table(amps, size)
    ph = (np.cumsum(f) / SR + phase0) % 1.0
    pos = ph * size
    i = pos.astype(np.int64)
    fr = pos - i
    return tab[i] * (1 - fr) + tab[i + 1] * fr


def saw_amps(k):
    return 1.0 / k


def soft_saw_amps(k):
    return 1.0 / k ** 1.15


def flute_amps(k):
    return [1.0, 0.22, 0.09, 0.045, 0.02, 0.01][k - 1] if k <= 6 else 0.0


def sine_amps(k):
    return 1.0 if k == 1 else 0.0
