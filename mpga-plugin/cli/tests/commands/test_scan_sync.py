"""Tests for the scan, sync, graph, and scope commands."""

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from tests.conftest import write_file

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_mpga_structure(root: Path) -> None:
    """Create .mpga/mpga.db and MPGA/scopes/ directory."""
    import sqlite3
    from mpga.db.schema import create_schema
    dot_mpga = root / ".mpga"
    dot_mpga.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dot_mpga / "mpga.db"))
    create_schema(conn)
    conn.close()
    (root / "MPGA" / "scopes").mkdir(parents=True, exist_ok=True)


def write_config(root: Path) -> None:
    """Write a minimal mpga.config.json."""
    config = {
        "version": "1.0.0",
        "project": {
            "name": "test-project",
            "languages": ["typescript"],
            "entryPoints": [],
            "ignore": ["node_modules", "dist", ".git", "MPGA/"],
        },
    }
    write_file(root, "mpga.config.json", json.dumps(config, indent=2))


def write_sample_ts_files(root: Path) -> None:
    """Write sample TypeScript source files."""
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "index.ts").write_text(
        "export function main(): void {\n  console.log('hello');\n}\n"
    )
    (src_dir / "utils.ts").write_text(
        "export function add(a: number, b: number): number {\n  return a + b;\n}\n"
    )


def write_graph_md(root: Path) -> None:
    """Write a minimal GRAPH.md."""
    mpga_dir = root / "MPGA"
    mpga_dir.mkdir(parents=True, exist_ok=True)
    (mpga_dir / "GRAPH.md").write_text(
        "# Dependency graph\n\n## Module dependencies\n\n(no inter-module dependencies detected)\n"
    )


def write_scope_file(root: Path, name: str, content: str | None = None) -> None:
    """Write a scope file under MPGA/scopes/."""
    scopes_dir = root / "MPGA" / "scopes"
    scopes_dir.mkdir(parents=True, exist_ok=True)
    if content is None:
        content = (
            f"# Scope: {name}\n\n## Summary\nTest scope\n\n"
            f"## Confidence and notes\n- **Health:** fresh\n- **Last verified:** 2026-01-01\n"
        )
    (scopes_dir / f"{name}.md").write_text(content)


# ---------------------------------------------------------------------------
# Tests: scan command
# ---------------------------------------------------------------------------

class TestScanCommand:
    """scan command tests."""

    def test_scan_json_returns_valid_result(self, tmp_path: Path, monkeypatch):
        """scan --json returns valid ScanResult JSON with files and languages."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts_files(tmp_path)

        from mpga.commands.scan import scan_cmd

        runner = CliRunner()
        result = runner.invoke(scan_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        assert "files" in parsed
        assert "total_files" in parsed or "totalFiles" in parsed
        assert "total_lines" in parsed or "totalLines" in parsed
        assert "languages" in parsed

    def test_scan_finds_typescript_files(self, tmp_path: Path, monkeypatch):
        """scan finds TypeScript files in temp directory."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts_files(tmp_path)

        from mpga.commands.scan import scan_cmd

        runner = CliRunner()
        result = runner.invoke(scan_cmd, ["--json"])
        assert result.exit_code == 0

        parsed = json.loads(result.output)
        # The JSON uses dataclass field names (snake_case)
        files = parsed.get("files", [])
        ts_files = [f for f in files if f.get("language") == "typescript"]
        assert len(ts_files) >= 2
        file_paths = [f["filepath"] for f in ts_files]
        assert "src/index.ts" in file_paths
        assert "src/utils.ts" in file_paths


# ---------------------------------------------------------------------------
# Tests: sync command
# ---------------------------------------------------------------------------

