"""Helpers shared by the rescored pieces: sampled sections on a stage, the
electronic layers, and the finishing chain (tape warmth + glue + loudness)."""
from __future__ import annotations

import numpy as np

from .core import SR, ns, rng
from .score import N, voicing, chord_pcs, humanize
from . import sampler as SM
from . import effects as FX
from .piece import Mix

# Where each section sits: pan, width, and depth (0 = near, 1 = far). Depth
# sets how wet the section is, how much of its dry signal is kept and how
# dark its dry signal is: wetter and darker means further away.
SEAT = {
    "violins": dict(pan=-0.48, width=0.75, depth=0.55),
    "violins2": dict(pan=-0.22, width=0.6, depth=0.6),
    "violas": dict(pan=0.12, width=0.6, depth=0.6),
    "cellos": dict(pan=0.36, width=0.6, depth=0.58),
    "basses": dict(pan=0.52, width=0.45, depth=0.62),
    "horns": dict(pan=-0.3, width=0.55, depth=0.85),
    "trombones": dict(pan=0.26, width=0.45, depth=0.85),
    "tuba": dict(pan=0.4, width=0.35, depth=0.85),
    "timpani": dict(pan=-0.05, width=0.7, depth=0.8),
    "piano": dict(pan=0.0, width=0.8, depth=0.4),
    "harp": dict(pan=-0.4, width=0.55, depth=0.55),
    "glock": dict(pan=0.3, width=0.5, depth=0.8),
    "organ": dict(pan=0.0, width=1.0, depth=0.85),
    "glass": dict(pan=0.0, width=1.0, depth=0.6),
    "solo_violin": dict(pan=-0.12, width=0.35, depth=0.45),
    "flutes": dict(pan=-0.18, width=0.4, depth=0.72),
    "clarinets": dict(pan=0.16, width=0.4, depth=0.72),
    "oboe": dict(pan=0.0, width=0.35, depth=0.74),
    "bassoon": dict(pan=0.24, width=0.35, depth=0.74),
    "marimba": dict(pan=0.1, width=0.6, depth=0.5),
    "triangle": dict(pan=0.35, width=0.4, depth=0.85),
    "sleighbells": dict(pan=0.3, width=0.6, depth=0.85),
    "belltree": dict(pan=-0.3, width=0.8, depth=0.85),
    # the title's groove: the stand-up bass near and centre, the hand drums around it
    "basses_pizz": dict(pan=0.04, width=0.35, depth=0.3),
    "congas": dict(pan=0.3, width=0.45, depth=0.55),
}

