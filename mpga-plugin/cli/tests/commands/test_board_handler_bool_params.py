"""RED test: boolean param sprawl in handle_board_search.

T058 — Fix boolean param sprawl in board_handlers.py.

handle_board_search currently mixes two separate concerns in one flat
parameter list:
  1. Filtering: query, priority, column, scope, agent, tags
  2. Output formatting: full

The refactor should introduce a dataclass (BoardSearchFilters) for the filter
concern and keep `full` as a separate explicit parameter, OR consolidate
everything into the dataclass.  Either way, the raw positional param explosion
must be replaced with a structured object.
"""

from __future__ import annotations

import inspect
from dataclasses import fields
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Contract tests for the refactored signature
# ---------------------------------------------------------------------------

class TestBoardSearchFiltersDataclass:
    """After refactor a BoardSearchFilters dataclass must exist."""

    def test_board_search_filters_dataclass_exists(self):
        """BoardSearchFilters must be importable from board_handlers."""
        from mpga.commands.board_handlers import BoardSearchFilters  # noqa: F401

    def test_board_search_filters_has_required_fields(self):
        """BoardSearchFilters must carry all filter fields."""
        from mpga.commands.board_handlers import BoardSearchFilters
        field_names = {f.name for f in fields(BoardSearchFilters)}
        expected = {"priority", "column", "scope", "agent", "tags"}
        missing = expected - field_names
        assert not missing, (
            f"BoardSearchFilters is missing fields: {missing}. "
            "All filter concerns must be encapsulated in the dataclass."
        )

    def test_board_search_filters_fields_have_none_defaults(self):
        """All filter fields must default to None (they are all optional)."""
        from mpga.commands.board_handlers import BoardSearchFilters
        instance = BoardSearchFilters()
        assert instance.priority is None
        assert instance.column is None
        assert instance.scope is None
        assert instance.agent is None
        assert instance.tags is None


class TestHandleBoardSearchSignature:
    """handle_board_search must accept BoardSearchFilters, not raw booleans."""

    def test_handle_board_search_accepts_filters_param(self):
        """handle_board_search must accept a `filters` parameter."""
        from mpga.commands.board_handlers import handle_board_search
        sig = inspect.signature(handle_board_search)
        assert "filters" in sig.parameters, (
            "handle_board_search must accept a `filters: BoardSearchFilters` "
            "parameter instead of the raw sprawl of individual filter args."
        )

    def test_handle_board_search_priority_not_top_level_param(self):
        """Flat `priority` must not appear as a top-level parameter anymore."""
        from mpga.commands.board_handlers import handle_board_search
        sig = inspect.signature(handle_board_search)
        assert "priority" not in sig.parameters, (
            "`priority` must be encapsulated inside BoardSearchFilters, "
            "not exposed as a raw keyword argument on handle_board_search."
        )

    def test_handle_board_search_column_not_top_level_param(self):
        """Flat `column` must not appear as a top-level parameter."""
        from mpga.commands.board_handlers import handle_board_search
        sig = inspect.signature(handle_board_search)
        assert "column" not in sig.parameters, (
            "`column` must be encapsulated inside BoardSearchFilters."
        )

    def test_handle_board_search_scope_not_top_level_param(self):
        from mpga.commands.board_handlers import handle_board_search
        sig = inspect.signature(handle_board_search)
        assert "scope" not in sig.parameters

    def test_handle_board_search_agent_not_top_level_param(self):
        from mpga.commands.board_handlers import handle_board_search
        sig = inspect.signature(handle_board_search)
        assert "agent" not in sig.parameters

    def test_handle_board_search_tags_not_top_level_param(self):
        from mpga.commands.board_handlers import handle_board_search
        sig = inspect.signature(handle_board_search)
        assert "tags" not in sig.parameters


class TestHandleBoardSearchBehavior:
    """Behavioral contract: the refactored function must still filter correctly."""

    def _mock_task(self, id_="T001", title="test task", column="backlog",
                   priority="medium", scopes=None, assigned=None, tags=None):
        from mpga.board.task import Task
        t = MagicMock(spec=Task)
        t.id = id_
        t.title = title
        t.column = column
        t.priority = priority
        t.scopes = scopes or []
        t.assigned = assigned
        t.tags = tags or []
        t.depends_on = []
        t.evidence_produced = []
        return t

    def test_empty_filters_returns_all_tasks(self):
        """With no filters set, all tasks are returned."""
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        tasks = [
            self._mock_task("T001", column="backlog", priority="high"),
            self._mock_task("T002", column="done", priority="low"),
        ]

        filters = BoardSearchFilters()

        with patch("mpga.commands.board_handlers._board_context") as mock_ctx, \
             patch("mpga.commands.board_handlers._search_db_tasks") as mock_db, \
             patch("mpga.commands.board_handlers.log"):
            mock_ctx.return_value = ("/fake/root", "/fake/board", "/fake/tasks")
            mock_db.return_value = tasks

            results = handle_board_search("", filters=filters)

        assert len(results) == 2

    def test_priority_filter_via_filters_object(self):
        """Filtering by priority through BoardSearchFilters must work."""
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        high_task = self._mock_task("T001", priority="high")
        low_task = self._mock_task("T002", priority="low")

        filters = BoardSearchFilters(priority="high")

        with patch("mpga.commands.board_handlers._board_context") as mock_ctx, \
             patch("mpga.commands.board_handlers._search_db_tasks") as mock_db, \
             patch("mpga.commands.board_handlers.log"):
            mock_ctx.return_value = ("/fake/root", "/fake/board", "/fake/tasks")
            # Simulate DB returning both; handler should filter by priority
            mock_db.return_value = None  # fall back to file-based filtering

            with patch("mpga.commands.board_handlers.load_all_tasks") as mock_load:
                mock_load.return_value = [high_task, low_task]
                results = handle_board_search("", filters=filters)

        assert all(t.priority == "high" for t in results)
        assert len(results) == 1

    def test_agent_filter_via_filters_object(self):
        """Filtering by agent through BoardSearchFilters must work."""
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        my_task = self._mock_task("T001", assigned="alice")
        other_task = self._mock_task("T002", assigned="bob")

        filters = BoardSearchFilters(agent="alice")

        with patch("mpga.commands.board_handlers._board_context") as mock_ctx, \
             patch("mpga.commands.board_handlers._search_db_tasks") as mock_db, \
             patch("mpga.commands.board_handlers.log"):
            mock_ctx.return_value = ("/fake/root", "/fake/board", "/fake/tasks")
            mock_db.return_value = [my_task, other_task]

            results = handle_board_search("", filters=filters)

        assert len(results) == 1
        assert results[0].assigned == "alice"

    def test_conflicting_filters_return_empty(self):
        """A task matching one filter but not another must be excluded."""
        from mpga.commands.board_handlers import BoardSearchFilters, handle_board_search

        task = self._mock_task("T001", priority="high", column="backlog")
        filters = BoardSearchFilters(priority="high", column="done")  # contradictory

        with patch("mpga.commands.board_handlers._board_context") as mock_ctx, \
             patch("mpga.commands.board_handlers._search_db_tasks") as mock_db, \
             patch("mpga.commands.board_handlers.log"):
            mock_ctx.return_value = ("/fake/root", "/fake/board", "/fake/tasks")
            mock_db.return_value = None

            with patch("mpga.commands.board_handlers.load_all_tasks") as mock_load:
                mock_load.return_value = [task]
                results = handle_board_search("", filters=filters)

        assert results == [], (
            "A task that is high-priority but in backlog must not match "
            "a filter that requires column=done."
        )
