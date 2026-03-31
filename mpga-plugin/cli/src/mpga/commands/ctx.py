"""Context protection command group (`mpga ctx ...`)."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import sqlite3
import subprocess
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import click

from mpga.bridge.hook_policy import policy_mode
from mpga.core.config import find_project_root
from mpga.db.connection import get_connection
from mpga.db.schema import create_schema

MAX_EMIT_BYTES = 2_000
MAX_INDEX_BYTES = 50_000
MAX_BATCH_COMMANDS = 10
MAX_SEARCH_RESULTS = 10

_ALLOWED_SCHEMES = {"http", "https"}


def _validate_url_for_fetch(url: str) -> None:
    """Validate a URL before fetching to prevent SSRF attacks.

    Raises ValueError if:
    - The scheme is not http or https.
    - The resolved host IP is in a private/loopback/reserved range.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"URL scheme '{scheme}' is not allowed. Only http and https are supported."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    try:
        # Resolve the hostname to an IP address to catch DNS rebinding.
        resolved_ip = socket.getaddrinfo(hostname, None)[0][4][0]
        addr = ipaddress.ip_address(resolved_ip)
    except (socket.gaierror, ValueError):
        # If we can't resolve the hostname, treat it as safe (public DNS lookup
        # failures are not an SSRF vector; the request will simply fail).
        return

    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
        raise ValueError(
            f"URL resolves to a disallowed private/loopback/reserved IP address: {addr}"
        )


def _project_root() -> Path:
    return Path(find_project_root() or Path.cwd())


def _conn() -> sqlite3.Connection:
    root = _project_root()
    conn = get_connection(str(root / ".mpga" / "mpga.db"))
    create_schema(conn)
    return conn


def _strip_markup(text: str) -> str:
    # Lightweight tag stripping for fetched HTML.
    return re.sub(r"<[^>]+>", " ", text)


def _summarize_text(text: str, max_chars: int = 600) -> str:
    squashed = " ".join(text.split())
    if len(squashed) <= max_chars:
        return squashed
    return squashed[: max_chars - 3] + "..."


