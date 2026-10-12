"""Lantern and candle sounds: pumpkin-flare-1..3 (a warm wooden knock, a
candle whoosh and a small chime), lantern-swing-1..2 (soft creak and tassel
swish), lantern-light (soft magical ignite), candle-light-1..3 (a real match
struck and catching: Joseph Sardin's "Match #1" and "Match #2", BigSoundBank,
CC0)."""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec, Track
from hlaudio.effects import chain, filt, reverb
from hlaudio import mallets as ML, perc as PC, nature as NA, nb
from hlaudio.piece import OUT, finish_sfx, update_manifest
from hlaudio.recordings import entry, lock_cc0, original


def place(n_s, *parts):
    """Sum (start_s, signal, gain) parts into one mono buffer of n_s seconds."""
    out = np.zeros(ns(n_s))
    for (t, x, g) in parts:
        i = ns(t)
        k = min(len(x), out.size - i)
        if k > 0:
            out[i:i + k] += x[:k] * g
    return out


def with_room(y, space="room", amt=0.2, tail=0.6):
    wet = reverb(y, space)
    n = y.shape[-1] + ns(tail)
    dry = np.pad(np.vstack([y, y]), ((0, 0), (0, n - y.shape[-1])))
    return dry + amt * wet[:, :n]


def whoosh(dur=0.5, f0=350, f1=1600, seed=0, low=0.5):
    """Flame flare: a breathy noise burst whose colour rises, with a soft low whump."""
    r = rng("whoosh", seed)
    n = ns(dur)
    t = tvec(n)
    env = (1 - np.exp(-t / 0.025)) * np.exp(-t / (dur * 0.35))
    fc = f0 * (f1 / f0) ** np.clip(t / (dur * 0.4), 0, 1)
    y = nb.svf(r.standard_normal(n), fc, 2.0, 1) * env
    y = filt(y, chain(("lp", 2800, 0.7), ("lp", 3500, 0.7)))
    y += low * filt(r.standard_normal(n), chain(("lp", 160, 0.7), ("lp", 200, 0.7))) * env * 3
    # tiny crackle of the wick
    hits = (r.uniform(size=n) < 0.003 * np.exp(-t / 0.2))
    y += filt(hits * r.uniform(-1, 1, n), chain(("bp", 2500, 2.0), ("lp", 4500, 0.7))) * 0.5
    k = min(n, ns(0.05))
    y[-k:] *= np.linspace(1, 0, k)
    return y


def pumpkin_flare(i):
    r = rng("flare", i)
    knock = PC.knock(r.uniform(150, 200), 0.9, seed=i, hollow=1.6)
    wh = whoosh(0.7, 300, 1400 + 200 * i, seed=i)
    chime = ML.celesta([86, 90, 93][i], 0.55, dur=0.6, seed=i)  # D6, F#6, A6
    y = place(1.6, (0.0, knock, 1.0), (0.02, wh, 0.22), (0.09, chime, 0.35))
    return with_room(y, "room", 0.18)


def lantern_swing(i):
    r = rng("swing", i)
    cr = NA.creak(seed=10 + i, dur=0.55, rate=(18, 34), res=(520, 900, 1400))
    cr = filt(cr, chain(("hp", 300, 0.7), ("lp", 2800, 0.7), ("lp", 3500, 0.7)))
    sw = []
    for k, (t, a) in enumerate([(0.08, 1.0), (0.48, 0.6), (0.86, 0.35)]):
        L = ns(0.28)
        u = np.linspace(0, 1, L)
        env = np.sin(np.pi * u ** 0.7) ** 2
        s = nb.svf(r.standard_normal(L), 1500 + 1500 * u if k % 2 == 0 else 3000 - 1500 * u, 2.0, 1) * env
        s = filt(s, chain(("lp", 4000, 0.7), ("lp", 5000, 0.7)))
        sw.append((t, s, 0.18 * a))
    y = place(1.4, (0.0, cr, 0.6 / (np.max(np.abs(cr)) + 1e-9)), *sw)
    return with_room(y, "forest", 0.15)


def lantern_light():
    r = rng("light")
    wh = whoosh(0.6, 250, 1200, seed=5, low=0.35)
    notes = [(0.12, 81), (0.2, 86), (0.28, 90)]  # A5 D6 F#6, rising
    parts = [(0.0, wh, 0.25)] + [(t, ML.celesta(p, 0.5, dur=0.8, seed=k), 0.3) for k, (t, p) in enumerate(notes)]
    n = ns(1.6)
    t = tvec(n)
    glow = np.sin(2 * np.pi * 440 * t) * (1 - np.exp(-t / 0.15)) * np.exp(-t / 0.5) * 0.12
    parts.append((0.0, glow, 1.0))
    y = place(1.8, *parts)
    return with_room(y, "hall", 0.25, 1.0)


# The ofrenda's candles are lit with a real match: (recording, page, title, where a strike begins).
MATCHES = [
    ("0004", "https://bigsoundbank.com/match-s0004.html", "Match #1", 0.2),
    ("0004", "https://bigsoundbank.com/match-s0004.html", "Match #1", 24.3),
    ("1271", "https://bigsoundbank.com/match-2-s1271.html", "Match #2", 4.15),
]


def candle_light(i):
    """A match struck, catching and burning a moment, a little way off in a quiet room."""
    sid, _, _, at = MATCHES[i]
    x = original(sid)
    seg = x[ns(at): ns(at) + ns(1.8)]
    # start right at the strike (the tap lights it), keeping a breath before it
    lvl = np.convolve(seg ** 2, np.ones(ns(0.005)) / ns(0.005), "same")
    start = max(0, int(np.argmax(lvl > lvl.max() * 1e-3)) - ns(0.01))
    y = filt(seg[start: start + ns(1.5)], chain(("hp", 120, 0.7), ("lp", 9000, 0.7)))
    k = ns(0.45)
    y[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return with_room(y, "room", 0.16, 0.5)


def render():
    for i in range(3):
        finish_sfx("pumpkin-flare", f"pumpkin-flare-{i + 1}", pumpkin_flare(i), -3.0)
    for i in range(2):
        finish_sfx("lantern-swing", f"lantern-swing-{i + 1}", lantern_swing(i), -5.0, max_s=1.2)
    finish_sfx("lantern-light", "lantern-light", lantern_light(), -4.0, max_s=1.4)
    old = OUT / "sfx" / "candle-light.mp3"  # the synthesised one this replaced
    if old.exists():
        old.unlink()
    update_manifest("sfx", "candle-light", [])
    entries = []
    for i, (_, page, title, _) in enumerate(MATCHES):
        name = f"candle-light-{i + 1}"
        finish_sfx("candle-light", name, candle_light(i), -4.0, max_s=2.0, kbps=128)
        entries.append(entry(name, page, f"{title} (a match struck and catching)"))
    lock_cc0(entries, ("candle-light",))


if __name__ == "__main__":
    render()
