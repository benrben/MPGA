"""Bridge observations into the evidence system."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


def link_observation_to_evidence(conn: sqlite3.Connection, observation_id: int) -> dict | None:
    """Create an evidence entry from an observation.

    Returns the evidence dict on success, or None if the observation doesn't exist.
    """
    row = conn.execute(
        "SELECT id, title, type, narrative, scope_id "
        "FROM observations WHERE id = ?",
        (observation_id,),
    ).fetchone()

    if row is None:
        return None

    obs_id, title, obs_type, narrative, scope_id = row
    description = f"{title}: {narrative}" if narrative else title
    raw = f"observation:{obs_id}"
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO evidence (raw, type, description, confidence, scope_id, created_at) "
        "VALUES (?, 'observation', ?, 1.0, ?, ?)",
        (raw, description, scope_id, now),
    )
    conn.commit()

    return {
        "observation_id": obs_id,
        "raw": raw,
        "type": "observation",
        "description": description,
        "scope_id": scope_id,
    }
