from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from mpga.core.config import MpgaConfig
from mpga.core.scanner import ScanResult

# Maximum number of orphan files to include in the graph output.
MAX_ORPHAN_FILES = 10
# Maximum number of dependencies to render in the Mermaid diagram.
MAX_MERMAID_DEPENDENCIES = 30


@dataclass
class Dependency:
    from_: str
    to: str


@dataclass
class GraphData:
    dependencies: list[Dependency] = field(default_factory=list)
    circular: list[tuple[str, str]] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)


def _extract_imports(
    filepath: str, content: str, project_root: str
) -> list[str]:
    """Extract imports from a file using regex (fast, no AST needed for basic graph)."""
    imports: list[str] = []

    # TypeScript/JS: import ... from '...' or require('...')
    import_re = re.compile(
        r"""(?:import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))"""
    )
    for m in import_re.finditer(content):
        dep = m.group(1) if m.group(1) is not None else m.group(2)
        if dep and dep.startswith("."):
            # Relative import -- resolve to a module name
            resolved = (
                Path(project_root) / Path(filepath).parent / dep
            ).resolve()
            rel = str(resolved.relative_to(Path(project_root).resolve()))
            imports.append(rel)

    # Python: from . import or import
    py_import_re = re.compile(
        r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
    )
    for m in py_import_re.finditer(content):
        dep = m.group(1) if m.group(1) is not None else m.group(2)
        if dep:
            imports.append(dep)

    return imports


def _get_module_name(
    filepath: str, scope_depth: int | str = "auto"
) -> str:
    """Resolve a filepath to its scope/module name using the same logic as group_into_scopes."""
    parts = filepath.split("/")
    if len(parts) <= 1:
        return Path(filepath).stem

    if scope_depth == "auto":
        src_like = ["src", "lib", "app", "pkg", "internal", "cmd"]
        src_idx = -1
        for i, part in enumerate(parts):
            if part in src_like:
                src_idx = i
        if src_idx >= 0 and src_idx + 1 < len(parts) - 1:
            return parts[src_idx + 1]
        return parts[0]

    depth = min(int(scope_depth), len(parts) - 1)
    return "/".join(parts[:depth])


def build_graph(
    scan_result: ScanResult, config: MpgaConfig | None = None
) -> GraphData:
    root = scan_result.root
    files = scan_result.files
    scope_depth: int | str = "auto"
    if config is not None:
        scope_depth = config.scopes.scope_depth

    module_deps: dict[str, set[str]] = {}
    modules: set[str] = set()

    for file in files:
        mod = _get_module_name(file.filepath, scope_depth)
        modules.add(mod)
        if mod not in module_deps:
            module_deps[mod] = set()

        full_path = Path(root) / file.filepath
        if not full_path.exists():
            continue

        try:
            content = full_path.read_text(encoding="utf-8")
        except Exception:
            continue

        file_imports = _extract_imports(file.filepath, content, root)
        for imp in file_imports:
            imp_mod = _get_module_name(imp, scope_depth)
            if imp_mod and imp_mod != mod:
                module_deps[mod].add(imp_mod)

    # Build dependency list
    dependencies: list[Dependency] = []
    for from_mod, tos in module_deps.items():
        for to_mod in tos:
            if to_mod in modules:
                dependencies.append(Dependency(from_=from_mod, to=to_mod))

    # Detect circular deps (simple check)
    circular: list[tuple[str, str]] = []
    for dep in dependencies:
        reverse = any(
            d.from_ == dep.to and d.to == dep.from_ for d in dependencies
        )
        if reverse:
            already = any(
                (a == dep.to and b == dep.from_) or (a == dep.from_ and b == dep.to)
                for a, b in circular
            )
            if not already:
                circular.append((dep.from_, dep.to))

    # Orphan modules: no outgoing or incoming edges in the module graph
    has_importers = {d.to for d in dependencies}
    has_imports = {d.from_ for d in dependencies}
    orphaned_modules = {
        m for m in modules if m not in has_importers and m not in has_imports
    }
    orphans = [
        f.filepath
        for f in files
        if _get_module_name(f.filepath, scope_depth) in orphaned_modules
    ][:MAX_ORPHAN_FILES]

    return GraphData(
        dependencies=dependencies,
        circular=circular,
        orphans=orphans,
        modules=list(modules),
    )


def render_graph_md(graph: GraphData) -> str:
    lines: list[str] = ["# Dependency graph", ""]

    lines.append("## Module dependencies")
    lines.append("")
    if not graph.dependencies:
        lines.append("(no inter-module dependencies detected)")
    else:
        for dep in graph.dependencies:
            lines.append(f"{dep.from_} \u2192 {dep.to}")

    lines.append("")
    lines.append("## Circular dependencies")
    if not graph.circular:
        lines.append("(none detected)")
    else:
        for a, b in graph.circular:
            lines.append(f"\u26a0 {a} \u2194 {b}")

    lines.append("")
    lines.append("## Orphan modules")
    if not graph.orphans:
        lines.append("(none detected)")
    else:
        for o in graph.orphans:
            lines.append(f"- {o}")

    lines.append("")
    lines.append("## Mermaid export")
    lines.append("```mermaid")
    lines.append("graph TD")
    if not graph.dependencies:
        lines.append("    (no dependencies)")
    else:
        seen: set[str] = set()
        for dep in graph.dependencies[:MAX_MERMAID_DEPENDENCIES]:
            key = f"{dep.from_}-->{dep.to}"
            if key not in seen:
                seen.add(key)
                safe_from = re.sub(r"[^a-zA-Z0-9_]", "_", dep.from_)
                safe_to = re.sub(r"[^a-zA-Z0-9_]", "_", dep.to)
                lines.append(f"    {safe_from} --> {safe_to}")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)
