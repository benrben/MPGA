"""Tests for the scan, sync, graph, and scope commands."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.conftest import write_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_mpga_structure(root: Path) -> None:
    """Create MPGA/scopes/ directory."""
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
        """sync creates GRAPH.md, scopes, and INDEX.md."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_sample_ts_files(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.sync import sync_cmd

        runner = CliRunner()
        result = runner.invoke(sync_cmd, [])
        assert result.exit_code == 0

        mpga_dir = tmp_path / "MPGA"
        assert (mpga_dir / "GRAPH.md").exists()
        assert (mpga_dir / "INDEX.md").exists()

        graph_content = (mpga_dir / "GRAPH.md").read_text()
        assert "Dependency graph" in graph_content

        index_content = (mpga_dir / "INDEX.md").read_text()
        assert "test-project" in index_content

        scopes_dir = mpga_dir / "scopes"
        assert scopes_dir.exists()
        scope_files = list(scopes_dir.glob("*.md"))
        assert len(scope_files) >= 1

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
        """graph show prints GRAPH.md content."""
        monkeypatch.chdir(tmp_path)
        write_config(tmp_path)
        write_graph_md(tmp_path)

        from mpga.commands.graph import graph_show

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


# ---------------------------------------------------------------------------
# Tests: scope command
# ---------------------------------------------------------------------------

class TestScopeCommand:
    """scope command tests."""

    def test_scope_add_creates_file(self, tmp_path: Path, monkeypatch):
        """scope add creates a new scope markdown file."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)

        from mpga.commands.scope import scope_add

        runner = CliRunner()
        result = runner.invoke(scope_add, ["my-new-scope"])
        assert result.exit_code == 0

        scope_path = tmp_path / "MPGA" / "scopes" / "my-new-scope.md"
        assert scope_path.exists()
        content = scope_path.read_text()
        assert "# Scope: my-new-scope" in content
        assert "## Summary" in content
        assert "## Evidence index" in content

    def test_scope_add_errors_when_exists(self, tmp_path: Path, monkeypatch):
        """scope add errors when scope already exists."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(tmp_path, "existing-scope")

        from mpga.commands.scope import scope_add

        runner = CliRunner()
        result = runner.invoke(scope_add, ["existing-scope"])
        assert result.exit_code != 0

    def test_scope_remove_archives(self, tmp_path: Path, monkeypatch):
        """scope remove archives a scope file."""
        monkeypatch.chdir(tmp_path)
        create_mpga_structure(tmp_path)
        write_scope_file(tmp_path, "to-remove")
        # Ensure the milestones dir exists for archiving
        (tmp_path / "MPGA" / "milestones").mkdir(parents=True, exist_ok=True)

        scope_path = tmp_path / "MPGA" / "scopes" / "to-remove.md"
        assert scope_path.exists()

        from mpga.commands.scope import scope_remove

        runner = CliRunner()
        result = runner.invoke(scope_remove, ["to-remove"])
        assert result.exit_code == 0

        assert not scope_path.exists()

        archive_dir = tmp_path / "MPGA" / "milestones" / "_archived-scopes"
        assert archive_dir.exists()
        archived = list(archive_dir.iterdir())
        assert len(archived) == 1
        assert archived[0].name.startswith("to-remove-")
        assert archived[0].name.endswith(".md")

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
