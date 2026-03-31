"""Tests for T005 — Wire observations into rebuild_global_fts.

Coverage checklist for: T005 — Wire observations into rebuild_global_fts

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: rebuild_global_fts includes observations (entity_type='observation')
        → test_rebuild_global_fts_includes_observations
[x] AC2: observation entity_type is 'observation'
        → test_rebuild_global_fts_observation_entity_type
[x] AC3: title → title column, narrative+facts → content column
        → test_rebuild_global_fts_observation_uses_title_and_narrative
[x] AC4: global_trigram populated with observations
        → test_rebuild_populates_global_trigram
[x] AC5: global_trigram includes ALL entity types (not just observations)
        → test_rebuild_global_trigram_includes_all_entities
[x] AC6: rebuild is idempotent — no duplicates on double-call
        → test_rebuild_clears_before_repopulating

Untested branches / edge cases:
- [ ] observation with NULL narrative/facts/concepts
- [ ] observation with very long text
- [ ] concurrent rebuild calls
"""

from __future__ import annotations

import sqlite3

import pytest

from mpga.db.connection import get_connection
from mpga.db.schema import create_schema
from mpga.db.search import rebuild_global_fts

# Evidence: [E] mpga-plugin/cli/src/mpga/db/search.py:196-270 :: rebuild_global_fts()
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:236-252 :: observations table
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:305-307 :: global_fts FTS5 table
# Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:356-359 :: global_trigram FTS5 table

NOW = "2026-01-01T00:00:00"


@pytest.fixture
def fts_conn(tmp_path):
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    conn.execute(
        "INSERT INTO tasks (id, title, body, column_, priority, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("t1", "Test task", "Task body", "todo", "high", NOW, NOW),
    )
    conn.execute(
        "INSERT INTO scopes (id, name, summary, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("s1", "test-scope", "Test scope summary", NOW, NOW),
    )
    conn.execute(
        "INSERT INTO milestones (id, name, summary, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("m1", "Test milestone", "Milestone summary", NOW),
    )
    conn.execute(
        "INSERT INTO decisions (id, title, content, created_at) "
        "VALUES (?, ?, ?, ?)",
        ("d1", "Test decision", "Decision content", NOW),
    )
    conn.execute(
        "INSERT INTO observations (session_id, title, type, narrative, facts, concepts, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "sess1",
            "Observed pattern",
            "tool_output",
            "Found a reusable pattern in the auth module",
            "auth uses JWT tokens",
            "modularity and reuse",
            NOW,
        ),
    )
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# 1. Degenerate — observations appear in global_fts at all
# ---------------------------------------------------------------------------


def test_rebuild_global_fts_includes_observations(fts_conn):
    """After rebuild, searching global_fts for observation content returns a row."""
    rebuild_global_fts(fts_conn)

    rows = fts_conn.execute(
        "SELECT entity_type, entity_id, title, content "
        "FROM global_fts WHERE entity_type = 'observation'"
    ).fetchall()
    assert len(rows) >= 1, "global_fts should contain at least one observation row"
    assert "Observed pattern" in rows[0][2]


# ---------------------------------------------------------------------------
# 2. entity_type value — must be exactly 'observation'
# ---------------------------------------------------------------------------


def test_rebuild_global_fts_observation_entity_type(fts_conn):
    """The entity_type column for observations is exactly 'observation'."""
    rebuild_global_fts(fts_conn)

    rows = fts_conn.execute(
        "SELECT DISTINCT entity_type FROM global_fts"
    ).fetchall()
    types = {r[0] for r in rows}
    assert "observation" in types, (
        f"Expected 'observation' in entity types, got {types}"
    )


# ---------------------------------------------------------------------------
# 3. Column mapping — title → title, narrative+facts+concepts → content
# ---------------------------------------------------------------------------


def test_rebuild_global_fts_observation_uses_title_and_narrative(fts_conn):
    """Observation title maps to FTS title column; narrative, facts, and concepts map to content."""
    rebuild_global_fts(fts_conn)

    row = fts_conn.execute(
        "SELECT entity_type, entity_id, title, content "
        "FROM global_fts WHERE entity_type = 'observation'"
    ).fetchone()
    assert row is not None

    fts_title = row[2]
    fts_content = row[3]

    assert fts_title == "Observed pattern", (
        f"FTS title should be the observation title, got '{fts_title}'"
    )
    assert "reusable pattern" in fts_content, (
        "FTS content should include narrative text"
    )
    assert "JWT tokens" in fts_content, (
        "FTS content should include facts text"
    )
    assert "modularity" in fts_content, (
        "FTS content should include concepts text"
    )


# ---------------------------------------------------------------------------
# 4. global_trigram — observations present after rebuild
# ---------------------------------------------------------------------------


def test_rebuild_populates_global_trigram(fts_conn):
    """rebuild_global_fts also populates global_trigram with observation rows."""
    rebuild_global_fts(fts_conn)

    rows = fts_conn.execute(
        "SELECT entity_type, entity_id, title, content "
        "FROM global_trigram WHERE entity_type = 'observation'"
    ).fetchall()
    assert len(rows) >= 1, "global_trigram should contain observation rows"
    assert "Observed pattern" in rows[0][2]

    # Trigram index supports substring matching
    trigram_hit = fts_conn.execute(
        "SELECT entity_type FROM global_trigram "
        "WHERE global_trigram MATCH '\"reusable pattern\"'"
    ).fetchall()
    assert any(r[0] == "observation" for r in trigram_hit), (
        "Trigram index should match substring 'reusable pattern' in observation content"
    )


# ---------------------------------------------------------------------------
# 5. global_trigram — includes ALL entity types, not just observations
# ---------------------------------------------------------------------------


def test_rebuild_global_trigram_includes_all_entities(fts_conn):
    """global_trigram mirrors global_fts: tasks, scopes, milestones, decisions, observations."""
    rebuild_global_fts(fts_conn)

    types = {
        r[0]
        for r in fts_conn.execute(
            "SELECT DISTINCT entity_type FROM global_trigram"
        ).fetchall()
    }
    assert "task" in types, f"global_trigram missing 'task', got {types}"
    assert "scope" in types, f"global_trigram missing 'scope', got {types}"
    assert "milestone" in types, f"global_trigram missing 'milestone', got {types}"
    assert "decision" in types, f"global_trigram missing 'decision', got {types}"
    assert "observation" in types, f"global_trigram missing 'observation', got {types}"


# ---------------------------------------------------------------------------
# 6. Idempotency — rebuild twice, no duplicates
# ---------------------------------------------------------------------------


def test_rebuild_clears_before_repopulating(fts_conn):
    """Calling rebuild_global_fts twice does not create duplicate rows."""
    rebuild_global_fts(fts_conn)
    count_first = fts_conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]
    trigram_first = fts_conn.execute("SELECT COUNT(*) FROM global_trigram").fetchone()[0]

    rebuild_global_fts(fts_conn)
    count_second = fts_conn.execute("SELECT COUNT(*) FROM global_fts").fetchone()[0]
    trigram_second = fts_conn.execute("SELECT COUNT(*) FROM global_trigram").fetchone()[0]

    assert count_first == count_second, (
        f"global_fts row count changed: {count_first} → {count_second}"
    )
    assert trigram_first == trigram_second, (
        f"global_trigram row count changed: {trigram_first} → {trigram_second}"
    )
