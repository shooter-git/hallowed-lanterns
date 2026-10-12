"""A sampler for the VSCO 2 Community Edition orchestral samples (CC0,
Versilian Studios), fetched into tools/audio/.cache/vsco/ (see README).

What it does, per note:
  * maps every sample to its real pitch (file names are read; the orchestral
    folders name middle C "C3", so they are shifted up an octave; the organ
    files are numbered, the glockenspiel is named two octaves low, and the
    timpani have no note names at all, so their tunings were measured);
  * picks the nearest sample (pitch-shifted by band-limited resampling, only
    ever a few semitones), the dynamic layer for the velocity (and
    cross-fades two layers when a sustain swells, like a mod wheel), cycles
    round-robins and varies the sample start a little;
  * plays sustains as long as they need: past the end of a recording it
    loops the steady part with correlation-aligned cross-fades; consecutive
    notes in a legato line cross-fade into the next sample's sustain
    (skipping its attack) with a short pitch slide;
  * releases fade naturally (no hard cuts) and the hall does the rest.

Levels: each sample's body loudness is measured and normalised towards its
dynamic layer's reference, so neighbouring notes match while the layers keep
their own colour.

A second library, the Versilian Community Sample Library (VCSL, CC0, also by
Versilian Studios; sparse-checked-out into tools/audio/.cache/vcsl/), gives
the Lantern Garden its festival colour: a dan tranh (the Vietnamese cousin of
the guzheng: plucks, tremolo, glissandi), a temple gong, finger cymbals, a
woodblock and an ocarina. Its names follow other conventions (notes at the
start of the file name, an octave low; dynamics as words), it is catalogued
separately (.cache/vcsl-catalog.json) and pitches that names cannot give are
measured: the gong, cymbal and woodblock by their strongest partial, the
zither's plucks well after the attack (a hard pluck starts sharp).
Plucked and struck notes can carry a pitch curve: `x["bend"]` (time, semitone
breakpoints: a guzheng press or slide) and `x["vib"]` (a pressed vibrato).
"""
from __future__ import annotations

import json
import math
import re
import warnings
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numba import njit
from scipy.io import wavfile

from .core import SR, ns, rng, undb, smoothstep, Track

VSCO = Path(__file__).resolve().parents[1] / ".cache" / "vsco"
CATALOG = Path(__file__).resolve().parents[1] / ".cache" / "vsco-catalog.json"
VCSL = Path(__file__).resolve().parents[1] / ".cache" / "vcsl"
VCSL_CATALOG = Path(__file__).resolve().parents[1] / ".cache" / "vcsl-catalog.json"
LIBS = {"vsco": (VSCO, CATALOG, 9), "vcsl": (VCSL, VCSL_CATALOG, 1)}
NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

# Timpani have no note names: principal (1,1)-mode frequencies measured from the
# spectra (the partner mode at ~1.5x confirms each one).
TIMP_HIT_HZ = {1: 89.7, 2: 122.1, 3: 142.7, 4: 168.9, 5: 191.1}
TIMP_ROLL_HZ = {1: 92.0, 2: 127.9, 3: 147.0, 4: 170.2, 5: 165.9}


def _hz2midi(f):
    return 69.0 + 12.0 * math.log2(f / 440.0)


@dataclass
class Inst:
    name: str
    folder: str
    kind: str                 # "sus" | "short" | "oneshot" | "drum"
    match: str = r".*"        # regex on file name
    octave: int = 0           # added to the named note
    release: float = 0.4      # release fade (s) at note end
    lag: float = 0.0          # perceived-attack delay to keep (s)
    max_lead: float = 0.06    # how early a slow attack may start before the beat
    legato_skip: float = 0.16  # where a legato note enters its sample (s after attack)
    xfade: float = 0.16       # legato cross-fade (s)
    body: float = 1.5         # seconds of body used to measure loudness
    ref_db: float = -20.0     # loud-layer body RMS reference
    layer_spread: float = 8.0  # dB between softest and loudest layer reference
    max_shift: float = 4.0    # semitones
    pan: float = 0.0
    width: float = 0.8
    pitch: str = "name"       # "name" | "organ" | "timp_hit" | "timp_roll" | "none"
    single_layer: bool = False
    organ_base: int = 0
    lib: str = "vsco"         # "vsco" | "vcsl"
    # VCSL measuring options
    tune_from: float = 0.04   # s after the attack where a pluck's tuning is read
    tune_n: int = 1           # how many 0.35 s windows (0.5 s apart)
    peak_band: tuple = ()     # pitch="peak": (lo, hi) Hz of the partial that names the pitch
    peak_win: tuple = (0.0, 0.5)  # ... read between these seconds after the onset
    fixed_midi: float = 0.0   # pitch="fixed": every file sits at this (nominal) pitch


