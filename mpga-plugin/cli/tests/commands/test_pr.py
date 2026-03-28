"""Tests for the pr and decision commands."""

import json
import subprocess
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers (reused from metrics tests)
# ---------------------------------------------------------------------------

def make_board_json(overrides: dict | None = None) -> str:
    board = {
        "version": "1.0.0",
        "milestone": None,
        "updated": "2026-01-01T00:00:00.000Z",
        "columns": {"backlog": [], "todo": [], "in-progress": [], "testing": [], "review": [], "done": []},
        "stats": {
            "total": 0, "done": 0, "in_flight": 0, "blocked": 0,
            "progress_pct": 0, "evidence_produced": 0, "evidence_expected": 0,
        },
        "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
        "next_task_id": 1,
    }
    if overrides:
        board.update(overrides)
    return json.dumps(board, indent=2) + "\n"


def write_task_file(tasks_dir: Path, task_id: str, title: str, overrides: dict | None = None):
    slug = title.lower().replace(" ", "-")[:40].strip("-")
    filename = f"{task_id}-{slug}.md"
    now = "2026-01-01T00:00:00.000Z"
    defaults = {
        "id": task_id, "title": title, "status": "active", "column": "backlog",
        "priority": "medium", "milestone": None, "created": now, "updated": now,
        "assigned": None, "depends_on": [], "blocks": [], "scopes": [],
        "tdd_stage": None, "lane_id": None, "run_status": "queued",
        "current_agent": None, "file_locks": [], "scope_locks": [],
        "started_at": None, "finished_at": None, "heartbeat_at": None,
        "evidence_expected": [], "evidence_produced": [], "tags": [], "time_estimate": "5min",
    }
    if overrides:
        defaults.update(overrides)
    fm_lines = []
    for k, v in defaults.items():
        if isinstance(v, list):
            fm_lines.append(f"{k}: [{', '.join(json.dumps(i) for i in v)}]")
        elif v is None:
            fm_lines.append(f"{k}: null")
        elif isinstance(v, str):
            fm_lines.append(f"{k}: {json.dumps(v)}")
        else:
            fm_lines.append(f"{k}: {v}")
    body = f"# {task_id}: {title}\n\n## Description\nTest task\n"
    (tasks_dir / filename).write_text("---\n" + "\n".join(fm_lines) + "\n---\n\n" + body)


def seed_project(root: Path, *, milestone: str | None = None, tasks: list[dict] | None = None):
    board_dir = root / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "board.json").write_text(make_board_json({"milestone": milestone}))
    for task in (tasks or []):
        write_task_file(tasks_dir, task["id"], task["title"], task.get("overrides"))


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
        """Includes evidence links from done tasks."""
        seed_project(tmp_path, tasks=[
            {
                "id": "T001", "title": "Implement auth",
                "overrides": {
                    "column": "done",
                    "evidence_produced": ["[E] src/auth.ts -- login handler"],
                },
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
        assert "[E] src/auth.ts" in result.output

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
