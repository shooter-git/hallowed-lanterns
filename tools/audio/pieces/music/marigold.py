"""VIII. The Marigold Garden — "Remember Me".

Nylon guitar and strings, bittersweet and loving, G major with a borrowed
C minor (the ache of remembering). The motif opens the melody (G E D B D).
4/4 at 66 bpm in eighths: 33 bars = exactly 120 s.

  bars  0-3   the guitar alone, fingerpicked
  bars  4-11  the song on a solo cello
  bars 12-19  the violins take it higher, the cello answers beneath
  bars 20-27  the guitar sings the bridge, the strings swell
  bars 28-32  the motif once more, softly, and the guitar carries on
"""
from hlaudio.score import N, seq, prog, pad, bass_line, arpeggio, shift, humanize, Clock
from hlaudio.arrange import window, legato, shape, ranks
from hlaudio import plucked as PL, bowed as BW, effects as FX
from hlaudio.piece import Mix, finish_loop

TITLE = "Remember Me"
BAR = 8
BARS = 33
BPM_UNIT = 66 * 2
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s

A_CH = "Cmaj7:8 | G/B:8 | Am7:8 | D7sus4:4 D7:4 | Em7:8 | Cmaj7:8 | Cm6:8 | G/D:4 D7:4 | "
SONG = "E5:4 D5:2 B4:2 | D5:6 G4:2 | C5:4 B4:2 A4:2 | A4:4 r:2 D4:2 | B4:4 A4:2 G4:2 | A4:2 B4:2 E5:4 | " \
       "Eb5:4 D5:2 C5:2 | "


def bar(b):
    return b * BAR


def harmony():
    return prog("G:8 | D/F#:8 | Em7:8 | Cmaj7:4 D7sus4:4 | " + A_CH + A_CH +
                "Em:8 | Bm7:8 | Cmaj7:8 | G/B:8 | Am7:8 | Em7:8 | Cm6:8 | D7sus4:4 D7:4 | "
                "G:8 | Cmaj7:8 | Cm6:8 | G:8 | D7sus4:8")


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["cello"] = seq("G3:2", bar(4) - 2, vel=0.62) + seq(SONG + "B4:4 A4:2 G4:2", bar(4), vel=0.66, transpose=-12)
    P["violins"] = seq(SONG + "B4:4 A4:4", bar(12), vel=0.68, transpose=12)
    P["cello2"] = seq("G4:8 | G4:4 F#4:4 | E4:8 | D4:4 C4:4 | B3:8 | C4:4 E4:4 | Eb4:8 | D4:8", bar(12), vel=0.5)
    P["guitar_mel"] = seq("G4:2 B4:2 E5:4 | D5:4 F#4:2 A4:2 | G4:2 B4:2 E5:2 G5:2 | F#5:4 D5:4 | "
                          "C5:2 E5:2 A5:4 | G5:4 B4:4 | Eb5:4 C5:2 A4:2 | D5:4 r:2 G4:2 | "
                          "E5:4 D5:2 B4:2 | D5:8 | Eb5:4 D5:4 | B4:8", bar(20), vel=0.78)
    # fingerpicking: bass on 1 and 3, inner voices in eighths
    dyn = [(0, 4, 0.9), (4, 12, 0.85), (12, 20, 0.85), (20, 28, 0.7), (28, 33, 0.85)]
    P["g_bass"] = shape(bass_line(pr, 40, vel=0.6, pattern=[(0, 4, "r"), (4, 4, "5")], period=8), dyn, BAR)
    P["g_arp"] = shape(arpeggio(pr, 55, 71, 1.0, [None, 0, 1, 2, None, 1, 2, 1], vel=0.42, n_tones=3, dur=2.5),
                       dyn, BAR)
    pd = pad(pr, 55, 74, 3, vel=0.4, legato=0.3)
    P["pad"] = shape(pd, [(0, 4, 0.0), (4, 12, 0.75), (12, 20, 0.85), (20, 28, 1.1), (28, 33, 0.7)], BAR)
    P["pad"] = [n for n in P["pad"] if n.v > 0.05]
    P["low"] = [n for n in shape(bass_line(pr, 38, vel=0.45), [(0, 12, 0.0), (12, 28, 1.0), (28, 33, 0.7)], BAR)
                if n.v > 0.05]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.045))
    S = lambda notes, seed, j=0.007: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    gt = mix.track()
    PL.render_plucked(gt, S(P["g_bass"], 1), "guitar", gain=1.5, pan=-0.05, seed=1)
    PL.render_plucked(gt, S(P["g_arp"], 2), "guitar", gain=1.3, pan=0.05, pan_by_pitch=0.2, center=64, seed=2)
    PL.render_plucked(gt, S(P["guitar_mel"], 3), "guitar", gain=2.3, pan=0.0, seed=3)
    gt.buf = FX.eq(gt.buf, ("hp", 60, 0.7), ("peak", 180, 1.0, 1.0), ("hs", 5000, 0.7, -3), circular=True).astype("float32")
    mix.add(gt, 1.0, {"room": 0.25, "hall": 0.3}, name="guitar")

    so = mix.track()
    BW.strings(so, S(legato(P["cello"], 0.1), 4), "solo_cello", gain=0.85, seed=4)
    BW.strings(so, S(legato(P["violins"], 0.1), 5), "violins", gain=0.8, seed=5)
    BW.strings(so, S(legato(P["cello2"], 0.1), 6), "solo_cello", gain=0.6, seed=6)
    mix.add(so, 0.7, {"hall": 0.45, "sky": 0.1}, name="melody strings")

    st = mix.track()
    lo, hi = ranks(S(P["pad"], 7, 0.0), [[0], [1, 2]])
    BW.strings(st, lo, "violas", gain=0.38, seed=7, style_over={"attack": 0.7, "release": 1.2})
    BW.strings(st, hi, "violins2", gain=0.36, seed=8, style_over={"attack": 0.7, "release": 1.2})
    BW.strings(st, S(P["low"], 9, 0.0), "cellos", gain=0.4, seed=9, style_over={"attack": 0.6, "release": 1.2})
    mix.add(st, 1.0, {"hall": 0.5}, name="pad strings")

    out = mix.render({"hall": {"seed": 81}, "room": {"seed": 82}, "sky": {"seed": 83}})
    return finish_loop("music", "marigold", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 66, "meter": "4/4", "beat": "quarter", "key": "G major",
                             "instrument": "nylon guitar"})


if __name__ == "__main__":
    render()
