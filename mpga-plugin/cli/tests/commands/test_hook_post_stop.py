"""Tests for T002 — scorer protocol and data models.

Evidence: mpga-plugin/cli/src/mpga/commands/hook_post_stop.py (to be created)
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Action enum
# ---------------------------------------------------------------------------

def test_action_enum_has_do_nothing():
    from mpga.commands.hook_post_stop import Action
    assert Action.DO_NOTHING is not None


def test_action_enum_has_enqueue_improvement():
    from mpga.commands.hook_post_stop import Action
    assert Action.ENQUEUE_IMPROVEMENT is not None


def test_action_enum_has_enqueue_improvement_high_priority():
    from mpga.commands.hook_post_stop import Action
    assert Action.ENQUEUE_IMPROVEMENT_HIGH_PRIORITY is not None


def test_action_enum_has_exactly_three_members():
    from mpga.commands.hook_post_stop import Action
    assert len(list(Action)) == 3


# ---------------------------------------------------------------------------
# PostStopEnvelope dataclass
# ---------------------------------------------------------------------------

def test_post_stop_envelope_instantiates_with_required_fields():
    from mpga.commands.hook_post_stop import PostStopEnvelope
    env = PostStopEnvelope(
        hook_event_name="PostToolUse",
        session_id="sess-abc",
    )
    assert env.hook_event_name == "PostToolUse"
    assert env.session_id == "sess-abc"


def test_post_stop_envelope_defaults_optional_fields_to_none():
    from mpga.commands.hook_post_stop import PostStopEnvelope
    env = PostStopEnvelope(hook_event_name="Stop", session_id="sess-xyz")
    assert env.transcript_path is None
    assert env.error is None
    assert env.error_details is None
    assert env.last_assistant_message is None


def test_post_stop_envelope_accepts_all_fields():
    from mpga.commands.hook_post_stop import PostStopEnvelope
    env = PostStopEnvelope(
        hook_event_name="Stop",
        session_id="sess-123",
        transcript_path="/tmp/transcript.jsonl",
        error="SomeError",
        error_details="details here",
        last_assistant_message="I have finished.",
    )
    assert env.transcript_path == "/tmp/transcript.jsonl"
    assert env.error == "SomeError"
    assert env.error_details == "details here"
    assert env.last_assistant_message == "I have finished."


# ---------------------------------------------------------------------------
# ImprovementTarget dataclass
# ---------------------------------------------------------------------------

def test_improvement_target_instantiates_with_skill_type():
    from mpga.commands.hook_post_stop import ImprovementTarget
    t = ImprovementTarget(
        skill_or_agent_name="my-skill",
        file_path="/path/to/skill.py",
        target_type="skill",
    )
    assert t.skill_or_agent_name == "my-skill"
    assert t.file_path == "/path/to/skill.py"
    assert t.target_type == "skill"


def test_improvement_target_instantiates_with_agent_type():
    from mpga.commands.hook_post_stop import ImprovementTarget
    t = ImprovementTarget(
        skill_or_agent_name="my-agent",
        file_path="/path/to/agent.md",
        target_type="agent",
    )
    assert t.target_type == "agent"


def test_improvement_target_rejects_invalid_type_at_runtime():
    """target_type should be validated as 'skill' or 'agent'."""
    from mpga.commands.hook_post_stop import ImprovementTarget
    with pytest.raises(ValueError, match="target_type must be"):
        ImprovementTarget(
            skill_or_agent_name="x",
            file_path="/x",
            target_type="invalid",
        )


# ---------------------------------------------------------------------------
# ScorerProtocol structural check
# ---------------------------------------------------------------------------

def test_scorer_protocol_is_a_protocol():
    """ScorerProtocol must be a typing.Protocol (not an ABC)."""
    from mpga.commands.hook_post_stop import ScorerProtocol
    from typing import Protocol
    # Protocol classes have _is_protocol = True
    assert getattr(ScorerProtocol, "_is_protocol", False) is True


def test_concrete_scorer_satisfies_protocol_structurally():
    """A class implementing detect/score/route methods satisfies the protocol."""
    from mpga.commands.hook_post_stop import Action, ScorerProtocol

    class ConcreteScorer:
        def detect(self, envelope: dict) -> bool:
            return True

        def score(self, envelope: dict) -> dict:
            return {"quality": 1.0}

        def route(self, scores: dict) -> str:
            return Action.DO_NOTHING.value

    scorer: ScorerProtocol = ConcreteScorer()  # type: ignore[assignment]
    assert scorer.detect({}) is True
    assert scorer.score({}) == {"quality": 1.0}
    assert scorer.route({}) == Action.DO_NOTHING.value


def test_scorer_protocol_requires_detect_method():
    from mpga.commands.hook_post_stop import ScorerProtocol
    assert hasattr(ScorerProtocol, "detect")


def test_scorer_protocol_requires_score_method():
    from mpga.commands.hook_post_stop import ScorerProtocol
    assert hasattr(ScorerProtocol, "score")


def test_scorer_protocol_requires_route_method():
    from mpga.commands.hook_post_stop import ScorerProtocol
    assert hasattr(ScorerProtocol, "route")


# ---------------------------------------------------------------------------
# T003 spike: PostStopEnvelope.from_dict — Stop payload parsing
# ---------------------------------------------------------------------------

_STOP_PAYLOAD = {
    "session_id": "bafd87fc-b27e-49ab-9fca-6b32c6f34877",
    "transcript_path": "/tmp/sessions/bafd87fc.jsonl",
    "cwd": "/Users/benreich/MPGA",
    "permission_mode": "ask",
    "hook_event_name": "Stop",
    "reason": "Task appears complete",
}

_STOP_FAILURE_PAYLOAD = {
    "session_id": "bafd87fc-b27e-49ab-9fca-6b32c6f34877",
    "transcript_path": "/tmp/sessions/bafd87fc.jsonl",
    "cwd": "/Users/benreich/MPGA",
    "permission_mode": "ask",
    "hook_event_name": "StopFailure",
    "error": "rate_limit_error",
    "error_details": "You have exceeded your API rate limit.",
}


def test_post_stop_envelope_from_dict_parses_stop_payload():
    """from_dict must parse a Stop hook payload into a PostStopEnvelope."""
    from mpga.commands.hook_post_stop import PostStopEnvelope
    env = PostStopEnvelope.from_dict(_STOP_PAYLOAD)
    assert env.hook_event_name == "Stop"
    assert env.session_id == "bafd87fc-b27e-49ab-9fca-6b32c6f34877"
    assert env.transcript_path == "/tmp/sessions/bafd87fc.jsonl"
    assert env.stop_reason == "Task appears complete"
    assert env.error is None
    assert env.error_details is None
    assert env.last_assistant_message is None


def test_post_stop_envelope_from_dict_parses_stop_failure_payload():
    """from_dict must parse a StopFailure hook payload into a PostStopEnvelope."""
    from mpga.commands.hook_post_stop import PostStopEnvelope
    env = PostStopEnvelope.from_dict(_STOP_FAILURE_PAYLOAD)
    assert env.hook_event_name == "StopFailure"
    assert env.session_id == "bafd87fc-b27e-49ab-9fca-6b32c6f34877"
    assert env.transcript_path == "/tmp/sessions/bafd87fc.jsonl"
    assert env.stop_reason is None
    assert env.error == "rate_limit_error"
    assert env.error_details == "You have exceeded your API rate limit."
    assert env.last_assistant_message is None


def test_post_stop_envelope_from_dict_handles_missing_optional_fields():
    """from_dict must tolerate payloads with only required fields."""
    from mpga.commands.hook_post_stop import PostStopEnvelope
    minimal = {
        "session_id": "sess-min",
        "hook_event_name": "Stop",
    }
    env = PostStopEnvelope.from_dict(minimal)
    assert env.session_id == "sess-min"
    assert env.hook_event_name == "Stop"
    assert env.transcript_path is None
    assert env.stop_reason is None
    assert env.error is None
    assert env.error_details is None
    assert env.last_assistant_message is None


def test_post_stop_envelope_stop_reason_field_exists():
    """PostStopEnvelope must have a stop_reason field (T003 spike finding: Stop uses 'reason' key)."""
    from mpga.commands.hook_post_stop import PostStopEnvelope
    env = PostStopEnvelope(hook_event_name="Stop", session_id="sess-x", stop_reason="done")
    assert env.stop_reason == "done"


def test_post_stop_envelope_from_dict_is_classmethod():
    """from_dict must be a classmethod on PostStopEnvelope."""
    from mpga.commands.hook_post_stop import PostStopEnvelope
    import inspect
    assert isinstance(
        inspect.getattr_static(PostStopEnvelope, "from_dict"),
        classmethod,
    )


# ---------------------------------------------------------------------------
# T004: hook post-stop CLI command
# ---------------------------------------------------------------------------


def test_post_stop_command_handles_stop_failure_payload(tmp_path, monkeypatch):
    """post-stop command must process a StopFailure JSON payload without error."""
    import json
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))
    (tmp_path / ".mpga").mkdir(parents=True, exist_ok=True)

    from click.testing import CliRunner
    from mpga.commands.hook import hook

    payload = json.dumps({
        "hook_event_name": "StopFailure",
        "session_id": "test-session-123",
        "transcript_path": str(tmp_path / "transcript.jsonl"),
        "error": "rate_limit_error",
        "error_details": "429 Too Many Requests",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["post-stop"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0


def test_post_stop_command_handles_stop_payload(tmp_path, monkeypatch):
    """post-stop command must process a Stop JSON payload without error."""
    import json
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))
    (tmp_path / ".mpga").mkdir(parents=True, exist_ok=True)

    from click.testing import CliRunner
    from mpga.commands.hook import hook

    payload = json.dumps({
        "hook_event_name": "Stop",
        "session_id": "test-session-456",
        "transcript_path": str(tmp_path / "transcript.jsonl"),
        "reason": "Task appears complete",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["post-stop"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0


def test_post_stop_command_handles_empty_stdin(tmp_path, monkeypatch):
    """post-stop command must return cleanly on empty stdin input."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from click.testing import CliRunner
    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["post-stop"], input="", catch_exceptions=False)
    assert result.exit_code == 0


