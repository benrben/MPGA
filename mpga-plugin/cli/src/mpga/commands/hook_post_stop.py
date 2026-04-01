"""Scorer protocol and shared data models for post-stop hook processing.

This module defines the structural contracts (Protocol, dataclasses, enums)
that all scorer implementations (T005–T008) must satisfy.

Evidence:
  - observations table columns: mpga-plugin/cli/src/mpga/db/schema.py:236-252

# ── T003 SPIKE: Empirical Stop/StopFailure Hook Payload Documentation ──────

Stop payload (confirmed fields):
  {
    "session_id": "<uuid>",
    "transcript_path": "/path/to/<session_id>.jsonl",  # ALWAYS present
    "cwd": "/project/root",
    "permission_mode": "ask|allow",
    "hook_event_name": "Stop",
    "reason": "Task appears complete"   # Stop-specific; absent on StopFailure
  }

StopFailure payload (confirmed + inferred fields):
  {
    "session_id": "<uuid>",
    "transcript_path": "/path/to/<session_id>.jsonl",  # ALWAYS present
    "cwd": "/project/root",
    "permission_mode": "ask|allow",
    "hook_event_name": "StopFailure",
    "error": "rate_limit_error",        # fires on API errors (CC v2.1.78+)
    "error_details": "..."              # [Inferred] may be absent; see tmp/stop_failure_hook_sample.json
  }

transcript_path availability:
  CONFIRMED PRESENT on Stop hooks. Empirical evidence:
  - .claude/plugins/.../skills/plugin-settings/references/real-world-examples.md:183
    (ralph-wiggum hook reads transcript_path from $HOOK_INPUT via jq -r '.transcript_path')
  - .claude/plugins/.../skills/hook-development/SKILL.md:307 (listed as common field)
  The path points to a JSONL file of the session transcript. For resumed/forked sessions,
  confirmed fixed in CC v2.0.x (changelog: "transcript_path pointing to wrong directory
  for resumed/forked sessions — fixed").

UserPromptSubmit field name:
  The payload field is "user_prompt" (NOT "user_message"). Evidence:
  - hook-development/SKILL.md:317: "UserPromptSubmit: user_prompt"
  - test-hook.sh:79: "user_prompt": "Test user prompt"
  BUG: mpga/commands/hook.py capture-user-prompt reads data.get("user_message") — always
  empty. The field name must be changed to "user_prompt" in that handler.
  Slash-command text (e.g. "/mpga:develop") IS available in user_prompt.

UserPromptSubmit hook registration:
  CONFIRMED — mpga-plugin/hooks/hooks.json:72-81 already has the UserPromptSubmit entry
  pointing to 'capture-user-prompt'. The hook fires before each user turn.

PostStopEnvelope field alignment:
  - "reason" field (Stop) maps to → last_assistant_message [workaround; consider adding
    a dedicated `stop_reason` field in a future revision]
  - "error" field (StopFailure) maps to → error ✓
  - "error_details" field (StopFailure, inferred) maps to → error_details ✓

Empirical samples: tmp/stop_hook_sample.json, tmp/stop_failure_hook_sample.json,
tmp/user_prompt_hook_sample.json
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

__all__ = [
    "Action",
    "PostStopEnvelope",
    "ImprovementTarget",
    "ScorerProtocol",
    "OutcomeScorer",
    "SeverityScorer",
    "RecurrenceScorer",
    "route_action",
    "LLMEscalationScorer",
]

_VALID_TARGET_TYPES = frozenset({"skill", "agent"})


# ---------------------------------------------------------------------------
# Action enum
# ---------------------------------------------------------------------------


class Action(str, Enum):
    """Possible routing decisions emitted by a scorer's route() method."""

    DO_NOTHING = "do_nothing"
    ENQUEUE_IMPROVEMENT = "enqueue_improvement"
    ENQUEUE_IMPROVEMENT_HIGH_PRIORITY = "enqueue_improvement_high_priority"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PostStopEnvelope:
    """Captures all context available at post-stop hook time.

    Required fields reflect what Claude Code always provides.
    Optional fields (None by default) may not be present in every event.

    Field mapping from raw hook JSON (T003 spike findings):
      hook_event_name  ← "hook_event_name"   (always present, added CC v1.0.41)
      session_id       ← "session_id"         (always present)
      transcript_path  ← "transcript_path"    (always present; confirmed CC docs)
      stop_reason      ← "reason"             (Stop only — "Task appears complete")
      error            ← "error"              (StopFailure only — e.g. "rate_limit_error")
      error_details    ← "error_details"      (StopFailure, inferred; may be absent)
      last_assistant_message — not in raw payload; populated by async worker from transcript
    """

    hook_event_name: str
    session_id: str
    transcript_path: str | None = field(default=None)
    stop_reason: str | None = field(default=None)
    error: str | None = field(default=None)
    error_details: str | None = field(default=None)
    last_assistant_message: str | None = field(default=None)

    @classmethod
    def from_dict(cls, data: dict) -> "PostStopEnvelope":
        """Parse a raw Stop/StopFailure hook JSON payload into a PostStopEnvelope.

        Args:
            data: Parsed JSON dict from Claude Code hook stdin.

        Returns:
            PostStopEnvelope populated from the provided dict.
        """
        return cls(
            hook_event_name=data["hook_event_name"],
            session_id=data["session_id"],
            transcript_path=data.get("transcript_path"),
            stop_reason=data.get("reason"),
            error=data.get("error"),
            error_details=data.get("error_details"),
            last_assistant_message=None,  # populated later by async worker
        )


