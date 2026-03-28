from __future__ import annotations

import click

from mpga.core.logger import log


@click.command("diagnose")
@click.argument("files", nargs=-1)
def diagnose_cmd(files: tuple[str, ...]) -> None:
    """Run bug-hunter + optimizer diagnosis."""
    log.header("Diagnose")
    if files:
        click.echo(f"  Target files: {', '.join(files)}")
    click.echo("  Use /mpga:diagnose to run bug-hunter + optimizer in your AI coding agent.")
    log.dim("  This skill analyzes code for bugs, performance issues, and optimization opportunities.")


@click.command("secure")
def secure_cmd() -> None:
    """Run security audit."""
    log.header("Secure")
    click.echo("  Use /mpga:secure to run a security audit in your AI coding agent.")
    log.dim("  This skill scans for vulnerabilities, insecure patterns, and secrets exposure.")


@click.command("simplify")
@click.argument("files", nargs=-1)
def simplify_cmd(files: tuple[str, ...]) -> None:
    """Improve code elegance."""
    log.header("Simplify")
    if files:
        click.echo(f"  Target files: {', '.join(files)}")
    click.echo("  Use /mpga:simplify to improve code elegance in your AI coding agent.")
    log.dim("  This skill reduces complexity, removes duplication, and improves readability.")
