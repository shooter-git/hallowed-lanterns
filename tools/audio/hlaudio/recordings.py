"""Real recordings: CC0 foley and field recordings by Joseph Sardin (BigSoundBank), fetched once
into .cache/recorded/ (git ignores it), and the assets.lock.json entries for what's made from them.

The night's wind is recorded too: wind() lays a stretch of a recording into a looping ambience,
cross-faded round on itself so it loops without a seam, with any twig-snap clicks taken down."""
import json
import re
import urllib.request
import warnings

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import median_filter, minimum_filter1d, uniform_filter1d
from scipy.signal import resample_poly

from hlaudio import master as M
from hlaudio.core import SR, ns, rng, smooth_random
from hlaudio.effects import chain, filt
from hlaudio.piece import CACHE, OUT

AUTHOR = "Joseph SARDIN (BigSoundBank)"


def _read(sound_id):
    """A BigSoundBank recording by its number as (channels, samples) at SR (fetched once into the cache)."""
    path = CACHE / "recorded" / f"bsb-{sound_id}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://bigsoundbank.com/UPLOAD/bwf-en/{sound_id}.wav"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Hallowed Lanterns audio tools)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", wavfile.WavFileWarning)  # BWF metadata chunks
        rate, data = wavfile.read(path)
    x = data.astype(np.float64)
    if data.dtype.kind == "i":
        x /= float(np.iinfo(data.dtype).max)
    x = np.atleast_2d(x.T) if x.ndim > 1 else x[None]
    return resample_poly(x, SR, rate, axis=1) if rate != SR else x


def original(sound_id):
    """A BigSoundBank recording by its number, mono, at SR."""
    return _read(sound_id).mean(axis=0)


def stereo(sound_id):
    """A BigSoundBank recording by its number, as stereo (2, samples) at SR."""
    x = _read(sound_id)
    return np.vstack([x[0], x[-1]])


# The wind recordings: number -> (title, page).
WIND = {
    "0907": ("Wind in shrub", "https://bigsoundbank.com/wind-in-shrub-s0907.html"),
    "0908": ("Wind in Tall Grass", "https://bigsoundbank.com/wind-in-tall-grass-s0908.html"),
    "0595": ("Wind", "https://bigsoundbank.com/wind-s0595.html"),
}
# Other field recordings laid in the same way: number -> (title, page).
FIELD = {
    "1880": ("Campaign at Night #4", "https://bigsoundbank.com/campaign-at-night-4-s1880.html"),
}


def declick(x, above_db=12.0):
    """Take down sharp clicks (a twig snapping on the microphone): wherever the 2 ms level jumps
    more than above_db over the level around it, it's pulled back to that level, smoothly."""
    x = np.atleast_2d(x)
    hop = ns(0.002)
    frames = x.shape[1] // hop
    lvl = np.sqrt(np.mean(x[:, : frames * hop].reshape(x.shape[0], frames, hop) ** 2, axis=(0, 2))) + 1e-9
    around = np.sqrt(median_filter(lvl ** 2, size=101, mode="wrap")) + 1e-9
    over = lvl / around / 10 ** (above_db / 20)
    gain = np.minimum(1.0, 1.0 / np.maximum(over, 1e-9))
    gain = minimum_filter1d(gain, 5, mode="wrap")  # hold the dip across the whole click
    gain = uniform_filter1d(gain, 5, mode="wrap")
    g = np.repeat(gain, hop)
    g = np.concatenate([g, np.full(x.shape[1] - g.size, g[-1])])
    return x * g


def loop_of(x, start, seconds, fade=4.0):
    """`seconds` of a recording from `start` that loops: the `fade` s after the stretch are
    cross-faded (equal power) into its beginning, so its end runs straight on into its start."""
    n, k = ns(seconds), ns(fade)
    a = ns(start)
    seg = np.atleast_2d(x)[:, a: a + n + k]
    assert seg.shape[1] == n + k, f"recording too short for {seconds}+{fade} s from {start} s"
    out = seg[:, :n].copy()
    u = np.linspace(0, np.pi / 2, k)
    out[:, :k] = seg[:, :k] * np.sin(u) + seg[:, n:] * np.cos(u)
    return out


def wind(track, sound_id, start, lufs, bands=(), swap=False, gust=None, seed=0, clicks=12.0):
    """Lay a stretch of a wind recording (from `start` s) into a circular track at `lufs`
    (integrated loudness of this layer alone, so the balance against the rest is set here).
    `bands` are EQ bands (as effects.chain takes them) after an 80 Hz high-pass that clears
    the rumble of wind on the microphone; `swap` swaps left and right (another stretch of the
    same wind shouldn't sit the same way round); `gust` (rate in Hz) lets a steady wind swell
    and ease slowly; `clicks` is how far (dB) over its surroundings a click is taken down (None
    leaves the recording alone: a meadow's crickets are not clicks). A mono recording is spread by
    taking each side from a different stretch."""
    x = _read(sound_id) if clicks is None else declick(_read(sound_id), clicks)
    if x.shape[0] == 1:
        x = np.vstack([x[0], np.roll(x[0], -ns(23.0))])
    if swap:
        x = x[::-1]
    y = loop_of(x, start, track.seconds)
    y = filt(y, chain(("hp", 80, 0.7), *bands), circular=True, warm=4.0)
    if gust:
        g = smooth_random(y.shape[1], rng("wind-gust", seed), gust, circular=True)
        y = y * np.clip(0.75 + 0.5 * g, 0.35, 1.25)
    y *= 10 ** ((lufs - M.lufs(y)) / 20)
    track.mix(y.astype(np.float32))
    return track


def ambience_source(sound_ids):
    """The assets.lock.json source line of an ambience made with these recordings."""
    known = {**WIND, **FIELD}
    names = ", ".join(f"\"{known[i][0]}\" ({known[i][1]})" for i in sound_ids)
    what = "wind recorded" if all(i in WIND for i in sound_ids) else "wind and a night meadow recorded"
    return f"Made with tools/audio (Hallowed Lanterns), with {what} by Joseph Sardin (BigSoundBank, CC0): {names}"


def lock_cc0(entries, groups):
    """Record sfx made from CC0 recordings: an entry replaces the older one for the same file
    (in place), and entries for the groups' files no longer made are dropped."""
    path = OUT.parents[1] / "assets.lock.json"
    data = json.loads(path.read_text()) if path.exists() else {"assets": []}
    new = {e["path"]: e for e in entries}
    ours = re.compile(r"^public/audio/sfx/(%s)-\d+\.mp3$" % "|".join(map(re.escape, groups)))
    assets = []
    for a in data.get("assets", []):
        p = a.get("path", "")
        if p in new:
            assets.append(new.pop(p))
        elif not ours.match(p):
            assets.append(a)
    assets.extend(new.values())
    data["assets"] = assets
    path.write_text(json.dumps(data, indent=2) + "\n")


def entry(name, page, title):
    return {
        "path": f"public/audio/sfx/{name}.mp3",
        "license": "CC0-1.0",
        "source": page,
        "author": AUTHOR,
        "title": title,
    }
