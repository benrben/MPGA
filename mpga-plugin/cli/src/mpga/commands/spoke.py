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
CACHE_MAX_BYTES = 100 * 1024 * 1024  # 100 MB hard cap

def _allowed_audio_dirs() -> list[Path]:
    """Return allowed directories for afplay, reading CACHE_DIR at call time."""
    return [Path("/tmp"), CACHE_DIR]


def _validate_afplay_path(raw_path: str) -> Path:
    """Resolve and validate a path before passing it to afplay.

    Raises ValueError if the resolved path is not under an allowed directory
    (/tmp or CACHE_DIR).  Returns the resolved Path on success.
    """
    resolved = Path(raw_path).resolve()
    allowed_dirs = _allowed_audio_dirs()
    for allowed in allowed_dirs:
        try:
            resolved.relative_to(allowed.resolve())
            return resolved
        except ValueError:
            continue
    raise ValueError(
        f"afplay path '{resolved}' is not allowed. "
        f"Only paths under {[str(d) for d in allowed_dirs]} are permitted."
    )


def _evict_cache() -> None:
    """Evict oldest WAV files from the cache if total size exceeds CACHE_MAX_BYTES."""
    files = sorted(CACHE_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime)
    total = sum(f.stat().st_size for f in files)
    while total > CACHE_MAX_BYTES and files:
        oldest = files.pop(0)
        total -= oldest.stat().st_size
        try:
            oldest.unlink()
        except OSError:
            pass


def trumpify(text: str) -> str:
    """Rewrite text into Trump's natural speaking cadence.

    Studied from hundreds of rally speeches and press conferences.
    Trump's signature patterns:
    - Fragments, not sentences. 3-8 words max.
    - Immediate repetition: "It's big. Very big."
    - Self-interruption mid-thought: "And by the way—"
    - Callback: "I told them. I said it from the beginning."
    - Superlative stacking: "the best, maybe the best ever"
    - Direct audience address: "you know it", "everybody knows"
    - Pause-for-effect one-word sentences: "Tremendous." "Beautiful."
    """
    import random

    # Sentence starters — Trump almost always opens with one of these
    openers = [
        "Look, ", "Here's the thing. ", "And let me tell you something. ",
        "So, ", "Now, ", "And frankly, ", "You know what? ",
        "Here's what happened. ", "I'll tell you, ", "People don't know this but, ",
    ]

    # Mid-speech interjections — dropped between fragments
    interjections = [
        "Believe me.", "It's true.", "Everybody knows it.",
        "True.", "That I can tell you.", "OK?",
        "You know that.", "Right?", "Think about it.",
        "Nobody thought it was possible.", "And they said it couldn't be done.",
        "Many people are saying it.", "Incredible.", "Tremendous.",
        "The likes of which nobody's ever seen.", "Not even close.",
        "Big league.", "Beautiful ring to it.",
    ]

    # Code/dev-specific interjections — only used when text is about code
    code_keywords = (
        "code", "module", "function", "deploy", "test", "merge", "branch",
        "dependency", "package", "lint", "build", "scope", "coverage", "docs",
        "commit", "repo", "git", "api", "bug", "fix", "refactor", "mpga",
    )
    is_code_context = any(kw in text.lower() for kw in code_keywords)
    if is_code_context:
        interjections += [
            "Fake docs!", "No collusion between modules.",
            "Build the wall around that module.", "Lock that mutex up!",
            "Law and order in the dependency graph.",
            "Covfefe. I mean, coverage.",
            "Total witch hunt against clean code.", "Pin your versions, folks.",
            "Even the type annotations are perfect.", "Zero merge conflicts.",
            "Not like Sleepy Copilot.", "Crooked Gemini could never.",
            "Little Cursor would forget this in 3 seconds.",
            "Crazy Devin charges $500 a month for THIS?",
            "Low Energy ESLint wouldn't catch that in a million years.",
            "Lyin' ChatGPT would make that up.", "Crazy NPM would need 200 packages for this.",
            "Cryin' Jenkins would be red right now.", "Sloppy Semicolons everywhere with those tools.",
        ]

    # Callbacks — Trump loves referring back to himself
    callbacks = [
        "I said it from day one.", "I called it.", "I was right.",
        "And I said that a long time ago.", "Everyone told me I was wrong. I wasn't.",
        "I knew it before anybody.", "They didn't listen. Now they listen.",
    ]
    if is_code_context:
        callbacks += [
            "I alone can fix this codebase.", "Make Project Great Again.",
            "A complete and total shutdown of untested deploys.",
            "Some of these dependencies, I assume, are good packages.",
            "Who can figure out this spaghetti code? Nobody. That's why we have MPGA.",
            "I will absolutely apologize if I'm ever wrong about a revert. Hasn't happened yet.",
        ]

    # Emphasis repetitions — key adjectives get the Trump double-tap
    emphasis = {
        "good": ["good. Very good.", "good, really good, the best actually"],
        "great": ["great. Really great.", "great, maybe the greatest ever"],
        "bad": ["bad. Really bad.", "bad, a total disaster frankly"],
        "big": ["big. Very big.", "big, tremendously big"],
        "important": ["important. Very important.", "important, maybe the most important ever"],
        "fast": ["fast. Incredibly fast.", "fast, like nobody's ever seen"],
        "best": ["the best. The absolute best.", "the best, and nobody even comes close"],
        "beautiful": ["beautiful. So beautiful.", "beautiful, the most beautiful you've ever seen"],
        "strong": ["strong. Very strong.", "strong, the strongest in history"],
        "smart": ["smart. Very smart.", "smart, genius level frankly"],
        "clean": ["clean. Very clean.", "clean, the cleanest anyone's ever seen"],
        "perfect": ["perfect. Absolutely perfect.", "perfect, some say the most perfect ever"],
        "amazing": ["amazing. Truly amazing.", "amazing, like nothing you've ever seen"],
        "terrible": ["terrible. Just terrible.", "terrible, maybe the worst ever"],
        "incredible": ["incredible. Truly incredible.", "incredible, the likes of which nobody's seen"],
        "tremendous": ["tremendous. Absolutely tremendous.", "tremendous, people can't believe it"],
    }

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    result = []

    # 40% chance to open with a Trump-style starter
    if random.random() < 0.4:
        result.append(random.choice(openers))

    for i, sentence in enumerate(sentences):
        s = sentence.strip()
        if not s:
            continue

        # Break long sentences (>12 words) into Trump fragments
        words = s.split()
        if len(words) > 12:
            mid = len(words) // 2
            # Find a natural break near the middle (comma, conjunction)
            break_at = mid
            for j in range(max(mid - 3, 0), min(mid + 3, len(words))):
                w = words[j].lower().rstrip(".,!?;:")
                if w in ("and", "but", "because", "so", "which", "that", "where", "when") or words[j].endswith(","):
                    break_at = j
                    break
            first_half = " ".join(words[:break_at + 1]).rstrip(",")
            second_half = " ".join(words[break_at + 1:])
            if first_half and second_half:
                s = first_half + ". " + second_half
                if not s.rstrip().endswith((".", "!", "?")):
                    s = s.rstrip() + "."

        # Apply emphasis doubling (40% chance per matching word)
        out_words = []
        for w in s.split():
            lower = w.lower().rstrip(".,!?;:")
            punct = w[len(lower):] if len(w) > len(lower) else ""
            if lower in emphasis and random.random() < 0.4:
                out_words.append(random.choice(emphasis[lower]) + punct)
            else:
                out_words.append(w)
        s = " ".join(out_words)

        result.append(s)

        # Interjection after sentence (30% chance, never after last)
        if i < len(sentences) - 1 and random.random() < 0.3:
            result.append(random.choice(interjections))

    # 25% chance to end with a callback
    if random.random() < 0.25:
        result.append(random.choice(callbacks))

    return " ".join(result)


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
    except (OSError, subprocess.TimeoutExpired):
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
        except (OSError, subprocess.TimeoutExpired):
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


