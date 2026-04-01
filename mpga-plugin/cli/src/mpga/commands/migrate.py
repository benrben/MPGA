"""Migration helpers: read task/scope/milestone .md files into SQLite."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import click

from mpga.db.migrations import run_migrations


@click.command("migrate")
@click.option("--db", default=None, help="Path to the SQLite database file.")
def migrate_cmd(db: str | None) -> None:
    """Apply pending SQL migrations to the MPGA database."""
    from mpga.db.connection import get_connection

    db_path = db or ".mpga/mpga.db"
    conn = get_connection(db_path)
    run_migrations(conn)
    conn.close()


def migrate_board(conn: sqlite3.Connection, board_dir: str) -> None:
    """Read board.json from board_dir (if present) and insert key-value rows into the board table."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS board (key TEXT PRIMARY KEY, value TEXT)"
    )
    board_file = Path(board_dir) / "board.json"
    if not board_file.exists():
        return
    try:
        data = json.loads(board_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError, OSError):
        return
    for key, value in data.items():
        serialized = json.dumps(value) if not isinstance(value, str) else value
        existing = conn.execute("SELECT key FROM board WHERE key = ?", (key,)).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO board (key, value) VALUES (?, ?)",
                (key, serialized),
            )
    conn.commit()


def migrate_tasks(conn: sqlite3.Connection, tasks_dir: str) -> dict:
    """Scan tasks_dir for .md task files and insert rows into the tasks table."""
    from mpga.board.task import parse_task_file
    from mpga.db.repos.tasks import TaskRepo

    repo = TaskRepo(conn)
    count = 0
    for md_file in sorted(Path(tasks_dir).glob("*.md")):
        try:
            task = parse_task_file(str(md_file))
            existing = conn.execute(
                "SELECT id FROM tasks WHERE id = ?", (task.id,)
            ).fetchone()
            if existing is None:
                repo.create(task)
            count += 1
        except (OSError, ValueError, sqlite3.Error):
            continue
    # Recount actual rows (idempotent calls should not inflate count)
    actual = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    return {"tasks": actual}


def migrate_scopes(conn: sqlite3.Connection, scopes_dir: str) -> dict:
    """Scan scopes_dir for .md scope files and insert rows into scopes + evidence tables."""
    from mpga.db.repos.evidence import EvidenceRepo
    from mpga.db.repos.scopes import Scope, ScopeRepo
    from mpga.evidence.parser import parse_evidence_links

    scope_repo = ScopeRepo(conn)
    evidence_repo = EvidenceRepo(conn)
    scope_count = 0
    evidence_count = 0

    for md_file in sorted(Path(scopes_dir).glob("*.md")):
        try:
            scope_id = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            existing = conn.execute(
                "SELECT id FROM scopes WHERE id = ?", (scope_id,)
            ).fetchone()
            if existing is None:
                scope = Scope(id=scope_id, name=scope_id, content=content)
                scope_repo.create(scope)
                scope_count += 1

            # Parse and insert evidence links
            existing_evidence = conn.execute(
                "SELECT COUNT(*) FROM evidence WHERE scope_id = ?", (scope_id,)
            ).fetchone()[0]
            if existing_evidence == 0:
                links = parse_evidence_links(content)
                for link in links:
                    evidence_repo.create(link, scope_id=scope_id, task_id=None)
                    evidence_count += 1
        except (OSError, ValueError, sqlite3.Error):
            continue

    # Rebuild evidence FTS
    conn.execute("INSERT INTO evidence_fts(evidence_fts) VALUES('rebuild')")
    conn.commit()

    actual_evidence = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
    actual_scopes = conn.execute("SELECT COUNT(*) FROM scopes").fetchone()[0]
    return {"scopes": actual_scopes, "evidence": actual_evidence}


def migrate_milestones(conn: sqlite3.Connection, milestones_dir: str) -> dict:
    """Scan milestones_dir for M*-* subdirectories and insert milestone rows."""
    from mpga.db.repos.milestones import Milestone, MilestoneRepo

    repo = MilestoneRepo(conn)
    count = 0

    for m_dir in sorted(Path(milestones_dir).iterdir()):
        if not m_dir.is_dir():
            continue
        # Match directories named like M001-some-name
        match = re.match(r"^(M\d+)-(.+)$", m_dir.name)
        if not match:
            continue
        milestone_id = match.group(1)
        milestone_name = m_dir.name

        existing = conn.execute(
            "SELECT id FROM milestones WHERE id = ?", (milestone_id,)
        ).fetchone()
        if existing is not None:
            continue

        plan_file = m_dir / "PLAN.md"
        summary_file = m_dir / "SUMMARY.md"
        design = plan_file.read_text(encoding="utf-8") if plan_file.exists() else None
        summary = summary_file.read_text(encoding="utf-8") if summary_file.exists() else None

        milestone = Milestone(
            id=milestone_id,
            name=milestone_name,
            design=design,
            summary=summary,
        )
        repo.create(milestone)
        count += 1

    actual = conn.execute("SELECT COUNT(*) FROM milestones").fetchone()[0]
    return {"milestones": actual}
