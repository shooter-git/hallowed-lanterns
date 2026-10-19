"""VIII. The Marigold Garden — "Remember Me": the stillness of Cliff Martinez,
the build of Hans Zimmer (the organ of Interstellar) and the turning piano and
quiet beat of Ólafur Arnalds - their ways, none of their tunes. A burning
heart, an ache, a longing, and the night's magic remembered.

No progression a listener can see coming: the harmony is a pedal and colours
drifting over it one note at a time, a figure that never changes while the
bass slides beneath it, and three real moves - the bass rising to C at the
peak, falling to B in the dark, and coming home to E in the hush.

  bars  0-7   the glass world (Martinez): a glass arpeggio and glass chords over the organ's E, the
              colours drifting one note at a time (the Ember's cell, G - E - D B, their top voice);
              the far bell; the Ember chimes
  bars  8-23  the figure (Arnalds): the felt piano turns one figure (B E F# G, in the walk's 3+3+2) and
              never changes it; the bass holds E, then slides beneath it - C, A, G, B, C, A - and every
              move re-colours the same notes. At 16 the beat is born: real brush taps on a snare; at 18
              the kick (a deep sub tuned bar by bar to the bass, a real concert drum's skin and its beater,
              through tape) and a warm analog bass, pulsing like a heart (the root, a ghost, an octave on
              the 3+3+2's accent, a pickup) - everything soft ducking a little under each kick, so the
              night breathes with it; at the turns, BOOMS: a sub diving an octave onto the bass note, a
              real timpani on the same note for its pop, the air drawn in before them by a suspended
              cymbal's real crescendo, the gong under the greatest; at 20 the snare itself
              (struck, wires on) under the brushes on the half-time backbeat; from 20, now and again, a few syncopated
              hats (a real shaker, high, through a slowly sweeping phaser) - colour, never a pattern; the
              organ's soft arpeggio arrives from the church across the field
  bars 24-31  the build (Zimmer): a long E again; the colours drift over it, the horns sing the cell
              slowly, the strings walk forward, the beat grows (ghost taps in sixteenths, the kick on the
              3+3+2 with pickups and doubles); the bass in eighths whose accents move every bar, its filter
              opening; a long cymbal swell and a timpani fill into...
  bars 32-35  the peak: the greatest boom, the gong; the bass rises to C and the same notes open into C
              major; the organ's open stops in sixteenths, the strings and horns close and loud, the bass
              driving in sixteenths (3+3+3+3+2+2, octaves leaping), the beat at full; a timpani fill
              tumbles into...
  bars 36-39  the dark (Interstellar): B sus, then B; the piano falls silent, the kick is a heartbeat -
              lub-dub, twice a bar - the bass throbs in dotted eighths across it; a timpani roll swells;
              the horns lean D-sharp up into...
  bars 40-43  the release: one last boom, and everything falls away but the figure, close and quiet;
              the far bell
  bars 44-55  the afterglow, in the light: the bass steps up to G, and the figure turns the same shape a
              third higher, in G major (D G A B: the night's notes, lifted); the Ember chimes its own song
              (G E D B D) as the light arrives; high strings warm it, the bass slides once more - C, E -
              home to G, the brushes far away like a memory; the glass world returns in G, its last colour
              the intro's first, and the loop begins again

THE MIX MOVES. Every voice has a near seat and a far seat and travels between
them, and grows louder or quieter, when the music asks (place()): the piano
starts beside you, steps back into the room as the orchestra rises (louder,
but part of the whole) and comes back alone at the release; the organ walks
forward from far away; the strings wait far back until the peak; the beat
stays across the room, warm but never in your face, and leaves as a faint
memory.
E minor, 4/4 at 72, 56 bars = 186.7 s.
"""
import numpy as np

from hlaudio.core import SR, Track
from hlaudio.score import N, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio import sampler as SM, effects as FX, electro as EL, analog as AN, kit as KIT
from hlaudio.orch import Stage, TONE
from hlaudio import festival  # noqa: F401  (the gong's tone and seat)
from hlaudio.piece import finish_loop

TITLE = "Remember Me"
BAR = 8            # eighths
BARS = 56
BPM_UNIT = 144     # eighths per minute (quarter = 72)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 186.67 s

# the bass, bar by bar
BASS = ([40] * 12 + [36, 36, 33, 33, 43, 43, 35, 35, 36, 36, 33, 33] + [40] * 8 + [36] * 4 + [35] * 4 + [40] * 4 +
        [43, 43, 36, 36, 40, 40, 43, 43] + [43] * 4)
