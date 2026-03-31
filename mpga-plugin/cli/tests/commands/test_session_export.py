"""Tests for session (handoff, log, resume, budget) and export commands."""

import json
from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def minimal_board(overrides: dict | None = None) -> str:
    board = {
        "version": "1.0.0",
        "milestone": "M001-alpha",
        "updated": "2026-01-01T00:00:00.000Z",
        "columns": {
            "backlog": [],
            "todo": ["T002"],
            "in-progress": ["T001"],
            "testing": [],
            "review": [],
            "done": [],
        },
        "stats": {
            "total": 2, "done": 0, "in_flight": 1, "blocked": 0,
            "progress_pct": 0, "evidence_produced": 0, "evidence_expected": 0,
        },
        "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
        "next_task_id": 3,
    }
    if overrides:
        board.update(overrides)
    return json.dumps(board, indent=2)


def task_frontmatter(task_id: str, title: str, column: str, extra: dict | None = None) -> str:
    extra = extra or {}
    return (
        f"---\n"
        f'id: {json.dumps(task_id)}\n'
        f'title: {json.dumps(title)}\n'
        f'column: {json.dumps(column)}\n'
        f'status: "active"\n'
        f'priority: "medium"\n'
        f'milestone: "M001-alpha"\n'
        f'created: "2026-01-01T00:00:00.000Z"\n'
        f'updated: "2026-01-01T00:00:00.000Z"\n'
        f'assigned: {json.dumps(extra.get("assigned")) if extra.get("assigned") else "null"}\n'
        f'depends_on: []\n'
        f'blocks: []\n'
        f'scopes: []\n'
        f'tdd_stage: {json.dumps(extra.get("tdd_stage")) if extra.get("tdd_stage") else "null"}\n'
        f'evidence_expected: []\n'
        f'evidence_produced: []\n'
        f'tags: []\n'
        f'time_estimate: "15min"\n'
        f"---\n\n"
        f"# {task_id}: {title}\n"
    )


def setup_session_project(tmp_path: Path, monkeypatch):
    """Set up a project with board and tasks for session tests."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))
    monkeypatch.setattr("mpga.commands.session_handoff.find_project_root", lambda: str(tmp_path))

    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    (board_dir / "board.json").write_text(minimal_board())
    (tasks_dir / "T001-implement-parser.md").write_text(
        task_frontmatter("T001", "Implement parser", "in-progress", {"tdd_stage": "green", "assigned": "agent"})
    )
    (tasks_dir / "T002-add-tests.md").write_text(
        task_frontmatter("T002", "Add tests", "todo")
    )

    # Set up SQLite DB with a session that has a board snapshot
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema
    from mpga.db.repos.sessions import SessionRepo

    db_path = tmp_path / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_path))
    create_schema(conn)
    snapshot = json.dumps({
        "milestone": "M001-alpha",
        "progress_pct": 0,
        "done": 0,
        "total": 2,
        "in_progress": [
            {"id": "T001", "title": "Implement parser", "column": "in-progress"},
        ],
    })
    repo = SessionRepo(conn)
    repo.ensure_active(str(tmp_path), task_snapshot=snapshot)
    conn.close()


# ---------------------------------------------------------------------------
# Tests: session handoff
# ---------------------------------------------------------------------------

class TestSessionHandoff:
    """session handoff tests."""

    def test_handoff_prints_to_stdout(self, tmp_path: Path, monkeypatch):
        """Handoff output is printed to stdout."""
        setup_session_project(tmp_path, monkeypatch)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['handoff'])
        assert result.exit_code == 0
        assert "# Session Handoff" in result.output

    def test_handoff_contains_board_state(self, tmp_path: Path, monkeypatch):
        """Handoff output contains correct board state."""
        setup_session_project(tmp_path, monkeypatch)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['handoff', '--accomplished', 'Fixed the parser'])
        assert result.exit_code == 0

        content = result.output
        assert "# Session Handoff" in content
        assert "Fixed the parser" in content
        assert "M001-alpha" in content
        assert "0/2" in content

    def test_handoff_includes_in_progress_tasks(self, tmp_path: Path, monkeypatch):
        """Handoff output includes in-progress tasks."""
        setup_session_project(tmp_path, monkeypatch)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['handoff'])
        assert result.exit_code == 0

        content = result.output
        assert "T001" in content
        assert "Implement parser" in content
        assert "in-progress" in content
        assert "1 task(s)" in content


# ---------------------------------------------------------------------------
# Tests: session log
# ---------------------------------------------------------------------------

class TestSessionLog:
    """session log tests."""

    def test_creates_session_log(self, tmp_path: Path, monkeypatch):
        """Records a log note into the SQLite DB."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.repos.sessions import SessionRepo
        import sqlite3

        db_path = tmp_path / ".mpga" / "mpga.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(str(db_path))
        create_schema(conn)
        repo = SessionRepo(conn)
        repo.ensure_active(str(tmp_path))
        conn.close()

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['log', 'Decided to use factory pattern'])
        assert result.exit_code == 0

        conn2 = sqlite3.connect(str(db_path))
        try:
            row = conn2.execute(
                "SELECT input_summary FROM events WHERE event_type = 'note' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            conn2.close()

        assert row is not None
        assert "Decided to use factory pattern" in row[0]

    def test_appends_to_existing_log(self, tmp_path: Path, monkeypatch):
        """Each log call appends a new event row into the DB."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.repos.sessions import SessionRepo
        import sqlite3

        db_path = tmp_path / ".mpga" / "mpga.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(str(db_path))
        create_schema(conn)
        repo = SessionRepo(conn)
        session_row = repo.ensure_active(str(tmp_path))
        repo.log_event(session_row.id, "note", action="session log", input_summary="First entry")
        conn.close()

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['log', 'Second entry here'])
        assert result.exit_code == 0

        conn2 = sqlite3.connect(str(db_path))
        try:
            rows = conn2.execute(
                "SELECT input_summary FROM events WHERE event_type = 'note' ORDER BY id"
            ).fetchall()
        finally:
            conn2.close()

        summaries = [r[0] for r in rows]
        assert any("First entry" in s for s in summaries)
        assert any("Second entry here" in s for s in summaries)


# ---------------------------------------------------------------------------
# Tests: session resume
# ---------------------------------------------------------------------------

class TestSessionResume:
    """session resume tests."""

    def test_shows_most_recent_handoff(self, tmp_path: Path, monkeypatch):
        """Shows resume summary from the most recent SQLite session."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.repos.sessions import SessionRepo

        db_path = tmp_path / ".mpga" / "mpga.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(str(db_path))
        create_schema(conn)
        repo = SessionRepo(conn)
        session_row = repo.ensure_active(str(tmp_path))
        repo.log_event(
            session_row.id,
            "command",
            action="board show",
            input_summary="Showed the board state",
        )
        conn.close()

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['resume'])
        assert result.exit_code == 0
        assert result.output.strip()  # some output was produced

    def test_shows_info_when_no_handoffs(self, tmp_path: Path, monkeypatch):
        """Shows info message when no session exists in DB."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['resume'])
        assert result.exit_code == 0
        assert "No session" in result.output or "mpga session start" in result.output


# ---------------------------------------------------------------------------
# Tests: session budget
# ---------------------------------------------------------------------------

class TestSessionBudget:
    """session budget tests."""

    def test_reports_line_counts(self, tmp_path: Path, monkeypatch):
        """Reports correct line counts for INDEX.md and scope docs."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        mpga_dir = tmp_path / "MPGA"
        scopes_dir = mpga_dir / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)

        (mpga_dir / "INDEX.md").write_text("\n".join(["line"] * 10))
        (scopes_dir / "core.md").write_text("\n".join(["scope-line"] * 5))
        (scopes_dir / "board.md").write_text("\n".join(["scope-line"] * 8))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['budget'])
        assert result.exit_code == 0
        assert "INDEX.md" in result.output
        assert "10" in result.output
        assert "Tier 1 (hot)" in result.output
        assert "scopes/core.md" in result.output
        assert "scopes/board.md" in result.output
        assert "Tier 2 (warm)" in result.output
        assert "23 lines" in result.output


