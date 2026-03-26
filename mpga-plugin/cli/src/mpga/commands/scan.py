from __future__ import annotations

import json
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log
from mpga.core.scanner import detect_project_type, scan


@click.command("scan")
@click.option("--deep", is_flag=True, help="Full analysis (default)")
@click.option("--quick", is_flag=True, help="File tree and exports only")
@click.option("--lang", default=None, help="Language hint (auto-detected if omitted)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def scan_cmd(deep: bool, quick: bool, lang: str | None, as_json: bool) -> None:
    """Analyze codebase structure and file tree."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)

    if not as_json:
        log.header("MPGA Scan")
        log.info(f"Scanning {project_root}...")

    result = scan(str(project_root), config.project.ignore, not quick)

    if as_json:
        click.echo(json.dumps(_scan_result_to_dict(result), indent=2))
        return

    project_type = detect_project_type(result)
    total_lines = result.total_lines

    click.echo("")
    log.bold("Project summary")
    click.echo(f"  Type:      {project_type}")
    click.echo(f"  Root:      {project_root}")
    click.echo(f"  Files:     {result.total_files}")
    click.echo(f"  Lines:     {total_lines:,}")

    click.echo("")
    log.bold("Languages")
    lang_entries = sorted(result.languages.items(), key=lambda x: x[1]["lines"], reverse=True)
    for lang_name, stats in lang_entries:
        pct = round((stats["lines"] / total_lines) * 100) if total_lines > 0 else 0
        filled = round(pct / 5)
        bar = "\u2588" * filled + "\u2591" * (20 - filled)
        click.echo(
            f"  {lang_name:<12} {bar} {pct}%  ({stats['files']} files, {stats['lines']:,} lines)"
        )

    if result.entry_points:
        click.echo("")
        log.bold("Entry points")
        for ep in result.entry_points:
            click.echo(f"  {ep}")

    if result.top_level_dirs:
        click.echo("")
        log.bold("Top-level directories")
        for d in result.top_level_dirs:
            click.echo(f"  {d}/")

    if deep:
        click.echo("")
        log.bold("Largest files")
        sorted_files = sorted(result.files, key=lambda f: f.lines, reverse=True)[:10]
        for f in sorted_files:
            click.echo(f"  {str(f.lines):>6} lines  {f.filepath}")

    click.echo("")
    log.dim("Run `mpga sync` to generate the full knowledge layer from this scan.")


def _scan_result_to_dict(result: object) -> dict:
    """Convert a ScanResult dataclass to a JSON-serializable dict."""
    from dataclasses import asdict

    return asdict(result)  # type: ignore[arg-type]
