"""Title — "Hallowed Lanterns" (the splash screen; loops, then cross-fades
into arbor). Wonder, not a tune: the hush before something magical.

Straight time: 4/4 at quarter = 80, the eighths grouped 3+3+2. A felt piano
plays a Glass-like broken-chord cycle in steady eighths over a D pedal
(Dmaj9, G6/9, Bm11, A sus, a Lydian Dmaj7#11), and ONE note of the voicing
changes at a time. The melody is not sung on top: it EMERGES as the top
voice of the arpeggio. First the pattern has no top voice; then the top
voice appears once a bar (B A F# A, the tail of the Ember's call); then it
crowns every group of the 3+3+2 and the theme is heard (B A F# A | D C# B A).
Then the top voice withdraws and a solo violin takes the Ember's motif,
long and slow (D - B - A - F# - A, bars to a note), with the violas
answering in canon at the fifth below on the clarinet. Underneath, a
Martinez glass pulse on the 3+3+2 accents with a dotted-eighth echo and a
soft sub; cello pizzicati pluck the D pedal in 3+3+2 and violin pizzicati
answer the glass; a slow Zimmer swell of the organ pedal, distant horns and
low strings far back rises to bar 18 and falls back through a Lydian G major
seventh before the cycle closes, never leaving D.
D (Lydian colours), 24 bars = 72 s.

  bars  0-3   the arpeggio cycle alone, the D pedal, the glass pulse
  bars  4-7   the top voice appears once a bar
  bars  8-15  the theme as the crest of each group; the swell begins
  bars 16-21  solo violin (the motif augmented), clarinet in canon; swell peak
  bars 22-23  G Lydian over D, then D again
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock, chord_at
from hlaudio.sampler import Curve
from hlaudio.orch import Stage, sustain_chords
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop

TITLE = "Hallowed Lanterns"
BAR = 8            # eighths
BARS = 24
BPM_UNIT = 160     # eighths per minute (quarter = 80)
LOOP = BARS * BAR * 60 / BPM_UNIT  # 72 s

G69 = "G6add9/D"
# (chord, inner voicing of the arpeggio, melody top voice or None)
PLAN = [
    ("Dmaj9", [66, 69, 73, 76], None), ("Dmaj9", [66, 69, 73, 76], None),
    (G69, [67, 69, 71, 76], None), (G69, [67, 69, 71, 76], None),
    (G69, [67, 69, 71, 76], 83), ("Dmaj9", [66, 69, 73, 76], 81),             # B5 A5
    ("Bm11/D", [66, 69, 71, 76], 78), ("Asus4/D", [64, 69, 71, 76], 81),        # F#5 A5
    (G69, [64, 67, 71, 76], 83), ("Dmaj9", [64, 66, 69, 76], 81),               # B5 A5
    ("Bm11/D", [64, 66, 71, 76], 78), ("Dmaj7#11", [64, 68, 71, 73], 81),       # F#5 A5 (G# inside)
    (G69, [64, 67, 71, 74], 86), ("Dmaj9", [64, 66, 69, 74], 85),               # D6 C#6
    ("Bm11/D", [64, 66, 71, 74], 83), ("Asus4/D", [64, 69, 71, 74], 81),        # B5 A5
    (G69, [64, 67, 71, 74], None), (G69, [64, 67, 71, 74], None),
    ("Dmaj9", [64, 66, 69, 74], None), ("Bm11/D", [64, 66, 71, 74], None),
    ("Asus4/D", [64, 69, 71, 74], None), ("Dmaj7#11", [64, 68, 71, 73], None),
    ("Gmaj7#11/D", [64, 67, 71, 73], None), ("Dadd9", [64, 66, 69, 74], None),
]
JUMP = set()
# the 3+3+2 patterns (indexes into the 4 inner voices; 4 = the top voice)
PAT_A = [0, 1, 2, 3, 2, 1, 2, 3]          # no top voice
PAT_B = [0, 1, 2, 3, 2, 1, 4, 3]          # the top voice once a bar, on the third accent
PAT_C = [0, 2, 4, 1, 3, 4, 2, 4]          # the top voice crowns every group
ACC = [1.0, .72, .8, .95, .72, .8, .92, .75]


def bar(b):
    return b * BAR


def harmony():
    return prog(" ".join(f"{c}:{BAR}" for c, _, _ in PLAN))


def arpeggio():
    """One note of the inner voicing changes per group (bar start, then the
    second and third accents), towards the bar's target."""
    out = []
    cur = list(PLAN[-1][1])
    for b, (sym, target, top) in enumerate(PLAN):
        pat = PAT_A if top is None else (PAT_B if b < 8 else PAT_C)
        if b in JUMP:
            cur = list(target)
        for i, idx in enumerate(pat):
            if i in (0, 3, 6) and cur != target:
                diffs = [(abs(c - g), k) for k, (c, g) in enumerate(zip(cur, target)) if c != g]
                _, k = min(diffs)
                cur[k] = target[k]
            t = bar(b) + i
            if idx == 4:
                v = (0.44 if b < 8 else 0.5) * (1.06 if i == 6 else 1.0)
                d = 2.6 if b >= 8 else 2.2
                out.append(N(t, d, float(top), v, {"top": True}))
            else:
                out.append(N(t, 2.2, float(cur[idx]), 0.4 * ACC[i]))
    return out


