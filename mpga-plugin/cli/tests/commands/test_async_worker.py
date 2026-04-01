"""Unit tests for the T012 async improvement worker.

Tests cover process_improvement_queue() in hook_post_stop.py.
All LLM calls, filesystem writes, and DB operations are mocked.

Evidence:
  - Worker implementation: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T012
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mpga.commands.hook_post_stop import (
    ImprovementValidationError,
    process_improvement_queue,
)
from mpga.db.schema import create_schema


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_conn() -> sqlite3.Connection:
    """In-memory SQLite DB with schema applied."""
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    return conn


def _enqueue(conn: sqlite3.Connection, session_id: str, envelope: dict) -> int:
    """Insert a raw post-stop queue item and return its id."""
    cur = conn.execute(
        "INSERT INTO observation_queue"
        "  (session_id, tool_name, tool_input, tool_output, created_at, processed)"
        " VALUES (?,?,?,?,datetime('now'),0)",
        (session_id, "post-stop", json.dumps(envelope), "enqueue_improvement"),
    )
    conn.commit()
    return cur.lastrowid


def _is_processed(conn: sqlite3.Connection, item_id: int) -> bool:
    row = conn.execute(
        "SELECT processed FROM observation_queue WHERE id=?", (item_id,)
    ).fetchone()
    return bool(row and row[0])


def _obs_types(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT type FROM observations ORDER BY id").fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_worker_skips_when_no_tracker_file_and_no_transcript(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """When tracker file absent and no transcript, item is skipped with improvement_skipped obs."""
    session_id = "sess-001"
    envelope = {"hook_event_name": "StopFailure", "session_id": session_id}
    item_id = _enqueue(mem_conn, session_id, envelope)

    count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    assert _is_processed(mem_conn, item_id)
    assert "improvement_skipped" in _obs_types(mem_conn)


def test_worker_resolves_skill_from_tracker_file(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """When tracker file names a skill and the SKILL.md exists, improvement is applied."""
    session_id = "sess-002"
    skill_name = "mpga-develop"

    # Create the tracker file
    tracker_dir = tmp_path / ".mpga" / "session" / session_id
    tracker_dir.mkdir(parents=True)
    (tracker_dir / "active_skill.json").write_text(
        json.dumps({"skill": skill_name, "session_id": session_id}),
        encoding="utf-8",
    )

    # Create the SKILL.md file
    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# mpga-develop\n\nSome content here.\n", encoding="utf-8")

    envelope = {"hook_event_name": "StopFailure", "session_id": session_id}
    item_id = _enqueue(mem_conn, session_id, envelope)

    improved_content = "# mpga-develop\n\nImproved content here.\n"

    with (
        patch(
            "mpga.commands.hook_post_stop_worker.generate_improvement",
            return_value=improved_content,
        ) as mock_gen,
        patch(
            "mpga.commands.hook_post_stop_worker.write_improvement"
        ) as mock_write,
    ):
        count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    assert _is_processed(mem_conn, item_id)
    mock_gen.assert_called_once()
    mock_write.assert_called_once()
    assert "improvement_applied" in _obs_types(mem_conn)


def test_worker_resolves_skill_from_transcript_regex(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """When tracker file absent but transcript has /mpga:<skill>, skill is resolved."""
    session_id = "sess-003"
    skill_name = "mpga-develop"

    # Create a transcript with a slash command
    transcript_file = tmp_path / f"{session_id}.jsonl"
    transcript_file.write_text(
        json.dumps({"role": "user", "content": "/mpga:develop run the TDD cycle"}) + "\n",
        encoding="utf-8",
    )

    # Create the SKILL.md file
    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# mpga-develop\n\nOriginal content.\n", encoding="utf-8")

    envelope = {
        "hook_event_name": "StopFailure",
        "session_id": session_id,
        "transcript_path": str(transcript_file),
    }
    item_id = _enqueue(mem_conn, session_id, envelope)

    improved_content = "# mpga-develop\n\nImproved content.\n"

    with (
        patch(
            "mpga.commands.hook_post_stop_worker.generate_improvement",
            return_value=improved_content,
        ),
        patch("mpga.commands.hook_post_stop_worker.write_improvement"),
    ):
        count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    assert _is_processed(mem_conn, item_id)
    assert "improvement_applied" in _obs_types(mem_conn)


def test_worker_skips_when_target_file_not_found(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """When tracker resolves a skill but SKILL.md doesn't exist, skip with improvement_skipped."""
    session_id = "sess-004"
    skill_name = "missing-skill"

    # Tracker points to a skill whose file does not exist
    tracker_dir = tmp_path / ".mpga" / "session" / session_id
    tracker_dir.mkdir(parents=True)
    (tracker_dir / "active_skill.json").write_text(
        json.dumps({"skill": skill_name, "session_id": session_id}),
        encoding="utf-8",
    )
    # Do NOT create the SKILL.md

    envelope = {"hook_event_name": "StopFailure", "session_id": session_id}
    item_id = _enqueue(mem_conn, session_id, envelope)

    count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    assert _is_processed(mem_conn, item_id)
    assert "improvement_skipped" in _obs_types(mem_conn)


