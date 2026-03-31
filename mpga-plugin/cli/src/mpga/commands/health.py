from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import (
    grade_color,
    log,
    mini_banner,
    progress_bar,
    status_badge,
)
from mpga.db.connection import get_connection
from mpga.db.repos.scopes import ScopeRepo
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema
from mpga.evidence.drift import run_drift_check

# Evidence health percentage at or above which status is considered good.
EVIDENCE_HEALTH_GOOD_PCT = 80
# Health percentage at or above which the project earns an A grade.
GRADE_A_THRESHOLD = 95
# Multiplier applied to CI threshold to determine the C grade cutoff.
GRADE_C_MULTIPLIER = 0.7
# TTL for the file-based link-validation cache (seconds).  5 minutes = 300 s.
HEALTH_CACHE_TTL_SECONDS = 300


def _summarize_tasks(tasks) -> dict[str, int]:
    total = len(tasks)
    done = sum(1 for task in tasks if task.column == "done")
    in_flight = sum(1 for task in tasks if task.column in ("in-progress", "testing", "review"))
    blocked = sum(1 for task in tasks if task.status == "blocked")
    progress_pct = round((done / total) * 100) if total else 0
    return {
        "total": total,
        "done": done,
        "in_flight": in_flight,
        "blocked": blocked,
        "progress_pct": progress_pct,
    }


def _load_sqlite_health(project_root: Path) -> dict[str, object] | None:
    project_root = Path(project_root)
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return None

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        tasks = TaskRepo(conn).filter()
        scopes = ScopeRepo(conn).list_all()
        if not tasks and not scopes:
            return None

        board_stats = _summarize_tasks(tasks) if tasks else None
        last_scanned = conn.execute("SELECT MAX(last_scanned) FROM file_info").fetchone()
        last_sync = last_scanned[0] if last_scanned and last_scanned[0] else "never"
        return {
            "board": board_stats,
            "scopes": len(scopes),
            "last_sync": last_sync,
        }
    finally:
        conn.close()


def _compute_grade(health_pct: int, threshold: int) -> str:
    if health_pct >= GRADE_A_THRESHOLD:
        return "A"
    if health_pct >= threshold:
        return "B"
    if health_pct >= threshold * GRADE_C_MULTIPLIER:
        return "C"
    return "D"


# ---------------------------------------------------------------------------
# Cache helpers — avoid re-scanning all evidence links on every run
# ---------------------------------------------------------------------------

def _cache_path(project_root: Path) -> Path:
    return project_root / ".mpga" / "health_cache.json"


