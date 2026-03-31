"""DecisionRepo — CRUD + FTS5 for Architecture Decision Records."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Decision:
    id: str
    title: str
    status: str = "accepted"
    content: str | None = None
    created_at: str = ""


class DecisionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, id: str, title: str, content: str | None = None) -> Decision:
        self._conn.execute(
            "INSERT INTO decisions (id, title, content, created_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (id, title, content),
        )
        self._conn.execute(
            "INSERT INTO decisions_fts(rowid, title, content) "
            "SELECT rowid, title, content FROM decisions WHERE id = ?",
            (id,),
        )
        self._conn.commit()
        return self.get(id)  # type: ignore[return-value]

    def get(self, decision_id: str) -> Decision | None:
        row = self._conn.execute(
            "SELECT id, title, status, content, created_at FROM decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()
        if row is None:
            return None
        return Decision(*row)

    def list_all(self) -> list[Decision]:
        rows = self._conn.execute(
            "SELECT id, title, status, content, created_at FROM decisions"
        ).fetchall()
        return [Decision(*r) for r in rows]

    def search(self, query: str, limit: int = 10) -> list[Decision]:
        rows = self._conn.execute(
            """
            SELECT d.id, d.title, d.status, d.content, d.created_at
            FROM decisions_fts
            JOIN decisions d ON d.rowid = decisions_fts.rowid
            WHERE decisions_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [Decision(*r) for r in rows]
