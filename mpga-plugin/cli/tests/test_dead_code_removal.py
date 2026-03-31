"""Tests for T031 — Remove compress_session_resume and dead code paths.

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: compress_session_resume DELETED     → test_compress_session_resume_removed
[x] AC2: build_session_resume still works    → test_build_session_resume_exists
[x] AC3: No references in codebase           → test_no_references_in_codebase
"""
from __future__ import annotations

import subprocess
from pathlib import Path


class TestDeadCodeRemoval:

    def test_compress_session_resume_removed(self) -> None:
        """compress_session_resume must not exist in the compress module."""
        import mpga.bridge.compress as mod

        assert not hasattr(mod, "compress_session_resume"), \
            "compress_session_resume should be deleted from compress.py"

    def test_build_session_resume_exists(self) -> None:
        """build_session_resume must still be importable and callable."""
        from mpga.bridge.compress import build_session_resume

        assert callable(build_session_resume)

    def test_no_references_in_codebase(self) -> None:
        """No source files (outside this test) should reference compress_session_resume."""
        cli_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "compress_session_resume", str(cli_root)],
            capture_output=True,
            text=True,
        )
        this_file_name = "test_dead_code_removal.py"
        remaining = [
            line for line in result.stdout.splitlines()
            if this_file_name not in line
        ]
        assert len(remaining) == 0, f"Found references:\n" + "\n".join(remaining)
