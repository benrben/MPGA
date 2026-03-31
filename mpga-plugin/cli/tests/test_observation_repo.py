"""Tests for ObservationRepo — CRUD, queue, dedup, and FIFO eviction.

Coverage checklist for: T003 — Implement ObservationRepo CRUD + dedup

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: create returns entity with id         → test_create_observation_returns_with_id
[x] AC2: get_by_id returns None for missing    → test_get_by_id_returns_none_for_missing
[x] AC3: get_by_id returns created observation → test_get_by_id_returns_created
[x] AC4: list_for_session with no results      → test_list_for_session_empty
[x] AC5: list_for_session filters by session   → test_list_for_session_filters
[x] AC6: search returns matching observations  → test_search_returns_matching
[x] AC7: search returns empty for no match     → test_search_returns_empty_for_no_match
[x] AC8: delete removes observation            → test_delete_removes_observation
[x] AC9: enqueue creates queue item            → test_enqueue_creates_queue_item
[x] AC10: dequeue returns unprocessed items    → test_dequeue_returns_unprocessed
[x] AC11: dequeue marks items as processed     → test_dequeue_marks_processed
[x] AC12: SHA256 dedup against last 10 hashes  → test_dedup_skips_duplicate_hash
[x] AC13: dedup window is 10 (11th allows)     → test_dedup_allows_after_window
[x] AC14: FIFO eviction at configurable limit  → test_fifo_eviction_removes_oldest

Untested branches / edge cases:
- [ ] create with all optional fields populated
- [ ] list_for_session ordering (chronological)
- [ ] search with special FTS characters
- [ ] delete nonexistent id (idempotent?)
- [ ] enqueue with None session_id
- [ ] concurrent dequeue from multiple threads
- [ ] FIFO eviction with custom limit != 1000
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema

# Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py (not yet created)
# This import will FAIL — the module doesn't exist yet. That's the RED state.
from mpga.db.repos.observations import Observation, ObservationRepo, QueueItem


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


def _make_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-263 :: observations + observation_queue tables


class TestObservationCRUD:
    """CRUD operations on the observations table."""

    # --- TPP step 1: null/degenerate ---

    def test_get_by_id_returns_none_for_missing(self, repo: ObservationRepo) -> None:
        """Degenerate case: fetching a nonexistent id returns None."""
        result = repo.get_by_id(999)
        assert result is None

    # --- TPP step 2: constant → variable (create returns entity) ---

    def test_create_observation_returns_with_id(self, repo: ObservationRepo) -> None:
        """Create a minimal observation and verify it gets an assigned id."""
        obs = Observation(title="first observation", type="tool_output")
        created = repo.create(obs)
        assert created.id is not None
        assert isinstance(created.id, int)
        assert created.title == "first observation"
        assert created.type == "tool_output"

    # --- TPP step 3: round-trip (create then get) ---

    def test_get_by_id_returns_created(self, repo: ObservationRepo) -> None:
        """Create, then fetch by id — returned fields must match."""
        obs = Observation(
            session_id="sess-1",
            scope_id="scope-a",
            title="round trip",
            type="manual",
            narrative="some narrative",
            priority=3,
        )
        created = repo.create(obs)
        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.session_id == "sess-1"
        assert fetched.scope_id == "scope-a"
        assert fetched.title == "round trip"
        assert fetched.narrative == "some narrative"
        assert fetched.priority == 3

    # --- TPP step 4: empty collection ---

    def test_list_for_session_empty(self, repo: ObservationRepo) -> None:
        """Listing observations for a session with none returns empty list."""
        result = repo.list_for_session("nonexistent-session")
        assert result == []

    # --- TPP step 5: unconditional → selection (filtering) ---

    def test_list_for_session_filters(self, repo: ObservationRepo) -> None:
        """Observations from different sessions must be filtered correctly."""
        repo.create(Observation(session_id="s1", title="obs A", type="tool_output"))
        repo.create(Observation(session_id="s2", title="obs B", type="tool_output"))
        repo.create(Observation(session_id="s1", title="obs C", type="manual"))

        s1_obs = repo.list_for_session("s1")
        s2_obs = repo.list_for_session("s2")

        assert len(s1_obs) == 2
        assert len(s2_obs) == 1
        assert all(o.session_id == "s1" for o in s1_obs)
        assert s2_obs[0].title == "obs B"

    # --- TPP step 6: search (FTS5) ---

    def test_search_returns_matching(self, repo: ObservationRepo) -> None:
        """Search by title substring returns matching observations."""
        repo.create(Observation(title="database migration plan", type="tool_output"))
        repo.create(Observation(title="API endpoint review", type="manual"))

        results = repo.search("database")
        assert len(results) >= 1
        assert any(o.title == "database migration plan" for o in results)

    def test_search_returns_empty_for_no_match(self, repo: ObservationRepo) -> None:
        """Search with no matching content returns empty list."""
        repo.create(Observation(title="unrelated observation", type="tool_output"))
        results = repo.search("xyznonexistent")
        assert results == []

    # --- TPP step 7: delete ---

    def test_delete_removes_observation(self, repo: ObservationRepo) -> None:
        """Delete an observation, then verify get_by_id returns None."""
        created = repo.create(Observation(title="to delete", type="manual"))
        assert created.id is not None

        repo.delete(created.id)
        assert repo.get_by_id(created.id) is None


class TestObservationQueue:
    """Enqueue/dequeue operations on the observation_queue table."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:255-263 :: observation_queue table

    # --- TPP step 1: single enqueue ---

    def test_enqueue_creates_queue_item(self, repo: ObservationRepo) -> None:
        """Enqueue a single item and verify it exists in the queue."""
        item = QueueItem(
            session_id="sess-1",
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="file contents...",
        )
        created = repo.enqueue(item)
        assert created.id is not None
        assert created.processed == 0
        assert created.tool_name == "Read"

    # --- TPP step 2: scalar → collection (dequeue multiple) ---

    def test_dequeue_returns_unprocessed(self, repo: ObservationRepo) -> None:
        """Enqueue 3 items, dequeue should return all 3 unprocessed."""
        for i in range(3):
            repo.enqueue(QueueItem(
                session_id="sess-1",
                tool_name=f"tool_{i}",
                tool_input=f"input_{i}",
                tool_output=f"output_{i}",
            ))

        unprocessed = repo.dequeue("sess-1")
        assert len(unprocessed) == 3
        assert all(isinstance(q, QueueItem) for q in unprocessed)

    # --- TPP step 3: state mutation (marks processed) ---

    def test_dequeue_marks_processed(self, repo: ObservationRepo) -> None:
        """After dequeue, a second dequeue returns empty (items marked processed)."""
        repo.enqueue(QueueItem(
            session_id="sess-1",
            tool_name="Grep",
            tool_input="pattern",
            tool_output="matches...",
        ))

        first_batch = repo.dequeue("sess-1")
        assert len(first_batch) == 1

        second_batch = repo.dequeue("sess-1")
        assert second_batch == []


