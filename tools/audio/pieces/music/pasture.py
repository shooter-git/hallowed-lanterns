"""IV. The Pasture of Giants — "Gentle Giants".

Low cellos and basses in open fifths, a soft horn and a solo cello calling to
each other with the motif, a hummed choir and slow starlight (celesta and glass
very high). D, mostly over a D-A pedal. 4/4 at 52 bpm: 26 bars = exactly 120 s.

  bars  0-3   open fifths and stars
  bars  4-11  horn calls the motif, the cello answers; together to the cadence
  bars 12-17  stillness: the choir swells under the starlight
  bars 18-21  the solo cello sings the motif up high, the horn beneath it
  bars 22-25  the field breathes out; a far horn echo; back to the fifths
"""
from hlaudio.core import rng
from hlaudio.score import N, seq, prog, pad, bass_line, shift, humanize, Clock
from hlaudio.arrange import window, legato, shape, ranks
from hlaudio import mallets as ML, bowed as BW, wind as WI, voice as VO, effects as FX
from hlaudio.piece import Mix, finish_loop

TITLE = "Gentle Giants"
BAR = 4
BARS = 26
BPM_UNIT = 52
LOOP = BARS * BAR * 60 / BPM_UNIT  # 120 s
STARS = [86, 88, 90, 93, 95, 98, 100, 102]  # D6..F#7 (D pentatonic)


def bar(b):
    return b * BAR


def harmony():
    return prog(
        "D5:4 | Dsus2:4 | G/D:4 | D5:4 | "
        "Gmaj7/D:4 | D5:4 | Em7:4 | A7sus4:2 A7:2 | G/D:4 | Bm:4 | D/A:2 A7:2 | D:4 | "
        "Gadd9/D:4 | D5:4 | Em7:4 | D5:4 | Bm7:4 | A7sus4:4 | "
        "Gmaj7/D:4 | D5:4 | G/D:4 | D:4 | "
        "D5:4 | Dsus2:4 | Gadd9/D:4 | A7sus4:4")


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["horn"] = seq("D4:1 | B4:2 A4:1 F#4:1 | A4:4", bar(3) + 3, vel=0.6) + \
        seq("D4:1 | B4:2 A4:1 F#4:1 | D5:3 C#5:1 | A4:2 F#4:1 E4:1 | D4:4", bar(7) + 3, vel=0.66) + \
        seq("A3:4 | A3:4 | B3:4 | A3:4 | F#3:4 | E3:4", bar(12), vel=0.42) + \
        seq("B3:2 A3:2 | A3:4 | G3:2 B3:2 | A3:4", bar(18), vel=0.45) + \
        seq("D4:1 | B4:2 A4:1 F#4:1 | A4:4", bar(22) + 3, vel=0.35)
    P["cello"] = seq("C#4:1 | A4:2 G4:1 E4:1 | G4:2 F#4:2", bar(5) + 3, vel=0.66) + \
        seq("F#3:2 D3:1 C#3:1 | D3:4", bar(10), vel=0.6) + \
        seq("D4:1 | B4:2 A4:1 F#4:1 | A4:3 D4:1 | B4:2 A4:1 F#4:1 | D5:4", bar(17) + 3, vel=0.7)
    # low strings: open fifths pedal, following the harmony
    lows = pad(pr, 45, 57, 2, vel=0.5, legato=0.3)
    dyn = [(0, 4, 0.75), (4, 12, 0.85), (12, 18, 1.0), (18, 22, 0.9), (22, 26, 0.7)]
    P["cellos"] = shape(lows, dyn, BAR)
    P["basses"] = shape(bass_line(pr, 33, vel=0.5), dyn, BAR)
    hum = pad(pr, 50, 66, 3, vel=0.45, legato=0.5)
    P["choir"] = shape(hum, [(0, 4, 0.7), (4, 12, 0.8), (12, 18, 1.15), (18, 22, 0.9), (22, 26, 0.7)], BAR)
    # starlight: sparse high celesta, a little more in the still middle
    r = rng("stars")
    st = []
    t = 0.7
    while t < BARS * BAR:
        dens = 1.0 if (bar(12) <= t < bar(18)) else 0.6
        st.append(N(t, 1.0, float(r.choice(STARS)), float(r.uniform(0.22, 0.42))))
        t += r.uniform(1.4, 3.2) / dens
    P["stars"] = st
    P["glass"] = seq("(A5 E6):24", bar(12), vel=0.4) + seq("(F#5 D6):8", bar(22), vel=0.3)
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.03))
    S = lambda notes, seed, j=0.006: humanize(clk.notes(notes), seed, t_jit=j)
    mix = Mix(LOOP, circular=True)

    low = mix.track()
    BW.strings(low, S(P["cellos"], 1), "cellos", gain=0.33, seed=1, style_over={"attack": 0.8, "release": 1.5})
    BW.strings(low, S(P["basses"], 2), "basses", gain=0.3, seed=2, style_over={"attack": 1.0, "release": 1.8})
    mix.add(low, 1.0, {"hall": 0.4, "sky": 0.2}, name="low strings")

    solo = mix.track()
    BW.strings(solo, S(legato(P["cello"], 0.1), 3), "solo_cello", gain=0.85, seed=3)
    mix.add(solo, 0.7, {"hall": 0.45, "sky": 0.2}, name="solo cello")

    hn = mix.track()
    WI.horn(hn, S(legato(P["horn"], 0.1), 4), gain=1.1, pan=-0.25, seed=4, players=2)
    mix.add(hn, 1.0, {"hall": 0.55, "sky": 0.3}, name="horn")

    ch = mix.track()
    lo, hi = ranks(S(P["choir"], 5, 0.0), [[0], [1, 2]])
    VO.choir(ch, lo, "bass", singers=6, vowel=("u", "o"), morph=0.2, gain=0.45, seed=5)
    VO.choir(ch, hi, "tenor", singers=6, vowel=("u", "o"), morph=0.25, gain=0.42, seed=6)
    mix.add(ch, 1.0, {"hall": 0.5, "sky": 0.3}, name="choir")

    sky = mix.track()
    ML.render(sky, S(P["stars"], 7, 0.0), ML.celesta, gain=0.5, pan_spread=0.7)
    VO.glass_pad(sky, S(P["glass"], 8, 0.0), gain=0.3, seed=8, attack=3.0, release=4.0)
    mix.add(sky, 1.0, {"shimmer:sky": 0.35, "hall": 0.2}, name="stars")

    out = mix.render({"hall": {"seed": 41}, "sky": {"seed": 42}, "shimmer:sky": {"seed": 43, "gens": 2, "fb": 0.4}})
    return finish_loop("music", "pasture", out, LOOP, 4, -16.0, 128,
                       meta={"title": TITLE, "bpm": 52, "meter": "4/4", "beat": "quarter", "key": "D (open fifths)",
                             "instrument": "cello"})


if __name__ == "__main__":
    render()
