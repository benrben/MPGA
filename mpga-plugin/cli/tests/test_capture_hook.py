"""Tests for T006 — Add PostToolUse * capture hook.

Coverage checklist for: T006 — PostToolUse * capture hook

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: hooks.json has PostToolUse * matcher     → test_hooks_json_has_posttooluse_star
[x] AC2: Existing PostToolUse entries unchanged    → test_hooks_json_preserves_existing_posttooluse
[x] AC3: * routes to capture-observation           → test_hooks_json_star_routes_to_capture_observation
[x] AC4: capture-observation Click command exists   → test_capture_observation_command_exists
[x] AC5: writes to observation_queue               → test_capture_observation_writes_to_queue
[x] AC6: skip list for low-value tools             → test_capture_observation_skips_configured_tools
[x] AC7: reads stdin JSON                          → test_capture_observation_reads_stdin_json
[x] AC8: existing post-bash still works            → test_existing_post_bash_still_works

Untested branches / edge cases:
- [ ] malformed JSON on stdin (graceful error handling)
- [ ] empty stdin
- [ ] concurrent queue writes
- [ ] skip list configured via env var
- [ ] <100ms timing constraint (integration-level)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

# Evidence: [E] mpga-plugin/hooks/hooks.json :: PostToolUse section (lines 23-42)
HOOKS_JSON = Path(__file__).resolve().parents[2] / "hooks" / "hooks.json"

# Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py :: hook Click group (line 139)
from mpga.commands.hook import hook


def _load_hooks() -> dict:
    return json.loads(HOOKS_JSON.read_text(encoding="utf-8"))


class TestHooksJsonPostToolUseStar:
    """hooks.json must have a PostToolUse * matcher routing to capture-observation."""

    # --- TPP step 1: degenerate — does the * entry exist at all? ---

    def test_hooks_json_has_posttooluse_star(self) -> None:
        """PostToolUse section must contain an entry with matcher '*'."""
        hooks = _load_hooks()
        post_entries = hooks["hooks"]["PostToolUse"]
        matchers = [e["matcher"] for e in post_entries]
        assert "*" in matchers, (
            f"No '*' matcher in PostToolUse. Found: {matchers}"
        )

    # --- TPP step 2: constant — verify exact routing ---

    def test_hooks_json_star_routes_to_capture_observation(self) -> None:
        """The * matcher must route to 'hook capture-observation'."""
        hooks = _load_hooks()
        post_entries = hooks["hooks"]["PostToolUse"]
        star_entry = next(
            (e for e in post_entries if e.get("matcher") == "*"), None,
        )
        assert star_entry is not None, "No '*' matcher found in PostToolUse"
        commands = [h["command"] for h in star_entry["hooks"]]
        assert any("capture-observation" in cmd for cmd in commands), (
            f"* matcher hooks don't reference capture-observation. Commands: {commands}"
        )

    # --- TPP step 3: selection — existing entries preserved (characterization) ---

    def test_hooks_json_preserves_existing_posttooluse(self) -> None:
        """Existing Bash and Write|Edit PostToolUse matchers must still be present."""
        hooks = _load_hooks()
        post_entries = hooks["hooks"]["PostToolUse"]
        matchers = [e["matcher"] for e in post_entries]
        assert "Bash" in matchers, (
            f"Bash matcher missing from PostToolUse. Found: {matchers}"
        )
        assert "Write|Edit" in matchers, (
            f"Write|Edit matcher missing from PostToolUse. Found: {matchers}"
        )

    def test_existing_post_bash_still_works(self) -> None:
        """The existing post-bash hook command must still function for non-mpga commands."""
        runner = CliRunner()
        result = runner.invoke(hook, ["post-bash", "echo hello", "hello"])
        assert result.exit_code == 0


class TestCaptureObservationCommand:
    """The capture-observation Click command must exist and process stdin."""

    # Evidence: [E] mpga-plugin/cli/src/mpga/commands/hook.py :: hook group (command not yet created)
    # Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:137-149 :: ObservationRepo.enqueue

    # --- TPP step 1: degenerate — command must exist ---

    def test_capture_observation_command_exists(self) -> None:
        """The hook group must have a 'capture-observation' subcommand."""
        command_names = list(hook.commands)
        assert "capture-observation" in command_names, (
            f"'capture-observation' not in hook commands. Found: {command_names}"
        )

    # --- TPP step 2: constant → variable — reads stdin JSON ---

    def test_capture_observation_reads_stdin_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Passing JSON on stdin is parsed; tool_name is extracted into queue item."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "tool_name": "Read",
            "tool_input": {"path": "/src/main.py"},
            "tool_output": "file contents here",
        })

        runner = CliRunner()
        result = runner.invoke(
            hook, ["capture-observation"], input=stdin_payload,
        )
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        row = conn.execute(
            "SELECT tool_name FROM observation_queue WHERE processed = 0",
        ).fetchone()
        conn.close()
        assert row is not None, "No queue item found after capture-observation"
        assert row[0] == "Read"

    # --- TPP step 3: unconditional → selection — writes to queue ---

    def test_capture_observation_writes_to_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """capture-observation with valid stdin writes exactly one entry to observation_queue."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "tool_name": "Grep",
            "tool_input": {"pattern": "TODO"},
            "tool_output": "src/app.py:12: # TODO fix this",
        })

        runner = CliRunner()
        result = runner.invoke(
            hook, ["capture-observation"], input=stdin_payload,
        )
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM observation_queue WHERE processed = 0",
        ).fetchone()[0]
        conn.close()
        assert count == 1, f"Expected 1 queue item, got {count}"

    # --- TPP step 4: selection — skip list filters out low-value tools ---

    def test_capture_observation_skips_configured_tools(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tools in the skip list (e.g., TodoRead) must not be enqueued."""
        self._setup_db(tmp_path, monkeypatch)

        stdin_payload = json.dumps({
            "tool_name": "TodoRead",
            "tool_input": {},
            "tool_output": "some todos",
        })

        runner = CliRunner()
        result = runner.invoke(
            hook, ["capture-observation"], input=stdin_payload,
        )
        assert result.exit_code == 0

        conn = self._get_conn(tmp_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM observation_queue",
        ).fetchone()[0]
        conn.close()
        assert count == 0, (
            f"TodoRead should be skipped but {count} items were enqueued"
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
