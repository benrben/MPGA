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


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


@pytest.fixture()
def schema_conn(tmp_db: Path):
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(str(tmp_db))
    create_schema(conn)
    yield conn
    conn.close()


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
            "observations",
            "observation_queue",
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
            "observations_fts",
            "ctx_artifacts_fts",
            "tasks_trigram",
            "scopes_trigram",
            "evidence_trigram",
            "symbols_trigram",
            "decisions_trigram",
            "events_trigram",
            "global_trigram",
            "ctx_artifacts_trigram",
            "observations_trigram",
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


class TestObservationsTables:
    """Observations + observation_queue tables, FTS5, and triggers.

    Coverage checklist for: T001 — Add observations + observation_queue tables

    Acceptance criteria → Test status
    ──────────────────────────────────
    [x] AC1: observations table exists with all columns  → test_observations_table_exists
    [x] AC2: observation_queue table exists               → test_observation_queue_table_exists
    [x] AC3: observations_fts FTS5 virtual table          → test_observations_fts_exists
    [x] AC4: observations_trigram FTS5 virtual table       → test_observations_trigram_exists
    [x] AC5: INSERT trigger syncs to FTS                   → test_observations_insert_trigger_syncs_fts
    [x] AC6: DELETE trigger syncs FTS                      → test_observations_delete_trigger_syncs_fts
    [x] AC7: observation_queue processed default is 0      → test_observation_queue_insert_and_read
    [x] AC8: all columns have correct types/defaults       → test_observations_columns
    [x] AC9: new tables in core_tables expected set        → test_observations_in_core_tables_set

    Untested branches / edge cases:
    - [ ] UPDATE trigger syncs FTS (not in AC but implied)
    - [ ] observations_trigram uses trigram tokenizer (hard to assert from SQL)
    """

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-263 :: observations + observation_queue

    def test_observations_table_exists(self, schema_conn: sqlite3.Connection) -> None:
        assert "observations" in _table_names(schema_conn)

    def test_observation_queue_table_exists(self, schema_conn: sqlite3.Connection) -> None:
        assert "observation_queue" in _table_names(schema_conn)

    def test_observations_fts_exists(self, schema_conn: sqlite3.Connection) -> None:
        assert "observations_fts" in _table_names(schema_conn)

    def test_observations_trigram_exists(self, schema_conn: sqlite3.Connection) -> None:
        assert "observations_trigram" in _table_names(schema_conn)

    def test_observations_columns(self, schema_conn: sqlite3.Connection) -> None:
        cols = {
            row[1]: {"type": row[2], "notnull": row[3], "dflt": row[4], "pk": row[5]}
            for row in schema_conn.execute("PRAGMA table_info(observations)").fetchall()
        }

        assert "id" in cols
        assert cols["id"]["pk"] == 1

        for col in (
            "session_id",
            "scope_id",
            "title",
            "type",
            "narrative",
            "facts",
            "concepts",
            "files_read",
            "files_modified",
            "tool_name",
            "priority",
            "evidence_links",
            "data_hash",
            "created_at",
        ):
            assert col in cols, f"Missing column: {col}"

        assert cols["title"]["notnull"] == 1
        assert cols["type"]["notnull"] == 1
        assert cols["created_at"]["notnull"] == 1
        assert cols["priority"]["dflt"] == "2"

    def test_observations_insert_trigger_syncs_fts(self, schema_conn: sqlite3.Connection) -> None:
        schema_conn.execute(
            "INSERT INTO observations (title, type, narrative, facts, concepts, created_at) "
            "VALUES ('test obs', 'manual', 'a narrative', 'fact1', 'concept1', '2026-01-01')"
        )
        schema_conn.commit()

        row = schema_conn.execute(
            "SELECT title FROM observations_fts WHERE observations_fts MATCH 'narrative'"
        ).fetchone()
        assert row is not None
        assert row[0] == "test obs"

    def test_observations_delete_trigger_syncs_fts(self, schema_conn: sqlite3.Connection) -> None:
        schema_conn.execute(
            "INSERT INTO observations (title, type, narrative, facts, concepts, created_at) "
            "VALUES ('to delete', 'manual', 'remove me', 'f1', 'c1', '2026-01-01')"
        )
        schema_conn.commit()

        schema_conn.execute("DELETE FROM observations WHERE title = 'to delete'")
        schema_conn.commit()

        row = schema_conn.execute(
            "SELECT title FROM observations_fts WHERE observations_fts MATCH 'remove'"
        ).fetchone()
        assert row is None

    def test_observation_queue_insert_and_read(self, schema_conn: sqlite3.Connection) -> None:
        schema_conn.execute(
            "INSERT INTO observation_queue (session_id, tool_name, tool_input, tool_output, created_at) "
            "VALUES ('s1', 'Read', '/foo.py', 'content...', '2026-01-01')"
        )
        schema_conn.commit()

        row = schema_conn.execute(
            "SELECT processed FROM observation_queue WHERE session_id = 's1'"
        ).fetchone()
        assert row is not None
        assert row[0] == 0

    def test_observations_update_trigger_syncs_fts(self, schema_conn: sqlite3.Connection) -> None:
        schema_conn.execute(
            "INSERT INTO observations (title, type, narrative, facts, concepts, created_at) "
            "VALUES ('old title', 'manual', 'some narrative', 'f1', 'c1', '2026-01-01')"
        )
        schema_conn.commit()

        schema_conn.execute(
            "UPDATE observations SET title = 'new title' WHERE title = 'old title'"
        )
        schema_conn.commit()

        old = schema_conn.execute(
            "SELECT title FROM observations_fts WHERE observations_fts MATCH 'old'"
        ).fetchone()
        assert old is None

        new = schema_conn.execute(
            "SELECT title FROM observations_fts WHERE observations_fts MATCH 'new'"
        ).fetchone()
        assert new is not None
        assert new[0] == "new title"

    def test_observations_trigram_trigger_syncs(self, schema_conn: sqlite3.Connection) -> None:
        schema_conn.execute(
            "INSERT INTO observations (title, type, narrative, facts, concepts, created_at) "
            "VALUES ('trigram test', 'manual', 'unique narrative', 'factoid', 'c1', '2026-01-01')"
        )
        schema_conn.commit()

        row = schema_conn.execute(
            "SELECT title FROM observations_trigram WHERE observations_trigram MATCH 'narr'"
        ).fetchone()
        assert row is not None
        assert row[0] == "trigram test"

    def test_observations_in_core_tables_set(self, schema_conn: sqlite3.Connection) -> None:
        expected = {"observations", "observation_queue"}
        assert expected.issubset(_table_names(schema_conn)), f"Missing: {expected - _table_names(schema_conn)}"


