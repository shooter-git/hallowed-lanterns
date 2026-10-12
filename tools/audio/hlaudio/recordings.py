"""Real recordings: CC0 foley by Joseph Sardin (BigSoundBank), fetched once into
.cache/recorded/ (git ignores it), and the assets.lock.json entries for what's made from them."""
import json
import re
import urllib.request

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from hlaudio.core import SR
from hlaudio.piece import CACHE, OUT

AUTHOR = "Joseph SARDIN (BigSoundBank)"


def original(sound_id):
    """A BigSoundBank recording by its number, mono, at SR (fetched once into the cache)."""
    path = CACHE / "recorded" / f"bsb-{sound_id}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://bigsoundbank.com/UPLOAD/bwf-en/{sound_id}.wav"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Hallowed Lanterns audio tools)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            path.write_bytes(r.read())
    rate, data = wavfile.read(path)
    x = data.astype(np.float64)
    if data.dtype.kind == "i":
        x /= float(np.iinfo(data.dtype).max)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return resample_poly(x, SR, rate) if rate != SR else x


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
