"""Click group for hook entrypoints used by Claude Code and other agents."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import click

from mpga.bridge.hook_policy import evaluate_bash, evaluate_read, mpga_routing_text
from mpga.db.connection import get_connection
from mpga.db.repos.sessions import SessionRepo
from mpga.db.schema import create_schema

from . import session as session_cmd


def _project_root() -> Path:
    return session_cmd._project_root()


def _open_repo() -> tuple[object, SessionRepo]:
    project_root = _project_root()
    db_path = project_root / ".mpga" / "mpga.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(str(db_path))
    create_schema(conn)
    return conn, SessionRepo(conn)


def _close_conn(conn: object) -> None:
    try:
        conn.close()  # type: ignore[attr-defined]
    except (AttributeError, sqlite3.Error):
        pass


def _block(message: str) -> None:
    click.echo(message)
    raise SystemExit(1)


def _read_message(path: str) -> str:
    return evaluate_read(path).to_output()


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _hooks_manifest() -> dict:
    hooks_path = _plugin_root() / "hooks" / "hooks.json"
    return json.loads(hooks_path.read_text(encoding="utf-8"))


def _routing_text() -> str:
    return mpga_routing_text()


def _hooks_export_markdown() -> str:
    """Render hooks.json as markdown for Cursor, Codex, and Antigravity installs."""
    hooks = _hooks_manifest().get("hooks", {})
    lines = [
        "\n## MPGA hooks (hooks.json parity)\n\n",
        "Configure the following where your agent supports hooks, to mirror Claude Code.\n\n",
    ]
    for event_name in sorted(hooks.keys()):
        lines.append(f"### {event_name}\n\n")
        for block in hooks[event_name]:
            matcher = block.get("matcher")
            if matcher is not None:
                lines.append(f"- **matcher**: `{matcher}`\n")
            for h in block.get("hooks", []):
                cmd = h.get("command", "")
                htype = h.get("type", "command")
                lines.append(f"  - ({htype}) `{cmd}`\n")
        lines.append("\n")
    return "".join(lines)


def _detect_platforms(project_root: Path) -> list[str]:
    matches: list[str] = []
    for platform, relpath in (
        ("claude", ".claude"),
        ("cursor", ".cursor"),
        ("codex", ".codex"),
        ("antigravity", ".antigravity"),
    ):
        if (project_root / relpath).exists():
            matches.append(platform)
    return matches or ["claude", "cursor", "codex", "antigravity"]


def _install_claude(project_root: Path) -> Path:
    claude_dir = project_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = claude_dir / "settings.json"
    settings = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["hooks"] = _hooks_manifest()["hooks"]
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return settings_path


def _install_cursor(project_root: Path) -> Path:
    rules_dir = project_root / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    path = rules_dir / "mpga-routing.mdc"
    path.write_text(
        "---\n"
        'description: "MPGA routing rules"\n'
        "globs:\n"
        "alwaysApply: true\n"
        "---\n\n"
        "# MPGA Routing\n\n"
        f"{_routing_text()}"
        f"{_hooks_export_markdown()}",
        encoding="utf-8",
    )
    return path


def _install_codex(project_root: Path) -> Path:
    agents_dir = project_root / ".codex" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / "mpga-routing.toml"
    body = _routing_text() + _hooks_export_markdown()
    instructions = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    path.write_text(
        'name = "MPGA Routing"\n'
        'description = "Route MPGA reads through CLI commands"\n'
        'model = "gpt-5.4-mini"\n'
        'sandbox_mode = "workspace-write"\n\n'
        'developer_instructions = """\n'
        f"{instructions}"
        '"""\n',
        encoding="utf-8",
    )
    return path


def _install_antigravity(project_root: Path) -> Path:
    rules_dir = project_root / ".antigravity" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    path = rules_dir / "mpga-routing.md"
    path.write_text(
        "# MPGA Routing\n\n" + _routing_text() + _hooks_export_markdown(),
        encoding="utf-8",
    )
    return path


def _install_platform(project_root: Path, platform: str) -> Path:
    installers = {
        "claude": _install_claude,
        "cursor": _install_cursor,
        "codex": _install_codex,
        "antigravity": _install_antigravity,
    }
    return installers[platform](project_root)


@click.group("hook", help="Hook entrypoints for editor/agent integration")
def hook() -> None:
    pass


@hook.command("pre-read", help="Redirect MPGA-managed file reads to mpga commands")
@click.argument("path")
def hook_pre_read(path: str) -> None:
    decision = evaluate_read(path)
    if decision.decision == "allow":
        return
    _block(decision.to_output())


