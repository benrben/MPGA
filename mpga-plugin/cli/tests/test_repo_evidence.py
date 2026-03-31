"""Tests for EvidenceRepo — CRUD + FTS5 search."""

from __future__ import annotations

import sqlite3
import pytest

from mpga.db.schema import create_schema
from mpga.db.repos.evidence import EvidenceRepo
from mpga.evidence.parser import EvidenceLink, EvidenceStats


@pytest.fixture()
def conn():
    """In-memory SQLite connection with schema applied."""
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)
    yield c
    c.close()


@pytest.fixture()
def repo(conn):
    return EvidenceRepo(conn)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_create_returns_int_id(repo):
    link = EvidenceLink(raw="[E] src/foo.ts:1-10", type="valid", confidence=1.0, filepath="src/foo.ts")
    eid = repo.create(link, scope_id=None, task_id=None)
    assert isinstance(eid, int)
    assert eid > 0


def test_get_returns_evidence_link(repo):
    link = EvidenceLink(
        raw="[E] src/foo.ts:1-10",
        type="valid",
        confidence=1.0,
        filepath="src/foo.ts",
        start_line=1,
        end_line=10,
    )
    eid = repo.create(link, scope_id=None, task_id=None)
    result = repo.get(eid)
    assert result is not None
    assert isinstance(result, EvidenceLink)
    assert result.filepath == "src/foo.ts"
    assert result.type == "valid"
    assert result.start_line == 1
    assert result.end_line == 10


def test_get_missing_returns_none(repo):
    assert repo.get(9999) is None


def test_delete_removes_record(repo):
    link = EvidenceLink(raw="[E] src/bar.ts", type="valid", confidence=1.0, filepath="src/bar.ts")
    eid = repo.create(link, scope_id=None, task_id=None)
    repo.delete(eid)
    assert repo.get(eid) is None


# ---------------------------------------------------------------------------
# FTS5 search
# ---------------------------------------------------------------------------

def test_fts_search_by_filepath(repo):
    link = EvidenceLink(
        raw="[E] src/auth/jwt.ts:5-15",
        type="valid",
        confidence=1.0,
        filepath="src/auth/jwt.ts",
    )
    repo.create(link, scope_id=None, task_id=None)
    results = repo.search("auth")
    assert len(results) >= 1
    assert any(r.filepath == "src/auth/jwt.ts" for r in results)


