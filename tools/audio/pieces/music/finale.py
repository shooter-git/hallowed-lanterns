"""Finale — "Hallowed Lanterns" (one-shot, plays at the Wishing Tree).

The full theme with a real ending. 6/8, D major, rising to E major for the
last statement. About 2'10".

  bars  0-3   the music box alone, as at sundown; strings breathe in
  bars  4-11  theme A: violins, the music box above, harp below
  bars 12-19  the journey: the motif passes through every chapter's voice —
              celesta, zither, cello, glockenspiel, whale-choir, sleigh bells,
              guitar — each in its own key over a circle of chords
  bars 20-27  theme B: cellos and horns, the choir arriving
  bars 28-29  the lift (B7)
  bars 30-37  theme A in E major: everyone, choir singing the melody
  bars 38-41  the closing phrase, broadening (ritardando)
  bars 42-46  coda: the music box plays the motif one last time over a held
              E major chord, a last chime of every bell, and stillness
"""
import numpy as np

from hlaudio.core import Track
from hlaudio.score import N, seq, prog, pad, bass_line, arpeggio, shift, humanize, Clock
from hlaudio.arrange import window, legato, shape, ranks
from hlaudio import theme as TH
from hlaudio import mallets as ML, plucked as PL, bowed as BW, wind as WI, voice as VO, perc as PC, effects as FX
from hlaudio.piece import Mix, finish_oneshot

TITLE = "Hallowed Lanterns"
BAR = 6
BARS = 46
A_BODY = ("B5:2 A5:1 F#5:1 A5:2 | A5:5 C#5:1 | A5:2 G5:1 E5:1 G5:2 | G5:3 F#5:2 D5:1 | "
          "B5:2 A5:1 F#5:1 A5:2 | D6:4 C#6:1 B5:1 | A5:2 F#5:1 E5:1 F#5:2 | ")
A_CH = ("G:3 D/F#:3 | Bm7:3 A:3 | Em7:3 A7sus4:3 | A7:3 D:3 | "
        "G:3 D/F#:3 | Bm:3 Gmaj7:3 | D/A:3 A7:3 | D:6 | ")


def bar(b):
    return b * BAR


def harmony():
    from hlaudio.score import transpose_prog
    p = prog("D:6 | G/D:6 | D:6 | A7sus4:3 A7:3 | " + A_CH +
             "Bm:6 | G:6 | Em:6 | A:6 | F#m:6 | D:6 | G:6 | A7sus4:3 A7:3 | " +
             TH.CHORDS_B + " | B7sus4:6 | B7:6")
    a_e = transpose_prog(prog(A_CH.rstrip(" |").rsplit("|", 1)[0]), 2, 1, bar(30))
    end_e = prog("A:3 E/G#:3 | C#m:3 Amaj7:3 | E/B:3 B7:3 | B7sus4:3 E:3 | "
                 "Eadd9:6 | Eadd9:6 | Amaj7/E:6 | Eadd9:6 | Eadd9:6", bar(37))
    return p + a_e + end_e


def score():
    pr = harmony()
    total = sum(d for _, d, _ in pr)
    assert abs(total - BARS * BAR) < 1e-6, (total, BARS * BAR)
    P = {}
    # intro: the music box alone
    P["box"] = seq("r:5 D6:1 | B6:2 A6:1 F#6:1 A6:2 | A6:12", bar(0), vel=0.62)
    # theme A (D) on violins, music box an octave up
    a1 = seq("D5:1", bar(4) - 1, vel=0.55) + seq(A_BODY + "D5:6", bar(4), vel=0.6)
    P["vln"] = a1
    P["box"] += shift(a1, dp=12, vmul=0.7)
    # the journey: one chapter voice per bar, each in its own key
    P["j_celesta"] = TH.motif(bar(12) - 1, "D6", 1.0, vel=0.6)            # Bm  (grove)
    P["j_zither"] = TH.motif(bar(13) - 1, "G4", 1.0, vel=0.7)             # G   (garden)
    P["j_cello"] = TH.motif(bar(14) - 1, "E3", 1.0, vel=0.7, minor=True)  # Em  (pasture)
    P["j_glock"] = TH.motif(bar(15) - 1, "A6", 1.0, vel=0.55)             # A   (hollow)
    P["j_whale"] = TH.motif(bar(16) - 1, "F#4", 1.0, vel=0.65, minor=True)  # F#m (deep)
    P["j_bells"] = TH.motif(bar(17) - 1, "D6", 1.0, vel=0.55)             # D   (snow)
    P["j_guitar"] = TH.motif(bar(18) - 1, "G4", 1.0, vel=0.75)            # G   (marigold)
    P["box"] += TH.motif(bar(19) - 1, "D6", 1.0, vel=0.5)                 # and home: the music box
    # theme B: cellos (8vb) with violas, horns answering
    b = TH.theme_b(bar(20), vel=0.7)
    b = [n for n in b if not (n.t >= bar(27) + 5)]  # drop the pickup: we lift to E instead
    P["cello_b"] = shift(b, dp=-12)
    P["horn_b"] = seq("D4:6 | D4:6 | D4:3 C4:3 | D4:3 C#4:3 | D4:3 C#4:3 | D4:3 Bb3:3 | A3:6 | A3:6", bar(20), vel=0.45)
    # the lift
    P["lift"] = seq("F#5:3 A5:3 | B5:5 E5:1", bar(28), vel=0.66)
    # theme A in E: violins + sopranos, music box/glock sparkle above
    a2 = seq(A_BODY.rstrip(" |"), bar(30), vel=0.85, transpose=2)
    a2 += seq(TH.THEME_A_END, bar(37), vel=0.8, transpose=2)
    P["vln2"] = a2
    P["sop2"] = a2
    P["box2"] = shift(a2, dp=12, vmul=0.5)
    # coda: the music box, one last time, slowly
    P["coda_box"] = seq("E6:1 | C#7:2 B6:1 G#6:1 B6:4 | r:4 | E7:4", bar(41) + 5, vel=0.55)
    P["final_chime"] = [N(bar(44) + i * 0.3, 6, float(p), 0.5) for i, p in enumerate([64, 68, 71, 76, 80, 83, 88])]
    # accompaniment
    dyn = [(0, 4, 0.35), (4, 12, 0.6), (12, 20, 0.48), (20, 24, 0.62), (24, 28, 0.8), (28, 30, 0.95),
           (30, 38, 1.15), (38, 42, 1.05), (42, 46, 0.42)]
    pd = pad(pr, 57, 76, 4, vel=0.5, legato=0.2)
    lo, hi = ranks(pd, [[0, 1], [2, 3]])
    P["violas"] = shape(lo, dyn, BAR)
    P["violins2"] = shape(hi, dyn, BAR)
    bl = bass_line(pr, 43, vel=0.55)
    P["cellos"] = shape([n for n in bl if not (bar(20) <= n.t < bar(28))], dyn, BAR)
    P["basses"] = shape(shift([n for n in bl if n.t >= bar(4)], dp=-12, vmul=0.9), dyn, BAR)
    harp = arpeggio(pr, 50, 83, 1.0, [0, 2, 3, 4, 3, 2], vel=0.36, n_tones=5)
    P["harp"] = shape([n for n in harp if bar(4) <= n.t < bar(42)], dyn, BAR)
    choir = pad(pr, 50, 69, 4, vel=0.5, legato=0.4)
    cdyn = [(0, 20, 0.0), (20, 24, 0.45), (24, 28, 0.7), (28, 30, 0.9), (30, 42, 1.1), (42, 46, 0.6)]
    c_lo, c_hi = ranks(choir, [[0, 1], [2, 3]])
    P["tenor"] = [n for n in shape(c_lo, cdyn, BAR) if n.v > 0.05]
    P["alto"] = [n for n in shape(c_hi, cdyn, BAR) if n.v > 0.05]
    P["horns"] = [n for n in shape(pad(pr, 52, 64, 2, vel=0.5, legato=0.2),
                                  [(0, 30, 0.0), (30, 42, 0.9), (42, 46, 0.6)], BAR) if n.v > 0.05]
    P["drum"] = [N(bar(b), 3, 0, 0.5 if b % 2 == 0 else 0.35) for b in range(30, 42)]
    P["glide_harp"] = [N(bar(3) + 2 + i * 0.22, 3, float(p), 0.35) for i, p in enumerate([62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86])] + \
        [N(bar(29) + 1 + i * 0.2, 3, float(p), 0.42) for i, p in enumerate([64, 66, 68, 71, 73, 76, 78, 80, 83, 85, 88])]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(points=[(0, 147), (bar(37), 147), (bar(41), 114), (bar(43), 100), (bar(46), 92)])
    S = lambda notes, seed, j=0.007: humanize(clk.notes(notes), seed, t_jit=j)
    end_s = clk.s(bar(BARS)) + 5.0
    mix = Mix(end_s, circular=False)

    box = mix.track()
    ML.render(box, S(P["box"], 1), ML.music_box, gain=0.5, pan=0.1, pan_by_pitch=0.25, center_pitch=88)
    ML.render(box, S(P["box2"], 2), ML.music_box, gain=0.32, pan=0.15, pan_by_pitch=0.25, center_pitch=90)
    ML.render(box, S(P["coda_box"], 3), ML.music_box, gain=0.55, pan=0.05, pan_by_pitch=0.2, center_pitch=92)
    box.buf = FX.convolve(box.buf, np.vstack([ML.box_ir(3)] * 2))[:, : box.n].astype("float32")
    box.buf = FX.eq(box.buf, ("hp", 300, 0.7), ("hs", 7000, 0.7, -4)).astype("float32")
    mix.add(box, 1.0, {"hall": 0.4, "sky": 0.12}, name="music box")

    st = mix.track()
    BW.strings(st, S(legato(P["vln"] + P["lift"] + P["vln2"], 0.05), 4), "violins", gain=0.95, seed=4)
    BW.strings(st, S(P["violins2"], 5), "violins2", gain=0.42, seed=5)
    BW.strings(st, S(P["violas"], 6), "violas", gain=0.45, seed=6)
    BW.strings(st, S(legato(P["cello_b"], 0.05), 7), "cellos", gain=0.85, seed=7)
    BW.strings(st, S(P["cellos"], 8), "cellos", gain=0.5, seed=8)
    BW.strings(st, S(P["basses"], 9), "basses", gain=0.45, seed=9)
    mix.add(st, 1.0, {"hall": 0.5, "sky": 0.15}, name="strings")

    hp = mix.track()
    PL.render_plucked(hp, S(P["harp"], 10), "harp", gain=0.45, pan=-0.3, pan_by_pitch=0.3, center=66, seed=10)
    PL.render_plucked(hp, S(P["glide_harp"], 11, 0.002), "harp", gain=0.4, pan=-0.25, pan_by_pitch=0.4, center=74, seed=11)
    mix.add(hp, 1.0, {"hall": 0.4}, name="harp")

    # the journey
    jr = mix.track()
    ML.render(jr, S(P["j_celesta"], 12), ML.celesta, gain=0.55, pan=0.25)
    PL.render_plucked(jr, S(P["j_zither"], 13), "zheng", gain=0.75, pan=-0.2, seed=13)
    m = S(P["j_cello"], 14, 0.0)
    for i, n in enumerate(m):
        n.d = (m[i + 1].t - n.t + 0.03) if i + 1 < len(m) else 1.4
    BW.strings(jr, m, "solo_cello", gain=0.8, seed=14)
    ML.render(jr, S(P["j_glock"], 15), ML.glockenspiel, gain=0.4, pan=0.3)
    w = S(P["j_whale"], 16, 0.0)
    for i, n in enumerate(w):
        n.d = (w[i + 1].t - n.t + 0.05) if i + 1 < len(w) else 1.6
    VO.glass_pad(jr, w, gain=0.55, seed=16, glide=0.2, attack=0.2, release=1.5,
                 partials=(1.0, 0.35, 0.18, 0.08), shimmer_partial=0.0, layers=2, pan_spread=0.3)
    ML.render(jr, S(P["j_bells"], 17), ML.bell, gain=0.45, pan=-0.2, tone="hand")
    t_j = S([N(bar(17), 1, 0, 0.5)], 18, 0.0)[0].t
    jr.add(t_j, ML.jingle(0.5, seed=3, shake=0.1), gain=0.45, pan=0.25)
    PL.render_plucked(jr, S(P["j_guitar"], 19), "guitar", gain=0.8, pan=0.1, seed=19)
    mix.add(jr, 1.0, {"hall": 0.45, "shimmer:cathedral": 0.12}, name="journey")

    hn = mix.track()
    WI.horn(hn, S(legato(P["horn_b"], 0.1), 20), gain=0.6, pan=0.3, seed=20, players=2)
    WI.horn(hn, S(P["horns"], 21), gain=0.5, pan=0.35, seed=21, players=2)
    mix.add(hn, 1.0, {"hall": 0.55}, name="horns")

    ch = mix.track()
    VO.choir(ch, S(P["alto"], 22, 0.0), "alto", singers=8, vowel=("u", "a"), morph=0.35, gain=0.42, seed=22)
    VO.choir(ch, S(P["tenor"], 23, 0.0), "tenor", singers=8, vowel=("u", "a"), morph=0.35, gain=0.4, seed=23)
    VO.choir(ch, S(legato(P["sop2"], 0.05), 24, 0.0), "soprano", singers=10, vowel=("o", "a"), morph=0.6,
             gain=0.5, seed=24)
    mix.add(ch, 1.0, {"hall": 0.45, "sky": 0.25}, name="choir")

    sp = mix.track()
    for i, n in enumerate(S(P["drum"], 25, 0.003)):
        sp.add(n.t, PC.drum(62.0, n.v, seed=i, decay=0.6, bend=0.08, brightness=0.55), gain=0.5)
    ML.render(sp, S(P["final_chime"], 26, 0.0), ML.celesta, gain=0.4, pan_by_pitch=0.4, center_pitch=76)
    ML.render(sp, S(shift(P["final_chime"], dp=12, vmul=0.7), 27, 0.0), ML.bell, gain=0.25, pan_by_pitch=0.4,
              center_pitch=88, tone="hand")
    t_end = clk.s(bar(44))
    sp.add(t_end, ML.jingle(0.45, seed=9, shake=0.14), gain=0.4, pan=0.2)
    sp.add(t_end + 0.05, ML.finger_cymbal(0.4, seed=4, f1=1650.0), gain=0.35, pan=-0.3)
    mix.add(sp, 1.0, {"hall": 0.45, "shimmer:cathedral": 0.3}, name="chimes")

    out = mix.render({"hall": {"seed": 91}, "sky": {"seed": 92},
                      "shimmer:cathedral": {"seed": 93, "gens": 2, "fb": 0.45}})
    # gentle fade over the last seconds so the tail ends in silence
    n = out.shape[1]
    k = int(5.0 * 44100)
    out[:, n - k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    return finish_oneshot("music", "finale", out, -16.0, 128, max_s=120.6, end_fade=4.5,
                          meta={"title": TITLE, "key": "D major -> E major", "meter": "6/8", "bpm": 48,
                                "beat": "dotted quarter"})


if __name__ == "__main__":
    render()
