"""Tests for the metrics and changelog commands."""

import json
from pathlib import Path

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
    """Seed the SQLite DB at .mpga/mpga.db with the given tasks."""
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


# ---------------------------------------------------------------------------
# Tests: metrics command
# ---------------------------------------------------------------------------

class TestMetricsCommand:
    """metrics command -- HUGE numbers, the BEST metrics."""

    def test_exits_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """Exits with error when MPGA is not initialized."""
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))
        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, [])
        assert result.exit_code != 0

    def test_shows_total_task_counts(self, tmp_path: Path, monkeypatch):
        """Shows total task counts."""
        seed_project(tmp_path, tasks=[
            {"id": "T001", "title": "First task", "overrides": {"column": "done"}},
            {"id": "T002", "title": "Second task", "overrides": {"column": "in-progress"}},
            {"id": "T003", "title": "Third task", "overrides": {"column": "backlog", "status": "blocked"}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, ['--json'])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["total"] == 3
        assert parsed["done"] == 1

    def test_shows_evidence_coverage(self, tmp_path: Path, monkeypatch):
        """Shows evidence coverage (always 0% since evidence fields are not stored in DB tasks table)."""
        seed_project(tmp_path, tasks=[
            {"id": "T001", "title": "Covered task", "overrides": {"column": "done"}},
            {"id": "T002", "title": "Uncovered task", "overrides": {"column": "todo"}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, ['--json'])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        # evidence_expected/produced are not stored in the DB tasks table,
        # so coverage is always 0% when reading from DB.
        assert parsed["evidence_coverage"] == "0%"

    def test_shows_tdd_adherence(self, tmp_path: Path, monkeypatch):
        """Shows TDD adherence."""
        seed_project(tmp_path, tasks=[
            {"id": "T001", "title": "Full TDD", "overrides": {"column": "done", "tdd_stage": "done"}},
            {"id": "T002", "title": "Partial TDD", "overrides": {"column": "done", "tdd_stage": "green"}},
            {"id": "T003", "title": "Not started", "overrides": {"column": "backlog", "tdd_stage": None}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, ['--json'])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["tdd_adherence"] == "50%"

    def test_json_output(self, tmp_path: Path, monkeypatch):
        """Outputs JSON when --json flag is passed."""
        seed_project(tmp_path, tasks=[
            {"id": "T001", "title": "Task one", "overrides": {"column": "done"}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, ['--json'])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["total"] == 1
        assert parsed["done"] == 1

    def test_handles_empty_board(self, tmp_path: Path, monkeypatch):
        """Handles empty board gracefully."""
        seed_project(tmp_path, tasks=[])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, ['--json'])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["total"] == 0
        assert parsed["evidence_coverage"] == "0%"


# ---------------------------------------------------------------------------
# Tests: changelog command
# ---------------------------------------------------------------------------

class TestChangelogCommand:
    """changelog command -- documenting our TREMENDOUS victories."""

    def test_exits_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """Exits with error when MPGA is not initialized."""
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))
        from mpga.commands.metrics import changelog_cmd

        runner = CliRunner()
        result = runner.invoke(changelog_cmd, [])
        assert result.exit_code != 0

    def test_generates_changelog(self, tmp_path: Path, monkeypatch):
        """Generates changelog from done tasks."""
        seed_project(tmp_path, tasks=[
            {
                "id": "T001", "title": "Add auth",
                "overrides": {
                    "column": "done",
                    "milestone": "M001-release",
                    "finished_at": "2026-03-20T10:00:00.000Z",
                },
            },
            {"id": "T002", "title": "WIP task", "overrides": {"column": "in-progress"}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import changelog_cmd

        runner = CliRunner()
        result = runner.invoke(changelog_cmd, [])
        assert result.exit_code == 0
        assert "Add auth" in result.output

    def test_filters_by_since_date(self, tmp_path: Path, monkeypatch):
        """Filters tasks by --since date."""
        seed_project(tmp_path, tasks=[
            {
                "id": "T001", "title": "Old task",
                "overrides": {"column": "done", "finished_at": "2026-01-01T10:00:00.000Z"},
            },
            {
                "id": "T002", "title": "Recent task",
                "overrides": {"column": "done", "finished_at": "2026-03-20T10:00:00.000Z"},
            },
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import changelog_cmd

        runner = CliRunner()
        result = runner.invoke(changelog_cmd, ['--since', '2026-03-01'])
        assert result.exit_code == 0
        assert "Recent task" in result.output
        assert "Old task" not in result.output

    def test_groups_by_milestone(self, tmp_path: Path, monkeypatch):
        """Groups done tasks by milestone."""
        seed_project(tmp_path, tasks=[
            {"id": "T001", "title": "Milestone A task", "overrides": {"column": "done", "milestone": "M001-alpha"}},
            {"id": "T002", "title": "Milestone B task", "overrides": {"column": "done", "milestone": "M002-beta"}},
            {"id": "T003", "title": "No milestone task", "overrides": {"column": "done"}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import changelog_cmd

        runner = CliRunner()
        result = runner.invoke(changelog_cmd, [])
        assert result.exit_code == 0
        assert "M001-alpha" in result.output
        assert "M002-beta" in result.output
        assert "Unlinked" in result.output

    def test_shows_message_when_no_done_tasks(self, tmp_path: Path, monkeypatch):
        """Shows message when no tasks are done yet."""
        seed_project(tmp_path, tasks=[
            {"id": "T001", "title": "Active task", "overrides": {"column": "in-progress"}},
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import changelog_cmd

        runner = CliRunner()
        result = runner.invoke(changelog_cmd, [])
        assert result.exit_code == 0
        assert "No completed tasks" in result.output
