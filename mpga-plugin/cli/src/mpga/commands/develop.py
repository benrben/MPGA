"""Click group for the ``mpga develop`` command tree.

Mirrors the Commander-based develop.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import click

from mpga.board.board import find_task_file, load_board
from mpga.board.task import Task, parse_task_file, render_task_file
from mpga.commands.board_handlers import persist_board
from mpga.commands.develop_scheduler import run_develop_task
from mpga.commands.develop_service import DevelopService
from mpga.core.config import find_project_root
from mpga.core.logger import console, log

# Fields copied from a db_task onto a file_task during merge.
# Uses a tuple so the set is immutable and iteration order is stable.
MERGE_FIELDS: tuple[str, ...] = (
    "column", "status", "priority", "assigned", "tdd_stage",
    "lane_id", "run_status", "current_agent",
    "started_at", "finished_at", "heartbeat_at",
    "scopes", "tags", "depends_on",
    "file_locks", "scope_locks",
    "milestone", "phase", "time_estimate",
)

# -- Helpers ----------------------------------------------------------------


def _merge_task_state(primary_task: Task, db_task: Task) -> Task:
    """Copy mutable state fields from *db_task* onto *primary_task*."""
    for field_name in MERGE_FIELDS:
        setattr(primary_task, field_name, getattr(db_task, field_name))
    return primary_task


def _load_task_or_raise(project_root: Path, tasks_dir: str, task_id: str):
    task_file = find_task_file(tasks_dir, task_id)
    file_task = parse_task_file(task_file) if task_file else None

    svc = DevelopService.from_project_root(project_root)
    db_task = None
    if svc is not None:
        try:
            db_task = svc.get_task(task_id)
        finally:
            svc.close()

    if file_task and db_task:
        return task_file, _merge_task_state(file_task, db_task)
    if file_task:
        return task_file, file_task
    if db_task:
        return None, db_task
    raise click.ClickException(f"Task '{task_id}' not found")


def _persist_task_state(project_root: Path, task_file: str | None, task) -> None:
    if task_file:
        Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    svc = DevelopService.from_project_root(project_root)
    if svc is None:
        return

    try:
        svc.persist_task_state(task)
    finally:
        svc.close()


# -- Handlers ---------------------------------------------------------------


def handle_develop_status(task_id: str) -> None:
    project_root = Path(find_project_root() or Path.cwd())
    tasks_dir = str(project_root / ".mpga" / "board" / "tasks")

    task_file, task = _load_task_or_raise(project_root, tasks_dir, task_id)

    log.header(f"Develop Status: {task.id}")
    console.print(f"  Title:         {task.title}")
    console.print(f"  Column:        {task.column}")
    console.print(f"  TDD Stage:     {task.tdd_stage or '(none)'}")
    console.print(f"  Run Status:    {task.run_status}")
    console.print(f"  Lane:          {task.lane_id or '(none)'}")
    console.print(f"  Agent:         {task.current_agent or '(none)'}")

    if task.file_locks:
        console.print("  File Locks:")
        for lock in task.file_locks:
            console.print(f"    - {lock.path} ({lock.agent}, lane: {lock.lane_id})")

    if task.scope_locks:
        console.print("  Scope Locks:")
        for lock in task.scope_locks:
            console.print(f"    - {lock.scope} ({lock.agent}, lane: {lock.lane_id})")

    if task.started_at:
        console.print(f"  Started:       {task.started_at}")
    if task.finished_at:
        console.print(f"  Finished:      {task.finished_at}")


def handle_develop_abort(task_id: str) -> None:
    project_root = Path(find_project_root() or Path.cwd())
    board_dir = str(project_root / ".mpga" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    task_file, task = _load_task_or_raise(project_root, tasks_dir, task_id)

    # Release all locks
    task.file_locks = []
    task.scope_locks = []
    task.current_agent = None
    task.lane_id = None
    task.run_status = "queued"
    task.heartbeat_at = None

    # Move task back to todo
    task.column = "todo"
    task.updated = datetime.now(UTC).isoformat()

    _persist_task_state(project_root, task_file, task)

    # Update board columns
    board = load_board(board_dir)
    persist_board(board, board_dir, tasks_dir)

    log.success(f"{task_id} aborted — locks released, moved to todo")


def handle_develop_resume(task_id: str) -> None:
    project_root = Path(find_project_root() or Path.cwd())
    board_dir = str(project_root / ".mpga" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    task_file, task = _load_task_or_raise(project_root, tasks_dir, task_id)

    # Resume: move to in-progress, set running
    task.column = "in-progress"
    task.run_status = "running"
    task.updated = datetime.now(UTC).isoformat()

    _persist_task_state(project_root, task_file, task)

    # Update board columns
    board = load_board(board_dir)
    persist_board(board, board_dir, tasks_dir)

    log.success(f"{task_id} resumed from TDD stage: {task.tdd_stage or '(none)'}")


# -- Registration -----------------------------------------------------------


@click.group("develop", help="Execute a task through the develop scheduler")
def develop() -> None:
    pass


@develop.command("run", help="Execute a task through the develop scheduler")
@click.argument("task_id")
@click.option("--parallel", "parallel", default="auto", help="Parallel scheduling mode")
@click.option("--lanes", "lanes", type=int, default=None, help="Maximum number of parallel lanes")
@click.option("--dashboard", is_flag=True, default=False, help="Refresh live board artifacts during scheduling")
def develop_run(task_id: str, parallel: str, lanes: int | None, dashboard: bool) -> None:
    run_develop_task(task_id, parallel=parallel, lanes=lanes, dashboard=dashboard)


@develop.command("status", help="Show current TDD stage, lane status, and file locks")
@click.argument("task_id")
def develop_status(task_id: str) -> None:
    handle_develop_status(task_id)


@develop.command("abort", help="Release all locks and move task back to todo")
@click.argument("task_id")
def develop_abort(task_id: str) -> None:
    handle_develop_abort(task_id)


@develop.command("resume", help="Resume task from last TDD stage")
@click.argument("task_id")
def develop_resume(task_id: str) -> None:
    handle_develop_resume(task_id)
