"""T012 — `mpga config` bare command should exit 0 and show help.

The bug: config_cmd is a @click.group with no invoke_without_command=True,
so running it with no subcommand exits with code 2 ("Missing command").
Fix: add invoke_without_command=True and print help when invoked bare.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner


def _write_config(root: Path) -> None:
    (root / "mpga.config.json").write_text(json.dumps({
        "version": "1.0.0",
        "project": {"name": "test", "languages": ["python"], "entryPoints": [], "ignore": []},
    }))


class TestConfigBare:
    """config bare command must exit 0 and show useful output."""

    def test_config_bare_exits_zero(self, tmp_path: Path, monkeypatch):
        """mpga config (no subcommand) exits with code 0."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)

        from mpga.commands.config_cmd import config_cmd

        runner = CliRunner()
        result = runner.invoke(config_cmd, [])
        assert result.exit_code == 0, (
            f"Expected exit code 0, got {result.exit_code}.\nOutput:\n{result.output}"
        )

    def test_config_bare_shows_useful_output(self, tmp_path: Path, monkeypatch):
        """mpga config (no subcommand) shows help or configuration summary."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)

        from mpga.commands.config_cmd import config_cmd

        runner = CliRunner()
        result = runner.invoke(config_cmd, [])
        assert result.exit_code == 0

        output_lower = result.output.lower()
        # Should show either help text or config values
        assert any(
            keyword in output_lower
            for keyword in ("config", "show", "set", "usage", "version", "project")
        ), (
            f"bare config should show useful output, got:\n{result.output}"
        )

    def test_config_show_subcommand_still_works(self, tmp_path: Path, monkeypatch):
        """config show still works after adding invoke_without_command."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)

        from mpga.commands.config_cmd import config_cmd

        runner = CliRunner()
        result = runner.invoke(config_cmd, ["show"])
        assert result.exit_code == 0, (
            f"config show should still work, got exit {result.exit_code}:\n{result.output}"
        )