@dataclass
class ImprovementTarget:
    """Identifies the skill or agent file that a scorer recommends improving.

    Attributes:
        skill_or_agent_name: Human-readable name (e.g. "mpga-develop").
        file_path: Absolute path to the file on disk.
        target_type: Either "skill" or "agent".
    """

    skill_or_agent_name: str
    file_path: str
    target_type: str

    def __post_init__(self) -> None:
        if self.target_type not in _VALID_TARGET_TYPES:
            raise ValueError(
                f"target_type must be one of {sorted(_VALID_TARGET_TYPES)!r}, "
                f"got {self.target_type!r}"
            )


# ---------------------------------------------------------------------------
# ScorerProtocol
# ---------------------------------------------------------------------------


class ScorerProtocol(Protocol):
    """Structural protocol that every scorer must satisfy.

    Scorers are discovered and called by the post-stop hook dispatcher.
    All three methods must be implemented; they must be pure and side-effect-free.
    """

    def detect(self, envelope: dict) -> bool:
        """Return True if this scorer is applicable to the given envelope."""
        ...

    def score(self, envelope: dict) -> dict:
        """Compute and return a dict of named scores (floats or booleans)."""
        ...

    def route(self, scores: dict) -> str:
        """Map scores to an Action value string (use Action.<X>.value)."""
        ...


# ---------------------------------------------------------------------------
# Severity classification patterns (T005)
# ---------------------------------------------------------------------------

_SEVERITY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("timeout", r"timeout|timed.out"),
    ("permission", r"permission.denied|forbidden|403"),
    ("api_error", r"rate.limit|429|api.error|overloaded"),
)


# ---------------------------------------------------------------------------
# OutcomeScorer (T005)
# ---------------------------------------------------------------------------


class OutcomeScorer:
    """Scores a hook envelope by its outcome (pass/fail) and routes accordingly.

    Applies to all events (detect always returns True).
    Stop  → outcome=pass → DO_NOTHING
    StopFailure → outcome=fail → ENQUEUE_IMPROVEMENT

    Evidence: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T005
    """

    def detect(self, envelope: dict) -> bool:
        """Always applicable — return True for every envelope."""
        return True

    def score(self, envelope: dict) -> dict:
        """Return {"outcome": "pass"} for Stop, {"outcome": "fail"} for StopFailure."""
        event = envelope.get("hook_event_name", "")
        outcome = "pass" if event == "Stop" else "fail"
        return {"outcome": outcome}

    def route(self, scores: dict) -> Action:
        """Route fail → ENQUEUE_IMPROVEMENT, pass → DO_NOTHING."""
        if scores.get("outcome") == "fail":
            return Action.ENQUEUE_IMPROVEMENT
        return Action.DO_NOTHING


# ---------------------------------------------------------------------------
# SeverityScorer (T005)
# ---------------------------------------------------------------------------