def test_post_stop_command_handles_invalid_json(tmp_path, monkeypatch):
    """post-stop command must return cleanly on malformed JSON input."""
    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: str(tmp_path))

    from click.testing import CliRunner
    from mpga.commands.hook import hook

    runner = CliRunner()
    result = runner.invoke(hook, ["post-stop"], input="not valid json {{", catch_exceptions=False)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# T005: OutcomeScorer
# ---------------------------------------------------------------------------


def test_outcome_scorer_stop_is_pass():
    """Stop hook_event_name must score as outcome=pass."""
    from mpga.commands.hook_post_stop import OutcomeScorer
    scorer = OutcomeScorer()
    scores = scorer.score({"hook_event_name": "Stop"})
    assert scores["outcome"] == "pass"


def test_outcome_scorer_stop_failure_is_fail():
    """StopFailure hook_event_name must score as outcome=fail."""
    from mpga.commands.hook_post_stop import OutcomeScorer
    scorer = OutcomeScorer()
    scores = scorer.score({"hook_event_name": "StopFailure"})
    assert scores["outcome"] == "fail"


def test_outcome_scorer_fail_routes_enqueue():
    """outcome=fail must route to ENQUEUE_IMPROVEMENT."""
    from mpga.commands.hook_post_stop import Action, OutcomeScorer
    scorer = OutcomeScorer()
    assert scorer.route({"outcome": "fail"}) == Action.ENQUEUE_IMPROVEMENT


