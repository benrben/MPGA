"""Tests for session start/event SQLite logging."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner


class TestSessionEvents:
    def test_session_start_creates_active_session(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ["start", "--model", "gpt-5"])
        assert result.exit_code == 0

        conn = sqlite3.connect(tmp_path / ".mpga" / "mpga.db")
        try:
            row = conn.execute("SELECT status, model FROM sessions").fetchone()
        finally:
            conn.close()

        assert row == ("active", "gpt-5")

    def test_session_event_records_event_row(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(
            session,
            ["event", "pre-read", "--action", "Read", "--input-summary", "MPGA/INDEX.md"],
        )
        assert result.exit_code == 0

        conn = sqlite3.connect(tmp_path / ".mpga" / "mpga.db")
        try:
            row = conn.execute(
                "SELECT event_type, action, input_summary FROM events"
            ).fetchone()
        finally:
            conn.close()

        assert row == ("pre-read", "Read", "MPGA/INDEX.md")
