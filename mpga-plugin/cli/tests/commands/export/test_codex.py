"""Tests for the Codex export module."""

from pathlib import Path
from unittest.mock import MagicMock

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
        side_effect=lambda _pr, slug, cli=None: f"Instructions for {slug}\nUse {cli or 'mpga'} sync"
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
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        index_content = "## File registry\n- src/index.ts\n"
        export_codex(str(project_root), index_content, "my-project", None, False)

        agents_md = project_root / "AGENTS.md"
        assert agents_md.exists()
        content = agents_md.read_text()
        assert "MPGA" in content
        assert "Evidence link protocol" in content
        assert "TDD protocol" in content
        assert index_content in content

    def test_copies_skills_to(self, tmp_path: Path, monkeypatch):
        """Calls copySkillsTo with correct arguments."""
        mock_copy, _ = setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), "", "my-project", "/some/plugin", False)

        expected_skills_dir = str(project_root / ".codex" / "skills")
        mock_copy.assert_called_once_with(
            expected_skills_dir,
            "/some/plugin",
            "codex",
            "./.mpga-runtime/bin/mpga.sh",
        )

    def test_creates_toml_agent_files(self, tmp_path: Path, monkeypatch):
        """Creates .codex/agents/ with TOML files for each agent."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "my-project"
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), "", "my-project", "/some/plugin", False)

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
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), "", "my-project", None, False)

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

        export_codex("/unused", "", "proj", None, True)

        codex_dir = tmp_path / ".codex"
        assert codex_dir.exists()

    def test_writes_global_agents_md(self, tmp_path: Path, monkeypatch):
        """Writes AGENTS.md to ~/.codex/."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.codex import export_codex

        export_codex("/unused", "", "proj", None, True)

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

        # Should not throw on HOME lookup — may fail on path creation, which is fine
        try:
            export_codex("/unused", "", "proj", None, True)
        except (FileNotFoundError, PermissionError, OSError):
            pass


# ---------------------------------------------------------------------------
# Tests: content verification
# ---------------------------------------------------------------------------

class TestCodexContentVerification:
    """Generated content verification."""

    def test_root_agents_md_contains_commands(self, tmp_path: Path, monkeypatch):
        """Root AGENTS.md contains verification commands section."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "proj"
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), "", "proj", "/plugin", False)

        content = (project_root / "AGENTS.md").read_text()
        assert "see project README for the test command" in content
        assert "./.mpga-runtime/bin/mpga.sh evidence verify" in content
        assert "./.mpga-runtime/bin/mpga.sh board show" in content

    def test_root_agents_md_contains_timestamp(self, tmp_path: Path, monkeypatch):
        """Root AGENTS.md contains timestamp."""
        setup_mocks(monkeypatch)
        project_root = tmp_path / "proj"
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.codex import export_codex

        export_codex(str(project_root), "", "proj", None, False)

        content = (project_root / "AGENTS.md").read_text()
        assert "Generated by MPGA" in content


# ---------------------------------------------------------------------------
# T034: Regression tests — frontmatter stripping + SKILL.md model field
# ---------------------------------------------------------------------------

class TestCodexRegressionT034:
    """Regression tests for M005: frontmatter stripping and SKILL.md model injection."""

    def test_developer_instructions_strips_frontmatter(self, tmp_path):
        """read_agent_instructions strips YAML frontmatter — no '---' in output."""
        from mpga.commands.export.agents import read_agent_instructions

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text(
            "---\nname: test-agent\nmodel: opus\ndescription: A test agent\n---\n"
            "# Agent: Test\n\nActual instructions here.\n"
        )

        result = read_agent_instructions(str(tmp_path), "test-agent")

        assert "---" not in result
        assert "name: test-agent" not in result
        assert "model: opus" not in result

    def test_developer_instructions_preserves_body(self, tmp_path):
        """read_agent_instructions keeps body text below frontmatter."""
        from mpga.commands.export.agents import read_agent_instructions

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text(
            "---\nname: test-agent\nmodel: opus\n---\n"
            "# Agent: Test\n\nActual instructions here.\nMore body text.\n"
        )

        result = read_agent_instructions(str(tmp_path), "test-agent")

        assert "Actual instructions here." in result
        assert "More body text." in result

    def test_inject_model_into_skill_md_basic(self):
        """_inject_model_into_skill_md inserts model: field into frontmatter."""
        from mpga.commands.export.agents import _inject_model_into_skill_md

        content = "---\nname: my-skill\ndescription: A skill\n---\n\n## Content\n"
        result = _inject_model_into_skill_md(content, "gpt-5.3-codex")
        assert "model: gpt-5.3-codex" in result

    def test_inject_model_no_double_inject(self):
        """_inject_model_into_skill_md is a no-op when model: already present."""
        from mpga.commands.export.agents import _inject_model_into_skill_md

        content = "---\nname: my-skill\nmodel: existing-model\n---\n\n## Content\n"
        result = _inject_model_into_skill_md(content, "gpt-5.3-codex")
        assert result.count("model:") == 1

    def test_inject_model_empty_model_is_noop(self):
        """_inject_model_into_skill_md with empty model string → content unchanged."""
        from mpga.commands.export.agents import _inject_model_into_skill_md

        content = "---\nname: my-skill\n---\n\n## Content\n"
        result = _inject_model_into_skill_md(content, "")
        assert result == content

    def test_fallback_skill_md_contains_model_for_codex(self, tmp_path):
        """copy_skills_to with tool_name='codex' produces SKILL.md with model: field."""
        from mpga.commands.export.agents import MODEL_TIERS, copy_skills_to

        target_skills = tmp_path / "skills"
        copy_skills_to(str(target_skills), None, "codex")

        # At least one SKILL.md should have been written via fallback
        skill_files = list(target_skills.rglob("SKILL.md"))
        assert len(skill_files) > 0

        codex_model = MODEL_TIERS["codex"]["mid"]
        for skill_md in skill_files:
            content = skill_md.read_text()
            assert f"model: {codex_model}" in content, (
                f"{skill_md.name} missing model field. Content:\n{content}"
            )

    def test_non_codex_skill_md_has_no_model_field(self, tmp_path):
        """copy_skills_to with tool_name='claude' does NOT inject model: into SKILL.md."""
        from mpga.commands.export.agents import copy_skills_to

        target_skills = tmp_path / "skills"
        copy_skills_to(str(target_skills), None, "claude")

        for skill_md in target_skills.rglob("SKILL.md"):
            content = skill_md.read_text()
            # The fallback template for claude should not have a model: line
            assert "model: gpt-" not in content
