"""VIII. The Marigold Garden — "Remember Me" (rescored: Glass, for a quiet
altar on the Day of the Dead, and the walk's one great yearning swell).

A place of remembrance, revered: an ofrenda glowing in candlelight,
marigolds, papel picado, a giant guitar. It begins as a vigil at night,
intimate and still - no string pads, nothing of the fiesta - and grows, by
melody and voicing alone, into the emotional high point of the walk before
the Wishing Tree, then pulls back to the altar so the loop's return feels
like a memory coming back.

A guitar (the harp's strings through a guitar body, the same colour as the
giant guitar in the scene) picks a broken chord in eighths, Glass's
process: one note of the figure changes at a time, so the bittersweet turn
happens inside it - C major 7 becomes C minor 6 when the E slips to
E-flat. The progression is an eight-bar cycle (G, Em7, Cmaj9, G/B, Cm6,
Cm6, G/D, D7sus4) over a soft organ pedal on G, the church at the edge of
the cemetery; a far bell (the gong, struck very gently) marks the turn of
the loop, and a marimba, softly rolled, blooms on the C minor 6 - the heart
of the piece - as the cycles come round.

The Ember's cell (G E D B D) is the seed of every line. An ocarina - a clay
flute, as Mesoamerica has always made them - breathes it augmented; a solo
violin answers it on its G string, an octave down (a canon at the cycle),
under the ocarina's suspensions. Then the cell grows into a longer line:
the violin sings it at walking pace and turns it towards the E-flat, the
ocarina follows a bar behind (a canon at the unison), the guitar starts to
add sixteenths between its eighths (Glass's additive process), horns and
the organ's quiet stops come in underneath. In the bridge the line becomes
the swell - violin and flute in unison, the Ember's own leap D-B over E
minor 9, climbing through C major 9 and A minor 9 to the high E, then the
E-flat over the borrowed C minor 6 and a C held aching over D sus, which
only resolves to B on the return to G. Horns, a fuller organ opening from
the pedal, the marimba's tremolo on every chord and a soft timpani
heartbeat carry it; then everything pulls back: the guitar's sixteenths
fall away, the horns sigh E-flat to D on the C minor 6, and the ocarina
remembers the cell once more and leaves its last leap, G up to E, hanging
over D sus, into the loop.
G major with a borrowed C minor, 4/4 at 72, 56 bars = 186.7 s.

  bars  0-7   the altar: the guitar's cycle, organ pedal, far bell; a marimba roll
  bars  8-15  ocarina: the cell augmented; cello pizzicati
  bars 16-23  solo violin: the cell an octave down (canon); the ocarina's suspensions
  bars 24-31  the build: the cell as a line, violin and ocarina in canon; guitar sixteenths;
              horns, organ
  bars 32-39  the bridge, the swell: violin and flute; E minor 9, C major 9, A minor 9,
              C minor 6, D sus; the heartbeat
  bars 40-47  the resolution and afterglow; the horns' sigh on C minor 6
  bars 48-55  the quiet altar; the ocarina's last leap left hanging
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords
from hlaudio import process as PR
from hlaudio import effects as FX
from hlaudio import festival  # noqa: F401  (seats and tone chains of the ocarina and the gong)
from hlaudio.beats import groove, drum_pitch
from hlaudio.body import stereo_body
from hlaudio.piece import finish_loop

TITLE = "Remember Me"
BAR = 8            # eighths
BARS = 56
BPM_UNIT = 144     # eighths per minute (quarter = 72)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 186.67 s
M = PR.Mode(55, "ionian")  # G

# (chord, bars, guitar voicing: the bass and three strings above it)
CYC = [("Gadd9", 1, [43, 50, 57, 59]), ("Em7", 1, [40, 50, 55, 59]), ("Cmaj9", 1, [36, 50, 55, 59]),
       ("G/B", 1, [35, 50, 55, 59]), ("Cm6", 1, [36, 51, 55, 57]), ("Cm6", 1, [36, 51, 55, 57]),
       ("G/D", 1, [38, 50, 55, 59]), ("D7sus4", 1, [38, 48, 55, 57])]
BRIDGE = [("Em9", 2, [40, 50, 55, 59]), ("Cmaj9", 2, [36, 50, 55, 59]), ("Am9", 1, [45, 48, 55, 59]),
          ("Cm6", 1, [36, 51, 55, 57]), ("D7sus4", 2, [38, 48, 55, 57])]
PLAN = CYC * 4 + BRIDGE + CYC * 2
FIG = [0, 1, 2, 3, 2, 1, 3, 2]          # thumb on the bass, fingers above, 3+3+2
ACC = [1.0, .7, .8, .9, .72, .78, .88, .74]
# the guitar's added sixteenths (offsets in eighths), section by section: grows, then falls away
ADDED = [(24, 28, (1.5, 4.5)), (28, 32, (0.5, 1.5, 3.5, 4.5, 6.5)),
         (32, 40, (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)), (40, 42, (0.5, 1.5, 3.5, 4.5, 6.5)),
         (42, 44, (1.5, 4.5))]
ROLL = {"Cm6": [63, 67, 69, 72], "Em9": [64, 67, 71, 74], "Cmaj9": [64, 67, 71, 74],
        "Am9": [64, 67, 71, 72], "D7sus4": [62, 67, 69, 72]}

# the line (pitch, eighths): the cell walked (24-31) and grown into the swell (31.75-40)
BUILD = [(67, 2), (76, 4), (74, 2),            # 24 G:      G E D        (the cell)
         (71, 2), (74, 4), (76, 2),            # 25 Em7:    B D E
         (79, 4), (76, 2), (74, 2),            # 26 Cmaj9:  G E D
         (71, 6), (74, 2),                     # 27 G/B:    B . D
         (75, 4), (74, 2), (72, 2),            # 28 Cm6:    E-flat D C   (the heart)
         (69, 4), (72, 2), (75, 2),            # 29 Cm6:    A C E-flat
         (74, 6), (71, 2),                     # 30 G/D:    D . B
         (72, 4), (69, 2)]                     # 31 D7sus4: C A ...
SWELL = [(74, 2),                              # pickup D5: the Ember's leap
         (83, 4), (81, 2), (78, 2),            # 32 Em9:    B A F#  (D B A F# A: the chime's own shape)
         (81, 4), (79, 2), (76, 2),            # 33 Em9:    A G E
         (84, 4), (83, 2), (79, 2),            # 34 Cmaj9:  C B G
         (83, 6), (86, 2),                     # 35 Cmaj9:  B . D
         (88, 4), (86, 2), (84, 2),            # 36 Am9:    E D C   (the high point)
         (87, 4), (86, 2), (84, 2),            # 37 Cm6:    E-flat D C
         (86, 4), (84, 4),                     # 38 D7sus4: D C
         (84, 8),                              # 39 D7sus4: C held, aching
         (83, 6)]                              # 40 G:      ... resolved, late, to B


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b, _ in PLAN))


def line(spec, t0, vel=0.55):
    out, t = [], t0
    for p, d in spec:
        out.append(N(t, float(d), float(p), float(vel)))
        t += d
    return out


def breathe(notes, gap=0.3):
    """Wind phrasing: re-tongue a repeated note or a leap (a small breath before it)."""
    for a, b in zip(notes, notes[1:]):
        if (abs(b.p - a.p) > 2 or b.p == a.p) and a.t + a.d > b.t - gap:
            a.d = b.t - a.t - gap
    return notes


def roll(pitches, t0, dur, v=0.32, step=0.3, swell=0.35, seed=0):
    """A soft marimba roll (eighths): each pitch re-struck every `step` (one
    mallet per note, the mallets out of phase), growing and fading."""
    r = np.random.default_rng(seed)
    out = []
    for k, p in enumerate(pitches):
        t = t0 + k * step / len(pitches)
        while t < t0 + dur - 0.05:
            u = (t - t0) / dur
            vv = v * (1 - swell + swell * np.sin(np.pi * u)) * r.uniform(0.85, 1.1)
            out.append(N(t, step * 1.5, float(p), float(np.clip(vv, 0.05, 1))))
            t += step * r.uniform(0.93, 1.07)
    return out


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    # the guitar: the bass moves with the chord; above it ONE string changes per half bar;
    # in the build and the swell it adds sixteenths between its eighths
    gt, cur, t, bnum = [], list(PLAN[-1][2]), 0.0, 0
    added = {b: pos for b0, b1, pos in ADDED for b in range(b0, b1)}
    for c, b, s in PLAN:
        for k in range(b):
            for i, idx in enumerate(FIG):
                if i == 0:
                    cur[0] = s[0]
                if i in (0, 4) and cur[1:] != s[1:]:
                    cand = [(s[j] in cur, abs(a - g), j) for j, (a, g) in enumerate(zip(cur, s)) if j > 0 and a != g]
                    j = min(cand)[2]                       # prefer a change that makes no unison
                    cur[j] = s[j]
                gt.append(N(t + i, 3.0 if idx == 0 else 2.4, float(cur[idx]), 0.42 * ACC[i]))
            for q in added.get(bnum, ()):
                idx = (3, 2, 3, 1, 2, 3, 1, 2)[int(q)]
                gt.append(N(t + q, 1.6, float(cur[idx]), 0.3))
            t += BAR
            bnum += 1
    P["guitar"] = gt
    # the ocarina: the cell augmented (8-14); its suspensions above the violin's canon (16-23)
    oc = PR.realize(PR.cell("P"), M, 7, bar(8), [8, 8, 8, 8, 12], vel=0.55)            # G4 E5 D5 B4 D5
    sus = PR.fit([N(bar(16), 8, 71.0, 0.48), N(bar(17), 8, 71.0, 0.5), N(bar(18), 6, 71.0, 0.52),
                  N(bar(18) + 6, 2, 69.0, 0.48), N(bar(19), 8, 69.0, 0.5), N(bar(20), 8, 67.0, 0.5),
                  N(bar(21), 8, 69.0, 0.52), N(bar(22), 8, 71.0, 0.5), N(bar(23), 8, 72.0, 0.46)], pr)
    # the build: the ocarina follows the violin's line a bar behind (a canon at the unison)
    canon = PR.fit([n for n in line(BUILD, bar(25), vel=0.5) if n.t < bar(32) - 1], pr)
    # the coda (50-55): the cell remembered, its last leap left hanging over D sus
    coda = line([(67, 8), (76, 8), (74, 10), (72, 6), (71, 6), (67, 2), (76, 6)], bar(50), vel=0.5)
    for ln in (oc, sus, canon, coda):
        breathe(ln)
    sus[-1].d -= 0.6
    P["ocarina"] = oc + sus + canon + coda
    # the solo violin: the cell an octave down on the G string (16-21), then the long line
    P["vn_cell"] = PR.realize(PR.cell("P"), M, 0, bar(16), [8, 8, 8, 8, 14], vel=0.55)    # G3 E4 D4 B3 D4
    P["vn_line"] = line(BUILD, bar(24), vel=0.52) + line(SWELL, bar(31) + 6, vel=0.62)
    # the flute joins the violin in unison for the swell
    P["fl_swell"] = line(SWELL, bar(31) + 6, vel=0.58)
    # the horns: under the build and the swell, then their sigh (E-flat to D) on C minor 6
    P["horns"] = sustain_chords(pr, 50, 62, 2, vel=0.55, overlap=0.3, start=bar(28), end=bar(40))
    P["hn_sigh"] = [N(bar(44), 8, 63.0, 0.5), N(bar(45), 8, 62.0, 0.46)]
    # the marimba: soft rolls on C minor 6 as the cycles come round; tremolo on every chord of the swell
    rolls = []
    for b0, nb, v in ((4, 2, 0.24), (20, 2, 0.28), (28, 2, 0.32), (44, 2, 0.28), (52, 2, 0.22)):
        rolls += roll(ROLL["Cm6"], bar(b0), bar(nb) - 0.5, v=v, seed=b0)
    t = bar(32)
    for c, b, s in BRIDGE:
        v = 0.42 if c == "Cm6" else 0.36
        rolls += roll(ROLL[c.split("/")[0]], t, bar(b) - 0.3, v=v, swell=0.25, seed=int(t))
        t += bar(b)
    P["marimba_roll"] = rolls
    # the organ: a soft pedal on G, following the bass in the bridge; quiet stops opening up
    ped = [N(bar(b), bar(8) + 0.3, 43.0, 0.45) for b in range(0, 32, 8)]
    t = bar(32)
    for c, b, s in BRIDGE:
        ped.append(N(t, bar(b) + 0.3, float(s[0]), 0.5))
        t += bar(b)
    ped += [N(bar(b), bar(8) + 0.3, 43.0, 0.45) for b in range(40, BARS, 8)]
    P["org_ped"] = ped
    P["org"] = sustain_chords(pr, 55, 67, 3, vel=0.45, overlap=0.3, start=bar(28), end=bar(42))
    P["org_full"] = sustain_chords(pr, 55, 74, 4, vel=0.55, overlap=0.3, start=bar(34), end=bar(40))
    # the far bell at the turn of the loop
    P["bell"] = [N(bar(0), 16.0, 50.0, 0.3)]
    # a soft heartbeat under the height of the swell (bars 34-39), timpani on the bass
    hb = Curve([(bar(34), 0.0), (bar(34.5), 0.2), (bar(35.5), 0.5), (bar(36.5), 0.85), (bar(37.5), 1.0),
                (bar(38.5), 0.7), (bar(39.4), 0.25), (bar(39.9), 0.0)])
    lo = drum_pitch(pr, 38, 49)
    fig = [(0, "timp", lo, 0.85, 0.0), (3, "timp", lo, 0.6, 0.35), (7.5, "timp", lo, 0.3, 0.6),
           (0, "bd", 0, 0.7, 0.75)]
    P["heart"] = groove(bar(34), bar(40), BAR, fig, hb, vel=(0.2, 0.62))
    # pizzicato: cellos pluck the bass on 1 and 3 (bars 8-51), violas answer in the build and swell
    pz_vc, pz_vla, t = [], [], 0.0
    for c, b, s_ in PLAN:
        for k in range(b):
            tb = t + bar(k)
            if bar(8) <= tb < bar(52):
                bp = s_[0] + (12 if s_[0] < 36 else 0)
                pz_vc += [N(tb, 3.0, float(bp), 0.55), N(tb + 4, 2.0, float(bp + 7), 0.4)]
            if bar(28) <= tb < bar(40):
                pz_vla += [N(tb + 3, 1.0, float(s_[2] + 12), 0.4), N(tb + 6, 1.0, float(s_[3] + 12), 0.38)]
        t += bar(b)
    P["pz_vc"], P["pz_vla"] = pz_vc, pz_vla
    return pr, P


def guitar_body(st, name, amount=0.8, seed=3):
    """The harp's strings through a guitar body (as sfxkit.guitar_body does for
    the giant guitar's strings), convolved circularly so the loop stays seamless."""
    tr = st.stems[name]
    ir = stereo_body("guitar", seed)
    x = tr.buf.astype(np.float64)
    wet = np.vstack([FX.convolve(x[c], ir[c], circular=True) for c in range(2)])
    wet *= np.sqrt(np.mean(x ** 2) / (np.mean(wet ** 2) + 1e-20))
    y = (1 - amount) * x + amount * wet
    # a nylon string's presence (the low strings are otherwise all body), the top rolled off
    tr.buf = FX.eq(y, ("peak", 200, 0.9, -1.5), ("peak", 1600, 0.8, 2.5), ("hs", 5000, 0.7, -3.0), ("lp", 9000, 0.7),
                   circular=True).astype(np.float32)


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.025))
    S = lambda notes, seed, j=0.012: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.4), (sec(8), 0.45), (sec(16), 0.5), (sec(24), 0.56), (sec(28), 0.64), (sec(31.5), 0.72),
                 (sec(33), 0.82), (sec(36), 0.92), (sec(37.5), 0.97), (sec(39.5), 0.86), (sec(40.5), 0.62),
                 (sec(44), 0.5), (sec(48), 0.44), (LOOP, 0.4)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.3, "swell": 0.12, "taper": 2.0}

    # the guitar (harp strings, a little room so they bloom, then the guitar body)
    st.stem("guitar", {"concert": 0.62, "chamber": 0.2}, depth=0.45)
    gt = S(P["guitar"], 1, 0.01)
    for n in gt:
        n.v = float(n.v * (0.85 + 0.4 * arc(n.t)))
    st.play("guitar", gt, "harp", seed=1, gain_db=2, release=1.0, pan=0.08, width=0.6)
    guitar_body(st, "guitar", 0.8, seed=3)

    oc_dyn = Curve([(0, 0.5), (sec(8), 0.5), (sec(10), 0.6), (sec(14), 0.55), (sec(16), 0.45), (sec(19), 0.55),
                    (sec(23), 0.5), (sec(25), 0.52), (sec(29), 0.62), (sec(31.5), 0.6), (sec(32), 0.5),
                    (sec(50), 0.45), (sec(53), 0.55), (LOOP, 0.5)], period=LOOP)
    st.play("ocarina", S(P["ocarina"], 2, 0.0), "ocarina", seed=2, dyn=oc_dyn, gain_db=9, slide=0.09,
            shape={"attack": 0.15, "swell": 0.15, "taper": 1.5}, lag=0.02)
    st.play("solo_violin", S(P["vn_cell"], 3), "solo_violin", seed=3,
            dyn=Curve([(sec(15.8), 0.4), (sec(18), 0.52), (sec(21), 0.52), (sec(22.8), 0.4)]), gain_db=3,
            shape=shape, legato=True, slide=0.1, lag=0.02, layer_bias=-0.15)
    vdyn = Curve([(sec(24), 0.45), (sec(28), 0.55), (sec(31.5), 0.62), (sec(33), 0.7), (sec(36), 0.8),
                  (sec(37.5), 0.85), (sec(39.5), 0.72), (sec(40.6), 0.5)])
    st.play("solo_violin", S(P["vn_line"], 4), "solo_violin", seed=4, dyn=vdyn, gain_db=3, shape=shape,
            legato=True, slide=0.11, lag=0.02)
    st.play("flutes", S(P["fl_swell"], 11), "flute", seed=11,
            dyn=Curve([(sec(31.6), 0.45), (sec(33), 0.58), (sec(37.5), 0.7), (sec(39.5), 0.6), (sec(40.6), 0.4)]),
            gain_db=0, shape=shape, lag=0.02)
    hdyn = Curve([(sec(28), 0.3), (sec(31), 0.45), (sec(33), 0.55), (sec(37.5), 0.7), (sec(39.5), 0.6),
                  (sec(40.3), 0.35)])
    st.play("horns", S(P["horns"], 12), "horns", seed=12, dyn=hdyn, gain_db=-5,
            shape={"attack": 0.6, "swell": 0.2, "taper": 2.5}, lag=0.03)
    st.play("horns", S(P["hn_sigh"], 13), "horns", seed=13,
            dyn=Curve([(sec(44), 0.4), (sec(44.6), 0.5), (sec(46), 0.32)]), gain_db=-3,
            shape={"attack": 0.5, "swell": 0.2, "taper": 3.0}, lag=0.03)

    # the marimba, softly rolled, the mallets' click rounded off
    mr = S(P["marimba_roll"], 6, 0.006)
    for n in mr:
        n.v = float(n.v * (0.8 + 0.4 * arc(n.t)))
    st.play("marimba", mr, "marimba", seed=6, gain_db=-9, humanize_v=0.08)
    mb = st.stems["marimba"]
    mb.buf = FX.eq(mb.buf.astype(np.float64), ("lp", 2600, 0.7), circular=True).astype(np.float32)

    st.play("organ", S(P["org_ped"], 7, 0.0), "organ_soft_pedal", seed=7, dyn=arc, gain_db=-6)
    st.play("organ", S(P["org"], 8, 0.0), "organ_soft", seed=8,
            dyn=Curve([(sec(28), 0.22), (sec(32), 0.45), (sec(37.5), 0.62), (sec(40), 0.45), (sec(42.2), 0.2)]),
            gain_db=-14)
    st.play("organ", S(P["org_full"], 14, 0.0), "organ", seed=14,
            dyn=Curve([(sec(34), 0.2), (sec(37.5), 0.6), (sec(39.5), 0.5), (sec(40.3), 0.2)]), gain_db=-17)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08, circular=True).astype("float32")

    pv = S(P["pz_vc"], 15, 0.008)
    for n in pv:
        n.v = float(n.v * (0.7 + 0.45 * arc(n.t)))
    st.play("cellos_pizz", pv, "cellos_pizz", seed=15, gain_db=1, seat="cellos")
    pa = S(P["pz_vla"], 16, 0.008)
    for n in pa:
        n.v = float(n.v * (0.7 + 0.45 * arc(n.t)))
    st.play("violas_pizz", pa, "violas_pizz", seed=16, gain_db=-1, seat="violas")

    # the heartbeat under the height of the swell
    H = P["heart"]
    st.play("timpani", S(H.get("timp", []), 17, 0.004), "timpani", seed=17, gain_db=1)
    st.play("drums", S(H.get("bd", []), 18, 0.003), "bass_drum", seed=18, gain_db=-6, seat="bass_drum")

    # the far bell: the gong, struck very gently, deep in the hall
    st.play("gong", S(P["bell"], 9, 0.0), "gong", seed=9, gain_db=11, tail=16.0, depth=0.95)
    gb = st.stems["gong"]
    gb.buf = FX.eq(gb.buf.astype(np.float64), ("lp", 2800, 0.7), circular=True).astype(np.float32)

    out = st.render({"concert": {"seed": 81}, "chamber": {"seed": 82}, "cathedral2": {"seed": 83}}, warmth=0.35)
    return finish_loop("music", "marigold", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "G major",
                             "instrument": "guitar"})


if __name__ == "__main__":
    render()