# Per-instrument tone: tame the close-mic attack and the 2-6 kHz edge, warm
# the low mids, roll off the very top (the depth low-pass comes on top).
TONE = {
    # strings: the bow's own attack and some air are what make them real, so
    # they get only a light softener and a gentle top
    "violins": dict(soften=0.1, eq=[("peak", 250, 0.9, 1.0), ("peak", 3000, 0.9, -2.0), ("peak", 5200, 1.2, -1.0),
                                    ("hs", 8500, 0.7, -2.5)]),
    "violas": dict(soften=0.1, eq=[("peak", 250, 0.9, 1.0), ("peak", 2800, 0.9, -1.5), ("hs", 8000, 0.7, -2.5)]),
    "cellos": dict(soften=0.1, eq=[("peak", 200, 0.9, 1.0), ("peak", 2600, 0.9, -1.5), ("hs", 7500, 0.7, -2.5)]),
    "basses": dict(soften=0.1, eq=[("peak", 2200, 0.9, -1.5), ("hs", 6500, 0.7, -3.0)]),
    "violins_spic": dict(soften=0.25, eq=[("peak", 3000, 0.9, -2.5), ("peak", 5500, 1.2, -1.5), ("hs", 8000, 0.7, -3.0)]),
    "violas_spic": dict(soften=0.25, eq=[("peak", 2800, 0.9, -2.0), ("hs", 7500, 0.7, -3.0)]),
    "cellos_spic": dict(soften=0.25, eq=[("peak", 2600, 0.9, -2.0), ("hs", 7000, 0.7, -3.0)]),
    "basses_spic": dict(soften=0.2, eq=[("peak", 2200, 0.9, -2.0), ("hs", 6000, 0.7, -3.0)]),
    "horns": dict(soften=0.4, eq=[("peak", 300, 0.8, 1.5), ("peak", 2400, 0.9, -3.0), ("hs", 4500, 0.7, -6.0)]),
    "horns_mute": dict(soften=0.4, eq=[("peak", 300, 0.8, 1.0), ("peak", 2400, 0.9, -2.5), ("hs", 4500, 0.7, -5.0)]),
    "horns_stac": dict(soften=0.6, eq=[("peak", 300, 0.8, 1.5), ("peak", 2400, 0.9, -3.0), ("hs", 4500, 0.7, -6.0)]),
    "trombones": dict(soften=0.4, eq=[("peak", 250, 0.8, 1.0), ("peak", 2200, 0.9, -3.0), ("hs", 4000, 0.7, -6.0)]),
    "trombones_vib": dict(soften=0.4, eq=[("peak", 250, 0.8, 1.0), ("peak", 2200, 0.9, -3.0), ("hs", 4000, 0.7, -6.0)]),
    "trombones_stac": dict(soften=0.6, eq=[("peak", 2200, 0.9, -3.0), ("hs", 4000, 0.7, -6.0)]),
    "tuba": dict(soften=0.4, eq=[("peak", 1800, 0.9, -2.0), ("hs", 3500, 0.7, -6.0)]),
    "tuba_stac": dict(soften=0.6, eq=[("peak", 1800, 0.9, -2.0), ("hs", 3500, 0.7, -6.0)]),
    "organ": dict(soften=0.2, eq=[("peak", 220, 0.8, 1.5), ("peak", 3500, 0.9, -2.5), ("hs", 6500, 0.7, -4.0)]),
    "organ_pedal": dict(soften=0.2, eq=[("peak", 2500, 0.9, -2.0), ("hs", 5000, 0.7, -4.0)]),
    "organ_soft": dict(soften=0.2, eq=[("peak", 220, 0.8, 1.5), ("peak", 3500, 0.9, -2.0), ("hs", 6500, 0.7, -3.5)]),
    "organ_soft_pedal": dict(soften=0.2, eq=[("peak", 2500, 0.9, -2.0), ("hs", 5000, 0.7, -4.0)]),
    # felt-piano: a soft hammer, a warm body and no top
    "piano": dict(soften=0.65, eq=[("peak", 180, 0.8, 2.0), ("peak", 2500, 0.8, -3.0), ("hs", 3200, 0.7, -5.0),
                                   ("lp", 6000, 0.6)]),
    "harp": dict(soften=0.55, eq=[("peak", 200, 0.8, 1.0), ("peak", 3000, 0.9, -2.5), ("hs", 5000, 0.7, -5.0)]),
    # the Spanish classical guitar (FreePats): its recordings were denoised dark, so the nail's presence
    # is given back (the attack kept, 3 kHz lifted) and the body's boom tamed
    "nylon": dict(soften=0.08, eq=[("hp", 80, 0.7), ("peak", 230, 0.8, -2.5), ("peak", 3000, 0.7, 3.0),
                                   ("hs", 9000, 0.7, -2.0)]),
    "glock": dict(soften=0.85, eq=[("hs", 3000, 0.7, -6.0), ("lp", 5200, 0.7), ("lp", 6000, 0.7)]),
    "timpani": dict(soften=0.35, eq=[("peak", 2500, 0.9, -2.0), ("hs", 5000, 0.7, -4.0)]),
    "timpani_roll": dict(soften=0.2, eq=[("hs", 5000, 0.7, -4.0)]),
    "bass_drum": dict(soften=0.4, eq=[("lp", 4000, 0.7)]),
    "violins_pizz": dict(soften=0.2, eq=[("peak", 250, 0.9, 1.0), ("peak", 3000, 0.9, -2.0), ("hs", 7500, 0.7, -3.0)]),
    "violas_pizz": dict(soften=0.2, eq=[("peak", 220, 0.9, 1.0), ("peak", 2800, 0.9, -2.0), ("hs", 7500, 0.7, -3.0)]),
    "cellos_pizz": dict(soften=0.2, eq=[("peak", 2500, 0.9, -2.0), ("hs", 6500, 0.7, -3.0)]),
    "violins_trem": dict(soften=0.15, eq=[("peak", 3000, 0.9, -2.5), ("peak", 5500, 1.2, -1.5), ("hs", 8000, 0.7, -3.0)]),
    "violas_trem": dict(soften=0.15, eq=[("peak", 2800, 0.9, -2.0), ("hs", 7500, 0.7, -3.0)]),
    "cellos_trem": dict(soften=0.15, eq=[("peak", 2600, 0.9, -2.0), ("hs", 7000, 0.7, -3.0)]),
    "solo_violin": dict(soften=0.15, eq=[("peak", 280, 0.9, 1.5), ("peak", 2900, 0.9, -2.5), ("peak", 4300, 1.0, -3.0),
                                         ("hs", 8000, 0.7, -3.0)]),
    "flute": dict(soften=0.3, eq=[("peak", 2800, 0.9, -2.0), ("hs", 6500, 0.7, -5.0)]),
    "flute_nv": dict(soften=0.3, eq=[("peak", 2800, 0.9, -2.0), ("hs", 6500, 0.7, -5.0)]),
    "flute_stac": dict(soften=0.5, eq=[("peak", 2800, 0.9, -2.5), ("hs", 6000, 0.7, -5.0)]),
    "clarinet": dict(soften=0.3, eq=[("peak", 250, 0.9, 1.0), ("peak", 3000, 0.9, -2.5), ("hs", 6000, 0.7, -5.0)]),
    "clarinet_stac": dict(soften=0.5, eq=[("peak", 3000, 0.9, -3.0), ("hs", 6000, 0.7, -5.0)]),
    "oboe": dict(soften=0.35, eq=[("peak", 1400, 0.8, -1.5), ("peak", 3200, 0.9, -3.5), ("hs", 5500, 0.7, -6.0)]),
    "oboe_stac": dict(soften=0.5, eq=[("peak", 1400, 0.8, -1.5), ("peak", 3200, 0.9, -3.5), ("hs", 5500, 0.7, -6.0)]),
    "bassoon": dict(soften=0.3, eq=[("peak", 2500, 0.9, -2.5), ("hs", 5000, 0.7, -5.0)]),
    "bassoon_stac": dict(soften=0.5, eq=[("peak", 2500, 0.9, -2.5), ("hs", 5000, 0.7, -5.0)]),
    "marimba": dict(soften=0.6, eq=[("peak", 200, 0.8, 1.5), ("peak", 3000, 0.9, -3.0), ("hs", 5000, 0.7, -5.0)]),
    "triangle": dict(soften=0.8, eq=[("hs", 4000, 0.7, -6.0), ("lp", 7000, 0.7)]),
    "sleighbells": dict(soften=0.7, eq=[("hs", 4000, 0.7, -6.0), ("lp", 7000, 0.7)]),
    "belltree": dict(soften=0.6, eq=[("hs", 4500, 0.7, -5.0), ("lp", 7500, 0.7)]),
    # the stand-up bass: its wood (90 Hz) kept and the boom above it (250 Hz) tamed, the finger's click
    # rounded off
    "basses_pizz": dict(soften=0.3, eq=[("hp", 35, 0.7), ("peak", 90, 0.8, 1.5), ("peak", 260, 0.8, -3.0),
                                        ("peak", 1200, 0.9, 1.0), ("hs", 4500, 0.7, -5.0)]),
    # the hand drums: the skin's tone, the slap's click softened
    "conga": dict(soften=0.45, eq=[("peak", 250, 0.8, 1.0), ("hs", 4000, 0.7, -6.0)]),
    "tumba": dict(soften=0.45, eq=[("peak", 180, 0.8, 1.5), ("hs", 4000, 0.7, -6.0)]),
}

