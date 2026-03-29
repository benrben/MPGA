"""Tests for the preview command."""

from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from click.testing import CliRunner
import pytest


def _seed_project(root: Path, milestone: str = "M007-ui-ux-design-layer") -> Path:
    mpga_dir = root / "MPGA"
    prototypes_dir = mpga_dir / "milestones" / milestone / "design" / "prototypes"
    prototypes_dir.mkdir(parents=True, exist_ok=True)
    (mpga_dir / "mpga.config.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    (mpga_dir / "INDEX.md").write_text(
        "# Project: demo\n\n## Active milestone\n- M007-ui-ux-design-layer\n",
        encoding="utf-8",
    )
    (prototypes_dir / "index.html").write_text(
        "<!doctype html><title>Prototype</title><main>Prototype</main>\n",
        encoding="utf-8",
    )
    return prototypes_dir


class TestPreviewServer:
    """preview server tests."""

    def test_serves_index_html_from_prototypes_directory(self, tmp_path: Path):
        """Serves GET / from the milestone prototypes directory."""
        prototypes_dir = _seed_project(tmp_path)

        from mpga.commands.preview import create_preview_server

        server = create_preview_server(str(prototypes_dir), host="127.0.0.1", port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_address[1]}/",
                timeout=5,
            ) as response:
                assert response.status == 200
                assert "Prototype" in response.read().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_rejects_non_localhost_host(self, tmp_path: Path, monkeypatch):
        """Rejects non-localhost preview binding."""
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.preview.find_project_root", lambda: tmp_path)

        from mpga.commands.preview import preview_cmd

        runner = CliRunner()
        result = runner.invoke(preview_cmd, ["--host", "0.0.0.0"])

        assert result.exit_code != 0
        assert "localhost" in result.output or "127.0.0.1" in result.output

    def test_rejects_parent_directory_escape(self, tmp_path: Path):
        """Rejects requests that try to escape the preview directory."""
        prototypes_dir = _seed_project(tmp_path)
        secret_path = prototypes_dir.parent / "secret.txt"
        secret_path.write_text("TOPSECRET\n", encoding="utf-8")

        from mpga.commands.preview import create_preview_server

        server = create_preview_server(str(prototypes_dir), host="127.0.0.1", port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with pytest.raises(HTTPError) as exc_info:
                urlopen(
                    f"http://127.0.0.1:{server.server_address[1]}/../secret.txt",
                    timeout=5,
                )
            assert exc_info.value.code == 403
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
