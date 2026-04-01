from __future__ import annotations

import importlib
from typing import Any

import click

from mpga import VERSION
from mpga.core.logger import banner


class LazyGroup(click.Group):
    """Click group that lazily loads commands on first use."""

    def __init__(self, *args: Any, lazy_commands: dict[str, tuple[str, str]] | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._lazy_commands: dict[str, tuple[str, str]] = lazy_commands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_commands.keys())
        return sorted(set(base + lazy))

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.BaseCommand | None:
        # Check already-loaded commands first
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv
        # Lazy-load
        if cmd_name in self._lazy_commands:
            module_path, attr_name = self._lazy_commands[cmd_name]
            mod = importlib.import_module(module_path)
            return getattr(mod, attr_name)
        return None

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        banner()
        super().format_help(ctx, formatter)
        formatter.write(
            "\n"
            "  Examples:\n"
            "    $ mpga init --from-existing    Bootstrap from existing codebase\n"
            "    $ mpga sync                    Generate knowledge layer\n"
            "    $ mpga status                  View project health dashboard\n"
            "    $ mpga drift                   Check evidence integrity\n"
            "    $ mpga export --cursor         Export for Cursor / Windsurf\n"
            "\n"
            "  Docs:  https://github.com/benreich/mpga\n"
        )


# Map of command name -> (module_path, attribute_name)
_COMMANDS: dict[str, tuple[str, str]] = {
    # Core workflow
    "init":       ("mpga.commands.init", "init_cmd"),
    "scan":       ("mpga.commands.scan", "scan_cmd"),
    "sync":       ("mpga.commands.sync", "sync_cmd"),
    "normalize":  ("mpga.commands.sync", "normalize_cmd"),
    "status":     ("mpga.commands.status", "status_cmd"),
    "health":     ("mpga.commands.health", "health_cmd"),
    # Evidence & drift
    "evidence":   ("mpga.commands.evidence", "evidence"),
    "drift":      ("mpga.commands.drift", "drift"),
    # Knowledge layer
    "scope":      ("mpga.commands.scope", "scope"),
    "graph":      ("mpga.commands.graph", "graph"),
    # Project management
    "board":      ("mpga.commands.board_cmd", "board"),
    "develop":    ("mpga.commands.develop", "develop"),
    "milestone":  ("mpga.commands.milestone", "milestone"),
    "session":    ("mpga.commands.session", "session"),
    "hook":       ("mpga.commands.hook", "hook"),
    "hooks":      ("mpga.commands.hook", "hook"),
    # Configuration & export
    "config":     ("mpga.commands.config_cmd", "config_cmd"),
    "export":     ("mpga.commands.export_cmd", "export_cmd"),
    # Metrics & changelog
    "metrics":    ("mpga.commands.metrics", "metrics_cmd"),
    "changelog":  ("mpga.commands.metrics", "changelog_cmd"),
    # PR & decisions
    "pr":         ("mpga.commands.pr", "pr_cmd"),
    "decision":   ("mpga.commands.pr", "decision_cmd"),
    # UI / design
    "wireframe":  ("mpga.commands.wireframe", "wireframe_cmd"),
    "preview":    ("mpga.commands.preview", "preview_cmd"),
    "design-system": ("mpga.commands.design_system", "design_system"),
    # Voice
    "spoke":      ("mpga.commands.spoke", "spoke_cmd"),
    # Memory
    "memory":     ("mpga.commands.memory", "memory"),
    # Index
    "index":      ("mpga.commands.index_cmd", "index_cmd"),
    # Search
    "search":     ("mpga.commands.search", "search_cmd"),
    "ctx":        ("mpga.commands.ctx", "ctx"),
    # API server
    "serve":      ("mpga.commands.serve", "serve_cmd"),
    # Database migrations
    "migrate":    ("mpga.commands.migrate", "migrate_cmd"),
    # Scout
    "scout":      ("mpga.commands.scout", "scout"),
}


@click.group(cls=LazyGroup, lazy_commands=_COMMANDS)
@click.version_option(VERSION, "-v", "--version", message="%(version)s")
def main() -> None:
    """Evidence-backed context engineering for AI-assisted development"""


from mpga.core.logger import log as _log  # noqa: E402


@main.command("diagnose")
@click.argument("files", nargs=-1)
def diagnose_cmd(files: tuple[str, ...]) -> None:
    """Run bug-hunter + optimizer diagnosis."""
    _log.header("Diagnose")
    if files:
        click.echo(f"  Target files: {', '.join(files)}")
    click.echo("  Use /mpga:diagnose to run bug-hunter + optimizer in your AI coding agent.")
    _log.dim("  This skill analyzes code for bugs, performance issues, and optimization opportunities.")


@main.command("secure")
def secure_cmd() -> None:
    """Run security audit."""
    _log.header("Secure")
    click.echo("  Use /mpga:secure to run a security audit in your AI coding agent.")
    _log.dim("  This skill scans for vulnerabilities, insecure patterns, and secrets exposure.")


@main.command("simplify")
@click.argument("files", nargs=-1)
def simplify_cmd(files: tuple[str, ...]) -> None:
    """Improve code elegance."""
    _log.header("Simplify")
    if files:
        click.echo(f"  Target files: {', '.join(files)}")
    click.echo("  Use /mpga:simplify to improve code elegance in your AI coding agent.")
    _log.dim("  This skill reduces complexity, removes duplication, and improves readability.")
