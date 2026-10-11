"""Voices and pads: formant choir ('ooh'/'aah'), glass pad, whale-song calls
and warm low drones."""
from __future__ import annotations

import numpy as np
from scipy import signal

from . import nb
from .core import SR, hz, ns, rng, tvec, Track, smooth_random, smoothstep
from .effects import chain, filt, bq
from .lines import LineStyle, phrases, curves, wt_osc
from .bowed import split_voices

# (freq Hz, level dB, bandwidth Hz) for five formants, by voice part and vowel
FORMANTS = {
    ("soprano", "a"): [(800, 0, 80), (1150, -6, 90), (2900, -32, 120), (3900, -20, 130), (4950, -50, 140)],
    ("soprano", "o"): [(450, 0, 70), (800, -11, 80), (2830, -22, 100), (3800, -22, 130), (4950, -50, 135)],
    ("soprano", "u"): [(325, 0, 50), (700, -16, 60), (2700, -35, 170), (3800, -40, 180), (4950, -60, 200)],
    ("alto", "a"): [(800, 0, 80), (1150, -4, 90), (2800, -20, 120), (3500, -36, 130), (4950, -60, 140)],
    ("alto", "o"): [(450, 0, 70), (800, -9, 80), (2830, -16, 100), (3500, -28, 130), (4950, -55, 135)],
    ("alto", "u"): [(325, 0, 50), (700, -12, 60), (2530, -30, 170), (3500, -40, 180), (4950, -64, 200)],
    ("tenor", "a"): [(650, 0, 80), (1080, -6, 90), (2650, -7, 120), (2900, -8, 130), (3250, -22, 140)],
    ("tenor", "o"): [(400, 0, 40), (800, -10, 80), (2600, -12, 100), (2800, -12, 120), (3000, -26, 120)],
    ("tenor", "u"): [(350, 0, 40), (600, -20, 60), (2700, -17, 100), (2900, -14, 120), (3300, -26, 120)],
    ("bass", "a"): [(600, 0, 60), (1040, -7, 70), (2250, -9, 110), (2450, -9, 120), (2750, -20, 130)],
    ("bass", "o"): [(400, 0, 40), (750, -11, 80), (2400, -21, 100), (2600, -20, 120), (2900, -40, 120)],
    ("bass", "u"): [(350, 0, 40), (600, -20, 80), (2400, -32, 100), (2675, -28, 120), (2950, -36, 120)],
}

PARTS = {
    "soprano": dict(pan=(-0.6, 0.0), vib=(5.3, 20), bright=1.7),
    "alto": dict(pan=(-0.2, 0.35), vib=(5.1, 18), bright=1.75),
    "tenor": dict(pan=(0.0, 0.5), vib=(5.0, 18), bright=1.8),
    "bass": dict(pan=(0.2, 0.7), vib=(4.8, 15), bright=1.9),
}


def formant_filter(x, part, vowel, circular=False):
    out = np.zeros_like(x, dtype=np.float64)
    for f, gdb, bw in FORMANTS[(part, vowel)]:
        sos = bq("bp", f, q=max(f / bw, 0.5))
        out += filt(x, sos, circular) * 10 ** (gdb / 20)
    return out


def choir(track: Track, notes, part="soprano", singers=8, vowel=("u", "a"), morph=0.25, gain=1.0, seed=0,
          breath=0.02, pan=None, style_over=None):
    """Soft choir. `morph` (0 = first vowel, 1 = second) may be a float or a
    callable of time (seconds) returning 0..1 for slow vowel changes."""
    pp = PARTS[part]
    src = track.like()
    for vi, voice in enumerate(split_voices(notes)):
        for s in range(singers):
            r = rng("choir", part, seed, vi, s)
            st = LineStyle(attack=0.35, release=0.9, glide=0.12, gap=0.08, vib_rate=pp["vib"][0] * r.uniform(0.9, 1.1),
                           vib_depth=pp["vib"][1] * r.uniform(0.6, 1.3), vib_delay=r.uniform(0.25, 0.6), vib_ramp=0.7,
                           vib_amp=0.03, drift=5.0, intonation=6.0, scoop=12, scoop_time=0.12, dip=0.08, swell=0.18,
                           vel_curve=1.3, detune=r.normal(0, 5))
            if style_over:
                for k, v in style_over.items():
                    setattr(st, k, v)
            for pi, ph in enumerate(phrases(voice, st.gap)):
                jit = r.normal(0, 0.03)
                t0, f, amp, onset = curves(ph, st, seed * 131 + vi * 17 + s * 5 + pi)
                n = f.shape[0]
                b = pp["bright"]
                g = wt_osc(f, lambda k: 1.0 / k ** b, ceiling=6000, phase0=r.uniform())
                # jitter/shimmer: tiny random amplitude flutter
                g *= 1 + 0.04 * smooth_random(n, r, 18.0)
                asp = r.standard_normal(n) * breath
                y = amp * (g + asp)
                lo, hi = pan if pan is not None else pp["pan"]
                src.add(t0 + jit, y, gain=gain / np.sqrt(singers) * 0.9, pan=float(r.uniform(lo, hi)))
    v1, v2 = vowel
    A = formant_filter(src.buf, part, v1, src.circular)
    if callable(morph) or morph > 0:
        B = formant_filter(src.buf, part, v2, src.circular)
        if callable(morph):
            mv = np.clip(morph(tvec(src.n)), 0, 1)
        else:
            mv = morph
        out = (1 - mv) * A + mv * B
    else:
        out = A
    out = filt(out, chain(("hp", 90, 0.7), ("lp", 3400, 0.6), ("hs", 2500, 0.7, -3)), src.circular)
    src.buf = (out * 3.5).astype(np.float32)
    track.mix(src)
    return track


