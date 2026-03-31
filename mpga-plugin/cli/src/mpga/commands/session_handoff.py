"""Handoff document generation for session export.

Extracted from session.py to keep that module under 500 lines.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import click

from mpga.core.config import find_project_root
from mpga.db.connection import get_connection
from mpga.db.repos.sessions import SessionRepo
from mpga.db.schema import create_schema


def _project_root() -> Path:
    return Path(find_project_root() or Path.cwd())


def _open_session_repo(project_root: Path) -> tuple[object, SessionRepo]:
    db_path = project_root / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_path))
    create_schema(conn)
    return conn, SessionRepo(conn)


def _close_conn(conn: object) -> None:
    try:
        conn.close()  # type: ignore[attr-defined]
    except (AttributeError, Exception):
        pass


def do_handoff(accomplished: str | None) -> None:
    """Shared implementation for both `handoff` and `export` subcommands."""
    from mpga.commands.session import _current_session

    project_root = _project_root()
    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _current_session(repo, project_root)
        snapshot_data: dict[str, object] = {}
        if session_row and session_row.task_snapshot:
            try:
                snapshot_data = json.loads(session_row.task_snapshot)
            except (json.JSONDecodeError, ValueError):
                pass
    finally:
        _close_conn(conn)

    now = datetime.now(UTC)
    date_str = now.strftime("%Y-%m-%d")

    milestone = snapshot_data.get("milestone") or "none"
    done = snapshot_data.get("done", 0)
    total = snapshot_data.get("total", 0)
    progress_pct = snapshot_data.get("progress_pct", 0)
    in_progress_tasks = snapshot_data.get("in_progress", [])
    in_flight_count = len(in_progress_tasks) if isinstance(in_progress_tasks, list) else 0

    if in_flight_count:
        in_flight_lines = "\n".join(
            f"- **{t.get('id', '?')}**: {t.get('title', '?')} [{t.get('column', '?')}]"
            for t in in_progress_tasks
            if isinstance(t, dict)
        )
        first = in_progress_tasks[0] if isinstance(in_progress_tasks[0], dict) else {}
        next_action = (
            f"Resume task {first.get('id', '?')}: {first.get('title', '?')} "
            f"-- run `mpga board claim {first.get('id', '?')}`"
        )
    else:
        in_flight_lines = "(none)"
        next_action = "No immediate next step -- run `mpga status` to assess"

    content = f"""# Session Handoff -- {date_str}

## Accomplished
{accomplished or '(describe what was done this session)'}

## Current state
- **Milestone:** {milestone}
- **Board:** {done}/{total} tasks done
- **Progress:** {progress_pct}%
- **In flight:** {in_flight_count} task(s)

## In-flight tasks
{in_flight_lines}

## Decisions made
| Decision | Rationale |
|----------|-----------|
| (add decisions here) | |

## Open questions
- [ ] (add unresolved questions)

## Modified files
(list key files changed this session)

## Next action
{next_action}

## How to resume
1. Run `mpga session resume` to load session context
2. Run `mpga board show` to see current task state
3. Resume from "Next action" above
"""

    click.echo(content)
