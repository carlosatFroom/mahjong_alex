"""American Mahjong game state machine for one human and three bots.

Seats 0..3 are East, South, West, North; play passes to seat+1 (the player on
your right). All state is plain JSON-serializable data so a game can be stored
between requests.
"""

import random
from collections import Counter

from . import bots
from .matcher import Holding, exposures_possible, mahjong, why_not_mahjong
from .tiles import JOKER, full_set, sort_tiles, tile_name

SEAT_WINDS = ("East", "South", "West", "North")
BOT_NAMES = ("Pearl", "Hazel", "Ivy", "June")
RIGHT, ACROSS, LEFT = 1, 2, 3
DIRECTION_NAMES = {RIGHT: "right", ACROSS: "across", LEFT: "left"}

# Charleston stages: (direction, blind pass allowed)
PASSES = {0: (RIGHT, False), 1: (ACROSS, False), 2: (LEFT, True),
          4: (LEFT, False), 5: (ACROSS, False), 6: (RIGHT, True)}
VOTE_STAGE, COURTESY_STAGE = 3, 7


class GameError(ValueError):
    """An illegal action by the human player; the message is shown to them."""


class Game:
    def __init__(self, card):
        self.card = card

    # ------------------------------------------------------------------ setup
    @classmethod
    def new(cls, card, seed=None, difficulty="normal", human=None):
        g = cls(card)
        seed = random.randrange(2**31) if seed is None else seed
        rng = random.Random(seed)
        tiles = full_set()
        rng.shuffle(tiles)
        g.seed = seed
        g.difficulty = difficulty
        g.human = rng.randrange(4) if human is None else human
        names = iter(BOT_NAMES)
        g.names = ["You" if s == g.human else next(names) for s in range(4)]
        g.hands = [tiles[:14]] + [tiles[14 + 13 * i: 27 + 13 * i] for i in range(3)]
        g.wall = tiles[53:]
        g.exposures = [[] for _ in range(4)]
        g.dead = [False] * 4
        g.discards = []
        g.phase = "charleston"
        g.stage = 0
        g.courtesy_offer = None
        g.current = 0
        g.turn = None
        g.from_wall = True
        g.last = None
        g.claims = None
        g.targets = [None] * 4
        g.result = None
        g.log = []
        g.step = 0
        g._log(f"New game. You sit {SEAT_WINDS[g.human]}. East deals.")
        return g

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if k != "card"}

    @classmethod
    def from_dict(cls, card, data):
        g = cls(card)
        g.__dict__.update(data)
        return g

    # ---------------------------------------------------------------- helpers
    def _rng(self):
        self.step += 1
        return random.Random(f"{self.seed}-{self.step}")

    def _log(self, text):
        self.log.append(text)

    def holding(self, seat):
        return Holding(self.hands[seat], self.exposures[seat])

    def who(self, seat):
        return "You" if seat == self.human else self.names[seat]

    def visible_counts(self, seat):
        """Tiles seat can see outside its own rack: discards and all exposures."""
        c = Counter(d["tile"] for d in self.discards)
        for s in range(4):
            if s != seat:
                for e in self.exposures[s]:
                    c.update(e["tiles"])
        return c

    def view_for(self, seat):
        """Everything `seat` is allowed to see. Bots and the coach use only this."""
        v = {
            "seat": seat,
            "seat_wind": SEAT_WINDS[seat],
            "names": self.names,
            "winds": list(SEAT_WINDS),
            "difficulty": self.difficulty,
            "hand": sort_tiles(self.hands[seat]),
            "rack_counts": [len(h) for h in self.hands],
            "exposures": self.exposures,
            "discards": self.discards,
            "wall_count": len(self.wall),
            "dead": self.dead[seat],
            "phase": self.phase,
            "current": self.current,
            "last_discard": self.last,
            "log": self.log[-40:],
        }
        if self.phase == "charleston":
            v["charleston_stage"] = self.stage
        if seat == self.human:
            v["prompt"] = self.prompt()
        if self.phase == "over":
            v["result"] = self.result
            v["reveal"] = [sort_tiles(h) for h in self.hands]
        return v

    # ---------------------------------------------------------------- prompts
    def prompt(self):
        """What the human must do next, or None while bots are acting."""
        if self.phase == "over":
            return {"type": "over"}
        if self.phase == "charleston":
            if self.stage in PASSES:
                direction, blind = PASSES[self.stage]
                first = "first" if self.stage < VOTE_STAGE else "second"
                return {"type": "pass", "count": 3, "blind_allowed": blind,
                        "direction": DIRECTION_NAMES[direction], "charleston": first}
            if self.stage == VOTE_STAGE:
                return {"type": "vote"}
            return {"type": "courtesy", "max": self.courtesy_offer}
        if self.turn == "discard" and self.current == self.human:
            return {"type": "discard", "swaps": self._swaps_for(self.human),
                    "can_mahjong": not self.dead[self.human]}
        if self.turn == "call" and self.claims and self.claims.get("human") == "pending":
            return {"type": "call", "tile": self.last["tile"], "from": self.last["seat"],
                    "sizes": self._call_sizes(self.human, self.last["tile"])}
        return None

    # ------------------------------------------------------------- charleston
    def _apply_pass(self, human_tiles, blind):
        direction, _ = PASSES[self.stage]
        picks = {}
        for s in range(4):
            picks[s] = human_tiles if s == self.human else bots.charleston_pass(self, s, 3)
        giver_to_human = (self.human - direction) % 4
        forwarded = []
        if blind:
            forwarded = self._rng().sample(picks[giver_to_human], blind)
        for s in range(4):
            for t in picks[s]:
                self.hands[s].remove(t)
        for s in range(4):
            receiver = (s + direction) % 4
            incoming = list(picks[s])
            if receiver == self.human and blind:
                for t in forwarded:
                    incoming.remove(t)
            if s == self.human:
                incoming += forwarded
            self.hands[receiver].extend(incoming)
        note = f" ({blind} blind)" if blind else ""
        self._log(f"Charleston: everyone passed {DIRECTION_NAMES[direction]}{note}.")

    def _next_stage(self):
        self.stage += 1
        if self.stage == COURTESY_STAGE:
            across = (self.human + 2) % 4
            self.courtesy_offer = bots.courtesy_count(self, across)
        if self.stage > COURTESY_STAGE:
            self.phase = "play"
            self.turn = "discard"
            self.current = 0
            self.from_wall = True
            for s in range(4):
                if s != self.human:
                    bots.choose_target(self, s)
            self._log("Charleston over. East discards first.")

    def _courtesy(self, human_tiles):
        across = (self.human + 2) % 4
        n = len(human_tiles)
        gives = {self.human: human_tiles, across: bots.charleston_pass(self, across, n)}
        others = [s for s in range(4) if s not in gives]
        m = min(bots.courtesy_count(self, others[0]), bots.courtesy_count(self, others[1]))
        for s in others:
            gives[s] = bots.charleston_pass(self, s, m)
        for s, tiles in gives.items():
            for t in tiles:
                self.hands[s].remove(t)
        for s, tiles in gives.items():
            self.hands[(s + 2) % 4].extend(tiles)
        self._log(f"Courtesy pass: you and {self.names[across]} swapped {n} tile(s).")

    # ------------------------------------------------------------------- play
    def _start_turn(self, seat):
        self.current = seat
        self.turn = "discard"
        self.claims = None
        if not self.wall:
            self._end(None, None, None)
            return
        tile = self.wall.pop()
        self.hands[seat].append(tile)
        self.from_wall = True
        if seat == self.human:
            self._log(f"You drew {tile_name(tile)}.")

    def _discard(self, seat, tile):
        self.hands[seat].remove(tile)
        self.discards.append({"seat": seat, "tile": tile})
        self.last = {"seat": seat, "tile": tile}
        self._log(f"{self.who(seat)} discarded {tile_name(tile)}.")
        if tile == JOKER:
            self._start_turn((seat + 1) % 4)
            return
        self.turn = "call"
        claims = {"bots": {}}
        for s in range(4):
            if s not in (seat, self.human):
                c = bots.claim(self, s, tile)
                if c:
                    claims["bots"][str(s)] = c
        claims["human"] = "pending" if self._human_can_call(tile) else None
        self.claims = claims

    def _human_can_call(self, tile):
        h = self.human
        if self.last["seat"] == h or self.dead[h]:
            return False
        if self._call_sizes(h, tile):
            return True
        test = Holding(self.hands[h] + [tile], self.exposures[h])
        return mahjong(self.card, test) is not None

    def _call_sizes(self, seat, tile):
        have = self.hands[seat].count(tile)
        jokers = self.hands[seat].count(JOKER)
        if have == 0:
            return []
        top = min(1 + have + jokers, 6, len(self.hands[seat]))
        return list(range(3, top + 1))

    def _resolve_claims(self):
        seat = self.last["seat"]
        tile = self.last["tile"]
        entries = {int(s): c for s, c in self.claims["bots"].items()}
        human = self.claims.get("human")
        if isinstance(human, dict):
            entries[self.human] = human
        order = [(seat + i) % 4 for i in (1, 2, 3)]
        winner = next((s for s in order if entries.get(s, {}).get("kind") == "mahjong"), None)
        if winner is not None:
            self.hands[winner].append(tile)
            self.discards.pop()
            self._log(f"{self.who(winner)} called {tile_name(tile)} for Mahjong!")
            self._end(winner, seat, mahjong(self.card, self.holding(winner)))
            return
        caller = next((s for s in order if entries.get(s, {}).get("kind") == "expose"), None)
        if caller is None:
            self._start_turn((seat + 1) % 4)
            return
        self.discards.pop()
        self._expose(caller, tile, entries[caller]["size"])

    def _expose(self, seat, tile, size):
        hand = self.hands[seat]
        group = [tile]
        while len(group) < size and tile in hand:
            hand.remove(tile)
            group.append(tile)
        while len(group) < size:
            hand.remove(JOKER)
            group.append(JOKER)
        self.exposures[seat].append({"code": tile, "tiles": group})
        self.current = seat
        self.turn = "discard"
        self.from_wall = False
        self.claims = None
        kind = {3: "pung", 4: "kong", 5: "quint", 6: "sextet"}[size]
        self._log(f"{self.who(seat)} called {tile_name(tile)} and exposed a {kind}.")
        if seat == self.human and not exposures_possible(self.card, self.exposures[seat]):
            self.dead[seat] = True
            self._log("Your exposures no longer fit any hand on the card: your hand is dead. "
                      "Keep playing, but you cannot win this game.")

    def _swaps_for(self, seat):
        out = []
        for s in range(4):
            for i, e in enumerate(self.exposures[s]):
                if JOKER in e["tiles"] and e["code"] in self.hands[seat]:
                    out.append({"seat": s, "index": i, "tile": e["code"]})
        return out

    def swap_joker(self, seat, owner, index):
        e = self.exposures[owner][index]
        tile = e["code"]
        if JOKER not in e["tiles"] or tile not in self.hands[seat]:
            raise GameError("That exposure has no joker you can swap for.")
        e["tiles"][e["tiles"].index(JOKER)] = tile
        self.hands[seat].remove(tile)
        self.hands[seat].append(JOKER)
        self._log(f"{self.who(seat)} swapped {tile_name(tile)} for a joker from "
                  f"{self.who(owner) if owner != seat else 'their own'} exposure.")

    def _end(self, winner, discarder, binding):
        self.phase = "over"
        self.turn = None
        self.claims = None
        if winner is None:
            self.result = {"winner": None, "wall_game": True, "payments": [0, 0, 0, 0]}
            self._log("The wall is empty: wall game, no winner.")
            return
        self_drawn = discarder is None
        all_tiles = self.hands[winner] + [t for e in self.exposures[winner] for t in e["tiles"]]
        jokerless = JOKER not in all_tiles and not binding.hand.singles_and_pairs
        base = binding.hand.points * (2 if jokerless else 1)
        payments = [0, 0, 0, 0]
        for s in range(4):
            if s == winner:
                continue
            pay = base * 2 if (self_drawn or s == discarder) else base
            payments[s] -= pay
            payments[winner] += pay
        self.result = {"winner": winner, "wall_game": False, "hand_id": binding.hand.id,
                       "hand": binding.hand.display, "points": binding.hand.points,
                       "self_drawn": self_drawn, "discarder": discarder,
                       "jokerless": jokerless, "payments": payments}
        how = "self-drawn" if self_drawn else f"on {self.who(discarder)}'s discard"
        self._log(f"{self.who(winner)} won with {binding.hand.display} ({binding.hand.id}) {how}.")

    def _declare(self, seat):
        if self.dead[seat]:
            raise GameError("Your hand is dead; you cannot declare Mahjong this game.")
        b = mahjong(self.card, self.holding(seat))
        if b is None:
            raise GameError(why_not_mahjong(self.card, self.holding(seat)))
        discarder = None if self.from_wall else self.last["seat"]
        self._end(seat, discarder, b)

    # ----------------------------------------------------------------- driver
    def advance(self):
        """Run bot actions until the human must act or the game ends."""
        while self.phase == "play":
            if self.turn == "call":
                if self.claims.get("human") == "pending":
                    return
                self._resolve_claims()
                continue
            if self.current == self.human:
                return
            seat = self.current
            for s in bots.swaps(self, seat):
                self.swap_joker(seat, s["seat"], s["index"])
            if mahjong(self.card, self.holding(seat)):
                self._declare(seat)
                return
            self._discard(seat, bots.discard(self, seat))

    def act(self, action):
        """Apply one human action, then let the bots play. Raises GameError."""
        p = self.prompt()
        kind = action.get("type")
        if p is None or (kind not in self._allowed(p["type"])):
            raise GameError("That action is not available right now.")
        handler = getattr(self, f"_act_{kind}")
        handler(action, p)
        self.advance()

    @staticmethod
    def _allowed(prompt_type):
        return {"pass": {"pass"}, "vote": {"vote"}, "courtesy": {"courtesy"},
                "discard": {"discard", "swap", "mahjong"},
                "call": {"call", "pass_call", "mahjong"}, "over": set()}[prompt_type]

    def _check_own(self, tiles):
        rack = Counter(self.hands[self.human])
        if JOKER in tiles:
            raise GameError("Jokers can never be passed.")
        if Counter(tiles) - rack:
            raise GameError("You can only pass tiles from your own rack.")

    def _act_pass(self, action, p):
        tiles = list(action.get("tiles", []))
        blind = int(action.get("blind", 0))
        if blind and not p["blind_allowed"]:
            raise GameError("Blind passing is only allowed on the last pass of a Charleston.")
        if not 0 <= blind <= 3 or len(tiles) + blind != 3:
            raise GameError("Pass exactly 3 tiles (counting blind-passed tiles).")
        self._check_own(tiles)
        self._apply_pass(tiles, blind)
        self._next_stage()

    def _act_vote(self, action, p):
        human_yes = bool(action.get("continue"))
        bot_yes = all(bots.continue_charleston(self, s) for s in range(4) if s != self.human)
        if human_yes and bot_yes:
            self._log("Everyone agreed to a second Charleston.")
            self._next_stage()
        else:
            who = "You" if not human_yes else "A player"
            self._log(f"{who} stopped the Charleston; no second Charleston.")
            self.stage = COURTESY_STAGE - 1
            self._next_stage()

    def _act_courtesy(self, action, p):
        tiles = list(action.get("tiles", []))
        if len(tiles) > p["max"]:
            raise GameError(f"Your partner across offers only {p['max']} tile(s).")
        self._check_own(tiles)
        self._courtesy(tiles)
        self._next_stage()

    def _act_discard(self, action, p):
        tile = action.get("tile")
        if tile not in self.hands[self.human]:
            raise GameError("You don't have that tile.")
        self._discard(self.human, tile)

    def _act_swap(self, action, p):
        self.swap_joker(self.human, int(action["seat"]), int(action["index"]))

    def _act_mahjong(self, action, p):
        if p["type"] == "discard":
            self._declare(self.human)
            return
        test = Holding(self.hands[self.human] + [self.last["tile"]], self.exposures[self.human])
        if self.dead[self.human]:
            raise GameError("Your hand is dead; you cannot declare Mahjong this game.")
        if mahjong(self.card, test) is None:
            raise GameError(why_not_mahjong(self.card, test))
        self.claims["human"] = {"kind": "mahjong"}

    def _act_call(self, action, p):
        size = int(action.get("size", 0))
        if size not in p["sizes"]:
            raise GameError("You can't expose that many with the tiles you hold.")
        self.claims["human"] = {"kind": "expose", "size": size}

    def _act_pass_call(self, action, p):
        self.claims["human"] = None
