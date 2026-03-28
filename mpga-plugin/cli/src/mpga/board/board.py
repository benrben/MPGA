from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mpga.board.task import (
    Column,
    Task,
    load_all_tasks,
    parse_task_file,
    render_task_file,
    task_filename,
)

WIP_LIMITS_DEFAULT: dict[str, int] = {"in-progress": 3, "testing": 3, "review": 2}


@dataclass
class BoardLane:
    id: str
    task_ids: list[str] = field(default_factory=list)
    status: str = "queued"  # 'queued' | 'running' | 'blocked' | 'done' | 'failed'
    scope: str | None = None
    files: list[str] = field(default_factory=list)
    current_agent: str | None = None
    updated_at: str = ""


@dataclass
class BoardRun:
    id: str
    lane_id: str
    task_id: str
    status: str = "queued"  # 'queued' | 'running' | 'handoff' | 'done' | 'failed'
    agent: str | None = None
    started_at: str = ""
    finished_at: str | None = None


@dataclass
class BoardStats:
    total: int = 0
    done: int = 0
    in_flight: int = 0
    blocked: int = 0
    progress_pct: int = 0
    evidence_produced: int = 0
    evidence_expected: int = 0
    avg_task_time: str | None = None


@dataclass
class BoardScheduler:
    lock_mode: str = "file"
    max_parallel_lanes: int = 3
    split_strategy: str = "file-groups"


@dataclass
class BoardUI:
    refresh_interval_ms: int = 2500
    theme: str = "mpga-signal"


@dataclass
class BoardState:
    version: str = "1.0.0"
    milestone: str | None = None
    updated: str = ""
    columns: dict[str, list[str]] = field(default_factory=lambda: {
        "backlog": [],
        "todo": [],
        "in-progress": [],
        "testing": [],
        "review": [],
        "done": [],
    })
    stats: BoardStats = field(default_factory=BoardStats)
    wip_limits: dict[str, int] = field(default_factory=lambda: dict(WIP_LIMITS_DEFAULT))
    next_task_id: int = 1
    lanes: dict[str, BoardLane] = field(default_factory=dict)
    active_runs: dict[str, BoardRun] = field(default_factory=dict)
    scheduler: BoardScheduler = field(default_factory=BoardScheduler)
    ui: BoardUI = field(default_factory=BoardUI)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_board(board_dir: str) -> BoardState:
    board_path = Path(board_dir) / "board.json"
    if not board_path.exists():
        return create_empty_board()
    raw = json.loads(board_path.read_text(encoding="utf-8"))
    return _normalize_board_state(raw)


