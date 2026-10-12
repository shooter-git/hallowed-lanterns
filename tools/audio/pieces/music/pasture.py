"""IV. The Pasture of Giants — "Gentle Giants" (rescored, Zimmer).

A long slow build by adding layers, never by getting faster. Open fifths on
D (pizzicato and soft low strings, the organ's pedal) under Mixolydian
chords that move above the same bass (D5, C/D, G/D). The horns state the
Ember's cell in whole-bar notes; a second horn answers it modally at the
fifth two bars later; then the trombones and the tuba enter with it in
STRETTO, each a bar after the last, while a dotted spiccato ostinato
(long-short, long-short) grows in the cellos and basses. A solo violin and a
clarinet hold the cell's inversion high in two-bar notes. The lift stays in
the key - G over B, C, then D - with the one low braam of the piece on G;
the full organ and timpani bring it home to D, and the layers come off one
by one until the fifths and the stars are left.

The giants' footsteps: the build has a beat, and only the build. From bar 20
low timpani and the concert bass drum walk in 3+3+2 (eighths: the long,
long, short of a heavy gait), the drums following the bass (D, then G, C);
at first only the downbeat, softly, then the syncopations, then the ghost
notes and the grace-note pickups, growing with the swell to the top at bar
24 (the braam) and falling away again by bar 31, where the fifths return.
D Mixolydian, 4/4 at 60, 34 bars = 136 s.
"""
import numpy as np

from hlaudio.core import rng
from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords, roots
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.beats import groove, drum_pitch
from hlaudio.piece import finish_loop

TITLE = "Gentle Giants"
BAR = 4
BARS = 34
BPM = 60
LOOP = BARS * BAR * 60 / BPM  # 136 s
M = PR.Mode(50, "mixolydian")  # D (C natural)
STARS = [81, 86, 88, 90, 93, 95, 98]

CH = ("D5:8 | Csus2/D:8 | G/D:8 | D5:8 | "            # 0-7
      "D5:8 | C/D:8 | G/D:8 | Dsus4:4 D:4 | "         # 8-15
      "D:8 | C/D:8 | G/B:8 | C:4 Dsus4:4 | "           # 16-23
      "D:8 | G:4 C:4 | Dsus4:4 D:4 | G/D:8 | "         # 24-31
      "D5:8")                                          # 32-33


def bar(b):
    return b * BAR


