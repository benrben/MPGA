"""Tests for T014 — Upgrade pre-compact hook with priority-tiered snapshot.

Coverage checklist for: T014 — pre-compact hook upgrade

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: uses build_session_resume              → test_pre_compact_includes_observations
[x] AC2: observations in priority order          → test_pre_compact_priority_tiered
[x] AC3: saves snapshot as event                 → test_pre_compact_saves_event
[x] AC4: respects resume_budget from config      → test_pre_compact_respects_budget
[x] degenerate: no observations                  → test_pre_compact_no_observations
[x] characterization: existing flow preserved    → test_pre_compact_still_works_without_observations

Untested branches / edge cases:
- [ ] observations with identical priority (stable sort by created_at)
- [ ] resume_budget = 0 edge case
- [ ] session with no events and no observations
- [ ] unicode in observation narratives
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

# Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py:200-217 :: hook_pre_compact
from mpga.commands.hook import hook


class TestPreCompactUpgrade:
    """Pre-compact hook must use build_session_resume with priority-tiered observations."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py:200-217 :: hook_pre_compact
    # Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:57-98 :: ObservationRepo
    # Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:75-81 :: MemoryConfig.resume_budget

    @staticmethod
    def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
        """Create DB, schema, active session. Returns session_id."""
        from mpga.db.connection import get_connection
        from mpga.db.repos.sessions import SessionRepo
        from mpga.db.schema import create_schema

        db_path = tmp_path / ".mpga" / "mpga.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(str(db_path))
        create_schema(conn)
        session = SessionRepo(conn).create(str(tmp_path), session_id="S-T014-test")
        conn.close()
        monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
        return session.id

    @staticmethod
    def _seed_obs(
        tmp_path: Path, session_id: str, title: str, priority: int = 2, narrative: str = "",
    ) -> None:
        conn = sqlite3.connect(str(tmp_path / ".mpga" / "mpga.db"))
        conn.execute(
            "INSERT INTO observations"
            "  (session_id, title, type, narrative, priority, created_at)"
            " VALUES (?,?,?,?,?,datetime('now'))",
            (session_id, title, "tool_output", narrative or f"Narrative for {title}", priority),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _seed_event(tmp_path: Path, session_id: str, action: str, summary: str) -> None:
        from mpga.db.repos.sessions import SessionRepo

        conn = sqlite3.connect(str(tmp_path / ".mpga" / "mpga.db"))
        SessionRepo(conn).log_event(session_id, "command", action=action, input_summary=summary)
        conn.close()

    @staticmethod
    def _get_conn(tmp_path: Path) -> sqlite3.Connection:
        return sqlite3.connect(str(tmp_path / ".mpga" / "mpga.db"))

    # --- TPP step 1: degenerate — no observations ---

    def test_pre_compact_no_observations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """With zero observations, pre-compact output still references an observations section."""
        self._setup(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(hook, ["pre-compact"])
        assert result.exit_code == 0

        output = result.output.lower()
        assert "observation" in output, (
            f"Output must include observations section from build_session_resume, "
            f"even when empty. Got: {result.output!r}"
        )

    # --- TPP step 2: characterization — existing functionality with new format ---

    def test_pre_compact_still_works_without_observations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Pre-compact with events but no observations still produces output with observations section."""
        session_id = self._setup(tmp_path, monkeypatch)
        self._seed_event(tmp_path, session_id, "mpga board show", "Board query")

        runner = CliRunner()
        result = runner.invoke(hook, ["pre-compact"])
        assert result.exit_code == 0

        output = result.output
        assert len(output.strip()) > 0, "Pre-compact must produce non-empty output"
        assert "observation" in output.lower(), (
            f"Output must include observations section from build_session_resume. Got: {output!r}"
        )

    # --- TPP step 3: unconditional → selection — observations appear in output ---

    def test_pre_compact_includes_observations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Seeded observations must appear in pre-compact output."""
        session_id = self._setup(tmp_path, monkeypatch)
        self._seed_obs(tmp_path, session_id, "Read config.py", priority=1)
        self._seed_obs(tmp_path, session_id, "Grep for TODO", priority=2)

        runner = CliRunner()
        result = runner.invoke(hook, ["pre-compact"])
        assert result.exit_code == 0

        output = result.output
        assert "Read config.py" in output, (
            f"Observation 'Read config.py' missing from output. Got: {output!r}"
        )
        assert "Grep for TODO" in output, (
            f"Observation 'Grep for TODO' missing from output. Got: {output!r}"
        )

    # --- TPP step 4: selection — priority ordering ---

    def test_pre_compact_priority_tiered(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Observations must appear in priority order: lower number = higher priority = first."""
        session_id = self._setup(tmp_path, monkeypatch)
        self._seed_obs(tmp_path, session_id, "Low priority obs", priority=3)
        self._seed_obs(tmp_path, session_id, "High priority obs", priority=1)
        self._seed_obs(tmp_path, session_id, "Medium priority obs", priority=2)

        runner = CliRunner()
        result = runner.invoke(hook, ["pre-compact"])
        assert result.exit_code == 0

        output = result.output
        high_pos = output.find("High priority obs")
        med_pos = output.find("Medium priority obs")
        low_pos = output.find("Low priority obs")

        assert high_pos != -1, f"High priority obs not in output: {output!r}"
        assert med_pos != -1, f"Medium priority obs not in output: {output!r}"
        assert low_pos != -1, f"Low priority obs not in output: {output!r}"
        assert high_pos < med_pos < low_pos, (
            f"Priority order violated. Positions: high={high_pos}, med={med_pos}, low={low_pos}"
        )

    # --- TPP step 5: saves event with observation content ---

    def test_pre_compact_saves_event(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Compact event full_output must include observation text, not just session events."""
        session_id = self._setup(tmp_path, monkeypatch)
        self._seed_obs(tmp_path, session_id, "UniqueMarkerXYZ123", priority=1)

        runner = CliRunner()
        result = runner.invoke(hook, ["pre-compact"])
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        row = conn.execute(
            "SELECT full_output FROM events WHERE event_type = 'compact' ORDER BY id DESC LIMIT 1",
        ).fetchone()
        conn.close()

        assert row is not None, "No compact event found in events table"
        assert "UniqueMarkerXYZ123" in row[0], (
            f"Compact event must include observation text. full_output: {row[0]!r}"
        )

    # --- TPP step 6: respects resume_budget from config ---

    def test_pre_compact_respects_budget(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Output must respect resume_budget from config, not hardcoded 700."""
        session_id = self._setup(tmp_path, monkeypatch)
        for i in range(15):
            self._seed_obs(
                tmp_path, session_id, f"Observation number {i:03d}", priority=2,
                narrative=f"Detailed narrative for obs {i:03d}. " * 5,
            )
        for i in range(10):
            self._seed_event(
                tmp_path, session_id,
                f"mpga action {i:03d}",
                f"Detailed summary for action {i:03d} with extra padding text here",
            )

        budget = 100
        config_path = tmp_path / ".mpga" / "mpga.config.json"
        config_path.write_text(
            json.dumps({"memory": {"resumeBudget": budget}}),
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(hook, ["pre-compact"])
        assert result.exit_code == 0

        output = result.output.strip()
        assert len(output) <= budget, (
            f"Output length {len(output)} exceeds resume_budget {budget}. "
            f"First 200 chars: {output[:200]!r}"
        )
