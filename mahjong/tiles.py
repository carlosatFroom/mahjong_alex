"""Tile codes and the 152-tile American Mahjong set.

Codes: "1B".."9B" Bams, "1C".."9C" Craks, "1D".."9D" Dots,
"N" "E" "W" "S" winds, "GD" "RD" "WD" dragons (WD = Soap, also used as zero),
"F" flower, "J" joker.
"""

SUITS = ("B", "C", "D")
SUIT_NAMES = {"B": "Bam", "C": "Crak", "D": "Dot"}
WINDS = ("N", "E", "W", "S")
DRAGONS = ("GD", "RD", "WD")
DRAGON_OF_SUIT = {"B": "GD", "C": "RD", "D": "WD"}
DRAGON_NAMES = {"GD": "Green Dragon", "RD": "Red Dragon", "WD": "Soap"}
WIND_NAMES = {"N": "North", "E": "East", "W": "West", "S": "South"}
FLOWER = "F"
JOKER = "J"
SOAP = "WD"

NUMBER_TILES = tuple(f"{n}{s}" for s in SUITS for n in range(1, 10))

COPIES = {**{t: 4 for t in NUMBER_TILES}, **{w: 4 for w in WINDS},
          **{d: 4 for d in DRAGONS}, FLOWER: 8, JOKER: 8}

ALL_CODES = tuple(COPIES)

# Order used to sort a rack for display.
SORT_ORDER = {code: i for i, code in enumerate(
    (FLOWER,) + NUMBER_TILES + WINDS + DRAGONS + (JOKER,))}


def full_set():
    """Return the 152 tiles as a list of codes."""
    return [code for code, n in COPIES.items() for _ in range(n)]


def is_number(code):
    return len(code) == 2 and code[0].isdigit()


def tile_name(code):
    if is_number(code):
        return f"{code[0]} {SUIT_NAMES[code[1]]}"
    if code in WIND_NAMES:
        return WIND_NAMES[code]
    if code in DRAGON_NAMES:
        return DRAGON_NAMES[code]
    return "Flower" if code == FLOWER else "Joker"


def sort_tiles(tiles):
    return sorted(tiles, key=lambda c: SORT_ORDER[c])
