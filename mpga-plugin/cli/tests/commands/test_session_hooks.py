"""Tests for session lifecycle, event logging, and hook plumbing."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner


def _minimal_board() -> str:
    board = {
        "version": "1.0.0",
        "milestone": "M008-sqlite-fts5-context-engine",
        "updated": "2026-03-29T00:00:00.000Z",
        "columns": {
            "backlog": [],
            "todo": ["T093"],
            "in-progress": ["T094"],
            "testing": [],
            "review": [],
            "done": [],
        },
        "stats": {
            "total": 2,
            "done": 0,
            "in_flight": 1,
            "blocked": 0,
            "progress_pct": 0,
            "evidence_produced": 0,
            "evidence_expected": 0,
        },
        "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
        "next_task_id": 3,
    }
    return json.dumps(board, indent=2)


def _task_frontmatter(task_id: str, title: str, column: str) -> str:
    return (
        "---\n"
        f'id: {json.dumps(task_id)}\n'
        f'title: {json.dumps(title)}\n'
        f'column: {json.dumps(column)}\n'
        'status: "active"\n'
        'priority: "medium"\n'
        'milestone: "M008-sqlite-fts5-context-engine"\n'
        'created: "2026-03-29T00:00:00.000Z"\n'
        'updated: "2026-03-29T00:00:00.000Z"\n'
        "assigned: null\n"
        "depends_on: []\n"
        "blocks: []\n"
        "scopes: [\"mpga\"]\n"
        "tdd_stage: null\n"
        "evidence_expected: []\n"
        "evidence_produced: []\n"
        "tags: []\n"
        'time_estimate: "15min"\n'
        "---\n\n"
        f"# {task_id}: {title}\n"
    )


def _setup_session_project(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    sessions_dir = tmp_path / "MPGA" / "sessions"
    scopes_dir = tmp_path / "MPGA" / "scopes"

    tasks_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    scopes_dir.mkdir(parents=True, exist_ok=True)

    (board_dir / "board.json").write_text(_minimal_board(), encoding="utf-8")
    (tasks_dir / "T093-hook-cli-commands-pre-read-pre-bash-post.md").write_text(
        _task_frontmatter("T093", "Hook CLI commands - pre-read pre-bash post-bash", "todo"),
        encoding="utf-8",
    )
    (tasks_dir / "T094-hook-cli-session-start-session-managemen.md").write_text(
        _task_frontmatter("T094", "Hook CLI - session-start + session management", "todo"),
        encoding="utf-8",
    )

    return tmp_path


def _open_db(project_root: Path) -> sqlite3.Connection:
    return sqlite3.connect(project_root / ".mpga" / "mpga.db")


def test_session_start_creates_active_session(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.session import session

    runner = CliRunner()
    result = runner.invoke(session, ["start"])

    assert result.exit_code == 0
    assert "Session" in result.output
    assert "routing" in result.output.lower()

    conn = _open_db(tmp_path)
    try:
        row = conn.execute(
            "SELECT id, project_root, status, ended_at FROM sessions ORDER BY started_at DESC, id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[1] == str(tmp_path)
    assert row[2] == "active"
    assert row[3] is None


def test_session_log_records_db_event(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0
    result = runner.invoke(session, ["log", "Chose the SQLite mirror"])

    assert result.exit_code == 0

    conn = _open_db(tmp_path)
    try:
        rows = conn.execute(
            "SELECT event_type, action, input_summary FROM events ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    assert any(
        event_type == "note" and action == "session log" and "SQLite mirror" in (input_summary or "")
        for event_type, action, input_summary in rows
    )


def test_session_events_and_resume_use_recent_db_events(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0
    assert runner.invoke(session, ["log", "First event"]).exit_code == 0
    assert runner.invoke(session, ["log", "Second event"]).exit_code == 0

    events_result = runner.invoke(session, ["events", "--last", "1"])
    assert events_result.exit_code == 0
    assert "Second event" in events_result.output
    assert "First event" not in events_result.output

    resume_result = runner.invoke(session, ["resume"])
    assert resume_result.exit_code == 0
    assert "Second event" in resume_result.output
    assert len(resume_result.output.encode("utf-8")) < 500


def test_session_end_marks_session_closed(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0
    result = runner.invoke(session, ["end"])

    assert result.exit_code == 0

    conn = _open_db(tmp_path)
    try:
        row = conn.execute(
            "SELECT status, ended_at FROM sessions ORDER BY started_at DESC, id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "closed"
    assert row[1] is not None


def test_session_budget_reports_db_activity(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0
    assert runner.invoke(session, ["log", "Budget event"]).exit_code == 0

    result = runner.invoke(session, ["budget"])

    assert result.exit_code == 0
    assert "Database sessions" in result.output
    assert "Budget event" not in result.output


def test_hook_pre_read_and_pre_bash_routes_mpga_paths(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.hook import hook

    runner = CliRunner()

    read_result = runner.invoke(hook, ["pre-read", ".mpga/scopes/mpga.md"])
    assert read_result.exit_code == 1
    assert "decision=redirect" in read_result.output
    assert "mpga" in read_result.output.lower()

    allow_result = runner.invoke(hook, ["pre-read", "src/main.py"])
    assert allow_result.exit_code == 0

    bash_block = runner.invoke(hook, ["pre-bash", "cat .mpga/board/board.json"])
    assert bash_block.exit_code == 1
    assert "decision=redirect" in bash_block.output
    assert "mpga" in bash_block.output.lower()

    network_block = runner.invoke(hook, ["pre-bash", "curl https://example.com"])
    assert network_block.exit_code == 1
    assert "decision=block" in network_block.output
    assert "network_fetch_blocked" in network_block.output

    bash_allow = runner.invoke(hook, ["pre-bash", "mpga search session"])
    assert bash_allow.exit_code == 0


def test_hook_post_bash_logs_mpga_command_event(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.hook import hook
    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0

    result = runner.invoke(hook, ["post-bash", "mpga board move T094 done", "Moved T094 to done"])
    assert result.exit_code == 0

    conn = _open_db(tmp_path)
    try:
        row = conn.execute(
            "SELECT event_type, action, output_summary FROM events WHERE action LIKE 'mpga board move%' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "command"
    assert "Moved T094 to done" in (row[2] or "")


def test_hook_session_start_prints_resume_state(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.hook import hook
    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0
    assert runner.invoke(session, ["log", "Routing event"]).exit_code == 0

    result = runner.invoke(hook, ["session-start"])

    assert result.exit_code == 0
    assert "Use mpga search/scope/board and mpga ctx commands" in result.output
    assert "Routing event" in result.output


def test_hook_pre_compact_logs_compact_snapshot(tmp_path: Path, monkeypatch) -> None:
    _setup_session_project(tmp_path, monkeypatch)

    from mpga.commands.hook import hook
    from mpga.commands.session import session

    runner = CliRunner()
    assert runner.invoke(session, ["start"]).exit_code == 0
    assert runner.invoke(session, ["log", "Compact me"]).exit_code == 0

    result = runner.invoke(hook, ["pre-compact"])

    assert result.exit_code == 0
    assert "Compact me" in result.output

    conn = _open_db(tmp_path)
    try:
        row = conn.execute(
            "SELECT event_type, action FROM events WHERE event_type='compact' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row == ("compact", "pre compact snapshot")


def test_hooks_json_includes_session_start_and_pre_tool_use() -> None:
    hooks_path = Path("/Users/benreich/MPGA/mpga-plugin/hooks/hooks.json")
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))

    hook_map = hooks["hooks"]
    assert "PreToolUse" in hook_map
    assert "PostToolUse" in hook_map
    assert "SessionStart" in hook_map
    assert "PreCompact" in hook_map
