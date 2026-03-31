"""T044: Test that db_dashboard.html does not use innerHTML with user data (XSS prevention).

The renderScopesTable function (lines 274-305) builds an HTML string from user-controlled
data using template literals, then sets content.innerHTML = html. This is XSS-prone even
with the escape() helper because the fix should use DOM APIs (createElement + textContent)
instead of innerHTML for user-data cells.

The test checks that the `escape()` helper function is REMOVED (no longer needed)
and that the renderScopesTable function uses DOM manipulation (createElement/textContent)
rather than innerHTML for user-supplied data.
"""

import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent.parent / "src" / "mpga" / "web" / "templates" / "db_dashboard.html"


def read_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_template_exists():
    assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"


def test_render_scopes_table_does_not_use_inner_html_for_user_data():
    """renderScopesTable must NOT build an HTML string from user data and assign via innerHTML."""
    html = read_template()

    # Find the renderScopesTable function body
    match = re.search(
        r"function renderScopesTable\s*\([^)]*\)\s*\{(.*?)^\s*\}",
        html,
        re.DOTALL | re.MULTILINE,
    )
    assert match, "renderScopesTable function not found in template"
    func_body = match.group(1)

    # The function must NOT assign user-data interpolations into innerHTML
    # i.e. it should NOT contain both template-literal scope data AND innerHTML assignment
    # Specifically: `content.innerHTML = html` where html contains `${escape(scope.` patterns
    uses_escape_in_template = "escape(scope." in func_body
    assigns_innerHTML = "content.innerHTML = html" in func_body or re.search(r"content\.innerHTML\s*=\s*html", func_body)

    # FAIL if both are true: still using the old XSS-prone pattern
    assert not (uses_escape_in_template and assigns_innerHTML), (
        "renderScopesTable still uses innerHTML with escape(scope.*) interpolations — "
        "XSS-prone pattern not fixed. Use DOM methods (createElement + textContent) instead."
    )


def test_scope_id_uses_text_content_not_escape():
    """scope.id must be set via textContent, not via escape() in innerHTML."""
    html = read_template()
    match = re.search(
        r"function renderScopesTable\s*\([^)]*\)\s*\{(.*?)^\s*\}",
        html,
        re.DOTALL | re.MULTILINE,
    )
    assert match, "renderScopesTable function not found"
    func_body = match.group(1)

    # Should use textContent for scope.id (or similar safe assignment)
    assert "textContent" in func_body or "createTextNode" in func_body, (
        "renderScopesTable does not use textContent or createTextNode for user data"
    )
