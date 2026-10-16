"""Fetch and prepare the University of Iowa Musical Instrument Samples the picture show plays: the
B-flat clarinet and the bassoon, every note at pp, mf and ff, recorded in an anechoic chamber
without vibrato by the university's Electronic Music Studios. "Since 1997, these recordings have
been freely available on this website and may be downloaded and used for any projects, without
restrictions" (https://theremin.music.uiowa.edu/MIS.html).

Each download is one dynamic's run of single notes (an octave or so) with silence between them.
This cuts every run into one file per note, from just before its attack to the end of its decay,
names it by its measured pitch and dynamic (C#4_mf.wav: concert pitch, as the sampler's other
libraries are named) and writes it, untouched but for a 2 ms fade at each end, to
tools/audio/.cache/iowa/{Clarinet,Bassoon}/ (git-ignored). The downloads stay in .cache/iowa/raw/.

    tools/audio/.venv/bin/python tools/audio/fetch_iowa.py
"""
from __future__ import annotations

import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hlaudio.sampler import _yin  # noqa: E402

SR = 44100
ROOT = HERE / ".cache" / "iowa"
SITE = "https://theremin.music.uiowa.edu/sound files/MIS/Woodwinds/"
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# instrument: (site folder, output folder, files)
SETS = {
    "clarinet": ("Bbclarinet", "Clarinet",
                 [f"BbClar.{d}.{r}.aiff" for d in ("pp", "mf", "ff") for r in ("D3B3", "C4B4", "C5B5", "C6B6")]
                 + ["BbClar.mf.C7.aiff"]),
    "bassoon": ("bassoon", "Bassoon",
                [f"Bassoon.{d}.{r}.aiff" for d in ("pp", "mf", "ff") for r in ("Bb1B1", "C2B2", "C4B4", "C5D5")]
                + ["Bassoon.pp.C3B3.aiff", "Bassoon.mf.C3B3.aiff", "Bassoon.ff.C3Bb3.aiff"]),
}


def _midi(name: str) -> int:
    """'Bb1' or 'C#4' -> MIDI number."""
    letter, rest = name[0], name[1:]
    acc = 0
    if rest[:1] in ("#", "b"):
        acc = 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + NAMES.index(letter) + acc


def _expected(fname: str) -> list[int]:
    """The notes a file's name says it holds: 'BbClar.mf.C4B4.aiff' -> C4 .. B4."""
    lo, hi = re.fullmatch(r"([A-G][#b]?\d)([A-G][#b]?\d)?", fname.split(".")[2]).groups()
    return list(range(_midi(lo), _midi(hi or lo) + 1))


def fetch(site_folder: str, fname: str, raw: Path) -> Path:
    p = raw / fname
    if not p.exists() or p.stat().st_size == 0:
        url = urllib.parse.quote(SITE + site_folder + "/" + fname, safe=":/")
        print(f"  fetching {fname}", flush=True)
        urllib.request.urlretrieve(url, p)
    return p


def decode(p: Path) -> np.ndarray:
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(out, dtype=np.float32).astype(np.float64)


def split_quiet(x: np.ndarray) -> list[tuple[int, int]]:
    """The same, for a run with long silences between soft notes (the clarinet's low pp): notes are
    found against the quiet of the room, 18 dB above it, and gaps under a quarter of a second are
    inside a note."""
    win = 441
    n = len(x) // win
    e = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-14)
    floor = float(np.percentile(e, 8))
    on = e > max(floor * 10 ** (18 / 20), e.max() * 10 ** (-60 / 20))
    runs, i = [], 0
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        while j < n and (on[j] or (j + 25 < n and on[j:j + 25].any())):
            j += 1
        if j - i >= 25:
            runs.append([i, j])
        i = j
    out = []
    for k, (a, b) in enumerate(runs):
        nxt = runs[k + 1][0] if k + 1 < len(runs) else n
        while b < nxt - 5 and e[b] > floor * 10 ** (5 / 20):
            b += 1
        prev = out[-1][1] // win if out else 0
        out.append((max(prev, a - 3) * win, min(len(x), (b + 5) * win)))
    return out


