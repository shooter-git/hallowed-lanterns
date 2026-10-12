"""Small magic: xylo-1..8 (the pumpkin xylophone, D pentatonic, contains the
motif), sprinkle-burst, snowflake-1..5, bubble-1..4, wish-hang, fog-swirl-1..2
and ui-tap. The instrument-like ones (xylo, sprinkle-burst, snowflakes,
wish-hang) are sampled (VSCO 2 CE marimba, glockenspiel, harp, strings) and
fairly dry; render_instruments() renders just those."""
import numpy as np

from hlaudio.core import SR, ns, rng, tvec, Track, smoothstep
from hlaudio.effects import chain, filt, reverb, eq, shimmer
from hlaudio.score import N
from hlaudio import mallets as ML, voice as VO, nature as NA, bowed as BW, nb, theme as TH
from hlaudio.core import m
from hlaudio.piece import finish_sfx
from hlaudio import sfxkit as K, electro as EL


def _verb(y, space, amt, keep):
    y = np.atleast_2d(np.asarray(y, dtype=float))
    if y.shape[0] == 1:
        y = np.vstack([y[0], y[0]])
    wet = reverb(y, space)
    n = ns(keep)
    y = np.pad(y, ((0, 0), (0, max(0, wet.shape[1] - y.shape[1]))))
    return (y[:, : wet.shape[1]] + amt * wet)[:, :n]


def xylo(p):
    """A pumpkin-xylophone note: the marimba, close and nearly dry."""
    st = K.stage(1.8)
    K.play(st, "marimba", [N(0.01, 0.9, float(p), 0.72)], "marimba", pan=0.0, width=0.3, send=0.09)
    return K.finish(st)


def sprinkle_burst():
    """A burst of soft glockenspiel notes (D pentatonic) thinning out, with a
    small airy 'pop' at the start and a touch of shimmer."""
    r = rng("sprinkle")
    st = K.stage(3.0)
    pent = [74, 76, 78, 81, 83, 86, 88, 90]  # D5..F#6
    notes, t = [], 0.0
    while t < 1.3:
        notes.append(N(t, 0.6, float(r.choice(pent)), float(r.uniform(0.25, 0.5) * (1 - t / 1.8)),
                       {"pan": float(r.uniform(-0.8, 0.8))}))
        t += r.exponential(0.02 + 0.06 * t)
    for i, n in enumerate(notes):
        K.play(st, "glock", [n], "glock", seed=i, pan=n.x["pan"], width=0.2, send=0.13,
               extra={"shimmer:concert": 0.08})
    n = ns(0.25)
    tt = tvec(n)
    pop = nb.svf(r.standard_normal(n), 600 + 2400 * smoothstep(tt / 0.15), 2.0, 1) * np.exp(-tt / 0.06)
    pop = filt(pop, chain(("lp", 3500, 0.7)))
    st.stem("pop", {"concert": 0.1}, depth=K.DEPTH).add(0.0, pop, gain=0.12)
    g = st.stems["glock"]
    g.buf = eq(g.buf.astype(float), ("lp", 3800, 0.7)).astype("float32")      # sparkle, not tinkle
    return K.finish(st, {"shimmer:concert": {"seed": 6, "gens": 1, "fb": 0.3}})


def snowflake(p, i):
    """One soft glockenspiel note with a harp harmonic under it."""
    st = K.stage(2.2)
    K.play(st, "glock", [N(0.01, 1.0, float(p), 0.36)], "glock", seed=i, pan=0.0, width=0.3, send=0.15)
    K.play(st, "harp", [N(0.01, 1.0, float(p - 12), 0.4)], "harp", seed=i, pan=0.0, width=0.3, send=0.15,
           gain_db=-12)
    return K.finish(st)


def bubble(i):
    r = rng("bub", i)
    tr = Track(0.6)
    k = [1, 2, 3, 2][i]
    for j in range(k):
        tr.add(j * r.uniform(0.05, 0.12), NA.bubble(r.uniform(800, 1700), seed=i * 10 + j, decay=r.uniform(0.012, 0.03),
                                                    rise=r.uniform(0.15, 0.4)), gain=r.uniform(0.6, 1.0))
    y = eq(tr.buf.astype(float), ("lp", 4000, 0.7))
    return _verb(y, "room", 0.12, 0.6)


