"""Click group for the ``mpga milestone`` command tree.

Mirrors the Commander-based milestone.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import click

from mpga.board.board import load_board, recalc_stats, save_board
from mpga.board.board_md import render_board_md
from mpga.core.config import find_project_root
from mpga.core.logger import console, log
from mpga.db.connection import get_connection
from mpga.db.repos.milestones import Milestone, MilestoneRepo
from mpga.db.schema import create_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _next_milestone_id(repo: MilestoneRepo) -> str:
    existing = repo.list_all()
    nums: list[int] = []
    for m in existing:
        try:
            # IDs are like "M001-slug" or "M001"
            raw = m.id.split("-")[0]
            nums.append(int(raw.replace("M", "")))
        except (ValueError, IndexError):
            pass
    max_num = max(nums) if nums else 0
    return f"M{str(max_num + 1).zfill(3)}"


def _open_milestone_repo(project_root: str) -> tuple[object, MilestoneRepo]:
    conn = get_connection(str(Path(project_root) / ".mpga" / "mpga.db"))
    create_schema(conn)
    return conn, MilestoneRepo(conn)


# ---------------------------------------------------------------------------
# Complete milestone (exported for use by other commands)
# ---------------------------------------------------------------------------


@dataclass
class CompleteMilestoneOk:
    ok: Literal[True]
    milestone_slug: str


@dataclass
class CompleteMilestoneFail:
    ok: Literal[False]
    error: str


CompleteMilestoneResult = CompleteMilestoneOk | CompleteMilestoneFail


def complete_active_milestone(project_root: str) -> CompleteMilestoneResult:
    """Clear ``board.milestone``, save board + BOARD.md, persist summary to DB."""
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")
    board = load_board(board_dir)

    if not board.milestone:
        return CompleteMilestoneFail(ok=False, error="no_active_milestone")

    milestone_slug = board.milestone
    today = date.today().isoformat()

    recalc_stats(board, tasks_dir)
    summary_content = (
        f"# {milestone_slug} — Summary\n"
        "\n"
        f"## Completed: {today}\n"
        "\n"
        "## Stats\n"
        f"- Tasks completed: {board.stats.done}\n"
        f"- Evidence links produced: {board.stats.evidence_produced}\n"
        "\n"
        "## Outcome\n"
        "(describe what was delivered)\n"
    )

    board.milestone = None
    save_board(board_dir, board)
    (Path(board_dir) / "BOARD.md").write_text(
        render_board_md(board, tasks_dir), encoding="utf-8"
    )

    conn, repo = _open_milestone_repo(project_root)
    try:
        milestone = repo.get(milestone_slug)
        if milestone is None:
            repo.create(
                Milestone(
                    id=milestone_slug,
                    name=milestone_slug,
                    status="completed",
                    summary=summary_content,
                    completed_at=datetime.now(UTC).isoformat(),
                )
            )
        else:
            milestone.status = "completed"
            milestone.summary = summary_content
            milestone.completed_at = datetime.now(UTC).isoformat()
            repo.update(milestone)
        conn.commit()
    finally:
        conn.close()

    return CompleteMilestoneOk(ok=True, milestone_slug=milestone_slug)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@click.group("milestone", help="Milestone workflow management")
def milestone() -> None:
    pass


# -- new --------------------------------------------------------------------


@milestone.command("new", help="Create a new milestone")
@click.argument("name")
def milestone_new(name: str) -> None:
    project_root = find_project_root() or str(Path.cwd())

    conn, repo = _open_milestone_repo(project_root)
    try:
        mid = _next_milestone_id(repo)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
        slug = re.sub(r"^-|-$", "", slug)
        milestone_id = f"{mid}-{slug}"

        today = datetime.now(UTC).isoformat().split("T")[0]

        plan_content = (
            f"# {mid}: {name} — Plan\n"
            "\n"
            "## Objective\n"
            "(describe what this milestone achieves)\n"
            "\n"
            "## Tasks\n"
            "(run `/mpga:plan` to generate evidence-based tasks)\n"
            "\n"
            "## Acceptance criteria\n"
            "- [ ] (define criteria)\n"
            "\n"
            "## Created\n"
            f"{today}\n"
        )

        context_content = (
            f"# {mid}: {name} — Context\n"
            "\n"
            "## Background\n"
            "(why this milestone, what problem it solves)\n"
            "\n"
            "## Constraints\n"
            "- (list constraints)\n"
            "\n"
            "## Dependencies\n"
            "- (list external dependencies)\n"
            "\n"
            "## Decisions\n"
            "| Decision | Rationale | Date |\n"
            "|----------|-----------|------|\n"
            "| | | |\n"
        )

        repo.create(
            Milestone(
                id=milestone_id,
                name=name,
                status="active",
                plan=plan_content,
                context=context_content,
            )
        )
        conn.commit()
    finally:
        conn.close()

    # Link milestone to board
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")
    board_json_path = Path(board_dir) / "board.json"
    if board_json_path.exists():
        board = load_board(board_dir)
        board.milestone = milestone_id
        recalc_stats(board, tasks_dir)
        save_board(board_dir, board)
        (Path(board_dir) / "BOARD.md").write_text(
            render_board_md(board, tasks_dir), encoding="utf-8"
        )

    log.success(f"Created milestone {mid}: {name}")
    log.dim(f"  ID: {milestone_id}")
    log.dim("")
    log.dim("Next steps:")
    log.dim("  Run /mpga:plan to generate tasks")


# -- list -------------------------------------------------------------------


@milestone.command("list", help="List all milestones")
def milestone_list() -> None:
    project_root = find_project_root() or str(Path.cwd())
    conn, repo = _open_milestone_repo(project_root)
    try:
        db_milestones = repo.list_all()
    finally:
        conn.close()

    if not db_milestones:
        log.info('No milestones yet. Run `mpga milestone new "<name>"` to create one.')
        return

    log.header("Milestones")
    rows: list[list[str]] = [["ID", "Name", "Status", "Created"]]
    for milestone in db_milestones:
        status_label = (
            "\u2705 complete"
            if milestone.status.startswith("complete")
            else "\U0001f504 active"
        )
        created = milestone.created_at.split("T")[0] if milestone.created_at else "?"
        rows.append([milestone.id, milestone.name, status_label, created])
    log.table(rows)


# -- status -----------------------------------------------------------------


@milestone.command("status", help="Show current milestone progress")
def milestone_status() -> None:
    project_root = find_project_root() or str(Path.cwd())
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    if not (Path(board_dir) / "board.json").exists():
        log.error("No board found. Run `mpga init` first.")
        sys.exit(1)

    board = load_board(board_dir)
    recalc_stats(board, tasks_dir)

    if not board.milestone:
        log.info('No active milestone. Run `mpga milestone new "<name>"` to create one.')
        return

    log.header(f"Milestone: {board.milestone}")
    stats = board.stats
    console.print(f"  Progress:    {stats.done}/{stats.total} tasks ({stats.progress_pct}%)")
    console.print(f"  In flight:   {stats.in_flight}")
    console.print(f"  Blocked:     {stats.blocked}")
    console.print(f"  Evidence:    {stats.evidence_produced}/{stats.evidence_expected} links")


# -- complete ---------------------------------------------------------------


@milestone.command("complete", help="Archive milestone and mark as complete")
def milestone_complete() -> None:
    project_root = find_project_root() or str(Path.cwd())
    result = complete_active_milestone(project_root)

    if not result.ok:
        log.error("No active milestone to complete.")
        sys.exit(1)

    slug = result.milestone_slug  # type: ignore[union-attr]

    log.success(f"Milestone '{slug}' marked complete.")
    log.dim("  Summary stored in DB (mpga milestone list to verify)")
    log.dim("  Run `mpga board archive` to archive done tasks.")
