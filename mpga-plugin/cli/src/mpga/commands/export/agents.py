from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


# --- Agent metadata -----------------------------------------------------------
# Canonical list of MPGA agents with their per-tool attributes.
# The markdown instructions live in mpga-plugin/agents/<slug>.md.


@dataclass
class AgentMeta:
    slug: str  # filename slug (e.g. "red-dev")
    name: str  # display name
    description: str  # one-line description for agent routing
    model: str  # preferred model
    readonly: bool  # Cursor: cannot write files
    is_background: bool  # Cursor: can run in parallel
    sandbox_mode: str  # Codex: workspace | none


AGENTS: list[AgentMeta] = [
    AgentMeta(
        slug="campaigner",
        name="mpga-campaigner",
        description="Read-only rally diagnostician. Runs a category-by-category audit and aggregates the sharpest evidence-backed case for fixing the project.",
        model="claude-opus-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="red-dev",
        name="mpga-red-dev",
        description="Write failing tests FIRST for a task. Use at the start of every TDD cycle (RED = failing test bar). Never writes implementation code.",
        model="claude-sonnet-4-6",
        readonly=False,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="green-dev",
        name="mpga-green-dev",
        description="Write minimal implementation to make a failing test pass (GREEN = passing test bar). Use after red-dev has written tests. Never modifies tests.",
        model="claude-sonnet-4-6",
        readonly=False,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="blue-dev",
        name="mpga-blue-dev",
        description="Refactor passing code and tests for quality without changing behavior. Use after green-dev. Updates evidence links in scope docs.",
        model="claude-sonnet-4-6",
        readonly=False,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="scout",
        name="mpga-scout",
        description="Read-only codebase explorer. Traces execution paths, maps dependencies, and builds evidence links. Never modifies files.",
        model="claude-sonnet-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="architect",
        name="mpga-architect",
        description="Structural analysis agent. Generates and updates GRAPH.md and scope docs from scout findings. Every claim must cite evidence.",
        model="claude-opus-4-6",
        readonly=False,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="auditor",
        name="mpga-auditor",
        description="Evidence integrity checker. Verifies evidence links resolve, flags stale links, calculates scope health. Read-only \u2014 only flags, never auto-fixes.",
        model="claude-sonnet-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="researcher",
        name="mpga-researcher",
        description="Domain research before planning. Reads scope docs, identifies knowledge gaps, investigates library options and pitfalls.",
        model="claude-opus-4-6",
        readonly=True,
        is_background=False,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="reviewer",
        name="mpga-reviewer",
        description="Two-stage code reviewer. Stage 1: spec compliance + evidence validity. Stage 2: code quality + security. Critical issues block progress.",
        model="claude-opus-4-6",
        readonly=True,
        is_background=False,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="verifier",
        name="mpga-verifier",
        description="Post-execution verification. Runs test suite, checks for stubs, verifies evidence links updated, confirms milestone progress.",
        model="claude-sonnet-4-6",
        readonly=True,
        is_background=False,
        sandbox_mode="workspace",
    ),
    AgentMeta(
        slug="bug-hunter",
        name="mpga-bug-hunter",
        description="Specification-based bug detection. Compares implementation against acceptance criteria, finds edge cases and specification gaps.",
        model="claude-opus-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="optimizer",
        name="mpga-optimizer",
        description="Code quality analyzer. Detects spaghetti, duplication, and elegance issues using Kent Beck and Sandi Metz rules.",
        model="claude-sonnet-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="security-auditor",
        name="mpga-security-auditor",
        description="Security-focused code review. Checks OWASP Top 10, scans for hardcoded secrets, runs npm audit, flags missing input validation.",
        model="claude-sonnet-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
    AgentMeta(
        slug="orchestrator",
        name="mpga-orchestrator",
        description="Dynamic lane management and deadlock detection. Monitors parallel task execution, resolves conflicts, balances load across lanes.",
        model="claude-opus-4-6",
        readonly=True,
        is_background=True,
        sandbox_mode="none",
    ),
]

SKILL_NAMES = [
    "sync-project",
    "brainstorm",
    "plan",
    "develop",
    "drift-check",
    "ask",
    "onboard",
    "rally",
    "ship",
    "handoff",
    "map-codebase",
    "diagnose",
    "secure",
    "simplify",
    "review-pr",
]


def _escape_regexp(value: str) -> str:
    return re.escape(value)


def rewrite_cli_references(
    content: str,
    cli_path: str | None = None,
    plugin_root: str | None = None,
) -> str:
    replacement = cli_path if cli_path is not None else "mpga"

    # Legacy Node.js patterns
    next_content = re.sub(
        r"node\s+\$\{CLAUDE_PLUGIN_ROOT\}/cli/dist/index\.js", replacement, content
    )
    next_content = next_content.replace(
        "${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js", replacement
    )

    # Current shell wrapper pattern
    next_content = next_content.replace(
        "${CLAUDE_PLUGIN_ROOT}/bin/mpga.sh", replacement
    )

    # Python venv pattern
    next_content = next_content.replace(
        "${CLAUDE_PLUGIN_ROOT}/cli/.venv/bin/mpga", replacement
    )

    # Runtime patterns
    next_content = next_content.replace(
        "./.mpga-runtime/bin/mpga.sh", replacement
    )
    next_content = re.sub(
        r"node\s+\./\.mpga-runtime/cli/dist/index\.js", replacement, next_content
    )
    next_content = next_content.replace(
        "./.mpga-runtime/cli/dist/index.js", replacement
    )

    next_content = re.sub(r"\bnpx mpga\b", replacement, next_content)

    if plugin_root:
        normalized_root = plugin_root.replace("\\", "/")
        escaped_root = _escape_regexp(normalized_root)
        # Legacy node patterns with absolute paths
        next_content = re.sub(
            rf"node\s+{escaped_root}/cli/dist/index\.js", replacement, next_content
        )
        next_content = re.sub(
            rf"{escaped_root}/cli/dist/index\.js", replacement, next_content
        )
        next_content = re.sub(
            rf"{escaped_root}/bin/mpga\.sh", replacement, next_content
        )
        next_content = re.sub(
            rf"{escaped_root}/cli/\.venv/bin/mpga", replacement, next_content
        )

    return next_content


# --- Plugin root finder -------------------------------------------------------


def find_plugin_root() -> str | None:
    # When running from the Python package, try to find the plugin root
    # by walking up from this file's location.
    candidate = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    if (candidate / "skills").exists() and (candidate / "agents").exists():
        return str(candidate)
    # Fallback: MPGA_PLUGIN_ROOT env var (set by bin/mpga.sh as PLUGIN_ROOT)
    env_root = os.environ.get("MPGA_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if env_root and (Path(env_root) / "skills").exists():
        return env_root
    return None


# --- Skills copying -----------------------------------------------------------


def copy_skills_to(
    target_skills_dir: str,
    plugin_root: str | None,
    tool_name: str,
    cli_path: str | None = None,
) -> None:
    """Copy or recreate SKILL.md packages from the plugin's skills/ directory
    into the target tool's skills directory."""
    target = Path(target_skills_dir)
    target.mkdir(parents=True, exist_ok=True)

    for skill_name in SKILL_NAMES:
        dest_dir = target / f"mpga-{skill_name}"
        dest_dir.mkdir(parents=True, exist_ok=True)

        if plugin_root:
            src_dir = Path(plugin_root) / "skills" / skill_name
            if src_dir.exists():
                _copy_dir(src_dir, dest_dir, tool_name, cli_path, plugin_root)
                continue

        # Fallback: write a minimal SKILL.md if plugin root not available
        skill_md = dest_dir / "SKILL.md"
        if not skill_md.exists():
            skill_md.write_text(
                _generate_fallback_skill_md(skill_name), encoding="utf-8"
            )


def _copy_dir(
    src: Path,
    dest: Path,
    tool_name: str,
    cli_path: str | None = None,
    plugin_root: str | None = None,
) -> None:
    for entry in src.iterdir():
        src_path = entry
        dest_path = dest / entry.name
        if entry.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
            _copy_dir(src_path, dest_path, tool_name, cli_path, plugin_root)
        else:
            content = src_path.read_text(encoding="utf-8")
            if cli_path:
                content = rewrite_cli_references(content, cli_path, plugin_root)
            elif tool_name != "claude":
                # Rewrite CLAUDE_PLUGIN_ROOT references to use mpga for non-Claude tools
                content = rewrite_cli_references(content, None, plugin_root)
            dest_path.write_text(content, encoding="utf-8")


def _generate_fallback_skill_md(skill_name: str) -> str:
    descriptions: dict[str, str] = {
        "sync-project": "Rebuild the MPGA knowledge layer from the current codebase state",
        "brainstorm": "Socratic design refinement before writing any code",
        "plan": "Generate an evidence-based task breakdown for a milestone",
        "develop": "Orchestrate the TDD cycle for a task (red \u2192 green \u2192 blue \u2192 review)",
        "drift-check": "Validate evidence links and detect stale scope docs",
        "ask": "Answer questions about the codebase using MPGA scope docs as citations",
        "onboard": "Guided tour of the codebase using the MPGA knowledge layer",
        "rally": "Run the MPGA campaign rally diagnostic and aggregate project issues",
        "ship": "Verify, commit, update evidence, and advance milestone",
        "handoff": "Export session state for cross-context continuity",
        "map-codebase": "Parallel scout agents analyze the full codebase and generate scopes",
        "diagnose": "Find bugs and quality issues using bug-hunter + optimizer agents",
        "secure": "Run a comprehensive security audit with OWASP and secrets scanning",
        "simplify": "Improve code elegance using Kent Beck and Sandi Metz rules",
        "review-pr": "Comprehensive PR review with reviewer + bug-hunter + security-auditor",
    }

    desc = descriptions.get(skill_name, skill_name)
    cli_equivalent = skill_name.replace("-", " ")
    return f"""---
name: mpga-{skill_name}
description: {desc}
---

## {skill_name}

See MPGA documentation for full protocol.

Run `mpga {cli_equivalent}` for CLI equivalent.
"""


# --- Agent file generators ----------------------------------------------------


def read_agent_instructions(
    plugin_root: str | None,
    slug: str,
    cli_path: str | None = None,
) -> str:
    if plugin_root:
        agent_path = Path(plugin_root) / "agents" / f"{slug}.md"
        if agent_path.exists():
            content = agent_path.read_text(encoding="utf-8")
            # Strip the H1 title line -- it becomes redundant with the YAML frontmatter
            content = re.sub(r"^# Agent:.*\n", "", content).lstrip()
            return rewrite_cli_references(content, cli_path, plugin_root)
    return f"See MPGA documentation for full {slug} agent protocol."
