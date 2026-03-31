"""Tests for observation feed UI static files."""

import pathlib

STATIC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "mpga" / "web" / "static"


def test_observation_feed_html_exists():
    feed = STATIC_DIR / "observation_feed.html"
    assert feed.exists(), "observation_feed.html must exist in web/static/"


def test_observation_feed_has_sse_connection():
    content = (STATIC_DIR / "observation_feed.html").read_text()
    assert "/api/stream" in content, "Must reference SSE endpoint /api/stream"
    assert "EventSource" in content, "Must use EventSource for SSE"


def test_observation_feed_has_card_template():
    content = (STATIC_DIR / "observation_feed.html").read_text()
    assert "observation-card" in content, "Must have observation-card element"
    assert "observation-title" in content, "Card must have a title element"
    assert "observation-time" in content, "Card must have a time element"


def test_observation_feed_has_type_badges():
    content = (STATIC_DIR / "observation_feed.html").read_text()
    assert "type-badge" in content, "Must have type-badge element"
    for obs_type in ("pattern", "decision", "issue"):
        assert obs_type in content, f"Must reference observation type '{obs_type}'"
