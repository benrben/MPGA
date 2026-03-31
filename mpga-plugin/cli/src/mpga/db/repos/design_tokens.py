"""DesignTokenRepo — CRUD for design tokens."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class DesignToken:
    id: int
    category: str
    name: str
    value: str
    source_file: str | None = None


class DesignTokenRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self,
        category: str,
        name: str,
        value: str,
        source_file: str | None = None,
    ) -> DesignToken:
        self._conn.execute(
            """
            INSERT INTO design_tokens (category, name, value, source_file)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(category, name) DO UPDATE SET
                value = excluded.value,
                source_file = excluded.source_file
            """,
            (category, name, value, source_file),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT id, category, name, value, source_file FROM design_tokens "
            "WHERE category = ? AND name = ?",
            (category, name),
        ).fetchone()
        return DesignToken(*row)

    def get_by_category(self, category: str) -> list[DesignToken]:
        rows = self._conn.execute(
            "SELECT id, category, name, value, source_file FROM design_tokens "
            "WHERE category = ?",
            (category,),
        ).fetchall()
        return [DesignToken(*r) for r in rows]

    def list_all(self) -> list[DesignToken]:
        rows = self._conn.execute(
            "SELECT id, category, name, value, source_file FROM design_tokens"
        ).fetchall()
        return [DesignToken(*r) for r in rows]