class TestSyncCommand:
    """sync command tests."""

    def test_sync_creates_graph_scopes_and_index(self, tmp_path: Path, monkeypatch):
        """sync populates graph, scopes, and file_info into SQLite."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts_files(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0

        db_path = tmp_path / ".mpga" / "mpga.db"
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        try:
            file_count = conn.execute("SELECT COUNT(*) FROM file_info").fetchone()[0]
            scope_count = conn.execute("SELECT COUNT(*) FROM scopes").fetchone()[0]
        finally:
            conn.close()

        assert file_count >= 2
        assert scope_count >= 1

    def test_sync_populates_sqlite_mirror(self, tmp_path: Path, monkeypatch):
        """sync mirrors scanned files, graph, and scopes into SQLite."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts_files(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0

        db_path = tmp_path / ".mpga" / "mpga.db"
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        try:
            file_count = conn.execute("SELECT COUNT(*) FROM file_info").fetchone()[0]
            scope_count = conn.execute("SELECT COUNT(*) FROM scopes").fetchone()[0]
            global_rows = conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]
            symbol_rows = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
        finally:
            conn.close()

        assert file_count >= 2
        assert scope_count >= 1
        assert global_rows >= scope_count
        assert symbol_rows >= 2

    def test_sync_errors_when_not_initialized(self, tmp_path: Path, monkeypatch):
        """sync errors when MPGA not initialized."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Tests: graph command
# ---------------------------------------------------------------------------

class TestGraphCommand:
    """graph command tests."""

    def test_graph_show_prints_content(self, tmp_path: Path, monkeypatch):
        """graph show prints dependency graph from SQLite."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)

        from mpga.commands.graph import graph_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.graph import GraphRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        repo = GraphRepo(conn)
        repo.add_edge("src/index.ts", "src/utils.ts")
        conn.close()

        runner = CliRunner()
        result = runner.invoke(graph_show, [])
        assert result.exit_code == 0
        assert "Dependency graph" in result.output
        assert "Module dependencies" in result.output

    def test_graph_show_errors_when_missing(self, tmp_path: Path, monkeypatch):
        """graph show errors when GRAPH.md does not exist."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)

        from mpga.commands.graph import graph_show

        runner = CliRunner()
        result = runner.invoke(graph_show, [])
        assert result.exit_code != 0

    def test_graph_show_reads_sqlite_edges_when_graph_md_is_missing(self, tmp_path: Path, monkeypatch):
        """graph show falls back to the SQLite graph mirror."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)

        from mpga.commands.graph import graph_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.graph import GraphRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        repo = GraphRepo(conn)
        repo.add_edge("src/index.ts", "src/utils.ts")
        conn.close()

        runner = CliRunner()
        result = runner.invoke(graph_show, [])
        assert result.exit_code == 0
        assert "src/index.ts" in result.output
        assert "src/utils.ts" in result.output


# ---------------------------------------------------------------------------
# Tests: scope command
# ---------------------------------------------------------------------------

