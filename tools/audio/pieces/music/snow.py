"""VI. October Snow — "First Snow" (rescored: Glass / Martinez, with a theme
to hum).

An unexpected snowfall in October: the hush of a snowy wood, a snowman who
raises his mug as you pass, and at the end the flakes slow, stop and begin
to rise. Straight time, the eighths grouped 3+3+2, in A with the Lydian
D-sharp; the pedal stays on A.

The snowfall is a glittering ostinato that grows by addition: the harp
picks the chord in eighths (one note of the voicing changing every half
bar), the glockenspiel answers on the last eighth of each group - first one
ping a bar, then two, then three, walking the Ember's cell high up - violin
pizzicati fill the gaps between them, cello pizzicati drop onto the A, and
the old glass pair still drifts three against four above it all.

THE THEME grows from the Ember's cell. Its first phrase is the cell itself
(A | F# E C# | E), the answer is the same shape a step lower with the
Lydian D-sharp (G# | E D# B | D#), and the second half climbs - the cell
again, then E F# A, up to B and a sigh back to E, open, "this way!":

    A4 | F#5 - E5 C#5 | E5 - - G#4 | E5 - D#5 B4 | D#5 - - A4 |
         F#5 - E5 C#5 | E5 F#5 A5 - | B5 - A5 F#5 | E5 - - -

The felt piano states it first, simply (bars 4-11). The oboe sings it
again (12-19) with the piano echoing the cell high up in its long notes and
the clarinet holding the cell augmented below. Then the climbing half is
developed as a rising sequence (20-27) - oboe, then flute and oboe a
step higher - over the horns' cell augmented (a bar a note), while the
snowfall thickens and soft timpani and a far bass drum are born in 3+3+2.
The one swell is the full theme (28-35): oboe and flute in octaves, horns
and organ, and at its heart the Lydian light - the held D-sharp over B major
above the A - before the drums leave and the theme's last phrase is sung
alone. Then the snow starts to rise (36-39): the harp's voicing climbs note
by note, the glockenspiel pings climb, the piano leaps the cell's sixth and
holds A, then B over B major - suspended - and the loop begins again from
the quiet snowfall.
4/4, quarter = 72, 40 bars = 133.3 s.

  bars  0-3   the snowfall alone (harp, glockenspiel, glass), A pedal
  bars  4-11  the theme: felt piano; cello pizzicati
  bars 12-19  the theme: oboe; piano echoes; clarinet: the cell augmented
  bars 20-27  development: rising sequence of the climb; horns' cell; the drums enter (24)
  bars 28-35  the swell: the full theme, the Lydian light (31); drums gone by 33
  bars 36-39  the snow rises: climbing voicings, a suspended B over A
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock, chord_pcs
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.beats import groove
from hlaudio.piece import finish_loop
from hlaudio import lead as LD

TITLE = "First Snow"
BAR = 8            # eighths
BARS = 40
BPM_UNIT = 144     # eighths per minute (quarter = 72)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 133.33 s
M = PR.Mode(57, "lydian")  # A (D#)

V = {  # harp voicings (E4-D#5 mostly), and the rising ones at the end
    "Aadd9": [64, 69, 71, 73], "A6add9": [64, 66, 71, 73], "Emaj7/A": [64, 68, 71, 75],
    "B/A": [63, 66, 71, 75], "F#m7/A": [64, 66, 69, 73], "Dmaj7#11/A": [64, 66, 68, 73],
    "Esus4/A": [64, 69, 71, 76], "C#m7/A": [64, 68, 71, 73], "E/A": [64, 68, 71, 76],
}
THEME_CHORDS = ["A6add9", "Aadd9", "Emaj7/A", "Emaj7/A", "F#m7/A", "Dmaj7#11/A", "Esus4/A", "Aadd9"]
DEV_CHORDS = ["F#m7/A", "Dmaj7#11/A", "F#m7/A", "Dmaj7#11/A", "C#m7/A", "Dmaj7#11/A", "Esus4/A", "E/A"]
PEAK_CHORDS = ["A6add9", "Aadd9", "Emaj7/A", "B/A", "F#m7/A", "Dmaj7#11/A", "Esus4/A", "Aadd9"]
PLAN = (["Aadd9", "A6add9", "Dmaj7#11/A", "Esus4/A"] + THEME_CHORDS + THEME_CHORDS + DEV_CHORDS + PEAK_CHORDS +
        ["Dmaj7#11/A", "Dmaj7#11/A", "Esus4/A", "B/A"])
RISE = {36: [68, 73, 76, 78], 37: [69, 73, 76, 80], 38: [71, 76, 81, 83], 39: [75, 78, 83, 87]}

# the theme in eighths, from its pickup (beat 4 of the bar before): (pitch, eighths)
THEME = [(69, 2),
         (78, 4), (76, 2), (73, 2), (76, 6), (68, 2),
         (76, 4), (75, 2), (71, 2), (75, 6), (69, 2),
         (78, 4), (76, 2), (73, 2), (76, 2), (78, 2), (81, 4),
         (83, 4), (81, 2), (78, 2), (76, 8)]
CLIMB = THEME[10:]            # the second half: A | F# E C# | E F# A | B A F# | E


def bar(b):
    return b * BAR


def line(spec, t0, vel=0.55, transpose=0, accent_long=0.06):
    out, t = [], t0
    for p, d in spec:
        out.append(N(t, float(d), float(p + transpose), float(vel + (accent_long if d >= 4 else 0.0))))
        t += d
    return out


def mono(notes):
    """One player: each note ends where the next begins (a legato hand-over)."""
    notes = sorted(notes, key=lambda n: n.t)
    for a, b in zip(notes, notes[1:]):
        if a.t + a.d > b.t:
            a.d = b.t - a.t
    return notes


def harmony():
    return prog(" ".join(f"{c}:{BAR}" for c in PLAN))


def harp_ostinato():
    """Eighths, 3+3+2; ONE voice of the voicing moves towards the next chord's
    every half bar (the rising voicings at the end climb the same way)."""
    pat = [0, 2, 3, 1, 2, 3, 1, 3]
    acc = [1.0, .72, .8, .95, .72, .8, .92, .76]
    out = []
    cur = sorted(RISE[39])                     # the loop begins where the snow rose to, and falls again
    for b, sym in enumerate(PLAN):
        target = sorted(RISE.get(b, V[sym]))
        for i, idx in enumerate(pat):
            if i in (0, 4) and cur != target:
                cand = [(target[k] in cur, abs(c - g), k) for k, (c, g) in enumerate(zip(cur, target)) if c != g]
                k = min(cand)[2]
                cur[k] = target[k]
                cur.sort()
            out.append(N(bar(b) + i, 2.4, float(cur[idx]), 0.4 * acc[i]))
    return out


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["harp"] = harp_ostinato()
    # the glockenspiel: the cell high up (A6 F#6 E6 C#6 E6), one ping per group-end, added to by section
    cell_hi = [M.p(14 + d) for d in PR.cell("P")]                 # A5 F#6 E6 C#6 E6
    slots = [(0, 4, (7,)), (4, 12, (5, 7)), (12, 20, (2, 5, 7)), (20, 28, (2, 5, 7, 7.5)),
             (28, 32, (1, 2, 4, 5, 7)), (32, 36, (2, 5, 7))]
    gl, i = [], 0
    for b0, b1, pos in slots:
        for b in range(b0, b1):
            for q in pos:
                gl.append(N(bar(b) + q, 2.0, float(cell_hi[i % 5]), 0.36 if q in (2, 5, 7) else 0.3))
                i += 1
    rise_pitches = [85, 88, 90, 92, 93, 95, 97, 100]          # C#6 E6 F#6 G#6 A6 B6 C#7 E7, climbing
    for k, (b, q) in enumerate([(36, 7), (37, 5), (37, 7), (38, 2), (38, 5), (38, 7), (39, 2), (39, 5)]):
        gl.append(N(bar(b) + q, 2.0, float(rise_pitches[k]), 0.32))
    P["glock"] = PR.fit(gl, pr)
    # violin pizzicati in the gaps (positions 1 and 4), chord tones above the harp
    vp = []
    for b in range(12, 36):
        cur = sorted(V[PLAN[b]])
        for q, j in ((4, 3),) if b < 20 else ((1, 2), (4, 3)):
            vp.append(N(bar(b) + q, 1.0, float(cur[j] + 12), 0.38))
    P["vn_pizz"] = vp
    P["vc_pizz"] = [N(bar(b), 2.0, 45.0, 0.5) for b in range(4, 36)] + \
        [N(bar(b) + 6, 1.5, 52.0, 0.36) for b in range(5, 35, 2)]
    # the glass pair of the old score: the cell and its inversion, three against four, very soft
    g1, g2, t = [], [], 0.0
    while t < bar(BARS):
        g1 += PR.realize(PR.cell("P"), M, 14, t, 3.0, vel=0.36)
        g2 += PR.realize(PR.cell("I"), M, 18, t + 3.0, 3.0, vel=0.3)
        t += 24.0
    P["g1"] = PR.fit([n for n in g1 if n.t < bar(BARS) - 2.0], pr)
    P["g2"] = PR.fit([n for n in g2 if n.t < bar(BARS) - 2.0], pr)
    # THE THEME: piano (bars 4-11), oboe (12-19), the full statement (28-35)
    P["piano_theme"] = line(THEME, bar(4) - 2, vel=0.5)
    P["vn_theme"] = line(THEME, bar(12) - 2, vel=0.52)
    # piano echoes of the cell high up, in the oboe's long notes
    P["piano_echo"] = PR.fit(line([(81, 1), (90, 1), (88, 3)], bar(13) + 2, vel=0.36) +
                             line([(80, 1), (88, 1), (87, 3)], bar(15) + 2, vel=0.36) +
                             line([(81, 1), (90, 1), (88, 4)], bar(19) + 2, vel=0.34), pr)
    # the clarinet: the cell augmented below (A3 F#4 E4 C#4 E4)
    P["cl_aug"] = PR.fit(PR.realize(PR.cell("P"), M, 0, bar(12), [16, 16, 16, 8, 8], vel=0.45), pr)
    # development: the climb as a rising sequence; the horns' cell augmented
    dev1 = line(CLIMB, bar(20) - 2, vel=0.5)
    dev2 = [N(n.t, n.d, float(M.p(M.deg(n.p) + 1)), n.v + 0.04) for n in line(CLIMB, bar(24) - 2, vel=0.52)]
    P["vn_dev"] = PR.fit(dev1 + dev2, pr)
    P["fl_dev"] = PR.fit([N(n.t, n.d, n.p, n.v * 0.9) for n in dev2], pr)               # in unison
    P["hn_aug"] = PR.fit(PR.realize(PR.cell("P"), M, 0, bar(20), [8, 8, 8, 8, 32], vel=0.5), pr)
    # the swell: the full theme, oboe and flute in octaves, horns and organ
    full = line(THEME, bar(28) - 2, vel=0.6)
    P["vn_full"] = full
    P["fl_full"] = [N(n.t, n.d, n.p + 12, n.v * 0.85) for n in full if n.t < bar(32)]
    P["horns"] = sustain_chords(pr, 52, 64, 2, vel=0.55, overlap=0.3, start=bar(27), end=bar(34))
    P["org"] = sustain_chords(pr, 57, 73, 3, vel=0.5, overlap=0.3, start=bar(26), end=bar(35))
    P["org_ped"] = [N(bar(b), bar(8) + 0.3, 45.0, 0.45) for b in range(0, BARS, 8)]
    # the rise: the cell's leap on the piano, then A held, then B over B major
    P["piano_rise"] = [N(bar(36) - 2, 2, 69.0, 0.44), N(bar(36), 8, 78.0, 0.48), N(bar(37) + 4, 4, 76.0, 0.4),
                       N(bar(38), 8, 81.0, 0.44), N(bar(39), 10, 83.0, 0.42)]
    P["air"] = [N(bar(37), 2.5, 76.0, 0.3), N(bar(37) + 2.5, 2.5, 81.0, 0.32), N(bar(38) + 1, 3, 83.0, 0.34),
                N(bar(38) + 4, 4, 87.0, 0.32), N(bar(39), 7, 90.0, 0.3)]
    # the drums (bars 24-33): soft timpani on A and E, a far bass drum, 3+3+2, born with the swell
    swell = Curve([(bar(24), 0.1), (bar(25), 0.22), (bar(26), 0.36), (bar(27), 0.5), (bar(27.9), 0.62),
                   (bar(28), 0.85), (bar(30), 0.92), (bar(31), 1.0), (bar(32), 0.6), (bar(32.6), 0.3),
                   (bar(33), 0.0)])
    A2, E2 = 45.0, 40.0
    fig = [(0, "bd", 0, 0.9, 0.0), (0, "timp", A2, 0.85, 0.0), (3, "timp", A2, 0.66, 0.25),
           (5.5, "timp", A2, 0.28, 0.6), (6, "timp", E2, 0.72, 0.4), (7.5, "timp", A2, 0.32, 0.55),
           (8, "timp", A2, 0.8, 0.12), (11, "timp", A2, 0.64, 0.3), (14, "timp", E2, 0.72, 0.35),
           (14, "bd", 0, 0.6, 0.5), (15, "timp", A2, 0.3, 0.62), (15.5, "timp", A2, 0.36, 0.5)]
    P["drums"] = groove(bar(24), bar(33), 16, fig, swell, vel=(0.18, 0.78))
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.015))
    S = lambda notes, seed, j=0.01: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.24), (sec(4), 0.28), (sec(12), 0.36), (sec(20), 0.46), (sec(24), 0.56), (sec(27.8), 0.7),
                 (sec(29), 0.86), (sec(31.5), 0.9), (sec(33), 0.62), (sec(36), 0.36), (sec(39), 0.28),
                 (LOOP, 0.24)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.3, "swell": 0.15, "taper": 2.0}

    hp = S(P["harp"], 1, 0.008)
    for n in hp:
        n.v = float(n.v * (0.8 + 0.5 * arc(n.t)))
    st.play("harp", hp, "harp", seed=1, gain_db=-1)
    gk = S(P["glock"], 2, 0.006)
    for n in gk:
        n.v = float(n.v * (0.8 + 0.4 * arc(n.t)))
    st.play("glock", gk, "glock", seed=2, gain_db=9)
    vp = S(P["vn_pizz"], 3, 0.006)
    for n in vp:
        n.v = float(n.v * (0.7 + 0.5 * arc(n.t)))
    st.play("violins_pizz", vp, "violins_pizz", seed=3, gain_db=5, seat="violins")
    pz = S(P["vc_pizz"], 4, 0.008)
    for n in pz:
        n.v = float(n.v * (0.75 + 0.45 * arc(n.t)))
    st.play("cellos_pizz", pz, "cellos_pizz", seed=4, gain_db=0, seat="cellos")
    gl = st.stem("glass", {"shimmer:cathedral2": 0.45, "concert": 0.5}, depth=0.75)
    EL.glass(gl, S(P["g1"], 5, 0.008), gain=0.3, seed=5, attack=0.15, release=2.5, pan_spread=0.0, breath=0.08,
             bright=0.6)
    EL.glass(gl, S(P["g2"], 6, 0.008), gain=0.24, seed=6, attack=0.15, release=2.5, pan_spread=0.0, breath=0.08,
             bright=0.6)
    EL.glass_line(gl, S(P["air"], 7, 0.0), gain=0.4, seed=7, glide=0.6, attack=0.8, release=3.0, bright=0.5)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4000, 0.7), circular=True)
    gl.buf = (gl.buf + FX.echo(gl.buf, clk.s(3), fb=0.35, mix=0.3, lp=2400, circular=True)).astype("float32")

    # the theme
    st.play("piano", S(P["piano_theme"], 10, 0.008), "piano", seed=10, gain_db=6, layer_bias=-0.1, release=1.4)
    st.play("piano", S(P["piano_echo"], 11, 0.006), "piano", seed=11, gain_db=8, layer_bias=-0.2, release=1.2)
    st.play("piano", S(P["piano_rise"], 12, 0.006), "piano", seed=12, gain_db=6, layer_bias=-0.15, release=2.0)
    vdyn = Curve([(sec(11.5), 0.42), (sec(14), 0.5), (sec(19.5), 0.5), (sec(20), 0.45), (sec(24), 0.55),
                  (sec(27.8), 0.62), (sec(29), 0.72), (sec(31.5), 0.75), (sec(33), 0.6), (sec(35.8), 0.5)])
    vn = S(mono(P["vn_theme"] + P["vn_dev"] + P["vn_full"]), 13)
    # the oboe a little further into the hall than the other pieces' leads: its slow notes melt into each other
    st.play("oboe", vn, "oboe", seed=13, dyn=vdyn, gain_db=10, shape=shape,
            lag=0.02, **LD.lead(st, wash=1.0))
    fdyn = Curve([(sec(23.5), 0.4), (sec(26), 0.5), (sec(28), 0.6), (sec(31.5), 0.64), (sec(32.2), 0.4)])
    st.play("flutes", S(mono(P["fl_dev"] + P["fl_full"]), 14), "flute", seed=14, dyn=fdyn, gain_db=2, shape=shape,
            lag=0.02)
    st.play("clarinets", S(P["cl_aug"], 15), "clarinet", seed=15,
            dyn=Curve([(sec(12), 0.38), (sec(15), 0.46), (sec(19), 0.42), (sec(20), 0.32)]), gain_db=2,
            shape={"attack": 0.6, "swell": 0.15, "taper": 2.5}, lag=0.02)
    hdyn = Curve([(sec(20), 0.38), (sec(24), 0.5), (sec(27.5), 0.6), (sec(29), 0.7), (sec(31.5), 0.72),
                  (sec(33), 0.45), (sec(34.2), 0.3)])
    st.play("horns", S(P["hn_aug"], 16), "horns", seed=16, dyn=hdyn, gain_db=-3,
            shape={"attack": 0.6, "swell": 0.2, "taper": 2.5}, lag=0.03)
    st.play("horns", S(P["horns"], 17), "horns", seed=17, dyn=hdyn, gain_db=-6,
            shape={"attack": 0.6, "swell": 0.2, "taper": 2.5}, lag=0.03)
    st.play("organ", S(P["org_ped"], 18, 0.0), "organ_soft_pedal", seed=18, dyn=arc, gain_db=-7)
    st.play("organ", S(P["org"], 19, 0.0), "organ_soft", seed=19,
            dyn=Curve([(sec(26), 0.25), (sec(28.5), 0.55), (sec(31.5), 0.6), (sec(35), 0.25)]), gain_db=-12)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08, circular=True).astype("float32")

    D = P["drums"]
    st.play("timpani", S(D.get("timp", []), 20, 0.004), "timpani", seed=20, gain_db=-1)
    st.play("drums", S(D.get("bd", []), 21, 0.003), "bass_drum", seed=21, gain_db=-3, seat="bass_drum")

    out = st.render({"concert": {"seed": 61}, "cathedral2": {"seed": 62}, "chamber": {"seed": 64},
                     "shimmer:cathedral2": {"seed": 63, "gens": 2, "fb": 0.45}}, warmth=0.3)
    return finish_loop("music", "snow", out, LOOP, 4, -17.0, 192, tilt_hs_db=-1.5,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "A lydian",
                             "instrument": "piano, oboe, harp and glockenspiel"})


if __name__ == "__main__":
    render()
