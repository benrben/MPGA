"""Tests for db migration runner."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mpga.db.migrations import run_migrations
from mpga.db.schema import create_schema


@pytest.fixture
def conn():
    """In-memory SQLite connection with schema applied."""
    c = sqlite3.connect(":memory:")
    create_schema(c)
    return c


def test_fresh_db_gets_all_migrations(conn, tmp_path):
    """A fresh DB should have all SQL migration files applied."""
    sql_dir = tmp_path / "migrations"
    sql_dir.mkdir()
    (sql_dir / "v001_initial.sql").write_text("SELECT 1;")
    (sql_dir / "v002_add_index.sql").write_text("SELECT 2;")

    run_migrations(conn, migrations_dir=str(sql_dir))

    rows = conn.execute("SELECT version FROM schema_version ORDER BY version").fetchall()
    versions = [r[0] for r in rows]
    assert 1 in versions
    assert 2 in versions


def test_skips_already_applied_versions(conn, tmp_path):
    """Already-applied versions must not be re-applied."""
    sql_dir = tmp_path / "migrations"
    sql_dir.mkdir()
    # v001 would create a table if it actually ran
    (sql_dir / "v001_initial.sql").write_text(
        "CREATE TABLE skip_test_marker (id INT);"
    )

    # Pre-insert v001 as applied
    conn.execute(
        "INSERT OR IGNORE INTO schema_version (version, applied_at, description) "
        "VALUES (1, datetime('now'), 'pre-applied')"
    )
    conn.commit()

    run_migrations(conn, migrations_dir=str(sql_dir))

    # The table should NOT exist because v001 was skipped
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "skip_test_marker" not in tables


def test_idempotent_running_twice(conn, tmp_path):
    """Running migrations twice must not raise and must not duplicate rows."""
    sql_dir = tmp_path / "migrations"
    sql_dir.mkdir()
    (sql_dir / "v001_initial.sql").write_text("SELECT 1;")

    run_migrations(conn, migrations_dir=str(sql_dir))
    run_migrations(conn, migrations_dir=str(sql_dir))

    count = conn.execute(
        "SELECT COUNT(*) FROM schema_version WHERE version = 1"
    ).fetchone()[0]
    assert count == 1


def test_applies_pending_in_order(conn, tmp_path):
    """Pending migrations are applied in ascending version order."""
    sql_dir = tmp_path / "migrations"
    sql_dir.mkdir()

    applied_order = []

    # Use a real table to track ordering side-effects
    conn.execute(
        "CREATE TABLE IF NOT EXISTS migration_log (seq INTEGER PRIMARY KEY AUTOINCREMENT, ver INT)"
    )
    conn.commit()

    (sql_dir / "v004_second.sql").write_text(
        "INSERT INTO migration_log (ver) VALUES (4);"
    )
    (sql_dir / "v003_first.sql").write_text(
        "INSERT INTO migration_log (ver) VALUES (3);"
    )

    run_migrations(conn, migrations_dir=str(sql_dir))

    rows = conn.execute("SELECT ver FROM migration_log ORDER BY seq").fetchall()
    assert [r[0] for r in rows] == [3, 4]
