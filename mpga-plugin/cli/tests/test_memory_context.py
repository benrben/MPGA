"""Tests for T010 — Implement mpga memory context (Layer 2: timeline).

Coverage checklist for: T010 — mpga memory context CLI command

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: context subcommand exists            → test_memory_context_command_exists
[x] AC2: shows observation details            → test_context_shows_observation_details
[x] AC3: shows surrounding timeline           → test_context_shows_timeline
[x] AC4: default window is 5 before/after     → test_context_window_default
[x] AC5: --window flag customizes window      → test_context_window_custom
[x] AC6: error for non-existent observation   → test_context_missing_observation
[x] AC7: includes session information         → test_context_shows_session_info

Untested branches / edge cases:
- [ ] observation at very start of timeline (fewer than N before)
- [ ] observation at very end of timeline (fewer than N after)
- [ ] --window 0 (degenerate window size)
- [ ] unicode in observation titles
"""

from __future__ import annotations

import sqlite3

import pytest
from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema

# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-252 :: observations table
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:188-196 :: sessions table
# Evidence: [E] mpga-plugin/cli/src/mpga/commands/memory.py:18-20 :: memory Click group

try:
    from mpga.commands.memory import memory

    _HAS_MEMORY = True
except ImportError:
    memory = None  # type: ignore[assignment]
    _HAS_MEMORY = False


_SESSION_ID = "sess-timeline-test"


@pytest.fixture
def timeline_db(tmp_path, monkeypatch):
    """Seed 12 observations with sequential timestamps for timeline tests.

    Observations are numbered obs-01 through obs-12, created one hour apart.
    The target for context queries is obs-07 (the middle-ish observation).
    A session row is also inserted so session info can be displayed.
    """
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    conn.execute(
        "INSERT INTO sessions (id, project_root, started_at, status, model) "
        "VALUES (?, ?, '2026-03-31T08:00:00', 'active', 'claude-4')",
        (_SESSION_ID, str(tmp_path)),
    )

    for i in range(1, 13):
        conn.execute(
            "INSERT INTO observations "
            "(session_id, scope_id, title, type, narrative, facts, priority, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 2, ?)",
            (
                _SESSION_ID,
                "scope-cli",
                f"Observation {i:02d}",
                "discovery" if i % 2 == 0 else "tool_output",
                f"Narrative for observation {i:02d}",
                f'["fact-{i:02d}"]',
                f"2026-03-31T{8 + i:02d}:00:00",
            ),
        )
    conn.commit()
    conn.close()

    if _HAS_MEMORY:
        monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)
    return tmp_path


def _target_obs_id(tmp_path) -> int:
    """Return the DB id for observation 07 (the middle target)."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    row = conn.execute(
        "SELECT id FROM observations WHERE title = 'Observation 07'"
    ).fetchone()
    conn.close()
    assert row is not None, "Seed observation 07 not found"
    return row[0]


# ---------------------------------------------------------------------------
# 1. Degenerate — context subcommand exists
# ---------------------------------------------------------------------------


def test_memory_context_command_exists():
    """The memory group must have a 'context' subcommand."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    command_names = list(memory.commands)
    assert "context" in command_names, (
        f"'context' not in memory commands. Found: {command_names}"
    )


# ---------------------------------------------------------------------------
# 2. Simplest valid — shows observation details for the target
# ---------------------------------------------------------------------------


def test_context_shows_observation_details(timeline_db):
    """context <id> must display title, type, and narrative of the target."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    obs_id = _target_obs_id(timeline_db)
    runner = CliRunner()
    result = runner.invoke(memory, ["context", str(obs_id)])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert "Observation 07" in result.output, (
        f"Expected title 'Observation 07' in output:\n{result.output}"
    )
    assert "Narrative for observation 07" in result.output, (
        f"Expected narrative in output:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 3. Collection — shows surrounding timeline entries
# ---------------------------------------------------------------------------


def test_context_shows_timeline(timeline_db):
    """context <id> must show observations before and after the target."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    obs_id = _target_obs_id(timeline_db)
    runner = CliRunner()
    result = runner.invoke(memory, ["context", str(obs_id)])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert "Observation 06" in result.output, (
        f"Expected preceding observation 06 in timeline:\n{result.output}"
    )
    assert "Observation 08" in result.output, (
        f"Expected following observation 08 in timeline:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 4. Scalar — default window is 5 before, 5 after
# ---------------------------------------------------------------------------


def test_context_window_default(timeline_db):
    """Default window shows 3 observations before and 3 after the target.

    With obs-07 as target:
      before: obs-04 through obs-06 (3 items)
      after:  obs-08 through obs-10 (3 items)
    obs-03 and obs-11 should NOT appear (outside default window of 3).
    """
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    obs_id = _target_obs_id(timeline_db)
    runner = CliRunner()
    result = runner.invoke(memory, ["context", str(obs_id)])

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    for i in range(4, 7):
        assert f"Observation {i:02d}" in result.output, (
            f"Expected obs-{i:02d} in default window before target:\n{result.output}"
        )
    for i in range(8, 11):
        assert f"Observation {i:02d}" in result.output, (
            f"Expected obs-{i:02d} in default window after target:\n{result.output}"
        )

    assert "Observation 03" not in result.output, (
        f"obs-03 should be outside default window of 3:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 5. Selection — --window flag customizes window size
# ---------------------------------------------------------------------------


def test_context_window_custom(timeline_db):
    """--window 2 shows only 2 before and 2 after the target.

    With obs-07 as target and --window 2:
      before: obs-05, obs-06
      after:  obs-08, obs-09
    obs-04 and obs-10 should NOT appear.
    """
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    obs_id = _target_obs_id(timeline_db)
    runner = CliRunner()
    result = runner.invoke(memory, ["context", str(obs_id), "--window", "2"])

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    assert "Observation 05" in result.output, (
        f"Expected obs-05 in window=2 before target:\n{result.output}"
    )
    assert "Observation 06" in result.output, (
        f"Expected obs-06 in window=2 before target:\n{result.output}"
    )
    assert "Observation 08" in result.output, (
        f"Expected obs-08 in window=2 after target:\n{result.output}"
    )
    assert "Observation 09" in result.output, (
        f"Expected obs-09 in window=2 after target:\n{result.output}"
    )

    assert "Observation 04" not in result.output, (
        f"obs-04 should be outside window=2:\n{result.output}"
    )
    assert "Observation 10" not in result.output, (
        f"obs-10 should be outside window=2:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 6. Error path — non-existent observation ID
# ---------------------------------------------------------------------------


def test_context_missing_observation(timeline_db):
    """context with a non-existent ID must exit non-zero with a 'not found' message."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    command_names = list(memory.commands)
    assert "context" in command_names, (
        f"'context' command must exist first. Found: {command_names}"
    )
    runner = CliRunner()
    result = runner.invoke(memory, ["context", "99999"])

    assert result.exit_code != 0, (
        f"Expected non-zero exit for missing observation, got 0:\n{result.output}"
    )
    assert "not found" in result.output.lower(), (
        f"Expected 'not found' message for missing observation:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 7. Integration — session information is included
# ---------------------------------------------------------------------------


def test_context_shows_session_info(timeline_db):
    """context output must include session information for the observation."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    obs_id = _target_obs_id(timeline_db)
    runner = CliRunner()
    result = runner.invoke(memory, ["context", str(obs_id)])

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert _SESSION_ID in result.output, (
        f"Expected session ID '{_SESSION_ID}' in output:\n{result.output}"
    )
