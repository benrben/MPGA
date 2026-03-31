from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log, mini_banner, progress_bar
from mpga.db.connection import get_connection
from mpga.db.repos.scopes import ScopeRepo
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema

_IN_FLIGHT_COLUMNS = {"in-progress", "testing", "review"}


def _summarize_tasks(tasks) -> dict[str, object]:
    columns: dict[str, list[str]] = {
        "backlog": [],
        "todo": [],
        "in-progress": [],
        "testing": [],
        "review": [],
        "done": [],
    }
    for task in tasks:
        columns.setdefault(task.column, []).append(task.id)

    total = len(tasks)
    done = sum(1 for task in tasks if task.column == "done")
    in_flight = sum(1 for task in tasks if task.column in _IN_FLIGHT_COLUMNS)
    blocked = sum(1 for task in tasks if task.status == "blocked")
    progress_pct = round((done / total) * 100) if total else 0
    return {
        "stats": {
            "total": total,
            "done": done,
            "in_flight": in_flight,
            "blocked": blocked,
            "progress_pct": progress_pct,
        },
        "columns": columns,
    }


def _load_db_status(project_root: Path) -> dict[str, object] | None:
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return None

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        tasks = TaskRepo(conn).filter()
        scopes = ScopeRepo(conn).list_all()

        board_state = _summarize_tasks(tasks) if tasks else None
        last_scanned = conn.execute("SELECT MAX(last_scanned) FROM file_info").fetchone()
        last_sync = last_scanned[0] if last_scanned and last_scanned[0] else "never"

        total_ev = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        valid_ev = conn.execute(
            "SELECT COUNT(*) FROM evidence WHERE type = 'valid'"
        ).fetchone()[0]
        evidence_pct = round(valid_ev / total_ev * 100) if total_ev else 0

        return {
            "board_state": board_state,
            "scopes": scopes,
            "last_sync": last_sync,
            "evidence_pct": evidence_pct,
        }
    finally:
        conn.close()



@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status_cmd(as_json: bool) -> None:
    """Show project health dashboard."""
    project_root = Path(find_project_root() or Path.cwd())
    config = load_config(project_root)

    db_status = _load_db_status(project_root)
    if db_status is None:
        log.error("No MPGA database found. Run `mpga init` first.")
        sys.exit(1)

    board_state: dict | None = db_status["board_state"]
    scopes = db_status["scopes"]
    last_sync = str(db_status["last_sync"])
    evidence_coverage = f"{db_status['evidence_pct']}%"

    if as_json:
        board_stats = board_state.get("stats") if board_state else None
        click.echo(
            json.dumps(
                {
                    "initialized": True,
                    "lastSync": last_sync,
                    "evidenceCoverage": evidence_coverage,
                    "scopes": len(scopes),
                    "board": board_stats,
                    "config": {"name": config.project.name},
                },
                indent=2,
            )
        )
        return

    mini_banner()

    log.header(f"Status \u2014 {config.project.name} (Looking TREMENDOUS)")

    log.section("  \U0001f4da Knowledge Layer")
    log.kv("Last sync", last_sync, 4)
    log.kv("Scopes", str(len(scopes)), 4)
    log.kv("Evidence", evidence_coverage, 4)

    if scopes:
        log.section("  \U0001f5c2  Scopes")
        for scope in scopes:
            click.echo(f"    {scope.name:<22} {scope.status}")

    if board_state:
        stats = board_state.get("stats", {})
        log.section("  \U0001f4cb Task Board")
        done = stats.get("done", 0)
        total = stats.get("total", 0)
        log.kv(
            "Progress",
            f"{progress_bar(done, total)}  [dim]{done}/{total}[/]",
            4,
        )
        in_flight = stats.get("in_flight", 0)
        if in_flight > 0:
            log.kv("In flight", f"[yellow]{in_flight}[/]", 4)
        blocked = stats.get("blocked", 0)
        if blocked > 0:
            log.kv("Blocked", f"[red]{blocked}[/]", 4)

        cols = board_state.get("columns", {})
        col_parts = []
        for col, tasks in cols.items():
            if tasks:
                col_parts.append(f"{col}([bold white]{len(tasks)}[/])")
        if col_parts:
            log.kv("Columns", "  ".join(col_parts), 4)

    log.section("  \u2699  Configuration")
    log.kv("Project", config.project.name, 4)
    log.kv("Languages", ", ".join(config.project.languages), 4)
    log.kv(
        "Evidence",
        f"{config.evidence.strategy}, {round(config.evidence.coverage_threshold * 100)}% target",
        4,
    )
    log.kv("CI threshold", f"{config.drift.ci_threshold}%", 4)

    log.blank()
    log.dim("  Run `mpga sync` to refresh  \u00b7  `mpga health` for full report")
    log.blank()