LIGHT = 44         # the afterglow, in G
assert len(BASS) == BARS
# the drifting colours over E (the cell, G - E - D B, as their top voice), two bars each
DRIFT = [[71, 74, 78, 79], [67, 72, 74, 76], [66, 69, 71, 74], [64, 66, 67, 71]]
FIGSET = [71, 76, 78, 79]                                  # the figure's notes, an octave up: the glass's
FIG = [59, 64, 66, 71, 66, 64, 67, 64]                     # the turning figure: B E F# B F# E G E
FIG_G = [62, 67, 69, 74, 69, 67, 71, 67]                   # ... in the light, a third higher: D G A D A G B G
FIGSET_G = [74, 79, 81, 83]                                # its notes, an octave up (the glass's): D G A B
# the glass world's return, in G: Gmaj7, G6, G6/9, and last the intro's first colour (the loop's seam)
GLOW = [[74, 78, 79, 83], [71, 74, 76, 79], [74, 76, 79, 81], [71, 74, 78, 79]]
ARP_FIG = [0, 2, 1, 3, 0, 2, 1, 3]
ACC = [1.0, .55, .6, .9, .55, .6, .85, .6]
# the glass arpeggio's voicing, bar by bar (None: silent)
# ... while the figure plays, the colours keep to its notes (B D E F# G: nothing a semitone from them)
DRIFT_FIG = [[71, 74, 78, 79], [67, 71, 74, 76], [66, 67, 71, 74], [64, 66, 67, 71]]
GA = ([DRIFT[b // 2] for b in range(8)] + [FIGSET] * 16 + [DRIFT_FIG[(b - 24) // 2] for b in range(24, 32)] +
      [[71, 74, 76, 79]] * 4 + [None] * 4 + [FIGSET] * 4 + [FIGSET_G] * 8 + GLOW)
assert len(GA) == BARS
# the organ's open stops in the peak and the dark (sixteenths): C major, B sus, B
OPEN = {32: [48, 55, 64, 67, 71], 33: [48, 55, 64, 67, 71], 34: [48, 55, 64, 67, 71], 35: [48, 55, 64, 67, 71],
        36: [47, 52, 54, 59, 64], 37: [47, 52, 54, 59, 64], 38: [47, 51, 54, 59, 63], 39: [47, 51, 54, 59, 63]}
SIXTEENTHS = [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 1, 3, 2, 4, 3, 1]
# the horns sing the cell slowly: (bar, pitch, bars)
HORNS = [(24, 67, 2), (26, 64, 2), (28, 62, 2), (30, 59, 1), (31, 62, 1), (32, 67, 2), (34, 64, 2),
         (36, 59, 2), (38, 63, 2), (40, 64, 1)]
# the hats' small bursts, in eighths (sixteenths off the beat, now and then a quick flick of 32nds); a bar
# gets one, or none - never the kick's or the brush's places
HAT_BURSTS = [[1.5], [2.5, 3.5], [5.5], [6.5, 6.75], [3.5], [7.5], [0.5, 1.5], [5.5, 6.5, 7.5], [2.5, 2.75],
              [1.5, 5.5]]
# the bass pulse: warm, round, a little bite as each note starts (eighths, the 3+3+2's accents)
PULSE = AN.Patch(oscs=[("saw", 0.0, 0, 0.8, 0.5), ("pulse", 3.0, 0, 0.45, 0.5), ("saw", -2.0, -1, 0.35, 0.5)],
                 drift=2.0, cutoff=210.0, res=0.15, env_oct=1.1, keytrack=0.3, vel_bright=0.9, a=0.004, d=0.28,
                 s=0.5, r=0.08, fa=0.002, fd=0.16, fs=0.0, fr=0.1, drive=1.4, sat=1.3, pre=0.45, fmax=2400.0,
                 level=0.5, vel_db=12.0)
# the booms: (bar, eighth, strength, the cymbal swell drawing the air in before it, or None)
BOOMS = [(16, 0, 0.4, None), (20, 0, 0.5, "short"), (24, 0, 0.8, "mid"), (26, 7.5, 0.45, None),
         (28, 0, 0.65, "short"), (30, 7.5, 0.5, None), (32, 0, 1.0, "long"), (33, 6.5, 0.5, None),
         (34, 0, 0.6, None), (36, 0, 0.9, "short"), (40, 0, 0.75, "mid")]
SWELL_PEAK = {"long": 7.15, "mid": 3.55, "short": 1.4}       # where each crescendo peaks (s)
# the timpani's fills: into the peak (sixteenths, E G E then C) and into the dark (triplets, C E B)
FILLS = [(31, [(6, 52, 0.45), (6.5, 55, 0.55), (7, 52, 0.65), (7.5, 48, 0.8)]),
         (35, [(6, 48, 0.55), (6 + 2 / 3, 52, 0.65), (7 + 1 / 3, 47, 0.8)])]


def sub_hz(midi):
    """A bass note's frequency brought into the sub's octave (38-76 Hz: below that no speaker plays it, and it
    only eats the headroom)."""
    f = 440.0 * 2 ** ((midi - 69) / 12)
    while f >= 76.0:
        f /= 2
    return f * 2 if f < 38.0 else f


def timp_pitch(midi):
    """A bass note placed on the timpani (40-55)."""
    p = midi
    while p > 55:
        p -= 12
    while p < 40:
        p += 12
    return float(p)
# THE EQ: every voice its own room in the spectrum. The piano owns the middle, the kick, the booms and the
# bass pulse own the low end; everything else gives way in the low-mids (where the mud gathers) and the
# voices that should sparkle get their presence and air back.
VOICE_EQ = {
    "figure": [("hp", 85, 0.7), ("ls", 160, 0.7, -2.0), ("peak", 260, 0.9, -3.5), ("peak", 600, 1.0, -1.0),
               ("peak", 2800, 0.9, 3.0), ("hs", 7000, 0.7, 4.0)],
    "arp": [("hp", 200, 0.7), ("peak", 450, 0.9, -2.0), ("hs", 5000, 0.7, 3.5)],
    "glass": [("hp", 300, 0.7), ("hs", 6000, 0.7, 3.5)],
    "organ_soft": [("hp", 150, 0.7), ("peak", 350, 0.9, -3.0), ("hs", 5000, 0.7, 2.5)],
    "organ_open": [("hp", 130, 0.7), ("peak", 350, 0.9, -3.0), ("peak", 2000, 1.0, 1.0), ("hs", 6000, 0.7, 2.0)],
    "pedal": [("hp", 30, 0.7), ("peak", 220, 0.9, -3.0), ("lp", 1200, 0.7)],
    "strings": [("hp", 220, 0.7), ("peak", 420, 0.9, -2.5), ("hs", 6000, 0.7, 3.5)],
    "glow": [("hp", 300, 0.7), ("peak", 500, 0.9, -2.0), ("peak", 3000, 1.0, 1.5), ("hs", 7000, 0.7, 3.0)],
    "low": [("hp", 40, 0.7), ("peak", 260, 0.9, -3.0), ("lp", 1600, 0.7)],
    "horns": [("hp", 110, 0.7), ("peak", 300, 0.9, -3.0), ("peak", 1300, 1.0, 1.5)],
    "roll": [("hp", 60, 0.7), ("peak", 300, 0.9, -2.5)],
    "timp": [("hp", 50, 0.7), ("peak", 320, 0.9, -3.0), ("peak", 2500, 1.0, 2.0)],
    "kick": [("hp", 38, 0.7), ("peak", 320, 0.9, -4.0), ("peak", 3500, 1.0, 0.5)],
    "boom": [("hp", 36, 0.7), ("peak", 250, 0.9, -2.0)],
    "pulse": [("hp", 42, 0.7), ("peak", 260, 0.9, -3.0), ("peak", 900, 1.0, 1.5)],
    "snare": [("hp", 150, 0.7), ("peak", 420, 0.9, -2.0), ("peak", 5000, 1.0, 1.0)],
    "brush": [("hp", 250, 0.7), ("hs", 6000, 0.7, 3.5)],
    "ghost": [("hp", 300, 0.7), ("hs", 6000, 0.7, 3.5)],
    "hats": [("hs", 9000, 0.7, 2.0)],
    "cymbal": [("hp", 400, 0.7)],
}
# THE STAGE: each voice's width (mid/side; 0 a point, 1 as played, above 1 wider) and its side (-1 left .. 1 right).
# The low end in the middle; the organ to the left and the horns left of centre, the timpani and the low strings
# to the right; the glass, the strings and the cymbals wide around everything; the hats far out to both sides.
STAGE = {"kick": (0.0, 0.0), "boom": (0.0, 0.0), "pulse": (0.0, 0.0), "pedal": (0.3, 0.0), "figure": (1.1, 0.0),
         "arp": (1.3, 0.25), "glass": (1.7, 0.0), "organ_soft": (1.1, -0.35), "organ_open": (1.4, -0.15),
         "strings": (1.4, 0.15), "glow": (1.5, 0.1), "low": (0.7, 0.3), "horns": (0.8, -0.35), "roll": (0.8, 0.2), "timp": (0.8, 0.25),
         "snare": (0.6, -0.06), "brush": (0.6, -0.15), "ghost": (0.6, 0.25), "hats": (1.4, 0.0),
         "cymbal": (1.5, 0.0)}
# ... and the spaces: every reverb's return high-passed and its low-mids dipped (space, not mud)
ROOM_EQ = [("hp", 180, 0.7), ("peak", 400, 0.8, -2.0)]
HALL_EQ = [("hp", 240, 0.7), ("peak", 420, 0.8, -2.5), ("hs", 6000, 0.7, 1.0)]
CELL = [(0, 2), (2, 2), (4, 1), (5, 1), (6, 2)]
CELL_PCS = [0, 9, 7, 4, 7]                                 # G E D B D (the Ember's chime, in G like the guitar)


def bar(b):
    return b * BAR


def bar_starts():
    """Where each bar begins (s), with the rubato the piece is played with (render()'s Clock)."""
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.02))
    return [round(float(clk.s(bar(b))), 6) for b in range(BARS)]


