"""Drift detection command."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import console, log
from mpga.commands.evidence import EVIDENCE_HEALTH_GOOD_PCT, EVIDENCE_HEALTH_WARN_PCT
from mpga.evidence.drift import apply_healed_items_to_db, run_drift_check


@click.command("drift")
@click.option("--report", "report_mode", is_flag=True, help="Full staleness report (default)")
@click.option("--quick", is_flag=True, help="Fast check (for hooks)")
@click.option("--ci", is_flag=True, help="CI mode -- exit code 0 = pass, 1 = fail")
@click.option("--threshold", default="80", help="Min % of valid evidence (default: 80)")
@click.option("--fix", is_flag=True, help="Auto-sync stale scopes")
@click.option("--scope", default=None, help="Check specific scope")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def drift(
    report_mode: bool,
    quick: bool,
    ci: bool,
    threshold: str,
    fix: bool,
    scope: str | None,
    as_json: bool,
) -> None:
    """Detect drift between evidence links and codebase."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)
    threshold_pct = int(threshold or str(config.drift.ci_threshold))

    report = run_drift_check(str(project_root), threshold_pct, scope)

    if as_json:
        click.echo(json.dumps(asdict(report), indent=2))
        if ci and not report.ci_pass:
            sys.exit(1)
        return

    if quick:
        # Minimal output for hooks
        stale_total = sum(r.stale_links for r in report.scopes)
        if stale_total > 0:
            log.warn(
                f"Drift detected: {stale_total} stale evidence link(s). "
                "Run `mpga evidence heal` to fix."
            )
        if ci and not report.ci_pass:
            sys.exit(1)
        return

    log.header("MPGA Drift Report")
    console.print(f"  Timestamp: {report.timestamp}")
    console.print(f"  Overall:   {report.overall_health_pct}% (threshold: {threshold_pct}%)")
    console.print("")

    if not report.scopes:
        log.info("No scopes found. Run `mpga sync` to generate them.")
        return

    for scope_report in report.scopes:
        if scope_report.health_pct >= EVIDENCE_HEALTH_GOOD_PCT:
            icon = "[green]\u2713 healthy[/]"
        elif scope_report.health_pct >= EVIDENCE_HEALTH_WARN_PCT:
            icon = "[yellow]\u26a0 drift[/]"
        else:
            icon = "[red]\u2717 stale[/]"

        console.print(
            f"  {scope_report.scope:<20} {icon}   "
            f"{scope_report.valid_links}/{scope_report.total_links} links valid  "
            f"({scope_report.health_pct}%)"
        )

        if report_mode:
            for item in scope_report.stale_items:
                start = f":{item.link.start_line}" if item.link.start_line else ""
                log.dim(f"    \u2717 stale: {item.link.filepath}{start} \u2014 {item.reason}")
            for item in scope_report.healed_items:
                log.dim(
                    f"    ~ healed: {item.link.filepath} "
                    f"line range updated to {item.new_start}-{item.new_end}"
                )

    if fix:
        console.print("")
        log.info("Auto-fixing stale links...")
        total_healed = 0
        for scope_report in report.scopes:
            if not scope_report.healed_items:
                continue
            healed = apply_healed_items_to_db(str(project_root), scope_report)
            if healed > 0:
                log.success(f"{scope_report.scope}: healed {healed} link(s)")
                total_healed += healed
        if total_healed > 0:
            log.success(f"Total healed: {total_healed}")
        stale = sum(r.stale_links for r in report.scopes)
        if stale > 0:
            log.warn(f"{stale} link(s) need manual review (symbol not found in file)")

    console.print("")
    if report.ci_pass:
        log.success(
            f"Drift check passed ({report.overall_health_pct}% >= {threshold_pct}%)"
        )
    else:
        log.error(
            f"Drift check FAILED ({report.overall_health_pct}% < {threshold_pct}%)"
        )
        if ci:
            sys.exit(1)
