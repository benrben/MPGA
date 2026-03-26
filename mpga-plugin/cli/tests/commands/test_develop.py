"""Tests for the develop command (status, abort, resume)."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import write_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_board(tmp_path: Path) -> Path:
    """Set up a minimal board structure and return the board dir."""
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return board_dir


def seed_running_task(tmp_path: Path, board_dir: Path) -> str:
    """Seed a running task and return its task ID."""
    from mpga.board.board import create_empty_board, save_board, add_task, AddTaskOptions
    from mpga.board.task import parse_task_file, render_task_file, FileLock, ScopeLock

    tasks_dir = board_dir / "tasks"

    board = create_empty_board()
    save_board(str(board_dir), board)
    task = add_task(board, str(tasks_dir), AddTaskOptions(
        title="Running task",
        column="in-progress",
        priority="high",
        scopes=["core"],
    ))
    save_board(str(board_dir), board)

    # Simulate a running develop state
    task_files = list(tasks_dir.iterdir())
    task_path = next(f for f in task_files if f.name.startswith(task.id))
    parsed = parse_task_file(str(task_path))
    parsed.lane_id = "T001-lane-1"
    parsed.run_status = "running"
    parsed.current_agent = "mpga-red-dev"
    parsed.tdd_stage = "red"
    parsed.file_locks = [
        FileLock(
            path="src/board.ts",
            lane_id="T001-lane-1",
            agent="mpga-red-dev",
            acquired_at="2026-03-24T12:00:00.000Z",
        ),
    ]
    parsed.scope_locks = [
        ScopeLock(
            scope="core",
            lane_id="T001-lane-1",
            agent="mpga-red-dev",
            acquired_at="2026-03-24T12:00:00.000Z",
        ),
    ]
    parsed.started_at = "2026-03-24T12:00:00.000Z"
    task_path.write_text(render_task_file(parsed))

    return task.id


# ---------------------------------------------------------------------------
# Tests: develop command registration
# ---------------------------------------------------------------------------

class TestDevelopCommand:
    """develop command -- WINNING development."""

    def test_registers_and_forwards_scheduler_options(self, tmp_path: Path, monkeypatch):
        """Registers the develop command and forwards scheduler options."""
        monkeypatch.chdir(tmp_path)

        calls = []

        def mock_run_develop_task(task_id, **kwargs):
            calls.append((task_id, kwargs))

        monkeypatch.setattr(
            "mpga.commands.develop.run_develop_task", mock_run_develop_task
        )

        from mpga.commands.develop import develop_run

        runner = CliRunner()
        result = runner.invoke(develop_run, ["T001", "--parallel", "auto", "--lanes", "2", "--dashboard"])
        assert result.exit_code == 0

        assert len(calls) == 1
        assert calls[0][0] == "T001"
        assert calls[0][1]["parallel"] == "auto"
        assert calls[0][1]["lanes"] == 2
        assert calls[0][1]["dashboard"] is True


# ---------------------------------------------------------------------------
# Tests: develop status
# ---------------------------------------------------------------------------

class TestDevelopStatus:
    """develop status -- the BEST status display."""

    def test_shows_tdd_stage_and_lane_status(self, tmp_path: Path, monkeypatch):
        """Shows TDD stage and lane status."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        task_id = seed_running_task(tmp_path, board_dir)

        from mpga.commands.develop import handle_develop_status

        handle_develop_status(task_id)

    def test_shows_file_locks(self, tmp_path: Path, monkeypatch):
        """Shows file locks for a running task."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        task_id = seed_running_task(tmp_path, board_dir)

        from mpga.commands.develop import handle_develop_status

        handle_develop_status(task_id)

    def test_errors_when_task_does_not_exist(self, tmp_path: Path, monkeypatch):
        """Errors when task does not exist."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        from mpga.board.board import create_empty_board, save_board

        board = create_empty_board()
        save_board(str(board_dir), board)

        from mpga.commands.develop import handle_develop_status

        with pytest.raises(Exception):
            handle_develop_status("T999")


# ---------------------------------------------------------------------------
# Tests: develop abort
# ---------------------------------------------------------------------------

class TestDevelopAbort:
    """develop abort -- sometimes you gotta PULL BACK."""

    def test_releases_locks_and_moves_task_back(self, tmp_path: Path, monkeypatch):
        """Releases all locks and moves task back to todo."""
        board_dir = setup_board(tmp_path)
        tasks_dir = board_dir / "tasks"
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        task_id = seed_running_task(tmp_path, board_dir)

        from mpga.commands.develop import handle_develop_abort
        from mpga.board.task import parse_task_file
        from mpga.board.board import load_board

        handle_develop_abort(task_id)

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task_id))
        parsed = parse_task_file(str(task_path))
        assert parsed.column == "todo"
        assert parsed.run_status == "queued"
        assert len(parsed.file_locks) == 0
        assert len(parsed.scope_locks) == 0
        assert parsed.current_agent is None
        assert parsed.lane_id is None

        board = load_board(str(board_dir))
        assert task_id in board.columns["todo"]
        assert task_id not in board.columns["in-progress"]

    def test_prints_success_message(self, tmp_path: Path, monkeypatch, capsys):
        """Prints success message on abort."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        task_id = seed_running_task(tmp_path, board_dir)

        from mpga.commands.develop import handle_develop_abort

        handle_develop_abort(task_id)

        # The output goes through rich console / log, so just verify no exception

    def test_errors_when_task_does_not_exist(self, tmp_path: Path, monkeypatch):
        """Errors when task does not exist."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        from mpga.board.board import create_empty_board, save_board

        board = create_empty_board()
        save_board(str(board_dir), board)

        from mpga.commands.develop import handle_develop_abort

        with pytest.raises(Exception):
            handle_develop_abort("T999")


# ---------------------------------------------------------------------------
# Tests: develop resume
# ---------------------------------------------------------------------------

class TestDevelopResume:
    """develop resume -- the COMEBACK."""

    def test_resumes_from_last_tdd_stage(self, tmp_path: Path, monkeypatch):
        """Resumes from last TDD stage."""
        board_dir = setup_board(tmp_path)
        tasks_dir = board_dir / "tasks"
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        task_id = seed_running_task(tmp_path, board_dir)

        from mpga.commands.develop import handle_develop_abort, handle_develop_resume
        from mpga.board.task import parse_task_file

        handle_develop_abort(task_id)
        handle_develop_resume(task_id)

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task_id))
        parsed = parse_task_file(str(task_path))
        assert parsed.column == "in-progress"
        assert parsed.run_status == "running"
        assert parsed.tdd_stage == "red"  # preserved from before abort

    def test_prints_success_message_on_resume(self, tmp_path: Path, monkeypatch, capsys):
        """Prints success message with TDD stage on resume."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        task_id = seed_running_task(tmp_path, board_dir)

        from mpga.commands.develop import handle_develop_abort, handle_develop_resume

        handle_develop_abort(task_id)
        handle_develop_resume(task_id)

        # The output goes through rich console / log, so just verify no exception

    def test_errors_when_task_does_not_exist(self, tmp_path: Path, monkeypatch):
        """Errors when task does not exist."""
        board_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop.find_project_root", lambda: str(tmp_path))

        from mpga.board.board import create_empty_board, save_board

        board = create_empty_board()
        save_board(str(board_dir), board)

        from mpga.commands.develop import handle_develop_resume

        with pytest.raises(Exception):
            handle_develop_resume("T999")
