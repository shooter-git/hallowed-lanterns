"""I. The Arbor of Faces — "Sundown" (rescored, Glass / Zimmer).

Process music for a sunset, in straight time. A felt piano's right hand
repeats a six-note figure (the Ember's cell D B A F# A plus one note) in
steady eighths across 4/4 bars, so the figure slides against the bar line
and only lines up again every three bars (Glass's phase); between chords one
note of the figure changes at a time. The left hand marks the bar in 3+3+2.
Over a D pedal the harmony shifts underneath the same notes (D, Bm9, G
Lydian, A sus) and never leaves D. The voices enter one by one with the
cell AUGMENTED (a bar per note) in canon - clarinet on D, bassoon a fifth
below, then the flute with the INVERSION, then the oboe in stretto with
the cell diminished - so the harmony grows out of overlapping long notes,
over cello pizzicati plucking the bass in 3+3+2. A pizzicato canon of the
cell (violins, then violas a fifth below) answers the piano. At the peak
the organ pedal plays the cell in the bass and the horns answer it in
canon; then E minor 9 over the D pedal and a subtractive return to the
piano alone.
4/4, quarter = 75, 42 bars = 134.4 s.

  bars  0-5   piano figure alone; glass air
  bars  6-15  left hand (3+3+2), clarinet's canon entry, bassoon, pizzicato bass
  bars 16-23  moving bass; flute (inversion), oboe (stretto);
              glass interlocking pair in additive groups; pizzicato canon
  bars 24-31  the peak: organ pedal cell in the bass, horns' canon, timpani
  bars 32-41  E minor 9 over D, then layers fall away to the piano
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock, chord_at
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop
from hlaudio import lead as LD

TITLE = "Sundown"
BAR = 8            # eighths
BARS = 42
BPM_UNIT = 150     # eighths per minute (quarter = 75)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 134.4 s
M = PR.Mode(62, "ionian")  # D

CYC = [("Dmaj9", [74, 78, 81, 83], 38), ("Bm9/D", [74, 78, 81, 85], 38),
       ("Gmaj7#11/D", [73, 78, 81, 83], 38), ("A7sus4/D", [74, 76, 81, 83], 38)]
MOV = [("D", [74, 78, 81, 83], 38), ("Bm7", [74, 78, 81, 85], 35),
       ("Gmaj9", [74, 78, 79, 83], 31), ("Aadd9", [73, 76, 81, 83], 33)]
PEAK = [("Dadd9", [74, 76, 78, 81], 38), ("Gmaj7/B", [74, 78, 79, 83], 35), ("D/A", [74, 78, 81, 86], 33),
        ("Aadd9", [73, 76, 81, 83], 33)]
END = [("Em9/D", [74, 78, 79, 83], 38), ("Dmaj9", [74, 78, 81, 83], 38),
       ("Gmaj7#11/D", [73, 78, 81, 83], 38), ("A7sus4/D", [74, 76, 81, 83], 38)]
# (chord, right-hand set, bass), two bars each, plus a closing D
PLAN = [(c, s, b, 2) for c, s, b in CYC * 2 + MOV + PEAK + END] + [("Dmaj9", [74, 78, 81, 83], 38, 2)]
FIG = [0, 3, 2, 1, 2, 3]                       # D B A F# A + one, over the current set
FIG_ACC = [1.0, 0.72, 0.82, 0.92, 0.7, 0.8]


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{n * BAR}" for c, _, _, n in PLAN))


def right_hand(pr):
    """The six-note figure in eighths, continuous across the bar lines; the
    voicing moves one note towards the current chord's set at every figure."""
    sets, t = [], 0.0
    for c, s, b, n in PLAN:
        sets.append((t, t + bar(n), s))
        t += bar(n)
    cur = list(PLAN[-1][1])
    out = []
    for i in range(BARS * BAR):
        k = i % 6
        if k == 0:
            target = next(s for t0, t1, s in sets if t0 <= i < t1)
            diffs = [(abs(a - g), j) for j, (a, g) in enumerate(zip(cur, target)) if a != g]
            if diffs:
                _, j = min(diffs)
                cur[j] = target[j]
        bar_acc = 1.12 if i % BAR in (0, 3, 6) else 1.0
        out.append(N(float(i), 1.6, float(cur[FIG[k]]), 0.42 * FIG_ACC[k] * bar_acc))
    return out


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["rh"] = right_hand(pr)
    # left hand, 3+3+2: bass, fifth, tenth (from bar 6, thinning at the end)
    lh, t = [], 0.0
    for c, s, bass, n in PLAN:
        for k in range(n):
            for pos, p, v in ((0, bass + 12, 1.1), (3, bass + 19, 0.9), (6, s[1] - 12, 0.85)):
                lh.append(N(t + pos, 3.2 if pos < 6 else 2.2, float(p), 0.36 * v))
            t += BAR
    P["lh"] = [n for n in lh if bar(6) <= n.t < bar(38)]
    # the canon of the augmented cell (a bar a note, the last held two)
    aug = [8, 8, 8, 8, 16]
    P["vla"] = PR.realize(PR.cell("P"), M, 0, bar(6), aug, vel=0.5)                        # D4 B4 A4 F#4 A4
    P["vc"] = PR.realize(PR.cell("P"), M, -3, bar(9), aug, vel=0.5)                        # A3 F#4 E4 C#4 E4
    P["vn2"] = PR.realize(PR.cell("I"), M, 11, bar(15), [8] * 5, vel=0.5)                 # A5 C#5 D5 F#5 D5
    dim = [2, 4, 2, 2, 6]
    P["vn1"] = (PR.realize(PR.cell("P"), M, 7, bar(18), dim, vel=0.55) +
                      PR.realize(PR.cell("P"), M, 5, bar(20), dim, vel=0.58) +
                      PR.realize(PR.cell("I"), M, 11, bar(24), [4, 4, 4, 4, 8], vel=0.6) +
                      PR.realize(PR.cell("P", 3), M, 7, bar(28), [4, 4, 8], vel=0.5))
    bass_plan = [(8, 16, 38), (16, 18, 38), (18, 20, 35), (20, 22, 31), (22, 24, 33), (24, 26, 38), (26, 28, 35),
                 (28, 30, 33), (30, 32, 33), (32, 38, 38)]
    # the bass plucked (3+3+2: root, fifth, octave) and a soft organ floor under it
    pz = []
    for b0, b1, p in bass_plan:
        for b in range(b0, b1):
            pz += [N(bar(b), 2.0, float(p + 12), 0.55), N(bar(b) + 3, 2.0, float(p + 19), 0.4),
                   N(bar(b) + 6, 1.5, float(p + 24), 0.45)]
    P["vc_pizz"] = pz
    P["cb"] = [N(bar(b0), bar(b1 - b0) + 0.5, float(p), 0.45) for b0, b1, p in bass_plan]
    # a pizzicato canon of the cell in quarter notes: violins, violas a bar later a fifth below
    P["pz_vn"] = PR.fit(PR.loop_figure(PR.realize(PR.cell("P"), M, 7, 0.0, [2, 2, 2, 2, 8], vel=0.5),
                                       bar(26), bar(34), 16), pr)
    P["pz_vla"] = PR.fit(PR.loop_figure(PR.realize(PR.cell("P"), M, 3, 0.0, [2, 2, 2, 2, 8], vel=0.45),
                                        bar(27), bar(34), 16), pr)
    # the peak: organ pedal plays the cell in the bass, the horns answer a fifth up
    P["org_ped"] = PR.realize(PR.cell("P"), M, -14, bar(24), aug, vel=0.55)               # D2 B2 A2 F#2 A2
    P["org"] = [N(bar(24), bar(6), float(p), 0.5) for p in (57, 62, 66)] + \
        [N(bar(30), bar(2), float(p), 0.5) for p in (57, 61, 64)]
    P["horns"] = PR.fit(PR.realize(PR.cell("P"), M, -3, bar(25), [8, 8, 8, 8, 8], vel=0.6), pr)  # A3 F#4 E4 C#4 E4
    P["timp_roll"] = [N(bar(22), bar(2) + 0.3, 50.0, 0.6)]
    P["timp"] = [N(bar(24), 3, 38.0, 0.7), N(bar(30), 3, 45.0, 0.55), N(bar(32), 3, 38.0, 0.45)]
    # glass: an interlocking pair in Glass's additive groups (2, 2, 3, 3, 4, 4, 5, 5)
    groups = [2, 2, 3, 3, 4, 4, 5, 5, 4, 4, 3, 3]
    g1, _ = PR.additive(PR.cell("P"), groups, M, 14, 0.0, 1.0, vel=0.4)
    g1 = PR.loop_figure(g1, bar(18), bar(33), sum(groups))
    g2 = PR.displace(g1, 0.5)
    for n in g2:
        n.p = float(M.p(M.deg(n.p) - 2))
        n.v *= 0.8
    P["glass1"], P["glass2"] = PR.fit(g1, pr), PR.fit(g2, pr)
    P["air"] = [N(bar(0), bar(6), 88.0, 0.25), N(bar(36), bar(6), 88.0, 0.25), N(bar(33), bar(3), 89.0, 0.2)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(8 * BAR, 0.015))
    S = lambda notes, seed, j=0.01: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.2), (sec(6), 0.28), (sec(12), 0.4), (sec(18), 0.55), (sec(23), 0.7), (sec(24.5), 0.88),
                 (sec(31), 0.85), (sec(33.5), 0.5), (sec(37), 0.28), (sec(41), 0.2), (LOOP, 0.2)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.5, "swell": 0.18, "taper": 2.5}

    rh = S(P["rh"], 1, 0.008)
    for n in rh:
        n.v = float(n.v * (0.85 + 0.5 * arc(n.t)))
    st.play("piano", rh, "piano", seed=1, gain_db=8, layer_bias=-0.25, release=0.8)
    lh = S(P["lh"], 2, 0.012)
    for n in lh:
        n.v = float(n.v * (0.8 + 0.6 * arc(n.t)))
    st.play("piano", lh, "piano", seed=2, gain_db=6, layer_bias=-0.25, release=0.9)

    kw = dict(dyn=arc, shape=shape, lag=0.025)
    st.play("clarinets", S(P["vla"], 3), "clarinet", seed=3, gain_db=7, **kw)
    st.play("bassoon", S(P["vc"], 4), "bassoon", seed=4, gain_db=7, **kw)
    st.play("flutes", S(P["vn2"], 5), "flute", seed=5, gain_db=6, **kw)
    st.play("oboe", S(P["vn1"], 6), "oboe", seed=6, gain_db=6, **LD.lead(st), **kw)
    st.play("basses", S(P["cb"], 7), "basses", seed=7, gain_db=-19, **LD.bed(), **kw)
    vp = S(P["vc_pizz"], 16, 0.006)
    for n in vp:
        n.v = float(n.v * (0.6 + 0.6 * arc(n.t)))
    st.play("cellos_pizz", vp, "cellos_pizz", seed=16, gain_db=2, seat="cellos")
    st.play("violins_pizz", S(P["pz_vn"], 17, 0.006), "violins_pizz", seed=17, gain_db=1, seat="violins")
    st.play("violas_pizz", S(P["pz_vla"], 18, 0.006), "violas_pizz", seed=18, gain_db=6, seat="violas")
    peak = Curve([(sec(23), 0.3), (sec(24.5), 0.75), (sec(30.5), 0.8), (sec(33), 0.4), (sec(35), 0.2)])
    st.play("organ", S(P["org_ped"], 8, 0.0), "organ_soft_pedal", seed=8, dyn=peak, gain_db=-8)
    st.play("organ", S(P["org"], 9, 0.0), "organ_soft", seed=9, dyn=peak, gain_db=-13)
    st.play("horns", S(P["horns"], 10), "horns", seed=10, dyn=peak, gain_db=-3, shape=shape, lag=0.03)
    st.play("timpani", S(P["timp_roll"], 11, 0.0), "timpani_roll", seed=11,
            dyn=Curve([(sec(22), 0.02), (sec(24), 0.7), (sec(24.05), 0.25)]), gain_db=-6, release=0.4)
    st.play("timpani", S(P["timp"], 12, 0.004), "timpani", seed=12, gain_db=-4)

    gl = st.stem("glass", {"shimmer:cathedral2": 0.4, "concert": 0.6})
    g1 = S(P["glass1"], 13, 0.004)
    g2 = S(P["glass2"], 14, 0.004)
    for n in g1 + g2:
        n.v = float(n.v * (0.6 + 0.6 * arc(n.t)))
    EL.glass(gl, g1, gain=0.3, seed=13, attack=0.05, release=1.2, pan_spread=0.0, breath=0.05, bright=0.6)
    EL.glass(gl, g2, gain=0.24, seed=14, attack=0.05, release=1.2, pan_spread=0.0, breath=0.05, bright=0.6)
    gl.buf = (FX.echo(gl.buf, clk.s(3), fb=0.35, mix=0.35, lp=2800, circular=True) + gl.buf).astype("float32")
    EL.glass(gl, S(P["air"], 15, 0.0), gain=0.3, seed=15, attack=2.5, release=4.0)

    out = st.render({"concert": {"seed": 1}, "cathedral2": {"seed": 2},
                     "shimmer:cathedral2": {"seed": 3, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "arbor", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 75, "meter": "4/4", "beat": "quarter", "key": "D major",
                             "instrument": "piano"})


if __name__ == "__main__":
    render()
