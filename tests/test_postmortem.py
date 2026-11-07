import json

import pytest

from app import create_app
from mahjong import postmortem
from mahjong.game import Game
from sim import autopilot

NAMES = ["You", "Pearl", "Hazel", "Ivy"]
RESULT = {"winner": 1, "wall_game": False, "hand": "FF 2468 2468 2468"}


def _entry(label, hands, kind="discard", visible_by=None, **kw):
    e = {"kind": kind, "label": label, "action": kw.pop("action", "discarded 5 Dot"),
         "visible_by": visible_by or {"Pearl": {}, "Hazel": {}, "Ivy": {}},
         "hands": [{"id": i, "display": d, "points": 25, "odds": o, "needed": 3,
                    "missing": m} for i, d, o, m in hands],
         "hidden": kw.pop("hidden", {}), "feedback": kw.pop("feedback", None)}
    e.update(kw)
    return e


def test_empty_history():
    pm = postmortem.build([], RESULT, NAMES, 0)
    assert pm["empty"] and pm["text"] == "Nothing to review yet."
    assert pm["summary"] == "Pearl won with FF 2468 2468 2468."


def test_collapse_switch_and_costly_are_reported():
    like = ("L1", "Like Numbers", 0.20, [["2D", 2]])
    winds = ("W1", "Winds", 0.04, [["N", 1]])
    history = [
        _entry("Your turn 1", [like, winds], played="L1", loss=0.0),
        # Hazel shows two 2 Dots: Like Numbers collapses.
        _entry("Your turn 2", [("L1", "Like Numbers", 0.02, [["2D", 2]]), ("W1", "Winds", 0.05, [["N", 1]])],
               visible_by={"Pearl": {}, "Hazel": {"2D": 2}, "Ivy": {}}, played="W1", loss=0.0),
        # Kept protecting Winds (4%) while Pungs was 30%: missed switch, also costly.
        _entry("Your turn 3", [("P1", "Pungs", 0.30, [["5B", 1]]), ("W1", "Winds", 0.04, [["N", 1]])],
               visible_by={"Pearl": {}, "Hazel": {"2D": 2}, "Ivy": {}}, played="W1", loss=0.15,
               after=[0.15, 0.04],
               feedback="That 5 Bam cost you odds: Pungs 30% → 15%. North would have cost less."),
        # Same streak: not flagged again. A separate costly discard, no switch.
        _entry("Your turn 4", [("P1", "Pungs", 0.30, [["5B", 1]]), ("W1", "Winds", 0.04, [["N", 1]])],
               visible_by={"Pearl": {}, "Hazel": {"2D": 2}, "Ivy": {}}, played="W1", loss=0.02,
               after=[0.28, 0.04],
               feedback="That 9 Crak cost you odds."),
        _entry("Your turn 5", [("P1", "Pungs", 0.25, [["5B", 1]])], played="P1", loss=0.05,
               feedback="That 1 Bam cost you odds.",
               hidden={"5B": {"wall": 1, "seats": {"Ivy": 2}}},
               visible_by={"Pearl": {}, "Hazel": {"2D": 2}, "Ivy": {}}),
    ]
    pm = postmortem.build(history, RESULT, NAMES, 0)
    kinds = [(m["type"], m["at"]) for m in pm["moments"]]
    assert ("collapse", "Your turn 2") in kinds
    assert ("switch", "Your turn 3") in kinds
    assert ("switch", "Your turn 4") not in kinds
    assert ("costly", "Your turn 3") not in kinds          # merged into the switch
    assert ("costly", "Your turn 5") in kinds
    # Protecting another hand with a discard the top hand did not need is not a missed switch.
    harmless = _entry("Your turn 9", [("P1", "Pungs", 0.30, [["5B", 1]]), ("W1", "Winds", 0.04, [["N", 1]])],
                      played="W1", loss=0.0, after=[0.30, 0.04])
    assert postmortem._switches([harmless]) == []
    collapse = next(m for m in pm["moments"] if m["type"] == "collapse")
    assert "Hazel put out 2× 2 Dot" in collapse["text"] and "20%" in collapse["text"]
    assert len(pm["key_moments"]) == 3
    assert [m["at"] for m in pm["key_moments"]] == ["Your turn 2", "Your turn 3", "Your turn 5"]
    assert len(pm["timeline"]) == 5 and pm["timeline"][1]["flag"]
    assert pm["hindsight"]["hand"] == "Pungs"
    assert pm["hindsight"]["lines"] == ["1× 5 Bam: 2 in Ivy's rack, 1 still in the wall"]


def test_called_discard_is_not_newly_visible():
    a = _entry("Your turn 1", [("L1", "Like", 0.3, [["2D", 1]])],
               visible_by={"Pearl": {"2D": 1}, "Hazel": {}, "Ivy": {}})
    b = _entry("Your turn 2", [("L1", "Like", 0.0, [["2D", 1]])],
               visible_by={"Pearl": {}, "Hazel": {"2D": 1}, "Ivy": {}})
    assert postmortem._newly_shown(a, b) == []


@pytest.fixture
def client(tmp_path):
    app = create_app({"DB_PATH": str(tmp_path / "g.sqlite3"), "GROQ_API_KEY": ""})
    return app, app.test_client()


def test_full_game_review_and_no_leak(client):
    app, c = client
    ext = app.extensions["mahjong"]
    r = c.post("/api/game", json={"difficulty": "normal"})
    gid = r.json["game_id"]
    with c.session_transaction() as s:
        sid = s["sid"]
    assert c.get(f"/api/game/{gid}/postmortem").status_code == 409
    decisions = 0
    for _ in range(400):
        state, _ = ext["store"].load(gid, sid)
        game = Game.from_dict(ext["card"], state)
        if game.phase == "over":
            break
        action = autopilot(game)
        decisions += action["type"] in ("pass", "courtesy", "discard", "call", "pass_call")
        r = c.post(f"/api/game/{gid}/action", json=action)
        assert r.status_code == 200
        body = json.dumps(r.json)
        for leak in ('"history"', '"hidden"', '"postmortem"', '"visible_by"'):
            assert leak not in body
        assert "history" not in json.dumps(c.get(f"/api/game/{gid}").json)
    assert game.phase == "over"
    pm = c.get(f"/api/game/{gid}/postmortem")
    assert pm.status_code == 200
    assert len(pm.json["timeline"]) == decisions > 0
    assert pm.json["summary"]
    assert c.get(f"/api/game/{gid}/postmortem").json == pm.json   # cached
