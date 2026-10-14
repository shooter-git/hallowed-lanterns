"""I. The Arbor of Faces — "Sundown": the piano's triplets and the Ember's motif,
dark, in the ways of Glass, Arnalds, Cliff Martinez and Zimmer (none of their
tunes).

The piece is in 12/8: four slow beats a bar, each one a piano triplet that
never stops - Glass's engine, the felt beat from the first note - with the
sustain pedal down throughout (it changes with the harmony). The left hand
strikes the chord's bass once and holds it; above it the triplets ripple in
the middle, evenly, the downbeat only leaned on: turning in place at first
(fifth, third or ninth, fifth), and from the bowed vibraphone's slow motif
on climbing to the fifth an octave up. The harmony is dark and never comes home the
church's way: B minor, G, E minor and F-sharp minor (a minor fifth, so there
is no pull to a cadence), turning again and again under the same figure.
The Ember's motif, D | B A F# A, belongs to the vibraphone (Martinez's world):
soft mallets play it slowly, with space around it, a beat a note; the bowed
vibraphone and the glass (the Cristal Baschet's sound) hold its long notes.
Then the bowed vibraphone sings it slower still, a bar a note, over a dark
analog bass that holds each chord's root and lets it decay (Drive, Zimmer's
low end, filling the room rather than pulsing), and it grows into the swell:
the motif on the vibraphone again, long sub booms on the downbeats, the timpani,
cymbal crescendos drawing the air in. Then the piano alone, and the Ember's
chime on the vibraphone, and the piano tapers away into the hall - and the
loop begins as softly as it ends, building again.

  bars  0-7   the piano's triplets alone, soft and a little far, growing steadily: the low B from bar 2, a
              breath of glass at 6
  bars  8-15  the vibraphone's motif (a beat a note, two bars a cycle) over B minor, G, E minor, F# minor;
              the bowed vibraphone and glass hold its long notes; the analog pad far back
  bars 16-23  the bowed vibraphone sings the motif a bar a note (D | B | A | F# | A); the dark analog bass, a
              held, decaying root for each chord; the strings far back; a long cymbal crescendo into...
  bars 24-31  the swell: the vibraphone's motif over the bass; sub booms and the timpani on the downbeats;
              it climbs again into its peak at 28 (a long cymbal crescendo and a timpani roll into the greatest
              boom; the strings, the pad, the bass and the glass at their fullest)
  bars 32-39  the piano alone over a last, slowly dying B in the bass; the Ember's chime; the piano tapers
              away into the hall, as soft at the loop's end as at its start

The voices: the piano, a real vibraphone (struck and bowed), glass and
analog synths (meant to sound like synths), and the strings only as a bed far
back. Every voice has a near and a far seat (place()).
B minor, 12/8 at dotted quarter = 60, 40 bars = 160 s.
"""
from dataclasses import replace

import numpy as np

from hlaudio.core import SR, Track
from hlaudio.score import N, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio import sampler as SM, effects as FX, electro as EL, analog as AN, kit as KIT
from hlaudio.orch import Stage, TONE
from hlaudio.piece import finish_loop

TITLE = "Sundown"
BAR = 12           # eighths (12/8)
BARS = 40
BPM_UNIT = 180     # eighths per minute (dotted quarter = 60)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 160 s

# the piano's triplet voicings: low, middle, top on beats 1 and 3, top on 2 and 4
V = {"Bm9": (47, 54, 62, 61), "Gmaj7/B": (47, 55, 62, 66), "Gmaj9": (43, 50, 59, 57), "Em9": (52, 59, 67, 66),
     "F#m11": (42, 52, 57, 59)}
