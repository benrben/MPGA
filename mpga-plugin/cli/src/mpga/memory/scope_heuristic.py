"""Scope assignment heuristic — map observations to scopes via file path membership."""
from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict


def assign_scope(
    conn: sqlite3.Connection,
    files_read: list[str],
    files_modified: list[str],
) -> str | None:
    all_files = files_read + files_modified
    if not all_files:
        return None

    scope_prefixes = _get_scope_prefixes(conn)
    if not scope_prefixes:
        return None

    votes: Counter[str] = Counter()
    for filepath in all_files:
        scope = _longest_prefix_match(filepath, scope_prefixes)
        if scope:
            votes[scope] += 1

    if not votes:
        return None

    total = len(all_files)
    best_scope, count = votes.most_common(1)[0]
    if count / total > 0.5:
        return best_scope

    return None


def _get_scope_prefixes(conn: sqlite3.Connection) -> dict[str, list[str]]:
    rows = conn.execute(
        "SELECT DISTINCT scope_id, filepath FROM evidence "
        "WHERE scope_id IS NOT NULL AND filepath IS NOT NULL"
    ).fetchall()

    prefixes: dict[str, list[str]] = defaultdict(list)
    for scope_id, filepath in rows:
        parts = filepath.rsplit("/", 1)
        prefix = parts[0] + "/" if len(parts) > 1 else ""
        if prefix and prefix not in prefixes[scope_id]:
            prefixes[scope_id].append(prefix)

    return dict(prefixes)


def _longest_prefix_match(filepath: str, scope_prefixes: dict[str, list[str]]) -> str | None:
    best_scope = None
    best_len = 0

    for scope_id, pfxs in scope_prefixes.items():
        for pfx in pfxs:
            if filepath.startswith(pfx) and len(pfx) > best_len:
                best_scope = scope_id
                best_len = len(pfx)

    return best_scope
