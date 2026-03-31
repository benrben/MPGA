"""Tests for T004 — DualIndexSearch with RRF fusion.

Coverage checklist for: T004 — Implement DualIndexSearch with RRF fusion

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: DualIndexSearch class exists and is importable
        → test_dual_index_search_class_exists
[x] AC2: Empty query returns empty results (degenerate)
        → test_empty_query_returns_empty
[x] AC3: Basic search returns SearchResult objects
        → test_search_returns_results
[x] AC4: RRF merge combines Porter and Trigram indexes
        → test_rrf_merge_combines_porter_and_trigram
[x] AC5: RRF score = sum(1/(k+rank)) with k=60
        → test_rrf_score_formula
[x] AC6: Title 5x weight boost — title match ranks higher
        → test_title_weight_boost
[x] AC7: Proximity reranking for multi-term queries
        → test_proximity_reranking
[x] AC8: Fuzzy fallback via Levenshtein on typo
        → test_fuzzy_fallback_on_typo
[x] AC9: Smart snippet extraction with window around match
        → test_snippet_extraction
[x] AC10: global_search() backward compatible (old signature)
        → test_global_search_backward_compatible
[x] AC11: global_search() uses dual index for better results
        → test_global_search_uses_dual_index
[x] AC12: Type filter still works with dual index
        → test_search_with_type_filter

Untested branches / edge cases:
- [x] null/empty query (degenerate)
- [ ] single-character query
- [ ] unicode in search terms
- [ ] concurrent access
"""

from __future__ import annotations

import sqlite3
import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.search import SearchResult, rebuild_global_fts, global_search

# Evidence: [E] mpga-plugin/cli/src/mpga/db/search.py:11-17 :: SearchResult dataclass
# Evidence: [E] mpga-plugin/cli/src/mpga/db/search.py:76-139 :: global_search()
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:305-307 :: global_fts FTS5 table
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:356-359 :: global_trigram FTS5 table

# Conditional import: DualIndexSearch does not exist yet (red phase).
# Backward-compat tests must still collect even when this import fails.
try:
    from mpga.db.search import DualIndexSearch

    _HAS_DUAL = True
except ImportError:
    DualIndexSearch = None  # type: ignore[assignment,misc]
    _HAS_DUAL = False

needs_dual = pytest.mark.xfail(not _HAS_DUAL, reason="DualIndexSearch not implemented yet")


NOW = "2026-01-01T00:00:00"


