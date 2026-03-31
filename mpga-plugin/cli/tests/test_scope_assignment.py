"""Tests for T008 — Add scope assignment heuristic for observations.

Coverage checklist for: T008 — Add scope assignment heuristic for observations

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: no files → returns None (degenerate)            → test_assign_scope_no_files
[x] AC2: single file in scope → assigns that scope       → test_assign_scope_single_file_in_scope
[x] AC3: majority voting (>50%) assigns winner            → test_assign_scope_majority_voting
[x] AC4: equal split → returns None                       → test_assign_scope_no_majority
[x] AC5: longest-prefix match picks deeper scope          → test_assign_scope_longest_prefix_match
[x] AC6: uses actual DB scope definitions                 → test_assign_scope_uses_db_scopes
[x] AC7: combines files_read and files_modified           → test_assign_scope_combines_read_and_modified

Untested branches / edge cases:
- [ ] file path not matching any scope prefix
- [ ] all files match scopes not present in DB
- [ ] duplicate file paths across read and modified lists
- [ ] single file in files_modified only (no files_read)
"""

from __future__ import annotations

import sqlite3

import pytest

from mpga.db.schema import create_schema

# Evidence: [E] mpga-plugin/cli/src/mpga/memory/scope_heuristic.py (not yet created)
# This import will FAIL — the module doesn't exist yet. That's the RED state.
from mpga.memory.scope_heuristic import assign_scope


@pytest.fixture()
def conn() -> sqlite3.Connection:
    """In-memory DB with schema + scope/evidence seed data.

    Scopes and their file roots (derived from evidence filepaths):
      - "mpga"        → mpga-plugin/cli/src/mpga/
      - "mpga-plugin" → mpga-plugin/  (hooks/, agents/ subdirs)
      - "root"        → project root (README.md, pyproject.toml)
    """
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    create_schema(c)

    for sid, name in [("mpga", "mpga"), ("mpga-plugin", "mpga-plugin"), ("root", "root")]:
        c.execute(
            "INSERT INTO scopes (id, name, created_at, updated_at) "
            "VALUES (?, ?, datetime('now'), datetime('now'))",
            (sid, name),
        )

    # Evidence: [E] mpga-plugin/cli/src/mpga/db/schema.py:39-50 :: scopes table
    # Evidence entries establish scope → file path associations.
    # The assign_scope function derives file roots from these.
    evidence = [
        ("mpga", "mpga-plugin/cli/src/mpga/db/schema.py"),
        ("mpga", "mpga-plugin/cli/src/mpga/commands/sync.py"),
        ("mpga", "mpga-plugin/cli/src/mpga/core/config.py"),
        ("mpga-plugin", "mpga-plugin/hooks/hooks.json"),
        ("mpga-plugin", "mpga-plugin/agents/architect.md"),
        ("root", "README.md"),
        ("root", "pyproject.toml"),
    ]
    for scope_id, filepath in evidence:
        c.execute(
            "INSERT INTO evidence (raw, type, filepath, scope_id, created_at) "
            "VALUES (?, 'file', ?, ?, datetime('now'))",
            (f"[E] {filepath}", filepath, scope_id),
        )

    c.commit()
    return c


# ---------------------------------------------------------------------------
# TPP step 1: degenerate — no files at all
# ---------------------------------------------------------------------------


class TestAssignScopeDegenerate:
    """Degenerate: no input files should produce None."""

    def test_assign_scope_no_files(self, conn: sqlite3.Connection) -> None:
        """No files_read and no files_modified → scope_id = None."""
        result = assign_scope(conn, files_read=[], files_modified=[])
        assert result is None


# ---------------------------------------------------------------------------
# TPP step 2: constant → single element (simplest positive case)
# ---------------------------------------------------------------------------


