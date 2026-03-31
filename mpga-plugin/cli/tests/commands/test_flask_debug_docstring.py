"""RED → GREEN: Ensure debug=True does not appear in flask_app.py docstrings/comments.

A debug=True example in documentation can lead developers to accidentally
run with debug mode enabled in production.
"""

from __future__ import annotations

import ast
import pathlib


_FLASK_APP_PATH = (
    pathlib.Path(__file__).parent.parent.parent
    / "src" / "mpga" / "web" / "flask_app.py"
)


def _extract_docstrings_and_comments(source: str) -> list[str]:
    """Return all string literals used as docstrings plus inline comments."""
    tree = ast.parse(source)
    results: list[str] = []

    for node in ast.walk(tree):
        # Module/function/class docstrings are Expr(value=Constant(str))
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            results.append(node.value.value)

    # Also capture inline comments via line scanning
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            results.append(stripped)

    return results


def test_no_debug_true_in_docstrings_or_comments() -> None:
    """flask_app.py must not contain debug=True in any docstring or comment example."""
    source = _FLASK_APP_PATH.read_text(encoding="utf-8")
    texts = _extract_docstrings_and_comments(source)

    violations = [t for t in texts if "debug=True" in t]
    assert not violations, (
        f"Found 'debug=True' in {len(violations)} docstring(s)/comment(s) in flask_app.py. "
        f"Change to debug=False or remove the debug parameter from examples. "
        f"Offending text(s): {violations}"
    )


def test_flask_app_file_exists() -> None:
    """Sanity check: flask_app.py must exist at the expected path."""
    assert _FLASK_APP_PATH.exists(), f"flask_app.py not found at {_FLASK_APP_PATH}"
