from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from mpga.board.task import Task
from mpga.core.config import find_project_root
from mpga.core.logger import log, mini_banner
from mpga.db.connection import get_connection
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema

# ---------------------------------------------------------------------------
# metrics helpers
# ---------------------------------------------------------------------------


def _compute_metrics(tasks: list[Task]) -> dict:
    total = len(tasks)
    done = sum(1 for t in tasks if t.column == "done")
    in_progress = sum(
        1 for t in tasks if t.column in ("in-progress", "testing", "review")
    )
    blocked = sum(1 for t in tasks if t.status == "blocked")

    # Evidence coverage: produced / expected across all tasks
    evidence_expected = sum(len(t.evidence_expected) for t in tasks)
    evidence_produced = sum(len(t.evidence_produced) for t in tasks)
    evidence_coverage = (
        "0%"
        if evidence_expected == 0
        else f"{round((evidence_produced / evidence_expected) * 100)}%"
    )

    # TDD adherence: done tasks that completed tdd_stage=done / total done tasks
    done_tasks = [t for t in tasks if t.column == "done"]
    tdd_complete = sum(1 for t in done_tasks if t.tdd_stage == "done")
    tdd_adherence = (
        "0%"
        if len(done_tasks) == 0
        else f"{round((tdd_complete / len(done_tasks)) * 100)}%"
    )

    # Average task completion time
    avg_task_time: str | None = None
    completed_with_times = [
        t for t in done_tasks if t.started_at and t.finished_at
    ]
    if completed_with_times:
        total_ms = 0.0
        for t in completed_with_times:
            start = datetime.fromisoformat(t.started_at).timestamp() * 1000  # type: ignore[arg-type]
            end = datetime.fromisoformat(t.finished_at).timestamp() * 1000  # type: ignore[arg-type]
            total_ms += end - start
        avg_ms = total_ms / len(completed_with_times)
        hours = round(avg_ms / (1000 * 60 * 60))
        avg_task_time = "<1h" if hours < 1 else f"{hours}h"

    return {
        "total": total,
        "done": done,
        "in_progress": in_progress,
        "blocked": blocked,
        "evidence_coverage": evidence_coverage,
        "tdd_adherence": tdd_adherence,
        "avg_task_time": avg_task_time,
    }


def _load_reporting_tasks(project_root: Path) -> list[Task]:
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return []

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        db_tasks = TaskRepo(conn).filter()
    finally:
        conn.close()

    # Merge evidence fields from markdown task files when available
    tasks_dir = project_root / "MPGA" / "board" / "tasks"
    if tasks_dir.is_dir():
        from mpga.board.task import load_all_tasks
        md_tasks = load_all_tasks(str(tasks_dir))
        md_by_id = {t.id: t for t in md_tasks}
        merged: list[Task] = []
        for task in db_tasks:
            if task.id in md_by_id:
                md = md_by_id[task.id]
                # Supplement evidence fields from the markdown file
                task.evidence_expected = md.evidence_expected
                task.evidence_produced = md.evidence_produced
            merged.append(task)
        return merged

    return db_tasks


# ---------------------------------------------------------------------------
# metrics command group
# ---------------------------------------------------------------------------

# Canonical metric names exposed by `mpga metrics list`.
METRIC_NAMES: list[tuple[str, str]] = [
    ("total", "Total number of tasks on the board"),
    ("done", "Tasks in the 'done' column"),
    ("in_progress", "Tasks currently in-progress / testing / review"),
    ("blocked", "Tasks with status 'blocked'"),
    ("evidence_coverage", "Evidence links produced vs expected (%)"),
    ("tdd_adherence", "Done tasks that completed the full TDD cycle (%)"),
    ("avg_task_time", "Average wall-clock time from start to done"),
]


def _print_metrics_dashboard(project_root: Path, as_json: bool) -> None:
    """Shared display logic used by both the bare group and the legacy command."""
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        log.error("DB not found. Run `mpga sync` first.")
        sys.exit(1)

    tasks = _load_reporting_tasks(project_root)
    metrics = _compute_metrics(tasks)

    if as_json:
        click.echo(json.dumps(metrics, indent=2))
        return

    mini_banner()
    log.header("Project Metrics")

    log.section("  Task Summary")
    log.kv("Total tasks", str(metrics["total"]), 4)
    log.kv("Done", str(metrics["done"]), 4)
    log.kv("In-progress", str(metrics["in_progress"]), 4)
    log.kv("Blocked", str(metrics["blocked"]), 4)

    log.section("  Quality")
    log.kv("Evidence coverage", metrics["evidence_coverage"], 4)
    log.kv("TDD adherence", metrics["tdd_adherence"], 4)
    if metrics["avg_task_time"]:
        log.kv("Avg completion", metrics["avg_task_time"], 4)

    log.blank()


@click.group("metrics", invoke_without_command=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def metrics_group(ctx: click.Context, as_json: bool) -> None:
    """Compute and display project metrics."""
    if ctx.invoked_subcommand is None:
        project_root = Path(find_project_root() or Path.cwd())
        _print_metrics_dashboard(project_root, as_json)


# Backward-compatible alias — keeps existing `cli.py` registrations working.
metrics_cmd = metrics_group


@metrics_group.command("list")
def metrics_list() -> None:
    """List available metric names and descriptions."""
    log.header("Available Metrics")
    for name, description in METRIC_NAMES:
        log.kv(name, description, indent=2)
    log.blank()


# ---------------------------------------------------------------------------
# changelog command
# ---------------------------------------------------------------------------


@click.command("changelog")
@click.option("--since", default=None, help="Only include tasks completed after this date")
def changelog_cmd(since: str | None) -> None:
    """Generate changelog from completed tasks."""
    project_root = Path(find_project_root() or Path.cwd())

    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        log.error("DB not found. Run `mpga sync` first.")
        sys.exit(1)

    tasks = _load_reporting_tasks(project_root)

    done_tasks = [t for t in tasks if t.column == "done"]

    # Filter by --since date
    if since:
        since_ts = datetime.fromisoformat(since).timestamp()
        filtered: list[Task] = []
        for t in done_tasks:
            finished_ts = (
                datetime.fromisoformat(t.finished_at).timestamp()
                if t.finished_at
                else 0.0
            )
            if finished_ts >= since_ts:
                filtered.append(t)
        done_tasks = filtered

    if not done_tasks:
        log.info("No completed tasks found for changelog.")
        return

    # Group by milestone
    grouped: dict[str, list[Task]] = {}
    for task in done_tasks:
        key = task.milestone or "Unlinked"
        grouped.setdefault(key, []).append(task)

    # Output markdown
    today = datetime.now().isoformat().split("T")[0]
    click.echo(f"# Changelog \u2014 {today}")
    click.echo("")

    for milestone, mil_tasks in grouped.items():
        click.echo(f"## {milestone}")
        click.echo("")
        for task in mil_tasks:
            date = (
                datetime.fromisoformat(task.finished_at).isoformat().split("T")[0]
                if task.finished_at
                else task.updated.split("T")[0]
            )
            click.echo(f"- **{task.id}**: {task.title} ({date})")
            for ev in task.evidence_produced:
                click.echo(f"  - {ev}")
        click.echo("")