def test_outcome_scorer_pass_routes_do_nothing():
    """outcome=pass must route to DO_NOTHING."""
    from mpga.commands.hook_post_stop import Action, OutcomeScorer
    scorer = OutcomeScorer()
    assert scorer.route({"outcome": "pass"}) == Action.DO_NOTHING


def test_outcome_scorer_detect_always_true():
    """OutcomeScorer.detect must return True for any envelope."""
    from mpga.commands.hook_post_stop import OutcomeScorer
    scorer = OutcomeScorer()
    assert scorer.detect({}) is True
    assert scorer.detect({"hook_event_name": "Stop"}) is True
    assert scorer.detect({"hook_event_name": "StopFailure"}) is True


# ---------------------------------------------------------------------------
# T005: SeverityScorer
# ---------------------------------------------------------------------------


def test_severity_scorer_detects_only_when_error_present():
    """SeverityScorer.detect must return True only when envelope has an error field."""
    from mpga.commands.hook_post_stop import SeverityScorer
    scorer = SeverityScorer()
    assert scorer.detect({"error": "rate_limit"}) is True
    assert scorer.detect({}) is False


def test_severity_scorer_classifies_timeout():
    """Error strings matching timeout|timed.out must score severity=timeout."""
    from mpga.commands.hook_post_stop import SeverityScorer
    scorer = SeverityScorer()
    assert scorer.score({"error": "operation timed out"})["severity"] == "timeout"


