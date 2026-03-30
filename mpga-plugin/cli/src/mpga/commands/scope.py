"""Scope document management commands."""
from __future__ import annotations

import re
import sys
import time
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

# Number of characters of context to show before a search match in excerpts.
EXCERPT_CONTEXT_CHARS = 50
# Maximum length of a search result excerpt in characters.
EXCERPT_MAX_LENGTH = 200
# Maximum number of scope search results to display.
MAX_SEARCH_RESULTS = 3
# Number of matched paragraphs to show for `scope show --query`.
MAX_SCOPE_QUERY_PARAGRAPHS = 1


def _get_scopes_dir(project_root: Path) -> Path:
    return project_root / "MPGA" / "scopes"


def _get_scope_repo(project_root: Path) -> tuple[object, ScopeRepo]:
    conn = get_connection(str(project_root / ".mpga" / "mpga.db"))
    create_schema(conn)
    return conn, ScopeRepo(conn)


def _read_scope_file(scope_path: Path) -> str:
    return scope_path.read_text(encoding="utf-8")


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
    scopes_dir = _get_scopes_dir(project_root)

    conn, repo = _get_scope_repo(project_root)
    try:
        db_scopes = repo.list_all()
    finally:
        conn.close()

    if db_scopes:
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
        return

    if not scopes_dir.exists():
        log.error("No scopes found. Run `mpga sync` first.")
        return

    files = sorted(f.name for f in scopes_dir.iterdir() if f.suffix == ".md")
    if not files:
        log.info("No scopes found. Run `mpga sync` to generate them.")
        return

    log.header("Scopes")
    rows: list[list[str]] = [["Scope", "Health", "Evidence", "Last verified"]]
    for file in files:
        content = (scopes_dir / file).read_text(encoding="utf-8")
        links = parse_evidence_links(content)
        stats = evidence_stats(links)
        health_match = re.search(r"\*\*Health:\*\* (.+)", content)
        health = health_match.group(1) if health_match else "? unknown"
        verified_match = re.search(r"\*\*Last verified:\*\* (.+)", content)
        verified = verified_match.group(1) if verified_match else "?"
        rows.append([
            file.removesuffix(".md"),
            health,
            f"{stats.valid}/{stats.total}",
            verified,
        ])
    log.table(rows)


@scope.command("show")
@click.argument("name")
@click.option("--full", is_flag=True, help="Show the complete scope document.")
@click.option("--query", "query_text", help="Show only snippets that match this search.")
def scope_show(name: str, full: bool, query_text: str | None) -> None:
    """Display a scope with evidence status."""
    if full and query_text:
        raise click.UsageError("Use either --full or --query, not both.")

    project_root = find_project_root() or Path.cwd()
    scope_path = _get_scopes_dir(project_root) / f"{name}.md"

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

    if scope_row is None and not scope_path.exists():
        log.error(f"Scope '{name}' not found. Run `mpga scope list` to see available scopes.")
        sys.exit(1)

    if query_text:
        if not query_matches:
            log.info(f'No matches for "{query_text}" in scope "{name}"')
            return

        if scope_row and scope_row.content:
            content = scope_row.content
        elif scope_path.exists():
            content = _read_scope_file(scope_path)
        else:
            content = ""

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

    if scope_row is None:
        content = _read_scope_file(scope_path)
        scope_row = _scope_from_content(name, content)
    else:
        content = scope_row.content or (_read_scope_file(scope_path) if scope_path.exists() else "")

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
    scopes_dir = _get_scopes_dir(project_root)
    scopes_dir.mkdir(parents=True, exist_ok=True)

    scope_path = scopes_dir / f"{name}.md"
    if scope_path.exists():
        log.error(f"Scope '{name}' already exists.")
        sys.exit(1)

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
    scope_path.write_text(template, encoding="utf-8")

    conn, repo = _get_scope_repo(project_root)
    try:
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
    log.success(f"Created MPGA/scopes/{name}.md")


@scope.command("remove")
@click.argument("name")
def scope_remove(name: str) -> None:
    """Archive a scope document."""
    project_root = find_project_root() or Path.cwd()
    scope_path = _get_scopes_dir(project_root) / f"{name}.md"

    if not scope_path.exists():
        log.error(f"Scope '{name}' not found.")
        sys.exit(1)

    archive_dir = project_root / "MPGA" / "milestones" / "_archived-scopes"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp_ms = int(time.time() * 1000)
    archive_path = archive_dir / f"{name}-{timestamp_ms}.md"
    scope_path.rename(archive_path)

    conn, repo = _get_scope_repo(project_root)
    try:
        repo.delete(name)
    finally:
        conn.close()

    rel_archive = archive_path.relative_to(project_root)
    log.success(f"Archived scope '{name}' to {rel_archive}")


@scope.command("query")
@click.argument("question")
def scope_query(question: str) -> None:
    """Search scopes for an answer."""
    project_root = find_project_root() or Path.cwd()
    scopes_dir = _get_scopes_dir(project_root)

    if not scopes_dir.exists():
        log.error("No scopes found. Run `mpga sync` first.")
        return

    conn, repo = _get_scope_repo(project_root)
    try:
        db_matches = repo.search(question, limit=MAX_SEARCH_RESULTS)
    finally:
        conn.close()

    if db_matches:
        log.header(f'Scope search: "{question}"')
        for scope_row, snippet in db_matches:
            console.print("")
            log.bold(f"  {scope_row.id}")
            log.dim(f"  ...{snippet}...")
        return

    files = sorted(f.name for f in scopes_dir.iterdir() if f.suffix == ".md")
    terms = question.lower().split()
    matches: list[dict[str, object]] = []

    for file in files:
        content = (scopes_dir / file).read_text(encoding="utf-8")
        lower = content.lower()
        score = 0
        for term in terms:
            score += len(re.findall(re.escape(term), lower))

        if score > 0:
            line_idx = lower.find(terms[0])
            start = max(0, line_idx - EXCERPT_CONTEXT_CHARS)
            excerpt = content[start : start + EXCERPT_MAX_LENGTH].replace("\n", " ")
            matches.append({
                "name": file.removesuffix(".md"),
                "score": score,
                "excerpt": excerpt,
            })

    matches.sort(key=lambda m: m["score"], reverse=True)  # type: ignore[arg-type]

    if not matches:
        log.info(f'No scopes matched "{question}"')
        log.dim("Tip: Run `mpga sync` to generate more detailed scope docs.")
        return

    log.header(f'Scope search: "{question}"')
    for m in matches[:MAX_SEARCH_RESULTS]:
        console.print("")
        log.bold(f"  {m['name']}  (score: {m['score']})")
        log.dim(f"  ...{m['excerpt']}...")