@hook.command("pre-bash", help="Intercept raw MPGA file access from shell commands")
@click.argument("command")
def hook_pre_bash(command: str) -> None:
    decision = evaluate_bash(command)
    if decision.decision == "allow":
        return
    _block(decision.to_output())


@hook.command("post-bash", help="Log mpga CLI commands as session events")
@click.argument("command")
@click.argument("output")
def hook_post_bash(command: str, output: str) -> None:
    if not command.strip().startswith("mpga "):
        return

    conn, repo = _open_repo()
    try:
        project_root = _project_root()
        session_row = session_cmd._ensure_active_session(repo, project_root)
        parts = command.split()
        action = " ".join(parts[:3]) if len(parts) >= 3 else command
        event_type = "ctx" if len(parts) > 1 and parts[1] == "ctx" else "command"
        repo.log_event(
            session_row.id,
            event_type,
            action=action,
            input_summary=command,
            output_summary=output[:240],
            full_output=output[:2000],
        )
    finally:
        _close_conn(conn)


@hook.command("session-start", help="Create or resume a session and print routing state")
def hook_session_start() -> None:
    conn, repo = _open_repo()
    try:
        project_root = _project_root()
        session_row = session_cmd._ensure_active_session(repo, project_root)
        for line in session_cmd._session_start_lines(repo, session_row):
            click.echo(line)
    finally:
        _close_conn(conn)


@hook.command("pre-compact", help="Persist concise compact packet before history compaction")
def hook_pre_compact() -> None:
    conn, repo = _open_repo()
    try:
        project_root = _project_root()
        session_row = session_cmd._ensure_active_session(repo, project_root)
        packet = session_cmd._render_compact_packet(repo, session_row, project_root=project_root)
        repo.log_event(
            session_row.id,
            "compact",
            action="pre compact snapshot",
            input_summary="PreCompact hook invoked",
            output_summary=packet[:240],
            full_output=packet[:2000],
        )
        click.echo(packet)
    finally:
        _close_conn(conn)


@hook.command("capture-user-prompt", help="Capture user decisions and intents as observations")
def hook_capture_user_prompt() -> None:
    import sys

    raw = sys.stdin.read()
    if not raw.strip():
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"user_message": raw}

    prompt_text = data.get("user_message", "")
    if not prompt_text.strip():
        return

    obs_type = "intent"
    text_lower = prompt_text.lower()
    if any(w in text_lower for w in ("decided", "chose", "decision", "choose", "picked")):
        obs_type = "decision"
    elif any(w in text_lower for w in ("as a", "role", "persona", "act as", "you are")):
        obs_type = "role"

    title = prompt_text[:80].strip()
    if len(prompt_text) > 80:
        title += "..."

    conn, _ = _open_repo()
    try:
        from mpga.db.repos.observations import ObservationRepo, Observation
        from mpga.core.config import load_config

        skip = set(load_config(_project_root()).memory.skip_tools)
        obs_repo = ObservationRepo(conn)
        obs_repo.create(Observation(
            session_id=data.get("session_id"),
            title=title,
            type=obs_type,
            tool_name="UserPromptSubmit",
            narrative=prompt_text[:2000],
        ))
    finally:
        _close_conn(conn)


@hook.command("capture-observation", help="Capture tool output into observation queue")
def hook_capture_observation() -> None:
    import sys

    raw = sys.stdin.read()
    if not raw.strip():
        return

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    tool_name = data.get("tool_name", "")

    try:
        from mpga.core.config import load_config
        skip_tools = set(load_config(_project_root()).memory.skip_tools)
    except (ImportError, FileNotFoundError, KeyError):
        skip_tools = {"TodoRead", "TodoWrite", "ListFiles"}
    if tool_name in skip_tools:
        return

    conn, _repo = _open_repo()
    try:
        from mpga.db.repos.observations import ObservationRepo, QueueItem

        obs_repo = ObservationRepo(conn)
        obs_repo.enqueue(QueueItem(
            session_id=data.get("session_id"),
            tool_name=tool_name,
            tool_input=json.dumps(data.get("tool_input", ""))[:2000],
            tool_output=json.dumps(data.get("tool_output", ""))[:2000],
        ))
    finally:
        _close_conn(conn)


@hook.command("install", help="Install MPGA routing config for supported agent platforms")
@click.option(
    "--platform",
    type=click.Choice(["claude", "cursor", "codex", "antigravity"]),
    default=None,
    help="Install for one specific platform instead of auto-detecting",
)
def hook_install(platform: str | None) -> None:
    project_root = _project_root()
    platforms = [platform] if platform else _detect_platforms(project_root)

    installed: list[tuple[str, Path]] = []
    for item in platforms:
        installed.append((item, _install_platform(project_root, item)))

    for item, path in installed:
        click.echo(f"{item}: installed {path.relative_to(project_root)}")
