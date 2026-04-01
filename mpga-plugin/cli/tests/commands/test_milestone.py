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

    # test_regenerates_board_md removed by T019 — milestone commands no longer write BOARD.md.
    # The opposite behavior is now enforced by TestT019NoBoardMdWrites.

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
        assert row[0] == "archived"
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


# ---------------------------------------------------------------------------
# Tests: T019 — Remove BOARD.md writes from milestone commands
#
# Coverage checklist for: T019 — Tier 1 — Remove BOARD.md writes
#
# Acceptance criteria → Test status
# ──────────────────────────────────
# [x] AC1: complete_active_milestone() no longer writes BOARD.md
#          → it('does not write BOARD.md when completing a milestone')
# [x] AC2: milestone_new() no longer writes BOARD.md
#          → it('does not write BOARD.md when creating a new milestone')
# [x] AC3: grep for BOARD.md write in milestone.py returns zero results
#          → structural/static (confirmed by green-dev)
# [ ] AC4: Milestone commands complete without error
#          → covered by existing exit_code == 0 tests above
#
# Untested branches / edge cases:
# - [ ] board.json absent: milestone_new() skips board link entirely (no BOARD.md created)
# - [ ] pre-existing BOARD.md is NOT modified by either command
#
# Evidence:
#   [E] mpga-plugin/cli/src/mpga/commands/milestone.py — BOARD.md writes removed by T019
#       complete_active_milestone() and milestone_new() no longer write BOARD.md
# ---------------------------------------------------------------------------


class TestT019NoBoardMdWrites:
    """T019: milestone commands must not write BOARD.md."""

    def test_complete_active_milestone_does_not_write_board_md(self, tmp_path: Path):
        """complete_active_milestone() must not create or overwrite BOARD.md.

        Evidence: [E] mpga-plugin/cli/src/mpga/commands/milestone.py — BOARD.md write removed
        Asserts that BOARD.md is never created by complete_active_milestone().
        """
        # Arrange — board with an active milestone, no BOARD.md present
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(
            make_board_json({"milestone": "M001-test"})
        )
        board_md_path = board_dir / "BOARD.md"
        assert not board_md_path.exists(), "pre-condition: BOARD.md must be absent"

        # Act
        from mpga.commands.milestone import complete_active_milestone

        result = complete_active_milestone(str(tmp_path))

        # Assert — command succeeds AND no BOARD.md was created
        assert result.ok is True
        assert not board_md_path.exists(), (
            "complete_active_milestone() must not write BOARD.md"
        )

    def test_milestone_new_does_not_write_board_md(self, tmp_path: Path, monkeypatch):
        """milestone_new() must not create or overwrite BOARD.md.

        Evidence: [E] mpga-plugin/cli/src/mpga/commands/milestone.py — BOARD.md write removed
        Asserts that BOARD.md is never created by milestone_new().
        """
        # Arrange — minimal project with board.json but NO BOARD.md
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(make_board_json())
        board_md_path = board_dir / "BOARD.md"
        assert not board_md_path.exists(), "pre-condition: BOARD.md must be absent"

        monkeypatch.setattr(
            "mpga.commands.milestone.find_project_root", lambda: str(tmp_path)
        )

        # Act
        from click.testing import CliRunner

        from mpga.commands.milestone import milestone_new

        runner = CliRunner()
        result = runner.invoke(milestone_new, ["No Board Md"])

        # Assert — command exits cleanly AND no BOARD.md was created
        assert result.exit_code == 0
        assert not board_md_path.exists(), (
            "milestone_new() must not write BOARD.md"
        )