class TestScopeCommand:
    """scope command tests."""

    def test_scope_show_uses_compressed_sqlite_summary_by_default(self, tmp_path: Path, monkeypatch):
        """scope show prints the compressed SQLite summary by default."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(
            tmp_path,
            "mpga",
            "# Scope: mpga\n\n## Summary\nFile copy that should not be shown by default.\n",
        )

        from mpga.commands.scope import scope_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(
            Scope(
                id="mpga",
                name="mpga",
                summary="SQLite summary paragraph.\n\nSecond paragraph that should stay hidden.",
                content=(
                    "# Scope: mpga\n\n## Summary\nSQLite summary paragraph.\n\n"
                    "## Details\nDeep implementation detail that should only appear with --full.\n"
                ),
                status="fresh",
                evidence_total=8,
                evidence_valid=7,
                last_verified="2026-03-30",
            )
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_show, ["mpga"])
        assert result.exit_code == 0
        assert "SQLite summary paragraph." in result.output
        assert "Health: fresh (7/8)" in result.output
        assert "Deep implementation detail" not in result.output
        assert "File copy that should not be shown" not in result.output

    def test_scope_show_full_prints_complete_scope_content(self, tmp_path: Path, monkeypatch):
        """scope show --full prints the complete scope content."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(tmp_path, "mpga")

        from mpga.commands.scope import scope_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.db.schema import create_schema

        full_content = (
            "# Scope: mpga\n\n## Summary\nSQLite summary paragraph.\n\n"
            "## Details\nDeep implementation detail visible in full output.\n"
        )

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(
            Scope(
                id="mpga",
                name="mpga",
                summary="SQLite summary paragraph.",
                content=full_content,
                status="fresh",
                evidence_total=2,
                evidence_valid=2,
                last_verified="2026-03-30",
            )
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_show, ["mpga", "--full"])
        assert result.exit_code == 0
        assert "## Details" in result.output
        assert "Deep implementation detail visible in full output." in result.output

    def test_scope_show_query_returns_only_matching_scope_snippets(self, tmp_path: Path, monkeypatch):
        """scope show --query restricts results to the requested scope."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(tmp_path, "mpga")

        from mpga.commands.scope import scope_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        repo = ScopeRepo(conn)
        repo.create(
            Scope(
                id="mpga",
                name="mpga",
                summary="Primary scope",
                content="Sync keeps the SQLite mirror fresh after every command.",
                status="fresh",
            )
        )
        repo.create(
            Scope(
                id="other",
                name="other",
                summary="Secondary scope",
                content="Sync also appears here, but this scope should not be shown.",
                status="fresh",
            )
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_show, ["mpga", "--query", "sync"])
        assert result.exit_code == 0
        assert "Scope search in mpga" in result.output
        assert "[Sync]" in result.output or "[sync]" in result.output
        assert "other" not in result.output
        assert "Health: fresh" not in result.output

    def test_scope_add_creates_file(self, tmp_path: Path, monkeypatch):
        """scope add creates a new scope DB row with correct content."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.scope import scope_add

        runner = CliRunner()
        result = runner.invoke(scope_add, ["my-new-scope"])
        assert result.exit_code == 0

        conn = sqlite3.connect(tmp_path / ".mpga" / "mpga.db")
        try:
            row = conn.execute(
                "SELECT id, name, content FROM scopes WHERE id = 'my-new-scope'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None
        scope_id, scope_name, content = row
        assert scope_id == "my-new-scope"
        assert scope_name == "my-new-scope"
        assert "# Scope: my-new-scope" in content
        assert "## Summary" in content
        assert "## Evidence index" in content

    def test_scope_add_updates_sqlite_when_present(self, tmp_path: Path, monkeypatch):
        """scope add mirrors the new scope into SQLite when the DB exists."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.commands.scope import scope_add

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_add, ["my-new-scope"])
        assert result.exit_code == 0

        conn = sqlite3.connect(tmp_path / ".mpga" / "mpga.db")
        try:
            row = conn.execute(
                "SELECT id, name FROM scopes WHERE id = 'my-new-scope'"
            ).fetchone()
        finally:
            conn.close()

        assert row == ("my-new-scope", "my-new-scope")

    def test_scope_add_errors_when_exists(self, tmp_path: Path, monkeypatch):
        """scope add errors when scope already exists in DB."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.repos.scopes import Scope, ScopeRepo

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(Scope(id="existing-scope", name="existing-scope", summary="exists"))
        conn.close()

        from mpga.commands.scope import scope_add

        runner = CliRunner()
        result = runner.invoke(scope_add, ["existing-scope"])
        assert result.exit_code != 0

    def test_scope_remove_archives(self, tmp_path: Path, monkeypatch):
        """scope remove deletes the scope from DB."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.repos.scopes import Scope, ScopeRepo

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(Scope(id="to-remove", name="to-remove", summary="test"))
        conn.close()

        from mpga.commands.scope import scope_remove

        runner = CliRunner()
        result = runner.invoke(scope_remove, ["to-remove"])
        assert result.exit_code == 0

        conn = sqlite3.connect(tmp_path / ".mpga" / "mpga.db")
        try:
            row = conn.execute(
                "SELECT id FROM scopes WHERE id = 'to-remove'"
            ).fetchone()
        finally:
            conn.close()

        assert row is None

    def test_scope_remove_deletes_sqlite_row_when_present(self, tmp_path: Path, monkeypatch):
        """scope remove deletes the mirrored SQLite scope row."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(tmp_path, "to-remove")
        (tmp_path / "MPGA" / "milestones").mkdir(parents=True, exist_ok=True)

        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.commands.scope import scope_remove

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(Scope(id="to-remove", name="to-remove", summary="test"))
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_remove, ["to-remove"])
        assert result.exit_code == 0

        conn = sqlite3.connect(tmp_path / ".mpga" / "mpga.db")
        try:
            row = conn.execute(
                "SELECT id FROM scopes WHERE id = 'to-remove'"
            ).fetchone()
        finally:
            conn.close()

        assert row is None

    def test_scope_list_shows_scopes(self, tmp_path: Path, monkeypatch):
        """scope list shows scopes without crashing."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(tmp_path, "alpha")
        write_scope_file(tmp_path, "beta")

        from mpga.commands.scope import scope_list

        runner = CliRunner()
        result = runner.invoke(scope_list, [])
        assert result.exit_code == 0

    def test_scope_show_defaults_to_compressed_sqlite_summary(self, tmp_path: Path, monkeypatch):
        """scope show prefers the SQLite scope row and compresses by default."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.scope import scope_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(
            Scope(
                id="mpga",
                name="mpga",
                summary="First paragraph from SQLite.\n\nSecond paragraph from SQLite.",
                content=(
                    "# Scope: mpga\n\n## Summary\n"
                    "First paragraph from SQLite.\n\n"
                    "Second paragraph from SQLite."
                ),
                status="fresh",
                evidence_total=9,
                evidence_valid=8,
            )
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_show, ["mpga"])
        assert result.exit_code == 0
        assert "First paragraph from SQLite." in result.output
        assert "Health: fresh (8/9)" in result.output
        assert "Second paragraph from SQLite." not in result.output

    def test_scope_show_full_prints_complete_content(self, tmp_path: Path, monkeypatch):
        """scope show --full prints the complete scope document."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.scope import scope_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(
            Scope(
                id="mpga",
                name="mpga",
                summary="Short summary.",
                content=(
                    "# Scope: mpga\n\n## Summary\n"
                    "First paragraph from SQLite.\n\n"
                    "Second paragraph from SQLite."
                ),
                status="fresh",
                evidence_total=9,
                evidence_valid=8,
            )
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_show, ["mpga", "--full"])
        assert result.exit_code == 0
        assert "# Scope: mpga" in result.output
        assert "Second paragraph from SQLite." in result.output

    def test_scope_show_query_only_prints_matching_paragraphs(self, tmp_path: Path, monkeypatch):
        """scope show --query narrows output to matching paragraphs for the selected scope."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.scope import scope_show
        from mpga.db.connection import get_connection
        from mpga.db.repos.scopes import Scope, ScopeRepo
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        ScopeRepo(conn).create(
            Scope(
                id="mpga",
                name="mpga",
                summary="SQLite summary.",
                content=(
                    "# Scope: mpga\n\n## Summary\n"
                    "Sync refreshes the SQLite mirror for scopes.\n\n"
                    "Board live rendering stays separate from the sync pipeline."
                ),
                status="fresh",
                evidence_total=9,
                evidence_valid=8,
            )
        )
        conn.close()

        runner = CliRunner()
        result = runner.invoke(scope_show, ["mpga", "--query", "sync"])
        assert result.exit_code == 0
        assert "Sync refreshes the SQLite mirror for scopes." in result.output
        assert "Board live rendering stays separate" not in result.output
