from __future__ import annotations

from datetime import UTC, datetime

from mpga.core.config import MpgaConfig
from mpga.core.scanner import ScanResult, detect_project_type
from mpga.generators.scope_md import ScopeInfo

# Number of top files (by line count) to list in the Key Files table.
TOP_FILES_COUNT = 10
# Maximum lines to reference in an evidence link for a key file.
KEY_FILE_EVIDENCE_MAX_LINES = 50


def render_index_md(
    scan_result: ScanResult,
    config: MpgaConfig,
    scopes: list[ScopeInfo],
    active_milestone: str | None,
    evidence_coverage: float,
    scope_health: dict | None = None,
) -> str:
    now = datetime.now(UTC).isoformat()
    project_type = detect_project_type(scan_result)
    total_files = scan_result.total_files
    total_lines = scan_result.total_lines
    languages = scan_result.languages

    lang_summary = ", ".join(
        f"{lang} ({round(stats['lines'] / total_lines * 100)}%)"
        for lang, stats in sorted(
            languages.items(), key=lambda item: item[1]["lines"], reverse=True
        )
    )

    lines: list[str] = []

    lines.append(f"# Project: {config.project.name}")
    lines.append("")
    lines.append("## Identity")
    lines.append(f"- **Type:** {project_type}")
    lines.append(
        f"- **Size:** ~{total_lines:,} lines across {total_files} files"
    )
    lines.append(f"- **Languages:** {lang_summary}")
    lines.append(f"- **Last sync:** {now}")
    lines.append(
        f"- **Evidence coverage:** {round(evidence_coverage * 100)}%"
        f" (target: {round(config.evidence.coverage_threshold * 100)}%)"
    )
    lines.append("")

    # Key files table -- top 10 by size
    lines.append("## Key files")
    lines.append("| File | Role | Evidence |")
    lines.append("|------|------|----------|")
    role_map: dict[str, str] = {}
    if config.knowledge_layer is not None:
        role_map = config.knowledge_layer.key_file_roles
    top_files = sorted(scan_result.files, key=lambda f: f.lines, reverse=True)[
        :TOP_FILES_COUNT
    ]
    for f in top_files:
        role = role_map.get(f.filepath, "(describe role)")
        lines.append(
            f"| {f.filepath} | {role}"
            f" | [E] {f.filepath}:1-{min(KEY_FILE_EVIDENCE_MAX_LINES, f.lines)} |"
        )
    lines.append("")

    lines.append("## Conventions")
    custom_conventions: list[str] = []
    if config.knowledge_layer is not None:
        custom_conventions = [
            c for c in config.knowledge_layer.conventions if c.strip()
        ]
    if custom_conventions:
        for c in custom_conventions:
            lines.append(f"- {c}")
    else:
        lines.append("- (Add your project conventions here)")
        lines.append('- (e.g. "All API routes follow REST naming: /api/v1/<resource>")')
    lines.append("")

    lines.append("## Agent trigger table")
    lines.append("| Task pattern | Agent | Scopes to load |")
    lines.append("|-------------|-------|-----------------|")
    lines.append(
        '| "add/modify authentication" | red-dev \u2192 green-dev \u2192 blue-dev | auth, database |'
    )
    lines.append('| "explore how X works" | scout | (auto-detect) |')
    lines.append(
        '| "plan feature X" | researcher \u2192 architect | (auto-detect) |'
    )
    lines.append(
        '| "fix bug in X" | scout \u2192 red-dev \u2192 green-dev | (auto-detect) |'
    )
    lines.append('| "refactor X" | architect \u2192 blue-dev | (auto-detect) |')
    lines.append('| "design/wireframe feature X" | designer | (auto-detect) |')
    lines.append('| "audit UI of X" | ui-auditor | (auto-detect) |')
    lines.append('| "check visual regression" | visual-tester | (auto-detect) |')
    lines.append('| "create design system" | designer \u2192 ui-auditor | (auto-detect) |')
    lines.append('| "frontend design for X" | mpga-frontend-design | (auto-detect) |')
    lines.append("")

    lines.append("## Scope registry")
    lines.append("| Scope | Status | Evidence links | Last verified |")
    lines.append("|-------|--------|---------------|---------------|")
    today = now.split("T")[0]
    for scope in scopes:
        if scope_health and scope.name in scope_health:
            sr = scope_health[scope.name]
            total = sr.total_links
            valid = sr.valid_links + sr.healed_links
            pct = sr.health_pct
            if pct >= 80:
                status = "✓ fresh"
            elif pct >= 50:
                status = "⚠ stale"
            else:
                status = "✗ broken"
            link_count = f"{valid}/{total}"
        else:
            status = "[Unknown]"
            link_count = f"0/{len(scope.exports)}"
        lines.append(f"| {scope.name} | {status} | {link_count} | {today} |")
    lines.append("")

    lines.append("## Active milestone")
    lines.append(f"- {active_milestone if active_milestone is not None else '(none)'}")
    lines.append("")

    lines.append("## Known unknowns")
    lines.append("- [ ] (run `mpga evidence verify` to detect unknowns)")

    return "\n".join(lines) + "\n"
