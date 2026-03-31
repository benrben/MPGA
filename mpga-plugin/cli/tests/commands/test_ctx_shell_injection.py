"""T003: Tests that _run_shell in ctx.py does NOT use shell=True.

shell=True with unsanitised user input is a command-injection vulnerability.
The function must use shell=False (list-based invocation) and reject shell
metacharacters that enable injection.
"""

from __future__ import annotations

import inspect
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from mpga.commands.ctx import _run_shell


# ---------------------------------------------------------------------------
# 1. Structural tests — the implementation must not use shell=True
# ---------------------------------------------------------------------------

def test_run_shell_does_not_use_shell_true() -> None:
    """_run_shell must pass shell=False (or omit shell) to subprocess.run."""
    calls = []

    def capturing_run(*args, **kwargs):
        calls.append(kwargs)
        # Return a mock result so the function can complete
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("mpga.commands.ctx.subprocess.run", side_effect=capturing_run):
        _run_shell("echo hello")

    assert calls, "subprocess.run was never called"
    for call_kwargs in calls:
        shell_value = call_kwargs.get("shell", False)
        assert shell_value is not True, (
            f"subprocess.run was called with shell=True — this is a security vulnerability. "
            f"Got kwargs: {call_kwargs}"
        )


# ---------------------------------------------------------------------------
# 2. Input validation — shell metacharacters must be rejected
# ---------------------------------------------------------------------------

INJECTION_PAYLOADS = [
    "echo hello; rm -rf /",
    "echo hello && cat /etc/passwd",
    "echo hello || id",
    "echo `id`",
    "echo $(id)",
    "echo hello | cat /etc/shadow",
    "echo hello > /tmp/pwned",
    "echo hello < /etc/passwd",
]


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
def test_run_shell_rejects_shell_metacharacters(payload: str) -> None:
    """Commands containing shell injection metacharacters must be rejected."""
    with pytest.raises((ValueError, PermissionError), match=r"[Ii]njection|[Mm]etachar|[Ii]nvalid|[Ff]orbidden|[Uu]nsafe"):
        _run_shell(payload)


# ---------------------------------------------------------------------------
# 3. Functional — safe commands still work
# ---------------------------------------------------------------------------

def test_run_shell_executes_safe_command() -> None:
    """A plain command with no metacharacters must still execute successfully."""
    rc, output = _run_shell("echo hello")
    assert rc == 0
    assert "hello" in output


def test_run_shell_returns_nonzero_on_failure() -> None:
    """A failing command must return a non-zero exit code."""
    rc, output = _run_shell("false")
    assert rc != 0
