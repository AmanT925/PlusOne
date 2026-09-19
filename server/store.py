"""SQLite event log, members, Linq chat bindings, and replay."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from contracts.schema import Constraint, Event


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL,
    ts REAL NOT NULL,
    speaker TEXT NOT NULL,
    visibility TEXT NOT NULL,
    text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS constraints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL,
    user TEXT NOT NULL,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    hard INTEGER NOT NULL,
    event_id INTEGER
);

CREATE TABLE IF NOT EXISTS linq_chats (
    chat_id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    user TEXT
);

CREATE TABLE IF NOT EXISTS members (
    room_id TEXT NOT NULL,
    user TEXT NOT NULL,
    phone TEXT,
    PRIMARY KEY (room_id, user)
);

CREATE TABLE IF NOT EXISTS processed_webhooks (
    event_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS whisper_times (
    room_id TEXT NOT NULL,
    user TEXT NOT NULL,
    ts REAL NOT NULL,
    PRIMARY KEY (room_id, user)
);
"""


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def append_event(
        self, room_id: str, ts: float, speaker: str, visibility: str, text: str
    ) -> Event:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO events (room_id, ts, speaker, visibility, text) "
                "VALUES (?, ?, ?, ?, ?)",
                (room_id, ts, speaker, visibility, text),
            )
            self._conn.commit()
            event_id = int(cur.lastrowid)
        return Event(
            id=event_id, ts=ts, speaker=speaker, visibility=visibility, text=text
        )

    def events(self, room_id: str) -> list[Event]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, ts, speaker, visibility, text FROM events "
                "WHERE room_id = ? ORDER BY id",
                (room_id,),
            ).fetchall()
        return [
            Event(
                id=int(r["id"]),
                ts=float(r["ts"]),
                speaker=r["speaker"],
                visibility=r["visibility"],
                text=r["text"],
            )
            for r in rows
        ]

    def add_constraints(self, room_id: str, event_id: int, items: list[Constraint]) -> None:
        if not items:
            return
        with self._lock:
            self._conn.executemany(
                "INSERT INTO constraints (room_id, user, type, value, hard, event_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (room_id, c.user, c.type, c.value, int(c.hard), event_id)
                    for c in items
                ],
            )
            self._conn.commit()

    def constraints(self, room_id: str) -> list[Constraint]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT user, type, value, hard FROM constraints WHERE room_id = ? ORDER BY id",
                (room_id,),
            ).fetchall()
        return [
            Constraint(
                user=r["user"],
                type=r["type"],
                value=r["value"],
                hard=bool(r["hard"]),
            )
            for r in rows
        ]

    def upsert_member(self, room_id: str, user: str, phone: str | None = None) -> None:
        with self._lock:
            existing = self._conn.execute(
                "SELECT phone FROM members WHERE room_id = ? AND user = ?",
                (room_id, user),
            ).fetchone()
            if existing is None:
                self._conn.execute(
                    "INSERT INTO members (room_id, user, phone) VALUES (?, ?, ?)",
                    (room_id, user, phone),
                )
            elif phone and not existing["phone"]:
                self._conn.execute(
                    "UPDATE members SET phone = ? WHERE room_id = ? AND user = ?",
                    (phone, room_id, user),
                )
            self._conn.commit()

    def members(self, room_id: str) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT user FROM members WHERE room_id = ? ORDER BY user",
                (room_id,),
            ).fetchall()
        return [r["user"] for r in rows]

    def bind_chat(self, chat_id: str, room_id: str, kind: str, user: str | None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO linq_chats (chat_id, room_id, kind, user) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(chat_id) DO UPDATE SET room_id=excluded.room_id, "
                "kind=excluded.kind, user=COALESCE(excluded.user, linq_chats.user)",
                (chat_id, room_id, kind, user),
            )
            self._conn.commit()

    def chat(self, chat_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(
                "SELECT chat_id, room_id, kind, user FROM linq_chats WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()

    def dm_chat_for(self, room_id: str, user: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT chat_id FROM linq_chats WHERE room_id = ? AND kind = 'dm' AND user = ?",
                (room_id, user),
            ).fetchone()
        return row["chat_id"] if row else None

    def group_chat_for(self, room_id: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT chat_id FROM linq_chats WHERE room_id = ? AND kind = 'group'",
                (room_id,),
            ).fetchone()
        return row["chat_id"] if row else None

    def phone_for(self, room_id: str, user: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT phone FROM members WHERE room_id = ? AND user = ?",
                (room_id, user),
            ).fetchone()
        return row["phone"] if row and row["phone"] else None

    def user_for_phone(self, room_id: str, phone: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT user FROM members WHERE room_id = ? AND phone = ?",
                (room_id, phone),
            ).fetchone()
        return row["user"] if row else None

    def already_processed(self, event_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM processed_webhooks WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return row is not None

    def mark_processed(self, event_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO processed_webhooks (event_id) VALUES (?)",
                (event_id,),
            )
            self._conn.commit()

    def last_whisper_at(self, room_id: str, user: str) -> float | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT ts FROM whisper_times WHERE room_id = ? AND user = ?",
                (room_id, user),
            ).fetchone()
        return float(row["ts"]) if row else None

    def set_whisper_at(self, room_id: str, user: str, ts: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO whisper_times (room_id, user, ts) VALUES (?, ?, ?) "
                "ON CONFLICT(room_id, user) DO UPDATE SET ts=excluded.ts",
                (room_id, user, ts),
            )
            self._conn.commit()
