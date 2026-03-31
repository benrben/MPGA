"""Tests for the /speak queue endpoint in spoke server.py."""

import importlib.util
import io
import json
import queue
import sys
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

np = pytest.importorskip("numpy")
wavfile = pytest.importorskip("scipy.io.wavfile")

# ---------------------------------------------------------------------------
# Register mpga_spoke_server at module import time (pytest_configure in test
# files is not called by pytest — must register here instead).
# ---------------------------------------------------------------------------

def _register_spoke_server() -> None:
    if "mpga_spoke_server" in sys.modules:
        return
    server_path = Path(__file__).resolve().parent.parent.parent / "spoke" / "server.py"
    if not server_path.exists():
        return
    spec = importlib.util.spec_from_file_location("mpga_spoke_server", server_path)
    if spec is None:
        return
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mpga_spoke_server"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop("mpga_spoke_server", None)


_register_spoke_server()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(sample_rate: int = 22050) -> bytes:
    """Return minimal valid WAV bytes for mocking."""
    audio = np.zeros(sample_rate, dtype=np.float32)
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, audio)
    return buf.getvalue()


def _start_test_server():
    """Start server on OS-assigned port, return (server, port, thread)."""
    # Import here so patches applied in tests don't affect the import itself

    # We need to patch get_model before the module starts its worker thread.
    # Since the module is already imported at this point, we patch the function.
    server = HTTPServer(("127.0.0.1", 0), None)  # placeholder
    port = server.server_address[1]
    server.server_close()
    return port


# ---------------------------------------------------------------------------
# Test class using a real server on a free port
# ---------------------------------------------------------------------------

class TestSpeakEndpoint:
    """Tests for POST /speak endpoint."""

    @pytest.fixture(autouse=True)
    def server(self):
        """Start a real HTTPServer on a free port for each test."""
        import mpga_spoke_server as srv
        from mpga_spoke_server import Handler

        mock_model = MagicMock()
        mock_model.sample_rate = 22050
        mock_model.generate_audio.return_value = np.zeros(22050, dtype=np.float32)
        mock_voice = MagicMock()

        with patch.object(srv, "get_model", return_value=(mock_model, mock_voice)):
            self._server = HTTPServer(("127.0.0.1", 0), Handler)
            self._port = self._server.server_address[1]
            t = threading.Thread(target=self._server.serve_forever, daemon=True)
            t.start()
            yield
            self._server.shutdown()

    def _post(self, path: str, body: dict, timeout: int = 5):
        """Helper: POST JSON to the test server, return (status, response_bytes)."""
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self._port}{path}",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(data)),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_speak_returns_202_when_queue_not_full(self):
        """POST /speak with valid JSON and empty queue returns 202."""
        import mpga_spoke_server as srv
        # Drain the shared queue first so it's not full
        while not srv._speak_queue.empty():
            try:
                srv._speak_queue.get_nowait()
            except queue.Empty:
                break

        status, body = self._post("/speak", {"text": "Hello world"})
        assert status == 202
        data = json.loads(body)
        assert data["status"] == "queued"
        # Clean up the queued item so worker doesn't try to call get_model
        try:
            srv._speak_queue.get_nowait()
        except queue.Empty:
            pass

    def test_speak_returns_503_when_queue_full(self):
        """POST /speak when queue is full returns 503."""
        import mpga_spoke_server as srv

        # Fill the queue to maxsize
        filled = 0
        for _ in range(srv._speak_queue.maxsize):
            try:
                srv._speak_queue.put_nowait("dummy text")
                filled += 1
            except queue.Full:
                break

        try:
            status, body = self._post("/speak", {"text": "This should be rejected"})
            assert status == 503
            data = json.loads(body)
            assert data["status"] == "busy"
            assert "error" in data
        finally:
            # Drain the queue
            while not srv._speak_queue.empty():
                try:
                    srv._speak_queue.get_nowait()
                except queue.Empty:
                    break

    def test_speak_json_serialization(self):
        """Response body from /speak is valid JSON with expected keys."""
        import mpga_spoke_server as srv
        # Drain queue first
        while not srv._speak_queue.empty():
            try:
                srv._speak_queue.get_nowait()
            except queue.Empty:
                break

        status, body = self._post("/speak", {"text": "Test serialization"})
        # Should get either 202 (queued) or 503 (busy), both valid JSON
        assert status in (202, 503)
        data = json.loads(body.decode("utf-8"))
        assert "status" in data
        assert data["status"] in ("queued", "busy")

        # Clean up
        try:
            srv._speak_queue.get_nowait()
        except queue.Empty:
            pass

    def test_generate_still_works(self):
        """POST /generate still returns 200 + WAV bytes (with mocked model)."""
        import mpga_spoke_server as srv

        mock_model = MagicMock()
        mock_model.sample_rate = 22050
        mock_model.generate_audio.return_value = np.zeros(22050, dtype=np.float32)
        mock_voice = MagicMock()

        with patch.object(srv, "get_model", return_value=(mock_model, mock_voice)):
            status, body = self._post("/generate", {"text": "Test generate"})

        assert status == 200
        # Should be WAV data (starts with RIFF header)
        assert body[:4] == b"RIFF"

