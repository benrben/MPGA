"""Tests for T014: generate_improvement() and write_improvement() in hook_post_stop.py."""

from __future__ import annotations

import unittest.mock as mock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_target(tmp_path, content="# My Skill\n\nSome content here.\n", name="my-skill", target_type="skill"):
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")

    from mpga.commands.hook_post_stop import ImprovementTarget
    return ImprovementTarget(
        skill_or_agent_name=name,
        file_path=str(skill_file),
        target_type=target_type,
    )


def _make_mock_client(response_text: str):
    mock_response = mock.MagicMock()
    mock_response.content = [mock.MagicMock(text=response_text)]
    mock_client = mock.MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# generate_improvement tests
# ---------------------------------------------------------------------------


def test_generate_improvement_prompt_structure(tmp_path):
    from mpga.commands.hook_post_stop import generate_improvement, ImprovementTarget

    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# My Skill\n\nSome content here.\n", encoding="utf-8")

    target = ImprovementTarget(
        skill_or_agent_name="my-skill",
        file_path=str(skill_file),
        target_type="skill",
    )

    mock_client = _make_mock_client("# My Skill\n\nImproved content.\n")

    result = generate_improvement(
        target, "transcript tail here", {"error": "rate_limit"}, client=mock_client
    )

    # Verify the prompt was structured correctly
    call_kwargs = mock_client.messages.create.call_args
    prompt_sent = call_kwargs.kwargs["messages"][0]["content"]
    assert "Current file content:" in prompt_sent
    assert "Recent transcript tail" in prompt_sent
    assert "Issue signal:" in prompt_sent
    assert "# My Skill" in prompt_sent
    assert result == "# My Skill\n\nImproved content.\n"


def test_generate_improvement_returns_llm_text(tmp_path):
    target = _make_target(tmp_path)
    mock_client = _make_mock_client("# My Skill\n\nFully improved.\n")

    from mpga.commands.hook_post_stop import generate_improvement
    result = generate_improvement(target, "tail", {}, client=mock_client)
    assert result == "# My Skill\n\nFully improved.\n"


def test_generate_improvement_truncates_transcript_to_3000(tmp_path):
    target = _make_target(tmp_path)
    long_tail = "x" * 5000
    mock_client = _make_mock_client("# My Skill\n\nok\n")

    from mpga.commands.hook_post_stop import generate_improvement
    generate_improvement(target, long_tail, {}, client=mock_client)

    call_kwargs = mock_client.messages.create.call_args
    prompt_sent = call_kwargs.kwargs["messages"][0]["content"]
    # The tail sent should be at most 3000 chars of x's
    assert "x" * 3000 in prompt_sent
    assert "x" * 3001 not in prompt_sent


# ---------------------------------------------------------------------------
# write_improvement validation tests
# ---------------------------------------------------------------------------


def test_write_improvement_validates_empty_content(tmp_path):
    from mpga.commands.hook_post_stop import write_improvement, ImprovementValidationError
    target = _make_target(tmp_path)

    with pytest.raises(ImprovementValidationError, match="empty"):
        write_improvement(target, "")


def test_write_improvement_validates_missing_header(tmp_path):
    from mpga.commands.hook_post_stop import write_improvement, ImprovementValidationError
    target = _make_target(tmp_path, content="# Original\n\nContent here.\n")

    with pytest.raises(ImprovementValidationError, match="# header"):
        write_improvement(target, "No header here, just plain text content that is long enough.")


def test_write_improvement_validates_too_short(tmp_path):
    from mpga.commands.hook_post_stop import write_improvement, ImprovementValidationError
    # Original is 100 chars; we supply < 50 chars (which is < 50% of 100)
    original = "# Skill\n\n" + "A" * 91  # exactly 100 chars
    target = _make_target(tmp_path, content=original)

    short_content = "# Skill\n\nX"  # 11 chars — well below 50 chars threshold
    with pytest.raises(ImprovementValidationError, match="too short"):
        write_improvement(target, short_content)


def test_write_improvement_validates_too_long(tmp_path):
    from mpga.commands.hook_post_stop import write_improvement, ImprovementValidationError
    original = "# Skill\n\n" + "A" * 91  # 100 chars
    target = _make_target(tmp_path, content=original)

    # 501 chars is > 500% of 100
    long_content = "# Skill\n\n" + "B" * 492  # 501 chars total
    with pytest.raises(ImprovementValidationError, match="too long"):
        write_improvement(target, long_content)


# ---------------------------------------------------------------------------
# write_improvement backup and write tests
# ---------------------------------------------------------------------------


def test_write_improvement_backs_up_before_writing(tmp_path, monkeypatch):
    from mpga.commands.hook_post_stop import write_improvement, ImprovementTarget

    skill_file = tmp_path / "SKILL.md"
    original_content = "# My Skill\n\nOriginal content that is long enough to pass validation.\n"
    skill_file.write_text(original_content, encoding="utf-8")

    target = ImprovementTarget(
        skill_or_agent_name="my-skill",
        file_path=str(skill_file),
        target_type="skill",
    )

    backup_calls = []

    def fake_backup(file_path, name, project_root=None):
        # Record that backup was called and verify original content is still present
        backup_calls.append({
            "file_path": file_path,
            "name": name,
            "content_at_backup_time": skill_file.read_text(encoding="utf-8"),
        })

    monkeypatch.setattr("mpga.commands.hook.backup_file", fake_backup)
    # Patch the import inside write_improvement
    import mpga.commands.hook_post_stop as hps_module
    monkeypatch.setattr(hps_module, "_backup_file_ref", fake_backup, raising=False)

    # Patch the from-import inside write_improvement using sys.modules approach
    import sys
    orig_hook = sys.modules.get("mpga.commands.hook")

    class FakeHookModule:
        backup_file = staticmethod(fake_backup)

    sys.modules["mpga.commands.hook"] = FakeHookModule()  # type: ignore[assignment]
    try:
        valid_content = "# My Skill\n\nImproved content that is long enough to pass validation checks.\n"
        write_improvement(target, valid_content)
    finally:
        if orig_hook is not None:
            sys.modules["mpga.commands.hook"] = orig_hook
        else:
            sys.modules.pop("mpga.commands.hook", None)

    assert len(backup_calls) == 1
    assert backup_calls[0]["name"] == "my-skill"
    # The backup was called before the new content was written
    assert backup_calls[0]["content_at_backup_time"] == original_content


def test_write_improvement_writes_valid_content(tmp_path, monkeypatch):
    from mpga.commands.hook_post_stop import write_improvement, ImprovementTarget

    skill_file = tmp_path / "SKILL.md"
    original_content = "# My Skill\n\nOriginal content that is long enough to pass validation.\n"
    skill_file.write_text(original_content, encoding="utf-8")

    target = ImprovementTarget(
        skill_or_agent_name="my-skill",
        file_path=str(skill_file),
        target_type="skill",
    )

    def fake_backup(file_path, name, project_root=None):
        pass  # no-op

    import sys
    orig_hook = sys.modules.get("mpga.commands.hook")

    class FakeHookModule:
        backup_file = staticmethod(fake_backup)

    sys.modules["mpga.commands.hook"] = FakeHookModule()  # type: ignore[assignment]
    try:
        valid_content = "# My Skill\n\nImproved content that is long enough to pass validation checks.\n"
        write_improvement(target, valid_content)
    finally:
        if orig_hook is not None:
            sys.modules["mpga.commands.hook"] = orig_hook
        else:
            sys.modules.pop("mpga.commands.hook", None)

    assert skill_file.read_text(encoding="utf-8") == valid_content
