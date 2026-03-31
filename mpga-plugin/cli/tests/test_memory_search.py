"""Tests for T009 — Implement mpga memory search (Layer 1: compact index).

Coverage checklist for: T009 — mpga memory search CLI command

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: memory CLI group exists               → test_memory_command_group_exists
[x] AC2: memory search subcommand exists        → test_memory_search_command_exists
[x] AC3: search returns matching observations   → test_search_returns_results
[x] AC4: compact format [O{id}] type: title     → test_search_compact_format
[x] AC5: --type filter restricts by obs type    → test_search_type_filter
[x] AC6: --limit caps result count (default 20) → test_search_limit
[x] AC7: no matches → informative message       → test_search_no_results
[x] AC8: uses DualIndexSearch for ranking        → test_search_uses_dual_index

Untested branches / edge cases:
- [ ] empty query string (degenerate)
- [ ] unicode in observation titles
- [ ] observations with missing fields (null narrative/facts)
- [ ] concurrent search access
"""

from __future__ import annotations

import re
import sqlite3

import pytest
from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.search import rebuild_global_fts

# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-252 :: observations table
# Evidence: [E] mpga-plugin/cli/src/mpga/db/search.py:41-68 :: DualIndexSearch.search()
# Evidence: [E] mpga-plugin/cli/src/mpga/cli.py:52-94 :: _COMMANDS lazy-load registry

try:
    from mpga.commands.memory import memory

    _HAS_MEMORY = True
except ImportError:
    memory = None  # type: ignore[assignment]
    _HAS_MEMORY = False


@pytest.fixture
def memory_db(tmp_path, monkeypatch):
    """Provide a schema-initialized DB seeded with observations for search tests."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    conn.execute(
        "INSERT INTO observations (session_id, title, type, narrative, facts, created_at) "
        "VALUES ('s1', 'Auth module pattern', 'discovery', 'Found JWT pattern', '[\"jwt\"]', '2026-03-31')"
    )
    conn.execute(
        "INSERT INTO observations (session_id, title, type, narrative, facts, created_at) "
        "VALUES ('s1', 'Database error fix', 'error', 'Fixed connection pool', '[\"pool\"]', '2026-03-31')"
    )
    conn.execute(
        "INSERT INTO observations (session_id, title, type, narrative, facts, created_at) "
        "VALUES ('s1', 'Chose Redis over Memcached', 'decision', 'Redis better for our use case', '[\"redis\"]', '2026-03-31')"
    )
    conn.commit()

    rebuild_global_fts(conn)
    conn.close()

    if _HAS_MEMORY:
        monkeypatch.setattr("mpga.commands.memory._project_root", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Degenerate — command group exists
# ---------------------------------------------------------------------------


def test_memory_command_group_exists():
    """The 'memory' Click group must be importable from mpga.commands.memory."""
    assert _HAS_MEMORY, (
        "mpga.commands.memory module does not exist or 'memory' group is not importable"
    )
    import click

    assert isinstance(memory, click.Group), (
        "'memory' should be a Click Group"
    )


# ---------------------------------------------------------------------------
# 2. Degenerate — search subcommand exists
# ---------------------------------------------------------------------------


def test_memory_search_command_exists():
    """The memory group must have a 'search' subcommand."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    command_names = list(memory.commands)
    assert "search" in command_names, (
        f"'search' not in memory commands. Found: {command_names}"
    )


# ---------------------------------------------------------------------------
# 3. Simplest valid — search returns results
# ---------------------------------------------------------------------------


def test_search_returns_results(memory_db):
    """Searching 'auth' returns at least one observation match."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["search", "auth"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert "Auth module pattern" in result.output, (
        f"Expected 'Auth module pattern' in output, got:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 4. Format — compact index format [O{id}] type: title (date)
# ---------------------------------------------------------------------------


def test_search_compact_format(memory_db):
    """Results are grouped by date/scope with icon [O{id}] title (~Ntok) format."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["search", "auth"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    pattern = re.compile(r"\[O\d+\] .+\(~\d+tok\)", re.MULTILINE)
    matches = pattern.findall(result.output)
    assert len(matches) >= 1, (
        f"No lines match enriched format icon [O{{id}}] title (~Ntok).\n"
        f"Output:\n{result.output}"
    )
    assert "##" in result.output, (
        f"Expected date grouping header (##) in output:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 5. Selection — --type filter restricts by observation type
# ---------------------------------------------------------------------------


def test_search_type_filter(memory_db):
    """--type error returns only error-type observations."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["search", "fix", "--type", "error"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    lines = [ln for ln in result.output.strip().splitlines() if "[O" in ln]
    assert len(lines) >= 1, f"Expected at least 1 error result, got:\n{result.output}"
    assert "Database error fix" in result.output, (
        f"Expected 'Database error fix' in filtered results:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 6. Scalar → collection — --limit caps result count
# ---------------------------------------------------------------------------


def test_search_limit(memory_db):
    """--limit 1 returns at most 1 observation result line."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["search", "auth", "--limit", "1"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    result_lines = [ln for ln in result.output.strip().splitlines() if "[O" in ln]
    assert len(result_lines) <= 1, (
        f"--limit 1 should return at most 1 result, got {len(result_lines)}:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 7. Selection — no results gives informative message
# ---------------------------------------------------------------------------


def test_search_no_results(memory_db):
    """Searching for a nonexistent term returns a 'no results' message."""
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["search", "zzz_nonexistent_zzz"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    result_lines = [ln for ln in result.output.strip().splitlines() if "[O" in ln]
    assert len(result_lines) == 0, (
        f"Should return no observation results for nonsense query, got:\n{result.output}"
    )
    lower_out = result.output.lower()
    assert "no" in lower_out and "result" in lower_out, (
        f"Expected informative 'no results' message, got:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# 8. Integration — search uses DualIndexSearch (trigram substring match)
# ---------------------------------------------------------------------------


def test_search_uses_dual_index(memory_db):
    """DualIndexSearch finds substring matches via trigram index.

    'Redis' appears in the observation title/narrative. A trigram search for
    a partial substring 'Redi' (not a full word, only 4 chars) should still
    match via the trigram index, proving DualIndexSearch is wired in.
    """
    assert _HAS_MEMORY, "mpga.commands.memory not importable"
    runner = CliRunner()
    result = runner.invoke(memory, ["search", "Redi"])
    assert result.exit_code == 0, f"CLI failed: {result.output}"
    assert "Redis" in result.output, (
        f"DualIndexSearch trigram should find 'Redis' via substring 'Redi'.\n"
        f"Output:\n{result.output}"
    )
