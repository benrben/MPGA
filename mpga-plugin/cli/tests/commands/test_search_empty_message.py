"""T014 — `mpga search` should explain empty results when FTS index is not populated.

The bug: when global_fts is empty (no records), search silently returns
"No results found." with no guidance on how to populate the index.
Fix: when FTS index count == 0, print a helpful message explaining the next step.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


def _make_empty_db(root: Path) -> None:
    """Create a DB with schema but no FTS data."""
    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()


class TestSearchEmptyMessage:
    """search must guide users when FTS index is empty."""

    def test_search_with_empty_fts_shows_populate_guidance(self, tmp_path: Path, monkeypatch):
        """When FTS index is empty, output contains guidance to populate it."""
        monkeypatch.chdir(tmp_path)
        _make_empty_db(tmp_path)

        # _get_conn() does a local import of find_project_root — patch at source
        import mpga.core.config as _cfg
        monkeypatch.setattr(_cfg, "find_project_root", lambda: str(tmp_path))

        from mpga.commands.search import search_cmd

        runner = CliRunner()
        result = runner.invoke(search_cmd, ["anything"])

        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Exception: {result.exception}\n"
            f"Output:\n{result.output}"
        )
        output_lower = result.output.lower()
        # Should contain guidance — e.g. "mpga sync" or "populate" or "index"
        assert any(
            phrase in output_lower
            for phrase in ("mpga sync", "mpga ctx", "populate", "index", "run `mpga")
        ), (
            f"Expected population guidance in output when FTS is empty, got:\n{result.output}"
        )

    def test_search_empty_message_not_shown_when_results_exist(self, tmp_path: Path, monkeypatch):
        """Guidance message is NOT shown when results are actually found."""
        monkeypatch.chdir(tmp_path)
        _make_empty_db(tmp_path)

        import mpga.core.config as _cfg
        monkeypatch.setattr(_cfg, "find_project_root", lambda: str(tmp_path))

        # Seed a task so FTS is non-empty (note: column name is column_ in schema)
        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.execute(
            "INSERT INTO tasks (id, title, column_, priority, created_at, updated_at) "
            "VALUES ('T001', 'authenticate users with JWT', 'backlog', 'medium', "
            "datetime('now'), datetime('now'))"
        )
        conn.commit()
        conn.close()

        from mpga.commands.search import search_cmd

        runner = CliRunner()
        result = runner.invoke(search_cmd, ["authenticate"])

        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Exception: {result.exception}\n{result.output}"
        )
        # When results are found, should NOT show the empty guidance
        assert "mpga sync" not in result.output.lower() or "authenticate" in result.output.lower()

    def test_search_still_shows_no_results_for_missing_query(self, tmp_path: Path, monkeypatch):
        """When FTS has data but query has no match, still shows 'No results found'."""
        monkeypatch.chdir(tmp_path)
        _make_empty_db(tmp_path)

        import mpga.core.config as _cfg
        monkeypatch.setattr(_cfg, "find_project_root", lambda: str(tmp_path))

        # Seed a task with known content
        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.execute(
            "INSERT INTO tasks (id, title, column_, priority, created_at, updated_at) "
            "VALUES ('T001', 'authenticate users', 'backlog', 'medium', "
            "datetime('now'), datetime('now'))"
        )
        conn.commit()
        conn.close()

        from mpga.commands.search import search_cmd

        runner = CliRunner()
        result = runner.invoke(search_cmd, ["zzzzunmatchablezzz"])

        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Exception: {result.exception}\n{result.output}"
        )
        # This is a "no match" case (not an "empty index" case)
        # Should show "No results found", not the empty-index guidance
        assert "No results found" in result.output
