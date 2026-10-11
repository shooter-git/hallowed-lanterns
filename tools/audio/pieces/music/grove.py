"""II. The Candle Grove — "Blue Hour".

Harp and celesta arpeggios over a soft choir; B minor, mysterious and gentle,
turning to D major when the choir sings. 4/4 at 72 bpm, written in
sixteenths: 36 bars = exactly 120 s.

  bars  0-3   harp alone, rising and falling like breath
  bars  4-11  choir hum enters; the celesta calls the motif, the harp answers
              (hide and seek)
  bars 12-19  the "Blue Hour" song on celesta (motif-born, B minor -> D)
  bars 20-27  the sopranos sing it in D major, the celesta twinkles above
  bars 28-35  the opening breath returns with far-off motif echoes
"""
from hlaudio.score import seq, prog, pad, bass_line, arpeggio, shift, humanize, Clock
from hlaudio.arrange import ranks, window, legato, shape
from hlaudio import mallets as ML, plucked as PL, voice as VO, effects as FX
from hlaudio.piece import Mix, finish_loop

TITLE = "Blue Hour"
BAR = 16
BARS = 36
BPM_UNIT = 72 * 4
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s


def bar(b):
    return b * BAR


def harmony():
    intro = "Bm9:16 | Gmaj7:16 | Em9:16 | F#sus4:8 F#7:8 | "
    a = "Bm:16 | Gmaj7:16 | D:16 | A:16 | Bm:16 | Gmaj7:16 | Em7:16 | F#sus4:8 F#:8 | "
    b = "Bm:16 | Gmaj7:16 | Em7:16 | F#sus4:8 F#:8 | Bm:16 | Gmaj7:16 | Em7:8 A:8 | D:16 | "
    c = "D:16 | Bm:16 | G:16 | A:16 | D/F#:16 | G:16 | Em7:16 | F#sus4:8 F#:8 | "
    d = intro + "Bm9:16 | Gmaj7:16 | Em9:16 | F#sus4:8 F#:8"
    return prog(intro + a + b + c + d)


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    # hide and seek: celesta calls, harp answers
    cel = seq("D6:2 | B6:4 A6:2 F#6:2 A6:6", bar(4) + 14, vel=0.62)
    cel += seq("C#6:2 | A6:4 G6:2 E6:2 G6:6", bar(8) + 14, vel=0.58)
    harp_ans = seq("D5:2 | B5:4 A5:2 F#5:2 A5:6", bar(6) + 14, vel=0.6)
    # the Blue Hour song
    song = seq("D5:4 | B5:6 A5:2 F#5:4 A5:4 | B5:12 D6:4 | E6:6 D6:2 B5:4 D6:4 | C#6:12 r:4 | "
               "B5:6 A5:2 F#5:4 A5:4 | B5:8 C#6:4 D6:4 | E6:8 F#6:4 E6:4 | D6:16", bar(11) + 12, vel=0.66)
    cel += song
    # far echoes at the end
    cel += seq("D6:2 | B6:4 A6:2 F#6:2 A6:8", bar(28) + 14, vel=0.42)
    cel += seq("D6:2 | B6:4 A6:2 F#6:2 A6:8", bar(32) + 14, vel=0.34)
    P["celesta"] = cel
    P["harp_ans"] = harp_ans
    # the sopranos' song in D major
    P["sop"] = seq("F#5:8 A5:4 D6:4 | D6:6 C#6:2 B5:8 | B5:6 A5:2 G5:4 B5:4 | A5:16 | "
                   "F#5:6 G5:2 A5:8 | B5:6 D6:2 B5:8 | G5:8 F#5:4 E5:4 | F#5:16", bar(20), vel=0.62)
    # celesta twinkles above the choir (sparse eighths)
    P["twinkle"] = window(arpeggio(pr, 86, 100, 4.0, [3, 1, 2, 0], vel=0.3, n_tones=4), bar(20), bar(28))
    # harp: flowing sixteenths + a low root each bar
    arp = arpeggio(pr, 47, 81, 1.0, [0, 1, 2, 3, 4, 5, 4, 3, 2, 3, 4, 5, 4, 3, 2, 1], vel=0.36, n_tones=6,
                   accent_every=8)
    dyn = [(0, 4, 0.8), (4, 12, 0.9), (12, 20, 0.85), (20, 28, 1.0), (28, 36, 0.75)]
    P["harp"] = shape(arp, dyn, BAR)
    P["harp_bass"] = shape(bass_line(pr, 35, vel=0.55), dyn, BAR)
    # choir hum ("ooh"), from bar 4; lower and softer while the sopranos sing
    hum = pad(pr, 50, 69, 4, vel=0.5, legato=0.5)
    lo, hi = ranks(hum, [[0, 1], [2, 3]])
    cdyn = [(0, 4, 0.0), (4, 12, 0.8), (12, 20, 0.9), (20, 28, 0.75), (28, 32, 0.7), (32, 36, 0.45)]
    P["tenor"] = [n for n in shape(lo, cdyn, BAR) if n.v > 0.05]
    P["alto"] = [n for n in shape(hi, cdyn, BAR) if n.v > 0.05]
    P["bass"] = [n for n in shape(bass_line(pr, 40, vel=0.45), cdyn, BAR) if n.v > 0.05]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.035))
    S = lambda notes, seed, j=0.006: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    harp = mix.track()
    PL.render_plucked(harp, S(P["harp"], 1), "harp", gain=0.55, pan=-0.25, pan_by_pitch=0.35, center=64, seed=1)
    PL.render_plucked(harp, S(P["harp_bass"], 2), "harp", gain=0.5, pan=-0.35, seed=2)
    PL.render_plucked(harp, S(P["harp_ans"], 3), "harp", gain=0.75, pan=-0.2, pan_by_pitch=0.3, center=74, seed=3)
    harp.buf = FX.eq(harp.buf, ("hp", 45, 0.7), ("hs", 5000, 0.7, -3), circular=True).astype("float32")
    mix.add(harp, 1.0, {"forest": 0.3, "hall": 0.35}, name="harp")

    cel = mix.track()
    ML.render(cel, S(P["celesta"], 4), ML.celesta, gain=0.55, pan=0.25, pan_by_pitch=0.25, center_pitch=86)
    ML.render(cel, S(P["twinkle"], 5), ML.celesta, gain=0.3, pan=0.35, pan_by_pitch=0.3, center_pitch=92)
    cel.buf = FX.eq(cel.buf, ("hp", 300, 0.7), ("hs", 6000, 0.7, -3), circular=True).astype("float32")
    mix.add(cel, 1.0, {"hall": 0.35, "shimmer:cathedral": 0.22}, name="celesta")

    ch = mix.track()
    VO.choir(ch, S(P["alto"], 6, 0.0), "alto", singers=6, vowel=("u", "o"), morph=0.3, gain=0.26, seed=6)
    VO.choir(ch, S(P["tenor"], 7, 0.0), "tenor", singers=6, vowel=("u", "o"), morph=0.3, gain=0.24, seed=7)
    VO.choir(ch, S(P["bass"], 8, 0.0), "bass", singers=5, vowel=("u", "o"), morph=0.2, gain=0.2, seed=8)
    VO.choir(ch, S(legato(P["sop"], 0.2), 9, 0.0), "soprano", singers=8, vowel=("o", "a"), morph=0.55, gain=0.42,
             seed=9)
    mix.add(ch, 1.0, {"hall": 0.45, "sky": 0.22}, name="choir")

    out = mix.render({"hall": {"seed": 21}, "forest": {"seed": 22}, "sky": {"seed": 23},
                      "shimmer:cathedral": {"seed": 24, "gens": 2, "fb": 0.4}})
    return finish_loop("music", "grove", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "B minor",
                             "instrument": "celesta"})


if __name__ == "__main__":
    render()
