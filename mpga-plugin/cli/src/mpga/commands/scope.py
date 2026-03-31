"""Scope document management commands."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import click

from mpga.bridge.compress import compress_scope
from mpga.core.config import find_project_root
from mpga.core.logger import console, log
from mpga.db.connection import get_connection
from mpga.db.repos.scopes import Scope, ScopeRepo
from mpga.db.schema import create_schema
from mpga.evidence.parser import evidence_stats, parse_evidence_links

# Maximum number of scope search results to display.
MAX_SEARCH_RESULTS = 3
# Number of matched paragraphs to show for `scope show --query`.
MAX_SCOPE_QUERY_PARAGRAPHS = 1


def _get_scope_repo(project_root: Path) -> tuple[object, ScopeRepo]:
    conn = get_connection(str(project_root / ".mpga" / "mpga.db"))
    create_schema(conn)
    return conn, ScopeRepo(conn)


def _extract_scope_summary(content: str) -> str:
    match = re.search(r"^## Summary\s*\n(.*?)(?:\n## |\Z)", content, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _scope_from_content(name: str, content: str) -> Scope:
    links = parse_evidence_links(content)
    stats = evidence_stats(links)
    health_match = re.search(r"\*\*Health:\*\* (.+)", content)
    status = health_match.group(1) if health_match else "unknown"
    verified_match = re.search(r"\*\*Last verified:\*\* (.+)", content)
    last_verified = verified_match.group(1) if verified_match else None
    return Scope(
        id=name,
        name=name,
        summary=_extract_scope_summary(content),
        content=content,
        status=status,
        evidence_total=stats.total,
        evidence_valid=stats.valid,
        last_verified=last_verified,
    )


def _print_scope_evidence_footer(content: str) -> None:
    links = parse_evidence_links(content)
    stats = evidence_stats(links)
    console.print("")
    log.dim(
        f"\u2500\u2500\u2500 Evidence: {stats.valid} valid, {stats.stale} stale, "
        f"{stats.unknown} unknown ({stats.health_pct}% health) \u2500\u2500\u2500"
    )


def _matching_scope_paragraphs(content: str, query_text: str) -> list[str]:
    terms = [term.lower() for term in re.findall(r"\w+", query_text) if term.strip()]
    if not terms:
        return []

    scored: list[tuple[int, int, str]] = []
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]
    for index, paragraph in enumerate(paragraphs):
        if paragraph.startswith("# Scope:"):
            continue

        lower = paragraph.lower()
        score = sum(lower.count(term) for term in terms)
        if score > 0:
            scored.append((score, index, paragraph))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [paragraph for _, _, paragraph in scored[:MAX_SCOPE_QUERY_PARAGRAPHS]]


def _scope_query_hits(paragraph: str, query_text: str) -> str:
    hits: list[str] = []
    terms = sorted({term for term in re.findall(r"\w+", query_text) if term.strip()}, key=len, reverse=True)
    for term in terms:
        pattern = re.compile(rf"\b({re.escape(term)})\b", re.IGNORECASE)
        match = pattern.search(paragraph)
        if match:
            hits.append(f"[{match.group(1)}]")
    return " ".join(hits)


@click.group("scope")
def scope() -> None:
    """Manage scope documents."""


@scope.command("list")
def scope_list() -> None:
    """Show all scopes with health status."""
    project_root = find_project_root() or Path.cwd()

    conn, repo = _get_scope_repo(project_root)
    try:
        db_scopes = repo.list_all()
    finally:
        conn.close()

    if not db_scopes:
        log.error("No scopes found. Run `mpga sync` first.")
        return

    log.header("Scopes")
    rows: list[list[str]] = [["Scope", "Health", "Evidence", "Last verified"]]
    for scope_row in db_scopes:
        verified = scope_row.last_verified or "?"
        rows.append([
            scope_row.id,
            scope_row.status,
            f"{scope_row.evidence_valid}/{scope_row.evidence_total}",
            verified,
        ])
    log.table(rows)


@scope.command("show")
@click.argument("name")
@click.option("--full", is_flag=True, help="Show the complete scope document.")
@click.option("--query", "query_text", help="Show only snippets that match this search.")
@click.option("--json", "as_json", is_flag=True, help="Output scope metadata as JSON.")
def scope_show(name: str, full: bool, query_text: str | None, as_json: bool = False) -> None:
    """Display a scope with evidence status."""
    if full and query_text:
        raise click.UsageError("Use either --full or --query, not both.")

    project_root = find_project_root() or Path.cwd()

    conn, repo = _get_scope_repo(project_root)
    try:
        scope_row = repo.get(name)
        query_matches = (
            repo.search(query_text, limit=1, scope_id=name)
            if query_text
            else []
        )
    finally:
        conn.close()

    if scope_row is None:
        log.error(f"Scope '{name}' not found. Run `mpga scope list` to see available scopes.")
        sys.exit(1)

    if as_json:
        payload = {
            "name": scope_row.name,
            "description": scope_row.summary or "",
            "health": scope_row.status,
            "evidence_count": scope_row.evidence_total,
        }
        click.echo(json.dumps(payload))
        return

    if query_text:
        if not query_matches:
            log.info(f'No matches for "{query_text}" in scope "{name}"')
            return

        content = scope_row.content or ""

        matches = _matching_scope_paragraphs(content, query_text)

        if matches:
            log.header(f'Scope search in {name}: "{query_text}"')
            for paragraph in matches:
                console.print("")
                hits = _scope_query_hits(paragraph, query_text)
                rendered = f"{paragraph} {hits}".rstrip() if hits else paragraph
                log.dim(rendered)
            return

        log.header(f'Scope search in {name}: "{query_text}"')
        for _, snippet in query_matches:
            console.print("")
            log.dim(f"  ...{snippet}...")
        return

    if scope_row.content is None:
        log.error("Scope content missing from DB. Run `mpga sync` to rebuild.")
        sys.exit(1)

    content = scope_row.content

    if full:
        console.print(content)
        _print_scope_evidence_footer(content)
        return

    console.print(compress_scope(scope_row))


@scope.command("add")
@click.argument("name")
def scope_add(name: str) -> None:
    """Create a new empty scope document."""
    project_root = find_project_root() or Path.cwd()

    now = date.today().isoformat()
    template = f"""# Scope: {name}

