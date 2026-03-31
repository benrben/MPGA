"""LaneRepo and RunRepo — CRUD for develop scheduler lanes and runs."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Lane:
    id: str
    status: str = "queued"
    scope: str | None = None
    current_agent: str | None = None
    updated_at: str = ""


@dataclass
class Run:
    id: str
    lane_id: str
    task_id: str | None = None
    status: str = "queued"
    agent: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class LaneRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, lane: Lane) -> Lane:
        self._conn.execute(
            "INSERT INTO lanes (id, status, scope, current_agent, updated_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (lane.id, lane.status, lane.scope, lane.current_agent),
        )
        self._conn.commit()
        return self.get(lane.id)  # type: ignore[return-value]

    def get(self, lane_id: str) -> Lane | None:
        row = self._conn.execute(
            "SELECT id, status, scope, current_agent, updated_at FROM lanes WHERE id = ?",
            (lane_id,),
        ).fetchone()
        if row is None:
            return None
        return Lane(*row)

    def update_status(self, lane_id: str, status: str) -> Lane | None:
        self._conn.execute(
            "UPDATE lanes SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, lane_id),
        )
        self._conn.commit()
        return self.get(lane_id)

    def list_all(self) -> list[Lane]:
        rows = self._conn.execute(
            "SELECT id, status, scope, current_agent, updated_at FROM lanes"
        ).fetchall()
        return [Lane(*r) for r in rows]


class RunRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, run: Run) -> Run:
        self._conn.execute(
            "INSERT INTO runs (id, lane_id, task_id, status, agent, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run.id, run.lane_id, run.task_id, run.status, run.agent,
             run.started_at, run.finished_at),
        )
        self._conn.commit()
        return self.get(run.id)  # type: ignore[return-value]

    def get(self, run_id: str) -> Run | None:
        row = self._conn.execute(
            "SELECT id, lane_id, task_id, status, agent, started_at, finished_at "
            "FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return Run(*row)

    def update_status(self, run_id: str, status: str) -> Run | None:
        self._conn.execute(
            "UPDATE runs SET status = ? WHERE id = ?",
            (status, run_id),
        )
        self._conn.commit()
        return self.get(run_id)

    def list_by_lane(self, lane_id: str) -> list[Run]:
        rows = self._conn.execute(
            "SELECT id, lane_id, task_id, status, agent, started_at, finished_at "
            "FROM runs WHERE lane_id = ?",
            (lane_id,),
        ).fetchall()
        return [Run(*r) for r in rows]
