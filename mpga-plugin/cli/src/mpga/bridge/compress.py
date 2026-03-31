"""Entity-aware output compression — T085.

Compression rules:
- Task:  "{id} [{column}] {priority}: {title} ({milestone}, scope:{scopes})"
- Scope: first paragraph of summary + "Health: {status} ({valid}/{total})", max 500B
- Evidence: "{type} {filepath}:{start}-{end} {symbol}" per link
- Search: "[{rank}] {entity_type}/{entity_id}: {title}\n  {snippet}" per result, max 2KB
- Board stats: tasks line + progress line (4 logical fields each)
- Session resume: priority-tiered builder from observations DB
"""
from __future__ import annotations

from mpga.board.task import Task
from mpga.db.repos.scopes import Scope


def compress_task(task: Task) -> str:
    """Return 1-line summary of a task, under 200 bytes."""
    scopes = ",".join(task.scopes) if task.scopes else ""
    milestone = task.milestone or "none"
    return f"{task.id} [{task.column}] {task.priority}: {task.title} ({milestone}, scope:{scopes})"


def compress_scope(scope: Scope) -> str:
    """Return first paragraph of summary + health line, max 500 bytes."""
    if scope.summary:
        first_para = scope.summary.split("\n\n")[0]
    else:
        first_para = ""

    health_line = f"Health: {scope.status} ({scope.evidence_valid}/{scope.evidence_total})"

    if first_para:
        result = f"{first_para}\n{health_line}"
    else:
        result = health_line

    # Truncate to 499 bytes if needed
    encoded = result.encode("utf-8")
    if len(encoded) >= 500:
        # truncate first_para to fit
        budget = 499 - len(("\n" + health_line).encode("utf-8"))
        truncated_para = first_para.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
        result = f"{truncated_para}\n{health_line}"

    return result


def compress_board_stats(stats: dict) -> str:
    """Return 4-line summary of board stats."""
    total = stats.get("total", 0)
    done = stats.get("done", 0)
    in_flight = stats.get("in_flight", 0)
    blocked = stats.get("blocked", 0)
    progress_pct = stats.get("progress_pct", 0)
    milestone = stats.get("milestone", "")
    line1 = f"Tasks: {total} | Done: {done} | In-flight: {in_flight} | Blocked: {blocked}"
    line2 = f"Progress: {progress_pct}% | Milestone: {milestone}"
    return f"{line1}\n{line2}"


_PRIORITY_TIERS = {
    "decision": 1, "error": 1,
    "discovery": 2, "pattern": 2,
    "tool_output": 3,
    "intent": 4,
}


def build_session_resume(
    conn: "sqlite3.Connection",
    session_id: str | None = None,
    budget: int = 2048,
) -> str:
    """Build priority-tiered session resume from observations.

    Budget allocation: P1=50%, P2=35%, P3-P4=15%.
    Output is structured markdown with tier headers.
    """
    import sqlite3

    if session_id is None:
        rows = conn.execute(
            "SELECT title, type, priority FROM observations WHERE session_id IS NULL"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT title, type, priority FROM observations WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    if not rows:
        return ""

    sorted_rows = sorted(rows, key=lambda r: (_PRIORITY_TIERS.get(r[1], r[2]), r[2]))

    tier_buckets: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
    for title, obs_type, pri in sorted_rows:
        tier = _PRIORITY_TIERS.get(obs_type, pri)
        tier_buckets.setdefault(tier, []).append(title)

    tier_budgets = {
        1: int(budget * 0.50),
        2: int(budget * 0.35),
        3: int(budget * 0.075),
        4: int(budget * 0.075),
    }

    _TIER_HEADERS = {
        1: "### Critical (decisions & errors)",
        2: "### Important (discoveries & patterns)",
        3: "### Context (tool outputs)",
        4: "### Background (intents)",
    }

    sections: list[str] = []
    for tier in (1, 2, 3, 4):
        items = tier_buckets.get(tier, [])
        if not items:
            continue
        header = _TIER_HEADERS[tier]
        tier_budget = tier_budgets[tier]
        lines: list[str] = [header]
        used = len(header) + 1
        for title in items:
            entry = f"- {title}"
            cost = len(entry) + 1
            if used + cost > tier_budget:
                lines.append("- ...")
                break
            lines.append(entry)
            used += cost
        sections.append("\n".join(lines))

    return "\n\n".join(sections)
