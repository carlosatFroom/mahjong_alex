from collections import Counter

import pytest

from conftest import tiles_of
from mahjong import tiles as T
from mahjong.matcher import Holding, mahjong, needed, exposures_possible, why_not_mahjong


def test_full_set_is_152_with_expected_counts():
    s = Counter(T.full_set())
    assert sum(s.values()) == 152
    assert sum(s[t] for t in T.NUMBER_TILES) == 108
    assert sum(s[w] for w in T.WINDS) == 16
    assert sum(s[d] for d in T.DRAGONS) == 12
    assert s[T.FLOWER] == 8
    assert s[T.JOKER] == 8


def test_card_has_every_category(card):
    cats = {h.category for h in card.hands}
    assert cats == {"2026", "2468", "Like Numbers", "Quints", "Consecutive Run", "13579",
                    "Winds and Dragons", "369", "Singles and Pairs"}
    assert len(card.hands) >= 30


def _near_miss(binding):
    """Replace one tile of the hand with a tile that appears nowhere in it."""
    tiles = tiles_of(binding)
    codes = {c for c, _ in binding.groups}
    stranger = next(t for t in T.ALL_CODES if t not in codes and t != T.JOKER)
    tiles[-1] = stranger
    return tiles


@pytest.mark.parametrize("hand_index", range(34))
def test_every_hand_has_win_and_near_miss(card, hand_index):
    hand = card.hands[hand_index]
    for b in [b for b in card.bindings if b.hand is hand]:
        win = mahjong(card, Holding(tiles_of(b), []))
        assert win is not None, f"{hand.id} example should win"
        miss = Holding(_near_miss(b), [])
        assert all(needed(x, *miss.counts(), []) != 0 for x in card.bindings if x.hand is hand), \
            f"{hand.id} near miss should not complete {hand.id}"


def test_card_has_34_hands(card):
    assert len(card.hands) == 34


def _binding(card, hand_id):
    return next(b for b in card.bindings if b.hand.id == hand_id)


def test_jokers_fill_pungs_and_kongs(card):
    b = _binding(card, "E1")  # FF 222 444 666 888, one suit
    tiles = tiles_of(b)
    for code in ("2", "4", "8"):
        idx = next(i for i, t in enumerate(tiles) if t.startswith(code))
        tiles[idx] = T.JOKER
    assert mahjong(card, Holding(tiles, [])) is not None


def test_jokers_never_fill_pairs_or_singles(card):
    b = _binding(card, "E1")
    tiles = tiles_of(b)
    tiles[tiles.index(T.FLOWER)] = T.JOKER  # FF pair
    assert needed(b, *Holding(tiles, []).counts(), []) == 1
    s = _binding(card, "S3")  # all pairs
    tiles = tiles_of(s)
    tiles[5] = T.JOKER
    assert mahjong(card, Holding(tiles, [])) is None


def test_concealed_hand_rejects_exposures(card):
    b = _binding(card, "L3")  # concealed
    code, n = next(g for g in b.groups if g[1] == 3)
    tiles = tiles_of(b)
    for _ in range(n):
        tiles.remove(code)
    h = Holding(tiles, [{"code": code, "tiles": [code] * n}])
    assert needed(b, *h.counts(), h.exposed_groups()) is None


def test_exposure_must_match_group_size(card):
    b = _binding(card, "R1")  # 1111 222 333 4444
    kong = next(code for code, n in b.groups if n == 4)
    assert needed(b, Counter(), 0, [(kong, 3)]) is None
    assert needed(b, Counter(), 0, [(kong, 4)]) == 10


def test_dead_exposures_detected(card):
    assert exposures_possible(card, [{"code": "5B", "tiles": ["5B"] * 3}])
    # No hand on the card has a quint of flowers.
    assert not exposures_possible(card, [{"code": "F", "tiles": ["F"] * 5}])


def test_why_not_mahjong_explains(card):
    b = _binding(card, "E1")
    msg = why_not_mahjong(card, Holding(_near_miss(b), []))
    assert "short" in msg
    assert "14 tiles" in why_not_mahjong(card, Holding(["1B"] * 3, []))
