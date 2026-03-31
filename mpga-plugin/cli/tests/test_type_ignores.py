"""T034: Test that type: ignore suppressions are reduced to < 40.

Excessive type: ignore comments hide real type errors. Target is < 40
(reduced from the original 67).
"""
import subprocess
from pathlib import Path

SRC_DIR = Path("/Users/benreich/MPGA/mpga-plugin/cli/src")


def _count_type_ignores() -> int:
    result = subprocess.run(
        ["grep", "-rn", "type: ignore", str(SRC_DIR)],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return len(lines)


def test_type_ignore_count_below_threshold():
    """There must be fewer than 40 'type: ignore' suppressions in the source."""
    count = _count_type_ignores()
    assert count < 40, (
        f"Found {count} 'type: ignore' suppressions in src/. "
        "Add specific error codes like 'type: ignore[assignment]' and remove unnecessary ones."
    )
