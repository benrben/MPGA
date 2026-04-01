"""Tests for backup_file() helper and rollback command — T013."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from mpga.commands.hook import hook, backup_file


def test_backup_file_creates_backup_at_expected_path(tmp_path, monkeypatch):
    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    src = tmp_path / "myskill.md"
    src.write_text("# My Skill\n", encoding="utf-8")
    backup_path = backup_file(str(src), "myskill", project_root=tmp_path)
    assert backup_path.exists()
    backup_dir = tmp_path / ".mpga" / "backups" / "myskill"
    assert backup_path.parent == backup_dir
    assert backup_path.suffix == ".md"


def test_backup_file_returns_path_object(tmp_path, monkeypatch):
    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    src = tmp_path / "myskill.md"
    src.write_text("# My Skill\n", encoding="utf-8")
    result = backup_file(str(src), "myskill", project_root=tmp_path)
    assert isinstance(result, Path)


def test_backup_file_preserves_content(tmp_path, monkeypatch):
    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    original_content = "# Original Skill Content\nSome details here.\n"
    src = tmp_path / "myskill.md"
    src.write_text(original_content, encoding="utf-8")
    backup_path = backup_file(str(src), "myskill", project_root=tmp_path)
    assert backup_path.read_text(encoding="utf-8") == original_content


def test_rollback_restores_correct_content(tmp_path, monkeypatch):
    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    src = tmp_path / "myskill.md"
    original_content = "# Original Content\n"
    src.write_text(original_content, encoding="utf-8")
    backup_file(str(src), "myskill", project_root=tmp_path)
    # Modify the original
    src.write_text("# Modified Content\n", encoding="utf-8")
    assert src.read_text() == "# Modified Content\n"
    # Rollback
    runner = CliRunner()
    result = runner.invoke(hook, ["rollback", "myskill"], catch_exceptions=False)
    assert result.exit_code == 0
    assert src.read_text() == original_content


def test_rollback_errors_when_no_backups_exist(tmp_path, monkeypatch):
    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    runner = CliRunner()
    result = runner.invoke(hook, ["rollback", "nonexistent-skill"])
    assert result.exit_code != 0


def test_rollback_prints_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr("mpga.commands.hook._project_root", lambda: tmp_path)
    src = tmp_path / "myskill.md"
    src.write_text("# Content\n", encoding="utf-8")
    backup_file(str(src), "myskill", project_root=tmp_path)
    runner = CliRunner()
    result = runner.invoke(hook, ["rollback", "myskill"], catch_exceptions=False)
    assert "Restored" in result.output
    assert "myskill" in result.output
