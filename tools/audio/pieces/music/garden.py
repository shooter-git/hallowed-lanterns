"""III. The Lantern Garden — "Lantern Song".

Plucked zither (guzheng-like, with bends and glissandi) and a breathy bamboo
flute, G major pentatonic, unhurried and warm, over a whisper of strings and a
soft frame drum. 4/4 at 64 bpm in sixteenths: 32 bars = exactly 120 s.

  bars  0-3   zither alone: a glissando, rolling patterns, low strings
  bars  4-11  the Lantern Song on the flute (it opens with the motif: G E D B D)
  bars 12-19  the song again, ornamented, with the zither answering; drum enters
  bars 20-27  the zither sings a second tune, the flute holds long notes under it
  bars 28-31  the flute's last motif, a glissando, and back around
"""
from hlaudio.core import rng
from hlaudio.score import N, seq, prog, pad, bass_line, arpeggio, shift, humanize, Clock
from hlaudio.arrange import window, legato, shape
from hlaudio import mallets as ML, plucked as PL, wind as WI, bowed as BW, perc as PC, effects as FX
from hlaudio.piece import Mix, finish_loop

TITLE = "Lantern Song"
BAR = 16
BARS = 32
BPM_UNIT = 64 * 4
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s
PENTA = [55, 57, 59, 62, 64, 67, 69, 71, 74, 76, 79, 81, 83, 86, 88]  # G3..E6, G A B D E


def bar(b):
    return b * BAR


def harmony():
    loop4 = "G6:16 | Em7:16 | Cmaj7:16 | Dsus4:16 | "
    a = "Em7:16 | G6:16 | Cmaj7:16 | Dsus4:16 | Em7:16 | G6:16 | Am7:8 Dsus4:8 | G6:16 | "
    b = "Em7:16 | Dsus4:16 | Cmaj7:16 | Am7:8 Dsus4:8 | Em7:16 | G6:16 | Cmaj7:16 | Dsus4:16 | "
    return prog(loop4 + a + a + b + loop4.rstrip(" |"))


