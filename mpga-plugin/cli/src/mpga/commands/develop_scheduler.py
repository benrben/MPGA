"""Develop scheduler: lane splitting, file-lock management, TDD checkpoints.

Mirrors the logic from develop-scheduler.ts, converting all async operations
to synchronous Python using the existing mpga.board.* modules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mpga.board.board import (
    BoardLane,
    BoardRun,
    find_task_file,
    load_board,
    recalc_stats,
    save_board,
)
from mpga.board.board_lock import with_board_lock
from mpga.board.live import write_board_live_snapshot
from mpga.board.live_html import write_board_live_html
from mpga.board.task import (
    FileLock,
    RunStatus,
    ScopeLock,
    load_all_tasks,
    parse_task_file,
    render_task_file,
)
from mpga.core.config import find_project_root
from mpga.db.connection import get_connection
from mpga.db.repos.lanes import Lane, LaneRepo, Run, RunRepo
from mpga.db.repos.locks import LockRepo
from mpga.db.repos.tasks import TaskRepo
from mpga.db.schema import create_schema


@dataclass
class PersistLaneTransitionOptions:
    task_id: str
    lane_id: str
    status: RunStatus
    agent: str | None = None
    files: list[str] | None = None
    scope: str | None = None


@dataclass
class TddCheckpoint:
    stage: str  # 'red' | 'green' | 'blue' | 'review'
    saved_at: str
    last_test_file: str | None = None
    last_impl_file: str | None = None
    failing_test: str | None = None



def render_checkpoint_section(checkpoint: TddCheckpoint) -> str:
    lines = ["## TDD Checkpoint"]
    lines.append(f"- stage: {checkpoint.stage}")
    if checkpoint.last_test_file:
        lines.append(f"- lastTestFile: {checkpoint.last_test_file}")
    if checkpoint.last_impl_file:
        lines.append(f"- lastImplFile: {checkpoint.last_impl_file}")
    if checkpoint.failing_test:
        lines.append(f"- failingTest: {checkpoint.failing_test}")
    lines.append(f"- savedAt: {checkpoint.saved_at}")
    return "\n".join(lines)


def parse_checkpoint_section(body: str) -> TddCheckpoint | None:
    section_start = body.find("## TDD Checkpoint")
    if section_start == -1:
        return None

    after_header = body[section_start:]
    # Find the next ## heading (if any) to bound the section
    next_section = after_header.find("\n## ", 1)
    section_text = after_header if next_section == -1 else after_header[:next_section]

    def get_value(key: str) -> str | None:
        match = re.search(rf"^- {key}: (.+)$", section_text, re.MULTILINE)
        return match.group(1) if match else None

    stage = get_value("stage")
    saved_at = get_value("savedAt")
    if not stage or not saved_at:
        return None

    checkpoint = TddCheckpoint(stage=stage, saved_at=saved_at)
    last_test_file = get_value("lastTestFile")
    last_impl_file = get_value("lastImplFile")
    failing_test = get_value("failingTest")
    if last_test_file:
        checkpoint.last_test_file = last_test_file
    if last_impl_file:
        checkpoint.last_impl_file = last_impl_file
    if failing_test:
        checkpoint.failing_test = failing_test

    return checkpoint



def save_tdd_checkpoint(
    tasks_dir: str,
    task_id: str,
    checkpoint: TddCheckpoint,
) -> None:
    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        raise RuntimeError(f"Task '{task_id}' not found")

    task = parse_task_file(task_file)
    if not task:
        raise RuntimeError(f"Could not parse task '{task_id}'")

    checkpoint_text = render_checkpoint_section(checkpoint)

    # Remove existing checkpoint section if present
    section_start = task.body.find("## TDD Checkpoint")
    if section_start != -1:
        after_header = task.body[section_start:]
        next_section = after_header.find("\n## ", 1)
        section_end = len(task.body) if next_section == -1 else section_start + next_section
        task.body = (
            task.body[:section_start].rstrip()
            + "\n\n"
            + checkpoint_text
            + task.body[section_end:]
        )
    else:
        # Append the checkpoint section at the end
        task.body = task.body.rstrip() + "\n\n" + checkpoint_text + "\n"

    Path(task_file).write_text(render_task_file(task), encoding="utf-8")


def load_tdd_checkpoint(tasks_dir: str, task_id: str) -> TddCheckpoint | None:
    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        return None

    task = parse_task_file(task_file)
    if not task:
        return None

    return parse_checkpoint_section(task.body)



def _merge_file_groups(groups: list[list[str]]) -> list[list[str]]:
    normalized = [sorted(set(group)) for group in groups if group]
    merged: list[list[str]] = []

    for group in normalized:
        overlapping = [
            existing
            for existing in merged
            if any(f in group for f in existing)
        ]
        if not overlapping:
            merged.append(group)
            continue

        combined = sorted(set(
            f for overlap in overlapping for f in overlap
        ) | set(group))
        for overlap in overlapping:
            merged.remove(overlap)
        merged.append(combined)

    return sorted(merged, key=lambda g: g[0] if g else "")


def split_into_file_groups(
    task_id: str,
    groups: list[list[str]],
    scope: str | None = None,
) -> list[BoardLane]:
    merged = _merge_file_groups(groups)
    normalized = merged if merged else [[]]

    return [
        BoardLane(
            id=f"{task_id}-lane-{index + 1}",
            task_ids=[task_id],
            status="queued",
            scope=scope,
            files=files,
            current_agent=None,
            updated_at=datetime.now(UTC).isoformat(),
        )
        for index, files in enumerate(normalized)
    ]


# ---------------------------------------------------------------------------
# File-lock conflict check
# ---------------------------------------------------------------------------


def can_acquire_file_locks(
    files: list[str],
    tasks_dir: str,
) -> tuple[bool, list[str]]:
    """Return ``(ok, conflicts)``."""
    tasks = load_all_tasks(tasks_dir)
    active_locks: set[str] = set()
    for task in tasks:
        if task.run_status in ("running", "handoff"):
            for lock in task.file_locks:
                active_locks.add(lock.path)
    conflicts = sorted(set(f for f in files if f in active_locks))
    return (len(conflicts) == 0, conflicts)


# ---------------------------------------------------------------------------
# Lane transition persistence
# ---------------------------------------------------------------------------


def persist_lane_transition(
    board_dir: str,
    tasks_dir: str,
    opts: PersistLaneTransitionOptions,
) -> None:
    def _inner() -> None:
        board = load_board(board_dir)
        task_file = find_task_file(tasks_dir, opts.task_id)
        if not task_file:
            raise RuntimeError(f"Task '{opts.task_id}' not found")

        task = parse_task_file(task_file)
        if not task:
            raise RuntimeError(f"Could not parse task '{opts.task_id}'")

        now = datetime.now(UTC).isoformat()
        files = opts.files or []
        is_terminal = opts.status in ("done", "failed")

        file_locks: list[FileLock] = (
            []
            if is_terminal
            else [
                FileLock(
                    path=f,
                    lane_id=opts.lane_id,
                    agent=opts.agent or "mpga-red-dev",
                    acquired_at=task.started_at or now,
                    heartbeat_at=now,
                )
                for f in files
            ]
        )

        task.lane_id = opts.lane_id
        task.run_status = opts.status
        task.current_agent = opts.agent if opts.agent else None
        task.file_locks = file_locks
        task.scope_locks = (
            [
                ScopeLock(
                    scope=opts.scope,
                    lane_id=opts.lane_id,
                    agent=opts.agent or "mpga-red-dev",
                    acquired_at=task.started_at or now,
                    heartbeat_at=now,
                )
            ]
            if opts.scope and not is_terminal
            else []
        )
        task.started_at = task.started_at or now
        task.finished_at = now if is_terminal else None
        task.heartbeat_at = None if is_terminal else now
        task.updated = now

        # Determine lane status from run status
        if opts.status == "handoff":
            lane_status = "running"
        elif opts.status in ("queued", "running", "done", "failed"):
            lane_status = opts.status
        else:
            lane_status = "running"

        board.lanes[opts.lane_id] = BoardLane(
            id=opts.lane_id,
            task_ids=[opts.task_id],
            status=lane_status,
            scope=opts.scope,
            files=files,
            current_agent=opts.agent if opts.agent else None,
            updated_at=now,
        )
        board.active_runs[f"{opts.lane_id}:{opts.task_id}"] = BoardRun(
            id=f"{opts.lane_id}:{opts.task_id}",
            lane_id=opts.lane_id,
            task_id=opts.task_id,
            status=opts.status,
            agent=opts.agent if opts.agent else None,
            started_at=task.started_at or now,
            finished_at=task.finished_at,
        )

        Path(task_file).write_text(render_task_file(task), encoding="utf-8")
        recalc_stats(board, tasks_dir)
        save_board(board_dir, board)
        write_board_live_snapshot(board, tasks_dir, board_dir)
        write_board_live_html(board_dir)

        db_path = Path(board_dir).parent.parent / ".mpga" / "mpga.db"
        conn = get_connection(str(db_path))
        try:
            create_schema(conn)
            for scope_id in task.scopes:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO scopes
                        (id, name, summary, content, status,
                         evidence_total, evidence_valid, last_verified,
                         created_at, updated_at)
                    VALUES (?, ?, NULL, NULL, 'fresh', 0, 0, NULL, datetime('now'), datetime('now'))
                    """,
                    (scope_id, scope_id),
                )

            task_repo = TaskRepo(conn)
            if task_repo.get(task.id) is None:
                task_repo.create(task)
            else:
                task_repo.update(task)

            lane_repo = LaneRepo(conn)
            existing_lane = lane_repo.get(opts.lane_id)
            if existing_lane is None:
                lane_repo.create(
                    Lane(
                        id=opts.lane_id,
                        status=lane_status,
                        scope=opts.scope,
                        current_agent=opts.agent if opts.agent else None,
                    )
                )
            else:
                conn.execute(
                    """
                    UPDATE lanes
                    SET status = ?, scope = ?, current_agent = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (lane_status, opts.scope, opts.agent if opts.agent else None, opts.lane_id),
                )

            run_id = f"{opts.lane_id}:{opts.task_id}"
            run_repo = RunRepo(conn)
            existing_run = run_repo.get(run_id)
            if existing_run is None:
                run_repo.create(
                    Run(
                        id=run_id,
                        lane_id=opts.lane_id,
                        task_id=opts.task_id,
                        status=opts.status,
                        agent=opts.agent if opts.agent else None,
                        started_at=task.started_at,
                        finished_at=task.finished_at,
                    )
                )
            else:
                conn.execute(
                    """
                    UPDATE runs
                    SET lane_id = ?, task_id = ?, status = ?, agent = ?, started_at = ?, finished_at = ?
                    WHERE id = ?
                    """,
                    (
                        opts.lane_id,
                        opts.task_id,
                        opts.status,
                        opts.agent if opts.agent else None,
                        task.started_at,
                        task.finished_at,
                        run_id,
                    ),
                )

            conn.execute("DELETE FROM file_locks WHERE task_id = ?", (opts.task_id,))
            conn.execute("DELETE FROM scope_locks WHERE task_id = ?", (opts.task_id,))
            lock_repo = LockRepo(conn)
            for file_path in files:
                lock_repo.acquire_file(
                    file_path,
                    opts.task_id,
                    lane_id=opts.lane_id,
                    agent=opts.agent if opts.agent else None,
                )
            if opts.scope and not is_terminal:
                lock_repo.acquire_scope(
                    opts.scope,
                    opts.task_id,
                    lane_id=opts.lane_id,
                    agent=opts.agent if opts.agent else None,
                )
            conn.commit()
        finally:
            conn.close()

    with_board_lock(board_dir, _inner)


# ---------------------------------------------------------------------------
# Main entry point: run_develop_task
# ---------------------------------------------------------------------------


def run_develop_task(
    task_id: str,
    *,
    parallel: str = "auto",
    lanes: int | None = None,
    dashboard: bool = False,
) -> list[str]:
    project_root = find_project_root() or str(Path.cwd())
    board_dir = str(Path(project_root) / ".mpga" / "board")
    tasks_dir = str(Path(board_dir) / "tasks")

    task_file = find_task_file(tasks_dir, task_id)
    if not task_file:
        raise RuntimeError(f"Task '{task_id}' not found")

    task = parse_task_file(task_file)
    if not task:
        raise RuntimeError(f"Could not parse task '{task_id}'")

    # Check for an existing TDD checkpoint and resume from that stage
    checkpoint = load_tdd_checkpoint(tasks_dir, task_id)
    agent_for_stage: dict[str, str] = {
        "red": "mpga-red-dev",
        "green": "mpga-green-dev",
        "blue": "mpga-blue-dev",
        "review": "mpga-reviewer",
    }
    resume_agent = (
        agent_for_stage.get(checkpoint.stage, "mpga-red-dev")
        if checkpoint
        else "mpga-red-dev"
    )
    if checkpoint:
        task.tdd_stage = checkpoint.stage  # type: ignore[assignment]
        Path(task_file).write_text(render_task_file(task), encoding="utf-8")

    file_paths = [lock.path for lock in task.file_locks]
    if not file_paths:
        initial_groups: list[list[str]] = [[]]
    elif parallel == "none":
        # Consolidate all files into a single lane
        initial_groups = [file_paths]
    else:
        # Each file gets its own lane (auto/default)
        initial_groups = [[p] for p in file_paths]

    lane_list = split_into_file_groups(task_id, initial_groups, task.scopes[0] if task.scopes else None)
    max_lanes = lanes if lanes and lanes > 0 else len(lane_list)
    scheduled = lane_list[:max_lanes]

    launched: list[BoardLane] = []
    for lane in scheduled:
        # Check file locks before scheduling each lane
        if lane.files:
            ok, _conflicts = can_acquire_file_locks(lane.files, tasks_dir)
            if not ok:
                continue  # Skip lanes with conflicting file locks

        persist_lane_transition(
            board_dir,
            tasks_dir,
            PersistLaneTransitionOptions(
                task_id=task_id,
                lane_id=lane.id,
                status="running",
                agent=resume_agent,
                files=lane.files,
                scope=lane.scope,
            ),
        )
        launched.append(lane)

    if dashboard:
        write_board_live_html(board_dir)

    return [lane.id for lane in launched]
