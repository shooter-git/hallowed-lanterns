"""Finale — "Hallowed Lanterns" (rescored; one-shot, plays at the Wishing Tree).

The title's music, grown into the whole arc and ending for real. 4/4,
quarter = 80, the eighths grouped 3+3+2, D with Lydian colours.

The felt piano's broken-chord cycle opens it exactly as the title does, one
note of the voicing changing at a time, and the theme EMERGES as the top
voice of the arpeggio (B A F# A | D C# B A). Then a three-voice CANON on the
Ember's motif augmented: the oboe (D B A F# A), the clarinet a fifth
below two bars later, the bassoon an octave below two bars after that, over
cello pizzicati plucking the pedal. Then a Zimmer build by adding layers:
spiccato sixteenths ticking in 3+3+2, a dotted ostinato in the low strings,
the organ pedal playing the motif in the bass while the horns sing the
theme above it in long notes. The one lift is prepared, never a jolt: G
Lydian, then E minor 9 over an A pedal and A sus - the dominant held while
the spiccato keeps ticking - with the one braam, into the full statement in
D: the theme in horns and trombones with the flute above, over the full
organ, timpani and the bassoon's canon. The coda leaves the piano alone to
say the Ember's motif once more over a held D major ninth, and stops.

  bars  0-11  the piano cycle; the theme emerges as its top voice
  bars 12-19  canon of the motif: solo violin, clarinet, bassoon; pizzicato pedal
  bars 20-27  the build: spiccato, ostinato, organ pedal motif, horns' theme
  bars 28-29  the A pedal (E minor 9 over A, A sus): the braam and the timpani
  bars 30-37  the full statement in D
  bars 38-41  coda: the piano's motif over D major ninth, and silence

The beat belongs to the build and the statement only: from bar 24 low
timpani (on the bass) and the concert bass drum lock to the 3+3+2 of the
spiccato, the downbeats first, then the syncopations, the ghost notes and a
sixteenth pickup into each second bar as the build grows; on the A pedal
(28-29) they hold back to the downbeats under the braam, then come in full
with the statement (30) and fall away through bars 36-37, so the coda is
the piano alone.
"""
import numpy as np

from hlaudio.core import SR
from hlaudio.score import N, prog, humanize, Clock, chord_pcs
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords, roots
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.beats import groove, drum_pitch
from hlaudio.piece import finish_oneshot
from hlaudio import lead as LD

TITLE = "Hallowed Lanterns"
BAR = 8            # eighths
BARS = 42
BPM_UNIT = 160     # eighths per minute (quarter = 80)
SECONDS = BARS * BAR * 60 / BPM_UNIT + 9.0
M = PR.Mode(62, "ionian")

G69 = "G6add9/D"
# (chord, melody top voice of the piano or None, piano pattern)
PLAN = [
    ("Dmaj9", None, "A"), ("Dmaj9", None, "A"), (G69, None, "A"), (G69, None, "A"),
    (G69, 83, "B"), ("Dmaj9", 81, "B"), ("Bm11/D", 78, "B"), ("Asus4/D", 81, "B"),
    (G69, 86, "C"), ("Dmaj9", 85, "C"), ("Bm11/D", 83, "C"), ("Asus4/D", 81, "C"),
    (G69, None, "A"), (G69, None, "A"), ("A7sus4/D", None, "A"), ("Bm11/D", None, "A"),
    (G69, None, "A"), (G69, None, "A"), ("Dmaj9", None, "A"), ("Bm11/D", None, "A"),
    ("Dmaj9", 83, "C"), ("Bm9", 81, "C"), ("Aadd9", 78, "C"), ("Dmaj7/F#", 81, "C"),
    ("Asus4", 86, "C"), ("A", 85, "C"), ("Gmaj7#11", 83, "C"), ("Gmaj7#11", 81, "C"),
    ("Em9/A", None, "A"), ("A7sus4", None, "A"),
    ("Dmaj9", 83, "C"), ("Bm9", 81, "C"), ("Aadd9", 78, "C"), ("Dmaj7/F#", 81, "C"),
    ("Asus4", 86, "C"), ("A", 85, "C"), ("Gmaj7#11", 83, "C"), ("Asus4", 81, "C"),
    ("Dmaj9", None, "A"), ("Dmaj9", None, "A"), ("Dmaj9", None, "D"), ("Dmaj9", None, "D"),
]
PAT = {"A": [0, 1, 2, 3, 2, 1, 2, 3], "B": [0, 1, 2, 3, 2, 1, 4, 3], "C": [0, 2, 4, 1, 3, 4, 2, 4], "D": []}
ACC = [1.0, .72, .8, .95, .72, .8, .92, .75]
BASS = {"Bm9": 35, "Aadd9": 33, "Dmaj7/F#": 30, "Asus4": 33, "A": 33, "Gmaj7#11": 31, "Em9/A": 33,
        "A7sus4": 33}


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{BAR}" for c, _, _ in PLAN))


