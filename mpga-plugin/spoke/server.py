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
import re
import tempfile
import time
import uuid
import wave
from http.server import HTTPServer, BaseHTTPRequestHandler

import scipy.io.wavfile

SPOKE_DIR = os.path.dirname(__file__)
TRUMP_VOICE = os.path.join(SPOKE_DIR, "voicedata", "trump.safetensors")
REF_AUDIO = os.path.join(SPOKE_DIR, "voicedata", "trump_ref.wav")

_model = None
_voice = None


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
    chunks = re.split(r'(?<=[.!?,;:])\s+', text)
    merged = []
    buf = ""
    for c in chunks:
        buf = (buf + " " + c).strip() if buf else c
        if len(buf) >= 20:
            merged.append(buf)
            buf = ""
    if buf:
        if merged:
            merged[-1] += " " + buf
        else:
            merged.append(buf)
    return merged if merged else [text]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/generate":
            self._handle_generate()
        elif self.path == "/stream":
            self._handle_stream()
        else:
            self.send_error(404)

    def _handle_generate(self):
        body = self._read_json()
        if not body:
            return
        text = body.get("text", "")
        if not text:
            self.send_error(400, "No text")
            return

        model, voice = get_model()
        t0 = time.time()
        audio = model.generate_audio(voice, text)

        buf = io.BytesIO()
        scipy.io.wavfile.write(buf, model.sample_rate, audio.numpy())
        wav_data = buf.getvalue()

        print(f"[spoke] {time.time()-t0:.1f}s: {text[:60]}")
        self._send_wav(wav_data)

    def _handle_stream(self):
        body = self._read_json()
        if not body:
            return
        text = body.get("text", "")
        if not text:
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
            chunk_path = os.path.join(tempfile.gettempdir(), f"spoke_stream_{i}.wav")
            scipy.io.wavfile.write(chunk_path, model.sample_rate, audio.numpy())
            elapsed = time.time() - t0
            print(f"[spoke] chunk {i+1}/{len(chunks)} ({elapsed:.1f}s): {chunk_text[:40]}")
            line = json.dumps({"chunk": i, "total": len(chunks), "file": chunk_path}) + "\n"
            self.wfile.write(line.encode())
            self.wfile.flush()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            self.send_error(400, "Empty body")
            return None
        return json.loads(self.rfile.read(length))

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
