"""Global FTS5 search — rebuild_global_fts and global_search."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from mpga.db.fts_utils import prefix_match_query


@dataclass
class SearchResult:
    entity_type: str
    entity_id: str
    title: str
    snippet: str
    rank: float


def rebuild_global_fts(conn: sqlite3.Connection) -> None:
    """Repopulate global_fts from tasks, scopes, evidence, milestones, decisions.

    DELETE all rows first (standalone FTS5 table — no content= sync),
    then INSERT from each entity table.
    """
    conn.execute("DELETE FROM global_fts")

    # Tasks
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT 'task', id, title, COALESCE(body, '')
        FROM tasks
        """
    )

    # Scopes
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT 'scope', id, name, COALESCE(summary, '') || ' ' || COALESCE(content, '')
        FROM scopes
        """
    )

    # Evidence
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT 'evidence', CAST(id AS TEXT), COALESCE(filepath, raw), COALESCE(description, '') || ' ' || raw
        FROM evidence
        """
    )

    # Milestones
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT 'milestone', id, name, COALESCE(summary, '')
        FROM milestones
        """
    )

    # Decisions
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT 'decision', id, title, COALESCE(content, '')
        FROM decisions
        """
    )

    conn.commit()


def global_search(
    conn: sqlite3.Connection,
    query: str,
    types: list[str] | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    """Search global_fts using FTS5 BM25 ranking.

    Args:
        conn: SQLite connection.
        query: Search query string (terms are auto-prefixed).
        types: Optional list of entity_type values to filter by.
        limit: Maximum number of results.

    Returns:
        List of SearchResult ordered by relevance (most relevant first).
    """
    match_query = prefix_match_query(query)

    if types:
        placeholders = ",".join("?" * len(types))
        sql = f"""
            SELECT
                entity_type,
                entity_id,
                title,
                snippet(global_fts, 3, '<b>', '</b>', '...', 32),
                bm25(global_fts)
            FROM global_fts
            WHERE global_fts MATCH ?
              AND entity_type IN ({placeholders})
            ORDER BY bm25(global_fts)
            LIMIT ?
        """
        params: list = [match_query, *types, limit]
    else:
        sql = """
            SELECT
                entity_type,
                entity_id,
                title,
                snippet(global_fts, 3, '<b>', '</b>', '...', 32),
                bm25(global_fts)
            FROM global_fts
            WHERE global_fts MATCH ?
            ORDER BY bm25(global_fts)
            LIMIT ?
        """
        params = [match_query, limit]

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        SearchResult(
            entity_type=row[0],
            entity_id=row[1],
            title=row[2],
            snippet=row[3],
            rank=row[4],
        )
        for row in rows
    ]
