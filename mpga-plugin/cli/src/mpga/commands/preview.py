from __future__ import annotations

import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import re
from urllib.parse import unquote

import click

from mpga.commands.board_live_server import open_board_live_url
from mpga.core.config import find_project_root
from mpga.core.logger import log

_CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}
_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


def _current_milestone(project_root: Path) -> str:
    index_path = project_root / "MPGA" / "INDEX.md"
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        match = re.search(r"## Active milestone\n(?:- )?([^\n]+)", content)
        if match:
            return match.group(1).strip()

    milestones_dir = project_root / "MPGA" / "milestones"
    if milestones_dir.exists():
        names = sorted(path.name for path in milestones_dir.iterdir() if path.is_dir())
        if names:
            return names[-1]

    return "M000-design-sandbox"


class _PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, preview_dir: str, **kwargs):  # type: ignore[no-untyped-def]
        self._preview_dir = preview_dir
        super().__init__(*args, directory=preview_dir, **kwargs)

    def do_GET(self) -> None:
        self.server.last_activity = time.monotonic()  # type: ignore[attr-defined]

        resolved = self._resolve_request_path()
        if resolved is None:
            self.send_error(403, "Forbidden")
            return

        target = Path(resolved)
        if not target.exists() or target.is_dir():
            self.send_error(404, "Not found")
            return

        try:
            data = target.read_bytes()
        except OSError:
            self.send_error(500, "Internal Server Error")
            return

        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _resolve_request_path(self) -> str | None:
        raw_path = unquote(self.path or "/")
        pathname = raw_path.split("?")[0].split("#")[0]
        relative = "index.html" if pathname == "/" else pathname.lstrip("/")
        preview_root = Path(self._preview_dir).resolve()
        resolved = (preview_root / relative).resolve()
        try:
            resolved.relative_to(preview_root)
        except ValueError:
            return None
        return str(resolved)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def create_preview_server(
    preview_dir: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8420,
) -> HTTPServer:
    handler = partial(_PreviewHandler, preview_dir=preview_dir)
    server = HTTPServer((host, port), handler)  # type: ignore[arg-type]
    server.last_activity = time.monotonic()  # type: ignore[attr-defined]
    return server


@click.command("preview", help="Serve the active milestone HTML prototype on localhost")
@click.option("--port", type=int, default=8420, show_default=True)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--open", "open_browser", is_flag=True, default=False)
def preview_cmd(port: int, host: str, open_browser: bool) -> None:
    if host not in _ALLOWED_HOSTS:
        raise click.ClickException("Preview server only allows localhost bindings (127.0.0.1 or localhost).")

    project_root = find_project_root() or Path.cwd()
    milestone = _current_milestone(project_root)
    preview_dir = project_root / "MPGA" / "milestones" / milestone / "design" / "prototypes"
    preview_dir.mkdir(parents=True, exist_ok=True)

    index_path = preview_dir / "index.html"
    if not index_path.exists():
        index_path.write_text(
            "<!doctype html><title>Preview</title><main>No prototype generated yet.</main>\n",
            encoding="utf-8",
        )

    server = create_preview_server(str(preview_dir), host=host, port=port)
    server.timeout = 1  # type: ignore[attr-defined]
    effective_host, effective_port = server.server_address
    url = f"http://{effective_host}:{effective_port}"

    log.success(f"Serving previews from {preview_dir}")
    log.success(f"Preview available at {url}")
    log.dim("Auto-shutdown after 30 minutes of inactivity.")
    if open_browser:
        open_board_live_url(url)

    inactivity_timeout = 30 * 60
    try:
        while True:
            server.handle_request()
            last_activity = getattr(server, "last_activity", time.monotonic())
            if time.monotonic() - last_activity > inactivity_timeout:
                log.warn("Preview server stopped after 30 minutes of inactivity.")
                break
    except KeyboardInterrupt:
        log.warn("Preview server stopped.")
    finally:
        server.server_close()
