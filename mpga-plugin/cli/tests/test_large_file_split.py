"""T031: Test that no single source file exceeds 500 lines.

Large files are harder to understand and maintain. The 822-line
scope_md.py should be split into focused modules.
"""
import subprocess
from pathlib import Path

SRC_DIR = Path("/Users/benreich/MPGA/mpga-plugin/cli/src/mpga")
MAX_LINES = 500


def test_no_source_file_exceeds_max_lines():
    """No source .py file should exceed 500 lines."""
    oversized = []
    for py_file in SRC_DIR.rglob("*.py"):
        line_count = len(py_file.read_text(encoding="utf-8", errors="replace").splitlines())
        if line_count > MAX_LINES:
            oversized.append((py_file, line_count))

    if oversized:
        details = "\n".join(f"  {f} ({n} lines)" for f, n in sorted(oversized, key=lambda x: -x[1]))
        assert False, (
            f"Files exceeding {MAX_LINES} lines:\n{details}\n"
            "Split these into focused modules."
        )
