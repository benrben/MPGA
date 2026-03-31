"""Tests for T007 — Add UserPromptSubmit hook for decisions/intents.

Coverage checklist for: T007 — UserPromptSubmit hook
                                                         
Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: hooks.json has UserPromptSubmit section         → test_hooks_json_has_user_prompt_submit
[x] AC2: UserPromptSubmit routes to capture-user-prompt  → test_hooks_json_user_prompt_routes_to_command
[x] AC3: capture-user-prompt Click command exists        → test_capture_user_prompt_command_exists
[x] AC4: extracts decision intent from user text         → test_captures_decision_intent
[x] AC5: extracts role/intent from slash commands        → test_captures_role_assignment
[x] AC6: extracts intent from questions                  → test_captures_intent_from_question
[x] AC7: returns in <50ms                               → test_returns_quickly
[x] AC8: existing hook sections unchanged                → test_preserves_existing_hooks

Untested branches / edge cases:
- [ ] empty user text (degenerate)
- [ ] very long user text (truncation)
- [ ] unicode in user prompt
- [ ] concurrent writes
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

# Evidence: [E] mpga-plugin/hooks/hooks.json :: full hooks structure (lines 1-73)
HOOKS_JSON = Path(__file__).resolve().parents[2] / "hooks" / "hooks.json"

# Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py :: hook Click group (line 139)
from mpga.commands.hook import hook


def _load_hooks() -> dict:
    return json.loads(HOOKS_JSON.read_text(encoding="utf-8"))


class TestHooksJsonUserPromptSubmit:
    """hooks.json must have a UserPromptSubmit section routing to capture-user-prompt."""

    # --- TPP step 1: degenerate — does the section exist at all? ---

    def test_hooks_json_has_user_prompt_submit(self) -> None:
        """hooks.json must contain a UserPromptSubmit key."""
        hooks = _load_hooks()
        assert "UserPromptSubmit" in hooks["hooks"], (
            f"No 'UserPromptSubmit' in hooks. Found sections: {list(hooks['hooks'].keys())}"
        )

    # --- TPP step 2: constant — verify exact routing ---

    def test_hooks_json_user_prompt_routes_to_command(self) -> None:
        """UserPromptSubmit must route to 'hook capture-user-prompt'."""
        hooks = _load_hooks()
        ups_entries = hooks["hooks"]["UserPromptSubmit"]
        all_commands = [
            h["command"]
            for entry in ups_entries
            for h in entry["hooks"]
        ]
        assert any("capture-user-prompt" in cmd for cmd in all_commands), (
            f"UserPromptSubmit hooks don't reference capture-user-prompt. "
            f"Commands: {all_commands}"
        )

    # --- TPP step 3: selection — existing sections preserved (characterization) ---

    def test_preserves_existing_hooks(self) -> None:
        """Adding UserPromptSubmit must not remove PreToolUse, PostToolUse, SessionStart, or PreCompact."""
        hooks = _load_hooks()
        sections = list(hooks["hooks"].keys())
        for required in ("PreToolUse", "PostToolUse", "SessionStart", "PreCompact"):
            assert required in sections, (
                f"'{required}' section missing after adding UserPromptSubmit. Found: {sections}"
            )


class TestCaptureUserPromptCommand:
    """The capture-user-prompt Click command must exist and extract decisions/intents."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py :: hook group (line 139)
    # Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:12-28 :: Observation dataclass

    # --- TPP step 1: degenerate — command must exist ---

    def test_capture_user_prompt_command_exists(self) -> None:
        """The hook group must have a 'capture-user-prompt' subcommand."""
        command_names = list(hook.commands)
        assert "capture-user-prompt" in command_names, (
            f"'capture-user-prompt' not in hook commands. Found: {command_names}"
        )

    # --- TPP step 2: constant → variable — decision extraction ---

    def test_captures_decision_intent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """User text containing a decision creates a decision-type observation."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "user_message": "I decided to use Redis for caching",
        })

        runner = CliRunner()
        result = runner.invoke(
            hook, ["capture-user-prompt"], input=stdin_payload,
        )
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        row = conn.execute(
            "SELECT type, title FROM observations ORDER BY id DESC LIMIT 1",
        ).fetchone()
        conn.close()
        assert row is not None, "No observation created for decision text"
        assert row[0] == "decision", (
            f"Expected observation type 'decision', got '{row[0]}'"
        )

    # --- TPP step 3: unconditional → selection — role/intent from slash commands ---

    def test_captures_role_assignment(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Slash-command text like '/mpga:develop T001' creates an intent-type observation."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "user_message": "/mpga:develop T001",
        })

        runner = CliRunner()
        result = runner.invoke(
            hook, ["capture-user-prompt"], input=stdin_payload,
        )
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        row = conn.execute(
            "SELECT type, title FROM observations ORDER BY id DESC LIMIT 1",
        ).fetchone()
        conn.close()
        assert row is not None, "No observation created for slash-command text"
        assert row[0] == "intent", (
            f"Expected observation type 'intent', got '{row[0]}'"
        )

    # --- TPP step 4: another selection branch — intent from questions ---

    def test_captures_intent_from_question(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Interrogative user text creates an intent-type observation."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "user_message": "How does the auth module work?",
        })

        runner = CliRunner()
        result = runner.invoke(
            hook, ["capture-user-prompt"], input=stdin_payload,
        )
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        row = conn.execute(
            "SELECT type, title FROM observations ORDER BY id DESC LIMIT 1",
        ).fetchone()
        conn.close()
        assert row is not None, "No observation created for question text"
        assert row[0] == "intent", (
            f"Expected observation type 'intent', got '{row[0]}'"
        )

    # --- TPP step 5: boundary — timing constraint ---

    def test_returns_quickly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """capture-user-prompt must complete in under 50ms."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "user_message": "I want to refactor the database layer",
        })

        runner = CliRunner()
        start = time.perf_counter()
        result = runner.invoke(
            hook, ["capture-user-prompt"], input=stdin_payload,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result.exit_code == 0
        assert elapsed_ms < 50, (
            f"capture-user-prompt took {elapsed_ms:.1f}ms, exceeds 50ms budget"
        )

    # --- helpers ---

    @staticmethod
    def _setup_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        db_path = tmp_path / ".mpga" / "mpga.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_connection(str(db_path))
        create_schema(conn)
        conn.close()
        monkeypatch.setattr(
            "mpga.commands.hook._project_root", lambda: tmp_path,
        )

    @staticmethod
    def _get_conn(tmp_path: Path):
        import sqlite3
        return sqlite3.connect(str(tmp_path / ".mpga" / "mpga.db"))