# ---------------------------------------------------------------------------
# Tests: T022 — Replace os.rename archive with DB status update
#
# Coverage checklist for: T022 — Replace os.rename archive with DB status update
#
# Acceptance criteria → Test status
# ──────────────────────────────────
# [x] AC1: complete_active_milestone() does NOT rename/move any directory
#          → test_no_directory_rename_on_completion (regression guard)
# [x] AC2: After completion, milestone status in DB is 'archived'
#          → test_milestone_status_is_archived_in_db  ← RED (current code sets 'completed')
# [x] AC3: The function still returns CompleteMilestoneOk (no regression)
#          → test_returns_complete_milestone_ok (degenerate regression guard)
# [ ] AC4: Existing 20 milestone tests still pass
#          → green-dev responsibility; no new test needed
#
# Untested branches / edge cases:
# - [ ] milestone directory absent: no rename attempted, no FileNotFoundError raised
# - [ ] milestone already has status 'archived' before call: idempotent update
#
# Evidence:
#   [E] mpga-plugin/cli/src/mpga/commands/milestone.py:70-121 :: complete_active_milestone()
#   Current code uses status="completed" (line 110, 113). T022 requires status="archived".
# ---------------------------------------------------------------------------


class TestT022NoRename:
    """T022: complete_active_milestone() uses DB status update, not os.rename."""

    # -----------------------------------------------------------------------
    # TPP step 1 (degenerate): regression guard — function still returns Ok
    # -----------------------------------------------------------------------

    def test_returns_complete_milestone_ok(self, tmp_path: Path):
        """complete_active_milestone() returns CompleteMilestoneOk after T022 changes.

        Evidence: [E] mpga-plugin/cli/src/mpga/commands/milestone.py:70-121
        Degenerate regression guard — the return type must not change.
        """
        # Arrange
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(
            make_board_json({"milestone": "M001-t022"})
        )

        # Act
        from mpga.commands.milestone import CompleteMilestoneOk, complete_active_milestone

        result = complete_active_milestone(str(tmp_path))

        # Assert
        assert isinstance(result, CompleteMilestoneOk)
        assert result.ok is True
        assert result.milestone_slug == "M001-t022"

    # -----------------------------------------------------------------------
    # TPP step 2 (constant): no directory was renamed or moved
    # -----------------------------------------------------------------------

    def test_no_directory_rename_on_completion(self, tmp_path: Path):
        """complete_active_milestone() must not rename or move any directory.

        Evidence: [E] mpga-plugin/cli/src/mpga/commands/milestone.py:70-121
        The milestone source directory (if present) must remain at its original
        location after the call — no os.rename / shutil.move must have occurred.
        """
        # Arrange — create a milestone directory that would be a rename target
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        milestones_dir = tmp_path / "MPGA" / "milestones"
        source_dir = milestones_dir / "M001-t022"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(
            make_board_json({"milestone": "M001-t022"})
        )
        archive_dir = milestones_dir / "archive" / "M001-t022"

        # Act
        from mpga.commands.milestone import complete_active_milestone

        result = complete_active_milestone(str(tmp_path))

        # Assert — source must still exist, archive must NOT have been created
        assert result.ok is True
        assert source_dir.exists(), (
            "milestone directory must not have been renamed away"
        )
        assert not archive_dir.exists(), (
            "complete_active_milestone() must not create an archive directory"
        )

    # -----------------------------------------------------------------------
    # TPP step 3 (variable): DB status is 'archived' after completion
    # -----------------------------------------------------------------------

    def test_milestone_status_is_archived_in_db(self, tmp_path: Path):
        """After complete_active_milestone(), milestone status in DB must be 'archived'.

        Evidence: [E] mpga-plugin/cli/src/mpga/commands/milestone.py:110-116
        T022 requires status='archived'. Current production code sets 'completed',
        so this test is RED until green-dev makes the change.
        """
        # Arrange
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        (board_dir / "board.json").write_text(
            make_board_json({"milestone": "M001-t022"})
        )

        # Act
        from mpga.commands.milestone import complete_active_milestone
        from mpga.db.connection import get_connection

        result = complete_active_milestone(str(tmp_path))
        assert result.ok is True

        # Assert — status column must be 'archived'
        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT status FROM milestones WHERE id = 'M001-t022'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "milestone row must exist in DB"
        assert row[0] == "archived", (
            f"expected status='archived', got status='{row[0]}' — "
            "T022 requires DB status update to 'archived', not 'completed'"
        )
