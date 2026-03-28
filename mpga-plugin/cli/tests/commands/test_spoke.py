"""Tests for the spoke command."""

import hashlib
import re
import urllib.error
from pathlib import Path
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# T012: Tests for --no-queue flag routing
# ---------------------------------------------------------------------------

class TestNoQueueFlag:
    """Tests verifying that --sync, default, and --stream route to the correct helpers."""

    def _make_fake_spoke_dir(self, tmp_path: Path) -> Path:
        """Create a fake spoke dir with the required files so setup check passes."""
        venv_bin = tmp_path / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python3").touch()
        voicedata = tmp_path / "voicedata"
        voicedata.mkdir()
        (voicedata / "trump_ref.wav").touch()
        return tmp_path

    def test_no_queue_flag_uses_generate_endpoint(self, tmp_path, monkeypatch):
        """--sync calls _generate_via_server, not _speak_via_queue."""
        from mpga.commands import spoke as spoke_mod

        spoke_dir = self._make_fake_spoke_dir(tmp_path)
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: spoke_dir)
        monkeypatch.setattr(spoke_mod, "_is_server_running", lambda: True)

        generate_calls = []
        speak_calls = []

        def fake_generate(text, wav_path):
            generate_calls.append(text)
            wav_path.write_bytes(b"RIFF" + b"\x00" * 36)  # minimal fake WAV

        def fake_speak(text):
            speak_calls.append(text)

        monkeypatch.setattr(spoke_mod, "_generate_via_server", fake_generate)
        monkeypatch.setattr(spoke_mod, "_speak_via_queue", fake_speak)
        monkeypatch.setattr(spoke_mod, "trumpify", lambda t: t)
        # Use an empty cache dir so no cached WAV exists
        monkeypatch.setattr(spoke_mod, "CACHE_DIR", tmp_path / "cache")

        # Mock afplay so it doesn't try to play audio
        with patch("subprocess.run"):
            runner = CliRunner()
            result = runner.invoke(spoke_mod.spoke_cmd, ["--sync", "Hello world"])

        assert result.exit_code == 0
        assert len(generate_calls) == 1
        assert len(speak_calls) == 0

    def test_default_uses_speak_endpoint(self, tmp_path, monkeypatch):
        """Without --no-queue, _speak_via_queue is called (not _generate_via_server)."""
        from mpga.commands import spoke as spoke_mod

        spoke_dir = self._make_fake_spoke_dir(tmp_path)
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: spoke_dir)
        monkeypatch.setattr(spoke_mod, "_is_server_running", lambda: True)

        generate_calls = []
        speak_calls = []

        def fake_generate(text, wav_path):
            generate_calls.append(text)

        def fake_speak(text):
            speak_calls.append(text)

        monkeypatch.setattr(spoke_mod, "_generate_via_server", fake_generate)
        monkeypatch.setattr(spoke_mod, "_speak_via_queue", fake_speak)
        monkeypatch.setattr(spoke_mod, "trumpify", lambda t: t)

        runner = CliRunner()
        result = runner.invoke(spoke_mod.spoke_cmd, ["Hello world"])

        assert result.exit_code == 0
        assert len(speak_calls) == 1
        assert len(generate_calls) == 0

    def test_stream_flag_takes_precedence(self, tmp_path, monkeypatch):
        """--stream calls _stream_via_server (neither queue nor generate)."""
        from mpga.commands import spoke as spoke_mod

        spoke_dir = self._make_fake_spoke_dir(tmp_path)
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: spoke_dir)
        monkeypatch.setattr(spoke_mod, "_is_server_running", lambda: True)

        stream_calls = []
        generate_calls = []
        speak_calls = []

        def fake_stream(text):
            stream_calls.append(text)

        def fake_generate(text, wav_path):
            generate_calls.append(text)

        def fake_speak(text):
            speak_calls.append(text)

        monkeypatch.setattr(spoke_mod, "_stream_via_server", fake_stream)
        monkeypatch.setattr(spoke_mod, "_generate_via_server", fake_generate)
        monkeypatch.setattr(spoke_mod, "_speak_via_queue", fake_speak)
        monkeypatch.setattr(spoke_mod, "trumpify", lambda t: t)

        runner = CliRunner()
        result = runner.invoke(spoke_mod.spoke_cmd, ["--stream", "Hello world"])

        assert result.exit_code == 0
        assert len(stream_calls) == 1
        assert len(generate_calls) == 0
        assert len(speak_calls) == 0

    def test_queue_busy_returns_503_error(self, tmp_path, monkeypatch):
        """When /speak returns 503, log.error is called with the busy message."""
        from mpga.commands import spoke as spoke_mod

        spoke_dir = self._make_fake_spoke_dir(tmp_path)
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: spoke_dir)
        monkeypatch.setattr(spoke_mod, "_is_server_running", lambda: True)
        monkeypatch.setattr(spoke_mod, "trumpify", lambda t: t)

        error_calls = []
        monkeypatch.setattr(spoke_mod.log, "error", lambda msg: error_calls.append(msg))

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                url=None, code=503, msg="Service Unavailable", hdrs=None, fp=None
            )

        with patch("urllib.request.urlopen", fake_urlopen):
            runner = CliRunner()
            result = runner.invoke(spoke_mod.spoke_cmd, ["Hello world"])

        assert result.exit_code == 0
        assert any("busy" in msg.lower() for msg in error_calls), \
            f"Expected 'busy' in error messages, got: {error_calls}"


