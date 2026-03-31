"""LockRepo — acquire/release file and scope locks."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class FileLock:
    filepath: str
    task_id: str
    lane_id: str | None = None
    agent: str | None = None
    acquired_at: str = ""
    heartbeat_at: str | None = None


@dataclass
class ScopeLock:
    scope: str
    task_id: str
    lane_id: str | None = None
    agent: str | None = None
    acquired_at: str = ""
    heartbeat_at: str | None = None


class LockRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # File locks
    # ------------------------------------------------------------------

    def acquire_file(
        self,
        filepath: str,
        task_id: str,
        lane_id: str | None = None,
        agent: str | None = None,
    ) -> FileLock:
        self._conn.execute(
            "INSERT OR REPLACE INTO file_locks "
            "(filepath, task_id, lane_id, agent, acquired_at, heartbeat_at) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            (filepath, task_id, lane_id, agent),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT filepath, task_id, lane_id, agent, acquired_at, heartbeat_at "
            "FROM file_locks WHERE filepath = ? AND task_id = ?",
            (filepath, task_id),
        ).fetchone()
        return FileLock(*row)

    def release_file(self, filepath: str, task_id: str) -> None:
        self._conn.execute(
            "DELETE FROM file_locks WHERE filepath = ? AND task_id = ?",
            (filepath, task_id),
        )
        self._conn.commit()

    def is_file_locked(self, filepath: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM file_locks WHERE filepath = ? LIMIT 1",
            (filepath,),
        ).fetchone()
        return row is not None

    def list_files_for_task(self, task_id: str) -> list[FileLock]:
        rows = self._conn.execute(
            """
            SELECT filepath, task_id, lane_id, agent, acquired_at, heartbeat_at
            FROM file_locks
            WHERE task_id = ?
            ORDER BY filepath
            """,
            (task_id,),
        ).fetchall()
        return [FileLock(*row) for row in rows]

    # ------------------------------------------------------------------
    # Scope locks
    # ------------------------------------------------------------------

    def acquire_scope(
        self,
        scope: str,
        task_id: str,
        lane_id: str | None = None,
        agent: str | None = None,
    ) -> ScopeLock:
        self._conn.execute(
            "INSERT OR REPLACE INTO scope_locks "
            "(scope, task_id, lane_id, agent, acquired_at, heartbeat_at) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            (scope, task_id, lane_id, agent),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT scope, task_id, lane_id, agent, acquired_at, heartbeat_at "
            "FROM scope_locks WHERE scope = ? AND task_id = ?",
            (scope, task_id),
        ).fetchone()
        return ScopeLock(*row)

    def release_scope(self, scope: str, task_id: str) -> None:
        self._conn.execute(
            "DELETE FROM scope_locks WHERE scope = ? AND task_id = ?",
            (scope, task_id),
        )
        self._conn.commit()

    def is_scope_locked(self, scope: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM scope_locks WHERE scope = ? LIMIT 1",
            (scope,),
        ).fetchone()
        return row is not None

    def list_scopes_for_task(self, task_id: str) -> list[ScopeLock]:
        rows = self._conn.execute(
            """
            SELECT scope, task_id, lane_id, agent, acquired_at, heartbeat_at
            FROM scope_locks
            WHERE task_id = ?
            ORDER BY scope
            """,
            (task_id,),
        ).fetchall()
        return [ScopeLock(*row) for row in rows]

    def release_all_for_task(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM file_locks WHERE task_id = ?", (task_id,))
        self._conn.execute("DELETE FROM scope_locks WHERE task_id = ?", (task_id,))
        self._conn.commit()
