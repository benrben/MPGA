"""Scope markdown generator — ScopeInfo dataclass and scope grouping.

Extraction helpers are in scope_extract.py.
Rendering logic is in scope_render.py.
This module is focused on the ScopeInfo data model and grouping algorithm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from mpga.core.config import MpgaConfig
from mpga.core.scanner import FileInfo, ScanResult
from mpga.generators.graph_md import GraphData
from mpga.generators.scope_extract import (
    ExportDescription,
    ExportedSymbol,
    ModuleSummary,
    RuleConstraint,
    _detect_entry_points,
    _extract_exports,
    detect_frameworks,
    extract_annotations,
    extract_jsdoc_for_export,
    extract_module_summary,
    get_scope_name,
)

# Pre-compiled regex for detecting inter-scope imports inside group_into_scopes loop.
_SCOPE_IMPORT_RE = re.compile(r"""(?:from|import)\s+['"]([^'"]+)['"]""")

# Maximum number of evidence index entries to display in a scope document.
MAX_EVIDENCE_INDEX_ENTRIES = 40
# Maximum number of files to list in the Files section of a scope document.
MAX_FILE_LIST_ENTRIES = 30

# Re-export extraction classes and render function so callers that imported
# from scope_md still work without changes.
__all__ = [
    "ExportedSymbol",
    "ExportDescription",
    "RuleConstraint",
    "ModuleSummary",
    "ScopeInfo",
    "group_into_scopes",
    "render_scope_md",
    "get_scope_name",
]


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
            except OSError:
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


# Import render_scope_md from scope_render for backwards compatibility.
# Rendering logic is in scope_render.py to keep this module focused.
from mpga.generators.scope_render import render_scope_md  # noqa: E402