def _read_cache(project_root: Path) -> dict | None:
    """Return cached drift data if the cache exists and is within TTL, else None."""
    path = _cache_path(project_root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age = time.time() - float(data.get("timestamp", 0))
        if age < HEALTH_CACHE_TTL_SECONDS:
            return data
    except (json.JSONDecodeError, ValueError, OSError):
        pass
    return None


def _write_cache(project_root: Path, drift_report) -> None:
    """Persist drift data to the file-based cache with a current timestamp."""
    path = _cache_path(project_root)
    payload = {
        "timestamp": time.time(),
        "overall_health_pct": drift_report.overall_health_pct,
        "valid_links": drift_report.valid_links,
        "total_links": drift_report.total_links,
        "ci_pass": drift_report.ci_pass,
        "scopes": [],  # raw scope objects are not JSON-serialisable; omit for now
    }
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        pass  # cache write failure is non-fatal


@click.command("health")
@click.option("--verbose", is_flag=True, help="Detailed breakdown")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output")
def health_cmd(verbose: bool, as_json: bool) -> None:
    """Overall project health report."""
    project_root = Path(find_project_root() or Path.cwd())
    config = load_config(project_root)

    db_exists = (Path(project_root) / ".mpga" / "mpga.db").exists()
    if not db_exists:
        log.error("No MPGA database found. Run `mpga init` first.")
        sys.exit(1)

    sqlite_health = _load_sqlite_health(project_root)

    # Gather evidence health — use file-based cache when still fresh
    cached = _read_cache(project_root)
    if cached is not None:
        # Re-hydrate a lightweight stand-in from the cache so the rest of the
        # function can treat it identically to a real DriftReport.
        from types import SimpleNamespace
        drift_report = SimpleNamespace(
            overall_health_pct=cached["overall_health_pct"],
            valid_links=cached["valid_links"],
            total_links=cached["total_links"],
            ci_pass=cached["ci_pass"],
            scopes=cached.get("scopes", []),
        )
    else:
        drift_report = run_drift_check(str(project_root), config.drift.ci_threshold)
        _write_cache(project_root, drift_report)

    # Gather board health
    board_stats: dict | None = None
    if sqlite_health and sqlite_health["board"]:
        board_stats = sqlite_health["board"]  # type: ignore[assignment]

    # Gather scope count
    scope_count = 0
    if sqlite_health and sqlite_health["scopes"] is not None:
        scope_count = int(sqlite_health["scopes"])

    overall_grade = _compute_grade(drift_report.overall_health_pct, config.drift.ci_threshold)

    health = {
        "initialized": True,
        "evidenceHealth": drift_report.overall_health_pct,
        "evidenceTarget": config.evidence.coverage_threshold * 100,
        "ciThreshold": config.drift.ci_threshold,
        "ciPass": drift_report.ci_pass,
        "scopes": scope_count,
        "board": board_stats,
        "lastSync": str(sqlite_health["last_sync"]) if sqlite_health else "never",
        "overallGrade": overall_grade,
    }

    if as_json:
        click.echo(json.dumps(health, indent=2))
        return

    mini_banner()
    log.header("Health Report \u2014 We're CRUSHING IT")

    # -- Grade --
    click.echo(f"\n  [dim]Grade[/]  {grade_color(overall_grade)}\n")

    # -- Evidence --
    evidence_ok = drift_report.overall_health_pct >= EVIDENCE_HEALTH_GOOD_PCT
    click.echo(
        f"  {status_badge(evidence_ok, 'Evidence health')}   "
        f"{drift_report.overall_health_pct}%  "
        f"[dim](CI threshold: {config.drift.ci_threshold}%)[/]"
    )
    click.echo(
        f"    {progress_bar(drift_report.valid_links, drift_report.total_links)}  "
        f"[dim]{drift_report.valid_links}/{drift_report.total_links} links[/]"
    )

    if verbose and drift_report.scopes:
        log.blank()
        for scope in drift_report.scopes:
            icon = (
                "[green]\u2713[/]"
                if scope.health_pct >= EVIDENCE_HEALTH_GOOD_PCT
                else "[yellow]\u26a0[/]"
            )
            click.echo(
                f"    {icon} {scope.scope:<20} {scope.health_pct}% "
                f"[dim]({scope.valid_links}/{scope.total_links})[/]"
            )

    # -- Scopes --
    log.blank()
    click.echo(f"  {status_badge(scope_count > 0, 'Scopes')}            {scope_count} document(s)")

    # -- Board --
    if board_stats:
        log.blank()
        click.echo(
            f"  {status_badge(board_stats['blocked'] == 0, 'Task board')}        "
            f"{board_stats['done']}/{board_stats['total']} tasks "
            f"[dim]({board_stats['progress_pct']}%)[/]"
        )
        if board_stats["blocked"] > 0:
            click.echo(f"    [yellow]\u26a0[/] {board_stats['blocked']} blocked task(s)")

    # -- Last sync --
    log.blank()
    click.echo(f"  [blue]\u2139[/] Last sync          [dim]{health['lastSync']}[/]")

    # -- Recommendations --
    log.blank()
    log.divider()
    if drift_report.overall_health_pct < config.drift.ci_threshold:
        log.warn("Evidence below CI threshold \u2014 SAD! Run `mpga evidence heal` or `mpga sync`")
    if scope_count == 0:
        log.warn("No scope documents \u2014 SAD! Run `mpga sync` to generate them")
    if not drift_report.ci_pass:
        log.error(
            f"CI would FAIL at {config.drift.ci_threshold}% threshold \u2014 TOTAL DISASTER!"
        )
    else:
        log.success("All health checks PASS \u2014 TREMENDOUS!")
    log.blank()
