"""Tests for mpga.core.scanner -- converted from scanner.test.ts."""

from pathlib import Path

from mpga.core.scanner import (
    FileInfo,
    ScanResult,
    count_lines,
    detect_language,
    detect_project_type,
    scan,
)

# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    def test_returns_other_for_unknown_extension(self):
        assert detect_language("file.xyz") == "other"

    def test_maps_ts_to_typescript(self):
        assert detect_language("src/index.ts") == "typescript"

    def test_maps_tsx_to_typescript(self):
        assert detect_language("App.tsx") == "typescript"

    def test_maps_js_to_javascript(self):
        assert detect_language("lib/utils.js") == "javascript"

    def test_maps_mjs_to_javascript(self):
        assert detect_language("module.mjs") == "javascript"

    def test_maps_py_to_python(self):
        assert detect_language("main.py") == "python"

    def test_maps_go_to_go(self):
        assert detect_language("cmd/server.go") == "go"

    def test_maps_rs_to_rust(self):
        assert detect_language("src/lib.rs") == "rust"

    def test_maps_sh_to_shell(self):
        assert detect_language("deploy.sh") == "shell"

    def test_maps_yaml_and_yml_to_yaml(self):
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("ci.yml") == "yaml"

    def test_is_case_insensitive_on_extension(self):
        assert detect_language("FILE.TS") == "typescript"

    def test_handles_files_with_no_extension(self):
        assert detect_language("Makefile") == "other"


# ---------------------------------------------------------------------------
# count_lines
# ---------------------------------------------------------------------------


class TestCountLines:
    def test_counts_lines_in_a_file(self, tmp_path: Path):
        fp = tmp_path / "test.txt"
        fp.write_text("line1\nline2\nline3\n")
        assert count_lines(str(fp)) == 3  # 3 lines (trailing newline does not add extra)

    def test_returns_1_for_a_single_line_file_with_no_newline(self, tmp_path: Path):
        fp = tmp_path / "single.txt"
        fp.write_text("hello")
        assert count_lines(str(fp)) == 1

    def test_returns_0_for_a_nonexistent_file(self, tmp_path: Path):
        assert count_lines(str(tmp_path / "nope.txt")) == 0

    def test_returns_0_for_an_empty_file(self, tmp_path: Path):
        fp = tmp_path / "empty.txt"
        fp.write_text("")
        assert count_lines(str(fp)) == 0  # empty file has 0 lines

    def test_returns_0_for_an_unreadable_file(self, tmp_path: Path):
        fp = tmp_path / "noperm.txt"
        fp.write_text("content")
        fp.chmod(0o000)
        try:
            assert count_lines(str(fp)) == 0
        finally:
            fp.chmod(0o644)  # restore for cleanup


# ---------------------------------------------------------------------------
# detect_project_type
# ---------------------------------------------------------------------------


def _make_scan_result(languages, file_paths=None):
    """Helper to build a ScanResult dataclass."""
    if file_paths is None:
        file_paths = []
    files = [
        FileInfo(filepath=fp, lines=10, language="other", size=100)
        for fp in file_paths
    ]
    return ScanResult(
        root="/tmp",
        files=files,
        total_files=len(file_paths),
        total_lines=len(file_paths) * 10,
        languages=languages,
        entry_points=[],
        top_level_dirs=[],
    )