class TestDedup:
    """SHA256 dedup against the last 10 data_hash values."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:250 :: data_hash column

    def test_dedup_skips_duplicate_hash(self, repo: ObservationRepo) -> None:
        """Creating an observation with a duplicate data_hash within the window is skipped."""
        h = _make_hash("same content")
        first = repo.create(Observation(
            title="original", type="tool_output", data_hash=h,
        ))
        duplicate = repo.create(Observation(
            title="duplicate", type="tool_output", data_hash=h,
        ))

        assert first.id is not None
        assert duplicate is None  # skipped due to dedup

    def test_dedup_allows_after_window(self, repo: ObservationRepo) -> None:
        """After 10 distinct hashes, re-inserting hash #1 succeeds (window slides)."""
        first_hash = _make_hash("content-0")
        repo.create(Observation(
            title="obs-0", type="tool_output", data_hash=first_hash,
        ))

        for i in range(1, 11):
            repo.create(Observation(
                title=f"obs-{i}", type="tool_output", data_hash=_make_hash(f"content-{i}"),
            ))

        reinserted = repo.create(Observation(
            title="obs-0-again", type="tool_output", data_hash=first_hash,
        ))
        assert reinserted is not None
        assert reinserted.id is not None
        assert reinserted.title == "obs-0-again"


class TestFIFOEviction:
    """FIFO eviction when observation count exceeds configurable limit."""

    def test_fifo_eviction_removes_oldest(self, repo: ObservationRepo) -> None:
        """Creating 1001 observations with default limit=1000 evicts the oldest."""
        for i in range(1001):
            repo.create(Observation(
                title=f"obs-{i:04d}",
                type="tool_output",
                data_hash=_make_hash(f"unique-{i}"),
            ))

        all_obs = repo.list_for_session(None)
        assert len(all_obs) == 1000

        titles = [o.title for o in all_obs]
        assert "obs-0000" not in titles
        assert "obs-1000" in titles
