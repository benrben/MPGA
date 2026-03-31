from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log, victory
from mpga.core.scanner import scan
from mpga.db.connection import get_connection
from mpga.db.repos.file_info import FileInfoRepo
from mpga.db.repos.graph import GraphRepo
from mpga.db.repos.symbols import SymbolRepo
from mpga.db.schema import create_schema
from mpga.db.search import rebuild_global_fts
from mpga.evidence.ast import extract_symbols
from mpga.evidence.drift import run_drift_check
from mpga.evidence.parser import parse_evidence_links
from mpga.generators.graph_md import build_graph
from mpga.generators.scope_md import group_into_scopes, render_scope_md


def _sync_to_db(project_root: Path, scan_result, graph, scopes) -> None:
    """Populate SQLite DB from in-memory data — no MPGA/ files written."""
    db_path = project_root / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    try:
        create_schema(conn)

        file_repo = FileInfoRepo(conn)
        graph_repo = GraphRepo(conn)
        symbol_repo = SymbolRepo(conn)

        # Clear derived data — preserve user data (tasks, milestones, sessions)
        conn.execute("DELETE FROM file_info")
        conn.execute("DELETE FROM symbols")
        conn.execute("DELETE FROM symbols_fts")
        graph_repo.clear()
        conn.execute("DELETE FROM evidence")
        conn.execute("DELETE FROM evidence_fts")
        conn.execute("DELETE FROM scopes")
        conn.execute("DELETE FROM scopes_fts")
        conn.commit()

        # File info + symbols
        for file in scan_result.files:
            file_repo.upsert(
                file.filepath,
                language=file.language,
                lines=file.lines,
                size=file.size,
            )
            try:
                for symbol in extract_symbols(file.filepath, str(project_root)):
                    symbol_repo.create(
                        file.filepath,
                        symbol.name,
                        type=symbol.type,
                        start_line=symbol.start_line,
                        end_line=symbol.end_line,
                    )
            except RecursionError:
                log.dim(f"  skip AST for {file.filepath} — too deeply nested")

        # Dependency graph edges
        for dep in graph.dependencies:
            graph_repo.add_edge(dep.from_, dep.to)

        # Scopes + evidence links — straight to DB, no files
        for scope in scopes:
            content = render_scope_md(scope, str(project_root))
            scope_id = scope.name
            name = scope_id
            summary: str | None = None
            in_body = False
            for line in content.splitlines():
                if line.startswith("# "):
                    name = line[2:].strip()
                elif line.startswith("#"):
                    in_body = True
                elif in_body and line.strip():
                    summary = line.strip()
                    break

            # Parse evidence counts from content so scope list shows real numbers
            from mpga.evidence.parser import evidence_stats as _evidence_stats
            _links = parse_evidence_links(content)
            _stats = _evidence_stats(_links)

            conn.execute(
                """
                INSERT OR REPLACE INTO scopes
                    (id, name, summary, content, status,
                     evidence_total, evidence_valid, last_verified,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, 'fresh', ?, ?, NULL, datetime('now'), datetime('now'))
                """,
                (scope_id, name, summary, content, _stats.total, _stats.valid),
            )
            conn.execute("DELETE FROM evidence WHERE scope_id = ?", (scope_id,))
            for link in parse_evidence_links(content):
                conn.execute(
                    """
                    INSERT INTO evidence
                        (raw, type, filepath, start_line, end_line,
                         symbol, symbol_type, description, confidence,
                         stale_date, last_verified, scope_id)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL, ?)
                    """,
                    (
                        link.raw, link.type, link.filepath,
                        link.start_line, link.end_line, link.symbol,
                        link.description, link.confidence, link.stale_date,
                        scope_id,
                    ),
                )

        rebuild_global_fts(conn)
    finally:
        conn.close()


