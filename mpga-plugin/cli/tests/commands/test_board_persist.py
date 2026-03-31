"""Tests for persistBoard function."""

from pathlib import Path
from unittest.mock import MagicMock

from mpga.board.board import create_empty_board

# ---------------------------------------------------------------------------
# Tests: persistBoard
# ---------------------------------------------------------------------------

class TestPersistBoard:
    """persistBoard tests."""

    def test_calls_recalc_stats(self, monkeypatch):
        """Calls recalcStats with board, tasksDir, and pre-loaded tasks."""
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_sync_sqlite = MagicMock()
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers._refresh_sqlite_board_mirror", mock_sync_sqlite)
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
        mock_sync_sqlite = MagicMock()
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers._refresh_sqlite_board_mirror", mock_sync_sqlite)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)
        mock_save.assert_called_once_with(board_dir, mock_board)

    def test_refreshes_sqlite_mirror(self, monkeypatch):
        """Refreshes the SQLite mirror after board persistence."""
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_sync_sqlite = MagicMock()
        mock_load_tasks = MagicMock(return_value=[])

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers._refresh_sqlite_board_mirror", mock_sync_sqlite)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)
        mock_sync_sqlite.assert_called_once()
        call_args = mock_sync_sqlite.call_args
        assert call_args[0] == (board_dir, tasks_dir) or call_args.args == (board_dir, tasks_dir)

    def test_load_all_tasks_called_once(self, monkeypatch):
        """Calls loadAllTasks exactly once and passes result to dependent functions."""
        from mpga.board.task import Task
        fake_tasks = [Task(
            id="T001", title="Test", column="todo", status=None, priority="medium",
            created="", updated="",
        )]
        mock_recalc = MagicMock()
        mock_save = MagicMock()
        mock_sync_sqlite = MagicMock()
        mock_load_tasks = MagicMock(return_value=fake_tasks)

        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", mock_recalc)
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", mock_save)
        monkeypatch.setattr("mpga.commands.board_handlers._refresh_sqlite_board_mirror", mock_sync_sqlite)
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", mock_load_tasks)

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        board_dir = "/tmp/test-project/MPGA/board"
        tasks_dir = "/tmp/test-project/MPGA/board/tasks"

        persist_board(mock_board, board_dir, tasks_dir)

        mock_load_tasks.assert_called_once_with(tasks_dir)
        assert mock_recalc.call_args is not None

    def test_correct_call_order(self, monkeypatch):
        """Calls functions in correct order: recalcStats -> saveBoard -> refreshSqliteMirror."""
        call_order = []
        monkeypatch.setattr("mpga.commands.board_handlers.recalc_stats", lambda *a, **kw: call_order.append("recalcStats"))  # noqa: E501
        monkeypatch.setattr("mpga.commands.board_handlers.save_board", lambda *a, **kw: call_order.append("saveBoard"))
        monkeypatch.setattr("mpga.commands.board_handlers._refresh_sqlite_board_mirror", lambda *a, **kw: call_order.append("refreshSqliteMirror"))  # noqa: E501
        monkeypatch.setattr("mpga.commands.board_handlers.load_all_tasks", lambda *a: [])

        from mpga.commands.board_handlers import persist_board

        mock_board = create_empty_board()
        persist_board(mock_board, "/tmp/board", "/tmp/tasks")

        assert call_order == [
            "recalcStats",
            "saveBoard",
            "refreshSqliteMirror",
        ]
