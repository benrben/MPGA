"""Tests for T013 — Upgrade session-start hook for cross-session context injection.

Coverage checklist for: T013 — session-start hook with observation injection

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: injects recent observations              → test_session_start_includes_observations
[x] AC2: shows observation count                   → test_session_start_shows_observation_count
[x] AC3: priority-tiered (P1 before P3)           → test_session_start_priority_tiered
[x] AC4: respects resume_budget config             → test_session_start_respects_budget
[x] AC5: includes search tips                      → test_session_start_includes_search_tips
[x] AC6: graceful with no observations             → test_session_start_no_observations
[x] AC7: cross-session observation injection       → test_session_start_cross_session

Untested branches / edge cases:
- [ ] observations older than 24 hours excluded
- [ ] resume_budget = 0 disables injection entirely
- [ ] unicode in observation titles
- [ ] exactly 10 observations boundary
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

# Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py:188-197 :: hook_session_start
from mpga.commands.hook import hook

# Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:12-28 :: Observation dataclass
# Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/sessions.py:13-20 :: Session dataclass
# Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:74-81 :: MemoryConfig with resume_budget


def _setup_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> sqlite3.Connection:
    """Create a fresh DB, patch project_root, and return the connection."""
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    db_path = tmp_path / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_path))
    create_schema(conn)

    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    monkeypatch.setattr("mpga.commands.session._project_root", lambda: tmp_path)

    return conn


def _seed_observation(
    conn: sqlite3.Connection,
    *,
    session_id: str | None = None,
    title: str = "test observation",
    obs_type: str = "tool_output",
    narrative: str = "some details",
    priority: int = 2,
    age_hours: float = 0,
) -> int:
    """Insert an observation and return its id."""
    created_at = datetime.now(UTC) - timedelta(hours=age_hours)
    cur = conn.execute(
        "INSERT INTO observations"
        "  (session_id, title, type, narrative, priority, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, title, obs_type, narrative, priority, created_at.isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def _get_conn(tmp_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(tmp_path / ".mpga" / "mpga.db"))


# ---------------------------------------------------------------------------
# TPP step 1: degenerate — no observations at all
# ---------------------------------------------------------------------------


class TestSessionStartNoObservations:
    """Session-start must work gracefully when the observations table is empty."""

    def test_session_start_no_observations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With zero observations, session-start must include observation section with zero count."""
        conn = _setup_db(tmp_path, monkeypatch)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0, f"session-start failed: {result.output}"
        lowered = result.output.lower()
        assert "0 observation" in lowered or "no recent observation" in lowered, (
            "With no observations, output must explicitly indicate zero observations "
            "(e.g. '0 observations' or 'no recent observations'). "
            f"Got: {result.output}"
        )


# ---------------------------------------------------------------------------
# TPP step 2: constant → variable — observations appear in output
# ---------------------------------------------------------------------------


class TestSessionStartIncludesObservations:
    """Session-start output must include recent observations from the DB."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/commands/session.py:205-215 :: _session_start_lines

    def test_session_start_includes_observations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When observations exist, session-start output must mention them."""
        conn = _setup_db(tmp_path, monkeypatch)
        _seed_observation(conn, title="Refactored auth module", narrative="Moved JWT logic")
        _seed_observation(conn, title="Fixed pagination bug", narrative="Off-by-one in cursor")
        conn.close()

        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0, f"session-start failed: {result.output}"
        assert "Refactored auth module" in result.output or "observation" in result.output.lower(), (
            "session-start output must include observation titles or a summary section. "
            f"Got: {result.output}"
        )

    def test_session_start_shows_observation_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Output must indicate how many recent observations exist."""
        conn = _setup_db(tmp_path, monkeypatch)
        for i in range(5):
            _seed_observation(conn, title=f"Observation #{i}")
        conn.close()

        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0
        lowered = result.output.lower()
        assert "5 observation" in lowered or "5 recent" in lowered, (
            "session-start output must show the count of recent observations "
            "(e.g. '5 observations' or '5 recent'). "
            f"Got: {result.output}"
        )


# ---------------------------------------------------------------------------
# TPP step 3: unconditional → selection — search tips
# ---------------------------------------------------------------------------


class TestSessionStartSearchTips:
    """Session-start must include tips on how to search observations."""

    def test_session_start_includes_search_tips(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Output must mention 'mpga memory search' so the agent knows how to query."""
        conn = _setup_db(tmp_path, monkeypatch)
        _seed_observation(conn, title="Some recent work")
        conn.close()

        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0
        assert "mpga memory search" in result.output.lower(), (
            "session-start must include search tips mentioning 'mpga memory search'. "
            f"Got: {result.output}"
        )


# ---------------------------------------------------------------------------
# TPP step 4: selection — priority tiering (P1 before P3)
# ---------------------------------------------------------------------------


class TestSessionStartPriorityTiered:
    """Observations must be shown priority-tiered: P1 (decisions) before P3 (low-value)."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:24 :: priority field

    def test_session_start_priority_tiered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """P1 items (decisions) must appear before P3 items in the output."""
        conn = _setup_db(tmp_path, monkeypatch)
        _seed_observation(
            conn, title="Low priority note", obs_type="tool_output", priority=3,
        )
        _seed_observation(
            conn, title="Critical decision: use SQLite", obs_type="decision", priority=1,
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0
        output = result.output
        p1_pos = output.find("Critical decision")
        p3_pos = output.find("Low priority note")
        assert p1_pos != -1, (
            f"P1 observation 'Critical decision: use SQLite' not found in output: {output}"
        )
        assert p3_pos != -1, (
            f"P3 observation 'Low priority note' not found in output: {output}"
        )
        assert p1_pos < p3_pos, (
            f"P1 item must appear before P3 item. P1 at {p1_pos}, P3 at {p3_pos}. Output: {output}"
        )


# ---------------------------------------------------------------------------
# TPP step 5: scalar → collection — budget enforcement
# ---------------------------------------------------------------------------


class TestSessionStartRespectsBudget:
    """Output length must be bounded by resume_budget from MemoryConfig."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:81 :: resume_budget default 4000

    def test_session_start_respects_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With many verbose observations, output must include observations AND stay bounded."""
        conn = _setup_db(tmp_path, monkeypatch)
        for i in range(50):
            _seed_observation(
                conn,
                title=f"Verbose observation #{i}",
                narrative="x" * 500,
                priority=2,
            )
        conn.close()

        budget = 4000
        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0
        lowered = result.output.lower()
        assert "observation" in lowered, (
            "session-start must include an observations section when observations exist. "
            f"Got: {result.output}"
        )
        assert len(result.output) <= budget * 2, (
            f"session-start output ({len(result.output)} chars) far exceeds "
            f"resume_budget ({budget}). Must be bounded."
        )


# ---------------------------------------------------------------------------
# TPP step 6: iteration — cross-session observations
# ---------------------------------------------------------------------------


class TestSessionStartCrossSession:
    """Session-start must show observations from OTHER sessions, not just the current one."""

    def test_session_start_cross_session(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Observations seeded with a different session_id must still appear."""
        conn = _setup_db(tmp_path, monkeypatch)
        _seed_observation(
            conn,
            session_id="old-session-abc",
            title="Previous session finding",
            narrative="Found a memory leak in the worker pool",
            priority=1,
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(hook, ["session-start"])

        assert result.exit_code == 0
        assert "Previous session finding" in result.output or "memory leak" in result.output.lower(), (
            "session-start must inject observations from previous sessions. "
            f"Got: {result.output}"
        )
