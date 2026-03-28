"""Handler functions for board subcommands.

Each handler mirrors the corresponding TS function in board-handlers.ts,
converted to synchronous Python using the existing mpga.board.* modules.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from mpga.board.board import (
    AddTaskOptions,
    BoardState,
    add_task,
    check_wip_limit,
    find_task_file,
    load_board,
    move_task,
    recalc_stats,
    save_board,
)
from mpga.board.board_lock import with_board_lock
from mpga.board.board_md import render_board_md
from mpga.board.live import write_board_live_snapshot
from mpga.board.live_html import write_board_live_html
from mpga.board.task import (
    Task,
    load_all_tasks,
    parse_task_file,
    render_task_file,
)
from mpga.commands.board_live_server import create_board_live_server, open_board_live_url
from mpga.core.config import find_project_root
from mpga.core.logger import console, log

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def get_board_dir(project_root: str | Path) -> str:
    return str(Path(project_root) / "MPGA" / "board")


def get_tasks_dir(project_root: str | Path) -> str:
    return str(Path(project_root) / "MPGA" / "board" / "tasks")


def _board_context() -> tuple[Path, str, str]:
    """Return (project_root, board_dir, tasks_dir) for the current project."""
    project_root = find_project_root() or Path.cwd()
    return project_root, get_board_dir(project_root), get_tasks_dir(project_root)


def persist_board(board: BoardState, board_dir: str, tasks_dir: str) -> None:
    """Recalculate stats, save board.json, and regenerate BOARD.md in one call."""
    tasks = load_all_tasks(tasks_dir)
    recalc_stats(board, tasks_dir, tasks)
    save_board(board_dir, board)
    board_md_path = Path(board_dir) / "BOARD.md"
    board_md_path.parent.mkdir(parents=True, exist_ok=True)
    board_md_path.write_text(render_board_md(board, tasks_dir, tasks), encoding="utf-8")
    write_board_live_snapshot(board, tasks_dir, board_dir, tasks)
    write_board_live_html(board_dir)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_board_show(*, json_output: bool = False, milestone: str | None = None) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)

    if json_output:
        tasks = load_all_tasks(tasks_dir)
        # Produce a JSON-serializable dict for board + tasks
        from dataclasses import asdict

        console.print(json.dumps({"board": asdict(board), "tasks": [asdict(t) for t in tasks]}, indent=2, default=str))
        return

    md_content = render_board_md(board, tasks_dir)
    console.print(md_content)


def handle_board_live(
    *,
    serve: bool = False,
    open_browser: bool = False,
    port: int = 4173,
) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    live_dir = str(Path(board_dir) / "live")
    log.success(f"Generated live board artifacts in {os.path.join('MPGA', 'board', 'live')}")

    should_serve = serve or open_browser
    if not should_serve:
        return

    effective_port = port if port > 0 else 4173
    server = create_board_live_server(live_dir, effective_port)
    url = f"http://127.0.0.1:{effective_port}"
    log.success(f"Serving live board at {url}")
    if open_browser:
        open_board_live_url(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


def handle_board_add(
    title: str,
    *,
    priority: str = "medium",
    scope: str | None = None,
    depends: str | None = None,
    tags: str | None = None,
    column: str = "backlog",
    milestone: str | None = None,
) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)

    task = add_task(
        board,
        tasks_dir,
        AddTaskOptions(
            title=title,
            column=column,  # type: ignore[arg-type]
            priority=priority,
            scopes=[scope] if scope else [],
            depends=[s.strip() for s in depends.split(",")] if depends else [],
            tags=[s.strip() for s in tags.split(",")] if tags else [],
            milestone=milestone,
        ),
    )

    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    log.success(f"Created task {task.id}: {task.title}")
    log.dim(f"  Column: {task.column}  Priority: {task.priority}")


def handle_board_move(task_id: str, column: str, *, force: bool = False) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    result = move_task(board, tasks_dir, task_id, column, force)  # type: ignore[arg-type]

    if not result.success:
        log.error(result.error or "Move failed")
        sys.exit(1)

    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    log.success(f"Moved {task_id} -> {column}")


def handle_board_claim(task_id: str, *, agent: str | None = None, force: bool = False) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)

    # Check WIP limit before claiming
    if not force and not check_wip_limit(board, "in-progress"):
        in_progress_ids = board.columns.get("in-progress", [])
        limit = board.wip_limits.get("in-progress", 3)
        log.error(
            f"WIP limit reached for 'in-progress' ({len(in_progress_ids)}/{limit}). "
            "Use --force to override."
        )
        sys.exit(1)

    # Find and update the task file
    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        log.error(f"Task '{task_id}' not found")
        sys.exit(1)

    task = parse_task_file(task_file)
    if not task:
        log.error("Could not parse task file")
        sys.exit(1)

    task.assigned = agent or "agent"
    task.updated = datetime.now(UTC).isoformat()

    old_column = task.column
    task.column = "in-progress"
    board.columns[old_column] = [id_ for id_ in board.columns[old_column] if id_ != task_id]
    board.columns["in-progress"].append(task_id)

    Path(task_file).write_text(render_task_file(task), encoding="utf-8")
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    log.success(f"{task_id} claimed by {task.assigned} -> in-progress")


def handle_board_assign(task_id: str, agent: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        log.error(f"Task '{task_id}' not found")
        sys.exit(1)

    task = parse_task_file(task_file)
    if not task:
        log.error("Could not parse task")
        sys.exit(1)

    task.assigned = agent
    task.updated = datetime.now(UTC).isoformat()
    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    log.success(f"{task_id} assigned to {agent}")


def handle_board_update(
    task_id: str,
    *,
    status: str | None = None,
    priority: str | None = None,
    evidence_add: str | None = None,
    tdd_stage: str | None = None,
) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        log.error(f"Task '{task_id}' not found")
        sys.exit(1)

    task = parse_task_file(task_file)
    if not task:
        log.error("Could not parse task")
        sys.exit(1)

    if status:
        task.status = status  # type: ignore[assignment]
    if priority:
        task.priority = priority  # type: ignore[assignment]
    if evidence_add:
        task.evidence_produced.append(evidence_add)
    if tdd_stage:
        task.tdd_stage = tdd_stage  # type: ignore[assignment]
    task.updated = datetime.now(UTC).isoformat()

    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    log.success(f"Updated {task_id}")


def handle_board_block(task_id: str, reason: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        log.error(f"Task '{task_id}' not found")
        sys.exit(1)

    task = parse_task_file(task_file)
    if not task:
        log.error("Could not parse task")
        sys.exit(1)

    task.status = "blocked"  # type: ignore[assignment]
    now_iso = datetime.now(UTC).isoformat()
    task.body += f"\n\n## Blocked\n{now_iso}: {reason}\n"
    task.updated = now_iso
    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    log.warn(f"{task_id} marked as blocked: {reason}")


def handle_board_unblock(task_id: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        log.error(f"Task '{task_id}' not found")
        sys.exit(1)

    task = parse_task_file(task_file)
    if not task:
        log.error("Could not parse task")
        sys.exit(1)

    task.status = None
    task.updated = datetime.now(UTC).isoformat()
    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    log.success(f"{task_id} unblocked")


def handle_board_deps(task_id: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    tasks = load_all_tasks(tasks_dir)
    task_map: dict[str, Task] = {t.id: t for t in tasks}

    visited: set[str] = set()

    def print_deps(id_: str, indent: int = 0) -> None:
        if id_ in visited:
            console.print(f"{'  ' * indent}{id_} (circular)")
            return
        visited.add(id_)
        task = task_map.get(id_)
        prefix = "  " * indent
        if not task:
            console.print(f"{prefix}{id_} (not found)")
            visited.discard(id_)
            return
        console.print(f"{prefix}{task.id}: {task.title} [{task.column}]")
        for dep in task.depends_on:
            print_deps(dep, indent + 1)
        visited.discard(id_)

    log.header(f"Dependencies for {task_id}")
    print_deps(task_id)

    # Also show what this task blocks
    blocks = [t for t in tasks if task_id in t.depends_on]
    if blocks:
        console.print("")
        log.dim("This task blocks:")
        for t in blocks:
            log.dim(f"  {t.id}: {t.title}")


def handle_board_stats() -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    recalc_stats(board, tasks_dir)

    log.header("Board Statistics")
    stats = board.stats

    console.print(f"  Total tasks:     {stats.total}")
    console.print(f"  Done:            {stats.done} ({stats.progress_pct}%)")
    console.print(f"  In flight:       {stats.in_flight}")
    console.print(f"  Blocked:         {stats.blocked}")
    console.print(f"  Evidence:        {stats.evidence_produced}/{stats.evidence_expected} links produced")

    tasks = load_all_tasks(tasks_dir)
    by_priority: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for t in tasks:
        by_priority[t.priority] = by_priority.get(t.priority, 0) + 1

    console.print("")
    log.dim("By priority:")
    for p, count in by_priority.items():
        if count > 0:
            console.print(f"  {p:<10} {count}")


def handle_board_archive() -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    done_ids = board.columns["done"]

    if not done_ids:
        log.info("No done tasks to archive.")
        return

    if board.milestone:
        archive_dir = str(project_root / "MPGA" / "milestones" / board.milestone / "tasks")
    else:
        archive_dir = str(project_root / "MPGA" / "milestones" / "_archived-tasks")

    Path(archive_dir).mkdir(parents=True, exist_ok=True)

    archived = 0
    for task_id in done_ids:
        task_file = find_task_file(tasks_dir, task_id)
        if not task_file:
            continue
        dest_file = str(Path(archive_dir) / Path(task_file).name)
        os.rename(task_file, dest_file)
        archived += 1

    board.columns["done"] = []
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir))

    relative = os.path.relpath(archive_dir, str(project_root))
    log.success(f"Archived {archived} done task(s) to {relative}")


def handle_board_search(
    query: str,
    *,
    priority: str | None = None,
    column: str | None = None,
    scope: str | None = None,
    agent: str | None = None,
    tags: str | None = None,
) -> list[Task]:
    """Search and filter board tasks by criteria.

    Returns matching tasks (also prints them to console).
    """
    project_root, board_dir, tasks_dir = _board_context()

    all_tasks = load_all_tasks(tasks_dir)
    results = all_tasks

    # Text search across task titles (case-insensitive)
    if query and query.strip():
        q = query.lower()
        results = [t for t in results if q in t.title.lower()]

    # Filter by priority
    if priority:
        results = [t for t in results if t.priority == priority]

    # Filter by column
    if column:
        results = [t for t in results if t.column == column]

    # Filter by scope
    if scope:
        results = [t for t in results if scope in t.scopes]

    # Filter by assigned agent
    if agent:
        results = [t for t in results if t.assigned == agent]

    # Filter by tags (comma-separated -- task must have ALL specified tags)
    if tags:
        required_tags = [s.strip() for s in tags.split(",")]
        results = [t for t in results if all(tag in t.tags for tag in required_tags)]

    # Print results
    if not results:
        log.info("No tasks match the given criteria.")
        return results

    log.header(f"Search Results ({len(results)} task{'s' if len(results) != 1 else ''})")
    for t in results:
        parts = [t.id, t.title, f"[{t.column}]", t.priority]
        if t.assigned:
            parts.append(f"@{t.assigned}")
        if t.tags:
            parts.append(f"#{','.join(t.tags)}")
        console.print(f"  {'  '.join(parts)}")

    return results
