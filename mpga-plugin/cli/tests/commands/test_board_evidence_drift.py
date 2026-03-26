"""Tests for board show, board add, board move, evidence verify/add, and drift commands."""

import json
from pathlib import Path

import pytest

from tests.conftest import write_file


# ---------------------------------------------------------------------------
# Helpers
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


def make_task_file(task_id: str, title: str, column: str = "backlog", priority: str = "medium") -> str:
    now = "2026-01-01T00:00:00.000Z"
    lines = [
        "---",
        f'id: "{task_id}"',
        f'title: "{title}"',
        f'status: "active"',
        f'column: "{column}"',
        f'priority: "{priority}"',
        "milestone: null",
        "phase: null",
        f'created: "{now}"',
        f'updated: "{now}"',
        "assigned: null",
        "depends_on: []",
        "blocks: []",
        "scopes: []",
        "tdd_stage: null",
        "evidence_expected: []",
        "evidence_produced: []",
        "tags: []",
        'time_estimate: "5min"',
        "---",
        "",
        f"# {task_id}: {title}",
        "",
    ]
    return "\n".join(lines)


def scaffold(tmp_path: Path):
    """Scaffold a minimal MPGA project with a source file and scope."""
    board_dir = tmp_path / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    scopes_dir = tmp_path / "MPGA" / "scopes"
    src_dir = tmp_path / "src"

    tasks_dir.mkdir(parents=True, exist_ok=True)
    scopes_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    (board_dir / "board.json").write_text(make_board_json())

    (src_dir / "utils.ts").write_text(
        "export function add(a: number, b: number): number {\n"
        "  return a + b;\n"
        "}\n"
        "\n"
        "export function subtract(a: number, b: number): number {\n"
        "  return a - b;\n"
        "}\n"
    )

    (scopes_dir / "core.md").write_text(
        "# Scope: core\n"
        "\n"
        "## Evidence\n"
        "[E] src/utils.ts:1-3 :: add()\n"
        "[E] src/utils.ts:5-7 :: subtract()\n"
        "\n"
        "## Known unknowns\n"
        "[Unknown] Need to investigate divide-by-zero handling\n"
    )


# ---------------------------------------------------------------------------
# Tests: board show
# ---------------------------------------------------------------------------

class TestBoardShow:
    """board show tests."""

    def test_displays_board_no_tasks(self, tmp_path: Path, monkeypatch, capsys):
        """Displays the board with no tasks."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_show

        handle_board_show()

        output = capsys.readouterr().out
        assert "Board" in output

    def test_displays_board_with_tasks(self, tmp_path: Path, monkeypatch, capsys):
        """Displays the board with tasks."""
        scaffold(tmp_path)
        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        (tasks_dir / "T001-setup-project.md").write_text(make_task_file("T001", "Setup project", "backlog"))
        board_dir = tmp_path / "MPGA" / "board"
        (board_dir / "board.json").write_text(make_board_json({
            "columns": {"backlog": ["T001"], "todo": [], "in-progress": [], "testing": [], "review": [], "done": []},
            "next_task_id": 2,
        }))

        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_show

        handle_board_show()

        output = capsys.readouterr().out
        assert "T001" in output
        assert "Setup project" in output

    def test_json_output(self, tmp_path: Path, monkeypatch, capsys):
        """Outputs JSON when --json is passed."""
        scaffold(tmp_path)
        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        (tasks_dir / "T001-setup.md").write_text(make_task_file("T001", "Setup", "backlog"))
        board_dir = tmp_path / "MPGA" / "board"
        (board_dir / "board.json").write_text(make_board_json({
            "columns": {"backlog": ["T001"], "todo": [], "in-progress": [], "testing": [], "review": [], "done": []},
            "next_task_id": 2,
        }))

        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_show

        handle_board_show(json_output=True)

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "board" in parsed
        assert "tasks" in parsed
        assert isinstance(parsed["tasks"], list)
        assert len(parsed["tasks"]) == 1
        assert parsed["tasks"][0]["id"] == "T001"


# ---------------------------------------------------------------------------
# Tests: board add
# ---------------------------------------------------------------------------

class TestBoardAdd:
    """board add tests."""

    def test_creates_new_task_defaults(self, tmp_path: Path, monkeypatch):
        """Creates a new task with default options."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_add

        handle_board_add("Implement feature X")

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        task_files = [f for f in tasks_dir.iterdir() if f.suffix == ".md"]
        assert len(task_files) == 1
        assert task_files[0].name.startswith("T001-")

        content = task_files[0].read_text()
        assert "Implement feature X" in content
        assert 'column: "backlog"' in content
        assert 'priority: "medium"' in content

        board_json = json.loads((tmp_path / "MPGA" / "board" / "board.json").read_text())
        assert board_json["next_task_id"] == 2
        assert "T001" in board_json["columns"]["backlog"]

    def test_creates_task_custom_options(self, tmp_path: Path, monkeypatch):
        """Creates a task with custom priority and column."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_add

        handle_board_add("Critical bugfix", priority="critical", column="todo")

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        task_files = [f for f in tasks_dir.iterdir() if f.suffix == ".md"]
        assert len(task_files) == 1

        content = task_files[0].read_text()
        assert 'priority: "critical"' in content
        assert 'column: "todo"' in content

        board_json = json.loads((tmp_path / "MPGA" / "board" / "board.json").read_text())
        assert "T001" in board_json["columns"]["todo"]

    def test_increments_task_ids(self, tmp_path: Path, monkeypatch):
        """Increments task IDs on successive adds."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_add

        handle_board_add("First task")
        handle_board_add("Second task")

        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        task_files = sorted(f.name for f in tasks_dir.iterdir() if f.suffix == ".md")
        assert len(task_files) == 2
        assert task_files[0].startswith("T001-")
        assert task_files[1].startswith("T002-")


