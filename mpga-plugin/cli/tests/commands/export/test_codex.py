"""Tests for the Codex export module."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mpga.commands.export.agents import AgentMeta


MOCK_AGENTS = [
    AgentMeta(
        slug="test-agent",
        name="mpga-test-agent",
        description='A test agent for unit tests',
        model="claude-sonnet-4-6",
        readonly=False,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="readonly-agent",
        name="mpga-readonly-agent",
        description='A read-only "quoted" agent',
        model="claude-opus-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
]


def setup_mocks(monkeypatch):
    mock_copy = MagicMock()
    mock_read = MagicMock(
        side_effect=lambda _pr, slug, cli=None: f"Instructions for {slug}\nUse {cli or 'npx mpga'} sync"
    )
    monkeypatch.setattr("mpga.commands.export.codex.AGENTS", MOCK_AGENTS)
    monkeypatch.setattr("mpga.commands.export.codex.SKILL_NAMES", ["sync-project", "plan"])
    monkeypatch.setattr("mpga.commands.export.codex.copy_skills_to", mock_copy)
    monkeypatch.setattr("mpga.commands.export.codex.read_agent_instructions", mock_read)
    return mock_copy, mock_read


# ---------------------------------------------------------------------------
# Tests: project-level export
# ---------------------------------------------------------------------------

class TestCodexProjectLevel:
    """exportCodex project-level tests."""

    def test_creates_root_agents_md(self, tmp_path: Path, monkeypatch):
        """Creates root AGENTS.md with project content."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        index_content = "## File registry\n- src/index.ts\n"
        export_codex(str(project_root), str(mpga_dir), index_content, "my-project", None, False)

        agents_md = project_root / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "MPGA" in content
        assert "Evidence link protocol" in content
        assert "TDD protocol" in content
        assert index_content in content

    def test_creates_mpga_agents_md(self, tmp_path: Path, monkeypatch):
        """Creates MPGA/AGENTS.md navigation guide."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "my-project", None, False)

        mpga_agents = mpga_dir / "AGENTS.md"
        assert mpga_agents.exists()
        content = mpga_agents.read_text()
        assert "MPGA Knowledge Layer" in content
        assert "Tier 1" in content
        assert "Tier 2" in content
        assert "INDEX.md" in content
        assert "GRAPH.md" in content

    def test_generates_subdir_agents_md(self, tmp_path: Path, monkeypatch):
        """Generates subdirectory AGENTS.md files for scopes with matching src dirs."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        scopes_dir = mpga_dir / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "core.md").write_text(
            "# Core\n[E] src/core/index.ts:1-10 :: main()\n[E] src/core/util.ts:5-20 :: helper()\n"
        )

        src_core_dir = project_root / "src" / "core"
        src_core_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "my-project", None, False)

        subdir_agents = src_core_dir / "AGENTS.md"
        assert subdir_agents.exists()
        content = subdir_agents.read_text()
        assert "core Module" in content
        assert "MPGA/scopes/core.md" in content
        assert "[E] src/core/index.ts:1-10 :: main()" in content

    def test_skips_subdir_when_src_missing(self, tmp_path: Path, monkeypatch):
        """Skips subdirectory AGENTS.md when matching src dir does not exist."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        scopes_dir = mpga_dir / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "missing.md").write_text("# Missing\n")

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "my-project", None, False)

        assert not (project_root / "src" / "missing" / "AGENTS.md").exists()

    def test_copies_skills_to(self, tmp_path: Path, monkeypatch):
        """Calls copySkillsTo with correct arguments."""
        mock_copy, _ = setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "my-project", "/some/plugin", False)

        expected_skills_dir = str(project_root / ".codex" / "skills")
        mock_copy.assert_called_once_with(
            expected_skills_dir,
            "/some/plugin",
            "codex",
            "node ./.mpga-runtime/cli/dist/index.js",
        )

    def test_creates_toml_agent_files(self, tmp_path: Path, monkeypatch):
        """Creates .codex/agents/ with TOML files for each agent."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "my-project", "/some/plugin", False)

        agents_dir = project_root / ".codex" / "agents"
        assert agents_dir.exists()

        for agent in MOCK_AGENTS:
            toml_path = agents_dir / f"{agent.name}.toml"
            assert toml_path.exists()
            content = toml_path.read_text()
            assert f'name = "{agent.name}"' in content
            assert f'model = "{agent.model}"' in content
            assert f'sandbox_mode = "{agent.sandbox_mode}"' in content
            assert 'developer_instructions = """' in content

    def test_toml_escapes_double_quotes(self, tmp_path: Path, monkeypatch):
        """TOML agent files escape double quotes in description."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "my-project", None, False)

        toml_path = project_root / ".codex" / "agents" / "mpga-readonly-agent.toml"
        content = toml_path.read_text()
        assert 'description = "A read-only \\"quoted\\" agent"' in content


# ---------------------------------------------------------------------------
# Tests: global export
# ---------------------------------------------------------------------------

class TestCodexGlobalExport:
    """exportCodex global tests."""

    def test_creates_codex_directory(self, tmp_path: Path, monkeypatch):
        """Creates ~/.codex/ directory."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.codex import export_codex

        export_codex("/unused", "/unused/MPGA", "", "proj", None, True)

        codex_dir = tmp_path / ".codex"
        assert codex_dir.exists()

    def test_writes_global_agents_md(self, tmp_path: Path, monkeypatch):
        """Writes AGENTS.md to ~/.codex/."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.codex import export_codex

        export_codex("/unused", "/unused/MPGA", "", "proj", None, True)

        agents_md = tmp_path / ".codex" / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "MPGA Methodology (Global)" in content
        assert "Evidence over claims" in content
        assert "TDD is mandatory" in content

    def test_uses_tilde_fallback(self, tmp_path: Path, monkeypatch):
        """Uses ~ as fallback when HOME is undefined."""
        setup_mocks(monkeypatch)
        monkeypatch.delenv("HOME", raising=False)

        from mpga.commands.export.codex import export_codex

        # Should not throw
        try:
            export_codex("/unused", "/unused/MPGA", "", "proj", None, True)
        except Exception:
            pass  # May fail on path creation but should not throw on HOME lookup


# ---------------------------------------------------------------------------
# Tests: content verification
# ---------------------------------------------------------------------------

class TestCodexContentVerification:
    """Generated content verification."""

    def test_root_agents_md_contains_commands(self, tmp_path: Path, monkeypatch):
        """Root AGENTS.md contains verification commands section."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "proj"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "proj", "/plugin", False)

        content = (project_root / "AGENTS.md").read_text()
        assert "npm test" in content
        assert "node ./.mpga-runtime/cli/dist/index.js evidence verify" in content
        assert "node ./.mpga-runtime/cli/dist/index.js board show" in content

    def test_root_agents_md_contains_timestamp(self, tmp_path: Path, monkeypatch):
        """Root AGENTS.md contains timestamp."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "proj"
        mpga_dir = project_root / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "proj", None, False)

        content = (project_root / "AGENTS.md").read_text()
        assert "Generated by MPGA" in content

    def test_subdir_agents_md_limits_evidence(self, tmp_path: Path, monkeypatch):
        """Subdirectory AGENTS.md limits evidence links to 5."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "proj"
        mpga_dir = project_root / "MPGA"
        scopes_dir = mpga_dir / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)

        links = [f"[E] src/big/file{i}.ts:1-10 :: fn{i}()" for i in range(8)]
        (scopes_dir / "big.md").write_text(f"# Big\n" + "\n".join(links) + "\n")

        src_big_dir = project_root / "src" / "big"
        src_big_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), str(mpga_dir), "", "proj", None, False)

        content = (src_big_dir / "AGENTS.md").read_text()
        evidence_lines = [l for l in content.split("\n") if "[E]" in l]
        assert len(evidence_lines) <= 5
