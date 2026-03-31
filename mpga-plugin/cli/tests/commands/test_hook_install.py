"""Tests for multi-platform hook installation."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner


def test_hook_install_claude_writes_settings_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "claude"])

    assert result.exit_code == 0
    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "PreToolUse" in settings["hooks"]
    assert "SessionStart" in settings["hooks"]


def test_hook_install_cursor_writes_routing_rule(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "cursor"])

    assert result.exit_code == 0
    routing_path = tmp_path / ".cursor" / "rules" / "mpga-routing.mdc"
    assert routing_path.exists()
    content = routing_path.read_text(encoding="utf-8")
    assert "hard-block mode" in content
    assert "mpga ctx execute" in content
    assert "mpga scope show <name>" in content


def test_hook_install_codex_writes_agent_toml(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "codex"])

    assert result.exit_code == 0
    agent_path = tmp_path / ".codex" / "agents" / "mpga-routing.toml"
    assert agent_path.exists()
    content = agent_path.read_text(encoding="utf-8")
    assert 'name = "MPGA Routing"' in content
    assert "mpga session resume" in content
    assert "mpga ctx fetch-and-index" in content


def test_hook_install_antigravity_writes_rule(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "antigravity"])

    assert result.exit_code == 0
    rule_path = tmp_path / ".antigravity" / "rules" / "mpga-routing.md"
    assert rule_path.exists()
    content = rule_path.read_text(encoding="utf-8")
    assert "# MPGA Routing" in content
    assert "mpga ctx doctor" in content


def test_hooks_alias_resolves_same_group(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    from mpga.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["hooks", "--help"])

    assert result.exit_code == 0
    assert "install" in result.output
