"""Tests for timeline view UI static files."""

import pathlib

STATIC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "mpga" / "web" / "static"


def test_timeline_html_exists():
    timeline = STATIC_DIR / "timeline.html"
    assert timeline.exists(), "timeline.html must exist in web/static/"


def test_timeline_has_chronological_layout():
    content = (STATIC_DIR / "timeline.html").read_text()
    assert "timeline" in content, "Must have timeline layout element"
    assert "timeline-entry" in content, "Must have timeline-entry elements"
    assert "timeline-date" in content, "Must have date markers"


def test_timeline_links_to_api():
    content = (STATIC_DIR / "timeline.html").read_text()
    assert "/api/observations/timeline" in content, "Must link to timeline API"


def test_timeline_has_observation_entries():
    content = (STATIC_DIR / "timeline.html").read_text()
    assert "timeline-entry" in content, "Must have timeline-entry elements"
    assert "entry-title" in content, "Entries must have titles"
    assert "entry-type" in content, "Entries must show observation type"
