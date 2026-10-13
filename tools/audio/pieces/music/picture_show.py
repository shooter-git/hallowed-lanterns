"""The Picture Show — a storybook film cue for the shadow-puppet screen.

The film is 64 s in four 16 s scenes and loops; the projector starts it at
0 together with this music. At quarter = 120 every scene is exactly 8 bars
of 4/4, and the cue is two passes of the film (128 s): the second pass is
reorchestrated, not repeated. D major throughout; each scene has its own
colour inside the key (B minor for the woods, a Mixolydian C for the giant),
with no key changes.

  pass A  pass B   film     scene
  0-7     32-39    0-16 s   MOONRISE. A warm cinema-piano cycle (harp in pass
                            B) in 3+3+2 eighths with glass rising like the
                            moon; at bar 4 (8 s) the Ember hops out: the
                            motif pops out in pizzicato and glockenspiel
                            (marimba and viola pizzicato in B), then it
                            bounces (pizzicato, then piano).
  8-15    40-47    16-32 s  INTO THE WOODS. A pizzicato walking bass on
                            tiptoe, the clarinet (bassoon in B) singing the
                            motif's shape down through Bm9, G Lydian and Em9,
                            soft viola pizzicati off the beat, a flute
                            'hoo-hoo' for the owl and pizzicato flurries
                            sweeping across for the bats. Mysterious, never
                            scary.
  16-23   48-55    32-48 s  THE GIANT. Footsteps on 1 and 3 (cello
                            pizzicato, staccato tuba, a soft timpani), the
                            motif in AUGMENTATION in the trombones and horns
                            (tuba and trombones with a horn counterline in B),
                            a playful staccato bassoon answering with the
                            motif in eighths, over D - C/D - G/D; the Ember's
                            little marimba ping between the horns.
  24-31   56-63    48-64 s  THE WEB AND THE MOON. The spider lowers in a
                            descending pizzicato line on a gliding glass
                            thread; mock tension at bars 26-27 (52-56 s) in
                            light spiccato sixteenths and a timpani roll;
                            at bar 28 (56 s) a harp glissando and the flute
                            (the oboe in B) rises with the motif up to a
                            high D - into the moon - and it resolves on
                            D major 9 by 63 s, the piano cycle returning.
"""
import numpy as np

from hlaudio.score import N, seq, prog, humanize, Clock, chord_pcs
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop
from hlaudio import lead as LD

TITLE = "The Picture Show"
BAR = 8            # eighths
BARS = 64
BPM_UNIT = 240     # eighths per minute (quarter = 120): a bar is 2 s, a scene 16 s
LOOP = BARS * BAR * 60 / BPM_UNIT  # 128 s
MX = PR.Mode(50, "mixolydian")     # the giant's D Mixolydian, from D3

MOON = [("Dmaj9", 2), ("Gmaj9/D", 2), ("Dadd9", 1), ("Bm7", 1), ("G6", 1), ("A7sus4", 1)]
WOODS = [("Bm9", 2), ("Gmaj7#11", 2), ("Em9", 2), ("F#m7", 1), ("A7sus4", 1)]
GIANT = [("D", 2), ("C/D", 2), ("G/D", 2), ("D", 1), ("Dsus4", 1)]
WEB = [("Em9", 2), ("F#m7/E", 1), ("Em9", 1), ("Gmaj9", 1), ("A7sus4", 1), ("Dmaj9", 2)]
FILM = MOON + WOODS + GIANT + WEB
PLAN = FILM + FILM
CYC = [0, 1, 2, 3, 2, 1, 2, 3]
CYC_B = [0, 2, 1, 3, 2, 1, 3, 2]
ACC = [1.0, .72, .8, .95, .72, .8, .92, .75]


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{b * BAR}" for c, b in PLAN))


def chord_of_bar():
    out = []
    for c, b in PLAN:
        out += [c] * b
    return out


def lead(cur, sym, lo=62, hi=76):
    """The 4-note voicing of `sym` in lo..hi that moves least from `cur` while
    keeping the chord's colour tones (all but root and fifth)."""
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


