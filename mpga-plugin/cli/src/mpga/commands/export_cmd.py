from __future__ import annotations

import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log

from .export.agents import find_plugin_root
from .export.antigravity import export_antigravity
from .export.claude import export_claude
from .export.codex import export_codex
from .export.cursor import export_cursor

# --- Main export command ------------------------------------------------------


@click.command("export")
@click.option("--claude", "do_claude", is_flag=True, help="Generate CLAUDE.md + .claude/skills/ for Claude Code")
@click.option("--cursor", "do_cursor", is_flag=True, help="Generate .cursor/rules/*.mdc + .cursor/skills/ + .cursor/agents/")  # noqa: E501
@click.option("--codex", "do_codex", is_flag=True, help="Generate AGENTS.md + .codex/skills/ + .codex/agents/*.toml")
@click.option(
    "--antigravity",
    "do_antigravity",
    is_flag=True,
    help="Generate GEMINI.md + .agent/skills/ + .antigravity/rules/ + .agents/workflows/",
)
@click.option("--all", "do_all", is_flag=True, help="Generate for all tools")
@click.option("--global", "is_global", is_flag=True, help="Generate user-level config instead of project config")
@click.option("--workflows", is_flag=True, help="Include workflow files (Antigravity)")
@click.option("--knowledge", is_flag=True, help="Seed Knowledge Items from MPGA/scopes/ (Antigravity)")
# Legacy aliases
@click.option("--cursorrules", is_flag=True, hidden=True, help="Deprecated alias for --cursor")
@click.option("--gemini", is_flag=True, hidden=True, help="Deprecated alias for --codex")
@click.option("--opencode", is_flag=True, hidden=True, help="Generate .opencode/ directory (legacy)")
def export_cmd(
    do_claude: bool,
    do_cursor: bool,
    do_codex: bool,
    do_antigravity: bool,
    do_all: bool,
    is_global: bool,
    workflows: bool,
    knowledge: bool,
    cursorrules: bool,
    gemini: bool,
    opencode: bool,
) -> None:
    """Export knowledge layer \u2014 other tools NEED this, believe me"""
    project_root_path = find_project_root()
    project_root = str(project_root_path) if project_root_path else str(Path.cwd())
    mpga_dir = str(Path(project_root) / "MPGA")
    config = load_config(project_root)
    plugin_root = find_plugin_root()

    if not Path(mpga_dir).exists():
        log.error("MPGA not initialized \u2014 DISASTER! Run `mpga init` first.")
        sys.exit(1)

    index_path = Path(mpga_dir) / "INDEX.md"
    index_content = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    project_name = config.project.name

    exported = 0

    # -- Claude Code -----------------------------------------------------------
    if do_claude or do_all:
        export_claude(project_root, index_content, project_name, plugin_root, is_global)
        log.success("Exported \u2014 your tools just got a LOT smarter")
        exported += 1

    # -- Cursor ----------------------------------------------------------------
    if do_cursor or cursorrules or do_all:
        if cursorrules:
            log.warn("--cursorrules is deprecated \u2014 SAD! Use --cursor instead.")
        export_cursor(project_root, mpga_dir, index_content, project_name, plugin_root, is_global)
        log.success("Exported for Cursor \u2014 it's fine, but without MPGA it's basically guessing")
        exported += 1

    # -- Codex / Gemini CLI ----------------------------------------------------
    if do_codex or gemini or do_all:
        if gemini:
            log.warn("--gemini is deprecated \u2014 very outdated! Use --codex.")
        export_codex(project_root, mpga_dir, index_content, project_name, plugin_root, is_global)
        log.success("Exported \u2014 your tools just got a LOT smarter")
        exported += 1

    # -- Antigravity -----------------------------------------------------------
    if do_antigravity or do_all:
        export_antigravity(
            project_root,
            mpga_dir,
            index_content,
            project_name,
            plugin_root,
            is_global,
            {
                "knowledge": knowledge,
            },
        )
        log.success("Exported \u2014 your tools just got a LOT smarter")
        exported += 1

    # -- Legacy --opencode -----------------------------------------------------
    if opencode:
        opencode_dir = Path(project_root) / ".opencode"
        opencode_dir.mkdir(parents=True, exist_ok=True)
        (opencode_dir / "context.md").write_text(index_content, encoding="utf-8")
        log.success("Generated .opencode/context.md \u2014 TREMENDOUS")
        exported += 1

    if exported == 0:
        log.info("Specify an export target: --claude, --cursor, --codex, --antigravity, --all")
        log.info("Add --global for user-level config.")
        log.info("Add --workflows for Antigravity workflow files.")
        log.info("Add --knowledge to seed Antigravity Knowledge Items from scopes.")