# ---------------------------------------------------------------------------
# Tests: board move
# ---------------------------------------------------------------------------

class TestBoardMove:
    """board move tests."""

    def test_moves_task_between_columns(self, tmp_path: Path, monkeypatch, capsys):
        """Moves a task between columns."""
        scaffold(tmp_path)
        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        (tasks_dir / "T001-my-task.md").write_text(make_task_file("T001", "My task", "backlog"))
        board_dir = tmp_path / "MPGA" / "board"
        (board_dir / "board.json").write_text(make_board_json({
            "columns": {"backlog": ["T001"], "todo": [], "in-progress": [], "testing": [], "review": [], "done": []},
            "next_task_id": 2,
        }))

        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_move

        handle_board_move("T001", "todo")

        content = (tasks_dir / "T001-my-task.md").read_text()
        assert 'column: "todo"' in content

        board_json = json.loads((board_dir / "board.json").read_text())
        assert "T001" in board_json["columns"]["todo"]
        assert "T001" not in board_json["columns"]["backlog"]

    def test_regenerates_board_md(self, tmp_path: Path, monkeypatch):
        """Regenerates BOARD.md after move."""
        scaffold(tmp_path)
        tasks_dir = tmp_path / "MPGA" / "board" / "tasks"
        (tasks_dir / "T001-my-task.md").write_text(make_task_file("T001", "My task", "backlog"))
        board_dir = tmp_path / "MPGA" / "board"
        (board_dir / "board.json").write_text(make_board_json({
            "columns": {"backlog": ["T001"], "todo": [], "in-progress": [], "testing": [], "review": [], "done": []},
            "next_task_id": 2,
        }))

        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from mpga.commands.board_handlers import handle_board_move

        handle_board_move("T001", "done")

        board_md = (board_dir / "BOARD.md").read_text()
        assert "T001" in board_md
        assert "Done" in board_md


# ---------------------------------------------------------------------------
# Tests: evidence verify -- use CliRunner with click commands
# ---------------------------------------------------------------------------

class TestEvidenceVerify:
    """evidence verify tests."""

    def test_json_drift_report(self, tmp_path: Path, monkeypatch):
        """Returns valid drift report JSON with --json flag."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.evidence import evidence_verify

        runner = CliRunner()
        result = runner.invoke(evidence_verify, ["--json"])
        assert result.exit_code == 0
        report = json.loads(result.output)

        assert "timestamp" in report
        assert "project_root" in report
        assert "scopes" in report
        assert "overall_health_pct" in report
        assert "total_links" in report
        assert "valid_links" in report
        assert "ci_pass" in report
        assert "ci_threshold" in report
        assert isinstance(report["scopes"], list)

    def test_shows_health_percentage(self, tmp_path: Path, monkeypatch, capsys):
        """Shows health percentage in non-JSON mode."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.evidence import evidence_verify

        runner = CliRunner()
        result = runner.invoke(evidence_verify, [])
        assert "Evidence" in result.output


