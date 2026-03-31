"""Tests for SQLite snapshot export and routing rule injection."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


def _seed_db(db_path: Path) -> None:
    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        conn.execute(
            "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("T001", "Export snapshots", "body", "todo", "high", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO scopes (id, name, summary, status, evidence_total, evidence_valid, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("scope-a", "scope-a", "A scope", "fresh", 1, 1, "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO evidence (raw, type, filepath) VALUES (?, ?, ?)",
            ("[E] src/app.py:1-2", "valid", "src/app.py"),
        )
        conn.execute(
            "INSERT INTO milestones (id, name, status, created_at) VALUES (?, ?, ?, ?)",
            ("M001", "Milestone", "active", "2026-01-01"),
        )
        conn.commit()
    finally:
        conn.close()


class TestExportSnapshots:
    def test_writes_markdown_snapshots_from_sqlite(self, tmp_path: Path):
        db_path = tmp_path / ".mpga" / "mpga.db"
        (tmp_path / "MPGA").mkdir(parents=True, exist_ok=True)
        _seed_db(db_path)

        from mpga.commands.export.snapshots import write_sqlite_snapshots

        snapshots_dir = Path(write_sqlite_snapshots(str(tmp_path), str(db_path)))

        assert (snapshots_dir / "tasks.md").exists()
        assert (snapshots_dir / "scopes.md").exists()
        assert (snapshots_dir / "evidence.md").exists()
        assert (snapshots_dir / "milestones.md").exists()
        assert (snapshots_dir / "stats.md").exists()

        assert "T001" in (snapshots_dir / "tasks.md").read_text(encoding="utf-8")
        assert "scope-a" in (snapshots_dir / "scopes.md").read_text(encoding="utf-8")

    def test_export_command_generates_snapshots_when_db_exists(self, tmp_path: Path, monkeypatch):
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)
        (mpga_dir / "INDEX.md").write_text("# INDEX\n", encoding="utf-8")
        (mpga_dir / "mpga.config.json").write_text(
            '{"version":"1.0.0","project":{"name":"proj","languages":[],"entryPoints":[],"ignore":[]}}',
            encoding="utf-8",
        )
        _seed_db(tmp_path / ".mpga" / "mpga.db")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("mpga.commands.export_cmd.find_project_root", lambda: tmp_path)
        monkeypatch.setattr("mpga.commands.export_cmd.export_claude", lambda *args, **kwargs: None)
        monkeypatch.setattr("mpga.commands.export_cmd.find_plugin_root", lambda: None)

        from mpga.commands.export_cmd import export_cmd

        runner = CliRunner()
        result = runner.invoke(export_cmd, ["--claude"])
        assert result.exit_code == 0
        assert (tmp_path / ".mpga" / "snapshots" / "tasks.md").exists()


class TestRoutingInjection:
    def test_claude_export_mentions_spa_and_api_routing(self):
        from mpga.commands.export.claude import _generate_claude_md

        content = _generate_claude_md("# INDEX", "proj")
        assert "/api/*" in content
        assert "SPA shell" in content
        assert "mpga serve" in content

    def test_cursor_export_mentions_spa_and_api_routing(self):
        from mpga.commands.export.cursor import _generate_cursor_project_mdc

        content = _generate_cursor_project_mdc("# INDEX", "proj", "mpga")
        assert "/api/*" in content
        assert "SPA shell" in content
        assert "mpga serve" in content

    def test_codex_export_mentions_spa_and_api_routing(self):
        from mpga.commands.export.codex import _generate_agents_md

        content = _generate_agents_md("# INDEX", "proj", "mpga")
        assert "/api/*" in content
        assert "SPA shell" in content
        assert "serve" in content
