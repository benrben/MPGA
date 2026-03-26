"""mpga spoke <text> -- Speak text in Trump's voice via F5-TTS.

Streams audio chunks for low-latency playback.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

import click

from mpga.core.logger import log

CACHE_DIR = Path.home() / ".mpga" / "spoke-cache"
PORT = 5151


def _find_spoke_dir() -> Path:
    """Find the spoke directory — check plugin root first, then .mpga-runtime."""
    # 1. Relative to this file (inside the plugin)
    plugin_spoke = Path(__file__).resolve().parent.parent.parent.parent.parent / "spoke"
    if plugin_spoke.exists() and (plugin_spoke / "server.py").exists():
        return plugin_spoke

    # 2. Project-level runtime install
    runtime_spoke = Path.cwd() / ".mpga-runtime" / "spoke"
    if runtime_spoke.exists():
        return runtime_spoke

    # 3. MPGA_PLUGIN_ROOT env var
    import os
    plugin_root = os.environ.get("MPGA_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        env_spoke = Path(plugin_root) / "spoke"
        if env_spoke.exists():
            return env_spoke

    return plugin_spoke  # fallback (will fail gracefully)


def _is_server_running() -> bool:
    try:
        result = subprocess.run(
            ["curl", "-sf", f"http://127.0.0.1:{PORT}/health"],
            capture_output=True,
            timeout=1,
        )
        return result.returncode == 0
    except Exception:
        return False


def _start_server(spoke_dir: Path) -> None:
    venv_python = spoke_dir / "venv" / "bin" / "python3"
    server_script = spoke_dir / "server.py"

    log.info("Starting spoke server (loading model, one-time ~10s)...")
    child = subprocess.Popen(
        [str(venv_python), str(server_script), "--port", str(PORT)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid_file = spoke_dir / ".server.pid"
    pid_file.write_text(str(child.pid), encoding="utf-8")

    for _ in range(40):
        try:
            result = subprocess.run(
                ["curl", "-sf", f"http://127.0.0.1:{PORT}/health"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                log.success("Spoke server ready!")
                return
        except Exception:
            pass
        time.sleep(1)

    log.error("Server failed to start")


def _generate_via_server(text: str, wav_path: Path) -> None:
    """Single-shot generation: POST text, save returned WAV bytes."""
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/generate",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Server returned {resp.status}")
        wav_path.write_bytes(resp.read())


def _stream_via_server(text: str) -> None:
    """Stream via server -- plays each sentence chunk as it's generated."""
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/stream",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Server returned {resp.status}")

        wav_files: list[str] = []
        for raw_line in resp:
            line = raw_line.decode("utf-8").strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("file"):
                    wav_files.append(data["file"])
            except (json.JSONDecodeError, KeyError):
                pass

    for wav_file in wav_files:
        subprocess.run(["afplay", wav_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@click.command("spoke")
@click.argument("text", nargs=-1)
@click.option("--setup", is_flag=True, help="Run one-time setup (install deps, download voice)")
@click.option("--no-cache", "no_cache", is_flag=True, help="Skip cache, regenerate audio")
@click.option("--stream", is_flag=True, help="Stream sentence-by-sentence (play while generating)")
def spoke_cmd(
    text: tuple[str, ...],
    setup: bool,
    no_cache: bool,
    stream: bool,
) -> None:
    """Speak text in Trump voice via F5-TTS -- TREMENDOUS."""
    spoke_dir = _find_spoke_dir()
    venv_python = spoke_dir / "venv" / "bin" / "python3"
    ref_audio = spoke_dir / "voicedata" / "trump_ref.wav"

    if setup:
        setup_script = spoke_dir / "setup.sh"
        if not setup_script.exists():
            log.error(f"Setup script not found at {setup_script}")
            return
        log.info("Running spoke setup...")
        subprocess.run(["bash", str(setup_script)], check=False)
        return

    if not venv_python.exists() or not ref_audio.exists():
        log.error("Spoke not set up. Run: mpga spoke --setup")
        return

    joined_text = " ".join(text)
    if not joined_text:
        log.error('No text provided. Usage: mpga spoke "Your text here"')
        return

    # Strip ANSI escape codes
    clean_text = re.sub(r"\x1b\[[0-9;]*m", "", joined_text)

    if not _is_server_running():
        _start_server(spoke_dir)

    # Stream mode -- play sentence by sentence as generated
    if stream:
        try:
            _stream_via_server(clean_text)
        except Exception:
            log.error("Streaming TTS failed")
        return

    # Single-shot mode with cache
    md5_hash = hashlib.md5(clean_text.encode()).hexdigest()
    wav_path = CACHE_DIR / f"{md5_hash}.wav"

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    use_cache = not no_cache
    if use_cache and wav_path.exists():
        subprocess.run(
            ["afplay", str(wav_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    try:
        _generate_via_server(clean_text, wav_path)
    except Exception:
        log.error("TTS generation failed")
        return

    subprocess.run(
        ["afplay", str(wav_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
