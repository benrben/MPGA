"""SessionRepo — session lifecycle + event log for the sessions/events tables."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


@dataclass
class Session:
    id: str
    project_root: str
    started_at: str
    ended_at: str | None = None
    model: str | None = None
    status: str = "active"
    task_snapshot: str | None = None


@dataclass
class Event:
    id: int | None
    session_id: str
    timestamp: str
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    action: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    full_output: str | None = None
    metadata: str | None = None


class SessionRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create(
        self,
        project_root: str,
        model: str | None = None,
        task_snapshot: str | None = None,
        session_id: str | None = None,
    ) -> Session:
        session = Session(
            id=session_id or self._make_session_id(),
            project_root=project_root,
            started_at=datetime.now(UTC).isoformat(),
            model=model,
            task_snapshot=task_snapshot,
        )
        self._conn.execute(
            """
            INSERT INTO sessions (id, project_root, started_at, ended_at, model, status, task_snapshot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.project_root,
                session.started_at,
                session.ended_at,
                session.model,
                session.status,
                session.task_snapshot,
            ),
        )
        self._conn.commit()
        return session

    def start(
        self,
        project_root: str,
        model: str | None = None,
        task_snapshot: str | None = None,
        session_id: str | None = None,
    ) -> Session:
        active = self.get_active(project_root)
        if active is not None:
            return active
        return self.create(
            project_root,
            model=model,
            task_snapshot=task_snapshot,
            session_id=session_id,
        )

    def get(self, session_id: str) -> Session | None:
        row = self._conn.execute(
            """
            SELECT id, project_root, started_at, ended_at, model, status, task_snapshot
            FROM sessions WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
        return self._row_to_session(row) if row else None

    def get_active(self, project_root: str) -> Session | None:
        row = self._conn.execute(
            """
            SELECT id, project_root, started_at, ended_at, model, status, task_snapshot
            FROM sessions
            WHERE project_root = ? AND status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (project_root,),
        ).fetchone()
        return self._row_to_session(row) if row else None

    def get_latest(self, project_root: str) -> Session | None:
        row = self._conn.execute(
            """
            SELECT id, project_root, started_at, ended_at, model, status, task_snapshot
            FROM sessions
            WHERE project_root = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (project_root,),
        ).fetchone()
        return self._row_to_session(row) if row else None

    def ensure_active(
        self,
        project_root: str,
        model: str | None = None,
        task_snapshot: str | None = None,
    ) -> Session:
        active = self.get_active(project_root)
        if active is not None:
            return active
        return self.create(project_root, model=model, task_snapshot=task_snapshot)

    def end(self, session_id: str) -> Session | None:
        ended_at = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            UPDATE sessions
            SET ended_at = ?, status = 'closed'
            WHERE id = ?
            """,
            (ended_at, session_id),
        )
        self._conn.commit()
        return self.get(session_id)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def log_event(
        self,
        session_id: str,
        event_type: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        full_output: str | None = None,
        metadata: str | dict | None = None,
        timestamp: str | None = None,
    ) -> Event:
        event = Event(
            id=None,
            session_id=session_id,
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            full_output=full_output,
            metadata=json.dumps(metadata) if isinstance(metadata, dict) else metadata,
        )
        cur = self._conn.execute(
            """
            INSERT INTO events (
                session_id, timestamp, event_type, entity_type, entity_id,
                action, input_summary, output_summary, full_output, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.session_id,
                event.timestamp,
                event.event_type,
                event.entity_type,
                event.entity_id,
                event.action,
                event.input_summary,
                event.output_summary,
                event.full_output,
                event.metadata,
            ),
        )
        event.id = int(cur.lastrowid)
        self._sync_fts_insert(event)
        self._conn.commit()
        return event

    def add(
        self,
        session_id: str,
        event_type: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        full_output: str | None = None,
        metadata: str | dict | None = None,
        timestamp: str | None = None,
    ) -> Event:
        return self.log_event(
            session_id,
            event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            full_output=full_output,
            metadata=metadata,
            timestamp=timestamp,
        )

    def list_events(self, session_id: str, limit: int = 10) -> list[Event]:
        rows = self._conn.execute(
            """
            SELECT id, session_id, timestamp, event_type, entity_type, entity_id,
                   action, input_summary, output_summary, full_output, metadata
            FROM events
            WHERE session_id = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def list_for_session(self, session_id: str, limit: int = 100) -> list[Event]:
        rows = self._conn.execute(
            """
            SELECT id, session_id, timestamp, event_type, entity_type, entity_id,
                   action, input_summary, output_summary, full_output, metadata
            FROM events
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def search_events(self, session_id: str, query: str, limit: int = 10) -> list[Event]:
        rows = self._conn.execute(
            """
            SELECT e.id, e.session_id, e.timestamp, e.event_type, e.entity_type, e.entity_id,
                   e.action, e.input_summary, e.output_summary, e.full_output, e.metadata
            FROM events_fts
            JOIN events e ON events_fts.rowid = e.id
            WHERE events_fts MATCH ? AND e.session_id = ?
            ORDER BY bm25(events_fts)
            LIMIT ?
            """,
            (query, session_id, limit),
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_session_id(self) -> str:
        return f"S{uuid4().hex[:8]}"

    def _sync_fts_insert(self, event: Event) -> None:
        self._conn.execute(
            """
            INSERT INTO events_fts (
                rowid, event_type, entity_type, action, input_summary, output_summary
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.event_type or "",
                event.entity_type or "",
                event.action or "",
                event.input_summary or "",
                event.output_summary or "",
            ),
        )

    def _row_to_session(self, row: tuple | sqlite3.Row) -> Session:
        return Session(*row)

    def _row_to_event(self, row: tuple | sqlite3.Row) -> Event:
        return Event(*row)


class EventRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._session_repo = SessionRepo(conn)

    def add(
        self,
        session_id: str,
        event_type: str,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        full_output: str | None = None,
        metadata: str | dict | None = None,
        timestamp: str | None = None,
    ) -> Event:
        return self._session_repo.add(
            session_id,
            event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            full_output=full_output,
            metadata=metadata,
            timestamp=timestamp,
        )

    def list_for_session(self, session_id: str, limit: int = 100) -> list[Event]:
        return self._session_repo.list_for_session(session_id, limit=limit)
