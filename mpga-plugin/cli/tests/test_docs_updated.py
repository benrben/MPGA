"""T034: CLAUDE.md and INDEX.md document memory commands and new modules."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def claude_md() -> str:
    path = REPO_ROOT / "CLAUDE.md"
    assert path.is_file(), f"Expected {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def index_md() -> str:
    path = REPO_ROOT / "INDEX.md"
    assert path.is_file(), f"Expected {path}"
    return path.read_text(encoding="utf-8")


def test_claude_md_has_memory_commands(claude_md: str) -> None:
    assert "mpga memory search" in claude_md


def test_claude_md_has_index_command(claude_md: str) -> None:
    assert "mpga index url" in claude_md


def test_index_md_has_memory_module(index_md: str) -> None:
    assert "memory/" in index_md


def test_index_md_has_mcp_module(index_md: str) -> None:
    assert "mcp/" in index_md


def test_claude_md_has_progressive_disclosure(claude_md: str) -> None:
    assert "Layer 1" in claude_md
    assert "Layer 2" in claude_md
    assert "Layer 3" in claude_md