def score():
    pr = harmony()
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6
    P = {}
    P["arp"] = arpeggio()
    # left hand: the D pedal, low octave every two bars (B-flat under the mediant)
    lh = []
    for b in range(0, BARS, 2):
        lo = 38
        lh += [N(bar(b), bar(2) + 1, float(lo), 0.42), N(bar(b) + 4, bar(2) - 3, float(lo + 12), 0.3)]
    P["lh"] = lh
    # the solo violin: the Ember's motif augmented, D (pickup) - B - A - F# - A
    P["solo"] = [N(bar(15) + 4, 4, 74.0, 0.55), N(bar(16), bar(2), 83.0, 0.62), N(bar(18), bar(1), 81.0, 0.6),
                 N(bar(19), bar(1), 78.0, 0.56), N(bar(20), bar(2) + 4, 81.0, 0.6)]
    # the clarinet answers in canon at the fifth below: G - E - D - B - D
    P["vla"] = [N(bar(17) + 4, 4, 67.0, 0.5), N(bar(18), bar(2), 76.0, 0.55), N(bar(20), bar(1), 74.0, 0.52),
                N(bar(21), bar(1), 71.0, 0.5), N(bar(22), bar(1) + 4, 74.0, 0.48)]
    # the swell: low strings (re-bowed every 8 bars, wrapping the loop), basses, organ, horns
    P["vc"] = [N(bar(b), bar(8) + 4, float(p), 0.5) for b in (4, 12, 20) for p in (38, 45)]
    P["cb"] = [N(bar(9), bar(15) + 2, 38.0, 0.5)]
    # pizzicato under the pedal (3+3+2: D, A, D) and plucks answering the glass pulse
    pz = []
    for b in range(4, 22):
        pz += [N(bar(b), 1.5, 38.0, 0.55), N(bar(b) + 3, 1.5, 45.0, 0.42), N(bar(b) + 6, 1.0, 50.0, 0.45)]
    P["vc_pizz"] = pz
    ans = []
    for b in range(8, 22, 2):
        ans += [N(bar(b) + 1, 0.8, 81.0, 0.38), N(bar(b) + 4, 0.8, 78.0, 0.34), N(bar(b) + 7, 0.8, 76.0, 0.34)]
    P["vn_pizz"] = ans
    P["org_ped"] = [N(bar(b), bar(8) + 2, 38.0, 0.5) for b in (2, 10, 18)]
    P["org_full_ped"] = [N(bar(12), bar(10), 26.0, 0.55)]
    P["org"] = sustain_chords(pr, 57, 69, 3, vel=0.5, overlap=0.5, start=bar(12), end=bar(23))
    P["hn1"] = [N(bar(13), bar(4), 62.0, 0.5), N(bar(17), bar(5), 64.0, 0.55), N(bar(22), bar(2), 66.0, 0.45)]
    P["hn2"] = [N(bar(13), bar(10) + 4, 57.0, 0.5)]
    # Martinez glass pulse on the 3+3+2 accents; soft sub on the first two
    gp = []
    for b in range(BARS):
        for pos, p in ((0, 74.0), (3, 81.0), (6, 76.0)):
            gp.append(N(bar(b) + pos, 1.0, p, 0.42 if pos == 0 else 0.34))
    P["glass"] = gp
    P["sub"] = [N(bar(b) + pos, 1.5, 26.0, 0.55 if pos == 0 else 0.42) for b in range(4, 22) for pos in (0, 3)]
    P["air"] = [N(bar(10), bar(12), 93.0, 0.25)]
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.008: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.42), (sec(4), 0.46), (sec(8), 0.54), (sec(12), 0.62), (sec(16), 0.74), (sec(18), 0.84),
                 (sec(20), 0.8), (sec(22), 0.6), (sec(23.5), 0.46), (LOOP, 0.42)], period=LOOP)
    swell = Curve([(0, 0.22), (sec(8), 0.24), (sec(12), 0.42), (sec(16), 0.7), (sec(18.5), 0.9), (sec(20.5), 0.76),
                   (sec(22.5), 0.38), (LOOP, 0.22)], period=LOOP)
    st = Stage(LOOP, circular=True)
    shape = {"attack": 0.7, "swell": 0.2, "taper": 2.5}

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
    st.play("solo_violin", S(P["solo"], 4, 0.01), "solo_violin", seed=4, gain_db=3,
            dyn=Curve([(sec(15.5), 0.42), (sec(17), 0.6), (sec(18.5), 0.68), (sec(21), 0.62), (sec(22.4), 0.38)]),
            shape=shape, legato=True, slide=0.12, lag=0.02)
    st.play("clarinets", S(P["vla"], 5, 0.01), "clarinet", seed=5, gain_db=3,
            dyn=Curve([(sec(17.5), 0.4), (sec(19), 0.58), (sec(21), 0.55), (sec(23.4), 0.3)]),
            shape=shape, legato=True, lag=0.02)
    # the low strings stay soft and far back, under the organ
    st.play("cellos", S(P["vc"], 6), "cellos", seed=6, dyn=swell, gain_db=-9, depth=0.78, shape=shape, lag=0.03)
    st.play("basses", S(P["cb"], 7), "basses", seed=7, dyn=swell, gain_db=-11, depth=0.8, shape=shape, lag=0.03)
    vp = S(P["vc_pizz"], 16, 0.006)
    for n in vp:
        n.v = float(n.v * (0.65 + 0.5 * swell(n.t)))
    st.play("cellos_pizz", vp, "cellos_pizz", seed=16, gain_db=5, seat="cellos")
    st.play("violins_pizz", S(P["vn_pizz"], 17, 0.006), "violins_pizz", seed=17, gain_db=6, seat="violins")
    st.play("organ", S(P["org_ped"], 8, 0.0), "organ_soft_pedal", seed=8, dyn=swell, gain_db=-7)
    st.play("organ", S(P["org_full_ped"], 9, 0.0), "organ_pedal", seed=9,
            dyn=Curve([(sec(12), 0.15), (sec(17), 0.6), (sec(20), 0.6), (sec(22), 0.15)]), gain_db=-11)
    st.play("organ", S(P["org"], 10, 0.0), "organ_soft", seed=10, dyn=swell, gain_db=-14)
    st.stems["organ"].buf = FX.tremulant(st.stems["organ"].buf, 5.0, 0.03, 0.08, circular=True).astype("float32")
    st.play("horns", S(P["hn1"], 11), "horns", seed=11, dyn=swell, gain_db=-5, shape=shape, lag=0.03)
    st.play("horns", S(P["hn2"], 12), "horns", seed=12, dyn=swell, gain_db=-8, shape=shape, lag=0.03)

    gl = st.stem("glass", {"shimmer:cathedral2": 0.35, "concert": 0.55}, depth=0.65)
    gp = S(P["glass"], 13, 0.0)
    for n in gp:
        n.v = float(n.v * (0.7 + 0.5 * arc(n.t)))
        n.x["attack"] = 0.03
        n.x["release"] = 1.1
    EL.glass(gl, gp, gain=0.4, seed=13, bright=0.5, pan_spread=0.35, breath=0.05)
    EL.glass(gl, S(P["air"], 14, 0.0), gain=0.22, seed=14, attack=3.0, release=5.0, bright=0.4)
    gl.buf = FX.eq(gl.buf.astype(np.float64), ("lp", 4200, 0.7), circular=True)
    gl.buf = (gl.buf + FX.echo(gl.buf, clk.s(1.5), fb=0.38, mix=0.32, lp=2200, circular=True)).astype("float32")
    sb = st.stem("sub", {}, depth=0.3)
    sub = S(P["sub"], 15, 0.0)
    for n in sub:
        n.v = float(n.v * (0.55 + 0.5 * swell(n.t)))
    EL.sub_pulse(sb, sub, gain=0.4, seed=15, decay=0.35)

    out = st.render({"concert": {"seed": 1}, "cathedral2": {"seed": 2},
                     "shimmer:cathedral2": {"seed": 3, "gens": 2, "fb": 0.4}}, warmth=0.35)
    return finish_loop("music", "title", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 80, "meter": "4/4", "beat": "quarter", "key": "D lydian",
                             "instrument": "piano", "theme": True})


if __name__ == "__main__":
    render()
