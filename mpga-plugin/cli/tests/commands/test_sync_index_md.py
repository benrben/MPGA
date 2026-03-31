"""Tests for INDEX.md generation at the end of mpga sync (T026)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner


def create_mpga_db(root: Path) -> None:
    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    from mpga.db.schema import create_schema
    conn = sqlite3.connect(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()


def write_config(root: Path, name: str = "test-project") -> None:
    cfg = {
        "version": "1.0.0",
        "project": {
            "name": name,
            "languages": ["typescript"],
            "entryPoints": [],
            "ignore": ["node_modules", "dist", ".git"],
        },
    }
    (root / "mpga.config.json").write_text(json.dumps(cfg, indent=2))


def write_sample_ts(root: Path) -> None:
    src = root / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "index.ts").write_text("export function main(): void {}\n")
    (src / "utils.ts").write_text("export function add(a: number, b: number): number { return a + b; }\n")


# ---------------------------------------------------------------------------
# Tests: INDEX.md generation
# ---------------------------------------------------------------------------

class TestSyncIndexMd:
    """sync generates INDEX.md in the project root after completing."""

    def test_sync_creates_index_md(self, tmp_path: Path, monkeypatch):
        """sync writes INDEX.md to the project root."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts(tmp_path)
        create_mpga_db(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output

        index_md = tmp_path / "INDEX.md"
        assert index_md.exists(), "sync should create INDEX.md in the project root"

    def test_index_md_contains_project_name(self, tmp_path: Path, monkeypatch):
        """INDEX.md contains the project name from config."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path, name="my-awesome-project")
        write_sample_ts(tmp_path)
        create_mpga_db(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output

        content = (tmp_path / "INDEX.md").read_text()
        assert "my-awesome-project" in content, "INDEX.md should mention the project name"

    def test_index_md_contains_scope_names(self, tmp_path: Path, monkeypatch):
        """INDEX.md lists scope names discovered during sync."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts(tmp_path)
        create_mpga_db(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output

        content = (tmp_path / "INDEX.md").read_text()
        # Sync groups files into at least one scope; INDEX.md must list it
        assert "## Scopes" in content or "scope" in content.lower(), (
            "INDEX.md should list discovered scopes"
        )

    def test_index_md_contains_key_files(self, tmp_path: Path, monkeypatch):
        """INDEX.md mentions entry-point files discovered during scan."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts(tmp_path)
        create_mpga_db(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output

        content = (tmp_path / "INDEX.md").read_text()
        # src/index.ts matches an ENTRY_PATTERNS pattern and should appear
        assert "index.ts" in content or "src/index" in content, (
            "INDEX.md should reference key entry-point files"
        )

    def test_index_md_overwritten_on_subsequent_sync(self, tmp_path: Path, monkeypatch):
        """A second sync overwrites INDEX.md rather than appending."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts(tmp_path)
        create_mpga_db(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        runner.invoke(sync_cmd, [])

        # Corrupt the file, then sync again
        (tmp_path / "INDEX.md").write_text("CORRUPTED DATA\n")
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0, result.output

        content = (tmp_path / "INDEX.md").read_text()
        assert "CORRUPTED DATA" not in content, "second sync should overwrite INDEX.md"
