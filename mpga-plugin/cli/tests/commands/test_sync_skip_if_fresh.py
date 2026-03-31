"""Tests for `mpga sync --skip-if-fresh N` flag.

Acceptance criteria:
1. `mpga sync --skip-if-fresh 10` skips sync if last sync was <10 minutes ago
2. When skipped, prints "Sync skipped: DB is fresh (last sync N minutes ago)"
3. Exit code 0 when skipped
4. `mpga sync` without flag runs normally (no regression)
5. `mpga sync --skip-if-fresh 0` always runs (0 means never skip)
6. Tests cover: flag exists, skip when fresh, run when stale, run without flag
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import write_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_mpga_structure(root: Path) -> None:
    """Create .mpga/mpga.db and MPGA/scopes/ directory."""
    import sqlite3
    from mpga.db.schema import create_schema

    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()
    (root / "MPGA" / "scopes").mkdir(parents=True, exist_ok=True)


def write_config(root: Path) -> None:
    """Write a minimal mpga.config.json."""
    config = {
        "version": "1.0.0",
        "project": {
            "name": "test-project",
            "languages": ["python"],
            "entryPoints": [],
            "ignore": ["node_modules", "dist", ".git", "MPGA/"],
        },
    }
    write_file(root, "mpga.config.json", json.dumps(config, indent=2))


def write_sample_py_files(root: Path) -> None:
    """Write sample Python source files."""
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.py").write_text("def main():\n    print('hello')\n")
    (src_dir / "utils.py").write_text("def add(a, b):\n    return a + b\n")


def write_last_sync(root: Path, age_seconds: float) -> None:
    """Write a last_sync timestamp that is `age_seconds` old."""
    import datetime

    ts = time.time() - age_seconds
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    last_sync_path = root / ".mpga" / "last_sync"
    last_sync_path.write_text(dt.isoformat())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSyncSkipIfFresh:
    """Tests for the --skip-if-fresh flag on `mpga sync`."""

    def test_flag_exists_and_accepts_integer(self, tmp_path: Path, monkeypatch):
        """--skip-if-fresh flag is accepted without errors (before any sync)."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        # Pass --skip-if-fresh 0 (never skip) — should run normally, exit 0
        result = runner.invoke(sync_cmd, ["--skip-if-fresh", "0"])
        assert result.exit_code == 0, result.output

    def test_skips_when_fresh(self, tmp_path: Path, monkeypatch):
        """sync --skip-if-fresh 10 skips when last sync was <10 minutes ago."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        # Simulate a sync that happened 2 minutes ago
        write_last_sync(tmp_path, age_seconds=120)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, ["--skip-if-fresh", "10"])
        assert result.exit_code == 0, result.output
        assert "Sync skipped" in result.output
        assert "fresh" in result.output.lower()

    def test_skip_message_includes_elapsed_minutes(self, tmp_path: Path, monkeypatch):
        """Skip message mentions how many minutes ago the last sync was."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        # 3 minutes ago
        write_last_sync(tmp_path, age_seconds=180)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, ["--skip-if-fresh", "10"])
        assert result.exit_code == 0, result.output
        # Message should contain the elapsed minutes (3)
        assert "3" in result.output

    def test_runs_when_stale(self, tmp_path: Path, monkeypatch):
        """sync --skip-if-fresh 5 runs normally when last sync was >5 minutes ago."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        # 10 minutes ago — stale relative to threshold of 5
        write_last_sync(tmp_path, age_seconds=600)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, ["--skip-if-fresh", "5"])
        assert result.exit_code == 0, result.output
        assert "Sync skipped" not in result.output
        assert "COMPLETE" in result.output or "Sync" in result.output

    def test_runs_without_flag(self, tmp_path: Path, monkeypatch):
        """sync without --skip-if-fresh runs normally regardless of last_sync."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        # Even a very fresh sync (10 seconds ago) should NOT skip without the flag
        write_last_sync(tmp_path, age_seconds=10)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output
        assert "Sync skipped" not in result.output

    def test_skip_if_fresh_zero_always_runs(self, tmp_path: Path, monkeypatch):
        """sync --skip-if-fresh 0 always runs even when DB is very fresh."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        # Just synced 5 seconds ago
        write_last_sync(tmp_path, age_seconds=5)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, ["--skip-if-fresh", "0"])
        assert result.exit_code == 0, result.output
        assert "Sync skipped" not in result.output
        assert "COMPLETE" in result.output or "Sync" in result.output

    def test_runs_when_no_last_sync_file(self, tmp_path: Path, monkeypatch):
        """sync --skip-if-fresh N runs normally when no last_sync file exists."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        # No last_sync file written at all
        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, ["--skip-if-fresh", "10"])
        assert result.exit_code == 0, result.output
        assert "Sync skipped" not in result.output

    def test_sync_writes_last_sync_file(self, tmp_path: Path, monkeypatch):
        """A successful sync writes .mpga/last_sync timestamp file."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        create_mpga_structure(tmp_path)
        write_sample_py_files(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output

        last_sync_path = tmp_path / ".mpga" / "last_sync"
        assert last_sync_path.exists(), "sync should write .mpga/last_sync on success"

    def test_is_fresh_helper_with_fresh_timestamp(self, tmp_path: Path):
        """_is_db_fresh returns True when last_sync is within threshold."""
        from mpga.commands.sync import _is_db_fresh

        last_sync_path = tmp_path / ".mpga" / "last_sync"
        last_sync_path.parent.mkdir(parents=True, exist_ok=True)
        write_last_sync(tmp_path, age_seconds=60)  # 1 minute ago

        assert _is_db_fresh(last_sync_path, threshold_minutes=5) is True

    def test_is_fresh_helper_with_stale_timestamp(self, tmp_path: Path):
        """_is_db_fresh returns False when last_sync is older than threshold."""
        from mpga.commands.sync import _is_db_fresh

        last_sync_path = tmp_path / ".mpga" / "last_sync"
        last_sync_path.parent.mkdir(parents=True, exist_ok=True)
        write_last_sync(tmp_path, age_seconds=600)  # 10 minutes ago

        assert _is_db_fresh(last_sync_path, threshold_minutes=5) is False

    def test_is_fresh_helper_when_file_missing(self, tmp_path: Path):
        """_is_db_fresh returns False when last_sync file does not exist."""
        from mpga.commands.sync import _is_db_fresh

        last_sync_path = tmp_path / ".mpga" / "last_sync"
        assert not last_sync_path.exists()

        assert _is_db_fresh(last_sync_path, threshold_minutes=10) is False

    def test_is_fresh_helper_threshold_zero_never_fresh(self, tmp_path: Path):
        """_is_db_fresh always returns False when threshold is 0."""
        from mpga.commands.sync import _is_db_fresh

        last_sync_path = tmp_path / ".mpga" / "last_sync"
        last_sync_path.parent.mkdir(parents=True, exist_ok=True)
        write_last_sync(tmp_path, age_seconds=1)  # 1 second ago

        assert _is_db_fresh(last_sync_path, threshold_minutes=0) is False
