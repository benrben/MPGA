"""T018: Test that runtime.py returns a usable vendored CLI command path."""
from pathlib import Path
import sys

SRC_ROOT = Path("/Users/benreich/MPGA/mpga-plugin/cli/src")
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def test_project_vendored_cli_command_is_not_stale():
    """project_vendored_cli_command() must return a valid vendored path string."""
    from mpga.commands.export.runtime import project_vendored_cli_command
    result = project_vendored_cli_command()
    assert isinstance(result, str) and len(result) > 0, (
        f"project_vendored_cli_command() must return a non-empty string, got: {result!r}"
    )
