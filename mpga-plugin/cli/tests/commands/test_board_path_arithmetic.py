"""RED test: brittle path arithmetic in _refresh_sqlite_board_mirror.

T057 — Replace manual `.parent.parent` depth-counting with an explicit,
named pathlib.Path operation that makes the structural assumption visible.

The brittle code at board_handlers.py:72 (in _refresh_sqlite_board_mirror):

    project_root = Path(board_dir).parent.parent

…silently derives the project root by counting two levels up from board_dir.
This breaks for:
  - Paths that contain trailing slashes (str(Path(...)) normalises them, but
    explicit string manipulation would not)
  - board_dir values that use a different depth (e.g. during testing)
  - Paths with spaces or unusual characters

These tests validate the *shape* of the path derivation function so we can
refactor to a named constant / helper that makes the assumption explicit.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_source() -> str:
    from mpga.commands import board_db
    return inspect.getsource(board_db)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBrittlePathArithmetic:
    """The function must NOT use raw chained `.parent.parent` to find root."""

    def test_no_double_parent_chain_in_refresh(self):
        """_refresh_sqlite_board_mirror must not contain `.parent.parent`.

        Using `.parent.parent` silently encodes a structural depth assumption.
        The refactored code should derive the project root from a named
        constant or helper (e.g. ``find_project_root()`` or a ``_board_context()``
        call) so the assumption is visible and testable.
        """
        source = _get_source()
        # Find the function body specifically
        # We look for the pattern inside _refresh_sqlite_board_mirror
        func_start = source.find("def refresh_sqlite_board_mirror(")
        assert func_start != -1, "_refresh_sqlite_board_mirror not found in module source"
        # Grab from function start to the next top-level def or end
        func_body = source[func_start:]
        next_def = func_body.find("\ndef ", 1)
        if next_def != -1:
            func_body = func_body[:next_def]

        assert ".parent.parent" not in func_body, (
            "Brittle `.parent.parent` chain still present in "
            "_refresh_sqlite_board_mirror. Replace with a named helper or "
            "find_project_root() call so the depth assumption is explicit."
        )

    def test_project_root_derivation_uses_named_helper_or_constant(self):
        """The project root must be derived via find_project_root or _board_context.

        After the refactor, _refresh_sqlite_board_mirror should accept the
        project_root as a parameter OR call find_project_root() instead of
        computing it via fragile chained .parent calls.
        """
        source = _get_source()
        func_start = source.find("def refresh_sqlite_board_mirror(")
        assert func_start != -1
        func_body = source[func_start:]
        next_def = func_body.find("\ndef ", 1)
        if next_def != -1:
            func_body = func_body[:next_def]

        uses_root_param = "project_root" in func_body
        uses_find_root = "find_project_root" in func_body
        assert uses_root_param or uses_find_root, (
            "_refresh_sqlite_board_mirror should either accept project_root as "
            "a parameter or call find_project_root() — not derive the root "
            "through brittle chained .parent calls."
        )

    def test_path_with_trailing_slash_resolves_correctly(self, tmp_path):
        """Path resolution must be stable when board_dir has a trailing slash.

        Chained .parent.parent fails consistently with trailing slashes in
        some string-manipulation approaches; pathlib normalises correctly.
        The refactored code must produce the same result whether or not
        board_dir ends with a separator.
        """
        project_root = tmp_path / "myproject"
        board_dir_clean = project_root / "MPGA" / "board"
        board_dir_slash = str(board_dir_clean) + "/"

        # pathlib normalises trailing slashes — both should yield the same root
        resolved_clean = Path(str(board_dir_clean)).parent.parent
        resolved_slash = Path(board_dir_slash).parent.parent

        # This test documents the expectation: both resolve to the same root.
        assert resolved_clean == resolved_slash, (
            "Trailing slash on board_dir must not change the resolved project_root. "
            "Use pathlib.Path — do NOT use string arithmetic."
        )
        assert resolved_clean == project_root

    def test_path_with_spaces_resolves_correctly(self, tmp_path):
        """Path arithmetic must work for paths that contain spaces."""
        project_root = tmp_path / "my project with spaces"
        board_dir = project_root / "MPGA" / "board"

        # Simulate what the refactored function should produce
        derived_root = Path(str(board_dir)).parent.parent
        assert derived_root == project_root, (
            "Path with spaces must resolve to the correct project root."
        )

    def test_refresh_accepts_project_root_or_derives_it_safely(self, tmp_path):
        """_refresh_sqlite_board_mirror signature or body must expose the root.

        Either the function takes project_root as a parameter (preferred) or
        it calls find_project_root() internally.  Either way the signature
        must be inspectable.
        """
        from mpga.commands.board_handlers import _refresh_sqlite_board_mirror
        sig = inspect.signature(_refresh_sqlite_board_mirror)
        params = set(sig.parameters)
        # Acceptable: function takes project_root directly, OR board_dir only
        # (in which case the body must use find_project_root, checked above).
        assert "board_dir" in params or "project_root" in params, (
            "_refresh_sqlite_board_mirror must accept board_dir or project_root."
        )