class SeverityScorer:
    """Classifies error severity and routes non-unknown errors for improvement.

    Applies only when the envelope contains an "error" field.
    Classification order (first match wins):
      timeout    — matches r"timeout|timed.out"
      permission — matches r"permission.denied|forbidden|403"
      api_error  — matches r"rate.limit|429|api.error|overloaded"
      unknown    — fallback

    Routing:
      timeout / permission / api_error → ENQUEUE_IMPROVEMENT
      unknown                          → DO_NOTHING

    Evidence: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T005
    """

    def detect(self, envelope: dict) -> bool:
        """Return True only if the envelope has a non-None "error" field."""
        return bool(envelope.get("error"))

    def score(self, envelope: dict) -> dict:
        """Classify the error string and return {"severity": <classification>}."""
        error_text = envelope.get("error", "") or ""
        for severity_label, pattern in _SEVERITY_PATTERNS:
            if re.search(pattern, error_text, re.IGNORECASE):
                return {"severity": severity_label}
        return {"severity": "unknown"}

    def route(self, scores: dict) -> Action:
        """Route non-unknown severity to ENQUEUE_IMPROVEMENT; unknown to DO_NOTHING."""
        if scores.get("severity", "unknown") == "unknown":
            return Action.DO_NOTHING
        return Action.ENQUEUE_IMPROVEMENT


# ---------------------------------------------------------------------------
# Normalization patterns (T006)
# ---------------------------------------------------------------------------

_NORMALIZE_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"), ""),
    (re.compile(r"/[^ ]+\.py:\d+"), ""),
    (re.compile(r"/[^ ]+/[^ ]+"), ""),
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE), ""),
    (re.compile(r"0x[0-9a-f]+", re.IGNORECASE), ""),
    (re.compile(r"line \d+"), ""),
    (re.compile(r"\b\d{2,}\b"), ""),
)


# ---------------------------------------------------------------------------
# RecurrenceScorer (T006)
# ---------------------------------------------------------------------------


class RecurrenceScorer:
    """Counts how often a normalized error string has been seen in the observations DB.

    Applies only when the envelope contains an "error" field.
    Recurrence does not route directly — returns DO_NOTHING always.
    The action router (T007) combines recurrence scores with other scorer outputs.

    Constructor:
        conn: Optional sqlite3.Connection. When None, recurrence counts default to 0
              (graceful degradation). When provided, queries the observations table
              for matching data_hash entries.

    score() returns:
        {
            "recurrence_24h": <int>,
            "recurrence_alltime": <int>,
            "error_hash": "<16-char hex>",
        }

    Evidence: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T006
    """

    def __init__(self, conn=None) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # ScorerProtocol implementation
    # ------------------------------------------------------------------

    def detect(self, envelope: dict) -> bool:
        """Return True only if the envelope has a non-None "error" field."""
        return bool(envelope.get("error"))

    def score(self, envelope: dict) -> dict:
        """Return recurrence counts and the canonical error hash.

        When no DB connection is available, counts are 0.
        """
        error_text = envelope.get("error", "") or ""
        normalized = self._normalize(error_text)
        error_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]

        recurrence_24h = 0
        recurrence_alltime = 0

        if self._conn is not None:
            try:
                row = self._conn.execute(
                    "SELECT COUNT(*) FROM observations WHERE data_hash = ?",
                    (error_hash,),
                ).fetchone()
                recurrence_alltime = row[0] if row else 0

                row_24h = self._conn.execute(
                    "SELECT COUNT(*) FROM observations WHERE data_hash = ?"
                    " AND created_at >= datetime('now', '-1 day')",
                    (error_hash,),
                ).fetchone()
                recurrence_24h = row_24h[0] if row_24h else 0
            except Exception:
                # Graceful degradation — DB errors should not crash the scorer
                recurrence_24h = 0
                recurrence_alltime = 0

        return {
            "recurrence_24h": recurrence_24h,
            "recurrence_alltime": recurrence_alltime,
            "error_hash": error_hash,
        }

    def route(self, scores: dict) -> Action:
        """Recurrence does not route directly — always returns DO_NOTHING."""
        return Action.DO_NOTHING

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize(self, error: str) -> str:
        """Strip volatile tokens (timestamps, paths, UUIDs, addresses) from an error string.

        Returns a stable canonical string suitable for hashing and deduplication.
        """
        result = error
        for pattern, replacement in _NORMALIZE_PATTERNS:
            result = pattern.sub(replacement, result)
        # Collapse extra whitespace produced by stripping tokens
        result = re.sub(r"\s+", " ", result).strip()
        return result


