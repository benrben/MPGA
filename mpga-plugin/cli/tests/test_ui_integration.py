"""Integration tests for the UI design layer skill updates."""

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


class TestUiSkillIntegration:
    """UI design integration tests."""

    def test_brainstorm_contains_wireframe_phase(self):
        """brainstorm adds Phase 1.5 for wireframe generation."""
        content = (_plugin_root() / "skills" / "brainstorm" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "Phase 1.5" in content
        assert "wireframe" in content

    def test_plan_contains_prototype_step(self):
        """plan references prototype generation and mpga preview."""
        content = (_plugin_root() / "skills" / "plan" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "prototype" in content.lower()
        assert "mpga preview" in content

    def test_develop_contains_visual_tester_step(self):
        """develop inserts visual-tester between green and blue."""
        content = (_plugin_root() / "skills" / "develop" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "visual-tester" in content
        assert "green" in content.lower()
        assert "blue" in content.lower()

    def test_review_pr_contains_ui_quality_section(self):
        """review-pr adds ui-auditor and a UI Quality report section."""
        content = (_plugin_root() / "skills" / "review-pr" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "ui-auditor" in content
        assert "## UI Quality" in content

    def test_ship_contains_visual_and_ui_audit_checks(self):
        """ship adds the UI-specific release checks."""
        content = (_plugin_root() / "skills" / "ship" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "visual regression clean" in content
        assert "ui-audit passed" in content

    def test_enhanced_skill_frontmatter_is_still_valid(self):
        """All enhanced skills continue to parse valid frontmatter."""
        plugin_root = _plugin_root()
        for rel_path in [
            "skills/brainstorm/SKILL.md",
            "skills/plan/SKILL.md",
            "skills/develop/SKILL.md",
            "skills/review-pr/SKILL.md",
            "skills/ship/SKILL.md",
        ]:
            post = _frontmatter(plugin_root / rel_path)
            assert post.get("name")
            assert post.get("description")
