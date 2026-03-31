"""Tests for ScopeRepo — CRUD + FTS5 search."""

from __future__ import annotations

import sqlite3

import pytest

from mpga.db.schema import create_schema
from mpga.db.repos.scopes import Scope, ScopeRepo


@pytest.fixture
def conn():
    """In-memory SQLite connection with schema applied."""
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)
    return c


@pytest.fixture
def repo(conn):
    return ScopeRepo(conn)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_create_and_read_scope(repo):
    scope = Scope(id="S001", name="Auth", summary="Auth scope", content="auth stuff")
    created = repo.create(scope)
    assert created.id == "S001"

    fetched = repo.get("S001")
    assert fetched is not None
    assert fetched.name == "Auth"
    assert fetched.summary == "Auth scope"


def test_get_nonexistent_returns_none(repo):
    assert repo.get("MISSING") is None


def test_update_scope(repo):
    scope = Scope(id="S002", name="Old Name", summary="old")
    repo.create(scope)

    scope.name = "New Name"
    scope.summary = "updated summary"
    updated = repo.update(scope)

    assert updated.name == "New Name"
    fetched = repo.get("S002")
    assert fetched.name == "New Name"
    assert fetched.summary == "updated summary"


def test_delete_scope(repo):
    scope = Scope(id="S003", name="To Delete")
    repo.create(scope)
    repo.delete("S003")
    assert repo.get("S003") is None


def test_list_all(repo):
    repo.create(Scope(id="S010", name="Alpha"))
    repo.create(Scope(id="S011", name="Beta"))
    all_scopes = repo.list_all()
    ids = [s.id for s in all_scopes]
    assert "S010" in ids
    assert "S011" in ids


# ---------------------------------------------------------------------------
# FTS5 search
# ---------------------------------------------------------------------------

def test_fts_search_finds_matching_scope(repo):
    scope = Scope(
        id="S100",
        name="Auth Module",
        summary="authentication middleware",
        content="This scope covers authentication middleware for the API gateway.",
    )
    repo.create(scope)

    results = repo.search("auth")
    assert len(results) >= 1
    scope_result, snippet = results[0]
    assert scope_result.id == "S100"


def test_fts_search_returns_snippet_not_full_body(repo):
    long_content = ("word " * 200) + "authentication middleware" + (" word" * 200)
    scope = Scope(
        id="S101",
        name="Big Scope",
        summary="nothing special",
        content=long_content,
    )
    repo.create(scope)

    results = repo.search("authentication")
    assert len(results) >= 1
    _, snippet = results[0]
    # Snippet must be shorter than the full content
    assert len(snippet) < len(long_content)
    assert snippet  # non-empty


def test_fts_search_no_match_returns_empty(repo):
    repo.create(Scope(id="S102", name="Logging", summary="log stuff", content="log log log"))
    results = repo.search("xyzzy_not_real_term")
    assert results == []


def test_fts_search_ranked_by_relevance(repo):
    # S200 mentions auth many times; S201 mentions it once
    repo.create(Scope(
        id="S200",
        name="Auth Heavy",
        summary="authentication authentication authentication",
        content="authentication middleware auth token auth flow",
    ))
    repo.create(Scope(
        id="S201",
        name="Logging",
        summary="logging scope",
        content="logging and monitoring, one mention of authentication here",
    ))

    results = repo.search("authentication", limit=10)
    ids = [s.id for s, _ in results]
    # S200 should appear before S201 (higher relevance)
    assert "S200" in ids
    assert "S201" in ids
    assert ids.index("S200") < ids.index("S201")
