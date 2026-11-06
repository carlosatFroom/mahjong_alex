"""Coach: turns engine facts into short, friendly advice with the LLM.

The LLM never computes anything: hand names, tile counts and suggestions come
from mahjong.coach_facts. If the LLM fails, callers fall back to facts_text().
"""

import json
import logging

from mahjong.coach_facts import coach_view, facts_text, hint_facts

logger = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """You are the coach at a Woodlands Mahjong Society practice table. \
The player has learned American Mahjong and is practicing against three computer players.

Rules of this table:
{rules}

The card in use:
{card}

How to coach:
- Be brief (at most 6 short sentences), warm, and concrete.
- ENGINE FACTS are computed by the game engine and are always correct. Use them; never \
invent hand names, tile counts, or tiles needed. If the facts don't answer something, say so.
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
        f"Player rack: {' '.join(v['hand'])}",
        f"Player exposures: {[''.join(e['tiles']) for e in v['exposures'][me]] or 'none'}",
        "Other players: " + "; ".join(others),
        f"Recent discards: {' '.join(recent) or 'none'}",
        f"Waiting for the player to: {(v.get('prompt') or {}).get('type', 'nothing')}",
        "Tile codes: 1B-9B Bams, 1C-9C Craks, 1D-9D Dots, N E W S winds, "
        "GD RD WD dragons (WD = Soap), F flower, J joker.",
    ])


def build_message(card, view, kind, question=None):
    """Return (user_message, facts). Only the human's view is used."""
    facts = hint_facts(card, view)
    ask = {"hint": "Give the player a hint for their current decision.",
           "question": f"The player asks: {question}"}[kind]
    msg = (f"GAME STATE\n{_state_summary(view)}\n\n"
           f"ENGINE FACTS\n{json.dumps(facts, indent=1)}\n\n{ask}")
    return msg, facts


def reply(provider, system, card, view, kind, question=None):
    """Ask the LLM; on any provider failure return the plain engine facts."""
    message, facts = build_message(card, view, kind, question)
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
