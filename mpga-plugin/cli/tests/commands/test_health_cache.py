"""Tests for health command link-validation cache (T015)."""

from __future__ import annotations

import json
import sqlite3
import time
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
# Tests: health cache
# ---------------------------------------------------------------------------

class TestHealthCache:
    """health command caches link-validation results."""

    def test_health_cache_file_written_after_run(self, tmp_path: Path, monkeypatch):
        """Running health writes a cache file to .mpga/health_cache.json."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        with patch("mpga.commands.health.run_drift_check") as mock_drift:
            mock_drift.return_value = MagicMock(
                overall_health_pct=90,
                valid_links=9,
                total_links=10,
                ci_pass=True,
                scopes=[],
            )
            result = runner.invoke(health_cmd, ["--json"])

        assert result.exit_code == 0
        cache_path = tmp_path / ".mpga" / "health_cache.json"
        assert cache_path.exists(), "health_cache.json should be written after running health"

    def test_health_cache_contains_timestamp(self, tmp_path: Path, monkeypatch):
        """The cache file contains a 'timestamp' field."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        with patch("mpga.commands.health.run_drift_check") as mock_drift:
            mock_drift.return_value = MagicMock(
                overall_health_pct=80,
                valid_links=8,
                total_links=10,
                ci_pass=True,
                scopes=[],
            )
            runner.invoke(health_cmd, ["--json"])

        cache_path = tmp_path / ".mpga" / "health_cache.json"
        data = json.loads(cache_path.read_text())
        assert "timestamp" in data, "cache must contain a 'timestamp' field"
        assert isinstance(data["timestamp"], (int, float)), "timestamp must be numeric (epoch seconds)"

    def test_health_cache_used_on_second_run_skips_drift(self, tmp_path: Path, monkeypatch):
        """A fresh cache (< TTL) prevents run_drift_check from being called again."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        # Pre-populate a fresh cache
        cache_path = tmp_path / ".mpga" / "health_cache.json"
        fresh_data = {
            "timestamp": time.time(),  # right now → definitely fresh
            "overall_health_pct": 75,
            "valid_links": 75,
            "total_links": 100,
            "ci_pass": True,
            "scopes": [],
        }
        cache_path.write_text(json.dumps(fresh_data))

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        with patch("mpga.commands.health.run_drift_check") as mock_drift:
            mock_drift.return_value = MagicMock(
                overall_health_pct=99,
                valid_links=99,
                total_links=100,
                ci_pass=True,
                scopes=[],
            )
            result = runner.invoke(health_cmd, ["--json"])

        assert result.exit_code == 0
        # drift check should NOT have been called because cache was fresh
        mock_drift.assert_not_called()

    def test_health_cache_ttl_is_five_minutes(self, tmp_path: Path, monkeypatch):
        """A stale cache (> 5 min old) causes run_drift_check to run again."""
        monkeypatch.chdir(tmp_path)
        create_mpga_db(tmp_path)
        write_config(tmp_path)

        # Pre-populate a STALE cache (6 minutes old)
        cache_path = tmp_path / ".mpga" / "health_cache.json"
        stale_data = {
            "timestamp": time.time() - 360,  # 6 minutes ago → stale
            "overall_health_pct": 50,
            "valid_links": 50,
            "total_links": 100,
            "ci_pass": False,
            "scopes": [],
        }
        cache_path.write_text(json.dumps(stale_data))

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        with patch("mpga.commands.health.run_drift_check") as mock_drift:
            mock_drift.return_value = MagicMock(
                overall_health_pct=90,
                valid_links=90,
                total_links=100,
                ci_pass=True,
                scopes=[],
            )
            result = runner.invoke(health_cmd, ["--json"])

        assert result.exit_code == 0
        # drift check SHOULD have been called because cache was stale
        mock_drift.assert_called_once()

    def test_health_cache_ttl_configurable_via_constant(self, tmp_path: Path, monkeypatch):
        """HEALTH_CACHE_TTL_SECONDS constant exists and equals 300 (5 minutes)."""
        from mpga.commands import health as health_mod
        assert hasattr(health_mod, "HEALTH_CACHE_TTL_SECONDS"), (
            "health module must expose HEALTH_CACHE_TTL_SECONDS constant"
        )
        assert health_mod.HEALTH_CACHE_TTL_SECONDS == 300
