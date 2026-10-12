"""The magical well and the giant flytrap, made from real recordings: CC0 foley by Joseph Sardin
(BigSoundBank), fetched into .cache/recorded/ the first time.

- fly-buzz-1..4: bursts of a big fly's buzz (the one the flytrap is after), cut where it flies
  freely, not where it bumps against the glass.
- flytrap-snap-1..2: a stick of celery snapped, doubled a fifth lower for the weight of a plant
  this size, over a soft low thud.
- well-coin-1..3: a coin rings off the stone rim, falls, and a drop meets the water far below;
  the shaft answers with its flutter and a long dark echo.

And the flytrap's life around the snap, from the same recordings (and his wind and mud):
- fly-buzz-trapped-1..3: the fly shut inside, furious and muffled: the stretches where it bangs
  against the glass, in bursts with stops, as if through thick leaves.
- flytrap-stir-1..3: a trigger hair touched: a tiny fibrous tick and the faintest creak.
- flytrap-lunge-1..2: the great head swinging past you: a rush of air, a gust through leaves,
  and the stem's fibres creaking with the strain.
- flytrap-digest-1..3: one slow squeeze: a low, wet squelch that swells and eases.
- flytrap-reopen-1..2: the lobes prising slowly apart: a long, stretching, fibrous creak that
  catches and stutters.
"""
import re

import numpy as np
from scipy.signal import fftconvolve, resample_poly

from hlaudio.core import SR, ns, rng
from hlaudio.effects import chain, filt
from hlaudio.piece import OUT, finish_sfx, update_manifest
from hlaudio.recordings import WIND, declick, entry, lock_cc0, original

FLY = ("0759", "Fly and glass", "https://bigsoundbank.com/fly-and-glass-s0759.html")
SNAPS = [("1408", "Bones cracking #2", "https://bigsoundbank.com/bones-cracking-2-s1408.html"),
         ("1409", "Bones cracking #3", "https://bigsoundbank.com/bones-cracking-3-s1409.html")]
COIN = ("0339", "Coin in cup #1", "https://bigsoundbank.com/coin-in-cup-1-s0339.html")
DROPS = ("1384", "Drops of water #1", "https://bigsoundbank.com/drops-of-water-1-s1384.html")
MUD = ("0495", "Steps in the mud", "https://bigsoundbank.com/steps-in-the-mud-s0495.html")
GROUPS = ("fly-buzz", "flytrap-snap", "well-coin", "fly-buzz-trapped", "flytrap-stir", "flytrap-lunge",
          "flytrap-digest", "flytrap-reopen")


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


def slower(x, k):
    """Slower and lower by k (the fibres of a plant this size)."""
    return resample_poly(x, int(round(100 * k)), 100)


def creak(x):
    """The celery's creak before it cracks: its fibres giving. (Only "Bones cracking #3" creaks
    first; #2 just clicks once and cracks.)"""
    return x[onset(x): int(np.argmax(np.abs(x))) - ns(0.008)]


def fly_trapped(x, i):
    """The fly banging about inside: stretches with knocks in them, chopped into bursts with
    stops, a little lower, and heard through the leaf (a dark, boxy chamber)."""
    r = rng("trapped", i)
    db, hop = level(x, 0.05)
    sharp, _ = level(filt(x, chain(("hp", 2500, 0.7))), 0.005)
    jumps = [np.max(np.diff(sharp[k * 10:(k + 30) * 10])) for k in range(0, len(db) - 30, 5)]
    order = np.argsort(jumps)[::-1]
    at = int(order[i * 3]) * 5 * hop
    seg = slower(x[at: at + ns(2.4)], 1.12)
    y = np.zeros(ns(r.uniform(1.6, 2.4)))
    t = 0.0
    while t < len(y) / SR - 0.15:
        d = r.uniform(0.12, 0.45)
        a, n = ns(t), ns(d)
        piece = seg[a: a + n]
        y[a: a + len(piece)] += fade(piece, 0.012, 0.04) * r.uniform(0.6, 1.0)
        t += d + r.uniform(0.04, 0.22)
    y = filt(y, chain(("lp", 900, 0.7), ("lp", 1400, 0.7)))
    box = filt(y, chain(("bp", 340, 3.0))) + 0.6 * filt(y, chain(("bp", 610, 4.0)))
    return fade(filt(y + 1.4 * box, chain(("hp", 90, 0.7))), 0.02, 0.2)


def stir(cracks, i):
    """A touched trigger hair: a tiny tick and the faintest creak, both from the celery."""
    x = cracks[1]
    c = slower(creak(x)[ns(0.03 * i):], 1.2 + 0.15 * i)[: ns(0.35)]
    c = c / (np.max(np.abs(c)) + 1e-9)
    hit = int(np.argmax(np.abs(x)))
    tick = filt(x[hit - ns(0.002): hit + ns(0.018)], chain(("lp", 3500, 0.7)))
    tick = tick / (np.max(np.abs(tick)) + 1e-9)
    y = np.zeros(ns(0.5))
    y[: len(c)] += 0.45 * fade(c, 0.03, 0.1)
    y[ns(0.04): ns(0.04) + len(tick)] += fade(tick, 0.001, 0.008)
    return fade(filt(y, chain(("hp", 160, 0.7), ("lp", 5000, 0.7))), 0.001, 0.1)


