from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from mpga.core.logger import log

from .agents import (
    AGENTS,
    SKILL_NAMES,
    AgentMeta,
    copy_skills_to,
    read_agent_instructions,
    resolve_model,
    write_agents,
)
from .runtime import (
    copy_vendored_runtime,
    global_vendored_cli_command,
    project_vendored_cli_command,
)

# --- Codex / Gemini CLI export ------------------------------------------------


def export_codex(
    project_root: str,
    index_content: str,
    project_name: str,
    plugin_root: str | None,
    is_global: bool,
) -> None:
    if is_global:
        home = os.environ.get("HOME", "~")
        codex_global_dir = str(Path(home) / ".codex")
        cli_command = global_vendored_cli_command(codex_global_dir) if plugin_root else "mpga"
        copy_vendored_runtime(codex_global_dir, plugin_root)
        Path(codex_global_dir).mkdir(parents=True, exist_ok=True)
        (Path(codex_global_dir) / "AGENTS.md").write_text(
            _generate_codex_global_agents_md(cli_command), encoding="utf-8"
        )
        log.success("Generated ~/.codex/AGENTS.md")
        global_skills_dir = str(Path(codex_global_dir) / "skills")
        copy_skills_to(global_skills_dir, plugin_root, "codex", cli_command)
        log.success(f"Generated ~/.codex/skills/ ({len(SKILL_NAMES)} skills)")
        global_agents_dir = Path(codex_global_dir) / "agents"
        write_agents(global_agents_dir, lambda a: _generate_codex_agent_toml(a, plugin_root, cli_command), ".toml", AGENTS)
        log.success(f"Generated ~/.codex/agents/ ({len(AGENTS)} TOML agents)")
    else:
        cli_command = project_vendored_cli_command() if plugin_root else "mpga"
        copy_vendored_runtime(project_root, plugin_root)
        # Root AGENTS.md
        (Path(project_root) / "AGENTS.md").write_text(
            _generate_agents_md(index_content, project_name, cli_command),
            encoding="utf-8",
        )
        log.success("Generated AGENTS.md (root)")
        # Skills
        codex_skills_dir = str(Path(project_root) / ".codex" / "skills")
        copy_skills_to(codex_skills_dir, plugin_root, "codex", cli_command)
        log.success(f".codex/skills/ ({len(SKILL_NAMES)} skills)")
        # TOML agents
        codex_agents_dir = Path(project_root) / ".codex" / "agents"
        write_agents(codex_agents_dir, lambda a: _generate_codex_agent_toml(a, plugin_root, cli_command), ".toml", AGENTS)
        log.success(f".codex/agents/ ({len(AGENTS)} TOML agents)")


# --- Codex generators ---------------------------------------------------------


def _generate_codex_agent_toml(
    agent: AgentMeta,
    plugin_root: str | None,
    cli_command: str,
) -> str:
    """Generate Codex-format TOML agent (.codex/agents/mpga-<slug>.toml)"""
    instructions = read_agent_instructions(plugin_root, agent.slug, cli_command)
    # Escape double-quotes and backslashes for TOML triple-quoted strings
    instructions = instructions.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')

    escaped_desc = agent.description.replace('"', '\\"')

    model = resolve_model(agent.tier, "codex") if agent.tier else (agent.model or "")

    return f"""name = "{agent.name}"
description = "{escaped_desc}"
model = "{model}"
sandbox_mode = "{agent.sandbox_mode}"

developer_instructions = \"\"\"
{instructions}
\"\"\"
"""


def _generate_agents_md(
    index_content: str, _project_name: str, cli_command: str
) -> str:
    now = datetime.now(UTC).isoformat()

    return f"""# MPGA \u2014 Evidence-Backed Context Engineering

This project uses MPGA to maintain a verified knowledge layer.

## Before any task
1. Run `{cli_command} status` \u2014 it's the project truth map
2. Run `{cli_command} board show` \u2014 see what's in progress
3. Run `{cli_command} scope list` then `{cli_command} scope show <name>` for the feature area

## Evidence link protocol
- Every code claim MUST cite evidence: [E] file:line :: symbol()
- Unknown things get marked: [Unknown] description
- Stale evidence: [Stale:date] file:line
- After making code changes, verify affected evidence links

## TDD protocol (mandatory)
1. Write failing test FIRST
2. Implement minimal code to pass
3. Refactor without changing behavior
4. Update scope docs with new evidence links

## Parallel execution protocol
- One writer per scope at a time
- Read-only helpers like scouts and auditors may run in parallel
- Break plans into independent scope lanes when possible

## Task board
- Run `{cli_command} board show` for current task state

## Verification commands
- Run tests: (see project README for the test command)
- Check evidence: {cli_command} evidence verify
- Check drift: {cli_command} drift --quick
- Board status: {cli_command} board show

## Routing rules
- `/api/*` returns JSON from the SQLite mirror
- Other app routes resolve to the MPGA SPA shell
- Run `{cli_command} serve` to inspect the web UI locally

---
*Generated by MPGA {now}*

{index_content}
"""


def _generate_mpga_layer_agents_md() -> str:
    return """# MPGA Knowledge Layer \u2014 Navigation Guide

This project uses MPGA \u2014 the AI's verified map of the codebase is stored in SQLite.

## Reading order (tiered loading)
1. **Tier 1 \u2014 hot (always read first):** `mpga status`
2. **Tier 2 \u2014 warm (read per task):** `mpga scope show <name>`
3. **Tier 3 \u2014 cold (on demand):** `mpga board show`, `mpga milestone show`

## CLI commands
| Command | Purpose |
|---------|---------|
| `mpga status` | Project truth map \u2014 identity, key files, conventions, scope registry |
| `mpga scope list` | List all registered scopes |
| `mpga scope show <name>` | Feature/capability docs with evidence links |
| `mpga board show` | Human-readable task board |
| `mpga evidence verify` | Verify all evidence links |
| `mpga drift --quick` | Check for evidence drift |

## Evidence link format
```
[E] filepath:startLine-endLine :: symbolName()   # verified, preferred
[E] filepath :: symbolName                        # AST-only, resilient
[Unknown] description                             # explicitly unknown
[Stale:YYYY-MM-DD] filepath:range                # needs re-verification
```

Use CLI commands to manage the knowledge layer:
- `mpga sync` to update the knowledge layer
- `mpga evidence heal` to fix stale evidence links
- `mpga board add/move` to manage tasks
"""


def _generate_codex_global_agents_md(cli_command: str) -> str:
    return f"""# MPGA Methodology (Global)

When working in ANY MPGA-managed project:

## Core principles
- Evidence over claims: every code assertion must cite [E] file:line
- Unknown is honest: mark gaps as [Unknown], never guess
- TDD is mandatory: test \u2192 implement \u2192 refactor \u2192 update evidence
- Tiered reading: status first, scope docs second, deep docs only if needed
- Parallelize reads, not writes: one writer per scope

## Workflow
1. Run `{cli_command} status` for project map
2. Run `{cli_command} board show` for current tasks
3. Run `{cli_command} scope show <name>` before touching code
4. After changes: update evidence links in scope docs
5. Run `{cli_command} drift --quick` to verify nothing broke

## Evidence link format
[E] filepath:startLine-endLine :: symbolName()
[E] filepath :: symbolName (AST-only, resilient)
[Unknown] description (explicitly unknown)
[Stale:YYYY-MM-DD] filepath:range (was valid, needs verification)
"""
