from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log, mini_banner, progress_bar


@click.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status_cmd(as_json: bool) -> None:
    """Show project health dashboard."""
    project_root = find_project_root() or Path.cwd()
    mpga_dir = Path(project_root) / "MPGA"
    config = load_config(project_root)

    if not mpga_dir.exists():
        log.error("MPGA not initialized. Run `mpga init` first.")
        sys.exit(1)

    index_path = mpga_dir / "INDEX.md"
    board_path = mpga_dir / "board" / "board.json"
    scopes_dir = mpga_dir / "scopes"

    # Read board state
    board_state: dict | None = None
    if board_path.exists():
        board_state = json.loads(board_path.read_text(encoding="utf-8"))

    # Count scopes
    scopes: list[str] = []
    if scopes_dir.exists():
        scopes = [f.name for f in scopes_dir.iterdir() if f.suffix == ".md"]

    # Read INDEX.md for last sync info
    last_sync = "never"
    evidence_coverage = "0%"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        sync_match = re.search(r"\*\*Last sync:\*\* (.+)", content)
        if sync_match and "run" not in sync_match.group(1):
            last_sync = sync_match.group(1)
        cov_match = re.search(r"\*\*Evidence coverage:\*\* ([\d.]+%)", content)
        if cov_match:
            evidence_coverage = cov_match.group(1)

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

    # -- Knowledge Layer --
    log.header(f"Status \u2014 {config.project.name} (Looking TREMENDOUS)")

    log.section("  \U0001f4da Knowledge Layer")
    log.kv("Last sync", last_sync, 4)
    log.kv("Scopes", str(len(scopes)), 4)
    log.kv("Evidence", evidence_coverage, 4)
    log.kv(
        "INDEX.md",
        "[green]\u2713 present[/]" if index_path.exists() else "[red]\u2717 missing[/]",
        4,
    )

    if scopes:
        log.section("  \U0001f5c2  Scopes")
        for scope_file in scopes:
            scope_name = scope_file.replace(".md", "")
            scope_path = scopes_dir / scope_file
            scope_content = scope_path.read_text(encoding="utf-8")
            health_match = re.search(r"\*\*Health:\*\* (.+)", scope_content)
            health = health_match.group(1) if health_match else "[dim]unknown[/]"
            click.echo(f"    {scope_name:<22} {health}")

    # -- Board --
    if board_state:
        stats = board_state.get("stats", {})
        log.section("  \U0001f4cb Task Board")
        milestone = board_state.get("milestone") or "[dim]none[/]"
        log.kv("Milestone", str(milestone), 4)
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

    # -- Config --
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