CYCLE = ["Bm9", "Bm9", "Gmaj9", "Gmaj9", "Em9", "Em9", "F#m11", "F#m11"]
# the opening (B minor and G over B, twice: the build), three cycles, and the ending, its taper slowing to two bars
# a chord, back into the opening's B minor
OPEN = ["Bm9", "Bm9", "Gmaj7/B", "Gmaj7/B"]
CH = OPEN * 2 + CYCLE * 3 + ["Bm9", "Gmaj7/B", "Bm9", "Gmaj7/B"] + OPEN
LH_FROM = 2                                # the left hand's low B enters in the opening's third bar
assert len(CH) == BARS
ROOT = {"Bm9": 35, "Gmaj7/B": 35, "Gmaj9": 31, "Em9": 40, "F#m11": 42}   # the bass (B1, G1, E2, F#2)
# the triplets' touch: even, the downbeat only leaned on. Every note stays inside the piano's soft recording (its
# brighter one begins at a velocity of 0.45 and would sound like an accent); the swell is in the level, not the touch
BEAT_W = [1.0, 0.95, 0.97, 0.95]           # the four beats of the bar
TRIP_W = [1.0, 0.93, 0.92]                 # inside each triplet
TOUCH = 0.36
CLIMB = (16, 32)                           # the bars where the triplets climb to the fifth an octave up
VOICE_SPLIT = 59                           # B3: from here up the piano's recordings are voiced down (see render)
# the motif on the vibraphone, a beat (three eighths) a note: (eighth in the two-bar cycle, eighths, MIDI) - the
# pickup D on the last beat before, B, A, F#, A held, a beat of silence. Its notes sit inside every chord of the
# cycle (B minor, G, E minor, and F# minor voiced without its C#)
MOTIF = [(-3, 3, 74), (0, 6, 71), (6, 3, 69), (9, 3, 66), (12, 6, 69)]
VIBES_BARS = [(8, 16), (24, 32)]           # where the vibraphone's cycle lives (two bars each)
# the motif's touch: A, F# and A soft; the pickup D and the downbeat's B, which carry the line, a touch firmer. The
# vibraphone's recordings change at a velocity of 0.5 (the softer one about 10 dB down and darker): D and B are set
# so that with their variation every one of them stays in the brighter recording (0.51-0.67 as played), and never
# sinks under the piano
VIB_TOUCH, VIB_D, VIB_B = 0.48, 0.53, 0.57
# the bowed vibraphone's slow motif, a bar a note (bar, bars, MIDI)
SLOW = [(16, 1, 74), (17, 2, 71), (19, 1, 69), (20, 1, 66), (21, 2, 69)]
MOTIF_R = [(0, 1), (1, 2), (3, 1), (4, 1), (5, 2)]  # the motif's own rhythm (eighths), for the chime
MOTIF_PCS = [0, 9, 7, 4, 7]                        # D B A F# A
SWELL_PEAK = {"long": 7.15, "mid": 3.55, "short": 1.4}   # where each cymbal crescendo peaks (s)
# the dark bass (Drive, Zimmer's low end): a warm analog root, struck once a chord and left to decay over its two
# bars, its filter closing with it - it fills the bottom, it does not pulse
BASS = AN.Patch(oscs=[("saw", 0.0, 0, 0.7, 0.5), ("saw", -3.0, 0, 0.4, 0.5), ("pulse", 2.0, -1, 0.5, 0.5)],
                drift=2.0, cutoff=260.0, res=0.12, env_oct=1.2, keytrack=0.3, vel_bright=0.8, a=0.02, d=4.5, s=0.25,
                r=1.8, fa=0.01, fd=2.5, fs=0.1, fr=1.5, drive=1.3, sat=1.2, pre=0.45, fmax=1800.0, level=0.5,
                vel_db=10.0)

