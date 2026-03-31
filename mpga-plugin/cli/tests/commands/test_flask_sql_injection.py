"""T004: Tests that flask_app.py PRAGMA functions are safe from SQL injection.

Two vulnerabilities are addressed:
1. PRAGMA table name is interpolated directly into SQL — injection possible.
2. allowed_tables=None bypasses the whitelist guard entirely.
"""

from __future__ import annotations

import sqlite3

import pytest

# Import the private helpers we're testing
from mpga.web.flask_app import _fetch_columns, _fetch_foreign_keys  # noqa: PLC2701


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mem_conn() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with a minimal schema."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE safe_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# 1. allowed_tables=None must NOT bypass the whitelist
# ---------------------------------------------------------------------------

def test_fetch_columns_none_allowed_raises(mem_conn: sqlite3.Connection) -> None:
    """allowed_tables=None must raise ValueError, not allow all tables."""
    with pytest.raises(ValueError, match=r"[Aa]llowed|[Ww]hitelist|[Nn]one"):
        _fetch_columns(mem_conn, "safe_table", allowed_tables=None)


def test_fetch_foreign_keys_none_allowed_raises(mem_conn: sqlite3.Connection) -> None:
    """allowed_tables=None must raise ValueError, not allow all tables."""
    with pytest.raises(ValueError, match=r"[Aa]llowed|[Ww]hitelist|[Nn]one"):
        _fetch_foreign_keys(mem_conn, "safe_table", allowed_tables=None)


# ---------------------------------------------------------------------------
# 2. PRAGMA injection via table name must be rejected
# ---------------------------------------------------------------------------

PRAGMA_INJECTION_PAYLOADS = [
    "safe_table; PRAGMA user_version=999",
    "'; PRAGMA user_version=999; --",
    "safe_table--",
    "safe_table UNION SELECT * FROM sqlite_master",
    "safe_table\x00injection",
    "(SELECT 1)",
    "safe table",   # space — not a valid identifier
    "safe-table",   # hyphen — not a valid identifier
]


@pytest.mark.parametrize("table_name", PRAGMA_INJECTION_PAYLOADS)
def test_fetch_columns_rejects_injection_in_table_name(
    mem_conn: sqlite3.Connection, table_name: str
) -> None:
    """Injection payloads in the table name must be rejected before hitting SQL."""
    allowed = {"safe_table", table_name}  # even if in allowed set, must be validated
    with pytest.raises(ValueError, match=r"[Ii]nvalid|[Ii]llegal|[Ii]njection|[Tt]able"):
        _fetch_columns(mem_conn, table_name, allowed_tables=allowed)


@pytest.mark.parametrize("table_name", PRAGMA_INJECTION_PAYLOADS)
def test_fetch_foreign_keys_rejects_injection_in_table_name(
    mem_conn: sqlite3.Connection, table_name: str
) -> None:
    """Injection payloads in the table name must be rejected before hitting SQL."""
    allowed = {"safe_table", table_name}
    with pytest.raises(ValueError, match=r"[Ii]nvalid|[Ii]llegal|[Ii]njection|[Tt]able"):
        _fetch_foreign_keys(mem_conn, table_name, allowed_tables=allowed)


# ---------------------------------------------------------------------------
# 3. Valid table names still work
# ---------------------------------------------------------------------------

def test_fetch_columns_returns_columns_for_valid_table(mem_conn: sqlite3.Connection) -> None:
    """A valid table name with a proper whitelist must return column info."""
    result = _fetch_columns(mem_conn, "safe_table", allowed_tables={"safe_table"})
    col_names = [col["name"] for col in result]
    assert "id" in col_names
    assert "name" in col_names


def test_fetch_foreign_keys_returns_empty_for_table_with_no_fks(mem_conn: sqlite3.Connection) -> None:
    """A valid table with no foreign keys returns an empty list (no error)."""
    result = _fetch_foreign_keys(mem_conn, "safe_table", allowed_tables={"safe_table"})
    assert result == []


# ---------------------------------------------------------------------------
# 4. Table not in allowed_tables must be rejected
# ---------------------------------------------------------------------------

def test_fetch_columns_rejects_table_not_in_whitelist(mem_conn: sqlite3.Connection) -> None:
    """A table name not in allowed_tables must raise ValueError."""
    with pytest.raises(ValueError, match=r"not in the allowed list"):
        _fetch_columns(mem_conn, "safe_table", allowed_tables={"other_table"})
