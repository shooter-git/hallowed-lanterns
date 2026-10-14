"""VI. October Snow — "First Snow": impossibly, it begins to snow. The hush of
a snowy wood (its wind is the chapter's ambience, not the music); a music box turning in the
falling snow; a snowman in striped gourds raising his corn-cob mug in a
toast as you pass; and at the end the flakes slow, stop and begin to rise.

The way of the Marigold Garden (the stillness of Cliff Martinez, the turning
figure and the quiet beat of Ólafur Arnalds, a swell in the way of Hans
Zimmer; their ways, none of their tunes), made of the chapter's own sounds:
snowflakes ringing like tiny bells, a jazz
double bass that rings as it does on a concert stage (Meatbass); and the
winter's own percussion, played as an orchestra plays it, not a drum kit -
sleigh bells, a woodblock for the snowman's steps, the triangle, finger
cymbals, a bell tree for the rising flakes, a soft concert bass drum and a
mallet on the suspended cymbal, all real recordings.

A Lydian (its raised fourth, D-sharp, is the snow's glow), 4/4 at 72, the
walk's 3+3+2. The music box - the glockenspiel, the felt piano an octave
below - turns one figure (E A C# D#) and never changes it; everything else
keeps to the Lydian's notes, so nothing rubs against it. The Snow theme (A |
F# E C# | E, answered a step lower with the D-sharp, then climbing to B) is
the top voice of piano chords, never one instrument alone.

  bars  0-5   the hush: glass chords over the organ's far A; snowflakes ringing
  bars  6-13  the music box, the piano beside it; the double bass (10), ringing; the bass slides to
              F# and E
  bars 14-21  the theme in piano chords; the sleigh bells come in far off, softly on the 3+3+2's
              accents, a glint of the triangle every other bar (16), the finger cymbals answering
  bars 22-25  the snowman's toast: his steps on the woodblock, a bouncy pizzicato and staccato-clarinet
              lift, a stop - and the clink (the triangle with it), and a warm Lydian chord (B over A) on
              the horns
  bars 26-33  the rise: the theme's climb in the piano's octaves, tremolo strings walking forward, the
              organ, the horns, the sleigh bells shaking in eighths, a soft concert bass drum, a timpani
              roll into a timpani stroke (30), a cymbal swell drawing the air in and a soft mallet on the
              cymbal at the top; at the peak the bass lifts once, A to B - the Lydian light
  bars 34-37  the flakes rise: the bell tree, reversed piano and glockenspiel swelling upward, a harp
              sweeping up, a glass line climbing octave over octave; the triangle's last glints
  bars 38-47  the hush again: the music box alone, far and soft; snowflakes
48 bars = 160 s.

THE MIX MOVES (as the Marigold's): every voice has a near and a far seat and travels between them,
its own EQ and its own place across the field.
"""
import numpy as np

from hlaudio.core import SR, Track
from hlaudio.score import N, humanize, Clock, chord_pcs
from hlaudio.sampler import Curve
from hlaudio import sampler as SM, effects as FX, electro as EL
from hlaudio.orch import Stage, TONE
from hlaudio.piece import finish_loop

TITLE = "First Snow"
BAR = 8            # eighths
BARS = 48
BPM_UNIT = 144     # eighths per minute (quarter = 72)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 160 s

LYD = [69, 71, 73, 75, 76, 78, 80]                        # A B C# D# E F# G#
FIG = [88, 81, 85, 87, 85, 83, 88, 85]                    # the music box: E A C# D# C# B E C#
ACC = [1.0, .55, .6, .9, .55, .6, .85, .6]
BASS = [45] * 10 + [42, 42, 40, 40] + [45] * 8 + [45, 42, 45, 45] + [45] * 5 + [47, 47, 45] + [45] * 4 + [45] * 10
assert len(BASS) == BARS
# the hush's glass colours (two bars each): A major 7, A add 9, E over A, B over A
COLORS = [[81, 85, 88, 92], [81, 83, 88, 92], [80, 85, 87, 90], [78, 83, 87, 90]]
# the chords, bar by bar (the theme's own, its D major turned to B over A: all of them inside the Lydian)
CH = (["Amaj7"] * 6 + ["Aadd9"] * 4 + ["F#m7"] * 2 + ["Emaj7"] * 2 +
      ["A6add9", "Aadd9", "Emaj7/A", "Emaj7/A", "F#m7/A", "B/A", "Esus4/A", "Aadd9"] +
      ["Aadd9", "F#m7", "B/A", "B/A"] +
      ["F#m7/A", "B/A", "Esus4/A", "Aadd9", "F#m7/A", "B", "B", "Aadd9"] +
      ["E/A", "B/A", "E/A", "B/A"] + ["Amaj7"] * 2 + ["Aadd9"] * 2 + ["E/A"] * 2 + ["B/A"] * 2 + ["Amaj7"] * 2)
