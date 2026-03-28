from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

from mpga.board.board import load_board, recalc_stats
from mpga.core.config import find_project_root, load_config
from mpga.core.logger import (
    grade_color,
    log,
    mini_banner,
    progress_bar,
    status_badge,
)
from mpga.evidence.drift import run_drift_check

# Evidence health percentage at or above which status is considered good.
EVIDENCE_HEALTH_GOOD_PCT = 80
# Health percentage at or above which the project earns an A grade.
GRADE_A_THRESHOLD = 95
# Multiplier applied to CI threshold to determine the C grade cutoff.
GRADE_C_MULTIPLIER = 0.7


def _compute_grade(health_pct: int, threshold: int) -> str:
    if health_pct >= GRADE_A_THRESHOLD:
        return "A"
    if health_pct >= threshold:
        return "B"
    if health_pct >= threshold * GRADE_C_MULTIPLIER:
        return "C"
    return "D"


def _get_last_sync(mpga_dir: Path) -> str:
    index_path = mpga_dir / "INDEX.md"
    if not index_path.exists():
        return "never"
    content = index_path.read_text(encoding="utf-8")
    m = re.search(r"\*\*Last sync:\*\* (.+)", content)
    if m and "run" not in m.group(1):
        return m.group(1).strip()
    return "never"


@click.command("health")
@click.option("--verbose", is_flag=True, help="Detailed breakdown")
@click.option("--json", "as_json", is_flag=True, help="Machine-readable output")
def health_cmd(verbose: bool, as_json: bool) -> None:
    """Overall project health report."""
    project_root = find_project_root() or Path.cwd()
    mpga_dir = Path(project_root) / "MPGA"
    config = load_config(project_root)

    if not mpga_dir.exists():
        log.error("MPGA not initialized. Run `mpga init` first.")
        sys.exit(1)

    # Gather evidence health
    drift_report = run_drift_check(str(project_root), config.drift.ci_threshold)

    # Gather board health
    board_dir = mpga_dir / "board"
    tasks_dir = board_dir / "tasks"
    board_stats: dict | None = None
    if (board_dir / "board.json").exists():
        board = load_board(str(board_dir))
        recalc_stats(board, str(tasks_dir))
        board_stats = {
            "total": board.stats.total,
            "done": board.stats.done,
            "in_flight": board.stats.in_flight,
            "blocked": board.stats.blocked,
            "progress_pct": board.stats.progress_pct,
        }

    # Gather scope count
    scopes_dir = mpga_dir / "scopes"
    scope_count = 0
    if scopes_dir.exists():
        scope_count = len([f for f in scopes_dir.iterdir() if f.suffix == ".md"])

    overall_grade = _compute_grade(drift_report.overall_health_pct, config.drift.ci_threshold)

    health = {
        "initialized": True,
        "evidenceHealth": drift_report.overall_health_pct,
        "evidenceTarget": config.evidence.coverage_threshold * 100,
        "ciThreshold": config.drift.ci_threshold,
        "ciPass": drift_report.ci_pass,
        "scopes": scope_count,
        "board": board_stats,
        "lastSync": _get_last_sync(mpga_dir),
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
