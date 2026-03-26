"""Tests for the Cursor export module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mpga.commands.export.agents import AgentMeta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_AGENTS = [
    AgentMeta(
        slug="test-agent",
        name="mpga-test-agent",
        description="A test agent",
        model="claude-sonnet-4-6",
        readonly=False,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="scout",
        name="mpga-scout",
        description="Read-only scout",
        model="claude-sonnet-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
]


def setup_mocks(monkeypatch):
    """Set up common mocks for cursor export tests."""
    mock_copy = MagicMock()
    mock_read_instructions = MagicMock(
        side_effect=lambda _pr, slug, cli=None: f"Instructions for {slug}\n\n{cli or 'mpga'} sync"
    )

    monkeypatch.setattr("mpga.commands.export.cursor.AGENTS", MOCK_AGENTS)
    monkeypatch.setattr("mpga.commands.export.cursor.SKILL_NAMES", ["sync-project", "plan"])
    monkeypatch.setattr("mpga.commands.export.cursor.copy_skills_to", mock_copy)
    monkeypatch.setattr("mpga.commands.export.cursor.read_agent_instructions", mock_read_instructions)

    return mock_copy, mock_read_instructions


# ---------------------------------------------------------------------------
# Tests: project-level export
# ---------------------------------------------------------------------------

class TestCursorProjectLevel:
    """exportCursor project-level (isGlobal = false) tests."""

    def test_creates_rules_directory(self, tmp_path: Path, monkeypatch):
        """Creates .cursor/rules directory."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n\n## Active milestone\nM001-alpha\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        assert (tmp_path / ".cursor" / "rules").is_dir()

    def test_writes_4_mdc_rule_files(self, tmp_path: Path, monkeypatch):
        """Writes 4 MDC rule files."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n\n## Active milestone\nM001-alpha\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        rules_dir = tmp_path / ".cursor" / "rules"
        rule_files = list(rules_dir.glob("*.mdc"))
        assert len(rule_files) == 4

    def test_project_mdc_contains_milestone(self, tmp_path: Path, monkeypatch):
        """Generates mpga-project.mdc with YAML frontmatter and milestone."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n\n## Active milestone\nM001-alpha\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-project.mdc").read_text()
        assert "alwaysApply: true" in content
        assert "MPGA Project Context" in content
        assert "M001-alpha" in content
        assert "@MPGA/INDEX.md" in content

    def test_evidence_mdc_content(self, tmp_path: Path, monkeypatch):
        """Generates mpga-evidence.mdc with evidence protocol."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-evidence.mdc").read_text()
        assert "Evidence Link Protocol" in content
        assert "[E]" in content
        assert "[Unknown]" in content
        assert "[Stale:" in content
        assert "./.mpga-runtime/bin/mpga.sh evidence verify" in content

    def test_tdd_mdc_content(self, tmp_path: Path, monkeypatch):
        """Generates mpga-tdd.mdc with TDD enforcement."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-tdd.mdc").read_text()
        assert "TDD Protocol (mandatory)" in content
        assert "WRITE FAILING TEST FIRST" in content

    def test_scopes_mdc_no_scopes_fallback(self, tmp_path: Path, monkeypatch):
        """Generates mpga-scopes.mdc with 'no scopes' fallback when dir missing."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-scopes.mdc").read_text()
        assert "MPGA Scope Lookup" in content
        assert "no scopes yet" in content

    def test_scopes_mdc_lists_existing(self, tmp_path: Path, monkeypatch):
        """Generates mpga-scopes.mdc listing existing scope files."""
        setup_mocks(monkeypatch)
        scopes_dir = tmp_path / "MPGA" / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "core.md").write_text("# Core\n")
        (scopes_dir / "board.md").write_text("# Board\n")

        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-scopes.mdc").read_text()
        assert "core" in content
        assert "board" in content
        assert "@MPGA/scopes/core.md" in content
        assert "@MPGA/scopes/board.md" in content

    def test_copies_skills(self, tmp_path: Path, monkeypatch):
        """Copies skills to .cursor/skills/."""
        mock_copy, _ = setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        mock_copy.assert_called_once_with(
            str(tmp_path / ".cursor" / "skills"),
            "/fake/plugin",
            "cursor",
            "./.mpga-runtime/bin/mpga.sh",
        )

    def test_creates_agent_files(self, tmp_path: Path, monkeypatch):
        """Creates agent markdown files in .cursor/agents/."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        agents_dir = tmp_path / ".cursor" / "agents"
        assert agents_dir.is_dir()

        for agent in MOCK_AGENTS:
            agent_file = agents_dir / f"{agent.name}.md"
            assert agent_file.exists()
            content = agent_file.read_text()
            assert f"name: {agent.name}" in content
            assert f"description: {agent.description}" in content
            assert f"model: {agent.model}" in content

    def test_rewrites_cli_references(self, tmp_path: Path, monkeypatch):
        """Rewrites CLAUDE_PLUGIN_ROOT to the vendored runtime path in agent instructions."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "agents" / "mpga-test-agent.md").read_text()
        assert "./.mpga-runtime/bin/mpga.sh" in content
        assert "${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js" not in content


# ---------------------------------------------------------------------------
# Tests: global export
# ---------------------------------------------------------------------------

class TestCursorGlobalExport:
    """exportCursor global (isGlobal = true) tests."""

    def test_copies_skills_to_global(self, tmp_path: Path, monkeypatch):
        """Copies skills to ~/.cursor/skills/."""
        mock_copy, _ = setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root="/fake/project",
            mpga_dir="/fake/project/MPGA",
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=True,
        )

        mock_copy.assert_called_once()
        call_args = mock_copy.call_args[0]
        assert ".cursor" in call_args[0]
        assert "skills" in call_args[0]

    def test_does_not_create_project_rules(self, tmp_path: Path, monkeypatch):
        """Does NOT create project-level .cursor/rules/ directory."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.cursor import export_cursor

        project_root = tmp_path / "project"
        project_root.mkdir()

        export_cursor(
            project_root=str(project_root),
            mpga_dir=str(project_root / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=True,
        )

        assert not (project_root / ".cursor" / "rules").exists()


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------

class TestCursorEdgeCases:
    """Cursor export edge cases."""

    def test_handles_missing_milestone(self, tmp_path: Path, monkeypatch):
        """Handles missing milestone in indexContent."""
        setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n\n## Scopes\n- core\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-project.mdc").read_text()
        assert "(none)" in content

    def test_handles_null_plugin_root(self, tmp_path: Path, monkeypatch):
        """Handles null pluginRoot."""
        mock_copy, mock_read = setup_mocks(monkeypatch)
        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root=None,
            is_global=False,
        )

        mock_copy.assert_called_once()
        assert mock_copy.call_args[0][1] is None
        assert mock_copy.call_args[0][3] == "mpga"

    def test_scopes_mdc_filters_non_md(self, tmp_path: Path, monkeypatch):
        """Scopes mdc filters non-.md files."""
        setup_mocks(monkeypatch)
        scopes_dir = tmp_path / "MPGA" / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "core.md").write_text("# Core\n")
        (scopes_dir / "README.txt").write_text("readme\n")
        (scopes_dir / ".DS_Store").write_text("")

        from mpga.commands.export.cursor import export_cursor

        export_cursor(
            project_root=str(tmp_path),
            mpga_dir=str(tmp_path / "MPGA"),
            index_content="# INDEX\n",
            project_name="test-project",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        content = (tmp_path / ".cursor" / "rules" / "mpga-scopes.mdc").read_text()
        assert "core" in content
        assert "README.txt" not in content
        assert ".DS_Store" not in content
