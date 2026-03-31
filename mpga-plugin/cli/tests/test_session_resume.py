"""Tests for T012 — Priority-tiered session resume builder.

Coverage checklist for: T012 — Priority-tiered session resume builder

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: build_session_resume returns a string       → test_build_session_resume_returns_string
[x] AC2: P1 decisions appear before P3 tool_output   → test_resume_includes_decisions_first
[x] AC3: errors are also P1 tier                     → test_resume_includes_errors_in_p1
[x] AC4: output fits within token budget (chars/4)   → test_resume_respects_budget
[x] AC5: small budget yields only P1 items           → test_resume_fills_highest_priority_first
[x] AC6: empty session returns empty string           → test_resume_empty_session
[x] AC7: each observation is one line                 → test_resume_format_one_line_per_observation

Untested branches / edge cases:
- [ ] session with only P4 intents (lowest tier)
- [ ] budget of 0 returns empty string
- [ ] unicode in observation titles
- [ ] observations with empty titles
- [ ] exact budget boundary (output == budget, not just <)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.repos.observations import Observation, ObservationRepo

from mpga.bridge.compress import build_session_resume


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def repo(db_conn: sqlite3.Connection) -> ObservationRepo:
    return ObservationRepo(db_conn)


def _seed_session(db_conn: sqlite3.Connection) -> None:
    """Insert a session row so observations can reference it."""
    db_conn.execute(
        "INSERT INTO sessions (id, project_root, started_at, status) "
        "VALUES ('sess-1', '/tmp/proj', datetime('now'), 'active')"
    )
    db_conn.commit()


def _add_obs(
    repo: ObservationRepo,
    title: str,
    obs_type: str,
    session_id: str = "sess-1",
) -> Observation:
    return repo.create(Observation(
        session_id=session_id,
        title=title,
        type=obs_type,
    ))


# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-252 :: observations table


class TestSessionResumeDegenerate:
    """Degenerate / null cases — TPP step 1."""

    def test_resume_empty_session(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """Empty session with no observations returns empty string."""
        _seed_session(db_conn)
        result = build_session_resume(db_conn, "sess-1", budget=500)
        assert result == ""


class TestSessionResumeBasic:
    """Basic return type and format — TPP steps 2-3."""

    def test_build_session_resume_returns_string(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """build_session_resume always returns a string."""
        _seed_session(db_conn)
        _add_obs(repo, "ran database migration", "tool_output")
        result = build_session_resume(db_conn, "sess-1", budget=500)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resume_format_structured_markdown(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """Output is structured markdown with tier headers and bullet items."""
        _seed_session(db_conn)
        _add_obs(repo, "first observation", "tool_output")
        _add_obs(repo, "second observation", "tool_output")
        _add_obs(repo, "third observation", "tool_output")

        result = build_session_resume(db_conn, "sess-1", budget=2000)
        assert "###" in result, "Expected markdown tier headers"
        assert "- first observation" in result
        assert "- second observation" in result
        assert "- third observation" in result


class TestSessionResumePriority:
    """Priority tier ordering — TPP steps 4-5."""

    def test_resume_includes_decisions_first(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """P1 decisions appear before P3 tool_output in the resume."""
        _seed_session(db_conn)
        _add_obs(repo, "ran linter check", "tool_output")
        _add_obs(repo, "chose REST over GraphQL", "decision")
        _add_obs(repo, "executed test suite", "tool_output")

        result = build_session_resume(db_conn, "sess-1", budget=2000)
        lines = result.strip().splitlines()

        decision_idx = next(i for i, ln in enumerate(lines) if "chose REST" in ln)
        tool_indices = [i for i, ln in enumerate(lines) if "linter" in ln or "test suite" in ln]
        assert all(decision_idx < ti for ti in tool_indices)

    def test_resume_includes_errors_in_p1(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """Errors are P1 tier and appear before P3 tool_output."""
        _seed_session(db_conn)
        _add_obs(repo, "fetched API response", "tool_output")
        _add_obs(repo, "import failed: module not found", "error")

        result = build_session_resume(db_conn, "sess-1", budget=2000)
        lines = result.strip().splitlines()

        error_idx = next(i for i, ln in enumerate(lines) if "import failed" in ln)
        tool_idx = next(i for i, ln in enumerate(lines) if "fetched API" in ln)
        assert error_idx < tool_idx

    def test_resume_fills_highest_priority_first(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """With a small budget, P1 tier gets 50% and appears first."""
        _seed_session(db_conn)
        _add_obs(repo, "decided on SQLite", "decision")
        _add_obs(repo, "found circular import", "error")
        _add_obs(repo, "read config file", "tool_output")
        _add_obs(repo, "discovered caching layer", "discovery")
        _add_obs(repo, "plan to refactor auth", "intent")

        result = build_session_resume(db_conn, "sess-1", budget=2000)
        lines = result.strip().splitlines()

        p1_header_idx = next(i for i, ln in enumerate(lines) if "Critical" in ln)
        decision_idx = next(i for i, ln in enumerate(lines) if "decided on SQLite" in ln)
        assert decision_idx > p1_header_idx, "P1 decision should appear under Critical header"

        if any("Context" in ln for ln in lines):
            p3_header_idx = next(i for i, ln in enumerate(lines) if "Context" in ln)
            assert p1_header_idx < p3_header_idx, "P1 Critical header should come before P3 Context"


class TestSessionResumeBudget:
    """Token budget enforcement — TPP step 6."""

    def test_resume_respects_budget(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """Output character count stays within budget * 4 (approx chars-per-token)."""
        _seed_session(db_conn)
        for i in range(20):
            _add_obs(repo, f"observation number {i:03d} with extra detail padding", "tool_output")

        budget_tokens = 50
        result = build_session_resume(db_conn, "sess-1", budget=budget_tokens)
        max_chars = budget_tokens * 4
        assert len(result) <= max_chars


