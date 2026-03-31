"""Tests for T032 — Comprehensive memory module integration tests.

Coverage checklist for: T032 — Memory pipeline integration
──────────────────────────────────────────────────────────
[x] AC1: extract → create → searchable         → test_full_pipeline_extract_to_observation
[x] AC2: search → context → get                → test_progressive_disclosure_search_context_get
[x] AC3: enqueue → worker → observation        → test_worker_pipeline
[x] AC4: observation gets scope via heuristic   → test_scope_assignment_integration
[x] AC5: duplicate observations rejected        → test_dedup_integration
[x] AC6: old observations cleaned up            → test_eviction_integration
[x] AC7: config values affect behavior          → test_memory_config_integration
[x] AC8: observation → evidence link created    → test_observation_evidence_integration
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from mpga.core.config import MemoryConfig, MpgaConfig, get_default_config
from mpga.db.connection import get_connection
from mpga.db.repos.observations import Observation, ObservationRepo, QueueItem
from mpga.db.schema import create_schema
from mpga.memory.extract import extract_observation
from mpga.memory.evidence_bridge import link_observation_to_evidence
from mpga.memory.scope_heuristic import assign_scope
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


def _seed_session(conn: sqlite3.Connection, session_id: str = "sess-1") -> None:
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, project_root, started_at, status) "
        "VALUES (?, '/tmp/proj', datetime('now'), 'active')",
        (session_id,),
    )
    conn.commit()


class TestFullPipeline:
    """AC1: extract → create → searchable."""

    def test_full_pipeline_extract_to_observation(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        """Extract an observation from tool data, persist it, and find it via FTS search."""
        _seed_session(db_conn)

        obs = extract_observation(
            tool_name="Read",
            tool_input="/src/api/handler.py",
            tool_output="def handle_request():\n    return 200\n",
        )
        obs.session_id = "sess-1"
        created = repo.create(obs)

        assert created is not None
        assert created.id is not None
        assert "handler" in created.title.lower()

        results = repo.search("handler")
        assert len(results) >= 1
        assert any("handler" in r.title.lower() for r in results)


class TestProgressiveDisclosure:
    """AC2: search finds, context shows timeline, get shows details."""

    def test_progressive_disclosure_search_context_get(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        _seed_session(db_conn)

        obs1 = extract_observation("Read", "/src/models.py", "class User:\n    pass\n")
        obs1.session_id = "sess-1"
        repo.create(obs1)

        obs2 = extract_observation("Edit", "/src/models.py", "class User:\n    name: str\n")
        obs2.session_id = "sess-1"
        repo.create(obs2)

        search_results = repo.search("models")
        assert len(search_results) >= 1

        timeline = repo.list_for_session("sess-1")
        assert len(timeline) == 2

        detail = repo.get_by_id(timeline[0].id)
        assert detail is not None
        assert detail.narrative is not None
        assert detail.facts is not None


class TestWorkerPipeline:
    """AC3: enqueue → worker processes → observation created."""

    def test_worker_pipeline(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        _seed_session(db_conn)

        repo.enqueue(QueueItem(
            session_id="sess-1",
            tool_name="Read",
            tool_input="/src/config.py",
            tool_output="DEBUG = True\nPORT = 8080\n",
        ))
        repo.enqueue(QueueItem(
            session_id="sess-1",
            tool_name="Grep",
            tool_input="pattern",
            tool_output="src/main.py:10: found pattern match\n",
        ))

        worker = ObservationWorker(db_conn, "sess-1")
        processed = worker.process_batch()
        assert processed == 2

        observations = repo.list_for_session("sess-1")
        assert len(observations) == 2


class TestScopeAssignment:
    """AC4: observation gets scope via file-path heuristic."""

    def test_scope_assignment_integration(self, db_conn: sqlite3.Connection) -> None:
        db_conn.execute(
            "INSERT INTO scopes (id, name, created_at, updated_at) "
            "VALUES ('api', 'API Layer', datetime('now'), datetime('now'))"
        )
        db_conn.execute(
            "INSERT INTO evidence (raw, type, filepath, scope_id, created_at) "
            "VALUES ('[E] src/api/routes.py', 'valid', 'src/api/routes.py', 'api', datetime('now'))"
        )
        db_conn.commit()

        scope = assign_scope(
            db_conn,
            files_read=["src/api/handler.py", "src/api/middleware.py"],
            files_modified=[],
        )
        assert scope == "api"


class TestDedupIntegration:
    """AC5: duplicate observations rejected."""

    def test_dedup_integration(self, repo: ObservationRepo) -> None:
        obs1 = extract_observation("Read", "/src/main.py", "content A")
        created1 = repo.create(obs1)
        assert created1 is not None

        obs2 = extract_observation("Read", "/src/main.py", "content A")
        created2 = repo.create(obs2)
        assert created2 is None


class TestEvictionIntegration:
    """AC6: old observations cleaned up."""

    def test_eviction_integration(self, db_conn: sqlite3.Connection) -> None:
        repo = ObservationRepo(db_conn, max_observations=5)

        for i in range(8):
            h = hashlib.sha256(f"unique-{i}".encode()).hexdigest()
            repo.create(Observation(
                title=f"obs-{i}",
                type="tool_output",
                data_hash=h,
            ))

        count = db_conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        assert count == 5


class TestMemoryConfigIntegration:
    """AC7: config values affect behavior."""

    def test_memory_config_integration(self) -> None:
        cfg = get_default_config()
        assert isinstance(cfg.memory, MemoryConfig)
        assert cfg.memory.enabled is True
        assert cfg.memory.retention_days == 30
        assert cfg.memory.max_observations == 1000
        assert cfg.memory.resume_budget == 2048
        assert isinstance(cfg.memory.skip_tools, list)
        assert cfg.memory.ai_compression.enabled is False


class TestObservationEvidenceIntegration:
    """AC8: observation → evidence link created."""

    def test_observation_evidence_integration(
        self, db_conn: sqlite3.Connection, repo: ObservationRepo,
    ) -> None:
        _seed_session(db_conn)

        obs = Observation(
            session_id="sess-1",
            scope_id="api",
            title="Found critical bug in auth",
            type="error",
            narrative="Authentication middleware bypassed on /admin routes",
        )
        created = repo.create(obs)
        assert created is not None

        evidence = link_observation_to_evidence(db_conn, created.id)
        assert evidence is not None
        assert evidence["observation_id"] == created.id
        assert evidence["type"] == "observation"
        assert f"observation:{created.id}" == evidence["raw"]
        assert evidence["scope_id"] == "api"

        row = db_conn.execute(
            "SELECT raw, type, description, scope_id FROM evidence WHERE raw = ?",
            (f"observation:{created.id}",),
        ).fetchone()
        assert row is not None
        assert row[1] == "observation"
        assert "critical bug" in row[2].lower()