def score():
    pr = prog(CH)
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    # the brass canon / stretto of the cell, a bar a note
    P["hn1"] = PR.fit(PR.realize(PR.cell("P"), M, 7, bar(8), [4, 4, 4, 4, 8], vel=0.6), pr)       # D4 B4 A4 F#4 A4
    P["hn2"] = PR.fit(PR.realize(PR.cell("P"), M, 4, bar(10), [4, 4, 4, 4, 8], vel=0.55), pr)      # A3 E4 D4 C4 D4
    P["tbn"] = PR.fit(PR.realize(PR.cell("P"), M, 0, bar(16), [4, 4, 4, 4, 8], vel=0.6), pr)       # D3 B3 A3 F#3 A3
    P["tuba"] = PR.fit(PR.realize(PR.cell("P"), M, -7, bar(17), [4, 4, 4, 4, 8], vel=0.6), pr)     # D2 ...
    P["hn_top"] = PR.fit(PR.realize(PR.cell("P"), M, 7, bar(24), [4, 4, 4, 4, 8], vel=0.75), pr)
    # strings: the inversion held high, two bars a note
    P["vn"] = PR.fit(PR.realize(PR.cell("I"), M, 14, bar(16), [8, 8, 8, 8], vel=0.55), pr)        # D5 F#4.. (up an 8ve)
    for n in P["vn"]:
        n.p += 12
    P["vla"] = PR.fit(PR.realize(PR.cell("I"), M, 11, bar(18), [8, 8, 8, 8], vel=0.5), pr)
    # the dotted ostinato (long-short in sixteenths: 3+1) in cellos and basses
    dot = []
    for b in range(10, 31):
        for q in range(4):
            t = bar(b) + q
            for o, d_, v in ((0.0, 0.7, 1.0), (0.75, 0.22, 0.7)):
                dot.append(N(t + o, d_, 38.0 if q % 2 == 0 else 45.0, 0.5 * v))
    P["dot_vc"] = dot
    P["dot_cb"] = [N(n.t, n.d, 26.0 + (n.p - 38.0), n.v) for n in dot if n.p == 38.0]
    P["fifths"] = [N(bar(0), bar(10), 38.0, 0.5), N(bar(0), bar(10), 45.0, 0.45),
                   N(bar(31), bar(3), 38.0, 0.5), N(bar(31), bar(3), 45.0, 0.45)]
    P["cb_ped"] = [N(bar(0), bar(10), 38.0, 0.5), N(bar(30), bar(4), 38.0, 0.5)]
    # plucked open fifths under the pedal where the spiccato is silent
    pz = []
    for b in list(range(0, 10)) + list(range(31, 34)):
        pz += [N(bar(b), 1.5, 38.0, 0.55), N(bar(b) + 2, 1.5, 45.0, 0.42)]
    P["pz"] = pz
    P["org_soft"] = sustain_chords(pr, 50, 69, 3, vel=0.5, overlap=0.4, end=bar(24)) + \
        sustain_chords(pr, 50, 69, 3, vel=0.5, overlap=0.4, start=bar(31))
    P["org_ped"] = [N(bar(0), bar(34), 26.0, 0.5)]
    P["org_full"] = sustain_chords(pr, 50, 74, 4, vel=0.6, start=bar(24), end=bar(31))
    P["org_full_ped"] = roots(pr, 26, vel=0.6, start=bar(24), end=bar(31))
    P["timp_roll"] = [N(bar(22), bar(2) + 0.3, 50.0, 0.6)]
    # the giants' gait (bars 20-31): timpani on the bass and its fifth, the bass drum,
    # 3+3+2 eighths with sixteenth ghosts and pickups, born and gone with the swell
    swell = Curve([(bar(20), 0.1), (bar(21), 0.24), (bar(22), 0.4), (bar(23), 0.56), (bar(23.8), 0.68),
                   (bar(24), 1.0), (bar(26), 0.95), (bar(28), 0.9), (bar(29), 0.72), (bar(30), 0.42),
                   (bar(30.75), 0.15), (bar(31), 0.0)])
    lo, hi = drum_pitch(pr, 38, 49), drum_pitch(pr, 38, 49, fifth=True)
    fig = [(0, "bd", 0, 1.0, 0.0), (0, "timp", lo, 0.9, 0.0),
           (1.25, "timp", hi, 0.3, 0.6), (1.5, "timp", hi, 0.72, 0.22),
           (2.75, "timp", lo, 0.32, 0.62), (3.0, "timp", lo, 0.78, 0.38), (3.0, "bd", 0, 0.5, 0.72),
           (3.5, "timp", lo, 0.3, 0.75), (3.75, "timp", lo, 0.4, 0.5)]
    P["drums"] = groove(bar(20), bar(31) + 1, BAR, fig, swell, vel=(0.2, 0.86), dur=3.0)
    P["timp"] = [N(bar(31), 4, 38.0, 0.45)]
    r = rng("stars")
    st, t = [], 1.0
    while t < BARS * BAR:
        if not (bar(20) <= t < bar(30)):
            st.append(N(t, 6.0, float(r.choice(STARS)), float(r.uniform(0.25, 0.4))))
        t += r.uniform(3.0, 7.0)
    P["stars"] = st
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM, rubato=(8 * BAR, 0.02))
    S = lambda notes, seed, j=0.015: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.34), (sec(8), 0.4), (sec(12), 0.47), (sec(16), 0.55), (sec(20), 0.64), (sec(23.5), 0.76),
                 (sec(24.5), 0.88), (sec(29), 0.85), (sec(31), 0.5), (sec(33), 0.36), (LOOP, 0.34)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.5, "swell": 0.22, "taper": 3.0}
    br = dict(shape=shape, lag=0.03)
    st.play("horns", S(P["hn1"], 1), "horns", seed=1, dyn=arc, gain_db=1, double=1, **br)
    st.play("horns2", S(P["hn2"], 2), "horns", seed=2, dyn=arc, gain_db=-2, seat="horns", **br)
    st.play("trombones", S(P["tbn"], 3), "trombones", seed=3, dyn=arc, gain_db=-3, double=1, **br)
    st.play("tuba", S(P["tuba"], 4), "tuba", seed=4, dyn=arc, gain_db=-3, **br)
    st.play("horns", S(P["hn_top"], 5), "horns", seed=5, dyn=arc, gain_db=0, double=2, **br)
    st.play("solo_violin", S(P["vn"], 6), "solo_violin", seed=6, dyn=arc, gain_db=0, legato=True, slide=0.1, **br)
    st.play("clarinets", S(P["vla"], 7), "clarinet", seed=7, dyn=arc, gain_db=2, **br)
    dv = S(P["dot_vc"], 8, 0.006)
    db_ = S(P["dot_cb"], 9, 0.006)
    for n in dv + db_:
        n.v = float(n.v * (0.45 + 0.75 * arc(n.t)))
    st.play("cellos_spic", dv, "cellos_spic", seed=8, gain_db=1, seat="cellos")
    st.play("basses_spic", db_, "basses_spic", seed=9, gain_db=-1, seat="basses")
    st.play("cellos", S(P["fifths"], 10), "cellos", seed=10, dyn=arc, gain_db=-5, depth=0.78, shape=shape)
    st.play("basses", S(P["cb_ped"], 11), "basses", seed=11, dyn=arc, gain_db=-5, depth=0.8, shape=shape)
    st.play("cellos_pizz", S(P["pz"], 21, 0.006), "cellos_pizz", seed=21, gain_db=3, seat="cellos")
    st.play("organ", S(P["org_soft"], 12, 0.0), "organ_soft", seed=12, dyn=arc, gain_db=-9)
    st.play("organ", S(P["org_ped"], 13, 0.0), "organ_soft_pedal", seed=13, dyn=arc, gain_db=-6)
    top = Curve([(sec(23.5), 0.3), (sec(24.5), 0.85), (sec(30), 0.8), (sec(31.5), 0.3)])
    st.play("organ", S(P["org_full"], 14, 0.0), "organ", seed=14, dyn=top, gain_db=-13)
    st.play("organ", S(P["org_full_ped"], 15, 0.0), "organ_pedal", seed=15, dyn=top, gain_db=-9)
    st.play("timpani", S(P["timp_roll"], 16, 0.0), "timpani_roll", seed=16,
            dyn=Curve([(sec(22), 0.02), (sec(24), 0.75), (sec(24.05), 0.3)]), gain_db=-5, release=0.4)
    st.play("timpani", S(P["timp"], 17, 0.004), "timpani", seed=17, gain_db=-2)
    D = P["drums"]
    st.play("timpani", S(D.get("timp", []), 22, 0.004), "timpani", seed=22, gain_db=5)
    st.play("drums", S(D.get("bd", []), 23, 0.003), "bass_drum", seed=23, gain_db=4, seat="bass_drum")
    # the braam on the G (bar 25): low brass and a sub
    t_b = sec(25) - 0.05
    bdyn = Curve([(t_b, 0.35), (t_b + 1.0, 0.95), (t_b + 2.6, 0.75), (t_b + 4.0, 0.3)])
    st.play("braam", [N(t_b, 4.0, 43.0, 0.95), N(t_b, 4.0, 50.0, 0.9)], "trombones", seed=18, dyn=bdyn,
            gain_db=-8, seat="trombones")
    st.play("braam", [N(t_b, 4.0, 31.0, 0.95)], "tuba", seed=19, dyn=bdyn, gain_db=-7, seat="tuba")
    bm = st.stem("braam")
    EL.sub_swell(bm, t_b, 3.2, 31.0, gain=0.18, attack=0.9, release=1.5)
    gl = st.stem("glass", {"shimmer:cathedral2": 0.5, "concert": 0.5}, depth=0.8)
    EL.glass(gl, S(P["stars"], 20, 0.0), gain=0.4, seed=20, attack=1.2, release=4.0, pan_spread=0.8)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08, circular=True).astype("float32")

    out = st.render({"concert": {"seed": 41}, "cathedral2": {"seed": 42},
                     "shimmer:cathedral2": {"seed": 43, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "pasture", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": BPM, "meter": "4/4", "beat": "quarter", "key": "D mixolydian",
                             "instrument": "horns"})


if __name__ == "__main__":
    render()