def test_fts_search_no_match_returns_empty(repo):
    results = repo.search("xyzzy_nonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# find — filter by type
# ---------------------------------------------------------------------------

def test_find_by_type_valid(repo):
    repo.create(EvidenceLink(raw="[E] a.ts", type="valid", confidence=1.0, filepath="a.ts"), None, None)
    repo.create(EvidenceLink(raw="[Stale:2026-01-01] b.ts", type="stale", confidence=0.0, filepath="b.ts"), None, None)
    results = repo.find(type="valid")
    assert all(r.type == "valid" for r in results)
    assert len(results) == 1


def test_find_by_type_stale(repo):
    repo.create(EvidenceLink(raw="[Stale:2026-01-01] b.ts", type="stale", confidence=0.0, filepath="b.ts"), None, None)
    repo.create(EvidenceLink(raw="[E] a.ts", type="valid", confidence=1.0, filepath="a.ts"), None, None)
    results = repo.find(type="stale")
    assert all(r.type == "stale" for r in results)
    assert len(results) == 1


def test_find_by_type_unknown(repo):
    repo.create(EvidenceLink(raw="[Unknown] desc", type="unknown", confidence=0.0, description="desc"), None, None)
    results = repo.find(type="unknown")
    assert len(results) == 1
    assert results[0].type == "unknown"


def test_find_by_type_deprecated(repo):
    repo.create(EvidenceLink(raw="[Deprecated] c.ts", type="deprecated", confidence=0.5, filepath="c.ts"), None, None)
    results = repo.find(type="deprecated")
    assert len(results) == 1
    assert results[0].type == "deprecated"


# ---------------------------------------------------------------------------
# find — filter by scope_id
# ---------------------------------------------------------------------------

def test_find_by_scope_id(repo, conn):
    # Insert a scope so the FK doesn't complain
    conn.execute(
        "INSERT INTO scopes (id, name, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
        ("scope-A", "Scope A"),
    )
    conn.commit()
    link_a = EvidenceLink(raw="[E] a.ts", type="valid", confidence=1.0, filepath="a.ts")
    link_b = EvidenceLink(raw="[E] b.ts", type="valid", confidence=1.0, filepath="b.ts")
    repo.create(link_a, scope_id="scope-A", task_id=None)
    repo.create(link_b, scope_id=None, task_id=None)
    results = repo.find(scope_id="scope-A")
    assert len(results) == 1
    assert results[0].filepath == "a.ts"


# ---------------------------------------------------------------------------
# find — filter by filepath
# ---------------------------------------------------------------------------

def test_find_by_filepath(repo):
    repo.create(EvidenceLink(raw="[E] src/auth/jwt.ts", type="valid", confidence=1.0, filepath="src/auth/jwt.ts"), None, None)
    repo.create(EvidenceLink(raw="[E] src/other.ts", type="valid", confidence=1.0, filepath="src/other.ts"), None, None)
    results = repo.find(filepath="src/auth/jwt.ts")
    assert len(results) == 1
    assert results[0].filepath == "src/auth/jwt.ts"


# ---------------------------------------------------------------------------
# find — no filters returns all (up to limit)
# ---------------------------------------------------------------------------

def test_find_no_filter_returns_all(repo):
    for i in range(3):
        repo.create(EvidenceLink(raw=f"[E] f{i}.ts", type="valid", confidence=1.0, filepath=f"f{i}.ts"), None, None)
    results = repo.find()
    assert len(results) == 3


def test_find_limit_respected(repo):
    for i in range(10):
        repo.create(EvidenceLink(raw=f"[E] f{i}.ts", type="valid", confidence=1.0, filepath=f"f{i}.ts"), None, None)
    results = repo.find(limit=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def test_stats_empty_db(repo):
    s = repo.stats()
    assert isinstance(s, EvidenceStats)
    assert s.total == 0
    assert s.health_pct == 100


def test_stats_all_valid(repo):
    for i in range(4):
        repo.create(EvidenceLink(raw=f"[E] f{i}.ts", type="valid", confidence=1.0, filepath=f"f{i}.ts"), None, None)
    s = repo.stats()
    assert s.total == 4
    assert s.valid == 4
    assert s.stale == 0
    assert s.unknown == 0
    assert s.deprecated == 0
    assert s.health_pct == 100


def test_stats_mixed(repo):
    repo.create(EvidenceLink(raw="[E] a.ts", type="valid", confidence=1.0, filepath="a.ts"), None, None)
    repo.create(EvidenceLink(raw="[E] b.ts", type="valid", confidence=1.0, filepath="b.ts"), None, None)
    repo.create(EvidenceLink(raw="[Stale:2026-01-01] c.ts", type="stale", confidence=0.0, filepath="c.ts"), None, None)
    repo.create(EvidenceLink(raw="[Unknown] desc", type="unknown", confidence=0.0, description="desc"), None, None)
    s = repo.stats()
    assert s.total == 4
    assert s.valid == 2
    assert s.stale == 1
    assert s.unknown == 1
    assert s.health_pct == 50


def test_stats_scoped(repo, conn):
    conn.execute(
        "INSERT INTO scopes (id, name, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
        ("scope-X", "Scope X"),
    )
    conn.commit()
    repo.create(EvidenceLink(raw="[E] a.ts", type="valid", confidence=1.0, filepath="a.ts"), scope_id="scope-X", task_id=None)
    repo.create(EvidenceLink(raw="[Stale:2026-01-01] b.ts", type="stale", confidence=0.0, filepath="b.ts"), scope_id="scope-X", task_id=None)
    # Link in different scope — should not count
    repo.create(EvidenceLink(raw="[E] c.ts", type="valid", confidence=1.0, filepath="c.ts"), scope_id=None, task_id=None)
    s = repo.stats(scope_id="scope-X")
    assert s.total == 2
    assert s.valid == 1
    assert s.stale == 1
    assert s.health_pct == 50