def lead(cur, sym, lo=64, hi=77):
    """The voicing for `sym` (4 distinct notes in lo..hi) that moves least
    from `cur` while keeping the chord's colour tones (all but root and fifth)."""
    from itertools import combinations
    pcs, _, root = chord_pcs(sym)
    colour = set(pcs) - {root, (root + 7) % 12}
    cand = [p for p in range(lo, hi + 1) if p % 12 in pcs]
    best, bs = None, 1e9
    for comb in combinations(cand, 4):
        move = sum(abs(a - b) for a, b in zip(sorted(cur), comb))
        miss = len(colour - {p % 12 for p in comb})
        crush = sum(1 for a, b in zip(comb, comb[1:]) if b - a == 1)
        sc = move + 5 * miss + 3 * crush
        if sc < bs:
            best, bs = list(comb), sc
    return best


def arpeggio():
    out = []
    cur = [64, 66, 69, 73]
    for b, (sym, top, pat) in enumerate(PLAN):
        target = lead(cur, sym)
        for i, idx in enumerate(PAT[pat]):
            if i in (0, 3, 6) and cur != target:
                cand = [(target[k] in cur, abs(c - g), k) for k, (c, g) in enumerate(zip(cur, target)) if c != g]
                k = min(cand)[2]
                cur[k] = target[k]
                cur.sort()
            t = bar(b) + i
            if idx == 4:
                v = (0.44 if pat == "B" else 0.5) * (1.06 if i == 6 else 1.0)
                out.append(N(t, 2.6, float(top), v, {"top": True}))
            else:
                out.append(N(t, 2.2, float(cur[idx]), 0.4 * ACC[i]))
    return out


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["arp"] = arpeggio()
    lh = []
    for b in range(0, 40, 2):
        sym = PLAN[b][0]
        lo = BASS.get(sym, 38)
        lh += [N(bar(b), bar(2) + 1, float(lo), 0.42), N(bar(b) + 4, bar(2) - 3, float(lo + 12), 0.3)]
    P["lh"] = lh
    # the coda: the Ember's motif on the piano, D5 | B5 A5 F#5 A5 (quarter = eighth x2), then the low D
    P["coda"] = [N(bar(38) + 6, 2, 74.0, 0.48), N(bar(39), 4, 83.0, 0.55), N(bar(39) + 4, 2, 81.0, 0.5),
                 N(bar(39) + 6, 2, 78.0, 0.46), N(bar(40), 12, 81.0, 0.5),
                 N(bar(40), 16, 50.0, 0.4), N(bar(40), 16, 38.0, 0.45), N(bar(40) + 2, 14, 66.0, 0.3),
                 N(bar(40) + 3, 13, 69.0, 0.3), N(bar(40) + 4, 12, 73.0, 0.28), N(bar(40) + 5, 11, 76.0, 0.28)]
    # the canon of the augmented motif (bars 12-22)
    P["vn_canon"] = [N(bar(12), 4, 74.0, 0.5), N(bar(12) + 4, 12, 83.0, 0.58), N(bar(14), 8, 81.0, 0.55),
                     N(bar(15), 8, 78.0, 0.52), N(bar(16), 16, 81.0, 0.55)]
    P["vla_canon"] = [N(bar(14), 4, 67.0, 0.5), N(bar(14) + 4, 12, 76.0, 0.56), N(bar(16), 8, 74.0, 0.54),
                      N(bar(17), 8, 71.0, 0.5), N(bar(18), 16, 74.0, 0.52)]
    P["vc_canon"] = [N(bar(16), 4, 50.0, 0.5), N(bar(16) + 4, 12, 59.0, 0.56), N(bar(18), 8, 57.0, 0.54),
                     N(bar(19), 8, 54.0, 0.52), N(bar(20), 16, 57.0, 0.52)]
    # the build: spiccato sixteenths (3+3+2 in each half bar), the dotted low ostinato
    acc16 = [1.15, .6, .7, 1.05, .6, .7, .95, .6]
    tick = []
    for b in range(20, 38):
        sym = PLAN[b][0]
        pcs, bass, root = chord_pcs(sym)
        lo = 62 + ((root - 62) % 12)
        p1, p2 = float(lo if lo <= 69 else lo - 12), float((lo if lo <= 69 else lo - 12) + 7)
        for k in range(16):
            tick.append(N(bar(b) + k * 0.5, 0.4, p1 if k % 2 == 0 else p2, 0.5 * acc16[k % 8]))
    P["tick"] = tick
    dot = []
    for b in range(22, 38):
        sym = PLAN[b][0]
        r = BASS.get(sym, 38) + 12
        for q in range(4):
            dot += [N(bar(b) + q * 2, 1.4, float(r), 0.55), N(bar(b) + q * 2 + 1.5, 0.45, float(r), 0.4)]
    P["dot"] = dot
    P["org_ped_motif"] = [N(bar(20), 8, 38.0, 0.55), N(bar(21), 8, 35.0, 0.55), N(bar(22), 8, 33.0, 0.55),
                          N(bar(23), 8, 30.0, 0.55), N(bar(24), 16, 33.0, 0.55)]
    P["horns"] = [N(bar(20) + i * 8, 8.2, float(p), 0.6) for i, p in enumerate([71, 69, 66, 69, 74, 73, 71, 69])]
    P["horns_full"] = [N(bar(30) + i * 8, 8.2, float(p), 0.75) for i, p in enumerate([71, 69, 66, 69, 74, 73, 71, 69])]
    P["tbn_full"] = [N(n.t, n.d, n.p - 12, n.v * 0.95) for n in P["horns_full"]]
    P["vn_full"] = [N(n.t, n.d, n.p + 12, n.v * 0.9) for n in P["horns_full"]]
    P["vc_canon2"] = [N(bar(30), 4, 50.0, 0.6), N(bar(30) + 4, 12, 59.0, 0.65), N(bar(32), 8, 57.0, 0.62),
                      N(bar(33), 8, 54.0, 0.6), N(bar(34), 16, 57.0, 0.6)]
    P["vla_sus"] = sustain_chords(pr, 57, 69, 2, vel=0.5, overlap=0.4, start=bar(20), end=bar(38))
    P["org_full"] = sustain_chords(pr, 57, 76, 4, vel=0.6, overlap=0.3, start=bar(28), end=bar(38))
    lowp = lambda p: p - 12 if p >= 36 else p
    P["org_full_ped"] = [N(bar(b), bar(1) + 0.3, float(lowp(BASS.get(PLAN[b][0], 38))), 0.6) for b in range(28, 38)]
    P["org_soft"] = [N(bar(0), bar(12), 50.0, 0.45), N(bar(12), bar(8), 50.0, 0.45),
                     N(bar(38), bar(4) + 4, 50.0, 0.4)] + \
        [N(bar(38), bar(4) + 4, float(p), 0.42) for p in (57, 61, 64, 66)]
    P["org_soft_ped"] = [N(bar(0), bar(20), 38.0, 0.45), N(bar(38), bar(4) + 4, 38.0, 0.45)]
    P["vc_pizz"] = [N(bar(b) + pos, 1.5, float(p), v) for b in range(12, 20)
                    for pos, p, v in ((0, 38, 0.55), (3, 45, 0.42), (6, 50, 0.45))]
    P["cb"] = [N(bar(12), bar(8), 38.0, 0.45)] + \
        [N(bar(b), bar(1) + 0.3, float(BASS.get(PLAN[b][0], 38)), 0.55) for b in range(20, 38)] + \
        [N(bar(38), bar(4) + 4, 38.0, 0.45)]
    P["timp_roll"] = [N(bar(18), bar(2) + 0.3, 45.0, 0.5), N(bar(29), bar(1) + 0.3, 45.0, 0.7),
                      N(bar(36), bar(2) + 0.3, 45.0, 0.6)]
    P["timp"] = [N(bar(20), 3, 38.0, 0.62), N(bar(38), 4, 38.0, 0.6)]
    # the beat (bars 24-37): timpani on the bass and its fifth, the bass drum, 3+3+2 with
    # ghost notes and a sixteenth pickup, held back to the downbeats on the A pedal
    swell = Curve([(bar(24), 0.12), (bar(25), 0.26), (bar(26), 0.42), (bar(27), 0.56), (bar(27.9), 0.64),
                   (bar(28), 0.36), (bar(29), 0.42), (bar(29.85), 0.66), (bar(30), 1.0), (bar(34), 0.95),
                   (bar(36), 0.8), (bar(37), 0.5), (bar(37.7), 0.2), (bar(38), 0.0)])
    lo, hi = drum_pitch(pr, 38, 49), drum_pitch(pr, 38, 49, fifth=True)
    fig = [(0, "bd", 0, 1.0, 0.0), (0, "timp", lo, 0.88, 0.0),
           (3, "timp", lo, 0.7, 0.22), (5.5, "timp", hi, 0.3, 0.6),
           (6, "timp", hi, 0.76, 0.38), (7, "timp", lo, 0.3, 0.66), (7.5, "timp", lo, 0.36, 0.52),
           (8, "timp", lo, 0.84, 0.1), (10.5, "timp", lo, 0.3, 0.64), (11, "timp", lo, 0.68, 0.28),
           (14, "bd", 0, 0.7, 0.32), (14, "timp", hi, 0.78, 0.32),
           (15, "timp", lo, 0.32, 0.5), (15.5, "timp", lo, 0.4, 0.45), (15.75, "timp", lo, 0.46, 0.7)]
    P["drums"] = groove(bar(24), bar(38), 16, fig, swell, vel=(0.2, 0.86))
    gp = []
    for b in range(0, 40):
        for pos, p in ((0, 74.0), (3, 81.0), (6, 76.0)):
            gp.append(N(bar(b) + pos, 1.0, p, 0.42 if pos == 0 else 0.34))
    P["glass"] = [n for n in gp if not (bar(28) <= n.t < bar(30))]
    P["air"] = [N(bar(36), bar(6), 93.0, 0.3), N(bar(38), bar(4), 86.0, 0.3)]
    P["sub"] = [N(bar(b) + pos, 1.5, 26.0, 0.55 if pos == 0 else 0.42) for b in range(12, 38) for pos in (0, 3)
                if not (28 <= b < 30)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.38), (sec(4), 0.44), (sec(8), 0.52), (sec(12), 0.56), (sec(16), 0.6), (sec(20), 0.66),
                 (sec(24), 0.74), (sec(27.5), 0.82), (sec(28.2), 0.9), (sec(30.2), 0.96), (sec(36), 0.92),
                 (sec(37.8), 0.7), (sec(38.5), 0.45), (sec(42), 0.32)])
    build = Curve([(sec(19.5), 0.25), (sec(22), 0.45), (sec(27.5), 0.75), (sec(30), 0.95), (sec(37), 0.9),
                   (sec(38.2), 0.3)])
    st = Stage(SECONDS, circular=False)
    shape = {"attack": 0.6, "swell": 0.2, "taper": 2.5}

    arp = S(P["arp"], 1, 0.006)
    for n in arp:
        n.v = float(n.v * (0.9 + 0.45 * arc(n.t)))
    st.play("piano", [n for n in arp if not n.x.get("top")], "piano", seed=1, gain_db=9, layer_bias=-0.25,
            release=0.9)
    st.play("piano", [n for n in arp if n.x.get("top")], "piano", seed=2, gain_db=10, layer_bias=-0.15,
            release=1.2)
    lh = S(P["lh"], 3, 0.01)
    for n in lh:
        n.v = float(n.v * (0.9 + 0.4 * arc(n.t)))
    st.play("piano", lh, "piano", seed=3, gain_db=6, layer_bias=-0.3, release=1.5)
    st.play("piano", S(P["coda"], 4, 0.012), "piano", seed=4, gain_db=9, layer_bias=-0.2, release=2.5)

    kw = dict(shape=shape, lag=0.025)
    st.play("oboe", S(P["vn_canon"], 5), "oboe", seed=5, gain_db=10, **LD.lead(st),
            dyn=Curve([(sec(12), 0.45), (sec(14), 0.6), (sec(17.5), 0.55), (sec(18.2), 0.35)]), **kw)
    st.play("clarinets", S(P["vla_canon"], 6), "clarinet", seed=6, gain_db=4,
            dyn=Curve([(sec(14), 0.45), (sec(16), 0.6), (sec(19.5), 0.55), (sec(20.2), 0.35)]), **kw)
    st.play("bassoon", S(P["vc_canon"], 7), "bassoon", seed=7, gain_db=0,
            dyn=Curve([(sec(16), 0.45), (sec(18), 0.62), (sec(21.5), 0.6), (sec(22.2), 0.4)]), **kw)
    vp = S(P["vc_pizz"], 31, 0.006)
    st.play("cellos_pizz", vp, "cellos_pizz", seed=31, gain_db=2, seat="cellos")
    tk = S(P["tick"], 8, 0.005)
    for n in tk:
        n.v = float(n.v * (0.55 + 0.6 * build(n.t)))
    st.play("violas_spic", [n for n in tk], "violas_spic", seed=8, gain_db=3, seat="violas")
    st.play("violins_spic", [N(n.t, n.d, n.p + 12, n.v * 0.85) for n in tk if n.t >= sec(24)], "violins_spic",
            seed=9, gain_db=-1, seat="violins2")
    dt = S(P["dot"], 10, 0.005)
    for n in dt:
        n.v = float(n.v * (0.6 + 0.5 * build(n.t)))
    st.play("cellos_spic", dt, "cellos_spic", seed=10, gain_db=2, seat="cellos")
    st.play("basses_spic", [N(n.t, n.d, n.p - 12, n.v) for n in dt], "basses_spic", seed=11, gain_db=-4,
            seat="basses")
    st.play("organ", S(P["org_ped_motif"], 12, 0.0), "organ_pedal", seed=12,
            dyn=Curve([(sec(20), 0.45), (sec(23), 0.6), (sec(26), 0.55)]), gain_db=-8)
    st.play("horns", S(P["horns"], 13), "horns", seed=13,
            dyn=Curve([(sec(20), 0.45), (sec(24), 0.62), (sec(27.8), 0.7)]), gain_db=-2, **kw)
    st.play("horns", S(P["horns_full"], 14), "horns", seed=14, dyn=build, gain_db=2, shape=shape, lag=0.03)
    st.play("trombones", S(P["tbn_full"], 15), "trombones", seed=15, dyn=build, gain_db=-3, shape=shape,
            lag=0.03)
    st.play("flutes", S(P["vn_full"], 16), "flute", seed=16, dyn=build, gain_db=2, **kw)
    st.play("bassoon", S(P["vc_canon2"], 17), "bassoon", seed=17, dyn=build, gain_db=-3, **kw)
    st.play("violas", S(P["vla_sus"], 18), "violas", seed=18, dyn=build, gain_db=-19, **LD.bed(), **kw)
    st.play("basses", S(P["cb"], 19), "basses", seed=19, dyn=arc, gain_db=-16, **LD.bed(), **kw)
    top = Curve([(sec(27.8), 0.35), (sec(28.5), 0.7), (sec(30.2), 0.85), (sec(37), 0.8), (sec(38.3), 0.3)])
    st.play("organ", S(P["org_full"], 20, 0.0), "organ", seed=20, dyn=top, gain_db=-12)
    st.play("organ", S(P["org_full_ped"], 21, 0.0), "organ_pedal", seed=21, dyn=top, gain_db=-8)
    soft = Curve([(0, 0.35), (sec(12), 0.45), (sec(19.5), 0.4), (sec(20), 0.0), (sec(38), 0.3), (sec(39), 0.45),
                  (sec(42), 0.35)])
    st.play("organ", S(P["org_soft"], 22, 0.0), "organ_soft", seed=22, dyn=soft, gain_db=-12)
    st.play("organ", S(P["org_soft_ped"], 23, 0.0), "organ_soft_pedal", seed=23, dyn=soft, gain_db=-7)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08).astype("float32")
    st.play("timpani", S(P["timp_roll"], 24, 0.0), "timpani_roll", seed=24,
            dyn=Curve([(sec(18), 0.05), (sec(20), 0.5), (sec(20.05), 0.1), (sec(29), 0.1), (sec(30), 0.8),
                       (sec(30.05), 0.1), (sec(36), 0.1), (sec(38), 0.6), (sec(38.05), 0.1)]),
            gain_db=-6, release=0.4)
    st.play("timpani", S(P["timp"], 25, 0.004), "timpani", seed=25, gain_db=-3)
    D = P["drums"]
    st.play("timpani", S(D.get("timp", []), 32, 0.004), "timpani", seed=32, gain_db=4)
    st.play("drums", S(D.get("bd", []), 33, 0.003), "bass_drum", seed=33, gain_db=3, seat="bass_drum")
    # the braam on the A pedal
    t_b = sec(28) - 0.05
    bdyn = Curve([(t_b, 0.4), (t_b + 1.2, 0.95), (t_b + 3.6, 0.8), (t_b + 5.8, 0.4)])
    st.play("braam", [N(t_b, 6.0, 45.0, 0.95), N(t_b, 6.0, 52.0, 0.9)], "trombones", seed=26, dyn=bdyn,
            gain_db=-8, seat="trombones")
    st.play("braam", [N(t_b, 6.0, 33.0, 0.95)], "tuba", seed=27, dyn=bdyn, gain_db=-7, seat="tuba")
    br = st.stem("braam")
    EL.sub_swell(br, t_b, 5.0, 33.0, gain=0.18, attack=1.0, release=1.5)

    gl = st.stem("glass", {"shimmer:cathedral2": 0.35, "concert": 0.55}, depth=0.65)
    gp = S(P["glass"], 28, 0.0)
    for n in gp:
        n.v = float(n.v * (0.7 + 0.4 * arc(n.t)))
        n.x["attack"] = 0.03
        n.x["release"] = 1.1
    EL.glass(gl, gp, gain=0.38, seed=28, bright=0.5, pan_spread=0.35, breath=0.05)
    EL.glass(gl, S(P["air"], 29, 0.0), gain=0.25, seed=29, attack=2.5, release=5.0, bright=0.4)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4200, 0.7))
    gl.buf = (gl.buf + FX.echo(gl.buf, clk.s(1.5), fb=0.38, mix=0.32, lp=2200)[:, : gl.buf.shape[1]]).astype("float32")
    sb = st.stem("sub", {}, depth=0.3)
    sub = S(P["sub"], 30, 0.0)
    for n in sub:
        n.v = float(n.v * (0.55 + 0.5 * arc(n.t)))
    EL.sub_pulse(sb, sub, gain=0.4, seed=30, decay=0.35)

    out = st.render({"concert": {"seed": 91}, "cathedral2": {"seed": 92},
                     "shimmer:cathedral2": {"seed": 93, "gens": 2, "fb": 0.42}}, warmth=0.35)
    return finish_oneshot("music", "finale", out, -16.0, 192, max_s=SECONDS, end_fade=3.0,
                          meta={"title": TITLE, "key": "D major", "meter": "4/4", "bpm": 80, "beat": "quarter"})


if __name__ == "__main__":
    render()
