"""Tests for develop refactoring: UnitOfWork, DevelopService, _merge_task_state."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# T038: UnitOfWork context manager
# ---------------------------------------------------------------------------


class TestUnitOfWork:
    """UnitOfWork — commit/rollback context manager for SQLite connections."""

    def test_uow_commits_on_success(self, tmp_path: Path):
        """UnitOfWork commits when the block exits normally."""
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.uow import UnitOfWork

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        with UnitOfWork(conn) as uow:
            uow.conn.execute(
                "INSERT INTO scopes (id, name, created_at, updated_at) "
                "VALUES ('s1', 'test', datetime('now'), datetime('now'))"
            )

        # Verify committed
        row = conn.execute("SELECT id FROM scopes WHERE id = 's1'").fetchone()
        assert row is not None
        conn.close()

    def test_uow_rolls_back_on_exception(self, tmp_path: Path):
        """UnitOfWork rolls back when an exception occurs."""
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.uow import UnitOfWork

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        with pytest.raises(ValueError, match="boom"):
            with UnitOfWork(conn) as uow:
                uow.conn.execute(
                    "INSERT INTO scopes (id, name, created_at, updated_at) "
                    "VALUES ('s2', 'test', datetime('now'), datetime('now'))"
                )
                raise ValueError("boom")

        # Verify rolled back
        row = conn.execute("SELECT id FROM scopes WHERE id = 's2'").fetchone()
        assert row is None
        conn.close()

    def test_uow_exposes_conn_attribute(self, tmp_path: Path):
        """UnitOfWork exposes a .conn attribute for database access."""
        from mpga.db.connection import get_connection
        from mpga.db.uow import UnitOfWork

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)

        with UnitOfWork(conn) as uow:
            assert uow.conn is conn
        conn.close()

    def test_uow_as_context_manager_type(self):
        """UnitOfWork supports the context manager protocol."""
        from mpga.db.uow import UnitOfWork

        assert hasattr(UnitOfWork, "__enter__")
        assert hasattr(UnitOfWork, "__exit__")


# ---------------------------------------------------------------------------
# T037: DevelopService facade
# ---------------------------------------------------------------------------


class TestDevelopService:
    """DevelopService — facade over db repos for develop operations."""

    def test_service_exists_and_is_importable(self):
        """DevelopService can be imported from develop_service module."""
        from mpga.commands.develop_service import DevelopService

        assert DevelopService is not None

    def test_service_get_task_returns_task_from_db(self, tmp_path: Path):
        """DevelopService.get_task retrieves a task from the database."""
        from mpga.board.task import Task
        from mpga.commands.develop_service import DevelopService
        from mpga.db.connection import get_connection
        from mpga.db.repos.tasks import TaskRepo
        from mpga.db.schema import create_schema

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        task = Task(
            id="T100", title="Test task", column="todo",
            status=None, priority="medium",
            created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
        )
        TaskRepo(conn).create(task)

        svc = DevelopService(conn)
        result = svc.get_task("T100")
        assert result is not None
        assert result.id == "T100"
        assert result.title == "Test task"
        conn.close()

    def test_service_get_task_returns_none_for_missing(self, tmp_path: Path):
        """DevelopService.get_task returns None for a missing task."""
        from mpga.commands.develop_service import DevelopService
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        svc = DevelopService(conn)
        assert svc.get_task("TXXX") is None
        conn.close()

    def test_service_save_task_creates_new(self, tmp_path: Path):
        """DevelopService.save_task creates a new task when it doesn't exist."""
        from mpga.board.task import Task
        from mpga.commands.develop_service import DevelopService
        from mpga.db.connection import get_connection
        from mpga.db.repos.tasks import TaskRepo
        from mpga.db.schema import create_schema

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        task = Task(
            id="T200", title="New task", column="todo",
            status=None, priority="high",
            created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
        )

        svc = DevelopService(conn)
        svc.save_task(task)

        saved = TaskRepo(conn).get("T200")
        assert saved is not None
        assert saved.title == "New task"
        conn.close()

    def test_service_save_task_updates_existing(self, tmp_path: Path):
        """DevelopService.save_task updates an existing task."""
        from mpga.board.task import Task
        from mpga.commands.develop_service import DevelopService
        from mpga.db.connection import get_connection
        from mpga.db.repos.tasks import TaskRepo
        from mpga.db.schema import create_schema

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        task = Task(
            id="T300", title="Original", column="todo",
            status=None, priority="medium",
            created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
        )
        TaskRepo(conn).create(task)

        task.title = "Updated"
        svc = DevelopService(conn)
        svc.save_task(task)

        saved = TaskRepo(conn).get("T300")
        assert saved.title == "Updated"
        conn.close()

    def test_service_persist_task_state_handles_locks(self, tmp_path: Path):
        """DevelopService.persist_task_state manages file and scope locks."""
        from mpga.board.task import FileLock, ScopeLock, Task
        from mpga.commands.develop_service import DevelopService
        from mpga.db.connection import get_connection
        from mpga.db.repos.locks import LockRepo
        from mpga.db.schema import create_schema

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        task = Task(
            id="T400", title="Locked task", column="in-progress",
            status=None, priority="high",
            created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
            file_locks=[FileLock(path="src/a.py", lane_id="L1", agent="red-dev", acquired_at="2026-01-01")],
            scope_locks=[ScopeLock(scope="core", lane_id="L1", agent="red-dev", acquired_at="2026-01-01")],
        )

        svc = DevelopService(conn)
        svc.persist_task_state(task)

        lock_repo = LockRepo(conn)
        file_locks = lock_repo.list_files_for_task("T400")
        scope_locks = lock_repo.list_scopes_for_task("T400")
        assert len(file_locks) == 1
        assert file_locks[0].filepath == "src/a.py"
        assert len(scope_locks) == 1
        assert scope_locks[0].scope == "core"
        conn.close()

    def test_service_persist_task_state_manages_lanes(self, tmp_path: Path):
        """DevelopService.persist_task_state creates/updates lanes and runs."""
        from mpga.board.task import Task
        from mpga.commands.develop_service import DevelopService
        from mpga.db.connection import get_connection
        from mpga.db.repos.lanes import LaneRepo, RunRepo
        from mpga.db.schema import create_schema

        db_path = str(tmp_path / "test.db")
        conn = get_connection(db_path)
        create_schema(conn)

        task = Task(
            id="T500", title="Lane task", column="in-progress",
            status=None, priority="high",
            created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
            lane_id="T500-lane-1", run_status="running",
            current_agent="red-dev", scopes=["core"],
            started_at="2026-01-01T00:00:00Z",
        )

        svc = DevelopService(conn)
        svc.persist_task_state(task)

        lane = LaneRepo(conn).get("T500-lane-1")
        assert lane is not None
        assert lane.status == "running"

        run = RunRepo(conn).get("T500:T500-lane-1")
        assert run is not None
        assert run.status == "running"
        conn.close()


