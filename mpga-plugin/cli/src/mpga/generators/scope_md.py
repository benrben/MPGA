from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from mpga.core.config import MpgaConfig
from mpga.core.logger import log
from mpga.core.scanner import FileInfo, ScanResult
from mpga.generators.graph_md import GraphData

_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"}


def _choose_evidence_form(
    filepath: str,
    symbol: str | None,
    project_root: str,
    fallback_lines: tuple[int, int] | None = None,
) -> str:
    """Return the canonical evidence form for a file+symbol pair.

    Source files with a known symbol use ``file#symbol:lineHint``.
    Config/doc files use ``file:start-end`` (structural, range-based).
    Falls back to ``file`` alone when no line information is available.
    """
    ext = Path(filepath).suffix.lower()
    if ext in _SOURCE_EXTENSIONS and symbol:
        try:
            from mpga.evidence.ast import find_symbol as _find_symbol

            loc = _find_symbol(filepath, symbol, project_root)
            if loc:
                return f"[E] {filepath}#{symbol}:{loc.start_line}"
        except Exception as exc:
            log.dim(f"AST lookup failed for {filepath}#{symbol}: {exc}")
    if fallback_lines:
        return f"[E] {filepath}:{fallback_lines[0]}-{fallback_lines[1]}"
    return f"[E] `{filepath}`"

# Pre-compiled regex for detecting inter-scope imports inside group_into_scopes loop.
_SCOPE_IMPORT_RE = re.compile(r"""(?:from|import)\s+['"]([^'"]+)['"]""")

# Maximum number of evidence index entries to display in a scope document.
MAX_EVIDENCE_INDEX_ENTRIES = 40
# Maximum number of files to list in the Files section of a scope document.
MAX_FILE_LIST_ENTRIES = 30


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


@dataclass
class ScopeInfo:
    """Describes a single scope (logical grouping of files by directory structure),
    including its files, exports, dependency relationships, and extracted metadata."""

    # Scope name, derived from directory structure (e.g., "evidence", "commands")
    name: str = ""
    # All files belonging to this scope
    files: list[FileInfo] = field(default_factory=list)
    # Exported symbols extracted from scope files
    exports: list[ExportedSymbol] = field(default_factory=list)
    # Names of other scopes that this scope depends on
    dependencies: list[str] = field(default_factory=list)
    # Names of other scopes that depend on this scope
    reverse_deps: list[str] = field(default_factory=list)
    # Conventional entry point files detected within this scope (e.g., index.ts, main.ts)
    entry_points: list[str] = field(default_factory=list)
    # Names of all scopes in the project, used for sibling navigation
    all_scope_names: list[str] = field(default_factory=list)
    # Module-level comments extracted from entry point files
    module_summaries: list[ModuleSummary] = field(default_factory=list)
    # Frameworks/libraries detected from imports
    detected_frameworks: list[str] = field(default_factory=list)
    # Exported functions with their JSDoc descriptions
    export_descriptions: list[ExportDescription] = field(default_factory=list)
    # JSDoc annotations: @throws, @deprecated, etc.
    rules_and_constraints: list[RuleConstraint] = field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Scope grouping
# ---------------------------------------------------------------------------

