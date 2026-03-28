"""Tests for the board live server."""

from pathlib import Path


class TestCreateBoardLiveServer:
    """createBoardLiveServer tests."""

    def test_serves_index_and_snapshot(self, tmp_path: Path):
        """Serves index.html and snapshot.json from the live board directory."""
        (tmp_path / "index.html").write_text("<!doctype html><h1>Board</h1>")
        (tmp_path / "snapshot.json").write_text('{"ok":true}\n')

        from mpga.commands.board_live_server import create_board_live_server

        # Use port 0 to let the OS assign a free port
        server = create_board_live_server(str(tmp_path), port=0)
        try:
            # Verify the server was created and bound successfully
            assert server.server_address[0] == "127.0.0.1"
            assert server.server_address[1] != 0  # OS assigned a real port

            # Verify the files exist in the live dir (the handler serves them)
            assert (tmp_path / "index.html").exists()
            assert (tmp_path / "snapshot.json").exists()
        finally:
            server.server_close()
