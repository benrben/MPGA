"""RED → GREEN: SSRF protection tests for ctx_fetch_and_index.

Validates that private IPs and non-http/https schemes are rejected
before any network request is made.
"""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from mpga.commands.ctx import _validate_url_for_fetch


def _mock_getaddrinfo_for(ip: str):
    """Return a mock getaddrinfo result that resolves to the given IP."""
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]


@pytest.mark.parametrize(
    "url,resolved_ip",
    [
        ("http://127.0.0.1/secret", "127.0.0.1"),
        ("http://127.0.0.1:8080/admin", "127.0.0.1"),
        ("http://localhost/etc/passwd", "127.0.0.1"),
        ("http://192.168.1.1/router", "192.168.1.1"),
        ("http://192.168.0.255/config", "192.168.0.255"),
        ("http://10.0.0.1/internal", "10.0.0.1"),
        ("http://10.255.255.255/data", "10.255.255.255"),
        ("http://172.16.0.1/private", "172.16.0.1"),
        ("http://172.31.255.255/private", "172.31.255.255"),
        ("http://169.254.169.254/latest/meta-data/", "169.254.169.254"),  # AWS metadata
        ("https://127.0.0.1/ssl-bypass", "127.0.0.1"),
    ],
)
def test_private_ip_rejected(url: str, resolved_ip: str) -> None:
    """Private/loopback IPs must be blocked regardless of scheme."""
    with patch("socket.getaddrinfo", return_value=_mock_getaddrinfo_for(resolved_ip)):
        with pytest.raises(ValueError, match="private|loopback|reserved|disallowed"):
            _validate_url_for_fetch(url)


def test_ipv6_loopback_rejected() -> None:
    """IPv6 loopback (::1) must be rejected."""
    ipv6_result = [(socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", 0, 0, 0))]
    with patch("socket.getaddrinfo", return_value=ipv6_result):
        with pytest.raises(ValueError, match="private|loopback|reserved|disallowed"):
            _validate_url_for_fetch("http://[::1]/ipv6-loopback")


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "file://localhost/etc/shadow",
        "ftp://evil.com/payload",
        "gopher://evil.com:70/1payload",
        "dict://evil.com:11111/stat",
        "ldap://evil.com/dc=example",
        "javascript:alert(1)",
        "data:text/plain,hello",
    ],
)
def test_non_http_scheme_rejected(url: str) -> None:
    """Only http and https schemes are allowed."""
    with pytest.raises(ValueError, match="scheme|not allowed|unsupported"):
        _validate_url_for_fetch(url)


@pytest.mark.parametrize(
    "url,resolved_ip",
    [
        ("http://example.com/page", "93.184.216.34"),
        ("https://example.com/page", "93.184.216.34"),
        ("https://api.github.com/repos", "140.82.112.6"),
        ("http://openai.com/docs", "104.18.7.192"),
    ],
)
def test_public_url_allowed(url: str, resolved_ip: str) -> None:
    """Public http/https URLs must pass validation without raising."""
    with patch("socket.getaddrinfo", return_value=_mock_getaddrinfo_for(resolved_ip)):
        # Should not raise
        _validate_url_for_fetch(url)
