"""T062: Test that ctx doctor outputs a fix command when export rules are missing."""
import sys
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

SRC_ROOT = Path("/Users/benreich/MPGA/mpga-plugin/cli/src")
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from mpga.commands.ctx import ctx


def test_doctor_shows_fix_command_when_exports_missing(tmp_path):
    """ctx doctor must print a fix command when Cursor/Codex/Antigravity exports are missing."""
    runner = CliRunner()

    with patch("mpga.commands.ctx._project_root", return_value=tmp_path), \
         patch("mpga.commands.ctx._conn") as mock_conn:
        # Mock DB connection to avoid DB setup
        mock_sqlite_conn = mock_conn.return_value.__enter__.return_value
        mock_conn.return_value.execute.return_value.fetchall.return_value = [
            ("ctx_artifacts",), ("ctx_events",), ("ctx_artifacts_fts",)
        ]
        mock_conn.return_value.close.return_value = None

        # tmp_path has no .cursor/rules/mpga-routing.mdc etc — so rules are missing
        result = runner.invoke(ctx, ["doctor"])

    output = result.output

    # The fix command must appear when exports are missing
    assert "mpga export" in output, (
        f"ctx doctor must print a fix command like 'mpga export --cursor --codex --antigravity' "
        f"when export rules are missing. Got:\n{output}"
    )
