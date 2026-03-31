"""Click group for the ``mpga session`` command tree.

Mirrors the Commander-based session.ts registration, converting each
subcommand to a Click command with the same options and arguments.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import click

from mpga.board.board import load_board, recalc_stats
from mpga.board.task import load_all_tasks
from mpga.bridge.compress import compress_session_resume, compress_task
from mpga.core.config import find_project_root
from mpga.core.logger import console, log
from mpga.db.connection import get_connection
from mpga.db.repos.sessions import Session, SessionRepo
from mpga.db.schema import create_schema

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOKENS_PER_LINE = 4
"""Approximate number of tokens per line of markdown/code."""

CONTEXT_WINDOW_TOKENS = 200_000
"""Default context window size in tokens (e.g. Claude 200K)."""

BUDGET_NAME_PAD_WIDTH = 30
"""Column width for budget display name padding."""

BUDGET_HEALTHY_PCT = 10
"""Context budget percentage below which scope usage is healthy."""

BUDGET_FULL_PCT = 30
"""Context budget percentage above which scope usage is getting full."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    return Path(find_project_root() or Path.cwd())


def _db_path(project_root: Path) -> Path:
    return project_root / ".mpga" / "mpga.db"


def _open_session_repo(project_root: Path) -> tuple[object, SessionRepo]:
    db_path = _db_path(project_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_path))
    create_schema(conn)
    return conn, SessionRepo(conn)


def _close_conn(conn: object) -> None:
    try:
        conn.close()  # type: ignore[attr-defined]
    except (AttributeError, sqlite3.Error):
        pass


def _load_board_snapshot(project_root: Path) -> dict[str, object]:
    board_dir = project_root / "MPGA" / "board"
    tasks_dir = board_dir / "tasks"
    board_path = board_dir / "board.json"

    board = load_board(str(board_dir)) if board_path.exists() else None
    if board:
        recalc_stats(board, str(tasks_dir))

    tasks = load_all_tasks(str(tasks_dir)) if tasks_dir.exists() else []
    in_progress = [t for t in tasks if t.column in ("in-progress", "testing", "review")]

    return {
        "board": board,
        "tasks": tasks,
        "in_progress": in_progress,
        "snapshot": json.dumps(
            {
                "milestone": board.milestone if board else None,
                "progress_pct": board.stats.progress_pct if board else 0,
                "done": board.stats.done if board else 0,
                "total": board.stats.total if board else 0,
                "in_progress": [compress_task(task) for task in in_progress[:5]],
            },
            indent=2,
        ),
    }


def _current_session(repo: SessionRepo, project_root: Path) -> Session | None:
    return repo.get_active(str(project_root)) or repo.get_latest(str(project_root))


def _ensure_active_session(repo: SessionRepo, project_root: Path) -> Session:
    snapshot = _load_board_snapshot(project_root)["snapshot"]
    return repo.ensure_active(str(project_root), task_snapshot=str(snapshot))


def _recent_event_dicts(repo: SessionRepo, session: Session, limit: int = 10) -> list[dict[str, str]]:
    events = repo.list_events(session.id, limit=limit)
    return [
        {
            "action": event.action or event.event_type,
            "input_summary": event.input_summary or event.output_summary or "",
        }
        for event in reversed(events)
    ]


def _session_state_lines(session: Session | None, repo: SessionRepo | None = None) -> list[str]:
    if session is None:
        return ["- No active session found."]

    lines = [
        f"- Session ID: {session.id}",
        f"- Status: {session.status}",
        f"- Started: {session.started_at}",
    ]
    if session.ended_at:
        lines.append(f"- Ended: {session.ended_at}")
    if session.task_snapshot:
        lines.append("- Snapshot: active board and task summary cached in SQLite")
    if repo is not None:
        events = repo.list_events(session.id, limit=5)
        if events:
            last = events[0]
            summary = last.input_summary or last.output_summary or last.action or last.event_type
            lines.append(f"- Last action: {summary}")
        else:
            lines.append("- Last action: none yet")
    return lines


def _render_resume_summary(repo: SessionRepo, session: Session, limit: int = 10) -> str:
    events = _recent_event_dicts(repo, session, limit=limit)
    if not events:
        snapshot = session.task_snapshot or ""
        if snapshot:
            return f"- session start: board snapshot cached\n- snapshot: {snapshot[:350]}"
        return "- session start: no recent events"

    return compress_session_resume(events, n=limit)


