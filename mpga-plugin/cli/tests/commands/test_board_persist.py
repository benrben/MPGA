"""Tests for persistBoard function."""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from mpga.board.board import BoardState, create_empty_board


# ---------------------------------------------------------------------------
# Tests: persistBoard
# ---------------------------------------------------------------------------

class TestPersistBoard:
    """persistBoard tests."""

    def test_calls_recalc_stats(self, monkeypatch):
        """Calls recalcStats with board, tasksDir, and pre-loaded tasks."""
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_render = MagicMock(return_value="# Mock Board")
        mock_write_snapshot = MagicMock(return_value="/tmp/test-project/MPGA/board/live/snapshot.json")
        mock_write_html = MagicMock(return_value="/tmp/test-project/MPGA/board/live/index.html")
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers.render_board_md", mock_render)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_snapshot", mock_write_snapshot)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_html", mock_write_html)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)
        mock_recalc.assert_called_once()

    def test_calls_save_board(self, monkeypatch):
        """Calls saveBoard with boardDir and board."""
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_render = MagicMock(return_value="# Mock Board")
        mock_write_snapshot = MagicMock(return_value="")
        mock_write_html = MagicMock(return_value="")
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers.render_board_md", mock_render)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_snapshot", mock_write_snapshot)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_html", mock_write_html)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)
        mock_save.assert_called_once_with(board_dir, mock_board)

    def test_writes_board_md(self, monkeypatch, tmp_path: Path):
        """Writes BOARD.md with rendered markdown using pre-loaded tasks."""
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_render = MagicMock(return_value="# Mock Board")
        mock_write_snapshot = MagicMock(return_value="")
        mock_write_html = MagicMock(return_value="")
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers.render_board_md", mock_render)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_snapshot", mock_write_snapshot)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_html", mock_write_html)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = str(tmp_path)
        tasks_dir = str(tmp_path / "tasks")

        persist_board(mock_board, board_dir, tasks_dir)
        mock_render.assert_called_once()

    def test_refreshes_live_artifacts(self, monkeypatch):
        """Refreshes live board artifacts from the same persisted state."""
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_render = MagicMock(return_value="# Mock Board")
        mock_write_snapshot = MagicMock(return_value="/tmp/snapshot.json")
        mock_write_html = MagicMock(return_value="/tmp/index.html")
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers.render_board_md", mock_render)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_snapshot", mock_write_snapshot)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_html", mock_write_html)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)
        mock_write_snapshot.assert_called_once()
        mock_write_html.assert_called_once()

    def test_load_all_tasks_called_once(self, monkeypatch):
        """Calls loadAllTasks exactly once and passes result to dependent functions."""
        from mpga.board.task import Task
        fake_tasks = [Task(
            id="T001", title="Test", column="todo", status=None, priority="medium",
            created="", updated="",
        )]
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_render = MagicMock(return_value="# Board")
        mock_write_snapshot = MagicMock(return_value="")
        mock_write_html = MagicMock(return_value="")
        mock_load_tasks = MagicMock(return_value=fake_tasks)

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers.render_board_md", mock_render)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_snapshot", mock_write_snapshot)
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_html", mock_write_html)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)

        mock_load_tasks.assert_called_once_with(tasks_dir)
        assert mock_recalc.call_args is not None

    def test_correct_call_order(self, monkeypatch):
        """Calls functions in correct order: recalcStats -> saveBoard -> writeBoardMd -> live artifacts."""
        call_order = []
        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", lambda *a, **kw: call_order.append("recalcStats"))
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", lambda *a: call_order.append("saveBoard"))
        monkeypatch.setattr("mpga.commands.board_handlers.render_board_md", lambda *a, **kw: (call_order.append("renderBoardMd"), "")[1])
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_snapshot", lambda *a, **kw: (call_order.append("writeBoardLiveSnapshot"), "")[1])
        monkeypatch.setattr("mpga.commands.board_handlers.write_board_live_html", lambda *a: (call_order.append("writeBoardLiveHtml"), "")[1])
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", lambda *a: [])

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        persist_board(mock_board, "/tmp/board", "/tmp/tasks")

        assert call_order == [
            "recalcStats",
            "saveBoard",
            "renderBoardMd",
            "writeBoardLiveSnapshot",
            "writeBoardLiveHtml",
        ]
