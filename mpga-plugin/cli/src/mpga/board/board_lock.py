from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

LOCK_FILENAME = ".board.lock"
DEFAULT_STALE_TIMEOUT_MS = 30_000  # 30 seconds

T = TypeVar("T")


@dataclass
class LockContent:
    pid: int
    timestamp: float  # milliseconds since epoch


def acquire_board_lock(
    board_dir: str,
    timeout: int = DEFAULT_STALE_TIMEOUT_MS,
) -> bool:
    """Acquire an advisory file lock for board.json concurrent access.

    Creates a ``.board.lock`` file in the given *board_dir* containing the
    current process PID and a timestamp.  If a lock already exists:

    - If held by the same PID, re-acquisition succeeds (re-entrant).
    - If the lock is older than *timeout* ms, it is considered stale and
      overridden.
    - Otherwise, acquisition fails and returns ``False``.
    """
    p = Path(board_dir)
    p.mkdir(parents=True, exist_ok=True)
    lock_path = p / LOCK_FILENAME
    content = LockContent(pid=os.getpid(), timestamp=time.time() * 1000)

    try:
        # Atomic exclusive create -- fails if file already exists (no TOCTOU)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, json.dumps({"pid": content.pid, "timestamp": content.timestamp}).encode())
        finally:
            os.close(fd)
        return True
    except FileExistsError:
        # Lock file exists -- check if re-entrant or stale
        try:
            existing_raw = lock_path.read_text(encoding="utf-8")
            existing = json.loads(existing_raw)

            # Re-entrant: same PID can re-acquire
            if existing.get("pid") == os.getpid():
                lock_path.write_text(
                    json.dumps({"pid": content.pid, "timestamp": content.timestamp}),
                    encoding="utf-8",
                )
                return True

            # Check for stale lock
            age = time.time() * 1000 - existing.get("timestamp", 0)
            if age < timeout:
                return False

            # Lock is stale -- override it
            lock_path.write_text(
                json.dumps({"pid": content.pid, "timestamp": content.timestamp}),
                encoding="utf-8",
            )
            return True
        except Exception:
            # Corrupted lock file -- override it
            lock_path.write_text(
                json.dumps({"pid": content.pid, "timestamp": content.timestamp}),
                encoding="utf-8",
            )
            return True
    except OSError:
        # Lock file exists (non-FileExistsError variant on some platforms)
        try:
            existing_raw = lock_path.read_text(encoding="utf-8")
            existing = json.loads(existing_raw)

            if existing.get("pid") == os.getpid():
                lock_path.write_text(
                    json.dumps({"pid": content.pid, "timestamp": content.timestamp}),
                    encoding="utf-8",
                )
                return True

            age = time.time() * 1000 - existing.get("timestamp", 0)
            if age < timeout:
                return False

            lock_path.write_text(
                json.dumps({"pid": content.pid, "timestamp": content.timestamp}),
                encoding="utf-8",
            )
            return True
        except Exception:
            lock_path.write_text(
                json.dumps({"pid": content.pid, "timestamp": content.timestamp}),
                encoding="utf-8",
            )
            return True


def release_board_lock(board_dir: str) -> None:
    """Release the advisory file lock for board.json.

    Removes the ``.board.lock`` file if it exists.  No-op if no lock exists.
    """
    lock_path = Path(board_dir) / LOCK_FILENAME
    if lock_path.exists():
        lock_path.unlink()


def with_board_lock(board_dir: str, fn: Callable[[], T]) -> T:
    """Convenience wrapper that acquires the board lock, runs *fn*, and
    releases the lock afterward (even if *fn* raises).

    Raises ``RuntimeError`` if the lock cannot be acquired.
    """
    acquired = acquire_board_lock(board_dir)
    if not acquired:
        raise RuntimeError(f"Could not acquire board lock in {board_dir}")
    try:
        return fn()
    finally:
        release_board_lock(board_dir)
