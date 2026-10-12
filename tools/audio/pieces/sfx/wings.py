"""wing-beat-1..3: one beat of the giant owl's wings - a slow, heavy push of air with the feathers
rustling as they spread and close.

Made from Joseph Sardin's recordings (BigSoundBank, CC0): his foley "Wind" for the air, swept
through a band that opens and closes with the stroke, and a gust through "Wind in shrub" for the
feathers."""
import numpy as np

from hlaudio.core import SR, ns, rng
from hlaudio.effects import chain, filt, reverb
from hlaudio import nb
from hlaudio.piece import finish_sfx, update_manifest
from hlaudio.recordings import WIND, declick, entry, lock_cc0, original

LENGTH = 1.1


def wing_beat(i):
    r = rng("wing-beat", i)
    n = ns(LENGTH)
    t = np.arange(n) / SR
    air = declick(original("0595")[None])[0]
    a = ns(r.uniform(5, 70))
    # The stroke: a quick swell of air (the downstroke) and a long, soft fall (the wing coming up).
    u = t / 0.32
    env = np.where(t < 0.32, np.sin(np.pi / 2 * np.clip(u, 0, 1)) ** 2, np.exp(-(t - 0.32) / 0.22))
    fc = 160 + 520 * np.where(t < 0.32, np.clip(u, 0, 1), np.exp(-(t - 0.32) / 0.3))
    push = nb.svf(air[a: a + n], fc, 0.8, 1)
    push = push / (np.max(np.abs(push * env)) + 1e-9) * env
    # Feathers: a short gust through leaves, brightest as the wing turns.
    leaves = declick(original("0907")[None])[0]
    b = ns(r.uniform(5, 170))
    rustle = filt(leaves[b: b + n], chain(("hp", 1800, 0.7), ("lp", 7000, 0.7)))
    renv = np.exp(-(((t - 0.3) / 0.16) ** 2)) + 0.5 * np.exp(-(((t - 0.62) / 0.2) ** 2))
    rustle = rustle / (np.max(np.abs(rustle * renv)) + 1e-9) * renv
    y = push + 0.28 * rustle
    y = filt(y, chain(("hp", 45, 0.7)))
    wet = reverb(np.vstack([y, y]), "forest")[:, :n]
    out = np.vstack([y, y]) + 0.25 * wet
    k = ns(0.2)
    out[:, -k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return out


def render():
    update_manifest("sfx", "wing-beat", [])
    entries = []
    for i in range(3):
        name = f"wing-beat-{i + 1}"
        finish_sfx("wing-beat", name, wing_beat(i), -6.0, stereo=True, max_s=LENGTH, kbps=96)
        made = entry(name, WIND["0595"][1], "Wind and Wind in shrub (a giant wing's beat: air and feathers)")
        made["also"] = WIND["0907"][1]
        entries.append(made)
    lock_cc0(entries, ("wing-beat",))


if __name__ == "__main__":
    render()
