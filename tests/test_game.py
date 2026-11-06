from collections import Counter

import pytest

from conftest import tiles_of
from mahjong.game import Game, GameError, COURTESY_STAGE, VOTE_STAGE
from mahjong.tiles import JOKER, full_set


def new(card, human=0, difficulty="normal", seed=7):
    g = Game.new(card, seed=seed, difficulty=difficulty, human=human)
    g.advance()
    return g


def three_tiles(g):
    return [t for t in g.hands[g.human] if t != JOKER][:3]


def total(g):
    c = Counter(g.wall)
    for s in range(4):
        c.update(g.hands[s])
        for e in g.exposures[s]:
            c.update(e["tiles"])
    c.update(d["tile"] for d in g.discards)
    return c


def test_deal(card):
    g = new(card)
    assert len(g.hands[0]) == 14
    assert [len(h) for h in g.hands[1:]] == [13, 13, 13]
    assert total(g) == Counter(full_set())


def test_first_charleston_directions_then_vote(card):
    g = new(card, human=0)
    seq = []
    for _ in range(3):
        p = g.prompt()
        seq.append(p["direction"])
        g.act({"type": "pass", "tiles": three_tiles(g)})
    assert seq == ["right", "across", "left"]
    assert g.prompt()["type"] == "vote"
    assert total(g) == Counter(full_set())


def test_pass_right_goes_to_next_seat(card):
    g = new(card, human=0)
    give = three_tiles(g)
    before = Counter(g.hands[1])
    g.act({"type": "pass", "tiles": give})
    received = Counter(g.hands[1]) - before
    assert Counter(give) - received == Counter()


def test_second_charleston_runs_when_all_agree(card):
    g = new(card, human=0, difficulty="easy")  # easy bots always continue
    for _ in range(3):
        g.act({"type": "pass", "tiles": three_tiles(g)})
    g.act({"type": "vote", "continue": True})
    dirs = []
    for _ in range(3):
        dirs.append(g.prompt()["direction"])
        g.act({"type": "pass", "tiles": three_tiles(g)})
    assert dirs == ["left", "across", "right"]
    assert g.prompt()["type"] == "courtesy"


def test_declining_skips_to_courtesy(card):
    g = new(card, human=0)
    for _ in range(3):
        g.act({"type": "pass", "tiles": three_tiles(g)})
    g.act({"type": "vote", "continue": False})
    assert g.stage == COURTESY_STAGE
    assert g.prompt()["type"] == "courtesy"


def test_jokers_cannot_be_passed(card):
    g = new(card, human=0)
    g.hands[0][0] = JOKER
    with pytest.raises(GameError, match="Jokers"):
        g.act({"type": "pass", "tiles": [JOKER] + three_tiles(g)[:2]})


def test_blind_pass_only_on_last_pass(card):
    g = new(card, human=0)
    with pytest.raises(GameError, match="Blind"):
        g.act({"type": "pass", "tiles": three_tiles(g)[:1], "blind": 2})
    g.act({"type": "pass", "tiles": three_tiles(g)})
    g.act({"type": "pass", "tiles": three_tiles(g)})
    assert g.prompt()["blind_allowed"]
    g.act({"type": "pass", "tiles": three_tiles(g)[:1], "blind": 2})
    assert g.stage == VOTE_STAGE
    assert total(g) == Counter(full_set())


def to_play(card, human=0, difficulty="normal", seed=7):
    g = new(card, human=human, difficulty=difficulty, seed=seed)
    for _ in range(3):
        g.act({"type": "pass", "tiles": three_tiles(g)})
    g.act({"type": "vote", "continue": False})
    g.act({"type": "courtesy", "tiles": []})
    return g


def test_east_discards_first_without_drawing(card):
    g = to_play(card, human=0)
    assert g.prompt()["type"] == "discard"
    assert len(g.hands[0]) == 14


def _binding(card, hand_id):
    return next(b for b in card.bindings if b.hand.id == hand_id)


def test_self_drawn_mahjong_and_scoring(card):
    g = to_play(card, human=0)
    b = _binding(card, "E1")  # 25 points
    g.hands[0] = tiles_of(b)
    pung = next(code for code, n in b.groups if n == 3)
    g.hands[0][g.hands[0].index(pung)] = JOKER
    g.from_wall = True
    g.act({"type": "mahjong"})
    assert g.phase == "over"
    r = g.result
    assert r["winner"] == 0 and r["self_drawn"] and not r["jokerless"]
    assert r["payments"] == [150, -50, -50, -50]


def test_jokerless_doubles(card):
    g = to_play(card, human=0)
    g.hands[0] = tiles_of(_binding(card, "E1"))
    g.from_wall = True
    g.act({"type": "mahjong"})
    assert g.result["jokerless"]
    assert g.result["payments"] == [300, -100, -100, -100]


