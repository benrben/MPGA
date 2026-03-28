#!/usr/bin/env python3
"""
MPGA Spoke TTS server — Pocket TTS (~100M params, ~200MB RAM).

Keeps model + Trump voice loaded. Generation in <1s.
Supports streaming via /stream endpoint.

Usage:
    python server.py --port 5151
"""

import io
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import wave
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np
import scipy.io.wavfile

SPOKE_DIR = os.path.dirname(__file__)
TRUMP_VOICE = os.path.join(SPOKE_DIR, "voicedata", "trump.safetensors")
REF_AUDIO = os.path.join(SPOKE_DIR, "voicedata", "trump_ref.wav")

_model = None
_voice = None

# Target RMS level (0.18-0.20 is typical "spoken word" loudness for float32)
TARGET_RMS = 0.20
# Hard limiter ceiling to prevent clipping
LIMITER_CEILING = 0.95

# Thread-safe queue for /speak endpoint
_speak_queue: queue.Queue = queue.Queue(maxsize=10)

# Maximum allowed request body size (bytes)
MAX_BODY = 65_536


def normalize_audio(audio_np):
    """RMS-normalize audio to consistent loudness, with a limiter to prevent clipping."""
    arr = audio_np if isinstance(audio_np, np.ndarray) else audio_np.numpy()
    arr = arr.astype(np.float32)

    # Compute RMS (skip silence at start/end)
    rms = np.sqrt(np.mean(arr ** 2))
    if rms < 1e-6:
        return arr  # silence

    # Scale to target RMS
    gain = TARGET_RMS / rms
    arr = arr * gain

    # Soft-clip anything above the ceiling (tanh limiter)
    arr = np.where(
        np.abs(arr) > LIMITER_CEILING,
        np.sign(arr) * LIMITER_CEILING * np.tanh(np.abs(arr) / LIMITER_CEILING),
        arr,
    )

    return arr


def load_voice_state(path):
    """Load exported voice state from safetensors file."""
    from safetensors.torch import load_file
    flat = load_file(path)
    result = {}
    for compound_key, tensor in flat.items():
        module, key = compound_key.split("/", 1)
        if module not in result:
            result[module] = {}
        result[module][key] = tensor
    return result


def get_model():
    global _model, _voice
    if _model is None:
        from pocket_tts import TTSModel, export_model_state
        print("[spoke] Loading Pocket TTS model...")
        t0 = time.time()
        _model = TTSModel.load_model()

        if os.path.exists(TRUMP_VOICE):
            _voice = load_voice_state(TRUMP_VOICE)
            print("[spoke] Trump voice loaded from cache")
        else:
            _voice = _model.get_state_for_audio_prompt(REF_AUDIO)
            export_model_state(_voice, TRUMP_VOICE)
            print("[spoke] Trump voice exported")

        print(f"[spoke] Ready in {time.time()-t0:.1f}s")
    return _model, _voice


def split_text(text):
    """Split text into natural sentence chunks for TTS generation.

    Strategy: split only on sentence-ending punctuation (.!?) to keep
    natural phrasing intact. Merge short fragments into the previous
    chunk to avoid choppy single-word outputs.
    """
    # Split on sentence boundaries only — keep commas/semicolons INSIDE sentences
    raw = re.split(r'(?<=[.!?])\s+', text)

    # Merge tiny fragments (< 40 chars) with previous chunk
    merged = []
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        if merged and len(chunk) < 40:
            merged[-1] += " " + chunk
        else:
            merged.append(chunk)

    # If everything merged into one giant chunk (> 200 chars), split on commas/dashes
    if len(merged) == 1 and len(merged[0]) > 200:
        parts = re.split(r'(?<=[,;—–])\s+', merged[0])
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

    return merged if merged else [text]


def _generate_wav_bytes(text: str) -> bytes:
    """Generate audio for text and return WAV bytes.

    Takes a text string, splits into chunks, generates audio per chunk,
    normalizes, concatenates, and returns WAV bytes.
    """
    model, voice = get_model()
    t0 = time.time()

    # Split into sentence chunks for natural pacing
    chunks = split_text(text)
    audio_parts = []
    for i, chunk in enumerate(chunks):
        chunk_audio = model.generate_audio(voice, chunk)
        chunk_loud = normalize_audio(chunk_audio)
        audio_parts.append(chunk_loud)
        print(f"[spoke] chunk {i+1}/{len(chunks)}: {chunk[:50]}")

    # Concatenate all chunks with minimal silence (30ms — just enough for natural breath)
    silence = np.zeros(int(model.sample_rate * 0.03), dtype=np.float32)
    combined = []
    for i, part in enumerate(audio_parts):
        combined.append(part)
        if i < len(audio_parts) - 1:
            combined.append(silence)
    full_audio = np.concatenate(combined)

    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, model.sample_rate, full_audio)
    wav_data = buf.getvalue()

    print(f"[spoke] {time.time()-t0:.1f}s total: {text[:60]}")
    return wav_data


def _speak_worker():
    """Background worker thread that reads from _speak_queue and plays audio."""
    while True:
        text = _speak_queue.get()
        tmp_path: str | None = None
        try:
            wav_data = _generate_wav_bytes(text)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_data)
                tmp_path = tmp.name
            subprocess.run(["afplay", tmp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[spoke] worker error: {e}", file=sys.stderr)
        finally:
            _speak_queue.task_done()
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass


# Start the background worker thread
_worker_thread = threading.Thread(target=_speak_worker, daemon=True)
_worker_thread.start()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/generate":
            self._handle_generate()
        elif self.path == "/stream":
            self._handle_stream()
        elif self.path == "/speak":
            self._handle_speak()
        else:
            self.send_error(404)

    def _handle_generate(self):
        body = self._read_json()
        if not body:
            return
        text = body.get("text", "")
        if not text.strip():
            self.send_error(400, "No text")
            return

        wav_data = _generate_wav_bytes(text)
        self._send_wav(wav_data)

    def _handle_speak(self):
        body = self._read_json()
        if not body:
            return
        text = body.get("text", "")
        if not text.strip():
            self.send_error(400, "No text")
            return

        try:
            _speak_queue.put_nowait(text)
            resp = json.dumps({"status": "queued"}).encode("utf-8")
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        except queue.Full:
            resp = json.dumps({"status": "busy", "error": "Queue full"}).encode("utf-8")
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

    def _handle_stream(self):
        body = self._read_json()
        if not body:
            return
        text = body.get("text", "")
        if not text.strip():
            self.send_error(400, "No text")
            return

        chunks = split_text(text)
        model, voice = get_model()

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()

        for i, chunk_text in enumerate(chunks):
            t0 = time.time()
            audio = model.generate_audio(voice, chunk_text)
            audio_loud = normalize_audio(audio)
            fd, chunk_path = tempfile.mkstemp(suffix=".wav", prefix="spoke_stream_")
            try:
                os.close(fd)
                scipy.io.wavfile.write(chunk_path, model.sample_rate, audio_loud)
                elapsed = time.time() - t0
                print(f"[spoke] chunk {i+1}/{len(chunks)} ({elapsed:.1f}s): {chunk_text[:40]}")
                line = json.dumps({"chunk": i, "total": len(chunks), "file": chunk_path}) + "\n"
                self.wfile.write(line.encode())
                self.wfile.flush()
            finally:
                try:
                    os.unlink(chunk_path)
                except Exception:
                    pass

    def _read_json(self):
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

    def _send_wav(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5151)
    args = parser.parse_args()
    get_model()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[spoke] http://127.0.0.1:{args.port}")
    server.serve_forever()
