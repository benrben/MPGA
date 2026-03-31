"""Centralized hook policy evaluation for context protection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

POLICY_MODE = "hard-block"

_NETWORK_PATTERNS = [
    re.compile(r"\bcurl\b", re.IGNORECASE),
    re.compile(r"\bwget\b", re.IGNORECASE),
    re.compile(r"fetch\(\s*['\"]https?://", re.IGNORECASE),
    re.compile(r"requests\.(get|post|put|delete)\(", re.IGNORECASE),
    re.compile(r"http\.(get|request)\(", re.IGNORECASE),
]

_SHELL_HEAVY_PATTERNS = [
    re.compile(r"^\s*(cat|grep|rg|sed|awk|head|tail|less)\b", re.IGNORECASE),
    re.compile(r"\|\s*(head|tail|sed|awk|jq)\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class PolicyDecision:
    decision: str  # allow | block | redirect
    reason_code: str
    message: str
    suggested_command: str | None = None

    def to_output(self) -> str:
        lines = [
            f"decision={self.decision}",
            f"reason={self.reason_code}",
            self.message,
        ]
        if self.suggested_command:
            lines.append(f"use={self.suggested_command}")
        return "\n".join(lines)


def policy_mode() -> str:
    return POLICY_MODE


def mpga_routing_text() -> str:
    return (
        "IMPORTANT: MPGA context protection is active in hard-block mode.\n"
        "Raw high-volume reads/exec and direct network fetching are blocked.\n"
        "\n"
        "Allowed:\n"
        "- mpga commands (including `mpga ctx ...`)\n"
        "- short safe shell tasks (git, ls, cd, mkdir, mv, rm)\n"
        "\n"
        "Blocked/redirected patterns:\n"
        "- curl/wget or inline HTTP scripts\n"
        "- direct reads/searches likely to flood context\n"
        "\n"
        "Use these commands instead:\n"
        "- mpga ctx execute --code '<command>'\n"
        "- mpga ctx execute-file <path>\n"
        "- mpga ctx fetch-and-index <url> --source <label>\n"
        "- mpga ctx search <query>\n"
        "- mpga ctx batch-execute --command '<cmd>' --query '<q>'\n"
        "- mpga search \"<query>\" (for MPGA entities)\n"
        "- mpga scope show <name>\n"
        "- mpga board show <id>\n"
        "- mpga session resume\n"
        "- mpga ctx stats / mpga ctx doctor\n"
    )


def _allow(reason_code: str = "allow", message: str = "allowed") -> PolicyDecision:
    return PolicyDecision("allow", reason_code, message)


def _redirect(reason_code: str, message: str, suggested: str) -> PolicyDecision:
    return PolicyDecision("redirect", reason_code, message, suggested)


def _block(reason_code: str, message: str, suggested: str) -> PolicyDecision:
    return PolicyDecision("block", reason_code, message, suggested)


def evaluate_read(path: str) -> PolicyDecision:
    parts = [part for part in Path(path).parts if part not in ("", ".")]
    if any(part == ".mpga" for part in parts):
        return _redirect(
            "mpga_path_redirect",
            "Direct .mpga/ reads are blocked. Use mpga CLI commands instead.",
            "mpga search '<query>' or mpga session resume",
        )

    try:
        size = Path(path).expanduser().stat().st_size
    except OSError:
        size = 0
    if size > 16_000:
        return _redirect(
            "large_read_redirect",
            "Large direct file reads are blocked to protect context budget.",
            f"mpga ctx execute-file {path}",
        )

    return _allow()


def evaluate_bash(command: str) -> PolicyDecision:
    stripped = command.strip()
    if not stripped:
        return _allow()

    if stripped.startswith("mpga "):
        return _allow("mpga_command_allow", "mpga command allowed")

    lowered = stripped.lower()

    for pat in _NETWORK_PATTERNS:
        if pat.search(stripped):
            return _block(
                "network_fetch_blocked",
                "Direct network fetch patterns are blocked in hard-block mode.",
                "mpga ctx fetch-and-index <url> --source <label>",
            )

    if ".mpga/" in lowered:
        return _redirect(
            "mpga_path_redirect",
            "Direct reads from .mpga/ are blocked. Use mpga CLI commands instead.",
            "mpga search '<query>' or mpga session resume",
        )

    for pat in _SHELL_HEAVY_PATTERNS:
        if pat.search(stripped):
            return _redirect(
                "heavy_shell_redirect",
                "Potentially high-volume shell output is blocked in hard-block mode.",
                f"mpga ctx execute --code {command!r}",
            )

    return _allow()
