"""Export SQLite data as Markdown snapshot files for context seeding."""

from __future__ import annotations

from pathlib import Path


def write_sqlite_snapshots(project_root: str, db_path: str) -> str:
    """Write Markdown snapshot files from the MPGA SQLite database.

    Returns the path to the snapshots directory.
    """
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(db_path)
    try:
        create_schema(conn)

        snapshots_dir = Path(project_root) / ".mpga" / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Tasks
        rows = conn.execute(
            "SELECT id, title, column_, priority FROM tasks ORDER BY id"
        ).fetchall()
        lines = ["# Tasks\n"]
        for row in rows:
            lines.append(f"- **{row[0]}** {row[1]} [{row[2]}] (priority: {row[3]})")
        (snapshots_dir / "tasks.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        # Scopes
        rows = conn.execute(
            "SELECT id, name, summary, status FROM scopes ORDER BY id"
        ).fetchall()
        lines = ["# Scopes\n"]
        for row in rows:
            lines.append(f"- **{row[0]}** {row[1]} — {row[2] or ''} [{row[3]}]")
        (snapshots_dir / "scopes.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        # Evidence
        rows = conn.execute(
            "SELECT raw, type, filepath FROM evidence ORDER BY id"
        ).fetchall()
        lines = ["# Evidence\n"]
        for row in rows:
            lines.append(f"- {row[0]} [{row[1]}] {row[2] or ''}")
        (snapshots_dir / "evidence.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        # Milestones
        rows = conn.execute(
            "SELECT id, name, status FROM milestones ORDER BY id"
        ).fetchall()
        lines = ["# Milestones\n"]
        for row in rows:
            lines.append(f"- **{row[0]}** {row[1]} [{row[2]}]")
        (snapshots_dir / "milestones.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

        # Stats
        task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        scope_count = conn.execute("SELECT COUNT(*) FROM scopes").fetchone()[0]
        evidence_count = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        milestone_count = conn.execute(
            "SELECT COUNT(*) FROM milestones"
        ).fetchone()[0]
        stats_lines = [
            "# Stats\n",
            f"- Tasks: {task_count}",
            f"- Scopes: {scope_count}",
            f"- Evidence links: {evidence_count}",
            f"- Milestones: {milestone_count}",
        ]
        (snapshots_dir / "stats.md").write_text(
            "\n".join(stats_lines) + "\n", encoding="utf-8"
        )

    finally:
        conn.close()

    return str(snapshots_dir)
