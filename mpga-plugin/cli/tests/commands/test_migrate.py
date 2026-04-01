"""Tests for mpga.commands.migrate: migrate_board, migrate_tasks, and the
Click command registered as 'mpga migrate'.

Coverage checklist for: T014 — Fix missing mpga.commands.migrate module

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: migrate_board is importable and callable   → it('module exposes migrate_board callable')
[x] AC2: migrate_tasks is importable and callable   → it('module exposes migrate_tasks callable')
[x] AC3: migrate_board with empty board dir         → it('migrate_board with no board.json writes nothing')
[x] AC4: migrate_tasks with empty tasks dir         → it('migrate_tasks with no task files writes nothing')
[x] AC5: migrate_board with board.json inserts row  → it('migrate_board inserts board key-value rows')
[x] AC6: migrate_tasks inserts task row             → it('migrate_tasks inserts a task into the tasks table')

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

──────────────────────────────────────────────────────────────────────────────
Coverage checklist for: T015 — Register mpga migrate as Click command in CLI registry

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: 'migrate' is in _COMMANDS dict in cli.py    → it('migrate key exists in CLI _COMMANDS registry')
[x] AC2: migrate_cmd is importable and is a Click command
                                                      → it('migrate_cmd is a Click BaseCommand')
[x] AC3: mpga migrate --help exits 0 and shows usage → it('migrate --help exits 0 and prints usage')
[x] AC4: mpga migrate calls run_migrations()         → it('migrate command invokes run_migrations')

Untested branches / edge cases:
- [ ] migrate with --db pointing to a non-existent path
- [ ] migrate when schema_version table is already populated (idempotent)

Evidence:
  [E] mpga-plugin/cli/src/mpga/cli.py:53-98   — _COMMANDS dict, no 'migrate' entry today
  [E] mpga-plugin/cli/src/mpga/commands/migrate.py  — no @click.command decorators today
  [E] mpga-plugin/cli/src/mpga/db/migrations.py:13  — run_migrations(conn, migrations_dir)
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


# ===========================================================================
# T015: Register mpga migrate as Click command in CLI registry
# ===========================================================================

# ---------------------------------------------------------------------------
# TPP step 1 (null/degenerate): registry lookup — 'migrate' key must exist in
# _COMMANDS before any command object is instantiated.
# Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:53-98
# ---------------------------------------------------------------------------


class TestMigrateRegisteredInCLI:
    """'migrate' must appear in the _COMMANDS registry in cli.py.

    This is the degenerate check — no filesystem, no DB, just a dict lookup.
    Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:53-98
    """

    def test_migrate_key_exists_in_commands_registry(self):
        """'migrate' is present in the _COMMANDS dict in mpga.cli."""
        # Arrange / Act — import the registry directly
        from mpga.cli import _COMMANDS

        # Assert
        assert "migrate" in _COMMANDS, (
            "'migrate' not found in _COMMANDS — add the entry to cli.py"
        )


# ---------------------------------------------------------------------------
# TPP step 2 (constant → variable): the mapped attribute must be a Click command
# Evidence: [E] mpga-plugin/cli/src/mpga/commands/migrate.py
# ---------------------------------------------------------------------------


class TestMigrateCmdIsClickCommand:
    """migrate_cmd must be a Click BaseCommand (decorated with @click.command).

    Evidence: [E] mpga-plugin/cli/src/mpga/commands/migrate.py
    """

    def test_migrate_cmd_is_a_click_base_command(self):
        """migrate_cmd imported from mpga.commands.migrate is a Click BaseCommand."""
        # Arrange
        import click

        # Act
        from mpga.commands.migrate import migrate_cmd  # noqa: F401 — will fail until green-dev adds decorator

        # Assert
        assert isinstance(migrate_cmd, click.Command), (
            "migrate_cmd must be decorated with @click.command"
        )


# ---------------------------------------------------------------------------
# TPP step 3 (selection): --help exits 0 and emits usage text
# Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:101-104 (main group)
#           [E] mpga-plugin/cli/src/mpga/commands/migrate.py
# ---------------------------------------------------------------------------


class TestMigrateHelpExitsZero:
    """'mpga migrate --help' must exit 0 and include 'Usage:' in output.

    Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:101-104
              [E] mpga-plugin/cli/src/mpga/commands/migrate.py
    """

    def test_migrate_help_exits_zero_and_shows_usage(self):
        """migrate --help exits 0 and includes usage text."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.migrate import migrate_cmd

        runner = CliRunner()

        # Act
        result = runner.invoke(migrate_cmd, ["--help"])

        # Assert
        assert result.exit_code == 0, (
            f"Expected exit code 0 from --help, got {result.exit_code}. "
            f"Output: {result.output}"
        )
        assert "Usage:" in result.output, (
            f"Expected 'Usage:' in --help output. Got: {result.output!r}"
        )


# ---------------------------------------------------------------------------
# TPP step 4 (iteration): invoking the command calls run_migrations()
# Evidence: [E] mpga-plugin/cli/src/mpga/db/migrations.py:13
# ---------------------------------------------------------------------------


class TestMigrateCommandInvokesRunMigrations:
    """'mpga migrate' must call run_migrations() from db/migrations.py.

    Evidence: [E] mpga-plugin/cli/src/mpga/db/migrations.py:13
              [E] mpga-plugin/cli/src/mpga/commands/migrate.py
    """

    def test_migrate_command_calls_run_migrations(self, tmp_path: Path, monkeypatch):
        """migrate command invokes run_migrations exactly once when executed."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.migrate import migrate_cmd

        calls: list[tuple] = []

        def fake_run_migrations(conn, migrations_dir=None):  # noqa: ANN001
            calls.append((conn, migrations_dir))

        monkeypatch.setattr("mpga.commands.migrate.run_migrations", fake_run_migrations)

        # Seed a minimal .mpga/mpga.db so the command can find the database
        dot_mpga = tmp_path / ".mpga"
        dot_mpga.mkdir(parents=True, exist_ok=True)

        runner = CliRunner()

        # Act — invoke with a known --db path to avoid touching the real project
        result = runner.invoke(migrate_cmd, ["--db", str(dot_mpga / "mpga.db")])

        # Assert
        assert result.exit_code == 0, (
            f"Expected exit code 0, got {result.exit_code}. Output: {result.output}"
        )
        assert len(calls) == 1, (
            f"Expected run_migrations to be called once, got {len(calls)} calls"
        )