def C(pts):
    """A control curve over bars: [(bar, value), ...] (held before the first point and after the last)."""
    pts = list(pts) if len(pts) > 1 else [pts[0], (pts[0][0] + 1, pts[0][1])]
    return Curve([(b * BAR * 60 / BPM_UNIT, v) for b, v in pts])


def score():
    P = {}
    # the glass arpeggio and the glass chords (the intro, the release, the outro; a halo at the peak)
    P["arp"] = [N(bar(b) + i, 1.0, float(GA[b][idx]), 0.5 * ACC[i]) for b in range(BARS) if GA[b]
                for i, idx in enumerate(ARP_FIG)]
    P["glass"] = [N(bar(b), BAR + 1, float(p), 0.42) for b in list(range(0, 8)) + list(range(40, 44)) +
                  list(range(52, 56)) for p in GA[b][1:]]
    P["halo"] = [N(bar(b), 2 * BAR + 1, float(p), 0.4) for b in (32, 34) for p in GA[b][2:]]
    # the figure (8-35, 40-53) and its left hand: the bass's octave on the beat and on the 3+3+2's accent
    fig, lh = [], []
    for b in list(range(8, 36)) + list(range(40, 52)):
        w = float(np.interp(b, [8, 12, 24, 32, 35, 40, 44, 48, 53], [0.36, 0.42, 0.46, 0.52, 0.52, 0.38, 0.42, 0.38,
                                                                     0.26]))
        fig += [N(bar(b) + i, 1.6, float(p), w * ACC[i]) for i, p in enumerate(FIG_G if b >= LIGHT else FIG)]
        # the left hand: the bass's octave; its low note only where the bass pulse leaves the low end free
        low_ok = not (18 <= b < 40)
        lh += [N(bar(b) + o, d, float(BASS[b] + k), v * w / 0.42) for o, d, v in ((0, 3.2, 0.46), (3, 5.2, 0.34))
               for k in ((0, 12) if low_ok else (12,))]
    P["figure"] = fig + lh
    # the organ: its soft arpeggio (eighths) from far away (16-31), its open stops in sixteenths (32-39),
    # its pedal (the intro, the build, the peak, the dark, the afterglow)
    soft = []
    for b in range(16, 32):
        if b < 24:
            v4 = sorted({BASS[b] + 19, 64, 71, 76})          # the bass's fifth and the figure's E and B (the root is the bass's)
            v4 = (v4 + [67])[:4] if len(v4) < 4 else v4[:4]
        else:
            v4 = [p - 12 for p in GA[b]]
        soft += [N(bar(b) + i, 1.05, float(v4[idx]), 0.55 * ACC[i]) for i, idx in enumerate(ARP_FIG)]
    P["organ_soft"] = soft
    P["organ_open"] = [N(bar(b) + k * 0.5, 0.55, float(OPEN[b][i]), (0.75 if b < 36 else 0.8) * (1.0 if k % 4 == 0 else 0.7))
                       for b in range(32, 40) for k, i in enumerate(SIXTEENTHS)]
    ped = [N(bar(0), bar(8) + 0.3, 40.0, 0.5)] + [N(bar(b), BAR + 0.3, float(BASS[b]), 0.55) for b in range(24, 40)]
    ped += [N(bar(40), bar(4) + 0.3, 40.0, 0.42)] + [N(bar(b), BAR + 0.3, float(BASS[b]), 0.42) for b in range(44, 52)]
    ped += [N(bar(52), bar(4) + 0.3, 43.0, 0.42)]
    P["pedal"] = ped
    # the strings: far, an open fifth over the sliding bass, then the drifting colours, then B sus and B
    sv = []
    for b in range(12, 40):
        if b < 24:
            ps = [BASS[b] + 19, 76]                         # the bass's fifth and the figure's E
        elif b < 36:
            ps = GA[b][1:]
        else:
            ps = [54, 59, 64] if b < 38 else [54, 59, 63]
        sv += [N(bar(b), BAR + 0.4, float(p), 0.5) for p in ps]
    P["strings"] = sv
    P["glow"] = ([N(bar(b), BAR + 0.4, float(p), 0.42) for b in range(LIGHT, 48) for p in (71, 74)] +
                 [N(bar(b), BAR + 0.4, float(p), 0.46) for b in range(48, 56) for p in (71, 74, 79)])
    P["low"] = [N(bar(b), BAR + 0.4, float(BASS[b]), 0.5) for b in range(24, 36)]
    P["low_b"] = [N(bar(36), bar(4) + 0.4, 35.0, 0.55)]
    P["horns"] = [N(bar(b), bar(d), float(p), 0.6) for b, p, d in HORNS]
    P["roll"] = [N(bar(36), bar(4) - 0.2, 47.0, 0.6)]
    # the beat (real brush taps on a snare and a muted concert drum), born at 16 and growing; the dark has only
    # the drum (a heartbeat); the afterglow, the brushes far away
    brush, ghost, kick = [], [], []
    for b in range(16, 52):
        if b < 20:
            brush += [(b, 4, 0.55)]
        elif b < 24:
            brush += [(b, 4, 0.6), (b, 7, 0.26), (b, 7.5, 0.2)]
        elif b < 32:
            brush += [(b, 4, 0.65), (b, 7, 0.28), (b, 7.5, 0.22)]
        elif b < 36:
            brush += [(b, 4, 0.72), (b, 6.5, 0.25), (b, 7, 0.3), (b, 7.5, 0.26)]
        elif 44 <= b < 52:
            brush += [(b, 4, 0.42)]
        if 24 <= b < 28:
            ghost += [(b, o, 0.2) for o in (1.5, 2.5, 5.5)]
        elif 28 <= b < 36:
            ghost += [(b, o, 0.16 + 0.06 * (k % 2)) for k, o in enumerate((0.5, 1.5, 2.5, 3.5, 5.5, 6.5))]
        # the kick: the downbeat (18), the 3+3+2 with a pickup now and then (20), the build's pickups and
        # doubles (24), the peak's syncopations (32), and in the dark a heartbeat, lub-dub twice a bar
        if 18 <= b < 20:
            kick += [(b, 0, 0.5)]
        elif 20 <= b < 24:
            kick += [(b, 0, 0.55), (b, 3, 0.35)] + ([(b, 7.5, 0.3)] if b % 2 else [])
        elif 24 <= b < 32:
            kick += ([(b, 0, 0.6), (b, 2.5, 0.3), (b, 3, 0.45), (b, 6.5, 0.35), (b, 7.25, 0.28)] if b in (27, 29)
                     else [(b, 0, 0.6), (b, 3, 0.42)] if b == 31 else [(b, 0, 0.6), (b, 3, 0.42), (b, 6.5, 0.35)])
        elif 32 <= b < 36:
            kick += [(b, 0, 0.7), (b, 3, 0.45)] + ([] if b == 35 else [(b, 6, 0.4), (b, 7.5, 0.35)])
        elif 36 <= b < 40:
            kick += [(b, 0, 0.75), (b, 0.6, 0.5), (b, 4, 0.7), (b, 4.6, 0.45)]
    # the hats: now and again (more often as the build grows), alternating strokes and sides
    r = np.random.default_rng(9)
    hats = []
    for b in list(range(20, 36)) + list(range(44, 52)):
        chance = 0.55 if b < 28 else (0.8 if b < 36 else 0.3)
        if r.random() < chance:
            for k, o in enumerate(HAT_BURSTS[r.integers(len(HAT_BURSTS))]):
                n = N(bar(b) + o, 0.3, 0.0, float(r.uniform(0.35, 0.6) * (0.7 if b >= 44 else 1.0)))
                n.x.update(pan=(-0.6 if (len(hats) + k) % 2 else 0.6), up=bool(k % 2))
                hats.append(n)
    P["hats"] = hats
    # the snare itself on the backbeat (20-35), and the bass pulse (18-39)
    P["snare"] = [N(bar(b) + 4, 0.5, 0.0, float(np.interp(b, [20, 24, 31, 32, 35], [0.45, 0.55, 0.65, 0.75, 0.75])))
                  for b in range(20, 36)]
    # the bass pulse: only under the kick's accents (not the heartbeat's second beat), a round note that
    # gives each hit its weight; a pickup on the last eighth already sounds the next bar's bass
    pulse = []
    for b, o, v in kick:
        if o in (0.6, 4.6) or o % 1 == 0.25:
            continue
        p = BASS[min(BARS - 1, b + 1)] if o >= 7 else BASS[b]
        pulse.append(N(bar(b) + o, 1.8 if o == 0 else 1.2, float(p), float(min(1.0, 0.45 + v))))
    P["pulse"] = pulse
    # the booms, their timpani, the cymbal swells before them, the gong under the greatest, the fills
    P["booms"] = BOOMS
    P["timp"] = ([N(bar(b) + o, 2.0, timp_pitch(BASS[min(BARS - 1, b + (1 if o > 6 else 0))]), 0.45 + 0.45 * v)
                  for b, o, v, _ in BOOMS] +
                 [N(bar(b) + o, 1.0, float(p), v) for b, hits in FILLS for o, p, v in hits])
    P["gong_hit"] = [N(bar(32), 16.0, 50.0, 0.42)]
    P["brush"] = [N(bar(b) + o, 0.5, 0.0, v) for b, o, v in brush]
    P["ghost"] = [N(bar(b) + o, 0.25, 0.0, v) for b, o, v in ghost]
    P["kick"] = [N(bar(b) + o, 1.0, 0.0, v) for b, o, v in kick]
    # the far bell (the loop's turn, and the release) and the Ember's chime (the glockenspiel)
    P["bell"] = [N(bar(0), 16.0, 50.0, 0.3), N(bar(40), 16.0, 50.0, 0.32)]
    P["chime"] = [N(bar(b) + o, d + 1.0, float(91 + pc), 0.42) for b in (7, LIGHT) for (o, d), pc in zip(CELL, CELL_PCS)]
    return P


