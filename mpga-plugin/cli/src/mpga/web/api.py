"""API handler functions — each returns a JSON-serializable dict."""

from __future__ import annotations

import sqlite3
from typing import Any

from mpga.db.repos.tasks import TaskRepo
from mpga.db.repos.scopes import ScopeRepo
from mpga.db.repos.evidence import EvidenceRepo
from mpga.db.repos.milestones import MilestoneRepo


def _task_to_dict(task: Any) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "body": task.body,
        "column": task.column,
        "status": task.status,
        "priority": task.priority,
        "milestone": task.milestone,
        "phase": task.phase,
        "assigned": task.assigned,
        "tdd_stage": task.tdd_stage,
        "lane_id": task.lane_id,
        "run_status": task.run_status,
        "current_agent": task.current_agent,
        "time_estimate": task.time_estimate,
        "created": task.created,
        "updated": task.updated,
        "scopes": task.scopes,
        "tags": task.tags,
        "depends_on": task.depends_on,
    }


def _scope_to_dict(scope: Any) -> dict:
    return {
        "id": scope.id,
        "name": scope.name,
        "summary": scope.summary,
        "content": scope.content,
        "status": scope.status,
        "evidence_total": scope.evidence_total,
        "evidence_valid": scope.evidence_valid,
        "last_verified": scope.last_verified,
        "created_at": scope.created_at,
        "updated_at": scope.updated_at,
    }


def _milestone_to_dict(m: Any) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "status": m.status,
        "design": m.design,
        "summary": m.summary,
        "plan": getattr(m, "plan", None),
        "context": getattr(m, "context", None),
        "created_at": m.created_at,
        "completed_at": m.completed_at,
    }


def handle_search(conn: sqlite3.Connection, params: dict) -> dict:
    """Search tasks and scopes for the given query."""
    q = params.get("q", "")
    if not q:
        return {"tasks": [], "scopes": [], "query": q}

    task_repo = TaskRepo(conn)
    scope_repo = ScopeRepo(conn)

    tasks = task_repo.search(q)
    scope_results = scope_repo.search(q)

    return {
        "query": q,
        "tasks": [_task_to_dict(t) for t in tasks],
        "scopes": [_scope_to_dict(s) for s, _snippet in scope_results],
    }


def handle_tasks(conn: sqlite3.Connection, params: dict) -> dict:
    """Return tasks, optionally filtered by column/priority/milestone."""
    repo = TaskRepo(conn)
    tasks = repo.filter(
        column=params.get("column"),
        priority=params.get("priority"),
        milestone=params.get("milestone"),
    )
    return {"tasks": [_task_to_dict(t) for t in tasks]}


def handle_task_detail(conn: sqlite3.Connection, task_id: str) -> dict:
    """Return a single task by ID."""
    repo = TaskRepo(conn)
    task = repo.get(task_id)
    if task is None:
        return {"error": "not found", "id": task_id}
    return {"task": _task_to_dict(task)}


def handle_scopes(conn: sqlite3.Connection, params: dict) -> dict:
    """Return all scopes."""
    repo = ScopeRepo(conn)
    scopes = repo.list_all()
    return {"scopes": [_scope_to_dict(s) for s in scopes]}


def handle_scope_detail(conn: sqlite3.Connection, scope_id: str) -> dict:
    """Return a single scope by ID."""
    repo = ScopeRepo(conn)
    scope = repo.get(scope_id)
    if scope is None:
        return {"error": "not found", "id": scope_id}
    return {"scope": _scope_to_dict(scope)}


def handle_scope_tasks(conn: sqlite3.Connection, scope_id: str) -> dict:
    """Return tasks linked to a scope via task_scopes."""
    repo = TaskRepo(conn)
    tasks = repo.filter(scope=scope_id)
    return {
        "scope_id": scope_id,
        "tasks": [_task_to_dict(t) for t in tasks],
    }


def handle_link_task_scope(conn: sqlite3.Connection, payload: dict) -> dict:
    """Create a task->scope link in task_scopes."""
    task_id = (payload.get("task_id") or "").strip()
    scope_id = (payload.get("scope_id") or "").strip()
    if not task_id or not scope_id:
        return {"error": "task_id and scope_id are required"}

    task = TaskRepo(conn).get(task_id)
    if task is None:
        return {"error": "task not found", "task_id": task_id}

    scope = ScopeRepo(conn).get(scope_id)
    if scope is None:
        return {"error": "scope not found", "scope_id": scope_id}

    conn.execute(
        "INSERT OR IGNORE INTO task_scopes (task_id, scope_id) VALUES (?, ?)",
        (task_id, scope_id),
    )
    conn.commit()
    return {"ok": True, "task_id": task_id, "scope_id": scope_id}


def handle_unlink_task_scope(conn: sqlite3.Connection, payload: dict) -> dict:
    """Remove a task->scope link from task_scopes."""
    task_id = (payload.get("task_id") or "").strip()
    scope_id = (payload.get("scope_id") or "").strip()
    if not task_id or not scope_id:
        return {"error": "task_id and scope_id are required"}

    conn.execute(
        "DELETE FROM task_scopes WHERE task_id = ? AND scope_id = ?",
        (task_id, scope_id),
    )
    conn.commit()
    return {"ok": True, "task_id": task_id, "scope_id": scope_id}


def handle_evidence(conn: sqlite3.Connection, params: dict) -> dict:
    """Return evidence links, optionally filtered."""
    repo = EvidenceRepo(conn)
    links = repo.find(
        type=params.get("type"),
        scope_id=params.get("scope_id"),
        filepath=params.get("filepath"),
    )
    return {
        "evidence": [
            {
                "raw": e.raw,
                "type": e.type,
                "filepath": e.filepath,
                "start_line": e.start_line,
                "end_line": e.end_line,
                "symbol": e.symbol,
                "description": e.description,
                "confidence": e.confidence,
            }
            for e in links
        ]
    }


