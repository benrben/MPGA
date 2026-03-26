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
)
from .runtime import (
    copy_vendored_runtime,
    global_vendored_cli_command,
    project_vendored_cli_command,
)


# --- Cursor export ------------------------------------------------------------


def export_cursor(
    project_root: str,
    mpga_dir: str,
    index_content: str,
    project_name: str,
    plugin_root: str | None,
    is_global: bool,
) -> None:
    if is_global:
        home = os.environ.get("HOME", "~")
        cursor_root = str(Path(home) / ".cursor")
        cli_command = global_vendored_cli_command(cursor_root) if plugin_root else "mpga"
        copy_vendored_runtime(cursor_root, plugin_root)
        log.info("Add the following to Cursor Settings > General > Rules for AI:")
        log.info("\n" + _generate_cursor_global(cli_command))
        global_skills_dir = str(Path(home) / ".cursor" / "skills")
        copy_skills_to(global_skills_dir, plugin_root, "cursor", cli_command)
        log.success(f"Generated ~/.cursor/skills/ ({len(SKILL_NAMES)} skills)")
        # Global agents
        global_agents_dir = Path(home) / ".cursor" / "agents"
        global_agents_dir.mkdir(parents=True, exist_ok=True)
        for agent in AGENTS:
            (global_agents_dir / f"{agent.name}.md").write_text(
                _generate_cursor_agent_md(agent, plugin_root, cli_command),
                encoding="utf-8",
            )
        log.success(f"Generated ~/.cursor/agents/ ({len(AGENTS)} agents)")
    else:
        cli_command = project_vendored_cli_command() if plugin_root else "mpga"
        copy_vendored_runtime(project_root, plugin_root)
        # Rules
        rules_dir = Path(project_root) / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "mpga-project.mdc").write_text(
            _generate_cursor_project_mdc(index_content, project_name, cli_command),
            encoding="utf-8",
        )
        (rules_dir / "mpga-evidence.mdc").write_text(
            _generate_cursor_evidence_mdc(cli_command), encoding="utf-8"
        )
        (rules_dir / "mpga-tdd.mdc").write_text(
            _generate_cursor_tdd_mdc(), encoding="utf-8"
        )
        (rules_dir / "mpga-scopes.mdc").write_text(
            _generate_cursor_scopes_mdc(mpga_dir), encoding="utf-8"
        )
        log.success("Generated .cursor/rules/ (4 MDC files)")
        # Skills
        cursor_skills_dir = str(Path(project_root) / ".cursor" / "skills")
        copy_skills_to(cursor_skills_dir, plugin_root, "cursor", cli_command)
        log.success(f".cursor/skills/ ({len(SKILL_NAMES)} skills)")
        # Agents
        cursor_agents_dir = Path(project_root) / ".cursor" / "agents"
        cursor_agents_dir.mkdir(parents=True, exist_ok=True)
        for agent in AGENTS:
            (cursor_agents_dir / f"{agent.name}.md").write_text(
                _generate_cursor_agent_md(agent, plugin_root, cli_command),
                encoding="utf-8",
            )
        log.success(f".cursor/agents/ ({len(AGENTS)} agents)")


# --- Cursor generators --------------------------------------------------------


def _generate_cursor_agent_md(
    agent: AgentMeta,
    plugin_root: str | None,
    cli_command: str,
) -> str:
    """Generate Cursor-format agent markdown (.cursor/agents/mpga-<slug>.md)"""
    instructions = read_agent_instructions(plugin_root, agent.slug, cli_command)

    return f"""---
name: {agent.name}
description: {agent.description}
model: {agent.model}
readonly: {str(agent.readonly).lower()}
is_background: {str(agent.is_background).lower()}
---

{instructions}"""