def test_worker_logs_improvement_skipped_on_no_target(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """When no target can be identified, an improvement_skipped observation is logged."""
    session_id = "sess-005"
    envelope = {
        "hook_event_name": "StopFailure",
        "session_id": session_id,
        # No transcript_path; no tracker file
    }
    item_id = _enqueue(mem_conn, session_id, envelope)

    count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    assert _is_processed(mem_conn, item_id)
    obs = _obs_types(mem_conn)
    assert obs.count("improvement_skipped") == 1


def test_worker_logs_improvement_applied_on_success(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """On successful improvement, an improvement_applied observation is logged."""
    session_id = "sess-006"
    skill_name = "mpga-test-skill"

    tracker_dir = tmp_path / ".mpga" / "session" / session_id
    tracker_dir.mkdir(parents=True)
    (tracker_dir / "active_skill.json").write_text(
        json.dumps({"skill": skill_name, "session_id": session_id}),
        encoding="utf-8",
    )

    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# mpga-test-skill\n\nOriginal content.\n", encoding="utf-8")

    envelope = {"hook_event_name": "StopFailure", "session_id": session_id}
    _enqueue(mem_conn, session_id, envelope)

    improved_content = "# mpga-test-skill\n\nImproved content.\n"

    with (
        patch(
            "mpga.commands.hook_post_stop_worker.generate_improvement",
            return_value=improved_content,
        ),
        patch("mpga.commands.hook_post_stop_worker.write_improvement"),
    ):
        count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    obs = _obs_types(mem_conn)
    assert "improvement_applied" in obs
    assert "improvement_failed" not in obs


def test_worker_logs_improvement_failed_on_validation_error(
    mem_conn: sqlite3.Connection, tmp_path: Path
) -> None:
    """When write_improvement raises ImprovementValidationError, log improvement_failed."""
    session_id = "sess-007"
    skill_name = "mpga-failing-skill"

    tracker_dir = tmp_path / ".mpga" / "session" / session_id
    tracker_dir.mkdir(parents=True)
    (tracker_dir / "active_skill.json").write_text(
        json.dumps({"skill": skill_name, "session_id": session_id}),
        encoding="utf-8",
    )

    skill_dir = tmp_path / ".claude" / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# mpga-failing-skill\n\nOriginal content.\n", encoding="utf-8")

    envelope = {"hook_event_name": "StopFailure", "session_id": session_id}
    item_id = _enqueue(mem_conn, session_id, envelope)

    with (
        patch(
            "mpga.commands.hook_post_stop_worker.generate_improvement",
            return_value="bad output",
        ),
        patch(
            "mpga.commands.hook_post_stop_worker.write_improvement",
            side_effect=ImprovementValidationError("LLM output does not start with a # header"),
        ),
    ):
        count = process_improvement_queue(mem_conn, tmp_path)

    assert count == 1
    assert _is_processed(mem_conn, item_id)
    obs = _obs_types(mem_conn)
    assert "improvement_failed" in obs
    assert "improvement_applied" not in obs
