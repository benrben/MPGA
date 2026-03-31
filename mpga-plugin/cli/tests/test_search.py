"""Tests for global FTS5 search — rebuild_global_fts and global_search."""

from __future__ import annotations

import sqlite3
import pytest

from mpga.db.schema import create_schema
from mpga.db.search import rebuild_global_fts, global_search, SearchResult


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)
    yield c
    c.close()


def _seed(conn: sqlite3.Connection) -> None:
    """Insert minimal rows into tasks, scopes, evidence, milestones, decisions."""
    now = "2026-01-01T00:00:00"

    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("T001", "Implement auth login flow", "OAuth2 authentication handler for login", "backlog", "medium", now, now),
    )
    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("T002", "Fix payment gateway bug", "Stripe integration payment error", "in-progress", "high", now, now),
    )
    conn.execute(
        "INSERT INTO scopes (id, name, summary, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("S001", "auth-scope", "Authentication and authorization scope", "JWT tokens and OAuth2 auth flows", now, now),
    )
    conn.execute(
        "INSERT INTO evidence (raw, type, description) VALUES (?, ?, ?)",
        ("src/auth/login.py:42", "code", "auth login function implements OAuth flow"),
    )
    conn.execute(
        "INSERT INTO milestones (id, name, summary, created_at) VALUES (?, ?, ?, ?)",
        ("M001", "Auth milestone", "Complete authentication subsystem", now),
    )
    conn.execute(
        "INSERT INTO decisions (id, title, content, created_at) VALUES (?, ?, ?, ?)",
        ("D001", "Use JWT for auth tokens", "Decision to use JWT over sessions for auth", now),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# rebuild_global_fts
# ---------------------------------------------------------------------------

def test_rebuild_global_fts_populates_table(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    count = conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]
    assert count > 0


def test_rebuild_global_fts_includes_all_entity_types(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    types = {
        row[0]
        for row in conn.execute("SELECT entity_type FROM global_fts").fetchall()
    }
    assert "task" in types
    assert "scope" in types
    assert "evidence" in types
    assert "milestone" in types
    assert "decision" in types


def test_rebuild_global_fts_is_idempotent(conn):
    _seed(conn)
    rebuild_global_fts(conn)
    count_first = conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]

    rebuild_global_fts(conn)
    count_second = conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]

    assert count_first == count_second


def test_rebuild_global_fts_includes_observations(conn):
    now = "2026-01-01T00:00:00"
    conn.execute(
        "INSERT INTO observations (title, type, narrative, facts, concepts, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "T005 observation title",
            "tool_output",
            "Narrative for FTS",
            "fact one",
            "concept alpha",
            now,
        ),
    )
    conn.commit()
    obs_id = str(conn.execute("SELECT id FROM observations").fetchone()[0])

    rebuild_global_fts(conn)

    row = conn.execute(
        "SELECT entity_type, entity_id, title FROM global_fts "
        "WHERE entity_type = 'observation' AND entity_id = ?",
        (obs_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "observation"
    assert row[1] == obs_id
    assert row[2] == "T005 observation title"


def test_rebuild_global_fts_populates_global_trigram(conn):
    now = "2026-01-01T00:00:00"
    conn.execute(
        "INSERT INTO observations (title, type, narrative, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("Trigram obs marker", "tool_output", "body for trigram index", now),
    )
    conn.commit()
    obs_id = str(conn.execute("SELECT id FROM observations").fetchone()[0])

    rebuild_global_fts(conn)

    row = conn.execute(
        "SELECT entity_type, entity_id, title, content FROM global_trigram "
        "WHERE entity_type = 'observation' AND entity_id = ?",
        (obs_id,),
    ).fetchone()
    assert row is not None
    assert "Trigram obs marker" in (row[2] or "")
    assert "trigram" in (row[3] or "").lower()


# ---------------------------------------------------------------------------
# global_search
# ---------------------------------------------------------------------------

def test_global_search_returns_results(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth")
    assert len(results) > 0


def test_global_search_returns_search_result_dataclass(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth")
    assert len(results) > 0
    r = results[0]
    assert isinstance(r, SearchResult)
    assert r.entity_type is not None
    assert r.entity_id is not None
    assert r.title is not None
    assert r.snippet is not None
    assert r.rank is not None


def test_global_search_returns_multiple_entity_types(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth")
    types = {r.entity_type for r in results}
    # auth appears in task, scope, evidence, milestone, decision
    assert len(types) > 1


def test_global_search_rank_ordering(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth")
    ranks = [r.rank for r in results]
    if ranks and ranks[0] > 0:
        # DualIndexSearch: RRF scores are positive; best match first (descending).
        assert ranks == sorted(ranks, reverse=True)
    else:
        # Porter-only fallback: BM25 is negative (more relevant = more negative).
        assert ranks == sorted(ranks)


def test_global_search_type_filter(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth", types=["task"])
    assert len(results) > 0
    assert all(r.entity_type == "task" for r in results)


def test_global_search_type_filter_excludes_other_types(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth", types=["task"])
    entity_types = {r.entity_type for r in results}
    assert "scope" not in entity_types
    assert "evidence" not in entity_types


def test_global_search_limit(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "auth", limit=2)
    assert len(results) <= 2


def test_global_search_no_results_for_unmatched_query(conn):
    _seed(conn)
    rebuild_global_fts(conn)

    results = global_search(conn, "xyzzy_nonexistent_term_12345")
    assert results == []


def test_global_search_empty_db_returns_empty(conn):
    rebuild_global_fts(conn)
    results = global_search(conn, "auth")
    assert results == []


def test_global_search_finds_observations(conn):
    now = "2026-01-01T00:00:00"
    conn.execute(
        "INSERT INTO observations (title, type, narrative, facts, concepts, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            "Global search obs headline",
            "tool_output",
            "Unique narrative token quinquatope_xyz",
            "supporting facts",
            "related concepts",
            now,
        ),
    )
    conn.commit()

    rebuild_global_fts(conn)

    by_title = global_search(conn, "headline")
    assert any(r.entity_type == "observation" for r in by_title)

    by_narrative = global_search(conn, "quinquatope")
    assert any(
        r.entity_type == "observation" and "quinquatope" in (r.snippet or "").lower()
        for r in by_narrative
    )
