"""Migration runner — applies pending SQL files in version order."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

_DEFAULT_MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_VERSION_RE = re.compile(r"^v(\d+)_")


def run_migrations(conn: sqlite3.Connection, migrations_dir: str | None = None) -> None:
    """Apply pending SQL migration files in ascending version order.

    Tracks applied versions in the schema_version table. Idempotent.
    """
    sql_dir = Path(migrations_dir) if migrations_dir is not None else _DEFAULT_MIGRATIONS_DIR

    sql_files = sorted(
        (f for f in sql_dir.iterdir() if f.suffix == ".sql"),
        key=lambda f: int(_VERSION_RE.match(f.name).group(1)),
    )

    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_version").fetchall()
    }

    for sql_file in sql_files:
        version = int(_VERSION_RE.match(sql_file.name).group(1))
        if version in applied:
            continue
        conn.executescript(sql_file.read_text())
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version, applied_at, description) "
            "VALUES (?, datetime('now'), ?)",
            (version, sql_file.stem),
        )
        conn.commit()
