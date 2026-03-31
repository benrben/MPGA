"""Observation-related API handlers — split from api.py for maintainability."""

from __future__ import annotations

import json
import sqlite3


def _obs_to_dict(row: tuple) -> dict:
    return {
        "id": row[0],
        "session_id": row[1],
        "scope_id": row[2],
        "title": row[3],
        "type": row[4],
        "narrative": row[5],
        "facts": row[6],
        "concepts": row[7],
        "created_at": row[8],
    }


_OBS_SELECT = (
    "SELECT id, session_id, scope_id, title, type, narrative, facts, concepts, created_at "
    "FROM observations"
)


def handle_observations(conn: sqlite3.Connection, params: dict) -> dict:
    """List observations, newest first."""
    limit = min(max(int(params.get("limit", 100)), 1), 500)
    rows = conn.execute(
        f"{_OBS_SELECT} ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return {"observations": [_obs_to_dict(r) for r in rows]}


def handle_observation_detail(conn: sqlite3.Connection, obs_id: str) -> dict:
    """Return a single observation by ID."""
    row = conn.execute(
        f"{_OBS_SELECT} WHERE id = ?", (obs_id,)
    ).fetchone()
    if row is None:
        return {"error": "not found", "id": obs_id}
    return {"observation": _obs_to_dict(row)}


def handle_observations_search(conn: sqlite3.Connection, params: dict) -> dict:
    """Full-text search over observations via FTS5."""
    from mpga.db.fts_utils import prefix_match_query

    q = params.get("q", "")
    if not q:
        return {"observations": [], "query": q}
    limit = min(max(int(params.get("limit", 50)), 1), 200)
    match_q = prefix_match_query(q)
    try:
        rows = conn.execute(
            "SELECT o.id, o.session_id, o.scope_id, o.title, o.type, "
            "o.narrative, o.facts, o.concepts, o.created_at "
            "FROM observations_fts "
            "JOIN observations o ON o.id = observations_fts.rowid "
            "WHERE observations_fts MATCH ? ORDER BY rank LIMIT ?",
            (match_q, limit),
        ).fetchall()
    except Exception:
        rows = []
    return {"observations": [_obs_to_dict(r) for r in rows], "query": q}


def handle_observations_timeline(conn: sqlite3.Connection, params: dict) -> dict:
    """Return observations before and after a given observation ID."""
    obs_id = params.get("id", "")
    if not obs_id:
        return {"error": "id parameter required"}
    window = min(max(int(params.get("window", 5)), 1), 50)

    anchor_row = conn.execute(
        f"{_OBS_SELECT} WHERE id = ?", (obs_id,)
    ).fetchone()
    if anchor_row is None:
        return {"error": "not found", "id": obs_id}

    before = conn.execute(
        f"{_OBS_SELECT} WHERE id < ? ORDER BY id DESC LIMIT ?",
        (obs_id, window),
    ).fetchall()
    after = conn.execute(
        f"{_OBS_SELECT} WHERE id > ? ORDER BY id ASC LIMIT ?",
        (obs_id, window),
    ).fetchall()

    return {
        "anchor": _obs_to_dict(anchor_row),
        "before": [_obs_to_dict(r) for r in reversed(before)],
        "after": [_obs_to_dict(r) for r in after],
    }


def handle_stream(conn: sqlite3.Connection, params: dict) -> dict:
    """SSE endpoint returning recent observation-created events."""
    limit = min(max(int(params.get("limit", 50)), 1), 200)
    rows = conn.execute(
        "SELECT id, title, type, narrative, created_at "
        "FROM observations ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()

    lines: list[str] = ["retry: 3000"]
    for row in reversed(rows):
        payload = json.dumps({
            "id": row[0],
            "title": row[1],
            "type": row[2],
            "narrative": row[3],
            "created_at": row[4],
        })
        lines.append(f"event: observation-created")
        lines.append(f"id: {row[0]}")
        lines.append(f"data: {payload}")
        lines.append("")

    return {
        "content_type": "text/event-stream",
        "body": "\n".join(lines) + "\n",
    }
