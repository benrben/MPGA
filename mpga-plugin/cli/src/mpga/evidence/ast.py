from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from mpga.core.scanner import detect_language


@dataclass
class SymbolLocation:
    name: str
    type: Literal["function", "class", "method", "variable", "type"]
    start_line: int
    end_line: int


# Maximum number of lines to scan forward when finding the end of a code block.
MAX_BLOCK_SCAN_LINES = 200


# ---------------------------------------------------------------------------
# Regex-based symbol extraction (fast fallback for all languages)
# ---------------------------------------------------------------------------

@dataclass
class _SymbolPattern:
    re: re.Pattern[str]
    type: Literal["function", "class", "method", "variable", "type"]
    langs: list[str]


_PATTERNS: list[_SymbolPattern] = [
    # TypeScript/JavaScript
    _SymbolPattern(
        re=re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
        type="function",
        langs=["typescript", "javascript"],
    ),
    _SymbolPattern(
        re=re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)"),
        type="class",
        langs=["typescript", "javascript"],
    ),
    _SymbolPattern(
        re=re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
        type="function",
        langs=["typescript", "javascript"],
    ),
    _SymbolPattern(
        re=re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function"),
        type="function",
        langs=["typescript", "javascript"],
    ),
    _SymbolPattern(
        re=re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)"),
        type="variable",
        langs=["typescript", "javascript"],
    ),
    _SymbolPattern(
        re=re.compile(r"^(?:export\s+)?(?:type|interface)\s+(\w+)"),
        type="type",
        langs=["typescript", "javascript"],
    ),
    # Method patterns (inside class)
    _SymbolPattern(
        re=re.compile(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\w+\s*)?\{"),
        type="method",
        langs=["typescript", "javascript"],
    ),
    # Python
    _SymbolPattern(re=re.compile(r"^def\s+(\w+)"), type="function", langs=["python"]),
    _SymbolPattern(re=re.compile(r"^class\s+(\w+)"), type="class", langs=["python"]),
    _SymbolPattern(re=re.compile(r"^\s{4}def\s+(\w+)"), type="method", langs=["python"]),
    # Go
    _SymbolPattern(
        re=re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)"),
        type="function",
        langs=["go"],
    ),
    _SymbolPattern(re=re.compile(r"^type\s+(\w+)\s+struct"), type="class", langs=["go"]),
    _SymbolPattern(re=re.compile(r"^type\s+(\w+)\s+interface"), type="type", langs=["go"]),
    # Rust
    _SymbolPattern(
        re=re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)"),
        type="function",
        langs=["rust"],
    ),
    _SymbolPattern(re=re.compile(r"^(?:pub\s+)?struct\s+(\w+)"), type="class", langs=["rust"]),
    _SymbolPattern(re=re.compile(r"^(?:pub\s+)?trait\s+(\w+)"), type="type", langs=["rust"]),
    # Java/C#
    _SymbolPattern(
        re=re.compile(r"(?:public|private|protected|static|\s)+\w+\s+(\w+)\s*\("),
        type="function",
        langs=["java", "csharp"],
    ),
    _SymbolPattern(
        re=re.compile(r"(?:public|private|protected)?\s+(?:abstract\s+)?class\s+(\w+)"),
        type="class",
        langs=["java", "csharp"],
    ),
    _SymbolPattern(
        re=re.compile(r"(?:public\s+)?interface\s+(\w+)"),
        type="type",
        langs=["java", "csharp"],
    ),
]

# Keywords that should never be treated as symbol names
_KEYWORD_BLACKLIST = re.compile(r"^(if|for|while|switch|return|const|let|var)$")


