"""VII. The Deep — "Where the Lanterns Swim".

Whale-song pads that glide between notes, a slow choir, low drones and
far-off glints, all heard as if underwater (soft highs, long blue reverb,
shimmer). F# minor opening onto A major. 4/4 at 50 bpm: 25 bars = 120 s.

  bars  0-3   the deep: drones, glass, the choir humming
  bars  4-11  a whale-voice sings the motif in the minor (F# D C# A C#),
              gliding from note to note
  bars 12-19  the choir sings it in A major, opening up, a slow heartbeat
  bars 20-24  everything sinks back into the blue
"""
from hlaudio.core import rng
from hlaudio.score import N, seq, prog, pad, bass_line, shift, humanize, Clock
from hlaudio.arrange import window, legato, shape, ranks
from hlaudio import mallets as ML, bowed as BW, voice as VO, perc as PC, effects as FX, plucked as PL
from hlaudio.piece import Mix, finish_loop

TITLE = "Where the Lanterns Swim"
BAR = 4
BARS = 25
BPM_UNIT = 50
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s
GLINTS = [73, 76, 78, 81, 85, 88, 90, 93]  # C#5 E5 F#5 A5 C#6 E6 F#6 A6


def bar(b):
    return b * BAR


def harmony():
    return prog("F#madd9:4 | Dmaj7:4 | F#madd9:4 | Dmaj7:4 | "
                "F#m:4 | Dmaj7:4 | Bm7:4 | C#7sus4:2 C#7:2 | F#m:4 | Dmaj7:4 | A/C#:4 | A:4 | "
                "Dmaj7:4 | A:4 | Bm7:4 | F#m:4 | Dmaj7:4 | E:4 | A:4 | C#7sus4:2 C#7:2 | "
                "F#madd9:4 | Dmaj7:4 | Bm9:4 | C#7sus4:4 | C#7sus4:2 C#7:2")


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["whale"] = seq("F#4:1 | D5:2 C#5:1 A4:1 | C#5:4 | B4:2 A4:1 F#4:1 | G#4:4 | r:3 F#4:1 | D5:2 C#5:1 A4:1 | "
                     "C#5:2 E5:2 | F#5:4", bar(3) + 3, vel=0.62) + \
        seq("F#4:1 | D5:2 C#5:1 A4:1 | C#5:8", bar(20) + 3, vel=0.4)
    P["sop"] = seq("A4:1 | F#5:2 E5:1 C#5:1 | E5:4 | D5:2 C#5:1 B4:1 | C#5:4 | F#5:2 E5:1 C#5:1 | B5:3 G#5:1 | "
                   "A5:2 E5:2 | F#5:2 E#5:2", bar(11) + 3, vel=0.6)
    hum = pad(pr, 49, 68, 4, vel=0.45, legato=0.8)
    lo, hi = ranks(hum, [[0, 1], [2, 3]])
    cdyn = [(0, 4, 0.7), (4, 12, 0.8), (12, 20, 1.1), (20, 25, 0.7)]
    P["tenor"] = shape(lo, cdyn, BAR)
    P["alto"] = shape(hi, cdyn, BAR)
    P["bass"] = shape(bass_line(pr, 37, vel=0.42), cdyn, BAR)
    P["glass"] = shape(pad(pr, 69, 88, 3, vel=0.4, legato=0.5), [(0, 12, 0.9), (12, 20, 1.0), (20, 25, 0.8)], BAR)
    P["low"] = shape(bass_line(pr, 30, vel=0.5), [(0, 25, 1.0)], BAR)
    r = rng("glints")
    gl = []
    t = 1.0
    while t < BARS * BAR:
        gl.append(N(t, 1.0, float(r.choice(GLINTS)), float(r.uniform(0.25, 0.45))))
        t += r.uniform(2.0, 4.5)
    P["glints"] = gl
    P["heart"] = [N(bar(b), 1, 0, 0.5) for b in range(12, 20, 1)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.03))
    S = lambda notes, seed, j=0.0: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    wh = mix.track()
    # the whale voice: a glass pad with long glides, doubled by a breathy soprano an octave up
    VO.glass_pad(wh, S(legato(P["whale"], 0.3), 1), gain=0.9, seed=1, glide=0.45, attack=0.5, release=2.5,
                 partials=(1.0, 0.35, 0.18, 0.08, 0.04), shimmer_partial=0.0, layers=2, pan_spread=0.3)
    VO.choir(wh, S(legato(P["whale"], 0.3), 2), "alto", singers=4, vowel=("u", "o"), morph=0.3, gain=0.35, seed=2,
             style_over={"glide": 0.4, "attack": 0.5, "release": 2.0})
    wh.buf = FX.chorus(wh.buf, rate=0.2, depth_ms=4.0, mix=0.4, circular=True, seed=1).astype("float32")
    mix.add(wh, 1.0, {"underwater": 0.6, "shimmer:cathedral": 0.2}, name="whale")

    ch = mix.track()
    VO.choir(ch, S(P["alto"], 3), "alto", singers=7, vowel=("u", "a"), morph=lambda t: 0.2 + 0.4 * (
        (t > clk.s(bar(12))) & (t < clk.s(bar(20)))), gain=0.5, seed=3)
    VO.choir(ch, S(P["tenor"], 4), "tenor", singers=7, vowel=("u", "a"), morph=0.25, gain=0.48, seed=4)
    VO.choir(ch, S(P["bass"], 5), "bass", singers=6, vowel=("u", "o"), morph=0.2, gain=0.4, seed=5)
    VO.choir(ch, S(legato(P["sop"], 0.2), 6), "soprano", singers=9, vowel=("o", "a"), morph=0.6, gain=0.65, seed=6,
             style_over={"glide": 0.18})
    mix.add(ch, 1.0, {"underwater": 0.5, "sky": 0.25}, name="choir")

    gp = mix.track()
    VO.glass_pad(gp, S(P["glass"], 7), gain=0.35, seed=7, glide=0.9, attack=2.0, release=3.0)
    BW.strings(gp, S(P["low"], 8), "basses", gain=0.5, seed=8, style_over={"attack": 1.5, "release": 2.5})
    mix.add(gp, 1.0, {"underwater": 0.5, "shimmer:cathedral": 0.15}, name="pads")

    gl = mix.track()
    ML.render(gl, S(P["glints"], 9), ML.celesta, gain=0.25, pan_spread=0.8)
    for i, n in enumerate(S(P["heart"], 10)):
        gl.add(n.t, PC.heartbeat(48.0, n.v, seed=i), gain=0.45, pan=0.0)
    gl.buf = FX.eq(gl.buf, ("lp", 3500, 0.7), circular=True).astype("float32")
    mix.add(gl, 1.0, {"underwater": 0.7}, name="glints")

    out = mix.render({"underwater": {"seed": 71}, "sky": {"seed": 72},
                      "shimmer:cathedral": {"seed": 73, "gens": 2, "fb": 0.45}})
    out = FX.eq(out, ("lp", 5200, 0.6), ("ls", 120, 0.7, 1.5), circular=True)
    return finish_loop("music", "deep", out, LOOP, 4, -16.0, 128, tilt_hs_db=-1.5,
                       meta={"title": TITLE, "bpm": 50, "meter": "4/4", "beat": "quarter",
                             "key": "F# minor / A major", "instrument": "whale-song choir"})


if __name__ == "__main__":
    render()