def lunge(air, leaves, cracks, i):
    """The head whipping past: air rushing through a sweeping band, a gust through leaves, and
    the stem creaking under the strain."""
    r = rng("lunge", i)
    n = ns(0.75)
    t = np.arange(n) / SR
    u = t / t[-1]
    a = ns(r.uniform(5, 60))
    w = air[a: a + n]
    fc = 350 + 1700 * np.sin(np.pi * np.clip(u * 1.2, 0, 1)) ** 2
    from hlaudio import nb
    rush = nb.svf(w, fc, 1.1, 1)
    env = np.sin(np.pi * np.clip(u / 0.85, 0, 1)) ** 1.5
    rush = rush / (np.max(np.abs(rush * env)) + 1e-9) * env
    b = ns(r.uniform(5, 160))
    lv = filt(leaves[b: b + n], chain(("hp", 1200, 0.7)))
    lv = lv / (np.max(np.abs(lv)) + 1e-9) * np.sin(np.pi * np.clip((u - 0.1) / 0.8, 0, 1)) ** 2
    c = slower(creak(cracks[1])[ns(0.04 * i):], 1.8 + 0.2 * i)
    y = 0.8 * rush + 0.35 * lv
    at = ns(0.08)
    c = c[: n - at]
    y[at: at + len(c)] += 0.5 * fade(filt(c, chain(("lp", 2600, 0.7))), 0.02, 0.08)
    return fade(filt(y, chain(("hp", 70, 0.7))), 0.01, 0.12)


def digest(mud, i):
    """One squeeze: the wettest moment of a step in the mud, slowed into a low squelch that swells
    and eases."""
    r = rng("digest", i)
    db, hop = level(mud, 0.02)
    loud = np.argsort(db)[::-1]
    picks = []
    for k in loud:
        if all(abs(int(k) - p) > 40 for p in picks):
            picks.append(int(k))
        if len(picks) > i:
            break
    at = max(0, picks[i] * hop - ns(0.15))
    seg = slower(mud[at: at + ns(0.9)], r.uniform(1.6, 1.9))
    n = min(len(seg), ns(r.uniform(1.6, 2.3)))
    seg = seg[:n]
    u = np.arange(n) / n
    env = np.sin(np.pi * u) ** 1.2
    y = filt(seg, chain(("lp", 1100, 0.7), ("lp", 1600, 0.7), ("hp", 60, 0.7))) * env
    return fade(y, 0.08, 0.3)


def reopen(cracks, leaves, i):
    """The lobes prising apart: the celery's creak slowed right down, in catches and stutters,
    over a faint stir of leaves."""
    r = rng("reopen", i)
    y = np.zeros(ns(5.2))
    t = 0.2
    k = 0
    while t < 4.6:
        c = creak(cracks[1])
        c = slower(c[ns(r.uniform(0, 0.06)):], r.uniform(2.6, 3.4))
        c = fade(filt(c, chain(("lp", 1800, 0.7), ("hp", 90, 0.7))), 0.05, 0.12)
        a = ns(t)
        c = c[: len(y) - a]
        y[a: a + len(c)] += c * r.uniform(0.6, 1.0) * np.sin(np.pi * min(1.0, t / 5.0)) ** 0.5
        t += len(c) / SR * r.uniform(0.55, 0.95) + (r.uniform(0.15, 0.4) if r.uniform() < 0.4 else 0)
        k += 1
    b = ns(r.uniform(5, 110))
    lv = filt(leaves[b: b + len(y)], chain(("hp", 900, 0.7), ("lp", 5000, 0.7)))
    lv = lv / (np.max(np.abs(lv)) + 1e-9)
    y = y / (np.max(np.abs(y)) + 1e-9) + 0.12 * lv * np.sin(np.pi * np.arange(len(y)) / len(y))
    return fade(y, 0.2, 0.6)


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

    cracks = [original(sid) for sid, _, _ in SNAPS]
    crack_pages = [page for _, _, page in SNAPS]
    air = declick(original("0595")[None])[0]
    leaves = declick(original("0907")[None])[0]
    mud = original(MUD[0])
    fly = original(FLY[0])
    for i in range(3):
        name = f"fly-buzz-trapped-{i + 1}"
        finish_sfx("fly-buzz-trapped", name, fly_trapped(fly, i), -10.0, max_s=2.6, kbps=96)
        entries.append(entry(name, FLY[2], f"{FLY[1]} (the fly against the glass, muffled, in bursts)"))
    for i in range(3):
        name = f"flytrap-stir-{i + 1}"
        finish_sfx("flytrap-stir", name, stir(cracks, i), -14.0, max_s=0.5, kbps=96)
        made = entry(name, crack_pages[1], "Bones cracking #3 (a celery's tick and creak, slowed)")
        entries.append(made)
    for i in range(2):
        name = f"flytrap-lunge-{i + 1}"
        finish_sfx("flytrap-lunge", name, lunge(air, leaves, cracks, i), -6.0, max_s=0.8, kbps=128)
        made = entry(name, WIND["0595"][1], "Wind, Wind in shrub and Bones cracking (a rush of air, leaves and a creak)")
        made["also"] = [WIND["0907"][1], crack_pages[1]]
        entries.append(made)
    for i in range(3):
        name = f"flytrap-digest-{i + 1}"
        finish_sfx("flytrap-digest", name, digest(mud, i), -12.0, max_s=2.4, kbps=96)
        entries.append(entry(name, MUD[2], f"{MUD[1]} (a squelch, slowed)"))
    for i in range(2):
        name = f"flytrap-reopen-{i + 1}"
        finish_sfx("flytrap-reopen", name, reopen(cracks, leaves, i), -12.0, max_s=5.2, kbps=96)
        made = entry(name, crack_pages[1], "Bones cracking #3 and Wind in shrub (a creak slowed right down, with leaves)")
        made["also"] = WIND["0907"][1]
        entries.append(made)

    lock_cc0(entries, GROUPS)


if __name__ == "__main__":
    render()
