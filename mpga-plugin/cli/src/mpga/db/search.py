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


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            curr_row.append(min(
                prev_row[j + 1] + 1,
                curr_row[j] + 1,
                prev_row[j] + (c1 != c2),
            ))
        prev_row = curr_row
    return prev_row[-1]


_VALID_FTS_TABLES = frozenset({"global_fts", "global_trigram"})


class DualIndexSearch:
    """RRF-fused search over Porter (global_fts) and Trigram (global_trigram) indexes."""

    TITLE_BOOST = 5.0
    PROXIMITY_THRESHOLD = 50
    PROXIMITY_MULTIPLIER = 2.0
    SNIPPET_WINDOW = 32
    SNIPPET_FALLBACK_LEN = 64
    MAX_LEVENSHTEIN_DIST = 2
    MAX_FUZZY_SCAN = 500

    def __init__(self, conn: sqlite3.Connection, k: int = 60):
        self._conn = conn
        self._k = k

    def search(
        self, query: str, types: list[str] | None = None, limit: int = 10,
    ) -> list[SearchResult]:
        if not query or not query.strip():
            return []

        porter_rows = self._query_porter(query, types)
        trigram_rows = self._query_trigram(query, types)

        if not porter_rows:
            porter_rows = self._fuzzy_search(query, types)

        return self._rrf_merge(porter_rows, trigram_rows, query)[:limit]

    def _query_porter(self, query: str, types: list[str] | None) -> list[tuple]:
        return self._run_fts("global_fts", prefix_match_query(query), types)

    def _query_trigram(self, query: str, types: list[str] | None) -> list[tuple]:
        terms = []
        for w in query.split():
            w = w.strip()
            if w and len(w) >= 3:
                terms.append('"' + w.replace('"', '""') + '"')
        if not terms:
            return []
        return self._run_fts("global_trigram", " ".join(terms), types)

    def _run_fts(
        self, table: str, match_expr: str, types: list[str] | None,
    ) -> list[tuple]:
        if table not in _VALID_FTS_TABLES:
            raise ValueError(f"Unknown FTS table: {table}")
        if types:
            placeholders = ",".join("?" * len(types))
            sql = (
                f"SELECT entity_type, entity_id, title, content "
                f"FROM {table} WHERE {table} MATCH ? "
                f"AND entity_type IN ({placeholders}) "
                f"ORDER BY bm25({table})"
            )
            params: list = [match_expr, *types]
        else:
            sql = (
                f"SELECT entity_type, entity_id, title, content "
                f"FROM {table} WHERE {table} MATCH ? "
                f"ORDER BY bm25({table})"
            )
            params = [match_expr]
        try:
            return self._conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            return []

    def _fuzzy_search(self, query: str, types: list[str] | None) -> list[tuple]:
        if types:
            placeholders = ",".join("?" * len(types))
            sql = (
                "SELECT entity_type, entity_id, title, content "
                f"FROM global_fts WHERE entity_type IN ({placeholders})"
            )
            rows = self._conn.execute(sql, types).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT entity_type, entity_id, title, content FROM global_fts",
            ).fetchall()
        q = query.lower()
        return [
            r for r in rows[:self.MAX_FUZZY_SCAN]
            if any(
                _levenshtein(q, w) <= self.MAX_LEVENSHTEIN_DIST
                for w in r[2].lower().split()
            )
        ]

    def _rrf_merge(
        self, porter_rows: list[tuple], trigram_rows: list[tuple], query: str,
    ) -> list[SearchResult]:
        scores: dict[tuple, float] = {}
        meta: dict[tuple, tuple] = {}

        for rank_idx, row in enumerate(porter_rows, 1):
            key = (row[0], row[1])
            scores[key] = scores.get(key, 0.0) + 1.0 / (self._k + rank_idx)
            meta[key] = row

        for rank_idx, row in enumerate(trigram_rows, 1):
            key = (row[0], row[1])
            scores[key] = scores.get(key, 0.0) + 1.0 / (self._k + rank_idx)
            if key not in meta:
                meta[key] = row

        query_terms = query.lower().split()

        def sort_key(key: tuple) -> float:
            rrf = scores[key]
            title_lower = meta[key][2].lower()
            boost = self.TITLE_BOOST if any(t in title_lower for t in query_terms) else 1.0
            prox = self._proximity_boost(
                query_terms, title_lower + " " + meta[key][3].lower(),
            )
            return rrf * boost * prox

        sorted_keys = sorted(scores, key=sort_key, reverse=True)

        return [
            SearchResult(
                entity_type=meta[k][0],
                entity_id=meta[k][1],
                title=meta[k][2],
                snippet=self._extract_snippet(query, meta[k][3]),
                rank=scores[k],
            )
            for k in sorted_keys
        ]

    @classmethod
    def _proximity_boost(cls, terms: list[str], text: str) -> float:
        if len(terms) < 2:
            return 1.0
        positions = [p for t in terms if (p := text.find(t)) >= 0]
        if len(positions) < 2:
            return 1.0
        positions.sort()
        return cls.PROXIMITY_MULTIPLIER if positions[-1] - positions[0] < cls.PROXIMITY_THRESHOLD else 1.0

    @classmethod
    def _extract_snippet(cls, query: str, content: str) -> str:
        if not content:
            return ""
        window = cls.SNIPPET_WINDOW
        content_lower = content.lower()
        for t in query.lower().split():
            pos = content_lower.find(t)
            if pos >= 0:
                start = max(0, pos - window)
                end = min(len(content), pos + window)
                return content[start:end]
        return content[:cls.SNIPPET_FALLBACK_LEN]


def rebuild_global_fts(conn: sqlite3.Connection) -> None:
    """Repopulate global_fts from tasks, scopes, evidence, milestones, decisions, observations, indexed_content.

    DELETE all rows first (standalone FTS5 table — no content= sync),
    then INSERT from each entity table. Rebuilds global_trigram from global_fts.
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

    # Observations
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT
            'observation',
            CAST(id AS TEXT),
            title,
            COALESCE(narrative, '') || ' ' || COALESCE(facts, '') || ' ' || COALESCE(concepts, '')
        FROM observations
        """
    )

    # Indexed content (web pages, external docs)
    conn.execute(
        """
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        SELECT
            'indexed_content',
            CAST(id AS TEXT),
            COALESCE(title, url),
            COALESCE(content, '')
        FROM indexed_content
        """
    )

    conn.execute("DELETE FROM global_trigram")
    conn.execute(
        """
        INSERT INTO global_trigram (entity_type, entity_id, title, content)
        SELECT entity_type, entity_id, title, content FROM global_fts
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
    try:
        if conn.execute("SELECT 1 FROM global_trigram LIMIT 1").fetchone():
            return DualIndexSearch(conn).search(query, types=types, limit=limit)
    except sqlite3.OperationalError:
        pass

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
