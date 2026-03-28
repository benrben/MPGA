#!/usr/bin/env python3
"""
MPGA Spoke TTS server — Pocket TTS (~100M params).

Memory-safe design:
  - Model loaded on first request, unloaded after IDLE_UNLOAD_SECS of inactivity
  - Audio buffers explicitly freed after each generation
  - Watchdog thread monitors idle time and unloads model automatically

Endpoints:
  GET  /health    — liveness probe
  POST /generate  — synchronous: returns WAV bytes
  POST /speak     — async queue: fire-and-forget playback
  POST /stream    — streaming: ndjson chunk file paths for low-latency playback

Usage:
    python server.py --port 5151
"""

from __future__ import annotations

import gc
import io
import json
import logging
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import scipy.io.wavfile

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SPOKE_DIR = Path(__file__).parent
TRUMP_VOICE = SPOKE_DIR / "voicedata" / "trump.safetensors"
REF_AUDIO = SPOKE_DIR / "voicedata" / "trump_ref.wav"

# ---------------------------------------------------------------------------
# Audio constants
# ---------------------------------------------------------------------------

TARGET_RMS = 0.20       # spoken-word loudness target (float32)
LIMITER_CEILING = 0.95  # hard clip ceiling
INTER_CHUNK_SILENCE_S = 0.03  # 30 ms breath gap between sentences

# ---------------------------------------------------------------------------
# Server constants
# ---------------------------------------------------------------------------

PORT = 5151
MAX_BODY = 65_536          # max request body bytes
QUEUE_MAXSIZE = 10         # speak queue depth

# ---------------------------------------------------------------------------
# Model lifecycle
# ---------------------------------------------------------------------------

IDLE_UNLOAD_SECS = 5 * 60    # unload model after 5 min idle
IDLE_EXIT_SECS   = 10 * 60   # exit process entirely after 10 min idle
WATCHDOG_INTERVAL_SECS = 30  # check every 30 s

_model = None
_voice = None
_model_lock = threading.Lock()
_last_used: float = 0.0

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("spoke")


def _load_model() -> None:
    """Load Pocket TTS model + Trump voice into globals (call under _model_lock)."""
    global _model, _voice
    from pocket_tts import TTSModel, export_model_state

    print("[spoke] Loading Pocket TTS model...", flush=True)
    t0 = time.time()
    _model = TTSModel.load_model()

    if TRUMP_VOICE.exists():
        _voice = _load_voice(TRUMP_VOICE)
        print("[spoke] Trump voice loaded from cache", flush=True)
    else:
        _voice = _model.get_state_for_audio_prompt(str(REF_AUDIO))
        export_model_state(_voice, str(TRUMP_VOICE))
        print("[spoke] Trump voice exported to cache", flush=True)

    print(f"[spoke] Ready in {time.time() - t0:.1f}s", flush=True)


def _load_voice(path: Path) -> dict:
    from safetensors.torch import load_file
    flat = load_file(str(path))
    voice: dict = {}
    for compound_key, tensor in flat.items():
        module, key = compound_key.split("/", 1)
        voice.setdefault(module, {})[key] = tensor
    return voice


def get_model():
    """Return (model, voice), loading if necessary. Updates last-used timestamp."""
    global _last_used
    with _model_lock:
        if _model is None:
            _load_model()
        _last_used = time.time()
        return _model, _voice


def unload_model() -> None:
    """Release model from memory and force GC. Safe to call at any time."""
    global _model, _voice
    with _model_lock:
        if _model is None:
            return
        print("[spoke] Idle timeout — unloading model to free RAM", flush=True)
        _model = None
        _voice = None

    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass


def _watchdog() -> None:
    """Background thread: unload model after 5 min idle, exit process after 10 min idle."""
    while True:
        time.sleep(WATCHDOG_INTERVAL_SECS)
        if _last_used > 0:
            idle = time.time() - _last_used
            if idle > IDLE_EXIT_SECS:
                print("[spoke] 10 min idle — exiting to free all RAM", flush=True)
                os._exit(0)
            elif idle > IDLE_UNLOAD_SECS and _model is not None:
                unload_model()


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def normalize_audio(audio) -> np.ndarray:
    """RMS-normalize to TARGET_RMS with a tanh limiter to prevent clipping."""
    arr = audio if isinstance(audio, np.ndarray) else audio.numpy()
    arr = arr.astype(np.float32)

    rms = np.sqrt(np.mean(arr ** 2))
    if rms < 1e-6:
        return arr  # silence — nothing to normalize

    arr = arr * (TARGET_RMS / rms)
    arr = np.where(
        np.abs(arr) > LIMITER_CEILING,
        np.sign(arr) * LIMITER_CEILING * np.tanh(np.abs(arr) / LIMITER_CEILING),
        arr,
    )
    return arr


def split_text(text: str) -> list[str]:
    """Split text into natural sentence chunks for TTS generation."""
    raw = re.split(r"(?<=[.!?])\s+", text)

    merged: list[str] = []
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        if merged and len(chunk) < 40:
            merged[-1] += " " + chunk
        else:
            merged.append(chunk)

    # If one giant chunk, split on commas/dashes into ~80-char pieces
    if len(merged) == 1 and len(merged[0]) > 200:
        parts = re.split(r"(?<=[,;—–])\s+", merged[0])
        merged = []
        buf = ""
        for p in parts:
            buf = (buf + " " + p).strip() if buf else p
            if len(buf) >= 80:
                merged.append(buf)
                buf = ""
        if buf:
            if merged:
                merged[-1] += " " + buf
            else:
                merged.append(buf)

    return merged or [text]


