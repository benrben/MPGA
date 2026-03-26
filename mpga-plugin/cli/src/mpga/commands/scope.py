"""Scope document management commands."""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path

import click

from mpga.core.config import find_project_root
from mpga.core.logger import console, log
from mpga.evidence.parser import evidence_stats, parse_evidence_links

# Number of characters of context to show before a search match in excerpts.
EXCERPT_CONTEXT_CHARS = 50
# Maximum length of a search result excerpt in characters.
EXCERPT_MAX_LENGTH = 200
# Maximum number of scope search results to display.
MAX_SEARCH_RESULTS = 3


def _get_scopes_dir(project_root: Path) -> Path:
    return project_root / "MPGA" / "scopes"


@click.group("scope")
def scope() -> None:
    """Manage scope documents."""


@scope.command("list")
def scope_list() -> None:
    """Show all scopes with health status."""
    project_root = find_project_root() or Path.cwd()
    scopes_dir = _get_scopes_dir(project_root)

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
def scope_show(name: str) -> None:
    """Display a scope with evidence status."""
    project_root = find_project_root() or Path.cwd()
    scope_path = _get_scopes_dir(project_root) / f"{name}.md"

    if not scope_path.exists():
        log.error(f"Scope '{name}' not found. Run `mpga scope list` to see available scopes.")
        sys.exit(1)

    content = scope_path.read_text(encoding="utf-8")
    links = parse_evidence_links(content)
    stats = evidence_stats(links)

    console.print(content)
    console.print("")
    log.dim(
        f"\u2500\u2500\u2500 Evidence: {stats.valid} valid, {stats.stale} stale, "
        f"{stats.unknown} unknown ({stats.health_pct}% health) \u2500\u2500\u2500"
    )


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
