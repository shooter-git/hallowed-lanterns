"""VIII. The Marigold Garden — "Remember Me" (rescored, Glass / Zimmer).

Remembering, warm and bittersweet, in straight time. The upright piano's
left hand cycles a broken chord in eighths, one note changing at a time, so
the bittersweet turn happens inside the figure: C major 7 becomes C minor 6
when the E slips to E-flat. The progression is an eight-bar cycle (G, Em7,
Cmaj9, G/B, Cm6, Cm6, G/D, D7sus4). Over it the right hand plays the
Ember's cell augmented - a bar a note, G E D B D - every note landing on
its chord. Then a clarinet takes the cell eight bars later (a canon at the
cycle) while the flute holds a countermelody of suspensions over cello
pizzicati; then the bridge leans on E minor 9 and C major 9 and comes home
through the borrowed C minor 6 (never leaving G), horns and soft far
strings swelling under piano fragments of the cell in stretto and viola
pizzicati. Last, a solo violin plays the INVERSION, intimately, and
everything falls back to the piano.
G major with a borrowed C minor, 4/4 at 72, 40 bars = 133.3 s.

  bars  0-7   the piano's cycle alone; the harp from bar 4
  bars  8-15  the right hand: the cell augmented
  bars 16-23  clarinet: the cell (canon at the cycle); flute's countermelody
  bars 24-31  the bridge: E minor 9, C major 9, A minor 9, C minor 6, D sus
  bars 32-39  solo violin: the inversion; the piano alone again
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords, roots
from hlaudio import process as PR
from hlaudio import effects as FX
from hlaudio.piece import finish_loop

TITLE = "Remember Me"
BAR = 8            # eighths
BARS = 40
BPM_UNIT = 144     # eighths per minute (quarter = 72)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 133.33 s
M = PR.Mode(55, "ionian")  # G

# (chord, bars, left-hand voicing)
CYC = [("Gadd9", 1, [43, 50, 57, 59]), ("Em7", 1, [40, 50, 55, 59]), ("Cmaj9", 1, [36, 50, 55, 59]),
       ("G/B", 1, [35, 50, 55, 59]), ("Cm6", 1, [36, 51, 55, 57]), ("Cm6", 1, [36, 51, 55, 57]),
       ("G/D", 1, [38, 50, 55, 59]), ("D7sus4", 1, [38, 48, 55, 57])]
BRIDGE = [("Em9", 2, [40, 50, 55, 59]), ("Cmaj9", 2, [36, 50, 55, 59]), ("Am9", 1, [45, 48, 55, 59]),
          ("Cm6", 1, [36, 51, 55, 57]), ("D7sus4", 2, [38, 48, 55, 57])]
PLAN = CYC * 3 + BRIDGE + CYC
LH_FIG = [0, 1, 2, 3, 2, 1, 3, 2]
LH_ACC = [1.0, .7, .8, .9, .72, .78, .88, .74]


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b, _ in PLAN))


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    # the bass moves with the chord; above it ONE voice changes per half bar
    lh, cur, t = [], list(PLAN[-1][2]), 0.0
    for c, b, s in PLAN:
        for k in range(b):
            for i, idx in enumerate(LH_FIG):
                if i == 0:
                    cur[0] = s[0]
                if i in (0, 4) and cur[1:] != s[1:]:
                    cand = [(s[j] in cur, abs(a - g), j) for j, (a, g) in enumerate(zip(cur, s)) if j > 0 and a != g]
                    j = min(cand)[2]                       # prefer a change that makes no unison
                    cur[j] = s[j]
                lh.append(N(t + i, 2.2, float(cur[idx]), 0.4 * LH_ACC[i]))
            t += BAR
    P["lh"] = lh
    P["rh"] = PR.realize(PR.cell("P"), M, 7, bar(8), [8, 8, 8, 8, 16], vel=0.55)              # G4 E5 D5 B4 D5
    P["rh2"] = PR.fit(PR.realize(PR.cell("P", 3), M, 11, bar(24), [3, 3, 10], vel=0.55) +       # D5 B5 A5
                      PR.realize(PR.cell("P", 3), M, 9, bar(25), [3, 3, 10], vel=0.5) +         # B4 G5 F#5
                      PR.realize(PR.cell("P", 3), M, 7, bar(26) + 4, [3, 3, 10], vel=0.52) +
                      PR.realize(PR.cell("P", 3), M, 8, bar(28), [3, 3, 10], vel=0.5), pr)
    P["vc_cell"] = PR.realize(PR.cell("P"), M, 0, bar(16), [8, 8, 8, 8, 16], vel=0.6)          # G3 E4 D4 B3 D4
    # the countermelody of suspensions over the cellos
    P["vn_counter"] = PR.fit([N(bar(16), 8, 83.0, 0.45), N(bar(17), 8, 83.0, 0.48), N(bar(18), 6, 83.0, 0.5),
                              N(bar(18) + 6, 2, 81.0, 0.46), N(bar(19), 8, 81.0, 0.48), N(bar(20), 8, 79.0, 0.5),
                              N(bar(21), 8, 81.0, 0.5), N(bar(22), 8, 83.0, 0.48), N(bar(23), 8, 84.0, 0.46)], pr)
    # the solo violin: the inversion, from D6 (D F# G B G)
    P["solo"] = PR.realize(PR.cell("I"), M, 18, bar(32), [8, 8, 8, 8, 12], vel=0.55)
    P["harp"] = [N(n.t, n.d, n.p + 12, n.v) for n in lh if bar(4) <= n.t < bar(32) and int(n.t) % BAR in (0, 3, 6)]
    P["vla"] = sustain_chords(pr, 52, 66, 2, vel=0.5, start=bar(16), end=bar(32))
    P["vc"] = sustain_chords(pr, 43, 55, 2, vel=0.5, start=bar(24), end=bar(32))
    P["cb"] = roots(pr, 31, vel=0.5, start=bar(22), end=bar(33))
    P["vn"] = sustain_chords(pr, 67, 79, 2, vel=0.5, start=bar(24), end=bar(32))
    P["horns"] = sustain_chords(pr, 52, 64, 2, vel=0.55, start=bar(24), end=bar(31))
    P["timp_roll"] = [N(bar(23), bar(1) + 0.3, 47.0, 0.5)]
    P["timp"] = [N(bar(24), 3, 47.0, 0.55)]
    # pizzicato: cellos pluck the bass on 1 and 3 (bars 12-31), violas answer the piano in the bridge
    pz_vc, pz_vla, t = [], [], 0.0
    for c, b, s_ in PLAN:
        for k in range(b):
            tb = t + bar(k)
            if bar(12) <= tb < bar(32):
                bp = s_[0] + (12 if s_[0] < 36 else 0)
                pz_vc += [N(tb, 3.0, float(bp), 0.55), N(tb + 4, 2.0, float(bp + 7), 0.4)]
            if bar(24) <= tb < bar(32):
                pz_vla += [N(tb + 3, 1.0, float(s_[2] + 12), 0.4), N(tb + 6, 1.0, float(s_[3] + 12), 0.38)]
        t += bar(b)
    P["pz_vc"], P["pz_vla"] = pz_vc, pz_vla
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.025))
    S = lambda notes, seed, j=0.012: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.4), (sec(4), 0.43), (sec(8), 0.48), (sec(16), 0.52), (sec(23), 0.62), (sec(24.5), 0.84),
                 (sec(30), 0.8), (sec(32), 0.55), (sec(37), 0.42), (LOOP, 0.4)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.45, "swell": 0.2, "taper": 2.5}

    lh = S(P["lh"], 1, 0.01)
    for n in lh:
        n.v = float(n.v * (0.9 + 0.4 * arc(n.t)))
    st.play("piano", lh, "piano", seed=1, gain_db=9, release=0.8, layer_bias=-0.2)
    st.play("piano", S(P["rh"], 2), "piano", seed=2, gain_db=12, release=1.2, layer_bias=-0.1)
    st.play("piano", S(P["rh2"], 3), "piano", seed=3, gain_db=11, release=1.0)
    harp = S(P["harp"], 4, 0.01)
    for n in harp:
        n.v = float(n.v * (0.6 + 0.5 * arc(n.t)))
    st.play("harp", harp, "harp", seed=4, gain_db=1)
    st.play("clarinets", S(P["vc_cell"], 5), "clarinet", seed=5,
            dyn=Curve([(sec(15.8), 0.45), (sec(18), 0.62), (sec(21), 0.62), (sec(22.5), 0.45)]), gain_db=2,
            shape=shape, lag=0.02)
    st.play("flutes", S(P["vn_counter"], 6), "flute", seed=6,
            dyn=Curve([(sec(16), 0.3), (sec(19), 0.48), (sec(23), 0.45)]), gain_db=0, shape=shape, lag=0.02)
    pv = S(P["pz_vc"], 15, 0.008)
    for n in pv:
        n.v = float(n.v * (0.7 + 0.45 * arc(n.t)))
    st.play("cellos_pizz", pv, "cellos_pizz", seed=15, gain_db=1, seat="cellos")
    st.play("violas_pizz", S(P["pz_vla"], 16, 0.008), "violas_pizz", seed=16, gain_db=-1, seat="violas")
    st.play("solo_violin", S(P["solo"], 7), "solo_violin", seed=7,
            dyn=Curve([(sec(31.8), 0.42), (sec(34), 0.55), (sec(37), 0.5), (sec(38.5), 0.32)]), gain_db=3,
            shape=shape, legato=True, slide=0.1, lag=0.02)
    far = dict(shape=shape, lag=0.03, depth=0.8)
    st.play("violas", S(P["vla"], 8), "violas", seed=8, dyn=arc, gain_db=-14, **far)
    st.play("cellos", S(P["vc"], 9), "cellos", seed=9, dyn=arc, gain_db=-13, **far)
    st.play("basses", S(P["cb"], 10), "basses", seed=10, dyn=arc, gain_db=-11, **far)
    st.play("violins2", S(P["vn"], 11), "violins", seed=11, dyn=arc, gain_db=-16, seat="violins2", **far)
    st.play("horns", S(P["horns"], 12), "horns", seed=12,
            dyn=Curve([(sec(23.5), 0.3), (sec(25), 0.62), (sec(30), 0.58), (sec(31.5), 0.3)]), gain_db=-6,
            shape=shape, lag=0.03)
    st.play("timpani", S(P["timp_roll"], 13, 0.0), "timpani_roll", seed=13,
            dyn=Curve([(sec(23), 0.02), (sec(24), 0.5), (sec(24.05), 0.2)]), gain_db=-9, release=0.4)
    st.play("timpani", S(P["timp"], 14, 0.004), "timpani", seed=14, gain_db=-8)

    out = st.render({"concert": {"seed": 81}}, warmth=0.35)
    return finish_loop("music", "marigold", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "G major",
                             "instrument": "piano"})


if __name__ == "__main__":
    render()
