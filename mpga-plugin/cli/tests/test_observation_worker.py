"""Tests for observation worker — daemon thread that processes queue items.

Coverage checklist for: T015 — Implement observation worker integrated with mpga serve

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: Worker processes queue items             → test_worker_processes_queue_item
[x] AC2: Worker creates observation from queue    → test_worker_creates_observation_from_queue
[x] AC3: Worker marks items as processed          → test_worker_marks_processed
[x] AC4: Worker handles empty queue gracefully    → test_worker_handles_empty_queue
[x] AC5: Worker handles extraction error          → test_worker_handles_extraction_error
[x] AC6: Worker processes items in batches        → test_worker_batch_processing
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.repos.observations import Observation, ObservationRepo, QueueItem
from mpga.memory.worker import ObservationWorker


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def repo(db_conn: sqlite3.Connection) -> ObservationRepo:
    return ObservationRepo(db_conn)


class TestObservationWorker:

    def test_worker_processes_queue_item(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """A single queued item gets processed into an observation."""
        repo.enqueue(QueueItem(
            session_id="s1", tool_name="Read",
            tool_input="/src/main.py", tool_output="contents",
        ))

        worker = ObservationWorker(db_conn, session_id="s1")
        processed = worker.process_batch()

        assert processed >= 1

    def test_worker_creates_observation_from_queue(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """Processing a queue item creates an Observation via extract_observation."""
        repo.enqueue(QueueItem(
            session_id="s1", tool_name="Read",
            tool_input="/src/main.py", tool_output="file body here",
        ))

        worker = ObservationWorker(db_conn, session_id="s1")
        worker.process_batch()

        observations = repo.list_for_session("s1")
        assert len(observations) >= 1
        assert observations[0].tool_name == "Read"

    def test_worker_marks_processed(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """After processing, queue items are marked processed (second batch is empty)."""
        repo.enqueue(QueueItem(
            session_id="s1", tool_name="Read",
            tool_input="/src/main.py", tool_output="content",
        ))

        worker = ObservationWorker(db_conn, session_id="s1")
        first = worker.process_batch()
        second = worker.process_batch()

        assert first >= 1
        assert second == 0

    def test_worker_handles_empty_queue(self, db_conn: sqlite3.Connection) -> None:
        """Processing an empty queue returns 0 and does not raise."""
        worker = ObservationWorker(db_conn, session_id="s1")
        processed = worker.process_batch()
        assert processed == 0

    def test_worker_handles_extraction_error(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """If extract_observation raises, the worker logs and continues."""
        repo.enqueue(QueueItem(
            session_id="s1", tool_name="Read",
            tool_input="/src/main.py", tool_output="content",
        ))

        with patch("mpga.memory.worker.extract_observation", side_effect=ValueError("boom")):
            worker = ObservationWorker(db_conn, session_id="s1")
            processed = worker.process_batch()

        assert processed == 0

    def test_worker_batch_processing(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """Multiple queue items are processed in a single batch call."""
        for i in range(5):
            repo.enqueue(QueueItem(
                session_id="s1", tool_name=f"Tool{i}",
                tool_input=f"/file{i}.py", tool_output=f"output {i}",
            ))

        worker = ObservationWorker(db_conn, session_id="s1")
        processed = worker.process_batch()

        assert processed == 5
        observations = repo.list_for_session("s1")
        assert len(observations) == 5
