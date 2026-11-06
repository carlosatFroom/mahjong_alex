"""Engine-computed facts for the coach, built only from the human's view."""

from collections import Counter

from .matcher import Holding, best_per_hand, choose_discards, missing_tiles
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


def _uses(binding, tile, have):
    """True if every copy of `tile` the player holds counts toward `binding`."""
    return any(code == tile and have.get(tile, 0) <= n for code, n in binding.groups)


def closest_hands(card, view, count=3):
    holding = _holding(view)
    have, jokers = holding.counts()
    out = []
    for n, b in best_per_hand(card, holding, _visible(view), count):
        missing = missing_tiles(b, have, 0, holding.exposed_groups())  # raw; jokers noted separately
        out.append({
            "hand_id": b.hand.id,
            "hand": b.hand.display,
            "points": b.hand.points,
            "concealed": b.hand.concealed,
            "tiles_needed": n,
            "jokers_held": jokers,
            "your_version": b.describe(),
            "missing": [{"tile": tile_name(code), "count": m, "joker_ok": ok,
                         "more": have.get(code, 0) > 0}
                        for code, m, ok in missing],
            "_binding": b,
        })
    return out


def _why(tile, hands, have):
    users = [i for i, h in enumerate(hands, 1) if _uses(h["_binding"], tile, have)]
    if not users:
        return f"none of your {len(hands)} closest hands uses it"
    names = ", ".join(f"#{i}" for i in users)
    return f"only hand {names} uses it" if len(users) < len(hands) else \
        "every close hand uses it, but it is the tile you'll miss least"


def hint_facts(card, view):
    """Facts for the Hint button: closest hands plus a reasoned pass/discard/call suggestion."""
    hands = closest_hands(card, view)
    facts = {"closest_hands": hands}
    if view.get("dead"):
        facts["dead"] = True
        return facts
    prompt = view.get("prompt") or {}
    holding = _holding(view)
    have, _ = holding.counts()
    if prompt.get("type") in ("pass", "courtesy"):
        k = 3 if prompt["type"] == "pass" else min(3, prompt.get("max") or 0)
        if k:
            tiles = choose_discards(card, holding, k)
            facts["suggest_pass"] = [{"tile": tile_name(t), "why": _why(t, hands, have)} for t in tiles]
    elif prompt.get("type") == "discard":
        tile = choose_discards(card, holding, 1, _visible(view))
        if tile:
            facts["suggest_discard"] = {"tile": tile_name(tile[0]), "why": _why(tile[0], hands, have)}
    elif prompt.get("type") == "call":
        facts["call"] = _call_advice(hands, prompt["tile"])
    return facts


def _call_advice(hands, tile):
    name = tile_name(tile)
    if not hands:
        return f"Pass on the {name}: no hand on the card fits your exposures."
    best = hands[0]
    b = best["_binding"]
    group = next(((c, n) for c, n in b.groups if c == tile and n >= 3), None)
    if group is None:
        return f"Pass on the {name}: your closest hand ({best['hand']}) has no pung or kong of it."
    if best["concealed"]:
        return (f"Think twice: {best['hand']} uses {name}, but it is a concealed hand, "
                f"so exposing would rule it out. Pass unless you switch hands.")
    kind = {3: "pung", 4: "kong", 5: "quint", 6: "sextet"}[group[1]]
    return f"Call it: the {name} {kind} is part of your closest hand, {best['hand']}."


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
    """The hint, written by the engine. Every statement here is computed, not generated."""
    lines = []
    if facts.get("dead"):
        lines.append("Your hand is dead: your exposures fit no hand on the card. "
                     "Play defensively and avoid discarding tiles other players need.")
    if facts.get("suggest_discard"):
        d = facts["suggest_discard"]
        lines.append(f"Suggested discard: {d['tile']} — {d['why']}.")
    if facts.get("suggest_pass"):
        tiles = ", ".join(f"{p['tile']} ({p['why']})" for p in facts["suggest_pass"])
        lines.append(f"Suggested pass: {tiles}.")
    if facts.get("call"):
        lines.append(facts["call"])
    hands = facts.get("closest_hands", [])
    if hands:
        lines.append("\nYour closest hands:")
    for i, h in enumerate(hands, 1):
        kind = "concealed" if h["concealed"] else "exposed OK"
        need = ", ".join(
            (f"{m['count']} more {m['tile']}" if m["more"] else f"{m['count']}× {m['tile']}")
            + (" (joker OK)" if m["joker_ok"] else "")
            for m in h["missing"]) or "nothing — call Mahjong!"
        jok = sum(m["count"] for m in h["missing"] if m["joker_ok"])
        joker_note = ""
        if h["jokers_held"] and jok:
            use = min(h["jokers_held"], jok)
            joker_note = f" (your {h['jokers_held']} joker(s) can cover {use} of the joker-OK tiles)"
        lines.append(f"#{i} {h['hand']} [{h['hand_id']}, {h['points']} pts, {kind}]\n"
                     f"   your version: {h['your_version']}\n"
                     f"   {h['tiles_needed']} away{joker_note} — need {need}")
    return "\n".join(lines)
