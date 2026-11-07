import time
from collections import Counter

from conftest import tiles_of
from mahjong.game import Game
from mahjong.matcher import Holding
from mahjong.odds import OddsModel, draws_left, unseen_pool, visible_counts
from mahjong.tiles import COPIES, full_set


def _view(game):
    return game.view_for(game.human)


def _model(card, view, **kw):
    return OddsModel(card, Holding(list(view["hand"]), view["exposures"][view["seat"]]),
                     visible_counts(view), draws_left(view), **kw)


def _midgame(card, seed=3, turns=30):
    g = Game.new(card, seed=seed, difficulty="normal", human=0)
    from sim import autopilot
    g.advance()
    for _ in range(turns):
        if g.phase == "over":
            break
        g.act(autopilot(g))
    return g


def test_unseen_pool_excludes_seen_and_ignores_hidden(card):
    g = _midgame(card)
    v = _view(g)
    holding = Holding(list(v["hand"]), v["exposures"][v["seat"]])
    pool = Counter(unseen_pool(holding, visible_counts(v)))
    seen = Counter(v["hand"]) + visible_counts(v)
    for e in v["exposures"][v["seat"]]:
        seen.update(e["tiles"])
    assert pool == Counter(full_set()) - seen
    # The pool is exactly the bots' racks plus the wall, whatever their contents.
    hidden = Counter(g.wall)
    for s in range(4):
        if s != g.human:
            hidden.update(g.hands[s])
    assert pool == hidden
    # Moving tiles between hidden places (bot racks <-> wall) never changes the odds.
    before = [(h.hand.id, h.odds) for h in _model(card, v).hands()]
    bot = (g.human + 1) % 4
    g.hands[bot][0], g.wall[0] = g.wall[0], g.hands[bot][0]
    after = [(h.hand.id, h.odds) for h in _model(card, _view(g)).hands()]
    assert before == after


def test_draws_left_counts_turn_order():
    base = {"seat": 2, "current": 0}
    assert draws_left({**base, "wall_count": 0}) == 0
    assert draws_left({**base, "wall_count": 1}) == 0   # seat 1 draws it
    assert draws_left({**base, "wall_count": 2}) == 1
    assert draws_left({**base, "wall_count": 6}) == 2
    assert draws_left({"seat": 1, "current": 0, "wall_count": 1}) == 1


def test_more_unseen_copies_means_higher_odds(card):
    b = next(b for b in card.bindings if not b.hand.concealed
             and any(n == 3 for _, n in b.groups) and all(c != "J" for c, _ in b.groups))
    code = next(c for c, n in b.groups if n == 3 and c != "F")
    rack = tiles_of(b)
    rack.remove(code)
    holding = Holding(rack, [])
    # Nothing visible: the needed tile has 1 copy + 8 jokers unseen.
    open_odds = OddsModel(card, holding, Counter(), 12).hands()
    # All jokers already discarded: only the one natural copy is left.
    dead_jokers = OddsModel(card, holding, Counter({"J": 8}), 12).hands()
    o1 = next(h.odds for h in open_odds if h.hand.id == b.hand.id)
    o2 = next((h.odds for h in dead_jokers if h.hand.id == b.hand.id), 0.0)
    assert o1 > o2 > 0


def test_hand_with_no_unseen_copies_is_excluded(card):
    b = next(b for b in card.bindings if any(n == 2 for _, n in b.groups))
    code = next(c for c, n in b.groups if n == 2)
    rack = tiles_of(b)
    rack.remove(code)
    holding_count = rack.count(code)
    visible = Counter({code: COPIES[code] - holding_count})
    hands = OddsModel(card, Holding(rack, []), visible, 20).hands()
    assert all(h.binding != b for h in hands)


def test_complete_hand_is_certain(card):
    b = card.bindings[0]
    hands = OddsModel(card, Holding(tiles_of(b), []), Counter(), 0).hands()
    assert hands[0].odds == 1.0


def test_same_view_same_odds_and_sorted(card):
    v = _view(_midgame(card, seed=7, turns=20))
    a = _model(card, v)
    b = _model(card, v)
    assert [(h.hand.id, h.odds) for h in a.hands()] == [(h.hand.id, h.odds) for h in b.hands()]
    assert a.discard_scores() == b.discard_scores()
    odds = [h.odds for h in a.hands()]
    assert odds == sorted(odds, reverse=True)


def test_hint_speed(card):
    v = _view(_midgame(card, seed=11, turns=10))
    t = time.time()
    m = _model(card, v)
    m.hands(3)
    m.best_discards(3)
    assert time.time() - t < 1.5
