"""Minimal HTTP server for the MPGA live board, plus a cross-platform browser opener."""

from __future__ import annotations

import os
import platform
import subprocess
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional

CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class _BoardLiveHandler(SimpleHTTPRequestHandler):
    """Serves files from a fixed *live_dir* with no-store caching."""

    def __init__(self, *args, live_dir: str, **kwargs):  # type: ignore[no-untyped-def]
        self._live_dir = live_dir
        super().__init__(*args, directory=live_dir, **kwargs)

    # --- request handling ---------------------------------------------------

    def do_GET(self) -> None:
        resolved = self._resolve_request_path()
        if resolved is None:
            self.send_error(403, "Forbidden")
            return

        p = Path(resolved)
        if not p.exists() or p.is_dir():
            self.send_error(404, "Not found")
            return

        content_type = CONTENT_TYPES.get(p.suffix, "application/octet-stream")
        try:
            data = p.read_bytes()
        except Exception:
            self.send_error(500, "Internal Server Error")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --- path resolution (mirrors the TS resolveRequestPath) ----------------

    def _resolve_request_path(self) -> Optional[str]:
        raw_path = self.path or "/"
        # Strip query string
        pathname = raw_path.split("?")[0].split("#")[0]
        relative = "index.html" if pathname == "/" else pathname.lstrip("/")
        resolved = Path(self._live_dir).resolve() / relative
        live_root = str(Path(self._live_dir).resolve()) + os.sep
        index_path = str((Path(self._live_dir).resolve() / "index.html"))
        if str(resolved).startswith(live_root) or str(resolved) == index_path:
            return str(resolved)
        return None

    # Suppress default logging
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def create_board_live_server(live_dir: str, port: int = 4173) -> HTTPServer:
    """Return an HTTPServer that serves *live_dir* on 127.0.0.1:*port*."""
    handler = partial(_BoardLiveHandler, live_dir=live_dir)
    return HTTPServer(("127.0.0.1", port), handler)  # type: ignore[arg-type]


def open_board_live_url(url: str) -> None:
    """Open *url* in the default browser (fire-and-forget)."""
    system = platform.system()
    if system == "Darwin":
        command = ["open", url]
    elif system == "Windows":
        command = ["cmd", "/c", "start", "", url]
    else:
        command = ["xdg-open", url]

    child = subprocess.Popen(
        command,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Detach so the child doesn't block the parent
    child.communicate = lambda *_a, **_k: (b"", b"")  # type: ignore[assignment]
