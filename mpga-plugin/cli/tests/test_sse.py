"""Tests for T019 — SSE endpoint at /api/stream."""

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


class TestSSERoute:
    def test_stream_route_registered(self) -> None:
        from mpga.web.router import route

        result = route("/api/stream")
        assert result is not None, "/api/stream must be a registered route"
        handler_name, _params = result
        assert handler_name == "stream"

    def test_sse_content_type(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_stream

        result = handle_stream(schema_conn, {})
        assert result["content_type"] == "text/event-stream"

    def test_sse_returns_recent_observations(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_stream

        schema_conn.execute(
            "INSERT INTO observations (title, type, narrative, created_at) "
            "VALUES ('test obs', 'tool_output', 'narrative text', datetime('now'))"
        )
        schema_conn.commit()

        result = handle_stream(schema_conn, {})
        body = result["body"]
        assert "test obs" in body

    def test_sse_retry_hint(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_stream

        result = handle_stream(schema_conn, {})
        body = result["body"]
        assert "retry:" in body

    def test_sse_event_format(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_stream

        schema_conn.execute(
            "INSERT INTO observations (title, type, narrative, created_at) "
            "VALUES ('fmt obs', 'tool_output', 'some narrative', datetime('now'))"
        )
        schema_conn.commit()

        result = handle_stream(schema_conn, {})
        body = result["body"]
        for line in body.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            assert (
                line.startswith("data:") or
                line.startswith("event:") or
                line.startswith("retry:") or
                line.startswith("id:")
            ), f"Non-SSE line found: {line!r}"

        data_lines = [l for l in body.split("\n") if l.startswith("data:")]
        assert len(data_lines) >= 1
        payload = json.loads(data_lines[0].split("data:", 1)[1].strip())
        assert "title" in payload

    def test_sse_empty_when_no_observations(self, schema_conn: sqlite3.Connection) -> None:
        from mpga.web.api import handle_stream

        result = handle_stream(schema_conn, {})
        body = result["body"]
        data_lines = [l for l in body.split("\n") if l.startswith("data:")]
        assert len(data_lines) == 0