def group_into_scopes(
    scan_result: ScanResult,
    graph: GraphData | None = None,
    config: MpgaConfig | None = None,
) -> list[ScopeInfo]:
    """Groups scanned files into logical scopes by directory structure, then enriches
    each scope with exported symbols, inter-scope dependencies, entry points,
    module summaries, framework detection, and JSDoc metadata.

    Args:
        scan_result: The result of a project scan containing the root path and
            file list.
        graph: Optional dependency graph data used to compute reverse dependencies.
        config: Optional MPGA config providing scope depth settings.

    Returns:
        A list of :class:`ScopeInfo` objects, one per detected scope.
    """
    root = scan_result.root
    files = scan_result.files
    groups: dict[str, list[FileInfo]] = {}
    scope_depth: int | str = "auto"
    if config is not None:
        scope_depth = config.scopes.scope_depth

    for file in files:
        group = get_scope_name(file.filepath, scope_depth)
        if group not in groups:
            groups[group] = []
        groups[group].append(file)

    all_scope_names = list(groups.keys())

    # Build reverse dependency map from graph data
    reverse_deps_map: dict[str, set[str]] = {}
    if graph is not None:
        for dep in graph.dependencies:
            if dep.to not in reverse_deps_map:
                reverse_deps_map[dep.to] = set()
            reverse_deps_map[dep.to].add(dep.from_)

    scopes: list[ScopeInfo] = []
    for name, group_files in groups.items():
        all_exports: list[ExportedSymbol] = []
        deps: set[str] = set()
        module_summaries: list[ModuleSummary] = []
        all_frameworks: list[str] = []
        export_descriptions: list[ExportDescription] = []
        rules_and_constraints: list[RuleConstraint] = []

        # Compute entry points first so we can extract summaries from them
        entry_points = _detect_entry_points(group_files)
        entry_point_set = set(entry_points)

        for file in group_files:
            full_path = Path(root) / file.filepath
            if not full_path.exists():
                continue
            try:
                content = full_path.read_text(encoding="utf-8")
            except Exception:
                continue

            file_exports = _extract_exports(file.filepath, content)
            all_exports.extend(file_exports)

            # Extract module summary from entry point files
            if file.filepath in entry_point_set:
                summary = extract_module_summary(content)
                if summary:
                    module_summaries.append(
                        ModuleSummary(filepath=file.filepath, summary=summary)
                    )

            # Detect frameworks
            all_frameworks.extend(detect_frameworks(content))

            # Extract JSDoc descriptions and annotations for exports
            for exp in file_exports:
                desc = extract_jsdoc_for_export(content, exp.symbol)
                if desc:
                    export_descriptions.append(
                        ExportDescription(
                            symbol=exp.symbol,
                            filepath=exp.filepath,
                            kind=exp.kind,
                            description=desc,
                        )
                    )
                annotations = extract_annotations(content, exp.symbol)
                for ann in annotations:
                    rules_and_constraints.append(
                        RuleConstraint(
                            filepath=file.filepath,
                            symbol=exp.symbol,
                            annotation=ann,
                        )
                    )

            # Detect inter-scope dependencies
            for m in _SCOPE_IMPORT_RE.finditer(content):
                imp = m.group(1)
                if not imp.startswith("."):
                    continue
                resolved = (
                    Path(root) / Path(file.filepath).parent / imp
                ).resolve()
                try:
                    rel = str(resolved.relative_to(Path(root).resolve()))
                except ValueError:
                    continue
                imp_group = get_scope_name(rel, scope_depth)
                if imp_group != name and imp_group in groups:
                    deps.add(imp_group)

        reverse_deps = (
            list(reverse_deps_map[name]) if name in reverse_deps_map else []
        )

        scopes.append(
            ScopeInfo(
                name=name,
                files=group_files,
                exports=all_exports,
                dependencies=list(deps),
                reverse_deps=reverse_deps,
                entry_points=entry_points,
                all_scope_names=all_scope_names,
                module_summaries=module_summaries,
                detected_frameworks=list(set(all_frameworks)),
                export_descriptions=export_descriptions,
                rules_and_constraints=rules_and_constraints,
            )
        )

    return scopes


# ---------------------------------------------------------------------------
# Scope markdown rendering
# ---------------------------------------------------------------------------