def gliss(t, lo=67, hi=88, step=0.45, vel=0.42):
    notes = [p for p in PENTA if lo <= p <= hi]
    return [N(t + i * step, 2.0, float(p), vel * (0.8 + 0.2 * i / len(notes))) for i, p in enumerate(notes)]


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    song = ("G5:4 | E6:8 D6:4 B5:4 | D6:12 D5:4 | B5:8 A5:4 G5:4 | A5:12 G5:4 | "
            "E6:8 D6:4 B5:4 | D6:6 E6:2 D6:4 B5:4 | A5:6 B5:2 A5:4 E5:4 | G5:12")
    song2 = ("G5:4 | E6:8 D6:4 B5:4 | D6:10 E6:1 D6:1 D5:4 | B5:8 A5:4 G5:4 | A5:10 B5:1 A5:1 G5:4 | "
             "E6:8 D6:4 B5:4 | D6:6 E6:2 G6:4 E6:4 | D6:6 B5:2 A5:4 B5:4 | G5:16")
    fl = seq(song, bar(3) + 12, vel=0.66) + seq(song2, bar(11) + 12, vel=0.72)
    fl += seq("G5:16 | A5:16 | G5:8 E5:8 | E5:8 D5:8 | B5:16 | B5:8 A5:8 | G5:8 E5:8 | D5:12", bar(20), vel=0.5)
    fl += seq("G5:4 | E6:8 D6:4 B5:4 | D6:16", bar(27) + 12, vel=0.5)
    P["flute"] = fl
    # the zither's own tune (B), with bends and vibrato
    zb = seq("B5:4 D6:4 E6:8 | D6:4 B5:4 A5:8 | G5:4 A5:4 B5:4 D6:4 | E6:12 D6:4 | "
             "E6:4 G6:4 E6:8 | D6:4 B5:4 A5:8 | G5:4 E5:4 A5:4 B5:4 | A5:16", bar(20), vel=0.72)
    for n in zb:
        if n.d >= 8:
            n.x["vib"] = (25, 5.2, 0.3)
    # a couple of press-bends: pluck a step low and press up into the note
    for n in zb:
        if abs(n.t - (bar(21) + 8)) < 0.01 or abs(n.t - (bar(25) + 8)) < 0.01:
            n.p -= 2
            n.x["bends"] = [(0.12, 2.0, 0.18)]
    P["zither_mel"] = zb
    # zither answers inside the second verse
    P["zither_ans"] = seq("D6:2 B5:2 A5:4", bar(13) + 8, vel=0.55) + seq("E6:2 D6:2 B5:4", bar(17) + 8, vel=0.55) \
        + seq("B5:2 A5:2 G5:4", bar(15) + 12, vel=0.5)
    # rolling accompaniment (eighths) and low roots
    acc = arpeggio(pr, 55, 76, 2.0, [0, 2, 4, 3, 1, 3, 2, 4], vel=0.36, n_tones=5, accent_every=8)
    dyn = [(0, 4, 0.9), (4, 12, 0.85), (12, 20, 0.9), (20, 28, 0.75), (28, 32, 0.85)]
    P["zither_acc"] = shape(acc, dyn, BAR)
    P["zither_bass"] = bass_line(pr, 43, vel=0.58)
    P["gliss"] = gliss(bar(0)) + gliss(bar(12) - 6, step=0.4) + gliss(bar(20) - 6, 69, 91, step=0.4) + \
        gliss(bar(29) + 8, 67, 93, step=0.5, vel=0.35)
    # warm string whisper
    pd = pad(pr, 48, 67, 3, vel=0.36, legato=0.5)
    P["strings"] = shape(pd, [(0, 4, 0.8), (4, 20, 1.0), (20, 28, 1.1), (28, 32, 0.8)], BAR)
    # soft drum from bar 12 to 27 (beat 1 strong, beat 3 lighter), finger cymbal on phrase starts
    P["drum"] = [N(bar(b), 4, 0, 0.42) for b in range(12, 28)] + [N(bar(b) + 8, 4, 0, 0.24) for b in range(12, 28)] + \
        [N(bar(b) + 14, 2, 0, 0.16) for b in range(13, 28, 2)]
    P["cymbal"] = [N(bar(b), 1, 0, 0.35) for b in (4, 12, 20, 28)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.04))
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    zi = mix.track()
    PL.render_plucked(zi, S(P["zither_acc"], 1), "zheng", gain=0.95, pan=0.15, pan_by_pitch=0.35, center=66, seed=1)
    PL.render_plucked(zi, S(P["zither_bass"], 2), "zheng", gain=1.1, pan=0.05, seed=2)
    PL.render_plucked(zi, S(P["gliss"], 3, 0.002), "zheng", gain=0.85, pan=0.2, pan_by_pitch=0.5, center=78, seed=3)
    PL.render_plucked(zi, S(P["zither_mel"], 4), "zheng", gain=1.5, pan=0.1, pan_by_pitch=0.2, center=80, seed=4)
    PL.render_plucked(zi, S(P["zither_ans"], 5), "zheng", gain=1.25, pan=0.25, seed=5)
    zi.buf = FX.eq(zi.buf, ("hp", 60, 0.7), ("peak", 3000, 1.0, -1.5), ("hs", 6000, 0.7, -3), circular=True).astype("float32")
    mix.add(zi, 1.0, {"forest": 0.25, "hall": 0.3}, name="zither")

    fl = mix.track()
    WI.flute(fl, S(legato(P["flute"], 0.1), 6, 0.004), gain=0.8, pan=-0.2, seed=6)
    mix.add(fl, 1.0, {"hall": 0.42, "sky": 0.14}, name="flute")

    st = mix.track()
    BW.strings(st, S(P["strings"], 7), "violas", gain=0.2, seed=7, style_over={"attack": 0.6, "release": 1.2})
    mix.add(st, 1.0, {"hall": 0.5}, name="strings")

    pc = mix.track()
    for i, n in enumerate(S(P["drum"], 8, 0.004)):
        pc.add(n.t, PC.drum(118.0, n.v, seed=i, decay=0.35, bend=0.05, brightness=0.7), gain=0.5, pan=0.05)
    for i, n in enumerate(S(P["cymbal"], 9, 0.0)):
        pc.add(n.t, ML.finger_cymbal(n.v, seed=i, f1=1760.0), gain=0.35, pan=-0.3)
    pc.buf = FX.eq(pc.buf, ("hs", 6000, 0.7, -4), circular=True).astype("float32")
    mix.add(pc, 1.0, {"hall": 0.3}, name="perc")

    out = mix.render({"hall": {"seed": 31}, "forest": {"seed": 32}, "sky": {"seed": 33}})
    return finish_loop("music", "garden", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 64, "meter": "4/4", "beat": "quarter",
                             "key": "G major pentatonic", "instrument": "zither"})


if __name__ == "__main__":
    render()
