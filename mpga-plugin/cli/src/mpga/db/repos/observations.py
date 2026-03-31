"""ObservationRepo — CRUD, queue, dedup, and FIFO eviction."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from mpga.db.fts_utils import prefix_match_query


@dataclass
class Observation:
    id: int | None = None
    session_id: str | None = None
    scope_id: str | None = None
    title: str = ""
    type: str = "tool_output"
    narrative: str | None = None
    facts: str | None = None
    concepts: str | None = None
    files_read: str | None = None
    files_modified: str | None = None
    tool_name: str | None = None
    priority: int = 2
    evidence_links: str | None = None
    data_hash: str | None = None
    created_at: str = ""


@dataclass
class QueueItem:
    id: int | None = None
    session_id: str | None = None
    tool_name: str | None = None
    tool_input: str | None = None
    tool_output: str | None = None
    created_at: str = ""
    processed: int = 0


_OBS_COLS = (
    "id, session_id, scope_id, title, type, narrative, facts, "
    "concepts, files_read, files_modified, tool_name, priority, "
    "evidence_links, data_hash, created_at"
)

_QUEUE_COLS = (
    "id, session_id, tool_name, tool_input, tool_output, created_at, processed"
)


def _prefixed(cols: str, alias: str) -> str:
    """Add a table alias prefix to a comma-separated column string."""
    return ", ".join(f"{alias}.{c.strip()}" for c in cols.split(","))


class ObservationRepo:
    def __init__(self, conn: sqlite3.Connection, max_observations: int = 1000) -> None:
        self._conn = conn
        self._max = max_observations

    def create(self, obs: Observation) -> Observation | None:
        if obs.data_hash is not None:
            recent = self._conn.execute(
                "SELECT id, data_hash FROM observations ORDER BY id DESC LIMIT 10"
            ).fetchall()
            if any(r[1] == obs.data_hash for r in recent):
                return None

        cur = self._conn.execute(
            "INSERT INTO observations"
            "  (session_id, scope_id, title, type, narrative, facts, concepts,"
            "   files_read, files_modified, tool_name, priority, evidence_links,"
            "   data_hash, created_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
            (
                obs.session_id, obs.scope_id, obs.title, obs.type,
                obs.narrative, obs.facts, obs.concepts,
                obs.files_read, obs.files_modified, obs.tool_name,
                obs.priority, obs.evidence_links, obs.data_hash,
            ),
        )
        self._conn.commit()
        obs_id = cur.lastrowid

        count = self._conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        if count > self._max:
            self._conn.execute(
                "DELETE FROM observations WHERE id IN ("
                "  SELECT id FROM observations"
                "  ORDER BY priority DESC, created_at ASC, id ASC"
                "  LIMIT ?"
                ")",
                (count - self._max,),
            )
            self._conn.commit()

        return self.get_by_id(obs_id)

    def get_by_id(self, obs_id: int) -> Observation | None:
        row = self._conn.execute(
            f"SELECT {_OBS_COLS} FROM observations WHERE id = ?",
            (obs_id,),
        ).fetchone()
        if row is None:
            return None
        return Observation(*row)

    def list_for_session(self, session_id: str | None) -> list[Observation]:
        if session_id is None:
            rows = self._conn.execute(
                f"SELECT {_OBS_COLS} FROM observations WHERE session_id IS NULL"
            ).fetchall()
        else:
            rows = self._conn.execute(
                f"SELECT {_OBS_COLS} FROM observations WHERE session_id = ?",
                (session_id,),
            ).fetchall()
        return [Observation(*r) for r in rows]

    def search(self, query: str, limit: int = 10) -> list[Observation]:
        match_query = prefix_match_query(query)
        rows = self._conn.execute(
            f"SELECT {_prefixed(_OBS_COLS, 'o')} "
            "FROM observations_fts "
            "JOIN observations o ON o.id = observations_fts.rowid "
            "WHERE observations_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (match_query, limit),
        ).fetchall()
        return [Observation(*r) for r in rows]

    def delete(self, obs_id: int) -> None:
        self._conn.execute("DELETE FROM observations WHERE id = ?", (obs_id,))
        self._conn.commit()

    def enqueue(self, item: QueueItem) -> QueueItem:
        cur = self._conn.execute(
            "INSERT INTO observation_queue"
            "  (session_id, tool_name, tool_input, tool_output, created_at, processed)"
            " VALUES (?,?,?,?,datetime('now'),0)",
            (item.session_id, item.tool_name, item.tool_input, item.tool_output),
        )
        self._conn.commit()
        row = self._conn.execute(
            f"SELECT {_QUEUE_COLS} FROM observation_queue WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return QueueItem(*row)

    def evict_old(self, max_count: int) -> int:
        """Remove lowest-priority, oldest observations when count exceeds max_count."""
        count = self._conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        excess = count - max_count
        if excess <= 0:
            return 0
        self._conn.execute(
            "DELETE FROM observations WHERE id IN ("
            "  SELECT id FROM observations"
            "  ORDER BY priority DESC, created_at ASC, id ASC"
            "  LIMIT ?"
            ")",
            (excess,),
        )
        self._conn.commit()
        return excess

    def cleanup_by_age(self, retention_days: int) -> int:
        """Remove observations older than retention_days."""
        cur = self._conn.execute(
            "DELETE FROM observations WHERE created_at < datetime('now', ? || ' days')",
            (f"-{retention_days}",),
        )
        self._conn.commit()
        return cur.rowcount

    def dequeue(self, session_id: str, batch_size: int = 50) -> list[QueueItem]:
        rows = self._conn.execute(
            f"SELECT {_QUEUE_COLS} FROM observation_queue "
            "WHERE processed = 0 AND session_id = ? LIMIT ?",
            (session_id, batch_size),
        ).fetchall()
        if rows:
            ids = [r[0] for r in rows]
            placeholders = ",".join("?" * len(ids))
            self._conn.execute(
                f"UPDATE observation_queue SET processed = 1 WHERE id IN ({placeholders})",
                ids,
            )
            self._conn.commit()
        return [QueueItem(*r) for r in rows]
