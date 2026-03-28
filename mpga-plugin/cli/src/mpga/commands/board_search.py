"""Search and filter board tasks by criteria."""

from __future__ import annotations

from pathlib import Path

from mpga.board.task import Task, load_all_tasks
from mpga.core.config import find_project_root
from mpga.core.logger import console, log


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
    project_root = find_project_root() or Path.cwd()
    tasks_dir = str(project_root / "MPGA" / "board" / "tasks")

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
