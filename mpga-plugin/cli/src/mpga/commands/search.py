"""Search CLI command — query global_fts via global_search."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click

from mpga.db.search import global_search, rebuild_global_fts


def _get_conn() -> sqlite3.Connection:
    from mpga.core.config import find_project_root
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    project_root = Path(find_project_root() or Path.cwd())
    db_path = str(project_root / ".mpga" / "mpga.db")
    conn = get_connection(db_path)
    create_schema(conn)
    return conn


@click.command("search")
@click.argument("query")
@click.option("--type", "types", multiple=True, help="Filter by entity type (task, scope, evidence, milestone, decision)")
@click.option("--limit", default=10, show_default=True, help="Maximum number of results")
@click.option("--full", is_flag=True, default=False, help="Show complete content instead of snippet")
def search_cmd(query: str, types: tuple[str, ...], limit: int, full: bool) -> None:
    """Search the project knowledge base using full-text search."""
    conn = _get_conn()
    try:
        rebuild_global_fts(conn)
        results = global_search(conn, query, types=list(types) if types else None, limit=limit)
        if not results:
            try:
                fts_count = conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]
            except sqlite3.OperationalError:
                fts_count = -1
    finally:
        conn.close()

    if not results:
        if fts_count == 0:
            click.echo(
                "No results found — the search index is empty.\n"
                "Run `mpga sync` to populate the search index, then try again."
            )
        else:
            click.echo("No results found.")
        return

    for r in results:
        header = f"[{r.entity_type}] {r.entity_id}  {r.title}"
        click.echo(header)
        if full:
            click.echo(f"  {r.snippet}")
        else:
            # Show at most 2 lines of snippet
            lines = r.snippet.split("\n")[:2]
            for line in lines:
                click.echo(f"  {line}")
        click.echo()
