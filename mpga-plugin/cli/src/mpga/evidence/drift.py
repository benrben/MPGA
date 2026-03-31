from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from mpga.db.connection import get_connection
from mpga.db.repos.evidence import EvidenceRepo
from mpga.db.repos.scopes import Scope, ScopeRepo
from mpga.db.schema import create_schema
from mpga.evidence.parser import EvidenceLink, format_evidence_link
from mpga.evidence.resolver import verify_all_links


@dataclass
class StaleDriftItem:
    """A stale link paired with the reason it could not be resolved."""

    link: EvidenceLink
    reason: str


@dataclass
class HealedDriftItem:
    """A healed link paired with its updated line range."""

    link: EvidenceLink
    new_start: int
    new_end: int


@dataclass
class ScopeDriftReport:
    """Drift report for a single scope file, summarising evidence link health
    and listing any stale or healed items found during verification.
    """

    # Name of the scope (derived from the filename without extension)
    scope: str
    # Absolute path to the scope markdown file
    scope_path: str
    # Total number of evidence links checked in this scope
    total_links: int
    # Number of links whose targets were found exactly as specified
    valid_links: int
    # Number of links that were stale but could be auto-healed via AST lookup
    healed_links: int
    # Number of links whose targets could not be resolved
    stale_links: int
    # Health percentage: (valid + healed) / total * 100
    health_pct: int
    # Links that could not be resolved, with the reason for failure
    stale_items: list[StaleDriftItem] = field(default_factory=list)
    # Links that were healed, with updated line ranges
    healed_items: list[HealedDriftItem] = field(default_factory=list)


@dataclass
class DriftReport:
    """Aggregate drift report across all scopes in a project, including
    overall health metrics and CI pass/fail status.
    """

    # ISO timestamp of when the drift check was performed
    timestamp: str
    # Absolute path to the project root directory
    project_root: str
    # Per-scope drift reports
    scopes: list[ScopeDriftReport]
    # Overall health percentage across all scopes
    overall_health_pct: int
    # Total number of evidence links across all scopes
    total_links: int
    # Total number of valid (including healed) links across all scopes
    valid_links: int
    # Whether the overall health meets or exceeds the CI threshold
    ci_pass: bool
    # The minimum health percentage required for CI to pass
    ci_threshold: int


def _load_db_scopes(
    project_root: str,
    scope_filter: str | None,
) -> list[Scope] | None:
    db_path = Path(project_root) / ".mpga" / "mpga.db"
    if not db_path.exists():
        return None

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        repo = ScopeRepo(conn)
        if scope_filter:
            scope_row = repo.get(scope_filter)
            return [scope_row] if scope_row is not None else []
        return repo.list_all()
    finally:
        conn.close()


def _build_scope_report(
    *,
    scope_name: str,
    scope_path: str,
    links: list[EvidenceLink],
    project_root: str,
) -> ScopeDriftReport:
    results = verify_all_links(links, project_root)

    valid = sum(1 for r in results if r.resolved.status == "valid")
    healed = sum(1 for r in results if r.resolved.status == "healed")
    stale = sum(1 for r in results if r.resolved.status == "stale")
    total = len(results)
    health_pct = 100 if total == 0 else round(((valid + healed) / total) * 100)

    stale_items: list[StaleDriftItem] = []
    for r in results:
        if r.resolved.status != "stale":
            continue
        if not r.link.filepath:
            reason = "No filepath in evidence link"
        else:
            full_path = Path(project_root) / r.link.filepath
            if not full_path.exists():
                reason = f"File not found: {r.link.filepath}"
            else:
                reason = "Symbol not found in file"
        stale_items.append(StaleDriftItem(link=r.link, reason=reason))

    healed_items: list[HealedDriftItem] = [
        HealedDriftItem(
            link=r.link,
            new_start=r.resolved.start_line or 0,
            new_end=r.resolved.end_line or 0,
        )
        for r in results
        if r.resolved.status == "healed"
    ]

    return ScopeDriftReport(
        scope=scope_name,
        scope_path=scope_path,
        total_links=total,
        valid_links=valid,
        healed_links=healed,
        stale_links=stale,
        health_pct=health_pct,
        stale_items=stale_items,
        healed_items=healed_items,
    )


