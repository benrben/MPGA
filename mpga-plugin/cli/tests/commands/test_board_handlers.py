"""Tests for board CLI enum validation and handleBoardClaim."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mpga.board.board import BoardState
from mpga.board.task import Task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_board(in_progress_count: int = 0) -> BoardState:
    """Create a BoardState with a configurable number of in-progress tasks."""
    from mpga.board.board import create_empty_board
    board = create_empty_board()
    board.columns["todo"] = ["T001"]
    board.columns["in-progress"] = [f"TWIP{i}" for i in range(in_progress_count)]
    board.next_task_id = 10
    return board


def make_task(column: str = "todo") -> Task:
    """Create a minimal Task dataclass."""
    return Task(
        id="T001",
        title="Test task",
        column=column,
        status=None,
        priority="medium",
        created="2026-01-01T00:00:00.000Z",
        updated="2026-01-01T00:00:00.000Z",
        depends_on=[],
        blocks=[],
        scopes=[],
        tdd_stage=None,
        lane_id=None,
        run_status="queued",
        current_agent=None,
        file_locks=[],
        scope_locks=[],
        started_at=None,
        finished_at=None,
        heartbeat_at=None,
        evidence_expected=[],
        evidence_produced=[],
        tags=[],
        time_estimate="5min",
        body="",
    )


def _mock_board_handler_deps(monkeypatch):
    """Mock board_handlers module-level imports to avoid Rich stderr issues."""
    monkeypatch.setattr("mpga.commands.board_handlers.log", MagicMock())


# ---------------------------------------------------------------------------
# Tests: CLI enum validation (via Click Choice)
# ---------------------------------------------------------------------------

class TestCliEnumValidation:
    """CLI enum validation tests using Click's built-in Choice type."""

    def test_rejects_invalid_priority_in_add(self):
        """Rejects invalid priority in board add."""
        from click.testing import CliRunner

        from mpga.commands.board_cmd import board_add

        runner = CliRunner()
        result = runner.invoke(board_add, ["Test", "--priority", "bogus"])
        assert result.exit_code != 0

    def test_rejects_invalid_column_in_add(self):
        """Rejects invalid column in board add."""
        from click.testing import CliRunner

        from mpga.commands.board_cmd import board_add

        runner = CliRunner()
        result = runner.invoke(board_add, ["Test", "--column", "bogus"])
        assert result.exit_code != 0

    def test_rejects_invalid_tdd_stage(self):
        """Rejects invalid tdd-stage in board update."""
        from click.testing import CliRunner

        from mpga.commands.board_cmd import board_update

        runner = CliRunner()
        result = runner.invoke(board_update, ["T001", "--tdd-stage", "bogus"])
        assert result.exit_code != 0

    def test_rejects_invalid_status(self):
        """Rejects invalid status in board update."""
        from click.testing import CliRunner

        from mpga.commands.board_cmd import board_update

        runner = CliRunner()
        result = runner.invoke(board_update, ["T001", "--status", "bogus"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests: handleBoardClaim
# ---------------------------------------------------------------------------

class TestHandleBoardClaim:
    """handleBoardClaim tests."""

    def test_rejects_claim_when_wip_limit_reached(self, monkeypatch):
        """Rejects claim when in-progress WIP limit is reached."""
        board = make_board(3)  # 3 tasks already in-progress, limit is 3

        _mock_board_handler_deps(monkeypatch)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: Path("/tmp/test-project"))
        monkeypatch.setattr("mpga.commands.board_handlers.load_board", lambda _: board)
        monkeypatch.setattr("mpga.commands.board_handlers.check_wip_limit", lambda b, col: False)
        monkeypatch.setattr(
            "mpga.commands.board_handlers.find_task_file",
            lambda _t, _d: "/tmp/test-project/MPGA/board/tasks/T001-test.md",
        )
        monkeypatch.setattr("mpga.commands.board_handlers.parse_task_file", lambda _: make_task("todo"))

        from mpga.commands.board_handlers import handle_board_claim

        with pytest.raises(SystemExit):
            handle_board_claim("T001")

        assert "T001" not in board.columns["in-progress"]

    def test_allows_claim_when_under_wip_limit(self, monkeypatch, tmp_path):
        """Allows claim when WIP limit is not reached."""
        board = make_board(1)  # only 1 in-progress, limit is 3

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_file = tasks_dir / "T001-test.md"
        task_file.write_text("---\nid: T001\n---\n")

        _mock_board_handler_deps(monkeypatch)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.load_board", lambda _: board)
        monkeypatch.setattr("mpga.commands.board_handlers.check_wip_limit", lambda b, col: True)
        monkeypatch.setattr(
            "mpga.commands.board_handlers.find_task_file",
            lambda _t, _d: str(task_file),
        )
        monkeypatch.setattr("mpga.commands.board_handlers.parse_task_file", lambda _: make_task("todo"))
        monkeypatch.setattr("mpga.commands.board_handlers.persist_board", lambda *a, **kw: None)
        monkeypatch.setattr("mpga.commands.board_handlers._sync_task_to_db", lambda *a: None)

        from mpga.commands.board_handlers import handle_board_claim

        handle_board_claim("T001")

        assert "T001" in board.columns["in-progress"]

    def test_allows_claim_with_force(self, monkeypatch, tmp_path):
        """Allows claim with --force even when WIP limit is reached."""
        board = make_board(3)  # 3 in-progress, limit is 3

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_file = tasks_dir / "T001-test.md"
        task_file.write_text("---\nid: T001\n---\n")

        _mock_board_handler_deps(monkeypatch)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.load_board", lambda _: board)
        monkeypatch.setattr("mpga.commands.board_handlers.check_wip_limit", lambda b, col: False)
        monkeypatch.setattr(
            "mpga.commands.board_handlers.find_task_file",
            lambda _t, _d: str(task_file),
        )
        monkeypatch.setattr("mpga.commands.board_handlers.parse_task_file", lambda _: make_task("todo"))
        monkeypatch.setattr("mpga.commands.board_handlers.persist_board", lambda *a, **kw: None)
        monkeypatch.setattr("mpga.commands.board_handlers._sync_task_to_db", lambda *a: None)

        from mpga.commands.board_handlers import handle_board_claim

        handle_board_claim("T001", force=True)

        assert "T001" in board.columns["in-progress"]
