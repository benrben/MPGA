"""Tests for T011 — skill tracker in capture-user-prompt hook.

Evidence: mpga-plugin/cli/src/mpga/commands/hook.py:246-290
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from mpga.commands.hook import hook


# ---------------------------------------------------------------------------
# Bug fix: capture-user-prompt reads user_prompt field (not user_message)
# ---------------------------------------------------------------------------


def test_capture_user_prompt_reads_user_prompt_field(tmp_path, monkeypatch):
    """Regression: handler must read 'user_prompt' field from UserPromptSubmit payload."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)
    (tmp_path / ".mpga").mkdir(parents=True, exist_ok=True)

    payload = json.dumps({
        "user_prompt": "Please help me with this task",
        "session_id": "sess-regression",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0


def test_capture_user_prompt_falls_back_to_user_message(tmp_path, monkeypatch):
    """Backwards compat: handler must also accept 'user_message' field."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)
    (tmp_path / ".mpga").mkdir(parents=True, exist_ok=True)

    payload = json.dumps({
        "user_message": "Legacy field value",
        "session_id": "sess-legacy",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Skill tracker: writes active_skill.json on slash command
# ---------------------------------------------------------------------------


def test_skill_tracker_writes_skill_on_slash_command(tmp_path, monkeypatch):
    """Slash-command prompt must write active_skill.json with skill name."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)

    payload = json.dumps({
        "user_prompt": "/mpga-develop please do task T001",
        "session_id": "test-sid",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    active_skill = tmp_path / ".mpga" / "session" / "test-sid" / "active_skill.json"
    assert active_skill.exists(), f"active_skill.json not found at {active_skill}"
    data = json.loads(active_skill.read_text())
    assert data["skill"] == "mpga-develop"
    assert data["session_id"] == "test-sid"


def test_skill_tracker_writes_empty_on_non_slash(tmp_path, monkeypatch):
    """Plain text prompt (no slash) must write empty {} to active_skill.json."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)

    payload = json.dumps({
        "user_prompt": "please help me with something",
        "session_id": "test-sid-plain",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    active_skill = tmp_path / ".mpga" / "session" / "test-sid-plain" / "active_skill.json"
    assert active_skill.exists(), f"active_skill.json not found at {active_skill}"
    data = json.loads(active_skill.read_text())
    assert data == {}


def test_skill_tracker_normalizes_mpga_colon_to_dash(tmp_path, monkeypatch):
    """Slash command /mpga:develop must normalize colon to dash → skill 'mpga-develop'."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)

    payload = json.dumps({
        "user_prompt": "/mpga:develop run the TDD cycle",
        "session_id": "test-sid-colon",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    active_skill = tmp_path / ".mpga" / "session" / "test-sid-colon" / "active_skill.json"
    assert active_skill.exists()
    data = json.loads(active_skill.read_text())
    assert data["skill"] == "mpga-develop"


def test_skill_tracker_handles_missing_session_id(tmp_path, monkeypatch):
    """Missing session_id must use 'unknown' as fallback — no crash."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)

    payload = json.dumps({
        "user_prompt": "/mpga-ship release the thing",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    active_skill = tmp_path / ".mpga" / "session" / "unknown" / "active_skill.json"
    assert active_skill.exists()
    data = json.loads(active_skill.read_text())
    assert data["skill"] == "mpga-ship"
    assert data["session_id"] == "unknown"


def test_skill_tracker_extracts_skill_name_only_from_first_word(tmp_path, monkeypatch):
    """Skill name is the first word (after /), not the whole prompt."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)

    payload = json.dumps({
        "user_prompt": "/mpga-plan generate a plan for milestone M002",
        "session_id": "test-sid-words",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["capture-user-prompt"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    active_skill = tmp_path / ".mpga" / "session" / "test-sid-words" / "active_skill.json"
    data = json.loads(active_skill.read_text())
    assert data["skill"] == "mpga-plan"
