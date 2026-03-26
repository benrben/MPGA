"""Tests for the develop-scheduler module."""

import json
from pathlib import Path

import pytest

from tests.conftest import write_file
from mpga.board.board import AddTaskOptions, create_empty_board, save_board, add_task, load_board
from mpga.board.task import FileLock, parse_task_file, render_task_file
from mpga.commands.develop_scheduler import (
    PersistLaneTransitionOptions,
    TddCheckpoint,
    split_into_file_groups,
    can_acquire_file_locks,
    run_develop_task,
    save_tdd_checkpoint,
    load_tdd_checkpoint,
    persist_lane_transition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_board(tmp_path: Path):
    """Set up minimal board structure, return (board_dir, tasks_dir)."""
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return board_dir, tasks_dir


# ---------------------------------------------------------------------------
# Tests: develop scheduler
# ---------------------------------------------------------------------------

class TestDevelopScheduler:
    """develop scheduler tests."""

    def test_splits_disjoint_file_groups(self):
        """Splits disjoint file groups into separate lanes."""
        lanes = split_into_file_groups(
            "T001",
            [["src/a.ts"], ["src/b.ts", "src/c.ts"]],
            "src-board",
        )
        assert len(lanes) == 2
        assert lanes[0].files == ["src/a.ts"]
        assert lanes[1].files == ["src/b.ts", "src/c.ts"]

    def test_merges_overlapping_file_groups(self):
        """Merges overlapping file groups into one lane."""
        lanes = split_into_file_groups(
            "T001",
            [["src/a.ts", "src/b.ts"], ["src/b.ts", "src/c.ts"]],
            "src-board",
        )
        assert len(lanes) == 1
        assert lanes[0].files == ["src/a.ts", "src/b.ts", "src/c.ts"]

    def test_creates_default_lane_for_empty_groups(self):
        """Creates a default lane when no file groups are known yet."""
        lanes = split_into_file_groups("T001", [[]], "src-board")
        assert len(lanes) == 1
        assert lanes[0].files == []

    def test_rejects_file_lock_conflicts(self, tmp_path: Path):
        """Rejects same-file lock conflicts against active tasks."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        add_task(board, str(tasks_dir), AddTaskOptions(title="Lock holder", column="in-progress"))

        task_path = next(tasks_dir.iterdir())
        parsed = parse_task_file(str(task_path))
        parsed.lane_id = "lane-1"
        parsed.run_status = "running"
        parsed.current_agent = "mpga-green-dev"
        parsed.file_locks = [
            FileLock(
                path="src/shared.ts",
                lane_id="lane-1",
                agent="mpga-green-dev",
                acquired_at="2026-03-24T12:00:00.000Z",
            ),
        ]
        task_path.write_text(render_task_file(parsed))

        ok, conflicts = can_acquire_file_locks(["src/shared.ts"], str(tasks_dir))
        assert ok is False
        assert conflicts == ["src/shared.ts"]

    def test_run_develop_task_consolidates_none_parallel(self, tmp_path: Path, monkeypatch):
        """runDevelopTask consolidates all files into one lane when parallel is none."""
        board_dir, tasks_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop_scheduler.find_project_root", lambda: tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(
            title="Multi-file task",
            column="in-progress",
            scopes=["src-board"],
        ))
        save_board(str(board_dir), board)

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task.id))
        parsed = parse_task_file(str(task_path))
        parsed.file_locks = [
            FileLock(path="src/a.ts", lane_id="l1", agent="red-dev", acquired_at="2026-03-24T12:00:00.000Z"),
            FileLock(path="src/b.ts", lane_id="l2", agent="red-dev", acquired_at="2026-03-24T12:00:00.000Z"),
            FileLock(path="src/c.ts", lane_id="l3", agent="red-dev", acquired_at="2026-03-24T12:00:00.000Z"),
        ]
        task_path.write_text(render_task_file(parsed))

        lane_ids = run_develop_task(task.id, parallel="none")
        assert len(lane_ids) == 1

        updated_board = load_board(str(board_dir))
        lane = updated_board.lanes[lane_ids[0]]
        assert sorted(lane.files) == ["src/a.ts", "src/b.ts", "src/c.ts"]

    def test_run_develop_task_keeps_lanes_auto_parallel(self, tmp_path: Path, monkeypatch):
        """runDevelopTask keeps separate lanes when parallel is auto."""
        board_dir, tasks_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop_scheduler.find_project_root", lambda: tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(
            title="Multi-file task",
            column="in-progress",
            scopes=["src-board"],
        ))
        save_board(str(board_dir), board)

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task.id))
        parsed = parse_task_file(str(task_path))
        parsed.file_locks = [
            FileLock(path="src/a.ts", lane_id="l1", agent="red-dev", acquired_at="2026-03-24T12:00:00.000Z"),
            FileLock(path="src/b.ts", lane_id="l2", agent="red-dev", acquired_at="2026-03-24T12:00:00.000Z"),
        ]
        task_path.write_text(render_task_file(parsed))

        lane_ids = run_develop_task(task.id, parallel="auto")
        assert len(lane_ids) == 2

    def test_run_develop_task_skips_conflicting_locks(self, tmp_path: Path, monkeypatch):
        """runDevelopTask skips lanes with conflicting file locks."""
        board_dir, tasks_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop_scheduler.find_project_root", lambda: tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)

        # Create a running task holding a lock on src/shared.ts
        holder = add_task(board, str(tasks_dir), AddTaskOptions(title="Lock holder", column="in-progress"))
        save_board(str(board_dir), board)
        holder_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(holder.id))
        holder_task = parse_task_file(str(holder_path))
        holder_task.run_status = "running"
        holder_task.lane_id = "holder-lane"
        holder_task.file_locks = [
            FileLock(path="src/shared.ts", lane_id="holder-lane", agent="mpga-green-dev", acquired_at="2026-03-24T12:00:00.000Z"),
        ]
        holder_path.write_text(render_task_file(holder_task))

        # Create a contender whose file_locks overlap
        contender = add_task(board, str(tasks_dir), AddTaskOptions(
            title="Contender",
            column="in-progress",
            scopes=["src-board"],
        ))
        save_board(str(board_dir), board)
        contender_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(contender.id))
        contender_task = parse_task_file(str(contender_path))
        contender_task.file_locks = [
            FileLock(path="src/shared.ts", lane_id="c-lane", agent="mpga-red-dev", acquired_at="2026-03-24T12:00:00.000Z"),
        ]
        contender_path.write_text(render_task_file(contender_task))

        scheduled_ids = run_develop_task(contender.id)

        updated_board = load_board(str(board_dir))
        for lane_id in scheduled_ids:
            lane = updated_board.lanes.get(lane_id)
            if lane and "src/shared.ts" in lane.files:
                assert lane.status != "running"
        assert len(scheduled_ids) == 0


# ---------------------------------------------------------------------------
# Tests: TDD checkpoint
# ---------------------------------------------------------------------------

class TestTddCheckpoint:
    """TDD checkpoint tests."""

    def test_save_checkpoint_writes_section(self, tmp_path: Path):
        """saveTddCheckpoint writes a TDD Checkpoint section to the task body."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(title="Checkpoint task", column="in-progress"))
        save_board(str(board_dir), board)

        checkpoint = TddCheckpoint(
            stage="red",
            last_test_file="src/foo.test.ts",
            last_impl_file="src/foo.ts",
            failing_test="should handle edge case",
            saved_at="2026-03-24T14:00:00.000Z",
        )
        save_tdd_checkpoint(str(tasks_dir), task.id, checkpoint)

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task.id))
        raw = task_path.read_text()
        assert "## TDD Checkpoint" in raw
        assert "stage: red" in raw
        assert "lastTestFile: src/foo.test.ts" in raw
        assert "lastImplFile: src/foo.ts" in raw
        assert "failingTest: should handle edge case" in raw
        assert "savedAt: 2026-03-24T14:00:00.000Z" in raw

    def test_load_checkpoint_returns_saved(self, tmp_path: Path):
        """loadTddCheckpoint returns the saved checkpoint."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(title="Load checkpoint", column="in-progress"))
        save_board(str(board_dir), board)

        checkpoint = TddCheckpoint(
            stage="green",
            last_test_file="src/bar.test.ts",
            last_impl_file="src/bar.ts",
            failing_test="should pass now",
            saved_at="2026-03-24T15:00:00.000Z",
        )
        save_tdd_checkpoint(str(tasks_dir), task.id, checkpoint)

        loaded = load_tdd_checkpoint(str(tasks_dir), task.id)
        assert loaded is not None
        assert loaded.stage == "green"
        assert loaded.last_test_file == "src/bar.test.ts"
        assert loaded.last_impl_file == "src/bar.ts"
        assert loaded.failing_test == "should pass now"
        assert loaded.saved_at == "2026-03-24T15:00:00.000Z"

    def test_load_checkpoint_returns_none_when_missing(self, tmp_path: Path):
        """loadTddCheckpoint returns None when no checkpoint exists."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(title="No checkpoint", column="in-progress"))
        save_board(str(board_dir), board)

        loaded = load_tdd_checkpoint(str(tasks_dir), task.id)
        assert loaded is None

    def test_save_checkpoint_replaces_existing(self, tmp_path: Path):
        """saveTddCheckpoint replaces an existing checkpoint section."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(title="Replace checkpoint", column="in-progress"))
        save_board(str(board_dir), board)

        save_tdd_checkpoint(str(tasks_dir), task.id, TddCheckpoint(
            stage="red",
            last_test_file="src/old.test.ts",
            saved_at="2026-03-24T14:00:00.000Z",
        ))
        save_tdd_checkpoint(str(tasks_dir), task.id, TddCheckpoint(
            stage="blue",
            last_test_file="src/new.test.ts",
            last_impl_file="src/new.ts",
            saved_at="2026-03-24T16:00:00.000Z",
        ))

        loaded = load_tdd_checkpoint(str(tasks_dir), task.id)
        assert loaded.stage == "blue"
        assert loaded.last_test_file == "src/new.test.ts"
        assert loaded.last_impl_file == "src/new.ts"

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task.id))
        raw = task_path.read_text()
        checkpoint_count = raw.count("## TDD Checkpoint")
        assert checkpoint_count == 1

    def test_load_checkpoint_returns_none_for_nonexistent_task(self, tmp_path: Path):
        """loadTddCheckpoint returns None for non-existent task."""
        _, tasks_dir = setup_board(tmp_path)

        loaded = load_tdd_checkpoint(str(tasks_dir), "T999")
        assert loaded is None

    def test_checkpoint_optional_fields(self, tmp_path: Path):
        """Checkpoint fields are optional except stage and savedAt."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(title="Minimal checkpoint", column="in-progress"))
        save_board(str(board_dir), board)

        save_tdd_checkpoint(str(tasks_dir), task.id, TddCheckpoint(
            stage="review",
            saved_at="2026-03-24T17:00:00.000Z",
        ))

        loaded = load_tdd_checkpoint(str(tasks_dir), task.id)
        assert loaded.stage == "review"
        assert loaded.last_test_file is None
        assert loaded.last_impl_file is None
        assert loaded.failing_test is None
        assert loaded.saved_at == "2026-03-24T17:00:00.000Z"

    def test_run_develop_task_resumes_from_checkpoint(self, tmp_path: Path, monkeypatch):
        """runDevelopTask resumes from checkpoint when one exists."""
        board_dir, tasks_dir = setup_board(tmp_path)
        monkeypatch.setattr("mpga.commands.develop_scheduler.find_project_root", lambda: tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(
            title="Resume task",
            column="in-progress",
            scopes=["src-board"],
        ))
        save_board(str(board_dir), board)

        save_tdd_checkpoint(str(tasks_dir), task.id, TddCheckpoint(
            stage="green",
            last_test_file="src/resume.test.ts",
            last_impl_file="src/resume.ts",
            failing_test="should resume",
            saved_at="2026-03-24T18:00:00.000Z",
        ))

        lane_ids = run_develop_task(task.id)
        assert len(lane_ids) >= 1

        task_path = next(f for f in tasks_dir.iterdir() if f.name.startswith(task.id))
        parsed = parse_task_file(str(task_path))
        assert parsed.tdd_stage == "green"


# ---------------------------------------------------------------------------
# Tests: persist lane transition
# ---------------------------------------------------------------------------

class TestPersistLaneTransition:
    """persistLaneTransition tests."""

    def test_persists_transition_into_task_board_and_snapshot(self, tmp_path: Path):
        """Persists lane transitions into task, board, and live snapshot state."""
        board_dir, tasks_dir = setup_board(tmp_path)

        board = create_empty_board()
        save_board(str(board_dir), board)
        task = add_task(board, str(tasks_dir), AddTaskOptions(title="Persist transition", column="todo"))
        save_board(str(board_dir), board)

        persist_lane_transition(str(board_dir), str(tasks_dir), PersistLaneTransitionOptions(
            task_id=task.id,
            lane_id="lane-1",
            status="running",
            agent="mpga-green-dev",
            files=["src/board/task.ts"],
            scope="src-board",
        ))

        task_path = next(tasks_dir.iterdir())
        parsed = parse_task_file(str(task_path))
        next_board = load_board(str(board_dir))
        assert parsed.lane_id == "lane-1"
        assert parsed.run_status == "running"
        assert parsed.file_locks[0].path == "src/board/task.ts"
        assert next_board.lanes["lane-1"].current_agent == "mpga-green-dev"
