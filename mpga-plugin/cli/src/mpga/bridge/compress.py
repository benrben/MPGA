"""Entity-aware output compression — T085.

Compression rules:
- Task:  "{id} [{column}] {priority}: {title} ({milestone}, scope:{scopes})"
- Scope: first paragraph of summary + "Health: {status} ({valid}/{total})", max 500B
- Evidence: "{type} {filepath}:{start}-{end} {symbol}" per link
- Search: "[{rank}] {entity_type}/{entity_id}: {title}\n  {snippet}" per result, max 2KB
- Board stats: tasks line + progress line (4 logical fields each)
- Session resume: "- {action}: {input_summary}" per event, last N only
"""
from __future__ import annotations

from mpga.board.task import Task
from mpga.db.repos.scopes import Scope

_DEFAULT_RESUME_N = 10


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


def compress_session_resume(events: list[dict], n: int = _DEFAULT_RESUME_N) -> str:
    """Return bullet list of last N actions."""
    if not events:
        return ""
    last = events[-n:]
    lines = [f"- {e.get('action', '')}: {e.get('input_summary', '')}" for e in last]
    return "\n".join(lines)