VOICE_EQ = {
    "piano": [("hp", 60, 0.7), ("peak", 250, 0.9, -2.5), ("peak", 2800, 0.9, 1.5), ("hs", 7000, 0.7, 2.0)],
    "vibes": [("hp", 150, 0.7), ("peak", 400, 0.9, -2.0), ("peak", 3000, 1.0, 1.0)],
    "bowed": [("hp", 200, 0.7), ("peak", 450, 0.9, -2.0), ("hs", 6000, 0.7, 1.0)],
    "halo": [("hp", 600, 0.7), ("hs", 7000, 0.7, 1.0)],
    "pad": [("hp", 180, 0.7), ("peak", 400, 0.9, -3.0), ("lp", 6000, 0.7)],
    "bass": [("hp", 32, 0.7), ("peak", 260, 0.9, -3.0), ("peak", 900, 1.0, 1.0)],
    "bed": [("hp", 150, 0.7), ("peak", 400, 0.9, -3.0), ("hs", 6000, 0.7, 2.0)],
    "boom": [("hp", 36, 0.7), ("peak", 250, 0.9, -2.0)],
    "timp": [("hp", 45, 0.7), ("peak", 320, 0.9, -3.0), ("peak", 2500, 1.0, 1.5)],
    "roll": [("hp", 60, 0.7), ("peak", 300, 0.9, -2.5)],
    "cymbal": [("hp", 400, 0.7)],
    "glass": [("hp", 300, 0.7), ("hs", 6000, 0.7, 2.0)],
    "chime": [("hp", 300, 0.7)],
}
# each voice's width (mid/side) and side (-1 left .. 1 right): the piano across the middle, the vibraphone just
# right of it, the bowed vibraphone and the glass wide behind, the bass and the booms in the middle, the timpani
# to the right
STAGE = {"piano": (1.0, 0.0), "vibes": (0.7, 0.2), "bowed": (1.4, -0.1), "halo": (1.5, 0.0), "pad": (1.6, 0.0),
         "bass": (0.2, 0.0), "bed": (1.5, 0.05), "boom": (0.0, 0.0), "timp": (0.8, 0.25), "roll": (0.8, 0.25),
         "cymbal": (1.5, 0.0), "glass": (1.7, 0.0), "chime": (0.6, 0.25)}
ROOM_EQ = [("hp", 180, 0.7), ("peak", 400, 0.8, -2.0)]
HALL_EQ = [("hp", 240, 0.7), ("peak", 420, 0.8, -2.5), ("hs", 6000, 0.7, 1.0)]


def bar(b):
    return b * BAR


def C(pts):
    """A control curve over bars: [(bar, value), ...] (held before the first point and after the last)."""
    pts = list(pts) if len(pts) > 1 else [pts[0], (pts[0][0] + 1, pts[0][1])]
    return Curve([(b * BAR * 60 / BPM_UNIT, v) for b, v in pts])


def sub_hz(midi):
    """A bass note's frequency brought into the sub's octave (38-76 Hz)."""
    f = 440.0 * 2 ** ((midi - 69) / 12)
    while f >= 76.0:
        f /= 2
    return f * 2 if f < 38.0 else f