## Summary
<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code
<!-- TODO: The main entry points -- files or modules someone should open first -->

## Context / stack / skills
<!-- TODO: Technologies, integrations, and relevant expertise -->

## Who and what triggers it
<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

## What happens
<!-- TODO: The flow in plain language: inputs, main steps, outputs or side effects -->

## Rules and edge cases
<!-- TODO: Constraints, validation, permissions, failures, retries, empty states -->

## Concrete examples
<!-- TODO: A few real scenarios ("when X happens, Y results") -->

## UI
<!-- TODO: Screens or flows if relevant. Remove this section if not applicable. -->

## Navigation
**Parent:** [INDEX.md](../INDEX.md)

## Relationships
<!-- TODO: What this depends on, what depends on it, and shared concepts -->

## Diagram
<!-- TODO: Flow, sequence, or boundary diagrams (must match written story and evidence) -->

## Traces
<!-- TODO: Step-by-step paths through the system:

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | (layer) | (description) | [E] file:line |
-->

## Evidence index
<!-- TODO: Map claims to code references:

| Claim | Evidence |
|-------|----------|
| (description) | [E] file :: symbol |
-->

## Deeper splits
<!-- TODO: Pointers to sub-topic scopes if this capability is large enough to split -->

## Confidence and notes
- **Confidence:** low -- manually created, not yet filled
- **Evidence coverage:** 0/0 verified
- **Last verified:** {now}
- **Drift risk:** unknown
<!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history
- {now}: Created manually
"""
    conn, repo = _get_scope_repo(project_root)
    try:
        existing = repo.get(name)
        if existing is not None:
            log.error(f"Scope '{name}' already exists.")
            sys.exit(1)
        repo.create(
            Scope(
                id=name,
                name=name,
                summary="<!-- TODO: Describe what this area does and what is intentionally out of scope -->",
                content=template,
                last_verified=now,
            )
        )
    finally:
        conn.close()
    log.success(f"Created scope '{name}' in DB")


@scope.command("remove")
@click.argument("name")
def scope_remove(name: str) -> None:
    """Remove a scope from the DB."""
    project_root = find_project_root() or Path.cwd()

    conn, repo = _get_scope_repo(project_root)
    try:
        existing = repo.get(name)
        if existing is None:
            log.error(f"Scope '{name}' not found.")
            sys.exit(1)
        repo.delete(name)
    finally:
        conn.close()

    log.success(f"Removed scope '{name}'")


@scope.command("update")
@click.argument("name")
@click.option("--file", "-f", type=click.File("r"), default="-", help="Read content from file (default: stdin).")
def scope_update(name: str, file: object) -> None:
    """Update a scope's content from a markdown file or stdin.

    Usage:
        cat enriched_scope.md | mpga scope update <name>
        mpga scope update <name> --file enriched_scope.md
    """
    project_root = find_project_root() or Path.cwd()

    # Read content from stdin or file
    content = file.read()  # type: ignore
    if not content.strip():
        log.error("No content provided. Pipe markdown via stdin or use --file.")
        sys.exit(1)

    conn, repo = _get_scope_repo(project_root)
    try:
        existing = repo.get(name)
        if existing is None:
            log.error(f"Scope '{name}' not found. Create it first with `mpga scope add {name}`.")
            sys.exit(1)

        # Parse content to extract metadata
        scope_obj = _scope_from_content(name, content)

        # Update in database
        repo.update(scope_obj)

    finally:
        conn.close()

    log.success(f"Updated scope '{name}' ({scope_obj.evidence_valid}/{scope_obj.evidence_total} evidence links verified)")


@scope.command("query")
@click.argument("question")
def scope_query(question: str) -> None:
    """Search scopes for an answer."""
    project_root = find_project_root() or Path.cwd()

    conn, repo = _get_scope_repo(project_root)
    try:
        db_matches = repo.search(question, limit=MAX_SEARCH_RESULTS)
    finally:
        conn.close()

    if not db_matches:
        log.error("No scopes found. Run `mpga sync` first.")
        return

    log.header(f'Scope search: "{question}"')
    for scope_row, snippet in db_matches:
        console.print("")
        log.bold(f"  {scope_row.id}")
        log.dim(f"  ...{snippet}...")
