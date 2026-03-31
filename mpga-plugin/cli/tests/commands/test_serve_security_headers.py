"""RED → GREEN: Security headers tests for serve.py _ApiHandler.

Verifies that every response (JSON and static file) includes the required
security headers: X-Frame-Options, X-Content-Type-Options, and
Content-Security-Policy.
"""

from __future__ import annotations

import io
import json
import socket
import threading
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import time

import pytest

from mpga.commands.serve import _ApiHandler, _STATIC_DIR
from http.server import HTTPServer


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def static_dir(tmp_path: Path) -> Path:
    """Create a minimal static dir with an index.html."""
    index = tmp_path / "index.html"
    index.write_text("<html><body>hello</body></html>", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def live_server(tmp_path: Path, static_dir: Path):
    """Spin up a real _ApiHandler server on a free port for the duration of the test."""
    db_path = str(tmp_path / "test.db")

    # Create a minimal DB so get_connection won't crash
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.close()

    port = _find_free_port()

    import functools
    handler = functools.partial(
        _ApiHandler,
        db_path=db_path,
        static_dir=str(static_dir),
    )

    server = HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


def _get_response_headers(port: int, path: str) -> dict[str, str]:
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    resp.read()  # drain body
    headers = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()
    return headers


def test_x_frame_options_on_static(live_server: int) -> None:
    """Static file responses must include X-Frame-Options: DENY."""
    headers = _get_response_headers(live_server, "/")
    assert "x-frame-options" in headers, "X-Frame-Options header missing from static response"
    assert headers["x-frame-options"].upper() == "DENY"


def test_x_content_type_options_on_static(live_server: int) -> None:
    """Static file responses must include X-Content-Type-Options: nosniff."""
    headers = _get_response_headers(live_server, "/")
    assert "x-content-type-options" in headers, "X-Content-Type-Options header missing from static response"
    assert headers["x-content-type-options"].lower() == "nosniff"


def test_csp_on_static(live_server: int) -> None:
    """Static file responses must include Content-Security-Policy header."""
    headers = _get_response_headers(live_server, "/")
    assert "content-security-policy" in headers, "Content-Security-Policy header missing from static response"


def test_x_frame_options_on_api_404(live_server: int) -> None:
    """API error responses must also include X-Frame-Options."""
    headers = _get_response_headers(live_server, "/api/nonexistent")
    assert "x-frame-options" in headers, "X-Frame-Options header missing from API response"
    assert headers["x-frame-options"].upper() == "DENY"


def test_x_content_type_options_on_api_404(live_server: int) -> None:
    """API error responses must include X-Content-Type-Options."""
    headers = _get_response_headers(live_server, "/api/nonexistent")
    assert "x-content-type-options" in headers, "X-Content-Type-Options header missing from API response"
    assert headers["x-content-type-options"].lower() == "nosniff"


def test_csp_on_api_404(live_server: int) -> None:
    """API error responses must include Content-Security-Policy."""
    headers = _get_response_headers(live_server, "/api/nonexistent")
    assert "content-security-policy" in headers, "Content-Security-Policy header missing from API response"
