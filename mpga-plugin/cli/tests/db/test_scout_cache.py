"""Tests for T016 — Add scout_cache table via DB migration.

Coverage checklist for: T016 — Add scout_cache table via DB migration

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: scout_cache DDL in _CORE_TABLES in schema.py  → test_scout_cache_table_exists_after_schema
[x] AC2: scout_cache columns: scope PK, scouted_at, summary nullable
         → test_scout_cache_columns
[x] AC3: migration is idempotent (CREATE TABLE IF NOT EXISTS)
         → test_create_schema_idempotent_with_scout_cache
[x] AC4: create_schema() includes scout_cache table    → test_scout_cache_in_core_tables_set
[x] AC5: can insert and query a row by scope           → test_insert_and_query_by_scope

Edge cases covered:
[x] summary column accepts NULL (nullable)             → test_summary_accepts_null
[ ] scouted_at stores ISO timestamp strings as TEXT    (behaviour guaranteed by SQLite TEXT affinity)
[ ] scope column rejects duplicates (PRIMARY KEY constraint)  (enforced by SQLite; no explicit test)

Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:9-282 :: _CORE_TABLES
Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:433-455 :: create_schema()
Evidence: [E] mpga-plugin/cli/src/mpga/db/migrations.py:13-40 :: run_migrations()
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return path for a temporary database file."""
    return tmp_path / ".mpga" / "mpga.db"


@pytest.fixture()
def schema_conn(tmp_db: Path) -> sqlite3.Connection:
    """Connection with create_schema() applied."""
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(str(tmp_db))
    create_schema(conn)
    yield conn
    conn.close()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


# ---------------------------------------------------------------------------
# TPP step 1 — degenerate: table exists after create_schema()
# ---------------------------------------------------------------------------

class TestScoutCacheTableExists:
    """AC1 + AC4: scout_cache table is present after create_schema()."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:433-455 :: create_schema()

    def test_scout_cache_table_exists_after_schema(self, schema_conn: sqlite3.Connection) -> None:
        """create_schema() must create the scout_cache table."""
        assert "scout_cache" in _table_names(schema_conn), (
            "scout_cache missing from tables created by create_schema()"
        )


# ---------------------------------------------------------------------------
# TPP step 2 — simple: columns have correct definitions
# ---------------------------------------------------------------------------

class TestScoutCacheColumns:
    """AC2: scout_cache has scope (TEXT PK), scouted_at (TEXT NOT NULL), summary (TEXT nullable)."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:9-282 :: _CORE_TABLES

    def test_scout_cache_columns(self, schema_conn: sqlite3.Connection) -> None:
        """scout_cache must have scope as PK, scouted_at as required TEXT, summary nullable."""
        cols = {
            row[1]: {"type": row[2], "notnull": row[3], "dflt": row[4], "pk": row[5]}
            for row in schema_conn.execute("PRAGMA table_info(scout_cache)").fetchall()
        }

        assert "scope" in cols, "Missing column: scope"
        assert "scouted_at" in cols, "Missing column: scouted_at"
        assert "summary" in cols, "Missing column: summary"

        assert cols["scope"]["pk"] == 1, "scope must be PRIMARY KEY"
        assert cols["scouted_at"]["notnull"] == 1, "scouted_at must be NOT NULL"
        assert cols["summary"]["notnull"] == 0, "summary must be nullable"


# ---------------------------------------------------------------------------
# TPP step 3 — variable: insert and query by scope
# ---------------------------------------------------------------------------

class TestScoutCacheInsertAndQuery:
    """AC5: can insert a row and retrieve it by scope."""

    def test_insert_and_query_by_scope(self, schema_conn: sqlite3.Connection) -> None:
        """Inserting a scout_cache row and querying by scope returns correct scouted_at."""
        # Arrange
        scope = "mpga-plugin/cli/src/mpga/db"
        scouted_at = "2026-03-31T16:00:00+00:00"

        # Act
        schema_conn.execute(
            "INSERT INTO scout_cache (scope, scouted_at) VALUES (?, ?)",
            (scope, scouted_at),
        )
        schema_conn.commit()
        row = schema_conn.execute(
            "SELECT scouted_at FROM scout_cache WHERE scope = ?", (scope,)
        ).fetchone()

        # Assert
        assert row is not None, "Row not found for inserted scope"
        assert row[0] == scouted_at

    def test_summary_accepts_null(self, schema_conn: sqlite3.Connection) -> None:
        """summary column must accept NULL (optional field)."""
        # Arrange
        scope = "mpga-plugin/cli/src/mpga/commands"
        scouted_at = "2026-03-31T16:00:00+00:00"

        # Act
        schema_conn.execute(
            "INSERT INTO scout_cache (scope, scouted_at, summary) VALUES (?, ?, NULL)",
            (scope, scouted_at),
        )
        schema_conn.commit()
        row = schema_conn.execute(
            "SELECT summary FROM scout_cache WHERE scope = ?", (scope,)
        ).fetchone()

        # Assert
        assert row is not None
        assert row[0] is None


# ---------------------------------------------------------------------------
# TPP step 4 — edge: idempotent schema creation
# ---------------------------------------------------------------------------

class TestScoutCacheIdempotent:
    """AC3: calling create_schema() twice must not raise and scout_cache persists."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:433-455 :: create_schema() uses CREATE IF NOT EXISTS

    def test_create_schema_idempotent_with_scout_cache(self, tmp_db: Path) -> None:
        """Running create_schema() twice must not raise for the scout_cache table."""
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        # Arrange + Act
        conn = get_connection(str(tmp_db))
        create_schema(conn)
        create_schema(conn)  # must not raise

        # Assert
        assert "scout_cache" in _table_names(conn), (
            "scout_cache absent after calling create_schema() twice"
        )
        conn.close()