def score():
    P = {}
    # the piano, the sustain pedal down throughout: the left hand strikes the chord's bass once and holds it for as
    # long as the bass stays (across chords that share it); the triplets ripple above it - the bass, fifth and top
    # on a chord's first beat, then the fifth, the top (the voicing's third and colour by turns) and the fifth an
    # octave up (from bar 16). Every note rings until the pedal changes with the harmony
    tri, lh = [], []
    for b, c in enumerate(CH):
        lo, mid, top_a, top_b = V[c]
        first = b == 0 or CH[b - 1] != c
        # it enters in the opening's third bar, struck again where the opening began before (bar 4), when the bass
        # moves, or after four bars (a piano's low string fades by then) - but not in the taper's last four bars,
        # where the low end dies away as it will come in again after the loop
        if b in (LH_FROM, 4) or (LH_FROM < b < BARS - 4 and
                                 (V[CH[b - 1]][0] != lo or bar(b) - lh[-1].t >= bar(4))):
            span = next((k for k in range(b + 1, BARS) if V[CH[k]][0] != lo), BARS) - b
            lh.append(N(bar(b), bar(min(span, 4)) - 0.3, float(lo), 0.38))
        climb = CLIMB[0] <= b < CLIMB[1]
        for beat in range(4):
            top = top_a if beat % 2 == 0 else top_b
            # turning in place (fifth, top, fifth) at first; climbing (fifth, top, the fifth an octave up) from 16
            notes = (lo, mid, top) if (beat == 0 and first) else (mid, top, mid + 12 if climb else mid)
            for k, p in enumerate(notes):
                if (beat == 0 and first) and k == 0:
                    continue                              # the bass: the left hand's held note
                v = TOUCH * BEAT_W[beat] * TRIP_W[k] * (0.95 if p == mid + 12 else 1.0)
                tri.append(N(bar(b) + 3 * beat + k, 1.0, float(p), v))
    # the pedal: it changes where the harmony does, and every note rings to the change (a key struck again adds to
    # its ringing string, as with the pedal down)
    changes = [bar(b) for b in range(BARS) if b == 0 or CH[b - 1] != CH[b]] + [bar(BARS)]
    for n in tri:
        n.d = next(t for t in changes if t > n.t) - n.t + 0.4
    P["piano"] = tri + lh
    # the vibraphone's motif, a two-bar cycle; each note let ring under the next (the pedal down)
    vib, held = [], []
    for b0, b1 in VIBES_BARS:
        for b in range(b0, b1, 2):
            for o, d, p in MOTIF:
                vib.append(N(bar(b) + o, d + 3.0, float(p), VIB_B if o == 0 else VIB_D if o < 0 else VIB_TOUCH))
                if d == 6:
                    held.append(N(bar(b) + o, d + 2.0, float(p), 0.5))
    P["vibes"] = vib
    # the bowed vibraphone holds the motif's long notes; then sings it slowly, a bar a note (16-23)
    P["bowed"] = held + [N(bar(b), bar(n) + 1.0, float(p), 0.55) for b, n, p in SLOW]
    # glass (the Cristal Baschet's sound) an octave above the bowed notes, faint
    P["halo"] = [N(n.t, n.d + 1.0, n.p + 12, 0.4) for n in P["bowed"]]
    # the analog pad far back: the chord's middle, two bars at a time (8-31)
    P["pad"] = [N(bar(b), 2 * BAR + 1, float(p + 12), 0.4) for b in range(8, 32, 2) for p in V[CH[b]][1:3]]
    # the dark bass (16-31): the chord's root, struck once and held for its two bars, decaying; and a last B under
    # the piano's ending, held into the taper and dying away well before the loop begins again
    P["bass"] = [N(bar(b), 2 * BAR - 0.3, float(ROOT[CH[b]]), 0.6 if b < 24 else 0.7) for b in range(16, 32, 2)]
    P["bass_end"] = [N(bar(32), bar(6) - 0.3, 35.0, 0.62)]
    # strings far back: the chord's middle an octave up (violins) and as voiced (cellos), a bed only (16-31)
    P["bed"] = [N(bar(b), BAR + 0.4, float(p + 12), 0.5) for b in range(16, 32) for p in V[CH[b]][1:3]]
    # the swell's downbeats: a sub boom on the bass, a timpani for its pop; cymbal crescendos into 24 and 28, where
    # the swell peaks: the greatest boom, a timpani roll growing into it on the same note
    P["booms"] = [(24, 0.85), (26, 0.55), (28, 1.0), (30, 0.7)]
    P["timp"] = [N(bar(b), 3.0, float(ROOT[CH[b]] + 12), 0.45 + 0.4 * v) for b, v in P["booms"]]
    P["roll"] = [N(bar(27) + 3, bar(1) - 3.2, float(ROOT[CH[28]] + 12), 0.6)]
    P["swells"] = [(24, "long", 0.8), (28, "long", 0.9)]
    # glass air: a breath of it late in the opening, and at the ending; the Ember chimes on the vibraphone
    P["glass"] = ([N(bar(6), 2 * BAR + 1, float(p), 0.4) for p in (78, 81, 83)] +
                  [N(bar(b), 2 * BAR + 1, float(p), 0.4) for b in (32, 34) for p in (78, 81, 83)])
    P["chime"] = [N(bar(34) + 5 + o, d + 3.0, float(74 + pc), 0.45) for (o, d), pc in zip(MOTIF_R, MOTIF_PCS)]
    return P


