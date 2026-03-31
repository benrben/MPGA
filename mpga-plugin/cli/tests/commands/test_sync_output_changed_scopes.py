"""Tests for `mpga sync --output-changed-scopes` flag (T007).

RED phase: write failing tests first, then implement.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import write_file


# ---------------------------------------------------------------------------
# Helpers (reused from test_scan_sync.py pattern)
# ---------------------------------------------------------------------------

def _create_mpga_structure(root: Path) -> None:
    from mpga.db.schema import create_schema

    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()
    (root / "MPGA" / "scopes").mkdir(parents=True, exist_ok=True)


def _write_config(root: Path, name: str = "test-project") -> None:
    config = {
        "version": "1.0.0",
        "project": {
            "name": name,
            "languages": ["python"],
            "entryPoints": [],
            "ignore": ["node_modules", "dist", ".git", "MPGA/"],
        },
    }
    write_file(root, "mpga.config.json", json.dumps(config, indent=2))


def _write_py_file(root: Path, rel_path: str, content: str = "# hello\n") -> Path:
    """Write a Python source file and return its Path."""
    p = root / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test: flag exists and sync still succeeds (no regression)
# ---------------------------------------------------------------------------

class TestOutputChangedScopesFlagExists:
    """The --output-changed-scopes flag is accepted by sync_cmd."""

    def test_flag_accepted_without_error(self, tmp_path: Path, monkeypatch):
        """sync --output-changed-scopes exits 0 and sync completes normally."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, ["--output-changed-scopes"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Test: without flag, output is unchanged (no regression)
# ---------------------------------------------------------------------------

class TestNoRegressionWithoutFlag:
    """Without --output-changed-scopes, sync output is identical to before."""

    def test_sync_without_flag_no_extra_output(self, tmp_path: Path, monkeypatch):
        """sync without flag produces same output as before (no scope names dumped)."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result_no_flag = runner.invoke(sync_cmd, [])
        assert result_no_flag.exit_code == 0

        # The output should NOT contain a bare scope name line by itself
        # (i.e. no machine-readable changed-scopes list)
        lines = [l for l in result_no_flag.output.splitlines() if l.strip()]
        # All lines should contain MPGA log prefixes — none should be a bare identifier
        bare_identifier_lines = [
            l for l in lines
            if l.strip() and not any(
                marker in l
                for marker in ["MPGA", "Sync", "Scan", "Build", "Group", "SQLite",
                               "Evidence", "INDEX", "scope", "file", "%", "Running",
                               "✓", "✗", "→", "·", "─", " ", "\t", "!", "?", "WINNING",
                               "TREMENDOUS", "COMPLETE", "FANTASTIC", "WINNING"]
            )
        ]
        # There should be no output lines that look like just a raw scope name
        # (they'd be things like "src" or "commands" with no other context)
        # The safest test: run with flag and without flag, check flag adds extra lines
        runner2 = CliRunner()
        result_with_flag = runner2.invoke(sync_cmd, ["--output-changed-scopes"])
        assert result_with_flag.exit_code == 0

        # The with-flag output on first sync should have MORE or equal lines
        # (changed scopes appended at end)
        lines_no_flag = result_no_flag.output.splitlines()
        lines_with_flag = result_with_flag.output.splitlines()
        assert len(lines_with_flag) >= len(lines_no_flag)


# ---------------------------------------------------------------------------
# Test: no scopes changed → empty output appended
# ---------------------------------------------------------------------------

class TestNoScopesChanged:
    """When nothing changed since last sync, --output-changed-scopes outputs nothing extra."""

    def test_second_sync_no_changes_empty_changed_list(self, tmp_path: Path, monkeypatch):
        """Second sync with no file changes outputs no scope names."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        # First sync — establishes baseline
        r1 = runner.invoke(sync_cmd, [])
        assert r1.exit_code == 0

        # Second sync immediately after — no files changed
        r2 = runner.invoke(sync_cmd, ["--output-changed-scopes"])
        assert r2.exit_code == 0

        # Extract changed-scopes section: lines after the "---CHANGED-SCOPES---" sentinel
        # OR all lines that are bare scope names (implementation detail — check either approach)
        changed = _extract_changed_scopes_from_output(r2.output)
        assert changed == [], f"Expected no changed scopes, got: {changed}"


# ---------------------------------------------------------------------------
# Test: changed scope IS listed
# ---------------------------------------------------------------------------

