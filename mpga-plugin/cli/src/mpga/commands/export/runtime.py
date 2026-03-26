from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_ASSETS = ("bin", "scripts", "cli")
COPY_EXCLUDES = {"node_modules", ".git", "coverage"}


def _copy_tree(src: Path, dest: Path) -> None:
    if src.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for entry in src.iterdir():
            if entry.name in COPY_EXCLUDES:
                continue
            _copy_tree(entry, dest / entry.name)
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dest))


def project_vendored_cli_command() -> str:
    return "node ./.mpga-runtime/cli/dist/index.js"


def global_vendored_cli_command(base_dir: str) -> str:
    p = Path(base_dir) / ".mpga-runtime" / "cli" / "dist" / "index.js"
    return "node " + str(p).replace("\\", "/")


def copy_vendored_runtime(target_root: str, plugin_root: str | None) -> str | None:
    if not plugin_root:
        return None

    runtime_dir = Path(target_root) / ".mpga-runtime"
    copied_assets: list[str] = []

    runtime_dir.mkdir(parents=True, exist_ok=True)
    for asset in RUNTIME_ASSETS:
        src_path = Path(plugin_root) / asset
        if not src_path.exists():
            continue
        _copy_tree(src_path, runtime_dir / asset)
        copied_assets.append(asset)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(Path(plugin_root)).replace("\\", "/"),
        "assets": copied_assets,
    }
    (runtime_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    return str(runtime_dir)
