"""T032: Test that bare 'except Exception:' usage is reduced to < 10.

Bare 'except Exception:' swallows all errors without logging. Replace with:
- File I/O -> except (OSError, IOError):
- JSON -> except (json.JSONDecodeError, ValueError):
- SQLite -> except sqlite3.Error:
- At minimum: except Exception as e: + log it
"""
import subprocess
from pathlib import Path

SRC_DIR = Path("/Users/benreich/MPGA/mpga-plugin/cli/src/mpga")


def _count_bare_exceptions() -> int:
    result = subprocess.run(
        ["grep", "-rn", "except Exception:", str(SRC_DIR)],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return len(lines)


def test_bare_exception_count_below_threshold():
    """There must be fewer than 10 bare 'except Exception:' in the source."""
    count = _count_bare_exceptions()
    assert count < 10, (
        f"Found {count} bare 'except Exception:' occurrences in src/mpga/. "
        "Replace with specific exception types (OSError, sqlite3.Error, etc.) "
        "or at minimum 'except Exception as e:' with logging."
    )