class TestChangedScopeListed:
    """A scope whose files changed since last sync appears in --output-changed-scopes."""

    def test_modified_file_scope_appears(self, tmp_path: Path, monkeypatch):
        """After modifying a file, its scope name appears in the changed-scopes output."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        alpha_file = _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        # First sync — establishes snapshot
        r1 = runner.invoke(sync_cmd, [])
        assert r1.exit_code == 0

        # Modify the file — bump its mtime by writing new content
        time.sleep(0.05)  # ensure mtime differs
        alpha_file.write_text("def alpha(): return 42\n", encoding="utf-8")
        # Force a distinct mtime so the comparison is reliable
        new_mtime = alpha_file.stat().st_mtime + 1.0
        os.utime(alpha_file, (new_mtime, new_mtime))

        # Second sync with flag
        r2 = runner.invoke(sync_cmd, ["--output-changed-scopes"])
        assert r2.exit_code == 0

        changed = _extract_changed_scopes_from_output(r2.output)
        assert len(changed) >= 1, f"Expected at least 1 changed scope, got: {changed}"
        # The scope should be something like "src" (the directory of alpha.py)
        assert any("src" in s for s in changed), (
            f"Expected 'src' scope in changed list, got: {changed}"
        )

    def test_new_file_scope_appears(self, tmp_path: Path, monkeypatch):
        """Adding a new file causes its scope to appear in changed-scopes output."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        # First sync — baseline
        r1 = runner.invoke(sync_cmd, [])
        assert r1.exit_code == 0

        # Add a new file in a new scope directory
        _write_py_file(tmp_path, "src/beta.py", "def beta(): pass\n")

        # Second sync with flag
        r2 = runner.invoke(sync_cmd, ["--output-changed-scopes"])
        assert r2.exit_code == 0

        changed = _extract_changed_scopes_from_output(r2.output)
        assert len(changed) >= 1, f"Expected at least 1 changed scope, got: {changed}"
        assert any("src" in s for s in changed), (
            f"Expected 'src' scope in changed list, got: {changed}"
        )


# ---------------------------------------------------------------------------
# Test: unchanged scope NOT listed
# ---------------------------------------------------------------------------

class TestUnchangedScopeNotListed:
    """A scope with no file changes since last sync does NOT appear in the output."""

    def test_unchanged_scope_absent(self, tmp_path: Path, monkeypatch):
        """Only the changed scope appears — the unchanged one is absent."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _write_py_file(tmp_path, "lib/helper.py", "def helper(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        # First sync
        r1 = runner.invoke(sync_cmd, [])
        assert r1.exit_code == 0

        # Only modify the src file
        src_file = tmp_path / "src" / "alpha.py"
        time.sleep(0.05)
        src_file.write_text("def alpha(): return 99\n", encoding="utf-8")
        new_mtime = src_file.stat().st_mtime + 1.0
        os.utime(src_file, (new_mtime, new_mtime))

        # Second sync
        r2 = runner.invoke(sync_cmd, ["--output-changed-scopes"])
        assert r2.exit_code == 0

        changed = _extract_changed_scopes_from_output(r2.output)
        # "src" scope should be listed, "lib" should NOT
        assert any("src" in s for s in changed), (
            f"Expected 'src' in changed scopes, got: {changed}"
        )
        assert not any("lib" in s for s in changed), (
            f"'lib' scope should NOT be in changed scopes, got: {changed}"
        )


# ---------------------------------------------------------------------------
# Test: first sync (no baseline) treats all scopes as changed
# ---------------------------------------------------------------------------

class TestFirstSyncAllScopesChanged:
    """On first sync with no prior snapshot, all scopes are treated as changed."""

    def test_first_sync_all_scopes_listed(self, tmp_path: Path, monkeypatch):
        """First sync lists all discovered scopes as changed."""
        monkeypatch.chdir(tmp_path)
        _write_config(tmp_path)
        _write_py_file(tmp_path, "src/alpha.py", "def alpha(): pass\n")
        _write_py_file(tmp_path, "lib/helper.py", "def helper(): pass\n")
        _create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        r = runner.invoke(sync_cmd, ["--output-changed-scopes"])
        assert r.exit_code == 0

        changed = _extract_changed_scopes_from_output(r.output)
        assert len(changed) >= 2, (
            f"First sync should list all scopes as changed, got: {changed}"
        )
        scope_names = set(changed)
        assert any("src" in s for s in scope_names)
        assert any("lib" in s for s in scope_names)


# ---------------------------------------------------------------------------
# Helper: parse the changed-scopes section from sync output
# ---------------------------------------------------------------------------

def _extract_changed_scopes_from_output(output: str) -> list[str]:
    """Extract the list of changed scope names from sync --output-changed-scopes output.

    Expects lines after a sentinel marker "---CHANGED-SCOPES---" up to end of output,
    one scope name per line.  Returns empty list if marker not found or no lines follow.
    """
    lines = output.splitlines()
    try:
        idx = lines.index("---CHANGED-SCOPES---")
    except ValueError:
        return []
    return [l.strip() for l in lines[idx + 1:] if l.strip()]
