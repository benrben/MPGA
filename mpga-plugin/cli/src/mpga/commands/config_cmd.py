from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from mpga.core.config import (
    find_project_root,
    get_config_value,
    load_config,
    save_config,
    set_config_value,
)
from mpga.core.logger import log


def _flatten_config(obj: Any, prefix: str = "") -> list[tuple[str, Any]]:
    if not isinstance(obj, dict) and not hasattr(obj, "__dataclass_fields__"):
        return [(prefix, obj)]

    # Convert dataclass to dict if needed
    if hasattr(obj, "__dataclass_fields__"):
        from dataclasses import asdict

        obj = asdict(obj)

    result: list[tuple[str, Any]] = []
    for k, v in obj.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.extend(_flatten_config(v, full_key))
        elif isinstance(v, list):
            result.append((full_key, ", ".join(str(i) for i in v)))
        else:
            result.append((full_key, v))
    return result


@click.group("config", invoke_without_command=True)
@click.pass_context
def config_cmd(ctx: click.Context) -> None:
    """View and update MPGA configuration."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@config_cmd.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def config_show(as_json: bool) -> None:
    """Display current configuration."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)

    if as_json:
        from mpga.core.config import _config_to_dict

        click.echo(json.dumps(_config_to_dict(config), indent=2))
        return

    log.header("MPGA Configuration")
    lines = _flatten_config(config)
    for key, value in lines:
        click.echo(f"  {key:<45} {value}")


@config_cmd.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Update a configuration value (e.g. drift.ciThreshold 90)."""
    project_root = find_project_root() or Path.cwd()
    config = load_config(project_root)

    config_path = Path(project_root) / ".mpga" / "mpga.config.json"
    if not config_path.exists():
        config_path = Path(project_root) / "mpga.config.json"

    if not config_path.exists():
        log.error("No mpga.config.json found. Run `mpga init` first.")
        sys.exit(1)

    before = get_config_value(config, key)
    if before is None:
        log.error(f"Unknown config key: {key}")
        sys.exit(1)

    set_config_value(config, key, value)
    save_config(config, config_path)

    log.success(f"{key}: {before} -> {get_config_value(config, key)}")
