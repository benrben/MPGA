"""Tests for the Antigravity (Gemini) export module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def setup_mocks(monkeypatch):
    mock_copy = MagicMock()
    monkeypatch.setattr("mpga.commands.export.antigravity.SKILL_NAMES", ["sync-project", "brainstorm", "plan", "develop", "drift-check"])
    monkeypatch.setattr("mpga.commands.export.antigravity.copy_skills_to", mock_copy)
    return mock_copy


def default_index_content(milestone: str | None = None) -> str:
    return (
        "# Project: test-project\n\n"
        "## Identity\n"
        "- **Last sync:** 2026-01-15T10:00:00Z\n"
        "- **Evidence coverage:** 45%\n\n"
        "## Active milestone\n"
        f"{milestone or 'M001-alpha'}\n\n"
        "## Scope registry\n"
        "| Scope | File count |\n"
    )


# ---------------------------------------------------------------------------
# Tests: project-level export
# ---------------------------------------------------------------------------

class TestAntigravityProjectLevel:
    """exportAntigravity project-level tests."""

    def test_creates_gemini_md(self, tmp_path: Path, monkeypatch):
        """Creates GEMINI.md at project root."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        gemini_path = tmp_path / "GEMINI.md"
        assert gemini_path.exists()
        content = gemini_path.read_text()
        assert "MPGA-Managed Project Context" in content
        assert "node ./.mpga-runtime/cli/dist/index.js sync" in content
        assert "MPGA/INDEX.md" in content

    def test_gemini_md_includes_milestone(self, tmp_path: Path, monkeypatch):
        """GEMINI.md includes the active milestone from INDEX content."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content("M002-beta"), "test-project", "/fake/plugin", False, {})

        content = (tmp_path / "GEMINI.md").read_text()
        assert "M002-beta" in content

    def test_gemini_md_fallback_no_milestone(self, tmp_path: Path, monkeypatch):
        """GEMINI.md falls back to (none) when no milestone section exists."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), "# Project: test-project\n\n## Identity\n- stuff\n", "test-project", "/fake/plugin", False, {})

        content = (tmp_path / "GEMINI.md").read_text()
        assert "(none)" in content

    def test_calls_copy_skills_to(self, tmp_path: Path, monkeypatch):
        """Calls copySkillsTo for .agent/skills/."""
        mock_copy = setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        mock_copy.assert_called_once_with(
            str(tmp_path / ".agent" / "skills"),
            "/fake/plugin",
            "antigravity",
            "node ./.mpga-runtime/cli/dist/index.js",
        )

    def test_creates_rules_files(self, tmp_path: Path, monkeypatch):
        """Creates .antigravity/rules/ with 3 rule files."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        rules_dir = tmp_path / ".antigravity" / "rules"
        assert rules_dir.exists()
        files = [f.name for f in rules_dir.iterdir()]
        assert "mpga-context.md" in files
        assert "mpga-evidence.md" in files
        assert "mpga-tdd.md" in files
        assert len(files) == 3

    def test_context_rule_content(self, tmp_path: Path, monkeypatch):
        """mpga-context.md contains milestone and evidence protocol."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        content = (tmp_path / ".antigravity" / "rules" / "mpga-context.md").read_text()
        assert "MPGA Project Context" in content
        assert "M001-alpha" in content
        assert "Evidence protocol" in content
        assert "[E]" in content
        assert "[Unknown]" in content

    def test_evidence_rule_content(self, tmp_path: Path, monkeypatch):
        """mpga-evidence.md contains evidence link format."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        content = (tmp_path / ".antigravity" / "rules" / "mpga-evidence.md").read_text()
        assert "MPGA Evidence Protocol" in content
        assert "[E] filepath:startLine-endLine :: symbolName()" in content
        assert "[Stale:YYYY-MM-DD]" in content
        assert "node ./.mpga-runtime/cli/dist/index.js evidence heal" in content

    def test_tdd_rule_content(self, tmp_path: Path, monkeypatch):
        """mpga-tdd.md contains TDD protocol steps."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        content = (tmp_path / ".antigravity" / "rules" / "mpga-tdd.md").read_text()
        assert "RED" in content
        assert "GREEN" in content
        assert "BLUE" in content
        assert "NEVER write implementation code before a test" in content
        assert content.index("1. RED") < content.index("2. GREEN")
        assert content.index("2. GREEN") < content.index("3. BLUE")

    def test_creates_workflow_files(self, tmp_path: Path, monkeypatch):
        """Creates .agents/workflows/ with 3 workflow files."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        workflows_dir = tmp_path / ".agents" / "workflows"
        assert workflows_dir.exists()
        files = [f.name for f in workflows_dir.iterdir()]
        assert "mpga-plan.md" in files
        assert "mpga-develop.md" in files
        assert "mpga-review.md" in files
        assert len(files) == 3

    def test_workflow_content(self, tmp_path: Path, monkeypatch):
        """Workflow files contain expected headings."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        workflows_dir = tmp_path / ".agents" / "workflows"

        plan = (workflows_dir / "mpga-plan.md").read_text()
        assert "MPGA Plan Workflow" in plan
        assert "milestone" in plan

        develop = (workflows_dir / "mpga-develop.md").read_text()
        assert "MPGA Develop Workflow" in develop
        assert "failing test" in develop

        review = (workflows_dir / "mpga-review.md").read_text()
        assert "MPGA Review Workflow" in review
        assert "Spec compliance" in review
        assert "node ./.mpga-runtime/cli/dist/index.js evidence verify" in review
        assert "npx mpga evidence verify" not in review

    # ── Knowledge seeding ──

    def test_no_knowledge_when_not_requested(self, tmp_path: Path, monkeypatch):
        """Does not seed knowledge items when opts.knowledge is false."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        scopes_dir = mpga_dir / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "core.md").write_text("# Scope: core\n[E] src/core.ts:1-10 :: main()\n")

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {})

        ki_dir = tmp_path / ".antigravity" / "knowledge"
        assert not (ki_dir / "mpga-core.md").exists()

    def test_seeds_knowledge_from_scopes(self, tmp_path: Path, monkeypatch):
        """Seeds knowledge items from scopes when opts.knowledge is true."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        scopes_dir = mpga_dir / "scopes"
        scopes_dir.mkdir(parents=True, exist_ok=True)
        (scopes_dir / "core.md").write_text(
            "# Scope: core\n[E] src/core.ts:1-10 :: main()\n[E] src/core.ts:20-30 :: init()\n"
        )
        (scopes_dir / "utils.md").write_text("# Scope: utils\n")

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {"knowledge": True})

        ki_dir = tmp_path / ".antigravity" / "knowledge"
        assert ki_dir.exists()
        ki_files = [f.name for f in ki_dir.iterdir()]
        assert "mpga-core.md" in ki_files
        assert "mpga-utils.md" in ki_files

        core_content = (ki_dir / "mpga-core.md").read_text()
        assert "Knowledge: core module" in core_content
        assert "[E] src/core.ts:1-10 :: main()" in core_content
        assert "[E] src/core.ts:20-30 :: init()" in core_content

        utils_content = (ki_dir / "mpga-utils.md").read_text()
        assert "Knowledge: utils module" in utils_content
        assert "run `mpga sync` to populate" in utils_content

    def test_no_knowledge_when_scopes_missing(self, tmp_path: Path, monkeypatch):
        """Does not seed knowledge when scopes directory is missing."""
        setup_mocks(monkeypatch)
        mpga_dir = tmp_path / "MPGA"
        mpga_dir.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(tmp_path), str(mpga_dir), default_index_content(), "test-project", "/fake/plugin", False, {"knowledge": True})

        ki_dir = tmp_path / ".antigravity" / "knowledge"
        assert not ki_dir.exists()


