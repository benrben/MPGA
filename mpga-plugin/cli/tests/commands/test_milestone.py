"""Tests for the milestone command."""

import json
from datetime import date
from pathlib import Path

from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_board_json(overrides: dict | None = None) -> str:
    """Create a board.json string."""
    board = {
        "version": "1.0.0",
        "milestone": None,
        "updated": "2026-01-01T00:00:00.000Z",
        "columns": {
            "backlog": [],
            "todo": [],
            "in-progress": [],
            "testing": [],
            "review": [],
            "done": [],
        },
        "stats": {
            "total": 0,
            "done": 0,
            "in_flight": 0,
            "blocked": 0,
            "progress_pct": 0,
            "evidence_produced": 0,
            "evidence_expected": 0,
        },
        "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
        "next_task_id": 1,
    }
    if overrides:
        board.update(overrides)
    return json.dumps(board, indent=2) + "\n"


def seed_project(
    root: Path,
    *,
    milestone: str | None = None,
    milestones: list[str] | None = None,
    with_summary: list[str] | None = None,
):
    """Seed a minimal MPGA project structure."""
    board_dir = root / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    milestones_dir = root / "MPGA" / "milestones"

    tasks_dir.mkdir(parents=True, exist_ok=True)
    milestones_dir.mkdir(parents=True, exist_ok=True)

    (board_dir / "board.json").write_text(make_board_json({"milestone": milestone}))
    (board_dir / "BOARD.md").write_text("# Board\n\nNo tasks yet.\n")

    for m in (milestones or []):
        (milestones_dir / m).mkdir(parents=True, exist_ok=True)

    for m in (with_summary or []):
        (milestones_dir / m / "SUMMARY.md").write_text(f"# {m} -- Summary\n")


# ---------------------------------------------------------------------------
# Tests: completeActiveMilestone
# ---------------------------------------------------------------------------

class TestCompleteActiveMilestone:
    """completeActiveMilestone tests."""

    def test_clears_board_milestone(self, tmp_path: Path):
        """Clears board.milestone and persists board.json after completion."""
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        milestone_dir = tmp_path / "MPGA" / "milestones" / "M001-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json({"milestone": "M001-test"}))

        from mpga.board.board import load_board
        from mpga.commands.milestone import complete_active_milestone

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is True
        assert result.milestone_slug == "M001-test"

        board = load_board(str(board_dir))
        assert board.milestone is None

        raw = json.loads((board_dir / "board.json").read_text())
        assert raw["milestone"] is None

    def test_writes_summary_md(self, tmp_path: Path):
        """Stores summary content in the DB summary column."""
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        milestone_dir = tmp_path / "MPGA" / "milestones" / "M001-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json({"milestone": "M001-test"}))

        from mpga.commands.milestone import complete_active_milestone
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is True

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT summary FROM milestones WHERE id = 'M001-test'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        body = row[0]
        assert "M001-test" in body
        assert "Tasks completed:" in body

    def test_returns_error_when_no_active_milestone(self, tmp_path: Path):
        """Returns error when no active milestone."""
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json({"milestone": None}))

        from mpga.commands.milestone import complete_active_milestone

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is False
        assert result.error == "no_active_milestone"

    def test_summary_includes_date_and_stats(self, tmp_path: Path):
        """DB summary column includes today date and stats."""
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        milestone_dir = tmp_path / "MPGA" / "milestones" / "M001-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json({"milestone": "M001-test"}))

        from mpga.commands.milestone import complete_active_milestone
        from mpga.db.connection import get_connection

        complete_active_milestone(str(tmp_path))

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT summary FROM milestones WHERE id = 'M001-test'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        body = row[0]
        today = date.today().isoformat()
        assert f"Completed: {today}" in body
        assert "Evidence links produced:" in body
        assert "Outcome" in body

    def test_regenerates_board_md(self, tmp_path: Path):
        """Regenerates BOARD.md after completion."""
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        milestone_dir = tmp_path / "MPGA" / "milestones" / "M001-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json({"milestone": "M001-test"}))

        from mpga.commands.milestone import complete_active_milestone

        complete_active_milestone(str(tmp_path))
        board_md_path = board_dir / "BOARD.md"
        assert board_md_path.exists()
        content = board_md_path.read_text()
        assert "No active milestone" in content

    def test_updates_sqlite_summary_and_status(self, tmp_path: Path):
        """Marks the milestone complete in SQLite and stores the summary."""
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        milestone_dir = tmp_path / "MPGA" / "milestones" / "M001-test"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        milestone_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json({"milestone": "M001-test"}))

        from mpga.commands.milestone import complete_active_milestone
        from mpga.db.connection import get_connection
        from mpga.db.repos.milestones import Milestone, MilestoneRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        MilestoneRepo(conn).create(Milestone(id="M001-test", name="Test milestone"))
        conn.close()

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is True

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT status, summary FROM milestones WHERE id = 'M001-test'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        assert row[0] == "completed"
        assert "Tasks completed:" in row[1]


# ---------------------------------------------------------------------------
# Tests: milestone new
# ---------------------------------------------------------------------------

