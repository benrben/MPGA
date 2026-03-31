"""Tests for migrate command — import Markdown/JSON into SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.commands.migrate import (
    migrate_tasks,
    migrate_scopes,
    migrate_milestones,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    db_path = str(tmp_path / ".mpga" / "mpga.db")
    c = get_connection(db_path)
    create_schema(c)
    return c


@pytest.fixture
def tasks_dir(tmp_path: Path) -> Path:
    """Fixture: tasks directory with two sample task .md files."""
    td = tmp_path / "tasks"
    td.mkdir()
    task1 = """\
---
id: "T001"
title: "First task"
status: "active"
column: "backlog"
priority: "high"
milestone: "M001"
phase: null
created: "2026-01-01T00:00:00"
updated: "2026-01-02T00:00:00"
assigned: null
depends_on: []
blocks: []
scopes: ["scope-a"]
tdd_stage: null
lane_id: null
run_status: "queued"
current_agent: null
file_locks: []
scope_locks: []
started_at: null
finished_at: null
heartbeat_at: null
evidence_expected: []
evidence_produced: []
tags: ["alpha"]
time_estimate: "10min"
---

# T001: First task

Some body text.
"""
    task2 = """\
---
id: "T002"
title: "Second task"
status: "active"
column: "todo"
priority: "medium"
milestone: null
phase: null
created: "2026-01-03T00:00:00"
updated: "2026-01-04T00:00:00"
assigned: null
depends_on: ["T001"]
blocks: []
scopes: []
tdd_stage: "green"
lane_id: null
run_status: "queued"
current_agent: null
file_locks: []
scope_locks: []
started_at: null
finished_at: null
heartbeat_at: null
evidence_expected: []
evidence_produced: []
tags: []
time_estimate: "5min"
---

# T002: Second task
"""
    (td / "T001-first-task.md").write_text(task1, encoding="utf-8")
    (td / "T002-second-task.md").write_text(task2, encoding="utf-8")
    return td


@pytest.fixture
def scopes_dir(tmp_path: Path) -> Path:
    """Fixture: scopes directory with sample .md files."""
    sd = tmp_path / "scopes"
    sd.mkdir()
    scope_content = """\
# scope-a

A test scope.

## Evidence