def glass_pad(track: Track, notes, gain=1.0, seed=0, pan_spread=0.6, glide=0.6, attack=1.2, release=2.5,
              partials=(1.0, 0.12, 0.05, 0.02), shimmer_partial=0.06, layers=3):
    """Airy glass-harmonica-like pad with slow glides between notes."""
    stem = track.like()
    amps = list(partials)
    for vi, voice in enumerate(split_voices(notes)):
        for L in range(layers):
            r = rng("glass", seed, vi, L)
            st = LineStyle(attack=attack, release=release, glide=glide, gap=0.3, vib_rate=r.uniform(3.5, 4.5),
                           vib_depth=r.uniform(4, 8), vib_delay=0.8, vib_ramp=1.5, drift=4.0, intonation=0,
                           swell=0.2, vel_curve=1.2, detune=(L - (layers - 1) / 2) * 5.0, min_note_attack=0.3)
            for pi, ph in enumerate(phrases(voice, st.gap)):
                t0, f, amp, onset = curves(ph, st, seed * 7 + vi * 3 + L * 101 + pi)
                y = wt_osc(f, lambda k: amps[k - 1] if k <= len(amps) else 0.0, ceiling=8000, phase0=r.uniform())
                if shimmer_partial:
                    y += shimmer_partial * np.sin(2 * np.pi * np.cumsum(f * 2.756) / SR) * (
                        0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * tvec(f.shape[0]) + r.uniform(0, 6)))
                stem.add(t0, amp * y, gain=gain / np.sqrt(layers) * 0.5,
                         pan=float(np.clip((L - (layers - 1) / 2) * pan_spread, -1, 1)))
    track.mix(stem)
    return track


def whale_call(f0=180.0, dur=3.5, contour=None, seed=0, rough=0.25, bright=1.0):
    """One whale-song phrase: a moaning tone with big slow glides.
    contour = [(t_frac, semitones), ...] relative to f0."""
    r = rng("whale", seed)
    n = ns(dur)
    t = tvec(n)
    if contour is None:
        k = r.integers(3, 6)
        contour = [(0.0, r.uniform(-3, 0))] + [(i / k, r.uniform(-5, 7)) for i in range(1, k)] + [(1.0, r.uniform(-8, -2))]
    ts = np.array([c[0] for c in contour]) * dur
    ss = np.array([c[1] for c in contour])
    semi = np.interp(t, ts, ss)
    # smooth the contour
    k = ns(0.15)
    semi = signal.oaconvolve(np.pad(semi, (k, k), mode="edge"), np.hanning(2 * k + 1) / np.sum(np.hanning(2 * k + 1)), "same")[k:-k]
    f = f0 * 2 ** (semi / 12) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t))
    ph = np.cumsum(f) / SR
    y = np.zeros(n)
    for h, a in enumerate([1.0, 0.55 * bright, 0.3 * bright, 0.16 * bright, 0.08 * bright], start=1):
        y += a * np.sin(2 * np.pi * h * ph + r.uniform(0, 1))
    # roughness (the groan), slow amplitude shape
    am = 1 + rough * np.sin(2 * np.pi * r.uniform(18, 30) * t) * smooth_random(n, r, 2.0)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.2 * (1 - np.exp(-t / 0.2))
    y = y * am * env
    return filt(y, chain(("lp", 1600 * bright, 0.7), ("hp", 60, 0.7)))


def drone(track: Track, start, dur, pitches, gain=1.0, seed=0, cutoff=500.0, attack=3.0, release=4.0,
          voices=3, detune=7.0, wobble=0.25, pan_spread=0.5):
    """Warm low drone: detuned soft saws, slow filter breathing."""
    for pi, p in enumerate(pitches):
        for v in range(voices):
            r = rng("drone", seed, pi, v)
            n = ns(dur + release)
            t = tvec(n)
            f = float(hz(p)) * 2 ** ((v - (voices - 1) / 2) * detune / 1200 + 0.002 * smooth_random(n, r, 0.2))
            y = wt_osc(f, lambda k: 1.0 / k ** 1.4, ceiling=4000, phase0=r.uniform())
            fc = cutoff * (1 + wobble * smooth_random(n, r, 0.15) * 2)
            y = nb.svf(y, np.maximum(fc, 80), 0.7, 0)
            env = smoothstep(t / attack) * np.where(t > dur, np.exp(-4 * (t - dur) / release), 1.0)
            track.add(start, y * env, gain=gain * 0.3 / np.sqrt(voices * len(pitches)),
                      pan=float((v - (voices - 1) / 2) * pan_spread / max(1, voices - 1) * 2))
    return track
