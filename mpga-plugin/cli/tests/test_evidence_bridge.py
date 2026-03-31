"""Tests for the observation → evidence bridge (mpga memory link)."""
from __future__ import annotations

import sqlite3
from contextlib import closing

from click.testing import CliRunner

from mpga.commands.memory import memory
from mpga.db.schema import create_schema


def _setup_db(tmp_path):
    """Create a fresh in-memory-style DB in tmp_path and seed an observation."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db_path))
    create_schema(conn)
    conn.execute(
        "INSERT INTO observations"
        "  (session_id, scope_id, title, type, narrative, facts, concepts,"
        "   files_read, files_modified, tool_name, priority, evidence_links,"
        "   data_hash, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
        (
            "sess-1", "scope-a", "Auth refactor insight", "insight",
            "Discovered that JWT rotation is missing", '["needs rotation"]',
            '["jwt","auth"]', "src/auth.ts", "src/auth.ts",
            "read_file", 2, "", "abc123",
        ),
    )
    conn.commit()
    return conn, db_path


def test_memory_link_command_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(memory, ["link", "--help"])
    assert result.exit_code == 0
    assert "link" in result.output.lower()


def test_link_creates_evidence(tmp_path, monkeypatch) -> None:
    conn, db_path = _setup_db(tmp_path)
    monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(memory, ["link", "1"])
    assert result.exit_code == 0, result.output

    with closing(sqlite3.connect(str(db_path))) as c:
        row = c.execute("SELECT COUNT(*) FROM evidence WHERE type = 'observation'").fetchone()
        assert row[0] >= 1


def test_link_evidence_type_observation(tmp_path, monkeypatch) -> None:
    conn, db_path = _setup_db(tmp_path)
    monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)

    runner = CliRunner()
    runner.invoke(memory, ["link", "1"])

    with closing(sqlite3.connect(str(db_path))) as c:
        row = c.execute("SELECT type FROM evidence ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert row[0] == "observation"


def test_link_missing_observation(tmp_path, monkeypatch) -> None:
    conn, db_path = _setup_db(tmp_path)
    monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(memory, ["link", "9999"])
    assert "not found" in result.output.lower()


def test_link_includes_observation_data(tmp_path, monkeypatch) -> None:
    conn, db_path = _setup_db(tmp_path)
    monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)

    runner = CliRunner()
    runner.invoke(memory, ["link", "1"])

    with closing(sqlite3.connect(str(db_path))) as c:
        row = c.execute(
            "SELECT description FROM evidence ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        desc = row[0]
        assert "Auth refactor insight" in desc
        assert "JWT rotation" in desc
