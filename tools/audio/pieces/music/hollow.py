"""V. Sweet Hollow — "Sugar Rush" (rescored, Glass).

Playful the Philip Glass way: bouncing, interlocking patterns, no jingle. A
marimba cycles broken chords in eighths grouped 3+3+2 against the 4/4 (one
note changes at a time; D Lydian, the G sharp is the sugar). Pizzicato
violins and violas HOCKET the Ember's cell diminished to sixteenths - D B A
F# A - displaced a sixteenth off the beat, so it hops between them. Cello
pizzicati syncopate the bass (1, the and of 2, 4). Flute and clarinet
staccati grow by an additive process (2, 2+3, 2+3+3 ...) on the cell. A
filtered synth pulse and a soft glockenspiel sparkle join; the lift turns
to the relative minor and back (B minor 9, G Lydian, E minor 9, A sus),
staying in the key, with spiccato sixteenths ticking under it; then
everything subtracts back to the marimba.
4/4, quarter = 120 (in sixteenths), 68 bars = 136 s.
"""
import numpy as np

from hlaudio.score import N, prog, humanize, Clock
from hlaudio.sampler import Curve
from hlaudio.orch import Stage
from hlaudio import process as PR
from hlaudio import electro as EL, effects as FX
from hlaudio.piece import finish_loop
from hlaudio import lead as LD

TITLE = "Sugar Rush"
BAR = 16
BARS = 68
BPM_UNIT = 480
LOOP = BARS * BAR * 60 / BPM_UNIT  # 136 s
M = PR.Mode(62, "lydian")  # D with G#

LOOP4 = [("Dmaj7#11", 2, [66, 69, 73, 76]), ("Bm9", 2, [66, 69, 71, 73]),
         ("Gmaj9", 2, [66, 69, 71, 74]), ("Aadd9", 2, [64, 69, 71, 73])]
LIFT = [("Bm9", 2, [66, 69, 73, 74]), ("Gmaj7#11", 2, [66, 69, 71, 73]),
        ("Em9", 2, [66, 67, 71, 74]), ("A7sus4", 2, [64, 67, 69, 74])]
PLAN = LOOP4 * 3 + LIFT + LOOP4 * 4 + [("Dmaj7#11", 4, [66, 69, 73, 76])]   # lift at bars 24-31
BASS = {"Dmaj7#11": 38, "Bm9": 35, "Gmaj9": 31, "Aadd9": 33, "Gmaj7#11": 31, "Em9": 40, "A7sus4": 33}


def bar(b):
    return b * BAR


def score():
    pr = prog(" ".join(f"{c}:{b * BAR}" for c, b, _ in PLAN))
    assert abs(sum(d for _, d, _ in pr) - BARS * BAR) < 1e-6, sum(d for _, d, _ in pr) / BAR
    P = {}
    acc = [1.15, .7, .8, 1.1, .7, .8, 1.05, .7]           # 3+3+2 in eighths
    mar, _ = PR.cycling([(s, b) for _, b, s in PLAN], [0, 2, 3, 1, 2, 3, 0, 2], 2.0, 0.0, 1, vel=0.6,
                        accents=acc, legato=1.2)
    P["marimba"] = mar
    # the cell diminished to sixteenths, displaced a sixteenth, hocketed
    fig = PR.realize(PR.cell("P"), M, 7, 1.0, 1.0, vel=0.6, accents=[1.1, .9, .85, .9, 1.0])
    cell_line = []
    for b in range(4, 60):
        sym = None
        for (t0, d, s) in pr:
            if t0 <= bar(b) < t0 + d:
                sym = s
        for half in (0, 8):
            for n in fig:
                cell_line.append(N(bar(b) + half + n.t, 0.9, n.p, n.v))
    cell_line = PR.fit(cell_line, pr)
    vn, vla = PR.hocket(cell_line, 2)
    P["pz_vn"], P["pz_vla"] = vn, [N(n.t, n.d, n.p - 12, n.v) for n in vla]
    # cello pizzicato: 1, the and of 2, 4
    vc = []
    t = 0.0
    for c, b, s in PLAN:
        for k in range(b):
            for o, dv in ((0, 1.0), (6, 0.75), (12, 0.85)):
                b_ = BASS[c] + (12 if BASS[c] < 36 else 0)          # inside the cellos' range
                vc.append(N(t + bar(k) + o, 3, float(b_ + (12 if o == 6 else 0)), 0.6 * dv))
        t += bar(b)
    P["pz_vc"] = [n for n in vc if bar(2) <= n.t < bar(64)]
    # woodwinds: additive process on the cell, eighths (flute), echoed a beat later (clarinet)
    groups = [2, 2, 3, 3, 2, 3, 3, 2, 3, 3, 4, 4, 5, 5, 4, 3]
    wl, t = [], bar(12)
    while t < bar(56):
        seg, t = PR.additive(PR.cell("P"), groups, M, 14, t, 2.0, vel=0.5, accent=1.25, legato=0.6)
        wl += [n for n in seg if n.t < bar(56)]
    wl = PR.fit(wl, pr)
    P["fl"] = wl
    P["cl"] = [N(n.t + 4, n.d, n.p - 12, n.v * 0.85) for n in wl if n.t + 4 < bar(56)]
    P["glock"] = []
    for b0 in (16, 20, 24, 28, 40, 44, 48):
        P["glock"] += PR.fit(PR.realize(PR.cell("P", 3), M, 14, bar(b0) + 3, [3, 3, 6], vel=0.45), pr)
    arp = PR.ticking([74, 81, 78, 81, 76, 81, 78, 83], bar(20), bar(56), 1.0,
                     [1.0, .55, .7, .55, .9, .55, .7, .55], vel=0.55)
    P["arp"] = PR.fit(arp, pr)
    P["spic"] = PR.fit(PR.ticking([62, 69, 62, 69, 62, 69, 62, 69], bar(22), bar(34), 1.0,
                                  [1.15, .6, .75, .6, 1.05, .6, .75, .6], vel=0.5), pr)
    P["sub"] = [N(bar(b) + q * 4, 3.0, float(BASS[[s for (t0, d, s) in pr if t0 <= bar(b) < t0 + d][0]] - 12), 0.6)
                for b in range(4, 64) for q in range(4)]
    P["vla_sus"] = []
    t = 0.0
    for c, b, s in PLAN:
        if bar(24) <= t < bar(32):
            P["vla_sus"] += [N(t, bar(b) + 0.5, float(p - 12), 0.5) for p in s[1:3]]
        t += bar(b)
    return pr, P


