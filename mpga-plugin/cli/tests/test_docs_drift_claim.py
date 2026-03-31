"""T025: Test that docs accurately describe drift as hook-triggered (PostToolUse),
not as running continuously on every file save.

Regression guard: ensure docs don't regress to claiming drift runs on every
file system save. The accurate behavior is: drift runs when the PostToolUse
hook fires (after Write/Edit tool calls).
"""
from pathlib import Path

CLAUDE_CODE_DOC = Path("/Users/benreich/MPGA/docs/claude-code.md")


def test_drift_described_as_hook_triggered():
    """claude-code.md must describe drift as running after Write/Edit tool calls (PostToolUse),
    not as continuous or every-file-save monitoring."""
    assert CLAUDE_CODE_DOC.exists(), f"Missing doc: {CLAUDE_CODE_DOC}"
    content = CLAUDE_CODE_DOC.read_text(encoding="utf-8")

    # Must NOT claim drift is continuous/always-on file watching
    misleading_phrases = [
        "on every file save",
        "on every save",
        "continuously monitors",
        "watches for changes",
        "file system watcher",
    ]
    for phrase in misleading_phrases:
        assert phrase.lower() not in content.lower(), (
            f"Doc contains misleading drift claim: '{phrase}'. "
            "Drift runs via PostToolUse hook, not continuous file watching."
        )

    # Must accurately describe that it's hook-triggered
    accurate_phrases = [
        "Write",
        "Edit",
        "hook",
    ]
    for phrase in accurate_phrases:
        assert phrase in content, (
            f"Doc missing accurate description of drift trigger. "
            f"Expected to find: '{phrase}'. "
            "Drift runs via PostToolUse hook after Write/Edit tool calls."
        )
