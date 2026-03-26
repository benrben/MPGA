import re
from pathlib import Path

import pytest

from mpga.board.board import (
    AddTaskOptions,
    BoardLane,
    load_board,
    save_board,
    create_empty_board,
    recalc_stats,
    add_task,
    move_task,
)
from mpga.board.task import parse_task_file


@pytest.fixture
def board_dirs(tmp_path: Path):
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    return board_dir, tasks_dir


def test_load_board_returns_empty_board_when_board_json_missing(board_dirs):
    board_dir, _ = board_dirs
    board = load_board(str(board_dir))
    assert board.milestone is None
    assert board.columns["todo"] == []
    assert board.lanes == {}
    assert board.active_runs == {}
    assert board.scheduler.lock_mode == "file"
    assert board.ui.refresh_interval_ms == 2500


def test_save_board_round_trips_through_load_board(board_dirs):
    board_dir, _ = board_dirs
    board = create_empty_board()
    board.milestone = "M001-x"
    board.scheduler.max_parallel_lanes = 4
    board.ui.theme = "signal"
    save_board(str(board_dir), board)
    again = load_board(str(board_dir))
    assert again.milestone == "M001-x"
    assert again.scheduler.max_parallel_lanes == 4
    assert again.ui.theme == "signal"
    assert (board_dir / "board.json").exists()


def test_load_board_backfills_missing_runtime_metadata_for_legacy_board_files(board_dirs):
    board_dir, _ = board_dirs
    import json

    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "board.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "milestone": "M001-legacy",
                "updated": "2026-03-24T00:00:00.000Z",
                "columns": {
                    "backlog": [],
                    "todo": [],
                    "in-progress": [],
                    "testing": [],
                    "review": [],
                    "done": [],
                },
                "stats": {
                    "total": 0,
                    "done": 0,
                    "in_flight": 0,
                    "blocked": 0,
                    "progress_pct": 0,
                    "evidence_produced": 0,
                    "evidence_expected": 0,
                },
                "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
                "next_task_id": 1,
            }
        )
    )

    board = load_board(str(board_dir))
    assert board.lanes == {}
    assert board.active_runs == {}
    assert board.scheduler.lock_mode == "file"
    assert board.ui.refresh_interval_ms == 2500


def test_add_task_writes_task_file_and_appends_id_to_column(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    save_board(str(board_dir), board)
    task = add_task(board, str(tasks_dir), AddTaskOptions(title="Hello world", column="todo"))
    assert re.match(r"^T\d+", task.id)
    assert task.id in board.columns["todo"]
    fp = next(tasks_dir.iterdir())
    assert parse_task_file(str(fp)).title == "Hello world"


def test_move_task_updates_column_in_board_and_task_file(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    save_board(str(board_dir), board)
    task = add_task(board, str(tasks_dir), AddTaskOptions(title="Move me", column="todo"))
    res = move_task(board, str(tasks_dir), task.id, "in-progress", True)
    assert res.success is True
    assert task.id not in board.columns["todo"]
    assert task.id in board.columns["in-progress"]
    task_file = next(tasks_dir.iterdir())
    assert parse_task_file(str(task_file)).column == "in-progress"


def test_recalc_stats_aggregates_tasks_from_disk(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    board.lanes["lane-1"] = BoardLane(
        id="lane-1",
        task_ids=[],
        status="queued",
        files=["src/board/task.ts"],
        updated_at="2026-03-24T00:00:00.000Z",
    )
    save_board(str(board_dir), board)
    add_task(board, str(tasks_dir), AddTaskOptions(title="A", column="todo"))
    add_task(board, str(tasks_dir), AddTaskOptions(title="B", column="done"))
    recalc_stats(board, str(tasks_dir))
    assert board.stats.total == 2
    assert board.stats.done == 1
    assert board.stats.progress_pct == 50
    assert board.lanes["lane-1"].files == ["src/board/task.ts"]
