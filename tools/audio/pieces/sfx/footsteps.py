"""Footsteps, cut from real recordings: studio foley by Joseph Sardin (BigSoundBank), released
under CC0 (public domain). Gravel for the lanes, dry leaves for the woodland trails, grass, snow,
and steps in very wet mud for the sea floor (the Deep muffles them further).

Each recording is split into single steps at their onsets; the cleanest, most even ones are kept
(a quiet start, a tail that has died away, a level near the recording's typical step), trimmed
and levelled. They stay dry and close-miked: the walk should sound like your own feet.

The originals are fetched into .cache/recorded/ the first time (git ignores them), and every step
made from them is recorded in assets.lock.json as CC0, with its source.
"""
import re

import numpy as np
from scipy.signal import resample_poly

from hlaudio.core import SR, ns
from hlaudio.effects import chain, filt
from hlaudio.piece import OUT, finish_sfx, update_manifest
from hlaudio.recordings import entry, lock_cc0, original

# group: (BigSoundBank id, title, page, how many steps, longest step (s), peak dB, extra treatment)
# Steps come at least GAP s apart (a quicker walk in the snow).
GAP = {"step-snow": 0.3}
SOURCES = {
    "step-gravel": ("1117", "Footsteps on gravels #2", "https://bigsoundbank.com/footsteps-on-gravels-2-s1117.html", 8, 0.6, -6.0, None),
    "step-leaves": ("2889", "Feet in leaves #2", "https://bigsoundbank.com/feet-in-leaves-2-s2889.html", 8, 0.75, -6.5, None),
    "step-grass": ("1253", "Steps in the grass, slow", "https://bigsoundbank.com/steps-in-the-grass-slow-s1253.html", 6, 0.75, -7.0, None),
    # A quick walk: a step is over in a third of a second, before the next crunch.
    "step-snow": ("3363", "Steps in the snow #3", "https://bigsoundbank.com/steps-in-the-snow-3-s3363.html", 8, 0.34, -6.0, None),
    # The sea floor: very wet mud, a little lower and darker, as if heavy with water.
    "step-sand": ("0495", "Steps in the mud", "https://bigsoundbank.com/steps-in-the-mud-s0495.html", 5, 0.7, -7.0, "seabed"),
}


def onsets(x, gap):
    """Where footfalls begin: sharp rises of the high band's level, smoothed over 40 ms so the
    pebble clicks within one step don't count as steps, at least `gap` seconds apart. Each is
    then moved back to where its first sound starts. The strictest rise that still finds a
    walking pace is used: soft surfaces (grass, a carpet of leaves) rise gently."""
    hop = ns(0.004)
    hi = filt(x, chain(("hp", 400, 0.7)))
    frames = len(hi) // hop
    env = np.sqrt(np.mean(hi[: frames * hop].reshape(frames, hop) ** 2, axis=1)) + 1e-9
    fast = 20 * np.log10(env)
    slow = 10 * np.log10(np.convolve(env ** 2, np.ones(10) / 10, "same") + 1e-18)
    floor = np.percentile(fast, 25)
    rise = slow - np.concatenate([np.full(6, slow[0]), slow[:-6]])
    seconds = len(x) / SR
    for above, by in ((14, 6), (11, 5), (9, 4), (7, 3), (5, 2.5), (4, 2)):
        out = []
        for i in range(6, frames):
            if slow[i] > floor + above and rise[i] > by and (not out or (i - out[-1]) * hop > ns(gap)):
                out.append(i)
        if len(out) / seconds >= 0.6:
            break
    starts = []
    for i in out:
        j = max(0, i - 15)
        while j < i and fast[j] < floor + 8:
            j += 1
        starts.append(j * hop)
    return starts


def cut(x, starts, i, longest):
    """One step: from just before its onset to just before the next (at most `longest` s)."""
    a = max(0, starts[i] - ns(0.012))
    end = starts[i + 1] - ns(0.02) if i + 1 < len(starts) else len(x)
    b = min(end, a + ns(longest))
    return x[a:b], a


def score(x, seg, a, longest):
    """Lower is better: a quiet run-up, a tail that has died away, a sensible length."""
    if len(seg) < ns(0.22):
        return np.inf
    peak = np.max(np.abs(seg)) + 1e-9
    # The footfall itself is at the start: a louder moment later on is the next step leaking in.
    if np.argmax(np.abs(seg)) > 0.35 * len(seg):
        return np.inf
    pre = x[max(0, a - ns(0.03)):a]
    pre_db = 20 * np.log10((np.sqrt(np.mean(pre ** 2)) if len(pre) else 1e-9) / peak + 1e-9)
    tail = seg[-ns(0.05):]
    tail_db = 20 * np.log10(np.sqrt(np.mean(tail ** 2)) / peak + 1e-9)
    # A step cut short by the next one sounds clipped: prefer the whole step.
    short = max(0.0, min(0.4, longest) - len(seg) / SR) * 30
    return pre_db + tail_db + short


def pick(x, n, longest, gap):
    starts = onsets(x, gap)
    steps = [cut(x, starts, i, longest) for i in range(len(starts))]
    peaks = np.array([np.max(np.abs(s)) if len(s) else 0 for s, _ in steps])
    if not len(peaks):
        raise SystemExit("no steps found")
    # Even steps only: not the stamps, not the scuffs.
    lo, hi = np.percentile(peaks, 25), np.percentile(peaks, 90)
    ok = [(score(x, s, a, longest), a, s) for (s, a), p in zip(steps, peaks) if lo <= p <= hi]
    ok = [o for o in ok if np.isfinite(o[0])]
    ok.sort(key=lambda o: o[0])
    best = sorted(ok[:n], key=lambda o: o[1])  # in the order they were walked
    return [s for _, _, s in best], len(starts)


def treat(seg, how):
    y = filt(seg, chain(("hp", 45, 0.7)))
    if how == "seabed":
        # a fifth of a tone heavier, and the top rolled away
        y = resample_poly(y, 6, 5)
        y = filt(y, chain(("lp", 2600, 0.7), ("lp", 3200, 0.7)))
    # a soft close, so a cut never clicks (longer where the rustle carries on)
    k = int(np.clip(len(y) * 0.22, ns(0.04), ns(0.15)))
    y[-k:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, k)))
    return y


def render():
    entries = []
    for group, (sid, title, page, n, longest, peak, how) in SOURCES.items():
        # Start the group afresh: no step left over from an earlier cut.
        for old in (OUT / "sfx").glob(f"{group}-*.mp3"):
            if re.fullmatch(rf"{re.escape(group)}-\d+\.mp3", old.name):
                old.unlink()
        update_manifest("sfx", group, [])
        x = original(sid)
        steps, found = pick(x, n, longest, GAP.get(group, 0.35))
        print(f"  {group}: {found} steps found in '{title}', kept {len(steps)}")
        for i, seg in enumerate(steps):
            name = f"{group}-{i + 1}"
            finish_sfx(group, name, treat(seg, how), peak, max_s=longest + 0.15, kbps=128)
            entries.append(entry(name, page, f"{title} (one step, trimmed and levelled)"))
    lock_cc0(entries, SOURCES)


if __name__ == "__main__":
    render()
