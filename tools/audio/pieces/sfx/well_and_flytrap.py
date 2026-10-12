"""The magical well and the giant flytrap, made from real recordings: CC0 foley by Joseph Sardin
(BigSoundBank), fetched into .cache/recorded/ the first time.

- fly-buzz-1..4: bursts of a big fly's buzz (the one the flytrap is after), cut where it flies
  freely, not where it bumps against the glass.
- flytrap-snap-1..2: a stick of celery snapped, doubled a fifth lower for the weight of a plant
  this size, over a soft low thud.
- well-coin-1..3: a coin rings off the stone rim, falls, and a drop meets the water far below;
  the shaft answers with its flutter and a long dark echo.
"""
import re

import numpy as np
from scipy.signal import fftconvolve, resample_poly

from hlaudio.core import SR, ns, rng
from hlaudio.effects import chain, filt
from hlaudio.piece import OUT, finish_sfx, update_manifest
from hlaudio.recordings import entry, lock_cc0, original

FLY = ("0759", "Fly and glass", "https://bigsoundbank.com/fly-and-glass-s0759.html")
SNAPS = [("1408", "Bones cracking #2", "https://bigsoundbank.com/bones-cracking-2-s1408.html"),
         ("1409", "Bones cracking #3", "https://bigsoundbank.com/bones-cracking-3-s1409.html")]
COIN = ("0339", "Coin in cup #1", "https://bigsoundbank.com/coin-in-cup-1-s0339.html")
DROPS = ("1384", "Drops of water #1", "https://bigsoundbank.com/drops-of-water-1-s1384.html")
GROUPS = ("fly-buzz", "flytrap-snap", "well-coin")


def level(x, win=0.02):
    """Level in dB over `win`-second frames."""
    hop = ns(win)
    frames = len(x) // hop
    return 20 * np.log10(np.sqrt(np.mean(x[: frames * hop].reshape(frames, hop) ** 2, axis=1)) + 1e-9), hop


def onset(x):
    """Where the sound starts: the first frame within 30 dB of its loudest."""
    db, hop = level(x, 0.002)
    return max(0, int(np.argmax(db > db.max() - 30)) * hop - ns(0.003))


