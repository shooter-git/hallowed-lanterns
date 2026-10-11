"""V. Sweet Hollow — "Sugar Rush".

Pizzicato strings and glockenspiel, playful and bouncy but still magical:
celesta harmonies, a soft shaker and frame drum, sprinkle glissandi, and in the
middle the pumpkin xylophone itself plays the Ember's motif (the same notes the
letter pumpkins play). D major, 4/4 at 112 bpm in eighths: 56 bars = 120 s.

  bars  0-3   pizzicato groove
  bars  4-11  A: the glockenspiel tune (the motif, bounced)
  bars 12-19  A again with celesta harmony
  bars 20-27  B: pizzicato violins call, glockenspiel answers
  bars 28-31  the pumpkins play the motif, sprinkles fly
  bars 32-39  A with the pumpkin xylophone doubling
  bars 40-47  B
  bars 48-55  A, and round again
"""
from hlaudio.score import N, seq, prog, pad, bass_line, shift, humanize, Clock
from hlaudio.arrange import window, shape, comp, counter_thirds
from hlaudio import mallets as ML, plucked as PL, perc as PC, effects as FX
from hlaudio.piece import Mix, finish_loop

TITLE = "Sugar Rush"
BAR = 8
BARS = 56
BPM_UNIT = 112 * 2
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s
DPENT = [62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86, 88]


def bar(b):
    return b * BAR


A_CH = "G:8 | D:8 | Em7:4 A7:4 | D:8 | G:8 | Bm:4 G:4 | Em7:4 A7:4 | D:8 | "
B_CH = "Bm:8 | G:8 | D:8 | A:8 | Bm:8 | G:8 | Em7:4 A7:4 | A7:8 | "
A_MEL = ("B5:2 A5:1 F#5:1 A5:3 D5:1 | B5:2 A5:1 F#5:1 A5:2 F#5:1 G5:1 | A5:1 B5:1 A5:1 F#5:1 E5:2 D5:1 E5:1 | "
         "F#5:4 r:3 D5:1 | B5:2 A5:1 F#5:1 A5:3 D6:1 | D6:2 C#6:1 B5:1 A5:2 F#5:1 G5:1 | "
         "A5:1 G5:1 F#5:1 E5:1 D5:2 E5:1 F#5:1 | ")
A_END_PICK = "D5:4 r:3 D5:1"
A_END = "D5:4 r:4"


def harmony():
    return prog("D:8 | G:8 | D:8 | A7:8 | " + A_CH + A_CH + B_CH + "D:8 | G/D:8 | D:8 | A7sus4:4 A7:4 | " +
                A_CH + B_CH + A_CH.rstrip(" |"))