def cycle(b0, b1, pattern, vel=0.42):
    """Glass-style broken-chord cycle in eighths (3+3+2 accents); one voice of
    the voicing moves at each group towards the bar's chord."""
    cb = chord_of_bar()
    cur = lead([66, 69, 73, 76], cb[b0])
    out = []
    for b in range(b0, b1):
        target = lead(cur, cb[b])
        for i, idx in enumerate(pattern):
            if i in (0, 3, 6) and cur != target:
                cand = [(target[k] in cur, abs(c - g), k) for k, (c, g) in enumerate(zip(cur, target)) if c != g]
                k = min(cand)[2]
                cur[k] = target[k]
                cur.sort()
            out.append(N(bar(b) + i, 2.0, float(cur[idx]), vel * ACC[i]))
    return out


ROOT = {"Dmaj9": 38, "Gmaj9/D": 38, "Dadd9": 38, "Bm7": 35, "G6": 31, "A7sus4": 33, "Bm9": 35, "Gmaj7#11": 31,
        "Em9": 40, "F#m7": 42, "D": 38, "C/D": 38, "G/D": 38, "Dsus4": 38, "F#m7/E": 40, "Gmaj9": 31}


def moonrise(o, B):
    P = {}
    P["cyc"] = cycle(o, o + 8, CYC_B if B else CYC, 0.44)
    P["lh"] = [N(bar(o + b), bar(1) if b >= 4 else bar(2), float(ROOT[chord_of_bar()[o + b]]), 0.42)
               for b in (0, 2, 4, 5, 6, 7)]
    rise = (69, 74, 78, 81) if not B else (74, 81, 86, 90)
    P["glass"] = [N(bar(o + k), bar(8 - k) - 2, float(p), 0.3) for k, p in enumerate(rise)]
    # the Ember hops out at bar 4 (8 s): the motif, D | B A F# A
    hop = seq("D5:1 B5:2 A5:1 F#5:1 A5:2", bar(o + 4) - 1, vel=0.62)
    P["hop"] = hop
    # ... and bounces, slower and lower each time (a ball coming to rest)
    bounce = []
    for b, pitches in ((5, (78, 81)), (6, (74, 79)), (7, (76, 81))):
        ts = [0.0, 1.6, 2.9, 3.9, 4.6, 5.1]
        for k, t in enumerate(ts):
            bounce.append(N(bar(o + b) + t, 0.8, float(pitches[k % 2]), 0.52 * (1 - 0.1 * k)))
    P["bounce"] = PR.fit(bounce, harmony())
    P["vc_pz"] = [N(bar(o + b), 2.0, float(ROOT[chord_of_bar()[o + b]] + 12), 0.5) for b in range(4, 8)] + \
        [N(bar(o + b) + 4, 2.0, float(ROOT[chord_of_bar()[o + b]] + 19), 0.38) for b in range(4, 8)]
    return P


WALK = ["B2 C#3 D3 F#3", "E3 D3 C#3 A2", "G2 A2 B2 D3", "C#3 B2 A2 F#2",
        "E2 F#2 G2 B2", "D3 B2 A2 G2", "F#2 A2 C#3 E3", "A2 B2 C#3 E3"]
WOODS_MEL = ("F#4:2 D5:4 C#5:2 A4:2 C#5:6 | E4:2 C#5:4 B4:2 G4:2 B4:6 | "
             "D4:2 B4:4 A4:2 F#4:2 A4:6 | C#5:6 B4:2 A4:8")
WOODS_COUNTER = "D5:16 | C#5:16 | B4:16 | C#5:8 D5:8"


