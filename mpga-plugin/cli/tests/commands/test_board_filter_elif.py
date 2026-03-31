"""T029: Test that agent filter and file fallback filter are independently applied.

Bug: handle_board_search uses `elif db_results is None` after `if agent:`, so when
both conditions are true (agent is set AND db_results is None i.e. no SQLite),
the file fallback filters (priority, column, scope, tags, text query) are silently skipped.

Fix: change `elif db_results is None:` to `if db_results is None:` so both the agent
filter and the file-based filters are independently evaluated.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def _make_task(
    id_: str,
    title: str,
    column: str = "backlog",
    priority: str = "medium",
    assigned: str | None = None,
    scopes: list[str] | None = None,
    tags: list[str] | None = None,
) -> object:
    from mpga.board.task import Task
    from datetime import UTC, datetime

    return Task(
        id=id_,
        title=title,
        column=column,
        priority=priority,
        status=None,
        assigned=assigned,
        scopes=scopes or [],
        tags=tags or [],
        created=datetime.now(UTC).isoformat(),
        updated=datetime.now(UTC).isoformat(),
    )


class TestBoardFilterElif:

    def _run_search(self, tasks: list, **kwargs) -> list:
        """Run handle_board_search with no SQLite (db_results=None) and capture results.

        Accepts the old flat kwargs (query, agent, column, priority, scope, tags)
        and converts them to a BoardSearchFilters object for the refactored API.
        """
        from mpga.commands import board_handlers
        from mpga.commands.board_handlers import BoardSearchFilters

        project_root = Path("/tmp/fake")
        board_dir = "/tmp/fake/MPGA/board"
        tasks_dir = "/tmp/fake/MPGA/board/tasks"

        query = kwargs.pop("query", "")
        full = kwargs.pop("full", False)
        filters = BoardSearchFilters(**kwargs)

        with (
            patch.object(board_handlers, "_board_context", return_value=(project_root, board_dir, tasks_dir)),
            patch.object(board_handlers, "_search_db_tasks", return_value=None),  # no SQLite
            patch.object(board_handlers, "load_all_tasks", return_value=tasks),
            patch.object(board_handlers.console, "print"),
            patch.object(board_handlers.log, "header"),
            patch.object(board_handlers.log, "info"),
            patch.object(board_handlers.log, "dim"),
        ):
            return board_handlers.handle_board_search(query, filters=filters, full=full)

    def test_agent_and_column_both_filter_when_no_sqlite(self):
        """When agent AND column filters both apply with no SQLite, both must be enforced."""
        tasks = [
            _make_task("T1", "Alpha", column="in-progress", assigned="alice"),
            _make_task("T2", "Beta", column="backlog", assigned="alice"),   # alice but wrong column
            _make_task("T3", "Gamma", column="in-progress", assigned="bob"),  # right column but wrong agent
            _make_task("T4", "Delta", column="done", assigned="carol"),
        ]

        results = self._run_search(tasks, query="", agent="alice", column="in-progress")

        ids = [t.id for t in results]
        assert "T1" in ids, "T1 (alice + in-progress) should be in results"
        assert "T2" not in ids, "T2 (alice + backlog) should be filtered out by column filter"
        assert "T3" not in ids, "T3 (bob + in-progress) should be filtered out by agent filter"

    def test_agent_and_priority_both_filter_when_no_sqlite(self):
        """When agent AND priority filters both apply with no SQLite, both must be enforced."""
        tasks = [
            _make_task("T1", "Alpha", priority="high", assigned="alice"),
            _make_task("T2", "Beta", priority="low", assigned="alice"),    # alice but wrong priority
            _make_task("T3", "Gamma", priority="high", assigned="bob"),    # right priority but wrong agent
        ]

        results = self._run_search(tasks, query="", agent="alice", priority="high")

        ids = [t.id for t in results]
        assert "T1" in ids, "T1 (alice + high) should be in results"
        assert "T2" not in ids, "T2 (alice + low) should be filtered by priority"
        assert "T3" not in ids, "T3 (bob + high) should be filtered by agent"

    def test_agent_and_scope_both_filter_when_no_sqlite(self):
        """When agent AND scope filters both apply with no SQLite, both must be enforced."""
        tasks = [
            _make_task("T1", "Alpha", scopes=["backend"], assigned="alice"),
            _make_task("T2", "Beta", scopes=["frontend"], assigned="alice"),   # alice but wrong scope
            _make_task("T3", "Gamma", scopes=["backend"], assigned="bob"),     # right scope but wrong agent
        ]

        results = self._run_search(tasks, query="", agent="alice", scope="backend")

        ids = [t.id for t in results]
        assert "T1" in ids, "T1 (alice + backend) should be in results"
        assert "T2" not in ids, "T2 (alice + frontend) should be filtered by scope"
        assert "T3" not in ids, "T3 (bob + backend) should be filtered by agent"

    def test_agent_and_text_query_both_filter_when_no_sqlite(self):
        """When agent AND text query both apply with no SQLite, both must be enforced."""
        tasks = [
            _make_task("T1", "Fix the login bug", assigned="alice"),
            _make_task("T2", "Add new feature", assigned="alice"),   # alice but no "login"
            _make_task("T3", "Fix the login bug", assigned="bob"),   # "login" but wrong agent
        ]

        results = self._run_search(tasks, query="login", agent="alice")

        ids = [t.id for t in results]
        assert "T1" in ids, "T1 (alice + 'login' in title) should be in results"
        assert "T2" not in ids, "T2 (alice + no 'login') should be filtered by text query"
        assert "T3" not in ids, "T3 (bob + 'login') should be filtered by agent"
