"""Tests for T020 — Observations REST API endpoints."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / ".mpga" / "mpga.db"


@pytest.fixture()
def schema_conn(tmp_db: Path):
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(str(tmp_db))
    create_schema(conn)
    yield conn
    conn.close()


def _seed_observations(conn: sqlite3.Connection, count: int = 3) -> list[int]:
    """Insert sample observations and return their IDs."""
    ids: list[int] = []
    for i in range(1, count + 1):
        cur = conn.execute(
            "INSERT INTO observations (title, type, narrative, facts, created_at) "
            "VALUES (?, 'tool_output', ?, ?, datetime('now', ? || ' seconds'))",
            (f"obs {i}", f"narrative {i}", f"fact {i}", str(-count + i)),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    return ids


class TestObservationsListRoute:
    def test_observations_list_route(self) -> None:
        from mpga.web.router import route

        result = route("/api/observations")
        assert result is not None, "/api/observations must be registered"
        handler_name, _params = result
        assert handler_name == "observations"

    def test_observations_list_returns_json(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_observations

        _seed_observations(schema_conn, 3)
        result = handle_observations(schema_conn, {})
        assert "observations" in result
        assert len(result["observations"]) == 3
        assert "title" in result["observations"][0]


class TestObservationsGetById:
    def test_observations_get_by_id(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_observation_detail

        ids = _seed_observations(schema_conn, 1)
        result = handle_observation_detail(schema_conn, str(ids[0]))
        assert "observation" in result
        assert result["observation"]["title"] == "obs 1"

    def test_observations_get_missing(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_observation_detail

        result = handle_observation_detail(schema_conn, "99999")
        assert "error" in result


class TestObservationsSearch:
    def test_observations_search(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_observations_search

        _seed_observations(schema_conn, 3)
        result = handle_observations_search(schema_conn, {"q": "narrative"})
        assert "observations" in result
        assert len(result["observations"]) >= 1

    def test_observations_search_empty(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_observations_search

        result = handle_observations_search(schema_conn, {"q": "zzz_nonexistent_zzz"})
        assert "observations" in result
        assert len(result["observations"]) == 0


class TestObservationsTimeline:
    def test_observations_timeline(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_observations_timeline

        ids = _seed_observations(schema_conn, 5)
        mid = ids[2]
        result = handle_observations_timeline(schema_conn, {"id": str(mid)})
        assert "before" in result
        assert "after" in result
        assert "anchor" in result
        assert result["anchor"]["id"] == mid


class TestObservationsRoutesRegistered:
    def test_observations_routes_registered(self) -> None:
        from mpga.web.router import route

        assert route("/api/observations") is not None
        assert route("/api/observations/123") is not None
        assert route("/api/observations/search") is not None
        assert route("/api/observations/timeline") is not None
