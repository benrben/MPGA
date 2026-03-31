"""T041: Test that deleted modules have tombstone REMOVED.md files.

When a module is deleted, a REMOVED.md tombstone should exist to document
what was removed and why, helping developers understand the history.
"""
from pathlib import Path


PIPELINE_DIR = Path("/Users/benreich/MPGA/mpga-plugin/cli/src/mpga/pipeline")


def test_pipeline_tombstone_exists():
    """Deleted pipeline/ module must have a REMOVED.md tombstone."""
    tombstone = PIPELINE_DIR / "REMOVED.md"
    assert tombstone.exists(), (
        f"Missing tombstone: {tombstone}. "
        "The pipeline/ module was deleted — document why with REMOVED.md."
    )
    content = tombstone.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, "REMOVED.md tombstone is empty."
