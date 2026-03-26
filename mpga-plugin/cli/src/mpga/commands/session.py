"""Click group for the ``mpga session`` command tree.

Mirrors the Commander-based session.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from mpga.board.board import load_board, recalc_stats
from mpga.board.task import load_all_tasks
from mpga.core.config import find_project_root
from mpga.core.logger import console, log


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOKENS_PER_LINE = 4
"""Approximate number of tokens per line of markdown/code."""

CONTEXT_WINDOW_TOKENS = 200_000
"""Default context window size in tokens (e.g. Claude 200K)."""

BUDGET_NAME_PAD_WIDTH = 30
"""Column width for budget display name padding."""

BUDGET_HEALTHY_PCT = 10
"""Context budget percentage below which scope usage is healthy."""

BUDGET_FULL_PCT = 30
"""Context budget percentage above which scope usage is getting full."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_sessions_dir(project_root: str) -> str:
    return str(Path(project_root) / "MPGA" / "sessions")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@click.group("session", help="Session management and context handoff")
def session() -> None:
    pass


# -- handoff ----------------------------------------------------------------


@session.command("handoff", help="Export current session state for fresh context")
@click.option("--accomplished", default=None, help="What was accomplished this session")
def session_handoff(accomplished: Optional[str]) -> None:
    project_root = find_project_root() or str(Path.cwd())
    sessions_dir = _get_sessions_dir(project_root)
    Path(sessions_dir).mkdir(parents=True, exist_ok=True)

    board_dir = str(Path(project_root) / "MPGA" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    board = load_board(board_dir) if (Path(board_dir) / "board.json").exists() else None
    if board:
        recalc_stats(board, tasks_dir)

    tasks = load_all_tasks(tasks_dir)
    in_progress = [t for t in tasks if t.column in ("in-progress", "testing", "review")]

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    filename = f"{date_str}-{time_str}-handoff.md"

    # Build in-flight tasks section
    if in_progress:
        in_flight_lines = "\n".join(
            f"- **{t.id}**: {t.title} [{t.column}"
            f"{f', TDD: {t.tdd_stage}' if t.tdd_stage else ''}"
            f"{f', assigned: {t.assigned}' if t.assigned else ''}]"
            for t in in_progress
        )
    else:
        in_flight_lines = "(none)"

    # Build next action section
    if in_progress:
        first = in_progress[0]
        next_action = (
            f"Resume task {first.id}: {first.title} "
            f"— run `mpga board claim {first.id}`"
        )
    elif board and board.columns.get("todo"):
        next_action = "Pick up next todo task — run `mpga board show`"
    else:
        next_action = "No immediate next step — run `mpga status` to assess"

    content = f"""# Session Handoff — {date_str}

## Accomplished
{accomplished or '(describe what was done this session)'}

## Current state
- **Milestone:** {board.milestone if board else 'none'}
- **Board:** {board.stats.done if board else 0}/{board.stats.total if board else 0} tasks done ({board.stats.progress_pct if board else 0}%)
- **In flight:** {len(in_progress)} task(s)

## In-flight tasks
{in_flight_lines}

## Decisions made
| Decision | Rationale |
|----------|-----------|
| (add decisions here) | |

## Open questions
- [ ] (add unresolved questions)

## Modified files
(list key files changed this session)

## Next action
{next_action}

## How to resume
1. Load this file into context: `cat MPGA/sessions/{filename}`
2. Load INDEX.md: `cat MPGA/INDEX.md`
3. Load relevant scope(s): `cat MPGA/scopes/<name>.md`
4. Resume from "Next action" above
"""

    handoff_path = Path(sessions_dir) / filename
    handoff_path.write_text(content, encoding="utf-8")

    log.success(f"Handoff saved to MPGA/sessions/{filename}")
    log.dim("")
    log.dim("In a new session, load with:")
    log.dim(f"  cat MPGA/sessions/{filename}")
    log.dim("  cat MPGA/INDEX.md")


# -- resume -----------------------------------------------------------------


@session.command("resume", help="Show most recent handoff for resuming")
def session_resume() -> None:
    project_root = find_project_root() or str(Path.cwd())
    sessions_dir = _get_sessions_dir(project_root)

    if not Path(sessions_dir).exists():
        log.info("No session handoffs found. Run `mpga session handoff` at end of sessions.")
        return

    files = sorted(
        [f for f in os.listdir(sessions_dir) if f.endswith("-handoff.md")],
        reverse=True,
    )

    if not files:
        log.info("No handoff files found.")
        return

    latest_path = Path(sessions_dir) / files[0]
    content = latest_path.read_text(encoding="utf-8")
    console.print(content)
    log.dim(f"--- From: MPGA/sessions/{files[0]} ---")


# -- log --------------------------------------------------------------------


@session.command("log", help="Record a session decision or note")
@click.argument("message")
def session_log(message: str) -> None:
    project_root = find_project_root() or str(Path.cwd())
    sessions_dir = _get_sessions_dir(project_root)
    Path(sessions_dir).mkdir(parents=True, exist_ok=True)

    log_path = Path(sessions_dir) / "session-log.md"
    now = datetime.now(timezone.utc).isoformat()

    entry = f"\n- {now}: {message}\n"
    if log_path.exists():
        with log_path.open("a", encoding="utf-8") as f:
            f.write(entry)
    else:
        log_path.write_text(f"# Session Log\n{entry}", encoding="utf-8")

    log.success(f"Logged: {message}")


# -- budget -----------------------------------------------------------------


@session.command("budget", help="Estimate context window usage from MPGA layer")
def session_budget() -> None:
    project_root = find_project_root() or str(Path.cwd())
    mpga_dir = Path(project_root) / "MPGA"

    estimates: list[dict[str, object]] = []

    # INDEX.md
    index_path = mpga_dir / "INDEX.md"
    if index_path.exists():
        lines = len(index_path.read_text(encoding="utf-8").splitlines())
        estimates.append({"name": "INDEX.md", "lines": lines, "tier": "Tier 1 (hot)"})

    # Scope docs
    scopes_dir = mpga_dir / "scopes"
    if scopes_dir.exists():
        for f in sorted(scopes_dir.iterdir()):
            if f.suffix == ".md":
                lines = len(f.read_text(encoding="utf-8").splitlines())
                estimates.append({"name": f"scopes/{f.name}", "lines": lines, "tier": "Tier 2 (warm)"})

    log.header("Context Budget")
    total = 0
    for e in estimates:
        name = str(e["name"])
        line_count = int(e["lines"])  # type: ignore[arg-type]
        tier = str(e["tier"])
        console.print(f"  {name:<{BUDGET_NAME_PAD_WIDTH}} {line_count:>5} lines  [{tier}]")
        total += line_count

    console.print("")
    console.print(f"  Total MPGA context:  {total} lines (~{round(total * TOKENS_PER_LINE)} tokens)")
    pct = round((total * TOKENS_PER_LINE) / CONTEXT_WINDOW_TOKENS * 100)
    console.print(f"  % of {CONTEXT_WINDOW_TOKENS // 1000}K window:    ~{pct}%")
    console.print("")

    if pct < BUDGET_HEALTHY_PCT:
        log.success("Healthy — room for more scope docs")
    elif pct < BUDGET_FULL_PCT:
        log.info("Getting full — consider using fewer scope docs per session")
    else:
        log.warn("Context heavy — consider running /mpga:handoff and starting fresh")
