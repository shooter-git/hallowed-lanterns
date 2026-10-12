"""VII. The Deep — "Where the Lanterns Swim" (rescored, Martinez / Glass).

Underwater, hypnotic, in straight time. A soft synth arpeggio repeats the
Ember's cell (F# D# C# A C#) in eighths - five notes against the eight of a
4/4 bar, so it slides across the bar line and only realigns every five
bars - through a low-pass filter that opens and closes like a tide, with a
dotted-eighth echo. Later a glass voice plays the same figure INVERTED a
sixteenth behind it and the two interlock. The pitch collection never
changes (E major's notes), but the pedal under it does: F# (Dorian, dark
blue water) and then A (Lydian, the sea opening into light) - modal
ambiguity instead of key changes. A gliding glass voice sings the cell
augmented, like whale song; low strings and the organ's quiet stops swell
like tides far back; in the light the horns state the cell and a solo
violin answers with its inversion in canon. A soft sub pulses under it in 3+3+2.
4/4, quarter = 100, 56 bars = 134.4 s.

  bars  0-7   pad, filtered arpeggio, sub, organ pedal on F#
  bars  8-23  the whale voice (cell augmented); the mirror arpeggio; tides
  bars 24-39  the pedal moves to A: horns' cell, violins' canon, the filter opens
  bars 40-55  back onto F#, layers falling away to the arpeggio
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords, roots
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop

TITLE = "Where the Lanterns Swim"
BAR = 8            # eighths
BARS = 56
BPM_UNIT = 200     # eighths per minute (quarter = 100)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 134.4 s
MF = PR.Mode(54, "dorian")   # F# dorian (D#)
MA = PR.Mode(57, "lydian")   # A lydian (D#) - the same notes

DARK = [("F#m9", 4), ("E/F#", 2), ("Amaj7/F#", 2)]
LIGHT = [("Amaj7#11", 4), ("E/A", 2), ("F#m9/A", 2)]
PLAN = DARK * 3 + LIGHT * 2 + DARK * 2        # bars 0-23 dark, 24-39 light, 40-55 dark


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b in PLAN))


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    # the arpeggio: the cell as a five-note figure in eighths, sliding across the 4/4 bars
    fig = [MF.p(14 + d) - 12 for d in PR.cell("P")]           # F#4 D#5 C#5 A4 C#5
    arp = []
    for i in range(BARS * BAR):
        t = float(i)
        p = fig[i % 5]
        if bar(24) <= t < bar(40):                              # in the light the figure lifts to A
            p = [MA.p(7 + d) for d in PR.cell("P")][i % 5]       # A4 F#5 E5 C#5 E5
        acc = 1.0 if i % 5 == 0 else 0.8
        arp.append(N(t, 0.9, float(p), 0.5 * acc))
    P["arp"] = arp
    # the mirror: the inversion a sixteenth late, a glass voice (bars 12-47)
    inv_f = [MF.p(14 + d) for d in PR.cell("I")]              # F#5 G#4 A4 C#5 A4
    inv_a = [MA.p(14 + d) for d in PR.cell("I")]
    mir = []
    for i in range(bar(12), bar(48)):
        t = float(i) + 0.5
        p = (inv_a if bar(24) <= i < bar(40) else inv_f)[i % 5]
        if i % 2 == 0:                                          # every other step: an interlocking hocket
            mir.append(N(t, 0.8, float(p), 0.42))
    P["mirror"] = mir
    # the whale: the cell augmented, gliding (two bars a note)
    P["whale"] = [N(bar(8) + 0.0, bar(2), 66.0, 0.55), N(bar(10), bar(2), 75.0, 0.62),
                  N(bar(12), bar(2), 73.0, 0.58), N(bar(14), bar(2), 69.0, 0.55), N(bar(16), bar(4), 73.0, 0.55),
                  N(bar(42), bar(2), 73.0, 0.45), N(bar(44), bar(2), 69.0, 0.42), N(bar(46), bar(4), 66.0, 0.4)]
    # in the light: horns state the cell in A, the violins answer with the inversion in canon
    P["horns"] = PR.realize(PR.cell("P"), MA, 0, bar(24), [16, 16, 16, 16, 32], vel=0.6)     # A3 F#4 E4 C#4 E4
    P["vn"] = PR.fit(PR.realize(PR.cell("I"), MA, 14, bar(28), [16, 16, 16, 16, 16], vel=0.55), pr)
    P["pad"] = sustain_chords(pr, 52, 69, 4, vel=0.55, overlap=1.5)
    P["org"] = sustain_chords(pr, 54, 69, 3, vel=0.5, overlap=0.6, start=bar(8))
    ped = []
    for b0, b1, p in ((0, 24, 30), (24, 40, 33), (40, 56, 30)):
        ped.append(N(bar(b0), bar(b1 - b0) + 1, float(p), 0.5))
    P["org_ped"] = ped
    P["vc"] = sustain_chords(pr, 42, 54, 2, vel=0.5, overlap=0.4, start=bar(10), end=bar(44))
    P["cb"] = [N(bar(10), bar(14) + 1, 30.0, 0.5), N(bar(24), bar(16) + 1, 33.0, 0.5), N(bar(40), bar(4), 30.0, 0.45)]
    P["vla"] = sustain_chords(pr, 56, 68, 2, vel=0.5, overlap=0.4, start=bar(20), end=bar(42))
    P["timp_roll"] = [N(bar(22), bar(2) + 0.5, 45.0, 0.5)]
    P["sub"] = [N(bar(b) + pos, 2.0, 30.0 if not (24 <= b < 40) else 33.0, 0.7 if pos == 0 else 0.5)
                for b in range(BARS) for pos in (0, 3, 6)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.01: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    tide = Curve([(0, 0.4), (sec(8), 0.44), (sec(16), 0.52), (sec(22), 0.6), (sec(24.5), 0.82), (sec(36), 0.8),
                  (sec(40), 0.58), (sec(48), 0.45), (LOOP, 0.4)], period=LOOP)
    # the filter breathes on a slow swell (two bars) under the long tide
    def cutoff(t):
        t = np.asarray(t, dtype=np.float64)
        sw = 0.5 - 0.5 * np.cos(2 * np.pi * t / sec(4))
        return 500.0 + 2600.0 * tide(t % LOOP) ** 1.6 * (0.55 + 0.45 * sw)
    st = Stage(LOOP, circular=True, hall="underwater")

    pd = st.stem("pad", {"underwater": 0.5, "shimmer:cathedral": 0.15}, depth=0.7)
    pads = S(P["pad"], 1, 0.0)
    for n in pads:
        n.v = float(n.v * (0.55 + 0.6 * tide(n.t)))
    EL.pad(pd, pads, gain=1.25, seed=1, cutoff=520, attack=4.0, release=5.0, detune=14, lfo=0.05, curve=tide)
    pd.buf = FX.chorus(pd.buf, rate=0.25, depth_ms=3.5, mix=0.4, circular=True).astype("float32")
    sb = st.stem("sub", {}, depth=0.3)
    subs = S(P["sub"], 2, 0.0)
    for n in subs:
        n.v = float(n.v * (0.6 + 0.5 * tide(n.t)))
    EL.sub_pulse(sb, subs, gain=0.55, seed=2, decay=0.5, drive=1.2)
    pd.buf = FX.duck(pd.buf, [n.t for n in subs], depth=0.22, release=0.35, circular=True).astype("float32")

    ar = st.stem("arp", {"underwater": 0.45, "concert": 0.25}, depth=0.6)
    arp = S(P["arp"], 3, 0.0)
    for n in arp:
        n.v = float(n.v * (0.6 + 0.5 * tide(n.t)))
    EL.arp(ar, arp, gain=1.0, seed=3, cutoff=cutoff, res=2.0, decay=0.22, shape=0.3, pan=-0.15, pan_wobble=0.25)
    ar.buf = (ar.buf + FX.echo(ar.buf, clk.s(1.5), fb=0.42, mix=0.32, lp=2200, circular=True)).astype("float32")
    mr = st.stem("mirror", {"underwater": 0.5, "shimmer:cathedral": 0.2}, depth=0.7)
    mir = S(P["mirror"], 4, 0.0)
    for n in mir:
        n.v = float(n.v * (0.5 + 0.6 * tide(n.t)))
        n.x["attack"] = 0.03
        n.x["release"] = 0.9
    EL.glass(mr, mir, gain=0.6, seed=4, bright=0.5, pan_spread=0.0, breath=0.04)
    mr.buf = FX.eq(mr.buf.astype(np.float64), ("lp", 3800, 0.7), circular=True)
    mr.buf = (mr.buf + FX.echo(mr.buf, clk.s(3), fb=0.38, mix=0.3, lp=2000, circular=True)).astype("float32")
    wh = st.stem("whale", {"underwater": 0.6, "shimmer:cathedral": 0.3}, depth=0.75)
    EL.glass_line(wh, S(P["whale"], 5, 0.0), gain=0.75, seed=5, glide=0.9, attack=1.2, release=4.0, pan=0.1,
                  bright=0.6)

    st.play("organ", S(P["org"], 6, 0.0), "organ_soft", seed=6, dyn=tide, gain_db=-14)
    st.play("organ", S(P["org_ped"], 7, 0.0), "organ_soft_pedal", seed=7, dyn=tide, gain_db=-7)
    shape = {"attack": 0.9, "swell": 0.25, "taper": 3.0}
    # the section strings only as soft tides far back, under the organ and the pad
    st.play("cellos", S(P["vc"], 8), "cellos", seed=8, dyn=tide, gain_db=-12, depth=0.82, shape=shape, lag=0.04)
    st.play("basses", S(P["cb"], 9), "basses", seed=9, dyn=tide, gain_db=-9, depth=0.82, shape=shape, lag=0.04)
    st.play("violas", S(P["vla"], 10), "violas", seed=10, dyn=tide, gain_db=-13, depth=0.82, shape=shape, lag=0.04)
    st.play("horns", S(P["horns"], 11), "horns", seed=11,
            dyn=Curve([(sec(23.5), 0.4), (sec(26), 0.68), (sec(34), 0.62), (sec(38), 0.4)]), gain_db=-2,
            shape=shape, lag=0.03)
    st.play("solo_violin", S(P["vn"], 12), "solo_violin", seed=12,
            dyn=Curve([(sec(27.5), 0.35), (sec(31), 0.55), (sec(37), 0.52), (sec(40), 0.3)]), gain_db=1,
            shape=shape, lag=0.03, layer_bias=-0.2, depth=0.65, legato=True, slide=0.12)
    st.play("timpani", S(P["timp_roll"], 13, 0.0), "timpani_roll", seed=13,
            dyn=Curve([(sec(22), 0.02), (sec(24.2), 0.55), (sec(24.3), 0.2)]), gain_db=-8, release=0.6)

    out = st.render({"underwater": {"seed": 71}, "concert": {"seed": 73},
                     "shimmer:cathedral": {"seed": 72, "gens": 2, "fb": 0.45}}, warmth=0.35)
    out = FX.eq(out, ("lp", 6000, 0.6), ("ls", 120, 0.7, 1.0), circular=True)
    return finish_loop("music", "deep", out, LOOP, 4, -16.0, 192, tilt_hs_db=-1.5,
                       meta={"title": TITLE, "bpm": 100, "meter": "4/4", "beat": "quarter",
                             "key": "F# dorian / A lydian", "instrument": "synth arpeggio and glass"})


if __name__ == "__main__":
    render()
