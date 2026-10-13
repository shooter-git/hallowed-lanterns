"""VII. The Deep — "Where the Lanterns Swim" (rescored, Martinez / Glass, with
the analog synths of a 1980s night-drive score).

Underwater, hypnotic, in straight time. An analog arpeggio repeats the
Ember's cell (F# D# C# A C#) in eighths - five notes against the eight of a
4/4 bar, so it slides across the bar line and only realigns every five
bars - through a resonant ladder filter that opens and closes like a tide,
with a dotted-eighth echo. Later a glass voice plays the same figure
INVERTED a sixteenth behind it and the two interlock. The pitch collection
never changes (E major's notes), but the pedal under it does: F# (Dorian,
dark blue water) and then A (Lydian, the sea opening into light) - modal
ambiguity instead of key changes. A gliding glass voice sings the cell
augmented, like whale song; low strings and the organ's quiet stops swell
like tides far back; in the light the horns state the cell and the
oboe answers with its inversion in canon. A soft sub pulses under it in
3+3+2.

The 1980s colour (the synth scores of Carpenter, Tangerine Dream, Dixon and
Stein - their sound, none of their tunes): real-analog-style voices
(polyBLEP saws and pulses, two or three drifting oscillators per voice, a
4-pole ladder filter with its own envelope per note, gentle saturation,
stereo chorus and a touch of tape) in the plate and the underwater hall.
A dark bass pulses in sixteenths on the pedal (accents in 3+3+2, a hiccup
up the octave at the end of each group) from the whale's entry; a sixteenth
sequencer walks the cell up and down the mode (the cell from F#, from A,
from C#, from A again: it rises and falls, five notes at a time against the
beat) while its filter sweeps slowly open and shut with the tide; in the
light, brassy pad swells bloom on each chord and the low drums are born
with the swell (timpani on A and a bass drum in 3+3+2, ghost notes joining
as it grows) and leave before the water darkens again.
4/4, quarter = 100, 56 bars = 134.4 s.

  bars  0-7   pad, filtered arpeggio, sub, organ pedal on F#
  bars  8-23  the whale voice; the mirror arpeggio; the bass pulse; the sequencer (16)
  bars 24-39  the pedal moves to A: horns' cell, the oboe's canon, the filter opens;
              pad swells; the drums (22-38)
  bars 40-55  back onto F#, layers falling away to the arpeggio
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords, roots
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio import analog as AN
from hlaudio.beats import groove
from hlaudio.piece import finish_loop
from hlaudio import lead as LD

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
    # in the light: horns state the cell in A, the oboe answers with the inversion in canon
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
    # the analog bass: sixteenths on the pedal (F#2, A2 in the light), accents in 3+3+2
    # (eighths), the last sixteenth of each group hops up the octave
    acc = [1.0, .42, .55, .45, .58, .5, .92, .42, .55, .45, .58, .5, .88, .45, .6, .52]
    hop = {5, 11, 15}
    bass = []
    for b in range(8, 48):
        root = 45.0 if 24 <= b < 40 else 42.0
        for k in range(16):
            bass.append(N(bar(b) + k * 0.5, 0.42, root + (12 if k in hop else 0), 0.62 * acc[k]))
    P["bass"] = bass
    # the sequencer: the cell walked up and down the mode in sixteenths (from the 1st,
    # 3rd, 5th and 3rd degrees), five notes at a time against the beat (bars 16-43)
    seq = []
    starts = [0, 2, 4, 2]
    i = 0
    t = bar(16)
    while t < bar(44) - 1e-6:
        light = bar(24) <= t < bar(40)
        md, base = (MA, 7) if light else (MF, 7)          # A4 / F#4
        k = (i // 5) % 4
        p = md.p(base + starts[k] + PR.cell("P")[i % 5])
        v = 0.5 * (1.12 if i % 5 == 0 else 0.92 if i % 5 == 1 else 0.8)
        seq.append(N(t, 0.42, float(p), v))
        t += 0.5
        i += 1
    P["seq"] = seq
    # brassy pad swells in the light, one per chord
    P["swell"] = sustain_chords(pr, 57, 76, 4, vel=0.6, overlap=0.0, start=bar(24), end=bar(40))
    # the drums in the light (22-38): timpani on A, a bass drum, 3+3+2 with ghost notes
    swell = Curve([(bar(22), 0.1), (bar(23), 0.25), (bar(23.9), 0.45), (bar(24), 0.7), (bar(26), 0.8),
                   (bar(28), 0.92), (bar(33), 0.95), (bar(35), 0.8), (bar(36.5), 0.5), (bar(37.5), 0.2),
                   (bar(38), 0.0)])
    A2, E2 = 45.0, 40.0
    fig = [(0, "bd", 0, 1.0, 0.0), (0, "timp", A2, 0.85, 0.0), (3, "timp", A2, 0.7, 0.25),
           (5.5, "timp", A2, 0.3, 0.6), (6, "timp", E2, 0.75, 0.4), (7.5, "timp", A2, 0.34, 0.55),
           (8, "timp", A2, 0.8, 0.12), (11, "timp", A2, 0.68, 0.3), (13.5, "timp", A2, 0.3, 0.65),
           (14, "bd", 0, 0.7, 0.35), (14, "timp", E2, 0.75, 0.35), (15, "timp", A2, 0.32, 0.6),
           (15.5, "timp", A2, 0.4, 0.5)]
    P["drums"] = groove(bar(22), bar(38), 16, fig, swell, vel=(0.2, 0.82))
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
        n.v = float(n.v * (0.6 + 0.5 * tide(n.t)) * (0.72 if sec(8) <= n.t < sec(48) else 1.0))
    EL.sub_pulse(sb, subs, gain=0.55, seed=2, decay=0.5, drive=1.2)
    pd.buf = FX.duck(pd.buf, [n.t for n in subs], depth=0.22, release=0.35, circular=True).astype("float32")

    ar = st.stem("arp", {"underwater": 0.4, "plate": 0.18, "concert": 0.2}, depth=0.6)
    arp = S(P["arp"], 3, 0.0)
    for n in arp:
        n.v = float(n.v * (0.6 + 0.5 * tide(n.t)))
        n.x["pan"] = 0.25 * np.sin(n.t * 0.9)
    AN.play(ar, arp, AN.ARP, gain=2.5, seed=3, sweep=lambda t: 0.7 * cutoff(t) / AN.ARP.cutoff, pan=-0.15)
    ar.buf = FX.chorus(ar.buf, rate=0.3, depth_ms=2.5, mix=0.35, circular=True, seed=3)
    ar.buf = (ar.buf + FX.echo(ar.buf, clk.s(1.5), fb=0.42, mix=0.32, lp=2200, circular=True)).astype("float32")

    # the 1980s colour: the bass pulse, the sequencer, the pad swells (chorus, tape, plate)
    def swp(lo, hi, per_bars):
        def f(t):
            t = np.asarray(t, dtype=np.float64) % LOOP
            sl = 0.5 - 0.5 * np.cos(2 * np.pi * t / sec(per_bars))
            return lo + (hi - lo) * tide(t) ** 1.5 * (0.45 + 0.55 * sl)
        return f
    bs = st.stem("bass", {"underwater": 0.18, "plate": 0.08}, depth=0.35)
    bn = S(P["bass"], 40, 0.0)
    for n in bn:
        n.v = float(n.v * (0.55 + 0.55 * tide(n.t)))
    AN.play(bs, bn, AN.BASS, gain=0.7, seed=40, sweep=swp(0.7, 2.2, 8))
    bs.buf = FX.chorus(bs.buf, rate=0.2, depth_ms=1.5, mix=0.2, circular=True, seed=40)
    sq = st.stem("seq", {"plate": 0.35, "underwater": 0.35}, depth=0.62)
    qn = S(P["seq"], 41, 0.0)
    for n in qn:
        n.v = float(n.v * (0.6 + 0.5 * tide(n.t)))
        n.x["pan"] = 0.35 * np.sin(n.t * 0.37)
    AN.play(sq, qn, AN.SEQ, gain=1.0, seed=41, sweep=swp(0.45, 2.6, 8))
    sq.buf = FX.chorus(sq.buf, rate=0.33, depth_ms=3.0, mix=0.45, circular=True, seed=41)
    sq.buf = (sq.buf + FX.echo(sq.buf, clk.s(3), fb=0.3, mix=0.22, lp=1800, circular=True)).astype("float32")
    sw = st.stem("swell", {"plate": 0.3, "underwater": 0.45, "shimmer:cathedral": 0.08}, depth=0.72)
    swn = S(P["swell"], 42, 0.0)
    AN.play(sw, swn, AN.SWELL, gain=0.6, seed=42, sweep=lambda t: 0.8 + 0.6 * tide(np.asarray(t) % LOOP),
            pan_spread=0.3)
    sw.buf = FX.chorus(sw.buf, rate=0.25, depth_ms=3.5, mix=0.5, circular=True, seed=42)
    for nm in ("bass", "seq", "swell", "arp"):
        st.stems[nm].buf = FX.wow_flutter(st.stems[nm].buf, wow=0.0009, flutter=0.00025, circular=True,
                                          seed=nm).astype("float32")
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
    st.play("cellos", S(P["vc"], 8), "cellos", seed=8, dyn=tide, gain_db=-22, shape=shape, lag=0.04,
            **LD.bed())
    st.play("basses", S(P["cb"], 9), "basses", seed=9, dyn=tide, gain_db=-19, shape=shape, lag=0.04,
            **LD.bed())
    st.play("violas", S(P["vla"], 10), "violas", seed=10, dyn=tide, gain_db=-23, shape=shape, lag=0.04,
            **LD.bed())
    st.play("horns", S(P["horns"], 11), "horns", seed=11,
            dyn=Curve([(sec(23.5), 0.4), (sec(26), 0.68), (sec(34), 0.62), (sec(38), 0.4)]), gain_db=-2,
            shape=shape, lag=0.03)
    st.play("oboe", S(P["vn"], 12), "oboe", seed=12,
            dyn=Curve([(sec(27.5), 0.35), (sec(31), 0.55), (sec(37), 0.52), (sec(40), 0.3)]), gain_db=9,
            shape=shape, lag=0.03, **LD.lead(st))
    st.play("timpani", S(P["timp_roll"], 13, 0.0), "timpani_roll", seed=13,
            dyn=Curve([(sec(22), 0.02), (sec(24.2), 0.55), (sec(24.3), 0.2)]), gain_db=-8, release=0.6)
    D = P["drums"]
    st.play("timpani", S(D.get("timp", []), 14, 0.004), "timpani", seed=14, gain_db=2,
            sends={"underwater": 0.45, "concert": 0.5})
    st.play("drums", S(D.get("bd", []), 15, 0.003), "bass_drum", seed=15, gain_db=3, seat="bass_drum",
            sends={"underwater": 0.45, "concert": 0.55})

    out = st.render({"underwater": {"seed": 71}, "concert": {"seed": 73}, "plate": {"seed": 74},
                     "shimmer:cathedral": {"seed": 72, "gens": 2, "fb": 0.45}}, warmth=0.35)
    out = FX.eq(out, ("lp", 6000, 0.6), ("ls", 120, 0.7, 1.0), circular=True)
    return finish_loop("music", "deep", out, LOOP, 4, -16.0, 192, tilt_hs_db=-1.5,
                       meta={"title": TITLE, "bpm": 100, "meter": "4/4", "beat": "quarter",
                             "key": "F# dorian / A lydian", "instrument": "analog synths and glass"})


if __name__ == "__main__":
    render()
