from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click

from mpga.core.config import find_project_root
from mpga.core.logger import log
from mpga.db.connection import get_connection
from mpga.db.repos.decisions import DecisionRepo
from mpga.db.repos.scopes import ScopeRepo
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema

# ---------------------------------------------------------------------------
# pr command
# ---------------------------------------------------------------------------


@click.command("pr")
def pr_cmd() -> None:
    """Generate PR description from current branch changes."""
    project_root = find_project_root() or Path.cwd()

    db_path = Path(project_root) / ".mpga" / "mpga.db"
    if not db_path.exists():
        log.error("DB not found. Run `mpga sync` first.")
        sys.exit(1)

    # Gather git info
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Determine merge base
        base_result = subprocess.run(
            [
                "bash",
                "-c",
                "git merge-base HEAD main 2>/dev/null || "
                "git merge-base HEAD master 2>/dev/null || "
                "echo HEAD~10",
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True,
        )
        base = base_result.stdout.strip()

        commits = subprocess.run(
            ["git", "log", "--oneline", f"{base}..HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        changed_files = subprocess.run(
            ["git", "diff", "--name-only", f"{base}..HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as e:
        log.error(f"Failed to read git information. Ensure you are in a git repository. ({e})")
        sys.exit(1)

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        db_tasks = TaskRepo(conn).filter()
        done_tasks = [t for t in db_tasks if t.column == "done"]
        evidence_links: list[str] = []
        for t in done_tasks:
            evidence_links.extend(t.evidence_produced)

        # Detect affected scopes from DB by cross-referencing with changed files
        changed_file_list = [f for f in changed_files.split("\n") if f.strip()] if changed_files else []
        scopes: list[str] = []
        db_scopes = ScopeRepo(conn).list_all()
        for scope_row in db_scopes:
            scope_path_segments = scope_row.id.replace("src-", "src/").split("-")
            is_affected = any(
                any(seg in file for seg in scope_path_segments)
                for file in changed_file_list
            )
            if is_affected:
                scopes.append(scope_row.id)

        decisions = DecisionRepo(conn).list_all()
    finally:
        conn.close()

    # Build PR description markdown
    lines: list[str] = []
    lines.append(f"## PR: {branch}")
    lines.append("")

    # Commits
    if commits:
        lines.append("### Commits")
        lines.append("")
        for line in commits.split("\n"):
            if line.strip():
                lines.append(f"- {line.strip()}")
        lines.append("")

    # Changed files
    if changed_files:
        lines.append("### Changed files")
        lines.append("")
        for file in changed_files.split("\n"):
            if file.strip():
                lines.append(f"- `{file.strip()}`")
        lines.append("")

    # Affected scopes
    if scopes:
        lines.append("### Affected scopes")
        lines.append("")
        for scope in scopes:
            lines.append(f"- {scope}")
        lines.append("")

    # Evidence links
    if evidence_links:
        lines.append("### Evidence")
        lines.append("")
        for link in evidence_links:
            lines.append(f"- {link}")
        lines.append("")

    if decisions:
        lines.append("### Decisions")
        lines.append("")
        for decision in decisions[-5:]:
            lines.append(f"- {decision.id}: {decision.title}")
        lines.append("")

    click.echo("\n".join(lines))


# ---------------------------------------------------------------------------
# decision command
# ---------------------------------------------------------------------------


@click.command("decision")
@click.argument("title")
def decision_cmd(title: str) -> None:
    """Create an Architecture Decision Record (ADR)."""
    project_root = find_project_root() or Path.cwd()
    mpga_dir = Path(project_root) / "MPGA"

    db_exists = (Path(project_root) / ".mpga" / "mpga.db").exists()
    if not mpga_dir.exists() and not db_exists:
        log.error("MPGA not initialized. Run `mpga init` first.")
        sys.exit(1)

    decisions_dir = mpga_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Determine next ADR number
    existing = [f for f in decisions_dir.iterdir() if f.suffix == ".md"]
    numbers: list[int] = []
    for f in existing:
        match = re.match(r"^(\d+)-", f.name)
        if match:
            numbers.append(int(match.group(1)))
    next_num = max(numbers) + 1 if numbers else 1
    num_str = str(next_num).zfill(3)

    # Slugify title
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = re.sub(r"^-|-$", "", slug)[:60]

    today = datetime.now().isoformat().split("T")[0]
    filename = f"{num_str}-{today}-{slug}.md"
    filepath = decisions_dir / filename

    content = f"""# ADR: {title}

**Date:** {today}
**Number:** {num_str}

## Status

Proposed

## Context

(Describe the context and problem statement that led to this decision.)

## Decision

(Describe the decision that was made.)

## Consequences

### Positive
- (List positive outcomes)

### Negative
- (List negative outcomes or trade-offs)

### Neutral
- (List neutral observations)
"""

    filepath.write_text(content, encoding="utf-8")

    db_path = Path(project_root) / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        DecisionRepo(conn).create(filepath.stem, title, content)
    finally:
        conn.close()
    log.success(f"ADR created: {filepath}")
