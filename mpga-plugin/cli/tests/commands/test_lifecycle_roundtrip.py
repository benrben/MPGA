"""Integration test for the SQLite/web/export lifecycle round-trip."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner


class TestLifecycleRoundTrip:
    def test_init_sync_board_search_export_round_trip(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text(
            "export function main(): void {\n  console.log('hello mpga');\n}\n",
            encoding="utf-8",
        )

        from mpga.commands.init import init_cmd
        from mpga.commands.sync import sync_cmd
        from mpga.commands.board_cmd import board
        from mpga.commands.search import search_cmd
        from mpga.commands.export_cmd import export_cmd

        runner = CliRunner()

        result = runner.invoke(init_cmd, ["--from-existing"])
        assert result.exit_code == 0

        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0

        result = runner.invoke(board, ["add", "Round trip task", "--column", "todo", "--priority", "high"])
        assert result.exit_code == 0

        result = runner.invoke(search_cmd, ["round"])
        assert result.exit_code == 0
        assert "Round trip task" in result.output

        result = runner.invoke(export_cmd, ["--opencode"])
        assert result.exit_code == 0

        db_path = tmp_path / ".mpga" / "mpga.db"
        assert db_path.exists()

        snapshots_dir = tmp_path / ".mpga" / "snapshots"
        assert (snapshots_dir / "tasks.md").exists()
        assert "Round trip task" in (snapshots_dir / "tasks.md").read_text(encoding="utf-8")

        result = runner.invoke(board, ["show", "--json"])
        assert result.exit_code == 0
        assert "Round trip task" in result.output
