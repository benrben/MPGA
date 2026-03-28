from pathlib import Path

import pytest

from mpga.board.board import (
    AddTaskOptions,
    BoardStats,
    add_task,
    create_empty_board,
    recalc_stats,
    save_board,
)
from mpga.board.board_md import render_board_md


@pytest.fixture
def board_dirs(tmp_path: Path):
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    return board_dir, tasks_dir


def test_includes_milestone_title_and_progress_line(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    board.milestone = "M001-demo"
    save_board(str(board_dir), board)
    add_task(board, str(tasks_dir), AddTaskOptions(title="Task one", column="todo"))
    recalc_stats(board, str(tasks_dir))
    md = render_board_md(board, str(tasks_dir))
    assert "# Board: M001-demo" in md
    assert "**Progress:" in md
    assert "Todo" in md
    assert "Task one" in md


def test_shows_health_line_for_blocked_tasks(board_dirs):
    board_dir, tasks_dir = board_dirs
    board = create_empty_board()
    save_board(str(board_dir), board)
    board.stats = BoardStats(
        blocked=2,
        total=3,
        done=0,
        in_flight=0,
        progress_pct=0,
        evidence_produced=0,
        evidence_expected=0,
    )
    md = render_board_md(board, str(tasks_dir))
    assert "blocked" in md
