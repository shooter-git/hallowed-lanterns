"""The Picture Show — a silent-film waltz for the shadow-puppet screen.

Deliberately an old-time waltz (the one place for one), but kept light and
charming rather than corny: the upright piano's left hand rolls each bar as
bass - two middle notes - one high note under the pedal instead of thumping
oom-pah-pah chords, the harmony is coloured (F6, Gm9, C9, a borrowed B-flat
minor 6), and the tune - the Ember's motif in F (F | D C A C) - passes from
the piano to a solo violin in the pit (over pizzicato strings), to a
clarinet, to a flute in the trio, and back to the violin and piano together
with the clarinet a third below. A small hall, a touch of tape wobble, a little
rubato like a pianist in a cinema pit.
3/4 at 132 bpm: 88 bars = exactly 120 s.

  bars  0-3   piano vamp
  bars  4-19  A: the tune on the piano
  bars 20-35  B: D minor 9: the solo violin sings over pizzicati, the piano answers
  bars 36-51  A: the clarinet sings it
  bars 52-67  C (trio): B-flat, the flute, violas beneath
  bars 68-83  A: solo violin and piano, clarinet a third below
  bars 84-87  a little cadence, and round again
"""
import numpy as np

from hlaudio.score import N, seq, prog, humanize, Clock, chord_pcs
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords
from hlaudio import process as PR
from hlaudio import effects as FX
from hlaudio.piece import finish_loop

TITLE = "The Picture Show"
BAR = 3
BARS = 88
BPM_UNIT = 132
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s
MF = PR.Mode(53, "ionian")  # F

A_CH = ("F6:3 | Fmaj7:3 | Gm9:3 | C9:3 | Gm9:3 | C7:3 | Fmaj7:3 | Fadd9:3 | "
        "F6:3 | F7:3 | Bbadd9:3 | Bbm6:3 | F/C:3 | C9:3 | Fmaj7:3 | C7sus4:3 | ")
A_MEL = ("D6:2 C6:1 | A5:1 C6:2 | Bb5:2 A5:1 | G5:1 Bb5:2 | A5:2 G5:1 | E5:1 G5:2 | F5:3 | r:2 F5:1 | "
         "D6:2 C6:1 | A5:1 Eb6:2 | D6:2 C6:1 | Bb5:1 Db6:2 | C6:2 A5:1 | G5:1 Bb5:1 E5:1 | F5:3 | r:2 F5:1 | ")
B_CH = ("Dm9:3 | Dm7:3 | Gm9:3 | Gm7:3 | C9:3 | C7:3 | Fmaj7:3 | F6:3 | "
        "Dm9:3 | Dm7:3 | Gm9:3 | Bbm6:3 | F/C:3 | D7:3 | Gm7:2 C7:1 | F:3 | ")
B_MEL = ("A5:3 | F5:1 A5:1 D6:1 | D6:2 C6:1 | Bb5:3 | G5:3 | E5:1 G5:1 C6:1 | C6:2 A5:1 | F5:3 | "
         "A5:3 | F5:1 A5:1 D6:1 | D6:2 Bb5:1 | Db6:2 Bb5:1 | A5:2 C6:1 | F#5:1 A5:1 C6:1 | G5:2 E5:1 | F5:2 F5:1 | ")
C_CH = ("Bb6:3 | Bbmaj7:3 | Cm9:3 | F9:3 | Cm9:3 | F7:3 | Bbmaj7:3 | Bbadd9:3 | "
        "Ebmaj7:3 | Ebm6:3 | Bb/D:3 | G7:3 | Cm9:3 | F7:3 | Bb6:3 | C7:3 | ")
C_MEL = ("G5:2 F5:1 | D5:1 F5:2 | Eb5:2 D5:1 | C5:1 Eb5:2 | D5:2 C5:1 | A4:1 C5:2 | Bb4:3 | r:2 Bb4:1 | "
         "G5:2 F5:1 | Eb5:1 Gb5:2 | F5:2 D5:1 | B4:1 D5:1 F5:1 | Eb5:2 C5:1 | A4:1 C5:1 Eb5:1 | D5:3 | r:2 F5:1 | ")
ANS = ("r:2 D6:1 | A6:2 r:1 | r:2 Bb5:1 | D6:2 r:1 | r:2 C6:1 | E6:2 r:1 | r:3 | r:3 | "
       "r:2 D6:1 | A6:2 r:1 | r:2 Bb5:1 | Db6:2 r:1 | r:3 | r:3 | r:3 | r:3")


def bar(b):
    return b * BAR


def harmony():
    return prog("F6:3 | F6:3 | C7sus4:3 | C7:3 | " + A_CH + B_CH + A_CH + C_CH + A_CH +
                "Fmaj7:3 | Bbadd9:3 | F/C:2 C7:1 | F6:3")


