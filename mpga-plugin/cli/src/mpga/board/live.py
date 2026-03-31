from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mpga.board.board import BoardLane, BoardRun, BoardState
from mpga.board.task import Task, load_all_tasks
from mpga.db.connection import get_connection
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema


@dataclass
class BoardLiveEvent:
    type: str
    lane_id: str | None = None
    task_id: str | None = None
    status: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class BoardLiveTaskSummary:
    id: str
    title: str
    column: str
    priority: str
    assigned: str | None = None
    lane_id: str | None = None
    run_status: str = "queued"
    current_agent: str | None = None
    file_locks: list[dict[str, Any]] = field(default_factory=list)
    scope_locks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BoardLiveSnapshot:
    generated_at: str
    milestone: str | None
    stats: Any  # BoardStats
    scheduler: Any  # BoardScheduler
    ui: Any  # BoardUI
    columns: dict[str, list[BoardLiveTaskSummary]]
    active_lanes: list[BoardLane]
    active_runs: list[BoardRun]
    recent_events: list[BoardLiveEvent]


def get_board_live_dir(board_dir: str) -> str:
    return str(Path(board_dir) / "live")


def read_recent_board_events(board_dir: str, limit: int = 20) -> list[BoardLiveEvent]:
    events_path = Path(get_board_live_dir(board_dir)) / "events.ndjson"
    if not events_path.exists():
        return []

    try:
        text = events_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        recent = lines[-limit:]
        events: list[BoardLiveEvent] = []
        for line in recent:
            try:
                raw = json.loads(line)
                events.append(BoardLiveEvent(
                    type=raw.get("type", ""),
                    lane_id=raw.get("lane_id"),
                    task_id=raw.get("task_id"),
                    status=raw.get("status"),
                    extra={k: v for k, v in raw.items() if k not in ("type", "lane_id", "task_id", "status")},
                ))
            except (json.JSONDecodeError, ValueError):
                continue
        return events
    except OSError:
        return []


def _summarize_task(task: Task) -> BoardLiveTaskSummary:
    from mpga.board.task import _file_lock_to_dict, _scope_lock_to_dict

    return BoardLiveTaskSummary(
        id=task.id,
        title=task.title,
        column=task.column,
        priority=task.priority,
        assigned=task.assigned,
        lane_id=task.lane_id,
        run_status=task.run_status,
        current_agent=task.current_agent,
        file_locks=[_file_lock_to_dict(fl) for fl in task.file_locks],
        scope_locks=[_scope_lock_to_dict(sl) for sl in task.scope_locks],
    )


def _load_db_tasks(board_dir: str) -> list[Task]:
    project_root = Path(board_dir).parent.parent
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return []

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        return TaskRepo(conn).filter()
    finally:
        conn.close()


def build_board_live_snapshot(
    board: BoardState,
    tasks_dir: str,
    board_dir: str,
    preloaded_tasks: list[Task] | None = None,
) -> BoardLiveSnapshot:
    if preloaded_tasks is not None:
        tasks = preloaded_tasks
    else:
        db_tasks = _load_db_tasks(board_dir)
        tasks = db_tasks if db_tasks else load_all_tasks(tasks_dir)
    columns: dict[str, list[BoardLiveTaskSummary]] = {
        "backlog": [],
        "todo": [],
        "in-progress": [],
        "testing": [],
        "review": [],
        "done": [],
    }

    for task in tasks:
        if task.column in columns:
            columns[task.column].append(_summarize_task(task))

    return BoardLiveSnapshot(
        generated_at=datetime.now(UTC).isoformat(),
        milestone=board.milestone,
        stats=board.stats,
        scheduler=board.scheduler,
        ui=board.ui,
        columns=columns,
        active_lanes=list(board.lanes.values()),
        active_runs=list(board.active_runs.values()),
        recent_events=read_recent_board_events(board_dir),
    )


def _snapshot_to_dict(snapshot: BoardLiveSnapshot) -> dict[str, Any]:
    from mpga.board.board import _stats_to_dict

    columns_dict: dict[str, list[dict[str, Any]]] = {}
    for col, summaries in snapshot.columns.items():
        columns_dict[col] = [_summary_to_dict(s) for s in summaries]

    return {
        "generated_at": snapshot.generated_at,
        "milestone": snapshot.milestone,
        "stats": _stats_to_dict(snapshot.stats),
        "scheduler": {
            "lock_mode": snapshot.scheduler.lock_mode,
            "max_parallel_lanes": snapshot.scheduler.max_parallel_lanes,
            "split_strategy": snapshot.scheduler.split_strategy,
        },
        "ui": {
            "refresh_interval_ms": snapshot.ui.refresh_interval_ms,
            "theme": snapshot.ui.theme,
        },
        "columns": columns_dict,
        "active_lanes": [
            {
                "id": lane.id,
                "task_ids": lane.task_ids,
                "status": lane.status,
                "scope": lane.scope,
                "files": lane.files,
                "current_agent": lane.current_agent,
                "updated_at": lane.updated_at,
            }
            for lane in snapshot.active_lanes
        ],
        "active_runs": [
            {
                "id": run.id,
                "lane_id": run.lane_id,
                "task_id": run.task_id,
                "status": run.status,
                "agent": run.agent,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
            }
            for run in snapshot.active_runs
        ],
        "recent_events": [
            {
                "type": e.type,
                **({"lane_id": e.lane_id} if e.lane_id is not None else {}),
                **({"task_id": e.task_id} if e.task_id is not None else {}),
                **({"status": e.status} if e.status is not None else {}),
                **e.extra,
            }
            for e in snapshot.recent_events
        ],
    }


def _summary_to_dict(s: BoardLiveTaskSummary) -> dict[str, Any]:
    return {
        "id": s.id,
        "title": s.title,
        "column": s.column,
        "priority": s.priority,
        "assigned": s.assigned,
        "lane_id": s.lane_id,
        "run_status": s.run_status,
        "current_agent": s.current_agent,
        "file_locks": s.file_locks,
        "scope_locks": s.scope_locks,
    }


def write_board_live_snapshot(
    board: BoardState,
    tasks_dir: str,
    board_dir: str,
    preloaded_tasks: list[Task] | None = None,
) -> str:
    live_dir = Path(get_board_live_dir(board_dir))
    live_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = live_dir / "snapshot.json"
    snapshot = build_board_live_snapshot(board, tasks_dir, board_dir, preloaded_tasks)
    snapshot_path.write_text(
        json.dumps(_snapshot_to_dict(snapshot), indent=2) + "\n",
        encoding="utf-8",
    )
    return str(snapshot_path)
