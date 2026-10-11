"""I. The Arbor of Faces — "Sundown".

Music box and warm strings, a slow 6/8 waltz in D major at golden hour.
50 bars of 6/8 at dotted-quarter = 50 (eighth = 150): exactly 120 s.

  bars  0-3   intro: music-box lullaby figure over a soft string pad
  bars  4-11  A1: the theme on the music box
  bars 12-19  A2: violins sing the theme, the music box twinkles around them
  bars 20-27  B: cellos take the bridge (relative minor, a borrowed G minor)
  bars 28-35  A3: everyone, the music box and violins together
  bars 36-43  coda: the motif passed between music box and a solo cello
  bars 44-49  transition: the lullaby figure returns, fading into the loop
"""
from hlaudio.core import Track
from hlaudio.score import seq, prog, pad, bass_line, arpeggio, shift, humanize, Clock
from hlaudio.arrange import ranks, vel_ramp, window, legato, tag
from hlaudio import theme as TH
from hlaudio import mallets as ML, bowed as BW, effects as FX
from hlaudio.piece import Mix, finish_loop
from hlaudio.mallets import box_ir
from hlaudio.effects import convolve

TITLE = "Sundown"
BARS, BAR = 50, 6
BPM_EIGHTH = 150
LOOP = BARS * BAR * 60 / BPM_EIGHTH  # 120 s


def bar(b):
    return b * BAR


A_BODY = ("B5:2 A5:1 F#5:1 A5:2 | A5:5 C#5:1 | A5:2 G5:1 E5:1 G5:2 | G5:3 F#5:2 D5:1 | "
          "B5:2 A5:1 F#5:1 A5:2 | D6:4 C#6:1 B5:1 | A5:2 F#5:1 E5:1 F#5:2 | ")
A_END_CLOSE = "D5:6"
A_END_PICK = "D5:5 D5:1"