class TestAssignScopeSingleFile:
    """Single file that unambiguously belongs to one scope."""

    def test_assign_scope_single_file_in_scope(self, conn: sqlite3.Connection) -> None:
        """One file under mpga-plugin/cli/src/mpga/ → assigns 'mpga'."""
        result = assign_scope(
            conn,
            files_read=["mpga-plugin/cli/src/mpga/db/schema.py"],
            files_modified=[],
        )
        assert result == "mpga"


# ---------------------------------------------------------------------------
# TPP step 3: unconditional → selection (majority voting threshold)
# ---------------------------------------------------------------------------


class TestAssignScopeMajority:
    """Majority voting: >50% of files in one scope wins; otherwise None."""

    def test_assign_scope_majority_voting(self, conn: sqlite3.Connection) -> None:
        """3 files: 2 in mpga, 1 in root → assigns 'mpga' (67% > 50%)."""
        result = assign_scope(
            conn,
            files_read=[
                "mpga-plugin/cli/src/mpga/db/schema.py",
                "mpga-plugin/cli/src/mpga/commands/sync.py",
                "README.md",
            ],
            files_modified=[],
        )
        assert result == "mpga"

    def test_assign_scope_no_majority(self, conn: sqlite3.Connection) -> None:
        """Equal split (50/50) across two scopes → returns None."""
        result = assign_scope(
            conn,
            files_read=[
                "mpga-plugin/cli/src/mpga/db/schema.py",
                "mpga-plugin/hooks/hooks.json",
            ],
            files_modified=[],
        )
        assert result is None


# ---------------------------------------------------------------------------
# TPP step 4: selection refinement — longest-prefix match
# ---------------------------------------------------------------------------


class TestAssignScopeLongestPrefix:
    """Longest-prefix match resolves ambiguous file paths to the deepest scope."""

    def test_assign_scope_longest_prefix_match(self, conn: sqlite3.Connection) -> None:
        """mpga-plugin/cli/src/mpga/db/schema.py matches 'mpga' not 'mpga-plugin'.

        Both scopes share the 'mpga-plugin/' prefix, but 'mpga' has a longer
        matching root ('mpga-plugin/cli/src/mpga/'), so it wins.
        """
        result = assign_scope(
            conn,
            files_read=["mpga-plugin/cli/src/mpga/db/schema.py"],
            files_modified=[],
        )
        assert result == "mpga"
        assert result != "mpga-plugin"


# ---------------------------------------------------------------------------
# TPP step 5: DB-driven scopes (not hardcoded)
# ---------------------------------------------------------------------------


class TestAssignScopeDBDriven:
    """Scope assignment must query actual DB definitions, not use hardcoded names."""

    def test_assign_scope_uses_db_scopes(self, conn: sqlite3.Connection) -> None:
        """A newly inserted scope with evidence entries is immediately usable."""
        conn.execute(
            "INSERT INTO scopes (id, name, created_at, updated_at) "
            "VALUES ('custom', 'custom', datetime('now'), datetime('now'))",
        )
        conn.execute(
            "INSERT INTO evidence (raw, type, filepath, scope_id, created_at) "
            "VALUES ('[E] custom/main.py', 'file', 'custom/main.py', 'custom', datetime('now'))",
        )
        conn.commit()

        result = assign_scope(
            conn,
            files_read=["custom/main.py"],
            files_modified=[],
        )
        assert result == "custom"


# ---------------------------------------------------------------------------
# TPP step 6: scalar → collection (combining two file lists)
# ---------------------------------------------------------------------------


class TestAssignScopeCombined:
    """Both files_read and files_modified contribute to majority voting."""

    def test_assign_scope_combines_read_and_modified(self, conn: sqlite3.Connection) -> None:
        """1 read in mpga + 1 modified in mpga + 1 read in root → mpga (67%)."""
        result = assign_scope(
            conn,
            files_read=["mpga-plugin/cli/src/mpga/db/schema.py", "README.md"],
            files_modified=["mpga-plugin/cli/src/mpga/commands/sync.py"],
        )
        assert result == "mpga"
