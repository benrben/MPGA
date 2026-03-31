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
from mpga.db.connection import get_connection
from mpga.db.repos.graph import GraphEdge, GraphRepo
from mpga.db.schema import create_schema
from mpga.generators.graph_md import build_graph, render_graph_md


@click.group("graph")
def graph() -> None:
    """Dependency graph management."""


def _load_graph_edges(project_root: Path) -> list[GraphEdge]:
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return []

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        return GraphRepo(conn).get_all()
    finally:
        conn.close()


def _render_graph_edges_md(edges: list[GraphEdge]) -> str:
    lines = ["# Dependency graph", "", "## Module dependencies", ""]
    if not edges:
        lines.append("(no inter-module dependencies detected)")
    else:
        for edge in edges:
            lines.append(f"- `{edge.source}` -> `{edge.target}` ({edge.type})")
    return "\n".join(lines)


@graph.command("show")
def graph_show() -> None:
    """Print dependency graph to terminal."""
    project_root = find_project_root() or Path.cwd()

    db_edges = _load_graph_edges(project_root)
    if not db_edges:
        log.error("No graph data found. Run `mpga sync` first.")
        sys.exit(1)

    console.print(_render_graph_edges_md(db_edges))


@graph.command("export")
@click.option("--mermaid", is_flag=True, help="Export as mermaid diagram")
@click.option("--json", "as_json", is_flag=True, help="Export as JSON")
def graph_export(mermaid: bool, as_json: bool) -> None:
    """Export dependency graph."""
    project_root = find_project_root() or Path.cwd()
    db_edges = _load_graph_edges(project_root)

    if as_json:
        if db_edges:
            console.print(
                json.dumps(
                    {
                        "dependencies": [
                            {"from": edge.source, "to": edge.target, "type": edge.type}
                            for edge in db_edges
                        ]
                    },
                    indent=2,
                )
            )
            return

        config = load_config(project_root)
        log.info("Building dependency graph...")
        scan_result = scan(str(project_root), config.project.ignore, False)
        graph_data = build_graph(scan_result, config)
        console.print(json.dumps(asdict(graph_data), indent=2))
        return

    if mermaid:
        lines = ["```mermaid", "graph TD"]
        seen: set[str] = set()
        edges = db_edges
        if not edges:
            config = load_config(project_root)
            log.info("Building dependency graph...")
            scan_result = scan(str(project_root), config.project.ignore, False)
            graph_data = build_graph(scan_result, config)
            edges = [
                GraphEdge(source=dep.from_, target=dep.to, type=dep.type)
                for dep in graph_data.dependencies
            ]
        for dep in edges:
            key = f"{dep.source}-->{dep.target}"
            if key not in seen:
                seen.add(key)
                safe_from = re.sub(r"[^a-zA-Z0-9_]", "_", dep.source)
                safe_to = re.sub(r"[^a-zA-Z0-9_]", "_", dep.target)
                lines.append(f"    {safe_from} --> {safe_to}")
        lines.append("```")
        console.print("\n".join(lines))
        return

    # Default: print text version
    if db_edges:
        md = _render_graph_edges_md(db_edges)
    else:
        config = load_config(project_root)
        log.info("Building dependency graph...")
        scan_result = scan(str(project_root), config.project.ignore, False)
        graph_data = build_graph(scan_result, config)
        md = render_graph_md(graph_data)
    console.print(md)
