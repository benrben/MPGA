"""HTTP server: routes /api/* to JSON handlers, /* to static files."""

from __future__ import annotations

import json
import platform
import subprocess
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import click

from mpga.core.config import find_project_root
from mpga.db.connection import get_connection
from mpga.web.router import route
from mpga.web import api as _api

_STATIC_DIR = Path(__file__).parent.parent / "web" / "static"
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class _ApiHandler(SimpleHTTPRequestHandler):
    """Routes /api/* to JSON handlers; serves static files for everything else."""

    def __init__(self, *args, db_path: str, static_dir: str, **kwargs):
        self._db_path = db_path
        self._static_dir = static_dir
        super().__init__(*args, directory=static_dir, **kwargs)

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path.startswith("/api/"):
            self._handle_api(path, query_params, method="GET")
        else:
            self._handle_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            self._send_json({"error": "not found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(payload, dict):
                raise ValueError("payload must be a JSON object")
        except Exception:
            self._send_json({"error": "invalid JSON payload"}, status=400)
            return

        self._handle_api(path, payload, method="POST")

    # ------------------------------------------------------------------
    # API dispatch
    # ------------------------------------------------------------------

    def _handle_api(self, path: str, query_params: dict, method: str = "GET") -> None:
        match = route(path, method, query_params)
        if match is None:
            self._send_json({"error": "not found"}, status=404)
            return

        handler_name, path_params = match
        conn = get_connection(self._db_path)
        try:
            result = self._dispatch(handler_name, conn, query_params, path_params, method=method)
        finally:
            conn.close()

        if result.get("content_type") == "text/event-stream":
            body = result["body"].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Content-Length", str(len(body)))
            self._send_security_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        status = 200 if "error" not in result else 400
        self._send_json(result, status=status)

    def _dispatch(
        self,
        handler_name: str,
        conn,
        query_params: dict,
        path_params: dict,
        method: str = "GET",
    ) -> dict:
        if handler_name == "search":
            return _api.handle_search(conn, query_params)
        if handler_name == "tasks":
            return _api.handle_tasks(conn, query_params)
        if handler_name == "task_detail":
            return _api.handle_task_detail(conn, path_params["task_id"])
        if handler_name == "scopes":
            return _api.handle_scopes(conn, query_params)
        if handler_name == "scope_detail":
            return _api.handle_scope_detail(conn, path_params["scope_id"])
        if handler_name == "scope_tasks":
            return _api.handle_scope_tasks(conn, path_params["scope_id"])
        if handler_name == "task_scope_link":
            if method != "POST":
                return {"error": "method not allowed"}
            return _api.handle_link_task_scope(conn, query_params)
        if handler_name == "task_scope_unlink":
            if method != "POST":
                return {"error": "method not allowed"}
            return _api.handle_unlink_task_scope(conn, query_params)
        if handler_name == "sessions":
            return _api.handle_sessions(conn, query_params)
        if handler_name == "graph":
            return _api.handle_graph(conn, query_params)
        if handler_name == "design_system":
            return _api.handle_design_system(conn, query_params)
        if handler_name == "decisions":
            return _api.handle_decisions(conn, query_params)
        if handler_name == "develop":
            return _api.handle_develop(conn, query_params)
        if handler_name == "evidence":
            return _api.handle_evidence(conn, query_params)
        if handler_name == "board":
            return _api.handle_board(conn)
        if handler_name == "milestones":
            return _api.handle_milestones(conn, query_params)
        if handler_name == "stats":
            return _api.handle_stats(conn)
        if handler_name == "health":
            return _api.handle_health(conn)
        if handler_name == "observations":
            return _api.handle_observations(conn, query_params)
        if handler_name == "observation_detail":
            return _api.handle_observation_detail(conn, path_params["obs_id"])
        if handler_name == "observations_search":
            return _api.handle_observations_search(conn, query_params)
        if handler_name == "observations_timeline":
            return _api.handle_observations_timeline(conn, query_params)
        if handler_name == "stream":
            return _api.handle_stream(conn, query_params)
        return {"error": "unknown handler"}

    # ------------------------------------------------------------------
    # Static file fallback
    # ------------------------------------------------------------------

    def _handle_static(self, path: str) -> None:
        static_root = Path(self._static_dir)
        index = static_root / "index.html"
        if not index.exists():
            self._send_json({"error": "no static files"}, status=404)
            return

        request_path = path or "/"
        if request_path in {"/", ""}:
            self._send_file(index)
            return

        relative = request_path.lstrip("/")
        target = (static_root / relative).resolve()
        try:
            target.relative_to(static_root.resolve())
        except ValueError:
            self._send_json({"error": "forbidden"}, status=403)
            return

        if target.exists() and target.is_file():
            self._send_file(target)
            return

        # SPA fallback: any non-API route without a concrete asset resolves to index.html.
        self._send_file(index)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send_security_headers(self) -> None:
        """Inject security headers into every response."""
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        # Local SPA currently ships inline <style> and <script>, so allow them explicitly.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        )
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self._send_security_headers()
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def _open_url(url: str) -> None:
    system = platform.system()
    if system == "Darwin":
        cmd = ["open", url]
    elif system == "Windows":
        cmd = ["cmd", "/c", "start", "", url]
    else:
        cmd = ["xdg-open", url]
    subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_spa_server(
    *,
    db_path: str,
    static_dir: str,
    host: str = "127.0.0.1",
    port: int = 4173,
) -> HTTPServer:
    handler = partial(_ApiHandler, db_path=db_path, static_dir=static_dir)
    return HTTPServer((host, port), handler)  # type: ignore[arg-type]


@click.command("serve")
@click.option("--port", default=4173, show_default=True, help="Port to listen on")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open in browser after start")
@click.option("--db", default=None, help="Path to MPGA database (defaults to .mpga/mpga.db)")
def serve_cmd(port: int, open_browser: bool, db: str | None) -> None:
    """Start the MPGA API + static file server."""
    if db is None:
        project_root = find_project_root() or Path.cwd()
        db = str(project_root / ".mpga" / "mpga.db")

    static_dir = str(_STATIC_DIR)
    server = create_spa_server(db_path=db, static_dir=static_dir, port=port)

    url = f"http://127.0.0.1:{port}"
    click.echo(f"MPGA server running at {url}")

    if open_browser:
        _open_url(url)

    from mpga.memory.worker import ObservationWorker

    conn = get_connection(db)
    worker = ObservationWorker(conn, session_id="serve", batch_size=50, poll_interval=2.0)
    worker_thread = worker.start()
    click.echo("Observation worker started (daemon thread)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        worker.stop()
        conn.close()
        click.echo("\nServer stopped.")
