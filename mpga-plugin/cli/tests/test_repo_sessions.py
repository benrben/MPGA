"""Tests for session and event repositories."""

from __future__ import annotations

import sqlite3

import pytest

from mpga.db.repos.sessions import EventRepo, SessionRepo
from mpga.db.schema import create_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)
    yield c
    c.close()


def test_session_repo_starts_and_reuses_active_session(conn):
    repo = SessionRepo(conn)
    session = repo.start("/tmp/project", model="gpt-5")
    assert session.project_root == "/tmp/project"

    same = repo.start("/tmp/project")
    assert same.id == session.id


def test_event_repo_adds_and_lists_events(conn):
    session = SessionRepo(conn).start("/tmp/project")
    repo = EventRepo(conn)
    repo.add(session_id=session.id, event_type="pre-read", action="Read", input_summary="MPGA/INDEX.md")
    repo.add(session_id=session.id, event_type="post-bash", action="Bash", output_summary="ok")

    events = repo.list_for_session(session.id)
    assert len(events) == 2
    assert events[0].event_type == "pre-read"
    assert events[1].event_type == "post-bash"
