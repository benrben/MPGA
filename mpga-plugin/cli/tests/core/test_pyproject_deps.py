"""T023: Assert flask is declared and key deps have upper bounds in pyproject.toml."""
from pathlib import Path

import tomllib


PYPROJECT = Path("/Users/benreich/MPGA/mpga-plugin/cli/pyproject.toml")


def _load() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_flask_in_dependencies():
    data = _load()
    deps: list[str] = data["project"]["dependencies"]
    flask_deps = [d for d in deps if d.lower().startswith("flask")]
    assert flask_deps, f"flask not found in [project.dependencies]: {deps}"


def test_deps_have_upper_bounds():
    data = _load()
    deps: list[str] = data["project"]["dependencies"]
    bounded = [d for d in deps if "<" in d or "~=" in d]
    assert bounded, (
        f"No dependencies have upper bounds (<x.y or ~=x.y). Current deps: {deps}"
    )