def _speak_via_queue(text: str) -> None:
    """POST text to /speak queue endpoint; handle non-202 gracefully."""
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/speak",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 202:
                log.error(f"Spoke queue returned {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code == 503:
            log.error("Spoke queue is busy — try again shortly")
        else:
            log.error(f"Spoke queue error: {e.code}")
    except Exception as exc:
        log.error(f"Spoke queue request failed: {exc}")


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
        try:
            safe_path = _validate_afplay_path(wav_file)
        except ValueError as exc:
            log.error(f"Refusing to play file: {exc}")
            continue
        subprocess.run(["afplay", str(safe_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@click.command("spoke")
@click.argument("text", nargs=-1)
@click.option("--setup", is_flag=True, help="Run one-time setup (install deps, download voice)")
@click.option("--no-cache", "no_cache", is_flag=True, help="Skip cache, regenerate audio")
@click.option("--stream", is_flag=True, help="Stream sentence-by-sentence (play while generating)")
@click.option("--sync", is_flag=True, help="Single-shot generation with cache (synchronous, bypasses queue)")
def spoke_cmd(
    text: tuple[str, ...],
    setup: bool,
    no_cache: bool,
    stream: bool,
    sync: bool,
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

    # Trumpify the text for natural Trump speaking cadence
    clean_text = trumpify(clean_text)

    if not _is_server_running():
        _start_server(spoke_dir)

    # Stream mode -- play sentence by sentence as generated
    if stream:
        try:
            _stream_via_server(clean_text)
        except (OSError, ConnectionError) as e:
            log.error(f"Streaming TTS failed: {e}")
        return

    if sync:
        # Single-shot mode with cache
        md5_hash = hashlib.md5(clean_text.encode()).hexdigest()
        wav_path = CACHE_DIR / f"{md5_hash}.wav"

        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        use_cache = not no_cache
        if use_cache and wav_path.exists():
            safe_path = _validate_afplay_path(str(wav_path))
            subprocess.run(
                ["afplay", str(safe_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        try:
            _generate_via_server(clean_text, wav_path)
        except (OSError, ConnectionError) as e:
            log.error(f"TTS generation failed: {e}")
            return

        _evict_cache()

        safe_path = _validate_afplay_path(str(wav_path))
        subprocess.run(
            ["afplay", str(safe_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # Queue mode bypasses cache — fire-and-forget semantics; cache only operative with --sync
        _speak_via_queue(clean_text)
