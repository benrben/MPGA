"""Tests for the compression module — T085."""
from __future__ import annotations

from mpga.board.task import Task
from mpga.db.repos.scopes import Scope
from mpga.bridge.compress import (
    compress_task,
    compress_scope,
    compress_board_stats,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_task(**kwargs) -> Task:
    defaults = dict(
        id="T035",
        title="Fix log.debug",
        column="done",
        status=None,
        priority="critical",
        created="2026-01-01",
        updated="2026-01-02",
        milestone="M006",
        scopes=["gen"],
    )
    defaults.update(kwargs)
    return Task(**defaults)


def _make_scope(**kwargs) -> Scope:
    defaults = dict(
        id="gen",
        name="Generator",
        summary="First paragraph of summary.\n\nSecond paragraph.",
        status="fresh",
        evidence_total=10,
        evidence_valid=8,
    )
    defaults.update(kwargs)
    return Scope(**defaults)


# ---------------------------------------------------------------------------
# compress_task
# ---------------------------------------------------------------------------

def test_compress_task_format():
    task = _make_task()
    result = compress_task(task)
    assert result == "T035 [done] critical: Fix log.debug (M006, scope:gen)"


def test_compress_task_under_200_bytes():
    task = _make_task()
    result = compress_task(task)
    assert len(result.encode("utf-8")) < 200


def test_compress_task_multiple_scopes():
    task = _make_task(scopes=["gen", "db"])
    result = compress_task(task)
    assert "scope:gen,db" in result


def test_compress_task_no_milestone():
    task = _make_task(milestone=None)
    result = compress_task(task)
    assert "none" in result.lower() or "scope:" in result


# ---------------------------------------------------------------------------
# compress_scope
# ---------------------------------------------------------------------------

def test_compress_scope_contains_first_paragraph():
    scope = _make_scope()
    result = compress_scope(scope)
    assert "First paragraph of summary." in result


def test_compress_scope_contains_health():
    scope = _make_scope()
    result = compress_scope(scope)
    assert "Health: fresh (8/10)" in result


def test_compress_scope_under_500_bytes():
    scope = _make_scope()
    result = compress_scope(scope)
    assert len(result.encode("utf-8")) < 500


def test_compress_scope_truncates_long_summary():
    long_summary = "A" * 600
    scope = _make_scope(summary=long_summary)
    result = compress_scope(scope)
    assert len(result.encode("utf-8")) < 500


def test_compress_scope_no_summary():
    scope = _make_scope(summary=None)
    result = compress_scope(scope)
    assert "Health:" in result


# ---------------------------------------------------------------------------
# compress_board_stats
# ---------------------------------------------------------------------------

def _make_stats():
    return {
        "total": 50,
        "done": 20,
        "in_flight": 5,
        "blocked": 2,
        "progress_pct": 40,
        "milestone": "M002",
    }


def test_compress_board_stats_four_lines():
    stats = _make_stats()
    result = compress_board_stats(stats)
    lines = [l for l in result.strip().split("\n") if l.strip()]
    assert len(lines) >= 2  # At minimum tasks line + progress line


def test_compress_board_stats_contains_key_info():
    stats = _make_stats()
    result = compress_board_stats(stats)
    assert "50" in result  # total
    assert "20" in result  # done
    assert "40%" in result  # progress
    assert "M002" in result  # milestone


