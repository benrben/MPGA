"""Tests for the Claude export module."""

from pathlib import Path
from unittest.mock import MagicMock


class TestExportClaude:
    """exportClaude tests."""

    def test_points_skill_exports_at_vendored_runtime(self, tmp_path: Path, monkeypatch):
        """Points Claude skill exports at the vendored runtime path."""
        mock_copy_skills = MagicMock()
        monkeypatch.setattr("mpga.commands.export.claude.copy_skills_to", mock_copy_skills)
        monkeypatch.setattr("mpga.commands.export.claude.SKILL_NAMES", ["sync-project", "plan"])

        # Mock fs operations
        monkeypatch.setattr("builtins.open", MagicMock())

        from mpga.commands.export.claude import export_claude

        export_claude(
            project_root=str(tmp_path),
            index_content="# INDEX",
            project_name="proj",
            plugin_root="/fake/plugin",
            is_global=False,
        )

        mock_copy_skills.assert_called_once_with(
            str(tmp_path / ".claude" / "skills"),
            "/fake/plugin",
            "claude",
            "./.mpga-runtime/bin/mpga.sh",
        )

    def test_exports_hook_configuration_into_settings(self, tmp_path: Path):
        plugin_root = tmp_path / "plugin"
        (plugin_root / "hooks").mkdir(parents=True)
        (plugin_root / "hooks" / "hooks.json").write_text(
            '{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh session start"}]}]}}',
            encoding="utf-8",
        )
        (plugin_root / "agents").mkdir(parents=True)

        from mpga.commands.export.claude import _deploy_claude_plugin

        _deploy_claude_plugin(
            str(tmp_path / ".claude"),
            str(plugin_root),
            str(tmp_path),
            False,
        )

        settings = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
        assert "SessionStart" in settings
        assert "./.mpga-runtime/bin/mpga.sh session start" in settings
