"""Mixing desk and output: buses with reverb sends, mastering, loop assembly,
MP3 encoding with post-encode verification, QA pictures and the manifest."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .core import SR, ns, undb, db, Track
from . import effects as FX
from . import master as M
from . import qa

ROOT = Path(__file__).resolve().parents[3]          # project root
OUT = ROOT / "public" / "audio"
CACHE = Path(__file__).resolve().parents[1] / ".cache"
MANIFEST = OUT / "manifest.json"
VERBOSE = True


class Mix:
    """Collects stems into a dry bus plus reverb send buses."""

    def __init__(self, seconds, circular=True):
        self.seconds = seconds
        self.circular = circular
        self.dry = Track(seconds, circular)
        self.sends: dict = {}

    def track(self):
        return Track(self.seconds, self.circular)

    def add(self, stem, gain=1.0, sends=None, pan=0.0, name=None):
        buf = stem.buf if isinstance(stem, Track) else np.asarray(stem, dtype=np.float32)
        if name and VERBOSE:
            lu = M.lufs(buf.astype(np.float64) * gain)
            print(f"    stem {name:14s} {lu:6.1f} LUFS", flush=True)
        self.dry.mix(buf, gain)
        for key, amt in (sends or {}).items():
            if key not in self.sends:
                self.sends[key] = Track(self.seconds, self.circular)
            self.sends[key].mix(buf, gain * amt)
        return self

    def render(self, reverb_opts=None):
        """Sum dry + every send through its effect. Send keys: a space name from
        effects.SPACES, 'shimmer:<space>', or 'echo:<seconds>'."""
        reverb_opts = reverb_opts or {}
        out = self.dry.buf.astype(np.float64)
        n = out.shape[1]
        for key, tr in self.sends.items():
            x = tr.buf.astype(np.float64)
            opts = reverb_opts.get(key, {})
            if key.startswith("shimmer:"):
                y = FX.shimmer(x, key.split(":", 1)[1], circular=self.circular, **opts)
            elif key.startswith("echo:"):
                y = FX.echo(x, float(key.split(":", 1)[1]), circular=self.circular, **opts)
            else:
                y = FX.reverb(x, key, circular=self.circular, **opts)
            if y.shape[1] > n:
                out = np.pad(out, ((0, 0), (0, y.shape[1] - n)))
                n = out.shape[1]
            out[:, : y.shape[1]] += y
        return out


# ----------------------------------------------------------------- manifest

def _load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"motif": {}, "music": {}, "ambience": {}, "sfx": {}}


def update_manifest(section, key, entry):
    """Read-modify-write the manifest under a file lock (parallel renders)."""
    import fcntl
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / "manifest.lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        man = _load_manifest()
        man.setdefault(section, {})
        if section == "motif":
            man["motif"] = entry
        else:
            man[section][key] = entry
            man[section] = dict(sorted(man[section].items()))
        tmp = MANIFEST.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(man, indent=2) + "\n")
        tmp.replace(MANIFEST)
        fcntl.flock(lk, fcntl.LOCK_UN)


def _log(msg):
    print(msg, flush=True)


def _qa(name, y, kind):
    try:
        qa.spectrogram_png(y, CACHE / "qa" / f"{kind}-{name}.png", f"{kind}/{name}")
    except Exception as e:  # pictures are a nicety, never fail a render for them
        _log(f"  (qa picture failed: {e})")
    M.write_wav(CACHE / "wav" / f"{kind}-{name}.wav", y)


def _encode_verified(y, path, kbps, target_lufs, tp_max=-1.6, mono=False, tries=4, lufs_tol=0.35,
                     measure_lufs=True):
    """Encode, measure the MP3, nudge gain/ceiling until it lands. Returns (y, I, TP)."""
    g = 0.0
    ceiling = None
    for i in range(tries):
        z = y * undb(g)
        if ceiling is not None:
            z = M.limit(z, ceiling)
        M.encode_mp3(z, path, kbps, mono)
        I, TP = M.measure_file(path)
        ok_tp = TP <= tp_max
        ok_I = (not measure_lufs) or abs(I - target_lufs) <= lufs_tol
        if ok_tp and ok_I:
            return z, I, TP
        if measure_lufs and not ok_I:
            g += target_lufs - I
        if not ok_tp:
            ceiling = (ceiling if ceiling is not None else M.true_peak_db(y * undb(g))) - (TP - tp_max) - 0.2
            if not measure_lufs:
                g -= (TP - tp_max) + 0.1
                ceiling = None
    return z, I, TP


def finish_loop(kind, name, x, loop_seconds, tail_seconds, target_lufs, kbps, meta=None,
                ceiling=-2.2, glue=True, tilt_hs_db=-1.0):
    """Master a circular mix and write <kind>/<name>.mp3 = loop + wrapped tail."""
    t0 = time.time()
    n = ns(loop_seconds)
    assert x.shape[1] == n, (x.shape, n)
    y = M.master(x, target_lufs, ceiling, circular=True, glue=glue, tilt_hs_db=tilt_hs_db)
    tail = ns(tail_seconds)
    full = np.concatenate([y, y[:, :tail]], axis=1)
    corr = M.loop_correlation(full, n, tail)
    st = qa.stats(y)
    path = OUT / kind / f"{name}.mp3"
    full, I, TP = _encode_verified(full, path, kbps, target_lufs)
    _qa(name, full, kind)
    entry = {"file": f"{kind}/{name}.mp3", "loopSeconds": round(loop_seconds, 3), "tailSeconds": tail_seconds}
    if meta:
        entry.update(meta)
    update_manifest(kind, name, entry)
    size = path.stat().st_size
    _log(f"  {kind}/{name}: loop {loop_seconds:.2f}s + {tail_seconds}s, seam corr {corr:.6f}, "
         f"mp3 I {I:.1f} LUFS, TP {TP:.1f} dBTP, hf>8k {st['hf8k_db']} dB, dc {st['dc']:.1e}, "
         f"{size / 1e6:.2f} MB, {time.time() - t0:.0f}s")
    return dict(I=I, TP=TP, corr=corr, size=size, stats=st)


def trim_silence(y, floor_db=-66.0, fade=0.08, keep_tail=0.05):
    a = np.max(np.abs(np.atleast_2d(y)), axis=0)
    above = np.nonzero(a > undb(floor_db))[0]
    end = int(above[-1]) + ns(keep_tail) if above.size else ns(0.05)
    end = min(end, y.shape[-1])
    y = y[..., :end].copy()
    k = min(ns(fade), end)
    y[..., end - k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return y


def finish_oneshot(kind, name, x, target_lufs, kbps, meta=None, ceiling=-2.2, glue=True, tilt_hs_db=-1.0,
                   max_s=None, end_fade=4.0):
    t0 = time.time()
    y = M.master(x, target_lufs, ceiling, circular=False, glue=glue, tilt_hs_db=tilt_hs_db)
    y = trim_silence(y, -60.0, fade=0.5)
    if max_s is not None and y.shape[1] > ns(max_s):
        y = y[:, : ns(max_s)].copy()
        k = ns(min(end_fade, max_s / 3))
        y[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    st = qa.stats(y)
    path = OUT / kind / f"{name}.mp3"
    y, I, TP = _encode_verified(y, path, kbps, target_lufs)
    _qa(name, y, kind)
    entry = {"file": f"{kind}/{name}.mp3", "oneShot": True, "seconds": round(y.shape[1] / SR, 2)}
    if meta:
        entry.update(meta)
    update_manifest(kind, name, entry)
    size = path.stat().st_size
    _log(f"  {kind}/{name}: {y.shape[1] / SR:.1f}s, mp3 I {I:.1f} LUFS, TP {TP:.1f} dBTP, "
         f"hf>8k {st['hf8k_db']} dB, {size / 1e6:.2f} MB, {time.time() - t0:.0f}s")
    return dict(I=I, TP=TP, size=size, stats=st)


_SFX_GROUPS: dict = {}


def _trim_tail(x, floor_db=-52.0, max_s=None, fade_max=0.35):
    """Cut the tail where the 20 ms RMS envelope falls below floor_db (relative
    to full scale after normalising) or at max_s, with a smooth fade."""
    from scipy.ndimage import uniform_filter1d
    a = np.sqrt(uniform_filter1d(np.mean(x ** 2, axis=0), ns(0.02)) + 1e-20)
    above = np.nonzero(a > undb(floor_db))[0]
    end = int(above[-1]) if above.size else ns(0.05)
    if max_s is not None:
        end = min(end, ns(max_s))
    end = min(end, x.shape[1])
    x = x[:, :end].copy()
    k = min(ns(fade_max), int(end * 0.3))
    if k > 1:
        x[:, end - k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return x


def finish_sfx(group, name, x, peak_db=-3.0, stereo=False, kbps=96, floor_db=-52.0, max_s=None, loop=False):
    """Peak-normalise (true peak), trim, encode one sfx; record it in its group.
    loop=True keeps the exact length (a seamless, circularly rendered loop)."""
    x = np.atleast_2d(np.asarray(x, dtype=np.float64))
    if not stereo and x.shape[0] == 2:
        x = x.mean(axis=0, keepdims=True)
    if stereo and x.shape[0] == 1:
        x = np.vstack([x, x])
    x = FX.dc_block(x, circular=loop)
    tp = M.true_peak_db(x)
    x = x * undb(peak_db - tp)
    if not loop:
        x = _trim_tail(x, floor_db, max_s)
        # tiny fade-in so nothing starts with a click
        k = min(ns(0.0015), x.shape[1])
        x[..., :k] *= np.linspace(0, 1, k)
    path = OUT / "sfx" / f"{name}.mp3"
    x, I, TP = _encode_verified(x, path, kbps, 0, tp_max=min(-1.6, peak_db + 0.6), mono=not stereo,
                                measure_lufs=False)
    M.write_wav(CACHE / "wav" / f"sfx-{name}.wav", x)
    _SFX_GROUPS.setdefault(group, {})[name] = f"sfx/{name}.mp3"
    man = _load_manifest()
    files = dict((Path(f).stem, f) for f in man.get("sfx", {}).get(group, []))
    files.update(_SFX_GROUPS[group])
    update_manifest("sfx", group, [files[k] for k in sorted(files, key=_natural)])
    _log(f"  sfx/{name}: {x.shape[1] / SR:.2f}s {'stereo' if stereo else 'mono'}, TP {TP:.1f} dBTP, "
         f"{path.stat().st_size / 1e3:.0f} kB")
    return TP


def _natural(s):
    import re
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]