def _generate_cursor_project_mdc(
    index_content: str,
    _project_name: str,
    cli_command: str,
) -> str:
    milestones_match = re.search(
        r"## Active milestone\n([\s\S]*?)(?=\n##|$)", index_content
    )
    milestone = milestones_match.group(1).strip() if milestones_match else "(none)"

    now = datetime.now(timezone.utc).isoformat()

    return f"""---
description: "MPGA project context \u2014 evidence-backed navigation layer"
globs:
alwaysApply: true
---

# MPGA Project Context

This project uses MPGA for evidence-backed context engineering.

## Before writing ANY code
1. Read MPGA/INDEX.md for the project map and scope registry
2. Find the relevant scope doc in MPGA/scopes/ for the area you're working in
3. Check MPGA/board/BOARD.md for current task assignments

## Evidence rules
- Every claim about how code works MUST cite a file:line evidence link
- Format: [E] src/auth/jwt.ts:42-67 :: validateToken()
- If you cannot find evidence \u2192 mark as [Unknown]
- Never guess \u2014 look it up or mark it unknown

## Key files
@MPGA/INDEX.md

## Active milestone
{milestone}

Generated: {now}
"""


def _generate_cursor_evidence_mdc(cli_command: str) -> str:
    return f"""---
description: "MPGA evidence link conventions \u2014 format and verification rules"
globs:
alwaysApply: true
---

# Evidence Link Protocol

## Format
```
[E] filepath:startLine-endLine :: symbolName()    # exact range + AST anchor (preferred)
[E] filepath :: symbolName                         # AST-only, resilient to line shifts
[Unknown] description                              # explicitly unknown \u2014 never guess
[Stale:YYYY-MM-DD] filepath:range                 # was valid, needs re-verification
```

## When to use
- Before touching code: read the relevant scope doc in MPGA/scopes/
- After changing code: check if evidence links in the scope doc still resolve
- When in doubt: mark [Unknown]

## Verification
```bash
{cli_command} evidence verify       # check all links
{cli_command} drift --quick         # fast staleness check
{cli_command} evidence heal --auto  # auto-fix broken links via AST
```
"""


def _generate_cursor_tdd_mdc() -> str:
    return """---
description: "MPGA TDD enforcement \u2014 write tests before implementation"
globs:
alwaysApply: true
---

# TDD Protocol (mandatory)

1. WRITE FAILING TEST FIRST \u2014 never write implementation before a test exists
2. Run test \u2014 confirm it FAILS (red)
3. Write MINIMAL implementation to pass (green)
4. Refactor without changing behavior (blue)
5. Update evidence links in the relevant MPGA/scopes/*.md file
6. Keep one writer per scope; parallelize read-only scouts and auditors instead

If you find yourself writing implementation code without a test:
STOP. Delete it. Write the test first.
"""


def _generate_cursor_scopes_mdc(mpga_dir: str) -> str:
    scopes_dir = Path(mpga_dir) / "scopes"
    scope_lines = "- (no scopes yet \u2014 run `mpga sync` to generate)"

    if scopes_dir.exists():
        scopes = [
            f.stem
            for f in sorted(scopes_dir.iterdir())
            if f.suffix == ".md"
        ]
        if scopes:
            scope_lines = "\n".join(
                f"- {s} \u2192 @MPGA/scopes/{s}.md" for s in scopes
            )

    return f"""---
description: "Load MPGA scope documents when working on specific features. Use when the user asks about a specific feature area or module."
globs:
alwaysApply: false
---

# MPGA Scope Lookup

When working on a specific feature, load the relevant scope document:

{scope_lines}

Each scope doc contains:
- Evidence links proving how the feature actually works
- Known unknowns (explicitly marked)
- Dependencies to other scopes
- Drift status (are the evidence links still valid?)

Always check the scope BEFORE making changes.
"""


def _generate_cursor_global(cli_command: str) -> str:
    return """When you see an MPGA/ directory in any project:
- Read MPGA/INDEX.md before starting any task
- Use evidence links [E] format: [E] file:line :: symbol()
- Mark unknowns as [Unknown] \u2014 never guess
- Follow TDD: test first, implement second, refactor third
- Check MPGA/board/BOARD.md for task assignments
- After modifying code, consider if evidence links need updating
- Prefer reading scope docs over scanning entire directories"""
