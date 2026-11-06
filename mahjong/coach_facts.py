"""Engine-computed facts for the coach, built only from the human's view."""

from collections import Counter

from .matcher import Holding, best_per_hand, choose_discards, missing_tiles, ranked
from .tiles import tile_name

VIEW_KEYS_FOR_COACH = ("seat_wind", "names", "hand", "exposures", "discards", "wall_count",
                       "dead", "phase", "current", "last_discard", "prompt", "charleston_stage")


def coach_view(view):
    """The subset of the human view the coach may use (never `reveal`)."""
    return {k: view[k] for k in VIEW_KEYS_FOR_COACH if k in view}


def _visible(view):
    seat = view["seat"]
    c = Counter(d["tile"] for d in view["discards"])
    for s, exps in enumerate(view["exposures"]):
        if s != seat:
            for e in exps:
                c.update(e["tiles"])
    return c


def _holding(view):
    return Holding(list(view["hand"]), view["exposures"][view["seat"]])


def closest_hands(card, view, count=3):
    holding = _holding(view)
    have, jokers = holding.counts()
    out = []
    for n, b in best_per_hand(card, holding, _visible(view), count):
        missing = missing_tiles(b, have, jokers, holding.exposed_groups())
        out.append({
            "hand_id": b.hand.id,
            "hand": b.hand.display,
            "category": b.hand.category,
            "points": b.hand.points,
            "concealed": b.hand.concealed,
            "tiles_needed": n,
            "this_version": b.describe(),
            "missing": [{"tile": tile_name(code), "count": m, "joker_ok": ok}
                        for code, m, ok in missing],
        })
    return out


def hint_facts(card, view):
    """Facts for the Hint button: closest hands plus a pass or discard suggestion."""
    facts = {"closest_hands": closest_hands(card, view)}
    if view.get("dead"):
        facts["dead"] = True
        return facts
    prompt = view.get("prompt") or {}
    holding = _holding(view)
    if prompt.get("type") in ("pass", "courtesy"):
        k = 3 if prompt["type"] == "pass" else min(3, prompt.get("max") or 0)
        if k:
            facts["suggest_pass"] = [tile_name(t) for t in choose_discards(card, holding, k)]
    elif prompt.get("type") == "discard":
        tile = choose_discards(card, holding, 1, _visible(view))
        if tile:
            facts["suggest_discard"] = tile_name(tile[0])
    elif prompt.get("type") == "call":
        facts["call_tile"] = tile_name(prompt["tile"])
        facts["call_helps"] = _call_helps(card, view, prompt["tile"])
    return facts


def _call_helps(card, view, tile):
    holding = _holding(view)
    best = ranked(card, holding, _visible(view), limit=1)
    if not best:
        return False
    n, b = best[0]
    return not b.hand.concealed and any(code == tile and size >= 3 for code, size in b.groups)


def move_feedback(card, before_view, tile):
    """Short engine-only note when a discard broke one of the closest hands."""
    before = _holding(before_view)
    have, jokers = before.counts()
    top = best_per_hand(card, before, _visible(before_view), 3)
    broke = []
    for _, b in top:
        if any(code == tile for code, _ in b.groups) and have.get(tile, 0) <= dict(b.groups)[tile]:
            broke.append(b.hand.display)
    if not broke:
        return None
    hands = "; ".join(broke)
    return (f"That {tile_name(tile)} was part of {len(broke)} of your {len(top)} closest "
            f"hand(s): {hands}.")


def facts_text(facts):
    """Plain-language rendering used when the LLM is unavailable or capped."""
    lines = []
    if facts.get("dead"):
        lines.append("Your hand is dead: your exposures fit no hand on the card. "
                     "Play defensively and avoid feeding other players.")
    for i, h in enumerate(facts.get("closest_hands", []), 1):
        need = ", ".join(f"{m['count']}× {m['tile']}" + (" (joker OK)" if m["joker_ok"] else "")
                         for m in h["missing"]) or "nothing — you have it!"
        kind = "concealed" if h["concealed"] else "exposed OK"
        lines.append(f"{i}. {h['hand']} [{h['hand_id']}, {h['points']} pts, {kind}] "
                     f"— {h['tiles_needed']} tile(s) away. Need: {need}.")
    if facts.get("suggest_pass"):
        lines.append("Suggested pass: " + ", ".join(facts["suggest_pass"]) + ".")
    if facts.get("suggest_discard"):
        lines.append(f"Suggested discard: {facts['suggest_discard']}.")
    if "call_helps" in facts:
        lines.append(f"Calling {facts['call_tile']} " +
                     ("helps your closest hand." if facts["call_helps"]
                      else "does not help your closest hand; consider passing."))
    return "\n".join(lines)
