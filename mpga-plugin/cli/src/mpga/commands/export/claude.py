from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from mpga.core.logger import log

from .agents import AGENTS, SKILL_NAMES, copy_skills_to, extract_active_milestone, resolve_model, rewrite_cli_references
from .runtime import (
    copy_vendored_runtime,
    global_vendored_cli_command,
    project_vendored_cli_command,
)


def rewrite_agent_frontmatter_model(content: str, tier: str) -> str:
    """Rewrite the model: line in YAML frontmatter to the resolved Claude model ID."""
    resolved = resolve_model(tier, "claude")
    return re.sub(r"^(model:\s*).*$", rf"\1{resolved}", content, flags=re.MULTILINE)


# --- Claude Code export -------------------------------------------------------


def export_claude(
    project_root: str,
    index_content: str,
    project_name: str,
    plugin_root: str | None,
    is_global: bool,
) -> None:
    if is_global:
        log.info("Append the following to ~/.claude/CLAUDE.md:")
        log.info("\n" + _generate_claude_global())
        home = os.environ.get("HOME", "~")
        copy_vendored_runtime(str(Path(home) / ".claude"), plugin_root)
        _deploy_claude_plugin(
            str(Path(home) / ".claude"),
            plugin_root,
            project_root,
            True,
        )
    else:
        copy_vendored_runtime(project_root, plugin_root)
        claude_md_path = Path(project_root) / "CLAUDE.md"
        claude_md_path.write_text(
            _generate_claude_md(index_content, project_name), encoding="utf-8"
        )
        log.success("Generated CLAUDE.md")
        _deploy_claude_plugin(
            str(Path(project_root) / ".claude"),
            plugin_root,
            project_root,
            False,
        )


# Deploy the full MPGA plugin into a .claude/ directory:
#   skills/mpga-<name>/SKILL.md  (11 skills)
#   agents/<slug>.md             (10 agents)
#   commands/<cmd>.md            (21 /mpga:* commands)
#   settings.json                (hooks merged with existing)
def _deploy_claude_plugin(
    claude_dir: str,
    plugin_root: str | None,
    project_root: str,
    is_global: bool,
) -> None:
    claude_path = Path(claude_dir)
    claude_path.mkdir(parents=True, exist_ok=True)

    cli_path: str | None = None
    if plugin_root:
        if is_global:
            cli_path = global_vendored_cli_command(claude_dir)
        else:
            cli_path = project_vendored_cli_command()

    # Skills
    copy_skills_to(str(claude_path / "skills"), plugin_root, "claude", cli_path)
    log.success(f".claude/skills/ ({len(SKILL_NAMES)} skills)")

    if not plugin_root:
        log.warn(
            "Plugin root not found \u2014 skipping agents, commands, and hooks. Set MPGA_PLUGIN_ROOT to fix."
        )
        return

    # Agents
    agents_src = Path(plugin_root) / "agents"
    agents_dest = claude_path / "agents"
    if agents_src.exists():
        agents_dest.mkdir(parents=True, exist_ok=True)
        md_files = [f for f in agents_src.iterdir() if f.suffix == ".md"]
        tier_by_slug = {a.slug: a.tier for a in AGENTS if a.tier is not None}
        for f in md_files:
            content = rewrite_cli_references(
                f.read_text(encoding="utf-8"),
                cli_path,
                plugin_root,
            )
            slug = f.stem
            if slug in tier_by_slug:
                content = rewrite_agent_frontmatter_model(content, tier_by_slug[slug])
            (agents_dest / f.name).write_text(content, encoding="utf-8")
        log.success(f".claude/agents/ ({len(md_files)} agents)")

    # Commands (project-scoped only -- global commands go in ~/.claude/commands/)
    if not is_global:
        commands_src = Path(plugin_root) / "commands"
        commands_dest = claude_path / "commands"
        if commands_src.exists():
            commands_dest.mkdir(parents=True, exist_ok=True)
            md_files = [f for f in commands_src.iterdir() if f.suffix == ".md"]
            for f in md_files:
                # Resolve ${CLAUDE_PLUGIN_ROOT} in command files too
                content = f.read_text(encoding="utf-8")
                if cli_path:
                    content = rewrite_cli_references(content, cli_path)
                (commands_dest / f.name).write_text(content, encoding="utf-8")
            log.success(f".claude/commands/ ({len(md_files)} /mpga:* commands)")

    # Hooks -> merged into settings.json
    hooks_src = Path(plugin_root) / "hooks" / "hooks.json"
    if hooks_src.exists():
        settings_path = claude_path / "settings.json"
        hooks = json.loads(hooks_src.read_text(encoding="utf-8"))

        # Rewrite local/plugin CLI references to the portable vendored command.
        hooks_str = rewrite_cli_references(json.dumps(hooks), cli_path, plugin_root)
        resolved_hooks = json.loads(hooks_str)

        settings: dict = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass  # ignore malformed or unreadable settings
        # Replace hooks entirely (not append) to avoid duplicates on re-export
        merged = resolved_hooks.get("hooks", {})
        settings["hooks"] = merged
        settings_path.write_text(
            json.dumps(settings, indent=2), encoding="utf-8"
        )
        log.success(".claude/settings.json (hooks configured)")


def _generate_claude_md(index_content: str, _project_name: str) -> str:
    milestone = extract_active_milestone(index_content)

    now = datetime.now(UTC).isoformat()

    return f"""# MPGA-Managed Project Context

This project uses MPGA \u2014 the GREATEST context engineering system ever built. Believe me.
Do NOT edit this file manually \u2014 generated by `mpga export --claude`.
Run `mpga sync && mpga export --claude` to update.

## Key rules \u2014 the BEST rules, nobody has better rules
- ALWAYS cite evidence links [E] when making claims about code
- NEVER write implementation before tests \u2014 Uncle Bob's way. The ONLY way.
- Mark anything unverified as [Unknown]
- Allow parallel READS, not parallel WRITES: one writer per scope, scouts/auditors in background
- Prefer scope-local work queues so independent scopes can move in parallel

## Available MPGA commands \u2014 each one a WINNER
- /mpga:status \u2014 project health dashboard
- /mpga:board \u2014 task board
- /mpga:plan \u2014 evidence-based planning
- /mpga:execute \u2014 TDD cycle execution
- /mpga:quick "<task>" \u2014 ad-hoc task with TDD

## Routing rules
- `/api/*` routes return JSON from the SQLite-backed API
- All other app routes should resolve to the MPGA SPA shell
- Run `mpga serve` to preview the app locally on localhost

## Active milestone
{milestone}

We're going to Make This Project GREAT AGAIN!

Generated: {now}
"""


def _generate_claude_global() -> str:
    return """## MPGA Global Rules

When working in an MPGA-managed project:
1. Run `mpga status` first \u2014 it is the project's truth map
2. Use evidence links [E] to ground every code claim
3. Mark unknowns explicitly as [Unknown]
4. Follow the TDD cycle: red-dev \u2192 green-dev \u2192 blue-dev
5. Run `mpga board` for current task state
6. Run `mpga drift --quick` after modifying files
7. Use one writer per scope; scouts and auditors may run in parallel as read-only helpers
"""