class TestDetectProjectType:
    def test_returns_unknown_when_no_languages(self):
        assert detect_project_type(_make_scan_result({})) == "Unknown"

    def test_detects_next_js(self):
        result = _make_scan_result(
            {"typescript": {"files": 5, "lines": 500}},
            ["src/index.ts", "next.config.js"],
        )
        assert detect_project_type(result) == "Next.js"

    def test_detects_react(self):
        result = _make_scan_result(
            {"typescript": {"files": 5, "lines": 500}},
            ["src/App.tsx", "node_modules/react/index.js"],
        )
        assert detect_project_type(result) == "React"

    def test_detects_node_js_api_express(self):
        result = _make_scan_result(
            {"typescript": {"files": 3, "lines": 300}},
            ["src/server.ts", "node_modules/express/index.js"],
        )
        assert detect_project_type(result) == "Node.js API"

    def test_detects_plain_typescript(self):
        result = _make_scan_result(
            {"typescript": {"files": 3, "lines": 300}},
            ["src/index.ts"],
        )
        assert detect_project_type(result) == "TypeScript"

    def test_detects_django(self):
        result = _make_scan_result(
            {"python": {"files": 10, "lines": 1000}},
            ["manage.py", "myapp/django/settings.py"],
        )
        assert detect_project_type(result) == "Django"

    def test_detects_plain_python(self):
        result = _make_scan_result(
            {"python": {"files": 5, "lines": 500}},
            ["main.py"],
        )
        assert detect_project_type(result) == "Python"

    def test_detects_go(self):
        result = _make_scan_result(
            {"go": {"files": 5, "lines": 500}},
            ["cmd/main.go"],
        )
        assert detect_project_type(result) == "Go"

    def test_detects_rust(self):
        result = _make_scan_result(
            {"rust": {"files": 3, "lines": 300}},
            ["src/main.rs"],
        )
        assert detect_project_type(result) == "Rust"

    def test_detects_java(self):
        result = _make_scan_result(
            {"java": {"files": 10, "lines": 1000}},
            ["src/Main.java"],
        )
        assert detect_project_type(result) == "Java"


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


class TestScan:
    def test_scans_an_empty_directory(self, tmp_path: Path):
        result = scan(str(tmp_path), [])
        assert result.root == str(tmp_path.resolve())
        assert result.files == []
        assert result.total_files == 0
        assert result.total_lines == 0
        assert result.languages == {}

    def test_finds_files_and_computes_languages(self, tmp_path: Path):
        (tmp_path / "index.ts").write_text("const x = 1;\n")
        (tmp_path / "util.ts").write_text(
            "export function foo() {}\nexport function bar() {}\n"
        )
        (tmp_path / "style.css").write_text("body {}")  # not in glob

        result = scan(str(tmp_path), [])
        assert result.total_files == 2
        assert result.languages["typescript"]["files"] == 2
        assert all(f.language == "typescript" for f in result.files)

    def test_respects_ignore_patterns(self, tmp_path: Path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lib.ts").write_text("x")
        (tmp_path / "app.ts").write_text("y\n")

        result = scan(str(tmp_path), ["node_modules"])
        assert result.total_files == 1
        assert result.files[0].filepath == "app.ts"

    def test_detects_entry_points(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "index.ts").write_text("main")

        result = scan(str(tmp_path), [])
        assert "src/index.ts" in result.entry_points

    def test_lists_top_level_dirs_excluding_ignored_and_dotfiles(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "lib").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "node_modules").mkdir()

        result = scan(str(tmp_path), ["node_modules"])
        assert "src" in result.top_level_dirs
        assert "lib" in result.top_level_dirs
        assert ".git" not in result.top_level_dirs
        assert "node_modules" not in result.top_level_dirs

    def test_computes_file_size(self, tmp_path: Path):
        content = "hello world\n"
        (tmp_path / "hello.ts").write_text(content)

        result = scan(str(tmp_path), [])
        assert result.files[0].size == len(content.encode("utf-8"))

    def test_excludes_non_code_file_extensions(self, tmp_path: Path):
        (tmp_path / "readme.md").write_text("# Hello")
        (tmp_path / "style.css").write_text("body {}")
        (tmp_path / "data.csv").write_text("a,b")
        (tmp_path / "app.ts").write_text("x")

        result = scan(str(tmp_path), [])
        assert result.total_files == 1
        assert result.files[0].filepath == "app.ts"

    def test_deduplicates_entry_points(self, tmp_path: Path):
        (tmp_path / "index.ts").write_text("main")

        result = scan(str(tmp_path), [])
        index_count = result.entry_points.count("index.ts")
        assert index_count == 1
