"""ScopeRepo — CRUD + FTS5 search for the scopes table."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class Scope:
    id: str
    name: str
    summary: str | None = None
    content: str | None = None
    status: str = "fresh"
    evidence_total: int = 0
    evidence_valid: int = 0
    last_verified: str | None = None
    created_at: str = ""
    updated_at: str = ""


class ScopeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, scope: Scope) -> Scope:
        self._conn.execute(
            """
            INSERT INTO scopes
                (id, name, summary, content, status,
                 evidence_total, evidence_valid, last_verified,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                scope.id, scope.name, scope.summary, scope.content,
                scope.status, scope.evidence_total, scope.evidence_valid,
                scope.last_verified,
            ),
        )
        self._conn.execute("INSERT INTO scopes_fts(scopes_fts) VALUES('rebuild')")
        self._conn.commit()
        return self.get(scope.id)  # type: ignore[return-value]

    def get(self, scope_id: str) -> Scope | None:
        row = self._conn.execute(
            "SELECT id, name, summary, content, status, "
            "evidence_total, evidence_valid, last_verified, "
            "created_at, updated_at FROM scopes WHERE id = ?",
            (scope_id,),
        ).fetchone()
        if row is None:
            return None
        return Scope(*row)

    def update(self, scope: Scope) -> Scope:
        self._conn.execute(
            """
            UPDATE scopes SET
                name = ?, summary = ?, content = ?, status = ?,
                evidence_total = ?, evidence_valid = ?,
                last_verified = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                scope.name, scope.summary, scope.content, scope.status,
                scope.evidence_total, scope.evidence_valid,
                scope.last_verified, scope.id,
            ),
        )
        # Sync FTS: rebuild entire index (safe for content-sync tables)
        self._conn.execute("INSERT INTO scopes_fts(scopes_fts) VALUES('rebuild')")
        self._conn.commit()
        return self.get(scope.id)  # type: ignore[return-value]

    def delete(self, scope_id: str) -> None:
        self._conn.execute("DELETE FROM scopes WHERE id = ?", (scope_id,))
        self._conn.execute("INSERT INTO scopes_fts(scopes_fts) VALUES('rebuild')")
        self._conn.commit()

    def list_all(self) -> list[Scope]:
        rows = self._conn.execute(
            "SELECT id, name, summary, content, status, "
            "evidence_total, evidence_valid, last_verified, "
            "created_at, updated_at FROM scopes"
        ).fetchall()
        return [Scope(*r) for r in rows]

    # ------------------------------------------------------------------
    # FTS5 search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 10,
        scope_id: str | None = None,
    ) -> list[tuple[Scope, str]]:
        """Return (Scope, snippet) tuples ranked by BM25 relevance."""
        if scope_id is None:
            rows = self._conn.execute(
                """
                SELECT s.id, s.name, s.summary, s.content, s.status,
                       s.evidence_total, s.evidence_valid, s.last_verified,
                       s.created_at, s.updated_at,
                       snippet(scopes_fts, 2, '[', ']', '...', 20)
                FROM scopes_fts
                JOIN scopes s ON s.rowid = scopes_fts.rowid
                WHERE scopes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT s.id, s.name, s.summary, s.content, s.status,
                       s.evidence_total, s.evidence_valid, s.last_verified,
                       s.created_at, s.updated_at,
                       snippet(scopes_fts, 2, '[', ']', '...', 20)
                FROM scopes_fts
                JOIN scopes s ON s.rowid = scopes_fts.rowid
                WHERE scopes_fts MATCH ?
                  AND s.id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, scope_id, limit),
            ).fetchall()
        return [(Scope(*r[:10]), r[10]) for r in rows]