# ---------------------------------------------------------------------------
# Tests: export --claude
# ---------------------------------------------------------------------------

class TestExportClaude:
    """export --claude tests."""

    def test_creates_claude_md(self, tmp_path: Path, monkeypatch):
        """Creates CLAUDE.md at project root."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)
        (mpga_dir / "INDEX.md").write_text("# INDEX\n\n## Active milestone\nM001-alpha\n")

        from mpga.commands.export.claude import export_claude

        export_claude(
            project_root=str(tmp_path),
            index_content="# INDEX\n\n## Active milestone\nM001-alpha\n",
            project_name="test-project",
            plugin_root=None,
            is_global=False,
        )

        claude_md_path = tmp_path / "CLAUDE.md"
        assert claude_md_path.exists()

        content = claude_md_path.read_text()
        assert "MPGA-Managed Project Context" in content
        assert "M001-alpha" in content

    def test_creates_skills_directory(self, tmp_path: Path, monkeypatch):
        """Creates .claude/skills/ directory structure."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)
        (mpga_dir / "INDEX.md").write_text("# INDEX\n")

        # Provide a real copy_skills_to to avoid test pollution from other tests
        # that may have monkeypatched it on the claude module
        from mpga.commands.export import agents as agents_mod
        from mpga.commands.export import claude as claude_mod

        monkeypatch.setattr(claude_mod, "copy_skills_to", agents_mod.copy_skills_to)

        claude_mod.export_claude(
            project_root=str(tmp_path),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root=None,
            is_global=False,
        )

        skills_dir = tmp_path / ".claude" / "skills"
        assert skills_dir.exists()

        skill_dirs = list(skills_dir.iterdir())
        assert len(skill_dirs) > 0
        for d in skill_dirs:
            assert d.name.startswith("mpga-")


# ---------------------------------------------------------------------------
# Tests: AGENTS metadata validity
# ---------------------------------------------------------------------------

class TestAgentsMetadata:
    """AGENTS metadata validity tests."""

    def test_every_agent_has_required_fields(self):
        """Every agent has required fields."""
        from mpga.commands.export.agents import AGENTS

        expected_slugs = [
            "campaigner", "red-dev", "green-dev", "blue-dev", "scout",
            "architect", "auditor", "researcher", "reviewer", "verifier",
        ]

        agent_slugs = [a.slug for a in AGENTS]
        for slug in expected_slugs:
            assert slug in agent_slugs

        for agent in AGENTS:
            assert agent.slug, "Agent missing slug"
            assert agent.name, f"Agent {agent.slug} missing name"
            assert agent.description, f"Agent {agent.slug} missing description"
            assert agent.model, f"Agent {agent.slug} missing model"
            # readonly, is_background, sandbox_mode are always present on the dataclass

    def test_exports_full_skill_catalog(self):
        """Exports the full skill catalog used by project integrations."""
        from mpga.commands.export.agents import SKILL_NAMES

        expected_skills = [
            "sync-project", "brainstorm", "plan", "develop", "drift-check",
            "ask", "onboard", "rally", "ship", "handoff", "map-codebase",
        ]
        for skill in expected_skills:
            assert skill in SKILL_NAMES
