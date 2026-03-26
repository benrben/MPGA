from __future__ import annotations

import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log, victory
from mpga.core.scanner import scan
from mpga.evidence.drift import run_drift_check
from mpga.generators.graph_md import build_graph, render_graph_md
from mpga.generators.index_md import render_index_md
from mpga.generators.scope_md import group_into_scopes, render_scope_md


@click.command("sync")
@click.option("--full", is_flag=True, help="Rebuild everything (default)")
@click.option("--incremental", is_flag=True, help="Only update changed files since last sync")
def sync_cmd(full: bool, incremental: bool) -> None:
    """Regenerate/update the knowledge layer."""
    project_root = find_project_root() or Path.cwd()
    mpga_dir = Path(project_root) / "MPGA"

    if not mpga_dir.exists():
        log.error("MPGA not initialized \u2014 SAD! Run `mpga init` to Make This Project Great Again.")
        sys.exit(1)

    config = load_config(project_root)
    log.header("MPGA Sync \u2014 Going to be TREMENDOUS")

    # Step 1: Scan
    log.info("Scanning the GREATEST codebase...")
    scan_result = scan(str(project_root), config.project.ignore, True)
    log.success(f"Scanned {scan_result.total_files} files ({scan_result.total_lines:,} lines)")

    # Step 2: Build dependency graph
    log.info("Building a TREMENDOUS dependency graph...")
    graph = build_graph(scan_result, config)
    graph_md = render_graph_md(graph)
    (mpga_dir / "GRAPH.md").write_text(graph_md)
    log.success(f"GRAPH.md \u2014 {len(graph.dependencies)} dependencies, {len(graph.circular)} circular")

    # Step 3: Generate scope docs
    log.info("Generating scope documents \u2014 the BEST docs...")
    scopes_dir = mpga_dir / "scopes"
    scopes_dir.mkdir(parents=True, exist_ok=True)
    scopes = group_into_scopes(scan_result, graph, config)

    for scope in scopes:
        scope_path = scopes_dir / f"{scope.name}.md"
        # In incremental mode, skip if file exists and scope hasn't changed
        if incremental and scope_path.exists():
            continue
        scope_md = render_scope_md(scope, str(project_root))
        scope_path.write_text(scope_md)
    log.success(f"Generated {len(scopes)} scope documents")

    # Step 4: Generate INDEX.md
    log.info("Generating INDEX.md \u2014 the most BEAUTIFUL index...")

    # Read active milestone
    active_milestone: str | None = None
    milestones_dir = mpga_dir / "milestones"
    if milestones_dir.exists():
        m_dirs = [
            d.name for d in sorted(milestones_dir.iterdir()) if d.is_dir()
        ]
        if m_dirs:
            active_milestone = m_dirs[-1]

    drift_report = run_drift_check(str(project_root), config.drift.ci_threshold)
    evidence_coverage = (
        0.0 if drift_report.total_links == 0
        else drift_report.valid_links / drift_report.total_links
    )

    index_md = render_index_md(scan_result, config, scopes, active_milestone, evidence_coverage)
    (mpga_dir / "INDEX.md").write_text(index_md)
    log.success("INDEX.md generated")

    # Summary
    victory("Sync COMPLETE! Your project is looking FANTASTIC!")
    click.echo("")
    log.dim(f"  {len(scopes)} scopes in MPGA/scopes/ \u2014 WINNING!")
    log.dim("  Run `mpga evidence verify` to check evidence health \u2014 believe me, you want to")
    log.dim("  Run `mpga status` to view your INCREDIBLE dashboard")
