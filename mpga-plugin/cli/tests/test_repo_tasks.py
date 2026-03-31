"""Tests for TaskRepo — CRUD, junction tables, FTS5 search, filter, BM25 ranking."""

from __future__ import annotations

import sqlite3
import pytest

from mpga.board.task import Task
from mpga.db.schema import create_schema
from mpga.db.repos.tasks import TaskRepo


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return TaskRepo(conn)


def make_task(**kwargs) -> Task:
    defaults = dict(
        id="T001",
        title="test task",
        column="backlog",
        status=None,
        priority="medium",
        created="2026-01-01T00:00:00",
        updated="2026-01-01T00:00:00",
    )
    defaults.update(kwargs)
    return Task(**defaults)


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

def test_create_and_get_by_id(repo):
    task = make_task(id="T001", title="hello world")
    created = repo.create(task)
    assert created.id == "T001"
    fetched = repo.get("T001")
    assert fetched is not None
    assert fetched.title == "hello world"
    assert fetched.column == "backlog"


def test_get_nonexistent_returns_none(repo):
    assert repo.get("NOPE") is None


def test_update_fields(repo):
    task = make_task(id="T002", title="original title", priority="low")
    repo.create(task)
    task.title = "updated title"
    task.priority = "high"
    task.column = "in-progress"
    updated = repo.update(task)
    assert updated.title == "updated title"
    fetched = repo.get("T002")
    assert fetched.priority == "high"
    assert fetched.column == "in-progress"


def test_delete(repo):
    task = make_task(id="T003")
    repo.create(task)
    repo.delete("T003")
    assert repo.get("T003") is None


# ---------------------------------------------------------------------------
# Junction tables
# ---------------------------------------------------------------------------

def test_task_scopes_populated_on_create(repo, conn):
    task = make_task(id="T010", scopes=["scope-auth", "scope-db"])
    repo.create(task)
    rows = conn.execute(
        "SELECT scope_id FROM task_scopes WHERE task_id = ? ORDER BY scope_id",
        ("T010",),
    ).fetchall()
    assert [r[0] for r in rows] == ["scope-auth", "scope-db"]


def test_task_tags_populated_on_create(repo, conn):
    task = make_task(id="T011", tags=["bugfix", "security"])
    repo.create(task)
    rows = conn.execute(
        "SELECT tag FROM task_tags WHERE task_id = ? ORDER BY tag",
        ("T011",),
    ).fetchall()
    assert [r[0] for r in rows] == ["bugfix", "security"]


def test_task_deps_populated_on_create(repo, conn):
    task = make_task(id="T012", depends_on=["T001", "T002"])
    repo.create(task)
    rows = conn.execute(
        "SELECT depends_on FROM task_deps WHERE task_id = ? ORDER BY depends_on",
        ("T012",),
    ).fetchall()
    assert [r[0] for r in rows] == ["T001", "T002"]


# ---------------------------------------------------------------------------
# FTS5 search
# ---------------------------------------------------------------------------

def test_fts_search_returns_matching_task(repo):
    task = make_task(id="T020", title="fix authentication bug")
    repo.create(task)
    results = repo.search("auth")
    assert len(results) == 1
    assert results[0].id == "T020"


def test_fts_search_no_match_returns_empty(repo):
    task = make_task(id="T021", title="refactor database layer")
    repo.create(task)
    results = repo.search("authentication")
    assert results == []


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def test_filter_by_column(repo):
    repo.create(make_task(id="T030", column="todo"))
    repo.create(make_task(id="T031", column="done"))
    results = repo.filter(column="todo")
    assert len(results) == 1
    assert results[0].id == "T030"


def test_filter_by_priority(repo):
    repo.create(make_task(id="T032", priority="critical"))
    repo.create(make_task(id="T033", priority="low"))
    results = repo.filter(priority="critical")
    assert len(results) == 1
    assert results[0].id == "T032"


def test_filter_by_milestone(repo):
    repo.create(make_task(id="T034", milestone="M001"))
    repo.create(make_task(id="T035", milestone="M002"))
    results = repo.filter(milestone="M001")
    assert len(results) == 1
    assert results[0].id == "T034"


def test_filter_by_scope(repo):
    repo.create(make_task(id="T036", scopes=["scope-api"]))
    repo.create(make_task(id="T037", scopes=["scope-ui"]))
    results = repo.filter(scope="scope-api")
    assert len(results) == 1
    assert results[0].id == "T036"


def test_filter_no_criteria_returns_all(repo):
    repo.create(make_task(id="T038"))
    repo.create(make_task(id="T039"))
    results = repo.filter()
    ids = {t.id for t in results}
    assert "T038" in ids
    assert "T039" in ids


# ---------------------------------------------------------------------------
# BM25 ranking
# ---------------------------------------------------------------------------

def test_bm25_ranking_most_relevant_first(repo):
    # T050: title mentions "auth" once
    repo.create(make_task(id="T050", title="fix auth", body="unrelated"))
    # T051: title and body both mention "auth" — more relevant
    repo.create(make_task(id="T051", title="auth authentication", body="auth token auth"))
    # T052: no mention of auth
    repo.create(make_task(id="T052", title="refactor pipeline", body="ci cd stuff"))

    results = repo.search("auth", limit=10)
    assert len(results) >= 2
    # T051 is more relevant; it should appear before T050
    ids = [t.id for t in results]
    assert "T052" not in ids
    assert ids.index("T051") < ids.index("T050")
