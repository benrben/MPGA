"""Tests for load_board_from_db() — reads BoardState from SQLite.

Coverage checklist for: T020 — Add load_board_from_db() and migrate all load_board() call sites

Acceptance criteria → Test status
──────────────────────────────────
[ ] AC1: load_board_from_db is importable from mpga.board.board
         → it('is importable and callable with a connection')
[ ] AC2: load_board_from_db returns a BoardState instance
         → it('returns a BoardState when the DB is empty')
[ ] AC3: returns empty/default Board when DB has no board rows
         → it('returns default columns when DB has no board table or rows')
[ ] AC4: populates board.milestone from the milestone key in the DB
         → it('reads milestone from the board key-value table')
[ ] AC5: populates board columns from task rows in the DB
         → it('puts a single task id in the correct column')
[ ] AC5 (iteration): multiple tasks in multiple columns
         → it('distributes multiple tasks across their respective columns')

Untested branches / edge cases:
- [ ] board table exists but milestone key is absent (None expected)
- [ ] tasks table has tasks in ALL six standard columns
- [ ] tasks table has tasks in an unrecognised column (should not crash)
- [ ] board show command uses load_board_from_db when conn is available (AC6)
      — requires integration test with click runner; marked for later

Evidence:
  [E] src/mpga/board/board.py:106-112 :: load_board() — return type is BoardState
  [E] src/mpga/board/board.py:70-89   :: BoardState dataclass definition
  [E] src/mpga/board/board.py:114-146 :: load_board_from_db() — function under test
  [E] src/mpga/board/board.py:95-104  :: _empty_columns() — extracted helper
  [E] src/mpga/commands/migrate.py:27-47 :: migrate_board creates 'board' (key,value) table
  [E] src/mpga/db/schema.py:53-73     :: tasks table with column_ column
  [E] src/mpga/db/connection.py:9-20  :: get_connection() pattern
"""

from __future__ import annotations

import sqlite3

