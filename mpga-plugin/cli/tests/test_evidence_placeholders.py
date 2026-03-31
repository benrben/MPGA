"""T024: Test that no scope docs contain literal unresolved [E] file:line placeholders.

A literal [E] file:line with no filename or line number substituted is an invalid
evidence link — it means the sync process failed to resolve the anchor.

We check all task and board markdown files specifically, as those are scope docs
that should have resolved links, not template examples.
"""
import re
from pathlib import Path


# Scope docs are in the MPGA board and task files
SCOPE_DOC_DIRS = [
    Path("/Users/benreich/MPGA/MPGA/board"),
]

# Pattern: literal [E] file:line (not inside backtick code blocks or example text)
# We look for it as a standalone evidence link (starts with [E] file:line exactly)
LITERAL_PLACEHOLDER_PATTERN = re.compile(r"^\s*\[E\]\s+file:line\b", re.MULTILINE)


def test_no_literal_evidence_placeholders_in_scope_docs():
    """Scope docs must not contain unresolved [E] file:line placeholder strings."""
    violations = []
    for base_dir in SCOPE_DOC_DIRS:
        if not base_dir.exists():
            continue
        for md_file in base_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="replace")
            if LITERAL_PLACEHOLDER_PATTERN.search(content):
                violations.append(str(md_file))
    assert violations == [], (
        f"Found unresolved [E] file:line placeholders in scope docs: {violations}. "
        "Replace with real evidence links or remove the placeholder."
    )
