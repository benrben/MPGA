"""Click group for the ``mpga develop`` command tree.

Mirrors the Commander-based develop.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from mpga.board.board import find_task_file, load_board
from mpga.board.task import parse_task_file, render_task_file
from mpga.commands.board_handlers import persist_board
from mpga.commands.develop_scheduler import run_develop_task
from mpga.core.config import find_project_root
from mpga.core.logger import console, log


# -- Handlers ---------------------------------------------------------------


def handle_develop_status(task_id: str) -> None:
    project_root = find_project_root() or str(Path.cwd())
    tasks_dir = str(Path(project_root) / "MPGA" / "board" / "tasks")

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        raise click.ClickException(f"Task '{task_id}' not found")

    task = parse_task_file(task_file)
    if not task:
        raise click.ClickException(f"Could not parse task '{task_id}'")

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
    project_root = find_project_root() or str(Path.cwd())
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        raise click.ClickException(f"Task '{task_id}' not found")

    task = parse_task_file(task_file)
    if not task:
        raise click.ClickException(f"Could not parse task '{task_id}'")

    # Release all locks
    task.file_locks = []
    task.scope_locks = []
    task.current_agent = None
    task.lane_id = None
    task.run_status = "queued"
    task.heartbeat_at = None

    # Move task back to todo
    task.column = "todo"
    task.updated = datetime.now(timezone.utc).isoformat()

    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    # Update board columns
    board = load_board(board_dir)
    persist_board(board, board_dir, tasks_dir)

    log.success(f"{task_id} aborted — locks released, moved to todo")


def handle_develop_resume(task_id: str) -> None:
    project_root = find_project_root() or str(Path.cwd())
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        raise click.ClickException(f"Task '{task_id}' not found")

    task = parse_task_file(task_file)
    if not task:
        raise click.ClickException(f"Could not parse task '{task_id}'")

    # Resume: move to in-progress, set running
    task.column = "in-progress"
    task.run_status = "running"
    task.updated = datetime.now(timezone.utc).isoformat()

    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

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
def develop_run(task_id: str, parallel: str, lanes: Optional[int], dashboard: bool) -> None:
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
