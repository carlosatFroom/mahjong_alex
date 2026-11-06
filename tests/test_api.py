import json
from collections import Counter
import time

import pytest

import coach
from app import create_app
from mahjong.game import Game
from mahjong.tiles import JOKER


class FakeProvider:
    def __init__(self, fail=False):
        self.fail = fail
        self.messages = []

    def chat(self, system, message):
        self.messages.append(message)
        if self.fail:
            raise RuntimeError("provider down")
        return {"content": "Keep your flowers and go for 2468.", "total_tokens": 42}


@pytest.fixture
def app(tmp_path):
    return create_app({"DB_PATH": str(tmp_path / "games.sqlite3"), "GROQ_API_KEY": "",
                       "COACH_MAX_MESSAGES": 3})


@pytest.fixture
def client(app):
    return app.test_client()


def start(client, difficulty="easy"):
    r = client.post("/api/game", json={"difficulty": difficulty})
    assert r.status_code == 200
    return r.json["game_id"], r.json["view"]


def test_page_and_card(client):
    assert client.get("/").status_code == 200
    hands = client.get("/api/card").json["hands"]
    assert len(hands) == 34


def test_new_game_and_refresh_returns_same_state(client):
    gid, view = start(client)
    again = client.get(f"/api/game/{gid}").json["view"]
    assert again["hand"] == view["hand"]
    assert again["prompt"] == view["prompt"]


def test_other_session_cannot_read_game(app, client):
    gid, _ = start(client)
    other = app.test_client()
    assert other.get(f"/api/game/{gid}").status_code == 404


def test_action_loop_reaches_next_human_prompt(client):
    gid, view = start(client)
    tiles = [t for t in view["hand"] if t != JOKER][:3]
    r = client.post(f"/api/game/{gid}/action", json={"type": "pass", "tiles": tiles})
    assert r.status_code == 200
    assert r.json["view"]["prompt"]["direction"] == "across"


def test_illegal_action_is_400_with_reason(client):
    gid, view = start(client)
    r = client.post(f"/api/game/{gid}/action", json={"type": "discard", "tile": view["hand"][0]})
    assert r.status_code == 400 and "not available" in r.json["error"]
    r = client.post(f"/api/game/{gid}/action", json={"type": "pass", "tiles": ["J", "J", "J"]})
    assert r.status_code == 400


def test_expired_game_is_404(app, client):
    gid, _ = start(client)
    store = app.extensions["mahjong"]["store"]
    store.ttl = -1
    assert client.get(f"/api/game/{gid}").status_code == 404


def test_hint_without_llm_returns_engine_facts(client):
    gid, _ = start(client)
    r = client.post(f"/api/game/{gid}/coach", json={"kind": "hint"})
    assert r.status_code == 200
    assert r.json["source"] == "engine"
    assert "away" in r.json["text"] and "need" in r.json["text"] and "Suggested pass" in r.json["text"]
    assert "your version:" in r.json["text"]


def test_coach_cap_applies_to_questions_not_hints(client):
    gid, _ = start(client)
    for _ in range(3):
        r = client.post(f"/api/game/{gid}/coach", json={"kind": "question", "text": "What is a kong?"})
        assert r.status_code == 200
    r = client.post(f"/api/game/{gid}/coach", json={"kind": "question", "text": "What is a kong?"})
    assert r.status_code == 429 and "Hint button still works" in r.json["error"]
    r = client.post(f"/api/game/{gid}/coach", json={"kind": "hint"})
    assert r.status_code == 200 and r.json["source"] == "engine"


def test_llm_failure_falls_back(app, client):
    app.extensions["mahjong"]["provider"] = None
    gid, _ = start(client)
    card = app.extensions["mahjong"]["card"]
    found = app.extensions["mahjong"]["store"].load(gid, _sid(client))
    game = Game.from_dict(card, found[0])
    out = coach.answer(FakeProvider(fail=True), "sys", card, game.view_for(game.human), "What now?")
    assert out["source"] == "engine" and "away" in out["text"]


