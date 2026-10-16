#!/usr/bin/env python3
"""Render Hallowed Lanterns audio.

    python3 tools/audio/render.py arbor               # music + ambience called "arbor"
    python3 tools/audio/render.py music:arbor sfx:footsteps
    python3 tools/audio/render.py --all [-j 3]
    python3 tools/audio/render.py --list

Re-runs itself inside tools/audio/.venv (numpy, scipy, numba) when needed.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / "bin" / "python"


def _ensure_env():
    try:
        import numba  # noqa: F401
        import scipy  # noqa: F401
        return
    except ImportError:
        pass
    if VENV_PY.exists() and Path(sys.prefix).resolve() != (HERE / ".venv").resolve():
        os.execv(str(VENV_PY), [str(VENV_PY), __file__, *sys.argv[1:]])
    sys.exit("Missing packages. Create the venv first:\n"
             "  python3 -m venv tools/audio/.venv\n"
             "  tools/audio/.venv/bin/pip install -r tools/audio/requirements.txt")


_ensure_env()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "pieces"))

KINDS = ("music", "ambience", "sfx")


def targets():
    out = {}
    for kind in KINDS:
        d = HERE / "pieces" / kind
        for f in sorted(d.glob("*.py")):
            if f.stem.startswith("_"):
                continue
            out[f"{kind}:{f.stem}"] = (kind, f.stem)
    return out


def resolve(names, all_t):
    sel = []
    for nm in names:
        nm = nm.replace("-", "_")
        if nm in all_t:
            sel.append(nm)
            continue
        hits = [k for k in all_t if k.split(":", 1)[1] == nm or k.split(":", 1)[0] == nm]
        if not hits:
            sys.exit(f"unknown target {nm!r}; try --list")
        sel += hits
    seen = set()
    return [s for s in sel if not (s in seen or seen.add(s))]


def run_one(key):
    kind, stem = key.split(":", 1)
    t0 = time.time()
    print(f"[{key}] rendering…", flush=True)
    mod = importlib.import_module(f"{kind}.{stem}")
    mod.render()
    print(f"[{key}] done in {time.time() - t0:.0f}s", flush=True)


SYNTH = "Synthesised with tools/audio (Hallowed Lanterns)"
VSCO_MUSIC = ("Composed with tools/audio (Hallowed Lanterns), using VSCO 2 Community Edition orchestral samples "
              "(CC0, Versilian Studios)")
VSCO_SFX = "Made with tools/audio (Hallowed Lanterns), using VSCO 2 Community Edition samples (CC0, Versilian Studios)"
VCSL_MUSIC = (VSCO_MUSIC + " and Versilian Community Sample Library samples (CC0, Versilian Studios: "
              "https://github.com/sgossner/VCSL)")
# The music that also plays VCSL instruments (vibraphone, zither, gong, finger cymbals, woodblock, ocarina, shaker).
USES_VCSL = ("arbor", "garden", "marigold", "snow")
FREEPATS_GUITAR = (" and the FreePats Spanish classical guitar (CC0, the FreePats project: "
                   "https://freepats.zenvoid.org/Guitar/acoustic-guitar.html)")
# The music that also plays the FreePats guitar (none now: the Marigold no longer does).
USES_FREEPATS = ()
MEATBASS = (" and Karoryfer's Meatbass double bass (CC0, Karoryfer Samples: "
            "https://github.com/sfzinstruments/karoryfer.meatbass)")
# The music that also plays the Meatbass double bass.
USES_MEATBASS = ("snow",)
IOWA_WOODWINDS = (" and the University of Iowa Musical Instrument Samples' clarinet and bassoon (Electronic Music "
                  "Studios, University of Iowa; free for any use: https://theremin.music.uiowa.edu/MIS.html)")
# The music whose clarinet and bassoon are the Iowa recordings.
USES_IOWA = ("picture-show",)
# Credit lines this file once wrote, so the lock's old entries are still ours to correct.
FORMER = (VCSL_MUSIC + FREEPATS_GUITAR,)
SAMPLED_SFX = ("xylo-", "guitar-", "ember-chime-", "snowflake-", "sprinkle-burst", "wish-hang")
# The ambiences with recorded wind in them, and the recordings they use (hlaudio/recordings.py).
RECORDED_WIND = {"arbor": ("0907",), "garden": ("0907",), "grove": ("0907", "0595"), "hollow": ("0907",),
                 "marigold": ("0907",), "pasture": ("0595", "1880"), "snow": ("0595",)}


def _passage_source():
    from hlaudio.recordings import WIND
    title, page = WIND["0595"]
    return (VSCO_SFX + f", and wind recorded by Joseph Sardin (BigSoundBank, CC0): \"{title}\" ({page})")


def _wind_source(name):
    from hlaudio.recordings import ambience_source
    return ambience_source(RECORDED_WIND[name])


def source_for(path):
    name = path.rsplit("/", 1)[-1]
    if "/audio/music/" in path:
        piece = name.removesuffix(".mp3")
        base = VCSL_MUSIC if piece in USES_VCSL else VSCO_MUSIC
        return (base + (FREEPATS_GUITAR if piece in USES_FREEPATS else "") + (MEATBASS if piece in USES_MEATBASS else "")
                + (IOWA_WOODWINDS if piece in USES_IOWA else ""))
    if "/audio/sfx/" in path and name.startswith("passage-final"):
        return _passage_source() + "; its far bell from the Versilian Community Sample Library (CC0, Versilian Studios)"
    if "/audio/sfx/" in path and name.startswith("passage-"):
        return _passage_source()
    if "/audio/sfx/" in path and name.startswith(SAMPLED_SFX):
        return VSCO_SFX
    if "/audio/ambience/" in path and name.removesuffix(".mp3") in RECORDED_WIND:
        return _wind_source(name.removesuffix(".mp3"))
    return SYNTH


def update_lock():
    """Add an entry for every file in public/audio to assets.lock.json (merging
    with whatever else is there; re-read right before writing), and keep the
    source line of our own entries right (music and the instrument-like sfx
    use the VSCO 2 CE samples). Entries with any other source (e.g. recorded
    footsteps) are never touched."""
    root = HERE.parents[1]
    files = sorted(p for p in (root / "public" / "audio").rglob("*") if p.is_file())
    entries = [{"path": str(p.relative_to(root)).replace(os.sep, "/"), "license": "own"} for p in files
               if p.suffix in (".mp3", ".json")]
    for e in entries:
        e["source"] = source_for(e["path"])
    lock = root / "assets.lock.json"
    ours = {SYNTH, VSCO_MUSIC, VCSL_MUSIC, VSCO_SFX, _passage_source(), source_for("public/audio/sfx/passage-final.mp3"),
            *(source_for(f"public/audio/music/{p}.mp3") for p in USES_FREEPATS + USES_MEATBASS + USES_IOWA), *FORMER,
            *(_wind_source(k) for k in RECORDED_WIND)}

    def merged(data):
        assets = data.setdefault("assets", [])
        have = {a.get("path") for a in assets}
        n = 0
        for a in assets:
            if a.get("source") in ours and a.get("path", "").startswith("public/audio/"):
                want = source_for(a["path"])
                if a["source"] != want:
                    a["source"] = want
                    n += 1
        added = [e for e in entries if e["path"] not in have]
        assets.extend(added)
        return n + len(added)

    data = json.loads(lock.read_text()) if lock.exists() else {"assets": []}
    if not merged(data):
        return 0
    # re-read immediately before writing, in case someone else changed it meanwhile
    data = json.loads(lock.read_text()) if lock.exists() else {"assets": []}
    n = merged(data)
    lock.write_text(json.dumps(data, indent=2) + "\n")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=1, help="parallel renders (each uses ~1-2 GB)")
    ap.add_argument("--no-lock", action="store_true", help="don't touch assets.lock.json")
    a = ap.parse_args()
    all_t = targets()
    if a.list:
        for k in all_t:
            print(k)
        return
    sel = list(all_t) if a.all else resolve(a.names, all_t)
    if not sel:
        ap.print_help()
        return
    from hlaudio.piece import update_manifest
    from hlaudio import theme
    update_manifest("motif", None, theme.manifest_entry())
    if a.jobs > 1 and len(sel) > 1:
        procs = []
        pending = list(sel)
        failed = []
        while pending or procs:
            while pending and len(procs) < a.jobs:
                k = pending.pop(0)
                procs.append((k, subprocess.Popen([sys.executable, __file__, k, "--no-lock"])))
            time.sleep(0.5)
            for k, p in list(procs):
                if p.poll() is not None:
                    procs.remove((k, p))
                    if p.returncode:
                        failed.append(k)
        if failed:
            print("FAILED:", ", ".join(failed))
    else:
        for k in sel:
            run_one(k)
    if not a.no_lock:
        n = update_lock()
        if n:
            print(f"assets.lock.json: added {n} entries")


if __name__ == "__main__":
    main()