def _extract_symbols_regex(content: str, language: str) -> list[SymbolLocation]:
    lines = content.split("\n")
    symbols: list[SymbolLocation] = []

    relevant_patterns = [p for p in _PATTERNS if language in p.langs]

    for i, line in enumerate(lines):
        for pat in relevant_patterns:
            m = pat.re.search(line)
            if m and m.group(1) and not _KEYWORD_BLACKLIST.match(m.group(1)):
                # Find end of block (simple heuristic: next same-indent line or end of file)
                end_line = i + 1
                indent_match = re.match(r"^(\s*)", line)
                indent = len(indent_match.group(1)) if indent_match else 0
                for j in range(i + 1, min(i + MAX_BLOCK_SCAN_LINES, len(lines))):
                    j_line = lines[j]
                    if j_line.strip() == "":
                        continue
                    j_indent_match = re.match(r"^(\s*)", j_line)
                    j_indent = len(j_indent_match.group(1)) if j_indent_match else 0
                    if j_indent <= indent and j_line.strip() and j > i + 1:
                        end_line = j - 1
                        break
                    end_line = j
                symbols.append(SymbolLocation(
                    name=m.group(1),
                    type=pat.type,
                    start_line=i + 1,
                    end_line=end_line + 1,
                ))
                break  # Only match the first pattern per line

    return symbols


_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}
_CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".env", ".css", ".md", ".mdx"}


def _extract_symbols_ast_python(content: str) -> list[SymbolLocation]:
    """Extract symbols from Python source using ast.parse(); falls back to regex on SyntaxError."""
    import ast as _ast

    try:
        tree = _ast.parse(content)
    except SyntaxError:
        return _extract_symbols_regex(content, "python")

    results: list[SymbolLocation] = []

    class _Visitor(_ast.NodeVisitor):
        def __init__(self) -> None:
            self._in_class = False

        def visit_ClassDef(self, node: _ast.ClassDef) -> None:
            results.append(SymbolLocation(
                name=node.name,
                type="class",
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            ))
            prev = self._in_class
            self._in_class = True
            self.generic_visit(node)
            self._in_class = prev

        def _visit_func(self, node: _ast.FunctionDef | _ast.AsyncFunctionDef) -> None:
            sym_type = "method" if self._in_class else "function"
            results.append(SymbolLocation(
                name=node.name,
                type=sym_type,  # type: ignore[arg-type]
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            ))
            # Don't recurse into nested functions by default
            prev = self._in_class
            self._in_class = False
            self.generic_visit(node)
            self._in_class = prev

        def visit_FunctionDef(self, node: _ast.FunctionDef) -> None:
            self._visit_func(node)

        def visit_AsyncFunctionDef(self, node: _ast.AsyncFunctionDef) -> None:
            self._visit_func(node)

    _Visitor().visit(tree)
    return results


def extract_symbols(filepath: str, project_root: str) -> list[SymbolLocation]:
    ext = Path(filepath).suffix.lower()
    if ext not in _SOURCE_EXTENSIONS:
        return []

    full_path = Path(project_root) / filepath
    if not full_path.exists():
        return []

    try:
        content = full_path.read_text(encoding="utf-8")
    except OSError:
        return []

    if ext == ".py":
        return _extract_symbols_ast_python(content)

    language = detect_language(filepath)
    return _extract_symbols_regex(content, language)


def find_symbol(
    filepath: str,
    symbol_name: str,
    project_root: str,
) -> SymbolLocation | None:
    symbols = extract_symbols(filepath, project_root)
    for s in symbols:
        if s.name == symbol_name:
            return s
    return None


def verify_range(
    filepath: str,
    start_line: int,
    end_line: int,
    symbol: str | None,
    project_root: str,
) -> bool:
    """Verify that a line range contains the expected symbol."""
    full_path = Path(project_root) / filepath
    if not full_path.exists():
        return False

    try:
        lines = full_path.read_text(encoding="utf-8").split("\n")
        range_content = "\n".join(lines[start_line - 1 : end_line])
        if not symbol:
            return True  # Range exists, no symbol check needed
        return symbol in range_content
    except OSError:
        return False