def fade(y, a, b):
    y = y.copy()
    ka, kb = min(ns(a), len(y) // 2), min(ns(b), len(y) // 2)
    y[:ka] *= np.sin(np.linspace(0, np.pi / 2, ka)) ** 2
    y[-kb:] *= np.cos(np.linspace(0, np.pi / 2, kb)) ** 2
    return y


def fly_bursts(x, n):
    """Stretches where the fly flies freely: a steady, loud buzz with no sharp knocks."""
    db, hop = level(x, 0.05)
    sharp, _ = level(filt(x, chain(("hp", 2500, 0.7))), 0.005)
    middle = np.percentile(db, 50)
    out, used = [], np.zeros(len(db), bool)
    r = rng("fly", 1)
    for _ in range(n * 6):
        length = int(r.uniform(1.6, 2.4) / 0.05)
        best, at = -np.inf, -1
        for i in range(0, len(db) - length, 2):
            if used[i:i + length].any():
                continue
            seg = db[i:i + length]
            knocks = sharp[i * 10:(i + length) * 10]
            jump = np.max(np.diff(knocks)) if len(knocks) > 1 else 0
            score = np.mean(seg) - middle - np.std(seg) - max(0.0, jump - 12) * 2
            # loud enough, and steady: no dropping out mid-burst
            if np.mean(seg) > middle and np.min(seg) > np.mean(seg) - 9 and score > best:
                best, at = score, i
        if at < 0:
            break
        used[max(0, at - 10):at + length + 10] = True
        out.append(x[at * hop:(at + length) * hop])
        if len(out) == n:
            break
    return out


def snap(x):
    s = x[onset(x):][: ns(0.45)]
    low = resample_poly(s, 3, 2)[: ns(0.5)]  # a fifth lower, for the size of it
    t = np.arange(ns(0.5)) / SR
    thud = np.sin(2 * np.pi * 62 * t) * np.exp(-t / 0.09) * (1 - np.exp(-t / 0.004))
    y = np.zeros(ns(0.8))
    y[: len(s)] += 0.8 * s
    y[ns(0.004): ns(0.004) + len(low)] += 0.75 * filt(low, chain(("lp", 2500, 0.7)))
    # the thud lands with the main crack (the celery creaks a little first)
    hit = int(np.argmax(np.abs(s)))
    y[hit: hit + len(thud)] += 0.45 * thud[: len(y) - hit]
    return fade(filt(y, chain(("hp", 40, 0.7))), 0.001, 0.12)


def drops_in(x, n):
    """Single clean drops: an onset with quiet on both sides."""
    db, hop = level(x, 0.004)
    floor = np.percentile(db, 30)
    hits = [i for i in range(3, len(db) - 60) if db[i] > floor + 18 and db[i] - db[i - 3] > 10]
    hits = [h for k, h in enumerate(hits) if k == 0 or h - hits[k - 1] > 25]
    clean = sorted(hits, key=lambda h: np.mean(db[h + 30:h + 60]) + np.mean(db[h - 12:h - 2]))
    return [x[h * hop - ns(0.004): h * hop + ns(0.3)] for h in clean[:n]]


def shaft():
    """A stone well's answer: echoes between the walls every few milliseconds, the water's
    reflection coming back up, and a dense, dark tail."""
    n = ns(2.8)
    ir = np.zeros(n)
    for i, tk in enumerate(np.arange(0, 1.2, 0.0087)):
        ir[ns(tk)] += 0.93 ** i * (1 if i % 2 == 0 else -0.8)
    for k, d in enumerate((0.071, 0.142, 0.213, 0.284)):
        ir[ns(d)] += 0.5 * 0.6 ** k
    t = np.arange(n) / SR
    tail = rng("shaft", 1).standard_normal(n) * np.exp(-t / 0.42)
    ir += 0.3 * filt(tail, chain(("lp", 1600, 0.7)))
    ir = filt(ir, chain(("lp", 3200, 0.7)))
    return ir / np.max(np.abs(ir))


def well(coin, drop, fall):
    clink = fade(coin[onset(coin):][: ns(0.4)], 0.001, 0.15)
    far = filt(drop, chain(("lp", 2400, 0.7), ("hp", 180, 0.7))) * 0.35
    wet = fftconvolve(far, shaft())[: ns(2.8)] * 0.22
    y = np.zeros(ns(0.4 + fall + 3.0))
    y[: len(clink)] += clink
    at = ns(0.4 + fall)
    y[at: at + len(far)] += far
    y[at: at + len(wet)] += wet
    return fade(y, 0.001, 0.6)


def render():
    entries = []
    for group in GROUPS:
        for old in (OUT / "sfx").glob(f"{group}-*.mp3"):
            if re.fullmatch(rf"{re.escape(group)}-\d+\.mp3", old.name):
                old.unlink()
        update_manifest("sfx", group, [])

    sid, title, page = FLY
    for i, b in enumerate(fly_bursts(original(sid), 4)):
        name = f"fly-buzz-{i + 1}"
        finish_sfx("fly-buzz", name, fade(filt(b, chain(("hp", 110, 0.7))), 0.25, 0.45), -9.0, max_s=2.6, kbps=96)
        entries.append(entry(name, page, f"{title} (a burst of the fly's buzz)"))

    for i, (sid, title, page) in enumerate(SNAPS):
        name = f"flytrap-snap-{i + 1}"
        finish_sfx("flytrap-snap", name, snap(original(sid)), -5.0, max_s=0.8, kbps=128)
        entries.append(entry(name, page, f"{title} (a celery snap, doubled lower, with a thud)"))

    coin = original(COIN[0])
    drops = drops_in(original(DROPS[0]), 3)
    for i, d in enumerate(drops):
        name = f"well-coin-{i + 1}"
        finish_sfx("well-coin", name, well(coin, d, 1.0 + 0.25 * i), -5.0, max_s=4.6, kbps=128)
        made = entry(name, COIN[2], f"{COIN[1]} and {DROPS[1]} (a coin down a well, with the shaft's echo)")
        made["also"] = DROPS[2]
        entries.append(made)

    lock_cc0(entries, GROUPS)


if __name__ == "__main__":
    render()
