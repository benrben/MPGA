"""Tests for FIFO eviction + retention policy on ObservationRepo.

Coverage checklist for: T018 — Add FIFO eviction + retention policy

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: evict_old removes excess lowest-priority oldest  → test_evict_old_removes_excess
[x] AC2: evict_old keeps high-priority items              → test_evict_old_keeps_high_priority
[x] AC3: evict_old noop under limit                       → test_evict_old_noop_under_limit
[x] AC4: cleanup_by_age removes old observations          → test_cleanup_by_age_removes_old
[x] AC5: cleanup_by_age keeps recent observations         → test_cleanup_by_age_keeps_recent
[x] AC6: cleanup_by_age noop when no old items            → test_cleanup_by_age_noop_no_old
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.repos.observations import Observation, ObservationRepo


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def repo(db_conn: sqlite3.Connection) -> ObservationRepo:
    return ObservationRepo(db_conn, max_observations=5000)


def _make_hash(i: int) -> str:
    return hashlib.sha256(f"unique-{i}".encode()).hexdigest()


class TestEvictOld:

    def test_evict_old_removes_excess(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """When count exceeds max_count, evict_old removes lowest-priority oldest."""
        for i in range(15):
            repo.create(Observation(
                title=f"obs-{i}", type="tool_output", priority=2,
                data_hash=_make_hash(i),
            ))

        removed = repo.evict_old(max_count=10)
        assert removed == 5

        count = db_conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        assert count == 10

    def test_evict_old_keeps_high_priority(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """High-priority items survive eviction even if older."""
        repo.create(Observation(
            title="high-pri", type="decision", priority=1,
            data_hash=_make_hash(0),
        ))
        for i in range(1, 12):
            repo.create(Observation(
                title=f"low-pri-{i}", type="tool_output", priority=3,
                data_hash=_make_hash(i),
            ))

        repo.evict_old(max_count=5)

        remaining = db_conn.execute(
            "SELECT title FROM observations ORDER BY priority, created_at"
        ).fetchall()
        titles = [r[0] for r in remaining]
        assert "high-pri" in titles

    def test_evict_old_noop_under_limit(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """When count is under max_count, evict_old removes nothing."""
        for i in range(3):
            repo.create(Observation(
                title=f"obs-{i}", type="tool_output",
                data_hash=_make_hash(i),
            ))

        removed = repo.evict_old(max_count=10)
        assert removed == 0

        count = db_conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        assert count == 3


class TestCleanupByAge:

    def test_cleanup_by_age_removes_old(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """Observations older than retention_days are removed."""
        db_conn.execute(
            "INSERT INTO observations (title, type, priority, created_at) "
            "VALUES (?, ?, ?, datetime('now', '-60 days'))",
            ("old-obs", "tool_output", 2),
        )
        db_conn.commit()

        repo.create(Observation(
            title="recent-obs", type="tool_output",
            data_hash=_make_hash(999),
        ))

        removed = repo.cleanup_by_age(retention_days=30)
        assert removed >= 1

        remaining = db_conn.execute("SELECT title FROM observations").fetchall()
        titles = [r[0] for r in remaining]
        assert "old-obs" not in titles
        assert "recent-obs" in titles

    def test_cleanup_by_age_keeps_recent(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """Observations within retention_days are kept."""
        for i in range(5):
            repo.create(Observation(
                title=f"recent-{i}", type="tool_output",
                data_hash=_make_hash(i),
            ))

        removed = repo.cleanup_by_age(retention_days=30)
        assert removed == 0

        count = db_conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        assert count == 5

    def test_cleanup_by_age_noop_no_old(self, db_conn: sqlite3.Connection, repo: ObservationRepo) -> None:
        """When no observations exist, cleanup is a noop."""
        removed = repo.cleanup_by_age(retention_days=30)
        assert removed == 0