INSTRUMENTS = {i.name: i for i in [
    Inst("violins", "Strings/Violin Section/susVib", "sus", octave=12, release=0.5, lag=0.03, ref_db=-20, pan=-0.5, width=0.7),
    Inst("violins_spic", "Strings/Violin Section/Spic", "short", octave=12, release=0.15, ref_db=-18, pan=-0.5, width=0.7, body=0.15),
    Inst("violas", "Strings/Viola Section/susvib", "sus", octave=12, release=0.5, lag=0.03, ref_db=-20, pan=0.1, width=0.6),
    Inst("violas_spic", "Strings/Viola Section/spic", "short", octave=12, release=0.15, ref_db=-18, pan=0.1, width=0.6, body=0.15),
    Inst("cellos", "Strings/Cello Section/susvib", "sus", octave=12, release=0.55, lag=0.03, ref_db=-20, pan=0.4, width=0.6),
    Inst("cellos_spic", "Strings/Cello Section/spic", "short", octave=12, release=0.15, ref_db=-18, pan=0.4, width=0.6, body=0.15),
    Inst("basses", "Strings/Solo Contrabass/SusNV", "sus", octave=12, release=0.6, lag=0.04, ref_db=-20, pan=0.6, width=0.4),
    Inst("basses_spic", "Strings/Solo Contrabass/Spic", "short", octave=12, release=0.2, ref_db=-18, pan=0.6, width=0.4, body=0.15),
    Inst("horns", "Brass/F Horn/sus", "sus", octave=12, release=0.45, lag=0.03, ref_db=-20, pan=-0.25, width=0.5, legato_skip=0.2),
    Inst("horns_stac", "Brass/F Horn/stac", "short", octave=12, release=0.2, ref_db=-18, pan=-0.25, width=0.5, body=0.15),
    Inst("horns_mute", "Brass/F Horn/mute", "sus", octave=12, release=0.4, lag=0.02, ref_db=-22, pan=-0.2, width=0.5),
    Inst("trombones", "Brass/Tenor Trombone/sus", "sus", octave=12, release=0.4, lag=0.02, ref_db=-20, pan=0.3, width=0.45),
    Inst("trombones_vib", "Brass/Tenor Trombone/vib", "sus", octave=12, release=0.4, lag=0.02, ref_db=-20, pan=0.3, width=0.45),
    Inst("trombones_stac", "Brass/Tenor Trombone/stac", "short", octave=12, release=0.2, ref_db=-18, pan=0.3, width=0.45, body=0.15),
    Inst("tuba", "Brass/Tuba/sus", "sus", octave=12, release=0.45, lag=0.03, ref_db=-20, pan=0.45, width=0.4),
    Inst("tuba_stac", "Brass/Tuba/stac", "short", octave=12, release=0.2, ref_db=-18, pan=0.45, width=0.4, body=0.15),
    Inst("organ", "Keys/Organ/Loud", "sus", match=r"Man3Open", pitch="organ", organ_base=35, release=0.6, ref_db=-20,
         width=1.0, legato_skip=0.25, layer_spread=0, max_shift=2.0),
    Inst("organ_pedal", "Keys/Organ/Loud", "sus", match=r"Pedal", pitch="organ", organ_base=23, release=0.7, ref_db=-20,
         width=0.9, legato_skip=0.25, layer_spread=0, max_shift=2.0),
    Inst("organ_soft", "Keys/Organ/Quiet", "sus", match=r"Man3Quiet", pitch="organ", organ_base=-86, release=0.6,
         ref_db=-20, width=1.0, legato_skip=0.25, layer_spread=0, max_shift=2.0),
    Inst("organ_soft_pedal", "Keys/Organ/Quiet", "sus", match=r"PedalQuiet", pitch="organ", organ_base=-28,
         release=0.7, ref_db=-20, width=0.9, legato_skip=0.25, layer_spread=0, max_shift=2.0),
    Inst("piano", "Keys/Upright Nr1", "oneshot", release=0.35, ref_db=-18, width=0.8, body=0.3, layer_spread=10),
    Inst("harp", "Strings/Harp", "oneshot", release=0.6, ref_db=-18, pan=-0.45, width=0.6, body=0.3, layer_spread=0,
         single_layer=True),
    Inst("glock", "Percussion/Glock", "oneshot", match=r"C5|G4|G5|C6|G6", octave=12, release=1.0, ref_db=-20, pan=0.35,
         width=0.5, body=0.2, layer_spread=0, max_shift=4.0, single_layer=True),
    Inst("timpani", "Percussion/Timpani", "drum", match=r"Hit", pitch="timp_hit", release=1.2, ref_db=-16, width=0.7,
         body=0.3, layer_spread=14),
    Inst("timpani_roll", "Percussion/Timpani/Rolls", "sus", match=r"Timpani[1-4]_Roll", pitch="timp_roll", release=1.0, ref_db=-18,
         width=0.7, layer_spread=8, legato_skip=0.5),
    Inst("bass_drum", "Percussion", "drum", match=r"BDrum", pitch="none", release=1.5, ref_db=-16, width=0.7, body=0.3,
         layer_spread=16),
    # added later (VSCO 2 CE, same checkout)
    Inst("violins_pizz", "Strings/Violin Section/Pizz", "short", octave=12, release=0.3, ref_db=-18, pan=-0.5,
         width=0.7, body=0.15),
    Inst("violas_pizz", "Strings/Viola Section/pizz", "short", octave=12, release=0.3, ref_db=-18, pan=0.1,
         width=0.6, body=0.15),
    Inst("cellos_pizz", "Strings/Cello Section/pizzT", "short", octave=12, release=0.4, ref_db=-18, pan=0.4,
         width=0.6, body=0.15),
    Inst("violins_trem", "Strings/Violin Section/Trem", "sus", octave=12, release=0.5, lag=0.02, ref_db=-21,
         pan=-0.5, width=0.7),
    Inst("violas_trem", "Strings/Viola Section/trem", "sus", octave=12, release=0.5, lag=0.02, ref_db=-21,
         pan=0.1, width=0.6),
    Inst("cellos_trem", "Strings/Cello Section/trem", "sus", octave=12, release=0.55, lag=0.02, ref_db=-21,
         pan=0.4, width=0.6),
    Inst("solo_violin", "Strings/Solo Violin/Arco Vib", "sus", octave=0, release=0.5, lag=0.03, ref_db=-21,
         pan=-0.15, width=0.4, legato_skip=0.2),
    Inst("flute", "Woodwinds/Flute/susvib", "sus", octave=12, release=0.35, lag=0.02, ref_db=-21, pan=-0.15,
         width=0.4, single_layer=True),
    Inst("flute_nv", "Woodwinds/Flute/susNV", "sus", octave=12, release=0.35, lag=0.02, ref_db=-21, pan=-0.15,
         width=0.4),
    Inst("flute_stac", "Woodwinds/Flute/stac", "short", octave=12, release=0.2, ref_db=-19, pan=-0.15, width=0.4,
         body=0.12),
    Inst("clarinet", "Woodwinds/Clarinet/susLong", "sus", octave=12, release=0.35, lag=0.02, ref_db=-21, pan=0.15,
         width=0.4),
    Inst("clarinet_stac", "Woodwinds/Clarinet/stac", "short", octave=12, release=0.2, ref_db=-19, pan=0.15,
         width=0.4, body=0.12),
    Inst("oboe", "Woodwinds/Oboe/Vib", "sus", octave=12, release=0.35, lag=0.02, ref_db=-21, pan=0.0, width=0.4),
    Inst("oboe_stac", "Woodwinds/Oboe/Stacc", "short", octave=12, release=0.2, ref_db=-19, pan=0.0, width=0.4,
         body=0.12),
    Inst("bassoon", "Woodwinds/Bassoon/sus", "sus", octave=12, release=0.35, lag=0.02, ref_db=-21, pan=0.25,
         width=0.4),
    Inst("bassoon_stac", "Woodwinds/Bassoon/stac", "short", octave=12, release=0.2, ref_db=-19, pan=0.25,
         width=0.4, body=0.12),
    Inst("marimba", "Percussion/Marimba", "oneshot", octave=12, release=0.6, ref_db=-18, pan=0.0, width=0.6,
         body=0.25, layer_spread=0, single_layer=True, max_shift=4.0),
    Inst("triangle", "Percussion", "drum", match=r"Triangle3-Hit", pitch="none", release=2.0, ref_db=-22,
         width=0.5, body=0.2, layer_spread=8),
    Inst("sleighbells", "Percussion", "drum", match=r"Sleighbells", pitch="none", release=1.0, ref_db=-22,
         width=0.6, body=0.2, layer_spread=0),
    Inst("belltree", "Percussion", "drum", match=r"BellTree", pitch="none", release=2.0, ref_db=-22, width=0.8,
         body=0.5, layer_spread=0, single_layer=True),
    # ---- VCSL (CC0, Versilian Studios): the Lantern Garden's festival colour
    # dan tranh plucks: strings B C# D# F# G# (B pentatonic) from B2 to B5, mf/f/ff;
    # named an octave low; tuning read 0.6-1.6 s after the pluck
    Inst("zither", "Chordophones/Zithers/Dan Tranh/Normal", "oneshot", lib="vcsl", octave=12, release=0.9,
         ref_db=-18, layer_spread=8, pan=0.2, width=0.5, body=0.3, tune_from=0.6, tune_n=3),
    # tremolo (the right hand's rapid re-plucking on a held note), one layer, ~10-13 s
    Inst("zither_trem", "Chordophones/Zithers/Dan Tranh/Tremolo", "oneshot", lib="vcsl", octave=12,
         release=0.7, ref_db=-20, layer_spread=0, pan=0.2, width=0.5, body=1.0, single_layer=True,
         tune_from=0.6, tune_n=3),
    # glissandi over all the strings (B pentatonic: play them at G to sweep G pentatonic)
    Inst("zither_gliss_up", "Chordophones/Zithers/Dan Tranh/Gliss", "oneshot", lib="vcsl",
         match=r"Gliss_Up_Med_mf", pitch="fixed", fixed_midi=71.0, release=1.5, ref_db=-20, layer_spread=0,
         pan=0.2, width=0.7, body=1.0, single_layer=True),
    Inst("zither_gliss_down", "Chordophones/Zithers/Dan Tranh/Gliss", "oneshot", lib="vcsl",
         match=r"Gliss_Dwn_Med_mf", pitch="fixed", fixed_midi=71.0, release=1.5, ref_db=-20, layer_spread=0,
         pan=0.2, width=0.7, body=1.0, single_layer=True),
    # ocarina (a clay flute: the xun's soft, breathy voice), straight and with vibrato; A4-C#6
    Inst("ocarina", "Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/Sus", "sus", lib="vcsl",
         octave=12, release=0.4, lag=0.03, ref_db=-22, pan=-0.1, width=0.35, single_layer=True,
         legato_skip=0.2, xfade=0.2),
    Inst("ocarina_vib", "Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/SusVib", "sus", lib="vcsl",
         octave=12, release=0.4, lag=0.03, ref_db=-22, pan=-0.1, width=0.35, single_layer=True,
         legato_skip=0.2, xfade=0.2),
    # temple gong: fundamental ~143.5 Hz (D3, a third of a semitone flat), partials at ~345, 420, 566 Hz
    Inst("gong", "Idiophones/Struck Idiophones/Gong 1", "drum", lib="vcsl", match=r"^gong_(p|mf|f|fff)\.wav$",
         pitch="peak", peak_band=(120.0, 170.0), peak_win=(1.0, 3.0), release=6.0, ref_db=-18, layer_spread=14,
         width=1.0, body=1.0),
    # finger cymbals: one hit, ringing at ~3.1 kHz (G7)
    Inst("finger_cymbal", "Idiophones/Struck Idiophones/Finger Cymbals", "drum", lib="vcsl", pitch="peak",
         peak_band=(2500.0, 4000.0), peak_win=(0.05, 1.0), release=2.5, ref_db=-24, layer_spread=0,
         width=0.4, body=0.3, single_layer=True),
    # woodblock (the temple block): pp/mp/f/ff, round robins; resonance ~1.37 kHz
    Inst("woodblock", "Idiophones/Struck Idiophones/Woodblock", "drum", lib="vcsl", match=r"^wood_click_",
         pitch="peak", peak_band=(900.0, 2000.0), peak_win=(0.0, 0.12), release=0.3, ref_db=-20,
         layer_spread=14, width=0.3, body=0.1),
]}


