"""T061: Assert pyproject.toml contains a [tool.mypy] or [tool.pyright] section."""
from pathlib import Path

import tomllib


PYPROJECT = Path("/Users/benreich/MPGA/mpga-plugin/cli/pyproject.toml")


def _load() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_type_checker_section_exists():
    data = _load()
    tool = data.get("tool", {})
    has_mypy = "mypy" in tool
    has_pyright = "pyright" in tool
    assert has_mypy or has_pyright, (
        "Neither [tool.mypy] nor [tool.pyright] found in pyproject.toml. "
        "Add a type checker configuration section."
    )


def test_mypy_python_version_set():
    data = _load()
    mypy = data.get("tool", {}).get("mypy", {})
    if mypy:
        assert "python_version" in mypy, (
            "[tool.mypy] exists but python_version is not set"
        )
