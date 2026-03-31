"""Tests for SyntaxWarning-free regex strings in the scanner module (T036)."""

from __future__ import annotations

import subprocess
import sys
import warnings

import pytest


class TestScannerRawStrings:
    """scanner module uses raw strings for all regex patterns."""

    def test_import_raises_no_syntax_warning(self):
        """Importing mpga.core.scanner emits no SyntaxWarning."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            # If a SyntaxWarning is raised, this will error
            import mpga.core.scanner  # noqa: F401

    def test_import_with_w_error_exits_zero(self):
        """python -W error -c 'import mpga.core.scanner' exits 0."""
        result = subprocess.run(
            [sys.executable, "-W", "error", "-c", "import mpga.core.scanner"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"SyntaxWarning detected on import:\n{result.stderr}"
        )

    def test_no_bare_regex_escape_sequences_in_source(self):
        """scanner.py source contains no bare invalid escape sequences in string literals."""
        from pathlib import Path
        import re

        scanner_path = (
            Path(__file__).parent.parent.parent
            / "src" / "mpga" / "core" / "scanner.py"
        )
        source = scanner_path.read_text(encoding="utf-8")

        # Pattern: a non-raw string literal containing a backslash followed by a
        # character that is not a recognised Python escape (not n, t, r, \, ', ", 0-9,
        # x, u, U, N, a, b, f, v, newline).
        # We check specifically for the most common regex escapes used in non-raw strings.
        problematic = re.findall(
            r'(?<![r])"[^"]*\\[.()\[\]{}+*?|^$][^"]*"',
            source,
        )
        assert not problematic, (
            f"Found bare regex escape sequences in non-raw strings: {problematic}"
        )
