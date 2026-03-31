"""MilestoneRepo — CRUD for the milestones table."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Milestone:
    id: str
    name: str
    status: str = "active"
    design: str | None = None
    summary: str | None = None
    plan: str | None = None
    context: str | None = None
    created_at: str = ""
    completed_at: str | None = None


class MilestoneRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, milestone: Milestone) -> Milestone:
        self._conn.execute(
            """
            INSERT INTO milestones (id, name, status, design, summary, plan, context, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """,
            (milestone.id, milestone.name, milestone.status, milestone.design,
             milestone.summary, milestone.plan, milestone.context, milestone.completed_at),
        )
        self._conn.commit()
        return self.get(milestone.id)  # type: ignore[return-value]

    def get(self, milestone_id: str) -> Milestone | None:
        row = self._conn.execute(
            "SELECT id, name, status, design, summary, plan, context, created_at, completed_at "
            "FROM milestones WHERE id = ?",
            (milestone_id,),
        ).fetchone()
        if row is None:
            return None
        return Milestone(*row)

    def list_all(self) -> list[Milestone]:
        rows = self._conn.execute(
            "SELECT id, name, status, design, summary, plan, context, created_at, completed_at FROM milestones"
        ).fetchall()
        return [Milestone(*r) for r in rows]

    def update(self, milestone: Milestone) -> Milestone:
        self._conn.execute(
            """
            UPDATE milestones SET name = ?, status = ?, design = ?, summary = ?,
                plan = ?, context = ?, completed_at = ?
            WHERE id = ?
            """,
            (milestone.name, milestone.status, milestone.design, milestone.summary,
             milestone.plan, milestone.context, milestone.completed_at, milestone.id),
        )
        self._conn.commit()
        return self.get(milestone.id)  # type: ignore[return-value]

    def complete(self, milestone_id: str) -> Milestone | None:
        self._conn.execute(
            "UPDATE milestones SET status = 'completed', completed_at = datetime('now') "
            "WHERE id = ?",
            (milestone_id,),
        )
        self._conn.commit()
        return self.get(milestone_id)