def handle_board(conn: sqlite3.Connection) -> dict:
    """Return tasks grouped by column."""
    repo = TaskRepo(conn)
    all_tasks = repo.filter()
    columns: dict[str, list] = {}
    for task in all_tasks:
        col = task.column or "backlog"
        columns.setdefault(col, []).append(_task_to_dict(task))
    return {"board": columns}


def handle_milestones(conn: sqlite3.Connection, params: dict) -> dict:
    """Return all milestones."""
    repo = MilestoneRepo(conn)
    milestones = repo.list_all()
    return {"milestones": [_milestone_to_dict(m) for m in milestones]}


def handle_stats(conn: sqlite3.Connection) -> dict:
    """Return summary statistics."""
    task_repo = TaskRepo(conn)
    scope_repo = ScopeRepo(conn)
    evidence_repo = EvidenceRepo(conn)

    all_tasks = task_repo.filter()
    all_scopes = scope_repo.list_all()
    ev_stats = evidence_repo.stats()

    return {
        "tasks": {
            "total": len(all_tasks),
        },
        "scopes": {
            "total": len(all_scopes),
        },
        "evidence": {
            "total": ev_stats.total,
            "valid": ev_stats.valid,
            "stale": ev_stats.stale,
            "health_pct": ev_stats.health_pct,
        },
    }


def handle_health(conn: sqlite3.Connection) -> dict:
    """Return basic health status."""
    try:
        conn.execute("SELECT 1").fetchone()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def handle_sessions(conn: sqlite3.Connection, params: dict) -> dict:
    """Return recent sessions."""
    limit = min(max(int(params.get("limit", 100)), 1), 500)
    try:
        rows = conn.execute(
            """
            SELECT id, project_root, started_at, ended_at, model, status
            FROM sessions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    return {
        "sessions": [
            {
                "id": r[0],
                "project_root": r[1],
                "started_at": r[2],
                "ended_at": r[3],
                "model": r[4],
                "status": r[5],
            }
            for r in rows
        ]
    }


def handle_graph(conn: sqlite3.Connection, params: dict) -> dict:
    """Return dependency graph edges."""
    limit = min(max(int(params.get("limit", 500)), 1), 5000)
    try:
        edges = conn.execute(
            """
            SELECT source, target, type
            FROM graph_edges
            ORDER BY source, target
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        edges = []

    type_counts: dict[str, int] = {}
    nodes: set[str] = set()
    for source, target, edge_type in edges:
        nodes.add(source)
        nodes.add(target)
        key = edge_type or "import"
        type_counts[key] = type_counts.get(key, 0) + 1

    return {
        "nodes_total": len(nodes),
        "edges_total": len(edges),
        "types": type_counts,
        "edges": [
            {"source": e[0], "target": e[1], "type": e[2] or "import"}
            for e in edges
        ],
    }


def handle_design_system(conn: sqlite3.Connection, params: dict) -> dict:
    """Return design tokens."""
    limit = min(max(int(params.get("limit", 2000)), 1), 5000)
    try:
        rows = conn.execute(
            """
            SELECT category, name, value, source_file
            FROM design_tokens
            ORDER BY category, name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        rows = []

    categories: dict[str, int] = {}
    for r in rows:
        categories[r[0]] = categories.get(r[0], 0) + 1

    return {
        "categories": categories,
        "tokens": [
            {
                "category": r[0],
                "name": r[1],
                "value": r[2],
                "source_file": r[3],
            }
            for r in rows
        ],
    }


def handle_decisions(conn: sqlite3.Connection, params: dict) -> dict:
    """Return architecture decisions."""
    limit = min(max(int(params.get("limit", 500)), 1), 2000)
    try:
        rows = conn.execute(
            """
            SELECT id, title, status, created_at
            FROM decisions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    return {
        "decisions": [
            {"id": r[0], "title": r[1], "status": r[2], "created_at": r[3]}
            for r in rows
        ]
    }


def handle_develop(conn: sqlite3.Connection, params: dict) -> dict:
    """Return develop scheduler lanes/runs plus in-flight tasks."""
    lane_limit = min(max(int(params.get("lane_limit", 200)), 1), 2000)
    run_limit = min(max(int(params.get("run_limit", 500)), 1), 5000)

    try:
        lanes = conn.execute(
            """
            SELECT id, status, scope, current_agent, updated_at
            FROM lanes
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (lane_limit,),
        ).fetchall()
    except sqlite3.Error:
        lanes = []

    try:
        runs = conn.execute(
            """
            SELECT id, lane_id, task_id, status, agent, started_at, finished_at
            FROM runs
            ORDER BY COALESCE(started_at, finished_at) DESC
            LIMIT ?
            """,
            (run_limit,),
        ).fetchall()
    except sqlite3.Error:
        runs = []

    task_repo = TaskRepo(conn)
    in_flight = [
        t for t in task_repo.filter()
        if t.column in {"in-progress", "testing", "review"}
    ]

    return {
        "lanes": [
            {
                "id": r[0],
                "status": r[1],
                "scope": r[2],
                "current_agent": r[3],
                "updated_at": r[4],
            }
            for r in lanes
        ],
        "runs": [
            {
                "id": r[0],
                "lane_id": r[1],
                "task_id": r[2],
                "status": r[3],
                "agent": r[4],
                "started_at": r[5],
                "finished_at": r[6],
            }
            for r in runs
        ],
        "in_flight_tasks": [_task_to_dict(t) for t in in_flight],
    }
