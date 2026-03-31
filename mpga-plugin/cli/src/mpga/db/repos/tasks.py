"""TaskRepo — CRUD + FTS5 search + filter for the tasks table."""

from __future__ import annotations

import sqlite3
from typing import Any

from mpga.board.task import FileLock as TaskFileLock
from mpga.board.task import ScopeLock as TaskScopeLock
from mpga.board.task import Task
from mpga.db.fts_utils import prefix_match_query


class TaskRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(self, task: Task) -> Task:
        self._conn.execute(
            """
            INSERT INTO tasks (
                id, title, body, column_, status, priority,
                milestone, phase, assigned, tdd_stage, lane_id,
                run_status, current_agent, time_estimate,
                created_at, updated_at, started_at, finished_at, heartbeat_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?
            )
            """,
            (
                task.id,
                task.title,
                task.body or "",
                task.column,
                task.status,
                task.priority,
                task.milestone,
                task.phase,
                task.assigned,
                task.tdd_stage,
                task.lane_id,
                task.run_status,
                task.current_agent,
                task.time_estimate,
                task.created,
                task.updated,
                task.started_at,
                task.finished_at,
                task.heartbeat_at,
            ),
        )
        self._insert_junctions(task)
        self._sync_fts()
        self._conn.commit()
        return task

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, task_id: str) -> Task | None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_task(row, task_id)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, task: Task) -> Task:
        self._conn.execute(
            """
            UPDATE tasks SET
                title = ?, body = ?, column_ = ?, status = ?, priority = ?,
                milestone = ?, phase = ?, assigned = ?, tdd_stage = ?,
                lane_id = ?, run_status = ?, current_agent = ?,
                time_estimate = ?, updated_at = ?,
                started_at = ?, finished_at = ?, heartbeat_at = ?
            WHERE id = ?
            """,
            (
                task.title,
                task.body or "",
                task.column,
                task.status,
                task.priority,
                task.milestone,
                task.phase,
                task.assigned,
                task.tdd_stage,
                task.lane_id,
                task.run_status,
                task.current_agent,
                task.time_estimate,
                task.updated,
                task.started_at,
                task.finished_at,
                task.heartbeat_at,
                task.id,
            ),
        )
        # Rebuild junctions
        self._delete_junctions(task.id)
        self._insert_junctions(task)
        # Rebuild FTS
        self._sync_fts()
        self._conn.commit()
        return task

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._sync_fts()
        self._conn.commit()

    # ------------------------------------------------------------------
    # FTS5 search
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> list[Task]:
        match_query = prefix_match_query(query)
        try:
            rows = self._conn.execute(
                """
                SELECT t.*
                FROM tasks t
                JOIN tasks_fts f ON t.rowid = f.rowid
                WHERE tasks_fts MATCH ?
                ORDER BY bm25(tasks_fts)
                LIMIT ?
                """,
                (match_query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return self._rows_to_tasks(rows)

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def filter(
        self,
        column: str | None = None,
        priority: str | None = None,
        milestone: str | None = None,
        scope: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Task]:
        conditions: list[str] = []
        params: list[Any] = []

        if column is not None:
            conditions.append("t.column_ = ?")
            params.append(column)
        if priority is not None:
            conditions.append("t.priority = ?")
            params.append(priority)
        if milestone is not None:
            conditions.append("t.milestone = ?")
            params.append(milestone)

        if scope is not None:
            conditions.append(
                "EXISTS (SELECT 1 FROM task_scopes ts WHERE ts.task_id = t.id AND ts.scope_id = ?)"
            )
            params.append(scope)

        if tags:
            for tag in tags:
                conditions.append(
                    "EXISTS (SELECT 1 FROM task_tags tt WHERE tt.task_id = t.id AND tt.tag = ?)"
                )
                params.append(tag)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT t.* FROM tasks t {where} ORDER BY t.created_at"
        rows = self._conn.execute(sql, params).fetchall()
        return self._rows_to_tasks(rows)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rows_to_tasks(self, rows: list[tuple]) -> list[Task]:
        """Convert a batch of task rows to Task objects with a single round of junction queries."""
        if not rows:
            return []
        ids = [r[0] for r in rows]
        placeholders = ",".join("?" * len(ids))

        scopes_map: dict[str, list[str]] = {i: [] for i in ids}
        for task_id, scope_id in self._conn.execute(
            f"SELECT task_id, scope_id FROM task_scopes WHERE task_id IN ({placeholders})", ids
        ).fetchall():
            scopes_map[task_id].append(scope_id)

        tags_map: dict[str, list[str]] = {i: [] for i in ids}
        for task_id, tag in self._conn.execute(
            f"SELECT task_id, tag FROM task_tags WHERE task_id IN ({placeholders})", ids
        ).fetchall():
            tags_map[task_id].append(tag)

        deps_map: dict[str, list[str]] = {i: [] for i in ids}
        for task_id, dep in self._conn.execute(
            f"SELECT task_id, depends_on FROM task_deps WHERE task_id IN ({placeholders})", ids
        ).fetchall():
            deps_map[task_id].append(dep)

        file_locks_map: dict[str, list[TaskFileLock]] = {i: [] for i in ids}
        for task_id, filepath, lane_id, agent, acquired_at, heartbeat_at in self._conn.execute(
            f"SELECT task_id, filepath, lane_id, agent, acquired_at, heartbeat_at "
            f"FROM file_locks WHERE task_id IN ({placeholders}) ORDER BY filepath", ids
        ).fetchall():
            file_locks_map[task_id].append(TaskFileLock(
                path=filepath, lane_id=lane_id or "", agent=agent or "",
                acquired_at=acquired_at, heartbeat_at=heartbeat_at,
            ))

        scope_locks_map: dict[str, list[TaskScopeLock]] = {i: [] for i in ids}
        for task_id, scope, lane_id, agent, acquired_at, heartbeat_at in self._conn.execute(
            f"SELECT task_id, scope, lane_id, agent, acquired_at, heartbeat_at "
            f"FROM scope_locks WHERE task_id IN ({placeholders}) ORDER BY scope", ids
        ).fetchall():
            scope_locks_map[task_id].append(TaskScopeLock(
                scope=scope, lane_id=lane_id or "", agent=agent or "",
                acquired_at=acquired_at, heartbeat_at=heartbeat_at,
            ))

        return [self._assemble_task(row, scopes_map, tags_map, deps_map, file_locks_map, scope_locks_map) for row in rows]

    def _assemble_task(
        self,
        row: tuple,
        scopes_map: dict[str, list[str]],
        tags_map: dict[str, list[str]],
        deps_map: dict[str, list[str]],
        file_locks_map: dict[str, list[TaskFileLock]],
        scope_locks_map: dict[str, list[TaskScopeLock]],
    ) -> Task:
        (
            id_, title, body, column_, status, priority,
            milestone, phase, assigned, tdd_stage, lane_id,
            run_status, current_agent, time_estimate,
            created_at, updated_at, started_at, finished_at, heartbeat_at,
        ) = row
        return Task(
            id=id_, title=title, body=body or "", column=column_,
            status=status, priority=priority, milestone=milestone,
            phase=phase, assigned=assigned, tdd_stage=tdd_stage,
            lane_id=lane_id, run_status=run_status or "queued",
            current_agent=current_agent, time_estimate=time_estimate or "5min",
            created=created_at, updated=updated_at,
            started_at=started_at, finished_at=finished_at,
            heartbeat_at=heartbeat_at,
            scopes=scopes_map.get(id_, []),
            tags=tags_map.get(id_, []),
            depends_on=deps_map.get(id_, []),
            file_locks=file_locks_map.get(id_, []),
            scope_locks=scope_locks_map.get(id_, []),
        )

    def _insert_junctions(self, task: Task) -> None:
        for scope in task.scopes:
            self._conn.execute(
                "INSERT OR IGNORE INTO task_scopes (task_id, scope_id) VALUES (?, ?)",
                (task.id, scope),
            )
        for tag in task.tags:
            self._conn.execute(
                "INSERT OR IGNORE INTO task_tags (task_id, tag) VALUES (?, ?)",
                (task.id, tag),
            )
        for dep in task.depends_on:
            self._conn.execute(
                "INSERT OR IGNORE INTO task_deps (task_id, depends_on) VALUES (?, ?)",
                (task.id, dep),
            )

    def _delete_junctions(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM task_scopes WHERE task_id = ?", (task_id,))
        self._conn.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
        self._conn.execute("DELETE FROM task_deps WHERE task_id = ?", (task_id,))

    def _sync_fts(self) -> None:
        """Rebuild the FTS5 index from the tasks table."""
        self._conn.execute("INSERT INTO tasks_fts(tasks_fts) VALUES('rebuild')")

    def _row_to_task(self, row: tuple, task_id: str) -> Task:
        result = self._rows_to_tasks([row])
        return result[0]


