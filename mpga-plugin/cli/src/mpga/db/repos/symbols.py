"""SymbolRepo — CRUD + FTS5 for AST symbols."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Symbol:
    id: int
    filepath: str
    name: str
    type: str | None = None
    start_line: int | None = None
    end_line: int | None = None


class SymbolRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        filepath: str,
        name: str,
        type: str | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> Symbol:
        cur = self._conn.execute(
            "INSERT INTO symbols (filepath, name, type, start_line, end_line) "
            "VALUES (?, ?, ?, ?, ?)",
            (filepath, name, type, start_line, end_line),
        )
        row_id = cur.lastrowid
        # Sync FTS5
        self._conn.execute(
            "INSERT INTO symbols_fts(rowid, name, type, filepath) VALUES (?, ?, ?, ?)",
            (row_id, name, type, filepath),
        )
        self._conn.commit()
        return self._get_by_id(row_id)  # type: ignore[return-value]

    def _get_by_id(self, symbol_id: int) -> Symbol | None:
        row = self._conn.execute(
            "SELECT id, filepath, name, type, start_line, end_line FROM symbols WHERE id = ?",
            (symbol_id,),
        ).fetchone()
        if row is None:
            return None
        return Symbol(*row)

    def find_by_name(self, name: str) -> list[Symbol]:
        rows = self._conn.execute(
            "SELECT s.id, s.filepath, s.name, s.type, s.start_line, s.end_line "
            "FROM symbols_fts "
            "JOIN symbols s ON s.id = symbols_fts.rowid "
            "WHERE symbols_fts MATCH ? "
            "ORDER BY rank",
            (name,),
        ).fetchall()
        return [Symbol(*r) for r in rows]

    def find_by_filepath(self, filepath: str) -> list[Symbol]:
        rows = self._conn.execute(
            "SELECT id, filepath, name, type, start_line, end_line "
            "FROM symbols WHERE filepath = ?",
            (filepath,),
        ).fetchall()
        return [Symbol(*r) for r in rows]

    def clear_filepath(self, filepath: str) -> None:
        # Remove FTS entries first
        self._conn.execute(
            "DELETE FROM symbols_fts WHERE rowid IN "
            "(SELECT id FROM symbols WHERE filepath = ?)",
            (filepath,),
        )
        self._conn.execute("DELETE FROM symbols WHERE filepath = ?", (filepath,))
        self._conn.commit()
