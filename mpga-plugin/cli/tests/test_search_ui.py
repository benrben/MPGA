"""Tests for search UI with progressive disclosure."""

import pathlib

STATIC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "mpga" / "web" / "static"


def test_search_html_exists():
    search = STATIC_DIR / "search.html"
    assert search.exists(), "search.html must exist in web/static/"


def test_search_has_input_field():
    content = (STATIC_DIR / "search.html").read_text()
    assert "search-input" in content, "Must have a search input element"
    assert 'type="search"' in content or 'type="text"' in content, (
        "Input must be a search or text field"
    )


def test_search_links_to_api():
    content = (STATIC_DIR / "search.html").read_text()
    assert "/api/observations/search" in content, "Must reference search API"


def test_search_has_progressive_disclosure():
    content = (STATIC_DIR / "search.html").read_text()
    assert "search-results" in content, "Must have search-results container"
    assert "result-detail" in content, "Must have result-detail panel"
    assert "keyboard" in content.lower() or "keydown" in content.lower(), (
        "Must have keyboard shortcut support"
    )