@pytest.fixture
def search_conn(tmp_path):
    """Provide a schema-initialized DB seeded with searchable data."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("t1", "Authentication system", "Implement OAuth2 authentication with JWT tokens",
         "todo", "high", NOW, NOW),
    )
    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("t2", "Database migration", "Migrate the authentication database to PostgreSQL",
         "todo", "medium", NOW, NOW),
    )
    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("t3", "API endpoints", "Create REST API endpoints for user management",
         "todo", "high", NOW, NOW),
    )
    conn.execute(
        "INSERT INTO scopes (id, name, summary, content, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("s1", "auth", "Authentication module",
         "Handles user authentication and authorization", NOW, NOW),
    )
    conn.commit()

    rebuild_global_fts(conn)

    conn.execute(
        "INSERT INTO tasks_trigram(title, body) SELECT title, COALESCE(body,'') FROM tasks"
    )
    conn.execute(
        "INSERT INTO scopes_trigram(name, summary, content) "
        "SELECT name, COALESCE(summary,''), COALESCE(content,'') FROM scopes"
    )
    conn.commit()

    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# 1. Degenerate — class exists
# ---------------------------------------------------------------------------

@needs_dual
def test_dual_index_search_class_exists():
    """DualIndexSearch is importable from mpga.db.search."""
    assert _HAS_DUAL
    assert callable(DualIndexSearch)


# ---------------------------------------------------------------------------
# 2. Degenerate — empty / missing input
# ---------------------------------------------------------------------------

@needs_dual
def test_empty_query_returns_empty(search_conn):
    """Empty query string produces no results."""
    ds = DualIndexSearch(search_conn)
    results = ds.search("")
    assert results == []


# ---------------------------------------------------------------------------
# 3. Simplest valid — basic search returns results
# ---------------------------------------------------------------------------

@needs_dual
def test_search_returns_results(search_conn):
    """A basic keyword search returns SearchResult objects."""
    ds = DualIndexSearch(search_conn)
    results = ds.search("authentication")
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)


# ---------------------------------------------------------------------------
# 4. RRF merge — both indexes contribute
# ---------------------------------------------------------------------------

@needs_dual
def test_rrf_merge_combines_porter_and_trigram(search_conn):
    """Results include hits from both the Porter FTS5 and Trigram FTS5 indexes.

    'auth' should hit via Porter stemming (authentication → auth),
    and via Trigram substring matching.  Both must contribute to the
    merged result set.
    """
    ds = DualIndexSearch(search_conn)
    results = ds.search("auth")
    assert len(results) >= 2, "RRF merge should surface results from both indexes"
    entity_ids = {r.entity_id for r in results}
    assert "t1" in entity_ids, "Porter index should find 'Authentication system'"
    assert "s1" in entity_ids, "Trigram index should find scope 'auth'"


# ---------------------------------------------------------------------------
# 5. RRF score formula — score = sum(1/(k+rank)) with k=60
# ---------------------------------------------------------------------------

@needs_dual
def test_rrf_score_formula(search_conn):
    """RRF score for a result appearing at rank 1 in both indexes is 2 * 1/(60+1)."""
    ds = DualIndexSearch(search_conn)
    results = ds.search("authentication")
    assert len(results) > 0
    top = results[0]

    expected_single_contribution = 1.0 / (60 + 1)
    assert top.rank >= expected_single_contribution, (
        f"Top result score {top.rank} should be at least 1/(60+1)={expected_single_contribution:.6f}"
    )
    max_possible = 2.0 / (60 + 1)
    assert top.rank <= max_possible + 1e-9, (
        f"Top result score {top.rank} should not exceed {max_possible:.6f} for rank-1 in both"
    )


# ---------------------------------------------------------------------------
# 6. Title weight boost — title 5x
# ---------------------------------------------------------------------------

@needs_dual
def test_title_weight_boost(search_conn):
    """A result with the query term in its title outranks one with term only in body.

    't1' has "Authentication" in the title.
    't2' has "authentication" only in the body.
    With 5x title boost, t1 should rank higher.
    """
    ds = DualIndexSearch(search_conn)
    results = ds.search("authentication")
    ids_ranked = [r.entity_id for r in results]
    assert "t1" in ids_ranked
    assert "t2" in ids_ranked
    assert ids_ranked.index("t1") < ids_ranked.index("t2"), (
        "Title-match result t1 should rank higher than body-match result t2"
    )


# ---------------------------------------------------------------------------
# 7. Proximity reranking — multi-term queries
# ---------------------------------------------------------------------------

@needs_dual
def test_proximity_reranking(search_conn):
    """Adjacent terms in source text rank higher than distant terms.

    't1' body: "Implement OAuth2 authentication with JWT tokens"
      → "OAuth2 authentication" are adjacent
    't2' body: "Migrate the authentication database to PostgreSQL"
      → "OAuth2" absent; "authentication" far from anything OAuth-like

    Searching "OAuth2 authentication" should rank t1 higher than t2.
    """
    ds = DualIndexSearch(search_conn)
    results = ds.search("OAuth2 authentication")
    ids_ranked = [r.entity_id for r in results]
    assert "t1" in ids_ranked
    if "t2" in ids_ranked:
        assert ids_ranked.index("t1") < ids_ranked.index("t2"), (
            "Proximity reranking: adjacent terms should outrank distant ones"
        )


# ---------------------------------------------------------------------------
# 8. Fuzzy fallback via Levenshtein
# ---------------------------------------------------------------------------

@needs_dual
def test_fuzzy_fallback_on_typo(search_conn):
    """Misspelling 'autentication' still finds 'authentication' via Levenshtein fuzzy fallback."""
    ds = DualIndexSearch(search_conn)
    results = ds.search("autentication")
    assert len(results) > 0, "Fuzzy fallback should find 'authentication' despite typo"
    matched_ids = {r.entity_id for r in results}
    assert "t1" in matched_ids or "s1" in matched_ids, (
        "At least one authentication-related entity should match"
    )


# ---------------------------------------------------------------------------
# 9. Smart snippet extraction
# ---------------------------------------------------------------------------

@needs_dual
def test_snippet_extraction(search_conn):
    """Snippets contain a window around the matched term."""
    ds = DualIndexSearch(search_conn)
    results = ds.search("JWT")
    assert len(results) > 0
    for r in results:
        assert r.snippet, "Snippet should not be empty"
    jwt_result = next((r for r in results if r.entity_id == "t1"), None)
    assert jwt_result is not None
    assert "JWT" in jwt_result.snippet or "jwt" in jwt_result.snippet.lower(), (
        "Snippet should contain a window around the matched term 'JWT'"
    )


# ---------------------------------------------------------------------------
# 10. Backward compat — global_search() still works with old signature
# ---------------------------------------------------------------------------

def test_global_search_backward_compatible(search_conn):
    """global_search(conn, query, types, limit) still returns results with old API."""
    results = global_search(search_conn, "authentication")
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)

    filtered = global_search(search_conn, "authentication", types=["task"])
    assert all(r.entity_type == "task" for r in filtered)

    limited = global_search(search_conn, "authentication", limit=1)
    assert len(limited) <= 1


# ---------------------------------------------------------------------------
# 11. global_search uses dual index under the hood
# ---------------------------------------------------------------------------

@needs_dual
def test_global_search_uses_dual_index(search_conn):
    """After DualIndexSearch is wired in, global_search() produces RRF-scored results.

    The score should follow RRF formula (positive, bounded) rather than raw
    BM25 (negative values from SQLite FTS5).
    """
    results = global_search(search_conn, "authentication")
    assert len(results) > 0
    for r in results:
        assert r.rank > 0, (
            f"With dual index, rank should be positive RRF score, got {r.rank}"
        )


# ---------------------------------------------------------------------------
# 12. Type filter works with dual index
# ---------------------------------------------------------------------------

@needs_dual
def test_search_with_type_filter(search_conn):
    """DualIndexSearch respects entity_type filter."""
    ds = DualIndexSearch(search_conn)
    results = ds.search("authentication", types=["task"])
    assert len(results) > 0
    assert all(r.entity_type == "task" for r in results), (
        "Type filter should restrict results to tasks only"
    )
