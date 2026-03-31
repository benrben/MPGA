"""FileInfoRepo — CRUD for scanned file metadata."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class FileInfo:
    filepath: str
    language: str | None = None
    lines: int | None = None
    size: int | None = None
    content_hash: str | None = None
    last_scanned: str = ""


class FileInfoRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(
        self,
        filepath: str,
        language: str | None = None,
        lines: int | None = None,
        size: int | None = None,
        content_hash: str | None = None,
    ) -> FileInfo:
        self._conn.execute(
            """
            INSERT INTO file_info (filepath, language, lines, size, content_hash, last_scanned)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(filepath) DO UPDATE SET
                language = excluded.language,
                lines = excluded.lines,
                size = excluded.size,
                content_hash = excluded.content_hash,
                last_scanned = datetime('now')
            """,
            (filepath, language, lines, size, content_hash),
        )
        self._conn.commit()
        return self.get(filepath)  # type: ignore[return-value]

    def get(self, filepath: str) -> FileInfo | None:
        row = self._conn.execute(
            "SELECT filepath, language, lines, size, content_hash, last_scanned "
            "FROM file_info WHERE filepath = ?",
            (filepath,),
        ).fetchone()
        if row is None:
            return None
        return FileInfo(*row)

    def list_all(self) -> list[FileInfo]:
        rows = self._conn.execute(
            "SELECT filepath, language, lines, size, content_hash, last_scanned FROM file_info"
        ).fetchall()
        return [FileInfo(*r) for r in rows]
