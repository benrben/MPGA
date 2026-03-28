"""mpga normalize — run the verify→heal→re-verify pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from mpga.core.config import find_project_root, load_config
from mpga.core.logger import log, victory
from mpga.pipeline import normalize


@click.command("normalize")
def normalize_cmd() -> None:
    """Run the verify→heal→re-verify pipeline and rewrite scope health lines."""
    project_root = find_project_root() or Path.cwd()
    mpga_dir = Path(project_root) / "MPGA"

    if not mpga_dir.exists():
        log.error("MPGA not initialized — run `mpga init` first.")
        sys.exit(1)

    config = load_config(project_root)
    log.header("MPGA Normalize — Healing the Evidence Layer")

    result = normalize(str(project_root), config)

    log.success(
        f"Normalized {result.scopes_healed} scope(s), "
        f"healed {result.links_healed} link(s)"
    )
    victory("Evidence layer is HEALTHY again!")
