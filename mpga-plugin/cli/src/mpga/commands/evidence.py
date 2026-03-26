"""Evidence link management commands."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import console, log, progress_bar
from mpga.evidence.drift import heal_scope_file, run_drift_check
from mpga.evidence.parser import format_evidence_link

# Evidence health percentage at or above which status is considered good.
EVIDENCE_HEALTH_GOOD_PCT = 80
# Evidence health percentage at or above which a warning (not error) is shown.
EVIDENCE_HEALTH_WARN_PCT = 50


@click.group("evidence")
def evidence() -> None:
    """Evidence link management."""


@evidence.command("verify")
@click.option("--scope", default=None, help="Check specific scope only")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def evidence_verify(scope: str | None, as_json: bool) -> None:
    """Check all evidence links resolve to real code."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)

    report = run_drift_check(str(project_root), config.drift.ci_threshold, scope)

    if as_json:
        from dataclasses import asdict

        click.echo(json.dumps(asdict(report), indent=2))
        return

    log.header("Evidence Verification")

    for scope_report in report.scopes:
        if scope_report.health_pct >= EVIDENCE_HEALTH_GOOD_PCT:
            icon = "[green]\u2713[/]"
        elif scope_report.health_pct >= EVIDENCE_HEALTH_WARN_PCT:
            icon = "[yellow]\u26a0[/]"
        else:
            icon = "[red]\u2717[/]"
        console.print(
            f"\n{icon} [bold]{scope_report.scope}[/]  "
            f"{scope_report.health_pct}% ({scope_report.valid_links}/{scope_report.total_links} valid)"
        )

        if scope_report.stale_items:
            log.dim("  Stale links:")
            for item in scope_report.stale_items:
                log.dim(f"    {format_evidence_link(item.link)} \u2014 {item.reason}")
        if scope_report.healed_items:
            log.dim("  Healed links:")
            for item in scope_report.healed_items:
                log.dim(
                    f"    {item.link.filepath}:{item.new_start}-{item.new_end} "
                    f"(was {item.link.start_line}-{item.link.end_line})"
                )

    console.print("")
    log.bold("Overall")
    console.print(
        f"  Health:  {progress_bar(report.valid_links, report.total_links)} "
        f"({report.valid_links}/{report.total_links})"
    )
    if report.total_links == 0:
        log.info("No evidence links found. Run `mpga sync` to generate them.")
    elif report.overall_health_pct >= EVIDENCE_HEALTH_GOOD_PCT:
        log.success(f"Evidence health: {report.overall_health_pct}%")
    else:
        log.warn(
            f"Evidence health: {report.overall_health_pct}% \u2014 "
            "run `mpga evidence heal` to fix stale links"
        )


@evidence.command("heal")
@click.option("--auto", "auto", is_flag=True, help="Auto-fix without confirmation")
@click.option("--scope", default=None, help="Heal specific scope only")
def evidence_heal(auto: bool, scope: str | None) -> None:
    """Re-resolve broken links via AST and update scope files."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)

    log.info("Running evidence heal...")
    report = run_drift_check(str(project_root), config.drift.ci_threshold, scope)

    total_healed = 0
    for scope_report in report.scopes:
        if not scope_report.healed_items:
            continue
        result = heal_scope_file(scope_report)
        if result.healed > 0:
            Path(scope_report.scope_path).write_text(result.content, encoding="utf-8")
            log.success(f"{scope_report.scope}: healed {result.healed} link(s)")
            total_healed += result.healed

    stale_count = sum(r.stale_links for r in report.scopes)
    if total_healed > 0:
        log.success(f"Total healed: {total_healed} link(s)")
    if stale_count > 0:
        log.warn(
            f"{stale_count} link(s) could not be healed (symbol not found) \u2014 "
            "manual review required"
        )
    if total_healed == 0 and stale_count == 0:
        log.success("All evidence links are already valid.")


@evidence.command("coverage")
@click.option("--min", "min_pct", default="20", help="Fail if coverage below this %")
def evidence_coverage(min_pct: str) -> None:
    """Report evidence-to-code ratio."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)
    report = run_drift_check(str(project_root), config.drift.ci_threshold)

    threshold = int(min_pct)
    log.header("Evidence Coverage")

    for scope_report in report.scopes:
        bar = progress_bar(scope_report.valid_links, scope_report.total_links)
        console.print(
            f"  {scope_report.scope:<20} {bar}  "
            f"({scope_report.valid_links}/{scope_report.total_links})"
        )

    console.print("")
    pct = report.overall_health_pct
    console.print(f"  Overall: {pct}% (threshold: {threshold}%)")

    if pct < threshold:
        log.warn(f"Coverage {pct}% is below threshold {threshold}%")
        sys.exit(1)
    else:
        log.success(f"Coverage {pct}% meets threshold {threshold}%")


@evidence.command("add")
@click.argument("scope_name")
@click.argument("link")
def evidence_add(scope_name: str, link: str) -> None:
    """Manually add an evidence link to a scope document."""
    project_root = find_project_root() or Path.cwd()
    scope_path = project_root / "MPGA" / "scopes" / f"{scope_name}.md"

    if not scope_path.exists():
        log.error(f"Scope '{scope_name}' not found.")
        sys.exit(1)

    content = scope_path.read_text(encoding="utf-8")
    evidence_link = link if link.startswith("[") else f"[E] {link}"

    # Insert before the Known unknowns section
    if "## Known unknowns" in content:
        updated = content.replace(
            "## Known unknowns", f"{evidence_link}\n\n## Known unknowns"
        )
    else:
        updated = content + "\n" + evidence_link + "\n"

    scope_path.write_text(updated, encoding="utf-8")
    log.success(f"Added evidence link to scope '{scope_name}': {evidence_link}")
