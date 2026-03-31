"""Tests for T011 — Implement mpga memory get (Layer 3: full details).

Coverage checklist for: T011 — mpga memory get CLI command

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: get subcommand exists                     → test_memory_get_command_exists
[x] AC2: shows all observation fields              → test_get_shows_full_details
[x] AC3: output contains title and type            → test_get_shows_title_and_type
[x] AC4: output contains narrative text            → test_get_shows_narrative
[x] AC5: facts displayed as readable list          → test_get_shows_parsed_facts
[x] AC6: files_read and files_modified shown       → test_get_shows_files
[x] AC7: --json flag outputs valid JSON            → test_get_json_format
[x] AC8: error for non-existent observation ID     → test_get_missing_observation

Untested branches / edge cases:
- [ ] observation with all-null optional fields
- [ ] unicode in title / narrative
- [ ] very large facts / concepts JSON
"""

from __future__ import annotations

import json
import sqlite3

import pytest
from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema

# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-252 :: observations table
# Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:12-27 :: Observation dataclass
# Evidence: [E] mpga-plugin/cli/src/mpga/commands/memory.py:18-20 :: memory Click group

try:
    from mpga.commands.memory import memory

    _HAS_MEMORY = True
except ImportError:
    memory = None  # type: ignore[assignment]
    _HAS_MEMORY = False


_SEED_OBS = (
    "INSERT INTO observations "
    "(session_id, scope_id, title, type, narrative, facts, concepts, "
    " files_read, files_modified, evidence_links, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

_SEED_VALUES = (
    "sess-1",
    "scope-cli",
    "Auth token rotation",
    "decision",
    "Decided to rotate JWT tokens every 15 minutes for security.",
    '["jwt-rotation", "15min-expiry", "refresh-token-required"]',
    '["authentication", "security", "jwt"]',
    "src/auth/jwt.ts,src/auth/refresh.ts",
    "src/auth/config.ts",
    "[E] src/auth/jwt.ts:42-67",
    "2026-03-30T14:22:00",
)


@pytest.fixture
def obs_db(tmp_path, monkeypatch):
    """Provide a schema-initialized DB seeded with one fully-populated observation."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    conn.execute(_SEED_OBS, _SEED_VALUES)
    conn.commit()
    conn.close()

    if _HAS_MEMORY:
        monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Degenerate — get subcommand exists
# ---------------------------------------------------------------------------


def test_memory_get_command_exists():
    """The memory group must have a 'get' subcommand."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    command_names = list(memory.commands)
    assert "get" in command_names, (
        f"'get' not in memory commands. Found: {command_names}"
    )


# ---------------------------------------------------------------------------
# 2. Simplest valid — shows all key fields in output
# ---------------------------------------------------------------------------


def test_get_shows_full_details(obs_db):
    """get <id> must include title, type, narrative, scope, evidence, created_at."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "1"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    for expected in [
        "Auth token rotation",
        "decision",
        "Decided to rotate JWT tokens every 15 minutes",
        "scope-cli",
        "[E] src/auth/jwt.ts:42-67",
        "2026-03-30",
    ]:
        assert expected in result.output, (
            f"Expected '{expected}' in output, got:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# 3. Scalar — title and type displayed
# ---------------------------------------------------------------------------


def test_get_shows_title_and_type(obs_db):
    """Output must contain the observation title and type."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "1"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert "Auth token rotation" in result.output
    assert "decision" in result.output


# ---------------------------------------------------------------------------
# 4. Scalar — narrative text displayed
# ---------------------------------------------------------------------------


def test_get_shows_narrative(obs_db):
    """Output must contain the full narrative text."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "1"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert "Decided to rotate JWT tokens every 15 minutes for security." in result.output


# ---------------------------------------------------------------------------
# 5. Collection — facts parsed from JSON into readable list
# ---------------------------------------------------------------------------


def test_get_shows_parsed_facts(obs_db):
    """Facts must be shown as individual items, not raw JSON brackets."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "1"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    for fact in ["jwt-rotation", "15min-expiry", "refresh-token-required"]:
        assert fact in result.output, (
            f"Fact '{fact}' not found in output:\n{result.output}"
        )
    assert '["jwt-rotation"' not in result.output, (
        "Facts should be parsed, not displayed as raw JSON array"
    )


# ---------------------------------------------------------------------------
# 6. Scalar — files_read and files_modified shown
# ---------------------------------------------------------------------------


def test_get_shows_files(obs_db):
    """Output must include files_read and files_modified entries."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "1"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    assert "src/auth/jwt.ts" in result.output
    assert "src/auth/refresh.ts" in result.output
    assert "src/auth/config.ts" in result.output


# ---------------------------------------------------------------------------
# 7. Selection — --json flag outputs valid JSON with all fields
# ---------------------------------------------------------------------------


def test_get_json_format(obs_db):
    """--json flag must produce valid JSON containing all observation fields."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "1", "--json"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    data = json.loads(result.output)
    assert data["title"] == "Auth token rotation"
    assert data["type"] == "decision"
    assert data["narrative"] == "Decided to rotate JWT tokens every 15 minutes for security."
    assert "jwt-rotation" in data["facts"]
    assert "authentication" in data["concepts"]
    assert "src/auth/jwt.ts" in data["files_read"]
    assert "src/auth/config.ts" in data["files_modified"]
    assert data["scope"] == "scope-cli"
    assert "[E] src/auth/jwt.ts:42-67" in data["evidence_links"]


# ---------------------------------------------------------------------------
# 8. Error — non-existent observation ID returns error
# ---------------------------------------------------------------------------


def test_get_missing_observation(obs_db):
    """Requesting a non-existent observation ID must produce a 'not found' message."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    command_names = list(memory.commands)
    assert "get" in command_names, (
        f"'get' subcommand must exist first. Found: {command_names}"
    )
    runner = CliRunner()
    result = runner.invoke(memory, ["get", "9999"])
    assert "not found" in result.output.lower(), (
        f"Expected 'not found' message for missing observation ID, got:\n{result.output}"
    )
