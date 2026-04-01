"""Tests for T017: mpga scout cache check/mark CLI commands.

Coverage checklist for: T017 — Implement `mpga scout cache check/mark` CLI commands
Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:277-281 — scout_cache table
          [E] mpga-plugin/cli/src/mpga/cli.py:53-100       — _COMMANDS dict pattern
          [E] mpga-plugin/cli/src/mpga/commands/board_cmd.py:15-17 — nested group pattern

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: `mpga scout cache check <scope>` exits 0 when scope marked within 5 min
          → TestScoutCacheCmdCheckFresh.test_check_fresh_scope_exits_zero
[x] AC2: `mpga scout cache check <scope>` exits 1 when scope not in cache or stale
          → TestScoutCacheCmdCheckMissing.test_check_missing_scope_exits_one
          → TestScoutCacheCmdCheckStale.test_check_stale_scope_exits_one
[x] AC3: `mpga scout cache mark <scope>` inserts/updates scope with current UTC timestamp
          → TestScoutCacheCmdMark.test_mark_scope_inserts_row
[x] AC4: `mpga scout cache mark <scope>` is idempotent
          → TestScoutCacheCmdMarkIdempotent.test_mark_twice_still_exits_zero_on_check
[x] AC5: `scout` command (or `scout cache` group) is registered in _COMMANDS in cli.py
          → TestScoutRegisteredInCLI.test_scout_key_exists_in_commands_registry

Untested branches / edge cases:
- [ ] scope name with slashes or special characters
- [ ] concurrent mark calls (race condition)
- [ ] summary field stored alongside scouted_at
- [ ] UTC vs local timezone correctness of stored timestamp
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_db(tmp_path: Path) -> sqlite3.Connection:
    """Return a SQLite connection with the full MPGA schema applied."""
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    return conn


def _db_path(tmp_path: Path) -> Path:
    """Return the path used by _make_db so Click commands can find it."""
    return tmp_path / "test.db"


# ===========================================================================
# TPP step 1 (null/degenerate): module is importable and exposes callables
# Evidence: [E] mpga-plugin/cli/src/mpga/commands/scout.py
# ===========================================================================


class TestScoutCacheModuleImportable:
    """The scout_cache command module must exist and expose the expected callables.

    This is the most degenerate test — no filesystem, no DB, just an import.
    """

    def test_scout_cache_check_is_importable_and_callable(self):
        """scout_cache_check is importable from mpga.commands.scout and is callable."""
        # Arrange / Act — import only
        from mpga.commands.scout import scout_cache_check  # noqa: F401

        # Assert
        assert callable(scout_cache_check)

    def test_scout_cache_mark_is_importable_and_callable(self):
        """scout_cache_mark is importable from mpga.commands.scout and is callable."""
        from mpga.commands.scout import scout_cache_mark  # noqa: F401

        assert callable(scout_cache_mark)


# ===========================================================================
# TPP step 2 (constant): check on empty DB returns exit code 1 (not cached)
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:277-281
# ===========================================================================


class TestScoutCacheCmdCheckMissing:
    """AC2: check on a scope that has never been marked exits 1.

    This is the constant-result case — the DB is empty, so the answer is
    always 'not cached'.
    """

    def test_check_missing_scope_exits_one(self, tmp_path: Path):
        """scout cache check on an empty DB exits with code 1."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        _make_db(tmp_path)
        runner = CliRunner()

        # Act
        result = runner.invoke(
            cache_group,
            ["check", "auth", "--db", str(_db_path(tmp_path))],
        )

        # Assert
        assert result.exit_code == 1, (
            f"Expected exit code 1 for uncached scope, got {result.exit_code}. "
            f"Output: {result.output}"
        )


# ===========================================================================
# TPP step 3 (variable): mark then check within 5 min returns exit code 0
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:277-281
# ===========================================================================


