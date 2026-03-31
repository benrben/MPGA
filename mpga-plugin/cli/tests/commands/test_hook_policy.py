"""Tests for centralized hook policy decisions."""

from __future__ import annotations

from mpga.bridge.hook_policy import evaluate_bash, evaluate_read


def test_bash_policy_blocks_network_fetch_patterns() -> None:
    decision = evaluate_bash("curl https://example.com")
    assert decision.decision == "block"
    assert decision.reason_code == "network_fetch_blocked"
    assert "fetch-and-index" in (decision.suggested_command or "")


def test_bash_policy_redirects_heavy_shell() -> None:
    decision = evaluate_bash("grep -R token src")
    assert decision.decision == "redirect"
    assert decision.reason_code == "heavy_shell_redirect"
    assert "ctx execute" in (decision.suggested_command or "")


def test_bash_policy_allows_mpga_command() -> None:
    decision = evaluate_bash("mpga search auth")
    assert decision.decision == "allow"


def test_read_policy_redirects_mpga_scope_path() -> None:
    decision = evaluate_read(".mpga/scopes/auth.md")
    assert decision.decision == "redirect"
