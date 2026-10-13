"""II. The Candle Grove — "Blue Hour" (rescored, Martinez / Glass / Zimmer).

Hide-and-seek in 7/8 (2+2+3). A glass arpeggio cycles seven notes a bar -
the Ember's cell D B A F# A sits inside it - and changes ONE note per bar as
the chords move over a B pedal (Bm9, Gmaj7#11, Em9, F#7sus4), with a dotted,
filtered delay behind it. A second glass voice enters with the MIRRORED
figure a sixteenth late, so the two interlock; cello pizzicati pluck the
pedal in 2+2+3. A clarinet carries the cell augmented (two bars a note);
then fragments of the cell (D-B-A) enter in stretto - oboe, flute,
bassoon - each three eighths a note so they slide across the 7/8 bar lines,
while a cello spiccato ticks in sixteenths with 2+2+3 accents. The lift
turns to the relative major, G to D, staying in the key (the arpeggio
morphs into it note by note; soft divisi violas far back; pizzicati hocket
with the glass) while distant horns sing the cell's inversion. Then the
oboe holds the cell high over everything and it all subtracts back to the
glass and the pedal. 7/8, eighth = 240, 76 bars = 133 s.
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop
from hlaudio import lead as LD

TITLE = "Blue Hour"
BAR = 7
BARS = 76
BPM_UNIT = 240
LOOP = BARS * BAR * 60 / BPM_UNIT  # 133 s
M = PR.Mode(59, "aeolian")  # B

PLAN = [  # (chord, bars, arpeggio set, bass)
    ("Bmadd9", 4, [66, 69, 71, 73, 74], 35), ("Gmaj7#11/B", 4, [66, 67, 71, 73, 74], 35),
    ("Bmadd9", 4, [66, 69, 71, 73, 74], 35),
    ("Bm9", 4, [66, 69, 71, 73, 74], 35), ("Gmaj7#11/B", 4, [66, 67, 71, 73, 74], 35),
    ("Em9/B", 4, [66, 67, 71, 74, 76], 35), ("F#7sus4/B", 4, [66, 71, 73, 76, 78], 35),
    ("Bm9", 4, [66, 69, 71, 73, 74], 35), ("G6/B", 4, [64, 67, 71, 74, 76], 35),
    ("Em9", 4, [66, 67, 71, 74, 76], 40), ("F#7sus4", 4, [66, 71, 73, 76, 78], 42),
    ("Gmaj9", 4, [66, 69, 71, 74, 78], 43), ("Dmaj9", 4, [66, 69, 73, 74, 76], 38),
    ("Bmadd9", 4, [66, 69, 71, 73, 74], 35),
    ("Bm9", 4, [66, 69, 71, 73, 74], 35), ("Gmaj7#11/B", 4, [66, 67, 71, 73, 74], 35),
    ("F#7sus4", 4, [66, 71, 73, 76, 78], 42),
    ("Bmadd9", 8, [66, 69, 71, 73, 74], 35),
]
FIG = [4, 2, 1, 0, 1, 3, 2]        # D B A F# A C# B over Bm: the cell plus two
MIRROR = [0, 2, 3, 4, 3, 1, 2]     # the same figure upside down


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b, _, _ in PLAN))


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    acc = [1.0, 0.7, 0.9, 0.7, 0.95, 0.72, 0.75]  # 2+2+3
    a1, _ = PR.cycling([(s, b) for _, b, s, _ in PLAN], FIG, 1.0, 0.0, 1, vel=0.6, accents=acc)
    a2, _ = PR.cycling([(s, b) for _, b, s, _ in PLAN], MIRROR, 1.0, 0.5, 1, vel=0.5, accents=acc)
    P["arp1"] = a1
    P["arp2"] = [n for n in a2 if bar(28) <= n.t < bar(68)]
    # pizzicato hocket in the lift: every other note of the mirror figure, an octave down
    pz = [n for i, n in enumerate(a2) if bar(44) <= n.t < bar(56) and i % 2 == 0]
    for n in pz:
        n.p -= 12
        n.v *= 0.9
    P["pizz"] = pz
    # the pedal and the moving bass
    cb, t = [], 0.0
    for c, b, s, bass in PLAN:
        cb.append(N(t, bar(b) + 0.5, float(bass + 12 if bass < 36 else bass), 0.5))
        t += bar(b)
    P["cb"] = cb
    # the pedal plucked: cellos pizzicato on the 2+2+3 group starts where the spiccato is silent
    pz_vc = []
    for n in cb:
        b0, b1 = int(round(n.t / BAR)), int(round((n.t + n.d - 0.5) / BAR))
        for b in range(b0, b1):
            if b < 28 or b >= 68:
                p = n.p + 12 if n.p < 48 else n.p
                pz_vc += [N(bar(b), 1.5, p, 0.55), N(bar(b) + 2, 1.0, p + 7, 0.38), N(bar(b) + 4, 1.5, p, 0.45)]
    P["vc_pizz"] = pz_vc
    P["vla"] = PR.realize(PR.cell("P"), M, 2, bar(12), [14, 14, 14, 14, 28], vel=0.5)     # D4 B4 A4 F#4 A4
    st = []
    for b0, deg, part in [(28, 9, "vn"), (29.5, 2, "cl"), (31, -3, "vc"), (36, 11, "vn"), (37.5, 4, "cl"),
                          (39, 0, "vc")]:
        notes = PR.realize(PR.cell("P", 3), M, deg, bar(b0), [3, 3, 6], vel=0.55)
        for n in notes:
            n.x["part"] = part
        st += notes
    P["stretto"] = st
    acc16 = [1.15, .6, .75, .6, 1.05, .6, .75, .6, 1.1, .6, .7, .6, .75, .6]
    P["tick"] = PR.ticking([47, 54, 47, 54, 47, 54, 50, 54, 47, 54, 47, 54, 50, 54], bar(28), bar(68), 0.5, acc16,
                           vel=0.5)
    P["vla_div"] = [N(bar(44), bar(4) + 0.5, float(p), 0.5) for p in (55, 62)] + \
        [N(bar(48), bar(4) + 0.5, float(p), 0.5) for p in (57, 62)] + \
        [N(bar(52), bar(4), float(p), 0.45) for p in (54, 62)]
    P["horns"] = PR.realize(PR.cell("I", 4), M, 2, bar(44), [14, 14, 14, 28], vel=0.55)  # D4 F#3 G3 B3
    P["vn_hi"] = PR.realize(PR.cell("P"), M, 11, bar(56), [14, 14, 14, 14, 28], vel=0.6)  # F#5 D6 C#6 A5 C#6
    P["org"] = [N(bar(56), bar(12), float(p), 0.5) for p in (54, 59, 62)]
    P["org_ped"] = [N(bar(56), bar(12), 35.0, 0.5)]
    P["sub"] = []
    for b in range(12, 68):
        P["sub"] += [N(bar(b), 1.5, 35.0, 0.75), N(bar(b) + 4, 1.0, 35.0, 0.5)]
    P["pad"] = []
    t = 0.0
    for c, b, s, bass in PLAN:
        P["pad"] += [N(t, bar(b) + 1.0, float(p - 12), 0.5) for p in s[1:4]]
        t += bar(b)
    P["timp_roll"] = [N(bar(54), bar(2) + 0.3, 47.0, 0.55)]
    P["timp"] = [N(bar(56), 3, 47.0, 0.65), N(bar(64), 3, 42.0, 0.5)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.22), (sec(12), 0.32), (sec(28), 0.45), (sec(44), 0.6), (sec(52), 0.7), (sec(57), 0.88),
                 (sec(66), 0.82), (sec(70), 0.4), (sec(75), 0.22), (LOOP, 0.22)], period=LOOP)
    cutoff = Curve([(0, 700), (sec(12), 900), (sec(28), 1500), (sec(44), 2400), (sec(57), 3600), (sec(66), 2800),
                    (sec(72), 900), (LOOP, 700)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.6, "swell": 0.2, "taper": 3.0}

    ar = st.stem("arp", {"concert": 0.55, "shimmer:cathedral2": 0.15}, depth=0.55)
    a1 = S(P["arp1"], 1, 0.004)
    a2 = S(P["arp2"], 2, 0.004)
    for n in a1 + a2:
        n.v = float(n.v * (0.55 + 0.6 * arc(n.t)))
    EL.arp(ar, a1, gain=0.6, seed=1, cutoff=cutoff, res=2.4, decay=0.3, shape=0.25, pan=-0.15, pan_wobble=0.2)
    EL.arp(ar, a2, gain=0.45, seed=2, cutoff=cutoff, res=2.4, decay=0.25, shape=0.2, pan=0.25, pan_wobble=0.2)
    ar.buf = (ar.buf + FX.echo(ar.buf, 0.375, fb=0.45, mix=0.35, lp=2200, circular=True)).astype("float32")

    pd = st.stem("pad", {"concert": 0.6}, depth=0.7)
    pads = S(P["pad"], 3, 0.0)
    for n in pads:
        n.v = float(n.v * (0.5 + 0.7 * arc(n.t)))
    EL.pad(pd, pads, gain=0.9, seed=3, cutoff=650, attack=3.0, release=4.0, detune=12, lfo=0.05)
    pd.buf = FX.chorus(pd.buf, rate=0.25, depth_ms=3.0, mix=0.35, circular=True, seed=3).astype("float32")
    sub_times = [clk.s(n.t) for n in P["sub"]]
    pd.buf = FX.duck(pd.buf, sub_times, depth=0.25, release=0.3, circular=True).astype("float32")
    sb = st.stem("sub", {}, depth=0.3)
    subs = S(P["sub"], 4, 0.0)
    for n in subs:
        n.v = float(n.v * (0.6 + 0.5 * arc(n.t)))
    EL.sub_pulse(sb, subs, gain=0.6, seed=4, decay=0.35)

    kw = dict(dyn=arc, shape=shape, lag=0.03)
    st.play("basses", S(P["cb"], 5), "basses", seed=5, gain_db=-21, **LD.bed(), **kw)
    vp = S(P["vc_pizz"], 6, 0.006)
    for n in vp:
        n.v = float(n.v * (0.7 + 0.5 * arc(n.t)))
    st.play("cellos_pizz", vp, "cellos_pizz", seed=6, gain_db=3, seat="cellos")
    st.play("clarinets", S(P["vla"], 7), "clarinet", seed=7, gain_db=6, **kw)
    sh2 = {"attack": 0.25, "swell": 0.25, "taper": 2.0}
    for part, inst, seat, g in (("vn", "oboe", "oboe", 6), ("cl", "flute", "flutes", 8),
                                ("vc", "bassoon", "bassoon", 2)):
        notes = [n for n in P["stretto"] if n.x["part"] == part]
        st.play(seat, S(notes, 8, 0.012), inst, seed=8, gain_db=g, dyn=arc, shape=sh2, lag=0.02,
                **(LD.lead(st) if inst == "oboe" else {}))
    tk = S(P["tick"], 9, 0.006)
    for n in tk:
        n.v = float(n.v * (0.6 + 0.55 * arc(n.t)))
    st.play("cellos_spic", tk, "cellos_spic", seed=9, gain_db=2, seat="cellos")
    st.play("violas", S(P["vla_div"], 10), "violas", seed=10, seat="violas", **LD.bed(),
            dyn=Curve([(sec(44), 0.3), (sec(50), 0.5), (sec(55), 0.55), (sec(56), 0.3)]), gain_db=-17,
            shape=shape, lag=0.03)
    st.play("pizz", S(P["pizz"], 11, 0.006), "violas_pizz", seed=11, seat="violas", gain_db=10)
    st.play("horns", S(P["horns"], 12), "horns", seed=12, dyn=Curve([(sec(44), 0.4), (sec(48), 0.6), (sec(53), 0.45)]),
            gain_db=1, shape=shape, lag=0.03)
    st.play("oboe", S(P["vn_hi"], 13), "oboe", seed=13, dyn=Curve([(sec(56), 0.5), (sec(60), 0.68),
                                                                    (sec(66), 0.58), (sec(68), 0.35)]),
            gain_db=7, shape=shape, lag=0.03, **LD.lead(st))
    peak = Curve([(sec(55), 0.25), (sec(58), 0.65), (sec(66), 0.6), (sec(68), 0.2)])
    st.play("organ", S(P["org"], 14, 0.0), "organ_soft", seed=14, dyn=peak, gain_db=-12)
    st.play("organ", S(P["org_ped"], 15, 0.0), "organ_soft_pedal", seed=15, dyn=peak, gain_db=-9)
    st.play("timpani", S(P["timp_roll"], 16, 0.0), "timpani_roll", seed=16,
            dyn=Curve([(sec(54), 0.02), (sec(56), 0.6), (sec(56.05), 0.25)]), gain_db=-7, release=0.4)
    st.play("timpani", S(P["timp"], 17, 0.004), "timpani", seed=17, gain_db=-5)

    out = st.render({"concert": {"seed": 21}, "cathedral2": {"seed": 22},
                     "shimmer:cathedral2": {"seed": 23, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "grove", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 240, "meter": "7/8", "beat": "eighth", "key": "B minor (aeolian)",
                             "instrument": "glass arpeggio"})


if __name__ == "__main__":
    render()
