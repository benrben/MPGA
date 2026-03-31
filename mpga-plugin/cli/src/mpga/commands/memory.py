"""Click group for mpga memory commands — progressive disclosure retrieval."""
from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path

import click

from mpga.core.config import find_project_root
from mpga.db.connection import open_db


def _project_root() -> Path:
    return find_project_root()


@click.group("memory", help="Memory and observation management — TREMENDOUS recall")
def memory() -> None:
    pass


@memory.command("get", help="Show full observation details (Layer 3)")
@click.argument("observation_ids", type=int, nargs=-1, required=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def memory_get(observation_ids: tuple[int, ...], as_json: bool) -> None:
    with closing(open_db(_project_root())) as conn:
        all_data: list[dict] = []
        for observation_id in observation_ids:
            row = conn.execute(
                "SELECT id, session_id, scope_id, title, type, narrative, facts, "
                "concepts, files_read, files_modified, evidence_links, created_at "
                "FROM observations WHERE id = ?",
                (observation_id,),
            ).fetchone()

            if row is None:
                click.echo(f"Observation {observation_id} not found.")
                continue

            (obs_id, session_id, scope_id, title, obs_type, narrative,
             facts_raw, concepts_raw, files_read, files_modified,
             evidence_links, created_at) = row

            facts = json.loads(facts_raw) if facts_raw else []
            concepts = json.loads(concepts_raw) if concepts_raw else []

            data = {
                "id": obs_id,
                "title": title,
                "type": obs_type,
                "narrative": narrative or "",
                "facts": facts,
                "concepts": concepts,
                "files_read": files_read or "",
                "files_modified": files_modified or "",
                "scope": scope_id or "",
                "evidence_links": evidence_links or "",
                "created_at": created_at or "",
            }

            if as_json:
                all_data.append(data)
            else:
                if len(observation_ids) > 1:
                    click.echo(f"\n{'=' * 40}")
                click.echo(f"Title: {title}")
                click.echo(f"Type: {obs_type}")
                click.echo(f"Scope: {scope_id}")
                click.echo(f"Created: {created_at}")
                click.echo(f"\nNarrative:\n  {narrative}")
                click.echo("\nFacts:")
                for f in facts:
                    click.echo(f"  - {f}")
                click.echo("\nConcepts:")
                for c in concepts:
                    click.echo(f"  - {c}")
                click.echo(f"\nFiles read: {files_read}")
                click.echo(f"Files modified: {files_modified}")
                click.echo(f"Evidence: {evidence_links}")

        if as_json and all_data:
            click.echo(json.dumps(all_data if len(all_data) > 1 else all_data[0], indent=2))


_TYPE_ICONS = {
    "tool_output": "\u2699\ufe0f",
    "decision": "\u2696\ufe0f",
    "discovery": "\U0001f50d",
    "pattern": "\U0001f504",
    "error": "\u274c",
    "intent": "\U0001f4ac",
    "role": "\U0001f3ad",
}


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@memory.command("search", help="Search observations (Layer 1: compact index)")
@click.argument("query")
@click.option("--type", "obs_type", default=None, help="Filter by observation type")
@click.option("--scope", "obs_scope", default=None, help="Filter by scope")
@click.option("--limit", default=20, help="Max results")
def memory_search(query: str, obs_type: str | None, obs_scope: str | None, limit: int) -> None:
    from collections import defaultdict

    from mpga.db.search import DualIndexSearch

    with closing(open_db(_project_root())) as conn:
        searcher = DualIndexSearch(conn)
        results = searcher.search(query, types=["observation"], limit=limit)

        grouped: dict[str, dict[str, list[tuple]]] = defaultdict(lambda: defaultdict(list))
        for r in results:
            row = conn.execute(
                "SELECT id, type, title, scope_id, created_at, narrative "
                "FROM observations WHERE id = ?",
                (int(r.entity_id),),
            ).fetchone()
            if not row:
                continue
            obs_id, obs_type_val, title, scope_id, created, narrative = row
            if obs_type and obs_type_val != obs_type:
                continue
            if obs_scope and (scope_id or "") != obs_scope:
                continue
            date = created[:10] if created else "unknown"
            scope_key = scope_id or "unscoped"
            grouped[date][scope_key].append((obs_id, obs_type_val, title, narrative or ""))

        if not any(items for scopes in grouped.values() for items in scopes.values()):
            click.echo("No observations found. No results matched your query.")
            return

        for date in sorted(grouped.keys(), reverse=True):
            click.echo(f"\n## {date}")
            for scope_key in sorted(grouped[date].keys()):
                click.echo(f"  [{scope_key}]")
                for obs_id, obs_type_val, title, narrative in grouped[date][scope_key]:
                    icon = _TYPE_ICONS.get(obs_type_val, "\u2022")
                    tokens = _estimate_tokens(title + (narrative or ""))
                    click.echo(f"    {icon} [O{obs_id}] {title}  (~{tokens}tok)")


@memory.command("link", help="Create evidence link from an observation")
@click.argument("observation_id", type=int)
def memory_link(observation_id: int) -> None:
    from mpga.memory.evidence_bridge import link_observation_to_evidence

    with closing(open_db(_project_root())) as conn:
        result = link_observation_to_evidence(conn, observation_id)
        if result is None:
            click.echo(f"Observation {observation_id} not found.")
            return
        click.echo(f"Evidence created: {result['raw']} — {result['description']}")


@memory.command("context", help="Show timeline around an observation (Layer 2)")
@click.argument("observation_id", type=int)
@click.option("--window", default=3, help="Number of observations before/after")
def memory_context(observation_id: int, window: int) -> None:
    with closing(open_db(_project_root())) as conn:
        row = conn.execute(
            "SELECT id, session_id, scope_id, title, type, narrative, created_at "
            "FROM observations WHERE id = ?",
            (observation_id,),
        ).fetchone()

        if row is None:
            click.echo(f"Observation {observation_id} not found.")
            raise SystemExit(1)

        obs_id, session_id, scope_id, title, obs_type, narrative, created_at = row

        click.echo(f"=== {title} ===")
        click.echo(f"Type: {obs_type}")
        click.echo(f"Narrative: {narrative}")
        click.echo(f"Created: {created_at}")
        click.echo()

        before = conn.execute(
            "SELECT id, session_id, title, type, created_at FROM observations "
            "WHERE created_at < ? ORDER BY created_at DESC LIMIT ?",
            (created_at, window),
        ).fetchall()

        after = conn.execute(
            "SELECT id, session_id, title, type, created_at FROM observations "
            "WHERE created_at > ? ORDER BY created_at ASC LIMIT ?",
            (created_at, window),
        ).fetchall()

        all_entries = list(reversed(before)) + [(obs_id, session_id, title, obs_type, created_at)] + list(after)

        click.echo("--- Timeline ---")
        current_session: str | None = None
        for entry in all_entries:
            eid, esess, etitle, etype, ecreated = entry
            if esess != current_session:
                current_session = esess
                sess_label = esess or "no-session"
                click.echo(f"\n  [Session: {sess_label}]")
            marker = ">>>" if eid == obs_id else "   "
            click.echo(f"  {marker} [{eid}] {etitle} ({etype}) - {ecreated}")
        click.echo()

        if session_id:
            sess = conn.execute(
                "SELECT id, started_at, status, model FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if sess:
                click.echo(
                    f"Session: {sess[0]} (started {sess[1]}, "
                    f"status: {sess[2]}, model: {sess[3]})"
                )