HALL = "concert"


class Stage:
    """A Mix with one stem per section, seated by depth in a hall."""

    def __init__(self, seconds, circular=True, hall=HALL, organ_hall="cathedral2"):
        self.mix = Mix(seconds, circular)
        self.hall = hall
        self.organ_hall = organ_hall
        self.stems = {}
        self.sends = {}
        self.depth = {}

    def stem(self, name, sends=None, depth=None, seat=None, room=0.0):
        if name not in self.stems:
            self.stems[name] = self.mix.track()
            sd = SEAT.get(seat or name, SEAT.get(name, {}))
            dp = sd.get("depth", 0.5) if depth is None else depth
            self.depth[name] = dp
            if sends is None:
                hall = self.organ_hall if (seat or name).startswith("organ") else self.hall
                sends = {hall: 0.3 + 0.75 * dp}
                if room:                      # a little room so plucks bloom
                    sends["chamber"] = room
            self.sends[name] = sends
        return self.stems[name]

    def play(self, section, notes, inst, seat=None, depth=None, sends=None, tone=True, **kw):
        s = SEAT.get(seat or section, SEAT.get(section, {}))
        kw.setdefault("pan", s.get("pan"))
        kw.setdefault("width", s.get("width"))
        stem = self.stem(section, sends=sends, depth=depth, seat=seat,
                         room=0.3 if inst.endswith("_pizz") else 0.0)
        tmp = stem.like()
        SM.play(tmp, notes, inst, **kw)
        if tone and inst in TONE:
            tn = TONE[inst]
            buf = tmp.buf.astype(np.float64)
            if tn.get("soften"):
                buf = FX.soften(buf, tn["soften"], circular=tmp.circular)
            buf = FX.eq(buf, *tn["eq"], circular=tmp.circular)
            tmp.buf = buf.astype(np.float32)
        stem.mix(tmp)

    def render(self, opts=None, warmth=0.3, gains=None, air=-54.0):
        gains = gains or {}
        opts = opts or {}
        for name, tr in self.stems.items():
            dp = self.depth.get(name, 0.5)
            # distance: less dry, darker dry
            dry_gain = gains.get(name, 1.0)
            buf = tr.buf.astype(np.float64)
            lp = 18000 - 8000 * dp
            buf_dry = FX.eq(buf, ("lp", lp, 0.6), circular=tr.circular) * (10 ** (-7.0 * dp / 20))
            self.mix.dry.mix(buf_dry, dry_gain)
            for key, amt in self.sends[name].items():
                if key not in self.mix.sends:
                    self.mix.sends[key] = self.mix.track()
                self.mix.sends[key].mix(buf, dry_gain * amt)
            if dp is not None:
                from .master import lufs
                from .qa import tone_check
                e_dry = float(np.sum(buf_dry ** 2)) + 1e-20
                e_wet = float(np.sum(buf ** 2)) * sum(a * a for a in self.sends[name].values()) * 1.19 + 1e-20
                ex, at = tone_check(buf)
                print(f"    stem {name:14s} {lufs(buf * dry_gain):6.1f} LUFS  depth {dp:.2f}  "
                      f"D/R {10 * np.log10(e_dry / e_wet):+5.1f} dB  top-end excess {ex:+.1f} dB@{at}", flush=True)
        for key in list(self.mix.sends):
            opts.setdefault(key, {})
            if not key.startswith(("echo:", "shimmer:")):
                opts[key].setdefault("seed", 7)
        out = self.mix.render(opts)
        if warmth:
            out = tape(out, warmth, self.mix.circular)
        if air is not None:
            out = add_air(out, air, self.mix.circular)
        return out


