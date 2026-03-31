"""T011 — `mpga metrics list` should exit 0 and list metric names.

The bug: metrics is a single @click.command (not a group), so `mpga metrics list`
passes 'list' as an unexpected extra argument and exits with code 2.
Fix: convert metrics to a @click.group with a `list` subcommand.
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


class TestMetricsList:
    """metrics list subcommand — must exist and exit 0."""

    def test_metrics_list_exits_zero(self, tmp_path: Path, monkeypatch):
        """mpga metrics list exits with code 0, not 2."""
        _seed_db(tmp_path)
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_group

        runner = CliRunner()
        result = runner.invoke(metrics_group, ["list"])
        assert result.exit_code == 0, (
            f"Expected exit code 0, got {result.exit_code}.\nOutput:\n{result.output}"
        )

    def test_metrics_list_shows_metric_names(self, tmp_path: Path, monkeypatch):
        """mpga metrics list shows available metric categories."""
        _seed_db(tmp_path)
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_group

        runner = CliRunner()
        result = runner.invoke(metrics_group, ["list"])
        assert result.exit_code == 0

        output_lower = result.output.lower()
        # Should contain recognisable metric names
        assert any(
            keyword in output_lower
            for keyword in ("total", "done", "evidence", "tdd", "coverage")
        ), (
            f"metrics list output should contain metric names, got:\n{result.output}"
        )

    def test_metrics_bare_still_shows_dashboard(self, tmp_path: Path, monkeypatch):
        """mpga metrics (no subcommand) still shows the dashboard."""
        _seed_db(tmp_path)
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_group

        runner = CliRunner()
        # Invoke with no subcommand — should show metrics dashboard
        result = runner.invoke(metrics_group, [])
        assert result.exit_code == 0, (
            f"bare metrics command should still work, got exit {result.exit_code}:\n{result.output}"
        )
