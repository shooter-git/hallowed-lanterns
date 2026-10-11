"""The Picture Show — a silent-film waltz for the shadow-puppet screen.

A sweet, slightly old-timey waltz on the Ember's motif (F C... the motif in F:
F5 | D6 C6 A5 C6), played by an upright piano with oom-pah-pah left hand, a
celesta and soft strings, with a little tape wobble and a small-hall warmth.
3/4 at 132 bpm: 88 bars = exactly 120 s.

  bars  0-3   piano vamp
  bars  4-19  A: the tune on the piano (in octaves)
  bars 20-35  B: D minor, the strings sing, the celesta answers
  bars 36-51  A: piano and celesta together
  bars 52-67  C (trio): B flat major, the motif on the celesta, strings beneath
  bars 68-83  A: everyone, a strings countermelody
  bars 84-87  a little cadence, and round again
"""
from hlaudio.score import N, seq, prog, pad, bass_line, shift, humanize, Clock
from hlaudio.arrange import window, legato, shape, ranks, comp, counter_thirds
from hlaudio import mallets as ML, bowed as BW, plucked as PL, effects as FX
from hlaudio.body import stereo_body
from hlaudio.piece import Mix, finish_loop

TITLE = "The Picture Show"
BAR = 3
BARS = 88
BPM_UNIT = 132
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s

A_CH = ("F:3 | F:3 | Gm7:3 | C7:3 | Gm7:3 | C7:3 | F:3 | F:3 | "
        "F:3 | F7:3 | Bb:3 | Bbm6:3 | F/C:3 | C7:3 | F:3 | C7:3 | ")
A_MEL = ("D6:2 C6:1 | A5:1 C6:2 | Bb5:2 A5:1 | G5:1 Bb5:2 | A5:2 G5:1 | E5:1 G5:2 | F5:3 | r:2 F5:1 | "
         "D6:2 C6:1 | A5:1 Eb6:2 | D6:2 C6:1 | Bb5:1 Db6:2 | C6:2 A5:1 | G5:1 Bb5:1 E5:1 | F5:3 | r:2 F5:1 | ")
B_CH = ("Dm:3 | Dm:3 | Gm:3 | Gm:3 | C7:3 | C7:3 | F:3 | F:3 | "
        "Dm:3 | Dm:3 | Gm:3 | Bbm6:3 | F/C:3 | D7:3 | Gm7:2 C7:1 | F:3 | ")
B_MEL = ("A5:3 | F5:1 A5:1 D6:1 | D6:2 C6:1 | Bb5:3 | G5:3 | E5:1 G5:1 C6:1 | C6:2 A5:1 | F5:3 | "
         "A5:3 | F5:1 A5:1 D6:1 | D6:2 Bb5:1 | Db6:2 Bb5:1 | A5:2 C6:1 | F#5:1 A5:1 C6:1 | G5:2 E5:1 | F5:2 F5:1 | ")
C_CH = ("Bb:3 | Bb:3 | Cm7:3 | F7:3 | Cm7:3 | F7:3 | Bb:3 | Bb:3 | "
        "Eb:3 | Ebm6:3 | Bb/D:3 | G7:3 | Cm7:3 | F7:3 | Bb:3 | C7:3 | ")
C_MEL = ("G6:2 F6:1 | D6:1 F6:2 | Eb6:2 D6:1 | C6:1 Eb6:2 | D6:2 C6:1 | A5:1 C6:2 | Bb5:3 | r:2 Bb5:1 | "
         "G6:2 F6:1 | Eb6:1 Gb6:2 | F6:2 D6:1 | B5:1 D6:1 F6:1 | Eb6:2 C6:1 | A5:1 C6:1 Eb6:1 | D6:3 | r:2 F5:1 | ")


def bar(b):
    return b * BAR