def render():
    pr, P = score()
    clk = Clock(bpm=BPM_UNIT)
    S = lambda notes, seed, j=0.006: humanize(clk.notes(notes), seed, t_jit=j)
    sec = lambda b: clk.s(bar(b))
    arc = Curve([(0, 0.35), (sec(4), 0.42), (sec(12), 0.52), (sec(20), 0.65), (sec(25), 0.85), (sec(31), 0.85),
                 (sec(40), 0.78), (sec(52), 0.65), (sec(62), 0.4), (LOOP, 0.35)], period=LOOP)
    cutoff = Curve([(0, 1200), (sec(20), 1600), (sec(28), 3800), (sec(40), 2600), (sec(56), 1200), (LOOP, 1200)],
                   period=LOOP)
    st = Stage(LOOP, circular=True)

    def shaped(notes, seed, lo=0.6, hi=0.6, j=0.006):
        out = S(notes, seed, j)
        for n in out:
            n.v = float(np.clip(n.v * (lo + hi * arc(n.t)), 0.05, 1))
        return out

    st.play("marimba", shaped(P["marimba"], 1, 0.55, 0.65), "marimba", seed=1, gain_db=4)
    st.play("violins_pizz", shaped(P["pz_vn"], 2), "violins_pizz", seed=2, gain_db=1, seat="violins")
    st.play("violas_pizz", shaped(P["pz_vla"], 3), "violas_pizz", seed=3, gain_db=2, seat="violas")
    st.play("cellos_pizz", shaped(P["pz_vc"], 4), "cellos_pizz", seed=4, gain_db=2, seat="cellos")
    st.play("flutes", shaped(P["fl"], 5), "flute_stac", seed=5, gain_db=-1)
    st.play("clarinets", shaped(P["cl"], 6), "clarinet_stac", seed=6, gain_db=4)
    st.play("glock", shaped(P["glock"], 7, 0.7, 0.4, 0.004), "glock", seed=7, gain_db=0)
    st.play("cellos_spic", shaped(P["spic"], 8), "cellos_spic", seed=8, gain_db=0, seat="cellos")
    st.play("violas", S(P["vla_sus"], 9), "violas", seed=9, dyn=arc, gain_db=-19, **LD.bed(),
            shape={"attack": 0.4, "swell": 0.2, "taper": 2.0}, lag=0.02)
    ar = st.stem("arp", {"concert": 0.45}, depth=0.6)
    EL.arp(ar, shaped(P["arp"], 10, 0.5, 0.6, 0.0), gain=0.45, seed=10, cutoff=cutoff, res=2.2, decay=0.12,
           shape=0.35, pan=0.2, pan_wobble=0.4)
    ar.buf = (ar.buf + FX.echo(ar.buf, 0.375, fb=0.4, mix=0.3, lp=2600, circular=True)).astype("float32")
    sb = st.stem("sub", {}, depth=0.3)
    EL.sub_pulse(sb, shaped(P["sub"], 11, 0.5, 0.6, 0.0), gain=0.5, seed=11, decay=0.3)

    out = st.render({"concert": {"seed": 51}}, warmth=0.35)
    return finish_loop("music", "hollow", out, LOOP, 4, -16.0, 192,
                       meta={"title": TITLE, "bpm": 120, "meter": "4/4", "beat": "quarter", "key": "D lydian",
                             "instrument": "marimba and pizzicato"})


if __name__ == "__main__":
    render()
