"""Tests for T021 — Add tdd_checkpoints table to SQLite schema.

Coverage checklist for: T021 — Tier 3 Add tdd_checkpoints table and remove task .md file writes

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: tdd_checkpoints table exists after create_schema()
         → test_tdd_checkpoints_table_exists_after_schema
[x] AC2: correct columns: task_id (TEXT PK), tdd_stage (TEXT), updated_at (TEXT)
         → test_tdd_checkpoints_columns
[x] AC3: schema is idempotent (CREATE TABLE IF NOT EXISTS)
         → test_create_schema_idempotent_with_tdd_checkpoints
[ ] AC4: persist_board() no longer writes .md files when DB is present
         → (not yet written — scoped out per HIGH RISK mitigation)
[ ] AC5: task state is still written to DB tasks table after .md removal
         → (not yet written — scoped out per HIGH RISK mitigation)

Untested branches / edge cases:
- [ ] tdd_stage accepts NULL (column is nullable — no NOT NULL constraint expected)
- [ ] task_id PRIMARY KEY rejects duplicate inserts (SQLite constraint)
- [ ] updated_at stores ISO timestamp strings as TEXT (TEXT affinity)

Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:9-289 :: _CORE_TABLES
Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:440-461 :: create_schema()
Evidence: [E] mpga-plugin/cli/tests/db/test_scout_cache.py:1-177 :: structural pattern
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

class TestTddCheckpointsTableExists:
    """AC1: tdd_checkpoints table is present after create_schema()."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:440-461 :: create_schema()

    def test_tdd_checkpoints_table_exists_after_schema(
        self, schema_conn: sqlite3.Connection
    ) -> None:
        """create_schema() must create the tdd_checkpoints table."""
        assert "tdd_checkpoints" in _table_names(schema_conn), (
            "tdd_checkpoints missing from tables created by create_schema()"
        )


# ---------------------------------------------------------------------------
# TPP step 2 — simple: columns have correct definitions
# ---------------------------------------------------------------------------

class TestTddCheckpointsColumns:
    """AC2: tdd_checkpoints has task_id (TEXT PK), tdd_stage (TEXT), updated_at (TEXT)."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:9-289 :: _CORE_TABLES

    def test_tdd_checkpoints_columns(self, schema_conn: sqlite3.Connection) -> None:
        """tdd_checkpoints must have task_id as PK, tdd_stage as TEXT, updated_at as TEXT."""
        cols = {
            row[1]: {"type": row[2], "notnull": row[3], "dflt": row[4], "pk": row[5]}
            for row in schema_conn.execute(
                "PRAGMA table_info(tdd_checkpoints)"
            ).fetchall()
        }

        assert "task_id" in cols, "Missing column: task_id"
        assert "tdd_stage" in cols, "Missing column: tdd_stage"
        assert "updated_at" in cols, "Missing column: updated_at"

        assert cols["task_id"]["pk"] == 1, "task_id must be PRIMARY KEY"
        assert cols["tdd_stage"]["type"].upper() == "TEXT", "tdd_stage must be TEXT type"
        assert cols["updated_at"]["type"].upper() == "TEXT", "updated_at must be TEXT type"


# ---------------------------------------------------------------------------
# TPP step 3 — variable: insert and query by task_id
# ---------------------------------------------------------------------------

class TestTddCheckpointsInsertAndQuery:
    """Verify rows can be inserted and retrieved by task_id."""

    def test_insert_and_query_by_task_id(self, schema_conn: sqlite3.Connection) -> None:
        """Inserting a tdd_checkpoints row and querying by task_id returns correct tdd_stage."""
        # Arrange
        task_id = "T021"
        tdd_stage = "red"
        updated_at = "2026-03-31T16:00:00+00:00"

        # Act
        schema_conn.execute(
            "INSERT INTO tdd_checkpoints (task_id, tdd_stage, updated_at) VALUES (?, ?, ?)",
            (task_id, tdd_stage, updated_at),
        )
        schema_conn.commit()
        row = schema_conn.execute(
            "SELECT tdd_stage FROM tdd_checkpoints WHERE task_id = ?", (task_id,)
        ).fetchone()

        # Assert
        assert row is not None, "Row not found for inserted task_id"
        assert row[0] == tdd_stage

    def test_tdd_stage_accepts_null(self, schema_conn: sqlite3.Connection) -> None:
        """tdd_stage column must accept NULL (stage not yet assigned)."""
        # Arrange
        task_id = "T021-null"
        updated_at = "2026-03-31T16:00:00+00:00"

        # Act
        schema_conn.execute(
            "INSERT INTO tdd_checkpoints (task_id, tdd_stage, updated_at) VALUES (?, NULL, ?)",
            (task_id, updated_at),
        )
        schema_conn.commit()
        row = schema_conn.execute(
            "SELECT tdd_stage FROM tdd_checkpoints WHERE task_id = ?", (task_id,)
        ).fetchone()

        # Assert
        assert row is not None
        assert row[0] is None


# ---------------------------------------------------------------------------
# TPP step 4 — edge: idempotent schema creation
# ---------------------------------------------------------------------------

class TestTddCheckpointsIdempotent:
    """AC3: calling create_schema() twice must not raise and tdd_checkpoints persists."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:440-461 :: create_schema() uses CREATE IF NOT EXISTS

    def test_create_schema_idempotent_with_tdd_checkpoints(
        self, tmp_db: Path
    ) -> None:
        """Running create_schema() twice must not raise for the tdd_checkpoints table."""
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        # Arrange + Act
        conn = get_connection(str(tmp_db))
        create_schema(conn)
        create_schema(conn)  # must not raise

        # Assert
        assert "tdd_checkpoints" in _table_names(conn), (
            "tdd_checkpoints absent after calling create_schema() twice"
        )
        conn.close()
