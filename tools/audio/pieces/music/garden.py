"""III. The Lantern Garden — "Lantern Song" (rescored: Glass, in the colours
of a lantern festival).

The garden is a tunnel and a great tree hung with hundreds of round red
lanterns behind bamboo fences: a Mid-Autumn night. The piece keeps its
process music and the Ember's cell, but lives in G major PENTATONIC (G A B D
E; no F, no C) and takes the festival's instruments (VCSL, CC0): a plucked
zither (the dan tranh, played as a guzheng), an ocarina standing in for the
clay xun, a temple gong, finger cymbals and a temple block.

Straight time, the eighths grouped 3+3+2. A low harp ostinato grows by
Philip Glass's additive process on the cell (G E D B D in the pentatonic:
the first 2 notes, then 2+3, 2+3+3 ...), its groups sliding across the bar
lines; a soft organ cycles the harmony in eighths (3+3+2), one note
changing at a time, over a G pedal: G6/9, E minor 11, A7sus4, D sus4 - all
five notes of the pentatonic, re-weighted. Above it the zither sings the
cell the guzheng way: a sweep over the strings lands on the first note, the
long notes are reached by pressing up from the string below and shimmer
with the left hand's pressed vibrato; it answers itself with the cell's
falling tail. Then the ocarina breathes the cell augmented (a bar a note)
while the zither answers in the gaps, a temple block ticks the pickups and
flute and clarinet interlock in a hocket of the organ's figure.

The FUGUE (bars 16-31): the subject is the cell with a falling tail (G E D B
D | E-D B A G); clarinet, the zither answering at the fifth, a horn, the
bassoon; a stretto of solo violin, ocarina, bassoon, zither, clarinet and
flute a bar apart over pizzicato cellos and violas plucking the harmony in
3+3+2. The drums are born in the stretto (bar 28): a big drum and the low
timpani in 3+3+2 (a Chinese drum's weight, the temple gong on the downbeat
of the top), syncopations and ghost notes joining as the swell grows. At
the top (32-39) the organ pedal plays the subject augmented (a bar a note)
under the full organ and horns while the zither's tremolo sings it twice as
fast (a mensuration canon); the drums thin out and are gone by bar 40,
where the ocarina sings the subject's tail, long, and the zither answers.
A soft gong and a falling sweep close the circle.

4/4, quarter = 96, 54 bars = 135 s.

  bars  0-7   the sweep; the zither's cell over the harp's additive process
  bars  8-15  ocarina: the cell augmented; the zither answers; temple block
  bars 16-31  the fugue; the stretto; the drums enter at 28
  bars 32-39  the top: gong, drums, pedal subject, zither tremolo canon
  bars 40-47  the drums gone; the ocarina's long tail; zither replies
  bars 48-53  soft gong, a falling sweep, the cell once more
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio import festival as FE
from hlaudio.beats import groove
from hlaudio.piece import finish_loop

TITLE = "Lantern Song"
BAR = 8           # eighths
BARS = 54
BPM_UNIT = 192    # eighths per minute (quarter = 96)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 135 s
MP = PR.Mode(55, "pentatonic")     # G pentatonic: degree 0 = G3, 3 = D4, 5 = G4, 8 = D5
PCELL = [0, 4, 3, 2, 3]            # the Ember's cell G E D B D, in pentatonic degrees

# (chord, bars, organ voicing, bass) - every chord inside G A B D E
G69 = ("G6add9", [62, 67, 69, 71], 31)
EM = ("Em11", [62, 64, 67, 71], 28)
A7 = ("A7sus4", [62, 64, 67, 69], 33)
GB = ("G/B", [62, 67, 71, 74], 35)
DS = ("Dsus4", [62, 67, 69, 74], 38)


def _c(ch, bars, sym=None, bass=None):
    return (sym or ch[0], bars, ch[1], ch[2] if bass is None else bass)


A = [_c(G69, 2), _c(EM, 2, "Em11/G", 31), _c(A7, 2, "A7sus4/G", 31), _c(DS, 2, "Dsus4/G", 31)]
B = [_c(G69, 1), _c(EM, 1), _c(A7, 1), _c(GB, 1), _c(G69, 1), _c(EM, 1), _c(A7, 1), _c(DS, 1)]
TOP = [_c(G69, 1), _c(EM, 1), _c(A7, 1, "A7sus4/D", 38), _c(GB, 1), _c(DS, 2), _c(G69, 2)]
END = [_c(G69, 2), _c(A7, 2, "A7sus4/G", 31), _c(G69, 2)]
PLAN = A * 3 + B + TOP + A + END   # bars 0-23, 24-31, 32-39, 40-47, 48-53
# the fugue subject: the cell, then a falling tail E-D (sixteenths) B A G
SUBJECT = PCELL + [4, 3, 2, 1, 0]
SUBJ_RH = [1, 2, 1, 1, 2, 0.5, 0.5, 1, 1, 2]
ORG_FIG = [0, 2, 1, 3, 2, 1, 3, 2]
ORG_ACC = [1.0, .75, .82, .95, .75, .82, .92, .78]
RING = 1.5        # a zither string rings past its written length (eighths)


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b, _, _ in PLAN))


def zn(t, d, p, v, **deco):
    """A zither note: rings past its written length; deco = slide (semitones
    below), vib (depth), press (semitones)."""
    n = N(float(t), float(d) + RING, float(p), float(v))
    if deco.get("slide"):
        n = FE.slide_in(n, frm=-deco["slide"], glide=deco.get("glide", 0.2))
    if deco.get("vib"):
        n = FE.vibrato(n, depth=deco["vib"], delay=deco.get("delay", 0.35))
    if deco.get("press"):
        n = FE.press(n, at=deco.get("at", 0.3), semis=deco["press"])
    return n


def zither_lines():
    """The zither's melody (eighths), plucked, with the guzheng's decorations."""
    z = []
    # bars 0-7: the cell, slow; then again, ending on its falling tail
    z += [zn(0, 2, 67, .56), zn(2, 4, 76, .6, slide=2, vib=.2), zn(6, 2, 74, .5),
          zn(8, 2, 71, .5), zn(10, 6, 74, .55, vib=.24, delay=.5)]
    z += [zn(32, 2, 67, .54), zn(34, 3, 76, .58, slide=2, vib=.18), zn(37, 1, 74, .44),
          zn(40, 2, 71, .5), zn(42, 2, 74, .5, press=2, at=.28), zn(44, .5, 76, .42), zn(44.5, .5, 74, .4),
          zn(45, 1, 71, .45), zn(46, 2, 69, .46), zn(48, 8, 67, .5, vib=.2, delay=.6)]
    # bars 8-15: short answers in the gaps of the ocarina's line
    z += [zn(84, 1, 76, .38), zn(85, 1, 74, .36), zn(86, 2, 71, .38),
          zn(100, 1, 71, .36), zn(101, 1, 69, .34), zn(102, 2, 67, .37),
          zn(116, 1, 74, .36), zn(117, 1, 76, .38), zn(118, 2, 79, .4, vib=.15)]
    # bars 36-38: the tail in plucks, after the tremolo canon
    z += [zn(288, 2, 74, .62), zn(288, 2, 62, .5), zn(290, 1, 71, .5), zn(291, 1, 69, .48),
          zn(292, 2, 71, .55, slide=2), zn(294, 2, 74, .55),
          zn(296, 3, 76, .58, vib=.2), zn(299, .5, 74, .45), zn(299.5, .5, 71, .43), zn(300, 2, 69, .48),
          zn(302, 2, 67, .5), zn(304, 8, 67, .55, vib=.2, delay=.5), zn(304, 8, 55, .45)]
    # bars 40-47: replies to the ocarina
    z += [zn(324, 1, 71, .36), zn(325, 1, 74, .37), zn(326, 2, 76, .4),
          zn(342, 1, 74, .36), zn(343, 1, 71, .35), zn(344, 2, 69, .37),
          zn(358, 1, 79, .36), zn(359, 1, 76, .36), zn(360, 3, 74, .38, vib=.15)]
    # bars 50-52: the cell once more, the last D ringing into the loop's sweep
    z += [zn(400, 2, 67, .5), zn(402, 4, 76, .54, slide=2, vib=.18), zn(406, 2, 74, .46),
          zn(408, 2, 71, .46), zn(410, 12, 74, .5, vib=.22, delay=.6)]
    # the octave pluck under the top's sweep
    z += [zn(256, 4, 79, .66), zn(256, 4, 67, .58)]
    return z


def fugue():
    """Entries (bar, start degree, part). The answers are at the fifth (D)."""
    entries = [(16, 0, "clarinet"), (18, 3, "zither"), (20, -2, "horn"), (22, -5, "bassoon"),
               (25, 5, "violin"), (26, 8, "ocarina"), (27, -5, "bassoon"), (28, 5, "zither"),
               (29, 0, "clarinet"), (30, 8, "flute")]
    out = []
    for b0, deg, part in entries:
        notes = PR.realize(SUBJECT, MP, deg, bar(b0), SUBJ_RH, vel=0.6)
        for n in notes:
            n.x["part"] = part
        out += notes
    return out


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    # harp: additive process on the cell, eighths, low (G3-E4), re-starting when grown
    groups = [2, 2, 2, 3, 3, 3, 2, 3, 3, 2, 3, 3, 4, 4, 5, 5, 4, 3]
    hp = []
    t = 0.0
    while t < bar(BARS):
        seg, t2 = PR.additive(PCELL, groups, MP, 0, t, 1.0, vel=0.5, accent=1.2, legato=1.8)
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
    P["fugue"] = PR.fit(fugue(), pr)
    # the zither: melody, the tremolo canon at the top, the sweeps
    P["zither"] = zither_lines()
    trem = PR.realize(PCELL[1:], MP, 5, bar(32) + 4, [8, 4, 4, 8], vel=0.55)       # (G) E5 D5 B4 D5, half bars
    for n in trem:
        n.d += 0.6
    P["zither_trem"] = trem
    # the ocarina: the cell augmented (bars 8-15), the subject's tail augmented (40-46)
    oc = PR.realize(PCELL, MP, 5, bar(8), [8, 16, 8, 8, 16], vel=0.55)              # G4 E5 D5 B4 D5
    oc[1].d -= 0.35                                                                # a breath after the E
    oc[-1].d -= 1.0
    tail = PR.realize([4, 3, 2, 1, 0], MP, 5, bar(40), [12, 4, 12, 8, 16], vel=0.55)  # E5 D5 B4 A4 G4
    tail[2].d -= 0.35
    tail[-1].d -= 2.0
    for line in (oc, tail):          # leaps are re-tongued; steps are slurred
        for a, b in zip(line, line[1:]):
            if abs(b.p - a.p) > 3 and a.t + a.d > b.t - 0.25:
                a.d = b.t - a.t - 0.25
    P["ocarina"] = oc + tail
    # the top: subject augmented in the organ pedal (a bar a note), full organ, horns, strings
    P["ped_aug"] = PR.realize(PCELL, MP, -5, bar(32), [8, 8, 8, 8, 16], vel=0.6)      # G2 E3 D3 B2 D3
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
    # temple colour: gong strokes at the top and the close, finger cymbals at phrase starts,
    # the temple block ticking the pickups (bars 12-15)
    P["gong"] = [N(bar(32), 16.0, 50.0, 0.62), N(bar(48), 16.0, 50.0, 0.5)]
    P["cymbal"] = [N(bar(b), 4.0, 103.0, v) for b, v in ((0, .5), (8, .42), (16, .44), (24, .38), (40, .48))]
    P["block"] = [N(bar(b) + pos, 1.0, 88.0, v) for b in range(12, 16) for pos, v in ((5, .34), (7, .3))]
    # the drums (bars 28-40): a big drum and low timpani in 3+3+2, born with the stretto
    swell = Curve([(bar(28), 0.12), (bar(29), 0.24), (bar(30), 0.4), (bar(31), 0.55), (bar(31.9), 0.66),
                   (bar(32), 1.0), (bar(35), 0.95), (bar(36.5), 0.86), (bar(38), 0.6), (bar(39), 0.36),
                   (bar(39.9), 0.18), (bar(40), 0.12), (bar(40.1), 0.0)])
    G2, D3 = 43.0, 50.0
    fig = [(0, "bd", 0, 1.0, 0.0), (0, "timp", G2, 0.9, 0.0),
           (3, "timp", G2, 0.72, 0.2), (5.5, "timp", G2, 0.32, 0.55),
           (6, "timp", D3, 0.78, 0.33), (7, "timp", G2, 0.3, 0.62), (7.5, "timp", G2, 0.36, 0.5),
           (8, "timp", G2, 0.85, 0.08), (10.5, "timp", G2, 0.3, 0.66), (11, "timp", G2, 0.7, 0.26),
           (14, "bd", 0, 0.72, 0.3), (14, "timp", D3, 0.8, 0.3),
           (15, "timp", G2, 0.32, 0.5), (15.25, "timp", G2, 0.36, 0.72), (15.5, "timp", G2, 0.42, 0.45),
           (15.75, "timp", G2, 0.48, 0.72),
           (2, "block", 88, 0.42, 0.7), (5, "block", 88, 0.4, 0.7), (10, "block", 88, 0.4, 0.75),
           (13, "block", 88, 0.42, 0.7)]
    P["drums"] = groove(bar(28), bar(40) + 1, 16, fig, swell, vel=(0.2, 0.86))
    P["timp_roll"] = [N(bar(30), bar(2) + 0.3, 43.0, 0.55)]
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
    st.play("harp", hp, "harp", seed=1, gain_db=-1)
    og = S(P["org"], 2, 0.0)
    for n in og:
        n.v = float(n.v * (0.7 + 0.5 * arc(n.t)))
    st.play("organ", og, "organ_soft", seed=2, dyn=arc, gain_db=-4, legato=False, release=0.3)
    st.play("organ", S(P["org_ped"], 3, 0.0), "organ_soft_pedal", seed=3, dyn=arc, gain_db=-6)
    st.play("flutes", S(P["fl_run"], 4, 0.008), "flute_stac", seed=4, gain_db=5)
    st.play("clarinets", S(P["cl_run"], 5, 0.008), "clarinet_stac", seed=5, gain_db=1)

    # the zither: a little room so the plucks bloom, then the hall
    dz = 0.5
    st.stem("zither", {"concert": 0.3 + 0.75 * dz, "chamber": 0.22}, depth=dz)
    zt = S(P["zither"], 20, 0.008)
    for n in zt:
        n.v = float(n.v * (0.85 + 0.3 * arc(n.t)))
    # the soft (mf) plucks: darker, and they settle on pitch quickly (a hard pluck starts sharp)
    st.play("zither", zt, "zither", seed=20, gain_db=10, layer_bias=-0.45)
    st.play("zither", S(P["zither_trem"], 21, 0.0), "zither_trem", seed=21, gain_db=-2)
    gls = [FE.gliss_up(sec(0), 67.0, 0.5), FE.gliss_up(sec(32), 67.0, 0.62)]
    st.play("zither", gls, "zither_gliss_up", seed=22, gain_db=-2, tail=3.0)
    st.play("zither", [FE.gliss_down(sec(48) + 0.02, 67.0, 0.42)], "zither_gliss_down", seed=23, gain_db=-5,
            tail=3.0)
    # the zither's fugue entries
    fz = [n for n in P["fugue"] if n.x["part"] == "zither"]
    fz = [FE.vibrato(N(n.t, n.d + RING, n.p, n.v), depth=0.16, delay=0.3) if n.d >= 2 else
          N(n.t, n.d + 0.6, n.p, n.v) for n in fz]
    st.play("zither", S(fz, 24, 0.008), "zither", seed=24, gain_db=6, layer_bias=-0.45)

    # the ocarina: the long-breathed line, and one entry in the stretto
    oc_dyn = Curve([(0, 0.5), (sec(8), 0.5), (sec(10), 0.6), (sec(14), 0.55), (sec(26), 0.55), (sec(40), 0.52),
                    (sec(42), 0.6), (sec(46), 0.48), (LOOP, 0.5)], period=LOOP)
    oc = S(P["ocarina"], 25, 0.0)
    st.play("ocarina", oc, "ocarina", seed=25, dyn=oc_dyn, gain_db=8, slide=0.09,
            shape={"attack": 0.12, "swell": 0.18, "taper": 1.5}, lag=0.02)
    fo = [n for n in P["fugue"] if n.x["part"] == "ocarina"]
    st.play("ocarina", S(fo, 26, 0.01), "ocarina", seed=26, dyn=oc_dyn, gain_db=7, xf=0.07, slide=0.04,
            shape={"attack": 0.08, "swell": 0.12, "taper": 1.0}, lag=0.02)

    # the fugue's other voices: winds, a horn and a solo violin (no section strings)
    insts = {"clarinet": ("clarinets", "clarinet", 6), "flute": ("flutes", "flute", 5), "horn": ("horns", "horns", -2),
             "bassoon": ("bassoon", "bassoon", 1), "violin": ("solo_violin", "solo_violin", 2)}
    for part, (stem, inst, g) in insts.items():
        notes = [n for n in P["fugue"] if n.x["part"] == part]
        if notes:
            st.play(stem, S(notes, 6, 0.012), inst, seed=6, dyn=arc, gain_db=g,
                    shape={"attack": 0.12, "swell": 0.15, "taper": 1.5}, lag=0.015)
    top = Curve([(sec(31), 0.3), (sec(33), 0.8), (sec(38.5), 0.8), (sec(41), 0.35)])
    st.play("organ", S(P["ped_aug"], 7, 0.0), "organ_pedal", seed=7, dyn=top, gain_db=-6)
    st.play("organ", S(P["org_full"], 8, 0.0), "organ", seed=8, dyn=top, gain_db=-13)
    st.play("horns", S(P["horns"], 9), "horns", seed=9, dyn=top, gain_db=-5, shape=shape, lag=0.03)
    st.play("violins2", S(P["vn"], 10), "violins", seed=10, dyn=arc, gain_db=-14, seat="violins2", depth=0.8,
            shape=shape, lag=0.03)
    pv = S(P["pz_vc"], 11, 0.006)
    pa = S(P["pz_vla"], 12, 0.006)
    for n in pv + pa:
        n.v = float(n.v * (0.65 + 0.5 * arc(n.t)))
    st.play("cellos_pizz", pv, "cellos_pizz", seed=11, gain_db=1, seat="cellos")
    st.play("violas_pizz", pa, "violas_pizz", seed=12, gain_db=0, seat="violas")

    # temple colour
    st.play("gong", S(P["gong"], 30, 0.0), "gong", seed=30, gain_db=0, tail=16.0)
    st.play("finger_cymbal", S(P["cymbal"], 31, 0.004), "finger_cymbal", seed=31, gain_db=6, tail=6.0)
    st.play("woodblock", S(P["block"], 32, 0.004), "woodblock", seed=32, gain_db=16)
    # the drums
    D = P["drums"]
    st.play("timpani", S(P["timp_roll"], 13, 0.0), "timpani_roll", seed=13,
            dyn=Curve([(sec(30), 0.02), (sec(32), 0.55), (sec(32.05), 0.25)]), gain_db=-5, release=0.4)
    st.play("timpani", S(D.get("timp", []), 14, 0.004), "timpani", seed=14, gain_db=0)
    st.play("drums", S(D.get("bd", []), 15, 0.003), "bass_drum", seed=15, gain_db=-2, seat="bass_drum")
    st.play("woodblock", S(D.get("block", []), 16, 0.003), "woodblock", seed=16, gain_db=10)

    gl = st.stem("glass", {"shimmer:cathedral2": 0.45, "concert": 0.5})
    EL.glass(gl, S(P["air"], 15, 0.0), gain=0.28, seed=15, attack=2.0, release=4.0)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.2, 0.04, 0.1, circular=True).astype("float32")

    out = st.render({"concert": {"seed": 31}, "cathedral2": {"seed": 32}, "chamber": {"seed": 34},
                     "shimmer:cathedral2": {"seed": 33, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "garden", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 96, "meter": "4/4", "beat": "quarter", "key": "G pentatonic",
                             "instrument": "zither, harp and organ"})


if __name__ == "__main__":
    render()