- [E] src/foo.py:10-20 :: my_func
- [Unknown] some unknown thing
"""
    (sd / "scope-a.md").write_text(scope_content, encoding="utf-8")
    return sd


@pytest.fixture
def milestones_dir(tmp_path: Path) -> Path:
    """Fixture: milestones directory with a sample milestone."""
    md = tmp_path / "milestones"
    md.mkdir()
    m_dir = md / "M001-first-milestone"
    m_dir.mkdir()
    (m_dir / "PLAN.md").write_text("# Plan\n\nThis is the plan.", encoding="utf-8")
    (m_dir / "SUMMARY.md").write_text("# Summary\n\nThis is the summary.", encoding="utf-8")
    return md


# ---------------------------------------------------------------------------
# migrate_tasks
# ---------------------------------------------------------------------------


def test_migrate_tasks_imports_tasks(conn, tasks_dir):
    """migrate_tasks inserts tasks from .md files into the tasks table."""
    counts = migrate_tasks(conn, str(tasks_dir))
    rows = conn.execute("SELECT id FROM tasks ORDER BY id").fetchall()
    ids = [r[0] for r in rows]
    assert "T001" in ids
    assert "T002" in ids


def test_migrate_tasks_imports_junction_tables(conn, tasks_dir):
    """migrate_tasks inserts scopes/tags/deps into junction tables."""
    migrate_tasks(conn, str(tasks_dir))
    # T001 has scope-a
    scope_rows = conn.execute(
        "SELECT scope_id FROM task_scopes WHERE task_id = 'T001'"
    ).fetchall()
    assert any(r[0] == "scope-a" for r in scope_rows)
    # T001 has tag alpha
    tag_rows = conn.execute(
        "SELECT tag FROM task_tags WHERE task_id = 'T001'"
    ).fetchall()
    assert any(r[0] == "alpha" for r in tag_rows)
    # T002 depends on T001
    dep_rows = conn.execute(
        "SELECT depends_on FROM task_deps WHERE task_id = 'T002'"
    ).fetchall()
    assert any(r[0] == "T001" for r in dep_rows)


def test_migrate_tasks_returns_counts(conn, tasks_dir):
    """migrate_tasks returns a counts dict with tasks key."""
    counts = migrate_tasks(conn, str(tasks_dir))
    assert isinstance(counts, dict)
    assert counts["tasks"] == 2


def test_migrate_tasks_idempotent(conn, tasks_dir):
    """Running migrate_tasks twice does not duplicate tasks."""
    migrate_tasks(conn, str(tasks_dir))
    migrate_tasks(conn, str(tasks_dir))
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert count == 2


# ---------------------------------------------------------------------------
# migrate_scopes
# ---------------------------------------------------------------------------


def test_migrate_scopes_imports_scopes(conn, scopes_dir):
    """migrate_scopes inserts scope rows from .md files."""
    counts = migrate_scopes(conn, str(scopes_dir))
    row = conn.execute("SELECT id, name FROM scopes WHERE id = 'scope-a'").fetchone()
    assert row is not None
    assert row[1] == "scope-a"


def test_migrate_scopes_imports_evidence(conn, scopes_dir):
    """migrate_scopes parses and inserts evidence links from scope content."""
    migrate_scopes(conn, str(scopes_dir))
    evidence_rows = conn.execute(
        "SELECT raw, type FROM evidence WHERE scope_id = 'scope-a'"
    ).fetchall()
    types = {r[1] for r in evidence_rows}
    assert "valid" in types
    assert "unknown" in types


def test_migrate_scopes_rebuilds_evidence_fts(conn, scopes_dir):
    """migrate_scopes refreshes the evidence FTS index."""
    migrate_scopes(conn, str(scopes_dir))
    count = conn.execute("SELECT COUNT(*) FROM evidence_fts").fetchone()[0]
    assert count >= 1


def test_migrate_scopes_returns_counts(conn, scopes_dir):
    """migrate_scopes returns counts dict with scopes and evidence keys."""
    counts = migrate_scopes(conn, str(scopes_dir))
    assert isinstance(counts, dict)
    assert counts["scopes"] == 1
    assert counts["evidence"] >= 2


def test_migrate_scopes_idempotent(conn, scopes_dir):
    """Running migrate_scopes twice does not duplicate scope rows."""
    migrate_scopes(conn, str(scopes_dir))
    migrate_scopes(conn, str(scopes_dir))
    count = conn.execute("SELECT COUNT(*) FROM scopes WHERE id = 'scope-a'").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# migrate_milestones
# ---------------------------------------------------------------------------


def test_migrate_milestones_imports_milestones(conn, milestones_dir):
    """migrate_milestones inserts milestone rows from M*-* directories."""
    counts = migrate_milestones(conn, str(milestones_dir))
    row = conn.execute(
        "SELECT id, name FROM milestones WHERE id = 'M001'"
    ).fetchone()
    assert row is not None
    assert "first-milestone" in row[1] or "M001" in row[1]


def test_migrate_milestones_reads_plan_and_summary(conn, milestones_dir):
    """migrate_milestones reads PLAN.md and SUMMARY.md content."""
    migrate_milestones(conn, str(milestones_dir))
    row = conn.execute(
        "SELECT design, summary FROM milestones WHERE id = 'M001'"
    ).fetchone()
    assert row is not None
    # PLAN.md content maps to design column
    assert row[0] is not None and "plan" in row[0].lower()
    # SUMMARY.md content maps to summary column
    assert row[1] is not None and "summary" in row[1].lower()


def test_migrate_milestones_returns_counts(conn, milestones_dir):
    """migrate_milestones returns counts dict with milestones key."""
    counts = migrate_milestones(conn, str(milestones_dir))
    assert isinstance(counts, dict)
    assert counts["milestones"] == 1


def test_migrate_milestones_idempotent(conn, milestones_dir):
    """Running migrate_milestones twice does not duplicate milestone rows."""
    migrate_milestones(conn, str(milestones_dir))
    migrate_milestones(conn, str(milestones_dir))
    count = conn.execute("SELECT COUNT(*) FROM milestones WHERE id = 'M001'").fetchone()[0]
    assert count == 1


# ---------------------------------------------------------------------------
# Full verification: combined counts dict
# ---------------------------------------------------------------------------


def test_full_migration_returns_combined_counts(conn, tasks_dir, scopes_dir, milestones_dir):
    """All migrate functions together return expected counts."""
    c1 = migrate_tasks(conn, str(tasks_dir))
    c2 = migrate_scopes(conn, str(scopes_dir))
    c3 = migrate_milestones(conn, str(milestones_dir))

    combined = {**c1, **c2, **c3}
    assert combined["tasks"] == 2
    assert combined["scopes"] == 1
    assert combined["milestones"] == 1
    assert combined["evidence"] >= 2
