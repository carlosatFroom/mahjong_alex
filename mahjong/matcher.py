"""Match a player's tiles against card bindings.

Jokers may only fill groups of 3 or more identical tiles; singles and pairs need
natural tiles. Exposures must each equal one group of the binding exactly.
"""

from collections import Counter
from dataclasses import dataclass

from .tiles import COPIES, JOKER


@dataclass
class Holding:
    """What one player holds: concealed tiles (incl. jokers) and exposures."""
    concealed: list
    exposures: list  # [{"code": str, "tiles": [codes incl. "J"]}]

    def counts(self):
        c = Counter(self.concealed)
        jokers = c.pop(JOKER, 0)
        return c, jokers

    def exposed_groups(self):
        return [(e["code"], len(e["tiles"])) for e in self.exposures]

    def size(self):
        return len(self.concealed) + sum(len(e["tiles"]) for e in self.exposures)


def needed(binding, have, jokers, exposed):
    """Tiles still missing to complete `binding`, or None if exposures rule it out."""
    if exposed and binding.hand.concealed:
        return None
    groups = binding.groups
    if exposed:
        open_groups = list(groups)
        for g in exposed:
            if g not in open_groups:
                return None
            open_groups.remove(g)
        groups = open_groups
    missing = jokerable = 0
    for code, n in groups:
        m = n - have.get(code, 0)
        if m > 0:
            missing += m
            if n >= 3:
                jokerable += m
    return missing - min(jokers, jokerable)


def missing_tiles(binding, have, jokers, exposed):
    """List of (code, count, joker_ok) still needed for `binding`."""
    exposed = list(exposed)
    out = []
    for code, n in binding.groups:
        if (code, n) in exposed:
            exposed.remove((code, n))
            continue
        m = n - have.get(code, 0)
        if m > 0:
            out.append((code, m, n >= 3))
    spare = jokers
    result = []
    for code, m, joker_ok in out:
        if joker_ok and spare:
            use = min(spare, m)
            spare -= use
            m -= use
        if m:
            result.append((code, m, joker_ok))
    return result


def feasible(binding, have, jokers, exposed, visible):
    """False when the tiles still needed are already all visible elsewhere."""
    exposed = list(exposed)
    joker_short = 0
    for code, n in binding.groups:
        if (code, n) in exposed:
            exposed.remove((code, n))
            continue
        m = n - have.get(code, 0)
        if m <= 0:
            continue
        left = COPIES[code] - have.get(code, 0) - visible.get(code, 0)
        if m > left:
            if n < 3:
                return False
            joker_short += m - left
    jokers_left = COPIES[JOKER] - visible.get(JOKER, 0)
    return joker_short <= jokers_left


def ranked(card, holding, visible=None, limit=None):
    """Bindings sorted by tiles needed (best first), as (needed, binding)."""
    have, jokers = holding.counts()
    exposed = holding.exposed_groups()
    scored = []
    for b in card.bindings:
        n = needed(b, have, jokers, exposed)
        if n is None:
            continue
        if visible is not None and n and not feasible(b, have, jokers, exposed, visible):
            continue
        scored.append((n, -b.hand.points, b))
    scored.sort(key=lambda t: (t[0], t[1]))
    if limit:
        scored = scored[:limit]
    return [(n, b) for n, _, b in scored]


def mahjong(card, holding):
    """Return the highest-value binding the 14 tiles complete, or None."""
    if holding.size() != 14:
        return None
    have, jokers = holding.counts()
    exposed = holding.exposed_groups()
    best = None
    for b in card.bindings:
        if needed(b, have, jokers, exposed) == 0:
            if best is None or b.hand.points > best.hand.points:
                best = b
    return best


def why_not_mahjong(card, holding):
    """Human-readable reason a Mahjong claim fails."""
    if holding.size() != 14:
        return f"A Mahjong hand has 14 tiles; you have {holding.size()}."
    top = ranked(card, holding, limit=1)
    if not top:
        return "Your exposures do not fit any hand on the card."
    n, b = top[0]
    have, jokers = holding.counts()
    missing = missing_tiles(b, have, jokers, holding.exposed_groups())
    need = ", ".join(f"{m}× {code}" for code, m, _ in missing)
    return (f"Not a winning hand. Closest is {b.hand.display} ({b.hand.id}), "
            f"still {n} tile(s) short: {need}.")


def exposures_possible(card, exposures):
    """True if at least one exposed-allowed binding accepts these exposures."""
    groups = [(e["code"], len(e["tiles"])) for e in exposures]
    empty = Counter()
    return any(needed(b, empty, 0, groups) is not None for b in card.bindings)


def best_per_hand(card, holding, visible=None, count=3):
    """Closest bindings, at most one per hand, for hints."""
    out, seen = [], set()
    for n, b in ranked(card, holding, visible):
        if b.hand.id in seen:
            continue
        seen.add(b.hand.id)
        out.append((n, b))
        if len(out) == count:
            break
    return out


def discard_values(card, holding, visible=None, top=8):
    """Score each concealed non-joker tile: higher = better to give away.

    Score of tile t = sum over the closest hands (best binding of each) of 0.5**needed after removing
    t. Removing a useless tile leaves the sum unchanged; removing a needed tile
    halves that binding's share.
    """
    targets = best_per_hand(card, holding, visible, top)
    have, jokers = holding.counts()
    exposed = holding.exposed_groups()
    values = {}
    for t in set(have):
        have[t] -= 1
        values[t] = sum(0.5 ** needed(b, have, jokers, exposed) for _, b in targets)
        have[t] += 1
    return values


def choose_discards(card, holding, k, visible=None, danger=None):
    """Pick k tiles (never jokers) to give away, best-to-lose first.

    `danger` maps tile code -> penalty for feeding opponents.
    """
    tiles = list(holding.concealed)
    danger = danger or {}
    picked = []
    for _ in range(k):
        values = discard_values(card, Holding(tiles, holding.exposures), visible)
        if not values:
            break
        choice = max(sorted(values), key=lambda t: values[t] - danger.get(t, 0.0))
        picked.append(choice)
        tiles.remove(choice)
    return picked
