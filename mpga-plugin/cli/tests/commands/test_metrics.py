"""Tests for the metrics and changelog commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import write_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_board_json(overrides: dict | None = None) -> str:
    board = {
        "version": "1.0.0",
        "milestone": "M001-test",
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
    """Write a task file with frontmatter."""
    slug = title.lower()
    for ch in " /\\?#":
        slug = slug.replace(ch, "-")
    slug = slug[:40].strip("-")
    filename = f"{task_id}-{slug}.md"
    now = "2026-01-01T00:00:00.000Z"
    defaults = {
        "id": task_id,
        "title": title,
        "status": "active",
        "column": "backlog",
        "priority": "medium",
        "milestone": None,
        "phase": None,
        "created": now,
        "updated": now,
        "assigned": None,
        "depends_on": [],
        "blocks": [],
        "scopes": [],
        "tdd_stage": None,
        "lane_id": None,
        "run_status": "queued",
        "current_agent": None,
        "file_locks": [],
        "scope_locks": [],
        "started_at": None,
        "finished_at": None,
        "heartbeat_at": None,
        "evidence_expected": [],
        "evidence_produced": [],
        "tags": [],
        "time_estimate": "5min",
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
    content = f"---\n" + "\n".join(fm_lines) + "\n---\n\n" + body
    (tasks_dir / filename).write_text(content)


def seed_project(root: Path, *, milestone: str | None = None, tasks: list[dict] | None = None):
    board_dir = root / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / "board.json").write_text(make_board_json({"milestone": milestone}))
    for task in (tasks or []):
        write_task_file(tasks_dir, task["id"], task["title"], task.get("overrides"))


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
        """Shows evidence coverage."""
        seed_project(tmp_path, tasks=[
            {
                "id": "T001", "title": "Covered task",
                "overrides": {
                    "column": "done",
                    "evidence_expected": ["[E] foo.ts"],
                    "evidence_produced": ["[E] foo.ts"],
                },
            },
            {
                "id": "T002", "title": "Uncovered task",
                "overrides": {
                    "column": "todo",
                    "evidence_expected": ["[E] bar.ts"],
                    "evidence_produced": [],
                },
            },
        ])
        monkeypatch.setattr("mpga.commands.metrics.find_project_root", lambda: str(tmp_path))

        from mpga.commands.metrics import metrics_cmd

        runner = CliRunner()
        result = runner.invoke(metrics_cmd, ['--json'])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["evidence_coverage"] == "50%"

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
        seed_project(tmp_path, milestone="M001-release", tasks=[
            {
                "id": "T001", "title": "Add auth",
                "overrides": {
                    "column": "done",
                    "milestone": "M001-release",
                    "evidence_produced": ["[E] auth.ts"],
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
        assert "[E] auth.ts" in result.output

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
