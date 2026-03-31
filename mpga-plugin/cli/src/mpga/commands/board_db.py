"""Database helpers for board: SQLite mirror, task search, and DB sync.

Extracted from board_handlers.py to keep that module under 500 lines.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from mpga.board.task import Task, load_all_tasks
from mpga.commands.migrate import migrate_tasks
from mpga.core.config import find_project_root
from mpga.db.connection import get_connection
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema
from mpga.db.search import rebuild_global_fts

# Board-structure constant: board_dir lives at <project_root>/MPGA/board.
_BOARD_DIR_DEPTH = 2  # levels below project_root


def refresh_sqlite_board_mirror(board_dir: str, tasks_dir: str, *, project_root: Path | None = None) -> None:
    """Atomically refresh the SQLite board mirror from task files on disk."""
    if project_root is None:
        project_root = find_project_root() or Path.cwd()
    db_path = str(project_root / ".mpga" / "mpga.db")
    conn = get_connection(db_path)
    try:
        create_schema(conn)
        import sqlite3 as _sqlite3

        mem = _sqlite3.connect(":memory:")
        try:
            conn.backup(mem)
            mem.execute("DELETE FROM task_scopes")
            mem.execute("DELETE FROM task_tags")
            mem.execute("DELETE FROM task_deps")
            mem.execute("DELETE FROM tasks")
            mem.commit()
            migrate_tasks(mem, tasks_dir)
        except (OSError, sqlite3.Error, ValueError):
            mem.close()
            raise
        conn.execute("DELETE FROM task_scopes")
        conn.execute("DELETE FROM task_tags")
        conn.execute("DELETE FROM task_deps")
        conn.execute("DELETE FROM tasks")
        conn.commit()
        migrate_tasks(conn, tasks_dir)
        mem.close()
        rebuild_global_fts(conn)
    finally:
        conn.close()


def load_task_repo(project_root: Path) -> tuple[object, TaskRepo] | None:
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return None
    conn = get_connection(str(db_path))
    create_schema(conn)
    return conn, TaskRepo(conn)


def search_db_tasks(
    project_root: Path,
    query: str,
    *,
    priority: str | None = None,
    column: str | None = None,
    scope: str | None = None,
    tags: str | None = None,
) -> list[Task] | None:
    repo_bundle = load_task_repo(project_root)
    if repo_bundle is None:
        return None

    conn, repo = repo_bundle
    try:
        required_tags = [s.strip() for s in tags.split(",") if s.strip()] if tags else None
        if query and query.strip():
            tasks = repo.search(query, limit=200)
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            if column:
                tasks = [t for t in tasks if t.column == column]
            if scope:
                tasks = [t for t in tasks if scope in t.scopes]
            if required_tags:
                tasks = [t for t in tasks if all(tag in t.tags for tag in required_tags)]
        else:
            tasks = repo.filter(
                column=column,
                priority=priority,
                scope=scope,
                tags=required_tags,
            )
        return tasks
    finally:
        conn.close()


def load_board_tasks(project_root: Path, tasks_dir: str) -> list[Task]:
    db_tasks = search_db_tasks(project_root, "")
    if db_tasks is not None:
        return db_tasks
    return load_all_tasks(tasks_dir)


def sync_task_to_db(project_root: Path, task: Task) -> None:
    repo_bundle = load_task_repo(project_root)
    if repo_bundle is None:
        return

    conn, repo = repo_bundle
    try:
        if repo.get(task.id) is None:
            repo.create(task)
        else:
            repo.update(task)
    finally:
        conn.close()