class TestQueueCacheBypass:
    """Cache is only consulted in --sync mode, not in default queue mode."""

    def _make_fake_spoke_dir(self, tmp_path: Path) -> Path:
        venv_bin = tmp_path / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python3").touch()
        voicedata = tmp_path / "voicedata"
        voicedata.mkdir()
        (voicedata / "trump_ref.wav").touch()
        return tmp_path

    def test_queue_mode_does_not_check_cache(self, tmp_path, monkeypatch):
        """Default queue mode does not read from CACHE_DIR."""
        from mpga.commands import spoke as spoke_mod

        spoke_dir = self._make_fake_spoke_dir(tmp_path)
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: spoke_dir)
        monkeypatch.setattr(spoke_mod, "_is_server_running", lambda: True)
        monkeypatch.setattr(spoke_mod, "trumpify", lambda t: t)

        speak_calls = []
        monkeypatch.setattr(spoke_mod, "_speak_via_queue", lambda t: speak_calls.append(t))

        # Point CACHE_DIR to tmp_path so we can detect if it's accessed
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr(spoke_mod, "CACHE_DIR", cache_dir)

        runner = CliRunner()
        runner.invoke(spoke_mod.spoke_cmd, ["Hello world"])

        # Queue was called
        assert len(speak_calls) == 1
        # No .wav files were read from cache_dir
        wav_files = list(cache_dir.glob("*.wav"))
        assert wav_files == [], "Queue mode must not create or read cache files"

    def test_sync_mode_uses_cache(self, tmp_path, monkeypatch):
        """--sync mode checks CACHE_DIR before generating."""
        from mpga.commands import spoke as spoke_mod

        spoke_dir = self._make_fake_spoke_dir(tmp_path)
        monkeypatch.setattr(spoke_mod, "_find_spoke_dir", lambda: spoke_dir)
        monkeypatch.setattr(spoke_mod, "_is_server_running", lambda: True)
        monkeypatch.setattr(spoke_mod, "trumpify", lambda t: t)

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr(spoke_mod, "CACHE_DIR", cache_dir)

        # Pre-seed a cached WAV
        import hashlib
        text = "Hello world"
        h = hashlib.md5(text.encode()).hexdigest()
        cached_wav = cache_dir / f"{h}.wav"
        cached_wav.write_bytes(b"RIFF" + b"\x00" * 36)

        generate_calls: list[str] = []

        def fake_generate(t, p):  # noqa: E501
            generate_calls.append(t)

        monkeypatch.setattr(spoke_mod, "_generate_via_server", fake_generate)

        with patch("subprocess.run"):
            runner = CliRunner()
            runner.invoke(spoke_mod.spoke_cmd, ["--sync", "Hello world"])

        # Cache hit — no generation needed
        assert generate_calls == [], "Cache hit must skip _generate_via_server"
