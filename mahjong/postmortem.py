"""Turn the recorded decisions of a finished game into a post-mortem. Engine-written, no I/O."""

from collections import Counter

from .coach_facts import FEEDBACK_THRESHOLD, pct
from .tiles import tile_name

COLLAPSE_MIN_DROP = 0.05   # odds points
SWITCH_MIN_ODDS = 0.02     # ignore "switches" between hands that were both hopeless
KEY_MOMENTS = 3
EMPTY = "Nothing to review yet."


def _odds_of(entry, hand_id):
    return next((h["odds"] for h in entry["hands"] if h["id"] == hand_id), 0.0)


def _hand(entry, hand_id):
    return next((h for h in entry["hands"] if h["id"] == hand_id), None)


def _newly_shown(a, b):
    """[(name, code)] tiles other players put on the table between entries a and b."""
    before_total = sum((Counter(v) for v in a["visible_by"].values()), Counter())
    after_total = sum((Counter(v) for v in b["visible_by"].values()), Counter())
    new = after_total - before_total   # a called discard moves, it is not new
    out = []
    for name, tiles in b["visible_by"].items():
        diff = Counter(tiles) - Counter(a["visible_by"].get(name, {}))
        for code, n in sorted(diff.items()):
            take = min(n, new[code])
            new[code] -= take
            out += [(name, code)] * take
    return out


def _collapses(history):
    out = []
    for a, b in zip(history, history[1:]):
        if not a["hands"]:
            continue
        top = a["hands"][0]
        now = _odds_of(b, top["id"])
        if top["odds"] - now < COLLAPSE_MIN_DROP or now > top["odds"] / 2:
            continue
        needed = {c for c, _ in top["missing"]}
        culprits = [(n, c) for n, c in _newly_shown(a, b) if c in needed]
        if not culprits:
            continue
        by = Counter(culprits)
        shown = "; ".join(f"{n} put out {k}× {tile_name(c)}" if k > 1 else f"{n} put out {tile_name(c)}"
                          for (n, c), k in by.items())
        out.append({"type": "collapse", "at": b["label"], "impact": top["odds"] - now,
                    "text": f"{shown}. {top['display']} needed it and fell from "
                            f"{pct(top['odds'])} to {pct(now)}."})
    return out


def _switches(history):
    out, last = [], None
    for e in history:
        if e["kind"] != "discard" or not e.get("played") or not e["hands"]:
            continue
        top = e["hands"][0]
        played = _hand(e, e["played"])
        pair = (played["id"], top["id"]) if played else None
        cost_to_top = top["odds"] - (e.get("after") or [top["odds"]])[0]
        if (played and played["id"] != top["id"] and top["odds"] >= SWITCH_MIN_ODDS
                and played["odds"] < top["odds"] / 2 and cost_to_top >= FEEDBACK_THRESHOLD):
            if pair != last:
                out.append({"type": "switch", "at": e["label"], "impact": top["odds"] - played["odds"],
                            "text": f"You {e['action']}, protecting {played['display']} "
                                    f"({pct(played['odds'])}) while {top['display']} was "
                                    f"{pct(top['odds'])} likely. The odds favoured switching."})
            last = pair
        else:
            last = None
    return out


def _costly(history):
    return [{"type": "costly", "at": e["label"], "impact": e["loss"], "text": e["feedback"]}
            for e in history
            if e["kind"] == "discard" and e.get("feedback") and e.get("loss", 0) >= FEEDBACK_THRESHOLD]


def _hindsight(history):
    last = history[-1]
    discards = [e for e in history if e["kind"] == "discard" and e.get("played")]
    hand_id = discards[-1]["played"] if discards else (last["hands"][0]["id"] if last["hands"] else None)
    source = discards[-1] if discards else last
    hand = _hand(source, hand_id) if hand_id else None
    if not hand:
        return None
    lines = []
    for code, m in hand["missing"]:
        where = source["hidden"].get(code)
        if not where:
            continue
        spots = [f"{n} in {name}'s rack" for name, n in where["seats"].items()]
        if where["wall"]:
            spots.append(f"{where['wall']} still in the wall")
        lines.append(f"{m}× {tile_name(code)}: " + (", ".join(spots) or
                     "every copy was already on the table; only jokers could help"))
    name = f"{hand['display']} ({hand['version']})" if hand.get("version") else hand["display"]
    return {"hand": name, "at": source["label"], "lines": lines}


def build(history, result, names, human):
    """The post-mortem as JSON-ready data."""
    if result.get("wall_game"):
        summary = "Wall game: nobody won."
    elif result.get("winner") == human:
        summary = f"You won with {result['hand']}."
    else:
        summary = f"{names[result['winner']]} won with {result['hand']}."
    if not history:
        return {"summary": summary, "empty": True, "text": EMPTY}
    switches = _switches(history)
    switch_at = {m["at"] for m in switches}
    moments = _collapses(history) + switches + [m for m in _costly(history) if m["at"] not in switch_at]
    order = {e["label"]: i for i, e in enumerate(history)}
    key = sorted(sorted(moments, key=lambda m: -m["impact"])[:KEY_MOMENTS], key=lambda m: order[m["at"]])
    flagged = {m["at"] for m in moments}
    timeline = [{"at": e["label"], "action": e["action"],
                 "top": (f"{e['hands'][0]['display']} {pct(e['hands'][0]['odds'])}"
                         if e["hands"] else "no hand within reach"),
                 "flag": e["label"] in flagged}
                for e in history]
    return {"summary": summary, "empty": False, "key_moments": key, "moments": moments,
            "timeline": timeline, "hindsight": _hindsight(history)}