def render():
    P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.015))
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
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

    def place(name, tmp, dist, gain_db, near=(("room", 0.22),), far=(("concert", 0.8),), near_depth=0.12,
              far_depth=0.85):
        """A voice between its near seat and its far seat (`dist`, 0 near .. 1 far, a curve over the loop), at
        `gain_db`, with its own EQ, width and side."""
        x = tmp.buf.astype(np.float64)
        if VOICE_EQ.get(name):
            x = FX.eq(x, *VOICE_EQ[name], circular=True)
        w_, side = STAGE.get(name, (1.0, 0.0))
        if w_ != 1.0:
            x = FX.width(x, w_)
        if side:
            x = x * np.array([[np.cos((side + 1) * np.pi / 4)], [np.sin((side + 1) * np.pi / 4)]]) * 2 ** 0.5
        t = np.arange(x.shape[1]) / SR
        d = np.clip(dist(t), 0, 1)
        g = 10 ** (gain_db(t) / 20)
        st.stem(f"{name}~near", dict(near), depth=near_depth).mix((x * np.cos(d * np.pi / 2) * g).astype(np.float32))
        st.stem(f"{name}~far", dict(far), depth=far_depth).mix((x * np.sin(d * np.pi / 2) * g).astype(np.float32))

    # ---- the piano's triplets: a felt upright beside you, the beat from the first note
    pn = humanize(clk.notes(P["piano"]), 1, t_jit=0.006, v_jit=0.015)
    # the recordings from B3 up are about 10 dB brighter in the attack than those below, so the triplets' tops
    # would leap out like accents: voiced down (a softer hammer, the treble eased), the brightness rises evenly
    pt = sampled([n for n in pn if n.p < VOICE_SPLIT], "piano", 1, tone=False, gain_db=6, layer_bias=-0.2,
                 release=1.6, humanize_v=0.015)
    pt.buf = FX.soften(pt.buf.astype(np.float64), 0.3, circular=True).astype(np.float32)
    hi = sampled([n for n in pn if n.p >= VOICE_SPLIT], "piano", 11, tone=False, gain_db=6, layer_bias=-0.2,
                 release=1.6, humanize_v=0.015)
    hx = FX.soften(hi.buf.astype(np.float64), 0.45, circular=True)
    pt.mix(FX.eq(hx, ("hs", 1200, 0.7, -8.0), circular=True).astype(np.float32))
    # it begins soft and a little far and comes toward you, growing steadily to the vibraphone's entrance; at the
    # end it tapers back into the hall to the level it began at, so the loop joins without a seam
    place("piano", pt, C([(0, 0.34), (8, 0.22), (24, 0.28), (32, 0.22), (36, 0.26), (39.9, 0.34)]),
          C([(0, -1.0), (8, 3.5), (16, 4.0), (23.9, 4.5), (24, 6.0), (27.9, 6.0), (28, 7.0), (31.9, 7.0), (32, 5.0),
             (35, 4.0), (39.9, -1.0)]),
          near=(("room", 0.24), ("concert", 0.28), ("plate", 0.1)),
          far=(("concert", 0.65), ("plate", 0.18), ("shimmer:cathedral2", 0.03)), near_depth=0.2, far_depth=0.6)

    # ---- the vibraphone: the motif, slowly, soft mallets, a little to the right, its ring into the hall
    vb = sampled(S(P["vibes"], 2, 0.006), "vibes", 2, gain_db=4, release=2.0)
    place("vibes", vb, C([(7, 0.35), (24, 0.4)]), C([(7, -2.0), (24, 0.0), (27.9, 0.0), (28, 1.0)]),
          near=(("chamber", 0.3), ("plate", 0.15)), far=(("concert", 0.7), ("shimmer:cathedral2", 0.08)),
          near_depth=0.35, far_depth=0.8)
    # ---- the bowed vibraphone: the long notes, then the slow motif, wide and behind
    bw = sampled(S(P["bowed"], 3, 0.0), "vibes_bowed", 3, gain_db=8, release=2.5)
    place("bowed", bw, C([(8, 0.7), (16, 0.5), (23.9, 0.45), (24, 0.7)]),
          C([(8, -1.0), (15.9, -1.0), (16, 5.0), (23.9, 6.0), (24, 0.0), (27.9, 0.0), (28, 1.0)]),
          near=(("chamber", 0.3), ("concert", 0.25)), far=(("concert", 0.7), ("shimmer:cathedral2", 0.15)),
          near_depth=0.45, far_depth=0.85)
    hl = Track(LOOP, True)
    EL.glass(hl, S(P["halo"], 4, 0.0), gain=0.2, seed=4, attack=0.6, release=3.0, bright=0.55, pan_spread=0.3,
             breath=0.1)
    # faint under the vibraphone and the bowed motif (high, it would cut through them); fuller in the swell
    place("halo", hl, C([(8, 0.8)]), C([(8, -12.0), (16, -9.0), (23.9, -9.0), (24, -6.0), (27.9, -6.0), (28, -4.5)]),
          near=(("chamber", 0.3),),
          far=(("shimmer:cathedral2", 0.4), ("concert", 0.5)), near_depth=0.45, far_depth=0.9)

    # ---- the analog pad, far back (Martinez): warm, slowly breathing
    pd = Track(LOOP, True)
    EL.pad(pd, S(P["pad"], 5, 0.0), gain=0.5, seed=5, voices=5, detune=10.0, cutoff=700.0, res=0.6, attack=3.0,
           release=4.0, curve=C([(8, 0.3), (23, 0.55), (24, 0.75), (27.9, 0.8), (28, 0.92), (31, 0.8)]))
    place("pad", pd, C([(8, 0.85)]), C([(8, -1.0), (16, 1.0), (24, 3.0), (27.9, 3.0), (28, 4.0), (31.9, 3.0),
                                       (32.5, -30.0)]),
          near=(("chamber", 0.3),), far=(("concert", 0.6), ("shimmer:cathedral2", 0.15)), near_depth=0.5,
          far_depth=0.9)

    # ---- the dark bass: a held root a chord, decaying; its filter a little more open toward the swell
    pb = Track(LOOP, True)
    AN.play(pb, S(P["bass"], 6, 0.0), BASS, gain=1.0, seed=6,
            sweep=C([(16, 0.8), (23.9, 1.2), (24, 1.5), (27.9, 1.6), (28, 1.9), (31.9, 1.8)]))
    AN.play(pb, S(P["bass_end"], 7, 0.0), replace(BASS, d=12.0, s=0.22, r=5.0), gain=1.0, seed=7, sweep=C([(32, 1.1)]))
    pb.buf = FX.eq(FX.saturate(pb.buf.astype(np.float64), drive=1.3, mix=0.4), ("lp", 1800, 0.7),
                   circular=True).astype(np.float32)
    place("bass", pb, C([(16, 0.3)]), C([(16, -6.0), (20, -4.0), (23.9, -3.0), (24, -2.0), (27.9, -2.0), (28, -1.0),
                                         (31.9, -1.0), (32, -3.0)]),
          near=(("chamber", 0.1),), far=(("concert", 0.3),), near_depth=0.15, far_depth=0.45)

    # ---- the strings: a quiet bed far back, never a line
    dyn_bed = C([(16, 0.22), (23, 0.35), (24, 0.5), (27.9, 0.6), (28, 0.72), (31.9, 0.68), (32, 0.2)])
    bd = sampled(S(P["bed"], 7), "violins", 7, gain_db=-12, slide=0, dyn=dyn_bed,
                 shape={"attack": 1.2, "swell": 0.1, "taper": 2.0})
    bd.mix(sampled(S([N(n.t, n.d, n.p - 12, n.v) for n in P["bed"]], 8), "cellos", 8, gain_db=-14, slide=0,
                   dyn=dyn_bed, shape={"attack": 1.2, "swell": 0.1, "taper": 2.0}))
    place("bed", bd, C([(16, 0.92), (24, 0.8), (28, 0.72)]),
          C([(16, -12.0), (23.9, -6.0), (24, -1.0), (27.9, 0.0), (28, 1.5), (31.9, 0.0), (32.4, -30.0)]),
          near=(("chamber", 0.3), ("concert", 0.3)), far=(("concert", 0.9),), near_depth=0.5, far_depth=0.95)

    # ---- the swell's downbeats: a sub boom diving onto the bass and held (a little less long than the bars
    # between), a real timpani for its pop, the cymbals' crescendos drawing the air in
    bm = Track(LOOP, True)
    for i, (b, v) in enumerate(P["booms"]):
        bm.add(clk.s(bar(b)), KIT.boom(sub_hz(ROOT[CH[b]]), v, 80 + i, decay=4.5 + 2.0 * v, drift=0.0), gain=0.8)
    place("boom", bm, C([(24, 0.2)]), C([(24, -12.0)]), near=(("room", 0.12),), far=(("concert", 0.3),),
          near_depth=0.15, far_depth=0.4)
    tp = sampled(S(P["timp"], 9, 0.004), "timpani", 9, gain_db=2)
    place("timp", tp, C([(24, 0.55)]), C([(24, -4.0)]), near=(("room", 0.25), ("concert", 0.3)),
          far=(("concert", 0.75),), near_depth=0.45, far_depth=0.85)
    # the roll growing into the peak's downbeat
    rl = sampled(S(P["roll"], 14, 0.0), "timpani_roll", 14, gain_db=6, dyn=C([(27.25, 0.1), (27.95, 0.85), (28, 0.0)]),
                 shape={"attack": 1.5, "swell": 0.0, "taper": 0.0})
    place("roll", rl, C([(27.25, 0.65), (27.95, 0.4)]), C([(27.25, -12.0), (27.95, -2.0), (28.05, -40.0)]),
          near=(("room", 0.25), ("concert", 0.3)), far=(("concert", 0.75),), near_depth=0.45, far_depth=0.85)
    cy = Track(LOOP, True)
    for i, (b, kind, v) in enumerate(P["swells"]):
        hit = clk.s(bar(b))
        cy.mix(sampled([N(hit - SWELL_PEAK[kind], SWELL_PEAK[kind] + 6.0, 0.0, v)], f"cymbal_swell_{kind}", 10 + i,
                       gain_db=2, release=2.0))
    place("cymbal", cy, C([(20, 0.6)]), C([(20, -6.0)]), near=(("chamber", 0.3),),
          far=(("concert", 0.6), ("shimmer:cathedral2", 0.15)), near_depth=0.4, far_depth=0.75)

    # ---- glass air and the Ember's chime on the vibraphone
    gl = Track(LOOP, True)
    # a breath of air, never a voice: soft, not too bright, a little shimmer
    EL.glass(gl, S(P["glass"], 12, 0.0), gain=0.26, seed=12, attack=2.0, release=3.5, bright=0.5, pan_spread=0.5,
             breath=0.2)
    # faintest in the opening (the piano alone is soft there), and tapering with the piano at the end
    place("glass", gl, C([(0, 0.85)]), C([(0, -15.0), (31.9, -15.0), (32, -12.0), (35, -14.0), (37, -21.0)]),
          near=(("chamber", 0.35),),
          far=(("shimmer:cathedral2", 0.3), ("concert", 0.5)), near_depth=0.4, far_depth=0.85)
    ch = sampled(S(P["chime"], 13, 0.004), "vibes", 13, gain_db=2, release=2.0)
    place("chime", ch, C([(34, 0.5)]), C([(34, -3.0)]), near=(("chamber", 0.3), ("plate", 0.1)),
          far=(("concert", 0.6), ("shimmer:cathedral2", 0.15)), near_depth=0.4, far_depth=0.8)

    out = st.render({"room": {"seed": 70, "eq": ROOM_EQ}, "chamber": {"seed": 71, "eq": ROOM_EQ},
                     "plate": {"eq": HALL_EQ}, "concert": {"seed": 72, "eq": HALL_EQ, "cross": 0.2},
                     "shimmer:cathedral2": {"seed": 74, "gens": 2, "fb": 0.4, "eq": [("hp", 400, 0.7)]}}, warmth=0.2)
    # the low end in the middle
    low = FX.eq(out, ("lp", 120, 0.7), circular=True)
    out = out - low + low.mean(axis=0, keepdims=True)
    return finish_loop("music", "arbor", out, LOOP, 4, -16.0, 192, tilt_hs_db=1.5,
                       meta={"title": TITLE, "bpm": 60, "meter": "12/8", "beat": "dotted quarter", "key": "B minor",
                             "instrument": "piano, vibraphone, glass and synths"})


if __name__ == "__main__":
    render()
