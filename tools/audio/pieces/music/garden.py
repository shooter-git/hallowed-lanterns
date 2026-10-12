"""III. The Lantern Garden — "Lantern Song" (rescored, Glass).

Straight time, the eighths grouped 3+3+2. A harp ostinato grows by Philip
Glass's additive process (the cell's first 2 notes, then 2+3, then 2+3+3
...), so its groups slide across the bar lines. A soft pipe organ cycles
broken chords in eighths (3+3+2), one note changing at a time, over a G
Mixolydian pedal (G, Em9, Cmaj9, F over G - the flat seventh is the
lantern-light colour). Flute and clarinet interlock in a hocket of the
organ's figure an octave up. Then a small FUGUE: the subject is the cell
G E D B D with a falling tail; the clarinet states it, the flute answers at
the fifth (modally, with F natural), a horn and the bassoon enter, and a stretto
of solo violin, oboe and bassoon piles the entries one bar apart, over
pizzicato cellos and violas plucking the harmony in 3+3+2. At the top the
full organ plays the subject augmented in the pedal (a bar a note) under
horns, the harmony following it; then the voices drop away to the harp
again. 4/4, quarter = 96, 54 bars = 135 s.
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords, roots
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop

TITLE = "Lantern Song"
BAR = 8           # eighths
BARS = 54
BPM_UNIT = 192    # eighths per minute (quarter = 96)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 135 s
M = PR.Mode(55, "mixolydian")  # G (F natural)

A = [("Gadd9", 2, [62, 67, 69, 71], 31), ("Em9/G", 2, [62, 66, 67, 71], 31),
     ("Cmaj9/G", 2, [62, 64, 67, 71], 31), ("F/G", 2, [60, 65, 67, 69], 31)]
B = [("Gadd9", 1, [62, 67, 69, 71], 31), ("Em9", 1, [62, 66, 67, 71], 28), ("Cmaj9", 1, [62, 64, 67, 71], 36),
     ("G/B", 1, [62, 67, 71, 74], 35), ("Gadd9", 1, [62, 67, 69, 71], 31), ("Em9", 1, [62, 66, 67, 71], 28),
     ("Cmaj9", 1, [62, 64, 67, 71], 36), ("D7sus4", 1, [60, 62, 67, 69], 38)]
TOP = [("Gadd9", 1, [62, 67, 69, 71], 31), ("Em9", 1, [62, 66, 67, 71], 28), ("Cmaj9", 1, [62, 64, 67, 71], 36),
       ("G/B", 1, [62, 67, 71, 74], 35), ("Dsus4", 2, [62, 67, 69, 74], 38), ("Gadd9", 2, [62, 67, 69, 71], 31)]
END = [("Gadd9", 2, [62, 67, 69, 71], 31), ("F/G", 2, [60, 65, 67, 69], 31), ("Gadd9", 2, [62, 67, 69, 71], 31)]
PLAN = A * 3 + B + TOP + A + END   # bars 0-23, 24-31, 32-39, 40-47, 48-53
# the fugue subject: the cell G E D B D, then a falling tail C B A G (eighths)
SUBJECT = [0, 5, 4, 2, 4, 3, 2, 1, 0]
SUBJ_RH = [1, 2, 1, 1, 2, 1, 1, 1, 2]
ORG_FIG = [0, 2, 1, 3, 2, 1, 3, 2]
ORG_ACC = [1.0, .75, .82, .95, .75, .82, .92, .78]


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b, _, _ in PLAN))


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    # harp: additive process on the cell, eighths, re-starting when it has grown
    groups = [2, 2, 2, 3, 3, 3, 2, 3, 3, 2, 3, 3, 4, 4, 5, 5, 4, 3]
    hp = []
    t = 0.0
    while t < bar(BARS):
        seg, t2 = PR.additive(PR.cell("P"), groups, M, 7, t, 1.0, vel=0.5, accent=1.2, legato=1.8)
        hp += [n for n in seg if n.t < bar(BARS)]
        t = t2
    P["harp"] = PR.fit([n for n in hp if not (bar(32) <= n.t < bar(40))], pr)
    # organ: cycling broken chords in 3+3+2, one note changing at a time (from bar 4)
    org, _ = PR.cycling([(s, b) for _, b, s, _ in PLAN], ORG_FIG, 1.0, 0.0, 1, vel=0.5, accents=ORG_ACC,
                        legato=1.1)
    P["org"] = [n for n in org if bar(4) <= n.t < bar(50)]
    ped, t = [], 0.0
    for c, b, s, bass in PLAN:
        ped.append(N(t, bar(b) + 0.3, float(bass + 12), 0.5))
        t += bar(b)
    P["org_ped"] = [n for n in ped if n.t < bar(32) or n.t >= bar(40)]
    # flute and clarinet: a hocket of the organ's figure an octave up (bars 12-31)
    run = [n for n in org if bar(12) <= n.t < bar(32)]
    fl, cl = PR.hocket([N(n.t, 0.9, n.p + 12, n.v * 0.9) for n in run], 2)
    P["fl_run"], P["cl_run"] = fl, cl
    # the fugue (bars 16-31): subject, answer at the fifth (modal), stretto
    entries = [(16, 0, "clarinet"), (18, 4, "flute"), (20, -3, "violas"), (22, -7, "bassoon"),
               (25, 7, "violins"), (26, 4, "oboe"), (27, -7, "cellos"), (29, 0, "clarinet"), (30, 4, "flute")]
    fug = []
    for b0, deg, part in entries:
        notes = PR.realize(SUBJECT, M, deg, bar(b0), SUBJ_RH, vel=0.6)
        for n in notes:
            n.x["part"] = part
        fug += notes
    P["fugue"] = fug
    # the top: subject augmented in the organ pedal (a bar a note), full organ, horns, strings
    P["ped_aug"] = PR.realize(SUBJECT[:5], M, -7, bar(32), [8, 8, 8, 8, 16], vel=0.6)   # G2 E3 D3 B2 D3
    P["org_full"] = sustain_chords(pr, 55, 74, 4, vel=0.6, start=bar(32), end=bar(40))
    P["horns"] = sustain_chords(pr, 52, 64, 2, vel=0.6, start=bar(32), end=bar(40))
    P["vn"] = sustain_chords(pr, 67, 81, 2, vel=0.55, start=bar(30), end=bar(40))
    # pizzicato in 3+3+2 under the organ: cellos pluck the bass, violas two chord tones
    pz_vc, pz_vla, t = [], [], 0.0
    for c, b, s_, bass in PLAN:
        for k in range(b):
            tb = t + bar(k)
            if bar(6) <= tb < bar(48) and not (bar(32) <= tb < bar(40)):
                pz_vc += [N(tb, 2.0, float(bass + 12), 0.55), N(tb + 6, 1.5, float(bass + 19), 0.4)]
                pz_vla += [N(tb + 3, 1.0, float(s_[0]), 0.42), N(tb + 3, 1.0, float(s_[2]), 0.38),
                           N(tb + 6, 1.0, float(s_[1]), 0.4)]
        t += bar(b)
    P["pz_vc"], P["pz_vla"] = pz_vc, pz_vla
    P["timp_roll"] = [N(bar(30), bar(2) + 0.3, 43.0, 0.55)]
    P["timp"] = [N(bar(32), 3, 43.0, 0.65), N(bar(38), 3, 43.0, 0.5)]
    P["air"] = [N(bar(0), bar(6), 86.0, 0.25), N(bar(48), bar(6), 86.0, 0.25)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.015))
    S = lambda notes, seed, j=0.01: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.3), (sec(6), 0.36), (sec(12), 0.44), (sec(16), 0.52), (sec(24), 0.62), (sec(30), 0.72),
                 (sec(32.5), 0.88), (sec(38), 0.84), (sec(41), 0.55), (sec(48), 0.36), (LOOP, 0.3)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.35, "swell": 0.2, "taper": 2.0}

    hp = S(P["harp"], 1, 0.008)
    for n in hp:
        n.v = float(n.v * (0.55 + 0.6 * arc(n.t)))
    st.play("harp", hp, "harp", seed=1, gain_db=-2)
    og = S(P["org"], 2, 0.0)
    for n in og:
        n.v = float(n.v * (0.7 + 0.5 * arc(n.t)))
    st.play("organ", og, "organ_soft", seed=2, dyn=arc, gain_db=-3, legato=False, release=0.3)
    st.play("organ", S(P["org_ped"], 3, 0.0), "organ_soft_pedal", seed=3, dyn=arc, gain_db=-6)
    st.play("flutes", S(P["fl_run"], 4, 0.008), "flute_stac", seed=4, gain_db=6)
    st.play("clarinets", S(P["cl_run"], 5, 0.008), "clarinet_stac", seed=5, gain_db=2)
    # the fugue's voices: winds, a horn and a solo violin (no section strings)
    insts = {"clarinet": ("clarinets", "clarinet"), "flute": ("flutes", "flute"), "violas": ("horns", "horns"),
             "bassoon": ("bassoon", "bassoon"), "violins": ("solo_violin", "solo_violin"), "oboe": ("oboe", "oboe"),
             "cellos": ("bassoon", "bassoon")}
    for part, (stem, inst) in insts.items():
        notes = [n for n in P["fugue"] if n.x["part"] == part]
        if notes:
            g = {"clarinet": 6, "flute": 6, "violas": -2, "bassoon": 1, "violins": 2, "oboe": 0, "cellos": 1}[part]
            st.play(stem, S(notes, 6, 0.012), inst, seed=6, dyn=arc, gain_db=g,
                    shape={"attack": 0.12, "swell": 0.15, "taper": 1.5}, lag=0.015)
    top = Curve([(sec(31), 0.3), (sec(33), 0.8), (sec(38.5), 0.8), (sec(41), 0.35)])
    st.play("organ", S(P["ped_aug"], 7, 0.0), "organ_pedal", seed=7, dyn=top, gain_db=-6)
    st.play("organ", S(P["org_full"], 8, 0.0), "organ", seed=8, dyn=top, gain_db=-12)
    st.play("horns", S(P["horns"], 9), "horns", seed=9, dyn=top, gain_db=-4, shape=shape, lag=0.03)
    st.play("violins2", S(P["vn"], 10), "violins", seed=10, dyn=arc, gain_db=-13, seat="violins2", depth=0.8,
            shape=shape, lag=0.03)
    pv = S(P["pz_vc"], 11, 0.006)
    pa = S(P["pz_vla"], 12, 0.006)
    for n in pv + pa:
        n.v = float(n.v * (0.65 + 0.5 * arc(n.t)))
    st.play("cellos_pizz", pv, "cellos_pizz", seed=11, gain_db=1, seat="cellos")
    st.play("violas_pizz", pa, "violas_pizz", seed=12, gain_db=0, seat="violas")
    st.play("timpani", S(P["timp_roll"], 13, 0.0), "timpani_roll", seed=13,
            dyn=Curve([(sec(30), 0.02), (sec(32), 0.6), (sec(32.05), 0.25)]), gain_db=-7, release=0.4)
    st.play("timpani", S(P["timp"], 14, 0.004), "timpani", seed=14, gain_db=-5)
    gl = st.stem("glass", {"shimmer:cathedral2": 0.45, "concert": 0.5})
    EL.glass(gl, S(P["air"], 15, 0.0), gain=0.28, seed=15, attack=2.0, release=4.0)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.2, 0.04, 0.1, circular=True).astype("float32")

    out = st.render({"concert": {"seed": 31}, "cathedral2": {"seed": 32},
                     "shimmer:cathedral2": {"seed": 33, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "garden", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 96, "meter": "4/4", "beat": "quarter", "key": "G mixolydian",
                             "instrument": "organ and harp"})


if __name__ == "__main__":
    render()
