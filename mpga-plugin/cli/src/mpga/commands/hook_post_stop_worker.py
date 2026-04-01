"""LLM improvement prompt, file writer, and async improvement worker.

Extracted from hook_post_stop.py to keep source files under 500 lines.

Evidence:
  - mpga-plugin/cli/src/mpga/commands/hook_post_stop.py — T014, T012
  - mpga-plugin/cli/src/mpga/db/schema.py:255-263 — observation_queue schema
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3 as _sqlite3
from pathlib import Path

from mpga.commands.hook_post_stop import Action, ImprovementTarget

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM improvement prompt and file writer (T014)
# ---------------------------------------------------------------------------

_IMPROVEMENT_PROMPT_TEMPLATE = """You are improving a Claude Code skill/agent file to fix a recurring issue.

Current file content:
{current_content}

Recent transcript tail (last 3000 chars):
{transcript_tail}

Issue signal:
{issue_signal}

Instructions:
- Preserve the exact markdown structure and heading hierarchy
- Do not change the skill/agent name or type
- Improve trigger conditions, workflow steps, or guardrails based on the issue
- Return ONLY the improved file content, starting with the # header"""


class ImprovementValidationError(Exception):
    """Raised when LLM improvement output fails validation."""


def generate_improvement(
    target: ImprovementTarget,
    transcript_tail: str,
    issue_signal: dict,
    *,
    client=None,  # injectable for testing
) -> str:
    """Call Claude API to generate improved skill/agent content."""
    current_content = Path(target.file_path).read_text(encoding="utf-8")
    prompt = _IMPROVEMENT_PROMPT_TEMPLATE.format(
        current_content=current_content,
        transcript_tail=transcript_tail[-3000:],
        issue_signal=json.dumps(issue_signal, indent=2),
    )
    if client is None:
        import anthropic as _anthropic
        client = _anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def write_improvement(
    target: ImprovementTarget,
    content: str,
    project_root=None,
) -> None:
    """Validate, backup, and write improved content to target file."""
    original = Path(target.file_path).read_text(encoding="utf-8")
    original_len = len(original)

    if not content:
        raise ImprovementValidationError("LLM output is empty")
    if not content.lstrip().startswith("#"):
        raise ImprovementValidationError("LLM output does not start with a # header")
    if len(content) < original_len * 0.5:
        raise ImprovementValidationError(
            f"LLM output too short: {len(content)} < {original_len * 0.5:.0f} (50% of original)"
        )
    if len(content) > original_len * 5.0:
        raise ImprovementValidationError(
            f"LLM output too long: {len(content)} > {original_len * 5.0:.0f} (500% of original)"
        )

    from mpga.commands.hook import backup_file
    backup_file(target.file_path, target.skill_or_agent_name, project_root=project_root)
    Path(target.file_path).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Async improvement worker (T012)
# ---------------------------------------------------------------------------


