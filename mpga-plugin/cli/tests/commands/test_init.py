"""Tests for the init, config, status, and health commands."""

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from tests.conftest import write_file
from mpga.db.connection import get_connection
from mpga.db.schema import create_schema

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def seed_mpga_project(root: Path, *, scopes: list[str] | None = None, index_content: str | None = None):
    """Seed a minimal MPGA structure so commands that expect an initialized project work."""
    mpga = root / "MPGA"
    dot_mpga = root / ".mpga"
    scopes_dir = mpga / "scopes"
    board_dir = mpga / "board"
    tasks_dir = board_dir / "tasks"

    scopes_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)
    dot_mpga.mkdir(parents=True, exist_ok=True)
    (mpga / "milestones").mkdir(parents=True, exist_ok=True)
    (mpga / "sessions").mkdir(parents=True, exist_ok=True)

    # Config — write to .mpga/ (where load_config looks first)
    config = {
        "version": "1.0.0",
        "project": {
            "name": "test-project",
            "languages": ["typescript"],
            "entryPoints": [],
            "ignore": [],
        },
        "evidence": {
            "strategy": "hybrid",
            "lineRanges": True,
            "astAnchors": True,
            "autoHeal": True,
            "coverageThreshold": 0.2,
        },
        "drift": {"ciThreshold": 80, "hookMode": "quick", "autoSync": False},
    }
    write_file(dot_mpga, "mpga.config.json", json.dumps(config, indent=2) + "\n")
    # Also write to legacy MPGA/ location for tests that check that path
    write_file(mpga, "mpga.config.json", json.dumps(config, indent=2) + "\n")

    # INDEX.md
    if index_content is None:
        index_content = (
            "# Project: test-project\n\n"
            "## Identity\n"
            "- **Last sync:** 2026-01-15T10:00:00Z\n"
            "- **Evidence coverage:** 45%\n"
        )
    write_file(mpga, "INDEX.md", index_content)

    # GRAPH.md
    write_file(mpga, "GRAPH.md", "# Dependency graph\n")

    # Board
    board = {
        "version": "1.0.0",
        "milestone": None,
        "updated": "2026-01-01T00:00:00.000Z",
        "columns": {
            "backlog": [],
            "todo": [],
            "in-progress": [],
            "testing": [],
            "review": [],
            "done": [],
        },
        "stats": {
            "total": 0,
            "done": 0,
            "in_flight": 0,
            "blocked": 0,
            "progress_pct": 0,
            "evidence_produced": 0,
            "evidence_expected": 0,
        },
        "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
        "next_task_id": 1,
    }
    write_file(board_dir, "board.json", json.dumps(board, indent=2) + "\n")
    write_file(board_dir, "BOARD.md", "# Board\n\nNo tasks yet.\n")

    # Create SQLite DB so status/health commands can find the project
    db_path = dot_mpga / "mpga.db"
    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        # Add a file_info row so lastSync is populated from the INDEX.md timestamp
        conn.execute(
            "INSERT INTO file_info (filepath, language, lines, size, content_hash, last_scanned) VALUES (?, ?, ?, ?, ?, ?)",
            ("MPGA/INDEX.md", "markdown", 5, 120, "abc", "2026-01-15T10:00:00Z"),
        )
        conn.commit()
        # Seed scope rows if requested
        if scopes:
            from mpga.db.repos.scopes import Scope, ScopeRepo
            scope_repo = ScopeRepo(conn)
            for scope in scopes:
                scope_repo.create(Scope(id=scope, name=scope, summary=f"{scope} scope", content=f"# Scope: {scope}\n\n- **Health:** ok\n"))
    finally:
        conn.close()

    # Optional scope files
    if scopes:
        for scope in scopes:
            write_file(scopes_dir, f"{scope}.md", f"# Scope: {scope}\n\n- **Health:** ok\n")


# ---------------------------------------------------------------------------
# Tests: init command
# ---------------------------------------------------------------------------

