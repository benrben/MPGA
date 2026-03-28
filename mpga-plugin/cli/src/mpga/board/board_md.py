from __future__ import annotations

from mpga.board.board import WIP_LIMITS_DEFAULT, BoardState
from mpga.board.task import Task, load_all_tasks
from mpga.core.logger import progress_bar

TDD_ICONS: dict[str, str] = {
    "green": "\U0001f7e2",
    "red": "\U0001f534",
    "blue": "\U0001f535",
    "review": "\U0001f4cb",
    "done": "\u2705",
}

PRIORITY_ICONS: dict[str, str] = {
    "critical": "\U0001f534",
    "high": "\U0001f7e0",
    "medium": "\U0001f7e1",
    "low": "\u26aa",
}

STATUS_ICONS: dict[str, str] = {
    "blocked": "\U0001f534 blocked",
    "stale": "\U0001f7e1 stale",
    "rework": "\U0001f501 rework",
    "paused": "\u23f8\ufe0f paused",
}



def render_board_md(
    board: BoardState,
    tasks_dir: str,
    preloaded_tasks: list[Task] | None = None,
) -> str:
    tasks = preloaded_tasks if preloaded_tasks is not None else load_all_tasks(tasks_dir)
    by_column: dict[str, list[Task]] = {
        "backlog": [],
        "todo": [],
        "in-progress": [],
        "testing": [],
        "review": [],
        "done": [],
    }
    for task in tasks:
        if task.column in by_column:
            by_column[task.column].append(task)

    stats = board.stats
    lines: list[str] = []

    milestone = board.milestone or "No active milestone"
    lines.append(f"# Board: {milestone}")
    lines.append("")

    lines.append(
        f"**Progress: {progress_bar(stats.done, stats.total)}** ({stats.done}/{stats.total} tasks)"
    )
    lines.append(
        f"**Evidence: {progress_bar(stats.evidence_produced, stats.evidence_expected)}** ({stats.evidence_produced}/{stats.evidence_expected} links produced)"  # noqa: E501
    )
    health = (
        f"\u26a0 {stats.blocked} blocked task(s)"
        if stats.blocked > 0
        else "\u2713 No blocked tasks"
    )
    lines.append(f"**Health: {health}**")
    lines.append("")

    # In-progress
    wip = board.wip_limits or WIP_LIMITS_DEFAULT
    in_progress = by_column["in-progress"]
    if in_progress:
        limit = wip.get("in-progress", 3)
        lines.append(f"## \U0001f534 In progress ({len(in_progress)}/{limit} WIP limit)")
        lines.append("| ID | Task | Agent | TDD | Priority |")
        lines.append("|----|------|-------|-----|----------|")
        for t in in_progress:
            tdd = (TDD_ICONS.get(t.tdd_stage or "", "") + " " + (t.tdd_stage or "")).strip() if t.tdd_stage else "\u2014"  # noqa: E501
            status = (STATUS_ICONS.get(t.status or "", "") + " ") if t.status else ""
            assigned = t.assigned or "\u2014"
            pri = PRIORITY_ICONS.get(t.priority, "") + " " + t.priority
            lines.append(f"| {t.id} | {status}{t.title} | {assigned} | {tdd} | {pri} |")
        lines.append("")

    # Testing
    testing = by_column["testing"]
    if testing:
        limit = wip.get("testing", 3)
        lines.append(f"## \U0001f9ea Testing ({len(testing)}/{limit} WIP limit)")
        lines.append("| ID | Task | Agent | TDD | Priority |")
        lines.append("|----|------|-------|-----|----------|")
        for t in testing:
            tdd = (TDD_ICONS.get(t.tdd_stage or "", "") + " " + (t.tdd_stage or "")).strip() if t.tdd_stage else "\u2014"  # noqa: E501
            assigned = t.assigned or "\u2014"
            pri = PRIORITY_ICONS.get(t.priority, "") + " " + t.priority
            lines.append(f"| {t.id} | {t.title} | {assigned} | {tdd} | {pri} |")
        lines.append("")

    # Review
    review = by_column["review"]
    if review:
        limit = wip.get("review", 2)
        lines.append(f"## \U0001f4cb Review ({len(review)}/{limit} WIP limit)")
        lines.append("| ID | Task | Agent | Evidence | Priority |")
        lines.append("|----|------|-------|----------|----------|")
        for t in review:
            if t.evidence_expected:
                ev_pct = f"{len(t.evidence_produced)}/{len(t.evidence_expected)} \u2713"
            else:
                ev_pct = "\u2014"
            assigned = t.assigned or "\u2014"
            pri = PRIORITY_ICONS.get(t.priority, "") + " " + t.priority
            lines.append(f"| {t.id} | {t.title} | {assigned} | {ev_pct} | {pri} |")
        lines.append("")

    # Todo
    todo = by_column["todo"]
    if todo:
        lines.append(f"## \U0001f4e5 Todo ({len(todo)})")
        lines.append("| ID | Task | Depends on | Priority |")
        lines.append("|----|------|-----------|----------|")
        for t in todo:
            deps = ", ".join(t.depends_on) if t.depends_on else "\u2014"
            pri = PRIORITY_ICONS.get(t.priority, "") + " " + t.priority
            lines.append(f"| {t.id} | {t.title} | {deps} | {pri} |")
        lines.append("")

    # Backlog
    backlog = by_column["backlog"]
    if backlog:
        lines.append(f"## \U0001f4e6 Backlog ({len(backlog)})")
        for t in backlog:
            lines.append(f"- {t.id}: {t.title}")
        lines.append("")

    # Done
    done = by_column["done"]
    if done:
        lines.append(f"## \u2705 Done ({len(done)})")
        lines.append("| ID | Task | Evidence produced | Completed |")
        lines.append("|----|------|-------------------|-----------|")
        for t in done:
            ev_count = f"{len(t.evidence_produced)} links"
            completed = t.updated.split("T")[0]
            lines.append(f"| {t.id} | {t.title} | {ev_count} | {completed} |")
        lines.append("")

    if not tasks:
        lines.append("No tasks yet. Run `/mpga:plan` to generate tasks from a milestone.")

    return "\n".join(lines)