# ---------------------------------------------------------------------------
# Tests: global export
# ---------------------------------------------------------------------------

class TestAntigravityGlobalExport:
    """exportAntigravity global tests."""

    def test_copies_skills_globally(self, tmp_path: Path, monkeypatch):
        """Calls copySkillsTo for ~/.gemini/antigravity/skills/."""
        mock_copy = setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity("/unused", "/unused/MPGA", "", "test", "/fake/plugin", True, {})

        mock_copy.assert_called_once()
        call_args = mock_copy.call_args[0]
        assert ".gemini" in call_args[0]
        assert "antigravity" in call_args[0]
        assert "skills" in call_args[0]

    def test_creates_global_rule(self, tmp_path: Path, monkeypatch):
        """Creates ~/.antigravity/rules/mpga-global.md."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity("/unused", "/unused/MPGA", "", "test", "/fake/plugin", True, {})

        global_rule = tmp_path / ".antigravity" / "rules" / "mpga-global.md"
        assert global_rule.exists()
        content = global_rule.read_text()
        assert "MPGA Global Methodology" in content
        assert "MPGA/ directory" in content
        assert "evidence links" in content
        assert "TDD" in content

    def test_global_rule_sections(self, tmp_path: Path, monkeypatch):
        """mpga-global.md contains always-do and never-do sections."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity("/unused", "/unused/MPGA", "", "test", "/fake/plugin", True, {})

        content = (tmp_path / ".antigravity" / "rules" / "mpga-global.md").read_text()
        assert "Always do" in content
        assert "Never do" in content
        assert "Evidence link format" in content

    def test_no_project_files_when_global(self, tmp_path: Path, monkeypatch):
        """Does not create project-level files when isGlobal is true."""
        setup_mocks(monkeypatch)
        monkeypatch.setenv("HOME", str(tmp_path))

        project_root = tmp_path / "project"
        project_root.mkdir(parents=True, exist_ok=True)

        from mpga.commands.export.antigravity import export_antigravity

        export_antigravity(str(project_root), str(project_root / "MPGA"), "", "test", "/fake/plugin", True, {})

        assert not (project_root / "GEMINI.md").exists()
        assert not (project_root / ".antigravity" / "rules").exists()
        assert not (project_root / ".agents" / "workflows").exists()
