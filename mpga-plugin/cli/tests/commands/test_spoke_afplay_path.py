"""RED → GREEN: afplay path validation tests for spoke.py.

Ensures that subprocess.run(['afplay', path]) is only called with paths
within allowed directories (/tmp or the MPGA spoke-cache dir), preventing
path traversal and arbitrary file playback.
"""

from __future__ import annotations

import pathlib
from unittest.mock import patch, MagicMock

import pytest

from mpga.commands.spoke import _validate_afplay_path, CACHE_DIR


_TMP = pathlib.Path("/tmp")
_ALLOWED_DIRS = [_TMP, CACHE_DIR]


# ---------------------------------------------------------------------------
# Path traversal — must be rejected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_path",
    [
        "/tmp/../etc/passwd",
        "/tmp/../../etc/shadow",
        str(CACHE_DIR) + "/../../../etc/passwd",
        "/tmp/audio/../../etc/hosts",
    ],
)
def test_path_traversal_rejected(raw_path: str) -> None:
    """Paths containing .. components (after resolution outside allowed dirs) must be rejected."""
    with pytest.raises(ValueError, match="not allowed|outside|disallowed|traversal"):
        _validate_afplay_path(raw_path)


# ---------------------------------------------------------------------------
# Absolute paths outside allowed dirs — must be rejected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw_path",
    [
        "/etc/passwd",
        "/etc/shadow",
        "/var/log/system.log",
        "/Users/root/secret.wav",
        "/home/attacker/evil.wav",
    ],
)
def test_absolute_path_outside_allowed_rejected(raw_path: str) -> None:
    """Absolute paths outside /tmp and CACHE_DIR must be rejected."""
    with pytest.raises(ValueError, match="not allowed|outside|disallowed"):
        _validate_afplay_path(raw_path)


# ---------------------------------------------------------------------------
# Valid paths — must be accepted
# ---------------------------------------------------------------------------

def test_tmp_path_allowed() -> None:
    """Paths inside /tmp must be accepted."""
    path = str(_TMP / "test_audio_abc123.wav")
    # Should not raise
    result = _validate_afplay_path(path)
    assert result == pathlib.Path(path).resolve()


def test_cache_dir_path_allowed() -> None:
    """Paths inside CACHE_DIR must be accepted."""
    path = str(CACHE_DIR / "abc123def456.wav")
    result = _validate_afplay_path(path)
    assert result == pathlib.Path(path).resolve()
