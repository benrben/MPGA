"""Tests for mpga.db — schema creation, connection, WAL mode."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return path for a temporary database file."""
    return tmp_path / ".mpga" / "mpga.db"


class TestGetConnection:
    """Connection factory returns WAL-mode connection with FK enabled."""

    def test_creates_parent_dirs(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection

        conn = get_connection(str(tmp_db))
        conn.close()
        assert tmp_db.exists()

    def test_wal_mode_enabled(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection

        conn = get_connection(str(tmp_db))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_foreign_keys_enabled(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection

        conn = get_connection(str(tmp_db))
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        assert fk == 1

    def test_returns_sqlite3_connection(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection

        conn = get_connection(str(tmp_db))
        assert isinstance(conn, sqlite3.Connection)
        conn.close()


class TestCreateSchema:
    """Schema creates all tables, FTS5 virtual tables, and version tracking."""

    def test_creates_core_tables(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        expected = {
            "file_info",
            "symbols",
            "graph_edges",
            "scopes",
            "tasks",
            "task_scopes",
            "task_tags",
            "task_deps",
            "evidence",
            "milestones",
            "design_tokens",
            "decisions",
            "lanes",
            "runs",
            "file_locks",
            "scope_locks",
            "schema_version",
        }
        assert expected.issubset(tables), f"Missing: {expected - tables}"
        conn.close()

    def test_creates_fts5_virtual_tables(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        fts_expected = {
            "tasks_fts",
            "scopes_fts",
            "evidence_fts",
            "symbols_fts",
            "decisions_fts",
            "events_fts",
            "global_fts",
        }
        assert fts_expected.issubset(tables), f"Missing FTS: {fts_expected - tables}"
        conn.close()

    def test_schema_version_set(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)

        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 1
        conn.close()

    def test_idempotent(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)
        create_schema(conn)  # should not raise

        rows = conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()
        assert rows[0] == 1
        conn.close()


class TestSessionEventsTables:
    """Session and event tables for context window continuity."""

    def test_sessions_table_exists(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)

        conn.execute(
            "INSERT INTO sessions (id, project_root, started_at, status) "
            "VALUES ('s1', '/tmp', '2026-01-01', 'active')"
        )
        row = conn.execute("SELECT id FROM sessions").fetchone()
        assert row[0] == "s1"
        conn.close()

    def test_events_table_exists(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)

        conn.execute(
            "INSERT INTO sessions (id, project_root, started_at, status) "
            "VALUES ('s1', '/tmp', '2026-01-01', 'active')"
        )
        conn.execute(
            "INSERT INTO events (session_id, timestamp, event_type, action) "
            "VALUES ('s1', '2026-01-01', 'command', 'search')"
        )
        row = conn.execute("SELECT event_type FROM events").fetchone()
        assert row[0] == "command"
        conn.close()


class TestConcurrentAccess:
    """WAL mode allows concurrent reads."""

    def test_concurrent_reads(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)
        conn.execute(
            "INSERT INTO scopes (id, name, created_at, updated_at) "
            "VALUES ('s1', 'test', '2026-01-01', '2026-01-01')"
        )
        conn.commit()
        conn.close()

        results: list[str] = []
        errors: list[Exception] = []

        def read_scope() -> None:
            try:
                c = get_connection(str(tmp_db))
                row = c.execute("SELECT name FROM scopes WHERE id='s1'").fetchone()
                results.append(row[0])
                c.close()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_scope) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"
        assert len(results) == 5
        assert all(r == "test" for r in results)