def _render_compact_packet(repo: SessionRepo, session: Session, limit: int = 6) -> str:
    """Return a bounded compact-resume packet for hook-time continuity."""
    events = repo.search_events(session.id, "session OR command OR ctx OR compact", limit=limit)
    if not events:
        return _render_resume_summary(repo, session, limit=limit)[:700]
    lines: list[str] = []
    for event in events:
        action = event.action or event.event_type
        summary = event.input_summary or event.output_summary or ""
        lines.append(f"- {action}: {summary}")
    payload = "\n".join(lines)
    return payload[:700]


def _is_mpga_managed_path(path: str) -> bool:
    parts = [part for part in Path(path).parts if part not in ("", ".")]
    return any(part in {"MPGA", ".mpga"} for part in parts)


def _read_redirect(path: str) -> tuple[int, str]:
    normalized = Path(path)
    parts = normalized.parts
    if "scopes" in parts:
        return 1, f"Use: mpga scope show {normalized.stem}"
    if "board" in parts:
        return 1, "Use: mpga board show"
    if ".mpga" in parts:
        return 1, "Use: mpga session resume"
    return 1, "Use: mpga search <query> or mpga session resume"


def _bash_redirect(command: str) -> tuple[int, str]:
    if command.strip().startswith("mpga "):
        return 0, ""

    lowered = command.lower()
    if "board" in lowered and ("mpga/" in lowered or ".mpga/" in lowered):
        return 1, "Use: mpga board show"
    if "scopes" in lowered and ("mpga/" in lowered or ".mpga/" in lowered):
        return 1, "Use: mpga scope show <scope>"
    if any(tool in lowered for tool in ("cat ", "grep ", "head ", "sed ", "less ", "tail ", "rg ")):
        if "mpga/" in lowered or ".mpga/" in lowered:
            return 1, "Use mpga search/scope/board commands instead of raw file reads."
    if "mpga/" in lowered or ".mpga/" in lowered:
        return 1, "Use mpga search/scope/board commands instead of raw file reads."
    return 0, ""


def _session_start_lines(repo: SessionRepo, session: Session) -> list[str]:
    lines = [
        "MPGA routing active. Use mpga search/scope/board and mpga ctx commands.",
        "Do not read MPGA/ files directly.",
        "Routing instructions loaded.",
        f"Session {session.id} ready.",
    ]
    resume = _render_resume_summary(repo, session, limit=5)
    if resume:
        lines.append(resume)
    return lines


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@click.group("session", help="Session management and context handoff")
def session() -> None:
    pass


# -- start ------------------------------------------------------------------


@session.command("start", help="Begin or resume SQLite-backed session tracking")
@click.option("--model", default=None, help="Model name to record for this session")
def session_start(model: str | None) -> None:
    project_root = _project_root()
    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _ensure_active_session(repo, project_root)
        if model:
            conn.execute(
                "UPDATE sessions SET model = ? WHERE id = ?", (model, session_row.id)
            )
            conn.commit()
        repo.log_event(
            session_row.id,
            "session",
            action="session start",
            input_summary="Started or resumed session tracking",
        )
        for line in _session_start_lines(repo, session_row):
            click.echo(line)
    finally:
        _close_conn(conn)


# -- handoff ----------------------------------------------------------------


@session.command("handoff", help="Export current session state for fresh context")
@click.option("--accomplished", default=None, help="What was accomplished this session")
def session_handoff(accomplished: str | None) -> None:
    from mpga.commands.session_handoff import do_handoff
    do_handoff(accomplished)


@session.command("export", help="Alias for 'handoff' — export current session state for fresh context")
@click.option("--accomplished", default=None, help="What was accomplished this session")
def session_export(accomplished: str | None) -> None:
    from mpga.commands.session_handoff import do_handoff
    do_handoff(accomplished)


# -- resume -----------------------------------------------------------------


@session.command("resume", help="Show most recent session summary from DB")
def session_resume() -> None:
    project_root = _project_root()
    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _current_session(repo, project_root)
        if session_row is None:
            log.info("No session events found. Run `mpga session start` first.")
            return
        summary = _render_resume_summary(repo, session_row)
        click.echo(summary)
        log.dim(f"--- Session: {session_row.id} ---")
    finally:
        _close_conn(conn)


# -- event (log a single event) ---------------------------------------------


@session.command("event", help="Record a single session event into SQLite")
@click.argument("event_type")
@click.option("--action", default=None, help="Action label (tool name, command, etc.)")
@click.option("--input-summary", default=None, help="Summary of the input/trigger")
@click.option("--output-summary", default=None, help="Summary of the output/result")
def session_event(
    event_type: str,
    action: str | None,
    input_summary: str | None,
    output_summary: str | None,
) -> None:
    project_root = _project_root()
    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _ensure_active_session(repo, project_root)
        repo.log_event(
            session_row.id,
            event_type,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
        )
        click.echo(f"event recorded: {event_type}")
    finally:
        _close_conn(conn)


