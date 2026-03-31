"""Handler functions for board subcommands.

Each handler mirrors the corresponding TS function in board-handlers.ts,
converted to synchronous Python using the existing mpga.board.* modules.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mpga.bridge.compress import compress_board_stats, compress_task
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
from mpga.board.task import (
    Task,
    load_all_tasks,
    parse_task_file,
    render_task_file,
)
from mpga.commands.board_db import (
    load_board_tasks as _load_board_tasks,
    refresh_sqlite_board_mirror as _refresh_sqlite_board_mirror,
    search_db_tasks as _search_db_tasks,
    sync_task_to_db as _sync_task_to_db,
)
from mpga.core.config import find_project_root
from mpga.core.logger import console, log

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _board_context() -> tuple[Path, str, str]:
    """Return (project_root, board_dir, tasks_dir) for the current project."""
    project_root = find_project_root() or Path.cwd()
    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(project_root) / "MPGA" / "board" / "tasks")
    return project_root, board_dir, tasks_dir


def persist_board(board: BoardState, board_dir: str, tasks_dir: str, *, project_root: Path | None = None) -> None:
    """Recalculate stats, save board.json, and sync to SQLite."""
    tasks = load_all_tasks(tasks_dir)
    recalc_stats(board, tasks_dir, tasks)
    save_board(board_dir, board)
    effective_root: Path = project_root or find_project_root() or Path.cwd()
    _refresh_sqlite_board_mirror(board_dir, tasks_dir, project_root=effective_root)


def _load_and_parse_task_or_exit(tasks_dir: str, task_id: str) -> Task:
    """Find and parse a task file, exiting with an error if not found or unparseable."""
    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        log.error(f"Task '{task_id}' not found")
        sys.exit(1)
    task = parse_task_file(task_file)
    if not task:
        log.error("Could not parse task file")
        sys.exit(1)
    return task


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_board_show(
    *,
    json_output: bool = False,
    milestone: str | None = None,
    full: bool = False,
) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    tasks = _load_board_tasks(project_root, tasks_dir)
    recalc_stats(board, tasks_dir, tasks)

    if json_output:
        from dataclasses import asdict

        console.print(json.dumps({"board": asdict(board), "tasks": [asdict(t) for t in tasks]}, indent=2, default=str))
        return

    if _search_db_tasks(project_root, "") is not None and not full:
        console.print(
            compress_board_stats(
                {
                    "total": board.stats.total,
                    "done": board.stats.done,
                    "in_flight": board.stats.in_flight,
                    "blocked": board.stats.blocked,
                    "progress_pct": board.stats.progress_pct,
                    "milestone": board.milestone or "No active milestone",
                }
            ),
            markup=False,
        )
        return

    md_content = render_board_md(board, tasks_dir, tasks)
    console.print(md_content)


def handle_board_live() -> None:
    """Persist the board to the SQLite mirror."""
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.info("Board persisted to DB. Live HTML artifacts are no longer generated.")


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

    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.success(f"Created task {task.id}: {task.title}")
    log.dim(f"  Column: {task.column}  Priority: {task.priority}")


def handle_board_move(task_id: str, column: str, *, force: bool = False) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    result = move_task(board, tasks_dir, task_id, column, force)  # type: ignore[arg-type]

    if not result.success:
        log.error(result.error or "Move failed")
        sys.exit(1)

    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.success(f"Moved {task_id} -> {column}")


def handle_board_claim(task_id: str, *, agent: str | None = None, force: bool = False) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)

    if not force and not check_wip_limit(board, "in-progress"):
        in_progress_ids = board.columns.get("in-progress", [])
        limit = board.wip_limits.get("in-progress", 3)
        log.error(
            f"WIP limit reached for 'in-progress' ({len(in_progress_ids)}/{limit}). "
            "Use --force to override."
        )
        sys.exit(1)

    task = _load_and_parse_task_or_exit(tasks_dir, task_id)

    task.assigned = agent or "agent"
    task.updated = datetime.now(UTC).isoformat()

    old_column = task.column
    task.column = "in-progress"
    board.columns[old_column] = [id_ for id_ in board.columns[old_column] if id_ != task_id]
    board.columns["in-progress"].append(task_id)

    task_file = find_task_file(tasks_dir, task_id)
    if task_file:
        Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    _sync_task_to_db(project_root, task)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.success(f"{task_id} claimed by {task.assigned} -> in-progress")


def handle_board_assign(task_id: str, agent: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task = _load_and_parse_task_or_exit(tasks_dir, task_id)
    task.assigned = agent
    task.updated = datetime.now(UTC).isoformat()
    _sync_task_to_db(project_root, task)
    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

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

    task = _load_and_parse_task_or_exit(tasks_dir, task_id)

    if status:
        task.status = status  # type: ignore[assignment]
    if priority:
        task.priority = priority  # type: ignore[assignment]
    if evidence_add:
        task.evidence_produced.append(evidence_add)
    if tdd_stage:
        task.tdd_stage = tdd_stage  # type: ignore[assignment]
    task.updated = datetime.now(UTC).isoformat()

    _sync_task_to_db(project_root, task)
    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.success(f"Updated {task_id}")


def handle_board_block(task_id: str, reason: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task = _load_and_parse_task_or_exit(tasks_dir, task_id)
    task.status = "blocked"  # type: ignore[assignment]
    now_iso = datetime.now(UTC).isoformat()
    task.body += f"\n\n## Blocked\n{now_iso}: {reason}\n"
    task.updated = now_iso
    _sync_task_to_db(project_root, task)
    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.warn(f"{task_id} marked as blocked: {reason}")


def handle_board_unblock(task_id: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    task = _load_and_parse_task_or_exit(tasks_dir, task_id)
    task.status = None
    task.updated = datetime.now(UTC).isoformat()
    _sync_task_to_db(project_root, task)
    board = load_board(board_dir)
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    log.success(f"{task_id} unblocked")


def handle_board_deps(task_id: str) -> None:
    project_root, board_dir, tasks_dir = _board_context()

    tasks = _load_board_tasks(project_root, tasks_dir)
    task_map: dict[str, Task] = {t.id: t for t in tasks}

    visited: set[str] = set()
    in_progress: set[str] = set()

    def print_deps(id_: str, indent: int = 0) -> None:
        prefix = "  " * indent
        if id_ in in_progress:
            console.print(f"{prefix}{id_} (circular)")
            return
        if id_ in visited:
            return
        visited.add(id_)
        in_progress.add(id_)
        task = task_map.get(id_)
        if not task:
            console.print(f"{prefix}{id_} (not found)")
            in_progress.discard(id_)
            return
        console.print(f"{prefix}{task.id}: {task.title} [{task.column}]")
        for dep in task.depends_on:
            print_deps(dep, indent + 1)
        in_progress.discard(id_)

    log.header(f"Dependencies for {task_id}")
    print_deps(task_id)

    blocks = [t for t in tasks if task_id in t.depends_on]
    if blocks:
        console.print("")
        log.dim("This task blocks:")
        for t in blocks:
            log.dim(f"  {t.id}: {t.title}")


def handle_board_stats() -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    tasks = _load_board_tasks(project_root, tasks_dir)
    recalc_stats(board, tasks_dir, tasks)

    log.header("Board Statistics")
    stats = board.stats

    if _search_db_tasks(project_root, "") is not None:
        console.print(
            compress_board_stats(
                {
                    "total": stats.total,
                    "done": stats.done,
                    "in_flight": stats.in_flight,
                    "blocked": stats.blocked,
                    "progress_pct": stats.progress_pct,
                    "milestone": board.milestone or "No active milestone",
                }
            ),
            markup=False,
        )
        return

    console.print(f"  Total tasks:     {stats.total}")
    console.print(f"  Done:            {stats.done} ({stats.progress_pct}%)")
    console.print(f"  In flight:       {stats.in_flight}")
    console.print(f"  Blocked:         {stats.blocked}")
    console.print(f"  Evidence:        {stats.evidence_produced}/{stats.evidence_expected} links produced")

    by_priority: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for t in tasks:
        by_priority[t.priority] = by_priority.get(t.priority, 0) + 1

    console.print("")
    log.dim("By priority:")
    for p, count in by_priority.items():
        if count > 0:
            console.print(f"  {p:<10} {count}")


_SAFE_MILESTONE_RE = __import__("re").compile(r"^[A-Za-z0-9_\-\.]+$")


def _sanitize_milestone(milestone: str) -> str:
    """Validate that *milestone* is safe to use as a path component."""
    if not _SAFE_MILESTONE_RE.match(milestone):
        raise ValueError(
            f"Invalid milestone name {milestone!r}: only alphanumeric characters, "
            "dashes, underscores, and dots are allowed."
        )
    if ".." in milestone or "/" in milestone or "\\" in milestone:
        raise ValueError(
            f"Unsafe milestone name {milestone!r}: path traversal sequences are not allowed."
        )
    return milestone


def handle_board_archive() -> None:
    project_root, board_dir, tasks_dir = _board_context()

    board = load_board(board_dir)
    done_ids = board.columns["done"]

    if not done_ids:
        log.info("No done tasks to archive.")
        return

    if board.milestone:
        safe_milestone = _sanitize_milestone(board.milestone)
        archive_dir = str(project_root / "MPGA" / "milestones" / safe_milestone / "tasks")
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
    with_board_lock(board_dir, lambda: persist_board(board, board_dir, tasks_dir, project_root=project_root))

    relative = os.path.relpath(archive_dir, str(project_root))
    log.success(f"Archived {archived} done task(s) to {relative}")


@dataclass
class BoardSearchFilters:
    """Filter criteria for board search (AND semantics)."""
    priority: str | None = None
    column: str | None = None
    scope: str | None = None
    agent: str | None = None
    tags: str | None = None


def handle_board_search(
    query: str, *, filters: BoardSearchFilters | None = None, full: bool = False,
) -> list[Task]:
    """Search and filter board tasks by criteria."""
    if filters is None:
        filters = BoardSearchFilters()

    project_root, board_dir, tasks_dir = _board_context()
    db_results = _search_db_tasks(
        project_root, query, priority=filters.priority,
        column=filters.column, scope=filters.scope, tags=filters.tags,
    )
    results = db_results if db_results is not None else load_all_tasks(tasks_dir)

    if filters.agent:
        results = [t for t in results if t.assigned == filters.agent]
    if db_results is None:
        if query and query.strip():
            q = query.lower()
            results = [t for t in results if q in t.title.lower()]
        if filters.priority:
            results = [t for t in results if t.priority == filters.priority]
        if filters.column:
            results = [t for t in results if t.column == filters.column]
        if filters.scope:
            results = [t for t in results if filters.scope in t.scopes]
        if filters.tags:
            required_tags = [s.strip() for s in filters.tags.split(",")]
            results = [t for t in results if all(tag in t.tags for tag in required_tags)]

    if not results:
        log.info("No tasks match the given criteria.")
        return results

    log.header(f"Search Results ({len(results)} task{'s' if len(results) != 1 else ''})")
    if db_results is not None and not full:
        for t in results:
            console.print(f"  {compress_task(t)}", markup=False)
    else:
        for t in results:
            parts = [t.id, t.title, f"[{t.column}]", t.priority]
            if t.assigned:
                parts.append(f"@{t.assigned}")
            if t.tags:
                parts.append(f"#{','.join(t.tags)}")
            console.print(f"  {'  '.join(parts)}")

    return results
