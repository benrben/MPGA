"""T009 — scanner must exclude .venv, .mpga-runtime, __pycache__, node_modules, .git.

The bug: scan() in scanner.py uses `not d.startswith(".")` to prune hidden dirs,
which handles .git but NOT named dirs like .venv (starts with dot — actually this
WOULD be pruned). The real problem is that .venv and similar dirs must appear in
a canonical DEFAULT exclusion list even when the user's config.ignore is empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mpga.core.scanner import DEFAULT_EXCLUDE_DIRS, scan


class TestScanExclude:
    """Scanner exclusion tests — protect sync from virtual-env bloat."""

    def test_default_exclude_dirs_contains_venv(self):
        """DEFAULT_EXCLUDE_DIRS constant includes .venv."""
        assert ".venv" in DEFAULT_EXCLUDE_DIRS, (
            f".venv must be in DEFAULT_EXCLUDE_DIRS, got: {DEFAULT_EXCLUDE_DIRS}"
        )

    def test_default_exclude_dirs_contains_mpga_runtime(self):
        """DEFAULT_EXCLUDE_DIRS constant includes .mpga-runtime."""
        assert ".mpga-runtime" in DEFAULT_EXCLUDE_DIRS, (
            f".mpga-runtime must be in DEFAULT_EXCLUDE_DIRS, got: {DEFAULT_EXCLUDE_DIRS}"
        )

    def test_default_exclude_dirs_contains_pycache(self):
        """DEFAULT_EXCLUDE_DIRS constant includes __pycache__."""
        assert "__pycache__" in DEFAULT_EXCLUDE_DIRS, (
            f"__pycache__ must be in DEFAULT_EXCLUDE_DIRS, got: {DEFAULT_EXCLUDE_DIRS}"
        )

    def test_default_exclude_dirs_contains_node_modules(self):
        """DEFAULT_EXCLUDE_DIRS constant includes node_modules."""
        assert "node_modules" in DEFAULT_EXCLUDE_DIRS, (
            f"node_modules must be in DEFAULT_EXCLUDE_DIRS, got: {DEFAULT_EXCLUDE_DIRS}"
        )

    def test_default_exclude_dirs_contains_git(self):
        """DEFAULT_EXCLUDE_DIRS constant includes .git."""
        assert ".git" in DEFAULT_EXCLUDE_DIRS, (
            f".git must be in DEFAULT_EXCLUDE_DIRS, got: {DEFAULT_EXCLUDE_DIRS}"
        )

    def test_scan_excludes_venv_directory(self, tmp_path: Path):
        """scan() ignores files inside a .venv directory."""
        venv = tmp_path / ".venv" / "lib" / "python3.11" / "site-packages"
        venv.mkdir(parents=True)
        (venv / "requests.py").write_text("# requests library stub\ndef get(): pass\n")

        # Real project file
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def main(): pass\n")

        result = scan(str(tmp_path), ignore=[])
        filepaths = [f.filepath for f in result.files]

        assert not any(".venv" in p for p in filepaths), (
            f".venv files should be excluded, but found: {[p for p in filepaths if '.venv' in p]}"
        )
        assert any("main.py" in p for p in filepaths), (
            "src/main.py should be scanned but was excluded"
        )

    def test_scan_excludes_mpga_runtime_directory(self, tmp_path: Path):
        """scan() ignores files inside .mpga-runtime."""
        runtime = tmp_path / ".mpga-runtime" / "cache"
        runtime.mkdir(parents=True)
        (runtime / "generated.py").write_text("# auto-generated\n")

        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def app(): pass\n")

        result = scan(str(tmp_path), ignore=[])
        filepaths = [f.filepath for f in result.files]

        assert not any(".mpga-runtime" in p for p in filepaths), (
            f".mpga-runtime files should be excluded, but found in: {filepaths}"
        )

    def test_scan_excludes_pycache_directory(self, tmp_path: Path):
        """scan() ignores .pyc files inside __pycache__."""
        cache = tmp_path / "src" / "__pycache__"
        cache.mkdir(parents=True)
        # .pyc files are not source files so won't match extensions anyway,
        # but a .py file accidentally in __pycache__ should also be excluded
        (cache / "main.cpython-311.py").write_text("# compiled stub\n")

        src = tmp_path / "src"
        (src / "main.py").write_text("def main(): pass\n")

        result = scan(str(tmp_path), ignore=[])
        filepaths = [f.filepath for f in result.files]

        assert not any("__pycache__" in p for p in filepaths), (
            f"__pycache__ files should be excluded, but found in: {filepaths}"
        )

    def test_scan_excludes_node_modules_directory(self, tmp_path: Path):
        """scan() ignores files inside node_modules."""
        nm = tmp_path / "node_modules" / "lodash"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {};\n")

        src = tmp_path / "src"
        src.mkdir()
        (src / "index.ts").write_text("export const x = 1;\n")

        result = scan(str(tmp_path), ignore=[])
        filepaths = [f.filepath for f in result.files]

        assert not any("node_modules" in p for p in filepaths), (
            f"node_modules files should be excluded, but found in: {filepaths}"
        )

    def test_scan_user_ignore_merges_with_defaults(self, tmp_path: Path):
        """User-supplied ignore list supplements DEFAULT_EXCLUDE_DIRS."""
        custom = tmp_path / "my-build"
        custom.mkdir()
        (custom / "output.py").write_text("# build output\n")

        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def main(): pass\n")

        result = scan(str(tmp_path), ignore=["my-build"])
        filepaths = [f.filepath for f in result.files]

        assert not any("my-build" in p for p in filepaths)
        assert any("main.py" in p for p in filepaths)