def harmony():
    intro = "D:6 | G/D:6 | D:6 | A7sus4:3 D:3 | "
    a = ("G:3 D/F#:3 | Bm7:3 A:3 | Em7:3 A7sus4:3 | A7:3 D:3 | "
         "G:3 D/F#:3 | Bm:3 Gmaj7:3 | D/A:3 A7:3 | D:6 | ")
    b = TH.CHORDS_B + " | "
    coda = ("G:3 D/F#:3 | Bm7:6 | Em7:3 A7sus4:3 | D:6 | "
            "Em7:3 A7sus4:3 | A7:3 D:3 | D/A:3 A7:3 | D:6 | ")
    trans = "G:6 | D/F#:6 | Em7:6 | Gm6:6 | D/A:6 | A7sus4:3 A7:3"
    return prog(intro + a + a + b + a + coda + trans)


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr)
    parts = {}
    # --- melodies
    pick = seq("D5:1", bar(4) - 1)
    a1 = pick + seq(A_BODY + A_END_PICK, bar(4))
    a2 = seq(A_BODY + A_END_CLOSE, bar(12))
    b = seq(TH.THEME_B, bar(20))
    a3 = seq(A_BODY + A_END_PICK, bar(28))
    coda_box = seq("B5:2 A5:1 F#5:1 A5:2 | A5:6", bar(36)) + \
        seq("r:5 C#5:1 | A5:2 G5:1 E5:1 G5:2 | G5:3 F#5:3", bar(39))
    coda_cello = seq("r:5 D4:1 | B4:2 A4:1 F#4:1 A4:2 | A4:6", bar(37)) + \
        seq("r:5 D4:1 | A4:2 F#4:1 E4:1 F#4:2 | D4:6", bar(41))
    trans_vln = seq("r:5 D5:1 | B5:2 A5:1 F#5:1 A5:2 | A5:6 | A5:6", bar(45))

    parts["box_mel"] = shift(a1, dp=12, vmul=0.95) + shift(a3, dp=12, vmul=1.0) + shift(coda_box, dp=12, vmul=0.85)
    parts["vln_mel"] = vel_ramp(shift(a2, vmul=0.95), bar(12), bar(20), 0.85, 1.05) + shift(a3, vmul=0.9) + \
        shift(trans_vln, vmul=0.55)
    parts["cello_mel"] = shift(b, dp=-12, vmul=1.0)
    parts["solo_cello"] = shift(coda_cello, vmul=0.85)

    # --- music-box lullaby figure (intro, A2 twinkle, B sparse, transition)
    arp_full = arpeggio(pr, 74, 91, 1.0, [0, 2, 3, 1, 3, 2], vel=0.42, n_tones=4)
    arp = window(arp_full, bar(0), bar(4)) + \
        shift(window(arpeggio(pr, 81, 98, 1.0, [3, 1, 2, 0, 2, 1], vel=0.33, n_tones=4), bar(12), bar(20)), vmul=1.0) + \
        shift(window(arpeggio(pr, 81, 96, 3.0, [2, 0], vel=0.3, n_tones=3), bar(20), bar(28)), vmul=1.0) + \
        vel_ramp(window(arp_full, bar(44), bar(50)), bar(44), bar(50), 0.95, 0.75)
    parts["box_arp"] = arp

    # --- strings pad (violas low pair, second violins high pair)
    pd = pad(pr, 57, 76, 4, vel=0.5, legato=0.15)
    lo, hi = ranks(pd, [[0, 1], [2, 3]])
    dyn = [(0, 4, 0.55), (4, 12, 0.7), (12, 20, 0.8), (20, 28, 0.85), (28, 36, 0.95), (36, 44, 0.7), (44, 50, 0.55)]

    def shape(ns_):
        out = []
        for (b0, b1, k) in dyn:
            out += shift(window(ns_, bar(b0), bar(b1)), vmul=k)
        return out
    parts["violas"] = shape(lo)
    parts["violins2"] = shape(hi)
    # --- bass: cellos on the roots (not while they sing B), basses an octave below in fuller parts
    bl = bass_line(pr, 43, vel=0.55)
    parts["cello_bass"] = shape(window(bl, bar(0), bar(20)) + window(bl, bar(28), bar(36)) + window(bl, bar(44), bar(50)))
    parts["basses"] = shape(shift(window(bl, bar(12), bar(44)), dp=-12, vmul=0.9))
    return pr, parts


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_EIGHTH, rubato=(4 * BAR, 0.04))
    S = lambda notes, seed: humanize(clk.notes(notes), seed, t_jit=0.008)
    mix = Mix(LOOP, circular=True)

    # music box: melody + figure, a little box resonance and tape wobble
    box = mix.track()
    ML.render(box, S(P["box_mel"], 1), ML.music_box, gain=0.55, pan=0.08, pan_by_pitch=0.25, center_pitch=88)
    ML.render(box, S(P["box_arp"], 2), ML.music_box, gain=0.36, pan=-0.05, pan_by_pitch=0.45, center_pitch=86)
    ir = box_ir(3)
    box.buf = FX.convolve(box.buf, ir[None, :].repeat(2, 0), True).astype("float32") * 0.8
    box.buf = FX.wow_flutter(box.buf, 0.0012, 0.0003, circular=True, seed=4).astype("float32")
    box.buf = FX.saturate(box.buf * 1.0, 1.2, 0.5).astype("float32")
    box.buf = FX.eq(box.buf, ("hp", 300, 0.7), ("peak", 3500, 1.0, -2.0), ("hs", 7000, 0.7, -4), circular=True).astype("float32")
    mix.add(box, 1.0, {"hall": 0.42, "echo:0.8": 0.10, "sky": 0.10}, name="music box")

    strings = mix.track()
    BW.strings(strings, S(legato(P["vln_mel"], 0.05), 5), "violins", gain=0.95, seed=5)
    BW.strings(strings, S(P["violins2"], 6), "violins2", gain=0.42, seed=6)
    BW.strings(strings, S(P["violas"], 7), "violas", gain=0.45, seed=7)
    BW.strings(strings, S(legato(P["cello_mel"], 0.05), 8), "cellos", gain=0.85, seed=8)
    BW.strings(strings, S(P["cello_bass"], 9), "cellos", gain=0.5, seed=9)
    BW.strings(strings, S(P["basses"], 10), "basses", gain=0.42, seed=10)
    BW.strings(strings, S(legato(P["solo_cello"], 0.05), 11), "solo_cello", gain=0.75, seed=11)
    strings.buf = FX.eq(strings.buf, ("peak", 220, 0.8, 1.0), ("hs", 6500, 0.7, -2), circular=True).astype("float32")
    mix.add(strings, 1.0, {"hall": 0.5, "sky": 0.12}, name="strings")

    out = mix.render({"hall": {"seed": 1}, "sky": {"seed": 2},
                      "echo:0.8": {"fb": 0.35, "lp": 3500, "pingpong": True}})
    return finish_loop("music", "arbor", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 50, "meter": "6/8", "beat": "dotted quarter",
                             "key": "D major", "instrument": "music box"})


if __name__ == "__main__":
    render()