def _resolve_target(
    session_id: str,
    envelope: dict,
    project_root: Path,
) -> ImprovementTarget | None:
    """Identify which skill or agent to improve.

    Resolution order:
      1. .mpga/session/<session_id>/active_skill.json (written by capture-user-prompt)
      2. Regex scan of transcript for /mpga-<name> or /mpga:<name> patterns
      3. Return None — caller must log + skip

    NEVER guesses: if identification fails, returns None.
    """
    tracker = project_root / ".mpga" / "session" / session_id / "active_skill.json"
    if tracker.exists():
        try:
            data = json.loads(tracker.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if data.get("skill"):
            name = data["skill"]
            fp = project_root / ".claude" / "skills" / name / "SKILL.md"
            return ImprovementTarget(name, str(fp), "skill")
        if data.get("agent"):
            name = data["agent"]
            fp = project_root / ".claude" / "agents" / f"{name}.md"
            return ImprovementTarget(name, str(fp), "agent")

    # Fallback: scan transcript for a slash-command pattern
    transcript_path = envelope.get("transcript_path")
    if transcript_path and Path(transcript_path).exists():
        try:
            transcript = Path(transcript_path).read_text(errors="replace")
            m = re.search(r'/mpga[:\-](\w[\w\-]*)', transcript)
            if m:
                name = "mpga-" + m.group(1)  # reconstruct: mpga:develop -> mpga-develop
                fp = project_root / ".claude" / "skills" / name / "SKILL.md"
                return ImprovementTarget(name, str(fp), "skill")
        except OSError:
            pass

    return None


def process_improvement_queue(
    conn: _sqlite3.Connection,
    project_root: Path,
    *,
    client=None,
) -> int:
    """Dequeue unprocessed post-stop improvement items and process each one.

    For each item the worker:
      1. Parses tool_input (JSON hook envelope).
      2. Resolves the target skill/agent via tracker file or transcript regex.
      3. If no target or file missing: logs improvement_skipped, marks processed.
      4. Reads transcript tail (last 3000 chars), calls generate_improvement(),
         then write_improvement().
      5. Logs improvement_applied on success, improvement_failed on
         ImprovementValidationError; marks processed either way.

    Returns the count of items processed.
    """
    from mpga.db.repos.observations import ObservationRepo, Observation

    rows = conn.execute(
        "SELECT id, session_id, tool_input FROM observation_queue"
        " WHERE tool_name='post-stop' AND processed=0"
    ).fetchall()

    obs_repo = ObservationRepo(conn)
    processed_count = 0

    for item_id, session_id, tool_input_raw in rows:
        try:
            envelope = json.loads(tool_input_raw or "{}")
        except json.JSONDecodeError:
            envelope = {}

        target = _resolve_target(session_id or "", envelope, project_root)

        if target is None:
            obs_repo.create(Observation(
                session_id=session_id,
                title=f"improvement_skipped: no target for session {session_id}",
                type="improvement_skipped",
                tool_name="improvement-worker",
                narrative="Could not identify skill or agent from tracker or transcript.",
            ))
            conn.execute("UPDATE observation_queue SET processed=1 WHERE id=?", (item_id,))
            conn.commit()
            processed_count += 1
            continue

        if not Path(target.file_path).exists():
            obs_repo.create(Observation(
                session_id=session_id,
                title=f"improvement_skipped: {target.skill_or_agent_name} — file not found",
                type="improvement_skipped",
                tool_name="improvement-worker",
                narrative=f"Resolved path does not exist: {target.file_path}",
            ))
            conn.execute("UPDATE observation_queue SET processed=1 WHERE id=?", (item_id,))
            conn.commit()
            processed_count += 1
            continue

        transcript_path = envelope.get("transcript_path")
        transcript_tail = ""
        if transcript_path and Path(transcript_path).exists():
            try:
                transcript_tail = Path(transcript_path).read_text(errors="replace")[-3000:]
            except OSError:
                transcript_tail = ""

        issue_signal: dict = {
            "hook_event_name": envelope.get("hook_event_name"),
            "error": envelope.get("error"),
            "stop_reason": envelope.get("reason"),
        }

        try:
            content = generate_improvement(target, transcript_tail, issue_signal, client=client)
            write_improvement(target, content, project_root=project_root)
            obs_repo.create(Observation(
                session_id=session_id,
                title=f"improvement_applied: {target.skill_or_agent_name}",
                type="improvement_applied",
                tool_name="improvement-worker",
                narrative=f"Applied improvement to {target.skill_or_agent_name}; new length={len(content)} chars",
            ))
        except ImprovementValidationError as exc:
            obs_repo.create(Observation(
                session_id=session_id,
                title=f"improvement_failed: {target.skill_or_agent_name}",
                type="improvement_failed",
                tool_name="improvement-worker",
                narrative=f"Validation error: {exc}",
            ))

        conn.execute("UPDATE observation_queue SET processed=1 WHERE id=?", (item_id,))
        conn.commit()
        processed_count += 1

    return processed_count