def test_severity_scorer_classifies_api_error():
    """Error strings matching rate.limit|429|api.error|overloaded must score severity=api_error."""
    from mpga.commands.hook_post_stop import SeverityScorer
    scorer = SeverityScorer()
    assert scorer.score({"error": "rate_limit_error 429"})["severity"] == "api_error"


def test_severity_scorer_classifies_permission():
    """Error strings matching permission.denied|forbidden|403 must score severity=permission."""
    from mpga.commands.hook_post_stop import SeverityScorer
    scorer = SeverityScorer()
    assert scorer.score({"error": "permission denied reading file"})["severity"] == "permission"


def test_severity_scorer_classifies_unknown_fallback():
    """Error strings matching no pattern must score severity=unknown."""
    from mpga.commands.hook_post_stop import SeverityScorer
    scorer = SeverityScorer()
    assert scorer.score({"error": "something weird happened"})["severity"] == "unknown"


def test_severity_scorer_route_non_unknown_enqueues():
    """Non-unknown severity must route to ENQUEUE_IMPROVEMENT."""
    from mpga.commands.hook_post_stop import Action, SeverityScorer
    scorer = SeverityScorer()
    for severity in ("timeout", "permission", "api_error"):
        assert scorer.route({"severity": severity}) == Action.ENQUEUE_IMPROVEMENT


def test_severity_scorer_route_unknown_does_nothing():
    """Unknown severity must route to DO_NOTHING."""
    from mpga.commands.hook_post_stop import Action, SeverityScorer
    scorer = SeverityScorer()
    assert scorer.route({"severity": "unknown"}) == Action.DO_NOTHING


# ---------------------------------------------------------------------------
# T006: RecurrenceScorer
# ---------------------------------------------------------------------------


def test_recurrence_scorer_detects_with_error():
    from mpga.commands.hook_post_stop import RecurrenceScorer
    scorer = RecurrenceScorer()
    assert scorer.detect({"error": "some error"}) is True


def test_recurrence_scorer_no_detect_without_error():
    from mpga.commands.hook_post_stop import RecurrenceScorer
    scorer = RecurrenceScorer()
    assert scorer.detect({}) is False


def test_recurrence_scorer_normalizes_timestamps():
    from mpga.commands.hook_post_stop import RecurrenceScorer
    scorer = RecurrenceScorer()
    e1 = "Failed at 2024-01-01 12:34:56"
    e2 = "Failed at 2024-12-31 23:59:59"
    # Both normalize to the same string
    assert scorer._normalize(e1) == scorer._normalize(e2)


def test_recurrence_scorer_hash_is_deterministic():
    from mpga.commands.hook_post_stop import RecurrenceScorer
    scorer = RecurrenceScorer()
    scores1 = scorer.score({"error": "rate_limit_error"})
    scores2 = scorer.score({"error": "rate_limit_error"})
    assert scores1["error_hash"] == scores2["error_hash"]