def harmony():
    return prog("F:3 | F:3 | C7:3 | C7:3 | " + A_CH + B_CH + A_CH + C_CH + A_CH + "F:3 | Bb:3 | F/C:2 C7:1 | F:3")


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    pick = lambda b: seq("F5:1", bar(b) - 1, vel=0.6)
    a1 = pick(4) + seq(A_MEL, bar(4), vel=0.66)
    a2 = [n for n in seq(A_MEL, bar(36), vel=0.68) if n.t < bar(51) + 2]  # the trio has its own pickup
    a3 = seq(A_MEL, bar(68), vel=0.72)
    # the last A's final pickup would lead nowhere (the cadence follows): drop it
    a3 = [n for n in a3 if n.t < bar(83) + 2]
    P["piano_mel"] = a1 + a2 + a3
    P["piano_oct"] = shift(a1 + a3, dp=-12, vmul=0.7)          # melody in octaves, old-style
    P["celesta"] = shift(a2, dp=12, vmul=0.6) + seq("Bb5:1", bar(52) - 1, vel=0.6) + seq(C_MEL, bar(52), vel=0.62)
    P["cel_ans"] = seq("r:2 D6:1 | A6:2 r:1 | r:2 Bb5:1 | D6:2 r:1 | r:2 C6:1 | E6:2 r:1 | r:3 | r:3 | "
                       "r:2 D6:1 | A6:2 r:1 | r:2 Bb5:1 | Db6:2 r:1 | r:3 | r:3 | r:3 | r:3", bar(20), vel=0.45)
    P["violins"] = seq(B_MEL, bar(20), vel=0.62)
    P["counter"] = counter_thirds(a3, pr)
    # piano left hand: oom (bass) on 1, pah-pah chords on 2 and 3
    P["oom"] = bass_line(pr, 36, vel=0.55, pattern=[(0, 1, "r")], period=3)
    # alternate root and fifth every other bar for the old-time 'stride'
    for i, n in enumerate(P["oom"]):
        if int(round(n.t / BAR)) % 2 == 1:
            sym = None
            for (t0, d, s) in pr:
                if t0 <= n.t < t0 + d:
                    sym = s
            from hlaudio.score import chord_pcs
            pcs, b, root = chord_pcs(sym)
            p5 = n.p + ((root + 7 - n.p) % 12)
            n.p = p5 - 12 if p5 > 48 else p5
    P["pah"] = comp(pr, [1, 2], 3, 53, 67, n=3, dur=0.45, vel=0.4, accent=[1.0, 0.85])
    pd = pad(pr, 55, 74, 3, vel=0.35, legato=0.2)
    P["pad"] = shape(pd, [(0, 4, 0.0), (4, 20, 0.7), (20, 36, 0.8), (36, 52, 0.75), (52, 68, 0.9),
                          (68, 84, 0.95), (84, 88, 0.6)], BAR)
    P["pad"] = [n for n in P["pad"] if n.v > 0.05]
    P["pizz"] = [n for n in shift(bass_line(pr, 36, vel=0.5, pattern=[(0, 1, "r")], period=3), dp=-12)
                 if n.t >= bar(20)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(8 * BAR, 0.035))
    S = lambda notes, seed, j=0.009: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    pn = mix.track()
    ML.render(pn, S(P["piano_mel"], 1), ML.piano, gain=0.55, pan=0.05, pan_by_pitch=0.15, center_pitch=72)
    ML.render(pn, S(P["piano_oct"], 2), ML.piano, gain=0.4, pan=0.0, pan_by_pitch=0.15, center_pitch=72)
    ML.render(pn, S(P["oom"], 3), ML.piano, gain=0.5, pan=-0.1, pan_by_pitch=0.2, center_pitch=60)
    ML.render(pn, S(P["pah"], 4), ML.piano, gain=0.3, pan=0.05, pan_by_pitch=0.2, center_pitch=60)
    sb = stereo_body("piano", 5)
    import numpy as np
    pn.buf = np.vstack([FX.convolve(pn.buf[0], sb[0], True), FX.convolve(pn.buf[1], sb[1], True)]).astype("float32")
    pn.buf = FX.eq(pn.buf, ("hp", 70, 0.7), ("peak", 2500, 1.0, 1.5), ("hs", 5000, 0.7, -5), ("lp", 7500, 0.7),
                   circular=True).astype("float32")
    pn.buf = FX.wow_flutter(pn.buf, 0.0011, 0.0004, circular=True, seed=6).astype("float32")
    mix.add(pn, 1.0, {"room": 0.3, "hall": 0.22}, name="piano")

    ce = mix.track()
    ML.render(ce, S(P["celesta"], 7), ML.celesta, gain=0.45, pan=0.3, pan_by_pitch=0.2, center_pitch=88)
    ML.render(ce, S(P["cel_ans"], 8), ML.celesta, gain=0.38, pan=0.35)
    mix.add(ce, 1.0, {"hall": 0.35}, name="celesta")

    st = mix.track()
    BW.strings(st, S(legato(P["violins"], 0.05), 9), "violins", gain=0.7, seed=9)
    BW.strings(st, S(legato(P["counter"], 0.05), 10), "violas", gain=0.42, seed=10)
    lo, hi = ranks(S(P["pad"], 11, 0.0), [[0], [1, 2]])
    BW.strings(st, lo, "violas", gain=0.25, seed=11, style_over={"attack": 0.5, "release": 0.9})
    BW.strings(st, hi, "violins2", gain=0.25, seed=12, style_over={"attack": 0.5, "release": 0.9})
    PL.render_plucked(st, S(P["pizz"], 13), "pizz_low", gain=0.55, pan=0.3, players=2, seed=13)
    st.buf = FX.eq(st.buf, ("hs", 5000, 0.7, -3), circular=True).astype("float32")
    mix.add(st, 1.0, {"hall": 0.45}, name="strings")

    out = mix.render({"hall": {"seed": 121}, "room": {"seed": 122}})
    return finish_loop("music", "picture-show", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 132, "meter": "3/4", "beat": "quarter", "key": "F major",
                             "instrument": "upright piano"})


if __name__ == "__main__":
    render()
