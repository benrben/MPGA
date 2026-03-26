"""Click group for the ``mpga milestone`` command tree.

Mirrors the Commander-based milestone.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import click

from mpga.board.board import load_board, recalc_stats, save_board
from mpga.board.board_md import render_board_md
from mpga.core.config import find_project_root
from mpga.core.logger import console, log


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class MilestoneInfo:
    id: str
    name: str
    dir_path: str
    status: Literal["active", "complete", "planned"]
    created: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_milestones_dir(project_root: str) -> str:
    return str(Path(project_root) / "MPGA" / "milestones")


def _list_milestones(milestones_dir: str) -> list[MilestoneInfo]:
    p = Path(milestones_dir)
    if not p.exists():
        return []
    results: list[MilestoneInfo] = []
    for d in sorted(p.iterdir()):
        if not d.is_dir():
            continue
        if not re.match(r"^M\d+", d.name):
            continue
        m = re.match(r"^(M\d+)-(.+)", d.name)
        summary_path = d / "SUMMARY.md"
        results.append(
            MilestoneInfo(
                id=m.group(1) if m else d.name,
                name=m.group(2).replace("-", " ") if m else d.name,
                dir_path=str(d),
                status="complete" if summary_path.exists() else "active",
                created=datetime.fromtimestamp(d.stat().st_birthtime, tz=timezone.utc).strftime("%Y-%m-%d")
                if hasattr(d.stat(), "st_birthtime")
                else datetime.fromtimestamp(d.stat().st_ctime, tz=timezone.utc).strftime("%Y-%m-%d"),
            )
        )
    return results


def _next_milestone_id(milestones_dir: str) -> str:
    existing = _list_milestones(milestones_dir)
    nums: list[int] = []
    for m in existing:
        try:
            nums.append(int(m.id.replace("M", "")))
        except ValueError:
            pass
    max_num = max(nums) if nums else 0
    return f"M{str(max_num + 1).zfill(3)}"


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
    """Write SUMMARY, clear ``board.milestone``, save board + BOARD.md."""
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")
    board = load_board(board_dir)

    if not board.milestone:
        return CompleteMilestoneFail(ok=False, error="no_active_milestone")

    milestone_slug = board.milestone
    milestone_dir = Path(project_root) / "MPGA" / "milestones" / milestone_slug
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    recalc_stats(board, tasks_dir)
    (milestone_dir / "SUMMARY.md").write_text(
        f"# {milestone_slug} — Summary\n"
        "\n"
        f"## Completed: {today}\n"
        "\n"
        "## Stats\n"
        f"- Tasks completed: {board.stats.done}\n"
        f"- Evidence links produced: {board.stats.evidence_produced}\n"
        "\n"
        "## Outcome\n"
        "(describe what was delivered)\n",
        encoding="utf-8",
    )

    board.milestone = None
    save_board(board_dir, board)
    (Path(board_dir) / "BOARD.md").write_text(
        render_board_md(board, tasks_dir), encoding="utf-8"
    )

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
    milestones_dir = _get_milestones_dir(project_root)
    Path(milestones_dir).mkdir(parents=True, exist_ok=True)

    mid = _next_milestone_id(milestones_dir)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    slug = re.sub(r"^-|-$", "", slug)
    dir_name = f"{mid}-{slug}"
    dir_path = Path(milestones_dir) / dir_name

    dir_path.mkdir()

    now = datetime.now(timezone.utc).isoformat()
    today = now.split("T")[0]

    # PLAN.md
    (dir_path / "PLAN.md").write_text(
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
        f"{today}\n",
        encoding="utf-8",
    )

    # CONTEXT.md
    (dir_path / "CONTEXT.md").write_text(
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
        "| | | |\n",
        encoding="utf-8",
    )

    # Link milestone to board
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")
    board_json_path = Path(board_dir) / "board.json"
    if board_json_path.exists():
        board = load_board(board_dir)
        board.milestone = dir_name
        recalc_stats(board, tasks_dir)
        save_board(board_dir, board)
        (Path(board_dir) / "BOARD.md").write_text(
            render_board_md(board, tasks_dir), encoding="utf-8"
        )

    log.success(f"Created milestone {mid}: {name}")
    log.dim(f"  Directory: MPGA/milestones/{dir_name}/")
    log.dim("")
    log.dim("Next steps:")
    log.dim(f"  Edit MPGA/milestones/{dir_name}/PLAN.md")
    log.dim("  Run /mpga:plan to generate tasks")


# -- list -------------------------------------------------------------------


@milestone.command("list", help="List all milestones")
def milestone_list() -> None:
    project_root = find_project_root() or str(Path.cwd())
    milestones_dir = _get_milestones_dir(project_root)
    milestones = _list_milestones(milestones_dir)

    if not milestones:
        log.info('No milestones yet. Run `mpga milestone new "<name>"` to create one.')
        return

    log.header("Milestones")
    rows: list[list[str]] = [["ID", "Name", "Status", "Created"]]
    for m in milestones:
        status_label = "\u2705 complete" if m.status == "complete" else "\U0001f504 active"
        rows.append([m.id, m.name, status_label, m.created])
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
    log.dim(f"  Summary saved to MPGA/milestones/{slug}/SUMMARY.md")
    log.dim("  Run `mpga board archive` to archive done tasks.")
