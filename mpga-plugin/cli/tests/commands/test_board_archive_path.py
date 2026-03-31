"""T056: Test that board_handlers.py sanitizes milestone name before using it in archive path.

A milestone name like '../../etc/passwd' must be rejected or sanitized so that
the archive path cannot escape the intended milestones directory.
"""

import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import the handler
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def _make_board(milestone: str | None):
    """Return a minimal mock BoardState with a given milestone."""
    board = MagicMock()
    board.milestone = milestone
    board.columns = {"done": ["T999"]}
    board.wip_limits = {}
    board.stats = MagicMock()
    return board


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestArchivePathSanitization:
    """handle_board_archive must reject or sanitize path-traversal milestone names."""

    def test_traversal_milestone_is_rejected(self, tmp_path):
        """A milestone name with '../' should raise ValueError (or be rejected)."""
        from mpga.commands import board_handlers

        project_root = tmp_path
        board_dir = str(project_root / "MPGA" / "board")
        tasks_dir = str(project_root / "MPGA" / "board" / "tasks")
        Path(board_dir).mkdir(parents=True, exist_ok=True)
        Path(tasks_dir).mkdir(parents=True, exist_ok=True)

        evil_milestone = "../../etc/passwd"

        board = _make_board(evil_milestone)

        with (
            patch.object(board_handlers, "_board_context", return_value=(project_root, board_dir, tasks_dir)),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "find_task_file", return_value=None),
            patch.object(board_handlers, "with_board_lock"),
            patch.object(board_handlers, "persist_board"),
        ):
            with pytest.raises(ValueError, match=r"(?i)invalid|unsafe|traversal|milestone"):
                board_handlers.handle_board_archive()

    def test_traversal_with_backslash_is_rejected(self, tmp_path):
        """A milestone name with backslash path component should be rejected."""
        from mpga.commands import board_handlers

        project_root = tmp_path
        board_dir = str(project_root / "MPGA" / "board")
        tasks_dir = str(project_root / "MPGA" / "board" / "tasks")
        Path(board_dir).mkdir(parents=True, exist_ok=True)
        Path(tasks_dir).mkdir(parents=True, exist_ok=True)

        evil_milestone = r"foo\..\..\bar"

        board = _make_board(evil_milestone)

        with (
            patch.object(board_handlers, "_board_context", return_value=(project_root, board_dir, tasks_dir)),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "find_task_file", return_value=None),
            patch.object(board_handlers, "with_board_lock"),
            patch.object(board_handlers, "persist_board"),
        ):
            with pytest.raises(ValueError):
                board_handlers.handle_board_archive()

    def test_safe_milestone_name_is_accepted(self, tmp_path):
        """A safe alphanumeric/dash/underscore milestone name must not raise."""
        from mpga.commands import board_handlers

        project_root = tmp_path
        board_dir = str(project_root / "MPGA" / "board")
        tasks_dir = str(project_root / "MPGA" / "board" / "tasks")
        Path(board_dir).mkdir(parents=True, exist_ok=True)
        Path(tasks_dir).mkdir(parents=True, exist_ok=True)

        safe_milestone = "M001-phase-2-evaluation_test"

        board = _make_board(safe_milestone)

        with (
            patch.object(board_handlers, "_board_context", return_value=(project_root, board_dir, tasks_dir)),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "find_task_file", return_value=None),
            patch.object(board_handlers, "with_board_lock"),
            patch.object(board_handlers, "persist_board"),
        ):
            # Must not raise — no done tasks so exits cleanly
            board.columns = {"done": []}
            board_handlers.handle_board_archive()

    def test_archive_path_stays_within_milestones_dir(self, tmp_path):
        """The resolved archive path must be inside the project milestones directory."""
        from mpga.commands import board_handlers

        project_root = tmp_path
        milestones_base = project_root / "MPGA" / "milestones"

        evil_milestone = "../../etc"

        board = _make_board(evil_milestone)
        board_dir = str(project_root / "MPGA" / "board")
        tasks_dir = str(project_root / "MPGA" / "board" / "tasks")
        Path(board_dir).mkdir(parents=True, exist_ok=True)
        Path(tasks_dir).mkdir(parents=True, exist_ok=True)

        with (
            patch.object(board_handlers, "_board_context", return_value=(project_root, board_dir, tasks_dir)),
            patch.object(board_handlers, "load_board", return_value=board),
            patch.object(board_handlers, "find_task_file", return_value=None),
            patch.object(board_handlers, "with_board_lock"),
            patch.object(board_handlers, "persist_board"),
        ):
            with pytest.raises(ValueError):
                board_handlers.handle_board_archive()
