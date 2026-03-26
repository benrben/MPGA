"""Tests for the agents export module (CLI rewriting, copySkillsTo, readAgentInstructions)."""

from pathlib import Path

import pytest


class TestExportAgentCliRewriting:
    """export agent/skill CLI rewriting tests."""

    def test_rewrites_placeholder_and_npx_in_skills(self, tmp_path: Path):
        """Rewrites both placeholder and hardcoded npx CLI references when vendoring skills."""
        plugin_root = tmp_path / "plugin"
        skills_dir = plugin_root / "skills" / "rally"
        agents_dir = plugin_root / "agents"
        skills_dir.mkdir(parents=True, exist_ok=True)
        agents_dir.mkdir(parents=True, exist_ok=True)

        plugin_root_str = str(plugin_root).replace("\\", "/")
        (skills_dir / "SKILL.md").write_text(
            f"Run node ${{CLAUDE_PLUGIN_ROOT}}/cli/dist/index.js sync\n"
            f"Or run node {plugin_root_str}/cli/dist/index.js board live --serve --open\n"
            f"Then run npx mpga export --all\n"
        )

        from mpga.commands.export.agents import copy_skills_to

        target_dir = tmp_path / "target-skills"
        copy_skills_to(
            str(target_dir),
            str(plugin_root),
            "claude",
            "node ./.mpga-runtime/cli/dist/index.js",
        )

        content = (target_dir / "mpga-rally" / "SKILL.md").read_text()
        assert "node ./.mpga-runtime/cli/dist/index.js sync" in content
        assert "node ./.mpga-runtime/cli/dist/index.js board live --serve --open" in content
        assert "node ./.mpga-runtime/cli/dist/index.js export --all" in content
        assert "npx mpga" not in content
        assert "${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js" not in content

    def test_rewrites_in_agent_instructions(self, tmp_path: Path):
        """Rewrites both placeholder and hardcoded npx CLI references in agent instructions."""
        plugin_root = tmp_path / "plugin"
        agents_dir = plugin_root / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        plugin_root_str = str(plugin_root).replace("\\", "/")
        (agents_dir / "campaigner.md").write_text(
            f"# Agent: campaigner\n\n"
            f"Use node ${{CLAUDE_PLUGIN_ROOT}}/cli/dist/index.js sync\n"
            f"Fallback: node {plugin_root_str}/cli/dist/index.js init --from-existing\n"
            f"Fallback: npx mpga init --from-existing\n"
        )

        from mpga.commands.export.agents import read_agent_instructions

        content = read_agent_instructions(
            str(plugin_root),
            "campaigner",
            "node ./.mpga-runtime/cli/dist/index.js",
        )

        assert "node ./.mpga-runtime/cli/dist/index.js sync" in content
        assert "node ./.mpga-runtime/cli/dist/index.js init --from-existing" in content
        assert "npx mpga" not in content
        assert "${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js" not in content

    def test_falls_back_to_npx_mpga(self):
        """Falls back to npx mpga when no vendored path is provided."""
        from mpga.commands.export.agents import rewrite_cli_references

        content = rewrite_cli_references(
            "Use node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js drift --quick"
        )
        assert "mpga drift --quick" in content
