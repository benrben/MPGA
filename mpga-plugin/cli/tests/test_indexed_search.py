"""Tests for T026 — Wire indexed_content into dual-index search."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.search import DualIndexSearch, SearchResult, rebuild_global_fts

NOW = "2026-01-01T00:00:00"


@pytest.fixture()
def search_conn(tmp_path: Path):
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    conn.execute(
        "INSERT INTO indexed_content (url, title, content, content_type, content_hash, fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("https://docs.example.com/api", "API Documentation",
         "REST API reference for authentication endpoints and OAuth2 flows",
         "text/html", "abc123hash", NOW),
    )
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# 1. rebuild_global_fts includes indexed_content
# ---------------------------------------------------------------------------

def test_rebuild_includes_indexed_content(search_conn):
    """rebuild_global_fts populates global_fts with indexed_content rows."""
    rebuild_global_fts(search_conn)

    row = search_conn.execute(
        "SELECT entity_type, entity_id, title, content FROM global_fts "
        "WHERE entity_type = 'indexed_content'"
    ).fetchone()

    assert row is not None, "indexed_content should appear in global_fts after rebuild"
    assert row[0] == "indexed_content"
    assert "API Documentation" in row[2]


# ---------------------------------------------------------------------------
# 2. DualIndexSearch finds indexed_content
# ---------------------------------------------------------------------------

def test_search_finds_indexed_content(search_conn):
    """DualIndexSearch returns indexed_content when query matches."""
    rebuild_global_fts(search_conn)

    ds = DualIndexSearch(search_conn)
    results = ds.search("API Documentation")

    assert len(results) > 0, "Should find indexed content"
    matched = [r for r in results if r.entity_type == "indexed_content"]
    assert len(matched) > 0, "At least one result should be entity_type='indexed_content'"


# ---------------------------------------------------------------------------
# 3. entity_type is 'indexed_content'
# ---------------------------------------------------------------------------

def test_indexed_content_entity_type(search_conn):
    """Indexed content entries use entity_type='indexed_content'."""
    rebuild_global_fts(search_conn)

    rows = search_conn.execute(
        "SELECT entity_type FROM global_fts WHERE entity_type = 'indexed_content'"
    ).fetchall()

    assert len(rows) > 0
    assert all(r[0] == "indexed_content" for r in rows)


# ---------------------------------------------------------------------------
# 4. Mixed results — observations + indexed content
# ---------------------------------------------------------------------------

def test_search_mixed_results(search_conn):
    """Search returns both observations and indexed content."""
    search_conn.execute(
        "INSERT INTO observations (session_id, scope_id, title, type, narrative, facts, concepts, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("s1", "sc1", "OAuth2 authentication flow",
         "discovery", "Discovered OAuth2 authentication patterns", "[]", "[]", NOW),
    )
    search_conn.commit()

    rebuild_global_fts(search_conn)

    ds = DualIndexSearch(search_conn)
    results = ds.search("authentication")

    entity_types = {r.entity_type for r in results}
    assert "observation" in entity_types, "Should find observations"
    assert "indexed_content" in entity_types, "Should find indexed content"