def save_board(board_dir: str, state: BoardState) -> None:
    p = Path(board_dir)
    p.mkdir(parents=True, exist_ok=True)
    state.updated = _now_iso()
    data = _board_state_to_dict(state)
    (p / "board.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def create_empty_board() -> BoardState:
    return _normalize_board_state({
        "version": "1.0.0",
        "milestone": None,
        "updated": _now_iso(),
        "columns": {
            "backlog": [],
            "todo": [],
            "in-progress": [],
            "testing": [],
            "review": [],
            "done": [],
        },
        "stats": {
            "total": 0,
            "done": 0,
            "in_flight": 0,
            "blocked": 0,
            "progress_pct": 0,
            "evidence_produced": 0,
            "evidence_expected": 0,
        },
        "wip_limits": dict(WIP_LIMITS_DEFAULT),
        "next_task_id": 1,
    })


def _normalize_board_state(board: dict[str, Any]) -> BoardState:
    columns = board.get("columns") or {}
    stats_raw = board.get("stats") or {}
    wip_raw = board.get("wip_limits") or {}
    scheduler_raw = board.get("scheduler") or {}
    ui_raw = board.get("ui") or {}
    lanes_raw = board.get("lanes") or {}
    runs_raw = board.get("active_runs") or {}

    stats = BoardStats(
        total=stats_raw.get("total", 0),
        done=stats_raw.get("done", 0),
        in_flight=stats_raw.get("in_flight", 0),
        blocked=stats_raw.get("blocked", 0),
        progress_pct=stats_raw.get("progress_pct", 0),
        evidence_produced=stats_raw.get("evidence_produced", 0),
        evidence_expected=stats_raw.get("evidence_expected", 0),
        avg_task_time=stats_raw.get("avg_task_time"),
    )

    scheduler = BoardScheduler(
        lock_mode="file",
        max_parallel_lanes=scheduler_raw.get("max_parallel_lanes", 3),
        split_strategy="file-groups",
    )

    ui = BoardUI(
        refresh_interval_ms=ui_raw.get("refresh_interval_ms", 2500),
        theme=ui_raw.get("theme", "mpga-signal"),
    )

    lanes: dict[str, BoardLane] = {}
    for k, v in lanes_raw.items():
        lanes[k] = BoardLane(
            id=v.get("id", k),
            task_ids=v.get("task_ids", []),
            status=v.get("status", "queued"),
            scope=v.get("scope"),
            files=v.get("files", []),
            current_agent=v.get("current_agent"),
            updated_at=v.get("updated_at", ""),
        )

    active_runs: dict[str, BoardRun] = {}
    for k, v in runs_raw.items():
        active_runs[k] = BoardRun(
            id=v.get("id", k),
            lane_id=v.get("lane_id", ""),
            task_id=v.get("task_id", ""),
            status=v.get("status", "queued"),
            agent=v.get("agent"),
            started_at=v.get("started_at", ""),
            finished_at=v.get("finished_at"),
        )

    return BoardState(
        version=board.get("version", "1.0.0"),
        milestone=board.get("milestone"),
        updated=board.get("updated", _now_iso()),
        columns={
            "backlog": columns.get("backlog", []),
            "todo": columns.get("todo", []),
            "in-progress": columns.get("in-progress", []),
            "testing": columns.get("testing", []),
            "review": columns.get("review", []),
            "done": columns.get("done", []),
        },
        stats=stats,
        wip_limits={
            "in-progress": wip_raw.get("in-progress", 3),
            "testing": wip_raw.get("testing", 3),
            "review": wip_raw.get("review", 2),
        },
        next_task_id=board.get("next_task_id", 1),
        lanes=lanes,
        active_runs=active_runs,
        scheduler=scheduler,
        ui=ui,
    )


def recalc_stats(
    board: BoardState,
    tasks_dir: str,
    preloaded_tasks: list[Task] | None = None,
) -> BoardState:
    tasks = preloaded_tasks if preloaded_tasks is not None else load_all_tasks(tasks_dir)
    total = len(tasks)
    done = sum(1 for t in tasks if t.column == "done")
    in_flight = sum(1 for t in tasks if t.column in ("in-progress", "testing", "review"))
    blocked = sum(1 for t in tasks if t.status == "blocked")
    evidence_produced = sum(len(t.evidence_produced) for t in tasks)
    evidence_expected = sum(len(t.evidence_expected) for t in tasks)

    board.stats = BoardStats(
        total=total,
        done=done,
        in_flight=in_flight,
        blocked=blocked,
        progress_pct=0 if total == 0 else round((done / total) * 100),
        evidence_produced=evidence_produced,
        evidence_expected=evidence_expected,
    )

    # Rebuild columns
    columns: dict[str, list[str]] = {
        "backlog": [],
        "todo": [],
        "in-progress": [],
        "testing": [],
        "review": [],
        "done": [],
    }
    for task in tasks:
        if task.column in columns:
            columns[task.column].append(task.id)
    board.columns = columns

    return board


def check_wip_limit(board: BoardState, column: Column) -> bool:
    limit = board.wip_limits.get(column)
    if not limit:
        return True
    return len(board.columns.get(column, [])) < limit


def next_task_id(board: BoardState, prefix: str = "T") -> str:
    id_ = f"{prefix}{str(board.next_task_id).zfill(3)}"
    board.next_task_id += 1
    return id_


@dataclass
class AddTaskOptions:
    title: str
    column: Column | None = None
    priority: str | None = None
    scopes: list[str] | None = None
    depends: list[str] | None = None
    tags: list[str] | None = None
    milestone: str | None = None


def add_task(
    board: BoardState,
    tasks_dir: str,
    options: AddTaskOptions,
) -> Task:
    id_ = next_task_id(board)
    now = _now_iso()
    task = Task(
        id=id_,
        title=options.title,
        column=options.column or "backlog",
        status=None,
        priority=options.priority or "medium",
        milestone=options.milestone,
        created=now,
        updated=now,
        depends_on=options.depends or [],
        blocks=[],
        scopes=options.scopes or [],
        tdd_stage=None,
        lane_id=None,
        run_status="queued",
        current_agent=None,
        file_locks=[],
        scope_locks=[],
        started_at=None,
        finished_at=None,
        heartbeat_at=None,
        evidence_expected=[],
        evidence_produced=[],
        tags=options.tags or [],
        time_estimate="5min",
        body="",
    )

    p = Path(tasks_dir)
    p.mkdir(parents=True, exist_ok=True)
    filename = task_filename(id_, options.title)
    (p / filename).write_text(render_task_file(task), encoding="utf-8")

    # Add to board columns
    board.columns[task.column].append(id_)
    return task


@dataclass
class MoveResult:
    success: bool
    error: str | None = None


def move_task(
    board: BoardState,
    tasks_dir: str,
    task_id: str,
    to_column: Column,
    force: bool = False,
) -> MoveResult:
    # Check WIP limit
    if not force and not check_wip_limit(board, to_column):
        col_list = board.columns.get(to_column, [])
        limit = board.wip_limits.get(to_column, 0)
        return MoveResult(
            success=False,
            error=f"WIP limit reached for '{to_column}' ({len(col_list)}/{limit}). Use --force to override.",
        )

    task_file = find_task_file(tasks_dir, task_id)
    if task_file is None:
        return MoveResult(success=False, error=f"Task '{task_id}' not found")

    task = parse_task_file(task_file)
    if task is None:
        return MoveResult(success=False, error="Could not parse task file")

    # Remove from old column
    old_column = task.column
    board.columns[old_column] = [
        id_ for id_ in board.columns.get(old_column, []) if id_ != task_id
    ]

    # Add to new column
    task.column = to_column
    task.updated = _now_iso()
    board.columns[to_column].append(task_id)

    # Write updated task file
    Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    return MoveResult(success=True)


def find_task_file(tasks_dir: str, task_id: str) -> str | None:
    p = Path(tasks_dir)
    if not p.exists():
        return None
    for f in sorted(p.iterdir()):
        if f.name.startswith(task_id + "-") or f.name.startswith(task_id + "."):
            return str(f)
    return None


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _board_state_to_dict(state: BoardState) -> dict[str, Any]:
    return {
        "version": state.version,
        "milestone": state.milestone,
        "updated": state.updated,
        "columns": state.columns,
        "stats": _stats_to_dict(state.stats),
        "wip_limits": state.wip_limits,
        "next_task_id": state.next_task_id,
        "lanes": {k: _lane_to_dict(v) for k, v in state.lanes.items()},
        "active_runs": {k: _run_to_dict(v) for k, v in state.active_runs.items()},
        "scheduler": {
            "lock_mode": state.scheduler.lock_mode,
            "max_parallel_lanes": state.scheduler.max_parallel_lanes,
            "split_strategy": state.scheduler.split_strategy,
        },
        "ui": {
            "refresh_interval_ms": state.ui.refresh_interval_ms,
            "theme": state.ui.theme,
        },
    }


def _stats_to_dict(s: BoardStats) -> dict[str, Any]:
    d: dict[str, Any] = {
        "total": s.total,
        "done": s.done,
        "in_flight": s.in_flight,
        "blocked": s.blocked,
        "progress_pct": s.progress_pct,
        "evidence_produced": s.evidence_produced,
        "evidence_expected": s.evidence_expected,
    }
    if s.avg_task_time is not None:
        d["avg_task_time"] = s.avg_task_time
    return d


def _lane_to_dict(lane: BoardLane) -> dict[str, Any]:
    return {
        "id": lane.id,
        "task_ids": lane.task_ids,
        "status": lane.status,
        "scope": lane.scope,
        "files": lane.files,
        "current_agent": lane.current_agent,
        "updated_at": lane.updated_at,
    }


def _run_to_dict(run: BoardRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "lane_id": run.lane_id,
        "task_id": run.task_id,
        "status": run.status,
        "agent": run.agent,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }
