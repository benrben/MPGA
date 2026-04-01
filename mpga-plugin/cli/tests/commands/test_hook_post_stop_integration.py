"""Integration tests: full post-stop pipeline end-to-end (T010).

Coverage:
  1. StopFailure → enqueue → worker → SKILL.md updated
  2. StopFailure with no identifiable skill → improvement_skipped
  3. Stop below threshold → no queue item, worker returns 0
  4. Rollback restores from backup

Evidence: [E] mpga-plugin/cli/tests/commands/test_hook_post_stop_integration.py — T010
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from mpga.commands.hook import backup_file, hook
from mpga.commands.hook_post_stop import process_improvement_queue
from mpga.db.repos.observations import ObservationRepo
from mpga.db.schema import create_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    """Create .mpga/mpga.db with schema and return an open connection."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    create_schema(conn)
    return conn


def _invoke_post_stop(tmp_path: Path, payload_dict: dict, monkeypatch) -> None:
    """Invoke `hook post-stop` with *payload_dict* piped to stdin."""
    monkeypatch.setattr(
        "mpga.commands.session.find_project_root", lambda: str(tmp_path)
    )
    runner = CliRunner()
    result = runner.invoke(
        hook,
        ["post-stop"],
        input=json.dumps(payload_dict),
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (
        f"hook post-stop exited with code {result.exit_code}:\n{result.output}"
    )


def _mock_llm_client(improved_text: str = "# My Skill\n\nImproved content.\n") -> MagicMock:
    """Return a mock Anthropic client that returns *improved_text*."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=improved_text)]
    mock_client.messages.create.return_value = mock_response
    return mock_client


def _make_skill(tmp_path: Path, skill_name: str = "mpga-develop") -> Path:
    """Create a SKILL.md file that passes validation (200 + chars) and return its path."""
    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    original_content = f"# {skill_name}\n\n" + "A" * 200 + "\n"
    skill_file.write_text(original_content, encoding="utf-8")
    return skill_file


def _write_tracker(tmp_path: Path, session_id: str, skill_name: str) -> None:
    """Write .mpga/session/<session_id>/active_skill.json."""
    tracker_dir = tmp_path / ".mpga" / "session" / session_id
    tracker_dir.mkdir(parents=True)
    (tracker_dir / "active_skill.json").write_text(
        json.dumps({"skill": skill_name, "session_id": session_id}),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Test 1: StopFailure → enqueue → worker → SKILL.md updated
# ---------------------------------------------------------------------------


class TestIntegrationStopFailureWithIdentifiedSkill:
    """Full pipeline: StopFailure payload → DB → queue → worker → SKILL.md written."""

    def test_stop_event_observation_created(self, tmp_path: Path, monkeypatch) -> None:
        """Invoking hook post-stop logs a stop_event observation."""
        _setup_db(tmp_path)
        skill_name = "mpga-develop"
        session_id = "test-sid-001"
        _make_skill(tmp_path, skill_name)
        _write_tracker(tmp_path, session_id, skill_name)

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        db_path = tmp_path / ".mpga" / "mpga.db"
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT type FROM observations WHERE type='stop_event'"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) >= 1, "Expected at least one stop_event observation"

    def test_queue_item_created_for_stop_failure(self, tmp_path: Path, monkeypatch) -> None:
        """StopFailure payload creates a queue item with tool_name='post-stop'."""
        _setup_db(tmp_path)
        skill_name = "mpga-develop"
        session_id = "test-sid-002"
        _make_skill(tmp_path, skill_name)
        _write_tracker(tmp_path, session_id, skill_name)

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        db_path = tmp_path / ".mpga" / "mpga.db"
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT tool_name FROM observation_queue WHERE tool_name='post-stop' AND processed=0"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) >= 1, "Expected a queue item with tool_name='post-stop'"

    def test_worker_updates_skill_md(self, tmp_path: Path, monkeypatch) -> None:
        """process_improvement_queue() writes improved content to SKILL.md."""
        conn = _setup_db(tmp_path)
        skill_name = "mpga-develop"
        session_id = "test-sid-003"
        skill_file = _make_skill(tmp_path, skill_name)
        _write_tracker(tmp_path, session_id, skill_name)

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        improved_text = "# mpga-develop\n\nImproved content.\n" + "B" * 150 + "\n"
        mock_client = _mock_llm_client(improved_text)

        count = process_improvement_queue(conn, tmp_path, client=mock_client)
        conn.close()

        assert count == 1, f"Expected 1 item processed, got {count}"
        written = skill_file.read_text(encoding="utf-8")
        assert written == improved_text, "SKILL.md content should be the improved text"

    def test_backup_file_created(self, tmp_path: Path, monkeypatch) -> None:
        """process_improvement_queue() creates a backup before writing SKILL.md."""
        conn = _setup_db(tmp_path)
        skill_name = "mpga-develop"
        session_id = "test-sid-004"
        _make_skill(tmp_path, skill_name)
        _write_tracker(tmp_path, session_id, skill_name)

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        improved_text = "# mpga-develop\n\nImproved content.\n" + "B" * 150 + "\n"
        mock_client = _mock_llm_client(improved_text)

        process_improvement_queue(conn, tmp_path, client=mock_client)
        conn.close()

        backup_dir = tmp_path / ".mpga" / "backups" / skill_name
        assert backup_dir.exists(), f"Backup dir should exist at {backup_dir}"
        md_backups = list(backup_dir.glob("*.md"))
        assert len(md_backups) >= 1, "At least one backup .md file should exist"

    def test_improvement_applied_observation_logged(self, tmp_path: Path, monkeypatch) -> None:
        """process_improvement_queue() logs an improvement_applied observation."""
        conn = _setup_db(tmp_path)
        skill_name = "mpga-develop"
        session_id = "test-sid-005"
        _make_skill(tmp_path, skill_name)
        _write_tracker(tmp_path, session_id, skill_name)

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        improved_text = "# mpga-develop\n\nImproved content.\n" + "B" * 150 + "\n"
        mock_client = _mock_llm_client(improved_text)

        process_improvement_queue(conn, tmp_path, client=mock_client)

        rows = conn.execute(
            "SELECT type FROM observations WHERE type='improvement_applied'"
        ).fetchall()
        conn.close()

        assert len(rows) >= 1, "Expected an improvement_applied observation"


# ---------------------------------------------------------------------------
# Test 2: StopFailure with no identifiable skill → improvement_skipped
# ---------------------------------------------------------------------------


class TestIntegrationStopFailureNoIdentifiableSkill:
    """StopFailure with no tracker file → queue item → worker skips gracefully."""

    def test_queue_item_still_created(self, tmp_path: Path, monkeypatch) -> None:
        """A queue item is created even when no skill can be identified."""
        _setup_db(tmp_path)
        session_id = "test-sid-010"

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
            # No transcript_path, no active_skill.json
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        db_path = tmp_path / ".mpga" / "mpga.db"
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT tool_name FROM observation_queue WHERE tool_name='post-stop'"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) >= 1, "Queue item should be created even without identifiable skill"

    def test_worker_logs_improvement_skipped(self, tmp_path: Path, monkeypatch) -> None:
        """Worker logs improvement_skipped when no skill can be identified."""
        conn = _setup_db(tmp_path)
        session_id = "test-sid-011"

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        mock_client = _mock_llm_client()
        count = process_improvement_queue(conn, tmp_path, client=mock_client)

        rows = conn.execute(
            "SELECT type FROM observations WHERE type='improvement_skipped'"
        ).fetchall()
        conn.close()

        assert count >= 1, "Worker should process 1 item (even if skipped)"
        assert len(rows) >= 1, "Expected an improvement_skipped observation"

    def test_no_file_writes_when_skipped(self, tmp_path: Path, monkeypatch) -> None:
        """No skill files are written when the worker skips due to no target."""
        conn = _setup_db(tmp_path)
        session_id = "test-sid-012"

        payload = {
            "hook_event_name": "StopFailure",
            "session_id": session_id,
            "error": "rate_limit_error",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        mock_client = _mock_llm_client()
        process_improvement_queue(conn, tmp_path, client=mock_client)
        conn.close()

        # No backups should have been created (nothing to back up)
        backup_root = tmp_path / ".mpga" / "backups"
        skill_backups = list(backup_root.glob("*/*.md")) if backup_root.exists() else []
        assert len(skill_backups) == 0, "No backup files should be written when skipped"


# ---------------------------------------------------------------------------
# Test 3: Stop (not StopFailure) below threshold → no queue item
# ---------------------------------------------------------------------------


class TestIntegrationStopBelowThreshold:
    """Normal Stop event (no error, no recurrence) → no queue item created."""

    def test_no_queue_item_for_normal_stop(self, tmp_path: Path, monkeypatch) -> None:
        """A Stop event with no error does not create a queue item."""
        _setup_db(tmp_path)
        session_id = "test-sid-020"

        payload = {
            "hook_event_name": "Stop",
            "session_id": session_id,
            "reason": "Task appears complete",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        db_path = tmp_path / ".mpga" / "mpga.db"
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT id FROM observation_queue WHERE tool_name='post-stop' AND processed=0"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) == 0, "Stop event below threshold must not create a queue item"

    def test_stop_event_observation_still_logged(self, tmp_path: Path, monkeypatch) -> None:
        """A stop_event observation is always logged, even for normal Stop."""
        _setup_db(tmp_path)
        session_id = "test-sid-021"

        payload = {
            "hook_event_name": "Stop",
            "session_id": session_id,
            "reason": "Task appears complete",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        db_path = tmp_path / ".mpga" / "mpga.db"
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute(
                "SELECT type FROM observations WHERE type='stop_event'"
            ).fetchall()
        finally:
            conn.close()

        assert len(rows) >= 1, "A stop_event observation should always be logged"

    def test_worker_returns_zero_for_empty_queue(self, tmp_path: Path, monkeypatch) -> None:
        """process_improvement_queue() returns 0 when no items are in the queue."""
        conn = _setup_db(tmp_path)
        session_id = "test-sid-022"

        payload = {
            "hook_event_name": "Stop",
            "session_id": session_id,
            "reason": "Task appears complete",
        }
        _invoke_post_stop(tmp_path, payload, monkeypatch)

        mock_client = _mock_llm_client()
        count = process_improvement_queue(conn, tmp_path, client=mock_client)
        conn.close()

        assert count == 0, "Worker should process 0 items when queue is empty"


# ---------------------------------------------------------------------------
# Test 4: Rollback restores from backup
# ---------------------------------------------------------------------------


class TestIntegrationRollback:
    """backup_file() + rollback command restores a skill file."""

    def test_rollback_restores_original_content(self, tmp_path: Path, monkeypatch) -> None:
        """hook rollback <name> restores the file to the content before modification."""
        monkeypatch.setattr(
            "mpga.commands.session.find_project_root", lambda: str(tmp_path)
        )

        skill_name = "mpga-develop"
        skill_dir = tmp_path / ".claude" / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"

        original_content = "# mpga-develop\n\nOriginal content.\n"
        skill_file.write_text(original_content, encoding="utf-8")

        # Back up before modification
        backup_file(str(skill_file), skill_name, project_root=tmp_path)

        # Simulate modification
        modified_content = "# mpga-develop\n\nModified content.\n"
        skill_file.write_text(modified_content, encoding="utf-8")

        assert skill_file.read_text(encoding="utf-8") == modified_content, (
            "Pre-condition: file should be modified before rollback"
        )

        # Invoke rollback
        runner = CliRunner()
        result = runner.invoke(hook, ["rollback", skill_name], catch_exceptions=False)
        assert result.exit_code == 0, (
            f"rollback exited with code {result.exit_code}:\n{result.output}"
        )

        # Verify restoration
        restored = skill_file.read_text(encoding="utf-8")
        assert restored == original_content, (
            f"Rollback should restore original content, got:\n{restored!r}"
        )

    def test_rollback_fails_when_no_backups(self, tmp_path: Path, monkeypatch) -> None:
        """hook rollback <name> exits with error when no backups exist."""
        monkeypatch.setattr(
            "mpga.commands.session.find_project_root", lambda: str(tmp_path)
        )

        runner = CliRunner()
        result = runner.invoke(hook, ["rollback", "nonexistent-skill"])
        assert result.exit_code != 0, "rollback with no backups should fail"

    def test_backup_creates_companion_path_file(self, tmp_path: Path) -> None:
        """backup_file() writes both <timestamp>.md and <timestamp>.path."""
        skill_name = "mpga-develop"
        skill_dir = tmp_path / ".claude" / "skills" / skill_name
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# mpga-develop\n\nContent.\n", encoding="utf-8")

        backup_path = backup_file(str(skill_file), skill_name, project_root=tmp_path)

        assert backup_path.exists(), "Backup .md file should exist"
        path_file = backup_path.with_suffix(".path")
        assert path_file.exists(), "Companion .path file should exist"

        restored_path = path_file.read_text(encoding="utf-8").strip()
        assert restored_path == str(skill_file), (
            f"Companion .path should contain '{skill_file}', got '{restored_path}'"
        )
