"""Coach. Hints are written by the engine (mahjong.coach_facts); the LLM only
answers typed questions, grounded in the same engine facts.
"""

import logging

from mahjong.coach_facts import coach_view, facts_text, hint_facts
from mahjong.tiles import tile_name

logger = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """You are the coach at a Woodlands Mahjong Society practice table. \
The player has learned American Mahjong and is practicing against three computer players.

Rules of this table:
{rules}

The card in use:
{card}

How to coach:
- Be brief (2 to 5 short sentences), warm, and concrete.
- ENGINE FACTS are computed by the game engine and are always correct. Never contradict \
them. Never state which tiles the player holds, needs, or should pass/discard unless it is \
written in the ENGINE FACTS or the player rack; do not count tiles yourself.
- American Mahjong has no runs/chows or straights; groups are pungs, kongs, quints, \
singles and pairs exactly as printed on the card.
- You only know what the player can see: their own rack, exposures, and discards. Never \
guess what other players hold.
- Explain the *why* (e.g. flexibility, joker use, what others have exposed) so the player learns.
- Only discuss Mahjong."""


def system_prompt(card, rules_text):
    return SYSTEM_TEMPLATE.format(rules=rules_text, card=card.text())


def _state_summary(view):
    v = coach_view(view)
    me = view["seat"]
    others = []
    for s, name in enumerate(v["names"]):
        if s == me:
            continue
        exps = ["".join(e["tiles"]) for e in v["exposures"][s]]
        others.append(f"{name}: exposures {exps or 'none'}")
    recent = [f"{v['names'][d['seat']]}:{d['tile']}" for d in v["discards"][-12:]]
    return "\n".join([
        f"Phase: {v['phase']}. Player sits {v['seat_wind']}. Tiles left in wall: {v['wall_count']}.",
        f"Player rack: {' '.join(v['hand'])} ({', '.join(tile_name(t) for t in v['hand'])})",
        f"Player exposures: {[''.join(e['tiles']) for e in v['exposures'][me]] or 'none'}",
        "Other players: " + "; ".join(others),
        f"Recent discards: {' '.join(recent) or 'none'}",
        f"Waiting for the player to: {(v.get('prompt') or {}).get('type', 'nothing')}",
        "Tile codes: 1B-9B Bams, 1C-9C Craks, 1D-9D Dots, N E W S winds, "
        "GD RD WD dragons (WD = Soap), F flower, J joker.",
    ])


def build_message(card, view, question):
    """Return (user_message, facts). Only the human's view is used."""
    facts = hint_facts(card, view)
    msg = (f"GAME STATE\n{_state_summary(view)}\n\n"
           f"ENGINE FACTS (correct; the player can see them)\n{facts_text(facts)}\n\n"
           f"The player asks: {question}")
    return msg, facts


def hint(card, view):
    """The Hint button: written entirely by the engine, so it can't misread the rack."""
    return {"text": facts_text(hint_facts(card, view)), "source": "engine"}


def answer(provider, system, card, view, question):
    """Answer a typed question with the LLM; fall back to the engine hint on failure."""
    message, facts = build_message(card, view, question)
    if provider is None:
        return {"text": facts_text(facts), "source": "engine"}
    try:
        out = provider.chat(system, message)
    except RuntimeError as e:
        logger.warning(f"Coach LLM unavailable, using engine facts: {e}")
        return {"text": facts_text(facts), "source": "engine"}
    text = (out.get("content") or "").strip()
    if not text:
        return {"text": facts_text(facts), "source": "engine"}
    return {"text": text, "source": "llm", "tokens": out["total_tokens"]}
