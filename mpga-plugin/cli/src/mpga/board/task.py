from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import frontmatter

Column = Literal["backlog", "todo", "in-progress", "testing", "review", "done"]
Priority = Literal["critical", "high", "medium", "low"]
TddStage = Literal["green", "red", "blue", "review", "done"]
TaskStatus = Literal["blocked", "stale", "rework", "paused"]
RunStatus = Literal["queued", "running", "handoff", "done", "failed"]


@dataclass
class FileLock:
    path: str
    lane_id: str
    agent: str
    acquired_at: str
    heartbeat_at: str | None = None


@dataclass
class ScopeLock:
    scope: str
    lane_id: str
    agent: str
    acquired_at: str
    heartbeat_at: str | None = None


@dataclass
class Task:
    id: str
    title: str
    column: Column
    status: TaskStatus | None
    priority: Priority
    created: str
    updated: str
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    tdd_stage: TddStage | None = None
    lane_id: str | None = None
    run_status: RunStatus = "queued"
    current_agent: str | None = None
    file_locks: list[FileLock] = field(default_factory=list)
    scope_locks: list[ScopeLock] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None
    heartbeat_at: str | None = None
    evidence_expected: list[str] = field(default_factory=list)
    evidence_produced: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    time_estimate: str = "5min"
    body: str = ""
    milestone: str | None = None
    phase: int | None = None
    assigned: str | None = None


def task_filename(id: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = re.sub(r"^-|-$", "", slug)[:40]
    return f"{id}-{slug}.md"


def render_task_file(task: Task) -> str:
    frontmatter_dict: dict[str, object] = {
        "id": task.id,
        "title": task.title,
        "status": task.status if task.status is not None else "active",
        "column": task.column,
        "priority": task.priority,
        "milestone": task.milestone,
        "phase": task.phase,
        "created": task.created,
        "updated": task.updated,
        "assigned": task.assigned,
        "depends_on": task.depends_on,
        "blocks": task.blocks,
        "scopes": task.scopes,
        "tdd_stage": task.tdd_stage,
        "lane_id": task.lane_id,
        "run_status": task.run_status,
        "current_agent": task.current_agent,
        "file_locks": [_file_lock_to_dict(fl) for fl in task.file_locks],
        "scope_locks": [_scope_lock_to_dict(sl) for sl in task.scope_locks],
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "heartbeat_at": task.heartbeat_at,
        "evidence_expected": task.evidence_expected,
        "evidence_produced": task.evidence_produced,
        "tags": task.tags,
        "time_estimate": task.time_estimate,
    }

    body = task.body or (
        f"# {task.id}: {task.title}\n"
        "\n"
        "## Description\n"
        "(describe the task)\n"
        "\n"
        "## Acceptance criteria\n"
        "- [ ] (define measurable criteria)\n"
        "\n"
        "## Evidence links (from scope)\n"
        "(will be populated as work progresses)\n"
        "\n"
        "## TDD trace\n"
        "- \U0001f534 red-dev: (pending)\n"
        "- \U0001f7e2 green-dev: (pending)\n"
        "- \U0001f535 blue-dev: (pending)\n"
        "- \U0001f4cb reviewer: (pending)\n"
        "\n"
        "## Notes\n"
        "(optional notes)\n"
        "\n"
        "## History\n"
        f"- {task.created}: created\n"
    )

    lines: list[str] = []
    for k, v in frontmatter_dict.items():
        if isinstance(v, list):
            items = ", ".join(json.dumps(i) for i in v)
            lines.append(f"{k}: [{items}]")
        elif v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, str):
            lines.append(f"{k}: {json.dumps(v)}")
        else:
            lines.append(f"{k}: {v}")

    fm = "\n".join(lines)
    return f"---\n{fm}\n---\n\n{body}"


def parse_task_file(filepath: str) -> Task | None:
    p = Path(filepath)
    if not p.exists():
        return None
    try:
        raw = p.read_text(encoding="utf-8")
        post = frontmatter.loads(raw)
        data = post.metadata
        content: str = post.content

        return Task(
            id=data["id"],
            title=data["title"],
            column=data.get("column", "backlog"),
            status=None if data.get("status") == "active" else data.get("status"),
            priority=data.get("priority", "medium"),
            milestone=data.get("milestone"),
            phase=data.get("phase"),
            created=data.get("created", ""),
            updated=data.get("updated", ""),
            assigned=data.get("assigned"),
            depends_on=data.get("depends_on") or [],
            blocks=data.get("blocks") or [],
            scopes=data.get("scopes") or [],
            tdd_stage=data.get("tdd_stage"),
            lane_id=data.get("lane_id"),
            run_status=data.get("run_status", "queued"),
            current_agent=data.get("current_agent"),
            file_locks=[_dict_to_file_lock(fl) for fl in (data.get("file_locks") or [])],
            scope_locks=[_dict_to_scope_lock(sl) for sl in (data.get("scope_locks") or [])],
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            heartbeat_at=data.get("heartbeat_at"),
            evidence_expected=data.get("evidence_expected") or [],
            evidence_produced=data.get("evidence_produced") or [],
            tags=data.get("tags") or [],
            time_estimate=data.get("time_estimate", "5min"),
            body=content.strip(),
        )
    except Exception:
        return None


def load_all_tasks(tasks_dir: str) -> list[Task]:
    p = Path(tasks_dir)
    if not p.exists():
        return []
    tasks: list[Task] = []
    for f in sorted(p.iterdir()):
        if f.suffix == ".md":
            task = parse_task_file(str(f))
            if task is not None:
                tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Internal helpers for FileLock / ScopeLock serialization
# ---------------------------------------------------------------------------

def _file_lock_to_dict(fl: FileLock) -> dict[str, object]:
    d: dict[str, object] = {
        "path": fl.path,
        "lane_id": fl.lane_id,
        "agent": fl.agent,
        "acquired_at": fl.acquired_at,
    }
    if fl.heartbeat_at is not None:
        d["heartbeat_at"] = fl.heartbeat_at
    return d


def _scope_lock_to_dict(sl: ScopeLock) -> dict[str, object]:
    d: dict[str, object] = {
        "scope": sl.scope,
        "lane_id": sl.lane_id,
        "agent": sl.agent,
        "acquired_at": sl.acquired_at,
    }
    if sl.heartbeat_at is not None:
        d["heartbeat_at"] = sl.heartbeat_at
    return d


def _dict_to_file_lock(d: dict[str, object]) -> FileLock:
    return FileLock(
        path=str(d.get("path", "")),
        lane_id=str(d.get("lane_id", "")),
        agent=str(d.get("agent", "")),
        acquired_at=str(d.get("acquired_at", "")),
        heartbeat_at=d.get("heartbeat_at"),  # type: ignore[arg-type]
    )


def _dict_to_scope_lock(d: dict[str, object]) -> ScopeLock:
    return ScopeLock(
        scope=str(d.get("scope", "")),
        lane_id=str(d.get("lane_id", "")),
        agent=str(d.get("agent", "")),
        acquired_at=str(d.get("acquired_at", "")),
        heartbeat_at=d.get("heartbeat_at"),  # type: ignore[arg-type]
    )