def run_drift_check(
    project_root: str,
    ci_threshold: int,
    scope_filter: str | None = None,
) -> DriftReport:
    """Run a drift check across all scope files in the project.

    Verifies that evidence links still point to valid code locations.

    Args:
        project_root: Absolute path to the project root directory.
        ci_threshold: Minimum health percentage (0-100) required for CI to pass.
        scope_filter: Optional scope name to limit the check to a single scope file.

    Returns:
        A :class:`DriftReport` containing per-scope results and aggregate
        health metrics.
    """
    now = datetime.now(UTC).isoformat()
    reports: list[ScopeDriftReport] = []
    db_scopes = _load_db_scopes(project_root, scope_filter)
    if db_scopes is None:
        raise RuntimeError("No scope data in DB. Run `mpga sync` first.")

    if db_scopes:
        conn = get_connection(str(Path(project_root) / ".mpga" / "mpga.db"))
        try:
            create_schema(conn)
            evidence_repo = EvidenceRepo(conn)
            for scope_row in db_scopes:
                links = [
                    link
                    for link in evidence_repo.find(scope_id=scope_row.id)
                    if link.type in ("valid", "stale")
                ]
                reports.append(
                    _build_scope_report(
                        scope_name=scope_row.id,
                        scope_path=str(Path(project_root) / "MPGA" / "scopes" / f"{scope_row.id}.md"),
                        links=links,
                        project_root=project_root,
                    )
                )
        finally:
            conn.close()

    total_links = sum(r.total_links for r in reports)
    valid_links = sum(r.valid_links + r.healed_links for r in reports)
    overall_health_pct = (
        100 if total_links == 0 else round((valid_links / total_links) * 100)
    )

    return DriftReport(
        timestamp=now,
        project_root=project_root,
        scopes=reports,
        overall_health_pct=overall_health_pct,
        total_links=total_links,
        valid_links=valid_links,
        ci_pass=overall_health_pct >= ci_threshold,
        ci_threshold=ci_threshold,
    )


def apply_healed_items_to_db(project_root: str, report: ScopeDriftReport) -> int:
    db_path = Path(project_root) / ".mpga" / "mpga.db"
    if not db_path.exists():
        return 0

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        repo = EvidenceRepo(conn)
        healed = 0
        for item in report.healed_items:
            updated_link = EvidenceLink(
                raw=item.link.raw,
                type="valid",
                confidence=item.link.confidence,
                filepath=item.link.filepath,
                start_line=item.new_start,
                end_line=item.new_end if item.link.end_line is not None or not item.link.symbol else None,
                symbol=item.link.symbol,
                symbol_type=item.link.symbol_type,
                description=item.link.description,
                stale_date=None,
                last_verified=datetime.now(UTC).isoformat(),
            )
            updated_link.raw = format_evidence_link(updated_link)
            repo.update_resolution(
                scope_id=report.scope,
                original_raw=item.link.raw,
                updated_link=updated_link,
            )
            healed += 1
        return healed
    finally:
        conn.close()


@dataclass
class HealResult:
    """Result of healing a scope file."""

    healed: int
    content: str


def heal_scope_file(report: ScopeDriftReport) -> HealResult:
    """Heal stale evidence links in a scope file.

    Replaces their line ranges with updated values determined by AST resolution.

    Args:
        report: The :class:`ScopeDriftReport` containing healed items with
            updated line ranges.

    Returns:
        A :class:`HealResult` with ``healed`` (number of links successfully
        updated) and ``content`` (the updated file content).
    """
    content = Path(report.scope_path).read_text(encoding="utf-8")
    updated = content
    healed = 0

    # Sort by symbol length descending to prevent shorter symbols from matching
    # inside longer ones
    sorted_items = sorted(
        report.healed_items,
        key=lambda item: len(item.link.symbol or ""),
        reverse=True,
    )

    for item in sorted_items:
        if item.link.symbol and item.link.end_line is None:
            # Symbol-based: preserve #symbol:lineHint format
            new_link = f"[E] {item.link.filepath}#{item.link.symbol}:{item.new_start}"
        else:
            new_link = (
                f"[E] {item.link.filepath}:{item.new_start}-{item.new_end}"
                + (f" :: {item.link.symbol}()" if item.link.symbol else "")
            )
        # Match the original evidence link in the file, accounting for
        # markdown table pipes and backticks
        if not item.link.filepath:
            continue
        fp = re.escape(item.link.filepath)
        sym = re.escape(item.link.symbol) if item.link.symbol else None
        range_pattern = (
            f":{item.link.start_line}-{item.link.end_line}"
            if item.link.start_line and item.link.end_line
            else r"(?::\d+-\d+)?"
        )
        sym_pattern = (
            rf"\s*::\s*{sym}\s*(?:\(\))?"
            if sym
            else r"(?:\s*::\s*\S+(?:\(\))?)?"
        )
        pattern = rf"\[E\]\s+`?{fp}`?{range_pattern}{sym_pattern}"
        match = re.search(pattern, updated)
        if match:
            updated = updated.replace(match.group(0), new_link, 1)
            healed += 1

    return HealResult(healed=healed, content=updated)


def try_downgrade_stale(item: StaleDriftItem, project_root: str) -> str | None:
    """Downgrade a stale symbol reference to a valid line-range reference when possible.

    If the referenced file still exists and ``start_line`` falls within the file,
    returns ``[E] filepath:start-end``.  Returns ``None`` if the file is missing
    or the line hint is out of range.
    """
    link = item.link
    if not link.filepath or link.start_line is None:
        return None

    full_path = Path(project_root) / link.filepath
    if not full_path.exists():
        return None

    try:
        with full_path.open(encoding="utf-8") as fh:
            line_count = sum(1 for _ in fh)
    except OSError:
        return None

    if link.start_line > line_count:
        return None

    end = link.end_line if link.end_line is not None else link.start_line
    return f"[E] {link.filepath}:{link.start_line}-{end}"