def sprinkle(t, lo=74, hi=98, step=0.25, vel=0.4):
    ps = [p + 12 for p in DPENT if lo <= p + 12 <= hi]
    return [N(t + i * step, 1.0, float(p), vel * (0.7 + 0.3 * i / len(ps))) for i, p in enumerate(ps)]


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    pick = seq("D5:1", bar(4) - 1, vel=0.62)
    a1 = pick + seq(A_MEL + A_END_PICK, bar(4), vel=0.66)
    a2 = seq(A_MEL + A_END, bar(12), vel=0.7)
    a3 = seq("D5:1", bar(32) - 1, vel=0.62) + seq(A_MEL + A_END, bar(32), vel=0.72)
    a4 = seq("D5:1", bar(48) - 1, vel=0.62) + seq(A_MEL + A_END, bar(48), vel=0.68)
    glock_ans = []
    for b0 in (20, 40):
        glock_ans += seq("r:6 B5:1 A5:1 | r:6 D6:1 B5:1 | r:6 A5:1 F#5:1 | r:6 C#6:1 A5:1 | "
                         "r:8 | r:8 | r:8 | " + ("r:7 D5:1" if b0 == 20 else "r:8"), bar(b0), vel=0.56)
    P["glock"] = shift(a1 + a2 + a3 + a4 + glock_ans, dp=12)
    P["celesta"] = counter_thirds(a2 + a4, pr)
    P["xylo"] = shift(a3, vmul=0.85) + seq("D5:1 B5:2 A5:1 F#5:1 A5:3 | r:8 | D5:1 B5:2 A5:1 F#5:1 A5:3 | r:8",
                                           bar(28), vel=0.72)
    P["cel_echo"] = seq("r:8 | D6:1 B6:2 A6:1 F#6:1 A6:3 | r:8 | D6:1 B6:2 A6:1 F#6:1 A6:3", bar(28), vel=0.4)
    vb = ("F#5:1 r:1 F#5:1 G5:1 A5:2 r:2 | B5:1 r:1 B5:1 A5:1 G5:2 r:2 | F#5:1 r:1 F#5:1 E5:1 D5:2 r:2 | "
          "E5:1 r:1 E5:1 F#5:1 E5:2 r:2 | D6:2 C#6:1 B5:1 A5:2 F#5:2 | B5:2 A5:1 G5:1 F#5:2 D5:2 | "
          "E5:2 F#5:1 G5:1 A5:2 C#6:2 | E5:2 C#5:2 A4:2 r:2")
    P["pizz_mel"] = seq(vb, bar(20), vel=0.72) + seq(vb, bar(40), vel=0.72)
    P["sprinkles"] = sprinkle(bar(4) - 4) + sprinkle(bar(20) - 4, step=0.2) + sprinkle(bar(29) + 4, step=0.2) + \
        sprinkle(bar(31) + 4, step=0.2) + sprinkle(bar(40) - 4) + sprinkle(bar(55) + 3, step=0.18, vel=0.3)
    # accompaniment
    P["bass"] = bass_line(pr, 38, vel=0.62, pattern=[(0, 2, "r"), (4, 2, "5")], period=8)
    P["chords"] = comp(pr, [2, 6], 8, 62, 74, n=3, dur=0.6, vel=0.42, accent=[1.0, 0.85])
    sh = []
    for b in range(4, BARS):
        for e in range(8):
            sh.append(N(bar(b) + e, 0.5, 0, 0.32 if e % 2 else 0.2))
    P["shaker"] = sh
    P["drum"] = [N(bar(b), 2, 0, 0.45) for b in range(4, BARS)] + [N(bar(b) + 4, 2, 0, 0.25) for b in range(4, BARS)]
    P["cymbal"] = [N(bar(b), 1, 0, 0.3) for b in (4, 12, 20, 28, 32, 40, 48)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.006: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    pz = mix.track()
    PL.render_plucked(pz, S(P["bass"], 1), "pizz_low", gain=1.05, pan=0.35, players=3, seed=1)
    PL.render_plucked(pz, S(P["chords"], 2), "pizz", gain=0.62, pan=-0.1, players=2, pan_spread=0.3, seed=2)
    PL.render_plucked(pz, S(P["pizz_mel"], 3), "pizz", gain=1.1, pan=-0.35, players=4, seed=3)
    pz.buf = FX.eq(pz.buf, ("hp", 50, 0.7), ("peak", 200, 1.0, 1.5), ("hs", 5000, 0.7, -3), circular=True).astype("float32")
    mix.add(pz, 1.0, {"room": 0.25, "hall": 0.3}, name="pizzicato")

    gl = mix.track()
    ML.render(gl, S(P["glock"], 4), ML.glockenspiel, gain=0.42, pan=0.2, pan_by_pitch=0.2, center_pitch=88)
    ML.render(gl, S(P["sprinkles"], 5, 0.002), ML.glockenspiel, gain=0.22, pan=0.0, pan_by_pitch=0.6, center_pitch=90)
    gl.buf = FX.eq(gl.buf, ("hp", 500, 0.7), ("hs", 6500, 0.7, -4), circular=True).astype("float32")
    mix.add(gl, 1.0, {"hall": 0.32, "echo:0.535": 0.08}, name="glock")

    ce = mix.track()
    ML.render(ce, S(P["celesta"], 6), ML.celesta, gain=0.18, pan=-0.3, pan_by_pitch=0.2)
    ML.render(ce, S(P["cel_echo"], 7), ML.celesta, gain=0.35, pan=0.3)
    mix.add(ce, 1.0, {"hall": 0.35}, name="celesta")

    xy = mix.track()
    ML.render(xy, S(P["xylo"], 8), ML.pumpkin_xylo, gain=0.5, pan=-0.15, pan_by_pitch=0.3, center_pitch=76)
    mix.add(xy, 1.0, {"room": 0.3, "hall": 0.25}, name="xylo")

    pc = mix.track()
    for i, n in enumerate(S(P["shaker"], 9, 0.004)):
        pc.add(n.t, PC.shaker(n.v, seed=i), gain=0.32, pan=0.45)
    for i, n in enumerate(S(P["drum"], 10, 0.003)):
        pc.add(n.t, PC.drum(105.0, n.v, seed=i, decay=0.3, bend=0.06, brightness=0.7), gain=0.42, pan=0.0)
    for i, n in enumerate(S(P["cymbal"], 11, 0.0)):
        pc.add(n.t, ML.finger_cymbal(n.v, seed=i, f1=1850.0), gain=0.3, pan=-0.4)
    pc.buf = FX.eq(pc.buf, ("hs", 6000, 0.7, -4), circular=True).astype("float32")
    mix.add(pc, 1.0, {"room": 0.3, "hall": 0.15}, name="perc")

    out = mix.render({"hall": {"seed": 51}, "room": {"seed": 52},
                      "echo:0.535": {"fb": 0.3, "lp": 4000, "pingpong": True}})
    return finish_loop("music", "hollow", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 112, "meter": "4/4", "beat": "quarter", "key": "D major",
                             "instrument": "glockenspiel"})


if __name__ == "__main__":
    render()