import pytest

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the MPGA schema applied.

    Uses :memory: to avoid any disk I/O during tests.
    """
    from mpga.db.schema import create_schema

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    create_schema(conn)
    return conn


def _ensure_board_table(conn: sqlite3.Connection) -> None:
    """Create the board key-value table (mirrors migrate_board behaviour).

    Evidence: [E] src/mpga/commands/migrate.py:29-30
    """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS board (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.commit()


def _insert_board_kv(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Insert a single key-value row into the board table."""
    conn.execute("INSERT INTO board (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


def _insert_task_row(
    conn: sqlite3.Connection,
    task_id: str,
    column: str,
    title: str = "Test task",
) -> None:
    """Insert a minimal tasks row for column-population tests.

    Evidence: [E] src/mpga/db/schema.py:53-73
    """
    conn.execute(
        """
        INSERT INTO tasks (
            id, title, column_, priority, run_status, created_at, updated_at
        ) VALUES (?, ?, ?, 'medium', 'queued', datetime('now'), datetime('now'))
        """,
        (task_id, title, column),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# TPP step 1 — null/degenerate: the symbol must be importable
# ---------------------------------------------------------------------------


class TestImportability:
    """AC1: load_board_from_db is importable from mpga.board.board.

    Evidence: [E] src/mpga/board/board.py:114-146 :: load_board_from_db() definition
    """

    def test_is_importable_from_board_module(self):
        # Arrange / Act
        from mpga.board.board import load_board_from_db  # noqa: F401

        # Assert — no ImportError means it is exported at module level
        assert callable(load_board_from_db)


# ---------------------------------------------------------------------------
# TPP step 2 — constant: callable returns BoardState with an empty DB
# ---------------------------------------------------------------------------


class TestEmptyDatabase:
    """AC2 + AC3: returns a BoardState (not a dict, not None) when the DB
    has no board rows and no tasks.

    Evidence: [E] src/mpga/board/board.py:70-89 :: BoardState dataclass
    """

    def test_returns_boardstate_instance_for_empty_db(self):
        # Arrange
        from mpga.board.board import BoardState, load_board_from_db

        conn = _make_db()

        # Act
        board = load_board_from_db(conn)

        # Assert — must be the same type that load_board() returns
        assert isinstance(board, BoardState)

    def test_returns_default_milestone_none_when_db_has_no_board_table(self):
        # Arrange — DB has no 'board' table at all
        from mpga.board.board import load_board_from_db

        conn = _make_db()  # schema does NOT include the board KV table

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert board.milestone is None

    def test_returns_all_standard_columns_empty_when_db_has_no_tasks(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()

        # Act
        board = load_board_from_db(conn)

        # Assert — all six standard columns present and empty
        assert board.columns["backlog"] == []
        assert board.columns["todo"] == []
        assert board.columns["in-progress"] == []
        assert board.columns["testing"] == []
        assert board.columns["review"] == []
        assert board.columns["done"] == []

    def test_returns_default_milestone_none_when_board_table_exists_but_is_empty(self):
        # Arrange — board table exists but has zero rows
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _ensure_board_table(conn)

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert board.milestone is None


# ---------------------------------------------------------------------------
# TPP step 3 — variable: milestone populated from the board KV table
# ---------------------------------------------------------------------------


class TestMilestoneFromDB:
    """AC4: load_board_from_db reads the 'milestone' key from the board table.

    Evidence: [E] src/mpga/commands/migrate.py:27-47 :: board KV table
              [E] src/mpga/board/board.py:71 :: BoardState.milestone field
    """

    def test_milestone_is_populated_from_board_kv_table(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _ensure_board_table(conn)
        _insert_board_kv(conn, "milestone", "M001-big-refactor")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert board.milestone == "M001-big-refactor"

    def test_milestone_is_none_when_milestone_key_absent_from_board_table(self):
        # Arrange — board table exists but has other keys, not 'milestone'
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _ensure_board_table(conn)
        _insert_board_kv(conn, "version", '"1.0.0"')

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert board.milestone is None


# ---------------------------------------------------------------------------
# TPP step 4 — selection: a single task lands in the correct column
# ---------------------------------------------------------------------------


class TestSingleTaskColumnPopulation:
    """AC5 (single element): one task row is reflected in the right column list.

    Evidence: [E] src/mpga/db/schema.py:53-73 :: tasks.column_ column
    """

    def test_single_backlog_task_appears_in_backlog_column(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T001", "backlog")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert "T001" in board.columns["backlog"]

    def test_single_todo_task_appears_in_todo_column(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T002", "todo")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert "T002" in board.columns["todo"]

    def test_single_in_progress_task_appears_in_in_progress_column(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T003", "in-progress")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert "T003" in board.columns["in-progress"]

    def test_single_done_task_appears_in_done_column(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T004", "done")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert "T004" in board.columns["done"]

    def test_task_does_not_bleed_into_other_columns(self):
        # Arrange — one task in backlog; all other columns must stay empty
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T001", "backlog")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert board.columns["todo"] == []
        assert board.columns["in-progress"] == []
        assert board.columns["done"] == []


# ---------------------------------------------------------------------------
# TPP step 5 — iteration: multiple tasks across multiple columns
# ---------------------------------------------------------------------------


class TestMultipleTasksAcrossColumns:
    """AC5 (iteration): all tasks in all columns are returned correctly.

    Evidence: [E] src/mpga/board/board.py:74-81 :: BoardState.columns dict structure
              [E] src/mpga/db/schema.py:57 :: tasks.column_ column
    """

    def test_multiple_tasks_distributed_across_columns(self):
        # Arrange
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T001", "backlog", "Backlog task one")
        _insert_task_row(conn, "T002", "backlog", "Backlog task two")
        _insert_task_row(conn, "T003", "todo", "Todo task")
        _insert_task_row(conn, "T004", "in-progress", "In progress task")
        _insert_task_row(conn, "T005", "done", "Done task")

        # Act
        board = load_board_from_db(conn)

        # Assert — each task lands in the right column
        assert "T001" in board.columns["backlog"]
        assert "T002" in board.columns["backlog"]
        assert "T003" in board.columns["todo"]
        assert "T004" in board.columns["in-progress"]
        assert "T005" in board.columns["done"]

    def test_tasks_in_one_column_do_not_appear_in_others(self):
        # Arrange — two tasks, different columns
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _insert_task_row(conn, "T010", "todo")
        _insert_task_row(conn, "T011", "done")

        # Act
        board = load_board_from_db(conn)

        # Assert — no cross-contamination
        assert "T010" not in board.columns["done"]
        assert "T011" not in board.columns["todo"]
        assert "T010" not in board.columns["backlog"]

    def test_combined_milestone_and_column_population(self):
        # Arrange — milestone from board table, tasks from tasks table
        from mpga.board.board import load_board_from_db

        conn = _make_db()
        _ensure_board_table(conn)
        _insert_board_kv(conn, "milestone", "M002-db-style")
        _insert_task_row(conn, "T020", "in-progress")

        # Act
        board = load_board_from_db(conn)

        # Assert
        assert board.milestone == "M002-db-style"
        assert "T020" in board.columns["in-progress"]
