"""SQLite storage for games in progress, keyed by an anonymous session id."""

import json
import sqlite3
import time
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    state_json TEXT NOT NULL,
    coach_count INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
)
"""


class GameStore:
    def __init__(self, path, ttl_hours=24):
        self.path = path
        self.ttl = ttl_hours * 3600
        with closing(self._conn()) as c, c:
            c.execute(SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path, timeout=10)

    def save(self, game_id, session_id, state):
        now = time.time()
        with closing(self._conn()) as c, c:
            c.execute("DELETE FROM games WHERE updated_at < ?", (now - self.ttl,))
            c.execute(
                "INSERT INTO games (id, session_id, state_json, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET state_json = excluded.state_json, "
                "updated_at = excluded.updated_at",
                (game_id, session_id, json.dumps(state), now))

    def load(self, game_id, session_id):
        """Return (state, coach_count) or None if missing, expired, or not this session's."""
        with closing(self._conn()) as c:
            row = c.execute(
                "SELECT state_json, coach_count, updated_at FROM games WHERE id = ? AND session_id = ?",
                (game_id, session_id)).fetchone()
        if not row or row[2] < time.time() - self.ttl:
            return None
        return json.loads(row[0]), row[1]

    def bump_coach(self, game_id, limit):
        """Atomically count one coach message. False when the game's cap is reached."""
        with closing(self._conn()) as c, c:
            cur = c.execute(
                "UPDATE games SET coach_count = coach_count + 1 WHERE id = ? AND coach_count < ?",
                (game_id, limit))
            return cur.rowcount == 1
