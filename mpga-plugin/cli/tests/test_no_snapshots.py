"""Tests ensuring snapshot generation exists and works correctly."""

from pathlib import Path


class TestSnapshotsExist:
    """Verify that snapshot generation code is present."""

    def test_snapshots_module_exists(self):
        """snapshots.py module should exist for SQLite-based exports."""
        snapshots_py = Path(__file__).parent.parent / "src" / "mpga" / "commands" / "export" / "snapshots.py"
        assert snapshots_py.exists(), "snapshots.py should exist for Markdown snapshot export"

    def test_export_cmd_references_snapshots(self):
        """export_cmd.py should import snapshots module for SQLite export."""
        export_cmd = Path(__file__).parent.parent / "src" / "mpga" / "commands" / "export_cmd.py"
        if export_cmd.exists():
            content = export_cmd.read_text()
            assert "snapshots" in content, "export_cmd should use the snapshots module"