class TestMilestoneNew:
    """registerMilestone -- milestone new."""

    def test_creates_plan_md(self, tmp_path: Path, monkeypatch):
        """Stores plan content in DB plan column."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_new
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(milestone_new, ["Auth Refactor"])
        assert result.exit_code == 0

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT plan FROM milestones WHERE id = 'M001-auth-refactor'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        content = row[0]
        assert "Auth Refactor" in content
        assert "Objective" in content
        assert "Tasks" in content
        assert "Acceptance criteria" in content

    def test_creates_context_md(self, tmp_path: Path, monkeypatch):
        """Stores context content in DB context column."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_new
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(milestone_new, ["Data Pipeline"])
        assert result.exit_code == 0

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT context FROM milestones WHERE id = 'M001-data-pipeline'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        content = row[0]
        assert "Data Pipeline" in content
        assert "Background" in content
        assert "Constraints" in content
        assert "Dependencies" in content
        assert "Decisions" in content

    def test_links_milestone_to_board(self, tmp_path: Path, monkeypatch):
        """Links the new milestone to the board."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.board.board import load_board
        from mpga.commands.milestone import milestone_new

        runner = CliRunner()
        result = runner.invoke(milestone_new, ["Test Link"])
        assert result.exit_code == 0

        board_dir = tmp_path / "MPGA" / "board"
        board = load_board(str(board_dir))
        assert board.milestone == "M001-test-link"

    def test_creates_sqlite_milestone_row(self, tmp_path: Path, monkeypatch):
        """Creates a milestone row in SQLite when the DB is available."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_new
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(milestone_new, ["SQLite milestone"])
        assert result.exit_code == 0

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT id, name, status FROM milestones WHERE id = 'M001-sqlite-milestone'"
            ).fetchone()
        finally:
            conn.close()

        assert row == ("M001-sqlite-milestone", "SQLite milestone", "active")

    def test_increments_milestone_ids(self, tmp_path: Path, monkeypatch):
        """Increments milestone IDs for subsequent milestones."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_new
        from mpga.db.connection import get_connection
        from mpga.db.repos.milestones import Milestone, MilestoneRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        MilestoneRepo(conn).create(Milestone(id="M001-first", name="First"))
        conn.close()

        runner = CliRunner()
        result = runner.invoke(milestone_new, ["Second"])
        assert result.exit_code == 0

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            rows = conn.execute(
                "SELECT id FROM milestones ORDER BY id"
            ).fetchall()
        finally:
            conn.close()

        ids = [r[0] for r in rows]
        assert "M001-first" in ids
        assert "M002-second" in ids


# ---------------------------------------------------------------------------
# Tests: milestone list
# ---------------------------------------------------------------------------

class TestMilestoneList:
    """registerMilestone -- milestone list."""

    def test_shows_info_when_no_milestones(self, tmp_path: Path, monkeypatch):
        """Shows info message when no milestones exist."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_list

        runner = CliRunner()
        result = runner.invoke(milestone_list, [])
        assert result.exit_code == 0

    def test_lists_active_milestones(self, tmp_path: Path, monkeypatch):
        """Lists active milestones with table output."""
        seed_project(tmp_path, milestones=["M001-alpha", "M002-beta"])
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_list

        runner = CliRunner()
        result = runner.invoke(milestone_list, [])
        assert result.exit_code == 0

    def test_marks_completed_milestones(self, tmp_path: Path, monkeypatch):
        """Marks completed milestones (those with SUMMARY.md) correctly."""
        seed_project(
            tmp_path,
            milestones=["M001-done-thing", "M002-active-thing"],
            with_summary=["M001-done-thing"],
        )
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_list

        runner = CliRunner()
        result = runner.invoke(milestone_list, [])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: milestone status
# ---------------------------------------------------------------------------

class TestMilestoneStatus:
    """registerMilestone -- milestone status."""

    def test_errors_when_no_board(self, tmp_path: Path, monkeypatch):
        """Exits with error when no board exists."""
        (tmp_path / "MPGA").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_status

        runner = CliRunner()
        result = runner.invoke(milestone_status, [])
        assert result.exit_code != 0

    def test_shows_info_when_no_active_milestone(self, tmp_path: Path, monkeypatch):
        """Shows info message when no active milestone."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_status

        runner = CliRunner()
        result = runner.invoke(milestone_status, [])
        assert result.exit_code == 0

    def test_shows_progress_for_active_milestone(self, tmp_path: Path, monkeypatch):
        """Shows progress for active milestone."""
        seed_project(tmp_path, milestone="M001-cool-feature")
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import milestone_status

        runner = CliRunner()
        result = runner.invoke(milestone_status, [])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Tests: milestone complete
# ---------------------------------------------------------------------------

class TestMilestoneComplete:
    """registerMilestone -- milestone complete."""

    def test_completes_active_milestone(self, tmp_path: Path, monkeypatch):
        """Completes an active milestone and stores summary in DB."""
        seed_project(tmp_path, milestone="M001-finish-me", milestones=["M001-finish-me"])
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.board.board import load_board
        from mpga.commands.milestone import complete_active_milestone
        from mpga.db.connection import get_connection

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is True

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT summary FROM milestones WHERE id = 'M001-finish-me'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        assert "Tasks completed:" in row[0]

        board = load_board(str(tmp_path / "MPGA" / "board"))
        assert board.milestone is None

    def test_errors_when_no_active_milestone(self, tmp_path: Path, monkeypatch):
        """Exits with error when no active milestone to complete."""
        seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.milestone.find_project_root", lambda: str(tmp_path))

        from mpga.commands.milestone import complete_active_milestone

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is False
