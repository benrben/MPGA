"""Shared fixtures for MPGA CLI tests."""

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _patch_logger_stderr(monkeypatch):
    """Patch log.error to avoid Rich Console.print(stderr=True) which is unsupported in Rich 14+."""
    try:
        from mpga.core.logger import console, log

        original_print = console.print

        def patched_print(*args, **kwargs):
            kwargs.pop("stderr", None)
            return original_print(*args, **kwargs)

        monkeypatch.setattr(console, "print", patched_print)
    except ImportError:
        pass


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory (uses pytest's built-in tmp_path)."""
    return tmp_path


@pytest.fixture
def mpga_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory with an MPGA subdirectory."""
    mpga = tmp_path / "MPGA"
    mpga.mkdir()
    return tmp_path


@pytest.fixture
def scopes_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory with MPGA/scopes/ subdirectory."""
    scopes = tmp_path / "MPGA" / "scopes"
    scopes.mkdir(parents=True)
    return tmp_path


def write_file(base: Path, relative_path: str, content: str) -> Path:
    """Helper to write a file relative to a base directory, creating parents as needed."""
    full = base / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full