# ---------------------------------------------------------------------------
# T040: _merge_task_state refactored
# ---------------------------------------------------------------------------


class TestMergeTaskState:
    """_merge_task_state — field-level merge from db_task to primary_task."""

    def _make_task(self, **overrides):
        from mpga.board.task import Task

        defaults = dict(
            id="T001", title="Test", column="backlog",
            status=None, priority="medium",
            created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
        )
        defaults.update(overrides)
        return Task(**defaults)

    def test_merge_copies_all_mutable_fields(self):
        """_merge_task_state copies all state fields from db_task."""
        from mpga.commands.develop import MERGE_FIELDS, _merge_task_state

        primary = self._make_task(column="backlog", priority="low")
        db = self._make_task(
            column="in-progress", priority="high", status=None,
            assigned="alice", tdd_stage="red", lane_id="L1",
            run_status="running", current_agent="red-dev",
            started_at="2026-03-24T12:00:00Z", finished_at=None,
            heartbeat_at="2026-03-24T12:01:00Z",
            scopes=["core"], tags=["urgent"], depends_on=["T000"],
            file_locks=[], scope_locks=[],
            milestone="M001", phase=2, time_estimate="30min",
        )

        result = _merge_task_state(primary, db)

        # Verify each MERGE_FIELDS field was copied
        for f in MERGE_FIELDS:
            assert getattr(result, f) == getattr(db, f), f"Field {f} not merged"

    def test_merge_preserves_identity_fields(self):
        """_merge_task_state does not overwrite id, title, body, created, updated."""
        from mpga.commands.develop import _merge_task_state

        primary = self._make_task(id="T001", title="Primary", body="keep me")
        db = self._make_task(id="T001", title="DB version", body="db body")

        result = _merge_task_state(primary, db)

        assert result.id == "T001"
        assert result.title == "Primary"
        assert result.body == "keep me"

    def test_merge_returns_primary_task(self):
        """_merge_task_state returns the primary_task object (mutated in place)."""
        from mpga.commands.develop import _merge_task_state

        primary = self._make_task()
        db = self._make_task(column="done")

        result = _merge_task_state(primary, db)
        assert result is primary

    def test_merge_fields_constant_covers_all_merged_attrs(self):
        """MERGE_FIELDS constant includes every field that was previously copied."""
        from mpga.commands.develop import MERGE_FIELDS

        expected = {
            "column", "status", "priority", "assigned", "tdd_stage",
            "lane_id", "run_status", "current_agent",
            "started_at", "finished_at", "heartbeat_at",
            "scopes", "tags", "depends_on",
            "file_locks", "scope_locks",
            "milestone", "phase", "time_estimate",
        }
        assert set(MERGE_FIELDS) == expected


# ---------------------------------------------------------------------------
# T042: Reduced fan-out — develop.py import count
# ---------------------------------------------------------------------------


class TestDevelopFanOut:
    """develop.py should have reduced direct imports after refactoring."""

    def test_develop_does_not_import_repos_directly(self):
        """develop.py should no longer import individual repo classes directly."""
        import inspect
        import mpga.commands.develop as dev_mod

        source = inspect.getsource(dev_mod)

        # Should NOT import individual repos
        assert "from mpga.db.repos.lanes import" not in source
        assert "from mpga.db.repos.locks import" not in source
        assert "from mpga.db.repos.tasks import" not in source

    def test_develop_does_not_import_schema(self):
        """develop.py should no longer import create_schema directly."""
        import inspect
        import mpga.commands.develop as dev_mod

        source = inspect.getsource(dev_mod)
        assert "from mpga.db.schema import" not in source

    def test_develop_imports_service_layer(self):
        """develop.py should import from the service layer."""
        import inspect
        import mpga.commands.develop as dev_mod

        source = inspect.getsource(dev_mod)
        assert "develop_service" in source
