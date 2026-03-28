"""Tests for the runtime export helper."""

from pathlib import Path


class TestRuntimeExportHelper:
    """runtime export helper tests."""

    def test_copies_assets_with_manifest(self, tmp_path: Path):
        """Copies bin, scripts, and cli assets into .mpga-runtime with a manifest."""
        plugin_root = tmp_path / "plugin"
        project_root = tmp_path / "project"

        (plugin_root / "bin").mkdir(parents=True, exist_ok=True)
        (plugin_root / "scripts").mkdir(parents=True, exist_ok=True)
        (plugin_root / "cli" / "src").mkdir(parents=True, exist_ok=True)

        (plugin_root / "bin" / "mpga.sh").write_text("#!/usr/bin/env bash\n")
        (plugin_root / "scripts" / "setup.sh").write_text("#!/usr/bin/env bash\n")
        (plugin_root / "cli" / "package.json").write_text('{"name":"mpga"}\n')
        (plugin_root / "cli" / "package-lock.json").write_text('{"lockfileVersion":3}\n')
        (plugin_root / "cli" / "tsconfig.json").write_text("{}\n")
        (plugin_root / "cli" / "src" / "index.ts").write_text("export {};\n")

        from mpga.commands.export.runtime import copy_vendored_runtime

        runtime_dir = copy_vendored_runtime(str(project_root), str(plugin_root))
        assert runtime_dir == str(project_root / ".mpga-runtime")

        runtime_path = Path(runtime_dir)
        assert (runtime_path / "bin" / "mpga.sh").exists()
        assert (runtime_path / "scripts" / "setup.sh").exists()
        assert (runtime_path / "cli" / "src" / "index.ts").exists()
        assert (runtime_path / "manifest.json").exists()

    def test_vendored_cli_commands(self):
        """Computes project and global vendored cli commands."""
        from mpga.commands.export.runtime import (
            global_vendored_cli_command,
            project_vendored_cli_command,
        )

        assert project_vendored_cli_command() == "./.mpga-runtime/bin/mpga.sh"
        assert global_vendored_cli_command("/tmp/tool-root") == "/tmp/tool-root/.mpga-runtime/bin/mpga.sh"
