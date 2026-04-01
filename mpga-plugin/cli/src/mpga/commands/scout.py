from __future__ import annotations

import sys
import sqlite3
from datetime import datetime, timezone

import click


DEFAULT_DB = ".mpga/mpga.db"


def scout_cache_check(scope: str, db_path: str) -> bool:
    """Return True if scope is in scout_cache and was marked within 5 minutes."""
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT scouted_at FROM scout_cache WHERE scope = ?", (scope,)
    ).fetchone()
    conn.close()
    if row is None:
        return False
    scouted_at = datetime.fromisoformat(row[0])
    now = datetime.now(timezone.utc)
    if scouted_at.tzinfo is None:
        scouted_at = scouted_at.replace(tzinfo=timezone.utc)
    elapsed = (now - scouted_at).total_seconds()
    return elapsed < 300


def scout_cache_mark(scope: str, db_path: str) -> None:
    """Upsert scope into scout_cache with current UTC timestamp."""
    conn = sqlite3.connect(db_path)
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO scout_cache (scope, scouted_at) VALUES (?, ?)",
        (scope, ts),
    )
    conn.commit()
    conn.close()


@click.group("cache")
def cache_group() -> None:
    """Scout cache subcommands."""


@cache_group.command("check")
@click.argument("scope")
@click.option("--db", default=DEFAULT_DB, help="Path to the MPGA database.")
def check_cmd(scope: str, db: str) -> None:
    """Exit 0 if scope is cached within 5 minutes, else exit 1."""
    fresh = scout_cache_check(scope, db)
    sys.exit(0 if fresh else 1)


@cache_group.command("mark")
@click.argument("scope")
@click.option("--db", default=DEFAULT_DB, help="Path to the MPGA database.")
def mark_cmd(scope: str, db: str) -> None:
    """Mark scope as scouted in the cache."""
    scout_cache_mark(scope, db)


@click.group("scout")
def scout() -> None:
    """Scout commands."""


scout.add_command(cache_group)
