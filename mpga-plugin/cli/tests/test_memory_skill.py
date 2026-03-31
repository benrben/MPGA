"""Tests for the mpga-memory skill SKILL.md file."""
from __future__ import annotations

from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "mpga-memory" / "SKILL.md"


def _read_skill() -> str:
    assert SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"
    return SKILL_PATH.read_text()


def test_memory_skill_exists() -> None:
    assert SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"


def test_skill_mentions_search() -> None:
    content = _read_skill()
    assert "mpga memory search" in content


def test_skill_mentions_context() -> None:
    content = _read_skill()
    assert "mpga memory context" in content


def test_skill_mentions_get() -> None:
    content = _read_skill()
    assert "mpga memory get" in content
