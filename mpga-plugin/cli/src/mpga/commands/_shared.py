from __future__ import annotations

from pathlib import Path

from mpga.db.connection import get_connection
from mpga.db.repos.milestones import MilestoneRepo
from mpga.db.schema import create_schema


def _current_milestone(project_root: Path) -> str | None:
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return None

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        milestones = MilestoneRepo(conn).list_all()
        active = next((m for m in milestones if m.status == "active"), None)
        if active is not None:
            return active.id
        return None
    finally:
        conn.close()


def get_current_milestone(project_root: Path) -> str | None:
    return _current_milestone(project_root)
