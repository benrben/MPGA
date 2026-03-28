"""Normalizer pipeline: verify → heal → re-verify → rewrite health lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from mpga.core.config import MpgaConfig
from mpga.evidence.drift import (
    DriftReport,
    ScopeDriftReport,
    heal_scope_file,
    run_drift_check,
    try_downgrade_stale,
)


@dataclass
class NormalizeResult:
    """Summary of what the normalizer did."""

    scopes_healed: int = 0
    links_healed: int = 0
    # Keyed by scope name → ScopeDriftReport from the second (re-verify) pass
    scope_health: dict[str, ScopeDriftReport] = field(default_factory=dict)


def normalize(project_root: str, config: MpgaConfig) -> NormalizeResult:
    """Run a verify → heal → re-verify → rewrite-health pipeline.

    1. First drift pass — collect healed and stale items.
    2. Write healed items back to scope files.
    3. Downgrade stale items to valid line-range refs where possible.
    4. Second drift pass — get updated health statistics.
    5. Rewrite the ``- **Health:**`` line in each scope file.

    Returns a :class:`NormalizeResult` with per-scope health data from the
    second pass, ready to be passed to ``render_index_md()``.
    """
    result = NormalizeResult()
    threshold = config.drift.ci_threshold

    # --- Pass 1 ---
    report: DriftReport = run_drift_check(project_root, threshold)
    Path(project_root) / "MPGA" / "scopes"

    for scope_report in report.scopes:
        # Heal line-drifted symbols
        if scope_report.healed_items:
            heal_result = heal_scope_file(scope_report)
            if heal_result.healed:
                Path(scope_report.scope_path).write_text(
                    heal_result.content, encoding="utf-8"
                )
                result.scopes_healed += 1
                result.links_healed += heal_result.healed

        # Downgrade stale symbol refs to range refs when file still exists
        if scope_report.stale_items:
            scope_path = Path(scope_report.scope_path)
            if scope_path.exists():
                content = scope_path.read_text(encoding="utf-8")
                changed = False
                for item in scope_report.stale_items:
                    replacement = try_downgrade_stale(item, project_root)
                    if replacement and item.link.raw:
                        content = content.replace(item.link.raw, replacement, 1)
                        changed = True
                if changed:
                    scope_path.write_text(content, encoding="utf-8")

    # --- Pass 2: re-verify ---
    re_report: DriftReport = run_drift_check(project_root, threshold)

    # Build scope_health dict and rewrite health lines
    for scope_report in re_report.scopes:
        scope_name = Path(scope_report.scope_path).stem
        result.scope_health[scope_name] = scope_report
        _rewrite_scope_health(scope_report)

    return result


def _rewrite_scope_health(scope_report: ScopeDriftReport) -> None:
    """Overwrite the ``- **Health:** …`` line in a scope file with verifier truth."""
    scope_path = Path(scope_report.scope_path)
    if not scope_path.exists():
        return

    total = scope_report.total_links
    valid = scope_report.valid_links + scope_report.healed_links
    pct = scope_report.health_pct

    if pct >= 80:
        status = "✓ fresh"
    elif pct >= 50:
        status = "⚠ stale"
    else:
        status = "✗ broken"

    health_line = f"- **Health:** {status} ({pct}% — {valid}/{total} links verified)"

    content = scope_path.read_text(encoding="utf-8")
    new_content = re.sub(
        r"- \*\*Health:\*\*[^\n]*",
        health_line,
        content,
        count=1,
    )
    if new_content != content:
        scope_path.write_text(new_content, encoding="utf-8")
