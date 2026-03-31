"""Observation worker — daemon thread that processes the observation queue."""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from typing import TYPE_CHECKING

from mpga.db.repos.observations import ObservationRepo, QueueItem
from mpga.memory.extract import extract_observation

logger = logging.getLogger(__name__)


class ObservationWorker:
    """Polls observation_queue for unprocessed items and creates Observations."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        session_id: str,
        batch_size: int = 50,
        poll_interval: float = 2.0,
    ) -> None:
        self._conn = conn
        self._session_id = session_id
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._repo = ObservationRepo(conn)
        self._stop = threading.Event()

    def process_batch(self) -> int:
        """Dequeue and process one batch. Returns number of items successfully processed."""
        items = self._repo.dequeue(self._session_id, self._batch_size)
        if not items:
            return 0

        created = 0
        for item in items:
            try:
                obs = extract_observation(
                    item.tool_name or "",
                    item.tool_input or "",
                    item.tool_output or "",
                    conn=self._conn,
                )
                obs.session_id = self._session_id
                self._repo.create(obs)
                created += 1
            except (sqlite3.Error, ValueError, KeyError) as e:
                logger.exception("Failed to process queue item %s", item.id)

        if created > 0:
            try:
                self._repo.evict_old(self._repo._max)
                self._repo.cleanup_by_age(30)
            except sqlite3.Error as e:
                logger.exception("Eviction/cleanup failed after batch")

        return created

    def run(self) -> None:
        """Blocking loop — call from a daemon thread."""
        while not self._stop.is_set():
            try:
                self.process_batch()
            except (sqlite3.Error, ValueError) as e:
                logger.exception("Worker loop error")
            self._stop.wait(self._poll_interval)

    def start(self) -> threading.Thread:
        """Launch the worker as a daemon thread."""
        t = threading.Thread(target=self.run, daemon=True, name="observation-worker")
        t.start()
        return t

    def stop(self) -> None:
        self._stop.set()
