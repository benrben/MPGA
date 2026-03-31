"""Tests for the MPGA SPA/API server."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


def _seed_db(db_path: Path) -> None:
    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        conn.execute(
            "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("T001", "Serve task", "Body", "todo", "medium", "2026-01-01", "2026-01-01"),
        )
        conn.commit()
    finally:
        conn.close()


class TestServe:
    def test_serves_spa_index_html(self, tmp_path: Path):
        db_path = tmp_path / ".mpga" / "mpga.db"
        _seed_db(db_path)

        from mpga.commands.serve import create_spa_server, _STATIC_DIR

        server = create_spa_server(db_path=str(db_path), static_dir=str(_STATIC_DIR), port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = urlopen(f"http://127.0.0.1:{server.server_address[1]}/")
            body = response.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert response.status == 200
        assert "Project Dashboard" in body
        assert "MPGA" in body

    def test_falls_back_to_index_for_spa_routes(self, tmp_path: Path):
        db_path = tmp_path / ".mpga" / "mpga.db"
        _seed_db(db_path)

        from mpga.commands.serve import create_spa_server, _STATIC_DIR

        server = create_spa_server(db_path=str(db_path), static_dir=str(_STATIC_DIR), port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = urlopen(f"http://127.0.0.1:{server.server_address[1]}/tasks")
            body = response.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert response.status == 200
        assert "Project Dashboard" in body

    def test_spa_shell_includes_core_and_secondary_pages(self, tmp_path: Path):
        db_path = tmp_path / ".mpga" / "mpga.db"
        _seed_db(db_path)

        from mpga.commands.serve import create_spa_server, _STATIC_DIR

        server = create_spa_server(db_path=str(db_path), static_dir=str(_STATIC_DIR), port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = urlopen(f"http://127.0.0.1:{server.server_address[1]}/")
            body = response.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        for label in (
            "Dashboard", "Board", "Tasks", "Scopes", "Search",
            "Evidence", "Milestones", "Sessions", "Graph",
            "Design System", "Decisions", "Develop", "Metrics", "Health",
        ):
            assert label in body

    def test_keeps_api_routes_json(self, tmp_path: Path):
        db_path = tmp_path / ".mpga" / "mpga.db"
        _seed_db(db_path)

        from mpga.commands.serve import create_spa_server, _STATIC_DIR

        server = create_spa_server(db_path=str(db_path), static_dir=str(_STATIC_DIR), port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = urlopen(f"http://127.0.0.1:{server.server_address[1]}/api/tasks")
            body = json.loads(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert response.status == 200
        assert body["tasks"][0]["id"] == "T001"