class TestScoutCacheCmdCheckFresh:
    """AC1: mark a scope, immediately check it — exits 0 (within 5-min window)."""

    def test_check_fresh_scope_exits_zero(self, tmp_path: Path):
        """scout cache check exits 0 when scope was marked moments ago."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        _make_db(tmp_path)
        runner = CliRunner()
        db = str(_db_path(tmp_path))

        # Act — mark then immediately check
        mark_result = runner.invoke(cache_group, ["mark", "auth", "--db", db])
        check_result = runner.invoke(cache_group, ["check", "auth", "--db", db])

        # Assert
        assert mark_result.exit_code == 0, (
            f"mark should exit 0, got {mark_result.exit_code}. Output: {mark_result.output}"
        )
        assert check_result.exit_code == 0, (
            f"check after fresh mark should exit 0, got {check_result.exit_code}. "
            f"Output: {check_result.output}"
        )


# ===========================================================================
# TPP step 4 (selection): mark then check after 5 min returns exit code 1
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:277-281
# ===========================================================================


class TestScoutCacheCmdCheckStale:
    """AC2 (stale branch): scope marked more than 5 minutes ago exits 1.

    Uses monkeypatch to plant a stale timestamp directly in the DB.
    """

    def test_check_stale_scope_exits_one(self, tmp_path: Path):
        """scout cache check exits 1 when the stored scouted_at is 6 minutes old."""
        # Arrange — insert a row with a timestamp 6 minutes in the past
        conn = _make_db(tmp_path)
        stale_ts = datetime(2026, 3, 31, 15, 54, 0, tzinfo=timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO scout_cache (scope, scouted_at) VALUES (?, ?)",
            ("auth", stale_ts),
        )
        conn.commit()
        conn.close()

        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        runner = CliRunner()

        # Act — check with a "current time" that is 6 min after the stale_ts,
        # achieved by monkeypatching datetime inside the scout module
        import unittest.mock as mock

        fake_now = datetime(2026, 3, 31, 16, 0, 0, tzinfo=timezone.utc)
        with mock.patch("mpga.commands.scout.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.fromisoformat = datetime.fromisoformat  # keep parsing intact
            result = runner.invoke(
                cache_group,
                ["check", "auth", "--db", str(_db_path(tmp_path))],
            )

        # Assert
        assert result.exit_code == 1, (
            f"Expected exit code 1 for stale scope, got {result.exit_code}. "
            f"Output: {result.output}"
        )


# ===========================================================================
# TPP step 5 (iteration / idempotent): mark twice, second check still exits 0
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:277-281 — scope TEXT PRIMARY KEY
# ===========================================================================


class TestScoutCacheCmdMarkIdempotent:
    """AC4: calling mark twice for the same scope does not error and updates timestamp.

    The scout_cache table uses scope as PRIMARY KEY, so a second mark must
    upsert (INSERT OR REPLACE / ON CONFLICT DO UPDATE), not fail.
    """

    def test_mark_twice_does_not_raise(self, tmp_path: Path):
        """Calling scout cache mark twice for the same scope both exit 0."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        _make_db(tmp_path)
        runner = CliRunner()
        db = str(_db_path(tmp_path))

        # Act — mark twice
        first = runner.invoke(cache_group, ["mark", "auth", "--db", db])
        second = runner.invoke(cache_group, ["mark", "auth", "--db", db])

        # Assert — both invocations succeed
        assert first.exit_code == 0, f"First mark failed: {first.output}"
        assert second.exit_code == 0, f"Second mark failed: {second.output}"

    def test_mark_twice_second_check_still_exits_zero(self, tmp_path: Path):
        """After marking twice, check still returns 0 (timestamp was updated)."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        _make_db(tmp_path)
        runner = CliRunner()
        db = str(_db_path(tmp_path))

        # Act
        runner.invoke(cache_group, ["mark", "auth", "--db", db])
        runner.invoke(cache_group, ["mark", "auth", "--db", db])
        check_result = runner.invoke(cache_group, ["check", "auth", "--db", db])

        # Assert
        assert check_result.exit_code == 0, (
            f"check after double-mark should exit 0, got {check_result.exit_code}. "
            f"Output: {check_result.output}"
        )


# ===========================================================================
# TPP: mark actually persists the row with a scouted_at timestamp (AC3)
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:277-281
# ===========================================================================


class TestScoutCacheCmdMark:
    """AC3: mark inserts a row with the scope and a non-empty scouted_at timestamp."""

    def test_mark_scope_inserts_row(self, tmp_path: Path):
        """scout cache mark inserts a row into scout_cache with scope and scouted_at."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        conn = _make_db(tmp_path)
        conn.close()
        runner = CliRunner()

        # Act
        result = runner.invoke(
            cache_group,
            ["mark", "auth", "--db", str(_db_path(tmp_path))],
        )

        # Assert — row present in the DB
        assert result.exit_code == 0, f"mark exited {result.exit_code}: {result.output}"

        conn2 = sqlite3.connect(str(_db_path(tmp_path)))
        row = conn2.execute(
            "SELECT scope, scouted_at FROM scout_cache WHERE scope = ?", ("auth",)
        ).fetchone()
        conn2.close()

        assert row is not None, "Expected a row in scout_cache after mark"
        assert row[0] == "auth", f"Expected scope='auth', got {row[0]!r}"
        assert row[1], "scouted_at must be non-empty"

    def test_mark_stores_utc_iso_timestamp(self, tmp_path: Path):
        """The scouted_at value stored by mark is a valid ISO 8601 UTC timestamp."""
        # Arrange
        from click.testing import CliRunner
        from mpga.commands.scout import cache_group

        _make_db(tmp_path)
        runner = CliRunner()

        # Act
        runner.invoke(cache_group, ["mark", "metrics", "--db", str(_db_path(tmp_path))])

        # Assert — value parses as datetime and is UTC (ends with +00:00 or 'Z')
        conn = sqlite3.connect(str(_db_path(tmp_path)))
        row = conn.execute(
            "SELECT scouted_at FROM scout_cache WHERE scope = ?", ("metrics",)
        ).fetchone()
        conn.close()

        assert row is not None
        ts_str = row[0]
        # Should parse without error as ISO 8601
        parsed = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, "scouted_at must be timezone-aware (UTC)"