# -- events -----------------------------------------------------------------


@session.command("events", help="Show recent session events from SQLite")
@click.option("--last", "last_n", default=10, show_default=True, help="Number of recent events to show")
def session_events(last_n: int) -> None:
    project_root = _project_root()
    db_path = _db_path(project_root)
    if not db_path.exists():
        log.info("No session database found. Run `mpga session start` first.")
        return

    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _current_session(repo, project_root)
        if session_row is None:
            log.info("No session events found. Run `mpga session start` first.")
            return
        events = repo.list_events(session_row.id, limit=last_n)
        if not events:
            log.info("No session events found.")
            return
        for event in reversed(events):
            summary = event.input_summary or event.output_summary or ""
            click.echo(f"- {event.timestamp} [{event.event_type}] {event.action or ''} {summary}".rstrip())
    finally:
        _close_conn(conn)


# -- end --------------------------------------------------------------------


@session.command("end", help="Mark the active session closed")
def session_end() -> None:
    project_root = _project_root()
    db_path = _db_path(project_root)
    if not db_path.exists():
        log.info("No session database found. Run `mpga session start` first.")
        return

    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _current_session(repo, project_root)
        if session_row is None:
            log.info("No session to end.")
            return
        repo.log_event(
            session_row.id,
            "session",
            action="session end",
            input_summary="Closed session tracking",
        )
        ended = repo.end(session_row.id)
        click.echo(f"Closed session {ended.id if ended else session_row.id}")
    finally:
        _close_conn(conn)


# -- log --------------------------------------------------------------------


@session.command("log", help="Record a session decision or note")
@click.argument("message")
def session_log(message: str) -> None:
    project_root = _project_root()
    conn, repo = _open_session_repo(project_root)
    try:
        session_row = _ensure_active_session(repo, project_root)
        repo.log_event(
            session_row.id,
            "note",
            action="session log",
            input_summary=message,
        )
    finally:
        _close_conn(conn)

    log.success(f"Logged: {message}")


# -- budget -----------------------------------------------------------------


@session.command("budget", help="Estimate context window usage from MPGA layer")
def session_budget() -> None:
    project_root = _project_root()
    mpga_dir = Path(project_root) / "MPGA"
    db_path = _db_path(project_root)

    if db_path.exists():
        conn, repo = _open_session_repo(project_root)
        try:
            session_row = _current_session(repo, project_root)
            session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            active_count = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE status = 'active'"
            ).fetchone()[0]
            console.print("[bold]Context Budget[/]")
            console.print(f"  Database sessions: {session_count} total / {active_count} active")
            console.print(f"  Event log: {event_count} events")
            if session_row is not None and session_row.task_snapshot:
                console.print("  Snapshot: cached in SQLite")
            console.print("")
            log.success("SQLite session budget summary ready")
            return
        finally:
            _close_conn(conn)

    estimates: list[dict[str, object]] = []

    index_path = mpga_dir / "INDEX.md"
    if index_path.exists():
        lines = len(index_path.read_text(encoding="utf-8").splitlines())
        estimates.append({"name": "INDEX.md", "lines": lines, "tier": "Tier 1 (hot)"})

    scopes_dir = mpga_dir / "scopes"
    if scopes_dir.exists():
        for f in sorted(scopes_dir.iterdir()):
            if f.suffix == ".md":
                lines = len(f.read_text(encoding="utf-8").splitlines())
                estimates.append({"name": f"scopes/{f.name}", "lines": lines, "tier": "Tier 2 (warm)"})

    log.header("Context Budget")
    total = 0
    for e in estimates:
        name = str(e["name"])
        line_count = int(e["lines"])  # type: ignore[arg-type]
        tier = str(e["tier"])
        console.print(f"  {name:<{BUDGET_NAME_PAD_WIDTH}} {line_count:>5} lines  [{tier}]")
        total += line_count

    console.print("")
    console.print(f"  Total MPGA context:  {total} lines (~{round(total * TOKENS_PER_LINE)} tokens)")
    pct = round((total * TOKENS_PER_LINE) / CONTEXT_WINDOW_TOKENS * 100)
    console.print(f"  % of {CONTEXT_WINDOW_TOKENS // 1000}K window:    ~{pct}%")
    console.print("")

    if pct <= BUDGET_HEALTHY_PCT:
        log.info("Still healthy — plenty of room in context window")
    elif pct <= BUDGET_FULL_PCT:
        log.warn("Getting full — consider pruning or using session handoff")
    else:
        log.warn("Getting full — consider using fewer scope docs per session")
