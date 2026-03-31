"""Service/facade layer for develop command database operations.

Wraps TaskRepo, LaneRepo, RunRepo, and LockRepo so that develop.py
doesn't manage connections and repos directly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mpga.board.task import Task
from mpga.db.connection import open_db
from mpga.db.repos.lanes import Lane, LaneRepo, Run, RunRepo
from mpga.db.repos.locks import LockRepo
from mpga.db.repos.tasks import TaskRepo
from mpga.db.uow import UnitOfWork


class DevelopService:
    """Facade over the db repos used by the develop command tree."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._task_repo = TaskRepo(conn)
        self._lane_repo = LaneRepo(conn)
        self._run_repo = RunRepo(conn)
        self._lock_repo = LockRepo(conn)

    # -- Convenience constructor -----------------------------------------------

    @classmethod
    def from_project_root(cls, project_root: Path) -> DevelopService | None:
        """Open the project database and return a service, or None if no DB."""
        db_path = project_root / ".mpga" / "mpga.db"
        if not db_path.exists():
            return None
        conn = open_db(project_root)
        return cls(conn)

    # -- Task operations -------------------------------------------------------

    def get_task(self, task_id: str) -> Task | None:
        """Fetch a task by ID, or None if it doesn't exist."""
        return self._task_repo.get(task_id)

    def save_task(self, task: Task) -> None:
        """Create or update a task in the database."""
        existing = self._task_repo.get(task.id)
        if existing is None:
            self._task_repo.create(task)
        else:
            self._task_repo.update(task)

    # -- Full persist (task + locks + lanes + runs) ----------------------------

    def persist_task_state(self, task: Task) -> None:
        """Save task and synchronise locks, lanes, and runs.

        This is the high-level operation previously inlined in develop.py's
        ``_persist_task_state`` helper.
        """
        self.save_task(task)

        # Locks
        self._lock_repo.release_all_for_task(task.id)
        for lock in task.file_locks:
            self._lock_repo.acquire_file(
                lock.path, task.id, lane_id=lock.lane_id, agent=lock.agent,
            )
        for lock in task.scope_locks:
            self._lock_repo.acquire_scope(
                lock.scope, task.id, lane_id=lock.lane_id, agent=lock.agent,
            )

        # Lanes and runs
        if task.lane_id:
            if self._lane_repo.get(task.lane_id) is None:
                self._lane_repo.create(
                    Lane(
                        id=task.lane_id,
                        status=task.run_status,
                        scope=task.scopes[0] if task.scopes else None,
                        current_agent=task.current_agent,
                    )
                )
            else:
                self._lane_repo.update_status(task.lane_id, task.run_status)

            run_id = f"{task.id}:{task.lane_id}"
            existing_run = self._run_repo.get(run_id)
            if existing_run is None:
                self._run_repo.create(
                    Run(
                        id=run_id,
                        lane_id=task.lane_id,
                        task_id=task.id,
                        status=task.run_status,
                        agent=task.current_agent,
                        started_at=task.started_at,
                        finished_at=task.finished_at,
                    )
                )
            else:
                self._run_repo.update_status(run_id, task.run_status)

        self._conn.commit()

    # -- Cleanup ---------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
