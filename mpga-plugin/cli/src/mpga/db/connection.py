"""SQLite connection factory with WAL mode and foreign keys."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a WAL-mode SQLite connection with foreign keys enabled.

    Creates parent directories if they don't exist.
    """
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def open_db(project_root: str | Path) -> sqlite3.Connection:
    """Open (and schema-init) the project's .mpga/mpga.db in one call.

    Equivalent to: get_connection(...) + create_schema(conn).
    Use this in command handlers instead of repeating the two-liner.
    """
    from mpga.db.schema import create_schema  # local import avoids circular

    db_path = Path(project_root) / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    return conn