def waltz_lh(pr):
    """Bass on 1 (root, the fifth every other bar), two middle chord tones on 2,
    one higher tone on 3, all held as if pedalled through the bar."""
    out = []
    for (t0, d, sym) in pr:
        pcs, bass, root = chord_pcs(sym)
        t = t0
        while t < t0 + d - 1e-6:
            b = int(round(t // BAR))
            pos = t - bar(b)
            if abs(pos) < 1e-6:
                bp = 41 + ((bass - 41) % 12)                        # F2..E3
                if b % 2 == 1 and "/" not in sym:
                    bp = 41 + ((root + 7 - 41) % 12)
                out.append(N(t, BAR - pos, float(bp - (12 if bp > 47 else 0)), 0.5))
            mids = sorted(p for p in range(53, 65) if p % 12 in pcs)  # F3..E4
            highs = sorted(p for p in range(62, 72) if p % 12 in pcs)
            if abs(pos - 1) < 1e-6 and mids:
                for p in (mids[0], mids[min(2, len(mids) - 1)]):
                    out.append(N(t, 2.0, float(p), 0.34))
            if abs(pos - 2) < 1e-6 and highs:
                out.append(N(t, 1.0, float(highs[min(1, len(highs) - 1)]), 0.3))
            t += 1.0
    return out


def third_below(notes):
    return [N(n.t, n.d, float(MF.p(MF.deg(n.p) - 2)), n.v * 0.8) for n in notes]


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    pick = lambda b, p="F5": seq(f"{p}:1", bar(b) - 1, vel=0.58)
    a1 = pick(4) + seq(A_MEL, bar(4), vel=0.64)
    a2 = [n for n in pick(36) + seq(A_MEL, bar(36), vel=0.64) if n.t < bar(51) + 2]
    a3 = [n for n in pick(68) + seq(A_MEL, bar(68), vel=0.68) if n.t < bar(83) + 2]
    P["pno_mel"] = a1 + a3
    P["clar"] = [N(n.t, n.d, n.p - 12, n.v) for n in a2]
    P["clar_counter"] = [N(n.t, n.d, n.p - 12, n.v) for n in third_below(a3)]
    P["vn_b"] = seq(B_MEL, bar(20), vel=0.6)
    P["vn_a3"] = a3
    P["flute"] = seq("Bb4:1", bar(52) - 1, vel=0.58) + seq(C_MEL, bar(52), vel=0.62)
    P["pno_ans"] = seq(ANS, bar(20), vel=0.42)
    P["lh"] = waltz_lh(pr)
    # B: pizzicato strings take the waltz (cellos on 1, violas on 2 and 3), the piano's left hand rests
    P["lh"] = [n for n in P["lh"] if not (bar(20) <= n.t < bar(36))]
    pz_vc, pz_vla = [], []
    for (t0, d, sym) in pr:
        if not (bar(20) <= t0 < bar(36)):
            continue
        pcs, bass, root = chord_pcs(sym)
        for k in range(int(round(d))):
            t = t0 + k
            if abs((t % BAR)) < 1e-6:
                pz_vc.append(N(t, 0.9, float(38 + ((bass - 38) % 12)), 0.6))
            else:
                mids = sorted(p for p in range(57, 69) if p % 12 in pcs)
                pz_vla += [N(t, 0.6, float(p), 0.45) for p in mids[:2]]
    P["pz_vc"], P["pz_vla"] = pz_vc, pz_vla
    P["cb_pz"] = [N(n.t, 0.9, n.p - 12, 0.5) for n in waltz_lh(pr) if n.p < 50 and bar(36) <= n.t < bar(84)]
    P["vla_sus"] = sustain_chords(pr, 55, 67, 2, vel=0.45, start=bar(52), end=bar(68))
    P["vc_sus"] = sustain_chords(pr, 43, 55, 1, vel=0.45, start=bar(68), end=bar(84))
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(8 * BAR, 0.03))
    S = lambda notes, seed, j=0.009: humanize(clk.notes(notes), seed, t_jit=j)
    st = Stage(LOOP, circular=True, hall="chamber")
    shape = {"attack": 0.12, "swell": 0.12, "taper": 1.5}

    st.play("piano", S(P["lh"], 1), "piano", seed=1, gain_db=5, release=0.5)
    st.play("piano", S(P["pno_mel"], 2), "piano", seed=2, gain_db=9, release=0.6)
    st.play("piano", S(P["pno_ans"], 3), "piano", seed=3, gain_db=4, release=0.8)
    st.play("solo_violin", S(P["vn_b"], 4), "solo_violin", seed=4, gain_db=4, legato=True, shape=shape, lag=0.02,
            slide=0.08, dyn=Curve([(0, 0.55)]))
    st.play("solo_violin", S(P["vn_a3"], 5), "solo_violin", seed=5, gain_db=1, legato=True, shape=shape, lag=0.02,
            slide=0.08, dyn=Curve([(0, 0.58)]))
    st.play("violins_pizz", S(P["pz_vla"], 6), "violas_pizz", seed=6, gain_db=4, seat="violas")
    st.play("cellos_pizz", S(P["pz_vc"], 7), "cellos_pizz", seed=7, gain_db=4, seat="cellos")
    st.play("clarinets", S(P["clar"], 8), "clarinet", seed=8, gain_db=4, legato=True, shape=shape)
    st.play("clarinets", S(P["clar_counter"], 9), "clarinet", seed=9, gain_db=0, legato=True, shape=shape)
    st.play("flutes", S(P["flute"], 10), "flute", seed=10, gain_db=8, legato=True, shape=shape)
    st.play("cellos_pizz", S(P["cb_pz"], 11), "cellos_pizz", seed=11, gain_db=-2, seat="basses")
    st.play("violas", S(P["vla_sus"], 12), "violas", seed=12, gain_db=-8, depth=0.75,
            shape={"attack": 0.4, "swell": 0.2, "taper": 2.0}, dyn=Curve([(0, 0.45)]))
    st.play("cellos", S(P["vc_sus"], 13), "cellos", seed=13, gain_db=-7, depth=0.75,
            shape={"attack": 0.4, "swell": 0.2, "taper": 2.0}, dyn=Curve([(0, 0.45)]))

    out = st.render({"chamber": {"seed": 121}, "concert": {"seed": 122}}, warmth=0.4)
    out = FX.wow_flutter(out, 0.0009, 0.0003, circular=True, seed=6)
    out = FX.eq(out, ("hp", 60, 0.7), ("lp", 9000, 0.7), circular=True)
    return finish_loop("music", "picture-show", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 132, "meter": "3/4", "beat": "quarter", "key": "F major",
                             "instrument": "upright piano"})


if __name__ == "__main__":
    render()
