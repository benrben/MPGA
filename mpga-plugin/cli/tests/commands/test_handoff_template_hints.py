"""T060: Test that handoff template placeholders have adjacent LLM-readable hints.

Each {{placeholder}} in the handoff template should have an adjacent hint
or comment telling the LLM what to put there, not just the bare placeholder name.
"""
import re
from pathlib import Path

HANDOFF_SKILL = Path("/Users/benreich/MPGA/mpga-plugin/skills/handoff/SKILL.md")

# {{placeholders}} that must have adjacent hints
PLACEHOLDERS_REQUIRING_HINTS = [
    "{{DATE}}",
    "{{BRANCH}}",
    "{{SHORT_HASH}} {{COMMIT_MSG}}",
    "{{DIRTY_COUNT}}",
    "{{STASH_COUNT}}",
    "{{GIT_STATUS_SHORT_OUTPUT}}",
    "{{TASK_ID}}",
    "{{TASK_TITLE}}",
    "{{WORK_SUMMARY}}",
    "{{DECISIONS}}",
    "{{BLOCKERS}}",
    "{{IMMEDIATE_NEXT_ACTION}}",
]


def _get_line_context(content: str, placeholder: str) -> str:
    """Return the line(s) around the placeholder."""
    for i, line in enumerate(content.splitlines()):
        if placeholder in line:
            surrounding = content.splitlines()[max(0, i-1):i+2]
            return "\n".join(surrounding)
    return ""


def test_handoff_placeholders_have_hints():
    """Each key {{placeholder}} in handoff template must have an adjacent hint/comment."""
    assert HANDOFF_SKILL.exists(), f"Handoff skill file not found: {HANDOFF_SKILL}"
    content = HANDOFF_SKILL.read_text(encoding="utf-8")

    missing_hints = []
    for placeholder in PLACEHOLDERS_REQUIRING_HINTS:
        # Find the simple placeholder name (strip {{ }})
        name = re.sub(r"[{}]", "", placeholder).strip()
        # Check if there's a hint — either an HTML comment or a # hint line nearby
        # A hint is defined as: within 3 lines of the placeholder, there is a
        # <!-- comment --> or a line starting with "# Hint:" or similar guidance text
        placeholder_simple = re.escape(placeholder)
        lines = content.splitlines()
        found_hint = False
        for i, line in enumerate(lines):
            if placeholder in line:
                # Check surrounding lines for comments or hint markers
                context = "\n".join(lines[max(0, i-2):i+3])
                # HTML comment nearby
                if "<!--" in context and "-->" in context:
                    found_hint = True
                    break
                # Hint marker or explanation nearby
                if "# " in context and any(word in context.lower() for word in [
                    "hint", "e.g.", "example", "format", "from", "run", "date", "iso"
                ]):
                    found_hint = True
                    break
                # Parenthetical explanation on same line
                if re.search(r"\(.*\)", line):
                    found_hint = True
                    break

        if not found_hint:
            missing_hints.append(placeholder)

    assert missing_hints == [], (
        f"The following {{{{placeholders}}}} lack adjacent LLM-readable hints in the handoff template:\n"
        + "\n".join(f"  - {p}" for p in missing_hints)
        + "\n\nAdd <!-- hint --> comments or inline guidance next to each placeholder."
    )
