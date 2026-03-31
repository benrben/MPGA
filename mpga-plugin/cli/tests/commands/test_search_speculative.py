"""T059: Test that search.py has no speculative dead-code branches.

The speculative branch is the 'fts_count = None' fallback pattern — setting
a variable to None just to suppress it in the happy path is dead-code generality.
The simplified version moves the FTS count query to only where it's needed.
"""
import sys
from pathlib import Path

SRC_ROOT = Path("/Users/benreich/MPGA/mpga-plugin/cli/src")
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SEARCH_CMD_FILE = Path("/Users/benreich/MPGA/mpga-plugin/cli/src/mpga/commands/search.py")


def test_no_fts_count_none_speculative_branch():
    """search.py must not assign fts_count = None as a dead-code placeholder.

    The pattern 'fts_count = None  # not needed when results were found' is
    speculative generality — it only exists to satisfy the else branch of an
    if/else that assigns it in the happy path. The simplified code queries
    fts_count only in the no-results branch where it's actually needed.
    """
    content = SEARCH_CMD_FILE.read_text(encoding="utf-8")
    assert "fts_count = None" not in content, (
        "Found 'fts_count = None' speculative dead branch in search.py. "
        "Refactor to query fts_count only where needed (in the no-results branch)."
    )


def test_search_returns_results_for_valid_query():
    """global_search must return SearchResult objects when given a valid query."""
    import sqlite3
    from mpga.db.search import global_search, SearchResult

    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS global_fts USING fts5(entity_type, entity_id, title, content)
    """)
    conn.execute("""
        INSERT INTO global_fts (entity_type, entity_id, title, content)
        VALUES ('task', 'T001', 'Test task', 'some test content')
    """)
    conn.commit()

    results = global_search(conn, "test", limit=5)
    conn.close()

    assert len(results) >= 1
    assert isinstance(results[0], SearchResult)
    # Also verify the speculative code is gone
    assert "fts_count = None" not in SEARCH_CMD_FILE.read_text(encoding="utf-8")