def add_air(x, rel_db=-54.0, circular=True):
    """A breath of hall air under everything (soft, dark, slowly moving)."""
    from .core import colored, smooth_random
    n = x.shape[1]
    r = rng("air")
    a = np.vstack([colored(n, rng("air", c), -4.0, lo=60, hi=2500) for c in range(2)])
    a *= 0.8 + 0.2 * smooth_random(n, r, 0.1, circular=circular) * 2
    lvl = np.sqrt(np.mean(x ** 2)) * 10 ** (rel_db / 20)
    return x + a * lvl


def organ_body(notes, octave=-12, vel=0.6):
    """Octave doubling for organ body (an extra rank)."""
    from dataclasses import replace
    return [replace(n, p=n.p + octave, v=float(n.v * vel), x=dict(n.x)) for n in notes]


def tape(x, amount=0.3, circular=True):
    """Light tape warmth: soft saturation, a touch of low-mid body, and
    rounded top end."""
    pk = np.max(np.abs(x)) + 1e-9
    y = FX.saturate(x / pk, drive=1.0 + 1.2 * amount, mix=0.5 * amount + 0.2, even=0.06) * pk
    return FX.eq(y, ("peak", 180, 0.8, 0.8 * amount), ("hs", 9500, 0.7, -2.0 * amount), circular=circular)


def ostinato(pr, low, high, step, pattern, vel=0.6, n_tones=5, accents=None, dur=None, start=None, end=None):
    """Repeating figure through a chord progression: `pattern` indexes the
    voiced chord tones (0 = lowest), one note per `step` beats."""
    out = []
    prev = None
    for (t0, d, sym) in pr:
        if start is not None and t0 + d <= start:
            continue
        if end is not None and t0 >= end:
            continue
        v = voicing(sym, low, high, n_tones, prev)
        prev = v
        k = 0
        t = t0
        while t < t0 + d - 1e-6:
            if (start is None or t >= start) and (end is None or t < end):
                idx = pattern[k % len(pattern)]
                if idx is not None:
                    p = v[idx % len(v)] + 12 * (idx // len(v))
                    vv = vel * (accents[k % len(accents)] if accents else 1.0)
                    out.append(N(t, dur if dur else step * 0.9, float(p), float(np.clip(vv, 0.02, 1))))
            t += step
            k += 1
    return out


def sustain_chords(pr, low, high, n, vel=0.6, overlap=0.15, start=None, end=None):
    """Voice-led held chords (one note per chord tone) for pads/strings."""
    out = []
    prev = None
    for (t0, d, sym) in pr:
        if (start is not None and t0 + d <= start) or (end is not None and t0 >= end):
            continue
        v = voicing(sym, low, high, n, prev)
        prev = v
        for p in v:
            out.append(N(t0, d + overlap, float(p), vel))
    return out


def roots(pr, low, vel=0.6, start=None, end=None, overlap=0.1):
    out = []
    for (t0, d, sym) in pr:
        if (start is not None and t0 + d <= start) or (end is not None and t0 >= end):
            continue
        pcs, bass, root = chord_pcs(sym)
        b = low + ((bass - low) % 12)
        out.append(N(t0, d + overlap, float(b), vel))
    return out


def window(notes, t0, t1):
    return [n for n in notes if t0 <= n.t < t1]