def woods(o, B):
    P = {}
    walk = []
    for b, line in enumerate(WALK):
        walk += seq(" ".join(f"{p}:2" for p in line.split()), bar(o + b), vel=0.55)
    for k, n in enumerate(walk):
        n.v *= (1.0 if k % 4 == 0 else 0.8)
    if B:   # the walk hocketed: cellos on 1 and 3, violas (an octave up) on 2 and 4
        P["walk_vc"] = [n for k, n in enumerate(walk) if k % 2 == 0]
        P["walk_vla"] = [N(n.t, n.d, n.p + 12, n.v * 0.9) for k, n in enumerate(walk) if k % 2 == 1]
    else:
        P["walk_vc"] = walk
        P["walk_vla"] = []
    cb = chord_of_bar()
    tip = []
    for b in range(8):
        pcs, _, _ = chord_pcs(cb[o + b])
        mids = sorted(p for p in range(62, 74) if p % 12 in pcs)[:2]
        tip += [N(bar(o + b) + 3, 0.8, float(p), 0.36) for p in mids] + \
            [N(bar(o + b) + 7, 0.8, float(p), 0.32) for p in mids]
    P["tip"] = tip if not B else [n for n in tip if int(n.t) % BAR == 7]
    mel = seq(WOODS_MEL, bar(o), vel=0.55)
    if B:
        P["bsn_mel"] = [N(n.t, n.d, n.p - 12, n.v) for n in mel]
        P["cl"] = seq(WOODS_COUNTER, bar(o), vel=0.42)
    else:
        P["cl"] = mel
        P["bsn_mel"] = []
    hoots = ((3, 4), (6, 4)) if not B else ((4, 0), (6, 6))      # bars 11 and 14 of the film (22 s, 28 s)
    P["owl"] = []
    for hb, pos in hoots:
        t = bar(o + hb) + pos
        P["owl"] += [N(t, 1.4, 81.0, 0.42), N(t + 2, 2.6, 78.0, 0.38)]
    # bats: pizzicato flurries sweeping across the screen
    bats = []
    shapes = ([(12, 2, [64, 67, 71, 74, 76, 74, 71, 67], -0.8, 0.8), (13, 5, [83, 81, 79, 76, 74, 71], 0.8, -0.8)]
              if not B else
              [(12, 4, [71, 74, 76, 79, 81, 79, 76, 74, 71], 0.8, -0.8), (13, 1, [67, 71, 74, 79, 74, 71], -0.8, 0.8)])
    for b, pos, ps, p0, p1 in shapes:
        for k, p in enumerate(ps):
            u = k / (len(ps) - 1)
            bats.append(N(bar(o + b - 8) + pos + 0.5 * k, 0.4, float(p), 0.4 + 0.1 * np.sin(np.pi * u),
                          {"pan": p0 + (p1 - p0) * u}))
    P["bats"] = bats
    P["air"] = [N(bar(o), bar(8), 78.0, 0.22)]
    return P


def giant(o, B):
    P = {}
    steps, tuba = [], []
    for b in range(8):
        for q, v in ((0, 0.62), (4, 0.5)):
            steps.append(N(bar(o + b) + q, 2.0, 38.0, v))
            tuba.append(N(bar(o + b) + q, 1.4, 38.0, v * 0.9))
    P["steps"] = steps
    P["tuba_stac"] = tuba if not B else []
    P["timp"] = [N(bar(o + b), 3.0, 38.0, 0.5) for b in (0, 2, 4, 6)]
    aug = seq("D3:4 B3:12 | A3:8 | F#3:8 | A3:16", bar(o), vel=0.62)
    if not B:
        P["tbn"] = aug
        P["hn"] = [N(n.t, n.d, n.p + 12, n.v * 0.85) for n in aug]
        P["tuba_aug"] = []
        P["hn_counter"] = []
    else:
        P["tbn"] = aug
        P["tuba_aug"] = [N(n.t, n.d, n.p - 12, n.v * 0.9) for n in aug]
        P["hn"] = []
        P["hn_counter"] = seq("F#4:16 | G4:16 | B4:16 | A4:16", bar(o), vel=0.5)
    # the playful bassoon: the motif in eighths from each bar's chord root (Mixolydian)
    cb = chord_of_bar()
    bsn = []
    for b in range(6):
        root = {"D": 0, "C/D": -1, "G/D": -4}.get(cb[o + b], 0)
        bsn += PR.realize(PR.cell("P"), MX, root, bar(o + b) + 3, 1.0, vel=0.5, legato=0.7)
    P["bsn"] = bsn
    P["cl_stac"] = [N(n.t, n.d, n.p + 12, n.v * 0.8) for n in bsn] if B else []
    P["ping"] = seq("D6:1 B5:1 A5:2", bar(o + 5) + 4, vel=0.45) + seq("A5:1 F#5:1 A5:2", bar(o + 7) + 4, vel=0.42)
    P["chords_vla"] = []
    for b in range(8):
        pcs, _, _ = chord_pcs(cb[o + b])
        mids = sorted(p for p in range(57, 69) if p % 12 in pcs)[:2]
        P["chords_vla"] += [N(bar(o + b) + 2, 0.8, float(p), 0.36) for p in mids] + \
            [N(bar(o + b) + 6, 0.8, float(p), 0.33) for p in mids]
    P["piano_low"] = [N(bar(o + b), 3.0, 26.0 + 12, 0.45) for b in range(8)] if B else []
    return P