def render_scope_md(scope: ScopeInfo, project_root: str) -> str:
    """Renders a complete scope markdown document from a ScopeInfo object, including
    summary, entry points, context, relationships, evidence index, and file listing.

    Args:
        scope: The ScopeInfo to render into markdown.
        project_root: The project root path used for symbol resolution.

    Returns:
        The full markdown string for the scope document.
    """
    now = datetime.now(UTC).isoformat().split("T")[0]
    lines: list[str] = []

    # -- Summary --
    lines.append(f"# Scope: {scope.name}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("- **Health:** [Unknown] — not yet verified")
    total_lines = sum(f.lines for f in scope.files)
    lines.append(
        f"The **{scope.name}** module \u2014 TREMENDOUS \u2014"
        f" {len(scope.files)} files,"
        f" {total_lines:,} lines of the finest code you've ever seen."
        " Believe me."
    )
    lines.append("")
    if scope.module_summaries:
        for ms in scope.module_summaries:
            lines.append(f"{ms.summary}")
        lines.append("")
    else:
        lines.append(
            "<!-- TODO: Tell the people what this GREAT module does."
            " What's in, what's out. Keep it simple. MPGA! -->"
        )
        lines.append("")

    # -- Where to start in code --
    lines.append("## Where to start in code")
    lines.append("")
    if scope.entry_points:
        lines.append(
            "These are your MAIN entry points"
            " \u2014 the best, the most important. Open them FIRST:"
        )
        lines.append("")
        for ep in scope.entry_points:
            lines.append(f"- {_choose_evidence_form(ep, None, project_root)}")
    else:
        lines.append(
            "- <!-- TODO: Find the main entry points."
            " The best ones. The ones everybody should be reading. -->"
        )
    lines.append("")

    # -- Context / stack / skills --
    lines.append("## Context / stack / skills")
    lines.append("")
    lang_set = {f.language for f in scope.files}
    langs = [lang for lang in lang_set if lang != "other"]
    if langs:
        lines.append(f"- **Languages:** {', '.join(langs)}")
    symbol_kinds = {e.kind for e in scope.exports}
    if symbol_kinds:
        lines.append(f"- **Symbol types:** {', '.join(symbol_kinds)}")
    if scope.detected_frameworks:
        lines.append(f"- **Frameworks:** {', '.join(scope.detected_frameworks)}")
    else:
        lines.append("- <!-- TODO: List the frameworks. We use only the BEST. -->")
    lines.append("")

    # -- Who and what triggers it --
    lines.append("## Who and what triggers it")
    lines.append("")
    lines.append(
        "<!-- TODO: Who triggers this?"
        " A lot of very important callers, believe me. Find them. -->"
    )
    lines.append("")
    if scope.reverse_deps:
        lines.append(
            "**Called by these GREAT scopes (they need us, tremendously):**"
        )
        lines.append("")
        for rd in scope.reverse_deps:
            lines.append(f"- \u2190 {rd}")
        lines.append("")

    # -- What happens --
    lines.append("## What happens")
    lines.append("")
    if scope.export_descriptions:
        for ed in scope.export_descriptions:
            ev = _choose_evidence_form(ed.filepath, ed.symbol, project_root)
            lines.append(
                f"- **{ed.symbol}** ({ed.kind})"
                f" \u2014 {ed.description} {ev}"
            )
        lines.append("")
    else:
        lines.append(
            "<!-- TODO: What happens here? Inputs, steps, outputs."
            " Keep it simple. Even Sleepy Copilot could understand. -->"
        )
        lines.append("")

    # -- Rules and edge cases --
    lines.append("## Rules and edge cases")
    lines.append("")
    if scope.rules_and_constraints:
        for rc in scope.rules_and_constraints:
            lines.append(
                f"- `{rc.symbol}`: {rc.annotation} [E] `{rc.filepath}`"
            )
        lines.append("")
    else:
        lines.append(
            "<!-- TODO: The guardrails. Validation, permissions, error handling"
            " \u2014 everything that keeps this code GREAT. -->"
        )
        lines.append("")

    # -- Concrete examples --
    lines.append("## Concrete examples")
    lines.append("")
    lines.append(
        '<!-- TODO: REAL examples. "When X happens, Y happens."'
        " Simple. Powerful. Like a deal. -->"
    )
    lines.append("")

    # -- UI --
    lines.append("## UI")
    lines.append("")
    lines.append(
        "<!-- TODO: Screens, flows, the beautiful UI."
        " No UI? Cut this section. We don't keep dead weight. -->"
    )
    lines.append("")

    # -- Navigation --
    lines.append("## Navigation")
    lines.append("")
    siblings = [s for s in scope.all_scope_names if s != scope.name]
    if siblings:
        lines.append("**Sibling scopes:**")
        lines.append("")
        for s in siblings:
            lines.append(f"- [{s}](./{s}.md)")
        lines.append("")
    lines.append("**Parent:** [INDEX.md](../INDEX.md)")
    lines.append("")

    # -- Relationships to other areas --
    lines.append("## Relationships")
    lines.append("")
    if scope.dependencies:
        lines.append("**Depends on:**")
        lines.append("")
        for dep in scope.dependencies:
            lines.append(f"- \u2192 [{dep}](./{dep}.md)")
        lines.append("")
    if scope.reverse_deps:
        lines.append("**Depended on by:**")
        lines.append("")
        for rd in scope.reverse_deps:
            lines.append(f"- \u2190 [{rd}](./{rd}.md)")
        lines.append("")
    if not scope.dependencies and not scope.reverse_deps:
        lines.append(
            "- (no dependencies \u2014 TOTALLY INDEPENDENT. Very strong.)"
        )
        lines.append("")
    lines.append(
        "<!-- TODO: What deals does this scope make with other scopes?"
        " Document them. -->"
    )
    lines.append("")

    # -- Diagram --
    lines.append("## Diagram")
    lines.append("")
    if scope.dependencies or scope.reverse_deps:
        lines.append("```mermaid")
        lines.append("graph LR")

        def safe_name(n: str) -> str:
            return re.sub(r"[^a-zA-Z0-9_]", "_", n)

        for dep in scope.dependencies:
            lines.append(f"    {safe_name(scope.name)} --> {safe_name(dep)}")
        for rd in scope.reverse_deps:
            lines.append(f"    {safe_name(rd)} --> {safe_name(scope.name)}")
        lines.append("```")
    else:
        lines.append(
            "<!-- TODO: A BEAUTIFUL diagram."
            " Flow, sequence, boundaries. Make it GREAT. -->"
        )
    lines.append("")

    # -- Traces --
    lines.append("## Traces")
    lines.append("")
    lines.append(
        "<!-- TODO: Step-by-step traces."
        " Follow the code like a WINNER follows a deal. Use this table:"
    )
    lines.append("")
    lines.append("| Step | Layer | What happens | Evidence |")
    lines.append("|------|-------|-------------|----------|")
    lines.append("| 1 | (layer) | (description) | [E] file:line |")
    lines.append("-->")
    lines.append("")

    # -- Evidence index --
    lines.append("## Evidence index")
    lines.append("")
    if scope.exports:
        lines.append("| Claim | Evidence |")
        lines.append("|-------|----------|")
        for exp in scope.exports[:MAX_EVIDENCE_INDEX_ENTRIES]:
            ev = _choose_evidence_form(
                exp.filepath, exp.symbol, project_root,
                fallback_lines=(1, 1),
            )
            lines.append(f"| `{exp.symbol}` ({exp.kind}) | {ev} |")
        if len(scope.exports) > MAX_EVIDENCE_INDEX_ENTRIES:
            lines.append(
                f"| ... | {len(scope.exports) - MAX_EVIDENCE_INDEX_ENTRIES}"
                " more symbols |"
            )
    else:
        lines.append(
            "- (no exports detected"
            " \u2014 working behind the scenes. Very mysterious.)"
        )
    lines.append("")

    # -- Files --
    lines.append("## Files")
    lines.append("")
    for file in scope.files[:MAX_FILE_LIST_ENTRIES]:
        lines.append(
            f"- `{file.filepath}` ({file.lines} lines, {file.language})"
        )
    if len(scope.files) > MAX_FILE_LIST_ENTRIES:
        lines.append(
            f"- ... and {len(scope.files) - MAX_FILE_LIST_ENTRIES} more files"
        )
    lines.append("")

    # -- Deeper splits --
    lines.append("## Deeper splits")
    lines.append("")
    lines.append(
        "<!-- TODO: Too big? Split it. Make each piece LEAN and GREAT. -->"
    )
    lines.append("")

    # -- Confidence and notes --
    lines.append("## Confidence and notes")
    lines.append("")
    lines.append(
        "- **Confidence:** LOW (for now)"
        " \u2014 auto-generated, not yet verified."
        " But it's going to be PERFECT."
    )
    lines.append(f"- **Evidence coverage:** 0/{len(scope.exports)} verified")
    lines.append(f"- **Last verified:** {now}")
    lines.append("- **Drift risk:** unknown")
    lines.append(
        "- <!-- TODO: Note anything unknown or ambiguous."
        " We don't hide problems \u2014 we FIX them. -->"
    )
    lines.append("")

    # -- Change history --
    lines.append("## Change history")
    lines.append("")
    lines.append(
        f"- {now}: Initial scope generation via `mpga sync`"
        " \u2014 Making this scope GREAT!"
    )

    return "\n".join(lines)
