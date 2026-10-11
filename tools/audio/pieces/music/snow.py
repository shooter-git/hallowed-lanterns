"""VI. October Snow — "First Snow".

Celesta and sleigh bells, hushed and tender: the full theme slowed into a
3/4 lullaby in A major, strings barely touching the string (sul tasto), tiny
bells like snowflakes. 3/4 at 60 bpm in eighths: 40 bars = exactly 120 s.

  bars  0-3   snowfall: glass, a sleigh-bell shimmer, single bells
  bars  4-19  the theme (A) on the celesta, very slow
  bars 20-35  the bridge (B) on soft violins, the celesta rocking beneath
  bars 36-39  the motif on tiny bells, and the snow again
"""
from hlaudio.core import rng
from hlaudio.score import N, seq, prog, pad, bass_line, arpeggio, shift, humanize, Clock, transpose_prog
from hlaudio.arrange import window, legato, shape, stretch, ranks
from hlaudio import theme as TH
from hlaudio import mallets as ML, bowed as BW, voice as VO, effects as FX
from hlaudio.piece import Mix, finish_loop

TITLE = "First Snow"
BAR = 6
BARS = 40
BPM_UNIT = 120
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s
T = 7  # D major theme -> A major
FLAKES = [93, 97, 100, 102, 105, 107]  # A6 C#7 E7 F#7 A7 B7

BW.SECTIONS["violins_tasto"] = dict(body="violin", players=6, pan=(-0.6, 0.1), detune=6, vib=(5.0, 10), bright=0.5,
                                    attack=0.45, release=0.9, noise=0.006,
                                    eq=[("hp", 200, 0.7), ("peak", 2800, 0.8, -3), ("hs", 4500, 0.7, -6)])


def bar(b):
    return b * BAR


def harmony():
    intro = prog("A:6 | F#m7:6 | Dmaj7:6 | E7sus4:3 E7:3")
    a = transpose_prog(prog(TH.CHORDS_A)[1:], T, 2, bar(4))
    b = transpose_prog(prog(TH.CHORDS_B), T, 2, bar(20))
    outro = prog("A:6 | Dmaj7:6 | Bm7:6 | E7sus4:3 E7:3", bar(36))
    return intro + a + b + outro


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr)
    P = {}
    P["celesta"] = shift(stretch(TH.theme_a(0, T, vel=0.55), 2), dt=bar(4) - 12)
    vb = shift(stretch(TH.theme_b(0, T, vel=0.5), 2), dt=bar(20))
    P["violins"] = vb
    P["bells"] = seq("A5:2 | F#6:4 E6:2 C#6:2 E6:8", bar(36) - 2, vel=0.42) + \
        seq("A6:2 | F#7:4 E7:2 C#7:2 E7:8", bar(38) - 2, vel=0.25)
    P["cel_rock"] = window(arpeggio(pr, 69, 88, 1.0, [0, 2, 3, 1, 3, 2], vel=0.26, n_tones=4), bar(20), bar(36))
    pd = pad(pr, 57, 76, 3, vel=0.32, legato=0.3)
    P["pad"] = shape(pd, [(0, 4, 0.8), (4, 20, 0.9), (20, 36, 0.75), (36, 40, 0.8)], BAR)
    P["cello"] = bass_line(pr, 45, vel=0.32)
    r = rng("flakes")
    fl = []
    t = 1.3
    while t < BARS * BAR:
        fl.append(N(t, 1.0, float(r.choice(FLAKES)), float(r.uniform(0.15, 0.32))))
        t += r.uniform(3.0, 7.0)
    P["flakes"] = fl
    P["jingle"] = [N(bar(b), 1, 0, 0.32) for b in (0, 4, 8, 12, 16, 20, 24, 28, 32, 36)]
    P["glass"] = seq("(A5 E6):24", bar(0), vel=0.3) + seq("(A5 E6):24", bar(36), vel=0.3)
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.05))
    S = lambda notes, seed, j=0.007: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    ce = mix.track()
    ML.render(ce, S(P["celesta"], 1), ML.celesta, gain=0.55, pan=0.05, pan_by_pitch=0.2, center_pitch=78)
    ML.render(ce, S(P["cel_rock"], 2), ML.celesta, gain=0.3, pan=0.25, pan_by_pitch=0.3, center_pitch=78)
    ce.buf = FX.eq(ce.buf, ("hp", 250, 0.7), ("hs", 5500, 0.7, -4), circular=True).astype("float32")
    mix.add(ce, 1.0, {"hall": 0.4, "shimmer:cathedral": 0.15}, name="celesta")

    st = mix.track()
    BW.strings(st, S(legato(P["violins"], 0.1), 3), "violins_tasto", gain=0.8, seed=3)
    BW.strings(st, S(P["pad"], 4), "violas", gain=0.32, seed=4, style_over={"attack": 0.9, "release": 1.4})
    BW.strings(st, S(P["cello"], 5), "cellos", gain=0.3, seed=5, style_over={"attack": 1.0, "release": 1.5})
    st.buf = FX.eq(st.buf, ("hs", 4000, 0.7, -3), circular=True).astype("float32")
    mix.add(st, 1.0, {"hall": 0.55, "sky": 0.15}, name="strings")

    bl = mix.track()
    ML.render(bl, S(P["bells"], 6), ML.bell, gain=0.4, pan=-0.1, pan_by_pitch=0.3, center_pitch=86, tone="hand")
    ML.render(bl, S(P["flakes"], 7, 0.0), ML.bell, gain=0.13, pan_spread=0.7, tone="tiny")
    for i, n in enumerate(S(P["jingle"], 8, 0.0)):
        bl.add(n.t, ML.jingle(n.v, seed=i, shake=0.12, n_bells=6, bright=0.9), gain=0.5, pan=0.3)
    VO.glass_pad(bl, S(P["glass"], 9, 0.0), gain=0.16, seed=9, attack=3.0, release=4.0)
    mix.add(bl, 1.6, {"hall": 0.4, "shimmer:cathedral": 0.2}, name="bells")

    out = mix.render({"hall": {"seed": 61}, "sky": {"seed": 62}, "shimmer:cathedral": {"seed": 63, "gens": 2, "fb": 0.4}})
    return finish_loop("music", "snow", out, LOOP, 4, -17.0, 128, tilt_hs_db=-1.5,
                       meta={"title": TITLE, "bpm": 60, "meter": "3/4", "beat": "quarter", "key": "A major",
                             "instrument": "celesta and sleigh bells"})


if __name__ == "__main__":
    render()
