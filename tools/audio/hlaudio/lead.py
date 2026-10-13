"""The melody near, the strings far: where the soundtrack's lines sit on the stage.

The sampled solo violin and the sections' legato lines are the library's weak spot, so every
line the solo violin used to carry is played by the OBOE (VSCO Oboe Vib), and the bowed
strings (sustains, swells, basses, tremolo) stay only as a bed far back in the hall, where
their legato can't be heard. Pizzicato and spiccato are untouched. The placement is made with
distance rather than level:

  * the oboe is near and present: depth 0.12 (dry and bright), a small hall send (0.28 instead
    of the ~0.4 its depth would give), re-tongued note by note (no legato slides), and its tone
    chain with a gentle presence lift (the 3.2 kHz cut of the orchestra's oboe chain eased from
    -3.5 to -1.5 dB: +2 dB of presence);
  * the string bed sits at depth 0.95 (darker, mostly hall, little dry signal), no slides.

Importing this module sets the oboe's tone chain (orch.TONE["oboe"]) for the piece being
rendered; `lead(st)` and `bed()` are the keyword sets for Stage.play (October Snow's slow theme
takes `lead(st, wash=1)`: more hall around it, so its note changes melt into each other).
"""
from __future__ import annotations

from . import orch

LEAD_DEPTH = 0.12
LEAD_SEND = 0.28
BED_DEPTH = 0.95

orch.TONE["oboe"] = dict(soften=0.35, eq=[("peak", 1400, 0.8, -1.5), ("peak", 3200, 0.9, -1.5),
                                          ("hs", 5500, 0.7, -6.0)])


def lead(st, wash=0.0):
    """Stage.play keywords for the oboe's line: near, little hall, note by note. `wash` (0..1) sets
    it a little further into the hall and adds the small room's early reflections, so the joins
    between its notes blur (where the line moves slowly and every note change would show)."""
    sends = {st.hall: LEAD_SEND + 0.32 * wash}
    if wash:
        sends["chamber"] = 0.3 * wash
    return dict(depth=LEAD_DEPTH + 0.18 * wash, sends=sends, legato=False, slide=0)


def bed():
    """Stage.play keywords for a bowed-string bed: far back in the hall, no slides."""
    return dict(depth=BED_DEPTH, slide=0)