# ----------------------------------------------------------------- catalog

def _read(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sr, x = wavfile.read(path)
    if sr != SR:
        raise ValueError(f"{path}: {sr} Hz")
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768.0
    elif x.dtype == np.int32:
        x = x.astype(np.float32) / 2147483648.0
    else:
        x = x.astype(np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    return np.ascontiguousarray(x[:, :2].T)


# VCSL dynamics are words in the file name; any order-preserving numbers do
_DYN = {"ppp": 1, "pp": 2, "p": 3, "mp": 4, "mf": 5, "f": 6, "ff": 7, "fff": 8}


def _parse_vcsl(inst: Inst, fname: str):
    """-> (midi or None, layer, rr) for a VCSL file name: 'B3_mf_1.wav',
    'StdOcarina_Sus_A#4.wav', 'gong_fff.wav', 'wood_click_pp_rr2.wav'.
    pitch="peak" files get their pitch measured later."""
    stem = fname[:-4]
    midi = None
    if inst.pitch == "name":
        mt = re.search(r"(?:^|_)([A-Ga-g]#?)(-?\d)(?=_|$)", stem)
        midi = float(12 * (int(mt.group(2)) + 1) + NOTE[mt.group(1).upper()] + inst.octave)
    elif inst.pitch == "fixed":
        midi = float(inst.fixed_midi)
    toks = stem.lower().split("_")
    layer, rrn = 1, 1
    for tk in toks:
        if tk in _DYN:
            layer = _DYN[tk]
        m_rr = re.fullmatch(r"rr(\d+)", tk)
        if m_rr:
            rrn = int(m_rr.group(1))
    if re.fullmatch(r"\d+", toks[-1]):
        rrn = int(toks[-1])
    if inst.single_layer:
        layer = 1
    return midi, layer, rrn


def _peak_midi(mono, info, band, win):
    """Pitch (MIDI) of the strongest partial in `band` Hz, read `win` seconds
    after the onset: names a gong, a cymbal or a woodblock."""
    a = info["start"] + ns(0.004)
    seg = mono[a + ns(win[0]): a + ns(win[1])]
    if seg.size < 256:
        seg = mono[a: a + ns(0.1)]
    n_fft = 1 << 17
    S = np.abs(np.fft.rfft(seg * np.hanning(seg.size), n_fft))
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    S[(f < band[0]) | (f > band[1])] = 0
    k = int(np.argmax(S))
    if 0 < k < S.size - 1:
        al, be, ga = np.log(S[k - 1] + 1e-12), np.log(S[k] + 1e-12), np.log(S[k + 1] + 1e-12)
        k = k + 0.5 * (al - ga) / (al - 2 * be + ga)
    return _hz2midi(k * SR / n_fft)


def _parse(inst: Inst, fname: str):
    """-> (midi or None, layer, rr) from a file name."""
    if inst.lib == "vcsl":
        return _parse_vcsl(inst, fname)
    stem = fname[:-4]
    if inst.pitch == "organ":
        num = int(re.search(r"_(\d+)(?:_rr\d)?$", stem).group(1))
        midi = float(num + inst.organ_base)
    elif inst.pitch == "timp_hit":
        midi = _hz2midi(TIMP_HIT_HZ[int(re.search(r"Timpani(\d)", stem).group(1))])
    elif inst.pitch == "timp_roll":
        midi = _hz2midi(TIMP_ROLL_HZ[int(re.search(r"Timpani(\d)", stem).group(1))])
    elif inst.pitch == "none":
        midi = None
    else:
        mt = re.search(r"_([A-G]#?)(-?\d)(?=_|$)", stem)
        midi = float(12 * (int(mt.group(2)) + 1) + NOTE[mt.group(1)] + inst.octave)
    if inst.single_layer:
        return midi, 1, 1
    lay = re.search(r"_v(\d)", stem)
    if lay:
        layer = int(lay.group(1))
    else:
        dyn = re.search(r"_(pp|p|mf|f)(?=_|$)", stem)
        layer = {"pp": 1, "p": 1, "mf": 2, "f": 3}[dyn.group(1)] if dyn else 1
    rr = re.search(r"_(?:rr|RR)(\d)", stem)
    if rr:
        rrn = int(rr.group(1))
    else:
        tail = re.search(r"_v\d_(\d)$", stem)
        rrn = int(tail.group(1)) if tail else 1
    return midi, layer, rrn


def _env(mono, win=441):
    """RMS envelope, one value per `win` samples (10 ms)."""
    n = len(mono) // win
    e = np.sqrt(np.mean(mono[: n * win].reshape(n, win) ** 2, axis=1) + 1e-14)
    return e


def _measure(inst: Inst, x):
    mono = x.mean(axis=0).astype(np.float64)
    win = 441
    e = _env(mono, win)
    pk = float(e.max())
    on = int(np.argmax(e > pk * 10 ** (-42 / 20)))
    start = max(0, on * win - ns(0.004))
    # perceived arrival: first frame within 9 dB of the early body level
    body_lo = on
    body_hi = min(len(e), on + max(2, int(inst.body * 100)))
    body_lvl = float(np.sqrt(np.mean(e[body_lo:body_hi] ** 2)))
    att = on + int(np.argmax(e[on:] > body_lvl * 10 ** (-9 / 20)))
    above = np.nonzero(e > pk * 10 ** (-62 / 20))[0]
    end = min(len(mono), (int(above[-1]) + 1) * win) if above.size else len(mono)
    info = dict(start=int(start), attack=int(att * win), end=int(end), body_db=float(20 * np.log10(body_lvl + 1e-12)),
                peak_db=float(20 * np.log10(np.max(np.abs(x)) + 1e-12)))
    if inst.kind == "sus":
        # recording glitches (a click, a chair) inside the sustain: stop before them
        frame, hop = 2048, 1024
        a0 = att * win + ns(1.2)
        if end - a0 > ns(1.5) and inst.pitch != "timp_roll":
            seg_m = mono[a0:end]
            nf = (len(seg_m) - frame) // hop
            idx = np.arange(frame)[None, :] + hop * np.arange(nf)[:, None]
            S = 20 * np.log10(np.abs(np.fft.rfft(seg_m[idx] * np.hanning(frame), axis=1)) + 1e-9)
            fl = np.mean(np.maximum(np.diff(S, axis=0), 0), axis=1)
            bad = np.nonzero(fl > 3.2 * np.median(fl))[0]
            if bad.size:
                info["clean_end"] = int(a0 + bad[0] * hop - ns(0.1))
        # steady part: frames within 4 dB of the median level after the attack
        seg = e[att:]
        if seg.size > 50:
            med = float(np.median(seg[: max(10, int(seg.size * 0.7))]))
            ok = np.nonzero(seg > med * 10 ** (-4 / 20))[0]
            sus_end = att + int(ok[-1]) if ok.size else att + seg.size
            if "clean_end" in info:
                sus_end = min(sus_end, info["clean_end"] // win)
            ls = (att + max(60, int(0.25 * (sus_end - att)))) * win
            le = (sus_end - 30) * win
            if le - ls > ns(1.2):
                ls, le, rho = _loop_points(mono, ls, le)
                info.update(loop_start=int(ls), loop_end=int(le), loop_rho=float(rho))
    return info


def _loop_points(mono, ls, le, search=0.25, w=2048):
    """Nudge the loop end so the waveform around it best matches the waveform
    around the loop start (normalised cross-correlation)."""
    a = mono[ls - w // 2: ls + w // 2]
    best, best_r = le, -2.0
    lo = max(ls + ns(1.0), le - ns(search))
    seg = mono[lo - w // 2: le + w // 2]
    if seg.size < w + 2:
        return ls, le, 0.0
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(seg, w)[:: 4]
    an = (a - a.mean()) / (np.linalg.norm(a - a.mean()) + 1e-12)
    wc = win - win.mean(axis=1, keepdims=True)
    r = wc @ an / (np.linalg.norm(wc, axis=1) + 1e-12)
    k = int(np.argmax(r))
    best = lo + k * 4
    return ls, best, float(r[k])


def _yin(seg, fmin=25.0, fmax=2500.0):
    n = len(seg)
    W = min(n // 2, 4096)
    taumax = min(int(SR / fmin), n - W - 1)
    taumin = int(SR / fmax)
    if taumax <= taumin + 2:
        return 0.0, 1.0
    x = seg.astype(np.float64)
    x0 = x[:W]
    cs = np.concatenate([[0.0], np.cumsum(x ** 2)])
    N = 1 << int(np.ceil(np.log2(W + taumax + 1)))
    corr = np.fft.irfft(np.fft.rfft(x[:W + taumax], N) * np.fft.rfft(x0[::-1], N), N)[W - 1:W - 1 + taumax]
    etau = cs[np.arange(taumax) + W] - cs[np.arange(taumax)]
    d = np.sum(x0 ** 2) + etau - 2 * corr
    d[0] = 0
    cm = np.concatenate([[1.0], d[1:] * np.arange(1, taumax) / np.maximum(np.cumsum(d[1:]), 1e-12)])
    cand = np.where(cm[taumin:] < 0.15)[0]
    t = taumin + (cand[0] if cand.size else int(np.argmin(cm[taumin:])))
    while t + 1 < taumax and cm[t + 1] < cm[t]:
        t += 1
    if 1 <= t < taumax - 1:
        a, b, c = cm[t - 1], cm[t], cm[t + 1]
        t = t + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return SR / t, float(cm[int(round(t))]) if int(round(t)) < taumax else 1.0


def _tuning(mono, info, midi, kind, t_from=0.04, n_win=1):
    """Cents this recording sits off its nominal note (0 if unsure)."""
    if midi is None:
        return 0.0
    a = info["attack"] + (ns(0.3) if kind == "sus" else ns(t_from))
    devs = []
    for k in range(4 if kind == "sus" else n_win):
        seg = mono[a + k * ns(0.6): a + k * ns(0.6) + ns(0.35)]
        if seg.size < ns(0.2):
            break
        f, conf = _yin(seg)
        if f <= 0 or conf > 0.25:
            continue
        det = 69 + 12 * np.log2(f / 440.0)
        dev = ((det - midi + 6) % 12) - 6
        if abs(dev) < 0.45:
            devs.append(dev * 100)
    return float(np.median(devs)) if len(devs) >= (2 if (kind == "sus" or n_win > 1) else 1) else 0.0


_CAT_MEM: dict = {}


def build_catalog(force=False):
    """The measured catalogue of every instrument: VSCO and VCSL are measured
    and cached separately (adding a VCSL instrument never re-measures VSCO)."""
    if _CAT_MEM and not force:
        return _CAT_MEM["cat"]
    inst_all = {}
    for lib in LIBS:
        inst_all.update(_build_lib(lib, force)["instruments"])
    cat = dict(instruments=inst_all)
    _CAT_MEM["cat"] = cat
    return cat


def _build_lib(lib, force=False):
    root, path, version = LIBS[lib]
    insts = [i for i in INSTRUMENTS.values() if i.lib == lib]
    if not root.exists():
        if lib == "vsco":
            raise SystemExit(f"VSCO samples not found in {root} (see tools/audio/README.md)")
        if path.exists():
            return json.loads(path.read_text())
        print(f"  (VCSL samples not found in {root}: its instruments are unavailable)", flush=True)
        return dict(instruments={})
    sig = {}
    for inst in insts:
        d = root / inst.folder
        for p in sorted(d.glob("*.wav")):
            if re.search(inst.match, p.name):
                sig[str(p.relative_to(root))] = p.stat().st_size
    if lib == "vcsl":
        # the measuring options are part of the signature, so retuning re-measures
        sig["__opts__"] = repr([(i.name, i.octave, i.pitch, i.tune_from, i.tune_n, i.peak_band, i.peak_win,
                                 i.fixed_midi, i.body, i.ref_db, i.layer_spread, i.single_layer, i.kind)
                                for i in insts])
    if path.exists() and not force:
        cat = json.loads(path.read_text())
        if cat.get("sig") == sig and cat.get("version") == version:
            return cat
    entries = {}
    for inst in insts:
        d = root / inst.folder
        rows = []
        for p in sorted(d.glob("*.wav")):
            if not re.search(inst.match, p.name):
                continue
            midi, layer, rr = _parse(inst, p.name)
            x = _read(p)
            info = _measure(inst, x)
            mono = x.mean(axis=0).astype(np.float64)
            tune = 0.0
            if inst.pitch == "peak":
                midi = round(_peak_midi(mono, info, inst.peak_band, inst.peak_win), 3)
            elif inst.kind in ("sus", "short", "oneshot") and inst.pitch == "name" and inst.name != "glock":
                tune = _tuning(mono, info, midi, inst.kind, inst.tune_from, inst.tune_n)
            if inst.name == "glock":
                tune = 12.0  # the glockenspiel bars sit ~12 cents sharp of their names (measured)
            info.update(file=str(p.relative_to(root)), midi=midi, layer=layer, rr=rr, n=int(x.shape[1]),
                        tune=round(tune, 1))
            if lib != "vsco":
                info["lib"] = lib
            rows.append(info)
        # layer references: loudest layer at ref_db, softest layer_spread below
        layers = sorted({r["layer"] for r in rows})
        for r in rows:
            li = layers.index(r["layer"]) / max(1, len(layers) - 1)
            same = [q["body_db"] for q in rows if q["layer"] == r["layer"]]
            med = float(np.median(same))
            target = inst.ref_db - inst.layer_spread * (1 - li)
            # move each sample 75% of the way to its layer median, then to target
            corr = -(r["body_db"] - med) * 0.75
            r["gain_db"] = float(np.clip(target - med + corr, -40, 40))
        entries[inst.name] = rows
    cat = dict(version=version, sig=sig, instruments=entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cat))
    return cat


# ----------------------------------------------------------------- audio cache

class _LRU:
    def __init__(self, limit_bytes):
        self.d = OrderedDict()
        self.size = 0
        self.limit = limit_bytes

    def get(self, k):
        v = self.d.get(k)
        if v is not None:
            self.d.move_to_end(k)
        return v

    def put(self, k, v):
        self.d[k] = v
        self.size += v.nbytes
        while self.size > self.limit and len(self.d) > 1:
            _, old = self.d.popitem(last=False)
            self.size -= old.nbytes


_RAW = _LRU(900 * 2 ** 20)
_SHIFTED = _LRU(700 * 2 ** 20)


def raw(entry):
    lib = entry.get("lib", "vsco")
    k = entry["file"] if lib == "vsco" else f"{lib}:{entry['file']}"
    x = _RAW.get(k)
    if x is None:
        x = _read(LIBS[lib][0] / entry["file"])
        _RAW.put(k, x)
    return x


# ----------------------------------------------------------------- resampling

_TAPS = 24
_PHASES = 512
_KERNELS: dict = {}


def _kernel(cut):
    key = round(cut, 3)
    if key not in _KERNELS:
        k = np.arange(-_TAPS + 1, _TAPS + 1)
        fr = np.arange(_PHASES + 1) / _PHASES
        d = k[None, :] - fr[:, None]
        w = np.kaiser(2 * _TAPS + 1, 9.0)
        win = np.interp(d, np.arange(-_TAPS, _TAPS + 1), w)
        _KERNELS[key] = (cut * np.sinc(cut * d) * win).astype(np.float64)
    return _KERNELS[key]


@njit(cache=True, fastmath=True)
def _resample(x, pos, ker, taps, phases):
    """Band-limited interpolation of x (channels, n) at fractional positions."""
    ch, n = x.shape
    m = pos.shape[0]
    out = np.zeros((ch, m), dtype=np.float32)
    for i in range(m):
        p = pos[i]
        ip = int(math.floor(p))
        fr = p - ip
        ph = int(fr * phases + 0.5)
        if ip - taps + 1 < 0 or ip + taps >= n:
            for c in range(ch):
                acc = 0.0
                for k in range(-taps + 1, taps + 1):
                    j = ip + k
                    if 0 <= j < n:
                        acc += x[c, j] * ker[ph, k + taps - 1]
                out[c, i] = acc
        else:
            for c in range(ch):
                acc = 0.0
                for k in range(-taps + 1, taps + 1):
                    acc += x[c, ip + k] * ker[ph, k + taps - 1]
                out[c, i] = acc
    return out


def shift(x, semis, start=0, length=None, glide=None):
    """Pitch-shift x (2, n) by `semis` semitones by resampling, from input
    index `start`, producing `length` output samples. `glide` (array of
    semitone offsets per output sample, optional) adds a pitch curve."""
    ratio = 2.0 ** (semis / 12.0)
    avail = int((x.shape[1] - start - 2) / ratio)
    if length is None or length > avail:
        length = max(0, avail)
    if glide is not None:
        inc = ratio * 2.0 ** (glide[:length] / 12.0)
        pos = start + np.concatenate([[0.0], np.cumsum(inc[:-1])])
        pos = np.minimum(pos, x.shape[1] - 1.0)
        top = float(np.max(inc)) if inc.size else ratio
    else:
        pos = start + np.arange(length) * ratio
        top = ratio
    if abs(semis) < 1e-4 and glide is None and float(start).is_integer():
        s = int(start)
        return np.array(x[:, s:s + length], dtype=np.float32)
    cut = min(1.0, 0.985 / max(top, 1e-6))
    return _resample(np.ascontiguousarray(x, dtype=np.float32), pos.astype(np.float64), _kernel(cut), _TAPS, _PHASES)


# ----------------------------------------------------------------- looping

def extend(x, entry, need, xf=0.9):
    """Return x[:, start:] lengthened to `need` samples by looping its steady
    part: equal-power cross-fades at the joins (linear when the waveforms are
    well correlated) and a slow gain ramp across each loop pass so the level
    is continuous at every join (x is the unshifted sample)."""
    s = entry["start"]
    usable = entry.get("clean_end", x.shape[1])
    if "loop_start" not in entry or usable - s >= need:
        return x[:, s:]
    ls, le = entry["loop_start"], entry["loop_end"]
    rho = entry.get("loop_rho", 0.0)
    # aligned, well-correlated joins want short linear fades (a long fade
    # between periodic signals drifts out of phase and combs); loose joins
    # want long equal-power fades
    xf_s = 0.04 if rho > 0.9 else 0.15 if rho > 0.6 else xf
    C = min(ns(xf_s), (le - ls) // 3, ls - s)
    t = np.linspace(0, 1, C)
    if rho > 0.6:
        fo, fi = 1 - t, t
    else:
        fo, fi = np.cos(t * np.pi / 2), np.sin(t * np.pi / 2)
    W = ns(0.4)
    lv_end = np.sqrt(np.mean(x[:, le - W:le] ** 2) + 1e-12)
    lv_start = np.sqrt(np.mean(x[:, ls:ls + W] ** 2) + 1e-12)
    r = float(np.clip(lv_end / lv_start, 0.5, 2.0))
    body = x[:, ls:le]
    ramp = np.linspace(r, 1.0, body.shape[1], dtype=np.float32)
    body = body * ramp
    pre = x[:, ls - C:ls] * r
    out = [x[:, s:le]]
    total = le - s
    while total < need + C:
        last = out[-1]
        mixed = last[:, -C:] * fo + pre * fi
        out[-1] = np.concatenate([last[:, :-C], mixed], axis=1)
        out.append(body)
        total += body.shape[1]
    return np.concatenate(out, axis=1)


# ----------------------------------------------------------------- the sampler

def pitch_curve(L, bend=None, vib=None, r=None):
    """Semitone offsets for L output samples: `bend` is [(time_s, semis), ...]
    (cosine-shaped between points: a guzheng press, a slide into the note, a
    release); `vib` is a dict(depth=semis, rate=Hz, delay=s, rise=s, up=0..1)
    for a pressed vibrato (up=1 only ever raises the pitch, as a finger
    pressing behind the bridge does; up=0 is symmetric). None if neither."""
    if not bend and not vib:
        return None
    t = np.arange(L) / SR
    g = np.zeros(L)
    if bend:
        ts = np.array([b[0] for b in bend], float)
        vs = np.array([b[1] for b in bend], float)
        idx = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, max(0, len(ts) - 2))
        if len(ts) == 1:
            g += vs[0]
        else:
            t0, t1 = ts[idx], ts[idx + 1]
            u = np.clip((t - t0) / np.maximum(t1 - t0, 1e-9), 0, 1)
            u = 0.5 - 0.5 * np.cos(np.pi * u)
            seg = vs[idx] + (vs[idx + 1] - vs[idx]) * u
            g += np.where(t < ts[0], vs[0], np.where(t > ts[-1], vs[-1], seg))
    if vib:
        depth = float(vib.get("depth", 0.25))
        rate = float(vib.get("rate", 5.5))
        delay = float(vib.get("delay", 0.3))
        rise = float(vib.get("rise", 0.4))
        up = float(vib.get("up", 0.7))
        ph0 = float(r.uniform(0, 0.3)) if r is not None else 0.0
        # a hand, not an LFO: the rate drifts a little
        drift = 1 + 0.04 * np.sin(2 * np.pi * 0.7 * t + 1.3)
        ph = 2 * np.pi * np.cumsum(rate * drift) / SR + ph0
        ramp = smoothstep((t - delay) / max(rise, 1e-3))
        osc = up * 0.5 * (1 - np.cos(ph)) + (1 - up) * 0.5 * np.sin(ph)
        g += depth * ramp * osc
    return g


class Sampler:
    def __init__(self, name, seed=0):
        self.inst = INSTRUMENTS[name]
        self.rows = build_catalog()["instruments"][name]
        self.layers = sorted({r["layer"] for r in self.rows})
        self.rr_count = {}
        self.r = rng("sampler", name, seed)

    # -- zone choice
    def _zone(self, midi, layer):
        cands = [r for r in self.rows if r["layer"] == layer]
        if not cands:
            cands = self.rows
        if midi is None:
            return cands
        # a layer that only has a few notes must not force a big pitch shift
        d_layer = min(abs(r["midi"] - midi) for r in cands)
        d_all = min(abs(r["midi"] - midi) for r in self.rows)
        if d_layer > max(2.6, d_all + 1.01):
            near = [r for r in self.rows if abs(r["midi"] - midi) - d_all < 0.01]
            ly = min({r["layer"] for r in near}, key=lambda l: abs(l - layer))
            cands = [r for r in self.rows if r["layer"] == ly]
        dist = sorted(abs(r["midi"] - midi) for r in cands)
        best = dist[0]
        pool = [r for r in cands if abs(abs(r["midi"] - midi) - best) < 0.01]
        # prefer shifting down (darker) on ties
        pool.sort(key=lambda r: (abs(r["midi"] - midi), r["midi"] < midi))
        bm = pool[0]["midi"]
        return [r for r in pool if abs(r["midi"] - bm) < 0.01]

    def pick(self, midi, layer, avoid=None):
        pool = self._zone(midi, layer)
        key = (round(pool[0]["midi"] or 0, 2), layer)
        c = self.rr_count.get(key, int(self.r.integers(0, 8)))
        self.rr_count[key] = c + 1
        if avoid is not None and len(pool) > 1:
            alt = [r for r in pool if r["file"] != avoid]
            pool = alt or pool
        return pool[c % len(pool)]

    def layer_for(self, v):
        """Velocity 0..1 -> (low layer, high layer, mix)."""
        L = len(self.layers)
        if L == 1:
            return self.layers[0], self.layers[0], 0.0
        p = np.clip(v, 0, 1) * (L - 1)
        lo = int(min(L - 2, math.floor(p)))
        return self.layers[lo], self.layers[lo + 1], float(p - lo)

    # -- one sample, shifted, from an offset, for a length
    def _voice(self, entry, midi, length, offset=0, glide=None, detune=0.0):
        x = raw(entry)
        semis = 0.0 if midi is None or entry["midi"] is None else \
            (midi - entry["midi"]) + (detune - entry.get("tune", 0.0)) / 100.0
        ratio = 2 ** (semis / 12)
        start = entry["start"] + offset
        need_in = int(length * ratio) + 64
        if self.inst.kind == "sus" and entry.get("clean_end", x.shape[1]) - start < need_in:
            ext = extend(x, entry, need_in + offset)
            src, st = ext, offset
        else:
            src, st = x, start
        key = None
        if glide is None and offset == 0 and src is x:
            key = (entry.get("lib", "vsco"), entry["file"], round(semis, 4))
            cached = _SHIFTED.get(key)
            if cached is not None and cached.shape[1] >= length:
                return cached[:, :length] * undb(entry["gain_db"])
        y = shift(src, semis, st, length if key is None else None, glide)
        if key is not None:
            _SHIFTED.put(key, y)
            y = y[:, :length]
        return y * undb(entry["gain_db"])

    def note(self, midi, v, dur, *, dyn=None, legato_in=None, xf_in=None, release=None, tail=None,
             start_jitter=0.006, detune=0.0, layer_bias=0.0, avoid=None, slide=0.06, shape=None, skip=0.0,
             bend=None, vib=None):
        """Render one note -> (stereo array, lead samples). `dyn` is an array of
        0..1 dynamics over the note's length (mod wheel) or None. `legato_in` is
        the previous pitch when this note is entered legato."""
        inst = self.inst
        rel = inst.release if release is None else release
        tail = rel * 2.5 if tail is None else tail
        n = ns(dur)
        L = n + ns(tail)
        if inst.kind in ("short", "oneshot", "drum"):
            lo, hi, mix = self.layer_for(np.clip(v + layer_bias, 0, 1))
            lay = hi if mix > 0.5 else lo
            e = self.pick(midi, lay, avoid)
            off = int(self.r.uniform(0, start_jitter) * SR)
            avail = int((raw(e).shape[1] - e["start"] - off) / 2 ** (((midi or 0) - (e["midi"] or 0)) / 12)) - 8
            pc = pitch_curve(min(avail, L), bend, vib, self.r) if (bend or vib) else None
            if pc is not None:
                # a pressed (raised) pitch reads the sample faster: keep inside it
                avail = int(avail / 2 ** (max(0.0, float(np.max(pc))) / 12)) - 8
                pc = pc[:max(1, min(avail, L))]
            y = self._voice(e, midi, min(avail, L), offset=off, detune=detune, glide=pc)
            gain = undb(-22 * (1 - np.clip(v, 0, 1)) ** 1.3 + 6 * (mix - 0.5) * (len(self.layers) > 1) * 0.3)
            y = y * gain
            if inst.kind == "oneshot" or inst.kind == "short":
                # damp at note end (piano dampers / string stopped), else ring out
                if dur > 0 and n < y.shape[1]:
                    t = np.arange(y.shape[1] - n) / SR
                    y[:, n:] *= np.exp(-t / max(rel / 4.0, 1e-3)).astype(np.float32)
            k = min(y.shape[1], ns(0.02))
            if k > 1:
                y[:, -k:] *= np.linspace(1, 0, k, dtype=np.float32)
            lead = 0
            return y, lead, e["file"]
        # ---- sustains
        if dyn is None:
            dyn = np.full(L, float(np.clip(v, 0, 1)))
        else:
            dyn = np.concatenate([dyn[:n], np.full(max(0, L - min(n, dyn.size)), dyn[min(n, dyn.size) - 1])])[:L]
            if dyn.size < L:
                dyn = np.pad(dyn, (0, L - dyn.size), mode="edge")
        dmean = float(np.mean(dyn[: max(1, n)]))
        # ONE recorded layer per note, chosen by the note's mean dynamic; swells
        # are a smooth volume (expression) curve. Cross-fading two layers of the
        # same note combs them into a phasey pad, the classic synth-string sound.
        lo, hi, mix_ = self.layer_for(np.clip(dmean + layer_bias, 0, 1))
        lo = hi if mix_ > 0.5 else lo
        hi = lo
        e_lo = self.pick(midi, lo, avoid)
        if legato_in is not None:
            off = max(0, e_lo["attack"] - e_lo["start"]) + ns(self.inst.legato_skip)
        else:
            off = int(self.r.uniform(0, start_jitter) * SR)
        off += ns(skip)
        glide = None
        if legato_in is not None and slide > 0 and abs(legato_in - midi) > 0.01:
            g = np.zeros(L)
            k = ns(slide)
            g[:k] = (legato_in - midi) * (1 - smoothstep(np.arange(k) / k))
            glide = g
        if bend or vib:
            pc = pitch_curve(L, bend, vib, self.r)
            glide = pc if glide is None else glide + pc
        y = self._voice(e_lo, midi, L, offset=off, glide=glide, detune=detune)
        if hi != lo:
            e_hi = self.pick(midi, hi)
            off_hi = off if legato_in is not None else off + max(0, (e_lo["attack"] - e_lo["start"]) - (e_hi["attack"] - e_hi["start"]))
            y2 = self._voice(e_hi, midi, L, offset=max(0, off_hi), glide=glide, detune=detune)
            m = min(y.shape[1], y2.shape[1])
            li, hj = self.layers.index(lo), self.layers.index(hi)
            p = np.clip(dyn[:m] + layer_bias, 0, 1) * (len(self.layers) - 1)
            w = np.clip((p - li) / max(1, hj - li), 0, 1)
            w = smoothstep(w)
            y = (y[:, :m] * np.sqrt(1 - w) + y2[:, :m] * np.sqrt(w)).astype(np.float32)
        L = min(L, y.shape[1])
        y = y[:, :L]
        # mod-wheel volume (smooth), release and legato fades
        g = undb(-20 * (1 - np.clip(dyn[:L], 0, 1)) ** 1.25)
        env = np.ones(L)
        if shape:
            # a bowed/blown note: soft attack, a little swell, a taper before the release
            tt = np.arange(L) / SR
            sw = shape.get("swell", 0.0)
            if sw and n > ns(0.4):
                u = np.clip(tt / max(dur, 1e-3), 0, 1)
                env *= 1 + sw * (np.sin(np.pi * u) ** 1.4 - 0.35)
            tp = shape.get("taper", 0.0)
            if tp and n > ns(0.5):
                u = np.clip((tt - 0.7 * dur) / (0.3 * dur), 0, 1)
                env *= 10 ** (-tp * u / 20)
            at = shape.get("attack", 0.0)
            if at and legato_in is None:
                env *= smoothstep(tt / at) ** 0.8
        if legato_in is not None:
            k = min(L, ns(xf_in if xf_in is not None else self.inst.xfade))
            env[:k] = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
        else:
            k = min(L, 64)
            env[:k] = np.linspace(0, 1, k)
        if n < L:
            t = np.arange(L - n) / SR
            env[n:] *= np.exp(-t / max(rel / 3.0, 1e-3)) * np.cos(np.clip(t / tail, 0, 1) * np.pi / 2)
        y = y * (g * env).astype(np.float32)
        lead = 0 if legato_in is not None else min(max(0, e_lo["attack"] - e_lo["start"]), ns(self.inst.max_lead))
        lead = max(0, lead - ns(self.inst.lag))
        return y, lead, e_lo["file"]


# ----------------------------------------------------------------- part rendering

# the longest stretch of one bow / one breath (s) before a re-bow
REBOW = {"violins": 5.5, "violas": 5.5, "cellos": 6.0, "basses": 6.0, "solo_violin": 6.0,
         "violins_trem": 6.0, "violas_trem": 6.0, "cellos_trem": 6.0,
         "horns": 7.0, "horns_mute": 7.0, "trombones": 7.0, "trombones_vib": 7.0, "tuba": 7.0,
         "flute": 6.0, "flute_nv": 6.0, "clarinet": 7.0, "oboe": 6.0, "bassoon": 6.0,
         "ocarina": 5.0, "ocarina_vib": 5.5}
REBOW_OVERLAP = 0.35


def rebow(notes, limit):
    """Split notes longer than `limit` seconds into near-equal bows that
    overlap by REBOW_OVERLAP; every new bow is a fresh (non-legato) note with
    its own natural attack."""
    from dataclasses import replace as _rep
    out = []
    for n in notes:
        if n.d <= limit + 0.5:
            out.append(n)
            continue
        k = int(math.ceil(n.d / limit))
        seg = n.d / k
        for i in range(k):
            x = dict(n.x)
            if i > 0:
                x["legato"] = False
                x["rebow"] = True
            out.append(_rep(n, t=n.t + i * seg, d=seg + (REBOW_OVERLAP if i < k - 1 else 0.0),
                            v=float(np.clip(n.v * (0.94 if i else 1.0), 0.02, 1)), x=x))
    return out


def _voices(notes):
    from .bowed import split_voices
    return split_voices(notes)


def play(track: Track, notes, inst, *, seed=0, gain_db=0.0, pan=None, width=None, dyn=None, legato=True,
         legato_gap=0.06, xf=None, detune=0.0, layer_bias=0.0, release=None, tail=None, pan_spread=0.0,
         humanize_v=0.05, slide=0.06, double=0, lag=0.0, shape=None):
    """Render notes (times in seconds) with sampler instrument `inst` into
    track. `dyn` is a callable dyn(t_seconds_array) -> 0..1 (mod wheel) for
    sustains. Sustained voices are played legato when notes touch.
    `double` is accepted for old scores but ignored: a detuned, time-offset
    copy of a sample is a chorus, the synth-string sound. Bowed and blown
    notes longer than the instrument's natural breath/bow (`REBOW`) are
    re-bowed: split into overlapping notes, each with its own natural attack,
    instead of looping the sustain."""
    double = 0
    smp = Sampler(inst, seed)
    I = smp.inst
    pan = I.pan if pan is None else pan
    width = I.width if width is None else width
    r = rng("play", inst, seed)
    g0 = undb(gain_db)
    stem = track.like()
    if I.kind == "sus" and inst in REBOW:
        notes = rebow(notes, REBOW[inst])
    if inst.endswith("_pizz") or inst.endswith("_spic"):
        humanize_v = max(humanize_v, 0.12)        # no two plucks alike
    voices = _voices(notes) if I.kind == "sus" else [sorted(notes, key=lambda n: n.t)]
    for vi, voice in enumerate(voices):
        voice = sorted(voice, key=lambda n: n.t)
        prev = None
        for k, nt in enumerate(voice):
            for d in range(double + 1):
                v = float(np.clip(nt.v * (1 + r.normal(0, humanize_v)), 0.02, 1.0))
                # divisi takes: another dynamic layer where there is one, a few cents
                # off, 10-30 ms late, and (for sustains) entering past the attack
                det = detune + (r.uniform(3.0, 6.0) * (-1) ** d if d else 0.0)
                dt = (r.uniform(0.010, 0.030) if d else 0.0) + lag
                lb_d = (0.35 * (-1) ** d if d else 0.0)
                skip_d = (r.uniform(0.05, 0.25) if (d and I.kind == "sus") else 0.0)
                leg = None
                if I.kind == "sus" and legato and prev is not None and nt.x.get("legato", True) and \
                        (nt.t - (prev.t + prev.d)) <= legato_gap and d == 0:
                    leg = prev.p
                dur = nt.d
                nxt = voice[k + 1] if k + 1 < len(voice) else None
                if I.kind == "sus" and legato and nxt is not None and (nxt.t - (nt.t + nt.d)) <= legato_gap and \
                        nxt.x.get("legato", True):
                    # hand over to the next note: overlap by the cross-fade, short tail
                    xfn = xf if xf is not None else I.xfade
                    dur = max(0.05, nxt.t - nt.t + xfn * 0.5)
                    rel_n, tail_n = xfn / 2, xfn
                else:
                    rel_n = nt.x.get("release", release)
                    tail_n = tail
                dy = None
                if I.kind == "sus" and dyn is not None:
                    tt = nt.t + np.arange(ns(dur + (tail_n if tail_n is not None else I.release * 2.5))) / SR
                    dy = np.clip(dyn(tt) + 0.3 * (v - 0.6), 0, 1)
                y, lead, _ = smp.note(nt.p if nt.p > 0 else None, v, dur, dyn=dy, legato_in=leg,
                                      xf_in=xf, release=rel_n, tail=tail_n, detune=det,
                                      layer_bias=layer_bias + lb_d + nt.x.get("layer_bias", 0.0), slide=slide,
                                      shape=shape if I.kind == "sus" else None, skip=skip_d,
                                      bend=nt.x.get("bend"), vib=nt.x.get("vib"))
                pn = pan + nt.x.get("pan", 0.0) + (r.uniform(-pan_spread, pan_spread) if pan_spread else 0.0) + \
                    (0.12 * (-1) ** d if d else 0.0)
                stem.add(nt.t + dt - (0 if leg is not None else (nt.x.get("xf_pre", 0.0))) - lead / SR, y,
                         gain=g0 * nt.x.get("gain", 1.0) * (0.75 if d else 1.0), pan=float(np.clip(pn, -1, 1)),
                         width=width)
            prev = nt
    track.mix(stem)
    return track


class Curve:
    """A smooth control curve through (time_s, value) points (cosine
    interpolation), usable as dyn= for play(). Periodic when `period` is set."""

    def __init__(self, pts, period=None):
        self.t = np.array([p[0] for p in pts], float)
        self.v = np.array([p[1] for p in pts], float)
        self.period = period

    def __call__(self, t):
        t = np.asarray(t, float)
        if self.period:
            t = np.mod(t, self.period)
        idx = np.clip(np.searchsorted(self.t, t, side="right") - 1, 0, len(self.t) - 2)
        t0, t1 = self.t[idx], self.t[idx + 1]
        v0, v1 = self.v[idx], self.v[idx + 1]
        u = np.clip((t - t0) / np.maximum(t1 - t0, 1e-9), 0, 1)
        u = 0.5 - 0.5 * np.cos(np.pi * u)
        out = v0 + (v1 - v0) * u
        out = np.where(t < self.t[0], self.v[0], out)
        out = np.where(t > self.t[-1], self.v[-1], out)
        return out