assert len(CH) == BARS
# the Snow theme (pitch, eighths) from its pickup; its climbing half
THEME = [(69, 2), (78, 4), (76, 2), (73, 2), (76, 6), (68, 2), (76, 4), (75, 2), (71, 2), (75, 6), (69, 2),
         (78, 4), (76, 2), (73, 2), (76, 2), (78, 2), (81, 4), (83, 4), (81, 2), (78, 2), (76, 8)]
CLIMB = [(78, 4), (76, 2), (73, 2), (76, 2), (78, 2), (81, 4), (83, 4), (81, 2), (78, 2), (76, 8)]
RIFF = [(0, 0), (1.5, 2), (3, 1), (4.5, 2), (6, 0), (7, 1)]           # the snowman's bounce
CELL = [(0, 2), (2, 2), (4, 1), (5, 1), (6, 2)]
CELL_PCS = [0, 9, 7, 4, 7]

VOICE_EQ = {
    "musicbox": [("hp", 500, 0.7), ("hs", 9000, 0.7, 1.0)],
    "piano": [("hp", 70, 0.7), ("peak", 260, 0.9, -3.0), ("peak", 2800, 0.9, 1.5), ("hs", 7000, 0.7, 2.0)],
    "glass": [("hp", 300, 0.7), ("hs", 6000, 0.7, 3.0)],
    "flakes": [("hp", 500, 0.7)],
    "bass": [("hp", 32, 0.7), ("peak", 75, 0.8, 1.5), ("peak", 250, 0.9, -2.0), ("peak", 700, 0.9, 1.5),
             ("hs", 4500, 0.7, -3.5)],
    "bells": [("hp", 500, 0.7), ("hs", 8000, 0.7, 1.0)],
    "steps": [("hp", 200, 0.7), ("peak", 1800, 1.0, 1.5)],
    "drum": [("hp", 35, 0.7), ("peak", 300, 0.9, -3.0)],
    "timp": [("hp", 50, 0.7), ("peak", 320, 0.9, -3.0), ("peak", 2500, 1.0, 2.0)],
    "roll": [("hp", 60, 0.7), ("peak", 300, 0.9, -2.5)],
    "riff": [("hp", 150, 0.7), ("peak", 3000, 0.9, 1.5)],
    "clarinet": [("hp", 150, 0.7), ("peak", 350, 0.9, -2.0), ("peak", 2500, 0.9, 1.5)],
    "horns": [("hp", 110, 0.7), ("peak", 300, 0.9, -3.0), ("peak", 1300, 1.0, 1.5)],
    "strings": [("hp", 200, 0.7), ("peak", 420, 0.9, -2.5), ("hs", 6000, 0.7, 3.0)],
    "organ": [("hp", 30, 0.7), ("peak", 300, 0.9, -3.0), ("hs", 5000, 0.7, 1.5)],
    "harp": [("hp", 200, 0.7), ("hs", 8000, 0.7, 1.5)],
    "climb": [("hp", 300, 0.7), ("hs", 6000, 0.7, 2.0)],
    "rise": [("hp", 250, 0.7), ("hs", 6000, 0.7, 2.0)],
    "cymbal": [("hp", 400, 0.7)],
}
# each voice's width (mid/side) and side (-1 left .. 1 right)
STAGE = {"musicbox": (1.2, 0.15), "piano": (1.1, 0.0), "glass": (1.7, 0.0), "flakes": (1.6, 0.0),
         "bells": (1.2, 0.0), "steps": (0.5, 0.2), "drum": (0.8, 0.0), "bass": (0.4, 0.05), "riff": (0.9, -0.3), "clarinet": (0.7, 0.3), "horns": (0.8, -0.3),
         "strings": (1.6, 0.1), "organ": (1.2, -0.2), "timp": (0.8, 0.25), "roll": (0.8, 0.2), "harp": (1.2, -0.25),
         "climb": (1.4, 0.0), "cymbal": (1.7, 0.0), "rise": (1.4, 0.0)}
