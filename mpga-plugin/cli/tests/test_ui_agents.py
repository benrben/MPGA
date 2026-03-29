"""Tests for the UI design agents and skills."""

from pathlib import Path
import re


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _frontmatter(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert match is not None, f"missing frontmatter in {path}"
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


class TestUiAgentsAndSkills:
    """UI design definition tests."""

    def test_agent_frontmatter_is_valid(self):
        """All new agent markdown files contain valid frontmatter."""
        plugin_root = _plugin_root()
        for rel_path in [
            "agents/designer.md",
            "agents/ui-auditor.md",
            "agents/visual-tester.md",
        ]:
            post = _frontmatter(plugin_root / rel_path)
            assert post.get("name")
            assert post.get("description")
            assert post.get("model")

    def test_skill_frontmatter_is_valid(self):
        """All new skill definitions contain valid frontmatter."""
        plugin_root = _plugin_root()
        for rel_path in [
            "skills/wireframe/SKILL.md",
            "skills/design-system/SKILL.md",
            "skills/ui-audit/SKILL.md",
            "skills/frontend-design/SKILL.md",
        ]:
            post = _frontmatter(plugin_root / rel_path)
            assert post.get("name")
            assert post.get("description")

    def test_designer_documents_all_renderers(self):
        """designer documents the full renderer fallback chain."""
        content = (_plugin_root() / "agents" / "designer.md").read_text(encoding="utf-8")
        assert "Excalidraw" in content
        assert "HTML" in content
        assert "SVG" in content
        assert "ASCII" in content

    def test_ui_auditor_documents_all_audit_categories(self):
        """ui-auditor contains all eight audit categories."""
        content = (_plugin_root() / "agents" / "ui-auditor.md").read_text(encoding="utf-8")
        for category in [
            "Accessibility",
            "Keyboard",
            "Forms",
            "Animation",
            "Performance",
            "Responsive",
            "Internationalization",
            "Design System Compliance",
        ]:
            assert category in content

    def test_visual_tester_documents_all_breakpoints(self):
        """visual-tester contains the mobile, tablet, and desktop breakpoints."""
        content = (_plugin_root() / "agents" / "visual-tester.md").read_text(encoding="utf-8")
        assert "375px" in content
        assert "768px" in content
        assert "1280px" in content

    def test_export_registry_includes_new_ui_agents_and_skills(self):
        """The export registry includes the new skills and agents."""
        from mpga.commands.export.agents import AGENTS, SKILL_NAMES

        slugs = {agent.slug for agent in AGENTS}

        assert "designer" in slugs
        assert "ui-auditor" in slugs
        assert "visual-tester" in slugs
        assert "wireframe" in SKILL_NAMES
        assert "design-system" in SKILL_NAMES
        assert "ui-audit" in SKILL_NAMES
        assert "frontend-design" in SKILL_NAMES
