"""Tests for session (handoff, log, resume, budget) and export commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import write_file


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

    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    sessions_dir = tmp_path / "MPGA" / "sessions"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    (board_dir / "board.json").write_text(minimal_board())
    (tasks_dir / "T001-implement-parser.md").write_text(
        task_frontmatter("T001", "Implement parser", "in-progress", {"tdd_stage": "green", "assigned": "agent"})
    )
    (tasks_dir / "T002-add-tests.md").write_text(
        task_frontmatter("T002", "Add tests", "todo")
    )


# ---------------------------------------------------------------------------
# Tests: session handoff
# ---------------------------------------------------------------------------

class TestSessionHandoff:
    """session handoff tests."""

    def test_creates_handoff_file(self, tmp_path: Path, monkeypatch):
        """Creates a handoff file in MPGA/sessions/."""
        setup_session_project(tmp_path, monkeypatch)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['handoff'])
        assert result.exit_code == 0

        sessions_dir = tmp_path / "MPGA" / "sessions"
        files = [f for f in sessions_dir.iterdir() if f.name.endswith("-handoff.md")]
        assert len(files) == 1

    def test_handoff_contains_board_state(self, tmp_path: Path, monkeypatch):
        """Handoff file contains correct board state."""
        setup_session_project(tmp_path, monkeypatch)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['handoff', '--accomplished', 'Fixed the parser'])
        assert result.exit_code == 0

        sessions_dir = tmp_path / "MPGA" / "sessions"
        files = [f for f in sessions_dir.iterdir() if f.name.endswith("-handoff.md")]
        content = files[0].read_text()

        assert "# Session Handoff" in content
        assert "Fixed the parser" in content
        assert "M001-alpha" in content
        assert "0/2 tasks done" in content

    def test_handoff_includes_in_progress_tasks(self, tmp_path: Path, monkeypatch):
        """Handoff file includes in-progress tasks."""
        setup_session_project(tmp_path, monkeypatch)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['handoff'])
        assert result.exit_code == 0

        sessions_dir = tmp_path / "MPGA" / "sessions"
        files = [f for f in sessions_dir.iterdir() if f.name.endswith("-handoff.md")]
        content = files[0].read_text()

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
        """Creates session-log.md with first entry."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))
        (tmp_path / "MPGA" / "sessions").mkdir(parents=True, exist_ok=True)

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['log', 'Decided to use factory pattern'])
        assert result.exit_code == 0

        log_path = tmp_path / "MPGA" / "sessions" / "session-log.md"
        assert log_path.exists()

        content = log_path.read_text()
        assert "# Session Log" in content
        assert "Decided to use factory pattern" in content

    def test_appends_to_existing_log(self, tmp_path: Path, monkeypatch):
        """Appends to existing session-log.md."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))
        sessions_dir = tmp_path / "MPGA" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        (sessions_dir / "session-log.md").write_text(
            "# Session Log\n\n- 2026-01-01T00:00:00.000Z: First entry\n"
        )

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['log', 'Second entry here'])
        assert result.exit_code == 0

        content = (sessions_dir / "session-log.md").read_text()
        assert "First entry" in content
        assert "Second entry here" in content

        entry_lines = [line for line in content.split("\n") if line.startswith("- 20")]
        assert len(entry_lines) == 2


# ---------------------------------------------------------------------------
# Tests: session resume
# ---------------------------------------------------------------------------

class TestSessionResume:
    """session resume tests."""

    def test_shows_most_recent_handoff(self, tmp_path: Path, monkeypatch):
        """Shows most recent handoff content."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))
        sessions_dir = tmp_path / "MPGA" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        (sessions_dir / "2026-01-01-10-00-00-handoff.md").write_text(
            "# Session Handoff -- 2026-01-01\nOlder handoff content\n"
        )
        (sessions_dir / "2026-01-02-14-30-00-handoff.md").write_text(
            "# Session Handoff -- 2026-01-02\nLatest handoff content\n"
        )

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['resume'])
        assert result.exit_code == 0
        assert "Latest handoff content" in result.output
        assert "2026-01-02" in result.output

    def test_shows_info_when_no_handoffs(self, tmp_path: Path, monkeypatch):
        """Shows info message when no handoffs exist."""
        monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

        from mpga.commands.session import session

        runner = CliRunner()
        result = runner.invoke(session, ['resume'])
        assert result.exit_code == 0
        assert "No session handoffs found" in result.output


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
            assert agent.slug, f"Agent missing slug"
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
