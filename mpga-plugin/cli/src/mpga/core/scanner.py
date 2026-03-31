from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

LANGUAGE_MAP: dict[str, str] = {
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "py": "python",
    "go": "go",
    "rs": "rust",
    "java": "java",
    "cs": "csharp",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "sh": "shell",
    "bash": "shell",
    "sql": "sql",
    "md": "markdown",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
}

SOURCE_EXTENSIONS = {
    "ts", "tsx", "js", "jsx", "mjs", "cjs",
    "py", "go", "rs", "java", "cs", "rb", "php", "swift", "kt", "sh", "sql",
}

SHALLOW_SCAN_MAX_DEPTH = 12

# Directories that are always excluded from scanning regardless of user config.
# These contain generated/installed files that inflate metrics and slow down sync.
DEFAULT_EXCLUDE_DIRS: frozenset[str] = frozenset({
    ".venv",
    "venv",
    ".env",
    ".mpga-runtime",
    "__pycache__",
    "node_modules",
    ".git",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "eggs",
    ".eggs",
    "htmlcov",
    ".coverage",
})

ENTRY_PATTERNS = [
    "src/index.*",
    "src/main.*",
    "index.*",
    "main.*",
    "app.*",
    "server.*",
    "cmd/main.*",
]


@dataclass
class FileInfo:
    filepath: str  # relative to project root
    lines: int
    language: str
    size: int


@dataclass
class ScanResult:
    root: str
    files: list[FileInfo] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, dict[str, int]] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)
    top_level_dirs: list[str] = field(default_factory=list)


def detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix.lstrip(".").lower()
    return LANGUAGE_MAP.get(ext, "other")


def count_lines(filepath: str | Path) -> int:
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        return content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    except OSError:
        return 0


def _should_ignore(rel_path: str, ignore_patterns: list[str]) -> bool:
    parts = Path(rel_path).parts
    for pattern in ignore_patterns:
        # Match any path component
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
        # Match the full relative path
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if fnmatch.fnmatch(rel_path, f"**/{pattern}/**"):
            return True
    return False


def scan(project_root: str | Path, ignore: list[str], deep: bool = False) -> ScanResult:
    root = Path(project_root).resolve()
    max_depth = float("inf") if deep else SHALLOW_SCAN_MAX_DEPTH
    files: list[FileInfo] = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        depth = len(rel_dir.parts) if str(rel_dir) != "." else 0

        if depth >= max_depth:
            dirnames.clear()
            continue

        # Prune ignored directories — always skip DEFAULT_EXCLUDE_DIRS plus user ignore list
        dirnames[:] = [
            d for d in dirnames
            if d not in DEFAULT_EXCLUDE_DIRS
            and not _should_ignore(str(rel_dir / d), ignore)
        ]

        for filename in filenames:
            ext = Path(filename).suffix.lstrip(".").lower()
            if ext not in SOURCE_EXTENSIONS:
                continue
            rel_path = str(rel_dir / filename) if str(rel_dir) != "." else filename
            if _should_ignore(rel_path, ignore):
                continue
            abs_path = Path(dirpath) / filename
            lines = count_lines(abs_path)
            language = detect_language(filename)
            try:
                size = abs_path.stat().st_size
            except OSError:
                size = 0
            files.append(FileInfo(filepath=rel_path, lines=lines, language=language, size=size))

    languages: dict[str, dict[str, int]] = {}
    for f in files:
        if f.language not in languages:
            languages[f.language] = {"files": 0, "lines": 0}
        languages[f.language]["files"] += 1
        languages[f.language]["lines"] += f.lines

    total_lines = sum(f.lines for f in files)

    # Detect entry points
    entry_points: list[str] = []
    for pattern in ENTRY_PATTERNS:
        for f in files:
            if fnmatch.fnmatch(f.filepath, pattern):
                if f.filepath not in entry_points:
                    entry_points.append(f.filepath)

    # Top-level dirs
    top_level_dirs: list[str] = []
    if root.exists():
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and not entry.name.startswith(".") and entry.name not in ignore:
                top_level_dirs.append(entry.name)

    return ScanResult(
        root=str(root),
        files=files,
        total_files=len(files),
        total_lines=total_lines,
        languages=languages,
        entry_points=entry_points,
        top_level_dirs=top_level_dirs,
    )


def _is_cli_project(result: ScanResult, project_root: str | Path | None = None) -> bool:
    """Return True when the project has CLI markers (pyproject.toml scripts, cli.py, Click/Typer)."""
    def has_file(pattern: str) -> bool:
        return any(pattern in f.filepath for f in result.files)

    # 1. pyproject.toml [project.scripts] — strongest CLI signal
    if project_root is not None:
        pyproject = Path(project_root) / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8", errors="replace")
            if "[project.scripts]" in content:
                return True

    # 2. Presence of a cli.py file
    if has_file("cli.py"):
        return True

    # 3. Click or Typer imports in any source file
    for file_info in result.files:
        if file_info.language != "python":
            continue
        if project_root is not None:
            abs_path = Path(project_root) / file_info.filepath
        else:
            abs_path = Path(file_info.filepath)
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
            if "import click" in source or "from click" in source or "import typer" in source:
                return True
        except OSError:
            continue

    return False


def detect_project_type(result: ScanResult, project_root: str | Path | None = None) -> str:
    """Detect the project type from the scan result.

    CLI markers (pyproject.toml [project.scripts], cli.py, Click/Typer imports)
    take priority over web-framework detection to avoid false FastAPI/Flask labels
    on projects that happen to have a small web server alongside their main CLI.
    """
    langs = result.languages

    def has_file(pattern: str) -> bool:
        return any(pattern in f.filepath for f in result.files)

    if "typescript" in langs and has_file("next.config"):
        return "Next.js"
    if "typescript" in langs and has_file("react"):
        return "React"
    if "typescript" in langs and (has_file("express") or has_file("fastify") or has_file("koa")):
        return "Node.js API"
    if "typescript" in langs:
        return "TypeScript"

    if "python" in langs:
        # CLI check must happen before framework detection
        if _is_cli_project(result, project_root):
            return "CLI"
        if has_file("django"):
            return "Django"
        if has_file("fastapi"):
            return "FastAPI"
        if has_file("flask"):
            return "Flask"
        return "Python"

    if "go" in langs:
        return "Go"
    if "rust" in langs:
        return "Rust"
    if "java" in langs:
        return "Java"
    return "Unknown"
