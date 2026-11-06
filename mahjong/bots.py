"""Bot policies. Every decision reads only game.view_for(seat): a bot never sees
another player's concealed tiles or the wall order.

Easy: locks one target binding after the Charleston, discards tiles outside it,
only calls a discard to win. Normal: re-evaluates targets every turn, calls
exposures, swaps jokers, and avoids feeding opponents' visible exposures.
"""

from collections import Counter

from .matcher import Holding, choose_discards, mahjong, needed, ranked
from .tiles import JOKER


def _view(game, seat):
    v = game.view_for(seat)
    holding = Holding(list(v["hand"]), v["exposures"][seat])
    visible = Counter(d["tile"] for d in v["discards"])
    for s, exps in enumerate(v["exposures"]):
        if s != seat:
            for e in exps:
                visible.update(e["tiles"])
    return v, holding, visible


def _normal(game):
    return game.difficulty == "normal"


def charleston_pass(game, seat, k):
    if k == 0:
        return []
    _, holding, _ = _view(game, seat)
    return choose_discards(game.card, holding, k)


def continue_charleston(game, seat):
    if not _normal(game):
        return True
    _, holding, _ = _view(game, seat)
    best = ranked(game.card, holding, limit=1)
    return not best or best[0][0] > 3


def courtesy_count(game, seat):
    _, holding, _ = _view(game, seat)
    top = ranked(game.card, holding, limit=1)
    if not top:
        return 3
    have, _ = holding.counts()
    used = Counter({code: min(have.get(code, 0), n) for code, n in top[0][1].groups})
    junk = sum((have - used).values())
    return min(3, junk)


def choose_target(game, seat):
    """Easy bots commit to their closest binding once the Charleston ends."""
    _, holding, _ = _view(game, seat)
    top = ranked(game.card, holding, limit=1)
    game.targets[seat] = game.card.bindings.index(top[0][1]) if top else None


def _danger(game, v, seat):
    """Penalty per tile code for discards that help an opponent's visible exposures."""
    danger = Counter()
    for s, exps in enumerate(v["exposures"]):
        if s == seat or not exps:
            continue
        groups = [(e["code"], len(e["tiles"])) for e in exps]
        fits = [b for b in game.card.bindings if needed(b, Counter(), 0, groups) is not None]
        if not fits:
            continue
        weight = 0.5 * len(exps) / len(fits)
        for b in fits:
            for code, _ in b.groups:
                danger[code] += weight
    return danger


def discard(game, seat):
    v, holding, visible = _view(game, seat)
    naturals = [t for t in holding.concealed if t != JOKER]
    if not naturals:
        return JOKER
    if not _normal(game) and game.targets[seat] is not None:
        target = game.card.bindings[game.targets[seat]]
        have, _ = holding.counts()
        used = Counter({code: min(have.get(code, 0), n) for code, n in target.groups})
        junk = sorted((have - used).elements())
        if junk:
            return game._rng().choice(junk)
    danger = _danger(game, v, seat) if _normal(game) else None
    if danger:
        scale = 0.25 / max(danger.values())
        danger = {code: d * scale for code, d in danger.items()}
    return choose_discards(game.card, holding, 1, visible, danger)[0]


def claim(game, seat, tile):
    """Return {'kind': 'mahjong'} / {'kind': 'expose', 'size': n} / None."""
    v, holding, visible = _view(game, seat)
    if mahjong(game.card, Holding(holding.concealed + [tile], holding.exposures)):
        return {"kind": "mahjong"}
    if not _normal(game):
        return None
    have, jokers = holding.counts()
    exposed = holding.exposed_groups()
    for n_needed, b in ranked(game.card, holding, visible, limit=3):
        if b.hand.concealed:
            continue
        for code, n in b.groups:
            if code != tile or n < 3 or (code, n) in exposed:
                continue
            if have.get(code, 0) >= 1 and have.get(code, 0) + jokers >= n - 1 \
                    and len(holding.concealed) - (n - 1) >= 1 and have.get(code, 0) < n:
                return {"kind": "expose", "size": n}
        break  # only call toward the single best target
    return None


def swaps(game, seat):
    """Joker swaps a Normal bot makes at the start of its turn (at most one per tile)."""
    if not _normal(game):
        return []
    v, holding, visible = _view(game, seat)
    out = []
    before = ranked(game.card, holding, visible, limit=1)
    before = before[0][0] if before else 99
    used = Counter()
    for s, exps in enumerate(v["exposures"]):
        for i, e in enumerate(exps):
            code = e["code"]
            if JOKER not in e["tiles"] or holding.concealed.count(code) - used[code] <= 0:
                continue
            trial = list(holding.concealed)
            trial.remove(code)
            trial.append(JOKER)
            after = ranked(game.card, Holding(trial, holding.exposures), visible, limit=1)
            if after and after[0][0] <= before:
                out.append({"seat": s, "index": i})
                used[code] += 1
                holding = Holding(trial, holding.exposures)
                before = after[0][0]
    return out
