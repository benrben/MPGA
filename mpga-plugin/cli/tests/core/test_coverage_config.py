"""Test that pyproject.toml enforces a meaningful coverage threshold (>= 80%)."""

import tomllib
from pathlib import Path


def test_coverage_fail_under_is_at_least_80():
    """Coverage threshold must be >= 80 to align with TDD discipline."""
    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        config = tomllib.load(f)

    fail_under = config["tool"]["coverage"]["report"]["fail_under"]
    assert fail_under >= 80, (
        f"Coverage fail_under is {fail_under} — TDD projects should enforce >= 80%"
    )
