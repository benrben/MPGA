"""T027: Test that handle_board_claim persists the claim to disk (task .md file).

The bug: handle_board_claim mutates task in memory but never writes the updated
task file back to disk. persist_board rebuilds SQLite from disk, so the in-memory
changes (assigned, column) silently revert on next load.

The fix: write the updated task file to disk (via render_task_file) before
calling persist_board.
"""

import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mpga.board.task import Task, render_task_file


def _make_task(task_id: str, tasks_dir: Path) -> tuple[Task, Path]:
    """Create a minimal task file on disk and return (task, file_path)."""
    task = Task(
        id=task_id,
        title="Sample task",
        column="backlog",
        priority="medium",
        assigned=None,
        status=None,
        created=datetime.now(UTC).isoformat(),
        updated=datetime.now(UTC).isoformat(),
    )
    filename = f"{task_id}-sample-task.md"
    task_file = tasks_dir / filename
    task_file.write_text(render_task_file(task), encoding="utf-8")
    return task, task_file


def _make_board(task_id: str):
    board = MagicMock()
    board.milestone = "M001"
    board.columns = {"backlog": [task_id], "in-progress": [], "done": []}
    board.wip_limits = {"in-progress": 3}
    board.stats = MagicMock()
    return board


class TestBoardClaimPersist:

    def test_claim_persists_assigned_field_to_disk(self, tmp_path):
        """After handle_board_claim, the task file on disk must reflect the new assigned value."""
        from mpga.commands import board_handlers
        from mpga.board.task import parse_task_file

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        tasks_dir.mkdir(parents=True)
        board_dir = str(tmp_path / "MPGA" / "board")
        Path(board_dir).mkdir(parents=True, exist_ok=True)

        task_id = "T001"
        task, task_file = _make_task(task_id, tasks_dir)
        board = _make_board(task_id)

        with (
            patch.object(board_handlers, "_board_context", return_value=(tmp_path, board_dir, str(tasks_dir))),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "with_board_lock", lambda bd, fn: fn()),
            patch.object(board_handlers, "persist_board"),  # skip full board save
            patch.object(board_handlers, "_sync_task_to_db"),
        ):
            board_handlers.handle_board_claim(task_id, agent="test-agent")

        # Re-parse the file from disk — the assignment must be persisted
        reloaded = parse_task_file(str(task_file))
        assert reloaded is not None, "Task file should still exist and be parseable"
        assert reloaded.assigned == "test-agent", (
            f"Expected assigned='test-agent' on disk, got {reloaded.assigned!r}"
        )

    def test_claim_persists_column_to_disk(self, tmp_path):
        """After handle_board_claim, the task file on disk must reflect column='in-progress'."""
        from mpga.commands import board_handlers
        from mpga.board.task import parse_task_file

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        tasks_dir.mkdir(parents=True)
        board_dir = str(tmp_path / "MPGA" / "board")
        Path(board_dir).mkdir(parents=True, exist_ok=True)

        task_id = "T002"
        task, task_file = _make_task(task_id, tasks_dir)
        board = _make_board(task_id)

        with (
            patch.object(board_handlers, "_board_context", return_value=(tmp_path, board_dir, str(tasks_dir))),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "with_board_lock", lambda bd, fn: fn()),
            patch.object(board_handlers, "persist_board"),
            patch.object(board_handlers, "_sync_task_to_db"),
        ):
            board_handlers.handle_board_claim(task_id, agent="agent-x")

        reloaded = parse_task_file(str(task_file))
        assert reloaded is not None
        assert reloaded.column == "in-progress", (
            f"Expected column='in-progress' on disk, got {reloaded.column!r}"
        )

    def test_claim_without_agent_defaults_to_agent_string(self, tmp_path):
        """handle_board_claim with agent=None should persist assigned='agent' on disk."""
        from mpga.commands import board_handlers
        from mpga.board.task import parse_task_file

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        tasks_dir.mkdir(parents=True)
        board_dir = str(tmp_path / "MPGA" / "board")
        Path(board_dir).mkdir(parents=True, exist_ok=True)

        task_id = "T003"
        task, task_file = _make_task(task_id, tasks_dir)
        board = _make_board(task_id)

        with (
            patch.object(board_handlers, "_board_context", return_value=(tmp_path, board_dir, str(tasks_dir))),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "with_board_lock", lambda bd, fn: fn()),
            patch.object(board_handlers, "persist_board"),
            patch.object(board_handlers, "_sync_task_to_db"),
        ):
            board_handlers.handle_board_claim(task_id, agent=None)

        reloaded = parse_task_file(str(task_file))
        assert reloaded is not None
        assert reloaded.assigned == "agent", (
            f"Expected assigned='agent' on disk, got {reloaded.assigned!r}"
        )