def web(o, B):
    P = {}
    down = seq("B4:2 A4:2 G4:2 F#4:2 | E4:2 D4:2 B3:2 A3:2", bar(o), vel=0.5)
    P["down_vla"] = down if not B else []
    P["down_vc"] = [N(n.t, n.d, n.p - 12, n.v) for n in down] if B else []
    P["thread"] = [N(bar(o), 6, 83.0, 0.4), N(bar(o) + 6, 5, 79.0, 0.38), N(bar(o) + 11, 5, 76.0, 0.36)]
    P["pedal_pz"] = [N(bar(o + b) + q, 2.0, 40.0, 0.5) for b in range(4) for q in (0, 4)]
    acc16 = [1.15, .6, .7, 1.05, .6, .7, .95, .6]
    spic = []
    for b in (2, 3):
        a, c = (64.0, 69.0) if b == 2 else (64.0, 71.0)
        for k in range(16):
            spic.append(N(bar(o + b) + 0.5 * k, 0.4, a if k % 2 == 0 else c, 0.5 * acc16[k % 8] * (0.8 + 0.25 * k / 16)))
    P["spic_vla"] = spic
    P["spic_vn"] = [N(n.t, n.d, n.p + 12, n.v * 0.8) for n in spic if (n.t >= bar(o + 3) or B)]
    P["roll"] = [N(bar(o + 3), bar(1) + 0.2, 40.0, 0.5)]
    P["gliss"] = [N(bar(o + 4) + 0.12 * k, 2.5, float(p), 0.42 + 0.02 * k)
                  for k, p in enumerate([55, 59, 62, 67, 69, 71, 74, 79, 81, 83, 86])]
    rise = seq("D5:2 B5:4 A5:2 | F#5:2 A5:6 | D6:16", bar(o + 4), vel=0.58)
    P["rise"] = rise
    P["halo"] = [N(bar(o + 6), bar(2) - 1, float(p), 0.32) for p in (78, 81, 86)]
    P["hn_soft"] = [N(bar(o + 5), bar(1) + 0.5, 57.0, 0.45), N(bar(o + 5), bar(1) + 0.5, 62.0, 0.42),
                    N(bar(o + 6), bar(2) - 1, 57.0, 0.42), N(bar(o + 6), bar(2) - 1, 66.0, 0.4)]
    P["cyc"] = cycle(o + 6, o + 8, CYC, 0.36)
    P["lh"] = [N(bar(o + 6), bar(2), 38.0, 0.4)]
    return P


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    parts = {}
    for p, B in ((0, False), (32, True)):
        for fn, off in ((moonrise, 0), (woods, 8), (giant, 16), (web, 24)):
            for k, v in fn(p + off, B).items():
                parts.setdefault(f"{fn.__name__}.{k}", []).extend(v)
    return pr, parts


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.15, "swell": 0.15, "taper": 1.5}
    long_ = {"attack": 0.4, "swell": 0.2, "taper": 2.0}
    G = lambda k: P.get(k, [])

    # MOONRISE: piano cycle (A) / harp cycle (B), glass rising, the hop and the bounces
    cyc_a = [n for n in G("moonrise.cyc") if n.t < bar(32)] + G("web.cyc")
    cyc_b = [n for n in G("moonrise.cyc") if n.t >= bar(32)]
    st.play("piano", S(cyc_a, 1, 0.006), "piano", seed=1, gain_db=7, layer_bias=-0.2, release=0.7)
    st.play("harp", S(cyc_b, 2, 0.006), "harp", seed=2, gain_db=1)
    st.play("piano", S(G("moonrise.lh") + G("web.lh"), 3, 0.01), "piano", seed=3, gain_db=4, layer_bias=-0.3,
            release=1.2)
    gl = st.stem("glass", {"shimmer:cathedral2": 0.35, "concert": 0.55}, depth=0.65)
    EL.glass(gl, S(G("moonrise.glass") + G("web.halo"), 4, 0.0), gain=0.32, seed=4, attack=1.5, release=3.0,
             bright=0.5)
    hop = G("moonrise.hop")
    hop_a = [n for n in hop if n.t < bar(32)]
    hop_b = [n for n in hop if n.t >= bar(32)]
    st.play("violins_pizz", S(hop_a, 5, 0.004), "violins_pizz", seed=5, gain_db=2, seat="violins")
    st.play("glock", S([N(n.t, n.d, n.p + 12, 0.3) for n in hop_a], 6, 0.004), "glock", seed=6, gain_db=0)
    st.play("marimba", S(hop_b, 7, 0.004), "marimba", seed=7, gain_db=-1)
    st.play("violas_pizz", S(hop_b, 8, 0.004), "violas_pizz", seed=8, gain_db=2, seat="violas")
    bounce = G("moonrise.bounce")
    st.play("violins_pizz", S([n for n in bounce if n.t < bar(32)], 9, 0.0), "violins_pizz", seed=9, gain_db=-2,
            seat="violins")
    st.play("piano", S([N(n.t, 0.6, n.p, n.v * 0.9) for n in bounce if n.t >= bar(32)], 10, 0.0), "piano",
            seed=10, gain_db=5, release=0.4)
    st.play("cellos_pizz", S(G("moonrise.vc_pz"), 11, 0.006), "cellos_pizz", seed=11, gain_db=1, seat="cellos")

    # WOODS: the tiptoe walk, clarinet / bassoon, the owl, the bats
    st.play("cellos_pizz", S(G("woods.walk_vc"), 12, 0.008), "cellos_pizz", seed=12, gain_db=4, seat="cellos")
    st.play("violas_pizz", S(G("woods.walk_vla") + G("woods.tip"), 13, 0.008), "violas_pizz", seed=13, gain_db=1,
            seat="violas")
    cl = G("woods.cl")
    st.play("clarinets", S(cl, 14, 0.01), "clarinet", seed=14, gain_db=5, shape=shape, lag=0.02,
            dyn=Curve([(0, 0.55)]))
    st.play("bassoon", S(G("woods.bsn_mel"), 15, 0.01), "bassoon", seed=15, gain_db=4, shape=shape, lag=0.02,
            dyn=Curve([(0, 0.55)]))
    st.play("flutes", S(G("woods.owl"), 16, 0.0), "flute_nv", seed=16, gain_db=4,
            shape={"attack": 0.12, "swell": 0.1, "taper": 3.0}, legato=False, dyn=Curve([(0, 0.45)]))
    st.play("bats", S(G("woods.bats"), 17, 0.0), "violins_pizz", seed=17, gain_db=-1, seat="violins", pan=0.0)
    EL.glass(gl, S(G("woods.air"), 18, 0.0), gain=0.2, seed=18, attack=3.0, release=4.0, bright=0.4)

    # THE GIANT: footsteps, augmentation, the playful bassoon, the ping
    stp = S(G("giant.steps"), 19, 0.005)
    st.play("cellos_pizz", stp, "cellos_pizz", seed=19, gain_db=5, seat="cellos")
    st.play("tuba", S(G("giant.tuba_stac"), 20, 0.005), "tuba_stac", seed=20, gain_db=-2)
    st.play("timpani", S(G("giant.timp"), 21, 0.004), "timpani", seed=21, gain_db=-2)
    br = dict(shape=long_, lag=0.03, dyn=Curve([(0, 0.6)]))
    st.play("trombones", S(G("giant.tbn"), 22), "trombones", seed=22, gain_db=3, **br)
    st.play("horns", S(G("giant.hn") + G("giant.hn_counter"), 23), "horns", seed=23, gain_db=3, **br)
    st.play("tuba", S(G("giant.tuba_aug"), 24), "tuba", seed=24, gain_db=1, **br)
    st.play("bassoon", S(G("giant.bsn"), 25, 0.006), "bassoon_stac", seed=25, gain_db=6)
    st.play("clarinets", S(G("giant.cl_stac"), 26, 0.006), "clarinet_stac", seed=26, gain_db=1)
    st.play("marimba", S(G("giant.ping"), 27, 0.004), "marimba", seed=27, gain_db=-4)
    st.play("violas_pizz", S(G("giant.chords_vla"), 28, 0.008), "violas_pizz", seed=28, gain_db=-1, seat="violas")
    st.play("piano", S(G("giant.piano_low"), 29, 0.008), "piano", seed=29, gain_db=3, layer_bias=-0.2)

    # THE WEB AND THE MOON
    st.play("violas_pizz", S(G("web.down_vla"), 30, 0.006), "violas_pizz", seed=30, gain_db=3, seat="violas")
    st.play("cellos_pizz", S(G("web.down_vc") + G("web.pedal_pz"), 31, 0.006), "cellos_pizz", seed=31, gain_db=3,
            seat="cellos")
    th = st.stem("thread", {"concert": 0.5, "shimmer:cathedral2": 0.2}, depth=0.65)
    EL.glass_line(th, S(G("web.thread"), 32, 0.0), gain=0.4, seed=32, glide=0.8, attack=0.6, release=2.0,
                  bright=0.5, pan=0.15)
    sv = S(G("web.spic_vla"), 33, 0.004)
    st.play("violas_spic", sv, "violas_spic", seed=33, gain_db=3, seat="violas")
    st.play("violins_spic", S(G("web.spic_vn"), 34, 0.004), "violins_spic", seed=34, gain_db=3, seat="violins2")
    st.play("timpani", S(G("web.roll"), 35, 0.0), "timpani_roll", seed=35, gain_db=-9, release=0.4,
            dyn=Curve([(sec(27), 0.05), (sec(28), 0.45), (sec(28.05), 0.1), (sec(59), 0.05), (sec(60), 0.5),
                       (sec(60.05), 0.1)]))
    st.play("harp", S(G("web.gliss"), 36, 0.0), "harp", seed=36, gain_db=-1)
    rise = G("web.rise")
    st.play("flutes", S([n for n in rise if n.t < bar(32)], 37, 0.008), "flute", seed=37, gain_db=6, shape=shape,
            lag=0.02, dyn=Curve([(sec(28), 0.5), (sec(30), 0.62), (sec(31.5), 0.45)]))
    st.play("oboe", S([n for n in rise if n.t >= bar(32)], 38, 0.008), "oboe", seed=38, gain_db=7,
            shape=shape, lag=0.02, **LD.lead(st),
            dyn=Curve([(sec(60), 0.5), (sec(62), 0.62), (sec(63.5), 0.45)]))
    st.play("horns", S(G("web.hn_soft"), 39), "horns", seed=39, gain_db=-6, shape=long_, lag=0.03,
            dyn=Curve([(0, 0.5)]))

    out = st.render({"concert": {"seed": 121}, "cathedral2": {"seed": 122}, "chamber": {"seed": 123},
                     "shimmer:cathedral2": {"seed": 124, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "picture-show", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 120, "meter": "4/4", "beat": "quarter", "key": "D major",
                             "instrument": "piano and pizzicato", "filmSeconds": 64})


if __name__ == "__main__":
    render()
