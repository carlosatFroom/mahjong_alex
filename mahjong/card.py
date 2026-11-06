"""Load a card file and expand every hand into concrete tile bindings."""

import json
from dataclasses import dataclass
from itertools import permutations

from .tiles import DRAGON_OF_SUIT, SOAP, SUITS, WINDS, FLOWER, tile_name

SUIT_VARS = ("A", "B", "C")


@dataclass(frozen=True)
class Hand:
    id: str
    category: str
    display: str
    note: str
    points: int
    concealed: bool

    @property
    def singles_and_pairs(self):
        return self.category == "Singles and Pairs"

    def label(self):
        kind = "C" if self.concealed else "X"
        note = f" ({self.note})" if self.note else ""
        return f"{self.category}: {self.display}{note} {kind} {self.points}"


@dataclass(frozen=True)
class Binding:
    """One way to complete a hand: a fixed list of (tile code, count) groups."""
    hand: Hand
    variant: int
    groups: tuple

    def describe(self):
        return ", ".join(f"{n}× {tile_name(code)}" for code, n in self.groups)


class CardError(ValueError):
    pass


def _resolve(template, suits, x):
    """Turn a group template like 'x+1:B' or 'D:A' into a tile code."""
    if template == FLOWER or template in WINDS:
        return template
    if template == "0":
        return SOAP
    if ":" not in template:
        raise CardError(f"Unknown tile template {template!r}")
    num, var = template.split(":")
    suit = suits[var]
    if num == "D":
        return DRAGON_OF_SUIT[suit]
    if num.startswith("x"):
        n = x + (int(num[2:]) if "+" in num else 0)
    else:
        n = int(num)
    if not 1 <= n <= 9:
        return None
    return f"{n}{suit}"


def _expand(hand, variant_index, variant, x_values):
    templates = [g[0] for g in variant]
    used_vars = sorted({t.split(":")[1] for t in templates if ":" in t})
    uses_x = any(t.startswith("x") for t in templates)
    seen = set()
    for perm in permutations(SUITS, len(used_vars)):
        suits = dict(zip(used_vars, perm))
        for x in (x_values if uses_x else [None]):
            codes = [_resolve(t, suits, x) for t in templates]
            if None in codes or len(set(codes)) != len(codes):
                continue
            groups = tuple(sorted(zip(codes, (g[1] for g in variant))))
            if groups in seen:
                continue
            seen.add(groups)
            yield Binding(hand, variant_index, groups)


def load_card(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    hands, bindings = [], []
    for h in data["hands"]:
        hand = Hand(h["id"], h["category"], h["display"], h.get("note", ""),
                    int(h["points"]), bool(h["concealed"]))
        hand_bindings = []
        for i, variant in enumerate(h["variants"]):
            if sum(n for _, n in variant) != 14:
                raise CardError(f"Hand {hand.id} variant {i} does not total 14 tiles")
            hand_bindings.extend(_expand(hand, i, variant, h.get("x_in", range(1, 10))))
        if not hand_bindings:
            raise CardError(f"Hand {hand.id} has no valid tile binding")
        hands.append(hand)
        bindings.extend(hand_bindings)
    return Card(data.get("name", path), hands, bindings)


class Card:
    def __init__(self, name, hands, bindings):
        self.name = name
        self.hands = hands
        self.bindings = bindings
        self.by_id = {h.id: h for h in hands}

    def text(self):
        """Plain-text card listing, used in the coach prompt."""
        lines, category = [], None
        for h in self.hands:
            if h.category != category:
                category = h.category
                lines.append(f"\n{category}")
            lines.append(f"  [{h.id}] {h.label()[len(category) + 2:]}")
        return "\n".join(lines).strip()

    def to_json(self):
        return [{"id": h.id, "category": h.category, "display": h.display, "note": h.note,
                 "points": h.points, "concealed": h.concealed} for h in self.hands]
