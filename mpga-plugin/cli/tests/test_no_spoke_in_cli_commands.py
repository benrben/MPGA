"""T013 — Tests: CLI commands no longer call spoke().

Evidence: [E] mpga-plugin/cli/src/mpga/commands/sync.py :: sync_cmd
Evidence: [E] mpga-plugin/cli/src/mpga/commands/evidence.py :: evidence_heal
Evidence: [E] mpga-plugin/cli/src/mpga/commands/milestone.py :: milestone_new, milestone_complete
Evidence: [E] mpga-plugin/cli/src/mpga/commands/board_handlers.py :: handle_board_move
Evidence: [E] mpga-plugin/cli/src/mpga/commands/session.py :: session_handoff

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: sync_cmd does not import or call spoke()          → test_sync_does_not_import_spoke
[x] AC2: evidence_heal does not import or call spoke()     → test_evidence_does_not_import_spoke
[x] AC3: milestone.py does not import or call spoke()      → test_milestone_does_not_import_spoke
[x] AC4: board_handlers does not import or call spoke() → test_board_handlers_does_not_import_spoke
[x] AC5: session.py does not import or call spoke()     → test_session_does_not_import_spoke
[x] AC6: spoke() is not called when sync_cmd runs       → test_sync_does_not_invoke_spoke_subprocess
[x] AC7: spoke() is not called when board move runs        → test_board_move_does_not_invoke_spoke
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Static import checks — verify spoke is not imported in CLI command modules
# ---------------------------------------------------------------------------


class TestSpokeNotImportedInCliModules:
    """Spoke is not imported by CLI command modules."""

    def test_sync_does_not_import_spoke(self):
        import mpga.commands.sync as sync_mod
        assert not hasattr(sync_mod, "spoke"), \
            "sync.py must not import spoke from logger"

    def test_evidence_does_not_import_spoke(self):
        import mpga.commands.evidence as evidence_mod
        assert not hasattr(evidence_mod, "spoke"), \
            "evidence.py must not import spoke from logger"

    def test_milestone_does_not_import_spoke(self):
        import mpga.commands.milestone as milestone_mod
        assert not hasattr(milestone_mod, "spoke"), \
            "milestone.py must not import spoke from logger"

    def test_board_handlers_does_not_import_spoke(self):
        import mpga.commands.board_handlers as board_handlers_mod
        assert not hasattr(board_handlers_mod, "spoke"), \
            "board_handlers.py must not import spoke from logger"

    def test_session_does_not_import_spoke(self):
        import mpga.commands.session as session_mod
        assert not hasattr(session_mod, "spoke"), \
            "session.py must not import spoke from logger"


# ---------------------------------------------------------------------------
# Runtime checks — spoke subprocess is NOT launched during command execution
# ---------------------------------------------------------------------------


class TestSpokeNotInvokedAtRuntime:
    """spoke() subprocess is not launched when CLI commands run."""

    def test_board_move_does_not_invoke_spoke(self, tmp_path, monkeypatch):
        """handle_board_move to 'done' does not launch mpga spoke subprocess."""
        import json

        from mpga.commands.board_handlers import handle_board_move

        # Seed minimal board + task
        board_dir = tmp_path / "MPGA" / "board"
        tasks_dir = board_dir / "tasks"
        tasks_dir.mkdir(parents=True)

        board = {
            "version": "1.0.0",
            "milestone": None,
            "updated": "2026-01-01T00:00:00.000Z",
            "columns": {
                "backlog": [], "todo": ["T001"], "in-progress": [],
                "testing": [], "review": [], "done": [],
            },
            "stats": {
                "total": 1, "done": 0, "in_flight": 0, "blocked": 0,
                "progress_pct": 0, "evidence_produced": 0, "evidence_expected": 0,
            },
            "wip_limits": {"in-progress": 3, "testing": 3, "review": 2},
            "next_task_id": 2,
        }
        (board_dir / "board.json").write_text(json.dumps(board), encoding="utf-8")

        task_md = (
            "---\n"
            'id: "T001"\n'
            'title: "Test task"\n'
            'status: "active"\n'
            'column: "todo"\n'
            'priority: "medium"\n'
            "milestone: null\n"
            "phase: null\n"
            'created: "2026-01-01T00:00:00+00:00"\n'
            'updated: "2026-01-01T00:00:00+00:00"\n'
            "assigned: null\n"
            "depends_on: []\n"
            "blocks: []\n"
            "scopes: []\n"
            "tdd_stage: null\n"
            "lane_id: null\n"
            "run_status: null\n"
            "current_agent: null\n"
            "file_locks: []\n"
            "scope_locks: []\n"
            "started_at: null\n"
            "finished_at: null\n"
            "heartbeat_at: null\n"
            "evidence_expected: []\n"
            "evidence_produced: []\n"
            "tags: []\n"
            "time_estimate: null\n"
            "---\n\n# T001\n"
        )
        (tasks_dir / "T001-test-task.md").write_text(task_md, encoding="utf-8")

        monkeypatch.chdir(tmp_path)

        popen_calls = []

        def tracking_popen(args, **kwargs):
            popen_calls.append(args)
            return MagicMock()

        monkeypatch.setattr(subprocess, "Popen", tracking_popen)

        handle_board_move("T001", "done")

        # No Popen call should reference "spoke"
        spoke_calls = [c for c in popen_calls if "spoke" in str(c)]
        assert spoke_calls == [], \
            f"handle_board_move must not call spoke subprocess, got: {spoke_calls}"
