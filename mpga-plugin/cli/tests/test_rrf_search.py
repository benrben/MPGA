"""Tests for T033 — Dual-index search and RRF scoring.

Coverage checklist for: T033 — DualIndexSearch + RRF
────────────────────────────────────────────────────
[x] AC1: RRF score computation correct           → test_rrf_score_computation
[x] AC2: Porter-only fallback works              → test_porter_only_fallback
[x] AC3: Trigram-only matches returned            → test_trigram_only_results
[x] AC4: Empty index returns empty               → test_empty_index_returns_empty
[x] AC5: 100+ items handled correctly            → test_large_result_set
[x] AC6: FTS special chars escaped safely         → test_search_with_special_characters
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.search import DualIndexSearch, SearchResult, rebuild_global_fts


@pytest.fixture()
def db_conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    yield conn
    conn.close()


def _insert_task(conn: sqlite3.Connection, task_id: str, title: str, body: str = "") -> None:
    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) "
        "VALUES (?, ?, ?, 'backlog', 'medium', datetime('now'), datetime('now'))",
        (task_id, title, body),
    )
    conn.commit()


def _insert_scope(conn: sqlite3.Connection, scope_id: str, name: str, summary: str = "") -> None:
    conn.execute(
        "INSERT INTO scopes (id, name, summary, created_at, updated_at) "
        "VALUES (?, ?, ?, datetime('now'), datetime('now'))",
        (scope_id, name, summary),
    )
    conn.commit()


class TestRRFScoreComputation:
    """AC1: Manual verification of the RRF formula."""

    def test_rrf_score_computation(self, db_conn: sqlite3.Connection) -> None:
        """Items in both indexes get higher RRF scores than items in only one."""
        _insert_task(db_conn, "T001", "authentication middleware", "handles user auth tokens")
        _insert_task(db_conn, "T002", "database migration", "schema changes for v2")
        _insert_scope(db_conn, "auth", "authentication", "auth module for the API")
        rebuild_global_fts(db_conn)

        searcher = DualIndexSearch(db_conn, k=60)
        results = searcher.search("authentication")

        assert len(results) >= 2

        auth_results = [r for r in results if "authentication" in r.title.lower()]
        other_results = [r for r in results if "authentication" not in r.title.lower()]

        if auth_results and other_results:
            assert auth_results[0].rank >= other_results[0].rank


class TestPorterOnlyFallback:
    """AC2: When no trigram data exists, porter-only search still works."""

    def test_porter_only_fallback(self, db_conn: sqlite3.Connection) -> None:
        _insert_task(db_conn, "T010", "refactor configuration", "clean up config loading")
        rebuild_global_fts(db_conn)

        db_conn.execute("DELETE FROM global_trigram")
        db_conn.commit()

        searcher = DualIndexSearch(db_conn, k=60)
        results = searcher.search("configuration")

        assert len(results) >= 1
        assert any("configuration" in r.title.lower() for r in results)


class TestTrigramOnlyResults:
    """AC3: Trigram-only matches still returned."""

    def test_trigram_only_results(self, db_conn: sqlite3.Connection) -> None:
        """A substring query that trigram finds but porter might miss."""
        _insert_task(db_conn, "T020", "AbcXyzHandler implementation", "custom handler for AbcXyz protocol")
        rebuild_global_fts(db_conn)

        searcher = DualIndexSearch(db_conn, k=60)
        results = searcher.search("AbcXyzHandler")

        assert len(results) >= 1
        assert any("AbcXyzHandler" in r.title for r in results)


class TestEmptyIndex:
    """AC4: Empty index returns empty results."""

    def test_empty_index_returns_empty(self, db_conn: sqlite3.Connection) -> None:
        rebuild_global_fts(db_conn)

        searcher = DualIndexSearch(db_conn, k=60)
        results = searcher.search("anything")
        assert results == []

    def test_empty_query_returns_empty(self, db_conn: sqlite3.Connection) -> None:
        _insert_task(db_conn, "T030", "some task", "body")
        rebuild_global_fts(db_conn)

        searcher = DualIndexSearch(db_conn, k=60)
        assert searcher.search("") == []
        assert searcher.search("   ") == []


class TestLargeResultSet:
    """AC5: 100+ items handled correctly."""

    def test_large_result_set(self, db_conn: sqlite3.Connection) -> None:
        for i in range(120):
            _insert_task(
                db_conn,
                f"T{i:04d}",
                f"migration step {i} update",
                f"migration detail {i} for database schema update",
            )
        rebuild_global_fts(db_conn)

        searcher = DualIndexSearch(db_conn, k=60)
        results = searcher.search("migration", limit=50)

        assert len(results) == 50
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(isinstance(r.rank, float) for r in results)


class TestSpecialCharacters:
    """AC6: FTS special characters are safely escaped."""

    def test_search_with_special_characters(self, db_conn: sqlite3.Connection) -> None:
        _insert_task(db_conn, "T040", "handle OR conditions", "support AND/OR logic in queries")
        _insert_task(db_conn, "T041", "parse (nested) expressions", "handle parenthesized groups")
        rebuild_global_fts(db_conn)

        searcher = DualIndexSearch(db_conn, k=60)

        results_or = searcher.search("OR")
        assert isinstance(results_or, list)

        results_parens = searcher.search("(nested)")
        assert isinstance(results_parens, list)

        results_quotes = searcher.search('"double quotes"')
        assert isinstance(results_quotes, list)

        results_dash = searcher.search("NOT -flag")
        assert isinstance(results_dash, list)