ROOM_EQ = [("hp", 180, 0.7), ("peak", 400, 0.8, -2.0)]
HALL_EQ = [("hp", 240, 0.7), ("peak", 420, 0.8, -2.5), ("hs", 6000, 0.7, 1.0)]


def bar(b):
    return b * BAR


def C(pts):
    """A control curve over bars: [(bar, value), ...] (held before the first point and after the last)."""
    pts = list(pts) if len(pts) > 1 else [pts[0], (pts[0][0] + 1, pts[0][1])]
    return Curve([(b * BAR * 60 / BPM_UNIT, v) for b, v in pts])


def under(sym, top, n=2):
    """The n chord tones nearest below a top note (a hand's chord under the tune)."""
    pcs = chord_pcs(sym)[0]
    below = [p for p in range(top - 1, top - 13, -1) if p % 12 in pcs and p % 12 != top % 12]
    return sorted(below[:n])


def chords_under(spec, t0, vel, octave=False, hits=(0, 3, 6)):
    """A line as the top voice of piano chords, struck again on the 3+3+2's accents while a note lasts."""
    out, t = [], t0
    for p, d in spec:
        b = int(t // BAR)
        sym = CH[min(BARS - 1, b)]
        pos = t % BAR
        offs = [0] + [h - pos for h in hits if pos < h < pos + d]
        for k, o in enumerate(offs):
            notes = under(sym, p) + [p] + ([p - 12] if octave else [])
            out += [N(t + o, (d - o) + 0.4, float(q), (vel if k == 0 else vel * 0.7) * (1.0 if q == p else 0.75))
                    for q in notes]
        t += d
    return out


def score():
    P = {}
    r = np.random.default_rng(11)
    # the music box (6-33, softly again 40-45), and the piano doubling it an octave below (6-21)
    mb_bars = list(range(6, 34)) + list(range(40, 46))
    P["musicbox"] = [N(bar(b) + i, 1.6, float(p), (0.5 if b < 40 else 0.36) * ACC[i]) for b in mb_bars
                     for i, p in enumerate(FIG)]
    P["piano"] = ([N(bar(b) + i, 1.6, float(p - 12), 0.34 * ACC[i]) for b in range(8, 22) for i, p in enumerate(FIG)
                   if not (14 <= b < 22 and i in (0, 3, 6))] +
                  chords_under(THEME, bar(13) + 6, 0.5) +
                  chords_under(CLIMB, bar(26), 0.6, octave=True) +
                  chords_under([(p + 12, d) for p, d in CLIMB], bar(30), 0.66, octave=True))
    # the hush's glass colours, and a halo at the peak
    P["glass"] = [N(bar(b), BAR + 1, float(p), 0.42) for b in list(range(0, 6)) + list(range(38, BARS))
                  for p in COLORS[(b // 2) % 4][1:]]
    P["halo"] = [N(bar(b), 2 * BAR + 1, float(p), 0.4) for b in (30, 32) for p in (88, 92, 95)]
    # snowflakes: sparse random bells, the Lydian's notes high up
    fl = []
    for b in list(range(0, 14)) + list(range(38, BARS)):
        for k in range(16):
            if r.random() < 0.09:
                fl.append(N(bar(b) + k / 2 + r.uniform(-0.05, 0.05), 2.0, float(r.choice(LYD) + 22),
                            float(r.uniform(0.25, 0.45))))
    P["flakes"] = fl
    P["fcymb"] = [N(bar(b) + o, 3.0, 0.0, 0.4) for b, o in ((2, 3), (5, 6.5), (9, 1.5), (40, 5), (44, 2.5))]
    # the double bass (10-33), as a jazz bassist plays a ballad: two long notes a bar (the root, the fifth on
    # the 3+3+2's second accent), each blooming until the next stops the string; a third pluck pushes only in
    # the toast's bounce and the rise; the last before the flakes rise rings out. Plucked with the side of the
    # finger: a round start (the first milliseconds of the pluck left out), never the orchestra's snap. Low,
    # where a bassist plays (around the open A string): up an octave the strings are short and die at once
    bs = []
    for b in range(10, 34):
        if b == 24:
            continue
        rt = BASS[b] - 12
        fifth = rt + 7 if rt + 7 <= 42 else rt - 5
        push = b in (22, 23) or b >= 26
        notes = [N(bar(b), 3.0, float(rt), 0.72), N(bar(b) + 3, 3.0 if push else 5.0, float(fifth), 0.6)]
        if push:
            notes.append(N(bar(b) + 6, 8.0 if b == 33 else 2.0, float(rt), 0.52))
        for n in notes:
            n.x["skip"] = 0.012
        bs += notes
    P["bass"] = bs
    # the snowman's toast: the bounce (22-23), a stop on 24's downbeat, then the clink and the warm chord
    riff, clar = [], []
    for b in (22, 23):
        rt = BASS[b] + 24
        tones = [rt, rt + 3 if BASS[b] == 42 else rt + 4, rt + 7]
        riff += [N(bar(b) + o, 0.5, float(tones[i] + (12 if i == 2 and o == 4.5 else 0)), 0.6 + (0.15 if o in (0, 3, 6) else 0))
                 for o, i in RIFF]
        clar += [N(bar(b) + 5, 0.5, 80.0 if b == 22 else 78.0, 0.5), N(bar(b) + 5.5, 0.5, 81.0, 0.45),
                 N(bar(b) + 7, 0.5, 85.0, 0.55)]
    P["riff"], P["clarinet"] = riff, clar
    P["clink"] = [N(bar(24) + 2, 3.0, 99.0, 0.6), N(bar(24) + 2.06, 3.0, 104.0, 0.5)]
    P["toast"] = [N(bar(24) + 2, 2 * BAR - 2, float(p), 0.6) for p in (59, 63, 66, 71)]
    # the percussion, the winter's own, played as an orchestra plays it: (part, [notes])
    perc = {k: [] for k in ("sleigh", "triangle", "fcym", "wood", "drum", "crash", "belltree")}

    def hit(part, b, hits):
        perc[part] += [N(bar(b) + o, 0.5, 0.0, float(v)) for o, v in hits]
    for b in range(14, 34):
        if 14 <= b < 22:                                        # the theme: far sleigh bells, a glint now and then
            if b >= 16:
                hit("sleigh", b, [(0, 0.42), (3, 0.3), (6, 0.34)])
            if b % 2 == 0 and b >= 16:
                hit("triangle", b, [(0, 0.4)])
            if b in (17, 21):
                hit("fcym", b, [(6.5, 0.4)])
        elif b in (22, 23):                                     # the snowman's steps with the bounce
            hit("wood", b, [(o, 0.6 if o in (0, 3, 6) else 0.42) for o, _ in RIFF])
            hit("sleigh", b, [(0, 0.4), (6, 0.36)])
        elif b == 24:                                           # the stop; the triangle with the clink
            hit("triangle", b, [(2.04, 0.5)])
        elif b == 25:
            hit("wood", b, [(4.5, 0.4), (6, 0.5), (7, 0.36)])     # he sets off again
        elif 26 <= b < 30:                                      # the rise: the bells shake in eighths
            hit("sleigh", b, [(k, (0.5 if k in (0, 3, 6) else 0.32) * (0.8 + 0.06 * (b - 26))) for k in range(8)])
            hit("drum", b, [(0, 0.35 + 0.04 * (b - 26))])
            if b == 28:
                hit("triangle", b, [(0, 0.45)])
        else:                                                   # the peak
            hit("sleigh", b, [(k, 0.55 if k in (0, 3, 6) else 0.36) for k in range(8)])
            hit("drum", b, [(0, 0.5), (3, 0.34)])
            hit("triangle", b, [(0, 0.5)] + ([(6, 0.4)] if b % 2 else []))
    perc["crash"] = [N(bar(30), 6.0, 0.0, 0.5)]                 # a soft mallet on the cymbal at the peak
    perc["belltree"] = [N(bar(34) + 0.0, 4.0, 0.0, 0.55), N(bar(36) + 0.0, 4.0, 0.0, 0.5)]   # the flakes rise
    for b, o in ((34, 4), (35, 3), (36, 4), (37, 3), (37, 6)):
        perc["triangle"].append(N(bar(b) + o, 2.0, 0.0, 0.4))
    P["perc"] = perc
    # the rise: tremolo strings, the organ's chords, the horns, a timpani roll into a timpani stroke
    P["strings"] = [N(bar(b), BAR + 0.4, float(p), 0.5) for b in range(26, 34)
                    for p in sorted(q for q in range(66, 83) if q % 12 in chord_pcs(CH[b])[0])[-4:]]
    P["organ_ch"] = [N(bar(b), BAR + 0.4, float(p), 0.5) for b in range(28, 34) for p in under(CH[b], 76, 3)]
    P["horns"] = [N(bar(b), BAR + 0.4, float(p), 0.55) for b in range(30, 34) for p in under(CH[b], 66, 2)]
    P["pedal"] = [N(0, bar(BARS) - 0.2, 45.0, 0.5)]
    P["roll"] = [N(bar(28), bar(2) - 0.2, 45.0, 0.6)]
    P["timp"] = [N(bar(26), 2.0, 45.0, 0.6), N(bar(30), 2.0, 45.0, 0.82)]
    # the flakes rise: a harp sweeping up, a glass line climbing octave over octave
    P["harp"] = ([N(bar(24) + 0.5 + k * 0.12, 2.5, float(p), 0.32 + 0.02 * k) for k, p in enumerate([69, 73, 76, 81, 85, 88, 93])] +
                 [N(bar(35) + 4 + k * 0.22, 3.0, float(p), 0.35 + 0.02 * k)
                  for k, p in enumerate([69, 71, 73, 75, 76, 78, 80, 81, 83, 85, 87, 88, 90, 92, 93])])
    P["climb"] = [N(bar(34) + k * 2, 2.4, float(p), 0.5) for k, p in enumerate([69, 73, 76, 80, 81, 85, 88, 92, 93, 97, 100,
                                                                                 104, 105, 104, 105, 105])]
    P["chime"] = [N(bar(b) + o, d + 1.0, float(93 + pc), 0.42) for b in (13, 37) for (o, d), pc in zip(CELL, CELL_PCS)]
    return P


def render():
    P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.02))
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    st = Stage(LOOP, circular=True)

    def sampled(notes, inst, seed, tone=True, **kw):
        tmp = Track(LOOP, True)
        SM.play(tmp, notes, inst, seed=seed, **kw)
        if tone and inst in TONE:
            tn = TONE[inst]
            x = tmp.buf.astype(np.float64)
            if tn.get("soften"):
                x = FX.soften(x, tn["soften"], circular=True)
            tmp.buf = FX.eq(x, *tn["eq"], circular=True).astype(np.float32)
        return tmp

    def character(tmp, drive=1.5, lp=12000.0, wow=0.0007, seed=0):
        """Tape and a little valve: the attack rounded, the body warmed, a slow breath of wow."""
        x = FX.saturate(tmp.buf.astype(np.float64), drive=drive, mix=0.5)
        if wow:
            x = FX.wow_flutter(x, wow=wow, flutter=wow / 4, circular=True, seed=seed)
        tmp.buf = FX.eq(x, ("lp", lp, 0.7), ("hp", 30, 0.7), circular=True).astype(np.float32)
        return tmp

    def place(name, tmp, dist, gain_db, eq=None, near=(("room", 0.22),), far=(("concert", 0.8),), near_depth=0.12,
              far_depth=0.85):
        """A voice between its near seat and its far seat (`dist`, 0 near .. 1 far), at `gain_db`, with its own
        EQ, width and side."""
        x = tmp.buf.astype(np.float64)
        bands = VOICE_EQ.get(eq or name)
        if bands:
            x = FX.eq(x, *bands, circular=True)
        w_, side = STAGE.get(eq or name, (1.0, 0.0))
        if w_ != 1.0:
            x = FX.width(x, w_)
        if side:
            x = x * np.array([[np.cos((side + 1) * np.pi / 4)], [np.sin((side + 1) * np.pi / 4)]]) * 2 ** 0.5
        t = np.arange(x.shape[1]) / SR
        d = np.clip(dist(t), 0, 1)
        g = 10 ** (gain_db(t) / 20)
        st.stem(f"{name}~near", dict(near), depth=near_depth).mix((x * np.cos(d * np.pi / 2) * g).astype(np.float32))
        st.stem(f"{name}~far", dict(far), depth=far_depth).mix((x * np.sin(d * np.pi / 2) * g).astype(np.float32))

    # ---- the hush: glass colours, the organ's far A, snowflakes ringing (the wind is the ambience's)
    gl = Track(LOOP, True)
    EL.glass(gl, S(P["glass"], 1, 0.0), gain=0.48, seed=1, attack=1.6, release=3.5, bright=0.85, pan_spread=0.5,
             breath=0.25)
    EL.glass(gl, S(P["halo"], 2, 0.0), gain=0.3, seed=2, attack=1.0, release=3.0, bright=0.7, pan_spread=0.3)
    place("glass", gl, C([(0, 0.8), (6, 0.85), (30, 0.6), (34, 0.8), (38, 0.8)]), C([(0, 0.0), (30, 0.0), (38, 0.0)]),
          near=(("chamber", 0.35),), far=(("shimmer:cathedral2", 0.45), ("concert", 0.5)), near_depth=0.4, far_depth=0.8)
    org = sampled(S(P["pedal"], 3, 0.0), "organ_soft_pedal", 3, gain_db=-6,
                  dyn=C([(0, 0.4), (26, 0.5), (30, 0.7), (34, 0.45), (48, 0.4)]))
    org.mix(sampled(S(P["organ_ch"], 4, 0.0), "organ_soft", 4, gain_db=-10, dyn=C([(28, 0.3), (31, 0.6), (33.9, 0.6)])))
    place("organ", org, C([(0, 0.85), (28, 0.6), (31, 0.45), (34, 0.85)]), C([(0, -3.0), (30, 1.0), (34, -3.0), (48, -3.0)]),
          near=(("chamber", 0.3),), far=(("cathedral2", 0.7),), near_depth=0.5, far_depth=0.9)
    fl = sampled(S(P["flakes"], 5, 0.0), "glock", 5, gain_db=10, release=1.5)
    fl.mix(sampled(S(P["fcymb"], 6, 0.0), "finger_cymbal", 6, gain_db=8))
    place("flakes", fl, C([(0, 0.45)]), C([(0, -6.0), (14, -8.0), (38, -6.0)]), near=(("chamber", 0.3),),
          far=(("concert", 0.6), ("shimmer:cathedral2", 0.2)), near_depth=0.3, far_depth=0.7)

    # ---- the music box: close and small, further as the music grows, far and soft at the end
    mb = sampled(S(P["musicbox"], 7, 0.006), "glock", 7, gain_db=17, release=1.2)
    place("musicbox", mb, C([(6, 0.15), (14, 0.3), (26, 0.45), (34, 0.55), (40, 0.65)]),
          C([(6, -2.0), (14, -5.0), (26, -6.0), (33.9, -6.0), (40, -6.0), (46, -14.0)]),
          near=(("room", 0.3),), far=(("concert", 0.6), ("shimmer:cathedral2", 0.2)), near_depth=0.2, far_depth=0.7)

    # ---- the piano: beside you, the theme in its chords; back in the hall for the rise
    pt = sampled(S(P["piano"], 8, 0.007), "piano", 8, tone=False, gain_db=4, layer_bias=-0.05, release=1.0)
    pt.buf = FX.soften(pt.buf.astype(np.float64), 0.35, circular=True).astype(np.float32)
    pt = character(pt, drive=1.25, lp=13000, wow=0.0007, seed=8)
    place("piano", pt, C([(8, 0.3), (14, 0.3), (26, 0.45), (33.9, 0.5), (34, 0.35)]),
          C([(8, -4.0), (14, 0.0), (26, 1.0), (30, 2.0), (33.9, 2.0), (34.5, -6.0)]),
          near=(("room", 0.25), ("concert", 0.3), ("plate", 0.12)), far=(("concert", 0.65), ("plate", 0.25)),
          near_depth=0.3, far_depth=0.7)

    # ---- the double bass, the toast's bounce, the clink, the warm chord
    # the softer plucks (they ring longest), a rounded attack, and the even sustain of a bass through its amp
    bt = sampled(S(P["bass"], 9, 0.006), "upright", 9, gain_db=7, release=0.6, layer_bias=-0.2)
    x = FX.soften(bt.buf.astype(np.float64), 0.4, circular=True)
    bt.buf = FX.compress(x, thresh_db=-20.0, ratio=4.0, attack=0.02, release=0.4, circular=True).astype(np.float32)
    place("bass", bt, C([(10, 0.18)]), C([(10, -6.0), (14, -3.0), (26, -1.5), (33.9, -0.5)]),
          near=(("room", 0.25), ("chamber", 0.1)), far=(("concert", 0.45),), near_depth=0.15, far_depth=0.5)
    rt = sampled(S(P["riff"], 10, 0.006), "violins_pizz", 10, gain_db=0)
    place("riff", rt, C([(22, 0.2)]), C([(22, -2.0)]), near=(("room", 0.35),), far=(("concert", 0.5),),
          near_depth=0.2, far_depth=0.6)
    ct = sampled(S(P["clarinet"], 11, 0.006), "clarinet_stac", 11, gain_db=9)
    place("clarinet", ct, C([(22, 0.3)]), C([(22, -3.0)]), near=(("room", 0.3),), far=(("concert", 0.5),),
          near_depth=0.25, far_depth=0.6)
    st.play("glock", S(P["clink"], 12, 0.0), "glock", seed=12, gain_db=2, release=2.0)
    ht = sampled(S(P["toast"] + P["horns"], 13), "horns", 13, gain_db=-1,
                 dyn=C([(24.2, 0.4), (25, 0.68), (25.9, 0.5), (30, 0.45), (32, 0.62), (33.9, 0.55)]),
                 shape={"attack": 0.5, "swell": 0.2, "taper": 1.5}, lag=0.03)
    place("horns", ht, C([(24, 0.7), (25, 0.45), (26, 0.8), (30, 0.6), (33.9, 0.5)]),
          C([(24, -4.0), (25, 0.0), (26, -10.0), (30, -4.0), (33.9, 0.0), (34.4, -14.0)]),
          near=(("chamber", 0.3),), far=(("concert", 0.85),), near_depth=0.5, far_depth=0.9)

    # ---- the percussion: real recordings (VSCO's sleigh bells, triangle, bell tree, concert bass drum and
    # suspended cymbal; VCSL's woodblock and finger cymbals), each in its own place in the hall: the bells
    # far off to the left, the glints right, the snowman's steps close, the drum and the cymbal far back
    K = P["perc"]
    bells = Track(LOOP, True)
    for part, inst, g, pan in (("sleigh", "sleighbells", 13, -0.35), ("triangle", "triangle", 5, 0.45),
                               ("fcym", "finger_cymbal", 9, 0.3), ("belltree", "belltree", 2, 0.0)):
        if K.get(part):
            bells.mix(sampled(S(K[part], 30 + len(part), 0.008), inst, 30 + len(part), gain_db=g, pan=pan))
    place("bells", bells, C([(14, 0.7), (26, 0.55), (30, 0.45), (34, 0.6)]),
          C([(14, -6.0), (22, -4.0), (26, -3.0), (33.9, -1.0), (34, -3.0)]),
          near=(("chamber", 0.35),), far=(("concert", 0.75),), near_depth=0.35, far_depth=0.8)
    stp = sampled(S(K["wood"], 36, 0.006), "woodblock", 36, gain_db=10, pan=0.0)
    place("steps", stp, C([(22, 0.25)]), C([(22, -6.0)]), near=(("room", 0.3),), far=(("concert", 0.5),),
          near_depth=0.2, far_depth=0.6)
    dr = sampled(S(K["drum"], 37, 0.004), "bass_drum", 37, gain_db=9)
    dr.mix(sampled(S(K["crash"], 38, 0.0), "cymbal_mallet", 38, gain_db=2, release=3.0))
    place("drum", dr, C([(26, 0.6)]), C([(26, -6.0), (30, -3.0)]), near=(("chamber", 0.3),), far=(("concert", 0.8),),
          near_depth=0.45, far_depth=0.85)

    # ---- the rise: tremolo strings walking forward, the timpani roll and stroke, the cymbal swell
    sv = sampled(S(P["strings"], 17), "violins_trem", 17, gain_db=-6, dyn=C([(26, 0.2), (30, 0.5), (33.8, 0.7), (34, 0.2)]),
                 shape={"attack": 1.5, "swell": 0.1, "taper": 1.0}, lag=0.03)
    place("strings", sv, C([(26, 0.95), (30, 0.6), (33.8, 0.45), (34, 0.9)]),
          C([(26, -14.0), (30, -5.0), (33.8, 0.0), (34.3, -18.0)]),
          near=(("chamber", 0.3), ("concert", 0.3)), far=(("concert", 0.9),), near_depth=0.5, far_depth=0.95)
    rl = sampled(S(P["roll"], 18, 0.0), "timpani_roll", 18, gain_db=6, dyn=C([(28, 0.1), (29.9, 0.8), (30, 0.0)]),
                 shape={"attack": 2.0, "swell": 0.0, "taper": 0.0})
    place("roll", rl, C([(28, 0.6), (29.9, 0.35)]), C([(28, -12.0), (29.9, 0.0), (30.05, -40.0)]),
          near=(("room", 0.3),), far=(("concert", 0.7),), near_depth=0.3, far_depth=0.8)
    tp = character(sampled(S(P["timp"], 19, 0.004), "timpani", 19, gain_db=4), drive=1.4, lp=9000, wow=0.0, seed=19)
    place("timp", tp, C([(26, 0.3)]), C([(26, -9.0)]), near=(("room", 0.25), ("concert", 0.25)), far=(("concert", 0.7),),
          near_depth=0.3, far_depth=0.8)
    cy = sampled([N(sec(30) - 3.55, 3.55 + 6.0, 0.0, 0.7)], "cymbal_swell_mid", 20, gain_db=2, release=2.0)
    place("cymbal", cy, C([(26, 0.5)]), C([(26, -6.0)]), near=(("chamber", 0.3),),
          far=(("concert", 0.6), ("shimmer:cathedral2", 0.15)), near_depth=0.4, far_depth=0.75)

    # ---- the flakes rise: the harp sweeping up, the glass line climbing, reversed piano and glockenspiel
    hp = sampled(S(P["harp"], 21, 0.003), "harp", 21, gain_db=-2, release=1.5)
    place("harp", hp, C([(24, 0.45)]), C([(24, -4.0)]), near=(("chamber", 0.3),),
          far=(("shimmer:cathedral2", 0.35), ("concert", 0.5)), near_depth=0.3, far_depth=0.75)
    cl = Track(LOOP, True)
    EL.glass_line(cl, S(P["climb"], 22, 0.0), gain=0.35, seed=22, glide=0.25, attack=0.4, release=3.0, bright=0.7)
    place("climb", cl, C([(34, 0.85), (37.8, 0.3), (38, 0.7)]), C([(34, -8.0), (37.8, 0.0), (38.5, -12.0)]),
          near=(("chamber", 0.3),), far=(("shimmer:cathedral2", 0.5), ("concert", 0.4)), near_depth=0.35, far_depth=0.8)
    rise = Track(LOOP, True)
    for k, (inst, notes, end) in enumerate((("piano", [57, 64, 69, 73, 76, 81], 35), ("glock", [81, 85, 88, 92], 37))):
        src = sampled([N(2.0, 6.0, float(p), 0.55) for p in notes], inst, 23 + k, release=2.5)
        a = int(SR * 2.0)
        seg = src.buf[:, a: a + int(SR * 3.5)][:, ::-1].astype(np.float64)
        rise.add(sec(end) - seg.shape[1] / SR, seg, gain=(1.0 if inst == "piano" else 0.6))
    place("rise", rise, C([(30, 0.55)]), C([(30, -4.0)]), near=(("chamber", 0.3),),
          far=(("shimmer:cathedral2", 0.4), ("concert", 0.5)), near_depth=0.4, far_depth=0.8)
    st.play("glock", S(P["chime"], 24, 0.004), "glock", seed=24, gain_db=3, release=1.5)

    out = st.render({"room": {"seed": 60, "eq": ROOM_EQ}, "chamber": {"seed": 61, "eq": ROOM_EQ},
                     "plate": {"eq": HALL_EQ}, "concert": {"seed": 62, "eq": HALL_EQ, "cross": 0.3},
                     "cathedral2": {"seed": 63, "eq": HALL_EQ, "cross": 0.3},
                     "shimmer:cathedral2": {"seed": 64, "gens": 2, "fb": 0.45, "eq": [("hp", 400, 0.7)]}}, warmth=0.12)
    low = FX.eq(out, ("lp", 120, 0.7), circular=True)
    out = out - low + low.mean(axis=0, keepdims=True)
    return finish_loop("music", "snow", out, LOOP, 4, -16.0, 192, tilt_hs_db=1.0,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "A lydian",
                             "instrument": "music box, piano, glass and orchestra"})


if __name__ == "__main__":
    render()