def split(x: np.ndarray) -> list[tuple[int, int]]:
    """(start, end) samples of each note, from 30 ms before its attack to where its decay has fallen
    well below it. Notes are found against their own level (most of a run is notes; the bassoon's
    follow each other with barely a tenth of a second between them): a dip 22 dB under it, however
    short, is a gap. The level is read over 30 ms, so a low note's own beating doesn't split it."""
    win = 441
    n = len(x) // win
    e = np.sqrt(np.mean(x[: n * win].reshape(n, win) ** 2, axis=1) + 1e-14)
    e = np.convolve(e, np.ones(3) / 3, mode="same")
    db = 20 * np.log10(e)
    thr = float(np.percentile(db, 70)) - 22
    on = db > thr
    runs, i = [], 0
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        while j < n and (on[j] or (j + 4 < n and on[j:j + 4].any())):  # flickers under 40 ms are inside a note
            j += 1
        if j - i >= 30:
            runs.append([i, j])
        i = j
    out = []
    for k, (a, b) in enumerate(runs):
        nxt = runs[k + 1][0] if k + 1 < len(runs) else n
        while b < nxt - 2 and db[b] > thr - 12:
            b += 1
        prev = out[-1][1] // win if out else 0
        start = max(prev, a - 3) * win
        out.append((start, min(len(x), (b + 2) * win)))
    return out


def pitch(x: np.ndarray, midi: int) -> float:
    """Median YIN pitch (MIDI, fractional) of the note's steady middle, searched within four semitones
    of the note it should be (so a strong partial can't pass for it)."""
    hz = 440.0 * 2 ** ((midi - 69) / 12)
    n = len(x)
    picks = []
    for f in (0.3, 0.4, 0.5, 0.6):
        a = int(n * f)
        seg = x[a: a + 15435]
        if seg.size < 8820:
            continue
        got, conf = _yin(seg, hz * 2 ** (-4 / 12), hz * 2 ** (4 / 12))
        if got > 0 and conf < 0.3:
            picks.append(69 + 12 * np.log2(got / 440.0))
    return float(np.median(picks)) if picks else float("nan")


def main() -> None:
    for key, (site_folder, out_name, files) in SETS.items():
        raw = ROOT / "raw" / key
        raw.mkdir(parents=True, exist_ok=True)
        out = ROOT / out_name
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.wav"):
            old.unlink()
        print(f"{key}:", flush=True)
        for fname in files:
            x = decode(fetch(site_folder, fname, raw))
            dyn = fname.split(".")[1]
            want = _expected(fname)
            notes = split(x)
            if len(notes) != len(want):
                notes = split_quiet(x)
            if len(notes) != len(want):
                print(f"  {fname:24s} {len(notes)} notes found, {len(want)} expected: skipped", flush=True)
                continue
            # Each run is chromatic, so a note is named by its place in it; the measured pitch only checks
            # it (its octave can't be trusted: a bassoon's second partial is often the stronger) and drops
            # any more than 40 cents out (the sampler plays a neighbour instead).
            kept, dropped = [], []
            for (a, b), midi in zip(notes, want):
                seg = x[a:b].copy()
                m = pitch(seg, midi)
                dev = ((m - midi + 6) % 12) - 6 if np.isfinite(m) else float("nan")
                if not abs(dev) <= 0.4:
                    dropped.append(f"{NAMES[midi % 12]}{midi // 12 - 1} ({dev * 100:+.0f}c)")
                    continue
                fade = int(0.002 * SR)
                seg[:fade] *= np.linspace(0, 1, fade)
                seg[-fade:] *= np.linspace(1, 0, fade)
                wavfile.write(out / f"{NAMES[midi % 12]}{midi // 12 - 1}_{dyn}.wav", SR, seg.astype(np.float32))
                kept.append(round(dev * 100))
            print(f"  {fname:24s} {len(kept):2d} notes, cents {kept}" + (f"  dropped {dropped}" if dropped else ""),
                  flush=True)


if __name__ == "__main__":
    main()