def test_singles_and_pairs_not_doubled_for_jokerless(card):
    g = to_play(card, human=0)
    g.hands[0] = tiles_of(_binding(card, "S3"))  # 50 points
    g.from_wall = True
    g.act({"type": "mahjong"})
    assert not g.result["jokerless"]
    assert g.result["payments"] == [300, -100, -100, -100]


def test_invalid_mahjong_rejected_with_reason(card):
    g = to_play(card, human=0)
    with pytest.raises(GameError, match="short|fit"):
        g.act({"type": "mahjong"})
    assert g.phase == "play"


def _human_turn_with_call(card, human_tiles, tile, discarder=3, human=0):
    """Put the game in a call window for `tile` discarded by `discarder`."""
    g = to_play(card, human=human)
    g.hands[human] = list(human_tiles)
    for s in range(4):
        if s != human:
            g.hands[s] = [t for t in g.hands[s] if t != tile][:13]
    g.hands[discarder].append(tile)
    g.current = discarder
    g.turn = "discard"
    g._discard(discarder, tile)
    return g


def test_discard_win_scoring(card):
    b = _binding(card, "E1")
    tiles = tiles_of(b)
    winning = tiles.pop()  # 13 tiles waiting on the last one
    g = _human_turn_with_call(card, tiles, winning, discarder=3)
    assert g.prompt()["type"] == "call"
    g.act({"type": "mahjong"})
    r = g.result
    assert r["winner"] == 0 and r["discarder"] == 3 and not r["self_drawn"]
    assert r["payments"] == [200, -50, -50, -100]  # jokerless 25 → 50, discarder pays double


def test_call_exposure_and_dead_hand(card):
    hand = ["F", "F", "F", "F", "1B", "2C", "3D", "4B", "5C", "6D", "7B", "8C", "9D"]
    g = _human_turn_with_call(card, hand, "F", discarder=3)
    assert 5 in g.prompt()["sizes"]
    g.claims["bots"] = {}
    g.act({"type": "call", "size": 5})
    assert g.exposures[0][-1]["tiles"] == ["F"] * 5
    assert g.dead[0]
    assert g.prompt()["type"] == "discard"
    assert not g.prompt()["can_mahjong"]


def test_mahjong_beats_exposure_and_order_breaks_ties(card):
    g = _human_turn_with_call(card, ["1B"] * 2 + ["2C"] * 11, "1B", discarder=3)
    g.claims["bots"] = {"1": {"kind": "expose", "size": 3}, "2": {"kind": "mahjong"}}
    b2 = _binding(card, "E1")
    g.hands[2] = tiles_of(b2)[:13]
    g.last["tile"] = tiles_of(b2)[13]
    g.discards[-1]["tile"] = g.last["tile"]
    g.claims["human"] = None
    g._resolve_claims()
    assert g.result["winner"] == 2

    g = _human_turn_with_call(card, ["1B"] * 2 + ["2C"] * 11, "1B", discarder=3)
    g.claims["bots"] = {"1": {"kind": "expose", "size": 3}}
    g.claims["human"] = {"kind": "expose", "size": 3}
    g._resolve_claims()
    assert g.exposures[0] and g.current == 0  # seat 0 is next after seat 3


def test_called_joker_is_dead(card):
    g = to_play(card, human=1)
    g.hands[0].append(JOKER)
    g.hands[0].pop(0)
    g.current = 0
    g._discard(0, JOKER)
    assert g.turn == "discard" and g.current == 1


def test_joker_swap(card):
    g = to_play(card, human=0)
    g.exposures[2].append({"code": "5B", "tiles": ["5B", JOKER, "5B"]})
    g.hands[0][0] = "5B"
    p = g.prompt()
    swap = next(s for s in p["swaps"] if s["seat"] == 2)
    g.act({"type": "swap", "seat": swap["seat"], "index": swap["index"]})
    assert g.exposures[2][-1]["tiles"] == ["5B", "5B", "5B"]
    assert JOKER in g.hands[0]


def test_wall_game(card):
    g = to_play(card, human=0)
    g.wall = []
    g._discard(0, next(t for t in g.hands[0] if t != JOKER))
    g.claims = {"bots": {}, "human": None}
    g.advance()
    assert g.phase == "over"
    assert g.result["wall_game"] and g.result["payments"] == [0, 0, 0, 0]


def test_round_trip_serialization(card):
    import json
    g = to_play(card, human=2)
    data = json.loads(json.dumps(g.to_dict()))
    g2 = Game.from_dict(card, data)
    assert g2.prompt() == g.prompt()
    assert g2.view_for(2) == g.view_for(2)


def test_view_hides_other_racks(card):
    g = to_play(card, human=0)
    v = g.view_for(0)
    assert "reveal" not in v
    assert "hands" not in v and "wall" not in v
    assert v["rack_counts"] == [len(h) for h in g.hands]