class TestRegisterInit:
    """registerInit -- the GREATEST init command in history."""

    def test_creates_mpga_dot_dir_only(self, tmp_path: Path, monkeypatch):
        """Creates only .mpga/ — no legacy MPGA/ folder."""
        monkeypatch.chdir(tmp_path)
        from mpga.commands.init import init_cmd

        runner = CliRunner()
        result = runner.invoke(init_cmd, [])
        assert result.exit_code == 0

        assert (tmp_path / ".mpga").is_dir()
        # Legacy MPGA/ folder must NOT be created
        assert not (tmp_path / "MPGA").exists()

    def test_creates_sqlite_db_with_schema(self, tmp_path: Path, monkeypatch):
        """Creates .mpga/mpga.db and initializes the schema."""
        monkeypatch.chdir(tmp_path)
        from mpga.commands.init import init_cmd

        runner = CliRunner()
        result = runner.invoke(init_cmd, [])
        assert result.exit_code == 0

        db_path = tmp_path / ".mpga" / "mpga.db"
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute("SELECT version FROM schema_version").fetchone()
        finally:
            conn.close()

        assert row == (1,)

    def test_creates_config_json_in_dot_mpga(self, tmp_path: Path, monkeypatch):
        """Creates mpga.config.json inside .mpga/ (not MPGA/)."""
        monkeypatch.chdir(tmp_path)
        from mpga.commands.init import init_cmd

        runner = CliRunner()
        result = runner.invoke(init_cmd, [])
        assert result.exit_code == 0

        config_path = tmp_path / ".mpga" / "mpga.config.json"
        assert config_path.exists()

        config = json.loads(config_path.read_text())
        assert config["version"] == "1.0.0"
        assert config["project"]["name"] == tmp_path.name
        assert config["evidence"]["strategy"] == "hybrid"
        assert config["drift"]["ciThreshold"] == 80

    def test_does_not_create_markdown_files(self, tmp_path: Path, monkeypatch):
        """Does not create any Markdown files (INDEX.md, GRAPH.md, BOARD.md)."""
        monkeypatch.chdir(tmp_path)
        from mpga.commands.init import init_cmd

        runner = CliRunner()
        result = runner.invoke(init_cmd, [])
        assert result.exit_code == 0

        assert not (tmp_path / "MPGA" / "INDEX.md").exists()
        assert not (tmp_path / "MPGA" / "GRAPH.md").exists()
        assert not (tmp_path / "MPGA" / "board" / "BOARD.md").exists()
        assert not (tmp_path / "MPGA" / "board" / "board.json").exists()

    def test_does_not_overwrite_if_already_initialized(self, tmp_path: Path, monkeypatch):
        """Does not overwrite if .mpga/mpga.db already exists."""
        monkeypatch.chdir(tmp_path)
        # Pre-create the db file
        dot_mpga = tmp_path / ".mpga"
        dot_mpga.mkdir(parents=True, exist_ok=True)
        (dot_mpga / "mpga.db").write_bytes(b"")

        from mpga.commands.init import init_cmd

        runner = CliRunner()
        result = runner.invoke(init_cmd, [])
        assert result.exit_code == 0
        assert "already initialized" in result.output

    def test_from_existing_detects_project_type(self, tmp_path: Path, monkeypatch):
        """--from-existing detects project type via scanner and saves to .mpga/."""
        monkeypatch.chdir(tmp_path)

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export function main() {}\n")

        from mpga.commands.init import init_cmd

        runner = CliRunner()
        result = runner.invoke(init_cmd, ["--from-existing"])
        assert result.exit_code == 0

        config_path = tmp_path / ".mpga" / "mpga.config.json"
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert isinstance(config["project"]["languages"], list)


# ---------------------------------------------------------------------------
# Tests: config command
# ---------------------------------------------------------------------------