def _truncate_bytes(text: str, max_bytes: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    return raw[:max_bytes].decode("utf-8", errors="ignore")


def _save_artifact(conn: sqlite3.Connection, source: str, content: str, summary: str) -> int:
    content = _truncate_bytes(content, MAX_INDEX_BYTES)
    summary = _truncate_bytes(summary, MAX_EMIT_BYTES)
    cur = conn.execute(
        """
        INSERT INTO ctx_artifacts (source, content, summary, content_bytes, summary_bytes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            source,
            content,
            summary,
            len(content.encode("utf-8")),
            len(summary.encode("utf-8")),
            datetime.now(UTC).isoformat(),
        ),
    )
    rowid = int(cur.lastrowid)
    conn.execute(
        """
        INSERT INTO ctx_artifacts_fts (rowid, source, content, summary)
        VALUES (?, ?, ?, ?)
        """,
        (rowid, source, content, summary),
    )
    conn.commit()
    return rowid


def _log_ctx_event(
    conn: sqlite3.Connection,
    *,
    tool: str,
    source: str | None,
    raw_bytes: int,
    emitted_bytes: int,
    indexed_count: int,
) -> None:
    conn.execute(
        """
        INSERT INTO ctx_events (timestamp, tool, source, raw_bytes, emitted_bytes, indexed_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(UTC).isoformat(),
            tool,
            source,
            raw_bytes,
            emitted_bytes,
            indexed_count,
        ),
    )
    conn.commit()


_SHELL_INJECTION_CHARS = frozenset(";|&`$><(){}")


def _validate_shell_command(code: str) -> None:
    """Raise ValueError if *code* contains shell injection metacharacters.

    This is a defence-in-depth guard: the primary protection is that we use
    ``shell=False`` with ``shlex.split``, but rejecting obvious injection
    payloads up-front gives a clearer error message and prevents surprising
    behaviour from split-based execution (e.g. ``echo hello; id`` would
    become ``["echo", "hello;", "id"]`` with shlex which is safe but silently
    wrong — better to refuse it).
    """
    found = _SHELL_INJECTION_CHARS & set(code)
    if found:
        raise ValueError(
            f"Unsafe shell metacharacters detected in command: {sorted(found)!r}. "
            "Remove injection characters before calling _run_shell()."
        )


def _run_shell(code: str, timeout_s: int = 20) -> tuple[int, str]:
    """Run *code* as a subprocess without invoking a shell interpreter.

    Uses ``shlex.split`` to tokenise the command string and passes
    ``shell=False`` to ``subprocess.run`` to eliminate shell injection risk.
    Raises ``ValueError`` if *code* contains obvious shell metacharacters.
    """
    import shlex

    _validate_shell_command(code)
    args = shlex.split(code)
    proc = subprocess.run(
        args,
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


@click.group("ctx", help="Context protection and sandbox tooling")
def ctx() -> None:
    pass


@ctx.command("execute", help="Run shell code and index raw output while emitting only a summary")
@click.option("--code", required=True, help="Shell command to execute")
@click.option("--source", default="shell", show_default=True, help="Source label for indexing")
def ctx_execute(code: str, source: str) -> None:
    conn = _conn()
    try:
        rc, output = _run_shell(code)
        summary = _summarize_text(output)
        artifact_id = _save_artifact(conn, source=source, content=output, summary=summary)
        _log_ctx_event(
            conn,
            tool="ctx_execute",
            source=source,
            raw_bytes=len(output.encode("utf-8")),
            emitted_bytes=len(summary.encode("utf-8")),
            indexed_count=1,
        )
    finally:
        conn.close()

    click.echo(f"exit_code={rc}")
    click.echo(f"artifact_id={artifact_id}")
    click.echo(f"summary={summary}")


@ctx.command("execute-file", help="Analyze a file with bounded output and index full content")
@click.argument("path")
@click.option("--query", default="", help="Optional pattern to count in file")
def ctx_execute_file(path: str, query: str) -> None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise click.ClickException(f"File not found: {path}")

    content = p.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    q_count = content.count(query) if query else 0
    summary = (
        f"path={path} lines={len(lines)} chars={len(content)}"
        + (f" query={query!r} matches={q_count}" if query else "")
    )
    conn = _conn()
    try:
        artifact_id = _save_artifact(conn, source=f"file:{path}", content=content, summary=summary)
        _log_ctx_event(
            conn,
            tool="ctx_execute_file",
            source=f"file:{path}",
            raw_bytes=len(content.encode("utf-8")),
            emitted_bytes=len(summary.encode("utf-8")),
            indexed_count=1,
        )
    finally:
        conn.close()
    click.echo(f"artifact_id={artifact_id}")
    click.echo(summary)


@ctx.command("index", help="Index content directly")
@click.option("--content", default=None, help="Inline content to index")
@click.option("--file", "file_path", default=None, help="Read content from file")
@click.option("--source", required=True, help="Source label")
def ctx_index(content: str | None, file_path: str | None, source: str) -> None:
    if not content and not file_path:
        raise click.ClickException("Provide --content or --file")
    if content and file_path:
        raise click.ClickException("Use only one of --content or --file")

    payload = content or Path(file_path or "").read_text(encoding="utf-8", errors="ignore")
    summary = _summarize_text(payload)
    conn = _conn()
    try:
        artifact_id = _save_artifact(conn, source=source, content=payload, summary=summary)
        _log_ctx_event(
            conn,
            tool="ctx_index",
            source=source,
            raw_bytes=len(payload.encode("utf-8")),
            emitted_bytes=len(summary.encode("utf-8")),
            indexed_count=1,
        )
    finally:
        conn.close()
    click.echo(f"artifact_id={artifact_id}")
    click.echo(f"summary={summary}")


@ctx.command("search", help="Search indexed ctx artifacts with BM25 ranking")
@click.argument("query")
@click.option("--limit", default=5, show_default=True, type=int)
def ctx_search(query: str, limit: int) -> None:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT a.id, a.source, snippet(ctx_artifacts_fts, 1, '<b>', '</b>', '...', 24), bm25(ctx_artifacts_fts)
            FROM ctx_artifacts_fts
            JOIN ctx_artifacts a ON ctx_artifacts_fts.rowid = a.id
            WHERE ctx_artifacts_fts MATCH ?
            ORDER BY bm25(ctx_artifacts_fts)
            LIMIT ?
            """,
            (query, max(1, min(limit, MAX_SEARCH_RESULTS))),
        ).fetchall()
        _log_ctx_event(conn, tool="ctx_search", source=None, raw_bytes=0, emitted_bytes=0, indexed_count=0)
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()

    if not rows:
        click.echo("No results found.")
        return
    for row in rows:
        click.echo(f"[{row[0]}] {row[1]}")
        click.echo(f"  {row[2]}")
        click.echo(f"  rank={row[3]}")


@ctx.command("batch-execute", help="Run multiple commands, index outputs, then run queries")
@click.option("--command", "commands", multiple=True, required=True, help="Shell command (repeatable)")
@click.option("--query", "queries", multiple=True, help="Search query against indexed outputs")
def ctx_batch_execute(commands: tuple[str, ...], queries: tuple[str, ...]) -> None:
    cmds = list(commands)[:MAX_BATCH_COMMANDS]
    conn = _conn()
    try:
        results: list[dict[str, object]] = []
        total_raw_bytes = 0
        for cmd in cmds:
            rc, output = _run_shell(cmd)
            summary = _summarize_text(output)
            total_raw_bytes += len(output.encode("utf-8"))
            artifact_id = _save_artifact(conn, source=f"batch:{cmd}", content=output, summary=summary)
            results.append({"command": cmd, "exit_code": rc, "artifact_id": artifact_id, "summary": summary})

        query_results: dict[str, list[dict[str, object]]] = {}
        for q in queries:
            rows = conn.execute(
                """
                SELECT a.id, a.source, snippet(ctx_artifacts_fts, 1, '<b>', '</b>', '...', 20), bm25(ctx_artifacts_fts)
                FROM ctx_artifacts_fts
                JOIN ctx_artifacts a ON ctx_artifacts_fts.rowid = a.id
                WHERE ctx_artifacts_fts MATCH ?
                ORDER BY bm25(ctx_artifacts_fts)
                LIMIT 5
                """,
                (q,),
            ).fetchall()
            query_results[q] = [
                {"id": row[0], "source": row[1], "snippet": row[2], "rank": row[3]} for row in rows
            ]

        emitted = len(json.dumps(results).encode("utf-8"))
        _log_ctx_event(
            conn,
            tool="ctx_batch_execute",
            source="batch",
            raw_bytes=total_raw_bytes,
            emitted_bytes=emitted,
            indexed_count=len(results),
        )
    finally:
        conn.close()

    click.echo(json.dumps({"results": results, "queries": query_results}, indent=2))


@ctx.command("fetch-and-index", help="Fetch URL, index response, and emit summary only")
@click.argument("url")
@click.option("--source", required=True, help="Source label for retrieval")
def ctx_fetch_and_index(url: str, source: str) -> None:
    _validate_url_for_fetch(url)
    req = urllib.request.Request(url, headers={"User-Agent": "mpga-ctx/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310 - user-invoked CLI utility
        raw = resp.read().decode("utf-8", errors="ignore")
    text = _strip_markup(raw)
    summary = _summarize_text(text)

    conn = _conn()
    try:
        artifact_id = _save_artifact(conn, source=source, content=text, summary=summary)
        _log_ctx_event(
            conn,
            tool="ctx_fetch_and_index",
            source=source,
            raw_bytes=len(raw.encode("utf-8")),
            emitted_bytes=len(summary.encode("utf-8")),
            indexed_count=1,
        )
    finally:
        conn.close()
    click.echo(f"artifact_id={artifact_id}")
    click.echo(f"summary={summary}")


@ctx.command("stats", help="Context savings stats for ctx_* tools")
def ctx_stats() -> None:
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT tool, COUNT(*), COALESCE(SUM(raw_bytes),0), COALESCE(SUM(emitted_bytes),0)
            FROM ctx_events
            GROUP BY tool
            ORDER BY tool
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        click.echo("No ctx events yet.")
        return

    click.echo("tool | calls | raw_bytes | emitted_bytes | saved_pct")
    for tool, calls, raw, emitted in rows:
        saved_pct = 0.0 if raw <= 0 else (1.0 - (emitted / raw)) * 100.0
        click.echo(f"{tool} | {calls} | {raw} | {emitted} | {saved_pct:.1f}%")


@ctx.command("doctor", help="Diagnostics for hook policy, ctx tooling, and FTS tables")
def ctx_doctor() -> None:
    root = _project_root()
    checks: list[tuple[str, bool, str]] = []
    checks.append(("policy_mode", policy_mode() == "hard-block", f"mode={policy_mode()}"))

    claude_hooks = root / ".claude" / "settings.json"
    checks.append(("claude_settings", claude_hooks.exists(), str(claude_hooks)))
    checks.append(("cursor_rule", (root / ".cursor" / "rules" / "mpga-routing.mdc").exists(), ".cursor/rules/mpga-routing.mdc"))
    checks.append(("codex_rule", (root / ".codex" / "agents" / "mpga-routing.toml").exists(), ".codex/agents/mpga-routing.toml"))
    checks.append(
        ("antigravity_rule", (root / ".antigravity" / "rules" / "mpga-routing.md").exists(), ".antigravity/rules/mpga-routing.md")
    )

    conn = _conn()
    try:
        table_names = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        checks.append(("ctx_artifacts_table", "ctx_artifacts" in table_names, "ctx_artifacts"))
        checks.append(("ctx_events_table", "ctx_events" in table_names, "ctx_events"))
        checks.append(("ctx_artifacts_fts", "ctx_artifacts_fts" in table_names, "ctx_artifacts_fts"))
    finally:
        conn.close()

    missing_exports: list[str] = []
    for name, ok, detail in checks:
        mark = "[x]" if ok else "[ ]"
        click.echo(f"{mark} {name}: {detail}")
        if not ok and name in ("cursor_rule", "codex_rule", "antigravity_rule"):
            missing_exports.append(name)

    if missing_exports:
        flags = " ".join(
            f"--{n.replace('_rule', '')}" for n in missing_exports
        )
        click.echo(f"\nFix missing export rules — run: mpga export {flags}")
