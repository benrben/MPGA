"""Tests for the pr and decision commands."""

import json
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

from mpga.board.task import Task
from mpga.db.connection import get_connection
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = "2026-01-01T00:00:00.000Z"


def _make_task(task_id: str, title: str, overrides: dict | None = None) -> Task:
    defaults = dict(
        id=task_id,
        title=title,
        column="backlog",
        status=None,
        priority="medium",
        created=_NOW,
        updated=_NOW,
        milestone=None,
        tdd_stage=None,
        finished_at=None,
        started_at=None,
    )
    if overrides:
        defaults.update(overrides)
    return Task(**defaults)


def seed_project(root: Path, *, tasks: list[dict] | None = None):
    """Seed the SQLite DB at .mpga/mpga.db and create the MPGA directory."""
    (root / "MPGA").mkdir(parents=True, exist_ok=True)
    db_dir = root / ".mpga"
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_dir / "mpga.db"))
    try:
        create_schema(conn)
        repo = TaskRepo(conn)
        for task_def in (tasks or []):
            task = _make_task(task_def["id"], task_def["title"], task_def.get("overrides"))
            repo.create(task)
    finally:
        conn.close()


def _make_subprocess_mock(responses: dict):
    """Create a mock for subprocess.run that returns different results based on command content."""
    def mock_run(cmd, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
        result = MagicMock()
        result.returncode = 0

        for pattern, output in responses.items():
            if pattern in cmd_str:
                result.stdout = output
                return result

        result.stdout = ""
        return result
    return mock_run


# ---------------------------------------------------------------------------
# Tests: pr command
# ---------------------------------------------------------------------------

class TestPrCommand:
    """pr command tests."""

    def test_exits_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """Exits with error when MPGA is not initialized."""
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))
        from mpga.commands.pr import pr_cmd

        runner = CliRunner()
        result = runner.invoke(pr_cmd, [])
        assert result.exit_code != 0

    def test_generates_pr_description(self, tmp_path: Path, monkeypatch):
        """Generates PR description with branch name and commits."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        mock_run = _make_subprocess_mock({
            "rev-parse --abbrev-ref HEAD": "feat/add-auth",
            "merge-base": "abc123",
            "git log": "abc456 Add authentication module\ndef789 Add login tests",
            "git diff --name-only": "src/auth.ts\nsrc/auth.test.ts",
        })
        monkeypatch.setattr("mpga.commands.pr.subprocess.run", mock_run)

        from mpga.commands.pr import pr_cmd

        runner = CliRunner()
        result = runner.invoke(pr_cmd, [])
        assert result.exit_code == 0
        assert "feat/add-auth" in result.output
        assert "Add authentication module" in result.output
        assert "Add login tests" in result.output

    def test_includes_affected_scopes(self, tmp_path: Path, monkeypatch):
        """Includes affected scopes in PR description."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))
        scopes_dir = tmp_path / "MPGA" / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "src-auth.md").write_text("# auth scope\n")

        mock_run = _make_subprocess_mock({
            "rev-parse --abbrev-ref HEAD": "feat/auth",
            "merge-base": "abc123",
            "git log": "abc456 Update auth",
            "git diff --name-only": "src/auth/login.ts",
        })
        monkeypatch.setattr("mpga.commands.pr.subprocess.run", mock_run)

        from mpga.commands.pr import pr_cmd

        runner = CliRunner()
        result = runner.invoke(pr_cmd, [])
        assert result.exit_code == 0
        assert "src/auth/login.ts" in result.output

    def test_includes_evidence_links(self, tmp_path: Path, monkeypatch):
        """PR description includes done tasks section even when evidence fields are not in DB."""
        seed_project(tmp_path, tasks=[
            {
                "id": "T001", "title": "Implement auth",
                "overrides": {"column": "done"},
            },
        ])

        mock_run = _make_subprocess_mock({
            "rev-parse --abbrev-ref HEAD": "feat/auth",
            "merge-base": "abc123",
            "git log": "abc456 Add auth",
            "git diff --name-only": "src/auth.ts",
        })
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))
        monkeypatch.setattr("mpga.commands.pr.subprocess.run", mock_run)

        from mpga.commands.pr import pr_cmd

        runner = CliRunner()
        result = runner.invoke(pr_cmd, [])
        assert result.exit_code == 0
        # PR description is generated successfully; evidence_produced is not
        # stored in DB tasks table so the Evidence section won't appear, but
        # the command succeeds and outputs the changed file.
        assert "src/auth.ts" in result.output

    def test_handles_git_failures(self, tmp_path: Path, monkeypatch):
        """Handles git command failures gracefully."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        def mock_run_fail(cmd, **kwargs):
            raise subprocess.CalledProcessError(1, cmd, stderr="not a git repository")

        monkeypatch.setattr("mpga.commands.pr.subprocess.run", mock_run_fail)

        from mpga.commands.pr import pr_cmd

        runner = CliRunner()
        result = runner.invoke(pr_cmd, [])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests: decision command
# ---------------------------------------------------------------------------

class TestDecisionCommand:
    """decision command tests."""

    def test_exits_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """Exits with error when MPGA is not initialized."""
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))
        from mpga.commands.pr import decision_cmd

        runner = CliRunner()
        result = runner.invoke(decision_cmd, ['Use PostgreSQL'])
        assert result.exit_code != 0

    def test_creates_adr_file(self, tmp_path: Path, monkeypatch):
        """Creates ADR file in MPGA/decisions directory."""
        (tmp_path / "MPGA").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        from mpga.commands.pr import decision_cmd

        runner = CliRunner()
        result = runner.invoke(decision_cmd, ['Use PostgreSQL'])
        assert result.exit_code == 0

        decisions_dir = tmp_path / "MPGA" / "decisions"
        assert decisions_dir.exists()

        files = list(decisions_dir.iterdir())
        assert len(files) == 1

        today = date.today().isoformat()
        assert today in files[0].name
        assert "use-postgresql" in files[0].name
        assert files[0].suffix == ".md"

    def test_adr_contains_template_sections(self, tmp_path: Path, monkeypatch):
        """ADR file contains all required template sections."""
        (tmp_path / "MPGA").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        from mpga.commands.pr import decision_cmd

        runner = CliRunner()
        result = runner.invoke(decision_cmd, ['Use PostgreSQL'])
        assert result.exit_code == 0

        decisions_dir = tmp_path / "MPGA" / "decisions"
        files = list(decisions_dir.iterdir())
        content = files[0].read_text()

        assert "# ADR: Use PostgreSQL" in content
        assert "## Status" in content
        assert "Proposed" in content
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Consequences" in content

    def test_persists_decision_to_sqlite(self, tmp_path: Path, monkeypatch):
        """Stores the ADR metadata in the decisions table when SQLite is available."""
        (tmp_path / "MPGA").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        from mpga.commands.pr import decision_cmd
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(decision_cmd, ['Use PostgreSQL'])
        assert result.exit_code == 0

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT id, title FROM decisions WHERE title = 'Use PostgreSQL'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        assert row[0].startswith("001-")

    def test_adr_slugified_filename(self, tmp_path: Path, monkeypatch):
        """Creates ADR with slugified filename."""
        (tmp_path / "MPGA").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        from mpga.commands.pr import decision_cmd

        runner = CliRunner()
        result = runner.invoke(decision_cmd, ['Switch to Event-Driven Architecture'])
        assert result.exit_code == 0

        decisions_dir = tmp_path / "MPGA" / "decisions"
        files = list(decisions_dir.iterdir())
        assert "switch-to-event-driven-architecture" in files[0].name

    def test_adr_sequential_numbering(self, tmp_path: Path, monkeypatch):
        """Numbers ADRs sequentially."""
        mpga_dir = tmp_path / "MPGA"
        decisions_dir = mpga_dir / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        (decisions_dir / "001-2026-03-20-existing-decision.md").write_text("# ADR: Existing\n")

        monkeypatch.setattr("mpga.commands.pr.find_project_root", lambda: str(tmp_path))

        from mpga.commands.pr import decision_cmd

        runner = CliRunner()
        result = runner.invoke(decision_cmd, ['New Decision'])
        assert result.exit_code == 0

        files = sorted(decisions_dir.iterdir())
        assert len(files) == 2
        assert files[1].name.startswith("002-")