def _write_index_md(project_root: Path, config, scan_result, scopes) -> None:
    """Write INDEX.md to the project root for cold-session agent orientation."""
    lines: list[str] = []
    project_name = config.project.name
    lines.append(f"# {project_name} — INDEX")
    lines.append("")
    lines.append(
        f"> Generated by `mpga sync`. "
        f"{scan_result.total_files} file(s) · {len(scopes)} scope(s)."
    )
    lines.append("")

    # Scopes section
    lines.append("## Scopes")
    lines.append("")
    if scopes:
        for scope in scopes:
            file_count = len(scope.files) if hasattr(scope, "files") else "?"
            lines.append(f"- **{scope.name}** ({file_count} files)")
    else:
        lines.append("_No scopes discovered._")
    lines.append("")

    # Entry points / key files
    if scan_result.entry_points:
        lines.append("## Key entry points")
        lines.append("")
        for ep in scan_result.entry_points:
            lines.append(f"- `{ep}`")
        lines.append("")

    # Top-level directories
    if scan_result.top_level_dirs:
        lines.append("## Top-level directories")
        lines.append("")
        for d in scan_result.top_level_dirs:
            lines.append(f"- `{d}/`")
        lines.append("")

    index_path = Path(project_root) / "INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")


_LAST_SYNC_FILENAME = "last_sync"
_FILE_SNAPSHOT_FILENAME = "file_snapshot.json"


def _load_file_snapshot(snapshot_path: Path) -> dict[str, float]:
    """Return {filepath: mtime} from the snapshot file, or {} if absent/corrupt."""
    if not snapshot_path.exists():
        return {}
    try:
        return json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_file_snapshot(snapshot_path: Path, project_root: Path, scan_result) -> None:
    """Write current filesystem mtimes for all scanned files to *snapshot_path*."""
    snapshot: dict[str, float] = {}
    for file in scan_result.files:
        abs_path = Path(project_root) / file.filepath
        try:
            snapshot[file.filepath] = abs_path.stat().st_mtime
        except OSError:
            pass
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")


def _compute_changed_scopes(
    snapshot: dict[str, float],
    project_root: Path,
    scan_result,
    scopes,
) -> list[str]:
    """Return scope names whose files changed/appeared since *snapshot*."""
    changed_files: set[str] = set()
    for file in scan_result.files:
        abs_path = Path(project_root) / file.filepath
        try:
            current_mtime = abs_path.stat().st_mtime
        except OSError:
            continue
        prev_mtime = snapshot.get(file.filepath)
        if prev_mtime is None or current_mtime > prev_mtime:
            changed_files.add(file.filepath)

    changed_scope_names: list[str] = []
    for scope in scopes:
        if any(f.filepath in changed_files for f in scope.files):
            changed_scope_names.append(scope.name)
    return sorted(changed_scope_names)


def _is_db_fresh(last_sync_path: Path, threshold_minutes: int) -> bool:
    """Return True if the last sync timestamp is within *threshold_minutes*.

    Returns False when:
    - threshold_minutes is 0 (caller wants to always run)
    - the last_sync file does not exist
    - the timestamp cannot be parsed
    - elapsed time >= threshold_minutes
    """
    if threshold_minutes <= 0:
        return False
    if not last_sync_path.exists():
        return False
    try:
        raw = last_sync_path.read_text(encoding="utf-8").strip()
        last_ts = datetime.datetime.fromisoformat(raw)
        # Normalise to UTC-aware for comparison
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        elapsed_minutes = (now - last_ts).total_seconds() / 60.0
        return elapsed_minutes < threshold_minutes
    except (ValueError, OSError):
        return False


