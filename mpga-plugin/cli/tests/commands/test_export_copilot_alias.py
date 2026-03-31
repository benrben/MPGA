"""Tests for --copilot alias in the export command (T017)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


def create_mpga_db(root: Path) -> None:
    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    from mpga.db.schema import create_schema
    conn = sqlite3.connect(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()


def write_config(root: Path) -> None:
    cfg = {
        "version": "1.0.0",
        "project": {"name": "test-project", "languages": ["python"], "ignore": []},
    }
    (root / "mpga.config.json").write_text(json.dumps(cfg))


# ---------------------------------------------------------------------------
# Tests: --copilot alias
# ---------------------------------------------------------------------------

class TestExportCopilotAlias:
    """--copilot is a recognised alias for --codex in the export command."""

    def test_copilot_flag_exists_and_exits_zero(self, tmp_path: Path, monkeypatch):
        """mpga export --copilot exits 0 (not 'No such option')."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        from mpga.commands.export_cmd import export_cmd

        runner = CliRunner()
        with patch("mpga.commands.export_cmd.export_codex") as mock_codex:
            result = runner.invoke(export_cmd, ["--copilot"])

        # Must NOT be a UsageError about an unknown option
        assert "No such option" not in (result.output or ""), (
            "--copilot should be a recognised option, not trigger 'No such option'"
        )
        assert result.exit_code == 0

    def test_copilot_calls_same_export_as_codex(self, tmp_path: Path, monkeypatch):
        """--copilot triggers the same export_codex call as --codex."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        from mpga.commands.export_cmd import export_cmd

        runner = CliRunner()

        # Invoke with --codex, capture export_codex call args
        with patch("mpga.commands.export_cmd.export_codex") as mock_codex:
            runner.invoke(export_cmd, ["--codex"])
            codex_call_count = mock_codex.call_count

        # Invoke with --copilot, capture export_codex call args
        with patch("mpga.commands.export_cmd.export_codex") as mock_copilot:
            result = runner.invoke(export_cmd, ["--copilot"])
            copilot_call_count = mock_copilot.call_count

        assert codex_call_count == 1, "--codex should call export_codex once"
        assert copilot_call_count == 1, "--copilot should also call export_codex once"

    def test_copilot_prints_deprecation_or_success(self, tmp_path: Path, monkeypatch):
        """--copilot prints a success or deprecation message (not a bare error)."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        from mpga.commands.export_cmd import export_cmd

        runner = CliRunner()
        with patch("mpga.commands.export_cmd.export_codex"):
            result = runner.invoke(export_cmd, ["--copilot"])

        # Should not print an uncaught traceback
        assert "Traceback" not in (result.output or "")
        assert result.exit_code == 0
