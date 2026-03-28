from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

from mpga.core.logger import log

from .agents import (
    AGENTS,
    SKILL_NAMES,
    AgentMeta,
    copy_skills_to,
    read_agent_instructions,
    resolve_model,
)
from .runtime import (
    copy_vendored_runtime,
    global_vendored_cli_command,
    project_vendored_cli_command,
)


# --- Codex / Gemini CLI export ------------------------------------------------


def export_codex(
    project_root: str,
    mpga_dir: str,
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
        global_agents_dir.mkdir(parents=True, exist_ok=True)
        for agent in AGENTS:
            (global_agents_dir / f"{agent.name}.toml").write_text(
                _generate_codex_agent_toml(agent, plugin_root, cli_command),
                encoding="utf-8",
            )
        log.success(f"Generated ~/.codex/agents/ ({len(AGENTS)} TOML agents)")
    else:
        cli_command = project_vendored_cli_command() if plugin_root else "mpga"
        copy_vendored_runtime(project_root, plugin_root)
        # Root AGENTS.md
        (Path(project_root) / "AGENTS.md").write_text(
            _generate_agents_md(index_content, project_name, cli_command),
            encoding="utf-8",
        )
        # MPGA layer nav guide
        (Path(mpga_dir) / "AGENTS.md").write_text(
            _generate_mpga_layer_agents_md(), encoding="utf-8"
        )
        # Subdirectory AGENTS.md files for detected scopes
        scopes_dir = Path(mpga_dir) / "scopes"
        if scopes_dir.exists():
            _generate_subdir_agents_md(project_root, str(scopes_dir))
        log.success("Generated AGENTS.md (root + MPGA/ + scope subdirs)")
        # Skills
        codex_skills_dir = str(Path(project_root) / ".codex" / "skills")
        copy_skills_to(codex_skills_dir, plugin_root, "codex", cli_command)
        log.success(f".codex/skills/ ({len(SKILL_NAMES)} skills)")
        # TOML agents
        codex_agents_dir = Path(project_root) / ".codex" / "agents"
        codex_agents_dir.mkdir(parents=True, exist_ok=True)
        for agent in AGENTS:
            (codex_agents_dir / f"{agent.name}.toml").write_text(
                _generate_codex_agent_toml(agent, plugin_root, cli_command),
                encoding="utf-8",
            )
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
    now = datetime.now(timezone.utc).isoformat()

    return f"""# MPGA \u2014 Evidence-Backed Context Engineering

This project uses MPGA to maintain a verified knowledge layer.
The AI's "map" of this codebase lives in the MPGA/ directory.

## Before any task
1. Read MPGA/INDEX.md \u2014 it's the project truth map
2. Check MPGA/board/BOARD.md \u2014 see what's in progress
3. Find the relevant MPGA/scopes/*.md for the feature area

## Evidence link protocol
- Every code claim MUST cite evidence: [E] file:line :: symbol()
- Unknown things get marked: [Unknown] description
- Stale evidence: [Stale:date] file:line
- After making code changes, verify affected evidence links

## TDD protocol (mandatory)
1. Write failing test FIRST
2. Implement minimal code to pass
3. Refactor without changing behavior
4. Update MPGA scope docs with new evidence links

## Parallel execution protocol
- One writer per scope at a time
- Read-only helpers like scouts and auditors may run in parallel
- Break plans into independent scope lanes when possible

## Task board
Current tasks tracked in MPGA/board/BOARD.md
Task cards in MPGA/board/tasks/T*.md

## Verification commands
- Run tests: npm test
- Check evidence: {cli_command} evidence verify
- Check drift: {cli_command} drift --quick
- Board status: {cli_command} board show

## Project structure
See MPGA/INDEX.md for complete file registry with evidence links.
See MPGA/GRAPH.md for module dependency graph.

---
*Generated by MPGA {now}. Source: MPGA/INDEX.md*

{index_content}
"""


def _generate_mpga_layer_agents_md() -> str:
    return """# MPGA Knowledge Layer \u2014 Navigation Guide

This directory is the MPGA knowledge layer \u2014 the AI's verified map of the codebase.

## Reading order (tiered loading)
1. **Tier 1 \u2014 hot (always read first):** INDEX.md
2. **Tier 2 \u2014 warm (read per task):** GRAPH.md, scopes/<relevant>.md
3. **Tier 3 \u2014 cold (on demand):** sessions/, milestones/, board/tasks/

## File purposes
| File | Purpose |
|------|---------|
| INDEX.md | Project truth map \u2014 identity, key files, conventions, scope registry |
| GRAPH.md | Module dependency graph |
| scopes/*.md | Feature/capability docs with evidence links |
| board/BOARD.md | Human-readable task board |
| board/board.json | Machine-readable board state |
| board/tasks/T*.md | Individual task cards with TDD trace |
| milestones/ | Milestone plans, context, summaries |
| sessions/ | Session handoff documents |

## Evidence link format
```
[E] filepath:startLine-endLine :: symbolName()   # verified, preferred
[E] filepath :: symbolName                        # AST-only, resilient
[Unknown] description                             # explicitly unknown
[Stale:YYYY-MM-DD] filepath:range                # needs re-verification
```

Do NOT modify files in this directory manually. Use:
- `mpga sync` to regenerate the knowledge layer
- `mpga evidence heal` to fix stale evidence links
- `mpga board add/move` to manage tasks
"""


def _evidence_section(scope_content: str) -> str:
    """Return a markdown bullet list of up to 5 evidence links from scope_content."""
    links = re.findall(r"\[E\] .+", scope_content)[:5]
    if links:
        return "\n".join(f"- {l}" for l in links)
    return "- (run `mpga sync` to populate evidence links)"


def _generate_subdir_agents_md(project_root: str, scopes_dir: str) -> None:
    scopes_path = Path(scopes_dir)
    scopes = [f for f in scopes_path.iterdir() if f.suffix == ".md"]
    for scope_file in scopes:
        scope_name = scope_file.stem
        src_dir = Path(project_root) / "src" / scope_name
        if not src_dir.exists():
            continue

        scope_content = scope_file.read_text(encoding="utf-8")

        (src_dir / "AGENTS.md").write_text(
            f"""# {scope_name} Module \u2014 MPGA Scope

For detailed evidence-backed documentation of this module,
read: MPGA/scopes/{scope_name}.md

## Key evidence
{_evidence_section(scope_content)}

## Dependencies
See MPGA/scopes/{scope_name}.md for full dependency graph.
""",
            encoding="utf-8",
        )


def _generate_codex_global_agents_md(cli_command: str) -> str:
    return f"""# MPGA Methodology (Global)

When working in ANY project that contains an MPGA/ directory:

## Core principles
- Evidence over claims: every code assertion must cite [E] file:line
- Unknown is honest: mark gaps as [Unknown], never guess
- TDD is mandatory: test \u2192 implement \u2192 refactor \u2192 update evidence
- Tiered reading: INDEX.md first, scope docs second, deep docs only if needed
- Parallelize reads, not writes: one writer per scope

## Workflow
1. Read MPGA/INDEX.md for project map
2. Check MPGA/board/BOARD.md for current tasks
3. Load relevant MPGA/scopes/*.md before touching code
4. After changes: update evidence links in scope docs
5. Run `{cli_command} drift --quick` to verify nothing broke

## Evidence link format
[E] filepath:startLine-endLine :: symbolName()
[E] filepath :: symbolName (AST-only, resilient)
[Unknown] description (explicitly unknown)
[Stale:YYYY-MM-DD] filepath:range (was valid, needs verification)
"""
