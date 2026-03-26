from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click

from mpga.board.task import load_all_tasks
from mpga.core.config import find_project_root
from mpga.core.logger import log


# ---------------------------------------------------------------------------
# pr command
# ---------------------------------------------------------------------------


@click.command("pr")
def pr_cmd() -> None:
    """Generate PR description from current branch changes."""
    project_root = find_project_root() or Path.cwd()
    mpga_dir = Path(project_root) / "MPGA"

    if not mpga_dir.exists():
        log.error("MPGA not initialized. Run `mpga init` first.")
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
    except Exception:
        log.error("Failed to read git information. Ensure you are in a git repository.")
        sys.exit(1)

    # Load tasks for evidence links
    tasks_dir = mpga_dir / "board" / "tasks"
    tasks = load_all_tasks(str(tasks_dir))
    done_tasks = [t for t in tasks if t.column == "done"]
    evidence_links: list[str] = []
    for t in done_tasks:
        evidence_links.extend(t.evidence_produced)

    # Detect affected scopes by cross-referencing with changed files
    scopes_dir = mpga_dir / "scopes"
    scopes: list[str] = []
    changed_file_list = [f for f in changed_files.split("\n") if f.strip()] if changed_files else []
    if scopes_dir.exists():
        scope_files = [f for f in scopes_dir.iterdir() if f.suffix == ".md"]
        for sf in scope_files:
            scope_name = sf.stem
            scope_content = sf.read_text(encoding="utf-8")
            scope_path_segments = scope_name.replace("src-", "src/").split("-")
            is_affected = any(
                any(seg in file for seg in scope_path_segments) or scope_content.find(file) != -1
                for file in changed_file_list
            )
            if is_affected:
                scopes.append(scope_name)

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

    if not mpga_dir.exists():
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
    log.success(f"ADR created: {filepath}")
