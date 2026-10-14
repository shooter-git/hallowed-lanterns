"""Projector ambience: a vintage film projector purring beside the shadow-puppet
screen. A warm motor hum, the soft 24-per-second patter of the film claw, the
cooling fan's breath and a slow reel squeak — gentle, never rattly. Loops
seamlessly (every periodic part completes whole cycles in the loop)."""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec, colored, smooth_random
from hlaudio.effects import chain, filt, eq
from hlaudio import nb
from hlaudio.piece import Mix, finish_loop

LOOP = 60.0


def render():
    mix = Mix(LOOP, circular=True)
    n = ns(LOOP)
    t = tvec(n)
    r = rng("projector")

    motor = mix.track()
    f0 = 3420 / LOOP  # 57 Hz, whole cycles per loop
    wob = 1 + 0.004 * np.sin(2 * np.pi * (round(0.7 * LOOP) / LOOP) * t)
    ph = 2 * np.pi * np.cumsum(f0 * wob) / SR
    hum = sum(a * np.sin(k * ph + 0.3 * k) for k, a in [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.18), (6, 0.08)])
    hum *= 0.85 + 0.15 * np.sin(2 * np.pi * (round(3.0 * LOOP) / LOOP) * t)
    motor.add(0, np.vstack([hum, np.roll(hum, ns(0.004))]), gain=0.05)
    mix.add(motor, 1.0, {"room": 0.3}, name="motor")

    claw = mix.track()
    # 24 frames per second: a soft, slightly uneven double tick per frame
    L = ns(0.02)
    tv = tvec(L)
    for i in range(int(24 * LOOP)):
        tt = i / 24.0 + r.normal(0, 0.0008)
        a = 0.75 + 0.25 * r.uniform()
        tick = (np.sin(2 * np.pi * r.uniform(1300, 1700) * tv) * np.exp(-tv / 0.002) +
                0.6 * np.sin(2 * np.pi * 420 * tv) * np.exp(-tv / 0.004)) * (1 - np.exp(-tv / 0.0004))
        claw.add(tt, tick * a, gain=0.28, pan=-0.1)
        claw.add(tt + 0.011, tick * a * 0.45, gain=0.28, pan=0.1)
    claw.buf = eq(claw.buf, ("lp", 3200, 0.7), ("lp", 4000, 0.7), ("hp", 200, 0.7), circular=True).astype("float32")
    mix.add(claw, 1.0, {"room": 0.35}, name="claw")

    fan = mix.track()
    blades = 1 + 0.15 * np.sin(2 * np.pi * (round(11.0 * LOOP) / LOOP) * t)
    air = np.vstack([colored(n, rng("fan", c), -4.0, lo=120, hi=1800) for c in range(2)]) * blades
    fan.add(0, air, gain=0.035)
    mix.add(fan, 1.0, name="fan")

    reel = mix.track()
    period = LOOP / 30.0  # one slow squeak every two seconds
    for i in range(30):
        Ls = ns(0.18)
        u = np.linspace(0, 1, Ls)
        sq = nb.svf(r.standard_normal(Ls), np.full(Ls, 2100.0 + 150 * np.sin(i)), 12.0, 1) * np.sin(np.pi * u) ** 2
        reel.add(i * period + 0.3, sq, gain=0.025 * r.uniform(0.5, 1.0), pan=0.35)
    mix.add(reel, 1.0, {"room": 0.3}, name="reel")

    out = mix.render({"room": {"seed": 131}})
    out = eq(out, ("lp", 6000, 0.7), circular=True)
    # the level: its bed 8 dB under the chapter's music as heard in the game (the music's group at 0.6,
    # the ambience's at 0.5), its crickets and wind never more than 2 dB over the music's own highs
    return finish_loop("ambience", "projector", out, LOOP, 3, -23.0, 128, glue=False, tilt_hs_db=-2.0)


if __name__ == "__main__":
    render()