def render():
    P = score()
    clk = Clock(bpm=BPM_UNIT, rubato=(4 * BAR, 0.02))  # (as bar_starts() has it)
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    st = Stage(LOOP, circular=True)
    bar_s = np.array([clk.s(bar(b)) for b in range(BARS + 1)])
    clk_bar = lambda t: float(np.searchsorted(bar_s, t + 1e-6, side="right") - 1)

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

    def character(tmp, drive=1.6, lp=3500.0, wow=0.0008, seed=0):
        """Tape and a little valve: the attack rounded, the body warmed, a slow breath of wow."""
        x = FX.saturate(tmp.buf.astype(np.float64), drive=drive, mix=0.5)
        if wow:
            x = FX.wow_flutter(x, wow=wow, flutter=wow / 4, circular=True, seed=seed)
        tmp.buf = FX.eq(x, ("lp", lp, 0.7), ("hp", 35, 0.7), circular=True).astype(np.float32)
        return tmp

    def place(name, tmp, dist, gain_db, near=(("room", 0.22),), far=(("concert", 0.8),), near_depth=0.12,
              far_depth=0.85):
        """A voice between its near seat and its far seat: `dist` (0 near .. 1 far, a curve over the loop)
        crossfades them with equal power, `gain_db` is its loudness; the far seat is darker and wetter. The voice
        gets its own EQ (VOICE_EQ) first."""
        w_, side = STAGE.get(name, (1.0, 0.0))
        x = tmp.buf.astype(np.float64)
        if VOICE_EQ.get(name):
            x = FX.eq(x, *VOICE_EQ[name], circular=True)
        if w_ != 1.0:
            x = FX.width(x, w_)
        if side:
            x = x * np.array([[np.cos((side + 1) * np.pi / 4)], [np.sin((side + 1) * np.pi / 4)]]) * 2 ** 0.5
        t = np.arange(x.shape[1]) / SR
        d = np.clip(dist(t), 0, 1)
        g = 10 ** (gain_db(t) / 20)
        st.stem(f"{name}~near", dict(near), depth=near_depth).mix((x * np.cos(d * np.pi / 2) * g).astype(np.float32))
        st.stem(f"{name}~far", dict(far), depth=far_depth).mix((x * np.sin(d * np.pi / 2) * g).astype(np.float32))

    # ---- the kick: a deep sub tuned under the E, the real concert drum's skin and beater, through tape; its
    # times make everything soft breathe (duck a little and swell back)
    kn = S(P["kick"], 42, 0.004)
    boom_times = [clk.s(bar(b) + o) for b, o, _, _ in P["booms"]]
    kick_times = [n.t for n in kn] + boom_times
    pump = lambda tmp, depth: setattr(tmp, "buf", FX.duck(tmp.buf.astype(np.float64), kick_times, depth=depth,
                                                          attack=0.006, release=0.26, circular=True).astype(np.float32))
    sub = Track(LOOP, True)
    for i, n in enumerate(kn):
        f = sub_hz(BASS[min(BARS - 1, int(clk_bar(n.t)))])
        sub.add(n.t, KIT.kick(n.v, 42 * 100 + i, f_hi=2.1 * f, f_lo=f, decay=0.3), gain=0.9)
    skin = sampled(kn, "bass_drum", 42, gain_db=4)
    sk = skin.buf.astype(np.float64)
    beater = FX.eq(sk, ("hp", 2500, 0.7), circular=True)
    kick = Track(LOOP, True)
    kick.buf = (sub.buf.astype(np.float64) + 0.8 * FX.eq(sk, ("lp", 1800, 0.7), circular=True) + 0.5 * beater).astype(np.float32)

    # ---- the glass world: the arpeggio through a dotted-eighth echo, and the glass chords and halo
    ar = Track(LOOP, True)
    EL.arp(ar, S(P["arp"], 2, 0.004), gain=1.0, seed=2, cutoff=C([(0, 2000), (24, 2300), (32, 3200), (36, 2000)]),
           res=1.1, decay=0.32, shape=0.3, pan_wobble=0.35)
    x = ar.buf.astype(np.float64)
    ar.buf = FX.eq(x + FX.echo(x, clk.s(1.5), fb=0.38, mix=0.32, lp=6000, circular=True), ("hp", 180, 0.7),
                   circular=True).astype(np.float32)
    pump(ar, 0.22)
    place("arp", ar, C([(0, 0.45), (8, 0.6), (16, 0.7), (24, 0.65), (32, 0.75), (40, 0.6), (44, 0.5), (52, 0.45)]),
          C([(0, 0.0), (8, -3.0), (16, -5.0), (32, -4.0), (35.8, -6.0), (40, -4.0), (44, -2.0), (52, 0.0)]),
          near=(("chamber", 0.3),), far=(("concert", 0.7), ("shimmer:cathedral2", 0.15)), near_depth=0.35,
          far_depth=0.75)
    gl = Track(LOOP, True)
    EL.glass(gl, S(P["glass"], 3, 0.0), gain=0.3, seed=3, attack=1.4, release=3.0, bright=0.85, pan_spread=0.5,
             breath=0.28)
    EL.glass(gl, S(P["halo"], 4, 0.0), gain=0.24, seed=4, attack=1.0, release=3.0, bright=0.55, pan_spread=0.3)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 10000, 0.7), circular=True).astype(np.float32)
    pump(gl, 0.25)
    place("glass", gl, C([(0, 0.85), (30, 0.85), (32, 0.65), (36, 0.85)]), C([(0, 0.0)]),
          near=(("chamber", 0.35),), far=(("shimmer:cathedral2", 0.45), ("concert", 0.5)), near_depth=0.4,
          far_depth=0.8)

    # ---- the figure: the felt piano through tape, beside you; it steps back as the orchestra rises
    ft = sampled(S(P["figure"], 20, 0.007), "piano", 20, tone=False, gain_db=7, layer_bias=-0.05, release=0.9)
    ft.buf = FX.soften(ft.buf.astype(np.float64), 0.35, circular=True).astype(np.float32)
    ft = character(ft, drive=1.3, lp=13000, wow=0.0008, seed=20)
    place("figure", ft, C([(8, 0.35), (24, 0.4), (28, 0.5), (32, 0.6), (35.9, 0.6), (40, 0.35), (52, 0.4)]),
          C([(8, -3.0), (12, -1.0), (24, 1.0), (32, 2.0), (35.9, 2.0), (40, -2.0), (48, -3.0), (51.9, -6.0)]),
          near=(("room", 0.25), ("concert", 0.35), ("plate", 0.15)), far=(("concert", 0.65), ("plate", 0.25)),
          near_depth=0.3, far_depth=0.7)

    # ---- the organ: from far away (soft stops), forward and open at the peak and in the dark; its pedal
    ot = sampled(S(P["organ_soft"], 30, 0.004), "organ_soft", 30, gain_db=-1, legato=False,
                 dyn=C([(16, 0.4), (24, 0.55), (31.9, 0.65)]))
    pump(ot, 0.25)
    place("organ_soft", ot, C([(16, 0.9), (20, 0.7), (24, 0.55), (31.9, 0.45)]),
          C([(16, -10.0), (20, -5.0), (24, -3.0), (31.9, -1.0)]),
          near=(("chamber", 0.25),), far=(("cathedral2", 0.75),), near_depth=0.45, far_depth=0.9)
    oo = sampled(S(P["organ_open"], 31, 0.003), "organ", 31, gain_db=-10, legato=False,
                 dyn=C([(32, 0.55), (35.9, 0.7), (36, 0.65), (39.9, 0.8)]))
    pump(oo, 0.2)
    place("organ_open", oo, C([(32, 0.35), (36, 0.3), (39.9, 0.35)]), C([(32, 0.0), (36, 1.0), (39.9, 0.0)]),
          near=(("chamber", 0.25), ("cathedral2", 0.2)), far=(("cathedral2", 0.75),), near_depth=0.45, far_depth=0.9)
    pt = sampled(S(P["pedal"], 32, 0.0), "organ_soft_pedal", 32, gain_db=-5,
                 dyn=C([(0, 0.45), (24, 0.5), (32, 0.65), (39.9, 0.7), (40, 0.4), (56, 0.45)]))
    pump(pt, 0.3)
    place("pedal", pt, C([(0, 0.85), (24, 0.8), (32, 0.5), (39.9, 0.45), (40, 0.85)]),
          C([(0, -2.0), (24, -4.0), (32, 1.0), (39.9, 2.0), (40, -4.0), (56, -2.0)]),
          near=(("chamber", 0.3),), far=(("cathedral2", 0.7),), near_depth=0.5, far_depth=0.9)

    # ---- the strings far back until the peak; the low strings; the horns singing the cell; the timpani roll
    sv = sampled(S(P["strings"], 33), "violins", 33, gain_db=-11, slide=0,
                 dyn=C([(12, 0.25), (24, 0.35), (31, 0.5), (32, 0.65), (35.9, 0.65), (39.9, 0.55)]),
                 shape={"attack": 0.9, "swell": 0.15, "taper": 2.0}, lag=0.03)
    pump(sv, 0.25)
    place("strings", sv, C([(12, 0.95), (24, 0.85), (30, 0.7), (32, 0.45), (36, 0.5), (39.9, 0.55), (40, 0.95)]),
          C([(12, -14.0), (20, -10.0), (24, -8.0), (31, -4.0), (32, 0.0), (36, -1.0), (39.9, -2.0), (40.4, -24.0)]),
          near=(("chamber", 0.3), ("concert", 0.3)), far=(("concert", 0.9),), near_depth=0.5, far_depth=0.95)
    gw = sampled(S(P["glow"], 38), "violins", 38, gain_db=-11, slide=0, dyn=C([(44, 0.3), (48, 0.4), (52, 0.42), (55.9, 0.3)]),
                 shape={"attack": 1.4, "swell": 0.2, "taper": 2.0}, lag=0.03)
    place("glow", gw, C([(44, 0.8), (48, 0.65), (52, 0.7), (55.9, 0.85)]),
          C([(43.9, -30.0), (44, -12.0), (46, -8.0), (48, -5.0), (52, -6.0), (55.9, -14.0), (56, -30.0)]),
          near=(("chamber", 0.3), ("concert", 0.3)), far=(("concert", 0.85), ("shimmer:cathedral2", 0.1)),
          near_depth=0.5, far_depth=0.9)
    lo = sampled(S(P["low"], 34), "cellos", 34, gain_db=-6, slide=0, dyn=C([(24, 0.3), (32, 0.6)]),
                 shape={"attack": 1.0, "swell": 0.1, "taper": 2.0}, lag=0.03)
    lo.mix(sampled(S(P["low_b"], 35), "basses", 35, gain_db=-4, slide=0, dyn=C([(36, 0.55), (39.9, 0.65)]),
                   shape={"attack": 0.8, "swell": 0.1, "taper": 2.0}, lag=0.03))
    pump(lo, 0.35)
    place("low", lo, C([(24, 0.9), (32, 0.6), (36, 0.5)]), C([(24, -10.0), (32, -2.0), (36, 0.0), (39.9, 0.0), (40.4, -24.0)]),
          near=(("chamber", 0.3),), far=(("concert", 0.85),), near_depth=0.5, far_depth=0.95)
    hn = sampled(S(P["horns"], 36), "horns", 36, gain_db=-1, slide=0,
                 dyn=C([(24, 0.4), (32, 0.62), (36, 0.68), (39.9, 0.75), (40, 0.4)]),
                 shape={"attack": 0.6, "swell": 0.2, "taper": 2.0}, lag=0.03)
    place("horns", hn, C([(24, 0.9), (28, 0.7), (32, 0.5), (36, 0.45), (39.9, 0.45), (40, 0.8)]),
          C([(24, -12.0), (28, -6.0), (32, -2.0), (36, 0.0), (39.9, 1.0), (40.5, -8.0), (41.5, -20.0)]),
          near=(("chamber", 0.3),), far=(("concert", 0.85),), near_depth=0.55, far_depth=0.9)
    rl = sampled(S(P["roll"], 37, 0.0), "timpani_roll", 37, gain_db=6, dyn=C([(36, 0.15), (39.9, 0.85), (40, 0.0)]),
                 shape={"attack": 2.0, "swell": 0.0, "taper": 0.0})
    place("roll", rl, C([(36, 0.6), (39.9, 0.35)]), C([(36, -12.0), (39.9, 0.0), (40.05, -40.0)]),
          near=(("room", 0.3),), far=(("concert", 0.7),), near_depth=0.3, far_depth=0.8)

    # ---- the beat: real brush taps and a muted concert drum, through tape, across the room (near enough to
    # feel, never in your face)
    bt = character(sampled(S(P["brush"], 40, 0.006), "snare_tap", 40, gain_db=10, pan=-0.1), drive=1.4, lp=9000,
                   wow=0.0, seed=40)
    place("brush", bt, C([(16, 0.5), (32, 0.45), (43.9, 0.45), (44, 0.75)]),
          C([(16, -8.0), (24, -5.0), (32, -2.0), (35.9, -2.0), (44, -12.0), (51.9, -14.0)]),
          near=(("room", 0.45), ("chamber", 0.15)), far=(("concert", 0.6),), near_depth=0.35, far_depth=0.7)
    gt = character(sampled(S(P["ghost"], 41, 0.004), "snare_tap", 41, gain_db=22, pan=0.12, layer_bias=-0.2),
                   drive=1.6, lp=8000, wow=0.0, seed=41)
    place("ghost", gt, C([(24, 0.5)]), C([(24, -14.0), (28, -9.0), (32, -6.0), (35.9, -6.0)]),
          near=(("room", 0.4), ("chamber", 0.15)), far=(("concert", 0.55),), near_depth=0.35, far_depth=0.7)
    kt = character(kick, drive=1.6, lp=6000, wow=0.0, seed=42)
    place("kick", kt, C([(18, 0.35), (36, 0.3)]), C([(18, -16.0), (24, -13.5), (32, -11.0), (36, -10.5), (39.9, -10.5)]),
          near=(("room", 0.25),), far=(("concert", 0.45),), near_depth=0.25, far_depth=0.55)
    # the snare, struck, under the brushes on the backbeat: a crack with body, and a long dark plate tail
    sn = character(sampled(S(P["snare"], 44, 0.005), "snare", 44, gain_db=4, pan=-0.06), drive=1.3, lp=10000, wow=0.0,
                   seed=44)
    place("snare", sn, C([(20, 0.5), (32, 0.45)]), C([(20, -8.0), (24, -4.5), (32, -1.0), (35.9, -1.0)]),
          near=(("room", 0.3), ("plate", 0.22)), far=(("concert", 0.65),), near_depth=0.35, far_depth=0.75)
    # the bass pulse: eighths on the bass, warm, ducking deep under each kick (the drive under the build)
    pb = Track(LOOP, True)
    AN.play(pb, S(P["pulse"], 45, 0.003), PULSE, gain=1.0, seed=45,
            sweep=C([(18, 0.8), (24, 0.9), (31.9, 1.6), (32, 2.0), (35.9, 2.2), (36, 1.0), (39.9, 1.4)]))
    pump(pb, 0.6)
    pb = character(pb, drive=1.5, lp=1800, wow=0.0, seed=45)
    place("pulse", pb, C([(18, 0.15)]), C([(18, -7.5), (20, -4.0), (24, -2.5), (32, -0.5), (36, 0.5), (39.9, 0.5)]),
          near=(("chamber", 0.08),), far=(("concert", 0.3),), near_depth=0.1, far_depth=0.4)

    # ---- the booms: a sub diving onto the bass note, a real timpani on the same note for its pop, a real
    # suspended cymbal's crescendo drawing the air in before the big ones, the gong under the peak
    bm = Track(LOOP, True)
    for i, (b, o, v, _) in enumerate(P["booms"]):
        nb_ = BASS[min(BARS - 1, b + (1 if o > 6 else 0))]
        bm.add(clk.s(bar(b) + o), KIT.boom(sub_hz(nb_), v, 60 + i, decay=1.0 + 0.9 * v), gain=0.8)
    bm = character(bm, drive=1.6, lp=900, wow=0.0, seed=60)
    place("boom", bm, C([(16, 0.12)]), C([(16, -12.5)]), near=(("room", 0.12),), far=(("concert", 0.3),),
          near_depth=0.08, far_depth=0.4)
    tp = character(sampled(S(P["timp"], 61, 0.004), "timpani", 61, gain_db=4), drive=1.4, lp=9000, wow=0.0, seed=61)
    place("timp", tp, C([(16, 0.5), (32, 0.45)]), C([(16, -10.0), (24, -8.0), (32, -6.0), (40, -8.0)]),
          near=(("room", 0.25), ("concert", 0.3)), far=(("concert", 0.75),), near_depth=0.4, far_depth=0.85)
    cy = Track(LOOP, True)
    for i, (b, o, v, kind) in enumerate(P["booms"]):
        if kind:
            hit = clk.s(bar(b) + o)
            cy.mix(sampled([N(hit - SWELL_PEAK[kind], SWELL_PEAK[kind] + 6.0, 0.0, 0.35 + 0.5 * v)],
                           f"cymbal_swell_{kind}", 62 + i, gain_db=2, release=2.0))
    place("cymbal", cy, C([(16, 0.6)]), C([(16, -4.0)]), near=(("chamber", 0.3),),
          far=(("concert", 0.6), ("shimmer:cathedral2", 0.15)), near_depth=0.4, far_depth=0.75)
    st.play("gong", S(P["gong_hit"], 63, 0.0), "gong", seed=63, gain_db=12, tail=12.0, depth=0.7)

    # ---- the hats: a real shaker's strokes, high-passed into a hat's air, through a slowly sweeping phaser
    hs = Track(LOOP, True)
    hn_ = S(P["hats"], 43, 0.004)
    for stroke, up in (("shaker_down", False), ("shaker_up", True)):
        hs.mix(sampled([n for n in hn_ if n.x.get("up", False) == up], stroke, 43, gain_db=8, pan=0.0))
    hx = FX.eq(hs.buf.astype(np.float64), ("hp", 4500, 0.7), ("hs", 9500, 0.7, -2.0), circular=True)
    hs.buf = FX.phaser(hx, rate=0.07, lo=1200.0, hi=9000.0, stages=6, fb=0.45, mix=0.6, circular=True).astype(np.float32)
    place("hats", hs, C([(20, 0.55), (35.9, 0.55), (44, 0.7)]),
          C([(20, -8.0), (28, -3.0), (32, -1.0), (35.9, -1.0), (44, -10.0), (51.9, -10.0)]),
          near=(("room", 0.35),), far=(("concert", 0.6),), near_depth=0.4, far_depth=0.75)

    # ---- the far bell and the Ember's chime
    st.play("gong", S(P["bell"], 50, 0.0), "gong", seed=50, gain_db=11, tail=16.0, depth=0.95)
    gb = st.stems["gong"]
    gb.buf = FX.eq(gb.buf.astype(np.float64), ("lp", 2800, 0.7), circular=True).astype(np.float32)
    st.play("glock", S(P["chime"], 51, 0.004), "glock", seed=51, gain_db=3, release=1.5)

    out = st.render({"room": {"seed": 70, "eq": ROOM_EQ}, "chamber": {"seed": 71, "eq": ROOM_EQ},
                     "plate": {"eq": HALL_EQ}, "concert": {"seed": 72, "eq": HALL_EQ, "cross": 0.2},
                     "cathedral2": {"seed": 73, "eq": HALL_EQ, "cross": 0.2},
                     "shimmer:cathedral2": {"seed": 74, "gens": 2, "fb": 0.4, "eq": [("hp", 400, 0.7)]}}, warmth=0.12)
    # the low end in the middle: everything under 120 Hz mono (tight, and no smear of reverb under the bass)
    low = FX.eq(out, ("lp", 120, 0.7), circular=True)
    out = out - low + low.mean(axis=0, keepdims=True)
    # the whole: the middle eased a little (the piano, the glass and the organ all live there), the air opened
    out = FX.eq(out, ("peak", 800, 0.6, -1.5), circular=True)
    return finish_loop("music", "marigold", out, LOOP, 4, -16.0, 192, tilt_hs_db=4.0,
                       meta={"title": TITLE, "bpm": 72, "meter": "4/4", "beat": "quarter", "key": "E minor",
                             "instrument": "piano, glass, organ and orchestra",
                             # where every bar begins (the rubato's breath included): the finale's way in starts
                             # on one of them
                             "barStarts": bar_starts()})


if __name__ == "__main__":
    render()
