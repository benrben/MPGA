"""Heuristic observation extractor — zero API calls, pure functions."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3

from mpga.db.repos.observations import Observation

_ERROR_KEYWORDS = ("error", "traceback", "exception", "failed")
_DECISION_KEYWORDS = ("decided", "chose", "decision", "picked")
_DISCOVERY_KEYWORDS = ("found", "discovered", "noticed", "realized")
_PATTERN_KEYWORDS = ("pattern", "always", "consistently", "every time", "recurring", "repeated")


def classify_type(tool_name: str, tool_input: str, tool_output: str) -> str:
    output_lower = tool_output.lower()
    if any(w in output_lower for w in _ERROR_KEYWORDS):
        return "error"
    if any(w in output_lower for w in _DECISION_KEYWORDS):
        return "decision"
    if any(w in output_lower for w in _DISCOVERY_KEYWORDS):
        return "discovery"
    if any(w in output_lower for w in _PATTERN_KEYWORDS):
        return "pattern"
    return "tool_output"


def _generate_title(tool_name: str, tool_input: str, tool_output: str) -> str:
    filename = os.path.basename(tool_input.strip())
    if filename:
        return f"{tool_name} {filename}"
    return f"{tool_name} operation"


def _generate_narrative(tool_name: str, tool_input: str, tool_output: str) -> str:
    preview = tool_output[:80].replace("\n", " ")
    return f"{tool_name} on {tool_input}: {preview}"


def _extract_facts(tool_output: str) -> list[str]:
    lines = [ln.strip() for ln in tool_output.splitlines() if ln.strip()]
    return lines if lines else [tool_output[:120]]


def _extract_concepts(tool_output: str) -> list[str]:
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", tool_output)
    seen: set[str] = set()
    concepts: list[str] = []
    for w in words:
        low = w.lower()
        if low not in seen:
            seen.add(low)
            concepts.append(w)
    return concepts if concepts else ["unknown"]


def _extract_files_read(tool_name: str, tool_input: str) -> str:
    if tool_name == "Read":
        return json.dumps([tool_input.strip()])
    return json.dumps([])


def _extract_files_modified(tool_name: str, tool_input: str) -> str:
    if tool_name in ("Edit", "Write"):
        return json.dumps([tool_input.strip()])
    return json.dumps([])


def _compute_hash(tool_name: str, tool_input: str, tool_output: str) -> str:
    payload = f"{tool_name}\0{tool_input}\0{tool_output}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _assign_scope_naive(tool_input: str) -> str | None:
    path = tool_input.strip().lstrip("/")
    if "/" in path:
        return path.split("/")[0]
    return None


def extract_observation(
    tool_name: str,
    tool_input: str,
    tool_output: str,
    conn: "sqlite3.Connection | None" = None,
) -> Observation:
    files_read = _extract_files_read(tool_name, tool_input)
    files_modified = _extract_files_modified(tool_name, tool_input)

    scope_id: str | None = None
    if conn is not None:
        try:
            from mpga.memory.scope_heuristic import assign_scope

            scope_id = assign_scope(
                conn,
                json.loads(files_read) if files_read else [],
                json.loads(files_modified) if files_modified else [],
            )
        except (ImportError, sqlite3.Error, ValueError):
            scope_id = _assign_scope_naive(tool_input)
    else:
        scope_id = _assign_scope_naive(tool_input)

    return Observation(
        title=_generate_title(tool_name, tool_input, tool_output),
        type=classify_type(tool_name, tool_input, tool_output),
        narrative=_generate_narrative(tool_name, tool_input, tool_output),
        facts=json.dumps(_extract_facts(tool_output)),
        concepts=json.dumps(_extract_concepts(tool_output)),
        files_read=files_read,
        files_modified=files_modified,
        tool_name=tool_name,
        data_hash=_compute_hash(tool_name, tool_input, tool_output),
        scope_id=scope_id,
    )
