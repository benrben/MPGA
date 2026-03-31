from __future__ import annotations

import shutil
import sqlite3
import subprocess
from pathlib import Path

import click

from mpga.core.config import default_config, save_config
from mpga.core.logger import banner, log
from mpga.core.scanner import detect_project_type, scan
from mpga.db.connection import get_connection
from mpga.db.schema import create_schema


@click.command("init")
@click.option("--from-zero", is_flag=True, help="New project with no existing code")
@click.option("--from-existing", is_flag=True, help="Scan and map an existing codebase")
def init_cmd(from_zero: bool, from_existing: bool) -> None:
    """Bootstrap MPGA SQLite knowledge layer in current project."""
    project_root = Path.cwd()
    db_path = project_root / ".mpga" / "mpga.db"
    config_path = project_root / ".mpga" / "mpga.config.json"

    # --- Auto-migrate legacy MPGA/ folder to DB before any other work ---
    mpga_dir = Path(project_root) / "MPGA"
    if mpga_dir.exists() and mpga_dir.is_dir():
        try:
            from mpga.commands.migrate import (
                migrate_board,
                migrate_milestones,
                migrate_scopes,
                migrate_tasks,
            )

            # Ensure DB + schema exist before migrating
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _migrate_conn = get_connection(str(db_path))
            try:
                create_schema(_migrate_conn)
                board_dir = str(mpga_dir)
                tasks_dir = str(mpga_dir / "tasks")
                scopes_dir = str(mpga_dir / "scopes")
                milestones_dir = str(mpga_dir / "milestones")

                migrate_board(_migrate_conn, board_dir)
                if Path(tasks_dir).is_dir():
                    migrate_tasks(_migrate_conn, tasks_dir)
                if Path(scopes_dir).is_dir():
                    migrate_scopes(_migrate_conn, scopes_dir)
                if Path(milestones_dir).is_dir():
                    migrate_milestones(_migrate_conn, milestones_dir)
            finally:
                _migrate_conn.close()

            shutil.rmtree(mpga_dir)
            log.info("Migrated MPGA/ folder to DB and removed it")
        except (OSError, sqlite3.Error) as e:
            shutil.rmtree(mpga_dir)
            log.info(f"Removed deprecated MPGA/ folder (DB is the source of truth): {e}")

    banner()

    if db_path.exists():
        log.warn(".mpga/mpga.db already initialized \u2014 we're already GREAT!")
        log.dim("Run `mpga sync` to refresh the knowledge layer.")
        return

    log.info(f"Making {project_root} GREAT AGAIN!")

    # Create .mpga/ directory (dot-dir only — no legacy MPGA/ folder)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    log.dim("  created .mpga/")

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
    finally:
        conn.close()
    log.success("Created .mpga/mpga.db — SQLite schema ready to WIN!")

    # Detect project info
    project_name = project_root.name
    project_type = "Application"
    config = default_config()
    config.project.name = project_name

    if from_existing:
        log.info("Scanning the existing codebase \u2014 going to be BEAUTIFUL...")
        try:
            scan_result = scan(str(project_root), config.project.ignore)
            project_type = detect_project_type(scan_result)
            log.success(
                f"Detected: {project_type} ({scan_result.total_files} files, {scan_result.total_lines:,} lines)"
            )

            langs = [lang for lang in scan_result.languages if lang not in ("other", "markdown")]
            if langs:
                config.project.languages = langs
            if scan_result.entry_points:
                config.project.entry_points = scan_result.entry_points
        except (OSError, ValueError) as e:
            log.warn(f"Scan failed — no problem, we have the BEST defaults! ({e})")

    # Save config to .mpga/
    save_config(config, config_path)
    log.success("Created .mpga/mpga.config.json \u2014 the BEST configuration, believe me!")

    # Setup spoke (Trump voice TTS)
    spoke_dir = project_root / ".mpga-runtime" / "spoke"
    spoke_setup = spoke_dir / "setup.sh"
    spoke_venv = spoke_dir / "venv" / "bin" / "python3"
    if spoke_setup.exists():
        click.echo("")
        log.info("Setting up Trump voice (F5-TTS) \u2014 the BEST voice, believe me...")
        try:
            if not spoke_venv.exists():
                subprocess.run(["bash", str(spoke_setup)], check=True)
            else:
                log.dim("  Spoke already installed.")
                # Just make sure server is running
                server_script = spoke_dir / "server.py"
                health = subprocess.run(
                    ["curl", "-sf", "http://127.0.0.1:5151/health"],
                    capture_output=True,
                    timeout=1,
                )
                if health.returncode != 0:
                    log.dim("  Starting spoke server...")
                    child = subprocess.Popen(
                        [str(spoke_venv), str(server_script), "--port", "5151"],
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    (spoke_dir / ".server.pid").write_text(str(child.pid))
            log.success("Spoke ready \u2014 Trump voice ACTIVATED!")
        except (OSError, subprocess.SubprocessError) as e:
            log.warn(f"Spoke setup failed — voice will be available later via `mpga spoke --setup` ({e})")

    click.echo("")
    log.success("MPGA initialized \u2014 your project is about to be GREAT AGAIN!")
    click.echo("")
    log.dim("Your next steps \u2014 each one a WINNER:")
    if from_existing:
        log.dim("  mpga sync          \u2014 generate knowledge layer, it's going to be FANTASTIC")
        log.dim("  mpga status        \u2014 see how GREAT your project is looking")
    else:
        log.dim("  mpga status        \u2014 see how GREAT your project is looking")
        log.dim("  mpga milestone new \u2014 start your first milestone, HUGE things ahead")
    log.dim('  mpga spoke "text"  \u2014 hear it in Trump voice, TREMENDOUS')
