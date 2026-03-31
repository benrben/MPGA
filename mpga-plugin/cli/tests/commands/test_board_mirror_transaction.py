"""T006: Tests that _refresh_sqlite_board_mirror wraps DELETE+migration in a transaction.

If migration fails after the DELETE, data must NOT be permanently lost — the
transaction must roll back so the DB is left in a consistent state.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from mpga.commands.board_db import refresh_sqlite_board_mirror as _refresh_sqlite_board_mirror
from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


def _setup_db(db_path: Path) -> None:
    """Seed a minimal DB with one task row so we can detect data loss."""
    conn = get_connection(str(db_path))
    create_schema(conn)
    conn.execute(
        "INSERT INTO tasks (id, title, column_, priority, created_at, updated_at) "
        "VALUES ('T999', 'Sentinel Task', 'todo', 'medium', '2024-01-01', '2024-01-01')"
    )
    conn.commit()
    conn.close()


def test_delete_rolls_back_when_migration_fails(tmp_path: pytest.TempPathFactory) -> None:
    """If migrate_tasks raises after DELETEs, the rows must still exist afterwards."""
    # Arrange: set up directory structure mpga expects
    project_root = tmp_path
    mpga_dir = project_root / ".mpga"
    mpga_dir.mkdir()
    board_dir = project_root / "MPGA" / "board"
    board_dir.mkdir(parents=True)
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir()

    db_path = mpga_dir / "mpga.db"
    _setup_db(db_path)

    # Confirm sentinel row exists before the call
    conn = get_connection(str(db_path))
    rows_before = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    conn.close()
    assert rows_before == 1, "Pre-condition: sentinel row should exist"

    # Act: patch migrate_tasks to fail after the DELETE has already run
    with patch(
        "mpga.commands.board_db.migrate_tasks",
        side_effect=RuntimeError("simulated migration failure"),
    ):
        with pytest.raises(RuntimeError, match="simulated migration failure"):
            _refresh_sqlite_board_mirror(str(board_dir), str(tasks_dir), project_root=project_root)

    # Assert: data must NOT have been permanently wiped (transaction rolled back)
    conn = get_connection(str(db_path))
    rows_after = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    conn.close()
    assert rows_after == 1, (
        "Transaction must roll back on migration failure — rows should be restored, "
        f"but found {rows_after} rows after the failed refresh"
    )


def test_delete_and_migration_committed_on_success(tmp_path: pytest.TempPathFactory) -> None:
    """Happy path: if migration succeeds, the DB is updated and committed."""
    project_root = tmp_path
    mpga_dir = project_root / ".mpga"
    mpga_dir.mkdir()
    board_dir = project_root / "MPGA" / "board"
    board_dir.mkdir(parents=True)
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir()

    db_path = mpga_dir / "mpga.db"
    _setup_db(db_path)

    # patch migrate_tasks to be a no-op and rebuild_global_fts likewise
    with (
        patch("mpga.commands.board_db.migrate_tasks"),
        patch("mpga.commands.board_db.rebuild_global_fts"),
    ):
        _refresh_sqlite_board_mirror(str(board_dir), str(tasks_dir), project_root=project_root)

    # Old sentinel row deleted, new empty state committed — 0 tasks
    conn = get_connection(str(db_path))
    rows_after = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    conn.close()
    assert rows_after == 0, "Successful refresh should clear old rows and commit"
