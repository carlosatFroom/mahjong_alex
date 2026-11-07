"""Completion odds by simulation over the tiles the player has not seen.

Only the player's own view is used: their rack and exposures, every discard, and other
players' exposures. Odds count the player's own future draws only (no calls).

All hands and all candidate discards are scored against the same seeded set of simulated
draws ("common random numbers"), so differences between them are not sampling noise.
"""

import random
from collections import Counter
from dataclasses import dataclass, field

from .matcher import missing_tiles, ranked
from .tiles import COPIES, JOKER

RUNS = 1000
CANDIDATES = 40      # nearest bindings (by tiles away) worth simulating
PER_HAND = 3         # bindings kept per hand
TOP_HANDS = 8        # hands whose odds a discard is scored against


def visible_counts(view):
    """Tiles outside the player's rack they can see: all discards, others' exposures."""
    seat = view["seat"]
    c = Counter(d["tile"] for d in view["discards"])
    for s, exps in enumerate(view["exposures"]):
        if s != seat:
            for e in exps:
                c.update(e["tiles"])
    return c


def draws_left(view):
    """Wall tiles the player will draw if nobody calls: the next draw goes to current+1."""
    wall = view["wall_count"]
    k = (view["seat"] - view["current"] - 1) % 4
    return (wall - k + 3) // 4 if wall > k else 0


def unseen_pool(holding, visible):
    """Tiles the player has not seen, as a flat list (wall + other players' racks)."""
    seen = Counter(holding.concealed) + visible
    for e in holding.exposures:
        seen.update(e["tiles"])
    return [code for code, n in COPIES.items() for _ in range(max(0, n - seen[code]))]


def _completes(missing, jokers, drawn):
    """True if `drawn` covers `missing`; jokers fill only groups of 3+."""
    short = 0
    for code, m, joker_ok in missing:
        s = m - drawn.get(code, 0)
        if s > 0:
            if not joker_ok:
                return False
            short += s
    return short <= jokers + drawn.get(JOKER, 0)


@dataclass
class HandOdds:
    hand: object
    odds: float
    needed: int
    binding: object                      # nearest binding, shown as "your version"
    bindings: list = field(repr=False)   # bindings simulated for this hand


class OddsModel:
    """Odds for one decision point. Build once, query hands and discards."""

    def __init__(self, card, holding, visible, draws, runs=RUNS):
        self.card = card
        self.holding = holding
        self.draws = draws
        self.pool = unseen_pool(holding, visible)
        self.unseen = Counter(self.pool)
        exps = ";".join(f"{e['code']}{len(e['tiles'])}" for e in holding.exposures)
        seed = f"{sorted(holding.concealed)}|{exps}|{sorted(visible.items())}|{draws}"
        rng = random.Random(seed)
        n = min(draws, len(self.pool))
        self.samples = [Counter(rng.sample(self.pool, n)) for _ in range(runs)] if n else []
        self.have, self.jokers = holding.counts()
        self.exposed = holding.exposed_groups()
        self._hands = self._rank(visible)
        self._scores = None

    def _rank(self, visible):
        by_hand = {}
        for needed, b in ranked(self.card, self.holding, visible, limit=CANDIDATES):
            if needed > self.draws:
                continue
            lst = by_hand.setdefault(b.hand.id, [])
            if len(lst) < PER_HAND:
                lst.append((needed, b))
        out = []
        for pairs in by_hand.values():
            bindings = [b for _, b in pairs]
            odds = self._odds(bindings, self.have)
            if odds > 0:
                out.append(HandOdds(bindings[0].hand, odds, pairs[0][0], bindings[0], bindings))
        out.sort(key=lambda h: (-h.odds, -h.hand.points, h.needed))
        return out

    def _odds(self, bindings, have):
        """Share of simulated draws that complete any of `bindings`."""
        missing = [missing_tiles(b, have, 0, self.exposed) for b in bindings]
        if any(not m for m in missing):
            return 1.0
        if not self.samples:
            return 0.0
        hits = sum(1 for drawn in self.samples
                   if any(_completes(m, self.jokers, drawn) for m in missing))
        return hits / len(self.samples)

    def hands(self, count=None):
        return self._hands[:count] if count else list(self._hands)

    def discard_scores(self):
        """{tile: [odds of each top hand after giving the tile away]} for each non-joker tile."""
        if self._scores is None:
            self._scores = self._discard_scores()
        return self._scores

    def _discard_scores(self):
        targets = self._hands[:TOP_HANDS]
        out = {}
        for t in sorted(self.have):
            if self.have[t] <= 0:
                continue
            self.have[t] -= 1
            out[t] = [self._odds(h.bindings, self.have) for h in targets]
            self.have[t] += 1
        return out

    def best_discards(self, k=1):
        """Pick k tiles to give away, keeping the most total odds. Never jokers."""
        picked = []
        for _ in range(k):
            scores = self._discard_scores() if picked else self.discard_scores()
            if not scores:
                break
            tile = max(scores, key=lambda t: sum(scores[t]))  # sorted keys: ties -> lowest code
            picked.append(tile)
            self.have[tile] -= 1
        for tile in picked:
            self.have[tile] += 1
        return picked
