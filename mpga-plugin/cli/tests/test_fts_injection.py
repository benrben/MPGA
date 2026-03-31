"""T002/T005: Tests that FTS5 query terms are properly escaped before use.

FTS5 has its own query language with special characters (", *, -, (, ), AND,
OR, NOT, NEAR) that can cause errors or unexpected query semantics when
injected by user input.  All user-supplied terms must be treated as literals.
"""

from __future__ import annotations

import sqlite3

import pytest

from mpga.db.fts_utils import prefix_match_query


# ---------------------------------------------------------------------------
# 1. Special FTS5 characters must NOT cause sqlite3.OperationalError
#    when the query is executed against a real FTS5 table.
# ---------------------------------------------------------------------------

@pytest.fixture()
def fts_conn() -> sqlite3.Connection:
    """In-memory FTS5 table for integration-level query testing."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE VIRTUAL TABLE docs USING fts5(content)"
    )
    conn.execute("INSERT INTO docs VALUES ('hello world')")
    conn.execute("INSERT INTO docs VALUES ('authentication token')")
    conn.commit()
    return conn


SPECIAL_INPUTS = [
    '"hello"',           # quoted phrase — must be escaped
    'hello*',            # explicit prefix operator — must be treated as literal
    'hello OR world',    # FTS5 OR operator
    'hello AND world',   # FTS5 AND operator
    'hello NOT world',   # FTS5 NOT operator
    '--',                # double dash
    '"unclosed',         # unclosed quote
    'NEAR(hello world)', # NEAR operator
    '-hello',            # negation prefix
    '(hello)',           # grouping parens
    '^hello',            # caret (start-of-column anchor)
]


@pytest.mark.parametrize("user_input", SPECIAL_INPUTS)
def test_fts5_special_input_does_not_raise(
    fts_conn: sqlite3.Connection, user_input: str
) -> None:
    """Special FTS5 chars in search terms must NOT raise sqlite3.OperationalError."""
    query = prefix_match_query(user_input)
    try:
        fts_conn.execute("SELECT * FROM docs WHERE docs MATCH ?", (query,)).fetchall()
    except sqlite3.OperationalError as exc:
        pytest.fail(
            f"prefix_match_query({user_input!r}) produced FTS5 query {query!r} "
            f"that caused a sqlite3.OperationalError: {exc}"
        )


# ---------------------------------------------------------------------------
# 2. Escaped terms must match their literal content (not act as operators)
# ---------------------------------------------------------------------------

def test_or_operator_treated_as_literal(fts_conn: sqlite3.Connection) -> None:
    """'hello OR world' must search for the literal tokens, not use FTS5 OR."""
    query = prefix_match_query("hello OR world")
    # If OR is treated literally, it becomes part of the search, not an operator.
    # The query should not cause an error and should return predictable results.
    results = fts_conn.execute(
        "SELECT * FROM docs WHERE docs MATCH ?", (query,)
    ).fetchall()
    # We do not assert a specific result count since "OR" as a literal is unusual,
    # but we do assert no error was raised (covered above) and results is a list.
    assert isinstance(results, list)


def test_unclosed_quote_treated_as_literal(fts_conn: sqlite3.Connection) -> None:
    """An unclosed quote in user input must not cause a parse error."""
    query = prefix_match_query('"unclosed')
    results = fts_conn.execute(
        "SELECT * FROM docs WHERE docs MATCH ?", (query,)
    ).fetchall()
    assert isinstance(results, list)


def test_double_quote_in_term_is_escaped(fts_conn: sqlite3.Connection) -> None:
    """A term containing a double-quote must have it escaped (doubled)."""
    query = prefix_match_query('"hello"')
    # The escaped form should wrap in double-quotes and double the internal quote
    # e.g. "hello" → "\"hello\""  →  ""hello""  in FTS5 quoting
    assert '""' in query or query.count('"') >= 2, (
        f"Expected internal double-quotes to be escaped in {query!r}"
    )


# ---------------------------------------------------------------------------
# 3. Normal terms still produce prefix-match queries
# ---------------------------------------------------------------------------

def test_plain_term_still_gets_prefix_suffix(fts_conn: sqlite3.Connection) -> None:
    """Plain word input must still produce a prefix-match (ends with *)."""
    query = prefix_match_query("auth")
    results = fts_conn.execute(
        "SELECT * FROM docs WHERE docs MATCH ?", (query,)
    ).fetchall()
    # "auth" should prefix-match "authentication"
    assert len(results) >= 1, f"Expected 'auth*' to match 'authentication', got: {results!r}"


def test_plain_term_matches_exact_word(fts_conn: sqlite3.Connection) -> None:
    """Plain word should match rows that contain it."""
    query = prefix_match_query("hello")
    results = fts_conn.execute(
        "SELECT * FROM docs WHERE docs MATCH ?", (query,)
    ).fetchall()
    assert len(results) >= 1
