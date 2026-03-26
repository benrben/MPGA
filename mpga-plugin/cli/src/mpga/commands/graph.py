"""Dependency graph management commands."""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import console, log
from mpga.core.scanner import scan
from mpga.generators.graph_md import build_graph, render_graph_md


@click.group("graph")
def graph() -> None:
    """Dependency graph management."""


@graph.command("show")
def graph_show() -> None:
    """Print dependency graph to terminal."""
    project_root = find_project_root() or Path.cwd()
    graph_path = project_root / "MPGA" / "GRAPH.md"

    if not graph_path.exists():
        log.error("GRAPH.md not found. Run `mpga sync` first.")
        sys.exit(1)

    console.print(graph_path.read_text(encoding="utf-8"))


@graph.command("export")
@click.option("--mermaid", is_flag=True, help="Export as mermaid diagram")
@click.option("--json", "as_json", is_flag=True, help="Export as JSON")
def graph_export(mermaid: bool, as_json: bool) -> None:
    """Export dependency graph."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)

    log.info("Building dependency graph...")
    scan_result = scan(str(project_root), config.project.ignore, False)
    graph_data = build_graph(scan_result, config)

    if as_json:
        console.print(json.dumps(asdict(graph_data), indent=2))
        return

    if mermaid:
        lines = ["```mermaid", "graph TD"]
        seen: set[str] = set()
        for dep in graph_data.dependencies:
            key = f"{dep.from_}-->{dep.to}"
            if key not in seen:
                seen.add(key)
                safe_from = re.sub(r"[^a-zA-Z0-9_]", "_", dep.from_)
                safe_to = re.sub(r"[^a-zA-Z0-9_]", "_", dep.to)
                lines.append(f"    {safe_from} --> {safe_to}")
        lines.append("```")
        console.print("\n".join(lines))
        return

    # Default: print text version
    md = render_graph_md(graph_data)
    console.print(md)
