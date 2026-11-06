#!/usr/bin/env python3
"""Play bot-only games through the public Game API and check invariants.

Usage: python sim.py --games 1000 --difficulty normal
"""

import argparse
import os
import sys
import traceback
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from mahjong import bots
from mahjong.card import load_card
from mahjong.game import Game
from mahjong.matcher import mahjong
from mahjong.tiles import JOKER, full_set

CARD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards", "practice_card.json")
FULL = Counter(full_set())
MAX_ACTIONS = 2000


def autopilot(game):
    """Choose the human seat's action with the same policy the bots use."""
    h = game.human
    p = game.prompt()
    t = p["type"]
    if t == "pass":
        return {"type": "pass", "tiles": bots.charleston_pass(game, h, 3)}
    if t == "vote":
        return {"type": "vote", "continue": bots.continue_charleston(game, h)}
    if t == "courtesy":
        n = min(p["max"], bots.courtesy_count(game, h))
        return {"type": "courtesy", "tiles": bots.charleston_pass(game, h, n)}
    if t == "discard":
        if p["can_mahjong"] and mahjong(game.card, game.holding(h)):
            return {"type": "mahjong"}
        for s in bots.swaps(game, h):
            return {"type": "swap", "seat": s["seat"], "index": s["index"]}
        return {"type": "discard", "tile": bots.discard(game, h)}
    if t == "call":
        c = bots.claim(game, h, p["tile"])
        if c and c["kind"] == "mahjong":
            return {"type": "mahjong"}
        if c and c["size"] in p["sizes"]:
            return {"type": "call", "size": c["size"]}
        return {"type": "pass_call"}
    raise AssertionError(f"unexpected prompt {p}")


def check_invariants(game):
    errors = []
    tiles = Counter(game.wall)
    for s in range(4):
        tiles.update(game.hands[s])
        for e in game.exposures[s]:
            tiles.update(e["tiles"])
            if len(e["tiles"]) < 3 or set(e["tiles"]) - {e["code"], JOKER} \
                    or e["code"] not in e["tiles"] or e["code"] == JOKER:
                errors.append(f"illegal exposure {e}")
    tiles.update(d["tile"] for d in game.discards)
    if tiles != FULL:
        errors.append(f"tile conservation broken: {sum(tiles.values())} tiles")
    if game.phase == "play" and game.turn == "discard":
        size = game.holding(game.current).size()
        if size != 14:
            errors.append(f"seat {game.current} has {size} tiles on its turn")
    return errors


def play_one(args):
    seed, difficulty = args
    card = load_card(CARD_PATH)
    try:
        game = Game.new(card, seed=seed, difficulty=difficulty)
        game.advance()
        for _ in range(MAX_ACTIONS):
            errs = check_invariants(game)
            if errs:
                return {"seed": seed, "error": "; ".join(errs)}
            if game.phase == "over":
                r = game.result
                return {"seed": seed, "winner": r["winner"], "hand": r.get("hand_id"),
                        "human_won": r["winner"] == game.human}
            game.act(autopilot(game))
        return {"seed": seed, "error": "game did not finish"}
    except Exception:
        return {"seed": seed, "error": traceback.format_exc()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--difficulty", choices=["easy", "normal"], default="normal")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    jobs = [(a.seed + i, a.difficulty) for i in range(a.games)]
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(play_one, jobs, chunksize=8))
    errors = [r for r in results if "error" in r]
    done = [r for r in results if "error" not in r]
    wins = sum(1 for r in done if r["winner"] is not None)
    hands = Counter(r["hand"] for r in done if r["hand"])
    print(f"games={a.games} difficulty={a.difficulty} finished={len(done)} "
          f"exceptions_or_violations={len(errors)}")
    print(f"wins={wins} wall_games={len(done) - wins}")
    print(f"most common winning hands: {hands.most_common(8)}")
    for r in errors[:3]:
        print(f"--- seed {r['seed']}:\n{r['error']}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
