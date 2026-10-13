"""VIII. The Marigold Garden — "Remember Me" (rescored: Glass, for a quiet
altar on the Day of the Dead, and the walk's one great yearning swell, in
light).

A place of remembrance, revered: an ofrenda glowing in candlelight,
marigolds, papel picado, a giant guitar. It begins as a vigil at night,
intimate and still - nothing of the fiesta - and grows into the emotional
high point of the walk before the Wishing Tree, then pulls back to the
altar so the loop's return feels like a memory coming back.

The altar is acoustic. A Spanish classical guitar (FreePats, CC0: a real
guitar, sampled note by note; a repeated note is never the same pluck
twice) picks a broken chord in eighths, Glass's process: one note of the
figure changes at a time, so the bittersweet turn happens inside it - C
major 7 becomes C minor 6 when the E slips to E-flat. The progression is an
eight-bar cycle (G, Em7, Cmaj9, G/B, Cm6, Cm6, G/D, D7sus4) over a soft
organ pedal on G, the church at the edge of the cemetery; a far bell (the
gong, struck very gently) marks the turn of the loop, and a marimba,
softly rolled, blooms on the C minor 6 as the cycles come round.

The Ember's cell (G E D B D) is the seed of every line. An ocarina - a clay
flute, as Mesoamerica has always made them - breathes it augmented; eight
bars later a voice not of this world answers it (a canon at the cycle),
under the ocarina's suspensions: a synth, singing.

The swell is electronic, in the manner of Cliff Martinez (his ways, none
of his tunes): the sky opening over the altar. A warm analog lead SINGS the
line - gliding into each note as a voice does, its vibrato growing on the
long notes, its filter blooming while a note is held - with a glass voice
(the cristal baschet's colour) in unison. Under it the guitar's figure
turns to light: a soft plucked synth joins the guitar's slow triplets (a
12/8 pulse inside the 4/4, the 1950s ballad's) and takes them over through
a long echo while the guitar falls silent; detuned analog pads open slowly
from dark to bright, and a glassy halo floats above. The harmony turns
plain and aching, the 1950s ballad's: I - vi - IV - V, then the heartache
(vi, its own dominant B7, IV, V), and at the climax vi - E7 - ii - V, then
IV turning to the borrowed minor iv. From bar 28 the synth pulses the
chords in triplets, the 12/8 ballad's pulse, accented, with every other
change PUSHED - struck on the last triplet before the bar, the downbeat
held over - and a warm analog bass beats under it like a heart (the root,
a quick triplet pickup, the fifth, an approach into the next chord), a soft
electronic heartbeat doubling it at the height. The line - grown from the
cell's leaps, the sixths G-E and B-G, the D-sharp leaning on E, then an
octave - climbs to a high D that is HELD while C major turns to C minor
beneath it, and falls away by step, C B A, to G. Then the light withdraws: the guitar's eighths
return, the pads close, the horns sigh E-flat to D on the C minor 6, and
the ocarina remembers the cell once more and leaves its last leap, G up to
E, hanging over D sus, into the loop.
G major with a borrowed C minor, 4/4 at 72, 56 bars = 186.7 s.

  bars  0-7   the altar: the guitar's cycle, organ pedal, far bell; a marimba roll
  bars  8-15  ocarina: the cell augmented; cello pizzicati
  bars 16-23  the singing synth: the cell (canon), dark and soft; the ocarina's suspensions above;
              the pads begin (20)
  bars 24-31  the build: G Em C D7, Em B7 C D7; the guitar's triplets (12/8 feel), the synth pluck
              joining them (24); the pulse and the bass (28); the pads opening; soft horns (30)
  bars 32-39  the swell: Em E7 Am D7, C - Cm under the held high D, G/D D7; heartbeat (34),
              glass halo
  bars 40-47  the resolution: the guitar's eighths return, the pads close; the horns' sigh
  bars 48-55  the quiet altar; the ocarina's last leap left hanging
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock, voicing
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords
from hlaudio import process as PR
from hlaudio import effects as FX, electro as EL, analog as AN
from hlaudio import festival  # noqa: F401  (seats and tone chains of the ocarina and the gong)
from hlaudio.beats import groove, drum_pitch
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
# the build, the 1950s ballad's progressions: I - vi - IV - V, then the heartache, vi - its own
# dominant (B7) - IV - V
BUILD_CYC = [("G", 1, [43, 50, 55, 59]), ("Em", 1, [40, 52, 55, 59]), ("C", 1, [48, 52, 55, 60]),
             ("D7", 1, [38, 50, 54, 60]), ("Em", 1, [40, 52, 55, 59]), ("B7", 1, [47, 51, 54, 57]),
             ("C", 1, [48, 52, 55, 60]), ("D7", 1, [38, 50, 54, 60])]
# the climax (the bridge): vi - E7 - ii - V, then IV turning to the borrowed minor iv under the held
# high note, home through I over its fifth and V
BRIDGE = [("Em", 1, [40, 52, 55, 59]), ("E7", 1, [40, 50, 56, 59]), ("Am", 1, [45, 52, 57, 60]),
          ("D7", 1, [38, 50, 54, 60]), ("C", 1, [48, 52, 55, 60]), ("Cm", 1, [48, 51, 55, 60]),
          ("G/D", 1, [38, 50, 55, 59]), ("D7", 1, [38, 50, 54, 60])]
PLAN = CYC * 3 + BUILD_CYC + BRIDGE + CYC * 2
TRIPLET = (24, 40)     # the build and the climax move in triplet eighths: a slow 12/8 inside the 4/4
FIG = [0, 1, 2, 3, 2, 1, 3, 2]          # thumb on the bass, fingers above, 3+3+2
ACC = [1.0, .7, .8, .9, .72, .78, .88, .74]
ROLL = {"Cm6": [63, 67, 69, 72]}
# the swell's chords, voiced by hand (the third and the seventh always there): the pulse close in the
# middle, the pads a little lower, the bass's root
PULSE = {"G": [62, 67, 71], "Em": [64, 67, 71], "C": [64, 67, 72], "D7": [62, 66, 72], "B7": [63, 66, 69, 71],
         "E7": [62, 64, 68, 71], "Am": [64, 69, 72], "Cm": [63, 67, 72], "G/D": [62, 67, 71], "Gadd9": [62, 67, 71]}
PAD = {"G": [55, 59, 62, 67], "Em": [55, 59, 64, 67], "C": [55, 60, 64, 67], "D7": [54, 57, 60, 62],
       "B7": [54, 57, 59, 63], "E7": [56, 59, 62, 64], "Am": [57, 60, 64, 69], "Cm": [55, 60, 63, 67],
       "G/D": [55, 59, 62, 67]}
ROOT = {"G": 43, "Em": 40, "C": 48, "D7": 38, "B7": 47, "E7": 40, "Am": 45, "Cm": 48, "G/D": 38, "Gadd9": 43}
ACC12 = [1.0, 0.5, 0.62, 0.82, 0.5, 0.62, 0.92, 0.5, 0.62, 0.82, 0.5, 0.7]   # the 12/8 pulse's accents
PUSH = (29, 31, 33, 35, 37)  # bars whose last triplet already strikes the next chord (its downbeat held over)
# the analog bass under the pulse: warm, round, a little bite as each note starts
HEARTBASS = AN.Patch(oscs=[("saw", 0.0, 0, 1.0, 0.5), ("pulse", 4.0, 0, 0.45, 0.45)], drift=2.0, cutoff=170.0,
                     res=0.12, env_oct=1.3, keytrack=0.3, vel_bright=0.9, a=0.006, d=0.45, s=0.55, r=0.16,
                     fa=0.003, fd=0.22, fs=0.0, fr=0.15, drive=1.3, sat=1.2, pre=0.45, fmax=2200.0, level=0.5,
                     vel_db=12.0)

# the long line (pitch, eighths), all from the cell's leaps (the sixths G-E, D-B, E-flat-C, and the
# octave): it climbs by aching leaps through the build, arrives at a high D HELD across C major
# turning to C minor, and falls away by step to G
BUILD = [(67, 2), (76, 4), (74, 2),            # 24 G:      G - E D     (the cell's sixth)
         (71, 4), (74, 2), (76, 2),            # 25 Em7:    B - D E
         (79, 6), (76, 2),                     # 26 Cmaj9:  G - - E
         (74, 4), (72, 2), (69, 2),            # 27 D7:     D - C A
         (71, 2), (79, 4), (76, 2),            # 28 Em:     B G - E        (a sixth up, the heart)
         (78, 4), (75, 4),                     # 29 B7:     F# - D# -      (leaning on E)
         (76, 2), (84, 4), (83, 2),            # 30 C:      E C - B        (the sixth again, higher)
         (81, 4), (78, 2), (74, 2)]            # 31 D7:     A - F# D ...
SWELL = [(83, 4), (81, 2), (79, 2),            # 32 Em:     B - A G
         (76, 2), (80, 2), (83, 4),            # 33 E7:     E G# B -
         (84, 4), (83, 2), (81, 2),            # 34 Am:     C - B A
         (69, 2), (81, 4), (84, 2),            # 35 D7:     A, the octave up to A, C
         (86, 16),                             # 36-37:     D, HELD: C major, then C minor beneath it
         (84, 4), (83, 4),                     # 38 G/D:    C - B -       (the fourth falling to the third)
         (81, 6), (79, 2),                     # 39 D7:     A - - G       (home a beat early)
         (79, 6)]                              # 40 G:      G, home
# where the singer breathes: after these notes of BUILD + SWELL (the ends of bars 27, 31 and 33)
BREATHS = (10, 21, 27)
LIGHT = (28, 30)       # the synth pluck takes the triplets over from the guitar between these bars


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
    # the guitar: the bass moves with the chord; above it ONE string changes per half bar
    gt, cur, t, bnum = [], list(PLAN[-1][2]), 0.0, 0

    def step(s):
        if cur[1:] != s[1:]:
            cand = [(s[j] in cur, abs(a - g), j) for j, (a, g) in enumerate(zip(cur, s)) if j > 0 and a != g]
            j = min(cand)[2]                               # prefer a change that makes no unison
            cur[j] = s[j]
    for c, b, s in PLAN:
        for k in range(b):
            if TRIPLET[0] <= bnum < TRIPLET[1]:
                # the ballad's slow triplets: bass, then the strings above, three to a beat
                for beat in range(4):
                    if beat == 0:
                        cur[:] = s
                    for j, idx in enumerate((0 if beat in (0, 2) else 1, 2, 3)):
                        v = 0.38 * (1.0 if j == 0 else 0.72) * (1.08 if beat == 0 else 1.0)
                        gt.append(N(t + 2 * beat + j * 2 / 3, 2.2 if idx == 0 else 1.6, float(cur[idx]), v))
            else:
                for i, idx in enumerate(FIG):
                    if i == 0:
                        cur[0] = s[0]
                    if i in (0, 4):
                        step(s)
                    gt.append(N(t + i, 3.0 if idx == 0 else 2.4, float(cur[idx]), 0.42 * ACC[i]))
            t += BAR
            bnum += 1
    r = np.random.default_rng(8)
    for n in gt:
        if n.p < 38:          # a guitar's lowest string is E (D when dropped): C and B go up an octave
            n.p += 12
        # no two plucks of a note alike: now and then a neighbouring note's recording, the nail a few
        # milliseconds into the pluck, a few cents
        n.x.update(nb=int(r.choice([0, 0, 1, -1])), skip=float(r.uniform(0.0, 0.004)),
                   detune=float(r.normal(0, 2.0)))
    # the synth pluck: the triplets an octave up, joining the guitar (24) and handing over to the pulse (29-31)
    pluck = []
    for n in gt:
        if bar(TRIPLET[0]) <= n.t < bar(31):
            w = float(np.interp(n.t, [bar(24), bar(26), bar(28), bar(29), bar(31)], [0.45, 0.75, 1.0, 1.0, 0.0]))
            pluck.append(N(n.t, n.d, n.p + 12, n.v * w))
    P["pluck"] = pluck
    # the pulse: the chords in triplets, accented (the 12/8 ballad's), every other change pushed
    pulse, trip = [], 2 / 3
    for b in range(28, 40):
        sym, nxt = PLAN[b][0], PLAN[b + 1][0]
        w = float(np.interp(b, [28, 30], [0.45, 1.0]))
        for q in range(12):
            if q == 0 and b - 1 in PUSH:
                continue                                   # struck already, on the last triplet
            if q == 11 and b in PUSH:
                pulse += [N(bar(b) + q * trip, 2 * trip, float(p), 0.95 * w) for p in PULSE[nxt]]
            else:
                pulse += [N(bar(b) + q * trip, 0.6, float(p), ACC12[q] * w) for p in PULSE[sym]]
    P["pulse"] = pulse
    # the bass, like a heart: the root, a quick pickup on the last triplet of beat 2, the fifth on 3, and an
    # approach from below into the next chord (or, where the pulse pushes, the next root itself, early)
    bass = []
    for b in range(28, 40):
        sym, nxt = PLAN[b][0], PLAN[b + 1][0]
        r, r2 = ROOT[sym], ROOT[nxt]
        fifth = r + 7 if r + 7 <= 50 else r - 5
        w = float(np.interp(b, [28, 30], [0.6, 1.0]))
        if not (b - 1 in PUSH):
            bass.append(N(bar(b), 2 * trip * 1.3, float(r), 1.0 * w))
        bass += [N(bar(b) + 5 * trip, trip * 0.9, float(r), 0.55 * w), N(bar(b) + 6 * trip, 2 * trip * 1.2, float(fifth), 0.8 * w)]
        if b in PUSH:
            bass.append(N(bar(b) + 11 * trip, 3 * trip * 1.3, float(r2), 0.95 * w))
        else:
            bass.append(N(bar(b) + 11 * trip, trip * 0.9, float(r2 - 1), 0.62 * w))
    bass.append(N(bar(40), 4.0, float(ROOT["G"]), 0.85))
    P["bass"] = bass
    # ... while the guitar falls silent (28-30) until its eighths return at 40
    out = []
    for n in gt:
        if bar(LIGHT[0]) <= n.t < bar(LIGHT[1]):
            n.v *= 1 - 0.85 * (n.t - bar(LIGHT[0])) / bar(LIGHT[1] - LIGHT[0])
        elif bar(LIGHT[1]) <= n.t < bar(TRIPLET[1]):
            continue
        out.append(n)
    P["guitar"] = out
    # the ocarina: the cell augmented (8-14); its suspensions above the singer's canon (16-23)
    oc = PR.realize(PR.cell("P"), M, 7, bar(8), [8, 8, 8, 8, 12], vel=0.55)            # G4 E5 D5 B4 D5
    sus = PR.fit([N(bar(16), 8, 83.0, 0.48), N(bar(17), 8, 83.0, 0.5), N(bar(18), 6, 83.0, 0.52),
                  N(bar(18) + 6, 2, 81.0, 0.48), N(bar(19), 8, 81.0, 0.5), N(bar(20), 8, 79.0, 0.5),
                  N(bar(21), 8, 81.0, 0.52), N(bar(22), 8, 83.0, 0.5), N(bar(23), 8, 84.0, 0.46)], pr)
    # the coda (50-55): the cell remembered, its last leap left hanging over D sus
    coda = line([(67, 8), (76, 8), (74, 10), (72, 6), (71, 6), (67, 2), (76, 6)], bar(50), vel=0.5)
    for ln in (oc, sus, coda):
        breathe(ln)
    sus[-1].d -= 0.6
    P["ocarina"] = oc + sus + coda
    # the singer: the cell (16-21, a canon at the cycle), then the long line, breathing between phrases
    P["cell"] = PR.realize(PR.cell("P"), M, 7, bar(16), [8, 8, 8, 8, 14], vel=0.42)    # G4 E5 D5 B4 D5
    sing = line(BUILD, bar(24), vel=0.55) + line(SWELL, bar(32), vel=0.7)
    for i in BREATHS:
        sing[i].d -= 0.9
    P["sing"] = sing
    # the pads: the harmony, three voices in the middle, from bar 20 until the light has gone (44)
    pads, prev = [], None
    for (t0, d, sym) in pr:
        if bar(20) <= t0 < bar(44):
            vc = PAD.get(sym) or voicing(sym, 55, 71, 3, prev)
            prev = vc
            pads += [N(t0, d + 0.5, float(p), 0.5) for p in vc]
    P["pads"] = pads
    # the horns: soft and low under the end of the build and the swell, then their sigh (E-flat to D)
    # on C minor 6
    P["horns"] = sustain_chords(pr, 50, 62, 2, vel=0.55, overlap=0.3, start=bar(30), end=bar(40))
    P["hn_sigh"] = [N(bar(44), 8, 63.0, 0.5), N(bar(45), 8, 62.0, 0.46)]
    # the marimba: soft rolls on C minor 6 as the cycles come round
    rolls = []
    for b0, nb, v in ((4, 2, 0.24), (20, 2, 0.28), (44, 2, 0.28), (52, 2, 0.22)):
        rolls += roll(ROLL["Cm6"], bar(b0), bar(nb) - 0.5, v=v, seed=b0)
    P["marimba_roll"] = rolls
    # the organ: a soft pedal on G at the altar (the sub-bass takes the bridge's roots)
    P["org_ped"] = [N(bar(b), bar(8) + 0.3, 43.0, 0.45) for b in list(range(0, 32, 8)) + list(range(40, BARS, 8))]
    # a slow glassy halo over the climax: the chords' high upper notes, breathing in
    P["halo"] = [N(bar(32), bar(2) + 1, 78.0, 0.32), N(bar(32), bar(2) + 1, 83.0, 0.28),
                 N(bar(34), bar(2) + 1, 79.0, 0.34), N(bar(34), bar(2) + 1, 84.0, 0.3),
                 N(bar(36), bar(2) + 1, 79.0, 0.36), N(bar(36), bar(2) + 1, 86.0, 0.32),
                 N(bar(38), bar(2) + 2, 81.0, 0.32), N(bar(38), bar(2) + 2, 86.0, 0.28)]
    # the far bell at the turn of the loop
    P["bell"] = [N(bar(0), 16.0, 50.0, 0.3)]
    # a soft electronic heartbeat under the height of the swell (bars 34-39), with the bass: lub (the last
    # triplet of beat 2) - DUB (beat 3), and the downbeat
    hb = Curve([(bar(34), 0.0), (bar(34.5), 0.2), (bar(35.5), 0.5), (bar(36.5), 0.85), (bar(37.5), 1.0),
                (bar(38.5), 0.7), (bar(39.4), 0.25), (bar(39.9), 0.0)])
    lo = drum_pitch(pr, 38, 49)
    fig = [(0, "beat", lo, 0.85, 0.0), (10 / 3, "beat", lo, 0.45, 0.3), (4, "beat", lo, 0.72, 0.1)]
    P["heart"] = groove(bar(34), bar(40), BAR, fig, hb, vel=(0.2, 0.62))
    # pizzicato: cellos pluck the bass on 1 and 3 (bars 8-27 and 40-51)
    pz_vc, t = [], 0.0
    for c, b, s_ in PLAN:
        for k in range(b):
            tb = t + bar(k)
            if bar(8) <= tb < bar(28) or bar(40) <= tb < bar(52):
                bp = s_[0] + (12 if s_[0] < 36 else 0)
                pz_vc += [N(tb, 3.0, float(bp), 0.55), N(tb + 4, 2.0, float(bp + 7), 0.4)]
        t += bar(b)
    P["pz_vc"] = pz_vc
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.025))
    S = lambda notes, seed, j=0.012: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.4), (sec(8), 0.45), (sec(16), 0.5), (sec(24), 0.56), (sec(28), 0.64), (sec(31.5), 0.72),
                 (sec(33), 0.82), (sec(36), 0.92), (sec(37.5), 0.97), (sec(39.5), 0.86), (sec(40.5), 0.62),
                 (sec(44), 0.5), (sec(48), 0.44), (LOOP, 0.4)], period=LOOP)
    # how far the sky has opened: the pads' and the pluck's filters, the singer's brightness
    light = Curve([(0, 0.0), (sec(20), 0.0), (sec(24), 0.15), (sec(28), 0.32), (sec(32), 0.55), (sec(35), 0.75),
                   (sec(36.5), 0.92), (sec(38), 1.0), (sec(39.5), 0.75), (sec(41), 0.4), (sec(44), 0.1),
                   (LOOP, 0.0)], period=LOOP)
    st = Stage(LOOP, circular=True)

    # the guitar, a little to the left and back, a small room so it blooms
    st.stem("guitar", {"concert": 0.4, "chamber": 0.14}, depth=0.4)
    gt = S(P["guitar"], 1, 0.01)
    for n in gt:
        n.v = float(n.v * (0.85 + 0.4 * arc(n.t)))
    st.play("guitar", gt, "nylon", seed=1, gain_db=0, release=0.6, pan=-0.12, width=0.5)

    # the singer: the analog lead, near and centre, through a slow chorus, a long echo and the hall's
    # shimmer; the glass voice in unison a little behind it
    vdyn = Curve([(sec(16), 0.36), (sec(19), 0.44), (sec(22), 0.4), (sec(24), 0.5), (sec(28), 0.58),
                  (sec(31.5), 0.66), (sec(33), 0.72), (sec(35.5), 0.8), (sec(36), 0.86), (sec(37.5), 0.92),
                  (sec(39), 0.78), (sec(40.5), 0.6)])
    sg = S(P["cell"] + P["sing"], 4, 0.01)
    for n in sg:
        n.v = float(np.clip(vdyn(n.t) * (1 + 0.012 * (n.p - 76)), 0.05, 1.0))
    ld = st.stem("lead", {"concert": 0.42, "shimmer:cathedral2": 0.16}, depth=0.22)
    AN.sing(ld, sg, AN.SINGER, gain=1.0, seed=4, glide=0.17, vib=0.17, bloom=0.8,
            sweep=lambda t: 0.8 + 0.45 * light(t))
    lb = ld.buf.astype(np.float64)
    lb = FX.chorus(lb, rate=0.28, depth_ms=2.5, base_ms=11.0, mix=0.35, circular=True, seed=4)
    lb = lb + FX.echo(lb, clk.s(2), fb=0.3, mix=0.16, lp=2800, circular=True)
    ld.buf = FX.eq(lb, ("hp", 140, 0.7), circular=True).astype(np.float32)
    lg = st.stem("lead_glass", {"concert": 0.5, "shimmer:cathedral2": 0.3}, depth=0.45)
    EL.glass_line(lg, sg, gain=0.24, seed=5, glide=0.22, attack=0.5, release=3.0, bright=0.6, vib=0.004,
                  breath=0.08)

    # the synth pluck: the guitar's triplets turned to light, through an echo a beat long
    pk = st.stem("pluck", {"concert": 0.5}, depth=0.45)
    EL.arp(pk, S(P["pluck"], 6, 0.006), gain=0.9, seed=6, cutoff=lambda t: 900 + 2000 * light(t), res=1.3,
           decay=0.4, shape=0.3, pan=0.1, pan_wobble=0.3)
    pb = pk.buf.astype(np.float64)
    pk.buf = (pb + FX.echo(pb, clk.s(2), fb=0.32, mix=0.3, lp=2600, circular=True)).astype(np.float32)

    # the pads, opening from dark to bright with the sky; kept above the bass's mud
    pd = st.stem("pads", {"concert": 0.6}, depth=0.6)
    pn = S(P["pads"], 7, 0.0)
    for n in pn:
        n.v = float(0.35 + 0.4 * light(n.t))
    EL.pad(pd, pn, gain=0.9, seed=7, voices=5, detune=10.0, cutoff=700.0, res=0.6, attack=1.6, release=3.0,
           curve=light)
    pp = pd.buf.astype(np.float64)
    pp = FX.chorus(pp, rate=0.2, depth_ms=3.0, base_ms=14.0, mix=0.35, circular=True, seed=7)
    pd.buf = FX.eq(pp, ("hp", 170, 0.7), circular=True).astype(np.float32)

    # the pulse: the chords in triplets, a soft synth, close and dry-ish (no echo to blur the rhythm)
    pl = st.stem("pulse", {"concert": 0.42, "chamber": 0.12}, depth=0.35)
    pu = S(P["pulse"], 10, 0.004)
    for n in pu:
        n.v = float(np.clip(n.v * (0.55 + 0.5 * arc(n.t)), 0.03, 1.0))
    EL.arp(pl, pu, gain=0.24, seed=10, cutoff=lambda t: 1100 + 1700 * light(t), res=1.0, decay=0.26, shape=0.35,
           pan=0.0, pan_wobble=0.18)
    pl.buf = FX.eq(pl.buf.astype(np.float64), ("hp", 160, 0.7), circular=True).astype(np.float32)
    # the bass under it, and the heartbeat: near
    bs = st.stem("bass", {"concert": 0.15}, depth=0.2)
    bn = S(P["bass"], 11, 0.004)
    for n in bn:
        n.v = float(np.clip(n.v * (0.6 + 0.45 * arc(n.t)), 0.03, 1.0))
    AN.play(bs, bn, HEARTBASS, gain=1.0, seed=11)
    bs.buf = FX.eq(bs.buf.astype(np.float64), ("hp", 35, 0.7), circular=True).astype(np.float32)
    hs = st.stem("heart", {"concert": 0.2}, depth=0.25)
    EL.sub_pulse(hs, S(P["heart"].get("beat", []), 17, 0.004), gain=0.65, decay=0.32, drive=1.6)

    oc_dyn = Curve([(0, 0.5), (sec(8), 0.5), (sec(10), 0.6), (sec(14), 0.55), (sec(16), 0.45), (sec(19), 0.55),
                    (sec(23), 0.5), (sec(25), 0.52), (sec(29), 0.62), (sec(31.5), 0.6), (sec(32), 0.5),
                    (sec(50), 0.45), (sec(53), 0.55), (LOOP, 0.5)], period=LOOP)
    st.play("ocarina", S(P["ocarina"], 2, 0.0), "ocarina", seed=2, dyn=oc_dyn, gain_db=9, slide=0.09,
            shape={"attack": 0.15, "swell": 0.15, "taper": 1.5}, lag=0.02)
    hdyn = Curve([(sec(30), 0.3), (sec(32), 0.42), (sec(34), 0.5), (sec(37.5), 0.64), (sec(39.5), 0.55),
                  (sec(40.3), 0.32)])
    st.play("horns", S(P["horns"], 12), "horns", seed=12, dyn=hdyn, gain_db=-9,
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

    st.play("organ", S(P["org_ped"], 7, 0.0), "organ_soft_pedal", seed=7, dyn=arc, gain_db=-8)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08, circular=True).astype("float32")

    pv = S(P["pz_vc"], 15, 0.008)
    for n in pv:
        n.v = float(n.v * (0.7 + 0.45 * arc(n.t)))
    st.play("cellos_pizz", pv, "cellos_pizz", seed=15, gain_db=1, seat="cellos")

    gl = st.stem("glass", {"shimmer:cathedral2": 0.45, "concert": 0.5}, depth=0.7)
    EL.glass(gl, S(P["halo"], 22, 0.0), gain=0.26, seed=22, attack=2.2, release=4.0, bright=0.45, pan_spread=0.5)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4200, 0.7), circular=True).astype(np.float32)

    # the far bell: the gong, struck very gently, deep in the hall
    st.play("gong", S(P["bell"], 9, 0.0), "gong", seed=9, gain_db=11, tail=16.0, depth=0.95)
    gb = st.stems["gong"]
    gb.buf = FX.eq(gb.buf.astype(np.float64), ("lp", 2800, 0.7), circular=True).astype(np.float32)

    out = st.render({"concert": {"seed": 81}, "chamber": {"seed": 82}, "cathedral2": {"seed": 83},
                     "shimmer:cathedral2": {"seed": 84, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "marigold", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "G major",
                             "instrument": "guitar and synths"})


if __name__ == "__main__":
    render()