# ---------------------------------------------------------------------------
# Tests: evidence add -- use CliRunner with click commands
# ---------------------------------------------------------------------------

class TestEvidenceAdd:
    """evidence add tests."""

    def test_appends_evidence_link(self, tmp_path: Path, monkeypatch):
        """Appends evidence link to scope file."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.evidence import evidence_add

        runner = CliRunner()
        result = runner.invoke(evidence_add, ["core", "[E] src/utils.ts:10-15 :: multiply()"])

        content = (tmp_path / "MPGA" / "scopes" / "core.md").read_text()
        assert "[E] src/utils.ts:10-15 :: multiply()" in content

        known_index = content.index("## Known unknowns")
        link_index = content.index("[E] src/utils.ts:10-15 :: multiply()")
        assert link_index < known_index

    def test_adds_e_prefix(self, tmp_path: Path, monkeypatch):
        """Adds [E] prefix when link does not start with [."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.evidence import evidence_add

        runner = CliRunner()
        runner.invoke(evidence_add, ["core", "src/utils.ts:1-3"])

        content = (tmp_path / "MPGA" / "scopes" / "core.md").read_text()
        assert "[E] src/utils.ts:1-3" in content

    def test_errors_when_scope_missing(self, tmp_path: Path, monkeypatch):
        """Errors when scope does not exist."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.evidence import evidence_add

        runner = CliRunner()
        result = runner.invoke(evidence_add, ["nonexistent", "[E] src/foo.ts:1-5"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests: drift -- use CliRunner with click commands
# ---------------------------------------------------------------------------

class TestDrift:
    """drift command tests."""

    def test_json_report(self, tmp_path: Path, monkeypatch):
        """Returns valid report with --json flag."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.drift import drift

        runner = CliRunner()
        result = runner.invoke(drift, ["--json"])
        assert result.exit_code == 0
        report = json.loads(result.output)

        assert "timestamp" in report
        assert "project_root" in report
        assert "scopes" in report
        assert "overall_health_pct" in report
        assert "total_links" in report
        assert "valid_links" in report
        assert "ci_pass" in report
        assert "ci_threshold" in report
        assert isinstance(report["overall_health_pct"], (int, float))

    def test_quick_mode(self, tmp_path: Path, monkeypatch):
        """Shows minimal output with --quick flag."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.drift import drift

        runner = CliRunner()
        result = runner.invoke(drift, ["--quick"])
        assert "MPGA Drift Report" not in result.output

    def test_full_report(self, tmp_path: Path, monkeypatch):
        """Shows full report without --quick or --json."""
        scaffold(tmp_path)
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.drift import drift

        runner = CliRunner()
        result = runner.invoke(drift, ["--report"])
        assert "MPGA Drift Report" in result.output

    def test_reports_stale_links(self, tmp_path: Path, monkeypatch):
        """Reports stale links when source file is missing."""
        scaffold(tmp_path)
        (tmp_path / "src" / "utils.ts").unlink()
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.drift import drift

        runner = CliRunner()
        result = runner.invoke(drift, ["--json"])
        report = json.loads(result.output)

        assert report["total_links"] == 2
        assert report["valid_links"] == 0
        assert report["overall_health_pct"] == 0
        assert report["ci_pass"] is False

    def test_quick_mode_warns_on_stale(self, tmp_path: Path, monkeypatch):
        """Detects stale links with --quick and warns."""
        scaffold(tmp_path)
        (tmp_path / "src" / "utils.ts").unlink()
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.drift import drift

        runner = CliRunner()
        result = runner.invoke(drift, ["--quick"])
        assert "Drift detected" in result.output or "stale" in result.output

    def test_scope_filter(self, tmp_path: Path, monkeypatch):
        """Respects --scope filter."""
        scaffold(tmp_path)
        (tmp_path / "MPGA" / "scopes" / "other.md").write_text(
            "# Scope: other\n\n[E] src/nonexistent.ts:1-5\n"
        )
        monkeypatch.setattr("mpga.commands.board_handlers.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.evidence.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.drift.find_project_root", lambda: tmp_path)

        from click.testing import CliRunner
        from mpga.commands.drift import drift

        runner = CliRunner()
        result = runner.invoke(drift, ["--json", "--scope", "core"])
        report = json.loads(result.output)

        assert len(report["scopes"]) == 1
        assert report["scopes"][0]["scope"] == "core"
