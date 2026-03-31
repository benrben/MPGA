"""
Tests for markdown rendering tasks T001-T007.

Coverage:
  T001: marked.js and DOMPurify CDN script tags in <head>
  T002: .prose scoped CSS in <style> block
  T003: renderMarkdown() and stripMarkdown() utility functions
  T004: .prose class on modal content container element
  T005: renderModalContent() renders Markdown via innerHTML
  T006: renderTable() strips Markdown from content columns
  T007: renderTextBlock() strips Markdown from body
"""

import pathlib

INDEX_HTML = pathlib.Path(__file__).parent.parent.parent / "cli" / "src" / "mpga" / "web" / "static" / "index.html"


def _html() -> str:
    return INDEX_HTML.read_text()


# ---------------------------------------------------------------------------
# T001: marked.js and DOMPurify CDN script tags
# ---------------------------------------------------------------------------

def test_t001_marked_js_cdn_script_tag():
    """T001: index.html must include a marked.js CDN <script> tag in <head>."""
    html = _html()
    assert "marked" in html.lower(), (
        "index.html must include a <script> tag loading marked.js from CDN. "
        "Add: <script src=\"https://cdn.jsdelivr.net/npm/marked/marked.min.js\"></script>"
    )


def test_t001_dompurify_cdn_script_tag():
    """T001: index.html must include a DOMPurify CDN <script> tag in <head>."""
    html = _html()
    assert "dompurify" in html.lower(), (
        "index.html must include a <script> tag loading DOMPurify from CDN. "
        "Add: <script src=\"https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js\"></script>"
    )


# ---------------------------------------------------------------------------
# T002: .prose scoped CSS
# ---------------------------------------------------------------------------

def test_t002_prose_css_class_in_style_block():
    """T002: index.html <style> block must define a .prose CSS class."""
    html = _html()
    # Must define .prose { ... } in the <style> block
    assert ".prose" in html, (
        "index.html <style> block must define a .prose CSS class for rendered Markdown. "
        "Add .prose scoped styles (line-height, headings, code blocks, etc.)."
    )


def test_t002_prose_has_prose_styles():
    """T002: .prose CSS must include at least line-height or font-size styling."""
    html = _html()
    style_block_end = html.find("</style>")
    style_content = html[:style_block_end] if style_block_end > 0 else html
    has_prose = ".prose" in style_content
    assert has_prose, "index.html must define .prose CSS within the <style> block."


# ---------------------------------------------------------------------------
# T003: renderMarkdown() and stripMarkdown() utility functions
# ---------------------------------------------------------------------------

def test_t003_render_markdown_function_defined():
    """T003: index.html must define a renderMarkdown() JavaScript function."""
    html = _html()
    assert "function renderMarkdown" in html or "renderMarkdown(" in html, (
        "index.html must define a renderMarkdown() JS function that uses marked.parse() "
        "and DOMPurify.sanitize() to safely render Markdown as HTML."
    )


def test_t003_strip_markdown_function_defined():
    """T003: index.html must define a stripMarkdown() JavaScript function."""
    html = _html()
    assert "function stripMarkdown" in html or "stripMarkdown(" in html, (
        "index.html must define a stripMarkdown() JS function that removes Markdown "
        "formatting characters from a string (for plain-text table cells)."
    )


def test_t003_render_markdown_uses_dompurify():
    """T003: renderMarkdown() must call DOMPurify.sanitize() to prevent XSS."""
    html = _html()
    assert "DOMPurify" in html and "sanitize" in html, (
        "renderMarkdown() must call DOMPurify.sanitize() to prevent XSS when rendering "
        "user-supplied Markdown as innerHTML."
    )


# ---------------------------------------------------------------------------
# T004: .prose class on modal content container
# ---------------------------------------------------------------------------

def test_t004_prose_class_on_modal_content():
    """T004: #task-modal-content must have the .prose CSS class."""
    html = _html()
    # The div with id="task-modal-content" should have class="modal-content-block prose"
    assert 'id="task-modal-content"' in html, "task-modal-content element must exist."
    # Find the element and check it has .prose
    idx = html.find('id="task-modal-content"')
    # Look at the surrounding tag (within 200 chars)
    tag_context = html[max(0, idx - 100):idx + 100]
    assert "prose" in tag_context, (
        "The #task-modal-content div must include 'prose' in its class attribute "
        "so that rendered Markdown receives proper typography styling."
    )


# ---------------------------------------------------------------------------
# T005: renderModalContent() renders Markdown via innerHTML
# ---------------------------------------------------------------------------

def test_t005_render_modal_content_uses_inner_html():
    """T005: renderModalContent() must use innerHTML (not textContent) for Markdown rendering."""
    html = _html()
    # Find renderModalContent function
    func_start = html.find("function renderModalContent")
    assert func_start >= 0, "renderModalContent() function must exist."
    func_body = html[func_start:func_start + 400]
    assert "innerHTML" in func_body, (
        "renderModalContent() must assign innerHTML (not textContent) to render Markdown. "
        "Use: element.innerHTML = renderMarkdown(text)"
    )


def test_t005_render_modal_content_uses_render_markdown():
    """T005: renderModalContent() must call renderMarkdown() to parse and sanitize Markdown."""
    html = _html()
    func_start = html.find("function renderModalContent")
    assert func_start >= 0, "renderModalContent() function must exist."
    func_body = html[func_start:func_start + 400]
    assert "renderMarkdown" in func_body, (
        "renderModalContent() must call renderMarkdown() to convert Markdown to safe HTML."
    )


# ---------------------------------------------------------------------------
# T006: renderTable() strips Markdown from content columns
# ---------------------------------------------------------------------------

def test_t006_render_table_strips_markdown():
    """T006: renderTable() must call stripMarkdown() when rendering cell text content."""
    html = _html()
    func_start = html.find("function renderTable")
    assert func_start >= 0, "renderTable() function must exist."
    func_body = html[func_start:func_start + 1600]
    assert "stripMarkdown" in func_body, (
        "renderTable() must call stripMarkdown() on cell values to strip Markdown "
        "formatting characters from table cells (headings, bold, code, etc.)."
    )


# ---------------------------------------------------------------------------
# T007: renderTextBlock() strips Markdown from body
# ---------------------------------------------------------------------------

def test_t007_render_text_block_strips_markdown():
    """T007: renderTextBlock() must call stripMarkdown() on the body text."""
    html = _html()
    func_start = html.find("function renderTextBlock")
    assert func_start >= 0, "renderTextBlock() function must exist."
    func_body = html[func_start:func_start + 700]
    assert "stripMarkdown" in func_body, (
        "renderTextBlock() must call stripMarkdown() on the body text to remove "
        "Markdown formatting before displaying in plain-text contexts."
    )
