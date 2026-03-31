"""GraphRepo — CRUD for dependency graph edges."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class GraphEdge:
    source: str
    target: str
    type: str = "import"


class GraphRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_edge(self, source: str, target: str, type: str = "import") -> GraphEdge:
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_edges (source, target, type) VALUES (?, ?, ?)",
            (source, target, type),
        )
        self._conn.commit()
        return GraphEdge(source=source, target=target, type=type)

    def get_edges(self, source: str) -> list[GraphEdge]:
        rows = self._conn.execute(
            "SELECT source, target, type FROM graph_edges WHERE source = ?",
            (source,),
        ).fetchall()
        return [GraphEdge(*r) for r in rows]

    def get_all(self) -> list[GraphEdge]:
        rows = self._conn.execute(
            "SELECT source, target, type FROM graph_edges"
        ).fetchall()
        return [GraphEdge(*r) for r in rows]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM graph_edges")
        self._conn.commit()
