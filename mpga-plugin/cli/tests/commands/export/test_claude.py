"""Tests for the Claude export module."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest


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
