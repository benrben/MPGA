"""Tests for T024 — indexed_content table + FTS5 in schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / ".mpga" / "mpga.db"


@pytest.fixture()
def schema_conn(tmp_db: Path):
    from mpga.db.connection import get_connection
    from mpga.db.schema import create_schema

    conn = get_connection(str(tmp_db))
    create_schema(conn)
    yield conn
    conn.close()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


class TestIndexedContentSchema:
    def test_indexed_content_table_exists(self, schema_conn: sqlite3.Connection) -> None:
        assert "indexed_content" in _table_names(schema_conn)

    def test_indexed_content_columns(self, schema_conn: sqlite3.Connection) -> None:
        cols = {
            row[1]: {"type": row[2], "notnull": row[3], "dflt": row[4], "pk": row[5]}
            for row in schema_conn.execute("PRAGMA table_info(indexed_content)").fetchall()
        }
        assert "id" in cols
        assert cols["id"]["pk"] == 1

        for col in ("url", "title", "content", "content_type", "fetched_at", "content_hash"):
            assert col in cols, f"Missing column: {col}"

        assert cols["url"]["notnull"] == 1

    def test_indexed_content_fts_exists(self, schema_conn: sqlite3.Connection) -> None:
        tables = _table_names(schema_conn)
        assert "indexed_content_fts" in tables

        fts_sql = schema_conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='indexed_content_fts'"
        ).fetchone()[0].lower()
        assert "porter" in fts_sql

    def test_indexed_content_trigram_exists(self, schema_conn: sqlite3.Connection) -> None:
        tables = _table_names(schema_conn)
        assert "indexed_content_trigram" in tables

        fts_sql = schema_conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='indexed_content_trigram'"
        ).fetchone()[0].lower()
        assert "trigram" in fts_sql
        assert "content=" not in fts_sql

    def test_indexed_content_idempotent(self, tmp_db: Path) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_db))
        create_schema(conn)
        create_schema(conn)

        assert "indexed_content" in _table_names(conn)
        assert "indexed_content_fts" in _table_names(conn)
        assert "indexed_content_trigram" in _table_names(conn)
        conn.close()
