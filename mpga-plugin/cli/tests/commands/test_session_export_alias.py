"""T013 — `mpga session export` should be an alias for `mpga session handoff`.

The bug: the session group has no 'export' subcommand. Invoking
`mpga session export` exits 2 with "No such command 'export'".
Fix: add an 'export' subcommand (or alias) that calls the same handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


def _seed_db(root: Path) -> None:
    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()


class TestSessionExportAlias:
    """session export must be a working alias for session handoff."""

    def test_session_export_exits_zero(self, tmp_path: Path, monkeypatch):
        """mpga session export exits with code 0, not 2."""
        monkeypatch.chdir(tmp_path)
        _seed_db(tmp_path)
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ["export"])
        assert result.exit_code == 0, (
            f"Expected exit code 0, got {result.exit_code}.\nOutput:\n{result.output}"
        )

    def test_session_export_produces_handoff_content(self, tmp_path: Path, monkeypatch):
        """mpga session export produces the same content as session handoff."""
        monkeypatch.chdir(tmp_path)
        _seed_db(tmp_path)
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()

        export_result = runner.invoke(session, ["export"])
        handoff_result = runner.invoke(session, ["handoff"])

        assert export_result.exit_code == 0
        assert handoff_result.exit_code == 0

        # Both should contain handoff-style content
        for keyword in ("Session Handoff", "Accomplished", "Next action"):
            assert keyword in export_result.output, (
                f"'session export' output missing '{keyword}':\n{export_result.output}"
            )

    def test_session_handoff_still_works(self, tmp_path: Path, monkeypatch):
        """session handoff still works after adding the export alias."""
        monkeypatch.chdir(tmp_path)
        _seed_db(tmp_path)
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ["handoff"])
        assert result.exit_code == 0, (
            f"session handoff should still work, got exit {result.exit_code}:\n{result.output}"
        )