# ===========================================================================
# TPP step 1 (degenerate): 'scout' key in _COMMANDS (AC5)
# Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:53-100
# ===========================================================================


class TestScoutRegisteredInCLI:
    """AC5: 'scout' must appear in _COMMANDS in cli.py so `mpga scout` works.

    Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:53-100
    """

    def test_scout_key_exists_in_commands_registry(self):
        """'scout' is present in the _COMMANDS dict in mpga.cli."""
        # Arrange / Act
        from mpga.cli import _COMMANDS

        # Assert
        assert "scout" in _COMMANDS, (
            "'scout' not found in _COMMANDS — add the entry to cli.py"
        )

    def test_scout_command_maps_to_scout_module(self):
        """The 'scout' entry in _COMMANDS points to mpga.commands.scout."""
        # Arrange
        from mpga.cli import _COMMANDS

        # Act
        module_path, _attr = _COMMANDS.get("scout", ("", ""))

        # Assert
        assert module_path == "mpga.commands.scout", (
            f"Expected module_path 'mpga.commands.scout', got {module_path!r}"
        )

    def test_scout_cmd_is_a_click_group(self):
        """The scout command object is a Click Group (supports subcommands)."""
        # Arrange
        import click

        # Act — will ImportError until green-dev creates the module
        from mpga.commands.scout import scout  # noqa: F401

        # Assert
        assert isinstance(scout, click.Group), (
            "scout must be a click.Group so that 'cache' can be a subgroup"
        )
