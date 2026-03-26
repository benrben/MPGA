import json
import os
import time
from pathlib import Path

import pytest

from mpga.board.board_lock import acquire_board_lock, release_board_lock, with_board_lock


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    bd = tmp_path / "MPGA" / "board"
    bd.mkdir(parents=True)
    return bd


def test_acquire_board_lock_creates_lock_file(board_dir: Path):
    acquired = acquire_board_lock(str(board_dir))
    assert acquired is True
    lock_path = board_dir / ".board.lock"
    assert lock_path.exists()

    content = json.loads(lock_path.read_text())
    assert "pid" in content
    assert "timestamp" in content
    assert isinstance(content["pid"], int)
    assert isinstance(content["timestamp"], (int, float))


def test_release_board_lock_removes_lock_file(board_dir: Path):
    acquire_board_lock(str(board_dir))
    lock_path = board_dir / ".board.lock"
    assert lock_path.exists()

    release_board_lock(str(board_dir))
    assert not lock_path.exists()


def test_release_board_lock_is_noop_when_no_lock_exists(board_dir: Path):
    # Should not raise
    release_board_lock(str(board_dir))


def test_acquire_board_lock_returns_false_when_already_locked_by_another_process(
    board_dir: Path,
):
    lock_path = board_dir / ".board.lock"
    fake_pid = os.getpid() + 99999  # Very unlikely to be a real PID
    lock_path.write_text(
        json.dumps({"pid": fake_pid, "timestamp": int(time.time() * 1000)})
    )

    acquired = acquire_board_lock(str(board_dir))
    assert acquired is False


def test_acquire_board_lock_succeeds_when_held_by_current_process_reentrant(
    board_dir: Path,
):
    first = acquire_board_lock(str(board_dir))
    assert first is True

    # Same PID should be able to re-acquire
    second = acquire_board_lock(str(board_dir))
    assert second is True


def test_acquire_board_lock_overrides_stale_lock(board_dir: Path):
    lock_path = board_dir / ".board.lock"
    fake_pid = os.getpid() + 99999
    stale_timestamp = int(time.time() * 1000) - 60_000  # 60 seconds ago
    lock_path.write_text(
        json.dumps({"pid": fake_pid, "timestamp": stale_timestamp})
    )

    acquired = acquire_board_lock(str(board_dir))
    assert acquired is True

    # Lock file should now reflect current process
    content = json.loads(lock_path.read_text())
    assert content["pid"] == os.getpid()


def test_acquire_board_lock_respects_custom_timeout_for_stale_detection(
    board_dir: Path,
):
    lock_path = board_dir / ".board.lock"
    fake_pid = os.getpid() + 99999
    # 10 seconds ago -- stale with 5s timeout, not stale with 30s default
    timestamp = int(time.time() * 1000) - 10_000
    lock_path.write_text(json.dumps({"pid": fake_pid, "timestamp": timestamp}))

    # With 30s default timeout, should NOT be stale
    assert acquire_board_lock(str(board_dir), 30_000) is False

    # With 5s custom timeout, should be stale and overridable
    assert acquire_board_lock(str(board_dir), 5_000) is True


def test_with_board_lock_acquires_runs_function_and_releases(board_dir: Path):
    def callback():
        # Lock should exist inside the callback
        lock_path = board_dir / ".board.lock"
        assert lock_path.exists()
        return 42

    result = with_board_lock(str(board_dir), callback)
    assert result == 42
    # Lock should be released after
    lock_path = board_dir / ".board.lock"
    assert not lock_path.exists()


def test_with_board_lock_releases_lock_even_if_function_throws(board_dir: Path):
    with pytest.raises(Exception, match="boom"):
        with_board_lock(str(board_dir), _raise_boom)

    lock_path = board_dir / ".board.lock"
    assert not lock_path.exists()


def _raise_boom():
    raise Exception("boom")


def test_with_board_lock_throws_when_lock_cannot_be_acquired(board_dir: Path):
    lock_path = board_dir / ".board.lock"
    fake_pid = os.getpid() + 99999
    lock_path.write_text(
        json.dumps({"pid": fake_pid, "timestamp": int(time.time() * 1000)})
    )

    with pytest.raises(Exception, match=r"Could not acquire board lock"):
        with_board_lock(str(board_dir), lambda: "should not run")


def test_acquire_board_lock_creates_board_dir_if_not_exists(tmp_path: Path):
    new_board_dir = tmp_path / "new" / "board"
    acquired = acquire_board_lock(str(new_board_dir))
    assert acquired is True
    assert (new_board_dir / ".board.lock").exists()
