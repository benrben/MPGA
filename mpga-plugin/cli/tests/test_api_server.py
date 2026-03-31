"""Tests for the API server router and handler functions (T096)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from mpga.db.schema import create_schema
from mpga.web.router import route
from mpga.web import api as _api


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestRouter:
    def test_dispatches_search(self):
        result = route("/api/search", "GET", {"q": "test"})
        assert result is not None
        handler_name, path_params = result
        assert handler_name == "search"
        assert path_params == {}

    def test_dispatches_tasks(self):
        result = route("/api/tasks", "GET", {})
        assert result is not None
        handler_name, path_params = result
        assert handler_name == "tasks"
        assert path_params == {}

    def test_dispatches_scopes(self):
        result = route("/api/scopes", "GET", {})
        assert result is not None
        handler_name, path_params = result
        assert handler_name == "scopes"
        assert path_params == {}

    def test_dispatches_task_detail(self):
        result = route("/api/tasks/T001", "GET", {})
        assert result is not None
        handler_name, path_params = result
        assert handler_name == "task_detail"
        assert path_params == {"task_id": "T001"}

    def test_returns_none_for_unknown_api_route(self):
        result = route("/api/unknown-endpoint", "GET", {})
        assert result is None

    def test_returns_none_for_non_api_route(self):
        """Non-/api/ routes should not be matched by the router."""
        result = route("/index.html", "GET", {})
        assert result is None

    def test_dispatches_scope_detail(self):
        result = route("/api/scopes/SC-core", "GET", {})
        assert result is not None
        handler_name, path_params = result
        assert handler_name == "scope_detail"
        assert path_params == {"scope_id": "SC-core"}


# ---------------------------------------------------------------------------
# Handler unit tests — no HTTP server, call functions directly
# ---------------------------------------------------------------------------

class TestHandleSearch:
    def test_returns_dict_with_tasks_and_scopes_keys(self, conn):
        result = _api.handle_search(conn, {"q": "test"})
        assert isinstance(result, dict)
        assert "tasks" in result
        assert "scopes" in result
        assert result["query"] == "test"

    def test_empty_query_returns_empty_lists(self, conn):
        result = _api.handle_search(conn, {"q": ""})
        assert result["tasks"] == []
        assert result["scopes"] == []

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_search(conn, {"q": "test"})
        # Must not raise
        json.dumps(result)


class TestHandleTasks:
    def test_returns_dict_with_tasks_key(self, conn):
        result = _api.handle_tasks(conn, {})
        assert isinstance(result, dict)
        assert "tasks" in result
        assert isinstance(result["tasks"], list)

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_tasks(conn, {})
        json.dumps(result)


class TestHandleTaskDetail:
    def test_returns_error_for_missing_task(self, conn):
        result = _api.handle_task_detail(conn, "T-NONEXISTENT")
        assert "error" in result

    def test_returns_task_dict_for_existing_task(self, conn):
        from mpga.board.task import Task
        from mpga.db.repos.tasks import TaskRepo

        repo = TaskRepo(conn)
        task = Task(
            id="T001",
            title="test task",
            column="backlog",
            status=None,
            priority="medium",
            created="2026-01-01T00:00:00",
            updated="2026-01-01T00:00:00",
        )
        repo.create(task)

        result = _api.handle_task_detail(conn, "T001")
        assert "task" in result
        assert result["task"]["id"] == "T001"
        assert result["task"]["title"] == "test task"

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_task_detail(conn, "T-MISSING")
        json.dumps(result)


class TestHandleScopes:
    def test_returns_dict_with_scopes_key(self, conn):
        result = _api.handle_scopes(conn, {})
        assert isinstance(result, dict)
        assert "scopes" in result
        assert isinstance(result["scopes"], list)

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_scopes(conn, {})
        json.dumps(result)


class TestHandleScopeDetail:
    def test_returns_error_for_missing_scope(self, conn):
        result = _api.handle_scope_detail(conn, "SC-NONEXISTENT")
        assert "error" in result

    def test_returns_scope_for_existing(self, conn):
        from mpga.db.repos.scopes import Scope, ScopeRepo

        repo = ScopeRepo(conn)
        scope = Scope(id="SC-core", name="core", summary="core module")
        repo.create(scope)

        result = _api.handle_scope_detail(conn, "SC-core")
        assert "scope" in result
        assert result["scope"]["id"] == "SC-core"


class TestHandleEvidence:
    def test_returns_dict_with_evidence_key(self, conn):
        result = _api.handle_evidence(conn, {})
        assert "evidence" in result
        assert isinstance(result["evidence"], list)

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_evidence(conn, {})
        json.dumps(result)


class TestHandleBoard:
    def test_returns_dict_with_board_key(self, conn):
        result = _api.handle_board(conn)
        assert "board" in result
        assert isinstance(result["board"], dict)

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_board(conn)
        json.dumps(result)


class TestHandleMilestones:
    def test_returns_dict_with_milestones_key(self, conn):
        result = _api.handle_milestones(conn, {})
        assert "milestones" in result
        assert isinstance(result["milestones"], list)

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_milestones(conn, {})
        json.dumps(result)


class TestHandleStats:
    def test_returns_dict_with_expected_keys(self, conn):
        result = _api.handle_stats(conn)
        assert "tasks" in result
        assert "scopes" in result
        assert "evidence" in result

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_stats(conn)
        json.dumps(result)


class TestHandleHealth:
    def test_returns_ok_status(self, conn):
        result = _api.handle_health(conn)
        assert result["status"] == "ok"

    def test_result_is_json_serializable(self, conn):
        result = _api.handle_health(conn)
        json.dumps(result)


# ---------------------------------------------------------------------------
# Content-Type check (via the handler's _send_json logic — checked indirectly)
# ---------------------------------------------------------------------------

class TestJsonContentType:
    """Verify that all handlers return dicts (which the server json.dumps with
    application/json Content-Type).  HTTP-level Content-Type is verified via
    the serve.py _send_json helper — here we just confirm the dict contract."""

    def test_all_handlers_return_dicts(self, conn):
        handlers = [
            lambda: _api.handle_search(conn, {"q": "x"}),
            lambda: _api.handle_tasks(conn, {}),
            lambda: _api.handle_task_detail(conn, "T-MISSING"),
            lambda: _api.handle_scopes(conn, {}),
            lambda: _api.handle_scope_detail(conn, "SC-MISSING"),
            lambda: _api.handle_evidence(conn, {}),
            lambda: _api.handle_board(conn),
            lambda: _api.handle_milestones(conn, {}),
            lambda: _api.handle_stats(conn),
            lambda: _api.handle_health(conn),
        ]
        for fn in handlers:
            result = fn()
            assert isinstance(result, dict), f"Expected dict, got {type(result)} from {fn}"
            # Every dict must be JSON-serializable
            json.dumps(result)
