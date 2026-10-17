"""Tracks edited in HO[LO] Desk, played by the renderer in place of the code's own notes.

A piece's session lives in tools/audio/sessions/<piece>.holo.json. HO[LO] writes it when a song is sent
back from the studio; the tracks it marks `edited` replace their voice's notes in score(), and every
other voice stays as the code writes it. With no session (or no edited track), nothing changes.

render.py wraps each piece's score() with `wrap`, so a piece needs nothing of its own.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .score import N

# HOLO_SESSIONS points elsewhere for a preview HO[LO] asks for (the studio's edits, not yet sent)
SESSIONS = Path(os.environ["HOLO_SESSIONS"]) if os.environ.get("HOLO_SESSIONS") else Path(__file__).resolve().parents[1] / "sessions"
TICKS_PER_EIGHTH = 480


def _doc(piece: str) -> dict | None:
    path = SESSIONS / f"{piece}.holo.json"
    return json.loads(path.read_text()) if path.exists() else None


def edited_voices(piece: str) -> list[dict]:
    """The edited tracks of a piece's session: [{key, part, unpitched, notes: [(t, d, p, v, x)] in eighths}]."""
    doc = _doc(piece)
    if doc is None:
        return []
    out = []
    for track in doc.get("tracks", []):
        origin = track.get("origin") or {}
        extra = origin.get("extra") or {}
        if not origin.get("edited") or origin.get("locked") or "key" not in extra or extra.get("orphan"):
            continue
        notes = []
        for region in track.get("regions", []):
            if region.get("muted"):
                continue
            for n in region.get("notes", []):
                if n["t"] >= region["length"]:
                    continue
                at = region["start"] + n["t"]
                d = min(n["d"], region["length"] - n["t"])
                notes.append((at / TICKS_PER_EIGHTH, d / TICKS_PER_EIGHTH, n["p"], n["v"] / 127, n.get("x") or {}))
        out.append({"key": extra["key"], "part": extra.get("part", ""), "unpitched": bool(extra.get("unpitched")),
                    "name": track.get("name", extra["key"]), "notes": sorted(notes, key=lambda x: x[0])})
    return out


def _slot(P: dict, key: str):
    """The dict and the key that hold a voice ('drums.bd' is P['drums']['bd'])."""
    d = P
    parts = key.split(".")
    for p in parts[:-1]:
        if not isinstance(d.get(p), dict):
            return P, key
        d = d[p]
    return d, parts[-1]


def apply(piece: str, P: dict) -> dict:
    """Replace the edited voices in score()'s dict (in the piece's own unit: eighths, or as the session says)."""
    doc = _doc(piece) or {}
    eighths_per_unit = float(((doc.get("origin") or {}).get("extra") or {}).get("eighthsPerUnit", 1.0))
    for v in edited_voices(piece):
        holder, k = _slot(P, v["key"])
        if k not in holder or not isinstance(holder[k], list):
            print(f"  (HO[LO] session: {piece} has no voice {v['key']!r} any more; skipped)")
            continue
        fresh = []
        for t, d, p, vel, x in v["notes"]:
            x = dict(x)
            exact = x.pop("pitch", None)
            # a note left where it was keeps its exact (microtonal) pitch; one moved in HO[LO] takes its new key
            pitch = 0.0 if v["unpitched"] else float(exact if exact is not None and round(exact) == p else p)
            if v["part"]:
                x["part"] = v["part"]
            fresh.append(N(t / eighths_per_unit, d / eighths_per_unit, pitch, float(vel), x))
        if v["part"]:
            kept = [n for n in holder[k] if n.x.get("part", "") != v["part"]]
            holder[k] = sorted(kept + fresh, key=lambda n: n.t)
        else:
            holder[k] = fresh
        print(f"  HO[LO]: {v['name']} plays the notes edited in the studio ({len(fresh)} notes)")
    return P


def wrap(piece: str, score):
    """score() with the session's edited voices in it. score() returns P, or (progression, P)."""
    if not edited_voices(piece):
        return score

    def edited_score(*args, **kwargs):
        ret = score(*args, **kwargs)
        if isinstance(ret, tuple):
            prog, P = ret
            return prog, apply(piece, P)
        return apply(piece, ret)

    return edited_score
