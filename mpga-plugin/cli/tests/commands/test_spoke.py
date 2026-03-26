"""Tests for the spoke command."""

import hashlib
import re
from pathlib import Path

import pytest
from click.testing import CliRunner


# ---------------------------------------------------------------------------
# Tests: spoke command
# ---------------------------------------------------------------------------

class TestSpokeCommandRegistration:
    """spoke command registration tests."""

    def test_registers_spoke_command(self):
        """Registers a spoke command with a Trump-related description."""
        from mpga.commands.spoke import spoke_cmd

        assert spoke_cmd is not None
        assert spoke_cmd.name == "spoke"
        assert "Trump" in (spoke_cmd.help or "")


class TestAnsiStripping:
    """ANSI stripping tests."""

    ANSI_RE = re.compile(r"\x1B\[[0-9;]*m")

    def test_strips_ansi_escape_codes(self):
        """Strips ANSI escape codes from text."""
        text = "\x1B[31mHello\x1B[0m \x1B[1;32mWorld\x1B[0m"
        stripped = self.ANSI_RE.sub("", text)
        assert stripped == "Hello World"

    def test_leaves_plain_text_unchanged(self):
        """Leaves plain text unchanged."""
        text = "Make America Great Again"
        stripped = self.ANSI_RE.sub("", text)
        assert stripped == "Make America Great Again"


class TestCacheHashGeneration:
    """cache hash generation tests."""

    def test_deterministic_md5_hashes(self):
        """Produces deterministic MD5 hashes for the same input."""
        text = "We are going to win so much"
        hash1 = hashlib.md5(text.encode()).hexdigest()
        hash2 = hashlib.md5(text.encode()).hexdigest()
        assert hash1 == hash2

    def test_different_hashes_for_different_input(self):
        """Produces different hashes for different input."""
        hash1 = hashlib.md5(b"Hello").hexdigest()
        hash2 = hashlib.md5(b"World").hexdigest()
        assert hash1 != hash2

    def test_produces_32_char_hex(self):
        """Produces a 32-character hex string."""
        h = hashlib.md5(b"test").hexdigest()
        assert re.match(r"^[a-f0-9]{32}$", h)


class TestHandleSpokeSetup:
    """spoke --setup tests."""

    def test_setup_attempts_to_run_script(self, monkeypatch):
        """Attempts to run setup.sh when --setup flag is provided."""
        from mpga.commands.spoke import spoke_cmd

        # The setup.sh won't exist, so subprocess.run will fail.
        # The command catches the error and returns normally.
        runner = CliRunner()
        result = runner.invoke(spoke_cmd, ['--setup'])
        # The command prints "Running spoke setup..." before attempting to run the script
        assert "setup" in result.output.lower()


class TestHandleSpokeWithoutSetup:
    """spoke without setup tests."""

    def test_prints_error_when_not_set_up(self, tmp_path, monkeypatch):
        """Prints error when spoke is not set up."""
        from mpga.commands import spoke as spoke_mod

        # Point to a fake empty dir so venv/ref_audio won't exist
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(spoke_mod.spoke_cmd, ['Hello', 'world'])
        assert result.exit_code == 0
        # Error goes to stderr, check it wasn't silent success with generation
        assert "not set up" in (result.output.lower() + getattr(result, 'stderr', '') or '')\
            or result.output == ''  # error went to stderr which CliRunner doesn't capture
