"""Record the human's decisions for the end-of-game post-mortem.

Called by the web app before each human action (not by the engine, so the bot simulator
stays fast). Everything except `hidden` is computed from the human's view; `hidden`
(where missing tiles really were) is read from the full game state and is only ever
shown after the game is over.
"""

from collections import Counter

from .coach_facts import _holding, move_feedback, odds_model
from .matcher import missing_tiles
from .tiles import tile_name

RECORDED = {"pass", "courtesy", "discard", "call", "pass_call"}
HANDS_KEPT = 8
PLAYED_FROM = 5   # a discard "plays" one of this many most likely hands


def _visible_by(view):
    """Tiles each other player has put on the table (discards + exposures), by name."""
    me = view["seat"]
    out = {view["names"][s]: Counter() for s in range(4) if s != me}
    for d in view["discards"]:
        if d["seat"] != me:
            out[view["names"][d["seat"]]][d["tile"]] += 1
    for s, exps in enumerate(view["exposures"]):
        if s != me:
            for e in exps:
                out[view["names"][s]].update(e["tiles"])
    return {name: dict(c) for name, c in out.items()}


def _label(history, prompt, action):
    turn = sum(1 for e in history if e["kind"] == "discard") + 1
    kind = prompt["type"]
    if kind == "pass":
        return f"Charleston ({prompt['charleston']}), pass {prompt['direction']}"
    if kind == "courtesy":
        return "Courtesy pass"
    if kind == "call":
        return f"Call on {tile_name(prompt['tile'])} (before your turn {turn})"
    return f"Your turn {turn}"


def _action_text(prompt, action):
    kind = action["type"]
    if kind in ("pass", "courtesy"):
        tiles = [tile_name(t) for t in action.get("tiles", [])]
        blind = int(action.get("blind", 0) or 0)
        parts = ", ".join(tiles) or "nothing"
        return f"passed {parts}" + (f" + {blind} blind" if blind else "")
    if kind == "discard":
        return f"discarded {tile_name(action['tile'])}"
    if kind == "call":
        return f"called {tile_name(prompt['tile'])}"
    return f"let {tile_name(prompt['tile'])} go"


def _hidden(game, codes):
    out = {}
    for code in codes:
        seats = {game.names[s]: game.hands[s].count(code)
                 for s in range(4) if s != game.human and code in game.hands[s]}
        out[code] = {"wall": game.wall.count(code), "seats": seats}
    return out


def record(card, game, action):
    """Append one decision to game.history before `action` is applied.

    Returns the entry (its "feedback" is the discard feedback to show, or None).
    """
    prompt = game.prompt() or {}
    kind = action.get("type")
    if kind not in RECORDED or prompt.get("type") not in ("pass", "courtesy", "discard", "call"):
        return None
    history = game.__dict__.setdefault("history", [])
    view = game.view_for(game.human)
    model = odds_model(card, view)
    holding = _holding(view)
    have, _ = holding.counts()
    exposed = holding.exposed_groups()
    hands = model.hands(HANDS_KEPT)
    entry = {
        "kind": prompt["type"],
        "label": _label(history, prompt, action),
        "action": _action_text(prompt, action),
        "wall": view["wall_count"],
        "draws": model.draws,
        "dead": bool(view.get("dead")),
        "visible_by": _visible_by(view),
        "hands": [{"id": h.hand.id, "display": h.hand.display, "points": h.hand.points,
                   "odds": h.odds, "needed": h.needed,
                   "missing": [[c, m] for c, m, _ in missing_tiles(h.binding, have, 0, exposed)]}
                  for h in hands],
        "feedback": None,
    }
    if kind == "discard" and action.get("tile") in have and not entry["dead"]:
        tile = action["tile"]
        scores = model.discard_scores()
        totals = {t: sum(v) for t, v in scores.items()}
        best = max(totals, key=totals.get)
        entry.update(tile=tile, best=best, loss=round(totals[best] - totals[tile], 4),
                     after=scores[tile][:PLAYED_FROM])
        entry["played"] = _played(hands, scores[tile])
        entry["feedback"] = move_feedback(card, view, tile, model)
    codes = {c for h in entry["hands"][:PLAYED_FROM] for c, _ in h["missing"]}
    entry["hidden"] = _hidden(game, codes)
    history.append(entry)
    return entry


def _played(hands, after):
    """The hand this discard protected best: highest share of its odds kept."""
    best, key = None, None
    for h, a in zip(hands[:PLAYED_FROM], after):
        if h.odds <= 0:
            continue
        k = (a / h.odds, h.odds)
        if key is None or k > key:
            best, key = h.hand.id, k
    return best
