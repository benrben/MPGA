"""Tests that hook install exports full manifest including PostToolUse * and UserPromptSubmit."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner


def test_hook_install_exports_to_claude(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import _hooks_manifest, hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "claude"])

    assert result.exit_code == 0
    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    manifest = _hooks_manifest()
    assert "hooks" in settings
    assert set(settings["hooks"].keys()) == set(manifest["hooks"].keys())


def test_hook_install_includes_posttooluse_star(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "claude"])
    assert result.exit_code == 0

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    post = settings["hooks"]["PostToolUse"]
    assert any(block.get("matcher") == "*" for block in post)
    star_block = next(b for b in post if b.get("matcher") == "*")
    cmds = [h["command"] for h in star_block["hooks"]]
    assert any("capture-observation" in c for c in cmds)


def test_hook_install_includes_user_prompt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "claude"])
    assert result.exit_code == 0

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in settings["hooks"]
    blocks = settings["hooks"]["UserPromptSubmit"]
    cmds = [h["command"] for b in blocks for h in b["hooks"]]
    assert any("capture-user-prompt" in c for c in cmds)


def test_hook_install_cursor_platform(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "cursor"])
    assert result.exit_code == 0

    routing_path = tmp_path / ".cursor" / "rules" / "mpga-routing.mdc"
    assert routing_path.exists()
    content = routing_path.read_text(encoding="utf-8")
    assert "PostToolUse" in content
    assert "matcher" in content and "*" in content
    assert "capture-observation" in content
    assert "UserPromptSubmit" in content
    assert "capture-user-prompt" in content


def test_hook_install_preserves_existing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    prior = {
        "permissions": {"allow": ["mcp"]},
        "env": {"CUSTOM": "1"},
    }
    settings_path.write_text(json.dumps(prior, indent=2) + "\n", encoding="utf-8")

    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["install", "--platform", "claude"])
    assert result.exit_code == 0

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["permissions"] == prior["permissions"]
    assert settings["env"] == prior["env"]
    assert "hooks" in settings
    assert "PreToolUse" in settings["hooks"]