def test_recurrence_scorer_no_db_returns_zero_counts():
    from mpga.commands.hook_post_stop import RecurrenceScorer
    scorer = RecurrenceScorer()  # no conn
    scores = scorer.score({"error": "some error"})
    assert scores["recurrence_24h"] == 0
    assert scores["recurrence_alltime"] == 0


def test_recurrence_scorer_with_db_counts_observations(tmp_path):
    from mpga.commands.hook_post_stop import RecurrenceScorer
    # Setup: create DB with 2 observations having same error hash
    import sqlite3
    from mpga.db.schema import create_schema
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    create_schema(conn)
    now = "2025-01-01T12:00:00"
    scorer = RecurrenceScorer(conn=conn)
    error = "rate_limit_error"
    normalized = scorer._normalize(error)
    import hashlib
    error_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    # Insert 2 observations with matching data_hash
    conn.execute(
        "INSERT INTO observations (title, type, data_hash, created_at) VALUES (?, ?, ?, ?)",
        ("err", "stop_event", error_hash, now)
    )
    conn.execute(
        "INSERT INTO observations (title, type, data_hash, created_at) VALUES (?, ?, ?, ?)",
        ("err", "stop_event", error_hash, now)
    )
    conn.commit()
    scores = scorer.score({"error": error})
    assert scores["recurrence_alltime"] == 2


# ---------------------------------------------------------------------------
# T007: route_action
# ---------------------------------------------------------------------------


def test_route_action_stop_failure_enqueues():
    from mpga.commands.hook_post_stop import Action, route_action
    action = route_action({"hook_event_name": "StopFailure", "session_id": "s1", "error": "rate_limit"})
    assert action == Action.ENQUEUE_IMPROVEMENT


def test_route_action_stop_below_threshold_does_nothing():
    from mpga.commands.hook_post_stop import Action, route_action
    action = route_action({"hook_event_name": "Stop", "session_id": "s1"})
    assert action == Action.DO_NOTHING


def test_route_action_stop_failure_no_error_still_enqueues():
    # StopFailure with no error field still enqueues (outcome=fail is sufficient)
    from mpga.commands.hook_post_stop import Action, route_action
    action = route_action({"hook_event_name": "StopFailure", "session_id": "s1"})
    assert action == Action.ENQUEUE_IMPROVEMENT


def test_route_action_stop_at_recurrence_threshold_unknown_severity_does_nothing(tmp_path):
    # recurrence >= 3 but severity is unknown → DO_NOTHING
    import sqlite3
    import hashlib
    from mpga.db.schema import create_schema
    from mpga.commands.hook_post_stop import RecurrenceScorer, Action, route_action
    conn = sqlite3.connect(str(tmp_path / "db.db"))
    create_schema(conn)
    scorer = RecurrenceScorer(conn=conn)
    error = "something completely unrecognizable blarg 12345"
    normalized = scorer._normalize(error)
    h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    now = "2025-01-01T00:00:00"
    for _ in range(3):
        conn.execute("INSERT INTO observations (title, type, data_hash, created_at) VALUES (?, ?, ?, ?)", ("x", "stop_event", h, now))
    conn.commit()
    action = route_action({"hook_event_name": "Stop", "session_id": "s1", "error": error}, conn=conn)
    assert action == Action.DO_NOTHING


def test_route_action_stop_at_recurrence_threshold_known_severity_enqueues(tmp_path):
    # recurrence >= 3 AND known severity → ENQUEUE_IMPROVEMENT
    import sqlite3
    import hashlib
    from mpga.db.schema import create_schema
    from mpga.commands.hook_post_stop import RecurrenceScorer, Action, route_action
    conn = sqlite3.connect(str(tmp_path / "db.db"))
    create_schema(conn)
    scorer = RecurrenceScorer(conn=conn)
    error = "rate_limit_error 429"
    normalized = scorer._normalize(error)
    h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    # Use current time so the 24h window includes these rows
    now = conn.execute("SELECT datetime('now')").fetchone()[0]
    for _ in range(3):
        conn.execute("INSERT INTO observations (title, type, data_hash, created_at) VALUES (?, ?, ?, ?)", ("x", "stop_event", h, now))
    conn.commit()
    action = route_action({"hook_event_name": "Stop", "session_id": "s1", "error": error}, conn=conn)
    assert action == Action.ENQUEUE_IMPROVEMENT