class TestRegisterConfig:
    """registerConfig -- total CONTROL over your project."""

    def test_config_show_json(self, tmp_path: Path, monkeypatch):
        """config show --json outputs valid JSON."""
        seed_mpga_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.config_cmd import config_show

        runner = CliRunner()
        result = runner.invoke(config_show, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["project"]["name"] == "test-project"
        assert parsed["version"] == "1.0.0"

    def test_config_show_kv(self, tmp_path: Path, monkeypatch):
        """config show without --json outputs key-value lines."""
        seed_mpga_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.config_cmd import config_show

        runner = CliRunner()
        result = runner.invoke(config_show, [])
        assert result.exit_code == 0
        assert "project.name" in result.output

    def test_config_set_numeric(self, tmp_path: Path, monkeypatch):
        """config set updates a numeric config value."""
        seed_mpga_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.config_cmd import config_set

        runner = CliRunner()
        result = runner.invoke(config_set, ["drift.ciThreshold", "90"])
        assert result.exit_code == 0

        config_path = tmp_path / ".mpga" / "mpga.config.json"
        config = json.loads(config_path.read_text())
        assert config["drift"]["ciThreshold"] == 90

    def test_config_set_unknown_key_errors(self, tmp_path: Path, monkeypatch):
        """config set exits with error for unknown key."""
        seed_mpga_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.config_cmd import config_set

        runner = CliRunner()
        result = runner.invoke(config_set, ["nonexistent.key", "val"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests: status command
# ---------------------------------------------------------------------------

class TestRegisterStatus:
    """registerStatus -- the BEST status reports."""

    def test_exits_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """Exits with error when MPGA is not initialized."""
        monkeypatch.chdir(tmp_path)

        from mpga.commands.status import status_cmd

        runner = CliRunner()
        result = runner.invoke(status_cmd, [])
        assert result.exit_code != 0

    def test_json_returns_correct_structure(self, tmp_path: Path, monkeypatch):
        """--json returns correct structure."""
        seed_mpga_project(tmp_path, scopes=["core", "auth"])
        monkeypatch.chdir(tmp_path)

        from mpga.commands.status import status_cmd

        runner = CliRunner()
        result = runner.invoke(status_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["initialized"] is True
        assert parsed["lastSync"] == "2026-01-15T10:00:00Z"
        assert parsed["evidenceCoverage"].endswith("%")
        assert parsed["scopes"] == 2
        assert parsed["config"]["name"] == "test-project"
        assert "board" in parsed

    def test_json_zero_scopes(self, tmp_path: Path, monkeypatch):
        """--json returns zero scopes when none exist."""
        seed_mpga_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        from mpga.commands.status import status_cmd

        runner = CliRunner()
        result = runner.invoke(status_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["scopes"] == 0


# ---------------------------------------------------------------------------
# Tests: health command
# ---------------------------------------------------------------------------

class TestRegisterHealth:
    """registerHealth -- keeping our project in PERFECT health."""

    def test_exits_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """Exits with error when MPGA is not initialized."""
        monkeypatch.chdir(tmp_path)

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        result = runner.invoke(health_cmd, [])
        assert result.exit_code != 0

    def test_json_returns_correct_health_report(self, tmp_path: Path, monkeypatch):
        """--json returns correct health report."""
        seed_mpga_project(tmp_path, scopes=["core", "utils"])
        monkeypatch.chdir(tmp_path)

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        result = runner.invoke(health_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["initialized"] is True
        assert isinstance(parsed["evidenceHealth"], (int, float))
        assert isinstance(parsed["ciPass"], bool)
        assert parsed["scopes"] == 2
        assert "board" in parsed
        assert parsed["lastSync"] == "2026-01-15T10:00:00Z"
        assert "overallGrade" in parsed
        assert parsed["overallGrade"] in ("A", "B", "C", "D")

    def test_json_grade_a_for_100_percent(self, tmp_path: Path, monkeypatch):
        """--json includes correct grade for 100% health."""
        seed_mpga_project(tmp_path)
        monkeypatch.chdir(tmp_path)

        # Mock drift check to return 100% health
        from mpga.evidence.drift import DriftReport

        mock_report = DriftReport(
            timestamp="2026-01-01T00:00:00Z",
            project_root=str(tmp_path),
            overall_health_pct=100,
            ci_pass=True,
            scopes=[],
            total_links=0,
            valid_links=0,
            ci_threshold=80,
        )
        monkeypatch.setattr("mpga.commands.health.run_drift_check", lambda *a, **kw: mock_report)

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        result = runner.invoke(health_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["overallGrade"] == "A"

    def test_json_last_sync_never(self, tmp_path: Path, monkeypatch):
        """--json reports lastSync as 'never' when INDEX.md has placeholder."""
        seed_mpga_project(
            tmp_path,
            index_content="# Project: test\n\n- **Last sync:** (run `mpga sync` to populate)\n",
        )
        monkeypatch.chdir(tmp_path)

        from mpga.commands.health import health_cmd

        runner = CliRunner()
        result = runner.invoke(health_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert parsed["lastSync"] == "never"