def _sid(client):
    with client.session_transaction() as s:
        return s["sid"]


def test_coach_payload_has_no_bot_concealed_tiles(app, client):
    gid, _ = start(client, "normal")
    card = app.extensions["mahjong"]["card"]
    game = Game.from_dict(card, app.extensions["mahjong"]["store"].load(gid, _sid(client))[0])
    view = game.view_for(game.human)
    visible = set(view["hand"]) | {d["tile"] for d in view["discards"]}
    hidden = {t for s in range(4) if s != game.human for t in game.hands[s]} - visible
    assert hidden
    provider = FakeProvider()
    coach.answer(provider, "sys", card, view, "What should I pass?")
    state = provider.messages[0].split("ENGINE FACTS")[0]
    words = {w for line in state.splitlines() if not line.startswith("Tile codes")
             for w in line.replace(":", " ").split()}
    assert not (hidden & words)
    assert "reveal" not in provider.messages[0]


def test_discard_feedback(client, app):
    gid, view = start(client)
    # Walk through the Charleston with "first three non-joker tiles" until a discard prompt.
    for _ in range(10):
        p = view["prompt"]
        if p["type"] == "pass":
            body = {"type": "pass", "tiles": [t for t in view["hand"] if t != JOKER][:3]}
        elif p["type"] == "vote":
            body = {"type": "vote", "continue": False}
        elif p["type"] == "courtesy":
            body = {"type": "courtesy", "tiles": []}
        else:
            break
        view = client.post(f"/api/game/{gid}/action", json=body).json["view"]
    while view["prompt"]["type"] != "discard":
        p = view["prompt"]
        body = {"type": "pass_call"} if p["type"] == "call" else None
        if body is None:
            pytest.skip("game ended before the human's turn")
        view = client.post(f"/api/game/{gid}/action", json=body).json["view"]
    r = client.post(f"/api/game/{gid}/action", json={"type": "discard", "tile": view["hand"][0]})
    assert r.status_code == 200
    assert "feedback" in r.json


def test_hint_discard_reason_matches_closest_hands(card):
    """The suggested discard must not be a tile every listed hand needs unless it says so."""
    from mahjong.coach_facts import _uses, hint_facts
    from mahjong.tiles import tile_name
    from sim import autopilot
    checked = 0
    for seed in range(12):
        g = Game.new(card, seed=seed, human=1)
        g.advance()
        while g.phase != "over" and checked < 40:
            p = g.prompt()
            if p["type"] == "discard":
                view = g.view_for(g.human)
                facts = hint_facts(card, view)
                d = facts.get("suggest_discard")
                if d:
                    code = next(t for t in view["hand"] if tile_name(t) == d["tile"])
                    have = Counter(t for t in view["hand"] if t != "J")
                    users = [h for h in facts["closest_hands"] if _uses(h["_binding"], code, have)]
                    if not users:
                        assert d["why"].startswith("none")
                    elif len(users) == len(facts["closest_hands"]):
                        assert d["why"].startswith("every")
                    else:
                        assert d["why"].startswith("only hand")
                    checked += 1
            g.act(autopilot(g))
    assert checked >= 20


def test_following_the_hint_never_triggers_feedback(card):
    from mahjong.coach_facts import hint_facts, move_feedback
    from mahjong.tiles import tile_name
    from sim import autopilot
    followed = scolded_alternative = 0
    for seed in range(10):
        g = Game.new(card, seed=seed, human=2)
        g.advance()
        while g.phase != "over":
            if g.prompt()["type"] == "discard":
                view = g.view_for(g.human)
                d = hint_facts(card, view).get("suggest_discard")
                if d:
                    code = next(t for t in view["hand"] if tile_name(t) == d["tile"])
                    assert move_feedback(card, view, code) is None
                    followed += 1
                    worse = [t for t in set(view["hand"]) if t != "J" and move_feedback(card, view, t)]
                    scolded_alternative += bool(worse)
            g.act(autopilot(g))
    assert followed >= 20 and scolded_alternative > 0
