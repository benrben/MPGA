"""T028: Test that the DFS for board deps correctly handles diamond deps and cycles.

Bug: visited.discard() is called after visiting each node, which:
1. Causes diamond dependencies to print multiple times (D appears twice in A→B→D + A→C→D)
2. Causes cycles to not be detected (visited set never prevents re-entry, leading to infinite recursion)

Fix: Remove visited.discard(). Use a persistent visited set for deduplication,
and a separate in_progress set for cycle detection.
"""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def _make_task(id_: str, title: str, column: str = "backlog", depends_on: list[str] | None = None) -> object:
    """Create a minimal Task-like object."""
    from mpga.board.task import Task
    from datetime import UTC, datetime

    return Task(
        id=id_,
        title=title,
        column=column,
        priority="medium",
        status=None,
        depends_on=depends_on or [],
        created=datetime.now(UTC).isoformat(),
        updated=datetime.now(UTC).isoformat(),
    )


class TestBoardDepsDFS:

    def _run_deps(self, task_id: str, tasks: list) -> str:
        """Run handle_board_deps and capture console output."""
        from mpga.commands import board_handlers

        output_lines: list[str] = []

        def fake_print(msg="", **kwargs):
            output_lines.append(str(msg))

        project_root = Path("/tmp/fake")
        board_dir = "/tmp/fake/MPGA/board"
        tasks_dir = "/tmp/fake/MPGA/board/tasks"

        with (
            patch.object(board_handlers, "_board_context", return_value=(project_root, board_dir, tasks_dir)),
            patch.object(board_handlers, "_load_board_tasks", return_value=tasks),
            patch.object(board_handlers.console, "print", side_effect=fake_print),
            patch.object(board_handlers.log, "header"),
            patch.object(board_handlers.log, "dim"),
        ):
            board_handlers.handle_board_deps(task_id)

        return "\n".join(output_lines)

    def test_diamond_dependency_prints_leaf_only_once(self):
        """Diamond: A→B, A→C, B→D, C→D — D should appear exactly once in output."""
        tasks = [
            _make_task("A", "Task A", depends_on=["B", "C"]),
            _make_task("B", "Task B", depends_on=["D"]),
            _make_task("C", "Task C", depends_on=["D"]),
            _make_task("D", "Task D", depends_on=[]),
        ]

        output = self._run_deps("A", tasks)

        # Count how many times D appears in the deps tree output
        d_count = output.count("D: Task D")
        assert d_count == 1, (
            f"Task D should appear exactly once in diamond dependency output, "
            f"but appeared {d_count} times:\n{output}"
        )

    def test_cycle_does_not_infinite_loop(self):
        """Cycle: A→B→A — must terminate and print a cycle marker, not infinite loop."""
        tasks = [
            _make_task("A", "Task A", depends_on=["B"]),
            _make_task("B", "Task B", depends_on=["A"]),
        ]

        # If this does not raise RecursionError / timeout, the cycle is handled
        import signal

        def _timeout_handler(signum, frame):
            raise TimeoutError("DFS did not terminate — likely infinite recursion in cycle")

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(5)  # 5-second timeout

        try:
            output = self._run_deps("A", tasks)
        finally:
            signal.alarm(0)

        # Output must contain a cycle indicator for one of the nodes
        assert "circular" in output.lower() or "cycle" in output.lower(), (
            f"Expected cycle detection marker in output, got:\n{output}"
        )

    def test_linear_chain_prints_all_nodes_once(self):
        """Linear: A→B→C — all three nodes should appear exactly once."""
        tasks = [
            _make_task("A", "Task A", depends_on=["B"]),
            _make_task("B", "Task B", depends_on=["C"]),
            _make_task("C", "Task C", depends_on=[]),
        ]

        output = self._run_deps("A", tasks)

        assert output.count("A: Task A") == 1
        assert output.count("B: Task B") == 1
        assert output.count("C: Task C") == 1
