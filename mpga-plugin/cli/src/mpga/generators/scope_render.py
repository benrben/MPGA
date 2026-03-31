"""Scope markdown rendering — converts ScopeInfo to markdown text.

Extracted from scope_md.py to keep module size manageable.
The render_scope_md function is the primary public API.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from mpga.core.logger import log

# Source file extensions that support AST-based symbol resolution.
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


def render_scope_md(scope: object, project_root: str) -> str:
    """Renders a complete scope markdown document from a ScopeInfo object.

    Args:
        scope: A ScopeInfo instance.
        project_root: The project root path used for symbol resolution.

    Returns:
        The full markdown string for the scope document.
    """
    from mpga.generators.scope_md import MAX_EVIDENCE_INDEX_ENTRIES, MAX_FILE_LIST_ENTRIES, ScopeInfo
    assert isinstance(scope, ScopeInfo)

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
        lines.append("**Called by these GREAT scopes (they need us, tremendously):**")
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
            lines.append(f"- **{ed.symbol}** ({ed.kind}) \u2014 {ed.description} {ev}")
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
            lines.append(f"- `{rc.symbol}`: {rc.annotation} [E] `{rc.filepath}`")
        lines.append("")
    else:
        lines.append(
            "<!-- TODO: The guardrails. Validation, permissions, error handling"
            " \u2014 everything that keeps this code GREAT. -->"
        )
        lines.append("")

    lines += [
        "## Concrete examples", "",
        '<!-- TODO: REAL examples. "When X happens, Y happens." Simple. Powerful. Like a deal. -->', "",
        "## UI", "",
        "<!-- TODO: Screens, flows, the beautiful UI. No UI? Cut this section. We don't keep dead weight. -->", "",
    ]

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

    # -- Relationships --
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
        lines.append("- (no dependencies \u2014 TOTALLY INDEPENDENT. Very strong.)")
        lines.append("")
    lines.append("<!-- TODO: What deals does this scope make with other scopes? Document them. -->")
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
        lines.append("<!-- TODO: A BEAUTIFUL diagram. Flow, sequence, boundaries. Make it GREAT. -->")
    lines.append("")

    lines += [
        "## Traces", "",
        "<!-- TODO: Step-by-step traces. Follow the code like a WINNER follows a deal. Use this table:", "",
        "| Step | Layer | What happens | Evidence |",
        "|------|-------|-------------|----------|",
        "| 1 | (layer) | (description) | [E] file:line |",
        "-->", "",
    ]

    # -- Evidence index --
    lines.append("## Evidence index")
    lines.append("")
    if scope.exports:
        lines.append("| Claim | Evidence |")
        lines.append("|-------|----------|")
        for exp in scope.exports[:MAX_EVIDENCE_INDEX_ENTRIES]:
            ev = _choose_evidence_form(exp.filepath, exp.symbol, project_root, fallback_lines=(1, 1))
            lines.append(f"| `{exp.symbol}` ({exp.kind}) | {ev} |")
        if len(scope.exports) > MAX_EVIDENCE_INDEX_ENTRIES:
            lines.append(f"| ... | {len(scope.exports) - MAX_EVIDENCE_INDEX_ENTRIES} more symbols |")
    else:
        lines.append("- (no exports detected \u2014 working behind the scenes. Very mysterious.)")
    lines.append("")

    # -- Files --
    lines.append("## Files")
    lines.append("")
    for file in scope.files[:MAX_FILE_LIST_ENTRIES]:
        lines.append(f"- `{file.filepath}` ({file.lines} lines, {file.language})")
    if len(scope.files) > MAX_FILE_LIST_ENTRIES:
        lines.append(f"- ... and {len(scope.files) - MAX_FILE_LIST_ENTRIES} more files")
    lines.append("")

    lines += [
        "## Deeper splits", "",
        "<!-- TODO: Too big? Split it. Make each piece LEAN and GREAT. -->", "",
        "## Confidence and notes", "",
        f"- **Confidence:** LOW (for now) \u2014 auto-generated, not yet verified. But it's going to be PERFECT.",
        f"- **Evidence coverage:** 0/{len(scope.exports)} verified",
        f"- **Last verified:** {now}",
        "- **Drift risk:** unknown",
        "- <!-- TODO: Note anything unknown or ambiguous. We don't hide problems \u2014 we FIX them. -->",
        "",
        "## Change history", "",
        f"- {now}: Initial scope generation via `mpga sync` \u2014 Making this scope GREAT!",
    ]

    return "\n".join(lines)