# ---------------------------------------------------------------------------
# Action router (T007)
# ---------------------------------------------------------------------------


def route_action(envelope: dict, conn=None) -> Action:
    """Orchestrate all scorers and return the appropriate Action.

    Decision logic:
      - StopFailure (outcome=fail)           → ENQUEUE_IMPROVEMENT (always)
      - Stop with recurrence_24h >= 3 AND
        known severity (not "unknown")       → ENQUEUE_IMPROVEMENT
      - Everything else                      → DO_NOTHING

    Args:
        envelope: Raw hook JSON dict (hook_event_name, session_id, error, …).
        conn: Optional sqlite3.Connection for recurrence lookups.

    Returns:
        Action enum value.

    Evidence: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T007
    """
    outcome = OutcomeScorer()
    severity = SeverityScorer()
    recurrence = RecurrenceScorer(conn=conn)

    outcome_scores = outcome.score(envelope) if outcome.detect(envelope) else {}
    severity_scores = severity.score(envelope) if severity.detect(envelope) else {"severity": "unknown"}
    recurrence_scores = recurrence.score(envelope) if recurrence.detect(envelope) else {"recurrence_24h": 0}

    # StopFailure: outcome=fail is sufficient to enqueue
    if outcome_scores.get("outcome") == "fail":
        return Action.ENQUEUE_IMPROVEMENT

    # Stop events: only enqueue when recurrence threshold met AND known error type
    if recurrence_scores.get("recurrence_24h", 0) >= 3 and severity_scores.get("severity", "unknown") != "unknown":
        return Action.ENQUEUE_IMPROVEMENT

    return Action.DO_NOTHING


# ---------------------------------------------------------------------------
# LLM escalation threshold (T008)
# ---------------------------------------------------------------------------

_LLM_ESCALATION_MIN_LENGTH = 20


# ---------------------------------------------------------------------------
# LLMEscalationScorer (T008)
# ---------------------------------------------------------------------------


class LLMEscalationScorer:
    """Escalates unclassified long errors to the async LLM improvement queue.

    Applies when an error is present, classified as "unknown" severity by
    SeverityScorer, AND the error string exceeds _LLM_ESCALATION_MIN_LENGTH
    characters.  This ensures the async worker gets a chance to inspect the
    full transcript when the deterministic rules cannot classify the error.

    Routing:
      escalate_to_llm=True  → ENQUEUE_IMPROVEMENT
      escalate_to_llm=False → DO_NOTHING

    Evidence: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T008
    """

    def detect(self, envelope: dict) -> bool:
        """Return True when error is present, unknown severity, and long enough."""
        error = envelope.get("error", "")
        if not error:
            return False
        severity_scores = SeverityScorer().score({"error": error})
        return (
            severity_scores.get("severity") == "unknown"
            and len(error) > _LLM_ESCALATION_MIN_LENGTH
        )

    def score(self, envelope: dict) -> dict:
        """Return escalation decision and human-readable reason."""
        error = envelope.get("error", "")
        severity_scores = SeverityScorer().score({"error": error})
        if severity_scores.get("severity") == "unknown" and len(error) > _LLM_ESCALATION_MIN_LENGTH:
            return {
                "escalate_to_llm": True,
                "reason": "unclassified error exceeds length threshold",
            }
        return {"escalate_to_llm": False, "reason": "classified or too short"}

    def route(self, scores: dict) -> Action:
        """Route to ENQUEUE_IMPROVEMENT when escalation is warranted."""
        if scores.get("escalate_to_llm"):
            return Action.ENQUEUE_IMPROVEMENT
        return Action.DO_NOTHING



# ---------------------------------------------------------------------------
# Re-export worker symbols for backwards-compatible imports
# (ImprovementTarget and Action are defined above, so this import is safe)
# ---------------------------------------------------------------------------
from mpga.commands.hook_post_stop_worker import (  # noqa: E402, F401
    ImprovementValidationError,
    generate_improvement,
    write_improvement,
    process_improvement_queue,
)
