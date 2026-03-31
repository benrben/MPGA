"""RED test: handle_board_live must NOT have dead parameters.

T030 — Remove dead params from handle_board_live (serve, open_browser, port).

These parameters are accepted by the function but never used inside the
function body, which makes the signature misleading and creates maintenance
surface area with no benefit.
"""

from __future__ import annotations

import inspect

import pytest


def _get_handler():
    from mpga.commands.board_handlers import handle_board_live
    return handle_board_live


def test_handle_board_live_has_no_serve_param():
    """handle_board_live must not accept a `serve` parameter."""
    sig = inspect.signature(_get_handler())
    assert "serve" not in sig.parameters, (
        "Dead parameter `serve` is still present in handle_board_live. "
        "Remove it — it is never read inside the function body."
    )


def test_handle_board_live_has_no_open_browser_param():
    """handle_board_live must not accept an `open_browser` parameter."""
    sig = inspect.signature(_get_handler())
    assert "open_browser" not in sig.parameters, (
        "Dead parameter `open_browser` is still present in handle_board_live. "
        "Remove it — it is never read inside the function body."
    )


def test_handle_board_live_has_no_port_param():
    """handle_board_live must not accept a `port` parameter."""
    sig = inspect.signature(_get_handler())
    assert "port" not in sig.parameters, (
        "Dead parameter `port` is still present in handle_board_live. "
        "Remove it — it is never read inside the function body."
    )


def test_handle_board_live_accepts_no_unexpected_params():
    """handle_board_live should have an empty (or minimal) signature.

    After removing the three dead params the function body only calls
    internal helpers — no parameters are needed.
    """
    sig = inspect.signature(_get_handler())
    dead = {"serve", "open_browser", "port"}
    present_dead = dead & set(sig.parameters)
    assert not present_dead, (
        f"Dead parameter(s) {present_dead!r} still present in handle_board_live."
    )
