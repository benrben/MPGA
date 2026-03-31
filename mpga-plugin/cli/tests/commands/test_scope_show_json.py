"""Tests for `mpga scope show --json` flag (T001).

RED phase: written before implementation, all tests should fail initially.

Acceptance criteria:
1. `mpga scope show <name> --json` outputs valid JSON
2. JSON contains at minimum: name, description, health, evidence_count fields
3. Existing non-JSON output is unchanged
4. Tests cover: --json flag exists, output is valid JSON, required fields present,
   non-json output unchanged
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.repos.scopes import Scope, ScopeRepo
from mpga.db.schema import create_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_SCOPE_CONTENT = """\
# Scope: cli

## Summary
The CLI entry point for MPGA.

## Evidence index

| Claim | Evidence |
|-------|----------|
| CLI entry | [E] mpga-plugin/cli/src/mpga/cli.py:1 |
| Config loaded | [E] mpga-plugin/cli/src/mpga/core/config.py:10 |

## Confidence and notes
- **Health:** fresh
- **Last verified:** 2026-01-01
"""


def _make_db_with_scope(root: Path, scope: Scope) -> None:
    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    ScopeRepo(conn).create(scope)
    conn.close()


def _sample_scope() -> Scope:
    return Scope(
        id="cli",
        name="cli",
        summary="The CLI entry point for MPGA.",
        content=SAMPLE_SCOPE_CONTENT,
        status="fresh",
        evidence_total=2,
        evidence_valid=2,
        last_verified="2026-01-01",
    )


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

class TestScopeShowJson:
    """Tests for the --json flag on `mpga scope show`."""

    def test_json_flag_exists_on_scope_show(self, tmp_path: Path, monkeypatch):
        """Degenerate case: --json flag is recognised (no UsageError / exit code 2)."""
        monkeypatch.chdir(tmp_path)
        _make_db_with_scope(tmp_path, _sample_scope())

        from mpga.commands.scope import scope_show

        runner = CliRunner()
        result = runner.invoke(scope_show, ["cli", "--json"])
        # Exit code 2 means "no such option" — that's the failure we expect before impl
        assert result.exit_code != 2, (
            f"--json flag not recognised (exit_code=2). stderr:\n{result.output}"
        )

    def test_json_flag_outputs_valid_json(self, tmp_path: Path, monkeypatch):
        """--json flag produces output that is parseable as JSON."""
        monkeypatch.chdir(tmp_path)
        _make_db_with_scope(tmp_path, _sample_scope())

        from mpga.commands.scope import scope_show

        runner = CliRunner()
        result = runner.invoke(scope_show, ["cli", "--json"])
        assert result.exit_code == 0, f"Command failed:\n{result.output}"

        try:
            data = json.loads(result.output)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Output is not valid JSON: {exc}\nOutput was:\n{result.output}")

        assert isinstance(data, dict), f"Expected a JSON object, got: {type(data)}"

    def test_json_output_contains_required_fields(self, tmp_path: Path, monkeypatch):
        """JSON output includes name, description, health, and evidence_count."""
        monkeypatch.chdir(tmp_path)
        _make_db_with_scope(tmp_path, _sample_scope())

        from mpga.commands.scope import scope_show

        runner = CliRunner()
        result = runner.invoke(scope_show, ["cli", "--json"])
        assert result.exit_code == 0, f"Command failed:\n{result.output}"

        data = json.loads(result.output)

        assert "name" in data, f"Missing 'name' field. Keys: {list(data.keys())}"
        assert "description" in data, f"Missing 'description' field. Keys: {list(data.keys())}"
        assert "health" in data, f"Missing 'health' field. Keys: {list(data.keys())}"
        assert "evidence_count" in data, f"Missing 'evidence_count' field. Keys: {list(data.keys())}"

    def test_json_output_values_are_correct(self, tmp_path: Path, monkeypatch):
        """JSON fields carry the expected values from the DB record."""
        monkeypatch.chdir(tmp_path)
        _make_db_with_scope(tmp_path, _sample_scope())

        from mpga.commands.scope import scope_show

        runner = CliRunner()
        result = runner.invoke(scope_show, ["cli", "--json"])
        assert result.exit_code == 0, f"Command failed:\n{result.output}"

        data = json.loads(result.output)

        assert data["name"] == "cli", f"Expected name='cli', got {data['name']!r}"
        assert data["description"] == "The CLI entry point for MPGA.", (
            f"Unexpected description: {data['description']!r}"
        )
        assert data["health"] == "fresh", f"Expected health='fresh', got {data['health']!r}"
        assert data["evidence_count"] == 2, (
            f"Expected evidence_count=2, got {data['evidence_count']!r}"
        )

    def test_non_json_output_unchanged(self, tmp_path: Path, monkeypatch):
        """Default (non-JSON) output is unaffected by the new flag."""
        monkeypatch.chdir(tmp_path)
        _make_db_with_scope(tmp_path, _sample_scope())

        from mpga.commands.scope import scope_show

        runner = CliRunner()
        # Invoke without --json
        result = runner.invoke(scope_show, ["cli"])
        assert result.exit_code == 0, f"Default show failed:\n{result.output}"

        # Should NOT be JSON
        try:
            json.loads(result.output)
            pytest.fail("Default output should not be pure JSON, but it parsed as JSON")
        except json.JSONDecodeError:
            pass  # expected — it's human-readable text

    def test_json_flag_scope_not_found_exits_nonzero(self, tmp_path: Path, monkeypatch):
        """--json on a missing scope exits non-zero (same as plain show)."""
        monkeypatch.chdir(tmp_path)
        # Create DB but no scopes
        dot_mpga = tmp_path / ".mpga"
        dot_mpga.mkdir(parents=True, exist_ok=True)
        conn = get_connection(str(dot_mpga / "mpga.db"))
        create_schema(conn)
        conn.close()

        from mpga.commands.scope import scope_show

        runner = CliRunner()
        result = runner.invoke(scope_show, ["nonexistent", "--json"])
        assert result.exit_code != 0, (
            "Expected non-zero exit for missing scope, got 0"
        )
