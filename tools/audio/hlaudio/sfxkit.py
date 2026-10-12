"""Instrument-like sound effects from the VSCO 2 CE samples (xylophone notes,
the big guitar's strings, the Ember's chimes, snowflakes, sparkles).

They use the same sampler, tone chains and hall as the music, but sit much
closer and drier (about 15% of the music's reverb send), because the game
adds its own reverb send to sounds placed in the world."""
from __future__ import annotations

import numpy as np

from .orch import Stage
from . import effects as FX
from .body import stereo_body

SEND = 0.11      # the music's sends are ~0.6-0.95
DEPTH = 0.12


def stage(seconds, hall="concert"):
    return Stage(seconds, circular=False, hall=hall)


def play(st, name, notes, inst, send=SEND, depth=DEPTH, extra=None, **kw):
    sends = {st.hall: send}
    sends.update(extra or {})
    st.play(name, notes, inst, depth=depth, sends=sends, **kw)


def guitar_body(st, name, amount=0.8, seed=0):
    """Turn a plucked harp stem into a big guitar: its strings through a
    guitar body's resonances (blended with the dry string)."""
    tr = st.stems[name]
    ir = stereo_body("guitar", seed)
    x = tr.buf.astype(np.float64)
    wet = np.vstack([FX.convolve(x[0], ir[0], False)[: x.shape[1]], FX.convolve(x[1], ir[1], False)[: x.shape[1]]])
    wet *= np.sqrt(np.mean(x ** 2) / (np.mean(wet ** 2) + 1e-20))
    y = (1 - amount) * x + amount * wet
    tr.buf = FX.eq(y, ("hs", 5000, 0.7, -3.0), ("lp", 9000, 0.7)).astype(np.float32)


def finish(st, opts=None, warmth=0.12):
    if "glock" in st.stems:                  # bells soft: the bar's upper partials further down
        g = st.stems["glock"]
        g.buf = FX.eq(g.buf.astype(np.float64), ("hs", 3000, 0.7, -5.0), ("lp", 5000, 0.7)).astype(np.float32)
    o = {st.hall: {"seed": 5}}
    o.update(opts or {})
    return st.render(o, warmth=warmth, air=None)