def generate_wav_bytes(text: str) -> bytes:
    """Generate full WAV audio for *text* and return as bytes.

    Explicitly frees all intermediate numpy buffers after use.
    """
    model, voice = get_model()
    t0 = time.time()

    chunks = split_text(text)
    audio_parts: list[np.ndarray] = []

    for i, chunk in enumerate(chunks):
        raw = model.generate_audio(voice, chunk)
        audio_parts.append(normalize_audio(raw))
        del raw
        print(f"[spoke] chunk {i + 1}/{len(chunks)}: {chunk[:50]}", flush=True)

    # Concatenate with a short silence between sentences
    silence = np.zeros(int(model.sample_rate * INTER_CHUNK_SILENCE_S), dtype=np.float32)
    combined: list[np.ndarray] = []
    for i, part in enumerate(audio_parts):
        combined.append(part)
        if i < len(audio_parts) - 1:
            combined.append(silence)

    full_audio = np.concatenate(combined)

    # Free intermediate buffers immediately — they can be large
    del audio_parts
    del combined
    gc.collect()

    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, model.sample_rate, full_audio)
    wav_bytes = buf.getvalue()

    del full_audio
    del buf
    gc.collect()

    print(f"[spoke] {time.time() - t0:.1f}s total: {text[:60]}", flush=True)
    return wav_bytes


# ---------------------------------------------------------------------------
# Async speak queue
# ---------------------------------------------------------------------------

_speak_queue: queue.Queue[str] = queue.Queue(maxsize=QUEUE_MAXSIZE)


def _speak_worker() -> None:
    """Drain _speak_queue: generate WAV, write to tmp file, play with afplay."""
    while True:
        text = _speak_queue.get()
        tmp_path: str | None = None
        try:
            wav = generate_wav_bytes(text)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav)
                tmp_path = f.name
            del wav
            subprocess.run(
                ["afplay", tmp_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            print(f"[spoke] worker error: {exc}", file=sys.stderr, flush=True)
        finally:
            _speak_queue.task_done()
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    # --- routing ---

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        routes = {
            "/generate": self._handle_generate,
            "/speak":    self._handle_speak,
            "/stream":   self._handle_stream,
        }
        handler = routes.get(self.path)
        if handler:
            handler()
        else:
            self.send_error(404)

    # --- endpoint handlers ---

    def _handle_generate(self) -> None:
        body = self._read_json()
        if body is None:
            return
        text = (body.get("text") or "").strip()
        if not text:
            self.send_error(400, "No text")
            return
        wav = generate_wav_bytes(text)
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)

    def _handle_speak(self) -> None:
        body = self._read_json()
        if body is None:
            return
        text = (body.get("text") or "").strip()
        if not text:
            self.send_error(400, "No text")
            return
        try:
            _speak_queue.put_nowait(text)
            self._send_json(202, {"status": "queued"})
        except queue.Full:
            self._send_json(503, {"status": "busy", "error": "Queue full — try again shortly"})

    def _handle_stream(self) -> None:
        body = self._read_json()
        if body is None:
            return
        text = (body.get("text") or "").strip()
        if not text:
            self.send_error(400, "No text")
            return

        model, voice = get_model()
        chunks = split_text(text)

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()

        for i, chunk_text in enumerate(chunks):
            t0 = time.time()
            raw = model.generate_audio(voice, chunk_text)
            audio = normalize_audio(raw)
            del raw

            fd, chunk_path = tempfile.mkstemp(suffix=".wav", prefix="spoke_stream_")
            try:
                os.close(fd)
                scipy.io.wavfile.write(chunk_path, model.sample_rate, audio)
                del audio
                elapsed = time.time() - t0
                print(
                    f"[spoke] stream chunk {i + 1}/{len(chunks)} ({elapsed:.1f}s): {chunk_text[:40]}",
                    flush=True,
                )
                line = json.dumps({"chunk": i, "total": len(chunks), "file": chunk_path}) + "\n"
                self.wfile.write(line.encode())
                self.wfile.flush()
            except Exception:
                try:
                    os.unlink(chunk_path)
                except OSError:
                    pass
                raise

    # --- helpers ---

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            self.send_error(400, "Empty body")
            return None
        if length > MAX_BODY:
            self.send_error(413, "Body too large")
            return None
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return None

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        pass  # suppress default access log


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MPGA Spoke TTS server")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument(
        "--preload",
        action="store_true",
        help="Load model immediately on startup instead of on first request",
    )
    args = parser.parse_args()

    # Background threads
    threading.Thread(target=_speak_worker, daemon=True, name="speak-worker").start()
    threading.Thread(target=_watchdog, daemon=True, name="idle-watchdog").start()

    if args.preload:
        get_model()  # warm start — loads model before first request

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[spoke] listening on http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[spoke] shutting down", flush=True)