def test_route_action_stop_recurrence_below_3_does_nothing(tmp_path):
    # Only 2 occurrences → below threshold → DO_NOTHING even with known severity
    import sqlite3
    import hashlib
    from mpga.db.schema import create_schema
    from mpga.commands.hook_post_stop import RecurrenceScorer, Action, route_action
    conn = sqlite3.connect(str(tmp_path / "db.db"))
    create_schema(conn)
    scorer = RecurrenceScorer(conn=conn)
    error = "rate_limit_error"
    normalized = scorer._normalize(error)
    h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    now = "2025-01-01T00:00:00"
    for _ in range(2):
        conn.execute("INSERT INTO observations (title, type, data_hash, created_at) VALUES (?, ?, ?, ?)", ("x", "stop_event", h, now))
    conn.commit()
    action = route_action({"hook_event_name": "Stop", "session_id": "s1", "error": error}, conn=conn)
    assert action == Action.DO_NOTHING


# ---------------------------------------------------------------------------
# T008: LLMEscalationScorer
# ---------------------------------------------------------------------------


def test_llm_escalation_scorer_escalates_long_unknown_error():
    from mpga.commands.hook_post_stop import LLMEscalationScorer, Action
    scorer = LLMEscalationScorer()
    # long unrecognized error string
    envelope = {"error": "something completely unrecognizable and quite long blarg xyz"}
    assert scorer.detect(envelope) is True
    scores = scorer.score(envelope)
    assert scores["escalate_to_llm"] is True
    assert scorer.route(scores) == Action.ENQUEUE_IMPROVEMENT


def test_llm_escalation_scorer_no_escalate_short_error():
    from mpga.commands.hook_post_stop import LLMEscalationScorer
    scorer = LLMEscalationScorer()
    assert scorer.detect({"error": "short err"}) is False


def test_llm_escalation_scorer_no_escalate_known_severity():
    from mpga.commands.hook_post_stop import LLMEscalationScorer
    scorer = LLMEscalationScorer()
    # rate_limit_error matches api_error pattern — not unknown
    assert scorer.detect({"error": "rate_limit_error 429 too many requests"}) is False


def test_llm_escalation_scorer_no_escalate_without_error():
    from mpga.commands.hook_post_stop import LLMEscalationScorer
    scorer = LLMEscalationScorer()
    assert scorer.detect({}) is False


# ---------------------------------------------------------------------------
# T009: hook post-stop wired with route_action and enqueue
# ---------------------------------------------------------------------------


def test_post_stop_stop_failure_enqueues_improvement(tmp_path, monkeypatch):
    import json
    import sqlite3
    from click.testing import CliRunner
    from mpga.commands.hook import hook
    from mpga.db.schema import create_schema

    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)
    (tmp_path / ".mpga").mkdir()

    payload = json.dumps({
        "hook_event_name": "StopFailure",
        "session_id": "test-sid",
        "error": "rate_limit_error",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["post-stop"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = sqlite3.connect(str(db_path))
    create_schema(conn)
    items = conn.execute("SELECT * FROM observation_queue WHERE tool_name='post-stop'").fetchall()
    assert len(items) >= 1


def test_post_stop_stop_below_threshold_no_enqueue(tmp_path, monkeypatch):
    import json
    import sqlite3
    from click.testing import CliRunner
    from mpga.commands.hook import hook

    monkeypatch.setattr("mpga.commands.session.find_project_root", lambda: tmp_path)
    (tmp_path / ".mpga").mkdir()

    payload = json.dumps({
        "hook_event_name": "Stop",
        "session_id": "test-sid",
        "reason": "Task appears complete",
    })
    runner = CliRunner()
    result = runner.invoke(hook, ["post-stop"], input=payload, catch_exceptions=False)
    assert result.exit_code == 0

    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = sqlite3.connect(str(db_path))
    items = conn.execute("SELECT * FROM observation_queue WHERE tool_name='post-stop'").fetchall()
    assert len(items) == 0
