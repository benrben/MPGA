"""Tests for T025 — mpga index url CLI command."""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema

NOW = "2026-01-01T00:00:00"


@pytest.fixture()
def schema_conn(tmp_path: Path):
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def cli_runner(tmp_path: Path, monkeypatch):
    (tmp_path / ".mpga").mkdir(exist_ok=True)
    monkeypatch.setattr("mpga.core.config.find_project_root", lambda *a, **kw: tmp_path)
    from mpga.cli import main
    import mpga.commands.index_cmd as _idx
    monkeypatch.setattr(_idx, "find_project_root", lambda *a, **kw: tmp_path)
    runner = click.testing.CliRunner()
    return runner, main, tmp_path


def _mock_urlopen(content: bytes = b"<html><title>Test Page</title><body>Hello world</body></html>"):
    resp = MagicMock()
    resp.read.return_value = content
    resp.headers = {"Content-Type": "text/html"}
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# 1. Degenerate — command exists
# ---------------------------------------------------------------------------

def test_index_command_exists():
    """The 'index' command is registered in the CLI."""
    from mpga.cli import main
    runner = click.testing.CliRunner()
    result = runner.invoke(main, ["index", "--help"])
    assert result.exit_code == 0
    assert "url" in result.output.lower()


# ---------------------------------------------------------------------------
# 2. index url stores content in DB
# ---------------------------------------------------------------------------

@patch("mpga.commands.index_cmd.urlopen")
def test_index_url_stores_content(mock_urlopen, cli_runner):
    mock_urlopen.return_value = _mock_urlopen()
    runner, main, tmp_path = cli_runner

    result = runner.invoke(main, ["index", "url", "https://example.com/page"])
    assert result.exit_code == 0, result.output

    conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
    create_schema(conn)
    row = conn.execute("SELECT url, title, content, content_hash FROM indexed_content").fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "https://example.com/page"
    assert row[2] is not None
    assert row[3] is not None


# ---------------------------------------------------------------------------
# 3. Dedup — same URL doesn't duplicate
# ---------------------------------------------------------------------------

@patch("mpga.commands.index_cmd.urlopen")
def test_index_url_dedup(mock_urlopen, cli_runner):
    mock_urlopen.return_value = _mock_urlopen()
    runner, main, tmp_path = cli_runner

    runner.invoke(main, ["index", "url", "https://example.com/page"])
    mock_urlopen.return_value = _mock_urlopen()
    runner.invoke(main, ["index", "url", "https://example.com/page"])

    conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
    create_schema(conn)
    count = conn.execute("SELECT COUNT(*) FROM indexed_content WHERE url = ?",
                         ("https://example.com/page",)).fetchone()[0]
    conn.close()

    assert count == 1


# ---------------------------------------------------------------------------
# 4. FTS populated — content searchable
# ---------------------------------------------------------------------------

@patch("mpga.commands.index_cmd.urlopen")
def test_index_url_populates_fts(mock_urlopen, cli_runner):
    mock_urlopen.return_value = _mock_urlopen(
        b"<html><title>Python Guide</title><body>Learn python programming</body></html>"
    )
    runner, main, tmp_path = cli_runner

    result = runner.invoke(main, ["index", "url", "https://example.com/python"])
    assert result.exit_code == 0, result.output

    conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
    create_schema(conn)

    fts_row = conn.execute(
        "SELECT url, title, content FROM indexed_content_fts WHERE indexed_content_fts MATCH ?",
        ("python",),
    ).fetchone()
    conn.close()

    assert fts_row is not None, "Content should be searchable via FTS"


# ---------------------------------------------------------------------------
# 5. Confirmation output
# ---------------------------------------------------------------------------

@patch("mpga.commands.index_cmd.urlopen")
def test_index_url_shows_confirmation(mock_urlopen, cli_runner):
    mock_urlopen.return_value = _mock_urlopen()
    runner, main, _ = cli_runner

    result = runner.invoke(main, ["index", "url", "https://example.com/page"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "indexed" in output_lower or "stored" in output_lower or "success" in output_lower


# ---------------------------------------------------------------------------
# 6. Error handling — bad URL
# ---------------------------------------------------------------------------

@patch("mpga.commands.index_cmd.urlopen")
def test_index_url_handles_error(mock_urlopen, cli_runner):
    from urllib.error import URLError
    mock_urlopen.side_effect = URLError("Connection refused")
    runner, main, _ = cli_runner

    result = runner.invoke(main, ["index", "url", "https://nonexistent.invalid/"])
    assert result.exit_code == 0 or result.exit_code == 1
    output_lower = result.output.lower()
    assert "error" in output_lower or "failed" in output_lower
