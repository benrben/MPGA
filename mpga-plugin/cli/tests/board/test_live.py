import json
from pathlib import Path

import pytest

from mpga.board.board import AddTaskOptions, BoardLane, BoardRun, add_task, create_empty_board, recalc_stats
from mpga.board.task import FileLock, parse_task_file, render_task_file
from mpga.board.live import (
    build_board_live_snapshot,
    read_recent_board_events,
    write_board_live_snapshot,
)


@pytest.fixture
def board_dirs(tmp_path: Path):
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    return board_dir, tasks_dir


def test_builds_snapshot_with_lanes_locks_and_recent_events(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    board.milestone = "M001-live"
    board.lanes["lane-auth-1"] = BoardLane(
        id="lane-auth-1",
        task_ids=["T001"],
        status="running",
        scope="src-board",
        files=["src/board/task.ts"],
        current_agent="mpga-green-dev",
        updated_at="2026-03-24T12:00:00.000Z",
    )
    board.active_runs["run-1"] = BoardRun(
        id="run-1",
        lane_id="lane-auth-1",
        task_id="T001",
        status="running",
        agent="mpga-green-dev",
        started_at="2026-03-24T12:00:00.000Z",
    )

    task = add_task(board, str(tasks_dir), AddTaskOptions(title="Track locks", column="in-progress"))
    task_path = next(tasks_dir.iterdir())
    parsed = parse_task_file(str(task_path))
    parsed.lane_id = "lane-auth-1"
    parsed.run_status = "running"
    parsed.current_agent = "mpga-green-dev"
    parsed.file_locks = [
        FileLock(
            path="src/board/task.ts",
            lane_id="lane-auth-1",
            agent="mpga-green-dev",
            acquired_at="2026-03-24T12:00:00.000Z",
        ),
    ]
    task_path.write_text(render_task_file(parsed))

    live_dir = board_dir / "live"
    live_dir.mkdir(parents=True)
    (live_dir / "events.ndjson").write_text(
        json.dumps(
            {
                "type": "lane-transition",
                "lane_id": "lane-auth-1",
                "task_id": task.id,
                "status": "running",
            }
        )
        + "\n"
    )

    recalc_stats(board, str(tasks_dir))
    snapshot = build_board_live_snapshot(board, str(tasks_dir), str(board_dir))

    assert snapshot.milestone == "M001-live"
    assert len(snapshot.columns["in-progress"]) == 1
    assert snapshot.columns["in-progress"][0].lane_id == "lane-auth-1"
    assert len(snapshot.active_lanes) == 1
    assert snapshot.active_lanes[0].current_agent == "mpga-green-dev"
    assert len(snapshot.recent_events) == 1


def test_ignores_missing_or_malformed_event_files(board_dirs):
    board_dir, _ = board_dirs
    assert read_recent_board_events(str(board_dir)) == []

    live_dir = board_dir / "live"
    live_dir.mkdir(parents=True)
    (live_dir / "events.ndjson").write_text('{"bad-json"\n')
    assert read_recent_board_events(str(board_dir)) == []


def test_writes_snapshot_json_into_live_board_directory(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    add_task(board, str(tasks_dir), AddTaskOptions(title="Persist me", column="todo"))
    recalc_stats(board, str(tasks_dir))

    filepath = write_board_live_snapshot(board, str(tasks_dir), str(board_dir))
    expected_path = str(board_dir / "live" / "snapshot.json")
    assert filepath == expected_path
    assert Path(filepath).exists()
    raw = json.loads(Path(filepath).read_text())
    assert raw["columns"]["todo"][0]["title"] == "Persist me"
