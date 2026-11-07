"""Engine-computed facts for the coach, built only from the human's view."""

from .matcher import Holding, missing_tiles
from .odds import TOP_HANDS, OddsModel, draws_left, visible_counts
from .tiles import tile_name

FEEDBACK_THRESHOLD = 0.01  # total odds a discard must lose vs the best one to earn feedback
DRAW_ONLY_NOTE = ("Odds count your own draws only; calling discards can improve "
                  "exposed hands.")

VIEW_KEYS_FOR_COACH = ("seat_wind", "names", "hand", "exposures", "discards", "wall_count",
                       "dead", "phase", "current", "last_discard", "prompt", "charleston_stage")


def coach_view(view):
    """The subset of the human view the coach may use (never `reveal`)."""
    return {k: view[k] for k in VIEW_KEYS_FOR_COACH if k in view}


def _holding(view):
    return Holding(list(view["hand"]), view["exposures"][view["seat"]])


def odds_model(card, view):
    """Completion odds for the human at this moment, from their view only."""
    return OddsModel(card, _holding(view), visible_counts(view), draws_left(view))


def pct(x):
    return "<1%" if 0 < x < 0.01 else f"{round(x * 100)}%"


def _uses(binding, tile, have):
    """True if every copy of `tile` the player holds counts toward `binding`."""
    return any(code == tile and have.get(tile, 0) <= n for code, n in binding.groups)


def closest_hands(card, view, count=3, model=None):
    """The `count` most likely hands, most likely first."""
    model = model or odds_model(card, view)
    holding = _holding(view)
    have, jokers = holding.counts()
    out = []
    for h in model.hands(count):
        n, b = h.needed, h.binding
        missing = missing_tiles(b, have, 0, holding.exposed_groups())  # raw; jokers noted separately
        out.append({
            "hand_id": b.hand.id,
            "hand": b.hand.display,
            "points": b.hand.points,
            "concealed": b.hand.concealed,
            "tiles_needed": n,
            "odds": h.odds,
            "jokers_held": jokers,
            "your_version": b.describe(),
            "missing": [{"tile": tile_name(code), "count": m, "joker_ok": ok,
                         "more": have.get(code, 0) > 0, "unseen": model.unseen[code]}
                        for code, m, ok in missing],
            "_binding": b,
        })
    return out


def _why(tile, hands, have):
    users = [i for i, h in enumerate(hands, 1) if _uses(h["_binding"], tile, have)]
    if not users:
        return f"none of your {len(hands)} most likely hands uses it"
    names = ", ".join(f"#{i}" for i in users)
    return f"only hand {names} uses it" if len(users) < len(hands) else \
        "every likely hand uses it, but losing it costs the least odds"


def hint_facts(card, view, model=None):
    """Facts for the Hint button: closest hands plus a reasoned pass/discard/call suggestion."""
    model = model or odds_model(card, view)
    hands = closest_hands(card, view, model=model)
    facts = {"closest_hands": hands, "draws_left": model.draws}
    if view.get("dead"):
        facts["dead"] = True
        return facts
    prompt = view.get("prompt") or {}
    holding = _holding(view)
    have, _ = holding.counts()
    if prompt.get("type") in ("pass", "courtesy"):
        k = 3 if prompt["type"] == "pass" else min(3, prompt.get("max") or 0)
        if k:
            tiles = model.best_discards(k)
            facts["suggest_pass"] = [{"tile": tile_name(t), "why": _why(t, hands, have)} for t in tiles]
    elif prompt.get("type") == "discard":
        tile = model.best_discards(1)
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
        return f"Pass on the {name}: your most likely hand ({best['hand']}) has no pung or kong of it."
    if best["concealed"]:
        return (f"Think twice: {best['hand']} uses {name}, but it is a concealed hand, "
                f"so exposing would rule it out. Pass unless you switch hands.")
    kind = {3: "pung", 4: "kong", 5: "quint", 6: "sextet"}[group[1]]
    return f"Call it: the {name} {kind} is part of your most likely hand, {best['hand']}."


def move_feedback(card, before_view, tile, model=None):
    """Engine-only note, shown only when the discard lost clearly more odds than the best one.

    Uses the same model and scoring as the Hint, so following the hint never triggers it.
    """
    model = model or odds_model(card, before_view)
    scores = model.discard_scores()
    if tile not in scores:
        return None
    totals = {t: sum(v) for t, v in scores.items()}
    best = max(totals, key=totals.get)
    if totals[tile] >= totals[best] - FEEDBACK_THRESHOLD:
        return None
    hands = model.hands(TOP_HANDS)
    hurt = sorted(((h.odds - after, h, after) for h, after in zip(hands, scores[tile])
                   if h.odds - after >= 0.005), key=lambda x: -x[0])[:2]
    if not hurt:
        return None
    lost = "; ".join(f"{h.hand.display} {pct(h.odds)} → {pct(after)}" for _, h, after in hurt)
    return (f"That {tile_name(tile)} cost you odds: {lost}. "
            f"{tile_name(best)} would have cost less.")


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
        lines.append(f"\nYour most likely hands ({facts.get('draws_left', 0)} draws left):")
    for i, h in enumerate(hands, 1):
        kind = "concealed" if h["concealed"] else "exposed OK"
        need = ", ".join(
            (f"{m['count']} more {m['tile']}" if m["more"] else f"{m['count']}× {m['tile']}")
            + (" (joker OK)" if m["joker_ok"] else "") + f" · {m['unseen']} unseen"
            for m in h["missing"]) or "nothing — call Mahjong!"
        jok = sum(m["count"] for m in h["missing"] if m["joker_ok"])
        joker_note = ""
        if h["jokers_held"] and jok:
            use = min(h["jokers_held"], jok)
            joker_note = f" (your {h['jokers_held']} joker(s) can cover {use} of the joker-OK tiles)"
        lines.append(f"#{i} {h['hand']} — {pct(h['odds'])} likely [{h['hand_id']}, "
                     f"{h['points']} pts, {kind}]\n"
                     f"   your version: {h['your_version']}\n"
                     f"   {h['tiles_needed']} away{joker_note} — need {need}")
    if hands:
        lines.append(DRAW_ONLY_NOTE)
    return "\n".join(lines)
