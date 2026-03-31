"""T010 — project type detection should prefer CLI over FastAPI/Flask.

The bug: detect_project_type() checks for 'fastapi' or 'flask' in file paths
before checking for CLI markers. A project that has web/flask_app.py alongside
cli.py + Click + [project.scripts] should be identified as 'CLI', not 'FastAPI'.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mpga.core.scanner import ScanResult, FileInfo, detect_project_type


def _make_result(root: str, files: list[tuple[str, str]]) -> ScanResult:
    """Create a ScanResult with the given (filepath, language) pairs."""
    file_infos = [
        FileInfo(filepath=fp, lines=10, language=lang, size=100)
        for fp, lang in files
    ]
    languages: dict[str, dict[str, int]] = {}
    for fi in file_infos:
        if fi.language not in languages:
            languages[fi.language] = {"files": 0, "lines": 0}
        languages[fi.language]["files"] += 1
        languages[fi.language]["lines"] += fi.lines

    return ScanResult(
        root=root,
        files=file_infos,
        total_files=len(file_infos),
        total_lines=sum(fi.lines for fi in file_infos),
        languages=languages,
        entry_points=[],
        top_level_dirs=[],
    )


class TestDetectProjectType:
    """detect_project_type() should prefer CLI markers over web framework markers."""

    def test_cli_preferred_over_fastapi_when_cli_py_present(self, tmp_path: Path):
        """Project with cli.py and web/flask_app.py → 'CLI', not 'FastAPI'."""
        # Simulate the MPGA project structure: cli.py + flask_app.py (for TTS)
        result = _make_result(
            str(tmp_path),
            [
                ("src/mpga/cli.py", "python"),
                ("src/mpga/web/flask_app.py", "python"),
                ("src/mpga/commands/sync.py", "python"),
            ],
        )
        project_type = detect_project_type(result, project_root=str(tmp_path))
        assert project_type == "CLI", (
            f"Expected 'CLI' but got '{project_type}' — "
            "CLI marker (cli.py) should outrank web framework detection"
        )

    def test_cli_preferred_when_pyproject_has_scripts(self, tmp_path: Path):
        """Project with [project.scripts] in pyproject.toml → 'CLI'."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'mpga'\n\n[project.scripts]\nmpga = 'mpga.cli:main'\n"
        )
        result = _make_result(
            str(tmp_path),
            [
                ("mpga/cli.py", "python"),
                ("mpga/web/flask_app.py", "python"),
            ],
        )
        project_type = detect_project_type(result, project_root=str(tmp_path))
        assert project_type == "CLI", (
            f"Expected 'CLI' (pyproject.toml has [project.scripts]) but got '{project_type}'"
        )

    def test_cli_preferred_when_click_in_main_file(self, tmp_path: Path):
        """Project where cli.py imports click → 'CLI'."""
        cli_file = tmp_path / "cli.py"
        cli_file.write_text("import click\n\n@click.command()\ndef main(): pass\n")

        result = _make_result(
            str(tmp_path),
            [
                ("cli.py", "python"),
                ("web/app.py", "python"),
            ],
        )
        project_type = detect_project_type(result, project_root=str(tmp_path))
        assert project_type == "CLI", (
            f"Expected 'CLI' (click import in cli.py) but got '{project_type}'"
        )

    def test_fastapi_detected_when_no_cli_markers(self, tmp_path: Path):
        """Project with only fastapi files and no CLI markers → 'FastAPI'."""
        result = _make_result(
            str(tmp_path),
            [
                ("app/fastapi_main.py", "python"),
                ("app/routes.py", "python"),
            ],
        )
        project_type = detect_project_type(result, project_root=str(tmp_path))
        assert project_type == "FastAPI", (
            f"Expected 'FastAPI' when no CLI markers present, got '{project_type}'"
        )

    def test_python_fallback_when_no_framework_detected(self, tmp_path: Path):
        """Pure Python project with no framework or CLI markers → 'Python'."""
        result = _make_result(
            str(tmp_path),
            [
                ("utils.py", "python"),
                ("helpers.py", "python"),
            ],
        )
        project_type = detect_project_type(result, project_root=str(tmp_path))
        assert project_type == "Python", (
            f"Expected 'Python' fallback but got '{project_type}'"
        )
