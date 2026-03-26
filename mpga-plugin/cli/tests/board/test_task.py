import re
from pathlib import Path

import pytest

from mpga.board.task import task_filename, render_task_file, parse_task_file, Task, FileLock, ScopeLock


# ── task_filename ──


def test_task_filename_generates_slug_from_title():
    assert task_filename("T001", "Add authentication middleware") == (
        "T001-add-authentication-middleware.md"
    )


def test_task_filename_handles_special_characters():
    assert task_filename("T002", "Fix bug #42: login fails!") == (
        "T002-fix-bug-42-login-fails.md"
    )


def test_task_filename_truncates_long_titles():
    long_title = (
        "This is a very long task title that exceeds the maximum slug length for filenames"
    )
    filename = task_filename("T003", long_title)
    assert len(filename) < 60
    assert re.match(r"^T003-.+\.md$", filename)


# ── render_task_file / parse_task_file ──


@pytest.fixture
def sample_task() -> Task:
    return Task(
        id="T001",
        title="Add login page",
        column="todo",
        status=None,
        priority="high",
        milestone="v1.0",
        created="2026-03-22",
        updated="2026-03-22",
        depends_on=[],
        blocks=["T002"],
        scopes=["auth"],
        tdd_stage="green",
        lane_id="lane-auth-1",
        run_status="running",
        current_agent="mpga-green-dev",
        file_locks=[
            FileLock(
                path="src/auth/login.ts",
                lane_id="lane-auth-1",
                agent="mpga-green-dev",
                acquired_at="2026-03-22T10:00:00.000Z",
                heartbeat_at="2026-03-22T10:01:00.000Z",
            ),
        ],
        scope_locks=[
            ScopeLock(
                scope="auth",
                lane_id="lane-auth-1",
                agent="mpga-green-dev",
                acquired_at="2026-03-22T10:00:00.000Z",
            ),
        ],
        started_at="2026-03-22T10:00:00.000Z",
        finished_at=None,
        heartbeat_at="2026-03-22T10:01:00.000Z",
        evidence_expected=["[E] src/auth.ts :: login"],
        evidence_produced=[],
        tags=["auth", "frontend"],
        time_estimate="30min",
        body="# Task body\n\nSome details here.",
    )


def test_render_and_parse_round_trip(tmp_path: Path, sample_task: Task):
    rendered = render_task_file(sample_task)
    assert "---" in rendered
    assert "T001" in rendered
    assert "Add login page" in rendered

    filepath = tmp_path / "T001-add-login-page.md"
    filepath.write_text(rendered)

    parsed = parse_task_file(str(filepath))
    assert parsed is not None
    assert parsed.id == "T001"
    assert parsed.title == "Add login page"
    assert parsed.column == "todo"
    assert parsed.priority == "high"
    assert parsed.blocks == ["T002"]
    assert parsed.scopes == ["auth"]
    assert parsed.tdd_stage == "green"
    assert parsed.lane_id == "lane-auth-1"
    assert parsed.run_status == "running"
    assert parsed.current_agent == "mpga-green-dev"
    assert len(parsed.file_locks) == 1
    assert parsed.file_locks[0].path == "src/auth/login.ts"
    assert parsed.scope_locks[0].scope == "auth"
    assert parsed.heartbeat_at == "2026-03-22T10:01:00.000Z"


def test_fills_safe_defaults_for_missing_runtime_fields(tmp_path: Path):
    filepath = tmp_path / "T002-legacy-task.md"
    filepath.write_text(
        '---\n'
        'id: "T002"\n'
        'title: "Legacy task"\n'
        'status: "active"\n'
        'column: "todo"\n'
        'priority: "medium"\n'
        'created: "2026-03-22"\n'
        'updated: "2026-03-22"\n'
        'depends_on: []\n'
        'blocks: []\n'
        'scopes: []\n'
        'tdd_stage: null\n'
        'evidence_expected: []\n'
        'evidence_produced: []\n'
        'tags: []\n'
        'time_estimate: "5min"\n'
        '---\n'
        '\n'
        '# Legacy task\n'
    )

    parsed = parse_task_file(str(filepath))
    assert parsed is not None
    assert parsed.lane_id is None
    assert parsed.run_status == "queued"
    assert parsed.current_agent is None
    assert parsed.file_locks == []
    assert parsed.scope_locks == []
    assert parsed.started_at is None
    assert parsed.finished_at is None
    assert parsed.heartbeat_at is None


def test_parse_returns_none_for_nonexistent_file():
    assert parse_task_file("/nonexistent/path.md") is None
