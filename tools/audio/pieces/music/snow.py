"""VI. October Snow — "First Snow" (rescored, Glass / Martinez).

Hushed and slow, in straight time. The harp cycles a broken chord in
quarter notes while two glass voices move in dotted quarters - three
against four, so the two patterns drift against each other and only meet
again every three bars, like snowfall that never quite lines up. The glass
pair interlocks: one plays the Ember's cell, the other its inversion, a
dotted quarter apart, with a dotted-eighth echo. Over an A pedal the chords
drift (A add9, F#m add9 over A, Dmaj7#11, E sus), one harp note changing at
a time, with one brighter moment that stays in the mode - B major over A,
the Lydian colour - like a light coming on in a window. A clarinet and a
far-away solo violin enter in CANON with the cell augmented (two bars a
note), the clarinet on A, the violin a fifth higher four bars later; a
breathy flute holds the inversion; cello pizzicati drop onto the pedal like
snow from a branch. A Lydian, 4/4 at 60, 34 bars = 136 s.
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop

TITLE = "First Snow"
BAR = 4
BARS = 34
BPM = 60
LOOP = BARS * BAR * 60 / BPM  # 136 s
M = PR.Mode(57, "lydian")  # A (D#)

CYCLE = [("Aadd9", 2, [64, 69, 71, 73]), ("F#madd9/A", 2, [64, 66, 68, 73]),
         ("Dmaj7#11/A", 2, [64, 66, 68, 73]), ("Esus4/A", 2, [64, 69, 71, 76])]
PLAN = CYCLE + CYCLE + [("B/A", 2, [63, 66, 71, 75]), ("C#m7/A", 2, [64, 68, 71, 73]),
                        ("Dmaj7#11/A", 2, [64, 66, 68, 73]),
                        ("Esus4/A", 2, [64, 69, 71, 76])] + CYCLE + [("Aadd9", 2, [64, 69, 71, 73])]


def bar(b):
    return b * BAR


def score():
    pr = prog(" ".join(f"{c}:{b * BAR}" for c, b, _ in PLAN))
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    hp, _ = PR.cycling([(s, b) for _, b, s in PLAN], [0, 2, 3, 1], 1.0, 0.0, 1, vel=0.42,
                       accents=[1.0, .8, .9, .78], legato=2.5)
    P["harp"] = hp
    # the glass pair: the cell and its inversion in dotted quarters, a dotted quarter apart
    g1, g2 = [], []
    t = 0.0
    while t < bar(BARS):
        g1 += PR.realize(PR.cell("P"), M, 14, t, 1.5, vel=0.4)
        g2 += PR.realize(PR.cell("I"), M, 18, t + 1.5, 1.5, vel=0.32)
        t += 12.0                                   # three bars: the patterns meet again
    P["g1"] = PR.fit([n for n in g1 if n.t < bar(BARS) - 1.0], pr)
    P["g2"] = PR.fit([n for n in g2 if n.t < bar(BARS) - 1.0], pr)
    P["vn2"] = PR.fit(PR.realize(PR.cell("P"), M, 7, bar(6), [8, 8, 8, 8, 12], vel=0.45), pr)    # A4 F#5 E5 C#5 E5
    P["vn1"] = PR.fit(PR.realize(PR.cell("P"), M, 11, bar(10), [8, 8, 8, 8, 12], vel=0.45), pr)   # E5 C#6 B5 G#5 B5
    P["flute"] = PR.fit(PR.realize(PR.cell("I"), M, 14, bar(20), [8, 8, 8, 8, 8], vel=0.4), pr)
    P["pedal_vc"] = [N(bar(b), bar(8) + 1, 45.0, 0.4) for b in (2, 10, 18, 26)]
    P["pedal_cb"] = [N(bar(6), bar(17), 33.0, 0.4)]
    P["tri"] = [N(bar(16), 2, 0, 0.32), N(bar(24), 2, 0, 0.28)]
    P["pz"] = [N(bar(b) + 0.0, 2.0, 45.0, 0.5) for b in range(2, 32)] + \
        [N(bar(b) + 2.5, 1.5, 52.0, 0.36) for b in range(4, 30, 2)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM)
    S = lambda notes, seed, j=0.015: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.2), (sec(6), 0.26), (sec(12), 0.36), (sec(16), 0.48), (sec(19), 0.52), (sec(24), 0.42),
                 (sec(30), 0.26), (sec(33), 0.2), (LOOP, 0.2)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.8, "swell": 0.15, "taper": 3.0}

    hp = S(P["harp"], 1, 0.015)
    for n in hp:
        n.v = float(n.v * (0.85 + 0.5 * arc(n.t)))
    st.play("harp", hp, "harp", seed=1, gain_db=0)
    gl = st.stem("glass", {"shimmer:cathedral2": 0.45, "concert": 0.5}, depth=0.7)
    EL.glass(gl, S(P["g1"], 2, 0.008), gain=0.45, seed=2, attack=0.15, release=2.5, pan_spread=0.0, breath=0.08,
             bright=0.6)
    EL.glass(gl, S(P["g2"], 3, 0.008), gain=0.35, seed=3, attack=0.15, release=2.5, pan_spread=0.0, breath=0.08,
             bright=0.6)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4000, 0.7), circular=True)
    gl.buf = (gl.buf + FX.echo(gl.buf, 0.75, fb=0.35, mix=0.3, lp=2400, circular=True)).astype("float32")
    kw = dict(dyn=arc, shape=shape, lag=0.03)
    st.play("clarinets", S(P["vn2"], 4), "clarinet", seed=4, gain_db=4, depth=0.75, **kw)
    st.play("solo_violin", S(P["vn1"], 5), "solo_violin", seed=5, gain_db=3, depth=0.7, layer_bias=-0.3,
            legato=True, slide=0.1, **kw)
    pz = S(P["pz"], 11, 0.01)
    for n in pz:
        n.v = float(n.v * (0.7 + 0.5 * arc(n.t)))
    st.play("cellos_pizz", pz, "cellos_pizz", seed=11, gain_db=0, seat="cellos")
    st.play("flutes", S(P["flute"], 6), "flute_nv", seed=6, dyn=arc, gain_db=6, shape=shape, lag=0.03)
    st.play("cellos", S(P["pedal_vc"], 7), "cellos", seed=7, dyn=arc, gain_db=-4, depth=0.8, shape=shape)
    st.play("basses", S(P["pedal_cb"], 8), "basses", seed=8, dyn=arc, gain_db=-6, depth=0.8, shape=shape)
    st.play("triangle", S(P["tri"], 9, 0.0), "triangle", seed=9, gain_db=0)

    out = st.render({"concert": {"seed": 61}, "cathedral2": {"seed": 62},
                     "shimmer:cathedral2": {"seed": 63, "gens": 2, "fb": 0.45}}, warmth=0.3)
    return finish_loop("music", "snow", out, LOOP, 4, -17.0, 192, tilt_hs_db=-1.5,
                       meta={"title": TITLE, "bpm": BPM, "meter": "4/4", "beat": "quarter", "key": "A lydian",
                             "instrument": "harp and glass"})


if __name__ == "__main__":
    render()
