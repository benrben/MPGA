"""Tests for mpga.commands.migrate: migrate_board and migrate_tasks.

Coverage checklist for: T014 — Fix missing mpga.commands.migrate module

Acceptance criteria → Test status
──────────────────────────────────
[ ] AC1: migrate_board is importable and callable   → it('module exposes migrate_board callable')
[ ] AC2: migrate_tasks is importable and callable   → it('module exposes migrate_tasks callable')
[ ] AC3: migrate_board with empty board dir         → it('migrate_board with no board.json writes nothing')
[ ] AC4: migrate_tasks with empty tasks dir         → it('migrate_tasks with no task files writes nothing')
[ ] AC5: migrate_board with board.json inserts row  → it('migrate_board inserts board key-value rows')
[ ] AC6: migrate_tasks inserts task row             → it('migrate_tasks inserts a task into the tasks table')

Untested branches / edge cases:
- [ ] board.json with milestone field populated
- [ ] task file with scopes, tags, and deps junction rows
- [ ] malformed task frontmatter (should skip gracefully)

Evidence:
  [E] mpga-plugin/cli/src/mpga/commands/board_handlers.py:89-90
        migrate_board(conn, board_dir)
        migrate_tasks(conn, tasks_dir)
  [E] mpga-plugin/cli/src/mpga/db/schema.py:124-127  board table (key, value)
  [E] mpga-plugin/cli/src/mpga/db/schema.py:53-73   tasks table
  [E] mpga-plugin/cli/src/mpga/db/schema.py:75-93   task_scopes, task_tags, task_deps
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path: Path) -> sqlite3.Connection:
    """Return an in-memory-ish SQLite connection with the MPGA schema applied."""
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# TPP step 1: null/degenerate — module must be importable and symbols callable
# ---------------------------------------------------------------------------


class TestMigrateModuleImportable:
    """TPP step 1: the module exists and exports the expected callables.

    Evidence: [E] mpga-plugin/cli/src/mpga/commands/board_handlers.py:38
    """

    def test_module_exposes_migrate_board_callable(self):
        """migrate_board is importable from mpga.commands.migrate and is callable."""
        # Arrange / Act — import only; no filesystem needed
        from mpga.commands.migrate import migrate_board  # noqa: F401

        # Assert
        assert callable(migrate_board)

    def test_module_exposes_migrate_tasks_callable(self):
        """migrate_tasks is importable from mpga.commands.migrate and is callable."""
        from mpga.commands.migrate import migrate_tasks  # noqa: F401

        assert callable(migrate_tasks)


# ---------------------------------------------------------------------------
# TPP step 2: constant → variable — call with empty dirs, nothing explodes
# ---------------------------------------------------------------------------


class TestMigrateBoardEmpty:
    """migrate_board with no board.json writes nothing and does not raise.

    Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:124-127
    """

    def test_migrate_board_with_missing_board_json_writes_nothing(self, tmp_path: Path):
        """migrate_board leaves the board table empty when board.json is absent."""
        # Arrange
        from mpga.commands.migrate import migrate_board

        board_dir = str(tmp_path / "board")
        Path(board_dir).mkdir()
        conn = _make_db(tmp_path)

        # Act
        migrate_board(conn, board_dir)

        # Assert — board table must be empty; no exception raised
        rows = conn.execute("SELECT * FROM board").fetchall()
        conn.close()
        assert rows == []


class TestMigrateTasksEmpty:
    """migrate_tasks with no .md files writes nothing and does not raise.

    Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:53-73
    """

    def test_migrate_tasks_with_empty_tasks_dir_writes_nothing(self, tmp_path: Path):
        """migrate_tasks leaves the tasks table empty when no task files exist."""
        # Arrange
        from mpga.commands.migrate import migrate_tasks

        tasks_dir = str(tmp_path / "tasks")
        Path(tasks_dir).mkdir()
        conn = _make_db(tmp_path)

        # Act
        migrate_tasks(conn, tasks_dir)

        # Assert
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()
        assert rows == []


# ---------------------------------------------------------------------------
# TPP step 3: selection — board.json present, rows inserted
# ---------------------------------------------------------------------------


class TestMigrateBoardInsertsRows:
    """migrate_board reads board.json and inserts key-value rows into the board table.

    Evidence: [E] mpga-plugin/cli/src/mpga/commands/board_handlers.py:89
              [E] mpga-plugin/cli/src/mpga/db/schema.py:124-127
    """

    def test_migrate_board_inserts_milestone_from_board_json(self, tmp_path: Path):
        """migrate_board stores the milestone value from board.json into the board table."""
        # Arrange
        from mpga.commands.migrate import migrate_board

        board_dir = tmp_path / "board"
        board_dir.mkdir()
        board_data = {
            "version": "1.0.0",
            "milestone": "M001",
            "updated": "2026-01-01T00:00:00+00:00",
            "columns": {"backlog": [], "todo": [], "in-progress": [], "done": []},
            "stats": {"total": 0, "done": 0, "in_flight": 0},
            "wip_limits": {},
            "next_task_id": 1,
        }
        (board_dir / "board.json").write_text(json.dumps(board_data), encoding="utf-8")
        conn = _make_db(tmp_path)

        # Act
        migrate_board(conn, str(board_dir))

        # Assert — at least one row must be present in board table
        rows = conn.execute("SELECT * FROM board").fetchall()
        conn.close()
        assert len(rows) > 0, "Expected rows in board table after migrate_board with board.json"


# ---------------------------------------------------------------------------
# TPP step 4: iteration — tasks dir with one .md file inserts a task row
# ---------------------------------------------------------------------------


class TestMigrateTasksInsertsRow:
    """migrate_tasks reads .md task files and inserts rows into the tasks table.

    Evidence: [E] mpga-plugin/cli/src/mpga/commands/board_handlers.py:90
              [E] mpga-plugin/cli/src/mpga/db/schema.py:53-73
    """

    _TASK_MD = """\
---
id: T001
title: Test task
status: active
column: backlog
priority: medium
milestone: null
phase: null
tdd_stage: null
lane_id: null
run_status: queued
current_agent: null
assigned: null
time_estimate: 5min
created: "2026-01-01T00:00:00+00:00"
updated: "2026-01-01T00:00:00+00:00"
started_at: null
finished_at: null
heartbeat_at: null
scopes: []
tags: []
depends_on: []
blocks: []
evidence_expected: []
evidence_produced: []
---

Body text here.
"""

    def test_migrate_tasks_inserts_task_row_from_md_file(self, tmp_path: Path):
        """migrate_tasks inserts a row into tasks for a single valid task markdown file."""
        # Arrange
        from mpga.commands.migrate import migrate_tasks

        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "T001-test-task.md").write_text(self._TASK_MD, encoding="utf-8")
        conn = _make_db(tmp_path)

        # Act
        migrate_tasks(conn, str(tasks_dir))

        # Assert
        rows = conn.execute("SELECT id, title FROM tasks").fetchall()
        conn.close()
        assert len(rows) == 1, f"Expected 1 task row, got {len(rows)}"
        assert rows[0][0] == "T001"
        assert rows[0][1] == "Test task"