def _write_last_sync(last_sync_path: Path) -> None:
    """Write the current UTC time to *last_sync_path*."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    last_sync_path.write_text(now.isoformat(), encoding="utf-8")


@click.command("sync")
@click.option("--full", is_flag=True, help="Rebuild everything (default)")
@click.option("--incremental", is_flag=True, help="Only update changed files since last sync")
@click.option(
    "--skip-if-fresh",
    "skip_if_fresh",
    default=None,
    type=int,
    metavar="N",
    help=(
        "Skip sync if the last sync was less than N minutes ago. "
        "Pass 0 to always run. Omit to always run."
    ),
)
@click.option(
    "--output-changed-scopes",
    "output_changed_scopes",
    is_flag=True,
    default=False,
    help=(
        "After sync, print '---CHANGED-SCOPES---' followed by a newline-separated "
        "list of scope names whose files changed since the last sync."
    ),
)
def sync_cmd(full: bool, incremental: bool, skip_if_fresh: int | None, output_changed_scopes: bool) -> None:
    """Regenerate/update the knowledge layer — all SQLite, no file clutter."""
    project_root = find_project_root() or Path.cwd()
    db_path = Path(project_root) / ".mpga" / "mpga.db"

    if not db_path.exists():
        log.error("MPGA not initialized \u2014 SAD! Run `mpga init` to Make This Project Great Again.")
        sys.exit(1)

    # --skip-if-fresh: bail out early if the DB was synced recently
    if skip_if_fresh is not None:
        last_sync_path = Path(project_root) / ".mpga" / _LAST_SYNC_FILENAME
        if _is_db_fresh(last_sync_path, threshold_minutes=skip_if_fresh):
            raw = last_sync_path.read_text(encoding="utf-8").strip()
            last_ts = datetime.datetime.fromisoformat(raw)
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=datetime.timezone.utc)
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            elapsed_minutes = int((now - last_ts).total_seconds() / 60)
            click.echo(
                f"Sync skipped: DB is fresh (last sync {elapsed_minutes} minutes ago)"
            )
            return

    # Load file snapshot before sync for --output-changed-scopes comparison
    snapshot_path = Path(project_root) / ".mpga" / _FILE_SNAPSHOT_FILENAME
    pre_sync_snapshot: dict[str, float] = (
        _load_file_snapshot(snapshot_path) if output_changed_scopes else {}
    )

    config = load_config(project_root)
    log.header("MPGA Sync \u2014 Going to be TREMENDOUS")

    log.info("Scanning the GREATEST codebase...")
    scan_result = scan(str(project_root), config.project.ignore, True)
    log.success(f"Scanned {scan_result.total_files} files ({scan_result.total_lines:,} lines)")

    log.info("Building dependency graph...")
    graph = build_graph(scan_result, config)
    log.success(f"Graph built \u2014 {len(graph.dependencies)} dependencies, {len(graph.circular)} circular")

    log.info("Grouping into scopes...")
    scopes = group_into_scopes(scan_result, graph, config)
    log.success(f"Grouped into {len(scopes)} scopes")

    log.info("Syncing to SQLite...")
    _sync_to_db(project_root, scan_result, graph, scopes)
    log.success("SQLite knowledge layer synced")

    drift = run_drift_check(str(project_root), config.drift.ci_threshold)

    # Generate INDEX.md for cold-session agent orientation
    _write_index_md(project_root, config, scan_result, scopes)

    # Record successful sync timestamp for --skip-if-fresh
    _write_last_sync(Path(project_root) / ".mpga" / _LAST_SYNC_FILENAME)

    # Write file snapshot for --output-changed-scopes on next run
    _write_file_snapshot(snapshot_path, Path(project_root), scan_result)

    victory("Sync COMPLETE! Your project is looking FANTASTIC!")
    click.echo("")
    log.dim(f"  {len(scopes)} scopes in .mpga/mpga.db \u2014 WINNING!")
    log.dim(f"  Evidence: {drift.overall_health_pct}% ({drift.valid_links}/{drift.total_links} links)")
    log.dim("  Run `mpga status` to view your INCREDIBLE dashboard")
    log.dim("  Run `mpga export --claude` to update CLAUDE.md")

    # Output changed scopes last so sentinel is unambiguous
    if output_changed_scopes:
        changed = _compute_changed_scopes(
            pre_sync_snapshot, Path(project_root), scan_result, scopes
        )
        click.echo("---CHANGED-SCOPES---")
        for name in changed:
            click.echo(name)


@click.command("normalize")
def normalize_cmd() -> None:
    """Re-verify evidence links and report health."""
    project_root = find_project_root() or Path.cwd()
    db_path = Path(project_root) / ".mpga" / "mpga.db"

    if not db_path.exists():
        log.error("MPGA not initialized \u2014 run `mpga init` first.")
        sys.exit(1)

    config = load_config(project_root)
    log.header("MPGA Normalize \u2014 Checking Evidence Health")

    drift = run_drift_check(str(project_root), config.drift.ci_threshold)
    log.success(
        f"Evidence health: {drift.overall_health_pct}% "
        f"({drift.valid_links}/{drift.total_links} links verified)"
    )
    victory("Evidence layer verified!")