def wish_hang():
    """A harp run up a G major chord, a soft glockenspiel touch at the top,
    then a warm G major chord (violas and violins, a glass halo)."""
    st = K.stage(4.5)
    run = [N(0.02 + 0.035 * k, 1.6, float(p), 0.45 + 0.04 * k) for k, p in enumerate([67, 71, 74, 79, 83, 86])]
    K.play(st, "harp", run, "harp", pan=-0.1, width=0.6)
    K.play(st, "glock", [N(0.2, 1.0, 91.0, 0.3), N(0.24, 1.0, 95.0, 0.25)], "glock", pan=0.3, width=0.3,
           send=0.15)
    sh = {"attack": 0.35, "swell": 0.15, "taper": 1.5}
    K.play(st, "violas", [N(0.2, 1.8, float(p), 0.5) for p in (55, 62)], "violas", shape=sh, double=1, gain_db=-4)
    K.play(st, "violins", [N(0.22, 1.8, float(p), 0.48) for p in (67, 71, 74)], "violins", shape=sh, double=1,
           gain_db=-6, layer_bias=-0.2)
    gl = st.stem("glass", {"concert": 0.15}, depth=K.DEPTH)
    EL.glass(gl, [N(0.3, 1.6, float(p), 0.4) for p in (79, 86)], gain=0.25, seed=3, attack=0.35, release=1.4,
             bright=0.5)
    return K.finish(st)


def fog_swirl(i):
    """Chapter-change whoosh: soft noise that swirls across the stereo field,
    a faint glass glissando inside it, and a shimmer tail."""
    r = rng("fog", i)
    dur = 2.0
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    env = np.sin(np.pi * u) ** 1.6
    fc = 300 + 1500 * np.sin(np.pi * u) ** 2 * (1.0 if i == 0 else 0.8)
    out = np.zeros((2, n))
    for ch in range(2):
        x = nb.svf(rng("fog", i, ch).standard_normal(n), fc * (1 + 0.1 * ch), 1.6, 1)
        x = filt(x, chain(("lp", 3000, 0.7), ("lp", 3800, 0.7)))
        pan = 0.5 + 0.5 * np.sin(2 * np.pi * (0.6 if i == 0 else -0.6) * u + ch * np.pi)
        out[ch] = x * env * (0.35 + 0.65 * pan)
    # glass glissando up (i=0) or down (i=1)
    p0, p1 = (74.0, 93.0) if i == 0 else (93.0, 74.0)
    f = 440 * 2 ** ((p0 + (p1 - p0) * smoothstep(u) - 69) / 12)
    gl = np.sin(2 * np.pi * np.cumsum(f) / SR) * env * 0.08
    out += np.vstack([gl, gl])
    wet = shimmer(out, "cathedral", gens=1, fb=0.3)
    y = np.pad(out, ((0, 0), (0, wet.shape[1] - n))) + 0.35 * wet
    return eq(y, ("hp", 80, 0.7), ("hs", 5000, 0.7, -4))[:, : ns(4.0)]


def ui_tap():
    n = ns(0.12)
    t = tvec(n)
    y = np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.012) * 0.5
    y += np.sin(2 * np.pi * 2900 * t) * np.exp(-t / 0.006) * 0.15
    y += np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.02) * 0.4
    y *= 1 - np.exp(-t / 0.0004)
    return y


def render_instruments():
    for i, nm in enumerate(TH.XYLO_NOTES):
        finish_sfx("xylo", f"xylo-{i + 1}", xylo(m(nm)), -3.0, max_s=1.0)
    finish_sfx("sprinkle-burst", "sprinkle-burst", sprinkle_burst(), -3.0, stereo=True, max_s=1.7)
    for i, p in enumerate([81, 85, 88, 90, 93]):  # A5 C#6 E6 F#6 A6 (snow's A major)
        finish_sfx("snowflake", f"snowflake-{i + 1}", snowflake(p, i), -5.0, max_s=1.4)
    finish_sfx("wish-hang", "wish-hang", wish_hang(), -3.0, stereo=True, max_s=2.1)


def render():
    render_instruments()
    for i in range(4):
        finish_sfx("bubble", f"bubble-{i + 1}", bubble(i), -5.0)
    for i in range(2):
        finish_sfx("fog-swirl", f"fog-swirl-{i + 1}", fog_swirl(i), -4.0, stereo=True, max_s=1.9)
    finish_sfx("ui-tap", "ui-tap", ui_tap(), -9.0)


if __name__ == "__main__":
    render()