def _fts_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return ordered column names for an FTS5 virtual table."""
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _fts_sql(conn: sqlite3.Connection, table: str) -> str:
    """Return the CREATE VIRTUAL TABLE SQL for an FTS5 table."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row[0] if row else ""


class TestTrigramCompanionTables:
    """Trigram FTS5 companion tables for substring matching.

    Coverage checklist for: T002 — Add trigram FTS5 companion tables to schema

    Acceptance criteria → Test status
    ──────────────────────────────────
    [x] AC1: all 8 trigram tables exist          → test_all_trigram_tables_exist
    [x] AC2: trigram tables are standalone        → test_trigram_tables_are_standalone
    [x] AC3: tasks_trigram columns match          → test_tasks_trigram_columns_match
    [x] AC4: scopes_trigram columns match         → test_scopes_trigram_columns_match
    [x] AC5: global_trigram columns match         → test_global_trigram_columns_match
    [x] AC6: trigram substring search works       → test_trigram_search_works
    [x] AC7: idempotent creation                  → test_idempotent_trigram_creation

    Untested branches / edge cases:
    - [ ] columns match for evidence_trigram, symbols_trigram, decisions_trigram,
          events_trigram, ctx_artifacts_trigram (low risk — same pattern as tested ones)
    - [ ] trigram tokenizer actually configured (verified indirectly via search test)
    """

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:273-324 :: _FTS5_TABLES

    TRIGRAM_TABLES = {
        "tasks_trigram",
        "scopes_trigram",
        "evidence_trigram",
        "symbols_trigram",
        "decisions_trigram",
        "events_trigram",
        "global_trigram",
        "ctx_artifacts_trigram",
    }

    def test_all_trigram_tables_exist(self, schema_conn: sqlite3.Connection) -> None:
        """All 8 trigram companion tables must be created by create_schema."""
        tables = _table_names(schema_conn)
        missing = self.TRIGRAM_TABLES - tables
        assert not missing, f"Missing trigram tables: {missing}"

    def test_trigram_tables_are_standalone(self, schema_conn: sqlite3.Connection) -> None:
        """Trigram tables must NOT use content= sync (they are standalone FTS5)."""
        for table in self.TRIGRAM_TABLES:
            sql = _fts_sql(schema_conn, table)
            assert sql, f"{table} does not exist in sqlite_master"
            assert "content=" not in sql.lower(), (
                f"{table} should be standalone but has content= in: {sql}"
            )

    def test_tasks_trigram_columns_match(self, schema_conn: sqlite3.Connection) -> None:
        """tasks_trigram must have the same columns as tasks_fts."""
        porter_cols = _fts_columns(schema_conn, "tasks_fts")
        trigram_cols = _fts_columns(schema_conn, "tasks_trigram")
        assert trigram_cols == porter_cols, (
            f"tasks_trigram cols {trigram_cols} != tasks_fts cols {porter_cols}"
        )

    def test_scopes_trigram_columns_match(self, schema_conn: sqlite3.Connection) -> None:
        """scopes_trigram must have the same columns as scopes_fts."""
        porter_cols = _fts_columns(schema_conn, "scopes_fts")
        trigram_cols = _fts_columns(schema_conn, "scopes_trigram")
        assert trigram_cols == porter_cols, (
            f"scopes_trigram cols {trigram_cols} != scopes_fts cols {porter_cols}"
        )

    def test_global_trigram_columns_match(self, schema_conn: sqlite3.Connection) -> None:
        """global_trigram must have the same columns as global_fts."""
        porter_cols = _fts_columns(schema_conn, "global_fts")
        trigram_cols = _fts_columns(schema_conn, "global_trigram")
        assert trigram_cols == porter_cols, (
            f"global_trigram cols {trigram_cols} != global_fts cols {porter_cols}"
        )

    def test_trigram_search_works(self, schema_conn: sqlite3.Connection) -> None:
        """Inserting into a trigram table and querying with a substring MATCH works."""
        schema_conn.execute(
            "INSERT INTO tasks_trigram(title, body) VALUES ('refactor authentication', 'rewrite jwt logic')"
        )
        schema_conn.commit()

        row = schema_conn.execute(
            "SELECT title FROM tasks_trigram WHERE tasks_trigram MATCH '\"authe\"'"
        ).fetchone()
        assert row is not None, "Trigram substring match for 'authe' should find the row"
        assert row[0] == "refactor authentication"

    def test_idempotent_trigram_creation(self, tmp_db: Path) -> None:
        """Running create_schema twice must not raise errors for trigram tables."""
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)
        create_schema(conn)

        tables = _table_names(conn)
        missing = self.TRIGRAM_TABLES - tables
        assert not missing, f"Missing trigram tables after double create: {missing}"
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
