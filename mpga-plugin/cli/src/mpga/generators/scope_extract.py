"""Scope extraction helpers — symbol, summary, framework, and annotation extraction.

Extracted from scope_md.py to keep module size manageable. This module
contains pure extraction functions that analyze file content to produce
structured data for scope documents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mpga.core.scanner import FileInfo


# ---------------------------------------------------------------------------
# Data classes for extraction results
# ---------------------------------------------------------------------------

@dataclass
class ExportedSymbol:
    symbol: str
    filepath: str
    kind: str


@dataclass
class ExportDescription:
    symbol: str
    filepath: str
    kind: str
    description: str


@dataclass
class RuleConstraint:
    filepath: str
    symbol: str
    annotation: str


@dataclass
class ModuleSummary:
    filepath: str
    summary: str


# ---------------------------------------------------------------------------
# Known frameworks/libraries to detect from imports
# ---------------------------------------------------------------------------

FRAMEWORK_MAP: dict[str, str] = {
    "express": "Express",
    "fastify": "Fastify",
    "hono": "Hono",
    "koa": "Koa",
    "react": "React",
    "react-dom": "React",
    "vue": "Vue",
    "svelte": "Svelte",
    "next": "Next.js",
    "nuxt": "Nuxt",
    "angular": "Angular",
    "commander": "Commander",
    "yargs": "Yargs",
    "inquirer": "Inquirer",
    "zod": "Zod",
    "joi": "Joi",
    "ajv": "Ajv",
    "prisma": "Prisma",
    "drizzle": "Drizzle",
    "typeorm": "TypeORM",
    "sequelize": "Sequelize",
    "vitest": "Vitest",
    "jest": "Jest",
    "mocha": "Mocha",
    "tailwindcss": "Tailwind CSS",
    "styled-components": "styled-components",
    "graphql": "GraphQL",
    "trpc": "tRPC",
    "axios": "Axios",
    "mongoose": "Mongoose",
    "knex": "Knex",
    "flask": "Flask",
    "django": "Django",
    "fastapi": "FastAPI",
}


# ---------------------------------------------------------------------------
# Extract exported symbols with their kind
# ---------------------------------------------------------------------------

def _extract_exports(filepath: str, content: str) -> list[ExportedSymbol]:
    exports: list[ExportedSymbol] = []
    seen: set[str] = set()

    # TypeScript/JS exports
    ts_re = re.compile(
        r"export\s+(?:default\s+)?(?:async\s+)?"
        r"(function|class|const|let|var|type|interface|enum)\s+(\w+)"
    )
    for m in ts_re.finditer(content):
        kind = "variable" if m.group(1) in ("let", "var") else m.group(1)
        symbol = m.group(2)
        if symbol not in seen:
            seen.add(symbol)
            exports.append(ExportedSymbol(symbol=symbol, filepath=filepath, kind=kind))

    # Python def/class at module level
    py_re = re.compile(r"^(def|class)\s+(\w+)", re.MULTILINE)
    for m in py_re.finditer(content):
        symbol = m.group(2)
        if symbol not in seen:
            seen.add(symbol)
            exports.append(
                ExportedSymbol(symbol=symbol, filepath=filepath, kind=m.group(1))
            )

    # Go func
    go_re = re.compile(r"^func\s+(\w+)", re.MULTILINE)
    for m in go_re.finditer(content):
        symbol = m.group(1)
        if symbol not in seen:
            seen.add(symbol)
            exports.append(
                ExportedSymbol(symbol=symbol, filepath=filepath, kind="function")
            )

    return exports


# ---------------------------------------------------------------------------
# Module summary extraction
# ---------------------------------------------------------------------------

def extract_module_summary(content: str) -> str | None:
    """Extracts the leading module-level comment (JSDoc block or consecutive // lines)
    from the top of a file's content, before any imports or code.

    Args:
        content: The full text content of a source file.

    Returns:
        The extracted summary text with comment markers stripped, or None if no
        leading comment is found.
    """
    # Try JSDoc block comment at the top (before any import/code)
    jsdoc_match = re.match(r"^\s*/\*\*([\s\S]*?)\*/", content)
    if jsdoc_match:
        before_comment = content[: jsdoc_match.start()].strip()
        if before_comment == "":
            cleaned = " ".join(
                line
                for line in (
                    re.sub(r"^\s*\*\s?", "", raw_line).strip()
                    for raw_line in jsdoc_match.group(1).split("\n")
                )
                if not line.startswith("@") and line
            ).strip()
            if cleaned:
                return cleaned

    # Try leading // comment block
    comment_lines: list[str] = []
    for line in content.split("\n"):
        trimmed = line.strip()
        if trimmed == "" and not comment_lines:
            continue
        if trimmed.startswith("//"):
            comment_lines.append(re.sub(r"^//\s?", "", trimmed).strip())
        else:
            break
    if comment_lines:
        joined = " ".join(ln for ln in comment_lines if ln).strip()
        if joined:
            return joined

    return None


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

def detect_frameworks(content: str) -> list[str]:
    """Detect known frameworks/libraries from import statements."""
    found: set[str] = set()
    import_re = re.compile(r"""(?:from|import|require)\s*\(?\s*['"]([^'"./][^'"]*)['"]""")
    for m in import_re.finditer(content):
        raw = m.group(1)
        # Get the package name (handle scoped packages like @foo/bar)
        if raw.startswith("@"):
            pkg = "/".join(raw.split("/")[:2])
        else:
            pkg = raw.split("/")[0]
        framework = FRAMEWORK_MAP.get(pkg)
        if framework:
            found.add(framework)
    return list(found)


# ---------------------------------------------------------------------------
# JSDoc description extraction for exported symbols
# ---------------------------------------------------------------------------

def extract_jsdoc_for_export(content: str, symbol_name: str) -> str | None:
    """Extract JSDoc description for a specific exported symbol."""
    escaped = re.escape(symbol_name)
    pattern = (
        r"/\*\*([\s\S]*?)\*/\s*export\s+(?:default\s+)?(?:async\s+)?"
        r"(?:function|class|const|let|var|type|interface|enum)\s+"
        + escaped
        + r"\b"
    )
    match = re.search(pattern, content)
    if not match:
        return None

    lines = [
        line
        for line in (
            re.sub(r"^\s*\*\s?", "", raw_line).strip()
            for raw_line in match.group(1).split("\n")
        )
        if line and not line.startswith("@")
    ]

    return " ".join(lines).strip() if lines else None


# ---------------------------------------------------------------------------
# Constraint annotations
# ---------------------------------------------------------------------------

def extract_annotations(content: str, symbol_name: str) -> list[str]:
    """Extract constraint annotations (@throws, @deprecated, etc.) from JSDoc."""
    escaped = re.escape(symbol_name)
    pattern = (
        r"/\*\*([\s\S]*?)\*/\s*export\s+(?:default\s+)?(?:async\s+)?"
        r"(?:function|class|const|let|var|type|interface|enum)\s+"
        + escaped
        + r"\b"
    )
    match = re.search(pattern, content)
    if not match:
        return []

    annotations: list[str] = []
    for raw_line in match.group(1).split("\n"):
        line = re.sub(r"^\s*\*\s?", "", raw_line).strip()
        if line.startswith("@throws") or line.startswith("@deprecated"):
            annotations.append(line)
    return annotations


# ---------------------------------------------------------------------------
# Entry point detection
# ---------------------------------------------------------------------------

def _detect_entry_points(files: list[FileInfo]) -> list[str]:
    """Detect entry-point files within a scope."""
    entry_patterns = [
        re.compile(r"(?:^|/)index\.\w+$"),
        re.compile(r"(?:^|/)main\.\w+$"),
        re.compile(r"(?:^|/)app\.\w+$"),
        re.compile(r"(?:^|/)server\.\w+$"),
        re.compile(r"(?:^|/)cli\.\w+$"),
        re.compile(r"(?:^|/)mod\.\w+$"),
        re.compile(r"(?:^|/)lib\.\w+$"),
        re.compile(r"(?:^|/)__init__\.py$"),
    ]
    entries: list[str] = []
    for file in files:
        if any(p.search(file.filepath) for p in entry_patterns):
            entries.append(file.filepath)
    # If no conventional entry points, pick the largest file (likely the main one)
    if not entries and files:
        sorted_files = sorted(files, key=lambda f: f.lines, reverse=True)
        entries.append(sorted_files[0].filepath)
    return entries


# ---------------------------------------------------------------------------
# Scope name resolution
# ---------------------------------------------------------------------------

def get_scope_name(filepath: str, scope_depth: int | str) -> str:
    """Determines the scope name for a file based on its path.

    With ``scope_depth='auto'``, finds the deepest "source-like" directory
    (src/, lib/, app/, etc.) and uses its immediate subdirectory as the scope
    name.  With a numeric depth, uses that many leading path segments joined
    by '/'.

    Args:
        filepath: Relative file path (e.g., "src/evidence/parser.ts").
        scope_depth: Either ``'auto'`` for intelligent scope detection, or a
            number specifying how many path segments to use.

    Returns:
        The scope name string (e.g., "evidence"), or "root" for top-level files.
    """
    parts = filepath.split("/")
    if len(parts) <= 1:
        return "root"

    if scope_depth == "auto":
        # Find the deepest src-like directory and group by subdirectories under it
        src_like = ["src", "lib", "app", "pkg", "internal", "cmd"]
        src_idx = -1
        for i, part in enumerate(parts):
            if part in src_like:
                src_idx = i

        if src_idx >= 0 and src_idx + 1 < len(parts) - 1:
            # Use the subdirectory under the src-like dir as the scope name
            # e.g. mpga-plugin/cli/src/evidence/parser.ts -> "evidence"
            return parts[src_idx + 1]

        # No src-like dir found -- use the top-level directory
        return parts[0]

    # Numeric depth: use that many path segments
    depth = min(int(scope_depth), len(parts) - 1)
    return "/".join(parts[:depth])
